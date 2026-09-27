#!/usr/bin/env python3
"""
Helper script to fix metadata fields in categorization JSON files.

This script updates example_metadata fields (example_correct, example_has_solution,
example_code_hardcoded, example_code_error) based on the corresponding execution
and evaluation JSON files.

Usage:
    python extras/fix_categorization_metadata.py <categorization_json_path>

Example:
    python extras/fix_categorization_metadata.py output/gpt/meeting/baseline_categorization.json
"""

import json
import re
import sys
import os
from pathlib import Path


def detect_code_error(code_execution: dict) -> bool:
    """
    Detect if code execution resulted in an error.

    Args:
        code_execution: Code execution dict from execution JSON

    Returns:
        True if code had an error, False otherwise
    """
    # Check if code didn't run at all
    if not code_execution.get('ran', False):
        return True

    # Check exit code (non-zero = error)
    if code_execution.get('exit_code', 0) != 0:
        return True

    # Check for explicit error field
    if code_execution.get('error'):
        return True

    # Check if timed out
    if code_execution.get('timed_out', False):
        return True

    # Check for stderr content (Python tracebacks, syntax errors, etc.)
    stderr = code_execution.get('stderr', '').strip()
    if stderr:
        # Common error indicators in stderr
        error_indicators = [
            'Traceback',
            'Error:',
            'Exception:',
            'SyntaxError',
            'NameError',
            'TypeError',
            'ValueError',
            'ImportError',
            'ModuleNotFoundError',
        ]
        if any(indicator in stderr for indicator in error_indicators):
            return True

    return False


def detect_no_solution(code_execution: dict, extracted_code: str) -> bool:
    """
    Detect if code produced no solution/output.

    Args:
        code_execution: Code execution dict from execution JSON
        extracted_code: The actual code that was extracted

    Returns:
        True if no solution was produced, False if solution exists
    """
    # If parsed_output exists and is not None/empty, there's a solution
    parsed_output = code_execution.get('parsed_output')

    # Check for various "empty" indicators
    if parsed_output is None:
        return True

    if parsed_output == "":
        return True

    if parsed_output == []:
        return True

    if parsed_output == {}:
        return True

    # Check stdout for empty/no solution indicators
    stdout = code_execution.get('stdout', '').strip().lower()

    if not stdout:
        return True

    # Common "no solution" phrases
    no_solution_patterns = [
        r'\bno\s+solution\b',
        r'\bno\s+plan\b',
        r'\bno\s+output\b',
        r'\bno\s+valid\b',
        r'\bno\s+feasible\b',
        r'\bimpossible\b',
        r'\bunsolvable\b',
        r'\bno\s+schedule\b',
        r'\bno\s+itinerary\b',
        r'\bcannot\s+find\b',
        r'\bcannot\s+schedule\b',
        r'\bfailed\s+to\s+find\b',
    ]

    for pattern in no_solution_patterns:
        if re.search(pattern, stdout, re.IGNORECASE):
            return True

    # Check for empty brackets/structures in output
    if stdout in ['[]', '{}', '()', 'none', 'null']:
        return True

    return False


