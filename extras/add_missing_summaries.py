#!/usr/bin/env python3
"""
Add missing summary fields to existing pipeline JSONs.

This script retroactively adds summary statistics to JSONs that were
generated before the summary feature was implemented.

Usage:
    python extras/add_missing_summaries.py <json_file>
    python extras/add_missing_summaries.py --all
"""

import json
import sys
from pathlib import Path
from collections import OrderedDict


def compute_inference_summary(data: dict) -> dict:
    """Compute summary for inference JSON."""
    examples = data.get('examples', [])

    successful = sum(1 for ex in examples if 'reasoning_trace' in ex and ex['reasoning_trace'])
    errors = len(examples) - successful

    return {
        "total_examples": len(examples),
        "successful": successful,
        "errors": errors,
    }


def compute_execution_summary(data: dict) -> dict:
    """Compute summary for execution JSON."""
    examples = data.get('examples', [])

    successful = sum(1 for ex in examples
                     if ex.get('code_execution', {}).get('exit_code') == 0)
    failed = len(examples) - successful

    return {
        "total_examples": len(examples),
        "successful_executions": successful,
        "failed_executions": failed,
    }


def compute_chunking_summary(data: dict) -> dict:
    """Compute summary for chunking JSON."""
    examples = data.get('examples', [])

    with_solver_like = sum(1 for ex in examples if ex.get('has_solver_like', False))
    sound_only = len(examples) - with_solver_like

    split = sum(1 for ex in examples
                if ex.get('chunk_analysis', {}).get('num_chunks', 0) > 1)

    total_chunks = sum(ex.get('chunk_analysis', {}).get('num_chunks', 0)
                       for ex in examples)

    return {
        "total_examples": len(examples),
        "examples_with_solver_like": with_solver_like,
        "examples_sound_only": sound_only,
        "examples_split_into_segments": split,
        "total_chunks": total_chunks,
    }


def detect_json_type(data: dict) -> str:
    """
    Detect what type of pipeline JSON this is.

    Returns:
        'inference', 'execution', 'evaluation', 'chunking', or 'unknown'
    """
    metadata = data.get('run_metadata', {})

    # Check metadata fields
    if 'execution_json' in metadata:
        return 'evaluation'
    elif 'inference_json' in metadata:
        if 'judge_prompt' in metadata:
            return 'chunking'
        else:
            return 'execution'

    # Check example structure
    examples = data.get('examples', [])
    if not examples:
        return 'unknown'

    first_ex = examples[0]

    if 'chunk_analysis' in first_ex:
        return 'chunking'
    elif 'code_execution' in first_ex and 'reasoning_before_code' in first_ex:
        return 'execution'
    elif 'validation' in first_ex or 'is_correct' in first_ex:
        return 'evaluation'
    elif 'reasoning_trace' in first_ex:
        return 'inference'

    return 'unknown'


def add_summary_to_json(json_path: Path, backup: bool = True) -> bool:
    """
    Add summary to JSON if missing.

    Args:
        json_path: Path to JSON file
        backup: Whether to create backup

    Returns:
        True if summary was added, False if already present or error
    """
    if not json_path.exists():
        print(f"✗ File not found: {json_path}")
        return False

    try:
        # Read JSON
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        # Check if summary already exists
        if 'summary' in data:
            print(f"✓ Already has summary: {json_path.name}")
            return False

        # Detect JSON type
        json_type = detect_json_type(data)

        if json_type == 'unknown':
            print(f"⚠ Unknown JSON type: {json_path.name}")
            return False

        # Compute summary based on type
        if json_type == 'inference':
            summary = compute_inference_summary(data)
        elif json_type == 'execution':
            summary = compute_execution_summary(data)
        elif json_type == 'chunking':
            summary = compute_chunking_summary(data)
        elif json_type == 'evaluation':
            # Evaluation JSONs should already have summaries from the pipeline
            print(f"⊘ Evaluation JSON (should have summary): {json_path.name}")
            return False
        else:
            print(f"⚠ Unsupported type '{json_type}': {json_path.name}")
            return False

        # Create backup if requested
        if backup:
            backup_path = json_path.with_suffix('.json.bak')
            with backup_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write('\n')
            print(f"  → Backup: {backup_path.name}")

        # Add summary with correct key ordering
        ordered = OrderedDict()
        ordered['run_metadata'] = data['run_metadata']
        ordered['summary'] = summary
        ordered['examples'] = data['examples']

        # Add any other keys
        for key in data:
            if key not in ordered:
                ordered[key] = data[key]

        # Write updated JSON
        with json_path.open('w', encoding='utf-8') as f:
            json.dump(ordered, f, indent=2, ensure_ascii=False)
            f.write('\n')

        print(f"✓ Added {json_type} summary: {json_path.name}")
        print(f"  Summary: {summary}")
        return True

    except Exception as e:
        print(f"✗ Error: {json_path.name}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    repo_root = Path(__file__).parent.parent

    if sys.argv[1] == '--all':
        # Process all JSONs in output/
        output_dir = repo_root / 'output'
        json_files = sorted(output_dir.rglob('*.json'))

        # Skip .bak files
        json_files = [f for f in json_files if not f.name.endswith('.bak')]

        if not json_files:
            print("No JSON files found in output/")
            sys.exit(0)

        print(f"Found {len(json_files)} JSON files\n")

        added = 0
        skipped = 0

        for json_path in json_files:
            result = add_summary_to_json(json_path, backup=True)
            if result:
                added += 1
            else:
                skipped += 1
            print()

        print(f"{'='*60}")
        print(f"Summary added: {added}")
        print(f"Skipped: {skipped}")

    else:
        # Process single file
        json_path = Path(sys.argv[1])
        if not json_path.is_absolute():
            json_path = repo_root / json_path

        add_summary_to_json(json_path, backup=True)


if __name__ == '__main__':
    main()
