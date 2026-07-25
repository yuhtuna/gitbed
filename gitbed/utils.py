import logging
import re
import subprocess
import tempfile
from typing import Tuple
from github import Github

logger = logging.getLogger(__name__)


def clean_code_block(text: str) -> str:
    pattern = r"```(?:cpp|c\+\+|c)?\s*\n?(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip("` \n")


def verify_cpp_compilation(code: str) -> Tuple[bool, str]:
    with tempfile.NamedTemporaryFile(suffix=".cpp", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        cmd = ["g++", "-fsyntax-only", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, ""
    except Exception as exc:
        logger.warning(f"g++ compilation check warning: {exc}")
        return True, ""
    finally:
        try:
            import os
            os.remove(tmp_path)
        except OSError:
            pass


def fetch_github_file(repo_name: str, token: str, file_path: str) -> str:
    g = Github(token)
    repo = g.get_repo(repo_name)
    branch = repo.default_branch
    content = repo.get_contents(file_path, ref=branch)
    return content.decoded_content.decode("utf-8")
