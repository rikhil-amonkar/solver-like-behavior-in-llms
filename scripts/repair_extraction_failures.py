#!/usr/bin/env python3
"""
Repair script for inference examples with code extraction failures.

Re-extracts code from reasoning traces and re-executes it for affected examples.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from general.parsing_utils import split_reasoning_and_code
from inference.code_executor import execute_code_by_language, get_language_from_task


# Affected examples from analysis
AFFECTED_EXAMPLES = {
    "output/gpt/calendar/baseline_inference.json": [
        "calendar_scheduling_example_543",
        "calendar_scheduling_example_544",
    ],
    "output/gpt/meeting/baseline_inference.json": [
        "meeting_planning_example_867",
        "meeting_planning_example_978",
        "meeting_planning_example_956",
        "meeting_planning_example_73",
        "meeting_planning_example_900",
        "meeting_planning_example_98",
        "meeting_planning_example_800",
        "meeting_planning_example_174",
        "meeting_planning_example_937",
        "meeting_planning_example_835",
        "meeting_planning_example_592",
    ],
}


def repair_inference_file(json_path: str, affected_ids: list):
    """
    Repair code extraction failures in an inference JSON file.

    Args:
        json_path: Path to inference JSON file
        affected_ids: List of example IDs to repair
    """
    json_path = Path(json_path)

    # Determine task from path
    if "calendar" in str(json_path):
        task = "calendar"
    elif "meeting" in str(json_path):
        task = "meeting"
    elif "zebralogic" in str(json_path):
        task = "zebralogic"
    elif "blocksworld" in str(json_path):
        task = "blocksworld"
    else:
        raise ValueError(f"Cannot determine task from path: {json_path}")

    language = get_language_from_task(task)

    print(f"\n=== Repairing {json_path.name} ===")
    print(f"Task: {task}, Language: {language}")
    print(f"Affected examples: {len(affected_ids)}")

    # Load JSON
    with open(json_path, 'r') as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    examples = data.get("examples", [])

    # Track repairs
    repaired_count = 0
    not_found_count = 0

    # Process each example
    for example in examples:
        example_id = example.get("example_id")

        if example_id not in affected_ids:
            continue

        print(f"\n  Processing {example_id}...")

        # Check if code is already extracted
        if example.get("extracted_code", "").strip():
            print(f"    ⚠️  Code already extracted, skipping")
            continue

        # Re-extract code
        reasoning_trace = example.get("reasoning_trace", "")

        if not reasoning_trace.strip():
            print(f"    ❌ No reasoning trace found")
            not_found_count += 1
            continue

        reasoning_before_code, extracted_code = split_reasoning_and_code(reasoning_trace)

        if not extracted_code.strip():
            print(f"    ❌ Still cannot extract code (heuristic failed)")
            not_found_count += 1
            continue

        print(f"    ✓ Code extracted ({len(extracted_code)} chars)")

        # Execute code
        try:
            extra_kwargs = {}
            if task == "zebralogic":
                # Would need problem_data, but meeting/calendar don't need it
                pass

            code_result = execute_code_by_language(
                extracted_code,
                language=language,
                timeout_sec=30.0,
                **extra_kwargs
            )

            print(f"    ✓ Code executed (exit_code={code_result.get('exit_code')})")

            # Update example
            example["reasoning_before_code"] = reasoning_before_code
            example["extracted_code"] = extracted_code
            example["code_execution"] = code_result

            repaired_count += 1

        except Exception as e:
            print(f"    ❌ Execution failed: {e}")
            not_found_count += 1

    # Save repaired JSON
    if repaired_count > 0:
        with open(json_path, 'w') as f:
            json.dump({"metadata": metadata, "examples": examples}, f, indent=2)
        print(f"\n✓ Repaired {repaired_count} examples in {json_path.name}")
    else:
        print(f"\n⚠️  No examples repaired in {json_path.name}")

    return repaired_count, not_found_count


def main():
    print("\n=== Code Extraction Repair Script ===\n")

    total_repaired = 0
    total_failed = 0
    repaired_files = []

    script_dir = Path(__file__).parent.parent
    for json_path, affected_ids in AFFECTED_EXAMPLES.items():
        full_path = script_dir / json_path

        if not full_path.exists():
            print(f"\n⚠️  Skipping {json_path} (file not found)")
            continue

        repaired, failed = repair_inference_file(str(full_path), affected_ids)

        if repaired > 0:
            repaired_files.append(json_path)

        total_repaired += repaired
        total_failed += failed

    print("\n" + "="*50)
    print(f"\n✓ Repair complete!")
    print(f"  Total repaired: {total_repaired}")
    print(f"  Total failed: {total_failed}")
    print(f"\nFiles modified:")
    for f in repaired_files:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
