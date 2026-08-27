#!/usr/bin/env python3
"""
Chunking pipeline runner.

Uses Gemini judge to classify reasoning traces into sound vs solver-like chunks.

Default mode: Batch processing (fast, parallel via Vertex AI Batch API)
Sequential mode: One-by-one processing (--sequential flag)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, get_timestamp, make_path_relative, IncrementalJSONWriter
from general.cli import ProgressTracker
from chunking.vertex_batch_judge import (
    prepare_batch_requests,
    submit_batch_job,
    poll_batch_job,
    parse_batch_results
)
from chunking.judge_caller import call_judge
from chunking.chunk_parser import (
    parse_judge_response,
    enrich_chunks_with_tokens,
    has_solver_like_chunks,
    parse_and_stitch_segments,
)
from chunking.reasoning_splitter import split_reasoning_by_tokens, should_split_reasoning
import json
import os
import time


def run_batch_chunking_pipeline(
    execution_json_path: str,
    judge_prompt_path: str,
    gcs_bucket: str,
    gcs_prefix: str = None,
):
    """
    Run batch chunking pipeline on execution results.

    Args:
        execution_json_path: Path to execution JSON output
        judge_prompt_path: Path to judge prompt file
        gcs_bucket: GCS bucket name for batch I/O
        gcs_prefix: Optional GCS prefix (defaults to judge-batch/<timestamp>)
    """
    print(f"\n=== Batch Chunking Pipeline ===")
    print(f"Input: {execution_json_path}")
    print(f"Judge prompt: {judge_prompt_path}")
    print(f"GCS bucket: {gcs_bucket}\n")

    # Validate environment
    import os
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT not set in environment")
        sys.exit(1)

    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    print(f"Vertex AI Configuration:")
    print(f"  Project: {project_id}")
    print(f"  Location: {location}")
    print()

    # Load execution results
    print("Loading execution results...")
    execution_data = load_json_file(execution_json_path)

    task = execution_data["run_metadata"]["task"]
    model = execution_data["run_metadata"]["model"]
    condition = execution_data["run_metadata"].get("condition", "baseline")
    examples = execution_data["examples"]

    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Examples: {len(examples)}")

    # Determine output path
    execution_path = Path(execution_json_path)
    output_filename = f"{condition}_chunking.json"
    output_path = execution_path.parent / output_filename
    print(f"Output: {output_path}\n")

    # Load judge prompt
    judge_prompt = Path(judge_prompt_path).read_text(encoding="utf-8")

    # Prepare batch requests (handle splitting)
    print("Preparing batch requests...")
    batch_examples = []
    example_id_to_segments = {}  # Track which examples were split

    max_judge_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    for example in examples:
        example_id = example["example_id"]
        reasoning_before_code = example.get("reasoning_before_code", "")

        if not reasoning_before_code or not reasoning_before_code.strip():
            # Empty reasoning - will handle separately
            example_id_to_segments[example_id] = []
            continue

        # Check if needs splitting
        needs_split, reasoning_tokens = should_split_reasoning(
            reasoning_before_code,
            max_output_tokens=max_judge_tokens
        )

        if needs_split:
            # Split into segments
            segments = split_reasoning_by_tokens(reasoning_before_code)
            print(f"  ℹ {example_id}: Splitting {reasoning_tokens} tokens into {len(segments)} segments")

            # Create batch request for each segment
            segment_ids = []
            for seg_idx, segment in enumerate(segments):
                segment_id = f"{example_id}__segment_{seg_idx}"
                batch_examples.append({
                    "example_id": segment_id,
                    "reasoning_text": segment
                })
                segment_ids.append(segment_id)

            example_id_to_segments[example_id] = segment_ids
        else:
            # Single request
            batch_examples.append({
                "example_id": example_id,
                "reasoning_text": reasoning_before_code
            })
            example_id_to_segments[example_id] = [example_id]

    print(f"Total batch requests: {len(batch_examples)}")

    # Prepare requests in Vertex AI format
    requests = prepare_batch_requests(
        batch_examples,
        judge_prompt,
        max_output_tokens=max_judge_tokens
    )

    # Setup GCS paths
    timestamp = get_timestamp()
    if gcs_prefix is None:
        gcs_prefix = f"judge-batch/{model}/{task}/{condition}/{timestamp}"

    input_gcs_uri = f"gs://{gcs_bucket}/{gcs_prefix}/input.jsonl"
    output_gcs_uri_prefix = f"gs://{gcs_bucket}/{gcs_prefix}/output"

    print(f"\nGCS paths:")
    print(f"  Input: {input_gcs_uri}")
    print(f"  Output: {output_gcs_uri_prefix}")

    # Submit batch job
    print("\nSubmitting batch job to Vertex AI...")
    batch_job = submit_batch_job(
        requests=requests,
        input_gcs_uri=input_gcs_uri,
        output_gcs_uri_prefix=output_gcs_uri_prefix,
        display_name=f"judge-{model}-{task}-{condition}"
    )

    print(f"Batch job created: {batch_job.name}")
    print(f"State: {batch_job.state}")

    # Poll until complete
    print("\nWaiting for batch job to complete...")
    print("(This may take 10-30 minutes depending on dataset size)")

    completed_job = poll_batch_job(
        batch_job_name=batch_job.name,
        poll_interval=30,
        max_wait=7200  # 2 hours max
    )

    print(f"\n✓ Batch job completed!")
    print(f"  Duration: {(completed_job.end_time - completed_job.start_time).total_seconds():.0f}s")

    # Download and parse results
    print("\nDownloading batch results from GCS...")
    batch_results = parse_batch_results(output_gcs_uri_prefix)

    print(f"Retrieved {len(batch_results)} responses")

    # Map results back to examples (handle segments)
    print("\nProcessing results...")
    example_id_to_response = {}

    for idx, result in enumerate(batch_results):
        # Extract response text from Vertex AI format
        response_text = ""

        if "response" in result and "candidates" in result["response"]:
            candidate = result["response"]["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                response_text = candidate["content"]["parts"][0].get("text", "")

        # Map by index since batch results don't include custom_id in current format
        # Results are returned in same order as input requests
        if idx < len(batch_examples):
            example_id = batch_examples[idx]["example_id"]
            example_id_to_response[example_id] = response_text

    # Build final results
    judge_model = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")

    metadata = {
        "task": task,
        "model": model,
        "condition": condition,
        "execution_json": make_path_relative(str(execution_json_path)),
        "judge_model": judge_model,
        "judge_prompt": judge_prompt_path,
        "timestamp": timestamp,
        "num_examples": len(examples),
        "max_judge_tokens": max_judge_tokens,
        "batch_job_name": batch_job.name,
        "gcs_input": input_gcs_uri,
        "gcs_output": output_gcs_uri_prefix,
    }

    final_examples = []
    examples_with_solver_like = 0
    examples_sound_only = 0

    for example in examples:
        example_id = example["example_id"]
        reasoning_before_code = example.get("reasoning_before_code", "")

        # Check if this was split
        segment_ids = example_id_to_segments.get(example_id, [])

        if not segment_ids:
            # Empty reasoning
            result = {
                "example_id": example_id,
                "reasoning_before_code": reasoning_before_code,
                "chunk_analysis": [],
                "token_statistics": {
                    "encoding": "cl100k_base",
                    "reasoning_total_tokens": 0,
                    "solver_like_total_tokens": 0,
                    "sound_total_tokens": 0,
                    "solver_like_fraction": 0.0,
                },
                "has_solver_like": False,
                "judge_metadata": {},
            }
            examples_sound_only += 1
        elif len(segment_ids) > 1:
            # Multiple segments - need to stitch
            segment_responses = []
            for seg_id in segment_ids:
                if seg_id in example_id_to_response:
                    segment_responses.append(example_id_to_response[seg_id])

            # Parse and stitch
            from chunking.chunk_parser import parse_and_stitch_segments
            try:
                enriched_chunks, token_stats, has_solver_like = parse_and_stitch_segments(
                    segment_responses
                )
            except ValueError as e:
                print(f"  ⚠ Failed to parse segments for {example_id}: {str(e)}")
                enriched_chunks = []
                token_stats = {
                    "encoding": "cl100k_base",
                    "reasoning_total_tokens": 0,
                    "solver_like_total_tokens": 0,
                    "sound_total_tokens": 0,
                    "solver_like_fraction": 0.0,
                }
                has_solver_like = False

            result = {
                "example_id": example_id,
                "reasoning_before_code": reasoning_before_code,
                "chunk_analysis": enriched_chunks,
                "token_statistics": token_stats,
                "has_solver_like": has_solver_like,
                "judge_metadata": {
                    "num_segments": len(segment_ids),
                    "was_split": True
                },
            }

            if has_solver_like:
                examples_with_solver_like += 1
            else:
                examples_sound_only += 1
        else:
            # Single response
            response_text = example_id_to_response.get(segment_ids[0], "")

            try:
                parsed_response = parse_judge_response(response_text)
                chunks = parsed_response["chunk_analysis"]
            except ValueError as e:
                print(f"  ⚠ Failed to parse response for {example_id}: {str(e)}")
                chunks = []

            # Enrich with tokens
            enriched_chunks, token_stats = enrich_chunks_with_tokens(chunks)
            has_solver_like = has_solver_like_chunks(chunks)

            result = {
                "example_id": example_id,
                "reasoning_before_code": reasoning_before_code,
                "chunk_analysis": enriched_chunks,
                "token_statistics": token_stats,
                "has_solver_like": has_solver_like,
                "judge_metadata": {},
            }

            if has_solver_like:
                examples_with_solver_like += 1
            else:
                examples_sound_only += 1

        final_examples.append(result)

    # Write output
    output_data = {
        "run_metadata": metadata,
        "examples": final_examples,
        "summary": {
            "total_examples": len(examples),
            "examples_with_solver_like": examples_with_solver_like,
            "examples_sound_only": examples_sound_only,
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Batch chunking complete!")
    print(f"  Examples with solver-like: {examples_with_solver_like}/{len(examples)}")
    print(f"  Examples sound only: {examples_sound_only}/{len(examples)}")
    print(f"  Output: {output_path}")


def run_sequential_chunking_pipeline(
    execution_json_path: str,
    judge_prompt_path: str,
):
    """
    Run sequential chunking pipeline (one example at a time).

    Args:
        execution_json_path: Path to execution JSON output
        judge_prompt_path: Path to judge prompt file
    """
    print(f"\n=== Sequential Chunking Pipeline ===")
    print(f"Input: {execution_json_path}")
    print(f"Judge prompt: {judge_prompt_path}\n")

    # Validate environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT not set in environment")
        sys.exit(1)

    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    print(f"Vertex AI Configuration:")
    print(f"  Project: {project_id}")
    print(f"  Location: {location}")
    print()

    # Load execution results
    print("Loading execution results...")
    execution_data = load_json_file(execution_json_path)

    task = execution_data["run_metadata"]["task"]
    model = execution_data["run_metadata"]["model"]
    condition = execution_data["run_metadata"].get("condition", "baseline")
    examples = execution_data["examples"]

    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Examples: {len(examples)}")

    # Determine output path
    execution_path = Path(execution_json_path)
    output_filename = f"{condition}_chunking.json"
    output_path = execution_path.parent / output_filename
    print(f"Output: {output_path}\n")

    # Build metadata
    judge_model = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")
    max_judge_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    metadata = {
        "task": task,
        "model": model,
        "condition": condition,
        "execution_json": make_path_relative(str(execution_json_path)),
        "judge_model": judge_model,
        "judge_prompt": judge_prompt_path,
        "timestamp": get_timestamp(),
        "num_examples": len(examples),
        "max_judge_tokens": max_judge_tokens,
        "mode": "sequential",
    }

    # Process examples
    examples_with_solver_like = 0
    examples_sound_only = 0
    total_chunks = 0
    examples_split = 0

    # Rate limiting: ~2.5 seconds between requests
    last_request_time = 0
    min_request_interval = 2.5

    with IncrementalJSONWriter(str(output_path), metadata) as writer:
        with ProgressTracker(len(examples), f"Chunking {task}") as progress:
            for example in examples:
                try:
                    example_id = example["example_id"]
                    reasoning_before_code = example.get("reasoning_before_code", "")

                    # Skip if no reasoning
                    if not reasoning_before_code or not reasoning_before_code.strip():
                        result = {
                            "example_id": example_id,
                            "reasoning_before_code": reasoning_before_code,
                            "chunk_analysis": [],
                            "token_statistics": {
                                "encoding": "cl100k_base",
                                "reasoning_total_tokens": 0,
                                "solver_like_total_tokens": 0,
                                "sound_total_tokens": 0,
                                "solver_like_fraction": 0.0,
                            },
                            "has_solver_like": False,
                            "judge_metadata": {},
                        }
                        writer.write_example(result)
                        examples_sound_only += 1
                        progress.update(1)
                        continue

                    # Check if reasoning needs to be split
                    needs_split, reasoning_tokens = should_split_reasoning(
                        reasoning_before_code,
                        max_output_tokens=max_judge_tokens
                    )

                    if needs_split:
                        # Split reasoning into segments (15k tokens each)
                        segments = split_reasoning_by_tokens(reasoning_before_code)
                        print(f"\n  ℹ {example_id}: Splitting {reasoning_tokens} tokens into {len(segments)} segments (~15k tokens each)")
                        examples_split += 1

                        # Call judge for each segment
                        segment_responses = []
                        segment_metadata = []

                        for seg_idx, segment in enumerate(segments):
                            # Rate limiting between segment calls
                            time_since_last_request = time.time() - last_request_time
                            if last_request_time > 0 and time_since_last_request < min_request_interval:
                                sleep_time = min_request_interval - time_since_last_request
                                time.sleep(sleep_time)

                            # Call judge for this segment
                            last_request_time = time.time()
                            judge_result = call_judge(
                                reasoning_text=segment,
                                judge_prompt_path=judge_prompt_path,
                            )

                            segment_responses.append(judge_result["raw_response"])
                            segment_metadata.append(judge_result["metadata"])

                        # Parse and stitch all segments together
                        try:
                            enriched_chunks, token_stats, has_solver_like = parse_and_stitch_segments(
                                segment_responses
                            )

                            # Aggregate metadata from all segments
                            judge_metadata = {
                                "model": segment_metadata[0].get("model"),
                                "temperature": segment_metadata[0].get("temperature"),
                                "max_output_tokens": segment_metadata[0].get("max_output_tokens"),
                                "finish_reason": segment_metadata[-1].get("finish_reason"),
                                "attempts": sum(m.get("attempts", 1) for m in segment_metadata),
                            }

                        except ValueError as e:
                            print(f"\n  ⚠ Failed to parse segments for {example_id}: {str(e)}")
                            enriched_chunks = []
                            token_stats = {
                                "encoding": "cl100k_base",
                                "reasoning_total_tokens": 0,
                                "solver_like_total_tokens": 0,
                                "sound_total_tokens": 0,
                                "solver_like_fraction": 0.0,
                            }
                            has_solver_like = False
                            judge_metadata = {"error": f"Segment parsing failed: {str(e)}"}

                    else:
                        # Normal single-call path
                        time_since_last_request = time.time() - last_request_time
                        if last_request_time > 0 and time_since_last_request < min_request_interval:
                            sleep_time = min_request_interval - time_since_last_request
                            time.sleep(sleep_time)

                        # Call judge
                        last_request_time = time.time()
                        judge_result = call_judge(
                            reasoning_text=reasoning_before_code,
                            judge_prompt_path=judge_prompt_path,
                        )

                        raw_response = judge_result["raw_response"]
                        judge_metadata = judge_result["metadata"]

                        # Parse judge response
                        try:
                            parsed_response = parse_judge_response(raw_response)
                            chunks = parsed_response["chunk_analysis"]
                        except ValueError as e:
                            print(f"\n  ⚠ Failed to parse judge response for {example_id}: {str(e)}")
                            chunks = []

                        # Enrich with tokens
                        enriched_chunks, token_stats = enrich_chunks_with_tokens(chunks)
                        has_solver_like = has_solver_like_chunks(chunks)

                    # Build result
                    result = {
                        "example_id": example_id,
                        "reasoning_before_code": reasoning_before_code,
                        "chunk_analysis": enriched_chunks,
                        "token_statistics": token_stats,
                        "has_solver_like": has_solver_like,
                        "judge_metadata": judge_metadata,
                    }

                    writer.write_example(result)

                    # Update counts
                    if has_solver_like:
                        examples_with_solver_like += 1
                    else:
                        examples_sound_only += 1

                    total_chunks += len(enriched_chunks)

                except Exception as e:
                    # Print detailed error
                    import traceback
                    print(f"\n❌ Error chunking {example.get('example_id', '?')}:")
                    print(f"   {type(e).__name__}: {str(e)}")
                    traceback.print_exc()

                    # Write error result
                    result = {
                        "example_id": example.get("example_id", "unknown"),
                        "reasoning_before_code": example.get("reasoning_before_code", ""),
                        "chunk_analysis": [],
                        "token_statistics": {
                            "encoding": "cl100k_base",
                            "reasoning_total_tokens": 0,
                            "solver_like_total_tokens": 0,
                            "sound_total_tokens": 0,
                            "solver_like_fraction": 0.0,
                        },
                        "has_solver_like": False,
                        "judge_metadata": {
                            "error": str(e),
                            "error_type": type(e).__name__
                        },
                    }
                    writer.write_example(result)
                    examples_sound_only += 1

                progress.update(1)
                progress.set_postfix(solver_like=examples_with_solver_like, sound=examples_sound_only)

        # Finalize with summary
        summary = {
            "total_examples": len(examples),
            "examples_with_solver_like": examples_with_solver_like,
            "examples_sound_only": examples_sound_only,
            "examples_split_into_segments": examples_split,
            "total_chunks": total_chunks,
        }
        writer.finalize_with_summary(summary)

    print(f"\n✓ Sequential chunking complete!")
    print(f"  Examples with solver-like: {examples_with_solver_like}/{len(examples)}")
    print(f"  Examples sound only: {examples_sound_only}/{len(examples)}")
    print(f"  Examples split into segments: {examples_split}/{len(examples)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run chunking pipeline (batch mode by default, sequential with --sequential)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Batch mode (default, fast):
  python src/run_chunking.py \\
      --input output/deepseek/calendar/baseline_execution.json \\
      --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \\
      --gcs-bucket my-vertex-batch-bucket

  # Sequential mode (slower, no GCS needed):
  python src/run_chunking.py \\
      --input output/deepseek/calendar/baseline_execution.json \\
      --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \\
      --sequential
        """
    )

    parser.add_argument(
        "--input",
        "--execution-json",
        required=True,
        dest="execution_json",
        help="Path to execution JSON output"
    )
    parser.add_argument(
        "--judge-prompt",
        required=True,
        help="Path to judge prompt file"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Use sequential mode (one-by-one API calls) instead of batch mode"
    )
    parser.add_argument(
        "--gcs-bucket",
        help="GCS bucket name for batch I/O (required for batch mode, ignored for sequential)"
    )
    parser.add_argument(
        "--gcs-prefix",
        help="Optional GCS prefix for batch mode (defaults to judge-batch/<timestamp>)"
    )

    args = parser.parse_args()

    try:
        if args.sequential:
            # Sequential mode - no GCS required
            run_sequential_chunking_pipeline(
                args.execution_json,
                args.judge_prompt,
            )
        else:
            # Batch mode (default) - GCS required
            gcs_bucket = args.gcs_bucket or os.getenv("JUDGE_VERTEX_GCS_BUCKET")

            if not gcs_bucket:
                print("❌ ERROR: --gcs-bucket is required for batch mode")
                print("   Either:")
                print("   1. Provide --gcs-bucket your-bucket")
                print("   2. Set JUDGE_VERTEX_GCS_BUCKET in .env")
                print("   3. Use --sequential flag (no GCS needed)")
                sys.exit(1)

            run_batch_chunking_pipeline(
                args.execution_json,
                args.judge_prompt,
                gcs_bucket,
                args.gcs_prefix,
            )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
