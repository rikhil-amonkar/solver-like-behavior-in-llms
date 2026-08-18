#!/usr/bin/env python3
"""
Smoke test for chunking pipeline.

Tests chunking on smoke test inference outputs.
"""

import sys
import os
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from general.io_utils import load_json_file, get_timestamp, IncrementalJSONWriter
from general.cli import ProgressTracker
from chunking.judge_caller import call_judge
from chunking.chunk_parser import (
    parse_judge_response,
    enrich_chunks_with_tokens,
    has_solver_like_chunks,
)


def run_smoke_test_chunking():
    """Run smoke test for chunking."""
    print(f"\n{'='*60}")
    print(f"SMOKE TEST: Chunking Pipeline")
    print(f"{'='*60}\n")

    # Find smoke test inference outputs
    test_output_dir = Path(__file__).parent / "output"

    if not test_output_dir.exists():
        print("Error: No smoke test outputs found!")
        print("Run test_inference.py first to generate test data.")
        sys.exit(1)

    # Judge prompt path
    judge_prompt_path = str(repo_root / "prompts" / "llm_as_judge_for_chunking.txt")

    # Test both tasks
    for task in ["calendar", "meeting"]:
        inference_path = test_output_dir / f"smoke_{task}_inference.json"

        if not inference_path.exists():
            print(f"⚠ Skipping {task}: No inference output found")
            continue

        print(f"\n--- Testing {task} ---\n")
        print(f"Input: {inference_path}")

        # Load inference data
        inference_data = load_json_file(str(inference_path))
        examples = inference_data["examples"]

        print(f"Examples: {len(examples)}")

        # Prepare output
        output_path = test_output_dir / f"smoke_{task}_chunking.json"
        print(f"Output: {output_path}")

        # Build metadata
        judge_model = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")
        max_judge_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

        metadata = {
            "task": task,
            "model": inference_data["run_metadata"]["model"],
            "condition": "baseline",
            "test_type": "smoke_test",
            "inference_json": str(inference_path),
            "judge_model": judge_model,
            "judge_prompt": judge_prompt_path,
            "timestamp": get_timestamp(),
            "num_examples": len(examples),
            "max_judge_tokens": max_judge_tokens,
        }

        # Process
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
                        print(f"\nCalling judge for {example_id}...")
                        judge_result = call_judge(
                            reasoning_text=reasoning_before_code,
                            judge_prompt_path=judge_prompt_path,
                        )

                        raw_response = judge_result["raw_response"]
                        judge_metadata = judge_result["metadata"]

                        # Parse response
                        try:
                            parsed_response = parse_judge_response(raw_response)
                            chunks = parsed_response["chunk_analysis"]
                            print(f"✓ Parsed {len(chunks)} chunks")
                        except ValueError as e:
                            print(f"✗ Failed to parse judge response: {str(e)}")
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

                        if has_solver_like:
                            examples_with_solver_like += 1
                        else:
                            examples_sound_only += 1

                        total_chunks += len(chunks)

                    except Exception as e:
                        print(f"\n✗ Error chunking {example.get('example_id')}: {str(e)}")
                        examples_sound_only += 1

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

                    progress.update(1)
                    progress.set_postfix(solver_like=examples_with_solver_like, sound=examples_sound_only)

        print(f"\n✓ {task} chunking complete:")
        print(f"  Solver-like: {examples_with_solver_like}/{len(examples)}")
        print(f"  Sound only: {examples_sound_only}/{len(examples)}")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Output: {output_path}")

    print(f"\n{'='*60}")
    print(f"SMOKE TEST COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        run_smoke_test_chunking()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
