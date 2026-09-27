#!/usr/bin/env python3
"""
Reformat existing chunking JSON to make segmented traces seamless.

This script removes all segment metadata from chunking JSON files,
making split reasoning traces appear as if they were never segmented.
"""

import json
import sys
from pathlib import Path


def reformat_chunking_file(input_path: str, output_path: str = None):
    """
    Reformat chunking JSON to remove segment metadata.

    Args:
        input_path: Path to existing chunking JSON
        output_path: Path to save reformatted JSON (defaults to overwriting input)
    """
    if output_path is None:
        output_path = input_path

    print(f"Loading: {input_path}")
    with open(input_path, 'r') as f:
        data = json.load(f)

    # Track statistics
    total_examples = len(data.get("examples", []))
    segmented_examples = 0
    fixed_examples = 0

    # Process each example
    for example in data.get("examples", []):
        original_metadata = example.get("judge_metadata", {})
        original_token_stats = example.get("token_statistics", {})

        # Check if this was a segmented example
        was_segmented = (
            "segments" in original_metadata or
            "num_segments" in original_metadata or
            "num_segments" in original_token_stats or
            "was_split" in original_token_stats or
            "original_reasoning_tokens" in original_token_stats or
            "original_tokens" in original_metadata
        )

        if was_segmented:
            segmented_examples += 1

            # Clean judge_metadata
            if "segments" in original_metadata:
                # Extract aggregated metadata from segments
                segments = original_metadata["segments"]

                new_metadata = {
                    "model": segments[0].get("model") if segments else original_metadata.get("model"),
                    "temperature": segments[0].get("temperature") if segments else original_metadata.get("temperature"),
                    "max_output_tokens": segments[0].get("max_output_tokens") if segments else original_metadata.get("max_output_tokens"),
                    "finish_reason": segments[-1].get("finish_reason") if segments else original_metadata.get("finish_reason"),
                    "attempts": sum(s.get("attempts", 1) for s in segments) if segments else original_metadata.get("attempts", 1),
                }

                # Preserve error if present
                if "error" in original_metadata:
                    new_metadata["error"] = original_metadata["error"]

                example["judge_metadata"] = new_metadata
                fixed_examples += 1

            elif "error" in original_metadata:
                # Error case - keep minimal metadata
                new_metadata = {}
                if "error" in original_metadata:
                    # Clean up error message to remove segment references
                    error_msg = original_metadata["error"]
                    new_metadata["error"] = error_msg

                example["judge_metadata"] = new_metadata
                fixed_examples += 1

            # Clean token_statistics
            new_token_stats = {
                "encoding": original_token_stats.get("encoding", "cl100k_base"),
                "reasoning_total_tokens": original_token_stats.get("reasoning_total_tokens", 0),
                "solver_like_total_tokens": original_token_stats.get("solver_like_total_tokens", 0),
                "sound_total_tokens": original_token_stats.get("sound_total_tokens", 0),
                "solver_like_fraction": original_token_stats.get("solver_like_fraction", 0.0),
            }

            # Remove segment-related keys
            for key in ["num_segments", "was_split", "parse_failures", "original_reasoning_tokens", "parse_error"]:
                if key in original_token_stats:
                    # Already removed by only including specific keys above
                    pass

            example["token_statistics"] = new_token_stats

    # Clean run_metadata if needed
    if "num_examples_fixed" in data.get("run_metadata", {}):
        del data["run_metadata"]["num_examples_fixed"]
    if "last_fix_timestamp" in data.get("run_metadata", {}):
        del data["run_metadata"]["last_fix_timestamp"]

    # Save reformatted data
    print(f"Saving to: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Print summary
    print(f"\n✓ Reformatting complete!")
    print(f"  Total examples: {total_examples}")
    print(f"  Segmented examples found: {segmented_examples}")
    print(f"  Examples reformatted: {fixed_examples}")
    print(f"  Output: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python reformat_chunking_seamless.py <chunking_json_path> [output_path]")
        print("\nExample:")
        print("  python extras/reformat_chunking_seamless.py output/deepseek/calendar/baseline_chunking.json")
        print("  python extras/reformat_chunking_seamless.py input.json output.json")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(input_path).exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    reformat_chunking_file(input_path, output_path)


if __name__ == "__main__":
    main()
