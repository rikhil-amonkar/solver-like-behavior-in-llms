#!/usr/bin/env python3
"""
Run an open-weight judge (vLLM) on the validation chunks and score agreement.

Each chunk is sent the same way the Gemini judge received a trace segment:
one user message = judge prompt + "\\n\\n" + text. The judge's chunk labels are
collapsed to one label per input by character-weighted majority.

Usage (GPU 7, vllm-env):
    python validation/gemma_judge/run_judge.py \
        --model google/gemma-4-31B-it \
        --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
        --output validation/gemma_judge/gemma_baseline_prompt.json
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from chunking.chunk_parser import parse_judge_response  # noqa: E402

LABELS = ("solver-like", "sound")


def collapse_labels(chunks: list) -> dict:
    """Character-weighted majority label over the judge's chunks."""
    weight = {label: 0 for label in LABELS}
    for chunk in chunks:
        for label in LABELS:
            if label in chunk:
                weight[label] += len(chunk[label])
    if not any(weight.values()):
        return {"label": None, "any_solver_like": False, "weights": weight}
    return {
        "label": max(LABELS, key=lambda l: weight[l]),
        "any_solver_like": weight["solver-like"] > 0,
        "weights": weight,
    }


def main():
    parser = argparse.ArgumentParser(description="Run a vLLM judge on validation chunks")
    parser.add_argument("--model", default="google/gemma-4-31B-it")
    parser.add_argument("--judge-prompt", default="prompts/judge/llm_as_judge_for_chunking.txt")
    parser.add_argument("--sample", default="validation/gemma_judge/sample.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-tokens", type=int, default=8192)
    args = parser.parse_args()

    from vllm import LLM, SamplingParams

    judge_prompt = (REPO_ROOT / args.judge_prompt).read_text(encoding="utf-8")
    sample = json.loads((REPO_ROOT / args.sample).read_text(encoding="utf-8"))

    llm = LLM(model=args.model, max_model_len=16384, gpu_memory_utilization=0.9, max_num_seqs=64)
    messages = [[{"role": "user", "content": f"{judge_prompt}\n\n{c['text']}"}] for c in sample]
    outputs = llm.chat(messages, SamplingParams(temperature=0.0, max_tokens=args.max_tokens))

    results = []
    for chunk, output in zip(sample, outputs):
        response = output.outputs[0].text
        try:
            # Open models often wrap the JSON in a code fence; keep the outermost object
            json_text = response[response.find("{"):response.rfind("}") + 1]
            judged = parse_judge_response(json_text)["chunk_analysis"]
            parse_error = None
        except Exception as e:  # keep going; count as no label
            judged, parse_error = [], str(e)
        results.append({
            "id": chunk["id"],
            "gemini_label": chunk["gemini_label"],
            **collapse_labels(judged),
            "parse_error": parse_error,
            "judge_chunks": judged,
            "raw_response": response,
        })

    agree = sum(r["label"] == r["gemini_label"] for r in results)
    print(f"Agreement with Gemini labels: {agree}/{len(results)}")
    out = {
        "model": args.model,
        "judge_prompt": args.judge_prompt,
        "agreement_with_gemini": agree / len(results),
        "results": results,
    }
    (REPO_ROOT / args.output).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
