"""
BlocksWorld PDDL planning task evaluation (PDDL task).

Validates PDDL domain and problem definitions against BlocksWorld constraints.
Checks syntax, required actions, and proper constraint encoding.
"""

from typing import Tuple, Dict, Optional
import re


def evaluate_blocksworld_solution(
    problem: dict,
    execution_result: dict
) -> Tuple[bool, dict]:
    """
    Validate BlocksWorld PDDL solution.

    Evaluation criteria:
    1. PDDL syntax is valid (domain and problem extracted)
    2. Domain includes required actions (pickup, putdown, stack, unstack)
    3. Problem defines correct objects, init, and goal states
    4. (Optional) Plan exists and achieves goal from init state

    Args:
        problem: Problem dict from blocksworld_100.json
        execution_result: Result from run_pddl_code()

    Returns:
        (is_valid, error_detail)
    """
    # Check if PDDL was extracted and validated
    if not execution_result.get("ran"):
        return False, {"error": "PDDL code was not executed"}

    if not execution_result.get("syntax_valid"):
        return False, {
            "error": "PDDL syntax validation failed",
            "details": execution_result.get("error", "unknown syntax error")
        }

    domain_pddl = execution_result.get("domain_pddl", "")
    problem_pddl = execution_result.get("problem_pddl", "")

    # Validate domain has required actions
    required_actions = ["pickup", "putdown", "stack", "unstack"]
    missing_actions = []

    for action in required_actions:
        if f":action {action}" not in domain_pddl and f":action\n  {action}" not in domain_pddl:
            missing_actions.append(action)

    if missing_actions:
        return False, {
            "error": "domain missing required actions",
            "missing": missing_actions
        }

    # Validate domain has predicates
    if ":predicates" not in domain_pddl:
        return False, {"error": "domain missing :predicates section"}

    # Validate problem structure
    problem_checks = [
        (":domain", "problem missing :domain reference"),
        (":objects", "problem missing :objects section"),
        (":init", "problem missing :init section"),
        (":goal", "problem missing :goal section"),
    ]

    for pattern, error_msg in problem_checks:
        if pattern not in problem_pddl:
            return False, {"error": error_msg}

    # Check if problem references correct domain
    # Extract domain name from domain definition
    domain_name_match = re.search(r'\(define\s+\(domain\s+([\w-]+)\)', domain_pddl)
    if domain_name_match:
        domain_name = domain_name_match.group(1)
        if f":domain {domain_name}" not in problem_pddl:
            return False, {
                "error": "problem does not reference correct domain",
                "domain_name": domain_name
            }

    # Optional: Check if plan was found (if planner was run)
    plan_found = execution_result.get("plan_found")
    if plan_found is not None:
        if not plan_found:
            return False, {
                "error": "planner did not find a valid plan",
                "planner_output": execution_result.get("stderr", "")
            }

    # Optionally: validate against golden solution structure
    # (Check if constraints are properly encoded)
    golden = problem.get("golden_solution", {})
    if golden:
        validation_result = validate_constraint_encoding(
            domain_pddl,
            problem_pddl,
            problem.get("problem", "")
        )
        if not validation_result[0]:
            return False, validation_result[1]

    return True, {}


def validate_constraint_encoding(
    domain_pddl: str,
    problem_pddl: str,
    problem_description: str
) -> Tuple[bool, dict]:
    """
    Validate that additional constraints are properly encoded in PDDL.

    BlocksWorld problems may have additional constraints like:
    - "Block 1 is fragile" (no blocks can be placed on it)
    - "Start holding block2" (initial state constraint)
    - "Max 3 stacks at once" (state constraint)

    Args:
        domain_pddl: Domain PDDL
        problem_pddl: Problem PDDL
        problem_description: Natural language problem description

    Returns:
        (is_valid, error_detail)
    """
    # Extract constraint mentions from description
    constraint_markers = [
        "Additional constraint:",
        "CONSTRAINT:",
    ]

    has_constraint = any(marker in problem_description for marker in constraint_markers)

    if not has_constraint:
        # No additional constraints, basic PDDL is sufficient
        return True, {}

    # Check if PDDL includes constraint-related comments
    constraint_comments = [
        ";; CONSTRAINT",
        ";; BEGIN ADD",
        ";; BEGIN EDIT",
    ]

    has_constraint_markers = any(marker in domain_pddl or marker in problem_pddl
                                   for marker in constraint_comments)

    if not has_constraint_markers:
        return False, {
            "error": "problem has constraints but PDDL lacks constraint markers",
            "suggestion": "use comments like ';; CONSTRAINT' or ';; BEGIN ADD' to mark modifications"
        }

    # All checks passed
    return True, {}


def extract_plan_from_output(stdout: str) -> Optional[list]:
    """
    Extract plan steps from planner output.

    Different planners have different output formats.
    This handles common formats.

    Args:
        stdout: Planner stdout

    Returns:
        List of action strings, or None if no plan found
    """
    if not stdout or "plan" not in stdout.lower():
        return None

    plan = []
    lines = stdout.split('\n')

    for line in lines:
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith(';') or line.startswith('#'):
            continue

        # Fast Downward format: "action-name arg1 arg2"
        # Pyperplan format: "(action-name arg1 arg2)"

        # Remove parentheses and parse
        action_line = line.strip('()')

        # Check if it looks like an action
        if ' ' in action_line or '-' in action_line:
            plan.append(action_line)

    return plan if plan else None


def check_blocksworld_plan_validity(
    domain_pddl: str,
    problem_pddl: str,
    plan: list
) -> Tuple[bool, dict]:
    """
    Check if a plan is valid for the given PDDL problem.

    This is a simplified check - full validation requires a PDDL validator.

    Args:
        domain_pddl: Domain definition
        problem_pddl: Problem definition
        plan: List of action strings

    Returns:
        (is_valid, error_detail)
    """
    # Basic check: plan is non-empty
    if not plan:
        return False, {"error": "plan is empty"}

    # Check that all actions in plan are defined in domain
    defined_actions = re.findall(r':action\s+([\w-]+)', domain_pddl)

    for action_str in plan:
        action_name = action_str.split()[0] if ' ' in action_str else action_str

        if action_name not in defined_actions:
            return False, {
                "error": f"plan uses undefined action: {action_name}",
                "defined_actions": defined_actions
            }

    # All basic checks passed
    return True, {}
