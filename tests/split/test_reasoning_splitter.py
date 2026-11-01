#!/usr/bin/env python3
"""Test reasoning splitter functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from chunking.reasoning_splitter import (
    count_tokens,
    should_split_reasoning,
    split_reasoning_by_tokens,
)


def test_count_tokens():
    """Test token counting."""
    print("Testing token counting...")

    text = "This is a test sentence."
    tokens = count_tokens(text)
    print(f"  Text: '{text}'")
    print(f"  Tokens: {tokens}")
    assert tokens > 0, "Token count should be positive"
    print("  ✓ Token counting works\n")


def test_should_split_short_text():
    """Test that short text doesn't need splitting."""
    print("Testing short text (no split needed)...")

    short_text = "This is a short reasoning trace. " * 100  # ~600 tokens
    needs_split, token_count = should_split_reasoning(short_text)

    print(f"  Text tokens: {token_count}")
    print(f"  Needs split: {needs_split}")
    assert not needs_split, "Short text should not need splitting"
    print("  ✓ Short text correctly identified\n")


def test_should_split_long_text():
    """Test that very long text needs splitting."""
    print("Testing long text (split needed)...")

    # Create very long text (~60k tokens)
    long_text = "This is a very long reasoning trace. " * 10000
    needs_split, token_count = should_split_reasoning(long_text)

    print(f"  Text tokens: {token_count}")
    print(f"  Needs split: {needs_split}")
    assert needs_split, "Long text should need splitting"
    print("  ✓ Long text correctly identified\n")


def test_split_reasoning():
    """Test actual splitting of long text."""
    print("Testing text splitting...")

    # Create long text that needs splitting
    long_text = "Paragraph one.\n\n" + ("This is reasoning. " * 1000 + "\n\n") * 20

    print(f"  Original tokens: {count_tokens(long_text)}")

    segments = split_reasoning_by_tokens(long_text)

    print(f"  Number of segments: {len(segments)}")

    # Verify each segment is under limit
    for i, segment in enumerate(segments):
        seg_tokens = count_tokens(segment)
        print(f"    Segment {i+1}: {seg_tokens} tokens")
        assert seg_tokens <= 40000, f"Segment {i+1} exceeds token limit"

    # Verify segments can be joined to reconstruct (approximately)
    total_segment_tokens = sum(count_tokens(s) for s in segments)
    original_tokens = count_tokens(long_text)

    # Allow some variance due to splitting on boundaries
    assert abs(total_segment_tokens - original_tokens) / original_tokens < 0.1, \
        "Total segment tokens should be close to original"

    print("  ✓ Text splitting works correctly\n")


def test_split_short_text():
    """Test that short text returns single segment."""
    print("Testing split of short text (should return 1 segment)...")

    short_text = "This is short. " * 100
    segments = split_reasoning_by_tokens(short_text)

    print(f"  Text tokens: {count_tokens(short_text)}")
    print(f"  Number of segments: {len(segments)}")

    assert len(segments) == 1, "Short text should return single segment"
    assert segments[0] == short_text, "Single segment should be identical to input"

    print("  ✓ Short text returns single segment\n")


def main():
    """Run all tests."""
    print("\n=== Testing Reasoning Splitter ===\n")

    try:
        test_count_tokens()
        test_should_split_short_text()
        test_should_split_long_text()
        test_split_reasoning()
        test_split_short_text()

        print("=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
