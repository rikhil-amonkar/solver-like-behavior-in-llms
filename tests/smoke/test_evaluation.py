#!/usr/bin/env python3
"""
Smoke test for evaluation pipeline.

Tests evaluation on smoke test inference outputs.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from general.io_utils import load_json_file, load_constraints_json, load_problems_with_solutions, get_timestamp, IncrementalJSONWriter, make_path_relative
from general.cli import ProgressTracker
from evaluation.calendar_eval import evaluate_calendar_solution
from evaluation.meeting_eval import evaluate_meeting_solution


def run_smoke_test_evaluation():
    """Run smoke test for evaluation."""
    print(f"\n{'='*60}")
    print(f"SMOKE TEST: Evaluation Pipeline")
    print(f"{'='*60}\n")

    # Find smoke test inference outputs
    test_output_dir = Path(__file__).parent / "output"

    if not test_output_dir.exists():
        print("Error: No smoke test outputs found!")
        print("Run test_inference.py first to generate test data.")
        sys.exit(1)

    # Test both tasks
    for task in ["calendar", "meeting"]:
        inference_path = test_output_dir / f"smoke_{task}_inference.json"

        if not inference_path.exists():
            print(f"⚠ Skipping {task}: No inference output found")
            continue

        print(f"\n--- Testing {task} ---\n")
        print(f"Input: {inference_path}")

        # Load inference data
        inference_data = load_json_file(str(inference_path))
        examples = inference_data["examples"]

        print(f"Examples: {len(examples)}")

        # Load constraints
        all_constraints = load_constraints_json(task)

        # Load golden solutions
        golden_solutions = load_problems_with_solutions(task)

        # Prepare output
        output_path = test_output_dir / f"smoke_{task}_evaluation.json"
        print(f"Output: {output_path}")

        metadata = {
            "task": task,
            "model": inference_data["run_metadata"]["model"],
            "condition": "baseline",
            "test_type": "smoke_test",
            "inference_json": make_path_relative(str(inference_path)),
            "timestamp": get_timestamp(),
            "num_examples": len(examples),
        }

        # Evaluate
        correct_count = 0
        incorrect_count = 0
        golden_match_count = 0
        golden_available_count = 0
        error_breakdown = {}

        with IncrementalJSONWriter(str(output_path), metadata) as writer:
            with ProgressTracker(len(examples), f"Evaluating {task}") as progress:
                for example in examples:
                    try:
                        example_id = example["example_id"]
                        parsed_output = example["code_execution"].get("parsed_output")

                        # Get constraints
                        example_data = all_constraints.get(example_id, all_constraints)

                        # Extract nested constraints if present
                        if "constraints" in example_data:
                            example_constraints = example_data["constraints"]
                        else:
                            example_constraints = example_data

                        # Get golden solution from problems JSON
                        golden_solution = golden_solutions.get(example_id)

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
                            if task == "calendar":
                                is_correct, error_detail = evaluate_calendar_solution(
                                    example_constraints, parsed_output
                                )
                            else:  # meeting
                                is_correct, error_detail = evaluate_meeting_solution(
                                    example_constraints, parsed_output
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
                        incorrect_count += 1
                        error_breakdown["evaluation_error"] = error_breakdown.get("evaluation_error", 0) + 1

                        result = {
                            "example_id": example.get("example_id", "unknown"),
                            "correct": False,
                            "matches_expected": False,
                            "classification": "evaluation_error",
                            "solution": None,
                            "expected_solution": None,
                            "validation": {"error": f"evaluation failed: {str(e)}"},
                        }
                        writer.write_example(result)

                    progress.update(1)
                    progress.set_postfix(correct=correct_count, incorrect=incorrect_count)

            # Calculate and write summary
            total = len(examples)
            constraint_accuracy = correct_count / total if total > 0 else 0
            golden_accuracy = golden_match_count / golden_available_count if golden_available_count > 0 else None

            summary = {
                "constraint_based_accuracy": constraint_accuracy,
                "constraint_correct": correct_count,
                "constraint_incorrect": incorrect_count,
                "golden_solution_accuracy": golden_accuracy,
                "golden_matches": golden_match_count,
                "golden_available": golden_available_count,
                "error_breakdown": error_breakdown,
            }

            writer.finalize_with_summary(summary)

        # Print summary
        print(f"\n✓ {task} evaluation complete:")
        print(f"  Constraint-based accuracy: {correct_count}/{total} ({constraint_accuracy:.1%})")
        if golden_accuracy is not None:
            print(f"  Golden solution accuracy: {golden_match_count}/{golden_available_count} ({golden_accuracy:.1%})")
        else:
            print(f"  Golden solution accuracy: N/A (no golden solutions)")
        if error_breakdown:
            print(f"  Errors:")
            for error_type, count in error_breakdown.items():
                print(f"    {error_type}: {count}")
        print(f"  Output: {output_path}")

    print(f"\n{'='*60}")
    print(f"SMOKE TEST COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        run_smoke_test_evaluation()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
