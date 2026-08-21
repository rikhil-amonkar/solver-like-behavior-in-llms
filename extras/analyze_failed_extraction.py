#!/usr/bin/env python3
"""
Analyze why specific examples failed code extraction.
"""

import json
import re
from typing import List, Tuple

# Copy the exact heuristic from parsing_utils.py
FENCED_CODE_PATTERN = re.compile(
    r"```(?:python)?\s*\n(.*?)(?:\n)?```",
    re.DOTALL | re.IGNORECASE
)

def looks_like_code(code: str) -> Tuple[bool, int, int, dict]:
    """
    Check if a string looks like intended Python code (even if syntactically invalid).
    Returns (is_code, code_indicators, prose_indicators, details)
    """
    if not code or not code.strip():
        return False, 0, 0, {"reason": "empty"}

    stripped = code.strip()

    # Filter out trivial placeholders
    if stripped in ('...', 'pass', 'None'):
        return False, 0, 0, {"reason": "trivial placeholder"}

    # Filter out extremely short snippets (< 50 chars, unlikely to be solutions)
    if len(stripped) < 50:
        return False, 0, 0, {"reason": f"too short ({len(stripped)} chars)"}

    lines = stripped.split('\n')

    # Count lines with code-like patterns
    code_indicators = 0
    prose_indicators = 0
    has_print_statement = False

    details = {
        "length": len(stripped),
        "num_lines": len(lines),
        "has_print": False,
        "code_patterns": [],
        "prose_patterns": []
    }

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('#'):
            continue

        # Strong code indicators
        if any(line_stripped.startswith(kw) for kw in ['def ', 'class ', 'import ', 'from ', 'return ', 'yield ']):
            code_indicators += 3
            details["code_patterns"].append(f"def/class/import: {line_stripped[:40]}")
        if any(kw in line_stripped for kw in ['for ', 'while ', 'if ', 'elif ', 'else:', 'try:', 'except', 'with ']):
            code_indicators += 2
            details["code_patterns"].append(f"control flow: {line_stripped[:40]}")
        if '=' in line_stripped and not line_stripped.startswith('='):  # Assignment
            code_indicators += 2
            details["code_patterns"].append(f"assignment: {line_stripped[:40]}")
        if line_stripped.startswith('print(') or ' print(' in line_stripped:  # Print statement
            code_indicators += 3
            has_print_statement = True
            details["has_print"] = True
            details["code_patterns"].append(f"print: {line_stripped[:40]}")
        elif '(' in line_stripped and ')' in line_stripped:  # Function call/def
            code_indicators += 1
            details["code_patterns"].append(f"function call: {line_stripped[:40]}")
        if line_stripped.endswith(':'):  # Block start
            code_indicators += 1
        if line.startswith('    ') or line.startswith('\t'):  # Indented
            code_indicators += 1
        if any(c in line_stripped for c in ['{', '}', '[', ']']):  # Brackets
            code_indicators += 1

        # Prose indicators
        if line_stripped.endswith('.') and len(line_stripped.split()) > 5:  # Sentence
            prose_indicators += 2
            details["prose_patterns"].append(f"sentence: {line_stripped[:40]}")
        if line_stripped.startswith(('Need ', 'Let', 'We ', 'This ', 'Could ', 'Should ', 'The ', 'But ', 'If ')):
            prose_indicators += 2
            details["prose_patterns"].append(f"prose start: {line_stripped[:40]}")
        if ' maybe ' in line_stripped or ' perhaps ' in line_stripped:
            prose_indicators += 1
            details["prose_patterns"].append(f"maybe/perhaps: {line_stripped[:40]}")

    # Lowered threshold from 10 to 6 to catch simple solutions
    threshold = 5 if has_print_statement else 6
    is_code = code_indicators >= threshold and code_indicators > prose_indicators * 2

    details["threshold_used"] = threshold
    details["passes_threshold"] = code_indicators >= threshold
    details["passes_prose_ratio"] = code_indicators > prose_indicators * 2

    return is_code, code_indicators, prose_indicators, details


