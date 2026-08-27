#!/usr/bin/env python3
"""
Prepare test data: extract first 5 examples from execution JSON.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from general.io_utils import load_json_file


def prepare_test_data(execution_json_path: str, output_path: str, n: int = 5):
    """
    Extract first N examples from execution JSON for testing.

    Args:
        execution_json_path: Path to full execution JSON
        output_path: Path to write test subset
        n: Number of examples to extract (default 5)
    """
    print(f"Loading {execution_json_path}...")
    data = load_json_file(execution_json_path)

    # Extract first N examples
    test_data = {
        "run_metadata": data["run_metadata"].copy(),
        "examples": data["examples"][:n],
    }

    # Update metadata
    test_data["run_metadata"]["num_examples"] = n
    test_data["run_metadata"]["test_subset"] = True
    test_data["run_metadata"]["original_file"] = execution_json_path

    # Write test data
    print(f"Writing {n} examples to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Test data prepared: {n} examples")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare test data subset")
    parser.add_argument("--input", required=True, help="Full execution JSON path")
    parser.add_argument("--output", required=True, help="Output path for test subset")
    parser.add_argument("--n", type=int, default=5, help="Number of examples (default 5)")

    args = parser.parse_args()

    prepare_test_data(args.input, args.output, args.n)
