#!/usr/bin/env python3
import json
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from gitbed.graph import build_graph
from gitbed.state import AgentState
from gitbed.utils import fetch_github_file, get_default_repo, get_default_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gitbed")


def main():
    repo_name = os.environ.get("GITHUB_REPO", "")
    if not repo_name or "username/" in repo_name or "your_" in repo_name:
        detected_repo = get_default_repo()
        if detected_repo:
            os.environ["GITHUB_REPO"] = detected_repo

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or "your_" in token or token.startswith("github_pat_antigravity"):
        gh_token = get_default_token()
        if gh_token:
            os.environ["GITHUB_TOKEN"] = gh_token
            token = gh_token

    required_env = ["GITHUB_TOKEN", "OPENAI_API_KEY", "GITHUB_REPO"]
    missing = [var for var in required_env if not os.environ.get(var) or "your_" in os.environ.get(var, "")]
    if missing:
        logger.error(f"Missing required environment variable(s): {', '.join(missing)}")
        logger.info("Provide keys in your .env file or authenticate via 'gh auth login'.")
        sys.exit(1)

    diff_path = "mock_diff.json"
    if not os.path.exists(diff_path):
        logger.error(f"Diff file '{diff_path}' not found")
        sys.exit(1)

    with open(diff_path, "r", encoding="utf-8") as f:
        diff_data = json.load(f)

    repo_name = os.environ["GITHUB_REPO"]
    token = os.environ["GITHUB_TOKEN"]

    try:
        original_code = fetch_github_file(repo_name, token, "pin_config.h")
        logger.info(f"Fetched pin_config.h from GitHub repo '{repo_name}'")
    except Exception as exc:
        logger.warning(f"Could not fetch pin_config.h from repo ({exc}), using default template")
        original_code = (
            "#ifndef PIN_CONFIG_H\n"
            "#define PIN_CONFIG_H\n\n"
            "// Hardware Pin Configurations - PCB Rev A\n"
            "#define STATUS_LED_PIN PB6\n"
            "#define UART_TX_PIN PA9\n"
            "#define UART_RX_PIN PA10\n\n"
            "void init_pins();\n\n"
            "#endif // PIN_CONFIG_H\n"
        )

    app = build_graph()

    initial_state: AgentState = {
        "diff_data": diff_data,
        "original_code": original_code,
        "updated_code": "",
        "error_log": "",
        "attempts": 0,
        "pr_url": "",
    }

    logger.info("Starting GitBed agent pipeline")
    final_state = app.invoke(initial_state)

    pr_url = final_state.get("pr_url")
    if pr_url:
        logger.info(f"Workflow completed successfully. PR URL: {pr_url}")
    else:
        logger.error("Workflow failed to create Pull Request")


if __name__ == "__main__":
    main()
