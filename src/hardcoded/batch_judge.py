"""Batch and sequential judging for hardcoded detection."""

import os
import time
from google.genai import types
from tqdm import tqdm

from chunking.vertex_batch_judge import (
    submit_batch_job,
    poll_batch_job,
    parse_batch_results,
    get_vertex_client
)
from hardcoded.judge_parser import parse_judge_response


def prepare_batch_requests(execution_data: dict, judge_prompt: str) -> list[dict]:
    """
    Prepare batch requests for all examples with successful code execution.

    Args:
        execution_data: Loaded execution JSON
        judge_prompt: Judge prompt template

    Returns:
        List of batch request dicts with example_id
    """
    requests = []

    for example in execution_data.get('examples', []):
        example_id = example['example_id']
        extracted_code = example.get('extracted_code', '')
        code_execution = example.get('code_execution', {})

        # Skip if no code or execution failed
        if not extracted_code:
            continue

        if code_execution.get('exit_code', 0) != 0:
            continue

        # Build full prompt
        full_prompt = judge_prompt + "\n\n```python\n" + extracted_code + "\n```"

        requests.append({
            "example_id": example_id,
            "request": {
                "contents": full_prompt
            }
        })

    return requests


def run_batch_judging(requests: list[dict], job_display_name: str) -> list[dict]:
    """
    Run batch judging via Vertex AI Batch API.

    Args:
        requests: List of request dicts with example_id and request fields
        job_display_name: Display name for the batch job

    Returns:
        List of result dicts with example_id, hardcoded, error, raw_response
    """
    print("\nSubmitting batch job...")
    job_name = submit_batch_job(
        requests=[req["request"] for req in requests],
        job_display_name=job_display_name
    )
    print(f"  Job name: {job_name}")

    # Poll for completion
    print("\nWaiting for batch job to complete...")
    state = poll_batch_job(job_name)

    if state != "JOB_STATE_SUCCEEDED":
        raise RuntimeError(f"Batch job failed with state: {state}")

    print("\n✓ Batch job completed successfully")

    # Parse results
    print("\nParsing results...")
    raw_results = parse_batch_results(job_name)
    print(f"  Parsed {len(raw_results)} results")

    # Map results back to example IDs and parse responses
    results = []
    for i, response_text in enumerate(raw_results):
        if i < len(requests):
            example_id = requests[i]['example_id']
            parsed = parse_judge_response(response_text)

            results.append({
                'example_id': example_id,
                'hardcoded': parsed.get('hardcoded'),
                'error': parsed.get('error'),
                'raw_response': response_text
            })

    return results


def run_sequential_judging(requests: list[dict], judge_prompt: str) -> list[dict]:
    """
    Run sequential judging via google.genai client.

    Args:
        requests: List of request dicts with example_id and request fields
        judge_prompt: Judge prompt template (for building full prompts)

    Returns:
        List of result dicts with example_id, hardcoded, error, raw_response
    """
    # Initialize Gemini client using same method as chunking
    client = get_vertex_client()

    # Get model from environment (same as chunking pipeline)
    model_id = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")
    max_output_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 8192))

    results = []

    # Rate limiting: 2.5 seconds between requests (24 RPM)
    last_request_time = 0
    min_request_interval = 2.5

    for req in tqdm(requests, desc="Judging examples"):
        example_id = req['example_id']
        full_prompt = req['request']['contents']

        # Rate limiting
        time_since_last_request = time.time() - last_request_time
        if last_request_time > 0 and time_since_last_request < min_request_interval:
            sleep_time = min_request_interval - time_since_last_request
            time.sleep(sleep_time)

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
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json",
                    )
                )
                response_text = response.text if response.text else ""

                parsed = parse_judge_response(response_text)

                results.append({
                    'example_id': example_id,
                    'hardcoded': parsed.get('hardcoded'),
                    'error': parsed.get('error'),
                    'raw_response': response_text
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
                        results.append({
                            'example_id': example_id,
                            'hardcoded': None,
                            'error': f"API error after {max_retries} retries: {error_str}",
                            'raw_response': None
                        })
                        break
                else:
                    # Non-rate-limit error, don't retry
                    results.append({
                        'example_id': example_id,
                        'hardcoded': None,
                        'error': f"API error: {error_str}",
                        'raw_response': None
                    })
                    break

    return results
