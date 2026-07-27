import json
import logging
import os
import random
from github import Github
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from gitbed.bridge import BridgeCache
from gitbed.conflict_checker import PinConflictChecker
from gitbed.hal_sync import build_multi_file_patch_bundle
from gitbed.state import AgentState
from gitbed.utils import clean_code_block, verify_cpp_compilation

logger = logging.getLogger(__name__)


def generate_patch(state: AgentState) -> dict:
    attempts = state.get("attempts", 0) + 1
    logger.info(f"Generating C++ patch (attempt {attempts})")

    diff_data = state.get("diff_data", {})
    original_code = state.get("original_code", "")
    error_log = state.get("error_log", "")

    # 1. Check Deterministic Bridge Cache
    if not error_log:
        cache = BridgeCache()
        success, deterministic_code, rule_id = cache.apply_rules(original_code, diff_data)
        if success:
            logger.info(f"Cache HIT: Applied deterministic bridge rule '{rule_id}' (0ms, $0 AI cost)")
            return {
                "updated_code": deterministic_code,
                "attempts": attempts,
            }

    # 2. AI Synthesizer Fallback
    logger.info("Cache MISS: Invoking AI engine to synthesize C++ patch")
    diff_json = json.dumps(diff_data, indent=2)

    system_prompt = (
        "You are an embedded C/C++ hardware engineer updating hardware pin configurations (`pin_config.h`).\n"
        "Rules:\n"
        "1. Output valid C++ header code ONLY.\n"
        "2. You are provided with the full hardware net topology (`connected_nodes`).\n"
        "3. ALWAYS target the primary microcontroller / IC pin (component 'U' or 'IC') for firmware `#define SIGNAL_PIN` macros.\n"
        "4. Ignore passive pull-up/pull-down resistor pins (component 'R') and decoupling capacitors ('C') when determining the macro pin value.\n"
        "5. Keep all include guards and formatting intact."
    )

    user_prompt = (
        f"Netlist Diff:\n{diff_json}\n\n"
        f"Original Code:\n{original_code}\n"
    )
    if error_log:
        user_prompt += f"\nPrevious Error:\n{error_log}\nFix the error above."

    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    logger.info(f"Using OpenAI model: {model_name}")
    llm = ChatOpenAI(model=model_name, temperature=0.1, max_tokens=500)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    raw_text = response.content if isinstance(response.content, str) else str(response.content)
    cleaned_code = clean_code_block(raw_text)

    return {
        "updated_code": cleaned_code,
        "attempts": attempts,
    }


def verify_patch(state: AgentState) -> dict:
    logger.info("Verifying C++ patch with compiler and specification check")
    code = state.get("updated_code", "")
    diff = state.get("diff_data", {})
    new_pin = diff.get("new_pin", "")
    signal_name = diff.get("signal_name", "STATUS_LED")

    # 1. Compiler syntax verification
    valid, compile_err = verify_cpp_compilation(code)
    if not valid:
        err_msg = f"Compiler error:\n{compile_err}"
        logger.warning(f"Verification failed: {err_msg}")
        return {"error_log": err_msg}

    # 2. Specification verification
    if new_pin and new_pin not in code:
        err_msg = f"Specification error: pin '{new_pin}' missing in code"
        logger.warning(f"Verification failed: {err_msg}")
        return {"error_log": err_msg}

    # 3. Hardware Pin Conflict Verification
    checker = PinConflictChecker()
    clean_conflict, conflict_errs = checker.check_code_conflicts(code, new_pin, signal_name)
    if not clean_conflict:
        err_msg = "Hardware Conflict error:\n" + "\n".join(conflict_errs)
        logger.warning(f"Verification failed: {err_msg}")
        return {"error_log": err_msg}

    logger.info("Verification passed successfully")
    return {"error_log": ""}


def open_pr(state: AgentState) -> dict:
    logger.info("Creating GitHub Pull Request with Multi-File HAL Bundle")
    token = os.environ["GITHUB_TOKEN"]
    repo_name = os.environ["GITHUB_REPO"]

    g = Github(token)
    repo = g.get_repo(repo_name)

    base_branch = repo.default_branch
    main_ref = repo.get_branch(base_branch)

    branch_name = f"hardware-sync-{random.randint(1000, 9999)}"
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_ref.commit.sha)

    # Build multi-file HAL bundle with existing content merging
    diff_data = state.get("diff_data", {})
    updated_code = state.get("updated_code", "")

    existing_files = {}
    for path in ["boards/app.overlay", "src/gpio_driver.cpp"]:
        try:
            current_f = repo.get_contents(path, ref=base_branch)
            existing_files[path] = current_f.decoded_content.decode("utf-8")
        except Exception:
            pass

    bundle = build_multi_file_patch_bundle(diff_data, updated_code, existing_files)

    signal = diff_data.get("signal_name", "Pin Configuration")
    old_pin = diff_data.get("old_pin", "N/A")
    new_pin = diff_data.get("new_pin", "N/A")

    for file_path, content in bundle.items():
        commit_msg = f"chore(devops): update {file_path} for {signal} pin reassignment"
        try:
            current_file = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                path=file_path,
                message=commit_msg,
                content=content,
                sha=current_file.sha,
                branch=branch_name,
            )
            logger.info(f"Updated {file_path} in branch {branch_name}")
        except Exception:
            repo.create_file(
                path=file_path,
                message=commit_msg,
                content=content,
                branch=branch_name,
            )
            logger.info(f"Created {file_path} in branch {branch_name}")

    pr_body = (
        f"## 🤖 GitBed DevOps Bot - Multi-File HAL Sync\n\n"
        f"**Signal Name:** `{signal}`\n"
        f"**Pin Reassignment:** `{old_pin}` ➡️ `{new_pin}`\n\n"
        f"### Files Updated\n"
        f"- `pin_config.h` (C/C++ Macro Header)\n"
        f"- `boards/app.overlay` (Zephyr DeviceTree Overlay)\n"
        f"- `src/gpio_driver.cpp` (GPIO Driver Init Function)\n\n"
        f"✅ Static compiler verification & Pin conflict check passed."
    )

    pr = repo.create_pull(
        title=f"Hardware Netlist Sync: {signal} ({old_pin} -> {new_pin})",
        body=pr_body,
        head=branch_name,
        base=base_branch,
    )

    logger.info(f"Pull Request opened: {pr.html_url}")
    return {"pr_url": pr.html_url}
