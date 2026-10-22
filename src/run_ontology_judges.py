#!/usr/bin/env python3
"""
Gemma judges for the SLB ontology (docs/SLB_ONTOLOGY.md), run offline with vLLM.

- a: labels every paragraph of a reasoning segment (type N/V/P, search flag, purposes).
     Paragraphs are the same units the human labels (scripts/build_reliability_sets.py).
- b: labels a program (hardcoded / partly_fixed / steered / independent) and the
     specification-change flag.
- c: finds the answer reached in prose (A2 extent), rewrites it in the program's
     output format (for the C2 validator) and says whether it matches the output (C1).

Results are cached as JSONL (one line per item); re-running skips cached items, so
changing a prompt needs a new --tag.

Usage (vllm-env, one GPU):
    python src/run_ontology_judges.py a --items validation/reliability/segments.json --tag gemma_v1
    python src/run_ontology_judges.py b --items validation/reliability/programs.json --tag gemma_v1
"""

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROMPTS = {"a": REPO / "prompts/judge/a_paragraphs.txt", "b": REPO / "prompts/judge/b_program.txt",
           "c": REPO / "prompts/judge/c_prose_answer.txt"}
LINE = re.compile(r"^\s*(\d+)\s*\|\s*([NVP])\s*\|\s*([01])\s*\|\s*([a-z,\s-]*)\s*$", re.M)
PURPOSES = {"ans", "chp", "chg", "int"}
REASONING_HEAD, REASONING_TAIL = 6000, 40000  # characters kept from a long reasoning for the B judge


def build_prompt(kind: str, item: dict, template: str) -> str:
    if kind == "a":
        paras = "\n\n".join(f"[{i + 1}]\n{p}" for i, p in enumerate(item["paragraphs"]))
        return (template.replace("{problem}", item["problem"]).replace("{n}", str(len(item["paragraphs"])))
                .replace("{segment}", str(item["segment_index"] + 1)).replace("{n_segments}", str(item["n_segments"]))
                .replace("{paragraphs}", paras))
    reasoning, note = item["reasoning"], ""
    if len(reasoning) > REASONING_HEAD + REASONING_TAIL:
        cut = len(reasoning) - REASONING_HEAD - REASONING_TAIL
        reasoning = reasoning[:REASONING_HEAD] + f"\n\n[... {cut} characters omitted ...]\n\n" + reasoning[-REASONING_TAIL:]
        note = " (middle omitted)"
    return (template.replace("{problem}", item["problem"]).replace("{reasoning_note}", note)
            .replace("{reasoning}", reasoning).replace("{program}", item["program"] or "(none)")
            .replace("{output}", item.get("output") or "(no output)"))


def parse(kind: str, text: str, item: dict) -> dict:
    """Parse a judge response. Unparsed paragraphs are reported, never guessed."""
    if kind == "a":
        labels = {}
        for n, t, s, p in LINE.findall(text):
            i = int(n) - 1
            if 0 <= i < len(item["paragraphs"]) and i not in labels:
                purposes = sorted({x.strip() for x in p.split(",")} & PURPOSES) if t != "N" else []
                labels[i] = {"t": t, "s": t == "V" and s == "1", "p": purposes}
        missing = [i for i in range(len(item["paragraphs"])) if i not in labels]
        return {"paras": {str(i): v for i, v in labels.items()}, "missing": missing}
    start = text.find("{")
    if kind == "c":
        try:
            obj, _ = json.JSONDecoder().raw_decode(text, start)
            extent, match = obj.get("extent"), obj.get("match")
            ok = extent in {"complete", "partial", "none"} and match in {"yes", "no", "na"}
            return {"extent": extent if ok else None, "match": match if ok else None,
                    "prose_answer": obj.get("prose_answer", ""), "parse_error": not ok}
        except (ValueError, json.JSONDecodeError):
            return {"extent": None, "match": None, "prose_answer": "", "parse_error": True}
    try:
        obj, _ = json.JSONDecoder().raw_decode(text, start)
        label, spec = obj.get("label"), obj.get("spec")
        ok = label in {"hardcoded", "partly_fixed", "steered", "independent"} and spec in {"none", "required", "not_required"}
        return {"b": label if ok else None, "spec": spec if ok else None, "evidence": obj.get("evidence", ""), "parse_error": not ok}
    except (ValueError, json.JSONDecodeError):
        return {"b": None, "spec": None, "evidence": "", "parse_error": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["a", "b", "c"])
    ap.add_argument("--items", required=True, help="segments.json (a) or programs.json (b)")
    ap.add_argument("--tag", required=True, help="Output suffix; use a new tag whenever the prompt changes")
    ap.add_argument("--model", default="google/gemma-4-31B-it")
    ap.add_argument("--max-model-len", type=int, default=None)
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.92)
    ap.add_argument("--max-num-seqs", type=int, default=64)
    ap.add_argument("--quantization", default="fp8")
    ap.add_argument("--split", default=None, help="Only judge items of this split (dev/test)")
    args = ap.parse_args()

    items_path = Path(args.items)
    items = json.load(open(items_path))
    if args.split:
        items = [it for it in items if it.get("split") == args.split]
    out = items_path.with_name(f"judge_{args.kind}_{args.tag}.jsonl")
    done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
    todo = [it for it in items if it["id"] not in done]
    print(f"{len(items)} items, {len(done)} cached, {len(todo)} to judge -> {out}")
    if not todo:
        return

    from vllm import LLM, SamplingParams
    max_len = args.max_model_len or (12288 if args.kind == "a" else 32768)
    llm = LLM(model=args.model, max_model_len=max_len, gpu_memory_utilization=args.gpu_memory_utilization,
              max_num_seqs=args.max_num_seqs, quantization=None if args.quantization == "none" else args.quantization,
              kv_cache_dtype="fp8", enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    template = PROMPTS[args.kind].read_text(encoding="utf-8")
    msgs = [[{"role": "user", "content": build_prompt(args.kind, it, template)}] for it in todo]
    params = []
    for m, it in zip(msgs, todo):
        n_in = len(tok.apply_chat_template(m, tokenize=True, add_generation_prompt=True))
        budget = 20 * len(it["paragraphs"]) + 200 if args.kind == "a" else 400 if args.kind == "b" else 1500
        params.append(SamplingParams(temperature=0.0, max_tokens=max(1, min(budget, max_len - n_in))))
    outputs = llm.chat(msgs, params)
    with out.open("a", encoding="utf-8") as f:
        for it, o in zip(todo, outputs):
            text = o.outputs[0].text
            f.write(json.dumps({"id": it["id"], "response": text, "finish_reason": o.outputs[0].finish_reason,
                                **parse(args.kind, text, it)}) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
