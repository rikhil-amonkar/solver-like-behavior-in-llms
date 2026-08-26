#!/usr/bin/env python3
"""
Test to verify reasoning splitter behavior with 2.5k token chunks.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "../../src"))

from chunking.reasoning_splitter import (
    should_split_reasoning,
    split_reasoning_by_tokens,
    count_tokens,
)


def test_short_trace():
    """Test that short traces (< 2.5k tokens) don't get split."""
    print("=" * 60)
    print("TEST 1: Short Trace (< 2.5k tokens)")
    print("=" * 60)

    short_text = "This is a short reasoning trace. " * 50  # ~350 tokens
    should_split, token_count = should_split_reasoning(short_text)

    print(f"Token count: {token_count}")
    print(f"Should split: {should_split}")

    assert not should_split, "Short traces should NOT be split"
    print("✓ PASSED: Short trace not split\n")


def test_medium_trace():
    """Test that medium traces (2.5k - 5k tokens) get split into 2 segments."""
    print("=" * 60)
    print("TEST 2: Medium Trace (~4k tokens)")
    print("=" * 60)

    # Create ~4k token trace (need longer text)
    medium_text = "Here is some reasoning about the problem. " * 500  # ~4k tokens

    should_split, token_count = should_split_reasoning(medium_text)
    segments = split_reasoning_by_tokens(medium_text)

    print(f"Token count: {token_count}")
    print(f"Should split: {should_split}")
    print(f"Number of segments: {len(segments)}")

    for i, seg in enumerate(segments):
        seg_tokens = count_tokens(seg)
        print(f"  Segment {i+1}: {seg_tokens} tokens")

    assert should_split, "Medium traces should be split"
    assert len(segments) >= 2, "4k tokens should split into at least 2 segments"
    assert all(count_tokens(seg) <= 2500 for seg in segments), "Each segment should be <= 2.5k tokens"
    print("✓ PASSED: Medium trace split correctly\n")


def test_long_trace():
    """Test that long traces (10k+ tokens) get split into multiple segments."""
    print("=" * 60)
    print("TEST 3: Long Trace (~12k tokens)")
    print("=" * 60)

    # Create ~12k token trace (need much longer text)
    long_text = (
        "I need to carefully analyze this constraint satisfaction problem.\n\n" * 1200
    )  # ~12k tokens

    should_split, token_count = should_split_reasoning(long_text)
    segments = split_reasoning_by_tokens(long_text)

    print(f"Token count: {token_count}")
    print(f"Should split: {should_split}")
    print(f"Number of segments: {len(segments)}")

    for i, seg in enumerate(segments):
        seg_tokens = count_tokens(seg)
        print(f"  Segment {i+1}: {seg_tokens} tokens")
        assert seg_tokens <= 2500, f"Segment {i+1} exceeds 2.5k tokens!"

    assert should_split, "Long traces should be split"
    assert len(segments) >= 4, "12k tokens should split into at least 4 segments"
    print("✓ PASSED: Long trace split correctly\n")


def test_very_long_trace():
    """Test that very long traces (50k+ tokens) get split into many small segments."""
    print("=" * 60)
    print("TEST 4: Very Long Trace (~30k tokens)")
    print("=" * 60)

    # Create ~30k token trace (more realistic)
    very_long_text = (
        "Let me think through this step by step with detailed reasoning.\n\n" * 3000
    )  # ~30k tokens

    should_split, token_count = should_split_reasoning(very_long_text)
    segments = split_reasoning_by_tokens(very_long_text)

    print(f"Token count: {token_count}")
    print(f"Should split: {should_split}")
    print(f"Number of segments: {len(segments)}")

    # Check distribution
    segment_sizes = [count_tokens(seg) for seg in segments]
    avg_size = sum(segment_sizes) / len(segment_sizes)
    max_size = max(segment_sizes)
    min_size = min(segment_sizes)

    print(f"  Average segment size: {avg_size:.0f} tokens")
    print(f"  Max segment size: {max_size} tokens")
    print(f"  Min segment size: {min_size} tokens")

    assert should_split, "Very long traces should be split"
    assert len(segments) >= 10, "30k tokens should split into at least 10 segments"
    assert all(size <= 2500 for size in segment_sizes), "All segments must be <= 2.5k tokens"
    print("✓ PASSED: Very long trace split correctly\n")


def test_boundary_case():
    """Test exactly 2500 tokens (boundary case)."""
    print("=" * 60)
    print("TEST 5: Boundary Case (exactly 2500 tokens)")
    print("=" * 60)

    # Create text that's exactly ~2500 tokens
    text = "Reasoning text. " * 625  # ~2500 tokens

    actual_tokens = count_tokens(text)
    should_split, token_count = should_split_reasoning(text)

    print(f"Token count: {token_count}")
    print(f"Should split: {should_split}")

    # At exactly 2500 tokens, should NOT split (just under the limit)
    if actual_tokens <= 2500:
        assert not should_split, "Exactly 2500 tokens should NOT split"
        print("✓ PASSED: Boundary case handled correctly\n")
    else:
        # If slightly over, should split into 2
        assert should_split, "Over 2500 tokens should split"
        segments = split_reasoning_by_tokens(text)
        print(f"Number of segments: {len(segments)}")
        print("✓ PASSED: Slightly over boundary splits correctly\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("REASONING SPLITTER TESTS (2.5k token chunks)")
    print("=" * 60 + "\n")

    try:
        test_short_trace()
        test_medium_trace()
        test_long_trace()
        test_very_long_trace()
        test_boundary_case()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nNew chunking behavior:")
        print("- Traces <= 2.5k tokens: no splitting")
        print("- Traces > 2.5k tokens: split into ~2.5k token segments")
        print("- This prevents MAX_TOKENS errors from judge model")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
