#!/usr/bin/env python3
"""
Test that batch judge outputs are matched to requests by content, not position.

Run: python tests/batch/test_result_mapping.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# The helpers under test don't call Vertex; stub its client libraries if they aren't installed
from unittest import mock

for _name in ("google", "google.genai", "google.genai.types", "dotenv"):
    try:
        __import__(_name)
    except ImportError:
        sys.modules[_name] = mock.MagicMock()

from chunking.vertex_batch_judge import prepare_batch_requests, match_batch_results, batch_response_text


def fake_output(request: dict, answer: str) -> dict:
    """A Vertex batch output line: the echoed request plus a response."""
    return {
        "request": request["request"],
        "response": {"candidates": [{"content": {"parts": [{"text": answer}]}}]},
    }


def make_requests(texts):
    examples = [{"example_id": f"ex_{i}", "reasoning_text": t} for i, t in enumerate(texts)]
    return [e["example_id"] for e in examples], prepare_batch_requests(examples, "JUDGE PROMPT", max_output_tokens=10)


def test_shuffled_outputs_map_to_their_requests():
    ids, requests = make_requests([f"trace number {i}" for i in range(50)])
    outputs = [fake_output(r, f"answer for {i}") for i, r in zip(ids, requests)]
    random.Random(0).shuffle(outputs)
    matched = match_batch_results(outputs, requests, ids)
    assert len(matched) == 50
    for i in ids:
        assert batch_response_text(matched[i]) == f"answer for {i}", i


def test_duplicate_prompts_each_get_one_output():
    ids, requests = make_requests(["same", "same", "other"])
    outputs = [fake_output(requests[2], "B"), fake_output(requests[0], "A"), fake_output(requests[1], "A")]
    matched = match_batch_results(outputs, requests, ids)
    assert set(matched) == set(ids)
    assert batch_response_text(matched["ex_2"]) == "B"
    assert batch_response_text(matched["ex_0"]) == batch_response_text(matched["ex_1"]) == "A"


def test_missing_outputs_are_absent():
    ids, requests = make_requests(["a", "b", "c"])
    matched = match_batch_results([fake_output(requests[1], "B")], requests, ids)
    assert list(matched) == ["ex_1"]


def test_output_without_request_raises():
    ids, requests = make_requests(["a"])
    try:
        match_batch_results([{"response": {}}], requests, ids)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_unknown_prompt_raises():
    ids, requests = make_requests(["a"])
    _, other = make_requests(["not submitted"])
    try:
        match_batch_results([fake_output(other[0], "X")], requests, ids)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"✓ {t.__name__}")
    print(f"All {len(tests)} tests passed")
