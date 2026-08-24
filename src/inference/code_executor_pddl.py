"""Execute and validate PDDL code for planning tasks."""

import subprocess
import tempfile
import re
import json
from pathlib import Path
from typing import Optional, Tuple


def extract_pddl_from_json(code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract domain and problem PDDL from JSON output.

    Expected format:
    {
      "domain_pddl": "(define (domain blocksworld) ...)",
      "problem_pddl": "(define (problem ...) ...)"
    }

    Args:
        code: Model output containing JSON with PDDL code

    Returns:
        (domain_pddl, problem_pddl, error_message)
    """
    # Try to extract JSON from code blocks first
    json_block_pattern = r'```(?:json)?\s*\n(.*?)```'
    json_blocks = re.findall(json_block_pattern, code, re.DOTALL | re.IGNORECASE)

    json_text = json_blocks[0] if json_blocks else code

    # Try parsing as JSON
    try:
        parsed = json.loads(json_text.strip())

        if not isinstance(parsed, dict):
            return None, None, "JSON output is not an object/dict"

        domain_pddl = parsed.get("domain_pddl")
        problem_pddl = parsed.get("problem_pddl")

        if not domain_pddl:
            return None, None, "JSON missing 'domain_pddl' key"
        if not problem_pddl:
            return None, None, "JSON missing 'problem_pddl' key"

        return domain_pddl, problem_pddl, None

    except json.JSONDecodeError as e:
        return None, None, f"Failed to parse JSON: {str(e)}"


def extract_pddl_sections(code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract domain and problem PDDL from model output.

    First tries JSON format (preferred), then falls back to raw PDDL extraction.

    Models may output PDDL in various formats:
    - JSON: {"domain_pddl": "...", "problem_pddl": "..."}
    - Inside ```pddl or ``` code blocks
    - As raw S-expressions

    Args:
        code: Model output containing PDDL code

    Returns:
        (domain_pddl, problem_pddl, error_message)
    """
    # Try JSON format first (new preferred format)
    if "{" in code and "domain_pddl" in code:
        domain, problem, error = extract_pddl_from_json(code)
        if domain and problem:
            return domain, problem, None
        # If JSON extraction failed but looks like JSON, return the error
        if "JSON" in str(error) or "{" in code[:100]:
            return None, None, error

    # Fallback: Try to extract from code blocks
    code_block_pattern = r'```(?:pddl)?\s*\n(.*?)```'
    code_blocks = re.findall(code_block_pattern, code, re.DOTALL)

    # If no code blocks, treat entire code as PDDL
    if not code_blocks:
        pddl_text = code
    else:
        # Concatenate all code blocks
        pddl_text = "\n\n".join(code_blocks)

    # Extract domain and problem definitions
    domain_pattern = r'\(define\s+\(domain\s+[\w-]+\).*?\n\)'
    problem_pattern = r'\(define\s+\(problem\s+[\w-]+\).*?\n\)'

    domain_matches = list(re.finditer(domain_pattern, pddl_text, re.DOTALL))
    problem_matches = list(re.finditer(problem_pattern, pddl_text, re.DOTALL))

    if not domain_matches:
        return None, None, "No domain definition found (should start with '(define (domain ...)')"

    if not problem_matches:
        return None, None, "No problem definition found (should start with '(define (problem ...)')"

    # Use the first occurrence of each
    domain_pddl = domain_matches[0].group(0)
    problem_pddl = problem_matches[0].group(0)

    return domain_pddl, problem_pddl, None


def validate_pddl_syntax(domain_pddl: str, problem_pddl: str) -> Tuple[bool, Optional[str]]:
    """
    Validate PDDL syntax (basic checks).

    This performs simple structural validation, not full semantic validation.

    Args:
        domain_pddl: Domain PDDL code
        problem_pddl: Problem PDDL code

    Returns:
        (is_valid, error_message)
    """
    # Check balanced parentheses
    def check_balanced(text):
        count = 0
        for char in text:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
            if count < 0:
                return False
        return count == 0

    if not check_balanced(domain_pddl):
        return False, "Domain has unbalanced parentheses"

    if not check_balanced(problem_pddl):
        return False, "Problem has unbalanced parentheses"

    # Check required sections in domain
    required_domain_sections = [':predicates', ':action']
    for section in required_domain_sections:
        if section not in domain_pddl:
            return False, f"Domain missing required section: {section}"

    # Check required sections in problem
    required_problem_sections = [':domain', ':objects', ':init', ':goal']
    for section in required_problem_sections:
        if section not in problem_pddl:
            return False, f"Problem missing required section: {section}"

    return True, None


def run_val_validator(
    domain_pddl: str,
    problem_pddl: str,
    plan_text: str,
    val_path: Optional[str] = None,
    timeout_sec: float = 10.0
) -> Tuple[bool, str, str]:
    """
    Run VAL validator on domain, problem, and plan.

    Args:
        domain_pddl: Domain PDDL definition
        problem_pddl: Problem PDDL definition
        plan_text: Plan as text (one action per line or Fast Downward format)
        val_path: Path to VAL Validate binary (defaults to repos/VAL/build/bin/Validate relative to project root)
        timeout_sec: Timeout for validation

    Returns:
        (is_valid, stdout, stderr)
    """
    # Default to project-relative path if not specified
    if val_path is None:
        # Get project root (4 levels up from this file: src/inference/code_executor_pddl.py)
        project_root = Path(__file__).parent.parent.parent
        val_path = str(project_root / "repos" / "VAL" / "build" / "bin" / "Validate")

    with tempfile.TemporaryDirectory(prefix="val_validation_") as tmpdir:
        domain_file = Path(tmpdir) / "domain.pddl"
        problem_file = Path(tmpdir) / "problem.pddl"
        plan_file = Path(tmpdir) / "plan.txt"

        domain_file.write_text(domain_pddl, encoding="utf-8")
        problem_file.write_text(problem_pddl, encoding="utf-8")
        plan_file.write_text(plan_text, encoding="utf-8")

        try:
            result = subprocess.run(
                [val_path, str(domain_file), str(problem_file), str(plan_file)],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            # VAL outputs "Plan valid" when plan is valid
            is_valid = exit_code == 0 and ("Plan valid" in stdout or "plan valid" in stdout.lower())

            return is_valid, stdout, stderr

        except subprocess.TimeoutExpired:
            return False, "", f"VAL validation timeout after {timeout_sec}s"
        except FileNotFoundError:
            return False, "", f"VAL not found at: {val_path}"
        except Exception as e:
            return False, "", f"VAL execution error: {str(e)}"


def run_fast_downward_planner(
    domain_pddl: str,
    problem_pddl: str,
    timeout_sec: float = 60.0
) -> Tuple[Optional[str], str, str, bool]:
    """
    Run Fast Downward planner on domain and problem.

    This uses a simple LAMA-first configuration for quick planning.

    Args:
        domain_pddl: Domain PDDL definition
        problem_pddl: Problem PDDL definition
        timeout_sec: Timeout for planning

    Returns:
        (plan_text, stdout, stderr, plan_found)
    """
    with tempfile.TemporaryDirectory(prefix="fd_planner_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        domain_file = tmpdir_path / "domain.pddl"
        problem_file = tmpdir_path / "problem.pddl"
        sas_file = tmpdir_path / "output.sas"

        domain_file.write_text(domain_pddl, encoding="utf-8")
        problem_file.write_text(problem_pddl, encoding="utf-8")

        try:
            # Fast Downward requires two steps:
            # 1. Translate PDDL to SAS+ (using translate/translate.py)
            # 2. Search for plan (using downward binary)

            # We'll use the simple approach: call fast-downward.py wrapper
            # If not available, we can use pyperplan as fallback

            # Try pyperplan first (pure Python, easier to install)
            try:
                result = subprocess.run(
                    ["pyperplan", str(domain_file), str(problem_file)],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    check=False,
                )

                stdout = result.stdout
                stderr = result.stderr
                exit_code = result.returncode

                # Pyperplan writes plan to <problem_name>.soln
                plan_files = list(tmpdir_path.glob("*.soln"))
                if plan_files and exit_code == 0:
                    plan_text = plan_files[0].read_text(encoding="utf-8")
                    return plan_text, stdout, stderr, True
                else:
                    return None, stdout, stderr, False

            except FileNotFoundError:
                # Pyperplan not available, return no planner found
                return None, "", "No PDDL planner found (pyperplan not installed)", False

        except subprocess.TimeoutExpired:
            return None, "", f"Planner timeout after {timeout_sec}s", False
        except Exception as e:
            return None, "", f"Planner execution error: {str(e)}", False


def run_pddl_code(
    code: str,
    timeout_sec: float = 60.0,
    planner_path: Optional[str] = None,
    val_path: Optional[str] = None,
    run_planner: bool = True,
    run_validator: bool = True
) -> dict:
    """
    Extract, validate, plan, and validate PDDL code.

    This function:
    1. Extracts domain and problem PDDL from model output (JSON or raw format)
    2. Validates basic PDDL syntax
    3. Runs a PDDL planner to generate a plan (if run_planner=True)
    4. Validates the plan with VAL (if run_validator=True and plan exists)

    Args:
        code: Model output containing PDDL code
        timeout_sec: Timeout for planner execution
        planner_path: Optional path to PDDL planner (not used, pyperplan is default)
        val_path: Path to VAL Validate binary (defaults to repos/VAL/build/bin/Validate relative to project root)
        run_planner: Whether to run planner (default True)
        run_validator: Whether to run VAL validator on plan (default True)

    Returns:
        Dict with keys:
            - ran: bool
            - domain_pddl: str or None
            - problem_pddl: str or None
            - syntax_valid: bool
            - plan: str or None
            - plan_found: bool or None
            - val_valid: bool or None (if validator was run)
            - val_output: str (validator stdout)
            - stdout: str (planner stdout)
            - stderr: str (planner stderr)
            - error: Optional[str]
            - timeout_sec: float
    """
    if not code or not code.strip():
        return {
            "ran": False,
            "domain_pddl": None,
            "problem_pddl": None,
            "syntax_valid": False,
            "plan": None,
            "plan_found": None,
            "val_valid": None,
            "val_output": "",
            "stdout": "",
            "stderr": "",
            "error": "no code to execute",
            "timeout_sec": timeout_sec,
        }

    # Extract PDDL sections (JSON format preferred)
    domain_pddl, problem_pddl, extract_error = extract_pddl_sections(code)

    if extract_error:
        return {
            "ran": True,
            "domain_pddl": None,
            "problem_pddl": None,
            "syntax_valid": False,
            "plan": None,
            "plan_found": None,
            "val_valid": None,
            "val_output": "",
            "stdout": "",
            "stderr": "",
            "error": f"PDDL extraction failed: {extract_error}",
            "timeout_sec": timeout_sec,
        }

    # Validate syntax
    syntax_valid, syntax_error = validate_pddl_syntax(domain_pddl, problem_pddl)

    if not syntax_valid:
        return {
            "ran": True,
            "domain_pddl": domain_pddl,
            "problem_pddl": problem_pddl,
            "syntax_valid": False,
            "plan": None,
            "plan_found": None,
            "val_valid": None,
            "val_output": "",
            "stdout": "",
            "stderr": "",
            "error": f"PDDL syntax validation failed: {syntax_error}",
            "timeout_sec": timeout_sec,
        }

    # If planner disabled, return validation results only
    if not run_planner:
        return {
            "ran": True,
            "domain_pddl": domain_pddl,
            "problem_pddl": problem_pddl,
            "syntax_valid": True,
            "plan": None,
            "plan_found": None,
            "val_valid": None,
            "val_output": "",
            "stdout": "PDDL extracted and validated (planner disabled)",
            "stderr": "",
            "error": None,
            "timeout_sec": timeout_sec,
        }

    # Run planner
    plan_text, planner_stdout, planner_stderr, plan_found = run_fast_downward_planner(
        domain_pddl, problem_pddl, timeout_sec
    )

    # If no plan found, return planner results
    if not plan_found or not plan_text:
        return {
            "ran": True,
            "domain_pddl": domain_pddl,
            "problem_pddl": problem_pddl,
            "syntax_valid": True,
            "plan": plan_text,
            "plan_found": False,
            "val_valid": None,
            "val_output": "",
            "stdout": planner_stdout,
            "stderr": planner_stderr,
            "error": "planner did not find a plan",
            "timeout_sec": timeout_sec,
        }

    # Run VAL validator if enabled
    val_valid = None
    val_output = ""
    if run_validator:
        val_valid, val_stdout, val_stderr = run_val_validator(
            domain_pddl, problem_pddl, plan_text, val_path
        )
        val_output = val_stdout if val_stdout else val_stderr

    return {
        "ran": True,
        "domain_pddl": domain_pddl,
        "problem_pddl": problem_pddl,
        "syntax_valid": True,
        "plan": plan_text,
        "plan_found": True,
        "val_valid": val_valid,
        "val_output": val_output,
        "stdout": planner_stdout,
        "stderr": planner_stderr,
        "error": None if val_valid or not run_validator else "plan found but VAL validation failed",
        "timeout_sec": timeout_sec,
    }


def check_planner_available(planner_path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a PDDL planner is available.

    Args:
        planner_path: Path to planner executable

    Returns:
        (is_available, error_message)
    """
    planner = Path(planner_path)

    if not planner.exists():
        return False, f"Planner not found at: {planner_path}"

    if not planner.is_file():
        return False, f"Planner path is not a file: {planner_path}"

    # Try to run planner with --help or --version
    try:
        subprocess.run(
            [str(planner), "--help"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return True, None
    except Exception as e:
        return False, f"Cannot execute planner: {str(e)}"
