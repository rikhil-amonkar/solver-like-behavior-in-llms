"""Execute extracted Python code in isolated subprocess."""

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
    Execute code in isolated subprocess and return results.

    Args:
        code: Python code to execute
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
