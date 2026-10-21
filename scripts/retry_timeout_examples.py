#!/usr/bin/env python3
"""
Retry execution for examples that had timeout errors.

This script:
1. Loads an execution JSON
2. Identifies examples with timeout errors
3. Re-runs code execution for those examples
4. Writes updated execution JSON
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from inference.code_executor_pddl import run_pddl_code
from general.io_utils import load_json_file
from general.cli import ProgressTracker


def retry_timeout_examples(execution_json_path: str, output_path: str = None):
    """
    Retry examples that had timeout errors.

    Args:
        execution_json_path: Path to execution JSON with timeouts
        output_path: Optional output path (defaults to modifying input file in-place)
    """
    print(f"\n=== Retrying Timeout Examples ===")
    print(f"Input: {execution_json_path}\n")

    # Load execution data
    data = load_json_file(execution_json_path)

    # Find timeout examples
    timeout_examples = []
    for example in data["examples"]:
        code_execution = example.get("code_execution", {})
        stderr = code_execution.get("stderr", "")

        is_timeout = (
            "Read timed out" in stderr or
            "SOLVER_TIMEOUT" in stderr or
            "timeout" in stderr.lower()
        )

        if is_timeout:
            timeout_examples.append(example)

    print(f"Found {len(timeout_examples)} examples with timeout errors")

    if not timeout_examples:
        print("✓ No timeout examples to retry")
        return

    # Retry each timeout example
    retry_count = 0
    success_count = 0

    with ProgressTracker(len(timeout_examples), "Retrying timeouts") as progress:
        for example in timeout_examples:
            example_id = example["example_id"]
            extracted_code = example.get("extracted_code", "")

            # Re-run PDDL execution
            try:
                result = run_pddl_code(
                    extracted_code,
                    timeout_sec=120.0,  # Longer timeout
                    use_online_solver=True,
                )

                # Update execution result
                example["code_execution"] = result

                # Check if retry succeeded
                stderr = result.get("stderr", "")
                is_still_timeout = "timeout" in stderr.lower() or "SOLVER_TIMEOUT" in stderr

                if not is_still_timeout and result.get("ran"):
                    success_count += 1

                retry_count += 1

            except Exception as e:
                print(f"\n  ⚠ Error retrying {example_id}: {str(e)}")

            progress.update(1)

    # Determine output path (default: modify in-place)
    if output_path is None:
        output_path = execution_json_path

    # Write updated data
    print(f"\nWriting updated execution JSON...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Retry complete!")
    print(f"  Retried: {retry_count}")
    print(f"  Succeeded: {success_count}")
    print(f"  Still failing: {retry_count - success_count}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Retry examples with timeout errors")
    parser.add_argument("--input", required=True, help="Execution JSON with timeouts")
    parser.add_argument("--output", help="Output path (default: modify input file in-place)")

    args = parser.parse_args()

    retry_timeout_examples(args.input, args.output)
