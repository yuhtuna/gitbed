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
    """Parses Altium XML / Netlist export format to extract net signal assignments and full hardware topology."""
    net_map: Dict[str, List[Dict[str, str]]] = {}

    # 1. XML Parsing
    try:
        root = ET.fromstring(xml_content)
        for net in root.findall(".//Net"):
            net_name = net.get("Name") or net.findtext("Name", "")
            if not net_name or "GND" in net_name or "VCC" in net_name:
                continue

            nodes = []
            for node in net.findall(".//Node"):
                ref = node.get("ComponentRef", "U1")
                pin = node.get("Pin", "1")
                nodes.append({"component": ref, "pin": pin})

            if nodes:
                net_map[net_name] = nodes
    except Exception as exc:
        logger.warning(f"Altium XML parse fallback to regex: {exc}")
        # 2. Regex fallback for Protel format: ( \n NetName \n Node1-Pin1 \n )
        protel_blocks = re.findall(r"\(\s*\n\s*([\w]+)\s*\n(.*?)\n\)", xml_content, re.DOTALL)
        for net_name, nodes_block in protel_blocks:
            if not net_name or "GND" in net_name or "VCC" in net_name:
                continue
            nodes = re.findall(r"([\w]+)-([\w]+)", nodes_block)
            if nodes:
                node_list = [{"component": ref, "pin": pin} for ref, pin in nodes]
                net_map.setdefault(net_name, []).extend(node_list)

    diffs = []
    for net_name, nodes in net_map.items():
        # Deduplicate nodes
        unique_nodes = []
        seen = set()
        for n in nodes:
            key = (n["component"], n["pin"])
            if key not in seen:
                seen.add(key)
                unique_nodes.append(n)

        # Select primary component: prefer IC/MCU ('U'/'IC'), then Connector ('CN'/'J'), then first
        ic_nodes = [n for n in unique_nodes if n["component"].startswith("U") or n["component"].startswith("IC")]
        cn_nodes = [n for n in unique_nodes if n["component"].startswith("CN") or n["component"].startswith("J")]

        primary = ic_nodes[0] if ic_nodes else (cn_nodes[0] if cn_nodes else unique_nodes[0])
        pin_str = primary["pin"]
        new_pin = f"P{pin_str}" if not pin_str.startswith("P") else pin_str

        diffs.append({
            "signal_name": net_name,
            "primary_component": primary["component"],
            "component": primary["component"],
            "new_pin": new_pin,
            "connected_nodes": unique_nodes,
            "change_type": "ALTIUM_NETLIST_SYNC",
            "description": f"Parsed Altium net '{net_name}' (Primary: {primary['component']} pin {primary['pin']}, total nodes: {len(unique_nodes)})",
        })

    logger.info(f"Parsed {len(diffs)} distinct net signals from Altium netlist data")
    return diffs
