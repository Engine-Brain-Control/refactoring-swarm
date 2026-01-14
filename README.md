Refactoring Swarm Template
Overview

• Automates Python refactoring using a coordinated swarm of agents.
• Audits with Pylint, generates a refactoring plan, applies fixes, and validates via Pytest.
• Operates file-by-file with iteration control and optional LLM disable mode.
• Supports in-place overwrites or writing only changed functions to a mirrored output tree.

Key Capabilities

• Structured audit → fix → judge loop that converges on improved code.
• Pylint score tracking before/after changes for measurable progress.
• Safe file operations restricted to the selected target directory.
• Detailed JSON experiment logs capturing prompts, outputs, actions, and statuses.

Architecture
• Orchestrator builds a StateGraph that routes files through agents.
• Auditor reads file content and Pylint output to produce a refactoring plan.
• Fixer rewrites code by following the plan; copy mode writes only changed function blocks.
• Judge runs Pytest and decides whether to retry fixes or advance.
• State schema defines shared fields and execution context.

Requirements

• Python 3.10 or 3.11.
• Network access for LLMs if not using --disable_llm.
• A project with Python files and Pytest tests in the target directory.

Installation

pip install -r requirements.txt
python check_setup.py

• Dependencies: langgraph, langchain, langchain-groq, pylint, pytest, python-dotenv, pandas, colorama,
reportlab.

Configuration

Create a .env file with provider keys. For Groq:
GROQ_API_KEY=your_groq_api_key
The sanity check looks for GOOGLE_API_KEY by default; adjust according to the model used.
Usage
python main.py --target_dir path/to/your/python/project
python main.py --target_dir path/to/project --output_mode copy --output_dir refactored
python main.py --target_dir path/to/project --disable_llm
python main.py --target_dir path/to/project --max_files 10

CLI Options

• --target_dir: Directory containing Python files (required).
• --cooldown: Delay between agent steps (seconds); default 0.
• --disable_llm: Use deterministic Pylint guidance only.
• --output_mode: overwrite or copy; default overwrite.
• --output_dir: Destination folder used with copy mode; default refactored.
• --model: LLM model name; default llama-3.1-8b-instant.
• --max_files: Process only the first N files; default 0.

Workflow

• Manager selects the next file and enters the audit → fix → judge loop.
• Auditor generates a plan informed by Pylint results and missing tests.
• Fixer applies refactors; in copy mode, only modified function blocks are written.
• Judge runs Pytest and either retries fixes or advances to the next file.
• Iterations stop when tests pass or the iteration limit is reached.

Output Modes

• Overwrite: Replaces the original file content with corrected code.
• Copy: Writes changed function blocks to target_dir/output_dir while originals remain untouched.

Logging and Results

• Logs appended to logs/experiment_data.json with agent name, model, action, prompt, response, status,
timestamp.
• Final run prints a summary of corrections and Pylint score changes.

Project Structure

• src/: agents.py, graph.py, tools.py, state.py, utils/logger.py.
• main.py: CLI entry point and initial state wiring.
• logs/: Experiment logs.
• docs/: Course and setup PDFs.

Development and Testing

python -m pylint path/to/file.py
pytest path/to/your/python/project
The framework executes Pytest automatically during the Judge phase; failures trigger retries until the iteration
limit.

Troubleshooting

• No Python files found: Confirm target_dir exists and contains .py files.
• Missing API key: Set GROQ_API_KEY or the appropriate provider key.
• Pylint import errors: Ensure target project dependencies are installed or set PYTHONPATH.
• Persistent test failures: Inspect Judge output; fix or add tests as needed.
• LLM errors or rate limits: Use --disable_llm to proceed deterministically.

Extensibility

• Add agents or modify routing in the state graph.
• Customize prompts and heuristics in Auditor/Fixer.
• Extend tools for custom linters or formatters.

Security and Privacy

• File operations are restricted to the selected target_dir by path checks.
• Do not commit secrets; load keys from .env via python-dotenv.
• Logs include prompts and responses; avoid sensitive content in code or environment.

Attribution

• Built with LangGraph and LangChain.
• Uses Groq LLMs by default; configurable via the --model flag.
