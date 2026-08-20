"""
Code execution router for multi-language support.

This module provides the main routing logic to dispatch code execution
to language-specific executors based on task type.

Language-Specific Executors:
- Python standard library: code_executor_python.py
- Z3-Python: code_executor_z3.py
- PDDL: code_executor_pddl.py

Usage:
    from inference.code_executor import execute_code_by_language

    result = execute_code_by_language(code, language="z3")
"""

from typing import Optional


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

    This is the main entry point for code execution in the pipeline.
    It automatically routes to the correct executor based on language.

    Args:
        code: Code to execute
        language: Language type ('python', 'z3', 'pddl')
        timeout_sec: Execution timeout
        **kwargs: Additional language-specific parameters
                 For PDDL: planner_path

    Returns:
        Execution result dict (format varies by language)

    Examples:
        >>> # Python code
        >>> result = execute_code_by_language("print('hello')", "python")

        >>> # Z3 code
        >>> z3_code = "from z3 import *\\nprint(Int('x'))"
        >>> result = execute_code_by_language(z3_code, "z3")

        >>> # PDDL code
        >>> result = execute_code_by_language(pddl_code, "pddl")
    """
    if language == "python":
        from .code_executor_python import run_code
        return run_code(code, timeout_sec=timeout_sec)

    elif language == "z3":
        from .code_executor_z3 import run_z3_code
        return run_z3_code(code, timeout_sec=timeout_sec)

    elif language == "pddl":
        from .code_executor_pddl import run_pddl_code
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


# Re-export for backward compatibility
# This allows existing code to continue using: from inference.code_executor import run_code
def run_code(code: str, timeout_sec: float = 30.0) -> dict:
    """
    Execute Python standard library code (backward compatibility wrapper).

    Delegates to code_executor_python.run_code().

    For new code, prefer using execute_code_by_language() instead.
    """
    from .code_executor_python import run_code as _run_code
    return _run_code(code, timeout_sec=timeout_sec)
