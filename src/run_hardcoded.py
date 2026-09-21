#!/usr/bin/env python3
"""
Hardcoded Detection Pipeline

This script judges whether extracted code is hardcoded or computational using
Gemini via Vertex AI Batch API (or sequential mode).

Usage:
    # Batch mode (default, fast)
    python src/run_hardcoded.py \
        --input output/gpt/meeting/baseline_execution.json \
        --judge-prompt prompts/judge/judge_prompt_hardcoded.txt

    # Sequential mode (slower, no GCS needed)
    python src/run_hardcoded.py \
        --input output/gpt/meeting/baseline_execution.json \
        --judge-prompt prompts/judge/judge_prompt_hardcoded.txt \
        --sequential
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, save_json_output
from hardcoded.batch_judge import (
    prepare_batch_requests,
    run_batch_judging,
    run_sequential_judging
)


def run_batch_pipeline(execution_json_path: str, judge_prompt_path: str):
    """Run batch hardcoded detection pipeline."""

    print("="*80)
    print("HARDCODED DETECTION - BATCH MODE")
    print("="*80)
    print(f"Input: {execution_json_path}")
    print(f"Judge prompt: {judge_prompt_path}")
    print()

    # Load inputs
    print("Loading execution data...")
    execution_data = load_json_file(execution_json_path)

    with open(judge_prompt_path, 'r') as f:
        judge_prompt = f.read()

    # Prepare batch requests
    print("\nPreparing batch requests...")
    requests = prepare_batch_requests(execution_data, judge_prompt)
    print(f"  Total examples to judge: {len(requests)}")

    if len(requests) == 0:
        print("No examples to judge")
        return

    # Run batch judging
    results = run_batch_judging(
        requests=requests,
        job_display_name=f"hardcoded_judge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    # Build output
    output = {
        "run_metadata": {
            "execution_file": execution_json_path,
            "judge_prompt": judge_prompt_path,
            "mode": "batch",
            "timestamp": datetime.now().isoformat(),
            "total_examples": len(requests)
        },
        "examples": []
    }

    # Map results back to include code traces
    example_map = {ex['example_id']: ex for ex in execution_data.get('examples', [])}

    for result in results:
        example_id = result['example_id']
        example = example_map.get(example_id, {})

        output["examples"].append({
            "example_id": example_id,
            "extracted_code": example.get('extracted_code', ''),
            "hardcoded": result['hardcoded'],
            "error": result.get('error'),
            "raw_response": result['raw_response']
        })

    # Derive output path
    exec_path = Path(execution_json_path)
    output_path = exec_path.parent / exec_path.name.replace('_execution.json', '_hardcoded.json')

    save_json_output(output, str(output_path))
    print(f"\n✓ Saved results to: {output_path}")

    # Summary
    hardcoded_count = sum(1 for ex in output["examples"] if ex['hardcoded'] is True)
    computational_count = sum(1 for ex in output["examples"] if ex['hardcoded'] is False)
    error_count = sum(1 for ex in output["examples"] if ex['hardcoded'] is None)

    print("\nSummary:")
    print(f"  Hardcoded: {hardcoded_count}")
    print(f"  Computational: {computational_count}")
    print(f"  Errors: {error_count}")


def run_sequential_pipeline(execution_json_path: str, judge_prompt_path: str):
    """Run sequential hardcoded detection pipeline."""

    print("="*80)
    print("HARDCODED DETECTION - SEQUENTIAL MODE")
    print("="*80)
    print(f"Input: {execution_json_path}")
    print(f"Judge prompt: {judge_prompt_path}")
    print()

    # Load inputs
    print("Loading execution data...")
    execution_data = load_json_file(execution_json_path)

    with open(judge_prompt_path, 'r') as f:
        judge_prompt = f.read()

    # Prepare requests
    print("\nPreparing requests...")
    requests = prepare_batch_requests(execution_data, judge_prompt)
    print(f"  Total examples to judge: {len(requests)}")

    if len(requests) == 0:
        print("No examples to judge")
        return

    # Run sequential judging
    results = run_sequential_judging(requests, judge_prompt)

    # Build output
    output = {
        "run_metadata": {
            "execution_file": execution_json_path,
            "judge_prompt": judge_prompt_path,
            "mode": "sequential",
            "timestamp": datetime.now().isoformat(),
            "total_examples": len(requests)
        },
        "examples": []
    }

    # Map results back to include code traces
    example_map = {ex['example_id']: ex for ex in execution_data.get('examples', [])}

    for result in results:
        example_id = result['example_id']
        example = example_map.get(example_id, {})

        output["examples"].append({
            "example_id": example_id,
            "extracted_code": example.get('extracted_code', ''),
            "hardcoded": result['hardcoded'],
            "error": result.get('error'),
            "raw_response": result['raw_response']
        })

    # Derive output path
    exec_path = Path(execution_json_path)
    output_path = exec_path.parent / exec_path.name.replace('_execution.json', '_hardcoded.json')

    save_json_output(output, str(output_path))
    print(f"\n✓ Saved results to: {output_path}")

    # Summary
    hardcoded_count = sum(1 for ex in output["examples"] if ex['hardcoded'] is True)
    computational_count = sum(1 for ex in output["examples"] if ex['hardcoded'] is False)
    error_count = sum(1 for ex in output["examples"] if ex['hardcoded'] is None)

    print("\nSummary:")
    print(f"  Hardcoded: {hardcoded_count}")
    print(f"  Computational: {computational_count}")
    print(f"  Errors: {error_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Detect hardcoded vs computational solutions using Gemini judge"
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to execution JSON file'
    )
    parser.add_argument(
        '--judge-prompt',
        required=True,
        help='Path to judge prompt template'
    )
    parser.add_argument(
        '--sequential',
        action='store_true',
        help='Use sequential mode instead of batch (slower)'
    )

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    if not Path(args.judge_prompt).exists():
        print(f"Error: Judge prompt not found: {args.judge_prompt}")
        sys.exit(1)

    if args.sequential:
        run_sequential_pipeline(args.input, args.judge_prompt)
    else:
        run_batch_pipeline(args.input, args.judge_prompt)


if __name__ == '__main__':
    main()
