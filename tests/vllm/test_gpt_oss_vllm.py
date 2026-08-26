#!/usr/bin/env python3
"""
Smoke test for GPT-OSS vLLM integration.

Tests that the vLLM-based call_gpt_oss() function:
1. Loads the model successfully
2. Generates valid responses
3. Returns correct metadata format
4. Handles different reasoning_effort levels
5. Preserves reasoning tokens (if present)

Usage:
    python tests/vllm/test_gpt_oss_vllm.py
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from models.call_gpt_oss import call_gpt_oss


def test_basic_generation():
    """Test basic text generation."""
    print("=" * 60)
    print("TEST 1: Basic Generation")
    print("=" * 60)

    prompt = "What is 2 + 2? Answer in one sentence."
    result = call_gpt_oss(prompt, max_tokens=100, reasoning_effort="low")

    assert "reasoning_trace" in result, "Missing reasoning_trace in result"
    assert "metadata" in result, "Missing metadata in result"
    assert len(result["reasoning_trace"]) > 0, "Empty reasoning trace"

    print(f"✓ Generated {len(result['reasoning_trace'])} characters")
    print(f"✓ Prompt tokens: {result['metadata']['prompt_length']}")
    print(f"✓ Generated tokens: {result['metadata']['generated_tokens']}")
    print(f"✓ Inference engine: {result['metadata'].get('inference_engine', 'unknown')}")
    print(f"\nResponse preview: {result['reasoning_trace'][:200]}...")
    print("\n✓ TEST 1 PASSED\n")


def test_reasoning_efforts():
    """Test different reasoning effort levels."""
    print("=" * 60)
    print("TEST 2: Reasoning Effort Levels")
    print("=" * 60)

    prompt = "Explain the Pythagorean theorem briefly."

    for effort in ["low", "medium", "high"]:
        print(f"\n  Testing effort={effort}...")
        result = call_gpt_oss(prompt, max_tokens=200, reasoning_effort=effort)

        assert "reasoning_trace" in result, f"Missing reasoning_trace for effort={effort}"
        assert result["metadata"]["reasoning_effort"] == effort, f"Incorrect effort in metadata"

        print(f"    ✓ effort={effort}: {result['metadata']['generated_tokens']} tokens")

    print("\n✓ TEST 2 PASSED\n")


def test_csp_problem():
    """Test with a simple CSP-style problem (similar to actual usage)."""
    print("=" * 60)
    print("TEST 3: CSP Problem (Meeting Planning)")
    print("=" * 60)

    prompt = """You are solving a constraint satisfaction problem.

Problem:
Plan a meeting itinerary:
- Meeting at Office A at 10:00 (1 hour)
- Travel time from Office A to Restaurant: 30 minutes
- Lunch at Restaurant (1 hour)

Write Python code to compute the timeline.

Output format: List of steps with times.
"""

    result = call_gpt_oss(prompt, max_tokens=1000, reasoning_effort="medium")

    assert "reasoning_trace" in result, "Missing reasoning_trace in result"
    assert len(result["reasoning_trace"]) > 100, "Response too short for CSP problem"

    # Check if response contains code-like content
    has_code_markers = any(marker in result["reasoning_trace"].lower()
                          for marker in ["python", "def ", "import", "```"])

    print(f"✓ Generated {len(result['reasoning_trace'])} characters")
    print(f"✓ Contains code markers: {has_code_markers}")
    print(f"✓ Generated tokens: {result['metadata']['generated_tokens']}")
    print(f"\nResponse preview: {result['reasoning_trace'][:400]}...")
    print("\n✓ TEST 3 PASSED\n")


def test_metadata_format():
    """Test that metadata has all expected fields."""
    print("=" * 60)
    print("TEST 4: Metadata Format")
    print("=" * 60)

    prompt = "Hello, world!"
    result = call_gpt_oss(prompt, max_tokens=50, reasoning_effort="medium")

    expected_fields = [
        "model",
        "max_tokens",
        "reasoning_effort",
        "prompt_length",
        "generated_tokens",
        "has_reasoning_tokens",
        "inference_engine",
    ]

    for field in expected_fields:
        assert field in result["metadata"], f"Missing expected field: {field}"
        print(f"✓ {field}: {result['metadata'][field]}")

    # Check specific values
    assert result["metadata"]["model"] == "openai/gpt-oss-120b", "Incorrect model name"
    assert result["metadata"]["inference_engine"] == "vllm", "Should use vLLM"
    assert result["metadata"]["max_tokens"] == 50, "Incorrect max_tokens"
    assert result["metadata"]["reasoning_effort"] == "medium", "Incorrect reasoning_effort"

    print("\n✓ TEST 4 PASSED\n")


def test_reasoning_tokens():
    """Test detection of reasoning tokens."""
    print("=" * 60)
    print("TEST 5: Reasoning Token Detection")
    print("=" * 60)

    prompt = "Think step by step: What is 15 * 23?"
    result = call_gpt_oss(prompt, max_tokens=300, reasoning_effort="high")

    print(f"✓ Has reasoning tokens: {result['metadata']['has_reasoning_tokens']}")
    print(f"✓ Generated tokens: {result['metadata']['generated_tokens']}")

    # Just check that the field exists and is boolean
    assert isinstance(result["metadata"]["has_reasoning_tokens"], bool), \
        "has_reasoning_tokens should be boolean"

    print("\n✓ TEST 5 PASSED\n")


def main():
    """Run all smoke tests."""
    print("\n" + "=" * 60)
    print("GPT-OSS vLLM SMOKE TESTS")
    print("=" * 60 + "\n")

    try:
        test_basic_generation()
        test_reasoning_efforts()
        test_csp_problem()
        test_metadata_format()
        test_reasoning_tokens()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nvLLM integration for GPT-OSS is working correctly!")

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
