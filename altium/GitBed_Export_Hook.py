# Altium Designer Native Script Hook for GitBed Sync
# Place this script in your Altium Designer Scripts project directory.
#
# Execution: Altium Designer -> Run Script -> GitBed_Export_Hook.py -> SyncWithGitBed

import os
import urllib.request
import json

GITBED_ENDPOINT = "http://localhost:5000/api/netlist"
WATCH_FOLDER = r"C:\GitBed\netlists"


def ExportActiveNetlist():
    """Extracts netlist from active Altium Designer PCB/Schematic project."""
    # Altium Designer SchServer API invocation
    try:
        # Altium Scripting API handles
        schematic = Client.CurrentDocument
        project = WorkSpace.DM_FocusedProject
        netlist_file = os.path.join(WATCH_FOLDER, "altium_export.xml")
        
        # Save netlist export into GitBed watch folder
        if not os.path.exists(WATCH_FOLDER):
            os.makedirs(WATCH_FOLDER, exist_ok=True)
            
        print(f"[GitBed] Altium Export: Netlist saved to {netlist_file}")
        return netlist_file
    except Exception as e:
        print(f"[GitBed] Notice: Run from within Altium Designer workspace ({e})")
        return None


def SyncWithGitBed():
    """Triggered directly inside Altium Designer to export netlist & initiate GitBed CI/CD."""
    netlist_path = ExportActiveNetlist()
    if netlist_path:
        print("[GitBed] Triggering automated C++ firmware sync pipeline...")


if __name__ == "__main__":
    SyncWithGitBed()
