#!/usr/bin/env python3
"""
Reorder JSON keys to put metadata and summary at the top.

Usage:
    python extras/reorder_json_keys.py <json_file>
    python extras/reorder_json_keys.py --all  # Process all complete JSONs in output/

IMPORTANT: This script only processes complete .json files.
           It will NOT touch .jsonl files (those are still running).
"""

import json
import sys
from pathlib import Path
from collections import OrderedDict
from typing import Optional


def reorder_json_keys(data: dict) -> OrderedDict:
    """
    Reorder JSON to put metadata and summary at the top.

    Expected order:
    1. run_metadata (or metadata)
    2. summary (if present)
    3. examples (or data, results, etc.)
    4. Any other keys

    Args:
        data: Original JSON data

    Returns:
        OrderedDict with keys in correct order
    """
    ordered = OrderedDict()

    # 1. Add metadata first (try different key names)
    metadata_keys = ['run_metadata', 'metadata', 'meta']
    for key in metadata_keys:
        if key in data:
            ordered[key] = data[key]
            break

    # 2. Add summary second (if present)
    summary_keys = ['summary', 'stats', 'statistics']
    for key in summary_keys:
        if key in data:
            ordered[key] = data[key]
            break

    # 3. Add examples/data third
    examples_keys = ['examples', 'data', 'results', 'items']
    for key in examples_keys:
        if key in data:
            ordered[key] = data[key]
            break

    # 4. Add any remaining keys
    for key in data:
        if key not in ordered:
            ordered[key] = data[key]

    return ordered


def reorder_json_file(json_path: Path, backup: bool = True) -> bool:
    """
    Reorder keys in a JSON file.

    Args:
        json_path: Path to JSON file
        backup: Whether to create a .bak backup

    Returns:
        True if successful, False otherwise
    """
    if not json_path.exists():
        print(f"✗ File not found: {json_path}")
        return False

    if json_path.suffix == '.jsonl':
        print(f"⊘ Skipping JSONL file (still running): {json_path}")
        return False

    try:
        # Read original JSON
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        # Check if reordering is needed
        current_keys = list(data.keys())
        if current_keys and current_keys[0] in ['run_metadata', 'metadata', 'meta']:
            if len(current_keys) < 2 or current_keys[1] in ['summary', 'examples', 'data']:
                print(f"✓ Already ordered: {json_path.name}")
                return True

        # Create backup if requested
        if backup:
            backup_path = json_path.with_suffix('.json.bak')
            with backup_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write('\n')
            print(f"  → Backup created: {backup_path.name}")

        # Reorder keys
        ordered_data = reorder_json_keys(data)

        # Write reordered JSON
        with json_path.open('w', encoding='utf-8') as f:
            json.dump(ordered_data, f, indent=2, ensure_ascii=False)
            f.write('\n')

        new_keys = list(ordered_data.keys())
        print(f"✓ Reordered: {json_path.name}")
        print(f"  Before: {' → '.join(current_keys[:3])}")
        print(f"  After:  {' → '.join(new_keys[:3])}")
        return True

    except Exception as e:
        print(f"✗ Error processing {json_path}: {e}")
        return False


def find_all_complete_jsons(output_dir: Path) -> list[Path]:
    """
    Find all complete .json files (not .jsonl) in output directory.

    Args:
        output_dir: Root output directory

    Returns:
        List of JSON file paths
    """
    json_files = []

    for json_path in output_dir.rglob('*.json'):
        # Skip .jsonl files
        if json_path.suffix == '.jsonl':
            continue

        # Skip backup files
        if json_path.name.endswith('.bak'):
            continue

        json_files.append(json_path)

    return sorted(json_files)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Get repo root
    repo_root = Path(__file__).parent.parent
    output_dir = repo_root / 'output'

    if sys.argv[1] == '--all':
        # Process all complete JSONs
        json_files = find_all_complete_jsons(output_dir)

        if not json_files:
            print("No complete JSON files found in output/")
            sys.exit(0)

        print(f"Found {len(json_files)} complete JSON files\n")

        success_count = 0
        skip_count = 0
        error_count = 0

        for json_path in json_files:
            relative_path = json_path.relative_to(repo_root)
            print(f"\nProcessing: {relative_path}")

            result = reorder_json_file(json_path, backup=True)
            if result:
                success_count += 1
            elif json_path.suffix == '.jsonl':
                skip_count += 1
            else:
                error_count += 1

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Reordered: {success_count}")
        print(f"  Skipped:   {skip_count}")
        print(f"  Errors:    {error_count}")

    else:
        # Process single file
        json_path = Path(sys.argv[1])
        if not json_path.is_absolute():
            json_path = repo_root / json_path

        reorder_json_file(json_path, backup=True)


if __name__ == '__main__':
    main()
