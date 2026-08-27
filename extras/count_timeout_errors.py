#!/usr/bin/env python3
"""
Scan execution/evaluation JSONs for timeout errors and count them.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def count_timeout_errors_in_execution(json_path: str) -> dict:
    """
    Count timeout errors in an execution JSON.

    Returns:
        Dict with counts of different error types
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    error_counts = defaultdict(int)
    timeout_examples = []

    for example in data.get("examples", []):
        code_execution = example.get("code_execution", {})
        stderr = code_execution.get("stderr", "")
        planner_output = code_execution.get("planner_output", "")

        # Check for timeout
        is_timeout = (
            "Read timed out" in stderr or
            "Read timed out" in planner_output or
            "SOLVER_TIMEOUT" in stderr or
            "timeout" in stderr.lower()
        )

        if is_timeout:
            error_counts["timeout"] += 1
            timeout_examples.append(example.get("example_id", "unknown"))
        elif code_execution.get("ran") and code_execution.get("syntax_valid"):
            if code_execution.get("plan_found"):
                error_counts["plan_found"] += 1
            else:
                error_counts["no_plan"] += 1
        elif code_execution.get("ran"):
            error_counts["syntax_error"] += 1
        else:
            error_counts["not_run"] += 1

    total = len(data.get("examples", []))

    return {
        "file": json_path,
        "total_examples": total,
        "plan_found": error_counts["plan_found"],
        "timeout": error_counts["timeout"],
        "syntax_error": error_counts["syntax_error"],
        "no_plan": error_counts["no_plan"],
        "not_run": error_counts["not_run"],
        "timeout_examples": timeout_examples[:10],  # Show first 10
    }


def count_timeout_errors_in_evaluation(json_path: str) -> dict:
    """
    Count timeout errors in an evaluation JSON.

    Returns:
        Dict with counts of different error types
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    error_counts = defaultdict(int)
    timeout_examples = []

    for example in data.get("examples", []):
        error_detail = example.get("error_detail", {})
        error_type = error_detail.get("error_type", "")
        error_msg = error_detail.get("error", "")
        planner_output = error_detail.get("planner_output", "")

        # Check for timeout in various fields
        is_timeout = (
            error_type == "solver_timeout" or
            "timeout" in error_msg.lower() or
            "Read timed out" in planner_output or
            "SOLVER_TIMEOUT" in planner_output
        )

        if is_timeout:
            error_counts["timeout"] += 1
            timeout_examples.append(example.get("example_id", "unknown"))
        elif error_type == "pddl_error":
            error_counts["pddl_error"] += 1
        elif error_type == "planning_failure":
            error_counts["planning_failure"] += 1
        elif example.get("passes_constraints"):
            error_counts["success"] += 1
        else:
            error_counts["other_failure"] += 1

    total = len(data.get("examples", []))

    return {
        "file": json_path,
        "total_examples": total,
        "success": error_counts["success"],
        "timeout": error_counts["timeout"],
        "pddl_error": error_counts["pddl_error"],
        "planning_failure": error_counts["planning_failure"],
        "other_failure": error_counts["other_failure"],
        "timeout_examples": timeout_examples[:10],  # Show first 10
    }


def scan_directory(directory: str = "output", scan_execution: bool = True):
    """
    Scan all execution/evaluation JSONs in output directory.

    Args:
        directory: Output directory to scan
        scan_execution: If True, scan execution JSONs; otherwise scan evaluation JSONs
    """
    output_dir = Path(directory)

    if scan_execution:
        files = list(output_dir.glob("**/*execution.json"))
        file_type = "execution"
        count_func = count_timeout_errors_in_execution
    else:
        files = list(output_dir.glob("**/*evaluation.json"))
        file_type = "evaluation"
        count_func = count_timeout_errors_in_evaluation

    print(f"\n=== Scanning {len(files)} {file_type} files ===\n")

    all_results = []
    total_timeout = 0
    total_examples = 0

    for file_path in sorted(files):
        result = count_func(str(file_path))
        all_results.append(result)

        total_timeout += result["timeout"]
        total_examples += result["total_examples"]

        # Only print files with timeouts
        if result["timeout"] > 0:
            rel_path = file_path.relative_to(output_dir)
            print(f"📁 {rel_path}")
            print(f"   Total: {result['total_examples']}")

            if scan_execution:
                print(f"   ✓ Plan found: {result.get('plan_found', 0)}")
                print(f"   ⏱ Timeout: {result['timeout']} ({result['timeout']/result['total_examples']*100:.1f}%)")
                print(f"   ❌ Syntax error: {result.get('syntax_error', 0)}")
                print(f"   ❓ No plan: {result.get('no_plan', 0)}")
            else:
                print(f"   ✓ Success: {result.get('success', 0)}")
                print(f"   ⏱ Timeout: {result['timeout']} ({result['timeout']/result['total_examples']*100:.1f}%)")
                print(f"   ❌ PDDL Error: {result.get('pddl_error', 0)}")
                print(f"   ⚠ Planning Failure: {result.get('planning_failure', 0)}")
                print(f"   ❓ Other: {result.get('other_failure', 0)}")

            if result["timeout_examples"]:
                print(f"   Example IDs: {', '.join(result['timeout_examples'][:5])}")
            print()

    # Summary
    print(f"\n=== Summary ===")
    print(f"Total files scanned: {len(files)}")
    print(f"Total examples: {total_examples}")
    print(f"Total timeouts: {total_timeout} ({total_timeout/total_examples*100:.1f}% if total_examples > 0 else 0)")
    print(f"Files with timeouts: {sum(1 for r in all_results if r['timeout'] > 0)}")

    return all_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Count timeout errors in execution/evaluation JSONs")
    parser.add_argument("--dir", default="output", help="Output directory to scan (default: output)")
    parser.add_argument("--execution", action="store_true", help="Scan execution JSONs (default)")
    parser.add_argument("--evaluation", action="store_true", help="Scan evaluation JSONs instead")
    parser.add_argument("--file", help="Scan a single file instead of directory")

    args = parser.parse_args()

    # Default to execution if neither specified
    scan_execution = not args.evaluation

    if args.file:
        if "execution" in args.file:
            result = count_timeout_errors_in_execution(args.file)
        else:
            result = count_timeout_errors_in_evaluation(args.file)
        print(json.dumps(result, indent=2))
    else:
        scan_directory(args.dir, scan_execution=scan_execution)
