#!/usr/bin/env python3
"""
Smoke test for inference pipeline.

Tests with 3 random calendar + 3 random meeting examples.
"""

import sys
import json
import random
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from general.io_utils import load_problems_json, get_timestamp, IncrementalJSONWriter
from general.prompt_utils import load_prompt_template, get_task_prompts, build_full_prompt
from general.parsing_utils import split_reasoning_and_code
from general.cli import ProgressTracker
from inference.model_caller import call_model
from inference.code_executor import run_code


def run_smoke_test_inference(model="deepseek", num_per_task=3):
    """
    Run smoke test for inference.

    Args:
        model: Model to test (deepseek, qwen, gpt)
        num_per_task: Number of examples per task
    """
    print(f"\n{'='*60}")
    print(f"SMOKE TEST: Inference Pipeline")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Examples per task: {num_per_task}")
    print(f"{'='*60}\n")

    # Setup output directory
    test_output_dir = Path(__file__).parent / "output"
    test_output_dir.mkdir(exist_ok=True)

    # Test both tasks
    for task in ["calendar", "meeting"]:
        print(f"\n--- Testing {task} ---\n")

        # Load problems and sample random examples
        all_problems = load_problems_json(task)
        all_example_ids = list(all_problems.keys())
        random.seed(42)  # Reproducible random selection
        sampled_ids = random.sample(all_example_ids, min(num_per_task, len(all_example_ids)))

        print(f"Sampled {len(sampled_ids)} random examples")

        # Load prompts
        universal_prefix_path, output_format_path = get_task_prompts(task)
        universal_prefix = load_prompt_template(universal_prefix_path)
        output_format = load_prompt_template(output_format_path)

        # Prepare output
        output_path = test_output_dir / f"smoke_{task}_inference.json"
        print(f"Output: {output_path}")

        metadata = {
            "task": task,
            "model": model,
            "condition": "baseline",
            "test_type": "smoke_test",
            "timestamp": get_timestamp(),
            "num_examples": len(sampled_ids),
            "sampled_example_ids": sampled_ids,
        }

        # Run inference
        success_count = 0
        error_count = 0

        with IncrementalJSONWriter(str(output_path), metadata) as writer:
            with ProgressTracker(len(sampled_ids), f"Testing {task}") as progress:
                for example_id in sampled_ids:
                    try:
                        problem_data = all_problems[example_id]
                        problem_text = problem_data.get("problem", "")

                        # Build prompt
                        full_prompt = build_full_prompt(
                            universal_prefix,
                            problem_text,
                            output_format
                        )

                        # Call model
                        model_result = call_model(model, full_prompt, max_tokens=None)

                        reasoning_trace = model_result["reasoning_trace"]
                        model_metadata = model_result["metadata"]

                        # Split reasoning and code
                        reasoning_before_code, extracted_code = split_reasoning_and_code(
                            reasoning_trace
                        )

                        # Execute code
                        if extracted_code:
                            code_result = run_code(extracted_code, timeout_sec=30.0)
                        else:
                            code_result = {
                                "ran": False,
                                "exit_code": None,
                                "stdout": "",
                                "stderr": "",
                                "timed_out": False,
                                "timeout_sec": 30.0,
                                "error": "no code extracted",
                                "parsed_output": None,
                            }

                        # Write result
                        example_result = {
                            "example_id": example_id,
                            "problem_text": problem_text,
                            "reasoning_trace": reasoning_trace,
                            "reasoning_before_code": reasoning_before_code,
                            "extracted_code": extracted_code,
                            "code_execution": code_result,
                            "model_metadata": model_metadata,
                        }

                        writer.write_example(example_result)

                        if code_result.get("exit_code") == 0:
                            success_count += 1
                        else:
                            error_count += 1

                    except Exception as e:
                        error_count += 1

                        error_result = {
                            "example_id": example_id,
                            "problem_text": all_problems[example_id].get("problem", ""),
                            "reasoning_trace": "",
                            "reasoning_before_code": "",
                            "extracted_code": "",
                            "code_execution": {
                                "ran": False,
                                "exit_code": None,
                                "stdout": "",
                                "stderr": "",
                                "timed_out": False,
                                "timeout_sec": 30.0,
                                "error": f"test error: {str(e)}",
                                "parsed_output": None,
                            },
                            "model_metadata": {},
                        }
                        writer.write_example(error_result)

                    progress.update(1)
                    progress.set_postfix(success=success_count, errors=error_count)

        print(f"\n✓ {task} test complete: {success_count} success, {error_count} errors")
        print(f"  Output: {output_path}")

    print(f"\n{'='*60}")
    print(f"SMOKE TEST COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Smoke test for inference")
    parser.add_argument(
        "--model",
        default="deepseek",
        choices=["deepseek", "qwen", "gpt"],
        help="Model to test (default: deepseek)"
    )
    parser.add_argument(
        "--n",
        type=int,
        default=3,
        help="Number of examples per task (default: 3)"
    )

    args = parser.parse_args()

    try:
        run_smoke_test_inference(model=args.model, num_per_task=args.n)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
