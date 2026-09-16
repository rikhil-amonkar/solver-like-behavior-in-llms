"""
Vertex AI Batch API helper for categorization judge model.

Similar to vertex_batch_judge.py but for categorizing solver-like chunks.
"""

from google import genai
from google.genai import types
import os
from typing import Optional, List
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
                f"To use Vertex AI for categorization, you need to set up Application Default Credentials (ADC).\n\n"
                f"Choose ONE of the following methods:\n\n"
                f"1. Use gcloud CLI (recommended for development):\n"
                f"   $ gcloud auth application-default login\n"
                f"   $ gcloud config set project {project_id}\n\n"
                f"2. Use a service account key:\n"
                f"   - Download JSON key from Google Cloud Console\n"
                f"   - Add to .env: GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json\n\n"
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


def prepare_batch_categorization_requests(
    solver_chunks: list[dict],
    categorization_prompt: str,
    max_output_tokens: int = None,
    temperature: float = 0.0
) -> list[dict]:
    """
    Prepare batch prediction requests for categorization in Vertex AI JSONL format.

    Args:
        solver_chunks: List of dicts with 'example_id', 'chunk_index', 'chunk_text'
        categorization_prompt: The categorization prompt to use
        max_output_tokens: Max tokens per response (defaults to MAX_JUDGE_TOKENS from .env)
        temperature: Sampling temperature

    Returns:
        List of request dicts in JSONL format for batch API
    """
    if max_output_tokens is None:
        max_output_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    requests = []
    for chunk in solver_chunks:
        full_prompt = f"{categorization_prompt}\n\n{chunk['chunk_text']}"

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
        requests: List of request dicts (from prepare_batch_categorization_requests)
        input_gcs_uri: GCS URI where requests JSONL will be uploaded
        output_gcs_uri_prefix: GCS URI prefix for output results
        model_id: Gemini model ID (defaults to VERTEX_JUDGE_BATCH_MODEL from .env)
        display_name: Optional display name for the job

    Returns:
        BatchJob object with job details (name, state, etc.)
    """
    # Import here to avoid circular dependency
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from chunking.gcs_utils import upload_jsonl_to_gcs

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
        display_name=display_name or f"categorize-batch-{get_timestamp()}"
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
    # Import here to avoid circular dependency
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from chunking.gcs_utils import list_gcs_blobs, download_jsonl_from_gcs

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
