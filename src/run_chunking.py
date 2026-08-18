#!/usr/bin/env python3
"""
Chunking pipeline runner.

Uses Gemini judge to classify reasoning traces into sound vs solver-like chunks.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, get_timestamp, IncrementalJSONWriter
from general.cli import ProgressTracker
from chunking.judge_caller import call_judge
from chunking.chunk_parser import (
    parse_judge_response,
    enrich_chunks_with_tokens,
    has_solver_like_chunks,
)


def run_chunking_pipeline(
    inference_json_path: str,
    judge_prompt_path: str,
):
    """
    Run chunking pipeline on inference results.

    Args:
        inference_json_path: Path to inference JSON output
        judge_prompt_path: Path to judge prompt file
    """
    print(f"\n=== Chunking Pipeline ===")
    print(f"Input: {inference_json_path}")
    print(f"Judge prompt: {judge_prompt_path}\n")

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

    # Build metadata
    import os
    judge_model = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")
    max_judge_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    metadata = {
        "task": task,
        "model": model,
        "condition": condition,
        "inference_json": str(inference_json_path),
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
                            "judge_response": {"chunk_analysis": []},
                            "enriched_chunk_analysis": [],
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

                    # Call judge
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
                        print(f"\nWarning: Failed to parse judge response for {example_id}: {str(e)}")
                        # Use empty chunks
                        chunks = []

                    # Enrich with tokens
                    enriched_chunks, token_stats = enrich_chunks_with_tokens(chunks)

                    # Check for solver-like
                    has_solver_like = has_solver_like_chunks(chunks)

                    # Build result
                    result = {
                        "example_id": example_id,
                        "reasoning_before_code": reasoning_before_code,
                        "judge_response": {"chunk_analysis": chunks},
                        "enriched_chunk_analysis": enriched_chunks,
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

                    total_chunks += len(chunks)

                except Exception as e:
                    print(f"\nError chunking {example.get('example_id', '?')}: {str(e)}")

                    # Write error result
                    result = {
                        "example_id": example.get("example_id", "unknown"),
                        "reasoning_before_code": example.get("reasoning_before_code", ""),
                        "judge_response": {"chunk_analysis": []},
                        "enriched_chunk_analysis": [],
                        "token_statistics": {
                            "encoding": "cl100k_base",
                            "reasoning_total_tokens": 0,
                            "solver_like_total_tokens": 0,
                            "sound_total_tokens": 0,
                            "solver_like_fraction": 0.0,
                        },
                        "has_solver_like": False,
                        "judge_metadata": {"error": str(e)},
                    }
                    writer.write_example(result)
                    examples_sound_only += 1

                progress.update(1)
                progress.set_postfix(solver_like=examples_with_solver_like, sound=examples_sound_only)

    # Print summary
    print(f"\n✓ Chunking complete!")
    print(f"  Examples with solver-like: {examples_with_solver_like}/{len(examples)}")
    print(f"  Examples sound only: {examples_sound_only}/{len(examples)}")
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

    args = parser.parse_args()

    try:
        run_chunking_pipeline(
            args.inference_json,
            args.judge_prompt,
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
