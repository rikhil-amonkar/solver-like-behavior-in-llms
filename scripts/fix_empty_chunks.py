#!/usr/bin/env python3
"""
Fix script for chunking JSON files with empty chunk_analysis.

Identifies examples with empty chunk_analysis lists and re-processes them,
automatically updating the JSON file with the fixed versions.

Uses batch processing via Vertex AI for efficiency and 5K token segments
(instead of the default 15K) for more granular chunking.
"""

import argparse
import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunking.chunk_parser import (
    parse_judge_response,
    enrich_chunks_with_tokens,
    has_solver_like_chunks,
    parse_and_stitch_segments,
)
from chunking.reasoning_splitter import count_tokens
from chunking.vertex_batch_judge import (
    prepare_batch_requests,
    submit_batch_job,
    poll_batch_job,
    parse_batch_results,
    get_timestamp
)
from chunking.gcs_utils import upload_jsonl_to_gcs
from general.prompt_utils import load_prompt_template

# Custom 5K token limit for fix script (more conservative than default 15K)
FIX_SCRIPT_MAX_TOKENS_PER_SEGMENT = 5000


def split_reasoning_by_tokens_5k(
    reasoning_text: str,
    max_tokens_per_segment: int = FIX_SCRIPT_MAX_TOKENS_PER_SEGMENT,
    encoding: str = "cl100k_base"
) -> list[str]:
    """
    Split reasoning text into 5K token segments (custom for fix script).

    Uses same splitting strategy as regular splitter but with 5K limit.
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
) -> list[str]:
    """Split text by character count when sentences are too long."""
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


def find_empty_examples(chunking_data):
    """
    Find examples with empty chunk_analysis lists.

    Returns:
        List of (index, example) tuples for examples that need fixing
    """
    empty_examples = []

    for idx, example in enumerate(chunking_data["examples"]):
        chunk_analysis = example.get("chunk_analysis", [])
        if not chunk_analysis or len(chunk_analysis) == 0:
            empty_examples.append((idx, example))

    return empty_examples


def prepare_batch_data(empty_examples, judge_prompt_text):
    """
    Prepare batch requests for all empty examples.

    Segments long reasoning traces into 5K token chunks and creates
    batch requests for all segments.

    Returns:
        (batch_requests, segment_map, empty_examples_map)
        - batch_requests: List of request dicts for Vertex AI batch
        - segment_map: Maps request index -> (list_idx, segment_idx, total_segments)
        - empty_examples_map: Maps list_idx -> (original_idx, example)
    """
    batch_requests = []
    segment_map = {}
    empty_examples_map = {}  # Maps list_idx -> (idx, example)
    request_idx = 0
    list_idx = 0

    for idx, example in empty_examples:
        example_id = example["example_id"]
        reasoning_before_code = example.get("reasoning_before_code", "")

        # Skip empty reasoning
        if not reasoning_before_code or not reasoning_before_code.strip():
            print(f"  ⚠ {example_id}: Empty reasoning, skipping")
            continue

        # Store in map
        empty_examples_map[list_idx] = (idx, example)

        # Count tokens and split if needed
        reasoning_tokens = count_tokens(reasoning_before_code)

        if reasoning_tokens > FIX_SCRIPT_MAX_TOKENS_PER_SEGMENT:
            # Split into 5K segments
            segments = split_reasoning_by_tokens_5k(reasoning_before_code)
            print(f"  {example_id}: Splitting {reasoning_tokens} tokens into {len(segments)} segments (5K each)")

            # Create request for each segment
            for seg_idx, segment in enumerate(segments):
                batch_requests.append({
                    "example_id": example_id,
                    "reasoning_text": segment
                })
                segment_map[request_idx] = (list_idx, seg_idx, len(segments))
                request_idx += 1
        else:
            # Single request
            batch_requests.append({
                "example_id": example_id,
                "reasoning_text": reasoning_before_code
            })
            segment_map[request_idx] = (list_idx, 0, 1)  # Single segment
            request_idx += 1

        list_idx += 1

    return batch_requests, segment_map, empty_examples_map


def process_batch_results(
    batch_results: list[dict],
    segment_map: dict,
    empty_examples_map: dict,
    chunking_data: dict
):
    """
    Process batch results and update examples.

    Args:
        batch_results: Results from Vertex AI batch job
        segment_map: Maps request index -> (list_idx, segment_idx, total_segments)
        empty_examples_map: Maps list_idx -> (original_idx, example)
        chunking_data: Original chunking data to update
    """
    # Group results by example
    example_segments = {}  # list_idx -> list of (segment_idx, response_text)

    for req_idx, result in enumerate(batch_results):
        if req_idx not in segment_map:
            print(f"  ⚠ Warning: Request {req_idx} not in segment_map, skipping")
            continue

        list_idx, segment_idx, total_segments = segment_map[req_idx]

        # Extract response text
        response_text = None
        if "response" in result:
            # Vertex AI batch format
            candidates = result["response"].get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    response_text = parts[0].get("text", "")

        if not response_text:
            print(f"  ⚠ Warning: Empty response for request {req_idx}")
            continue

        # Store segment result
        if list_idx not in example_segments:
            example_segments[list_idx] = []

        example_segments[list_idx].append((segment_idx, response_text))

    # Process each example
    fixed_count = 0
    failed_count = 0

    for list_idx, segment_results in example_segments.items():
        idx, example = empty_examples_map[list_idx]
        example_id = example["example_id"]

        # Sort segments by index
        segment_results.sort(key=lambda x: x[0])
        segment_responses = [resp for _, resp in segment_results]

        try:
            # Check if this was segmented
            if len(segment_responses) > 1:
                # Multi-segment: parse and stitch
                enriched_chunks, token_stats, has_solver_like = parse_and_stitch_segments(
                    segment_responses
                )

                # Update example
                example["chunk_analysis"] = enriched_chunks
                example["token_statistics"] = token_stats
                example["has_solver_like"] = has_solver_like

                if "judge_metadata" not in example:
                    example["judge_metadata"] = {}

                example["judge_metadata"]["was_split"] = True
                example["judge_metadata"]["num_segments"] = len(segment_responses)
                example["judge_metadata"]["segment_size_tokens"] = FIX_SCRIPT_MAX_TOKENS_PER_SEGMENT

            else:
                # Single segment
                parsed_response = parse_judge_response(segment_responses[0])
                chunks = parsed_response["chunk_analysis"]

                # Enrich with tokens
                enriched_chunks, token_stats = enrich_chunks_with_tokens(chunks)
                has_solver_like = has_solver_like_chunks(chunks)

                # Update example
                example["chunk_analysis"] = enriched_chunks
                example["token_statistics"] = token_stats
                example["has_solver_like"] = has_solver_like

                if "judge_metadata" not in example:
                    example["judge_metadata"] = {}

                example["judge_metadata"]["was_split"] = False

            # Update in original data
            chunking_data["examples"][idx] = example
            fixed_count += 1
            print(f"  ✓ {example_id}")

        except Exception as e:
            print(f"  ❌ Failed to process {example_id}: {str(e)}")
            failed_count += 1
            continue

    return fixed_count, failed_count


def main():
    parser = argparse.ArgumentParser(
        description="Fix chunking JSON files with empty chunk_analysis using batch processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python extras/fix_empty_chunks.py \\
      --input output/deepseek/calendar/baseline_chunking.json \\
      --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \\
      --gcs-bucket your-batch-bucket

Note: This script uses batch processing with 5K token segments (vs 15K in normal chunking)
        """
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to chunking JSON file to fix"
    )
    parser.add_argument(
        "--judge-prompt",
        required=True,
        help="Path to judge prompt file"
    )
    parser.add_argument(
        "--gcs-bucket",
        help="GCS bucket for batch processing (defaults to JUDGE_VERTEX_GCS_BUCKET env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which examples would be fixed without making changes"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup of original file (default: True)"
    )

    args = parser.parse_args()

    # Validate environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT not set in environment")
        sys.exit(1)

    # Get GCS bucket from args or environment
    gcs_bucket = args.gcs_bucket or os.getenv("JUDGE_VERTEX_GCS_BUCKET")
    if not gcs_bucket:
        print("❌ ERROR: --gcs-bucket is required for batch processing")
        print("   Either:")
        print("   1. Provide --gcs-bucket your-bucket")
        print("   2. Set JUDGE_VERTEX_GCS_BUCKET in .env")
        sys.exit(1)

    # Load chunking JSON
    print(f"Loading chunking JSON: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        chunking_data = json.load(f)

    # Find examples with empty chunk_analysis
    empty_examples = find_empty_examples(chunking_data)

    if not empty_examples:
        print("\n✓ No examples with empty chunk_analysis found!")
        return

    print(f"\nFound {len(empty_examples)} examples with empty chunk_analysis:")
    for idx, example in empty_examples:
        print(f"  - {example['example_id']}")

    if args.dry_run:
        print("\n(Dry run - no changes made)")
        return

    # Create backup
    if args.backup:
        backup_path = Path(args.input).with_suffix(".json.backup")
        print(f"\nCreating backup: {backup_path}")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(chunking_data, f, indent=2, ensure_ascii=False)

    # Load judge prompt
    print(f"\nLoading judge prompt: {args.judge_prompt}")
    judge_prompt_text = load_prompt_template(args.judge_prompt)

    # Get max_judge_tokens from metadata or environment
    max_judge_tokens = chunking_data["run_metadata"].get(
        "max_judge_tokens",
        int(os.getenv("MAX_JUDGE_TOKENS", 65536))
    )

    # Prepare batch data
    print(f"\nPreparing batch requests (5K token segments)...")
    batch_data, segment_map, empty_examples_map = prepare_batch_data(empty_examples, judge_prompt_text)

    if not batch_data:
        print("\n⚠ No valid examples to process (all had empty reasoning)")
        return

    print(f"  Total batch requests: {len(batch_data)}")
    print(f"  Examples to fix: {len(set(d['example_id'] for d in batch_data))}")

    # Prepare batch requests in Vertex AI format
    batch_requests = prepare_batch_requests(
        batch_data,
        judge_prompt_text,
        max_output_tokens=max_judge_tokens,
        temperature=0.0
    )

    # Generate GCS paths
    timestamp = get_timestamp()
    input_gcs_uri = f"gs://{gcs_bucket}/fix_empty_chunks/input_{timestamp}.jsonl"
    output_gcs_prefix = f"gs://{gcs_bucket}/fix_empty_chunks/output_{timestamp}/"

    print(f"\nSubmitting batch job...")
    print(f"  Input: {input_gcs_uri}")
    print(f"  Output: {output_gcs_prefix}")

    # Submit batch job
    batch_job = submit_batch_job(
        batch_requests,
        input_gcs_uri,
        output_gcs_prefix,
        display_name=f"fix-empty-chunks-{timestamp}"
    )

    print(f"  Batch job: {batch_job.name}")
    print(f"  Status: {batch_job.state}")

    # Poll for completion
    print(f"\nWaiting for batch job to complete...")
    print(f"  (This may take 10-30 minutes for {len(batch_data)} requests)")

    try:
        completed_job = poll_batch_job(
            batch_job.name,
            poll_interval=30,
            max_wait=2592000  # 30 days max (effectively unlimited)
        )

        print(f"\n✓ Batch job completed: {completed_job.state}")

    except Exception as e:
        print(f"\n❌ Batch job failed: {str(e)}")
        sys.exit(1)

    # Download and parse results
    print(f"\nDownloading batch results from {output_gcs_prefix}...")
    batch_results = parse_batch_results(output_gcs_prefix)

    print(f"  Retrieved {len(batch_results)} results")

    # Process results and update examples
    print(f"\nProcessing results...")
    fixed_count, failed_count = process_batch_results(
        batch_results,
        segment_map,
        empty_examples_map,
        chunking_data
    )

    # Update summary statistics
    examples_with_solver_like = sum(
        1 for ex in chunking_data["examples"] if ex.get("has_solver_like", False)
    )
    examples_sound_only = len(chunking_data["examples"]) - examples_with_solver_like

    if "summary" not in chunking_data:
        chunking_data["summary"] = {}

    chunking_data["summary"]["examples_with_solver_like"] = examples_with_solver_like
    chunking_data["summary"]["examples_sound_only"] = examples_sound_only

    # Write updated JSON
    print(f"\nWriting updated JSON to {args.input}")
    with open(args.input, "w", encoding="utf-8") as f:
        json.dump(chunking_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Fix complete!")
    print(f"  Fixed: {fixed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total examples with solver-like: {examples_with_solver_like}")
    print(f"  Total examples sound only: {examples_sound_only}")


if __name__ == "__main__":
    main()
