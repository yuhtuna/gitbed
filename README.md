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

1. **State Schema (`AgentState`)**
   Maintains system context across node executions, including `diff_data`, `original_code`, `updated_code`, `error_log`, attempt counts, and resulting PR URL.

2. **Deterministic-First Patch Generation (`generate_patch` & `BridgeCache`)**
   Attempts zero-cost deterministic rule execution using cached bridge rules (`.gitbed_rules.json`). Only falls back to `gpt-4o-mini` synthesis on cache misses, caching new rules upon successful compilation.

3. **Compiler & Spec Verification (`verify_patch`)**
   Executes a multi-stage validation:
   - **Syntax Verification:** Compiles the patch headlessly using local `g++ -fsyntax-only` to ensure standard compliance.
   - **Specification Verification:** Checks that newly reassigned pin declarations from the netlist diff are explicitly present in the patch.

4. **Reflection Router (`route_verification`)**
   Evaluates error status. If syntax or specification errors are present and attempts are below 3, control loops back to `generate_patch` with compiler diagnostics included in the LLM context.

5. **GitHub Pull Request Automation (`open_pr`)**
   Uses `PyGithub` to connect to the target repository, create an isolated feature branch (`hardware-sync-<id>`), commit updated header files, and submit a Pull Request.

---

## Repository Structure

```
gitbed/
├── gitbed/
│   ├── __init__.py      # Package initialization
│   ├── bridge.py        # Self-Synthesizing Bridge Cache Engine
│   ├── state.py         # AgentState schema definition
│   ├── utils.py         # Code formatting, GCC invocation, and GitHub content fetchers
│   ├── nodes.py         # Node implementations (generate_patch, verify_patch, open_pr)
│   └── graph.py         # StateGraph workflow assembly and routing logic
├── tests/               # Unit and integration test suite
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
