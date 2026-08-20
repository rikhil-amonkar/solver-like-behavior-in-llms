#!/usr/bin/env python3
"""Test chunk parsing and stitching functionality."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunking.chunk_parser import (
    parse_judge_response,
    parse_and_stitch_segments,
    has_solver_like_chunks,
)


def test_parse_single_response():
    """Test parsing a single judge response."""
    print("Testing single judge response parsing...")

    response = json.dumps({
        "chunk_analysis": [
            {"sound": "This is sound reasoning."},
            {"solver-like": "Let me just try values."},
            {"sound": "Therefore the answer is correct."}
        ]
    })

    parsed = parse_judge_response(response)
    chunks = parsed["chunk_analysis"]

    print(f"  Parsed {len(chunks)} chunks")
    assert len(chunks) == 3, "Should parse 3 chunks"
    assert "sound" in chunks[0], "First chunk should be sound"
    assert "solver-like" in chunks[1], "Second chunk should be solver-like"

    print("  ✓ Single response parsing works\n")


def test_stitch_multiple_segments():
    """Test stitching multiple segment responses."""
    print("Testing segment stitching...")

    # Simulate 3 segment responses
    segment_responses = [
        json.dumps({
            "chunk_analysis": [
                {"sound": "Segment 1 chunk 1"},
                {"solver-like": "Segment 1 chunk 2"}
            ]
        }),
        json.dumps({
            "chunk_analysis": [
                {"sound": "Segment 2 chunk 1"},
            ]
        }),
        json.dumps({
            "chunk_analysis": [
                {"solver-like": "Segment 3 chunk 1"},
                {"sound": "Segment 3 chunk 2"},
                {"solver-like": "Segment 3 chunk 3"}
            ]
        }),
    ]

    enriched_chunks, token_stats, has_solver_like = parse_and_stitch_segments(
        segment_responses
    )

    print(f"  Total chunks: {len(enriched_chunks)}")
    print(f"  Has solver-like: {has_solver_like}")
    print(f"  Segments: {token_stats.get('num_segments', 0)}")
    print(f"  Was split: {token_stats.get('was_split', False)}")

    # Should have 2 + 1 + 3 = 6 total chunks
    assert len(enriched_chunks) == 6, "Should have 6 total chunks"
    assert has_solver_like, "Should detect solver-like chunks"
    assert token_stats["num_segments"] == 3, "Should record 3 segments"
    assert token_stats["was_split"], "Should mark as split"

    print("  ✓ Segment stitching works\n")


def test_stitch_single_segment():
    """Test that single segment doesn't get 'split' flag."""
    print("Testing single segment (no split)...")

    segment_responses = [
        json.dumps({
            "chunk_analysis": [
                {"sound": "Only one segment"}
            ]
        })
    ]

    enriched_chunks, token_stats, has_solver_like = parse_and_stitch_segments(
        segment_responses
    )

    print(f"  Total chunks: {len(enriched_chunks)}")
    print(f"  Was split: {token_stats.get('was_split', False)}")

    assert len(enriched_chunks) == 1, "Should have 1 chunk"
    assert not token_stats["was_split"], "Should not mark as split"

    print("  ✓ Single segment handled correctly\n")


def test_stitch_with_failures():
    """Test stitching when some segments fail to parse."""
    print("Testing segment stitching with parse failures...")

    segment_responses = [
        json.dumps({
            "chunk_analysis": [
                {"sound": "Good segment"}
            ]
        }),
        "{invalid json",  # This will fail
        json.dumps({
            "chunk_analysis": [
                {"solver-like": "Another good segment"}
            ]
        }),
    ]

    enriched_chunks, token_stats, has_solver_like = parse_and_stitch_segments(
        segment_responses
    )

    print(f"  Total chunks: {len(enriched_chunks)}")
    print(f"  Parse failures: {token_stats.get('parse_failures', 0)}")

    # Should still get 2 chunks from the valid segments
    assert len(enriched_chunks) == 2, "Should have 2 chunks from valid segments"
    assert token_stats.get("parse_failures") == 1, "Should record 1 parse failure"

    print("  ✓ Partial failures handled gracefully\n")


def test_has_solver_like():
    """Test solver-like detection."""
    print("Testing solver-like detection...")

    sound_only = [
        {"sound": "Sound reasoning", "tokens": 10}
    ]

    mixed = [
        {"sound": "Sound reasoning", "tokens": 10},
        {"solver-like": "Solver behavior", "tokens": 5}
    ]

    assert not has_solver_like_chunks(sound_only), "Should be False for sound-only"
    assert has_solver_like_chunks(mixed), "Should be True for mixed chunks"

    print("  ✓ Solver-like detection works\n")


def main():
    """Run all tests."""
    print("\n=== Testing Chunk Parsing and Stitching ===\n")

    try:
        test_parse_single_response()
        test_stitch_multiple_segments()
        test_stitch_single_segment()
        test_stitch_with_failures()
        test_has_solver_like()

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
