#!/usr/bin/env python3
"""
Categorization pipeline runner.

Takes chunked reasoning traces and categorizes ONLY the solver-like chunks
to determine if they used state-machine simulation or brute-force search.

Default mode: Batch processing (fast, parallel via Vertex AI Batch API)
Sequential mode: One-by-one processing (--sequential flag)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import load_json_file, get_timestamp, make_path_relative, IncrementalJSONWriter
from general.cli import ProgressTracker
from categorization.vertex_batch_categorize import (
    prepare_batch_categorization_requests,
    submit_batch_job,
    poll_batch_job,
    parse_batch_results
)
from categorization.category_parser import parse_categorization_response
import json
import os


def extract_solver_like_chunks(chunking_data: dict) -> list[dict]:
    """
    Extract only solver-like chunks from chunking output.

    Args:
        chunking_data: Loaded chunking JSON data

    Returns:
        List of dicts with example_id, chunk_index, chunk_text for each solver-like chunk
    """
    solver_chunks = []

    for example in chunking_data["examples"]:
        example_id = example["example_id"]
        chunk_analysis = example.get("chunk_analysis", [])

        for chunk_idx, chunk in enumerate(chunk_analysis):
            # Check if this chunk is solver-like
            if "solver-like" in chunk:
                solver_chunks.append({
                    "example_id": example_id,
                    "chunk_index": chunk_idx,
                    "chunk_text": chunk["solver-like"]
                })

    return solver_chunks


def run_batch_categorization_pipeline(
    chunking_json_path: str,
    categorization_prompt_path: str,
    gcs_bucket: str,
    gcs_prefix: str = None,
):
    """
    Run batch categorization pipeline on solver-like chunks.

    Args:
        chunking_json_path: Path to chunking JSON output
        categorization_prompt_path: Path to categorization prompt file
        gcs_bucket: GCS bucket name for batch I/O
        gcs_prefix: Optional GCS prefix (defaults to categorize-batch/<timestamp>)
    """
    print(f"\n=== Batch Categorization Pipeline ===")
    print(f"Input: {chunking_json_path}")
    print(f"Categorization prompt: {categorization_prompt_path}")
    print(f"GCS bucket: {gcs_bucket}\n")

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

    # Load chunking results
    print("Loading chunking results...")
    chunking_data = load_json_file(chunking_json_path)

    task = chunking_data["run_metadata"]["task"]
    model = chunking_data["run_metadata"]["model"]
    condition = chunking_data["run_metadata"].get("condition", "baseline")
    total_examples = chunking_data["run_metadata"]["num_examples"]

    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Total examples: {total_examples}")

    # Extract solver-like chunks
    print("\nExtracting solver-like chunks...")
    solver_chunks = extract_solver_like_chunks(chunking_data)

    if not solver_chunks:
        print("⚠ No solver-like chunks found in input. Nothing to categorize.")
        sys.exit(0)

    print(f"Found {len(solver_chunks)} solver-like chunks across examples")

    # Count unique examples with solver-like chunks
    unique_examples = len(set(chunk["example_id"] for chunk in solver_chunks))
    print(f"  From {unique_examples} unique examples")

    # Determine output path
    chunking_path = Path(chunking_json_path)
    output_filename = f"{condition}_categorization.json"
    output_path = chunking_path.parent / output_filename
    print(f"Output: {output_path}\n")

    # Load categorization prompt
    categorization_prompt = Path(categorization_prompt_path).read_text(encoding="utf-8")

    # Prepare batch requests
    print("Preparing batch requests...")
    max_judge_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    requests = prepare_batch_categorization_requests(
        solver_chunks,
        categorization_prompt,
        max_output_tokens=max_judge_tokens
    )

    print(f"Total batch requests: {len(requests)}")

    # Setup GCS paths
    timestamp = get_timestamp()
    if gcs_prefix is None:
        gcs_prefix = f"categorize-batch/{model}/{task}/{condition}/{timestamp}"

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
        display_name=f"categorize-{model}-{task}-{condition}"
    )

    print(f"Batch job created: {batch_job.name}")
    print(f"State: {batch_job.state}")

    # Poll until complete
    print("\nWaiting for batch job to complete...")
    print("(This may take 10-30 minutes depending on number of solver-like chunks)")

    completed_job = poll_batch_job(
        batch_job_name=batch_job.name,
        poll_interval=30,
        max_wait=2592000  # 30 days max (effectively unlimited)
    )

    print(f"\n✓ Batch job completed!")
    print(f"  Duration: {(completed_job.end_time - completed_job.start_time).total_seconds():.0f}s")

    # Download and parse results
    print("\nDownloading batch results from GCS...")
    batch_results = parse_batch_results(output_gcs_uri_prefix)

    print(f"Retrieved {len(batch_results)} responses")

    # Map results back to solver chunks
    print("\nProcessing results...")
    categorization_results = []

    for idx, result in enumerate(batch_results):
        # Extract response text from Vertex AI format
        response_text = ""

        if "response" in result and "candidates" in result["response"]:
            candidate = result["response"]["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                response_text = candidate["content"]["parts"][0].get("text", "")

        # Map by index since batch results are returned in same order as input
        if idx < len(solver_chunks):
            chunk_info = solver_chunks[idx]

            # Parse categorization response
            try:
                categorization = parse_categorization_response(response_text)
            except ValueError as e:
                print(f"  ⚠ Failed to parse categorization for {chunk_info['example_id']}, chunk {chunk_info['chunk_index']}: {str(e)}")
                categorization = {
                    "state_machine_simulation": False,
                    "brute_force_search": False,
                    "led_to_hardcoded_answer": [False, False],
                    "error": str(e)
                }

            categorization_results.append({
                "example_id": chunk_info["example_id"],
                "chunk_index": chunk_info["chunk_index"],
                "categorization": categorization,
            })

    # Build metadata
    judge_model = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")

    metadata = {
        "task": task,
        "model": model,
        "condition": condition,
        "chunking_json": make_path_relative(str(chunking_json_path)),
        "judge_model": judge_model,
        "categorization_prompt": categorization_prompt_path,
        "timestamp": timestamp,
        "total_examples": total_examples,
        "examples_with_solver_like": unique_examples,
        "total_solver_like_chunks": len(solver_chunks),
        "max_judge_tokens": max_judge_tokens,
        "batch_job_name": batch_job.name,
        "gcs_input": input_gcs_uri,
        "gcs_output": output_gcs_uri_prefix,
    }

    # Group results by example_id for output
    examples_output = {}
    for cat_result in categorization_results:
        example_id = cat_result["example_id"]
        if example_id not in examples_output:
            examples_output[example_id] = {
                "example_id": example_id,
                "solver_like_chunks": []
            }

        examples_output[example_id]["solver_like_chunks"].append({
            "chunk_index": cat_result["chunk_index"],
            "categorization": cat_result["categorization"]
        })

    # Write output
    output_data = {
        "run_metadata": metadata,
        "examples": list(examples_output.values()),
        "summary": {
            "total_examples": total_examples,
            "examples_with_solver_like": unique_examples,
            "total_solver_like_chunks": len(solver_chunks),
            "state_machine_count": sum(1 for r in categorization_results if r["categorization"].get("state_machine_simulation", False)),
            "brute_force_count": sum(1 for r in categorization_results if r["categorization"].get("brute_force_search", False)),
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Batch categorization complete!")
    print(f"  Examples with solver-like chunks: {unique_examples}/{total_examples}")
    print(f"  Total solver-like chunks categorized: {len(solver_chunks)}")
    print(f"  State-machine simulation chunks: {output_data['summary']['state_machine_count']}")
    print(f"  Brute-force search chunks: {output_data['summary']['brute_force_count']}")
    print(f"  Output: {output_path}")


def run_sequential_categorization_pipeline(
    chunking_json_path: str,
    categorization_prompt_path: str,
):
    """
    Run sequential categorization pipeline (one chunk at a time).

    Args:
        chunking_json_path: Path to chunking JSON output
        categorization_prompt_path: Path to categorization prompt file
    """
    print(f"\n=== Sequential Categorization Pipeline ===")
    print(f"Input: {chunking_json_path}")
    print(f"Categorization prompt: {categorization_prompt_path}\n")

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

    # Load chunking results
    print("Loading chunking results...")
    chunking_data = load_json_file(chunking_json_path)

    task = chunking_data["run_metadata"]["task"]
    model = chunking_data["run_metadata"]["model"]
    condition = chunking_data["run_metadata"].get("condition", "baseline")
    total_examples = chunking_data["run_metadata"]["num_examples"]

    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Total examples: {total_examples}")

    # Extract solver-like chunks
    print("\nExtracting solver-like chunks...")
    solver_chunks = extract_solver_like_chunks(chunking_data)

    if not solver_chunks:
        print("⚠ No solver-like chunks found in input. Nothing to categorize.")
        sys.exit(0)

    print(f"Found {len(solver_chunks)} solver-like chunks across examples")

    unique_examples = len(set(chunk["example_id"] for chunk in solver_chunks))
    print(f"  From {unique_examples} unique examples")

    # Determine output path
    chunking_path = Path(chunking_json_path)
    output_filename = f"{condition}_categorization.json"
    output_path = chunking_path.parent / output_filename
    print(f"Output: {output_path}\n")

    # Build metadata
    judge_model = os.getenv("VERTEX_JUDGE_BATCH_MODEL", "publishers/google/models/gemini-2.5-pro")
    max_judge_tokens = int(os.getenv("MAX_JUDGE_TOKENS", 65536))

    metadata = {
        "task": task,
        "model": model,
        "condition": condition,
        "chunking_json": make_path_relative(str(chunking_json_path)),
        "judge_model": judge_model,
        "categorization_prompt": categorization_prompt_path,
        "timestamp": get_timestamp(),
        "total_examples": total_examples,
        "examples_with_solver_like": unique_examples,
        "total_solver_like_chunks": len(solver_chunks),
        "max_judge_tokens": max_judge_tokens,
        "mode": "sequential",
    }

    # Process chunks
    import time
    from chunking.vertex_batch_judge import call_vertex_judge

    categorization_results = []
    state_machine_count = 0
    brute_force_count = 0

    # Rate limiting: ~2.5 seconds between requests
    last_request_time = 0
    min_request_interval = 2.5

    with ProgressTracker(len(solver_chunks), f"Categorizing solver-like chunks") as progress:
        for chunk_info in solver_chunks:
            try:
                # Rate limiting
                time_since_last_request = time.time() - last_request_time
                if last_request_time > 0 and time_since_last_request < min_request_interval:
                    sleep_time = min_request_interval - time_since_last_request
                    time.sleep(sleep_time)

                # Call judge for categorization
                last_request_time = time.time()
                judge_result = call_vertex_judge(
                    reasoning_text=chunk_info["chunk_text"],
                    judge_prompt=Path(categorization_prompt_path).read_text(encoding="utf-8"),
                )

                raw_response = judge_result["response_text"]

                # Parse categorization response
                try:
                    categorization = parse_categorization_response(raw_response)
                except ValueError as e:
                    print(f"\n  ⚠ Failed to parse categorization for {chunk_info['example_id']}, chunk {chunk_info['chunk_index']}: {str(e)}")
                    categorization = {
                        "state_machine_simulation": False,
                        "brute_force_search": False,
                        "led_to_hardcoded_answer": [False, False],
                        "error": str(e)
                    }

                # Update counts
                if categorization.get("state_machine_simulation", False):
                    state_machine_count += 1
                if categorization.get("brute_force_search", False):
                    brute_force_count += 1

                categorization_results.append({
                    "example_id": chunk_info["example_id"],
                    "chunk_index": chunk_info["chunk_index"],
                    "categorization": categorization,
                })

            except Exception as e:
                import traceback
                print(f"\n❌ Error categorizing {chunk_info['example_id']}, chunk {chunk_info['chunk_index']}:")
                print(f"   {type(e).__name__}: {str(e)}")
                traceback.print_exc()

                # Write error result
                categorization_results.append({
                    "example_id": chunk_info["example_id"],
                    "chunk_index": chunk_info["chunk_index"],
                    "categorization": {
                        "state_machine_simulation": False,
                        "brute_force_search": False,
                        "led_to_hardcoded_answer": [False, False],
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                })

            progress.update(1)
            progress.set_postfix(state_machine=state_machine_count, brute_force=brute_force_count)

    # Group results by example_id for output
    examples_output = {}
    for cat_result in categorization_results:
        example_id = cat_result["example_id"]
        if example_id not in examples_output:
            examples_output[example_id] = {
                "example_id": example_id,
                "solver_like_chunks": []
            }

        examples_output[example_id]["solver_like_chunks"].append({
            "chunk_index": cat_result["chunk_index"],
            "categorization": cat_result["categorization"]
        })

    # Write output
    output_data = {
        "run_metadata": metadata,
        "examples": list(examples_output.values()),
        "summary": {
            "total_examples": total_examples,
            "examples_with_solver_like": unique_examples,
            "total_solver_like_chunks": len(solver_chunks),
            "state_machine_count": state_machine_count,
            "brute_force_count": brute_force_count,
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Sequential categorization complete!")
    print(f"  Examples with solver-like chunks: {unique_examples}/{total_examples}")
    print(f"  Total solver-like chunks categorized: {len(solver_chunks)}")
    print(f"  State-machine simulation chunks: {state_machine_count}")
    print(f"  Brute-force search chunks: {brute_force_count}")
    print(f"  Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run categorization pipeline on solver-like chunks (batch mode by default, sequential with --sequential)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Batch mode (default, fast):
  python src/run_categorization.py \\
      --input output/deepseek/calendar/baseline_chunking.json \\
      --categorization-prompt prompts/judge/llm_as_judge_for_categorization.txt \\
      --gcs-bucket my-vertex-batch-bucket

  # Sequential mode (slower, no GCS needed):
  python src/run_categorization.py \\
      --input output/deepseek/calendar/baseline_chunking.json \\
      --categorization-prompt prompts/judge/llm_as_judge_for_categorization.txt \\
      --sequential
        """
    )

    parser.add_argument(
        "--input",
        "--chunking-json",
        required=True,
        dest="chunking_json",
        help="Path to chunking JSON output"
    )
    parser.add_argument(
        "--categorization-prompt",
        required=True,
        help="Path to categorization prompt file"
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
        help="Optional GCS prefix for batch mode (defaults to categorize-batch/<timestamp>)"
    )

    args = parser.parse_args()

    try:
        if args.sequential:
            # Sequential mode - no GCS required
            run_sequential_categorization_pipeline(
                args.chunking_json,
                args.categorization_prompt,
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

            run_batch_categorization_pipeline(
                args.chunking_json,
                args.categorization_prompt,
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
