#!/usr/bin/env python3
"""
Hardcoded Judge Validation Script

This script validates the hardcoded judge by testing it against curated examples
in hardcoded_and_not_samples.json and reporting accuracy.

Usage:
    python tests/hardcoded/validate_judge.py \
        --samples tests/hardcoded/hardcoded_and_not_samples.json \
        --judge-prompt prompts/judge/judge_prompt_hardcoded.txt \
        [--sequential]
"""

import json
import sys
import argparse
from pathlib import Path
import os
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from hardcoded.judge_parser import parse_judge_response
from chunking.vertex_batch_judge import get_vertex_client
from google.genai import types
from tqdm import tqdm


def validate_judge(samples_path: str, judge_prompt_path: str):
    """
    Validate judge against curated samples.

    Args:
        samples_path: Path to hardcoded_and_not_samples.json
        judge_prompt_path: Path to judge prompt
    """
    print("="*80)
    print("HARDCODED JUDGE VALIDATION")
    print("="*80)
    print(f"Samples: {samples_path}")
    print(f"Judge prompt: {judge_prompt_path}")
    print()

    # Load samples
    print("Loading samples...")
    with open(samples_path, 'r') as f:
        samples_data = json.load(f)

    with open(judge_prompt_path, 'r') as f:
        judge_prompt = f.read()

    # Initialize Gemini client using same method as chunking
    client = get_vertex_client()

    # Get model from environment (same as chunking pipeline)
    model_id = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")
    print(f"Using model: {model_id}")
    print()

    # Collect all test cases
    test_cases = []

    for example in samples_data.get('hardcoded_examples', []):
        test_cases.append({
            'example_id': example['example_id'],
            'code': example['extracted_code'],
            'expected': True
        })

    for example in samples_data.get('non_hardcoded_examples', []):
        test_cases.append({
            'example_id': example['example_id'],
            'code': example['extracted_code'],
            'expected': False
        })

    print(f"Total test cases: {len(test_cases)}")
    print(f"  Hardcoded examples: {len(samples_data.get('hardcoded_examples', []))}")
    print(f"  Computational examples: {len(samples_data.get('non_hardcoded_examples', []))}")
    print()

    # Judge each example
    results = []
    correct = 0
    incorrect = 0
    errors = 0

    # Rate limiting: 2.5 seconds between requests (24 RPM)
    last_request_time = 0
    min_request_interval = 2.5

    for case in tqdm(test_cases, desc="Validating"):
        example_id = case['example_id']
        code = case['code']
        expected = case['expected']

        # Rate limiting
        time_since_last_request = time.time() - last_request_time
        if last_request_time > 0 and time_since_last_request < min_request_interval:
            sleep_time = min_request_interval - time_since_last_request
            time.sleep(sleep_time)

        # Build prompt
        full_prompt = judge_prompt + "\n\n```python\n" + code + "\n```"

        # Retry loop with exponential backoff for rate limit errors
        max_retries = 3
        retry_delay = 5  # Start with 5 second delay

        for attempt in range(max_retries):
            try:
                last_request_time = time.time()
                response = client.models.generate_content(
                    model=model_id,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=8192,
                        response_mime_type="application/json",
                    )
                )
                response_text = response.text if response.text else ""

                parsed = parse_judge_response(response_text)
                predicted = parsed.get('hardcoded')

                if predicted is None:
                    errors += 1
                    results.append({
                        'example_id': example_id,
                        'expected': expected,
                        'predicted': None,
                        'correct': False,
                        'error': parsed.get('error', 'Unknown error')
                    })
                elif predicted == expected:
                    correct += 1
                    results.append({
                        'example_id': example_id,
                        'expected': expected,
                        'predicted': predicted,
                        'correct': True,
                        'error': None
                    })
                else:
                    incorrect += 1
                    results.append({
                        'example_id': example_id,
                        'expected': expected,
                        'predicted': predicted,
                        'correct': False,
                        'error': None
                    })

                break  # Success, exit retry loop

            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    if attempt < max_retries - 1:
                        # Wait with exponential backoff
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Double the delay for next attempt
                        continue  # Retry
                    else:
                        # Final attempt failed
                        errors += 1
                        results.append({
                            'example_id': example_id,
                            'expected': expected,
                            'predicted': None,
                            'correct': False,
                            'error': f"API error after {max_retries} retries: {error_str}"
                        })
                        break
                else:
                    # Non-rate-limit error, don't retry
                    errors += 1
                    results.append({
                        'example_id': example_id,
                        'expected': expected,
                        'predicted': None,
                        'correct': False,
                        'error': f"API error: {error_str}"
                    })
                    break

    # Print summary
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    print(f"Total test cases: {len(test_cases)}")
    print(f"Correct predictions: {correct} ({100*correct/len(test_cases):.1f}%)")
    print(f"Incorrect predictions: {incorrect} ({100*incorrect/len(test_cases):.1f}%)")
    print(f"Errors: {errors} ({100*errors/len(test_cases):.1f}%)")
    print()

    # Show incorrect predictions
    if incorrect > 0:
        print("Incorrect predictions:")
        for result in results:
            if not result['correct'] and result['predicted'] is not None:
                expected_label = "hardcoded" if result['expected'] else "computational"
                predicted_label = "hardcoded" if result['predicted'] else "computational"
                print(f"  {result['example_id']}: expected {expected_label}, got {predicted_label}")
        print()

    # Show errors
    if errors > 0:
        print("Errors:")
        for result in results:
            if result['predicted'] is None:
                print(f"  {result['example_id']}: {result['error']}")
        print()

    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Validate hardcoded judge against curated samples"
    )
    parser.add_argument(
        '--samples',
        required=True,
        help='Path to hardcoded_and_not_samples.json'
    )
    parser.add_argument(
        '--judge-prompt',
        required=True,
        help='Path to judge prompt template'
    )

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.samples).exists():
        print(f"Error: Samples file not found: {args.samples}")
        sys.exit(1)

    if not Path(args.judge_prompt).exists():
        print(f"Error: Judge prompt not found: {args.judge_prompt}")
        sys.exit(1)

    validate_judge(args.samples, args.judge_prompt)


if __name__ == '__main__':
    main()
