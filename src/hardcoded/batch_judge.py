"""Batch and sequential judging for hardcoded detection."""

import os
import time
from google.genai import types
from tqdm import tqdm

from chunking.vertex_batch_judge import (
    submit_batch_job,
    poll_batch_job,
    parse_batch_results,
    get_vertex_client,
    prepare_batch_requests as prepare_vertex_requests
)
from hardcoded.judge_parser import parse_judge_response


def prepare_batch_examples(execution_data: dict) -> list[dict]:
    """
    Prepare examples for batch judging (filter to successful executions).

    Args:
        execution_data: Loaded execution JSON

    Returns:
        List of example dicts with example_id and extracted_code
    """
    examples = []

    for example in execution_data.get('examples', []):
        example_id = example['example_id']
        extracted_code = example.get('extracted_code', '')
        code_execution = example.get('code_execution', {})

        # Skip if no code or execution failed
        if not extracted_code:
            continue

        if code_execution.get('exit_code', 0) != 0:
            continue

        examples.append({
            "example_id": example_id,
            "code": extracted_code
        })

    return examples


def run_batch_judging(
    examples: list[dict],
    judge_prompt: str,
    input_gcs_uri: str,
    output_gcs_uri_prefix: str,
    display_name: str
) -> list[dict]:
    """
    Run batch judging via Vertex AI Batch API.

    Args:
        examples: List of dicts with example_id and code
        judge_prompt: Judge prompt template
        input_gcs_uri: GCS URI for input JSONL
        output_gcs_uri_prefix: GCS URI prefix for output
        display_name: Display name for the batch job

    Returns:
        List of result dicts with example_id, hardcoded, error, raw_response
    """
    # Prepare examples in format expected by vertex batch API
    # Convert code blocks to reasoning_text format
    batch_examples = []
    for ex in examples:
        # Wrap code in markdown for judge
        code_with_markdown = f"```python\n{ex['code']}\n```"
        batch_examples.append({
            "example_id": ex['example_id'],
            "reasoning_text": code_with_markdown  # Use reasoning_text key expected by prepare_batch_requests
        })

    # Prepare batch requests using chunking infrastructure
    requests = prepare_vertex_requests(
        examples=batch_examples,
        judge_prompt=judge_prompt,
        max_output_tokens=int(os.getenv("MAX_JUDGE_TOKENS", 8192))
    )

    print(f"\nSubmitting batch job with {len(requests)} requests...")
    batch_job = submit_batch_job(
        requests=requests,
        input_gcs_uri=input_gcs_uri,
        output_gcs_uri_prefix=output_gcs_uri_prefix,
        display_name=display_name
    )
    print(f"  Job name: {batch_job.name}")
    print(f"  State: {batch_job.state}")

    # Poll for completion
    print("\nWaiting for batch job to complete...")
    print("(This may take 10-30 minutes depending on dataset size)")
    completed_job = poll_batch_job(
        batch_job_name=batch_job.name,
        poll_interval=30,
        max_wait=2592000  # 30 days max
    )

    print(f"\n✓ Batch job completed!")
    print(f"  Duration: {(completed_job.end_time - completed_job.start_time).total_seconds():.0f}s")

    # Parse results
    print("\nDownloading batch results from GCS...")
    raw_results = parse_batch_results(output_gcs_uri_prefix)
    print(f"  Retrieved {len(raw_results)} responses")

    # Map results back to example IDs and parse responses
    results = []
    for i, result in enumerate(raw_results):
        if i >= len(examples):
            break

        example_id = examples[i]['example_id']

        # Extract response text from Vertex AI format
        response_text = ""
        if "response" in result and "candidates" in result["response"]:
            candidate = result["response"]["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                response_text = candidate["content"]["parts"][0].get("text", "")

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
