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

    # Load current firmware pin assignments from GitHub
    baseline = _load_baseline_pins()
    if not baseline:
        logger.warning("No baseline firmware found on GitHub. Returning first parsed net.")
        return diffs[0] if diffs else None

    # Resolve auto-generated net names (e.g. NetR13_1) back to real signal names
    # by checking if any IC pin in the baseline has changed
    for d in diffs:
        signal = d["signal_name"]
        new_pin = d["new_pin"]

        # If the signal already has a proper name (not auto-generated), check directly
        if not signal.startswith("Net"):
            if signal in baseline and baseline[signal] != new_pin:
                d["old_pin"] = baseline[signal]
                logger.info(f"Detected pin change: {signal} moved from {baseline[signal]} -> {new_pin} (primary: {d['component']})")
                return d
        else:
            # Auto-generated net name: find which baseline signal this IC pin USED to belong to
            # by checking if any tracked signal now has a different pin
            for base_signal, base_pin in baseline.items():
                if base_pin != new_pin:
                    # Check: does this net connect to the same IC component type?
                    # This is a candidate — but we need more evidence
                    continue

            # Simply expose with the auto-generated name for now; the baseline diff below will catch it
            pass

    # Final pass: check if any baseline signal is MISSING entirely from the netlist
    # This means the net label detached — find the auto-generated net that took its place
    named_signals = {d["signal_name"] for d in diffs if not d["signal_name"].startswith("Net")}
    auto_nets = [d for d in diffs if d["signal_name"].startswith("Net")]

    missing_signals = [(sig, pin) for sig, pin in baseline.items() if sig not in named_signals]

    if missing_signals:
        logger.info(f"Baseline signals missing from netlist (label detached): {[s for s, _ in missing_signals]}")

    # Phase 1: Initialize signal_to_ic map from ALL named signals currently in the netlist
    # (e.g. INA_SCL is on U2, so INA bus signals belong to U2)
    signal_to_ic = {d["signal_name"]: d["component"] for d in diffs if not d["signal_name"].startswith("Net")}
    used_auto = set()

    for base_signal, base_pin in missing_signals:
        for i, d in enumerate(auto_nets):
            if i not in used_auto and d["new_pin"] == base_pin:
                used_auto.add(i)
                signal_to_ic[base_signal] = d["component"]
                logger.info(f"Label detached but pin unchanged: {base_signal} still on {base_pin} (auto-named as {d['signal_name']}, IC: {d['component']})")
                break

    # Phase 2: For missing signals that had NO same-pin match, find the auto-net with a DIFFERENT pin
    # Prefer auto-nets on the same IC component as the signal's known/inferred IC
    for base_signal, base_pin in missing_signals:
        # If this signal was matched to a same-pin auto-net in Phase 1, skip it
        if base_signal in signal_to_ic and any(d["new_pin"] == base_pin for i, d in enumerate(auto_nets) if i in used_auto):
            continue

        # Infer expected IC component for this signal (e.g. INA_SDA -> INA_SCL is on U2)
        expected_ic = None
        prefix = base_signal.rsplit("_", 1)[0]
        for other_sig, other_ic in signal_to_ic.items():
            if other_sig.startswith(prefix) and other_sig != base_signal:
                expected_ic = other_ic
                break

        best_match = None
        for i, d in enumerate(auto_nets):
            if i not in used_auto and d["new_pin"] != base_pin:
                if expected_ic and d["component"] == expected_ic:
                    best_match = (i, d)
                    break  # Exact IC match!
                elif best_match is None:
                    best_match = (i, d)

        if best_match:
            i, d = best_match
            used_auto.add(i)
            d["signal_name"] = base_signal
            d["old_pin"] = base_pin
            logger.info(f"Resolved detached net label: {base_signal} moved from {base_pin} -> {d['new_pin']} (primary: {d['component']})")
            return d

    logger.info(f"All net signals match current firmware baseline ({len(baseline)} tracked signals). No firmware update required.")
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
