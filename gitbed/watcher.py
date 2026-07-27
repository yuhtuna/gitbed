import logging
import os
import re
import time
from typing import Callable, Optional

from gitbed.parsers import parse_altium_netlist, parse_kicad_netlist

logger = logging.getLogger(__name__)


def _load_baseline_pins() -> dict:
    """Fetches pin_config.h from the target GitHub repo and extracts current pin assignments."""
    try:
        from gitbed.utils import fetch_github_file, get_default_token
        token = os.environ.get("GITHUB_TOKEN") or get_default_token()
        repo = os.environ.get("GITHUB_REPO", "")
        if not token or not repo:
            return {}
        code = fetch_github_file(repo, token, "pin_config.h")
        # Parse lines like: #define INA_SDA_PIN P4
        pins = {}
        for m in re.finditer(r"#define\s+(\w+)_PIN\s+(P\w+)", code):
            signal = m.group(1)  # e.g. INA_SDA
            pin = m.group(2)     # e.g. P4
            pins[signal] = pin
        logger.info(f"Loaded {len(pins)} baseline pin assignments from GitHub: {pins}")
        return pins
    except Exception as exc:
        logger.warning(f"Could not load baseline pins from GitHub: {exc}")
        return {}


def process_netlist_file(file_path: str) -> Optional[dict]:
    """Reads and parses an EDA netlist file, then compares against GitHub baseline to find real changes."""
    if not os.path.exists(file_path):
        logger.error(f"Netlist file '{file_path}' not found.")
        return None

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    diffs = []
    lower_path = file_path.lower()
    if lower_path.endswith(".xml") or "Altium" in content or "<Netlist" in content or (lower_path.endswith(".net") and "(export" not in content):
        diffs = parse_altium_netlist(content)
    elif lower_path.endswith(".net") and "(export" in content:
        diffs = parse_kicad_netlist(content)

    if not diffs:
        logger.warning(f"No valid signal data parsed from '{file_path}'")
        return None

    logger.info(f"Parsed {len(diffs)} total nets from EDA export")

    # Load current firmware pin assignments from GitHub
    baseline = _load_baseline_pins()
    if not baseline:
        logger.warning("No baseline firmware found on GitHub. Returning first parsed net.")
        return diffs[0]

    # Compare: find nets where the pin ACTUALLY changed vs the firmware
    for d in diffs:
        signal = d["signal_name"]
        new_pin = d["new_pin"]
        if signal in baseline and baseline[signal] != new_pin:
            d["old_pin"] = baseline[signal]
            logger.info(f"Detected real pin change: {signal} moved from {baseline[signal]} -> {new_pin} (component: {d['component']})")
            return d

    logger.info(f"All {len(diffs)} parsed nets match the current firmware baseline. No firmware update required.")
    return None


def watch_netlists_directory(target_dir: str, on_diff_callback: Callable[[dict], None], poll_interval: float = 2.0):
    """Monitors a directory for Altium/KiCad exports and triggers callback when files change."""
    logger.info(f"Starting Altium/KiCad Netlist Watcher on directory '{target_dir}'...")
    last_mtimes = {}

    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    try:
        while True:
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                if os.path.isfile(file_path) and filename.lower().endswith((".xml", ".net", ".json", ".rpt")):
                    mtime = os.path.getmtime(file_path)
                    if file_path not in last_mtimes or mtime > last_mtimes[file_path]:
                        last_mtimes[file_path] = mtime
                        logger.info(f"Detected new/updated EDA export file: {filename}")
                        diff_data = process_netlist_file(file_path)
                        if diff_data:
                            on_diff_callback(diff_data)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("Stopped Netlist Watcher service.")
