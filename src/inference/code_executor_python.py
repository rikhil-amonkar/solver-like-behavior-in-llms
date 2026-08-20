"""
Execute extracted code in isolated subprocess.

This module provides the main routing logic and Python standard library executor.

Language-Specific Executors:
- Python standard library: run_code() [this file]
- Z3-Python: run_z3_code() [code_executor_z3.py]
- PDDL: run_pddl_code() [code_executor_pddl.py]

Use execute_code_by_language() for automatic routing based on task.
"""

import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from general.parsing_utils import parse_code_output


def run_code(code: str, timeout_sec: float = 30.0) -> dict:
    """
    Execute Python standard library code in isolated subprocess.

    This executor is for Python code that uses ONLY the standard library.
    No external packages (numpy, pandas, etc.) are allowed.

    For code requiring external packages, use:
    - run_z3_code() for Z3-Python code
    - run_pddl_code() for PDDL code

    Args:
        code: Python standard library code to execute
        timeout_sec: Timeout in seconds

    Returns:
        Dict with keys:
            - ran: bool (whether execution was attempted)
            - exit_code: int or None
            - stdout: str
            - stderr: str
            - timed_out: bool
            - timeout_sec: float
            - error: Optional[str]
            - parsed_output: Any (parsed from stdout)
    """
    if not code or not code.strip():
        return {
            "ran": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "timeout_sec": timeout_sec,
            "error": "no code to execute",
            "parsed_output": None,
        }

    # Create temporary directory for code execution
    with tempfile.TemporaryDirectory(prefix="code_exec_") as tmpdir:
        script_path = Path(tmpdir) / "solution.py"
        script_path.write_text(code, encoding="utf-8")

        try:
            # Run code in subprocess
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,  # Don't raise on non-zero exit
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode
            timed_out = False
            error = None if exit_code == 0 else f"exit code {exit_code}"

        except subprocess.TimeoutExpired as e:
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            exit_code = None
            timed_out = True
            error = f"timeout after {timeout_sec}s"

        except Exception as e:
            stdout = ""
            stderr = str(e)
            exit_code = None
            timed_out = False
            error = f"execution error: {str(e)}"

    # Parse output
    parsed_output, parse_error = parse_code_output(stdout)

    return {
        "ran": True,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "timeout_sec": timeout_sec,
        "error": error,
        "parsed_output": parsed_output,
    }


def get_language_from_task(task: str) -> str:
    """
    Determine programming language/solver type from task name.

    Args:
        task: Task name (calendar, meeting, zebralogic, blocksworld)

    Returns:
        Language identifier ('python', 'z3', 'pddl')
    """
    task_to_language = {
        "calendar": "python",
        "meeting": "python",
        "trip": "python",
        "zebralogic": "z3",
        "blocksworld": "pddl",
    }

    return task_to_language.get(task, "python")  # Default to python


def execute_code_by_language(code: str, language: str, timeout_sec: float = 30.0, **kwargs) -> dict:
    """
    Route code execution to appropriate language-specific executor.

    Args:
        code: Code to execute
        language: Language type ('python', 'z3', 'pddl')
        timeout_sec: Execution timeout
        **kwargs: Additional language-specific parameters
                 For PDDL: planner_path

    Returns:
        Execution result dict (format varies by language)
    """
    if language == "python":
        return run_code(code, timeout_sec=timeout_sec)

    elif language == "z3":
        from inference.code_executor_z3 import run_z3_code
        return run_z3_code(code, timeout_sec=timeout_sec)

    elif language == "pddl":
        from inference.code_executor_pddl import run_pddl_code
        planner_path = kwargs.get("planner_path")
        return run_pddl_code(code, timeout_sec=timeout_sec, planner_path=planner_path)

    else:
        return {
            "ran": False,
            "error": f"unknown language: {language}",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "timed_out": False,
            "timeout_sec": timeout_sec,
            "parsed_output": None,
        }
