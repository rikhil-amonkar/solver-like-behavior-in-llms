#!/usr/bin/env python3
"""
Smoke test for Qwen vLLM integration.

Tests that the vLLM-based call_qwen() function:
1. Loads the model successfully
2. Generates valid responses
3. Returns correct metadata format
4. Preserves thinking tags (if present)

Usage:
    python tests/vllm/test_qwen_vllm.py
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from models.call_qwen import call_qwen


def test_basic_generation():
    """Test basic text generation."""
    print("=" * 60)
    print("TEST 1: Basic Generation")
    print("=" * 60)

    prompt = "What is 2 + 2? Answer in one sentence."
    result = call_qwen(prompt, max_tokens=100, enable_thinking=False)

    assert "reasoning_trace" in result, "Missing reasoning_trace in result"
    assert "metadata" in result, "Missing metadata in result"
    assert len(result["reasoning_trace"]) > 0, "Empty reasoning trace"

    print(f"✓ Generated {len(result['reasoning_trace'])} characters")
    print(f"✓ Prompt tokens: {result['metadata']['prompt_length']}")
    print(f"✓ Generated tokens: {result['metadata']['generated_tokens']}")
    print(f"✓ Inference engine: {result['metadata'].get('inference_engine', 'unknown')}")
    print(f"\nResponse preview: {result['reasoning_trace'][:200]}...")
    print("\n✓ TEST 1 PASSED\n")


def test_thinking_mode():
    """Test generation with thinking mode enabled."""
    print("=" * 60)
    print("TEST 2: Thinking Mode")
    print("=" * 60)

    prompt = "Solve this problem step by step: If a train travels 60 mph for 2.5 hours, how far does it go?"
    result = call_qwen(prompt, max_tokens=500, enable_thinking=True)

    assert "reasoning_trace" in result, "Missing reasoning_trace in result"
    assert "metadata" in result, "Missing metadata in result"
    assert result["metadata"]["enable_thinking"] == True, "Thinking mode not enabled in metadata"

    print(f"✓ Generated {len(result['reasoning_trace'])} characters")
    print(f"✓ Has thinking tags: {result['metadata']['has_thinking_tags']}")
    print(f"✓ Generated tokens: {result['metadata']['generated_tokens']}")
    print(f"\nResponse preview: {result['reasoning_trace'][:300]}...")
    print("\n✓ TEST 2 PASSED\n")


def test_csp_problem():
    """Test with a simple CSP-style problem (similar to actual usage)."""
    print("=" * 60)
    print("TEST 3: CSP Problem (Calendar Scheduling)")
    print("=" * 60)

    prompt = """You are solving a constraint satisfaction problem.

Problem:
Schedule a 1-hour meeting on Monday for Alice and Bob.
- Alice is unavailable: 9:00-12:00
- Bob is unavailable: 14:00-17:00

Write Python code using a solver to find a valid meeting time.

Output format: ['Monday', 'HH:MM', 'HH:MM']
"""

    result = call_qwen(prompt, max_tokens=1000, enable_thinking=True)

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
    result = call_qwen(prompt, max_tokens=50)

    expected_fields = [
        "model",
        "max_tokens",
        "enable_thinking",
        "prompt_length",
        "generated_tokens",
        "has_thinking_tags",
        "inference_engine",
    ]

    for field in expected_fields:
        assert field in result["metadata"], f"Missing expected field: {field}"
        print(f"✓ {field}: {result['metadata'][field]}")

    # Check specific values
    assert result["metadata"]["model"] == "Qwen/Qwen3.8-27B", "Incorrect model name"
    assert result["metadata"]["inference_engine"] == "vllm", "Should use vLLM"
    assert result["metadata"]["max_tokens"] == 50, "Incorrect max_tokens"

    print("\n✓ TEST 4 PASSED\n")


def main():
    """Run all smoke tests."""
    print("\n" + "=" * 60)
    print("QWEN vLLM SMOKE TESTS")
    print("=" * 60 + "\n")

    try:
        test_basic_generation()
        test_thinking_mode()
        test_csp_problem()
        test_metadata_format()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nvLLM integration for Qwen is working correctly!")

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
