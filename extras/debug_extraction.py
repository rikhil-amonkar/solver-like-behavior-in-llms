#!/usr/bin/env python3
"""Debug why code extraction failed."""

import json
import re
import sys

# Add src to path
sys.path.insert(0, 'src')
from general.parsing_utils import looks_like_code, FENCED_CODE_PATTERN

def debug_extraction(json_path):
    """Debug extraction for examples with code blocks but no extraction."""

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Find first example with no code but has ticks
    for ex in data['examples']:
        reasoning = ex.get('reasoning_before_code', '')
        if not ex.get('extracted_code') and '```' in reasoning:
            print(f"=== Example: {ex['example_id']} ===\n")

            # Find all code blocks
            matches = list(FENCED_CODE_PATTERN.finditer(reasoning))
            print(f"Number of code blocks found by regex: {len(matches)}\n")

            if matches:
                for i, match in enumerate(matches):
                    code = match.group(1)
                    print(f"--- Code block {i+1} ---")
                    print(f"Length: {len(code)} chars")
                    print(f"First 300 chars: {repr(code[:300])}")
                    print(f"looks_like_code(): {looks_like_code(code)}")
                    print()

                    if not looks_like_code(code):
                        # Debug why it failed
                        stripped = code.strip()
                        lines = stripped.split('\n')

                        code_indicators = 0
                        prose_indicators = 0

                        print(f"  Total lines: {len(lines)}")
                        print(f"  First 5 lines:")
                        for line in lines[:5]:
                            print(f"    {repr(line)}")
                        print()

                        # Count indicators
                        for line in lines:
                            line_stripped = line.strip()
                            if not line_stripped or line_stripped.startswith('#'):
                                continue

                            if any(line_stripped.startswith(kw) for kw in ['def ', 'class ', 'import ', 'from ', 'return ']):
                                code_indicators += 3
                            if any(kw in line_stripped for kw in ['for ', 'while ', 'if ', 'elif ', 'else:', 'try:', 'except']):
                                code_indicators += 2
                            if '=' in line_stripped and not line_stripped.startswith('='):
                                code_indicators += 2
                            if '(' in line_stripped and ')' in line_stripped:
                                code_indicators += 1
                            if line_stripped.endswith(':'):
                                code_indicators += 1
                            if line.startswith('    ') or line.startswith('\t'):
                                code_indicators += 1

                            if line_stripped.endswith('.') and len(line_stripped.split()) > 5:
                                prose_indicators += 2
                            if line_stripped.startswith(('Need ', 'Let', 'We ', 'This ', 'Could ', 'Should ', 'The ', 'But ', 'If ')):
                                prose_indicators += 2

                        print(f"  Code indicators: {code_indicators}")
                        print(f"  Prose indicators: {prose_indicators}")
                        print(f"  Code >= 10? {code_indicators >= 10}")
                        print(f"  Code > prose*2? {code_indicators > prose_indicators * 2}")
                        print()

            # Only show first example
            break

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_extraction.py <json_path>")
        sys.exit(1)

    debug_extraction(sys.argv[1])
