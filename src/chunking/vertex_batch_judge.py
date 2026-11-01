"""
Vertex AI Batch API helper for judge model.

Provides a cleaner way to call Gemini judge using Google Cloud Vertex AI
batch prediction for processing many examples efficiently.
"""

from google import genai
from google.genai import types
import os
import json
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_vertex_client() -> genai.Client:
    """
    Initialize Vertex AI client for Gemini.

    Requires environment variables:
    - GOOGLE_CLOUD_PROJECT: GCP project ID
    - GOOGLE_CLOUD_LOCATION: Region (e.g., 'us-central1')
    - GOOGLE_APPLICATION_CREDENTIALS: Path to service account key JSON (optional if using default credentials)
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not project_id:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT environment variable not set.\n"
            "Set it in your .env file or export it:\n"
            "  export GOOGLE_CLOUD_PROJECT=your-project-id"
        )

    # Check credentials
    if creds_path and not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"GOOGLE_APPLICATION_CREDENTIALS points to non-existent file: {creds_path}\n"
            "Ensure the service account key JSON exists or unset this variable to use default credentials."
        )

    try:
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )
        return client
    except Exception as e:
        error_msg = str(e)
        if "DefaultCredentialsError" in type(e).__name__ or "default credentials" in error_msg.lower():
            raise RuntimeError(
                f"❌ Google Cloud authentication not configured.\n\n"
                f"To use Vertex AI for chunking, you need to set up Application Default Credentials (ADC).\n\n"
                f"Choose ONE of the following methods:\n\n"
                f"1. Use gcloud CLI (recommended for development):\n"
                f"   $ gcloud auth application-default login\n"
                f"   $ gcloud config set project {project_id}\n\n"
                f"2. Use a service account key:\n"
                f"   - Download JSON key from Google Cloud Console\n"
                f"   - Add to .env: GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json\n\n"
                f"3. For testing/development without Vertex AI:\n"
                f"   - You can skip chunking tests until credentials are configured\n\n"
                f"More info: https://cloud.google.com/docs/authentication/provide-credentials-adc\n"
            ) from e
        else:
            raise RuntimeError(
                f"Failed to initialize Vertex AI client:\n"
                f"  Error: {str(e)}\n"
                f"  Project: {project_id}\n"
                f"  Location: {location}\n"
                f"  Credentials: {creds_path or 'default'}\n"
                "Ensure you have proper Google Cloud authentication configured."
            ) from e


def call_vertex_judge(
    reasoning_text: str,
    judge_prompt: str,
    model_id: str = None,
    max_output_tokens: int = None,
    temperature: float = 0.0,
    timeout: int = 180,
    max_retries: int = 5
) -> dict:
    """
    Call Gemini judge via Vertex AI for a single reasoning trace.

    Args:
        reasoning_text: The reasoning trace to classify
        judge_prompt: System/instruction prompt for the judge
        model_id: Gemini model ID (defaults to VERTEX_JUDGE_BATCH_MODEL from .env)
        max_output_tokens: Max tokens for judge response (defaults to MAX_JUDGE_TOKENS from .env)
        temperature: Sampling temperature (0 = deterministic)
        timeout: Timeout in seconds (default 180s)
        max_retries: Maximum retry attempts on timeout/transient errors (default 5)

    Returns:
        dict with: response_text, metadata (tokens, finish_reason, etc.)
    """
    import time as time_module

    client = get_vertex_client()

    # Use model from env if not specified
    if model_id is None:
        model_id = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")

    # Use token limit from env for long chunking outputs
    if max_output_tokens is None:
        max_output_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    # Combine judge prompt with reasoning text
    full_prompt = f"{judge_prompt}\n\n{reasoning_text}"

    # Retry loop with exponential backoff
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    response_mime_type="application/json",  # Force JSON output
                )
            )

            response_text = response.text if response.text else ""
            finish_reason = str(response.candidates[0].finish_reason) if response.candidates else None

            # Check if response was truncated at max tokens
            if finish_reason == "FinishReason.MAX_TOKENS":
                print(f"   ⚠ Warning: Judge response hit MAX_TOKENS limit ({max_output_tokens})")
                print(f"      Response may be incomplete. Consider splitting this reasoning trace.")

            return {
                "response_text": response_text,
                "metadata": {
                    "model": model_id,
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                    "finish_reason": finish_reason,
                    "attempts": attempt + 1,
                }
            }

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            error_type = type(e).__name__

            # Check if this is a retryable error
            is_timeout = "timeout" in error_msg or "timed out" in error_msg or "ReadTimeout" in error_type
            is_rate_limit = any(keyword in error_msg for keyword in [
                "429", "rate limit", "resource_exhausted", "quota"
            ])
            is_transient = any(keyword in error_msg for keyword in [
                "deadline", "unavailable", "503", "500", "internal error"
            ])

            # Special handling for rate limits - longer backoff
            if is_rate_limit and attempt < max_retries - 1:
                # Aggressive backoff for rate limits: 10s, 30s, 60s, 120s, 240s
                backoff_time = min(10 * (3 ** attempt), 300)  # Cap at 5 minutes
                print(f"   ⚠ Rate limit hit (attempt {attempt + 1}/{max_retries}), retrying in {backoff_time}s...")
                time_module.sleep(backoff_time)
                continue

            # Don't retry on hard quota exceeded
            if "quota" in error_msg and "exceeded" in error_msg and "resource_exhausted" not in error_msg:
                raise RuntimeError(f"Vertex AI quota exceeded: {error_msg}") from e
            elif "permission" in error_msg or "forbidden" in error_msg:
                raise RuntimeError(f"Vertex AI permission denied: {error_msg}") from e

            # Retry on timeout or transient errors
            if (is_timeout or is_transient) and attempt < max_retries - 1:
                # Exponential backoff: 5s, 10s, 20s, 40s, 80s
                backoff_time = min(5 * (2 ** attempt), 120)  # Cap at 2 minutes
                print(f"   ⚠ Attempt {attempt + 1}/{max_retries} failed ({error_type}), retrying in {backoff_time}s...")
                time_module.sleep(backoff_time)
                continue
            else:
                # Final attempt failed or non-retryable error
                if is_timeout:
                    raise TimeoutError(
                        f"Vertex AI judge call timed out after {max_retries} attempts. "
                        f"Last error: {error_msg}"
                    ) from e
                else:
                    raise

    # Should never reach here, but just in case
    raise last_error if last_error else RuntimeError("Unknown error in call_vertex_judge")


def prepare_batch_requests(
    examples: list[dict],
    judge_prompt: str,
    max_output_tokens: int = None,
    temperature: float = 0.0
) -> list[dict]:
    """
    Prepare batch prediction requests for Vertex AI JSONL format.

    Args:
        examples: List of dicts with 'example_id' and 'reasoning_text'
        judge_prompt: The judge prompt to use
        max_output_tokens: Max tokens per response (defaults to MAX_JUDGE_TOKENS from .env)
        temperature: Sampling temperature

    Returns:
        List of request dicts in JSONL format for batch API
    """
    if max_output_tokens is None:
        max_output_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    requests = []
    for example in examples:
        full_prompt = f"{judge_prompt}\n\n{example['reasoning_text']}"

        # Vertex AI batch JSONL format
        request = {
            "request": {
                "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_output_tokens,
                    "responseMimeType": "application/json",
                }
            }
        }

        requests.append(request)

    return requests


def submit_batch_job(
    requests: list[dict],
    input_gcs_uri: str,
    output_gcs_uri_prefix: str,
    model_id: str = None,
    display_name: str = None
) -> types.BatchJob:
    """
    Submit batch prediction job to Vertex AI using google-genai SDK.

    Args:
        requests: List of request dicts (from prepare_batch_requests)
        input_gcs_uri: GCS URI where requests JSONL will be uploaded
        output_gcs_uri_prefix: GCS URI prefix for output results
        model_id: Gemini model ID (defaults to VERTEX_JUDGE_BATCH_MODEL from .env)
        display_name: Optional display name for the job

    Returns:
        BatchJob object with job details (name, state, etc.)
    """
    from .gcs_utils import upload_jsonl_to_gcs

    # Upload requests to GCS
    upload_jsonl_to_gcs(requests, input_gcs_uri)

    # Get client
    client = get_vertex_client()

    # Use model from env if not specified
    if model_id is None:
        model_id = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")

    # Create batch job
    config = types.CreateBatchJobConfig(
        dest=output_gcs_uri_prefix,
        display_name=display_name or f"judge-batch-{get_timestamp()}"
    )

    batch_job = client.batches.create(
        model=model_id,
        src=input_gcs_uri,
        config=config
    )

    return batch_job


def get_timestamp() -> str:
    """Get ISO timestamp for naming."""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def poll_batch_job(batch_job_name: str, poll_interval: int = 30, max_wait: int = 2592000) -> types.BatchJob:
    """
    Poll batch job until complete.

    Args:
        batch_job_name: Name of batch job (from BatchJob.name)
        poll_interval: Seconds between polls (default 30s)
        max_wait: Max seconds to wait (default 30 days)

    Returns:
        Final BatchJob object

    Raises:
        TimeoutError: If job doesn't complete within max_wait
        RuntimeError: If job fails
    """
    import time
    from datetime import datetime

    client = get_vertex_client()
    start_time = time.time()
    poll_count = 0

    while True:
        batch_job = client.batches.get(name=batch_job_name)

        state = batch_job.state
        poll_count += 1
        elapsed = time.time() - start_time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)

        # Print progress update
        print(f"  [{elapsed_min:02d}:{elapsed_sec:02d}] Poll #{poll_count}: {state}", end="")

        # Try to get progress info if available
        if hasattr(batch_job, 'model_monitoring_stats') and batch_job.model_monitoring_stats:
            stats = batch_job.model_monitoring_stats
            if hasattr(stats, 'completed_count') and hasattr(stats, 'total_count'):
                print(f" ({stats.completed_count}/{stats.total_count} completed)", end="")

        print()  # Newline

        # Check terminal states
        if state == types.JobState.JOB_STATE_SUCCEEDED:
            return batch_job
        elif state == types.JobState.JOB_STATE_FAILED:
            error_msg = str(batch_job.error) if batch_job.error else "Unknown error"
            raise RuntimeError(f"Batch job failed: {error_msg}")
        elif state == types.JobState.JOB_STATE_CANCELLED:
            raise RuntimeError("Batch job was cancelled")

        # Check timeout
        if elapsed > max_wait:
            raise TimeoutError(
                f"Batch job did not complete within {max_wait}s. "
                f"Current state: {state}"
            )

        # Wait before next poll
        time.sleep(poll_interval)


def parse_batch_results(output_gcs_uri_prefix: str) -> list[dict]:
    """
    Parse results from completed batch job.

    Args:
        output_gcs_uri_prefix: GCS URI prefix where results were written

    Returns:
        List of response dicts with 'response' containing the judge output text
    """
    from .gcs_utils import list_gcs_blobs, download_jsonl_from_gcs

    # List all output files (Vertex AI writes multiple shards)
    output_files = list_gcs_blobs(output_gcs_uri_prefix)

    if not output_files:
        raise ValueError(f"No output files found at {output_gcs_uri_prefix}")

    # Download and parse all JSONL files
    all_results = []
    for file_uri in output_files:
        # Skip metadata files
        if "metadata" in file_uri or file_uri.endswith("/"):
            continue

        results = download_jsonl_from_gcs(file_uri)
        all_results.extend(results)

    return all_results


def _prompt_text(request: dict) -> str:
    """Concatenated text parts of a generateContent request."""
    return "".join(
        part.get("text", "")
        for content in request.get("contents", [])
        for part in content.get("parts", [])
    )


def match_batch_results(raw_results: list[dict], requests: list[dict], request_ids: list[str]) -> dict:
    """
    Match batch output lines to the requests they answer.

    Vertex AI does not keep input order in batch output, so results must not be
    matched by position. Each output line echoes its request, so we match on the
    request's prompt text. Identical prompts are interchangeable.

    Args:
        raw_results: Output lines from parse_batch_results
        requests: Request dicts as submitted (from prepare_batch_requests)
        request_ids: ID for each request, in the same order as requests

    Returns:
        Dict mapping request ID to its output line (IDs with no output are absent)
    """
    ids_by_prompt = {}
    for request_id, request in zip(request_ids, requests):
        ids_by_prompt.setdefault(_prompt_text(request["request"]), []).append(request_id)

    matched = {}
    for result in raw_results:
        if "request" not in result:
            raise ValueError("Batch output line has no 'request' field; cannot match it to an example")
        pending = ids_by_prompt.get(_prompt_text(result["request"]))
        if not pending:
            raise ValueError("Batch output line does not match any submitted request")
        matched[pending.pop(0)] = result
    return matched


def batch_response_text(result: dict) -> str:
    """Judge output text from one batch output line ('' if missing)."""
    candidates = result.get("response", {}).get("candidates", [])
    if candidates and "parts" in candidates[0].get("content", {}):
        return candidates[0]["content"]["parts"][0].get("text", "")
    return ""


if __name__ == "__main__":
    # Test single call
    print("Testing Vertex AI judge call...")

    test_reasoning = """
    This is a calendar scheduling problem. I need to find a time that works
    for both participants. Let me check the constraints...
    """

    test_prompt = "Classify this reasoning trace as sound or solver-like."

    try:
        result = call_vertex_judge(test_reasoning, test_prompt)
        print(f"Response: {result['response_text'][:200]}...")
        print(f"Metadata: {result['metadata']}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure GOOGLE_CLOUD_PROJECT is set in .env")
