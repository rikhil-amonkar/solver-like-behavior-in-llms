#!/usr/bin/env python3
"""
Blind round-2 check sheets for A1 and A2 (no judge label shown), added to
validation/reliability/judge_checks.json as tabs "a1r2" and "a2r2". Items are new: no
segment or trace from earlier sheets. Stratified by the gemma_v1 labels so each class
appears, and spread over models and tasks.

- a1r2: 20 paragraphs (8 V, 5 P, 7 N by v1); one choice: values with a rejection,
        values without, properties, not SLB.
- a2r2: 20 traces (8 complete, 6 partial, 6 none by v1); choose the extent. The search
        box is pre-filled with a key value of the program's answer.

Usage (env venv):
    python scripts/build_round2_sheets.py
"""
import glob
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from ontology_items import build_items
from build_check_sheets import load_judge, stratified, trace_blocks, meta
from assemble_ontology_labels import problem_data
from execution.output_formatter import parse_output_by_task


def key_value(t):
    """A value from the program's answer to pre-fill the reasoning search."""
    try:
        if t["task"] == "blocksworld":
            line = next(l for l in (t["plan"] or "").splitlines() if l.strip().startswith("("))
            return line.strip("() \n")
        ans = parse_output_by_task(t["raw_stdout"], t["task"], problem_data(t["task"], t["example_id"]))
        if t["task"] == "calendar":
            return str(ans[1])
        if t["task"] == "meeting":
            meet = next(s for s in ans if "meet" in s.lower())
            return meet.split(" from ")[1].split(" to ")[0] if " from " in meet else meet.split()[2]
        if t["task"] == "zebralogic":
            return str(ans["rows"][0][1])
    except Exception:
        pass
    return ""


def main():
    rng = random.Random(1029)
    segments, traces = build_items()
    sheets = json.load(open(REL / "judge_checks.json"))
    used_traces = {it["trace"] for k, v in sheets.items() for it in v}
    used_traces |= {it["trace"] for it in json.load(open(REL / "a2_verify.json"))}
    used_traces |= {it["trace"] for it in json.load(open(REL / "b_verify.json"))}
    used_traces |= {s.split("#")[0] for s in (it["segment"] for it in json.load(open(REL / "a1_verify.json")))}
    ja, jc = load_judge("a"), load_judge("c")

    pool = []
    for s in segments:
        if s["trace"] in used_traces:
            continue
        r = ja.get((s["id"], s["h"]))
        if not r:
            continue
        for i, text in enumerate(s["paragraphs"]):
            if len(text) >= 60:
                pool.append(((s["model"], s["task"]), (s, i), r["paras"].get(str(i), {"t": "N"})["t"]))
    picks = stratified(pool, [("V", 8), ("P", 5), ("N", 7)], key=lambda p: p[1][0]["trace"], rng=rng)  # one paragraph per trace
    items = []
    for _, (s, i), _ in picks:
        items.append({**{k: s[k] for k in ("model", "task", "cond")}, "trace": s["trace"], "segment": s["id"], "para": i, "blind": True,
                      "gemma_text": "", "question": {"key": "a1", "type": "single", "prompt": "What does the highlighted paragraph do?",
                      "options": [["V_rej", "Values, rejects a candidate"], ["V", "Values, no rejection"], ["P", "Properties"], ["N", "Not SLB"], ["unsure", "Can't tell"]], "gemma": None},
                      "blocks": [{"label": "Problem", "text": s["problem"], "mode": "collapsed"},
                                 {"label": "", "text": s["paragraphs"][i - 1] if i else "", "mode": "context"},
                                 {"label": "Paragraph", "text": s["paragraphs"][i], "mode": "target"},
                                 {"label": "", "text": s["paragraphs"][i + 1] if i + 1 < len(s["paragraphs"]) else "", "mode": "context"}]})
    sheets["a1r2"] = items

    used2 = used_traces | {it["trace"] for it in items}
    pool = [((t["model"], t["task"]), t, jc[(t["id"], t["h"])]["extent"]) for t in traces
            if t["id"] not in used2 and (t["id"], t["h"]) in jc and jc[(t["id"], t["h"])].get("extent") and t["ran"]]
    picks = stratified(pool, [("complete", 8), ("partial", 6), ("none", 6)], key=lambda p: p[1]["id"], rng=rng)
    items = []
    for _, t, _ in picks:
        blocks = trace_blocks(t, program=False)
        for b in blocks:
            if b.get("search"):
                b["query"] = key_value(t)
        items.append({**meta(t), "blind": True, "gemma_text": "",
                      "question": {"key": "a2", "type": "single", "prompt": "Does the reasoning reach an answer (its final position)?",
                                   "options": [["complete", "Complete"], ["partial", "Partial"], ["none", "None"], ["unsure", "Can't tell"]], "gemma": None},
                      "blocks": [b for b in blocks if b["label"] != "Program"]})
    sheets["a2r2"] = items
    for name in ("a1r2", "a2r2"):
        for n, it in enumerate(sheets[name]):
            it["id"] = f"{name}-{n:02d}"
        print(name, len(sheets[name]))
    json.dump(sheets, open(REL / "judge_checks.json", "w"))


if __name__ == "__main__":
    main()
