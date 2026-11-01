#!/usr/bin/env python3
"""
Blind round-3 check sheets for A1 and A2, balanced by the CURRENT judges' predictions so
every predicted label gets validated about equally (round 2 was stratified by gemma_v1,
and under the newer judges it had no rejecting Values paragraphs and 12/20 complete).

Two steps:
  pool    pick fresh traces (none used on any earlier sheet), spread over model x task,
          and write their judge inputs: checks/r3_traces.json (C) and
          checks/r3_segments.json (A). Run the judges on them, e.g.
            run_ontology_judges.py a --items validation/reliability/checks/r3_segments.json --tag gemma_v7
            run_ontology_judges.py c --items validation/reliability/checks/r3_traces.json --tag gemma_v8 --condense-a-tag gemma_v7
  sheets  stratify by those judges and write tabs a1r3 and a2r3 into judge_checks.json
          (the unlabeled a2r2 tab is removed):
          - a1r3: 20 paragraphs, 5 each of N, V with a rejection, V without, P (one per trace);
          - a2r3: 20 traces, 7 complete, 7 partial, 6 none.

Usage (vllm env, for tiktoken):
    python scripts/build_round3_sheets.py pool --n 150
    python scripts/build_round3_sheets.py sheets --a-tag gemma_v7 --c-tag gemma_v8
"""
import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from ontology_items import build_items
from build_check_sheets import stratified, trace_blocks, meta
from build_round2_sheets import key_value

A1_OPTS = [["V_rej", "Values, rejects a candidate"], ["V", "Values, no rejection"], ["P", "Properties"], ["N", "Not SLB"], ["unsure", "Can't tell"]]
A2_OPTS = [["complete", "Complete"], ["partial", "Partial"], ["none", "None"], ["unsure", "Can't tell"]]


def used_traces():
    sheets = json.load(open(REL / "judge_checks.json"))
    used = {it["trace"] for v in sheets.values() for it in v}
    for f in ("a2_verify.json", "b_verify.json"):
        used |= {it["trace"] for it in json.load(open(REL / f))}
    used |= {it["segment"].split("#")[0] for it in json.load(open(REL / "a1_verify.json"))}
    return used


def load(kind, tag):
    out = {}
    f = REL / "checks" / f"judge_{kind}_{tag}.jsonl"  # judge output sits next to the items file
    for line in open(f):
        r = json.loads(line)
        out[r["id"]] = r
    return out


def pool(n):
    rng = random.Random(2910)
    segments, traces = build_items()
    used = used_traces()
    cand = [t for t in traces if t["id"] not in used and t["ran"] and t["reasoning"].strip()]
    rng.shuffle(cand)
    by_cell = {}
    for t in cand:
        by_cell.setdefault((t["model"], t["task"]), []).append(t)
    picked = []
    while len(picked) < n and any(by_cell.values()):  # round-robin over model x task
        for cell in sorted(by_cell):
            if by_cell[cell] and len(picked) < n:
                picked.append(by_cell[cell].pop())
    ids = {t["id"] for t in picked}
    segs = [s for s in segments if s["trace"] in ids]
    json.dump(picked, open(REL / "checks/r3_traces.json", "w"))
    json.dump(segs, open(REL / "checks/r3_segments.json", "w"))
    print(len(picked), "traces,", len(segs), "segments")


def sheets(a_tag, c_tag):
    rng = random.Random(2911)
    traces = {t["id"]: t for t in json.load(open(REL / "checks/r3_traces.json"))}
    segs = json.load(open(REL / "checks/r3_segments.json"))
    ja, jc = load("a", a_tag), load("c", c_tag)
    out = json.load(open(REL / "judge_checks.json"))

    # A2 first, then A1 from other traces, so no trace is on both sheets
    pool_c = [((t["model"], t["task"]), t, jc[t["id"]]["extent"]) for t in traces.values() if t["id"] in jc and jc[t["id"]].get("extent")]
    picks = stratified(pool_c, [("complete", 7), ("partial", 7), ("none", 6)], key=lambda p: p[1]["id"], rng=rng)
    a2 = []
    for _, t, _ in picks:
        blocks = trace_blocks(t, program=False)
        for b in blocks:
            if b.get("search"):
                b["query"] = key_value(t)
        a2.append({**meta(t), "blind": True, "gemma_text": "",
                   "question": {"key": "a2", "type": "single", "prompt": "Does the reasoning reach an answer (its final position)?", "options": A2_OPTS, "gemma": None},
                   "blocks": [b for b in blocks if b["label"] != "Program"]})
    on_a2 = {it["trace"] for it in a2}

    pool_a = []
    for s in segs:
        r = ja.get(s["id"])
        if not r or s["trace"] in on_a2:
            continue
        for i, text in enumerate(s["paragraphs"]):
            if len(text) < 60:
                continue
            p = r["paras"].get(str(i), {"t": "N", "s": False})
            lab = "V_rej" if p["t"] == "V" and p["s"] else p["t"]
            pool_a.append(((s["model"], s["task"]), (s, i), lab))
    picks = stratified(pool_a, [("N", 5), ("V_rej", 5), ("V", 5), ("P", 5)], key=lambda p: p[1][0]["trace"], rng=rng)
    a1 = []
    for _, (s, i), _ in picks:
        a1.append({**{k: s[k] for k in ("model", "task", "cond")}, "trace": s["trace"], "segment": s["id"], "para": i, "blind": True,
                   "gemma_text": "", "question": {"key": "a1", "type": "single", "prompt": "What does the highlighted paragraph do?", "options": A1_OPTS, "gemma": None},
                   "blocks": [{"label": "Problem", "text": s["problem"], "mode": "collapsed"},
                              {"label": "", "text": s["paragraphs"][i - 1] if i else "", "mode": "context"},
                              {"label": "Paragraph", "text": s["paragraphs"][i], "mode": "target"},
                              {"label": "", "text": s["paragraphs"][i + 1] if i + 1 < len(s["paragraphs"]) else "", "mode": "context"}]})
    out.pop("a2r2", None)  # superseded before it was labeled
    out["a1r3"], out["a2r3"] = a1, a2
    for name in ("a1r3", "a2r3"):
        for k, it in enumerate(out[name]):
            it["id"] = f"{name}-{k:02d}"
        print(name, len(out[name]))
    json.dump(out, open(REL / "judge_checks.json", "w"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["pool", "sheets"])
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--a-tag")
    ap.add_argument("--c-tag")
    args = ap.parse_args()
    pool(args.n) if args.step == "pool" else sheets(args.a_tag, args.c_tag)


if __name__ == "__main__":
    main()
