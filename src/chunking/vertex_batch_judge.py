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


def get_vertex_client() -> genai.Client:
    """
    Initialize Vertex AI client for Gemini.

    Requires environment variables:
    - GOOGLE_CLOUD_PROJECT: GCP project ID
    - GOOGLE_CLOUD_LOCATION: Region (e.g., 'us-central1')
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location
    )

    return client


def call_vertex_judge(
    reasoning_text: str,
    judge_prompt: str,
    model_id: str = None,
    max_output_tokens: int = None,
    temperature: float = 0.0
) -> dict:
    """
    Call Gemini judge via Vertex AI for a single reasoning trace.

    Args:
        reasoning_text: The reasoning trace to classify
        judge_prompt: System/instruction prompt for the judge
        model_id: Gemini model ID (defaults to VERTEX_JUDGE_BATCH_MODEL from .env)
        max_output_tokens: Max tokens for judge response (defaults to MAX_JUDGE_TOKENS from .env)
        temperature: Sampling temperature (0 = deterministic)

    Returns:
        dict with: response_text, metadata (tokens, finish_reason, etc.)
    """
    client = get_vertex_client()

    # Use model from env if not specified
    if model_id is None:
        model_id = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")

    # Use token limit from env for long chunking outputs
    if max_output_tokens is None:
        max_output_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    # Combine judge prompt with reasoning text
    full_prompt = f"{judge_prompt}\n\n{reasoning_text}"

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

    return {
        "response_text": response_text,
        "metadata": {
            "model": model_id,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "finish_reason": str(response.candidates[0].finish_reason) if response.candidates else None,
        }
    }


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
