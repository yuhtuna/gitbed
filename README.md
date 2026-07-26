# GitBed

Automated hardware-to-software CI/CD agent for Enterprise.

GitBed listens for Altium Designer and KiCad netlist changes and automatically generates verified C++ Pull Requests to keep firmware tightly synchronized with hardware revisions.

---

## Quickstart

```bash
git clone https://github.com/yuhtuna/gitbed.git
cd gitbed

pip install -r requirements.txt

# Copy environment variables template and configure your keys
cp .env.example .env

# Run the standard pipeline on a mock hardware diff
python gitbed_engine.py
```

---

## Live Demo Workflow

To experience GitBed operating as a live background service mirroring an Enterprise environment:

1. Configure your target GitHub repository in `.env` (e.g., `GITHUB_REPO="your-org/firmware-repo"`).
2. Start the GitBed Live Watcher on a specific directory (e.g., your Altium outputs folder):
   ```bash
   python gitbed_engine.py --watch "C:/Users/Public/Documents/Altium/Sample - Kame_PDB/Project Outputs"
   ```
   *Note: Windows users can create a `.bat` script containing this command for 1-click startup.*
3. Open Altium Designer and modify a pin on your schematic.
4. Export the netlist (**Design -> Netlist For Project -> Protel / XML**) and save it into the watched directory.
5. GitBed will instantly detect the file, parse the structural netlist changes, compile the C++ firmware locally, check for hardware pin conflicts, and open a multi-file Pull Request on GitHub.

---

## EDA Integration Modes

GitBed connects with Altium Designer and KiCad through three seamless methods without requiring manual parsing:

### 1. Automated OutJob Export (Zero-Code)
1. In Altium Designer, open your project's Output Job File (`.OutJob`).
2. Add a **Netlist Outputs -> Export Netlist** generator targeting your local outputs folder.
3. Start GitBed in watcher mode (`--watch`). Every save and export automatically updates firmware.

### 2. Altium Native Script Hook
- Add `altium/GitBed_Export_Hook.py` to your Altium Designer Scripts folder.
- Execute `SyncWithGitBed` inside Altium Designer to trigger instantaneous netlist extraction and GitHub PR creation via a single click.

### 3. Cloud Webhooks
For Altium 365 cloud workspaces, configure Webhook notifications on `Project Release` or `Netlist Modified` events to trigger GitBed's CI/CD pipeline headlessly.

---

## Enterprise Architecture

The workflow is modeled as a stateful directed graph using LangGraph. It incorporates an automated reflection loop to catch compilation or specification errors and prompt the LLM for corrections before creating pull requests.

### Core Pipeline Components

1. **State Schema (AgentState)**
   Maintains system context across node executions, including structural diffs, C++ source code, compiler error logs, attempt counts, and the resulting Pull Request URL.

2. **Deterministic-First Patch Generation**
   Attempts zero-cost deterministic rule execution using a cached bridge engine (`.gitbed_rules.json`). Only falls back to state-of-the-art LLM synthesis on a cache miss, caching new rules upon successful compilation.

3. **Compiler, Conflict & Spec Verification**
   Executes a multi-stage validation:
   - **Syntax Verification:** Compiles the patch headlessly using a local C++ compiler (`g++ -fsyntax-only`) to ensure standard compliance.
   - **Specification Verification:** Checks that newly reassigned pin declarations are explicitly present in the patch.
   - **Hardware Conflict Verification:** Cross-checks the MCU peripheral multiplexing matrix to detect duplicate pin assignments or bus collisions (I2C/SPI/UART).

4. **Multi-File HAL & DeviceTree Sync**
   Automatically synchronizes pin reassignments across:
   - `pin_config.h` (C/C++ Macro Header)
   - `boards/app.overlay` (Zephyr / Linux RTOS DeviceTree Overlay)
   - `src/gpio_driver.cpp` (GPIO Driver Initialization logic)

5. **Reflection Router**
   Evaluates error status. If syntax or conflict errors occur, it loops back to the generation node with detailed compiler diagnostics included in the LLM context.

6. **GitHub Pull Request Automation**
   Connects to the target repository, creates an isolated feature branch, commits the multi-file patch bundle, and submits a Pull Request.

---

## Repository Structure

```text
gitbed/
├── .github/workflows/
│   └── gitbed-sync.yml       # GitHub Actions CI/CD workflow template
├── altium/
│   └── GitBed_Export_Hook.py # Altium Designer native script hook
├── gitbed/
│   ├── bridge.py             # Self-Synthesizing Bridge Cache Engine
│   ├── conflict_checker.py   # Hardware pin conflict guard
│   ├── hal_sync.py           # Multi-file HAL patch generator
│   ├── parsers.py            # KiCad and Altium EDA netlist parsers
│   ├── state.py              # AgentState schema definition
│   ├── utils.py              # Compilation and GitHub integrations
│   ├── nodes.py              # Agent Node implementations
│   ├── watcher.py            # EDA live directory watcher
│   └── graph.py              # StateGraph assembly and routing
├── tests/                    # Automated unit and integration test suite
├── gitbed_engine.py          # Main application entry point
└── LICENSE                   # AGPL-3.0 License
```

---

## Testing

Run the automated test suite using pytest:

```bash
pytest -v
```

## License

This software is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). See the `LICENSE` file for full text.
