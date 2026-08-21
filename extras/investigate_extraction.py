#!/usr/bin/env python3
"""Investigate code extraction issues in inference JSON."""

import json
import sys

def investigate_extraction(json_path):
    """Check for examples where code wasn't extracted despite code blocks present."""

    with open(json_path, 'r') as f:
        data = json.load(f)

    examples = data['examples']
    total = len(examples)
    no_code = [ex for ex in examples if not ex.get('extracted_code') or not ex['extracted_code'].strip()]
    has_ticks = []

    for ex in no_code:
        reasoning = ex.get('reasoning_before_code', '')
        if '```' in reasoning:
            has_ticks.append(ex)

    print(f'Total examples: {total}')
    print(f'Examples with no extracted code: {len(no_code)}')
    print(f'Examples with no code BUT have code ticks in reasoning: {len(has_ticks)}')

    if has_ticks:
        print(f'\n=== First example with ticks but no extraction ===')
        ex = has_ticks[0]
        print(f'Example ID: {ex["example_id"]}')
        print(f'\nReasoning excerpt (first 500 chars):')
        print(ex.get('reasoning_before_code', '')[:500])
        print('\n...')

        # Find where code blocks are
        reasoning = ex.get('reasoning_before_code', '')
        tick_positions = [i for i, char in enumerate(reasoning) if reasoning[i:i+3] == '```']
        print(f'\nCode tick positions: {tick_positions[:10]}')

        # Show what's around first code tick
        if tick_positions:
            pos = tick_positions[0]
            print(f'\nContext around first code tick (position {pos}):')
            print(repr(reasoning[max(0, pos-50):pos+150]))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python investigate_extraction.py <inference_json>')
        sys.exit(1)

    investigate_extraction(sys.argv[1])