def analyze_example(example_id: str, example: dict):
    """Analyze a single failed extraction example."""
    print(f"\n{'='*80}")
    print(f"EXAMPLE: {example_id}")
    print(f"{'='*80}")

    reasoning_trace = example.get("reasoning_trace", "")
    extracted_code = example.get("extracted_code", "")

    print(f"\nExtracted code status: {'EMPTY' if not extracted_code else 'HAS CODE'}")

    # Find all code blocks
    matches = list(FENCED_CODE_PATTERN.finditer(reasoning_trace))

    if not matches:
        print("\n❌ NO CODE BLOCKS FOUND (no ```...``` patterns)")
        print("\nFirst 500 chars of reasoning_trace:")
        print(reasoning_trace[:500])
        return

    print(f"\n✓ Found {len(matches)} code block(s)")

    # Analyze each code block
    for i, match in enumerate(matches):
        code_content = match.group(1).strip()
        print(f"\n--- Code Block {i+1} ---")
        print(f"Position: {match.start()} - {match.end()}")
        print(f"Length: {len(code_content)} chars")
        print(f"\nFirst 200 chars:")
        print(code_content[:200])
        print("...")

        # Run heuristic
        is_code, code_score, prose_score, details = looks_like_code(code_content)

        print(f"\n📊 Heuristic Analysis:")

        # Check if this was rejected early
        if details.get("reason"):
            print(f"  Early rejection: {details['reason']}")
            print(f"  ❌ REJECTED: {is_code}")
            continue

        print(f"  Length: {details['length']} chars")
        print(f"  Lines: {details['num_lines']}")
        print(f"  Code indicators score: {code_score}")
        print(f"  Prose indicators score: {prose_score}")
        print(f"  Has print statement: {details['has_print']}")
        print(f"  Threshold used: {details['threshold_used']}")
        print(f"  Passes threshold ({code_score} >= {details['threshold_used']}): {details['passes_threshold']}")
        print(f"  Passes prose ratio ({code_score} > {prose_score * 2}): {details['passes_prose_ratio']}")
        print(f"  ✓ WOULD EXTRACT: {is_code}" if is_code else f"  ❌ REJECTED: {is_code}")

        if not is_code:
            print(f"\n🔍 WHY REJECTED:")
            if details.get("reason"):
                print(f"  - {details['reason']}")
            if not details['passes_threshold']:
                print(f"  - Code score {code_score} below threshold {details['threshold_used']}")
            if not details['passes_prose_ratio']:
                print(f"  - Code score {code_score} not > 2x prose score ({prose_score * 2})")

        if details['code_patterns']:
            print(f"\n  Code patterns found ({len(details['code_patterns'])}):")
            for pattern in details['code_patterns'][:5]:
                print(f"    • {pattern}")

        if details['prose_patterns']:
            print(f"\n  Prose patterns found ({len(details['prose_patterns'])}):")
            for pattern in details['prose_patterns'][:5]:
                print(f"    • {pattern}")

        print(f"\n{'─'*60}")


def main():
    # Target examples
    examples_to_check = {
        "calendar": ["calendar_scheduling_example_543"],
        "meeting": [
            "meeting_planning_example_867",
            "meeting_planning_example_978",
            "meeting_planning_example_956",
            "meeting_planning_example_835",
            "meeting_planning_example_592",
            "meeting_planning_example_900",
            "meeting_planning_example_800",
            "meeting_planning_example_937",
        ]
    }

    # Load JSONs
    for task, example_ids in examples_to_check.items():
        json_path = f"/local-ssd/rma336/solver-like-behavior-in-llms/output/gpt/{task}/baseline_inference.json"

        print(f"\n{'#'*80}")
        print(f"# TASK: {task.upper()}")
        print(f"# File: {json_path}")
        print(f"{'#'*80}")

        with open(json_path, 'r') as f:
            data = json.load(f)

        # Extract examples array
        examples = data.get("examples", [])

        # Find and analyze each example
        for example_id in example_ids:
            example = None
            for item in examples:
                if item.get("example_id") == example_id:
                    example = item
                    break

            if example:
                analyze_example(example_id, example)
            else:
                print(f"\n❌ Example {example_id} not found in JSON")


if __name__ == "__main__":
    main()
