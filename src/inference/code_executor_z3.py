"""Execute Z3-Python code in isolated subprocess with z3-solver support."""

import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from general.parsing_utils import parse_code_output, parse_zebralogic_grid_output


def run_z3_code(code: str, timeout_sec: float = 30.0, problem_data: dict = None) -> dict:
    """
    Execute Z3-Python code in isolated subprocess.

    This is similar to run_code() but allows Z3 imports.
    The code is expected to use `from z3 import *` and solve
    constraint satisfaction problems using Z3 solver.

    Args:
        code: Z3-Python code to execute
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
            - z3_used: bool (whether z3 import was detected)
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
            "z3_used": False,
        }

    # Check if code uses z3
    z3_used = "from z3 import" in code or "import z3" in code

    # Create temporary directory for code execution
    with tempfile.TemporaryDirectory(prefix="z3_exec_") as tmpdir:
        script_path = Path(tmpdir) / "solution_z3.py"
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

            # Enhanced error detection for Z3
            if exit_code != 0:
                if "ModuleNotFoundError" in stderr and "z3" in stderr:
                    error = "z3-solver not installed (pip install z3-solver)"
                else:
                    error = f"exit code {exit_code}"
            else:
                error = None

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

    # Parse output (Z3 solutions are usually printed as text/tables)
    # For zebralogic, use specialized parser
    if problem_data and "headers" in problem_data:
        headers = problem_data.get("headers", [])
        parsed_output, parse_error = parse_zebralogic_grid_output(stdout, headers)
    else:
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
        "z3_used": z3_used,
    }


def check_z3_available() -> tuple[bool, Optional[str]]:
    """
    Check if z3-solver is available in the environment.

    Returns:
        (is_available, error_message)
    """
    try:
        import z3
        return True, None
    except ImportError as e:
        return False, str(e)
