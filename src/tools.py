import os
import subprocess
import sys
from typing import List, Dict, Any

class SwarmTools:
    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir)
        # Security check: Ensure we are operating within the sandbox (or at least the target dir)
        # For this TP, we assume target_dir IS the sandbox subfolder we are allowed to touch.
    
    def _is_safe_path(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.target_dir)

    def list_files(self) -> List[str]:
        """Lists all Python files in the target directory recursively."""
        py_files = []
        for root, dirs, files in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in ["refactored", "tests"]]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    py_files.append(full_path)
        return py_files

    def read_file(self, file_path: str) -> str:
        """Reads the content of a file."""
        if not self._is_safe_path(file_path):
            raise ValueError(
                f"Security Alert: Attempted to read outside target directory: {file_path}"
            )
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"

    def write_file(self, file_path: str, content: str) -> str:
        """Writes content to a file."""
        if not self._is_safe_path(file_path):
            raise ValueError(
                f"Security Alert: Attempted to write outside target directory: {file_path}"
            )
        
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing to {file_path}: {str(e)}"

    def run_pylint(self, file_path: str) -> str:
        """Runs pylint on a specific file and returns the output."""
        if not self._is_safe_path(file_path):
            return "Security Alert: invalid path"
            
        try:
            # We use a relaxed configuration or default. 
            # Capturing stdout and stderr.
            result = subprocess.run(
                [sys.executable, "-m", "pylint", file_path],
                capture_output=True,
                text=True,
                check=False,
            )
            # Pylint returns non-zero exit codes even for warnings, so we don't check returncode strictly for failure.
            return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        except Exception as e:
            return f"Error running pylint: {str(e)}"

    def run_pytest(self) -> Dict[str, Any]:
        """Runs pytest on the target directory and returns the result."""
        try:
            # Run pytest on the target directory
            result = subprocess.run(
                [sys.executable, "-m", "pytest", self.target_dir],
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "success": result.returncode == 0,
                "output": f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
                "return_code": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Error running pytest: {str(e)}",
                "return_code": -1
            }
