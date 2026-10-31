"""
BlocksWorld (PDDL) evaluation.

Evaluation pipeline:
1. The execution stage runs a planner on the model's domain + the model's problem PDDL.
2. Here, the resulting plan is validated with VAL against the golden domain + golden
   problem PDDL (which encode the instance's additional constraint).

A response is correct if:
- the instance is solvable (plan_exists) and the plan from the model's PDDL is valid
  under the golden PDDL, or
- the instance is unsolvable and the planner proved the model's PDDL has no plan.
"""

import re
from pathlib import Path
from typing import Tuple

from inference.code_executor_pddl import (
    run_val_validator,
    FD_INPUT_ERROR_CODES,
    FD_TIMEOUT_CODES,
)


def evaluate_blocksworld_solution(
    problem: dict,
    execution_result: dict,
    val_path: str = None,  # Will default to repos/VAL/build/bin/Validate relative to project root
) -> Tuple[bool, dict]:
    """
    Validate a BlocksWorld PDDL solution against the golden PDDL.

    Args:
        problem: Problem dict from blocksworld_100.json (contains golden_solution and plan_exists)
        execution_result: Result from run_pddl_code()
        val_path: Path to VAL Validate binary

    Returns:
        (is_valid, error_detail)
    """
    if val_path is None:
        project_root = Path(__file__).parent.parent.parent
        val_path = str(project_root / "repos" / "VAL" / "build" / "bin" / "Validate")

    golden = problem.get("golden_solution") or {}
    golden_domain = golden.get("domain_pddl")
    golden_problem = golden.get("problem_pddl")
    if not golden_domain or not golden_problem:
        return False, {"error": "golden domain/problem PDDL missing", "error_type": "evaluation_error"}

    if not execution_result.get("ran"):
        return False, {"error": "PDDL code was not executed"}

    if not execution_result.get("syntax_valid"):
        return False, {
            "error": "PDDL syntax validation failed",
            "details": execution_result.get("error", "unknown syntax error")
        }

    plan_should_exist = problem.get("plan_exists", True)
    plan = execution_result.get("plan")
    exit_code = execution_result.get("planner_exit_code")
    planner_output = (execution_result.get("stderr") or execution_result.get("stdout") or "")[-500:]

    if not execution_result.get("plan_found") or plan is None:  # "" is the empty plan
        if exit_code in FD_TIMEOUT_CODES:
            return False, {
                "error": "planner timed out on the model's PDDL",
                "error_type": "solver_timeout",
                "planner_output": planner_output,
            }
        if exit_code in FD_INPUT_ERROR_CODES or exit_code is None:
            return False, {
                "error": "planner rejected the model's PDDL",
                "error_type": "pddl_error",
                "planner_exit_code": exit_code,
                "planner_output": planner_output,
            }
        if not plan_should_exist:
            if execution_result.get("plan_proven_unsolvable"):
                return True, {"note": "Correctly determined that no valid plan exists for this problem"}
            return False, {
                "error": "no plan found, but unsolvability was not proven",
                "error_type": "planning_failure",
                "planner_exit_code": exit_code,
            }
        return False, {
            "error": "planner did not find a plan (but plan should exist)",
            "error_type": "planning_failure",
            "planner_exit_code": exit_code,
            "planner_output": planner_output,
        }

    if not plan_should_exist:
        return False, {
            "error": "Found a plan, but no plan should exist for this problem",
            "error_type": "incorrect_plan_exists",
        }

    golden_plan = rename_plan_actions(plan, golden_domain)
    val_valid, val_stdout, val_stderr = run_val_validator(golden_domain, golden_problem, golden_plan, val_path)
    if not val_valid:
        return False, {
            "error": "plan from the model's PDDL is not valid under the golden PDDL",
            "error_type": "invalid_plan",
            "val_output": (val_stdout or val_stderr)[-1000:],
        }

    return True, {}


def rename_plan_actions(plan: str, golden_domain: str) -> str:
    """
    Map plan action names onto the golden domain's names when they differ only
    in case, hyphens or underscores (e.g. PICK-UP -> pickup).
    """
    golden_actions = re.findall(r'\(:action\s+([\w-]+)', golden_domain)
    lookup = {re.sub(r'[-_]', '', a.lower()): a for a in golden_actions}

    def rename(match):
        name = match.group(1)
        return "(" + lookup.get(re.sub(r'[-_]', '', name.lower()), name)

    return "\n".join(
        line if line.lstrip().startswith(";") else re.sub(r'^\s*\(\s*([\w-]+)', rename, line)
        for line in plan.splitlines()
    )
