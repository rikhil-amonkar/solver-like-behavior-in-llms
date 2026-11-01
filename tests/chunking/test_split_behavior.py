#!/usr/bin/env python3
"""
Test reasoning splitter behavior: traces longer than
MAX_REASONING_TOKENS_PER_SEGMENT are split into segments no longer than it.

Run: python tests/chunking/test_split_behavior.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "../../src"))

from chunking.reasoning_splitter import (
    MAX_REASONING_TOKENS_PER_SEGMENT as LIMIT,
    should_split_reasoning,
    split_reasoning_by_tokens,
    count_tokens,
)


def make_text(sentence: str, target_tokens: int) -> str:
    """Repeat sentence until the text has about target_tokens tokens."""
    per_sentence = count_tokens(sentence * 100) / 100  # repeats merge tokens
    return sentence * int(target_tokens / per_sentence + 1)


def check_split(text: str, min_segments: int):
    should_split, token_count = should_split_reasoning(text)
    segments = split_reasoning_by_tokens(text)
    sizes = [count_tokens(seg) for seg in segments]
    print(f"  {token_count} tokens -> {len(segments)} segments, max {max(sizes)} tokens")

    assert should_split, f"{token_count} tokens (> {LIMIT}) should be split"
    assert len(segments) >= min_segments, f"Expected at least {min_segments} segments"
    assert all(size <= LIMIT for size in sizes), f"Every segment must be <= {LIMIT} tokens"


def test_short_trace():
    """Traces well under the limit are not split."""
    print("Short trace")
    should_split, _ = should_split_reasoning(make_text("This is a short reasoning trace. ", 350))
    assert not should_split, "Short traces should NOT be split"


def test_medium_trace():
    """A trace of 1.5x the limit splits into at least 2 segments."""
    print("Medium trace")
    check_split(make_text("Here is some reasoning about the problem. ", int(LIMIT * 1.5)), 2)


def test_long_trace():
    """A trace of 4x the limit, with paragraph breaks, splits into at least 4 segments."""
    print("Long trace")
    check_split(make_text("I need to carefully analyze this constraint satisfaction problem.\n\n", LIMIT * 4), 4)


def test_boundary_case():
    """At or below the limit nothing is split; just above it is."""
    print("Boundary case")
    text = make_text("Reasoning text. ", LIMIT - 100)
    assert not should_split_reasoning(text)[0], "Text under the limit should NOT split"
    check_split(make_text("Reasoning text. ", LIMIT + 100), 2)


def main():
    try:
        test_short_trace()
        test_medium_trace()
        test_long_trace()
        test_boundary_case()
        print(f"ALL TESTS PASSED (segment limit {LIMIT} tokens)")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
