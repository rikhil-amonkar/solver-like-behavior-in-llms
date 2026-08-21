#!/usr/bin/env python3
"""
One-time script to fix parsed_output in zebralogic inference JSON.

Reads baseline_inference.json, parses stdout using zebralogic parser,
and writes parsed_output back into the JSON without changing anything else.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from general.parsing_utils import parse_zebralogic_grid_output


def fix_inference_json(input_path: str):
    """
    Fix parsed_output field in zebralogic inference JSON.

    Args:
        input_path: Path to inference JSON file
    """
    print(f"Loading: {input_path}")

    with open(input_path, 'r') as f:
        data = json.load(f)

    # Load problem data to get headers
    task = data["run_metadata"]["task"]
    problems_path = f"data/problems/{task}_grid_100.json"

    print(f"Loading problems from: {problems_path}")
    with open(problems_path, 'r') as f:
        problems = json.load(f)

    total = len(data["examples"])
    fixed_count = 0

    print(f"Processing {total} examples...")

    for example in data["examples"]:
        example_id = example["example_id"]

        # Get headers from problem data
        problem = problems.get(example_id, {})
        headers = problem.get("headers", problem.get("header", []))
        if not headers and "golden_solution" in problem:
            headers = problem["golden_solution"].get("header", problem["golden_solution"].get("headers", []))

        if not headers:
            print(f"  ⚠ {example_id}: No headers found, skipping")
            continue

        # Parse stdout
        stdout = example["code_execution"].get("stdout", "")
        if not stdout or not stdout.strip():
            continue

        # Parse with zebralogic parser
        parsed_output, parse_error = parse_zebralogic_grid_output(stdout, headers)

        if parsed_output:
            example["code_execution"]["parsed_output"] = parsed_output
            fixed_count += 1
        else:
            print(f"  ⚠ {example_id}: Parse failed - {parse_error}")

    print(f"\nFixed {fixed_count}/{total} examples")

    # Write back
    output_path = input_path
    print(f"Writing to: {output_path}")

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print("✓ Done!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_zebralogic_parsed_output.py <inference_json_path>")
        sys.exit(1)

    fix_inference_json(sys.argv[1])
