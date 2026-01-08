from typing import Dict, Any
import os
import re
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.utils.logger import log_experiment, ActionType
from src.state import SwarmState
from src.tools import SwarmTools

# Load environment variables
load_dotenv()

class SwarmAgents:
    def __init__(self, tools: SwarmTools, model_name: str = "llama-3.1-8b-instant"):
        self.tools = tools
        self.model_name = model_name
        self.llm = ChatGroq(model=self.model_name, temperature=0.1, max_retries=0)
    def _safe_llm_invoke(self, prompt: str, agent_name: str, action: ActionType) -> Dict[str, Any]:
        try:
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", "")
            log_experiment(
                agent_name=agent_name,
                model_used=self.model_name,
                action=action,
                details={"input_prompt": prompt, "output_response": content},
                status="SUCCESS",
            )
            return {"content": content, "failed": False}
        except Exception as e:
            log_experiment(
                agent_name=agent_name,
                model_used=self.model_name,
                action=action,
                details={"input_prompt": prompt, "output_response": str(e)},
                status="FAILURE",
            )
            return {"content": str(e), "failed": True}

    def auditor_node(self, state: SwarmState) -> Dict[str, Any]:
        """
        The Auditor Agent: Analyzes the code and produces a refactoring plan.
        """
        current_file = state["current_file_path"]
        print(f"🕵️ Auditor analyzing: {current_file}")
        code_content = self.tools.read_file(current_file)
        pylint_output = self.tools.run_pylint(current_file)
        prompt = f"""
You are The Auditor, an expert Python code analyst.
Your goal is to analyze the following Python file and the pylint report to create a detailed refactoring plan.
You must identify bugs, security issues, bad practices (PEP 8), and missing documentation.
You must also check if there are corresponding tests. If not, include "Create Unit Tests" in the plan.

File Name: {current_file}

Code Content:
```python
{code_content}
```

Pylint Report:
{pylint_output}

Provide a clear, step-by-step Refactoring Plan.
"""
        if state.get("disable_llm", False):
            plan = (
                "LLM disabled. Apply pylint recommendations, add docstrings/tests.\n"
                f"{pylint_output}"
            )
            log_experiment(
                agent_name="Auditor",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={"input_prompt": prompt, "output_response": plan},
                status="DISABLED",
            )
            return {
                "refactoring_plan": plan,
                "current_file_content": code_content,
                "pylint_report": pylint_output,
                "status": "LLM_DISABLED",
            }
        time.sleep(state.get("cooldown_seconds", 0))
        _res = self._safe_llm_invoke(
            prompt,
            "Auditor",
            ActionType.ANALYSIS,
        )
        if _res["failed"]:
            _fallback = (
                "LLM unavailable. Apply pylint recommendations and add "
                "docstrings/tests.\n"
                f"{pylint_output}"
            )
            return {
                "refactoring_plan": _fallback,
                "current_file_content": code_content,
                "pylint_report": pylint_output,
                "status": "LLM_FAILURE",
            }
        plan = _res["content"]
        return {"refactoring_plan": plan, "current_file_content": code_content, "pylint_report": pylint_output}

    def fixer_node(self, state: SwarmState) -> Dict[str, Any]:
        """
        The Fixer Agent: Applies the refactoring plan.
        """
        current_file = state["current_file_path"]
        plan = state["refactoring_plan"]
        code_content = state["current_file_content"]
        test_results = state.get("test_results", {})
        
        print(f"🔧 Fixer working on: {current_file}")
        test_feedback = ""
        if test_results and not test_results.get("success", True):
            test_feedback = f"\nPrevious Test Failures:\n{test_results.get('output', '')}\nFix these errors."

        prompt = f"""
You are The Fixer, an expert Python developer.
You have a Refactoring Plan and the original code.
Your task is to rewrite the code to implement the plan and fix any issues.
If the plan asks for tests, you should generate a new test file or append tests (but prefer keeping the original file clean and valid).
However, for this task, if you are fixing a module, return the FULL CORRECTED CONTENT of the module.

If the plan implies creating a SEPARATE test file (e.g. test_file.py), you should mention it, but for now, provide the content for: {current_file}.
(If you need to create a new file, please combine it or handle it intelligently, but the system currently expects the content for {current_file}).

Refactoring Plan:
{plan}

{test_feedback}

Original Code:
```python
{code_content}
```

Output ONLY the full Python code for {current_file}. 
Wrap the code in ```python ... ``` blocks.
"""
        if state.get("output_mode", "overwrite") == "copy":
            prompt += """
Additionally, output ONLY the corrected function(s) that changed compared to the original.
Do not include any unchanged functions, imports, or boilerplate.
Wrap only the corrected function block(s) in a single ```python``` block.
Do not add module docstrings or new functions. Do not rename functions.
"""
        if state.get("disable_llm", False):
            log_experiment(
                agent_name="Fixer",
                model_used=self.model_name,
                action=ActionType.FIX,
                details={"input_prompt": prompt, "output_response": "LLM disabled"},
                status="DISABLED",
            )
            return {
                "current_file_content": code_content,
                "pylint_report": state.get("pylint_report", ""),
                "status": "LLM_DISABLED",
            }
        if state.get("status") == "LLM_FAILURE":
            return {"current_file_content": code_content, "pylint_report": state.get("pylint_report", "")}
        time.sleep(state.get("cooldown_seconds", 0))
        _res = self._safe_llm_invoke(
            prompt,
            "Fixer",
            ActionType.FIX,
        )
        if _res["failed"]:
            return {
                "current_file_content": code_content,
                "pylint_report": state.get("pylint_report", ""),
                "status": "LLM_FAILURE",
            }
        response_content = _res["content"]
        # Extract code from markdown blocks
        code_match = re.search(r"```python\n(.*?)```", response_content, re.DOTALL)
        if code_match:
            new_code = code_match.group(1)
        else:
            # Fallback if no blocks (risky but possible)
            new_code = response_content

        mode = state.get("output_mode", "overwrite")
        if mode == "copy":
            rel = os.path.relpath(current_file, state["target_dir"])
            dest_root = os.path.join(state["target_dir"], state.get("output_dir", "refactored"))
            dest_path = os.path.join(dest_root, rel)
            def _func_blocks(src: str):
                pat = re.compile(r"^def\s+(\w+)\s*\([^)]*\):[\s\S]*?(?=^def\s+\w+\s*\(|\Z)", re.MULTILINE)
                return {m.group(1): m.group(0).strip() for m in pat.finditer(src)}
            orig_map = _func_blocks(code_content)
            new_map = _func_blocks(new_code)
            def _norm(s: str) -> str:
                return re.sub(r"\s+", "", s)
            changed_blocks = []
            for name, block in new_map.items():
                if name in orig_map and _norm(block) != _norm(orig_map[name]):
                    changed_blocks.append(block.strip())
            content_to_write = "\n\n".join(changed_blocks)
            if not content_to_write:
                inter = [new_map[n].strip() for n in new_map.keys() if n in orig_map]
                if len(inter) == 1:
                    content_to_write = inter[0]
                elif len(inter) > 1:
                    content_to_write = inter[0]
                else:
                    any_block = next(iter(new_map.values()), "").strip()
                    content_to_write = any_block
            self.tools.write_file(dest_path, content_to_write)
            updated_pylint = self.tools.run_pylint(dest_path)
            before_score = self._extract_score(state.get("pylint_report", ""))
            after_score = self._extract_score(updated_pylint)
            entry = {
                "original_path": current_file,
                "dest_path": dest_path,
                "mode": "copy",
                "before_score": before_score,
                "after_score": after_score,
                "status": "UPDATED"
            }
            return {"current_file_content": new_code, "pylint_report": updated_pylint, "results": state.get("results", []) + [entry]}
        else:
            self.tools.write_file(current_file, new_code)
            updated_pylint = self.tools.run_pylint(current_file)
            before_score = self._extract_score(state.get("pylint_report", ""))
            after_score = self._extract_score(updated_pylint)
            entry = {
                "original_path": current_file,
                "dest_path": current_file,
                "mode": "overwrite",
                "before_score": before_score,
                "after_score": after_score,
                "status": "UPDATED"
            }
            return {"current_file_content": new_code, "pylint_report": updated_pylint, "results": state.get("results", []) + [entry]}

    def judge_node(self, state: SwarmState) -> Dict[str, Any]:
        """
        The Judge Agent: Runs tests and decides next step.
        """
        print("⚖️ Judge running tests...")
        # Run pytest
        results = self.tools.run_pytest()

        success = results["success"]
        iteration = state["iteration_count"]
        # In copy mode, we consider the run successful for reporting purposes,
        # since originals are intentionally preserved and fragments are written separately.
        if state.get("output_mode") == "copy":
            success = True

        # Logic: If fail and iterations < max, return failure (triggers loop).
        # We assume the graph handles the conditional edge.

        # LOGGING
        # Since Judge runs tools, maybe strictly speaking it's ANALYSIS or DEBUG?
        # If it analyzes the output to make a decision.
        # Let's log it as DEBUG if it fails, or ANALYSIS if it passes.

        action_type = ActionType.ANALYSIS if success else ActionType.DEBUG

        log_experiment(
            agent_name="Judge",
            model_used="system-tool",
            action=action_type,
            details={
                "input_prompt": "Run Pytest",
                "output_response": results["output"],
                "success": success
            },
            status="SUCCESS" if success else "FAILURE"
        )
        results["success"] = success
        return {"test_results": results, "iteration_count": iteration + 1}

    def _extract_score(self, text: str) -> float:
        m = re.search(r"rated at\s+([0-9.]+)\/10", text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return -1.0
        return -1.0
