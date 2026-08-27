"""
GCS utilities for batch prediction I/O.

Handles uploading JSONL requests and downloading JSONL results.
"""

import json
import os
from pathlib import Path
from typing import List, Dict
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()


def get_gcs_client() -> storage.Client:
    """Get GCS storage client."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT not set in environment")

    return storage.Client(project=project_id)


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    """
    Parse GCS URI into bucket and blob path.

    Args:
        uri: GCS URI like "gs://bucket/path/to/file.jsonl"

    Returns:
        (bucket_name, blob_path)
    """
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}")

    path = uri[5:]  # Remove "gs://"
    parts = path.split("/", 1)

    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def upload_jsonl_to_gcs(data: List[Dict], gcs_uri: str) -> str:
    """
    Upload JSONL data to GCS.

    Args:
        data: List of dicts to write as JSONL
        gcs_uri: Target GCS URI like "gs://bucket/path/file.jsonl"

    Returns:
        GCS URI of uploaded file
    """
    bucket_name, blob_path = parse_gcs_uri(gcs_uri)

    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # Convert to JSONL string
    jsonl_content = "\n".join(json.dumps(item) for item in data)

    # Upload
    blob.upload_from_string(jsonl_content, content_type="application/jsonl")

    return gcs_uri


def download_jsonl_from_gcs(gcs_uri: str) -> List[Dict]:
    """
    Download and parse JSONL from GCS.

    Args:
        gcs_uri: Source GCS URI like "gs://bucket/path/file.jsonl"

    Returns:
        List of parsed JSON objects
    """
    bucket_name, blob_path = parse_gcs_uri(gcs_uri)

    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # Download as string
    content = blob.download_as_text()

    # Parse JSONL
    results = []
    for line in content.strip().split("\n"):
        if line.strip():
            results.append(json.loads(line))

    return results


def list_gcs_blobs(gcs_uri_prefix: str) -> List[str]:
    """
    List all blobs with given prefix.

    Args:
        gcs_uri_prefix: GCS URI prefix like "gs://bucket/path/prefix"

    Returns:
        List of full GCS URIs
    """
    bucket_name, blob_prefix = parse_gcs_uri(gcs_uri_prefix)

    client = get_gcs_client()
    bucket = client.bucket(bucket_name)

    blobs = bucket.list_blobs(prefix=blob_prefix)

    return [f"gs://{bucket_name}/{blob.name}" for blob in blobs]


def gcs_blob_exists(gcs_uri: str) -> bool:
    """
    Check if a GCS blob exists.

    Args:
        gcs_uri: GCS URI to check

    Returns:
        True if blob exists, False otherwise
    """
    bucket_name, blob_path = parse_gcs_uri(gcs_uri)

    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    return blob.exists()
