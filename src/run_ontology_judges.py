#!/usr/bin/env python3
"""
Gemma judges for the SLB ontology (docs/SLB_ONTOLOGY.md), run offline with vLLM.

- a: labels every paragraph of a reasoning segment (type N/V/P; up to gemma_v7 also a search flag).
     Paragraphs are the same units the human labels (scripts/build_reliability_sets.py).
- b: labels a program (hardcoded / partly_fixed / steered / independent) and the
     specification-change flag.
- c: finds the answer reached in prose (A2 extent), rewrites it in the program's
     output format (for the C2 validator) and says whether it matches the output (C1).
- cs: the C judge per segment: does this excerpt state a complete answer (and which), a
     partial one, or none. scripts/assemble_ontology_labels.py takes the last complete
     answer of a trace as its prose answer (from gemma_v3).

Results are cached as JSONL (one line per item); re-running skips cached items, so
changing a prompt needs a new --tag.

With --items all, items are built from every stored run (src/ontology_items.py) and
results go to <root>/ontology/judge_<kind>_<tag>[.shard<i>].jsonl (--root: output, or
output_crossfl for the cross-FL runs). Cache keys are the item
id plus a hash of its text, so re-run traces are judged again. --shard i/n splits the
items across processes (one per GPU).

Usage (vllm-env, one GPU each):
    python src/run_ontology_judges.py a --items validation/reliability/segments.json --tag gemma_v1
    python src/run_ontology_judges.py a --items all --tag gemma_v1 --shard 0/2
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROMPTS = {"a": REPO / "prompts/judge/a_paragraphs.txt", "b": REPO / "prompts/judge/b_program.txt",
           "c": REPO / "prompts/judge/c_prose_answer.txt", "cs": REPO / "prompts/judge/c_segment.txt",
           "c_condensed": REPO / "prompts/judge/c_prose_answer_condensed.txt"}
LINE = re.compile(r"^\s*(\d+)\s*\|\s*(VP|PV|[NVP])\s*(?:\|\s*([01])\s*)?(?:\|\s*([a-z,\s-]*))?\s*$", re.M)  # search flag: up to gemma_v7; purposes: gemma_v1/v2
PURPOSES = {"ans", "chp", "chg", "int"}
REASONING_HEAD, REASONING_TAIL = 50000, 350000  # characters kept from a very long reasoning (B, C); fits a 160k-token context


def build_prompt(kind: str, item: dict, template: str) -> str:
    if kind == "a":
        paras = "\n\n".join(f"[{i + 1}]\n{p}" for i, p in enumerate(item["paragraphs"]))
        return (template.replace("{problem}", item["problem"]).replace("{n}", str(len(item["paragraphs"])))
                .replace("{segment}", str(item["segment_index"] + 1)).replace("{n_segments}", str(item["n_segments"]))
                .replace("{paragraphs}", paras))
    if kind == "cs":
        return (template.replace("{problem}", item["problem"]).replace("{segment}", str(item["segment_index"] + 1))
                .replace("{n_segments}", str(item["n_segments"])).replace("{text}", "\n\n".join(item["paragraphs"])))
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
                purposes = sorted({x.strip() for x in (p or "").split(",")} & PURPOSES) if t != "N" else []
                t = "VP" if t == "PV" else t  # VP (both): gemma_v11 on
                labels[i] = {"t": t, "s": t == "V" and s == "1", "p": purposes}
        missing = [i for i in range(len(item["paragraphs"])) if i not in labels]
        return {"paras": {str(i): v for i, v in labels.items()}, "missing": missing}
    start = text.find("{")
    if kind == "cs":
        try:
            obj, _ = json.JSONDecoder().raw_decode(text, start)
            extent = obj.get("extent")
            ok = extent in {"complete", "partial", "none"}
            return {"extent": extent if ok else None, "answer": obj.get("answer", "") if ok else "", "parse_error": not ok}
        except (ValueError, json.JSONDecodeError):
            return {"extent": None, "answer": "", "parse_error": True}
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
        # spec flag: none/required/not_required up to gemma_v1, none/changed in gemma_b2t, dropped from gemma_b3t on
        ok = label in {"hardcoded", "partly_fixed", "steered", "independent"} and spec in {None, "none", "changed", "required", "not_required"}
        return {"b": label if ok else None, "spec": spec if ok else None, "evidence": obj.get("evidence", ""), "parse_error": not ok}
    except (ValueError, json.JSONDecodeError):
        return {"b": None, "spec": None, "evidence": "", "parse_error": True}


def condense(traces, a_tag, values_only=False, root="output"):
    """Replace each trace's reasoning by its solver-like paragraphs (V or P per the A judge),
    in order, with a marker where other paragraphs were left out. The hash changes with the
    A labels, so a new A tag re-judges. Traces with any unjudged segment are dropped."""
    import glob
    import hashlib
    sys.path.insert(0, str(REPO / "src"))
    from ontology_items import build_items
    ja = {}
    for f in glob.glob(str(REPO / root / f"ontology/judge_a_{a_tag}*.jsonl")) + glob.glob(str(REPO / f"validation/reliability/checks/judge_a_{a_tag}.jsonl")):
        for line in open(f):
            r = json.loads(line)
            ja[(r["id"], r.get("h"))] = r
    segments, _ = build_items(root)
    by_trace = {}
    for s in segments:
        by_trace.setdefault(s["trace"], []).append(s)
    out = []
    for t in traces:
        segs = by_trace.get(t["id"], [])
        if not segs or any((s["id"], s["h"]) not in ja for s in segs):
            continue
        parts, gap = [], False
        for s in segs:
            r = ja[(s["id"], s["h"])]
            for i, p in enumerate(s["paragraphs"]):
                t_ = r["paras"].get(str(i), {"t": "N"})["t"]
                if ("V" in t_) if values_only else t_ != "N":
                    if gap and parts:
                        parts.append("[...]")
                    parts.append(p)
                    gap = False
                else:
                    gap = True
        text = "\n\n".join(parts) if parts else "(no solver-like paragraphs)"
        out.append({**t, "reasoning": text, "h": hashlib.sha1((t["h"] + a_tag + text).encode()).hexdigest()[:10]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["a", "b", "c", "cs"])
    ap.add_argument("--items", required=True, help="segments.json (a) or programs.json (b)")
    ap.add_argument("--tag", required=True, help="Output suffix; use a new tag whenever the prompt changes")
    ap.add_argument("--model", default="google/gemma-4-31B-it")
    ap.add_argument("--max-model-len", type=int, default=None)
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.92)
    ap.add_argument("--max-num-seqs", type=int, default=64)
    ap.add_argument("--quantization", default="fp8")
    ap.add_argument("--split", default=None, help="Only judge items of this split (dev/test)")
    ap.add_argument("--shard", default="0/1", help="i/n: judge every n-th item starting at i")
    ap.add_argument("--wave-size", type=int, default=1024, help="Requests per vLLM call between cache flushes")
    ap.add_argument("--condense-values-only", action="store_true",
                    help="Condense to Values paragraphs only (A1 properties dropped on 2026-10-29)")
    ap.add_argument("--thinking", type=int, default=0,
                    help="Gemma thinking mode with this many extra tokens for the thought (0: off)")
    ap.add_argument("--root", default="output",
                    help="With --items all: runs to judge (output, or output_crossfl); results go to <root>/ontology")
    ap.add_argument("--condense-a-tag", default=None,
                    help="C judge: give only the paragraphs this A-judge tag labelled V or P (in order, gaps marked)")
    args = ap.parse_args()
    shard, n_shards = map(int, args.shard.split("/"))

    if args.items == "all":
        sys.path.insert(0, str(REPO / "src"))
        from ontology_items import build_items
        segments, traces = build_items(args.root)
        items = segments if args.kind in ("a", "cs") else [t for t in traces if t["reasoning"].strip()]
        if args.kind == "b":
            items = [t for t in items if t["program"].strip()]
        out_dir = REPO / args.root / "ontology"
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = f".shard{shard}" if n_shards > 1 else ""
        out = out_dir / f"judge_{args.kind}_{args.tag}{suffix}.jsonl"
    else:
        items_path = Path(args.items)
        items = json.load(open(items_path))
        if args.split:
            items = [it for it in items if it.get("split") == args.split]
        # shards write to their own files: concurrent appends of long lines to one file can interleave
        suffix = f".shard{shard}" if n_shards > 1 else ""
        out = items_path.with_name(f"judge_{args.kind}_{args.tag}{suffix}.jsonl")
    if args.condense_a_tag:
        items = condense(items, args.condense_a_tag, args.condense_values_only, args.root)
    template = PROMPTS["c_condensed" if args.kind == "c" and args.condense_a_tag else args.kind].read_text(encoding="utf-8")
    # every record carries the prompt's hash, so a tag can never mix prompts (the first full A run,
    # tagged gemma_v11t, silently used the v12 prompt file)
    ph = hashlib.sha1(template.encode()).hexdigest()[:10]
    # The cache is every shard's file: when traces change, items move between shards.
    key = lambda r: (r["id"], r.get("h"))
    done = set()
    for f in out.parent.glob(f"judge_{args.kind}_{args.tag}*.jsonl"):
        recs = [json.loads(l) for l in f.open()]
        other = {r["ph"] for r in recs if r.get("ph", ph) != ph}
        if other:
            sys.exit(f"{f} was judged with another prompt ({', '.join(other)}, now {ph}); use a new tag")
        done |= {key(r) for r in recs}
    pending = [it for it in items if key(it) not in done]
    todo = [it for i, it in enumerate(pending) if i % n_shards == shard]
    print(f"{len(items)} items, {len(items) - len(pending)} cached, {len(todo)} to judge in this shard -> {out}", flush=True)
    if not todo:
        return

    from vllm import LLM, SamplingParams
    max_len = args.max_model_len or ((12288 + args.thinking) if args.kind in ("a", "cs") else 163840)
    chat_kw = {"enable_thinking": True} if args.thinking else {}
    llm = LLM(model=args.model, max_model_len=max_len, gpu_memory_utilization=args.gpu_memory_utilization,
              max_num_seqs=args.max_num_seqs, quantization=None if args.quantization == "none" else args.quantization,
              kv_cache_dtype="fp8", enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    start = time.time()
    for w in range(0, len(todo), args.wave_size):
        wave = todo[w:w + args.wave_size]
        msgs, params, keep = [], [], []
        for it in wave:
            m = [{"role": "user", "content": build_prompt(args.kind, it, template)}]
            n_in = len(tok.apply_chat_template(m, tokenize=True, add_generation_prompt=True, **chat_kw))
            budget = {"a": 20 * len(it.get("paragraphs", [])) + 200, "b": 400, "c": 1500, "cs": 1500}[args.kind] + args.thinking
            if n_in + 50 > max_len:  # prompt too long even after truncation: record, do not guess
                skipped = {"a": {"paras": {}, "missing": list(range(len(it.get("paragraphs", []))))},
                           "b": {"b": None, "spec": None, "evidence": "", "parse_error": True},
                           "c": {"extent": None, "match": None, "prose_answer": "", "parse_error": True},
                           "cs": {"extent": None, "answer": "", "parse_error": True}}[args.kind]
                with out.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": it["id"], "h": it.get("h"), "ph": ph, "response": "", "finish_reason": "prompt_too_long", **skipped}) + "\n")
                continue
            msgs.append(m)
            # with thinking, keep the channel markers so the thought can be split off before parsing
            params.append(SamplingParams(temperature=0.0, max_tokens=min(budget, max_len - n_in), skip_special_tokens=not args.thinking))
            keep.append(it)
        outputs = llm.chat(msgs, params, use_tqdm=False, chat_template_kwargs=chat_kw or None) if msgs else []
        with out.open("a", encoding="utf-8") as f:
            for it, o in zip(keep, outputs):
                text, thought = o.outputs[0].text, None
                if args.thinking:  # <|channel>thought\n ... <channel|> answer
                    head, sep, tail = text.partition("<channel|>")
                    thought, text = (head.replace("<|channel>thought", "", 1).strip(), tail) if sep else (head, "")
                    text = re.sub(r"<[|][^>]*>|<[^>]*[|]>", "", text)
                f.write(json.dumps({"id": it["id"], "h": it.get("h"), "ph": ph, "response": text, **({"thought": thought} if args.thinking else {}),
                                    "finish_reason": o.outputs[0].finish_reason, **parse(args.kind, text, it)}) + "\n")
        n = min(w + args.wave_size, len(todo))
        rate = n / (time.time() - start)
        print(f"{n}/{len(todo)} judged, {rate:.2f}/s, ~{(len(todo) - n) / rate / 60:.0f} min left", flush=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
