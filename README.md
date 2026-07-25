# GitBed (Community Edition)

Automated hardware-to-software CI/CD agent.

GitBed listens for Altium/KiCad netlist changes and automatically generates verified C++ Pull Requests to keep firmware in sync with hardware.

---

[ 🔗 Insert your 90-second Loom Demo Video Link Here ]

---

## 🚀 Quickstart (Run Locally)

```bash
git clone https://github.com/yuhtuna/gitbed.git
cd gitbed

pip install -r requirements.txt

# Copy environment variables template and configure your keys
cp .env.example .env

python gitbed_engine.py
```

---

## 🏢 GitBed Enterprise

The Community Edition runs strictly locally. For Enterprise teams requiring Zero Data Retention (ZDR), SOC 2 compliance, and Hardware-in-the-Loop (HIL) server integrations, join the Alpha waitlist.

---

## System Architecture

The workflow is modeled as a stateful directed graph using LangGraph. It incorporates an automated reflection loop to catch compilation or specification errors and prompt the LLM for corrections before creating pull requests.

```
       +-------------------+
       |       START       |
       +---------+---------+
                 |
                 v
       +-------------------+
       |  generate_patch   | <-------+
       +---------+---------+         |
                 |                   | (Attempt < 3 & Error)
                 v                   |
       +-------------------+         |
       |   verify_patch    | --------+
       +---------+---------+
                 |
                 | (Verification Clean)
                 v
       +-------------------+
       |      open_pr      |
       +---------+---------+
                 |
                 v
       +-------------------+
       |        END        |
       +---------+---------+
```

### Core Pipeline Components

2. **Deterministic-First Patch Generation (`generate_patch` & `BridgeCache`)**
   Attempts zero-cost deterministic rule execution using cached bridge rules (`.gitbed_rules.json`). Only falls back to `gpt-4o-mini` synthesis on cache misses, caching new rules upon successful compilation.

3. **Compiler, Conflict & Spec Verification (`verify_patch` & `PinConflictChecker`)**
   Executes a multi-stage validation:
   - **Syntax Verification:** Compiles the patch headlessly using local `g++ -fsyntax-only` to ensure standard compliance.
   - **Specification Verification:** Checks that newly reassigned pin declarations from the netlist diff are explicitly present in the patch.
   - **Hardware Conflict Verification:** Cross-checks MCU peripheral multiplexing matrix to detect duplicate pin assignments or bus collisions (I2C/SPI/UART).

4. **Multi-File HAL & DeviceTree Sync (`hal_sync`)**
   Automatically synchronizes pin reassignments across:
   - `pin_config.h` (C/C++ Macro Header)
   - `boards/app.overlay` (Zephyr / Linux RTOS DeviceTree Overlay)
   - `src/gpio_driver.cpp` (GPIO Driver Initialization functions)

5. **Reflection Router (`route_verification`)**
   Evaluates error status. If syntax or conflict errors occur, loops back to `generate_patch` with compiler diagnostics included in the LLM context.

6. **GitHub Pull Request Automation (`open_pr`)**
   Uses `PyGithub` to connect to the target repository, create an isolated feature branch (`hardware-sync-<id>`), commit multi-file patch bundles, and submit a Pull Request.

---

## Repository Structure

```
gitbed/
├── .github/workflows/
│   └── gitbed-sync.yml  # GitHub Actions CI/CD workflow template
├── gitbed/
│   ├── __init__.py      # Package initialization
│   ├── bridge.py        # Self-Synthesizing Bridge Cache Engine
│   ├── conflict_checker.py # Hardware pin conflict & peripheral collision guard
│   ├── hal_sync.py      # Multi-file HAL & DeviceTree patch generator
│   ├── parsers.py       # KiCad and Altium EDA netlist diff parsers
│   ├── state.py         # AgentState schema definition
│   ├── utils.py         # Code formatting, GCC invocation, and GitHub content fetchers
│   ├── nodes.py         # Node implementations (generate_patch, verify_patch, open_pr)
│   └── graph.py         # StateGraph workflow assembly and routing logic
├── tests/               # 26 automated unit and integration tests
├── gitbed_engine.py     # Main application entry point and logging configuration
├── mock_diff.json       # Input hardware netlist diff specification
├── requirements.txt     # Python package dependencies
├── .gitignore           # Git ignore rules for Python artifacts and secrets
└── README.md            # System documentation
```

---

## Testing

Run the automated test suite using `pytest`:

```bash
pytest -v
```
