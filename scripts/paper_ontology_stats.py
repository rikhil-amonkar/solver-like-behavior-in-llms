#!/usr/bin/env python3
"""
Per-trace table for the paper's results (Section 5): the assembled ontology labels
(output/<m>/<t>/<c>_ontology_<tag>.json) joined with program accuracy (<c>_evaluation.json) and
token counts (cl100k, the tokenizer the segmenter uses): reasoning tokens and solver-like tokens
(tokens in paragraphs the A judge labels V or VP).

Writes output/paper/ontology_traces_<tag>.json (one row per trace) and prints per-cell summaries.

Usage (vllm env, for tiktoken):
    python scripts/paper_ontology_stats.py --tag gemma_v11_b5t --a-tag gemma_v11t
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import tiktoken

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from ontology_items import build_items, MODELS, TASKS, CONDS
from assemble_ontology_labels import load_judge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="gemma_v11_b5t")
    ap.add_argument("--a-tag", default="gemma_v11t")
    args = ap.parse_args()
    enc = tiktoken.get_encoding("cl100k_base")
    ntok = lambda s: len(enc.encode(s, disallowed_special=()))
    segments, _ = build_items()
    ja = load_judge("a", args.a_tag)
    tok = collections.defaultdict(lambda: [0, 0])  # trace -> [reasoning tokens, solver-like tokens]
    for s in segments:
        r = ja.get((s["id"], s["h"]))
        for i, text in enumerate(s["paragraphs"]):
            n = ntok(text)
            tok[s["trace"]][0] += n
            if r and "V" in r["paras"].get(str(i), {"t": "N"})["t"]:
                tok[s["trace"]][1] += n
    rows = []
    for m in MODELS:
        for t in TASKS:
            for c in CONDS:
                lab = json.load(open(REPO / f"output/{m}/{t}/{c}_ontology_{args.tag}.json"))["examples"]
                ev = {e["example_id"]: e for e in json.load(open(REPO / f"output/{m}/{t}/{c}_evaluation.json"))["examples"]}
                for r in lab:
                    e = ev.get(r["example_id"], {})
                    rt, st = tok.get(f"{m}/{t}/{c}/{r['example_id']}", [0, 0])
                    rows.append(dict(model=m, task=t, cond=c, example_id=r["example_id"],
                                     values="values" in r["A1"], ratio=r["ratio"], A2=r["A2"], B=r["B"],
                                     C1=r["C1"], c1_source=r["c1_source"], C2=r["C2"],
                                     correct=e.get("correct") in (True, "True"), outcome=e.get("classification"),
                                     reasoning_tokens=rt, slb_tokens=st))
    out = REPO / f"output/paper/ontology_traces_{args.tag}.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(rows, open(out, "w"), indent=0)
    print("wrote", out, len(rows))
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["model"], r["task"], r["cond"])].append(r)
    print("cell\tacc\tvalues\tcmpl\tpart\tratio\tslb_tok\treas_tok\tB1\tB2\tB3\tB4\tna")
    for k in sorted(by):
        g = by[k]
        n = len(g)
        mean = lambda f: sum(map(f, g)) / n
        print("/".join(k), f"{mean(lambda r: r['correct']):.2f}", sum(r["values"] for r in g),
              sum(r["A2"] == "complete" for r in g), sum(r["A2"] == "partial" for r in g),
              f"{mean(lambda r: r['ratio'] or 0):.2f}", f"{mean(lambda r: r['slb_tokens']):.0f}",
              f"{mean(lambda r: r['reasoning_tokens']):.0f}",
              *[sum(r["B"] == b for r in g) for b in ("hardcoded", "partly_fixed", "steered", "independent", "na")], sep="\t")


if __name__ == "__main__":
    main()
