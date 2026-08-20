#!/usr/bin/env python3
"""
Evaluation pipeline runner.

Validates code outputs against task constraints and computes accuracy.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, load_constraints_json, load_problems_with_solutions, get_timestamp, IncrementalJSONWriter, make_path_relative
from general.cli import ProgressTracker
from evaluation.calendar_eval_python import evaluate_calendar_solution
from evaluation.meeting_eval_python import evaluate_meeting_solution
from evaluation.zebralogic_eval import evaluate_zebralogic_solution
from evaluation.blocksworld_eval import evaluate_blocksworld_solution


def is_no_solution_indicator(stdout: str) -> bool:
    """
    Check if stdout indicates "no solution found" rather than parse error.

    Args:
        stdout: Output string from code execution

    Returns:
        True if this looks like "no solution found" message
    """
    if not stdout:
        return False

    stdout_lower = stdout.lower().strip()

    # Common "no solution" patterns
    no_solution_patterns = [
        "no solution",
        "no valid solution",
        "no meeting",
        "no plan",
        "not possible",
        "impossible",
        "cannot find",
        "none found",
    ]

    # Check for exact matches or substrings
    if any(pattern in stdout_lower for pattern in no_solution_patterns):
        return True

    # Check if output is just empty list/none representations (literal or string form)
    empty_value_patterns = [
        "[]",           # empty list
        "{}",           # empty dict
        "none",         # None
        "null",         # null
        "'[]'",         # string literal of empty list
        "\"[]\"",       # string literal of empty list
        "'none'",       # string literal of None
        "\"none\"",     # string literal of None
        "'null'",       # string literal of null
        "\"null\"",     # string literal of null
        "'{}'",         # string literal of empty dict
        "\"{}\"",       # string literal of empty dict
    ]

    if stdout_lower in empty_value_patterns:
        return True

    return False


def run_evaluation_pipeline(inference_json_path: str):
    """
    Run evaluation pipeline on inference results.

    Args:
        inference_json_path: Path to inference JSON output
    """
    print(f"\n=== Evaluation Pipeline ===")
    print(f"Input: {inference_json_path}\n")

    # Load inference results
    print("Loading inference results...")
    inference_data = load_json_file(inference_json_path)

    task = inference_data["run_metadata"]["task"]
    model = inference_data["run_metadata"]["model"]
    condition = inference_data["run_metadata"].get("condition", "baseline")
    examples = inference_data["examples"]

    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Examples: {len(examples)}")

    # Load constraints and golden solutions
    print("Loading constraints...")
    all_constraints = load_constraints_json(task)
    print("Loading golden solutions...")
    golden_solutions = load_problems_with_solutions(task)

    # Determine output path (use same condition as inference)
    inference_path = Path(inference_json_path)
    output_filename = f"{condition}_evaluation.json"
    output_path = inference_path.parent / output_filename
    print(f"Output: {output_path}\n")

    # Build metadata
    metadata = {
        "task": task,
        "model": model,
        "condition": condition,
        "inference_json": make_path_relative(str(inference_json_path)),
        "constraints_json": f"data/constraints/{task}_constraints.json",
        "timestamp": get_timestamp(),
        "num_examples": len(examples),
    }

    # Initialize summary with all possible error categories at 0
    all_error_categories = [
        "code_execution_failed",
        "execution_error",
        "no_output",
        "no_solution",
        "parse_error",
        "constraint_violation",
        "evaluation_error",
    ]

    # Build initial summary skeleton
    initial_summary = {
        "constraint_based_accuracy": 0.0,
        "constraint_correct": 0,
        "constraint_incorrect": 0,
        "golden_solution_accuracy": None,
        "golden_matches": 0,
        "golden_available": 0,
        "error_breakdown": {cat: 0 for cat in all_error_categories},
    }

    # Process examples
    correct_count = 0
    incorrect_count = 0
    golden_match_count = 0
    golden_available_count = 0
    error_breakdown = {cat: 0 for cat in all_error_categories}

    with IncrementalJSONWriter(str(output_path), metadata, summary=initial_summary) as writer:
        with ProgressTracker(len(examples), f"Evaluating {task}") as progress:
            for example in examples:
                try:
                    example_id = example["example_id"]
                    parsed_output = example["code_execution"].get("parsed_output")

                    # Get example-specific constraints if available
                    example_data = all_constraints.get(example_id, all_constraints)

                    # Extract nested constraints if present
                    if "constraints" in example_data:
                        example_constraints = example_data["constraints"]
                    else:
                        example_constraints = example_data

                    # Get golden solution from problems JSON
                    golden_solution = golden_solutions.get(example_id)

                    # Classify result with fine-grained categories
                    exec_result = example["code_execution"]

                    if not exec_result["ran"]:
                        classification = "code_execution_failed"
                        is_correct = False
                        validation = {"error": "code not executed"}
                    elif exec_result["exit_code"] != 0:
                        # Code ran but exited with error
                        classification = "execution_error"
                        is_correct = False
                        validation = {
                            "error": "execution failed",
                            "exit_code": exec_result["exit_code"],
                            "stderr": exec_result.get("stderr", "")[:200]  # truncate
                        }
                    elif parsed_output is None:
                        # Code ran successfully but no parseable output
                        stdout = exec_result.get("stdout", "").strip()

                        # Check if this is a "no solution" indicator
                        if is_no_solution_indicator(stdout):
                            classification = "no_solution"
                            is_correct = False
                            validation = {
                                "error": "model reported no solution",
                                "stdout": stdout[:200]
                            }
                        elif not stdout:
                            classification = "no_output"
                            is_correct = False
                            validation = {"error": "empty stdout"}
                        else:
                            classification = "parse_error"
                            is_correct = False
                            validation = {
                                "error": "failed to parse output",
                                "stdout": stdout[:200]
                            }
                    else:
                        # Parsed successfully, run task-specific validator
                        # For z3/pddl tasks, pass execution result instead of parsed output
                        if task in ["zebralogic", "blocksworld"]:
                            solution_data = example["code_execution"]  # Pass full execution result
                        else:
                            solution_data = parsed_output  # Pass parsed output

                        is_correct, error_detail = evaluate_solution(
                            task,
                            example_constraints,
                            solution_data
                        )

                        classification = "correct" if is_correct else "constraint_violation"
                        validation = error_detail if not is_correct else {}

                    # Check if solution matches golden solution
                    matches_golden = False
                    if golden_solution is not None and parsed_output is not None:
                        matches_golden = parsed_output == golden_solution

                    # Build result
                    result = {
                        "example_id": example_id,
                        "correct": is_correct,
                        "matches_expected": matches_golden,
                        "classification": classification,
                        "solution": parsed_output,
                        "expected_solution": golden_solution,
                        "validation": validation,
                    }

                    writer.write_example(result)

                    # Update counts
                    if is_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                        error_breakdown[classification] = error_breakdown.get(classification, 0) + 1

                    # Update golden match counts
                    if golden_solution is not None:
                        golden_available_count += 1
                        if matches_golden:
                            golden_match_count += 1

                except Exception as e:
                    print(f"\nError evaluating {example.get('example_id', '?')}: {str(e)}")

                    # Write error result
                    result = {
                        "example_id": example.get("example_id", "unknown"),
                        "correct": False,
                        "classification": "evaluation_error",
                        "solution": None,
                        "validation": {"error": f"evaluation failed: {str(e)}"},
                    }
                    writer.write_example(result)
                    incorrect_count += 1
                    error_breakdown["evaluation_error"] = error_breakdown.get("evaluation_error", 0) + 1

                progress.update(1)
                progress.set_postfix(correct=correct_count, incorrect=incorrect_count)

        # Calculate accuracies
        total = len(examples)
        constraint_accuracy = correct_count / total if total > 0 else 0
        golden_accuracy = golden_match_count / golden_available_count if golden_available_count > 0 else None

        # Build final summary (with actual counts)
        final_summary = {
            "constraint_based_accuracy": constraint_accuracy,
            "constraint_correct": correct_count,
            "constraint_incorrect": incorrect_count,
            "golden_solution_accuracy": golden_accuracy,
            "golden_matches": golden_match_count,
            "golden_available": golden_available_count,
            "error_breakdown": error_breakdown,  # Already has all categories
        }

        # Close examples array (summary already at top)
        writer.finalize_with_summary(final_summary)

    # Print summary
    print(f"\n✓ Evaluation complete!")
    print(f"  Constraint-based accuracy: {correct_count}/{total} ({constraint_accuracy:.2%})")
    if golden_accuracy is not None:
        print(f"  Golden solution accuracy: {golden_match_count}/{golden_available_count} ({golden_accuracy:.2%})")
    else:
        print(f"  Golden solution accuracy: N/A (no golden solutions)")
    print(f"  Errors: {incorrect_count}/{total}")
    if error_breakdown:
        print(f"  Breakdown:")
        for error_type, count in error_breakdown.items():
            print(f"    {error_type}: {count}")
    print(f"  Output: {output_path}")


def evaluate_solution(task: str, constraints: dict, solution) -> tuple:
    """
    Dispatch to task-specific evaluator.

    Args:
        task: Task name
        constraints: Constraints dict
        solution: Parsed solution

    Returns:
        (is_valid, error_detail)
    """
    if task == "calendar":
        return evaluate_calendar_solution(constraints, solution)
    elif task == "meeting":
        return evaluate_meeting_solution(constraints, solution)
    elif task == "zebralogic":
        # For zebralogic, extract stdout from solution (execution result)
        stdout = solution.get("stdout", "") if isinstance(solution, dict) else str(solution)
        return evaluate_zebralogic_solution(constraints, stdout)
    elif task == "blocksworld":
        # For blocksworld, pass full execution result
        return evaluate_blocksworld_solution(constraints, solution)
    else:
        return False, {"error": f"unknown task: {task}"}


def main():
    parser = argparse.ArgumentParser(
        description="Run evaluation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/run_evaluation.py --input output/deepseek/calendar/inference.json
        """
    )

    parser.add_argument(
        "--input",
        "--inference-json",
        required=True,
        dest="inference_json",
        help="Path to inference JSON output"
    )

    args = parser.parse_args()

    try:
        run_evaluation_pipeline(args.inference_json)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
