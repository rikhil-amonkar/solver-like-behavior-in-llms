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


def prepare_batch_request(
    examples: list[dict],
    judge_prompt: str,
    output_gcs_path: str = None,
    model_id: str = None
) -> dict:
    """
    Prepare a batch prediction request for Vertex AI.

    Args:
        examples: List of dicts with 'example_id' and 'reasoning_text'
        judge_prompt: The judge prompt to use
        output_gcs_path: GCS path for results (defaults to JUDGE_VERTEX_GCS_BUCKET/JUDGE_VERTEX_GCS_PREFIX from .env)
        model_id: Gemini model ID (defaults to VERTEX_JUDGE_BATCH_MODEL from .env)

    Returns:
        Batch request dict ready for submission
    """
    # Use settings from env if not specified
    if model_id is None:
        model_id = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")

    if output_gcs_path is None:
        bucket = os.getenv("JUDGE_VERTEX_GCS_BUCKET")
        prefix = os.getenv("JUDGE_VERTEX_GCS_PREFIX", "judge-batch")
        if not bucket:
            raise ValueError("JUDGE_VERTEX_GCS_BUCKET not set in .env")
        output_gcs_path = f"gs://{bucket}/{prefix}"

    # Format examples for batch API
    requests = []
    for example in examples:
        full_prompt = f"{judge_prompt}\n\n{example['reasoning_text']}"
        requests.append({
            "contents": full_prompt,
            "id": example["example_id"],
        })

    return {
        "model": model_id,
        "requests": requests,
        "output_uri": output_gcs_path,
        "config": {
            "temperature": 0.0,
            "max_output_tokens": int(os.getenv("MAX_JUDGE_TOKENS", 65536)),
            "response_mime_type": "application/json",
        }
    }


def submit_batch_job(
    batch_request: dict,
    input_gcs_path: Optional[str] = None
) -> str:
    """
    Submit batch prediction job to Vertex AI.

    Args:
        batch_request: Batch request dict from prepare_batch_request()
        input_gcs_path: Optional GCS path to save request JSON

    Returns:
        Batch job ID for monitoring

    Note: This is a simplified stub. Actual implementation would use
    google.cloud.aiplatform for batch job submission.
    """
    # TODO: Implement actual batch job submission
    # Would use: aiplatform.BatchPredictionJob.create(...)
    raise NotImplementedError(
        "Batch job submission not yet implemented. "
        "Use call_vertex_judge() for single-example mode, or implement "
        "batch submission using google.cloud.aiplatform.BatchPredictionJob"
    )


def parse_batch_results(results_gcs_path: str) -> list[dict]:
    """
    Parse results from completed batch job.

    Args:
        results_gcs_path: GCS path to results JSON

    Returns:
        List of dicts with example_id and judge response
    """
    # TODO: Implement GCS result parsing
    # Would download from GCS and parse JSONL output
    raise NotImplementedError(
        "Batch result parsing not yet implemented. "
        "Load results from GCS and parse JSONL format."
    )


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
