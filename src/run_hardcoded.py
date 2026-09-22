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
import os
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, save_json_output, get_timestamp
from hardcoded.batch_judge import (
    prepare_batch_examples,
    run_batch_judging,
    run_sequential_judging
)


def run_batch_pipeline(execution_json_path: str, judge_prompt_path: str, gcs_bucket: str):
    """Run batch hardcoded detection pipeline."""

    print("="*80)
    print("HARDCODED DETECTION - BATCH MODE")
    print("="*80)
    print(f"Input: {execution_json_path}")
    print(f"Judge prompt: {judge_prompt_path}")
    print(f"GCS bucket: {gcs_bucket}")
    print()

    # Load inputs
    print("Loading execution data...")
    execution_data = load_json_file(execution_json_path)

    with open(judge_prompt_path, 'r') as f:
        judge_prompt = f.read()

    # Prepare examples for batch judging
    print("\nPreparing batch requests...")
    examples = prepare_batch_examples(execution_data)
    print(f"  Total examples to judge: {len(examples)}")

    if len(examples) == 0:
        print("No examples to judge")
        return

    # Setup GCS paths
    timestamp = get_timestamp()
    exec_path = Path(execution_json_path)
    model = execution_data["run_metadata"]["model"]
    task = execution_data["run_metadata"]["task"]
    condition = execution_data["run_metadata"].get("condition", "baseline")

    gcs_prefix = f"hardcoded-judge/{model}/{task}/{condition}/{timestamp}"
    input_gcs_uri = f"gs://{gcs_bucket}/{gcs_prefix}/input.jsonl"
    output_gcs_uri_prefix = f"gs://{gcs_bucket}/{gcs_prefix}/output"

    print(f"\nGCS paths:")
    print(f"  Input: {input_gcs_uri}")
    print(f"  Output: {output_gcs_uri_prefix}")

    # Run batch judging
    results = run_batch_judging(
        examples=examples,
        judge_prompt=judge_prompt,
        input_gcs_uri=input_gcs_uri,
        output_gcs_uri_prefix=output_gcs_uri_prefix,
        display_name=f"hardcoded-{model}-{task}-{condition}"
    )

    # Build output
    output = {
        "run_metadata": {
            "execution_file": execution_json_path,
            "judge_prompt": judge_prompt_path,
            "mode": "batch",
            "timestamp": timestamp,
            "total_examples": len(examples)
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

    # Prepare examples
    print("\nPreparing requests...")
    examples = prepare_batch_examples(execution_data)
    print(f"  Total examples to judge: {len(examples)}")

    if len(examples) == 0:
        print("No examples to judge")
        return

    # Convert examples to request format for sequential judging
    requests = []
    for ex in examples:
        full_prompt = judge_prompt + "\n\n```python\n" + ex['code'] + "\n```"
        requests.append({
            "example_id": ex['example_id'],
            "request": {
                "contents": full_prompt
            }
        })

    # Run sequential judging
    results = run_sequential_judging(requests, judge_prompt)

    # Build output
    output = {
        "run_metadata": {
            "execution_file": execution_json_path,
            "judge_prompt": judge_prompt_path,
            "mode": "sequential",
            "timestamp": datetime.now().isoformat(),
            "total_examples": len(examples)
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
    parser.add_argument(
        '--gcs-bucket',
        help='GCS bucket name for batch I/O (required for batch mode, ignored for sequential)'
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
        # Batch mode - GCS required
        gcs_bucket = args.gcs_bucket or os.getenv("JUDGE_VERTEX_GCS_BUCKET")

        if not gcs_bucket:
            print("❌ ERROR: --gcs-bucket is required for batch mode")
            print("   Either:")
            print("   1. Provide --gcs-bucket your-bucket")
            print("   2. Set JUDGE_VERTEX_GCS_BUCKET in .env")
            print("   3. Use --sequential flag (no GCS needed)")
            sys.exit(1)

        run_batch_pipeline(args.input, args.judge_prompt, gcs_bucket)


if __name__ == '__main__':
    main()
