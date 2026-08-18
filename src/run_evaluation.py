#!/usr/bin/env python3
"""
Evaluation pipeline runner.

Validates code outputs against task constraints and computes accuracy.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, load_constraints_json, get_timestamp, IncrementalJSONWriter
from general.cli import ProgressTracker
from evaluation.calendar_eval import evaluate_calendar_solution
from evaluation.meeting_eval import evaluate_meeting_solution


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

    # Load constraints
    print("Loading constraints...")
    all_constraints = load_constraints_json(task)

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
        "inference_json": str(inference_json_path),
        "constraints_json": f"data/constraints/{task}_constraints.json",
        "timestamp": get_timestamp(),
        "num_examples": len(examples),
    }

    # Process examples
    correct_count = 0
    incorrect_count = 0
    error_breakdown = {}

    with IncrementalJSONWriter(str(output_path), metadata) as writer:
        with ProgressTracker(len(examples), f"Evaluating {task}") as progress:
            for example in examples:
                try:
                    example_id = example["example_id"]
                    parsed_output = example["code_execution"].get("parsed_output")

                    # Get example-specific constraints if available
                    example_constraints = all_constraints.get(example_id, all_constraints)

                    # Classify result
                    if not example["code_execution"]["ran"]:
                        classification = "code_execution_failed"
                        is_correct = False
                        validation = {"error": "code not executed"}
                    elif parsed_output is None:
                        classification = "parse_error"
                        is_correct = False
                        validation = {"error": "failed to parse output"}
                    else:
                        # Run task-specific validator
                        is_correct, error_detail = evaluate_solution(
                            task,
                            example_constraints,
                            parsed_output
                        )

                        classification = "correct" if is_correct else "constraint_violation"
                        validation = error_detail if not is_correct else {}

                    # Build result
                    result = {
                        "example_id": example_id,
                        "correct": is_correct,
                        "classification": classification,
                        "solution": parsed_output,
                        "validation": validation,
                    }

                    writer.write_example(result)

                    # Update counts
                    if is_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                        error_breakdown[classification] = error_breakdown.get(classification, 0) + 1

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

    # Print summary
    total = len(examples)
    accuracy = correct_count / total if total > 0 else 0

    print(f"\n✓ Evaluation complete!")
    print(f"  Accuracy: {correct_count}/{total} ({accuracy:.2%})")
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