def detect_hardcoded_solution(extracted_code: str, code_execution: dict) -> bool:
    """
    Detect if the code contains a hardcoded solution.

    This looks for strong indicators that the solution was directly written into
    the code rather than computed programmatically.

    Args:
        extracted_code: The actual code that was extracted
        code_execution: Code execution dict (for cross-validation)

    Returns:
        True if code appears to be hardcoded, False otherwise
    """
    if not extracted_code or not extracted_code.strip():
        return False

    # Explicit hardcoding keywords in comments or variable names
    hardcode_keywords = [
        r'hardcod',
        r'hard[\s-]cod',
        r'directly\s+assign',
        r'directly\s+return',
        r'manual',
        r'literal',
    ]

    for keyword in hardcode_keywords:
        if re.search(keyword, extracted_code, re.IGNORECASE):
            return True

    # Parse code structure
    lines = extracted_code.split('\n')
    code_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]

    if len(code_lines) == 0:
        return False

    # Count different types of operations
    direct_assignment_lines = 0  # Lines like: itinerary = [...]
    direct_output_lines = 0      # Lines like: print([...])
    computation_lines = 0         # Lines with loops, conditionals, etc.

    for line in code_lines:
        # Skip imports
        if line.startswith('import ') or line.startswith('from '):
            continue

        # Direct assignment of literal data structures
        # Match patterns like: variable = [ ... ] or variable = "..."
        if '=' in line and not any(op in line for op in ['==', '!=', '<=', '>=', '+=', '-=', '*=', '/=', '//=']):
            # Check if right side has literal data (lists, strings with content)
            right_side = line.split('=', 1)[1].strip() if '=' in line else ''

            # Strong indicators of literal assignment
            if right_side.startswith('[') or right_side.startswith('{'):
                direct_assignment_lines += 1
            elif right_side.startswith('"') or right_side.startswith("'"):
                # String assignment (might be hardcoded if multi-line or detailed)
                if len(right_side) > 30:  # Long string = likely hardcoded content
                    direct_assignment_lines += 1

        # Direct print/return of literals
        if 'print(' in line or 'return ' in line:
            # Check if it's printing/returning a literal structure or long string
            if re.search(r'print\s*\(\s*\[', line) or re.search(r'return\s*\[', line):
                direct_output_lines += 1
            elif re.search(r'print\s*\(\s*["\']', line) or re.search(r'return\s*["\']', line):
                direct_output_lines += 1
            # Also count if printing a simple variable (that was likely assigned a literal)
            elif re.search(r'print\s*\(\s*\w+\s*\)', line):
                direct_output_lines += 1

        # Computational indicators
        computational_keywords = [
            'for ', 'while ', 'if ', 'elif ', 'else:',
            'def ', 'class ',
            'range(', 'enumerate(', 'zip(',
            'sorted(', 'filter(', 'map(',
            '.append(', '.extend(', '.insert(',
        ]

        if any(keyword in line for keyword in computational_keywords):
            computation_lines += 1

    # Decision logic for hardcoding
    # Strong indicator: Direct assignment + direct output with minimal computation
    if direct_assignment_lines > 0 and direct_output_lines > 0 and computation_lines == 0:
        return True

    # Another strong indicator: Only direct output with no computation
    if direct_output_lines > 0 and computation_lines < 2 and len(code_lines) < 10:
        return True

    # Pattern-based detection: Look for specific hardcoding patterns
    # Example: itinerary = ["You start at X", "You travel to Y", ...]
    itinerary_pattern = re.compile(
        r'(itinerary|schedule|solution|result|answer|plan)\s*=\s*\[',
        re.IGNORECASE
    )

    # Check if we have a list assignment followed by immediate print
    has_list_assignment = False
    has_subsequent_print = False

    for i, line in enumerate(code_lines):
        if itinerary_pattern.search(line):
            has_list_assignment = True
            # Check if there's a print within the next 3 lines
            for j in range(i + 1, min(i + 4, len(code_lines))):
                if 'print(' in code_lines[j]:
                    has_subsequent_print = True
                    break

    # If we have a list assignment followed by print with minimal computation, it's hardcoded
    if has_list_assignment and has_subsequent_print and computation_lines <= 2:
        return True

    # Check for multi-line list literals with string content (very strong indicator)
    # This catches patterns like:
    # itinerary = [
    #     "You start at X",
    #     "You travel to Y",
    #     ...
    # ]
    multiline_list_pattern = re.compile(
        r'(itinerary|schedule|solution|result|answer|plan)\s*=\s*\[\s*\n.*".*"',
        re.IGNORECASE | re.DOTALL
    )

    if multiline_list_pattern.search(extracted_code):
        # Count how many quoted strings are in the list
        list_match = re.search(r'=\s*\[([^\]]*)\]', extracted_code, re.DOTALL)
        if list_match:
            list_content = list_match.group(1)
            string_count = len(re.findall(r'"[^"]*"', list_content))
            # If there are multiple strings (e.g., itinerary steps), it's hardcoded
            if string_count >= 3:
                return True

    return False


def build_corrected_metadata(
    execution_data: dict,
    evaluation_data: dict
) -> dict:
    """
    Build corrected metadata for all examples.

    Args:
        execution_data: Loaded execution JSON
        evaluation_data: Loaded evaluation JSON

    Returns:
        Dict mapping example_id to corrected metadata
    """
    metadata = {}

    # First pass: Get correctness from evaluation data
    for example in evaluation_data.get('examples', []):
        example_id = example['example_id']
        metadata[example_id] = {
            'example_correct': example.get('correct', False),
            'example_has_solution': None,  # Will be computed from execution
            'example_code_hardcoded': None,  # Will be computed from execution
            'example_code_error': None,  # Will be computed from execution
        }

    # Second pass: Analyze execution data
    for example in execution_data.get('examples', []):
        example_id = example['example_id']

        # Initialize metadata if not present (shouldn't happen, but safe)
        if example_id not in metadata:
            metadata[example_id] = {
                'example_correct': False,
                'example_has_solution': None,
                'example_code_hardcoded': None,
                'example_code_error': None,
            }

        code_execution = example.get('code_execution', {})
        extracted_code = example.get('extracted_code', '')

        # Detect code error
        has_error = detect_code_error(code_execution)
        metadata[example_id]['example_code_error'] = has_error

        # If there's an error, set has_solution and hardcoded to null
        if has_error:
            metadata[example_id]['example_has_solution'] = None
            metadata[example_id]['example_code_hardcoded'] = None
        else:
            # No error - analyze solution and hardcoding
            no_solution = detect_no_solution(code_execution, extracted_code)
            metadata[example_id]['example_has_solution'] = not no_solution

            # Only check for hardcoding if there's a solution
            if not no_solution:
                is_hardcoded = detect_hardcoded_solution(extracted_code, code_execution)
                metadata[example_id]['example_code_hardcoded'] = is_hardcoded
            else:
                metadata[example_id]['example_code_hardcoded'] = False

    return metadata


