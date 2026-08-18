"""Parse and validate judge model chunk outputs."""

import json
import tiktoken
from typing import Tuple, Optional


def parse_judge_response(response_text: str) -> dict:
    """
    Parse judge JSON response and validate structure.

    Expected format:
    {
        "chunk_analysis": [
            {"sound": "text"} or {"solver-like": "text"},
            ...
        ]
    }

    Args:
        response_text: Raw JSON response from judge

    Returns:
        Parsed dict with chunk_analysis

    Raises:
        ValueError: If response is invalid
    """
    if not response_text or not response_text.strip():
        raise ValueError("Empty judge response")

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from judge: {str(e)}")

    if "chunk_analysis" not in data:
        raise ValueError("Missing 'chunk_analysis' key in judge response")

    chunk_analysis = data["chunk_analysis"]

    if not isinstance(chunk_analysis, list):
        raise ValueError("chunk_analysis must be a list")

    # Validate each chunk
    for i, chunk in enumerate(chunk_analysis):
        if not isinstance(chunk, dict):
            raise ValueError(f"Chunk {i} must be a dict")

        if len(chunk) != 1:
            raise ValueError(f"Chunk {i} must have exactly one key")

        key = list(chunk.keys())[0]
        if key not in ["sound", "solver-like"]:
            raise ValueError(f"Chunk {i} has invalid key: {key}")

        if not isinstance(chunk[key], str):
            raise ValueError(f"Chunk {i} value must be a string")

    return {"chunk_analysis": chunk_analysis}


def enrich_chunks_with_tokens(
    chunks: list,
    encoding: str = "cl100k_base"
) -> Tuple[list, dict]:
    """
    Add token counts to each chunk and compute statistics.

    Args:
        chunks: List of chunk dicts from judge
        encoding: Tokenizer to use (cl100k_base for Gemini/GPT-4)

    Returns:
        (enriched_chunks, token_statistics)
    """
    try:
        tokenizer = tiktoken.get_encoding(encoding)
    except Exception:
        # Fallback to simple whitespace splitting
        tokenizer = None

    enriched_chunks = []
    total_tokens = 0
    solver_like_tokens = 0
    sound_tokens = 0

    for chunk in chunks:
        # Chunk has exactly one key
        chunk_type = list(chunk.keys())[0]
        chunk_text = chunk[chunk_type]

        # Count tokens
        if tokenizer:
            tokens = len(tokenizer.encode(chunk_text))
        else:
            # Rough approximation
            tokens = len(chunk_text.split())

        # Add to enriched
        enriched_chunks.append({
            chunk_type: chunk_text,
            "tokens": tokens
        })

        total_tokens += tokens
        if chunk_type == "solver-like":
            solver_like_tokens += tokens
        else:
            sound_tokens += tokens

    # Compute statistics
    solver_like_fraction = solver_like_tokens / total_tokens if total_tokens > 0 else 0.0

    token_statistics = {
        "encoding": encoding,
        "reasoning_total_tokens": total_tokens,
        "solver_like_total_tokens": solver_like_tokens,
        "sound_total_tokens": sound_tokens,
        "solver_like_fraction": solver_like_fraction,
    }

    return enriched_chunks, token_statistics


def has_solver_like_chunks(chunks: list) -> bool:
    """
    Check if any chunk is labeled solver-like.

    Args:
        chunks: List of chunk dicts

    Returns:
        True if any chunk has "solver-like" key
    """
    return any("solver-like" in chunk for chunk in chunks)
