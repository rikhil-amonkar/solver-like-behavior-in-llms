"""Execute and validate PDDL code for planning tasks."""

import subprocess
import tempfile
import re
from pathlib import Path
from typing import Optional, Tuple


def extract_pddl_sections(code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract domain and problem PDDL from model output.

    Models may output PDDL in various formats:
    - Inside ```pddl or ``` code blocks
    - As raw S-expressions
    - With commentary/explanations outside blocks

    Args:
        code: Model output containing PDDL code

    Returns:
        (domain_pddl, problem_pddl, error_message)
    """
    # Try to extract from code blocks first
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


def run_pddl_code(code: str, timeout_sec: float = 60.0, planner_path: Optional[str] = None) -> dict:
    """
    Extract, validate, and optionally plan PDDL code.

    This function:
    1. Extracts domain and problem PDDL from model output
    2. Validates basic PDDL syntax
    3. Optionally runs a PDDL planner (if planner_path provided)

    Args:
        code: Model output containing PDDL code
        timeout_sec: Timeout for planner execution
        planner_path: Optional path to PDDL planner executable
                     (e.g., fast-downward.py or pyperplan)

    Returns:
        Dict with keys:
            - ran: bool
            - domain_pddl: str or None
            - problem_pddl: str or None
            - syntax_valid: bool
            - plan: str or None (if planner was run)
            - plan_found: bool or None
            - stdout: str
            - stderr: str
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
            "stdout": "",
            "stderr": "",
            "error": "no code to execute",
            "timeout_sec": timeout_sec,
        }

    # Extract PDDL sections
    domain_pddl, problem_pddl, extract_error = extract_pddl_sections(code)

    if extract_error:
        return {
            "ran": True,
            "domain_pddl": None,
            "problem_pddl": None,
            "syntax_valid": False,
            "plan": None,
            "plan_found": None,
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
            "stdout": "",
            "stderr": "",
            "error": f"PDDL syntax validation failed: {syntax_error}",
            "timeout_sec": timeout_sec,
        }

    # If no planner specified, return validation results
    if not planner_path:
        return {
            "ran": True,
            "domain_pddl": domain_pddl,
            "problem_pddl": problem_pddl,
            "syntax_valid": True,
            "plan": None,
            "plan_found": None,
            "stdout": "PDDL extracted and validated (no planner run)",
            "stderr": "",
            "error": None,
            "timeout_sec": timeout_sec,
        }

    # Run planner
    with tempfile.TemporaryDirectory(prefix="pddl_exec_") as tmpdir:
        domain_file = Path(tmpdir) / "domain.pddl"
        problem_file = Path(tmpdir) / "problem.pddl"

        domain_file.write_text(domain_pddl, encoding="utf-8")
        problem_file.write_text(problem_pddl, encoding="utf-8")

        try:
            # Run planner (command depends on which planner is used)
            # This is a generic approach - adjust for specific planners
            result = subprocess.run(
                [planner_path, str(domain_file), str(problem_file)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            # Parse plan from output (format depends on planner)
            plan_found = exit_code == 0 and "plan" in stdout.lower()
            plan = stdout if plan_found else None
            error = None if exit_code == 0 else f"planner exit code {exit_code}"

        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = f"Planner timeout after {timeout_sec}s"
            plan_found = False
            plan = None
            error = f"planner timeout after {timeout_sec}s"

        except FileNotFoundError:
            stdout = ""
            stderr = f"Planner not found: {planner_path}"
            plan_found = False
            plan = None
            error = f"planner not found: {planner_path}"

        except Exception as e:
            stdout = ""
            stderr = str(e)
            plan_found = False
            plan = None
            error = f"planner execution error: {str(e)}"

    return {
        "ran": True,
        "domain_pddl": domain_pddl,
        "problem_pddl": problem_pddl,
        "syntax_valid": True,
        "plan": plan,
        "plan_found": plan_found,
        "stdout": stdout,
        "stderr": stderr,
        "error": error,
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
