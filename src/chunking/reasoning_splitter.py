"""
Helper functions to split long reasoning traces and stitch judge responses.

When reasoning traces exceed token limits, we split them into segments,
send each to the judge separately, then stitch the chunk results together.
"""

import tiktoken
from typing import List, Tuple


# Conservative token limit per segment to avoid output overflow
# Judge output can be 2-3x input size for complex traces with many chunks
# Max output: 65536 tokens. Empirically, 22k input → >65k output on detailed traces
# Using 15k per segment to ensure judge output stays under 65k limit
MAX_REASONING_TOKENS_PER_SEGMENT = 15000
SAFETY_MARGIN = 0.8  # Use 80% of limit for safety


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        encoding: Tokenizer encoding to use (cl100k_base approximates Gemini)

    Returns:
        Number of tokens
    """
    try:
        tokenizer = tiktoken.get_encoding(encoding)
        return len(tokenizer.encode(text))
    except Exception:
        # Fallback: rough estimate (~4 chars per token)
        return len(text) // 4


def split_reasoning_by_tokens(
    reasoning_text: str,
    max_tokens_per_segment: int = MAX_REASONING_TOKENS_PER_SEGMENT,
    encoding: str = "cl100k_base"
) -> List[str]:
    """
    Split long reasoning text into smaller segments based on token count.

    Strategy:
    - Split by paragraphs (double newline) to maintain coherent chunks
    - If a single paragraph exceeds limit, split by sentences
    - If a single sentence exceeds limit, split by character count

    Args:
        reasoning_text: Full reasoning trace to split
        max_tokens_per_segment: Max tokens per segment (default 15k)
        encoding: Tokenizer encoding to use

    Returns:
        List of text segments, each under the token limit
    """
    total_tokens = count_tokens(reasoning_text, encoding)

    # No split needed
    if total_tokens <= max_tokens_per_segment:
        return [reasoning_text]

    # Split into segments
    segments = []

    # Try splitting by paragraphs first (most natural)
    paragraphs = reasoning_text.split('\n\n')

    current_segment = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = count_tokens(para, encoding)

        # If single paragraph is too large, handle specially
        if para_tokens > max_tokens_per_segment:
            # Save current segment if it has content
            if current_segment:
                segments.append('\n\n'.join(current_segment))
                current_segment = []
                current_tokens = 0

            # Split large paragraph by sentences
            sentences = para.split('. ')
            for i, sentence in enumerate(sentences):
                # Add period back (except for last sentence which might not have it)
                if i < len(sentences) - 1:
                    sentence = sentence + '.'

                sent_tokens = count_tokens(sentence, encoding)

                # If single sentence is too large, force split by characters
                if sent_tokens > max_tokens_per_segment:
                    # Character-based splitting as last resort
                    char_chunks = _split_by_characters(sentence, max_tokens_per_segment, encoding)
                    for chunk in char_chunks[:-1]:
                        segments.append(chunk)
                    # Last chunk becomes start of next segment
                    current_segment = [char_chunks[-1]]
                    current_tokens = count_tokens(char_chunks[-1], encoding)
                elif current_tokens + sent_tokens > max_tokens_per_segment:
                    # Start new segment
                    segments.append('. '.join(current_segment))
                    current_segment = [sentence]
                    current_tokens = sent_tokens
                else:
                    # Add to current segment
                    current_segment.append(sentence)
                    current_tokens += sent_tokens

        # Normal paragraph fits or can be added
        elif current_tokens + para_tokens > max_tokens_per_segment:
            # Save current segment and start new one
            if current_segment:
                segments.append('\n\n'.join(current_segment))
            current_segment = [para]
            current_tokens = para_tokens
        else:
            # Add to current segment
            current_segment.append(para)
            current_tokens += para_tokens

    # Add remaining segment
    if current_segment:
        segments.append('\n\n'.join(current_segment))

    return segments


def _split_by_characters(
    text: str,
    max_tokens: int,
    encoding: str = "cl100k_base"
) -> List[str]:
    """
    Split text by character count when sentences are too long.

    This is a last resort for extremely long unbroken text.
    """
    # Rough estimate: 4 chars per token
    max_chars = max_tokens * 4

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end]

        # Verify token count and adjust if needed
        while count_tokens(chunk, encoding) > max_tokens and len(chunk) > 100:
            end = start + int(len(chunk) * 0.9)  # Reduce by 10%
            chunk = text[start:end]

        chunks.append(chunk)
        start = end

    return chunks


def stitch_judge_responses(segment_responses: List[dict]) -> Tuple[List[dict], dict]:
    """
    Stitch together judge responses from multiple segments into unified chunks.

    Each segment was judged independently, producing chunk_analysis arrays.
    We combine them into a single coherent chunk_analysis.

    Args:
        segment_responses: List of parsed judge responses, each with 'chunk_analysis'
                          Format: [{"chunk_analysis": [{"sound": "..."}, ...]}, ...]

    Returns:
        (combined_chunks, combined_metadata)
        - combined_chunks: Single list of all chunks from all segments
        - combined_metadata: Aggregated metadata about the stitching
    """
    if not segment_responses:
        return [], {"num_segments": 0, "total_chunks": 0}

    # If only one segment, no stitching needed
    if len(segment_responses) == 1:
        chunks = segment_responses[0].get("chunk_analysis", [])
        return chunks, {
            "num_segments": 1,
            "total_chunks": len(chunks),
            "was_split": False
        }

    # Combine all chunks from all segments in order
    combined_chunks = []

    for segment_idx, response in enumerate(segment_responses):
        segment_chunks = response.get("chunk_analysis", [])

        # Add all chunks from this segment
        for chunk in segment_chunks:
            combined_chunks.append(chunk)

    metadata = {
        "num_segments": len(segment_responses),
        "total_chunks": len(combined_chunks),
        "was_split": True,
        "chunks_per_segment": [len(r.get("chunk_analysis", [])) for r in segment_responses]
    }

    return combined_chunks, metadata


def should_split_reasoning(
    reasoning_text: str,
    max_output_tokens: int = 65536,
    encoding: str = "cl100k_base"
) -> Tuple[bool, int]:
    """
    Determine if reasoning trace should be split based on estimated output size.

    Args:
        reasoning_text: Reasoning trace to check
        max_output_tokens: Maximum output tokens allowed by judge model
        encoding: Tokenizer encoding

    Returns:
        (should_split, estimated_tokens)
    """
    reasoning_tokens = count_tokens(reasoning_text, encoding)

    # Estimate judge output size:
    # - Judge repeats text in chunks (~1.0x input)
    # - JSON formatting overhead (~0.2x input)
    # - Total: ~1.2-1.5x input tokens
    estimated_output = int(reasoning_tokens * 1.3)

    # Use safety margin (80% of max)
    safe_max = int(max_output_tokens * SAFETY_MARGIN)

    should_split = estimated_output > safe_max

    return should_split, reasoning_tokens
