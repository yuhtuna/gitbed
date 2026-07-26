import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_kicad_netlist(netlist_content: str) -> List[Dict[str, Any]]:
    """Parses S-expression / KiCad netlist format to extract net signal assignments."""
    diffs = []
    # Match KiCad net definitions: (net (code 1) (name "STATUS_LED") (node (ref U1) (pin 7)))
    net_pattern = r'\(net\s+\(code\s+\d+\)\s+\(name\s+"([^"]+)"\)\s+.*?\(node\s+\(ref\s+(\w+)\)\s+\(pin\s+(\w+)\)\)'
    matches = re.findall(net_pattern, netlist_content, re.DOTALL)

    for signal_name, ref, pin in matches:
        if "NC" not in signal_name and "GND" not in signal_name and "VCC" not in signal_name:
            diffs.append({
                "component": ref,
                "signal_name": signal_name,
                "new_pin": f"P{pin}" if not pin.startswith("P") else pin,
                "change_type": "KICAD_NETLIST_SYNC",
                "description": f"Parsed KiCad net assignment for {signal_name} on {ref} pin {pin}",
            })

    logger.info(f"Parsed {len(diffs)} signal nets from KiCad netlist data")
    return diffs


def parse_altium_netlist(xml_content: str) -> List[Dict[str, Any]]:
    """Parses Altium XML / Netlist export format to extract net signal assignments."""
    diffs = []
    try:
        root = ET.fromstring(xml_content)
        for net in root.findall(".//Net"):
            net_name = net.get("Name") or net.findtext("Name", "")
            node = net.find(".//Node")
            if node is not None:
                ref = node.get("ComponentRef", "U1")
                pin = node.get("Pin", "1")
                if net_name and "GND" not in net_name and "VCC" not in net_name:
                    diffs.append({
                        "component": ref,
                        "signal_name": net_name,
                        "new_pin": f"P{pin}" if not pin.startswith("P") else pin,
                        "change_type": "ALTIUM_NETLIST_SYNC",
                        "description": f"Parsed Altium net assignment for {net_name} on {ref} pin {pin}",
                    })
    except Exception as exc:
        logger.warning(f"Altium XML parse fallback to regex: {exc}")
        # Regex fallback for Protel format: ( \n NetName \n Node1-Pin1 \n )
        protel_blocks = re.findall(r"\(\s*\n\s*([\w]+)\s*\n(.*?)\n\)", xml_content, re.DOTALL)
        for net_name, nodes_block in protel_blocks:
            nodes = re.findall(r"([\w]+)-([\w]+)", nodes_block)
            for ref, pin in nodes:
                if net_name and "GND" not in net_name and "VCC" not in net_name:
                    diffs.append({
                        "component": ref,
                        "signal_name": net_name,
                        "new_pin": f"P{pin}" if not pin.startswith("P") else pin,
                        "change_type": "ALTIUM_NETLIST_SYNC",
                        "description": f"Parsed Protel entry for {net_name}",
                    })

        # Regex fallback for Report text format
        matches = re.findall(r"Net\s+(\w+)\s+Node\s+(\w+)-(\w+)", xml_content)
        for net_name, ref, pin in matches:
            if net_name and "GND" not in net_name and "VCC" not in net_name:
                diffs.append({
                    "component": ref,
                    "signal_name": net_name,
                    "new_pin": f"P{pin}" if not pin.startswith("P") else pin,
                    "change_type": "ALTIUM_NETLIST_SYNC",
                    "description": f"Parsed Altium report entry for {net_name}",
                })

    logger.info(f"Parsed {len(diffs)} signal nets from Altium netlist data")
    return diffs
