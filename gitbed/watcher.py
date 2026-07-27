import logging
import os
import time
from typing import Callable, Optional

from gitbed.parsers import parse_altium_netlist, parse_kicad_netlist

logger = logging.getLogger(__name__)


def process_netlist_file(file_path: str) -> Optional[dict]:
    """Reads and parses an EDA netlist file (Altium XML/RPT or KiCad .net)."""
    if not os.path.exists(file_path):
        logger.error(f"Netlist file '{file_path}' not found.")
        return None

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lower_path = file_path.lower()
    if lower_path.endswith(".xml") or "Altium" in content or "<Netlist" in content or (lower_path.endswith(".net") and "(export" not in content):
        diffs = parse_altium_netlist(content)
        # Filter for demo signals, ignoring passive components (Resistors/Capacitors)
        demo_diffs = [d for d in diffs if d['signal_name'] in ['INA_SDA', 'ESC_EN', 'STATUS_LED'] and not d['component'].startswith(('R', 'C'))]
        if demo_diffs:
            logger.info(f"Parsed Altium netlist '{file_path}': found signal '{demo_diffs[0]['signal_name']}' -> '{demo_diffs[0]['new_pin']}'")
            return demo_diffs[0]
        else:
            logger.info(f"Parsed {len(diffs)} nets from Altium, but none match tracked firmware signals (e.g. INA_SDA, ESC_EN). No firmware update required.")
            return None
    elif lower_path.endswith(".net") and "(export" in content:
        diffs = parse_kicad_netlist(content)
        if diffs:
            logger.info(f"Parsed KiCad netlist '{file_path}': found signal '{diffs[0]['signal_name']}' -> '{diffs[0]['new_pin']}'")
            return diffs[0]

    logger.warning(f"No valid signal changes parsed from '{file_path}'")
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
