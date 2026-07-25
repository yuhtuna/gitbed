# GitBed: Automated Hardware Netlist Sync & Firmware Patch Engine

GitBed is an automated DevOps pipeline designed for embedded systems engineering. It ingests hardware netlist specification diffs, generates appropriate C/C++ hardware abstraction layer patches using LLM capabilities, validates code correctness using local compiler checks, and automatically manages Git branching and Pull Request creation on GitHub.

---

## Architecture and System Flow

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
       +-------------------+
```

### Core Pipeline Components

1. **State Schema (`AgentState`)**
   Maintains system context across node executions, including `diff_data`, `original_code`, `updated_code`, `error_log`, attempt counts, and resulting PR URL.

2. **Patch Generation (`generate_patch`)**
   Invokes `gpt-4o` using structured system constraints to produce pure C++ header configurations (`pin_config.h`) derived from the hardware netlist diff.

3. **Compiler & Spec Verification (`verify_patch`)**
   Executes a multi-stage validation:
   - **Syntax Verification:** Compiles the patch headlessly using local `g++ -fsyntax-only` to ensure standard compliance.
   - **Specification Verification:** Checks that newly reassigned pin declarations from the netlist diff are explicitly present in the patch.

4. **Reflection Router (`route_verification`)**
   Evaluates error status. If syntax or specification errors are present and attempts are below the threshold of 3, control loops back to `generate_patch` with compiler diagnostics included in the LLM context.

5. **GitHub Pull Request Automation (`open_pr`)**
   Uses `PyGithub` to connect to the target repository, create an isolated feature branch (`hardware-sync-<id>`), commit updated header files, and submit a Pull Request.

---

## Repository Structure

```
gitbed/
├── gitbed/
│   ├── __init__.py      # Package initialization
│   ├── state.py         # AgentState schema definition
│   ├── utils.py         # Code formatting, GCC invocation, and GitHub content fetchers
│   ├── nodes.py         # Node implementations (generate_patch, verify_patch, open_pr)
│   └── graph.py         # StateGraph workflow assembly and routing logic
├── gitbed_engine.py     # Main application entry point and logging configuration
├── mock_diff.json       # Input hardware netlist diff specification
├── .gitignore           # Git ignore rules for Python artifacts
└── README.md            # System documentation
```

---

## Prerequisites

- **Python:** 3.10 or higher
- **C++ Compiler:** `g++` (GCC) or `clang` accessible in system `PATH`
- **Dependencies:** `pygithub`, `langchain-openai`, `langgraph`, `typing_extensions`

---

## Environment Configuration

Configure the following environment variables prior to running the engine:

| Variable Name | Description | Example |
| :--- | :--- | :--- |
| `GITHUB_TOKEN` | GitHub Personal Access Token with repository write permissions | `ghp_xxxxxxxxxxxx` |
| `OPENAI_API_KEY` | OpenAI API key for `gpt-4o` invocation | `sk-proj-xxxxxxxx` |
| `GITHUB_REPO` | Target GitHub repository (owner/name format) | `yuhtuna/gitbed` |

### Setting Environment Variables

#### On Linux / macOS:
```bash
export GITHUB_TOKEN="your_github_token"
export OPENAI_API_KEY="your_openai_api_key"
export GITHUB_REPO="owner/repository"
```

#### On Windows (PowerShell):
```powershell
$env:GITHUB_TOKEN="your_github_token"
$env:OPENAI_API_KEY="your_openai_api_key"
$env:GITHUB_REPO="owner/repository"
```

---

## Installation and Execution

1. **Install Dependencies**

   ```bash
   pip install pygithub langchain-openai langgraph typing-extensions
   ```

2. **Run the Engine**

   Execute the main entry script from the project root:

   ```bash
   python gitbed_engine.py
   ```

---

## Logging and Diagnostics

The engine outputs structured logs using Python's standard `logging` module.

Sample output format:

```text
00:42:10 [INFO] gitbed: Loaded netlist diff: STATUS_LED (PB6 -> PB7)
00:42:11 [INFO] gitbed: Fetched pin_config.h from GitHub repo 'yuhtuna/gitbed'
00:42:11 [INFO] gitbed: Starting GitBed agent pipeline
00:42:11 [INFO] gitbed.nodes: Generating C++ patch (attempt 1)
00:42:13 [INFO] gitbed.nodes: Verifying C++ patch with compiler and specification check
00:42:13 [INFO] gitbed.nodes: Verification passed successfully
00:42:13 [INFO] gitbed.graph: Routing to open_pr
00:42:13 [INFO] gitbed.nodes: Creating GitHub Pull Request
00:42:15 [INFO] gitbed.nodes: Pull Request opened: https://github.com/yuhtuna/gitbed/pull/12
00:42:15 [INFO] gitbed: Workflow completed successfully. PR URL: https://github.com/yuhtuna/gitbed/pull/12
```