def fix_categorization_metadata(categorization_path: str) -> None:
    """
    Fix metadata in a categorization JSON file.

    Args:
        categorization_path: Path to the categorization JSON file
    """
    categorization_path = Path(categorization_path)

    if not categorization_path.exists():
        print(f"Error: Categorization file not found: {categorization_path}")
        sys.exit(1)

    # Derive paths to execution and evaluation files
    # Expected pattern: output/{model}/{task}/{condition}_categorization.json
    parts = categorization_path.parts

    # Find 'output' in the path
    try:
        output_idx = parts.index('output')
        model = parts[output_idx + 1]
        task = parts[output_idx + 2]
        filename = categorization_path.stem  # e.g., "baseline_categorization"
        condition = filename.replace('_categorization', '')
    except (ValueError, IndexError):
        print(f"Error: Could not parse path structure: {categorization_path}")
        print("Expected format: output/<model>/<task>/<condition>_categorization.json")
        sys.exit(1)

    # Build paths to execution and evaluation files
    base_dir = categorization_path.parent
    execution_path = base_dir / f"{condition}_execution.json"
    evaluation_path = base_dir / f"{condition}_evaluation.json"

    # Verify files exist
    if not execution_path.exists():
        print(f"Error: Execution file not found: {execution_path}")
        sys.exit(1)

    if not evaluation_path.exists():
        print(f"Error: Evaluation file not found: {evaluation_path}")
        sys.exit(1)

    print(f"{'='*80}")
    print(f"Fixing metadata for: {categorization_path.name}")
    print(f"{'='*80}")
    print(f"Model: {model}")
    print(f"Task: {task}")
    print(f"Condition: {condition}")
    print(f"\nLoading data files...")
    print(f"  Categorization: {categorization_path}")
    print(f"  Execution: {execution_path}")
    print(f"  Evaluation: {evaluation_path}")

    # Load all three files
    with open(categorization_path, 'r') as f:
        categorization_data = json.load(f)

    with open(execution_path, 'r') as f:
        execution_data = json.load(f)

    with open(evaluation_path, 'r') as f:
        evaluation_data = json.load(f)

    print(f"\nBuilding corrected metadata...")

    # Build corrected metadata
    corrected_metadata = build_corrected_metadata(execution_data, evaluation_data)

    # Update categorization data with corrected metadata
    print(f"\nUpdating metadata in categorization data...")

    updated_count = 0
    for example in categorization_data.get('examples', []):
        example_id = example['example_id']

        if example_id in corrected_metadata:
            example['example_metadata'] = corrected_metadata[example_id]
            updated_count += 1

    # Save updated categorization file
    print(f"\nSaving updated categorization file...")
    with open(categorization_path, 'w') as f:
        json.dump(categorization_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✓ Successfully updated {updated_count} examples")
    print(f"{'='*80}")

    # Print summary statistics
    print(f"\nMetadata Summary:")
    stats = {
        'correct': 0,
        'has_solution': 0,
        'hardcoded': 0,
        'code_error': 0,
        'has_solution_null': 0,
        'hardcoded_null': 0,
    }

    for metadata in corrected_metadata.values():
        if metadata['example_correct']:
            stats['correct'] += 1
        if metadata['example_has_solution'] is True:
            stats['has_solution'] += 1
        if metadata['example_has_solution'] is None:
            stats['has_solution_null'] += 1
        if metadata['example_code_hardcoded'] is True:
            stats['hardcoded'] += 1
        if metadata['example_code_hardcoded'] is None:
            stats['hardcoded_null'] += 1
        if metadata['example_code_error']:
            stats['code_error'] += 1

    total = len(corrected_metadata)
    print(f"  Total examples: {total}")
    print(f"  Correct: {stats['correct']} ({100*stats['correct']/total:.1f}%)")
    print(f"  Has solution: {stats['has_solution']} ({100*stats['has_solution']/total:.1f}%)")
    print(f"  Hardcoded: {stats['hardcoded']} ({100*stats['hardcoded']/total:.1f}%)")
    print(f"  Code error: {stats['code_error']} ({100*stats['code_error']/total:.1f}%)")
    print(f"  Has solution (null): {stats['has_solution_null']}")
    print(f"  Hardcoded (null): {stats['hardcoded_null']}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python extras/fix_categorization_metadata.py <categorization_json_path>")
        print("\nExample:")
        print("  python extras/fix_categorization_metadata.py output/gpt/meeting/baseline_categorization.json")
        sys.exit(1)

    categorization_path = sys.argv[1]
    fix_categorization_metadata(categorization_path)


if __name__ == '__main__':
    main()
