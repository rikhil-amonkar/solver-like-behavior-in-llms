#!/usr/bin/env python3
"""
Chunking pipeline runner.

Uses Gemini judge to classify reasoning traces into sound vs solver-like chunks.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, get_timestamp, IncrementalJSONWriter, make_path_relative
from general.cli import ProgressTracker
from chunking.judge_caller import call_judge
from chunking.chunk_parser import (
    parse_judge_response,
    enrich_chunks_with_tokens,
    has_solver_like_chunks,
    parse_and_stitch_segments,
)
from chunking.reasoning_splitter import (
    should_split_reasoning,
    split_reasoning_by_tokens,
    count_tokens,
)
import time


def run_chunking_pipeline(
    inference_json_path: str,
    judge_prompt_path: str,
    fix_mode: bool = False,
):
    """
    Run chunking pipeline on inference results.

    Args:
        inference_json_path: Path to inference JSON output
        judge_prompt_path: Path to judge prompt file
        fix_mode: If True, only re-process examples with empty chunk_analysis from existing chunking file
    """
    print(f"\n=== Chunking Pipeline {'(Fix Mode)' if fix_mode else ''} ===")
    print(f"Input: {inference_json_path}")
    print(f"Judge prompt: {judge_prompt_path}\n")

    # Validate environment variables for Vertex AI
    import os
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT not set in environment")
        print("   Add to your .env file:")
        print("     GOOGLE_CLOUD_PROJECT=your-project-id")
        print("   Or export it:")
        print("     export GOOGLE_CLOUD_PROJECT=your-project-id")
        sys.exit(1)

    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    print(f"Vertex AI Configuration:")
    print(f"  Project: {project_id}")
    print(f"  Location: {location}")
    print()

    # Determine if we're working with inference or chunking file
    if fix_mode:
        # If user provided inference file, derive chunking file path
        input_path = Path(inference_json_path)

        # Check if input is inference or chunking file
        if "_inference.json" in input_path.name:
            # Derive chunking file path
            condition = input_path.name.replace("_inference.json", "").replace("inference.json", "baseline")
            chunking_path = input_path.parent / f"{condition}_chunking.json"

            if not chunking_path.exists():
                print(f"❌ ERROR: Chunking file not found: {chunking_path}")
                print(f"   Run chunking first without --fix flag, or check file path.")
                sys.exit(1)

            print(f"Detected inference file, loading chunking file: {chunking_path}")
            chunking_data = load_json_file(str(chunking_path))
            actual_chunking_path = chunking_path
        else:
            # Assume it's already a chunking file
            print("Loading existing chunking results...")
            chunking_data = load_json_file(inference_json_path)
            actual_chunking_path = input_path

        task = chunking_data["run_metadata"]["task"]
        model = chunking_data["run_metadata"]["model"]
        condition = chunking_data["run_metadata"].get("condition", "baseline")

        # Filter examples with empty chunk_analysis
        all_examples = chunking_data["examples"]
        examples_to_fix = [ex for ex in all_examples if not ex.get("chunk_analysis")]

        print(f"Task: {task}")
        print(f"Model: {model}")
        print(f"Condition: {condition}")
        print(f"Total examples: {len(all_examples)}")
        print(f"Examples to fix (empty chunk_analysis): {len(examples_to_fix)}")

        if not examples_to_fix:
            print("\n✓ No examples to fix - all have chunk_analysis!")
            return

        examples = examples_to_fix
        all_examples_for_output = all_examples

        # Output path is the chunking file (we'll overwrite)
        output_path = actual_chunking_path
        print(f"Output: {output_path} (will update in place)\n")
    else:
        # Load inference results
        print("Loading inference results...")
        inference_data = load_json_file(inference_json_path)

        task = inference_data["run_metadata"]["task"]
        model = inference_data["run_metadata"]["model"]
        condition = inference_data["run_metadata"].get("condition", "baseline")
        examples = inference_data["examples"]

        print(f"Task: {task}")
        print(f"Model: {model}")
        print(f"Condition: {condition}")
        print(f"Examples: {len(examples)}")

        # Determine output path (use same condition as inference)
        inference_path = Path(inference_json_path)
        output_filename = f"{condition}_chunking.json"
        output_path = inference_path.parent / output_filename
        print(f"Output: {output_path}\n")

        all_examples_for_output = None

    # Build metadata
    import os
    judge_model = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")
    max_judge_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    if fix_mode:
        # Preserve existing metadata, update timestamp
        metadata = chunking_data["run_metadata"].copy()
        metadata["last_fix_timestamp"] = get_timestamp()
        metadata["num_examples_fixed"] = len(examples)
    else:
        metadata = {
            "task": task,
            "model": model,
            "condition": condition,
            "inference_json": make_path_relative(str(inference_json_path)),
            "judge_model": judge_model,
            "judge_prompt": judge_prompt_path,
            "timestamp": get_timestamp(),
            "num_examples": len(examples),
            "max_judge_tokens": max_judge_tokens,
        }

    # Process examples
    examples_with_solver_like = 0
    examples_sound_only = 0
    total_chunks = 0
    examples_split = 0

    # Rate limiting: ~2.5 seconds between requests to avoid hitting Vertex AI rate limits
    # More conservative to handle retry backoffs better
    last_request_time = 0
    min_request_interval = 2.5  # seconds

    with IncrementalJSONWriter(str(output_path), metadata) as writer:
        # In fix mode, first write all non-fixed examples as-is
        if fix_mode:
            for ex in all_examples_for_output:
                if ex.get("chunk_analysis"):  # Already has chunks, keep as-is
                    writer.write_example(ex)

        with ProgressTracker(len(examples), f"{'Fixing' if fix_mode else 'Chunking'} {task}") as progress:
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
                        # Split reasoning into segments
                        segments = split_reasoning_by_tokens(reasoning_before_code)
                        print(f"\n  ℹ {example_id}: Splitting {reasoning_tokens} tokens into {len(segments)} segments")
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
                            # Fallback: empty chunks
                            enriched_chunks = []
                            token_stats = {
                                "encoding": "cl100k_base",
                                "reasoning_total_tokens": 0,
                                "solver_like_total_tokens": 0,
                                "sound_total_tokens": 0,
                                "solver_like_fraction": 0.0,
                            }
                            has_solver_like = False
                            judge_metadata = {
                                "error": f"Segment parsing failed: {str(e)}",
                            }

                    else:
                        # Normal single-call path (no splitting needed)
                        # Rate limiting
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

                        # Check if judge hit MAX_TOKENS - if so, retry with splitting
                        finish_reason = judge_metadata.get("finish_reason")
                        if finish_reason == "FinishReason.MAX_TOKENS":
                            print(f"\n  ℹ {example_id}: Judge hit MAX_TOKENS, retrying with splitting...")

                            # Split and retry
                            segments = split_reasoning_by_tokens(reasoning_before_code)
                            examples_split += 1

                            segment_responses = []
                            segment_metadata = []

                            for seg_idx, segment in enumerate(segments):
                                # Rate limiting
                                time_since_last_request = time.time() - last_request_time
                                if last_request_time > 0 and time_since_last_request < min_request_interval:
                                    sleep_time = min_request_interval - time_since_last_request
                                    time.sleep(sleep_time)

                                last_request_time = time.time()
                                seg_result = call_judge(
                                    reasoning_text=segment,
                                    judge_prompt_path=judge_prompt_path,
                                )

                                segment_responses.append(seg_result["raw_response"])
                                segment_metadata.append(seg_result["metadata"])

                            # Parse and stitch segments
                            try:
                                enriched_chunks, token_stats, has_solver_like = parse_and_stitch_segments(
                                    segment_responses
                                )
                                judge_metadata = {
                                    "model": segment_metadata[0].get("model"),
                                    "temperature": segment_metadata[0].get("temperature"),
                                    "max_output_tokens": segment_metadata[0].get("max_output_tokens"),
                                    "finish_reason": segment_metadata[-1].get("finish_reason"),
                                    "attempts": sum(m.get("attempts", 1) for m in segment_metadata),
                                }
                            except ValueError as e:
                                print(f"\n  ⚠ Failed to parse segments after MAX_TOKENS retry for {example_id}: {str(e)}")
                                enriched_chunks = []
                                token_stats = {
                                    "encoding": "cl100k_base",
                                    "reasoning_total_tokens": 0,
                                    "solver_like_total_tokens": 0,
                                    "sound_total_tokens": 0,
                                    "solver_like_fraction": 0.0,
                                }
                                has_solver_like = False
                                judge_metadata = {
                                    "error": f"Segment parsing failed after MAX_TOKENS retry: {str(e)}",
                                }
                        else:
                            # Normal path - no MAX_TOKENS issue
                            # Parse judge response
                            try:
                                parsed_response = parse_judge_response(raw_response)
                                chunks = parsed_response["chunk_analysis"]
                            except ValueError as e:
                                print(f"\n  ⚠ Failed to parse judge response for {example_id}: {str(e)}")
                                # Use empty chunks
                                chunks = []

                            # Enrich with tokens
                            enriched_chunks, token_stats = enrich_chunks_with_tokens(chunks)

                            # Check for solver-like
                            has_solver_like = has_solver_like_chunks(chunks)

                    # Build result (use enriched chunks as the main chunk_analysis)
                    result = {
                        "example_id": example_id,
                        "reasoning_before_code": reasoning_before_code,
                        "chunk_analysis": enriched_chunks,  # Only enriched version
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
                    # Print detailed error to terminal
                    import traceback
                    print(f"\n❌ Error chunking {example.get('example_id', '?')}:")
                    print(f"   {type(e).__name__}: {str(e)}")
                    if "--verbose" in sys.argv:
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

    # Print summary
    if fix_mode:
        print(f"\n✓ Fix complete!")
        print(f"  Fixed examples: {len(examples)}")
        print(f"  Examples with solver-like: {examples_with_solver_like}/{len(examples)}")
        print(f"  Examples sound only: {examples_sound_only}/{len(examples)}")
        print(f"  Examples split into segments: {examples_split}/{len(examples)}")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Output: {output_path}")
    else:
        print(f"\n✓ Chunking complete!")
        print(f"  Examples with solver-like: {examples_with_solver_like}/{len(examples)}")
        print(f"  Examples sound only: {examples_sound_only}/{len(examples)}")
        print(f"  Examples split into segments: {examples_split}/{len(examples)}")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run chunking pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/run_chunking.py --input output/deepseek/calendar/inference.json \\
                              --judge-prompt prompts/llm_as_judge_for_chunking.txt
        """
    )

    parser.add_argument(
        "--input",
        "--inference-json",
        required=True,
        dest="inference_json",
        help="Path to inference JSON output"
    )
    parser.add_argument(
        "--judge-prompt",
        required=True,
        help="Path to judge prompt file"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix mode: re-process only examples with empty chunk_analysis from existing chunking file"
    )

    args = parser.parse_args()

    try:
        run_chunking_pipeline(
            args.inference_json,
            args.judge_prompt,
            fix_mode=args.fix,
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
