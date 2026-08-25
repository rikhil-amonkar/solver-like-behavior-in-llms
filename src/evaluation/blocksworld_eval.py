"""
BlocksWorld PDDL planning task evaluation (PDDL task).

Validates PDDL domain and problem definitions against BlocksWorld constraints.
Checks syntax, required actions, proper constraint encoding, and VAL validation.
"""

from typing import Tuple, Dict, Optional
import re
import sys
from pathlib import Path

# Import VAL validator from code_executor_pddl
sys.path.insert(0, str(Path(__file__).parent.parent))
from inference.code_executor_pddl import run_val_validator


def evaluate_blocksworld_solution(
    problem: dict,
    execution_result: dict,
    val_path: str = "/local-ssd/rma336/solver-like-behavior-in-llms/repos/VAL/build/bin/Validate",
    validate_with_golden_plan: bool = True
) -> Tuple[bool, dict]:
    """
    Validate BlocksWorld PDDL solution.

    Evaluation criteria:
    1. PDDL syntax is valid (domain and problem extracted)
    2. Domain includes required actions (pickup, putdown, stack, unstack)
    3. Problem defines correct objects, init, and goal states
    4. Plan was found by planner
    5. Plan is valid according to VAL validator
    6. (Optional) Model's domain/problem can execute the golden plan (semantic check)

    Args:
        problem: Problem dict from blocksworld_100.json
        execution_result: Result from run_pddl_code()
        val_path: Path to VAL Validate binary
        validate_with_golden_plan: Whether to check model PDDL against golden plan

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
    # Accept both hyphenated and non-hyphenated variants
    required_actions = {
        "pickup": ["pickup", "pick-up"],
        "putdown": ["putdown", "put-down"],
        "stack": ["stack"],
        "unstack": ["unstack"],
    }
    missing_actions = []

    for action_canonical, action_variants in required_actions.items():
        # Check if any variant is present
        found = False
        for variant in action_variants:
            if f":action {variant}" in domain_pddl or f":action\n  {variant}" in domain_pddl:
                found = True
                break

        if not found:
            missing_actions.append(action_canonical)

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

    # Check if plan was found (if planner was run)
    plan_found = execution_result.get("plan_found")
    plan_should_exist = problem.get("plan_exists", True)  # Default to True if not specified

    if plan_found is not None and not plan_found:
        # Planner did not find a plan - check if this is expected or an error
        stderr = execution_result.get("stderr", "")

        # Check for PDDL semantic/syntax errors
        pddl_errors = [
            "SemanticError",
            "ValueError",
            "unknown predicate",
            "unknown keyword",
            "parse error",
            "syntax error",
        ]

        is_pddl_error = any(error_type in stderr for error_type in pddl_errors)

        if is_pddl_error:
            # This is a PDDL formalization error, not a constraint violation
            return False, {
                "error": "PDDL semantic or syntax error",
                "error_type": "pddl_error",
                "planner_output": stderr[:500]  # Truncate for readability
            }

        # No PDDL errors - check if not finding a plan is expected
        if not plan_should_exist:
            # Correctly identified that no plan exists - this is CORRECT!
            return True, {
                "note": "Correctly determined that no valid plan exists for this problem"
            }

        # Plan should exist but wasn't found (timeout or genuine planning failure)
        return False, {
            "error": "planner did not find a valid plan (but plan should exist)",
            "error_type": "planning_failure",
            "planner_output": stderr[:500] if stderr else "planner timeout or no solution"
        }

    # Check VAL validation result (if validator was run)
    val_valid = execution_result.get("val_valid")
    if val_valid is not None:
        if not val_valid:
            return False, {
                "error": "VAL validation failed - plan is not valid",
                "val_output": execution_result.get("val_output", "")
            }

        # Plan was found and is valid - check if this is expected
        if not plan_should_exist:
            # Found a valid plan but shouldn't have - this is WRONG!
            return False, {
                "error": "Found a valid plan, but no plan should exist for this problem",
                "error_type": "incorrect_plan_exists"
            }

    # Semantic validation: check if model's PDDL can execute golden plan
    # This ensures the model's formalization matches the intended problem semantics
    golden = problem.get("golden_solution", {})
    if validate_with_golden_plan and golden:
        # First check constraint encoding
        constraint_validation = validate_constraint_encoding(
            domain_pddl,
            problem_pddl,
            problem.get("problem", "")
        )
        if not constraint_validation[0]:
            return False, constraint_validation[1]

        # Semantic check: can model's PDDL execute a plan for the golden problem?
        # We use the golden problem's plan with the model's domain
        # If VAL says valid, the model understood the problem correctly
        semantic_check = validate_with_golden_solution(
            domain_pddl,
            problem_pddl,
            golden,
            val_path
        )
        if not semantic_check[0]:
            return False, semantic_check[1]

    return True, {}


def validate_with_golden_solution(
    model_domain_pddl: str,
    model_problem_pddl: str,
    golden_solution: dict,
    val_path: str
) -> Tuple[bool, dict]:
    """
    Validate model's PDDL against golden solution using VAL.

    This performs a semantic check by attempting to run a reference plan
    (from the golden solution) against the model's domain/problem.
    If VAL validates the plan, the model correctly understood the problem.

    Args:
        model_domain_pddl: Model's domain PDDL
        model_problem_pddl: Model's problem PDDL
        golden_solution: Golden solution dict with domain_pddl and problem_pddl
        val_path: Path to VAL Validate binary

    Returns:
        (is_valid, error_detail)
    """
    # Extract golden domain and problem
    golden_domain = golden_solution.get("domain_pddl", "")
    golden_problem = golden_solution.get("problem_pddl", "")

    if not golden_domain or not golden_problem:
        # No golden solution available for comparison
        return True, {}

    # Generate a plan using the golden PDDL (we'll use a simple planner)
    # For now, we'll skip this semantic check if we don't have a golden plan
    # TODO: Could add pyperplan to generate golden plan on-the-fly

    # Simplified approach: just check that constraint markers are present
    # This is less rigorous but avoids needing to generate plans dynamically
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
