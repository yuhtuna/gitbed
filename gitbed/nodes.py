import json
import logging
import os
import random
from github import Github
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from gitbed.state import AgentState
from gitbed.utils import clean_code_block, verify_cpp_compilation

logger = logging.getLogger(__name__)


def generate_patch(state: AgentState) -> dict:
    attempts = state.get("attempts", 0) + 1
    logger.info(f"Generating C++ patch (attempt {attempts})")

    diff_json = json.dumps(state.get("diff_data", {}), indent=2)
    original_code = state.get("original_code", "")
    error_log = state.get("error_log", "")

    system_prompt = (
        "You are an embedded C/C++ engineer updating hardware pin configurations (`pin_config.h`).\n"
        "Rules:\n"
        "1. Output valid C++ header code ONLY.\n"
        "2. Update pin constants matching the hardware netlist diff.\n"
        "3. Keep all include guards and formatting."
    )

    user_prompt = (
        f"Netlist Diff:\n{diff_json}\n\n"
        f"Original Code:\n{original_code}\n"
    )
    if error_log:
        user_prompt += f"\nPrevious Error:\n{error_log}\nFix the error above."

    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
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

    logger.info("Verification passed successfully")
    return {"error_log": ""}


def open_pr(state: AgentState) -> dict:
    logger.info("Creating GitHub Pull Request")
    token = os.environ["GITHUB_TOKEN"]
    repo_name = os.environ["GITHUB_REPO"]

    g = Github(token)
    repo = g.get_repo(repo_name)

    base_branch = repo.default_branch
    main_ref = repo.get_branch(base_branch)

    branch_name = f"hardware-sync-{random.randint(1000, 9999)}"
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_ref.commit.sha)

    file_path = "pin_config.h"
    commit_msg = f"chore(devops): update {file_path} hardware pin assignments"
    content = state["updated_code"]

    try:
        current_file = repo.get_contents(file_path, ref=branch_name)
        repo.update_file(
            path=file_path,
            message=commit_msg,
            content=content,
            sha=current_file.sha,
            branch=branch_name,
        )
    except Exception:
        repo.create_file(
            path=file_path,
            message=commit_msg,
            content=content,
            branch=branch_name,
        )

    signal = state["diff_data"].get("signal_name", "Pin Configuration")
    old_pin = state["diff_data"].get("old_pin", "N/A")
    new_pin = state["diff_data"].get("new_pin", "N/A")

    pr = repo.create_pull(
        title=f"Hardware Netlist Sync: {signal}",
        body=f"Automated hardware patch for signal `{signal}`: `{old_pin}` -> `{new_pin}`.",
        head=branch_name,
        base=base_branch,
    )

    logger.info(f"Pull Request opened: {pr.html_url}")
    return {"pr_url": pr.html_url}
