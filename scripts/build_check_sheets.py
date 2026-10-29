#!/usr/bin/env python3
"""
20-item human check sheets for the remaining ontology nodes, in one schema for the
judge-check page (validation/reliability/judge_checks.html):

- a3:   SLB paragraphs, 5 per purpose Gemma gave (ans, chp, chg, int); check the purposes.
        (A3 was dropped from the ontology on 2026-10-29; the sheet is kept so the other
        sheets, drawn after it from the same random stream, stay the same.)
- b:    the B sheet (validation/reliability/b_verify.json); check the label.
- spec: 8 not_required, 4 required, 8 none; check the specification-change flag.
- c1:   complete prose answers, 10 the parser says match the output and 10 it says differ;
        check whether they are the same answer.
- c2:   complete prose answers, 10 the validator accepts and 10 it rejects; check
        whether the prose answer is a correct solution.

Labels come from the gemma_v1 full run (A, B, C judges) and the script judges.
Each pick takes the least-used model x task cell, so sheets spread over models and tasks.

Usage (env venv):
    python scripts/build_check_sheets.py
"""

import glob
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
from ontology_items import build_items

TAG = "gemma_v1"
PURPOSE = {"ans": "Answer", "chp": "Check problem", "chg": "Check program", "int": "Disambiguate by solving"}
TYPE = {"V": "Values", "P": "Properties", "N": "Not SLB"}
B_OPTS = [["hardcoded", "Hardcoded"], ["partly_fixed", "Partly fixed"], ["steered", "Steered"], ["independent", "Independent"]]
SPEC_OPTS = [["none", "No change"], ["required", "Changed, required by the problem"], ["not_required", "Changed, not required"]]


def load_judge(kind):
    out = {}
    for f in sorted(glob.glob(str(REPO / f"output/ontology/judge_{kind}_{TAG}*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            out[(r["id"], r.get("h"))] = r
    return out


def stratified(pool, plan, key, rng):
    """pool: list of (cell, payload, value); plan: [(value, k)]; least-used cell first."""
    rng.shuffle(pool)
    used, chosen, picks = {}, set(), []
    for value, k in plan:
        for _ in range(k):
            cands = [p for p in pool if p[2] == value and key(p) not in chosen]
            if not cands:
                break
            p = min(cands, key=lambda x: (used.get(x[0], 0), rng.random()))
            used[p[0]] = used.get(p[0], 0) + 1
            chosen.add(key(p))
            picks.append(p)
    rng.shuffle(picks)
    return picks


def trace_blocks(t, reasoning=True, program=True, output=True):
    blocks = [{"label": "Problem", "text": t["problem"], "mode": "collapsed"}]
    if reasoning:
        blocks.append({"label": f"Reasoning ({round(len(t['reasoning']) / 1000)}k characters; the end is shown, search below)",
                       "text": t["reasoning"], "mode": "tail", "search": True})
    if program:
        blocks.append({"label": "Program", "text": t["program"], "mode": "open"})
    if output:
        out = t["plan"] or t["output"] if t["task"] == "blocksworld" else t["raw_stdout"][:4000]
        blocks.append({"label": "Program output" + (" (planner's plan)" if t["task"] == "blocksworld" else ""), "text": out or "(no output)", "mode": "open"})
    return blocks


def meta(t):
    return {"model": t["model"], "task": t["task"], "cond": t["cond"], "trace": t["id"]}


def main():
    rng = random.Random(29)
    segments, traces = build_items()
    tr = {t["id"]: t for t in traces}
    ja, jb, jc = load_judge("a"), load_judge("b"), load_judge("c")
    onto = {}
    for f in glob.glob(str(REPO / f"output/*/*/*_ontology_{TAG}.json")):
        m, task, fn = f.split("/")[-3:]
        cond = fn.split("_ontology")[0]
        for e in json.load(open(f))["examples"]:
            onto[f"{m}/{task}/{cond}/{e['example_id']}"] = e
    sheets = {}

    # ---- A3: one SLB paragraph per pick, by a purpose Gemma gave it ----
    pool = []
    for s in segments:
        r = ja.get((s["id"], s["h"]))
        if not r:
            continue
        for i, text in enumerate(s["paragraphs"]):
            lab = r["paras"].get(str(i))
            if lab and lab["t"] != "N" and lab["p"] and len(text) >= 60:
                for p in lab["p"]:
                    pool.append(((s["model"], s["task"]), (s, i, lab), p))
    picks = stratified(pool, [(p, 5) for p in PURPOSE], key=lambda p: (p[1][0]["id"], p[1][1]), rng=rng)
    items = []
    for _, (s, i, lab), _ in picks:
        items.append({**{k: s[k] for k in ("model", "task", "cond")}, "trace": s["trace"], "segment": s["id"], "para": i,
                      "gemma_text": f"{TYPE[lab['t']]}; purposes: " + ", ".join(PURPOSE[p] for p in lab["p"]),
                      "question": {"key": "purposes", "type": "multi", "prompt": "Which purposes apply?",
                                   "options": [[k, v] for k, v in PURPOSE.items()], "gemma": lab["p"]},
                      "blocks": [{"label": "Problem", "text": s["problem"], "mode": "collapsed"},
                                 {"label": "Paragraph before", "text": s["paragraphs"][i - 1] if i else "", "mode": "context"},
                                 {"label": "Paragraph", "text": s["paragraphs"][i], "mode": "target"},
                                 {"label": "Paragraph after", "text": s["paragraphs"][i + 1] if i + 1 < len(s["paragraphs"]) else "", "mode": "context"}]})
    sheets["a3"] = items

    # ---- B: reuse the existing B sheet ----
    items = []
    for it in json.load(open(REL / "b_verify.json")):
        t = tr[it["trace"]]
        g = it["gemma"]
        items.append({**meta(t), "gemma_text": f"{dict(B_OPTS)[g['b']]}. Evidence: {g['evidence']}",
                      "question": {"key": "b", "type": "single", "prompt": "What does the program do with the prose answer?",
                                   "options": B_OPTS, "gemma": g["b"]},
                      "blocks": trace_blocks(t)})
    sheets["b"] = items

    # ---- Spec change ----
    pool = [((t["model"], t["task"]), t, jb[(t["id"], t["h"])]["spec"]) for t in traces
            if (t["id"], t["h"]) in jb and jb[(t["id"], t["h"])].get("spec") and t["program"].strip()]
    picks = stratified(pool, [("not_required", 8), ("required", 4), ("none", 8)], key=lambda p: p[1]["id"], rng=rng)
    items = []
    for _, t, _ in picks:
        r = jb[(t["id"], t["h"])]
        items.append({**meta(t), "gemma_text": f"{dict(SPEC_OPTS)[r['spec']]}. Evidence: {r.get('evidence', '')}",
                      "question": {"key": "spec", "type": "single", "prompt": "Does the program drop, relax or add a constraint, goal or action?",
                                   "options": SPEC_OPTS, "gemma": r["spec"]},
                      "blocks": trace_blocks(t, output=False)})
    sheets["spec"] = items

    # ---- C1 and C2: complete prose answers ----
    comp = [t for t in traces if onto.get(t["id"], {}).get("A2") == "complete" and (t["id"], t["h"]) in jc]
    pool = [((t["model"], t["task"]), t, onto[t["id"]]["C1"]) for t in comp if onto[t["id"]]["c1_source"] == "script"]
    picks = stratified(pool, [(True, 10), (False, 10)], key=lambda p: p[1]["id"], rng=rng)
    items = []
    for _, t, v in picks:
        prose = jc[(t["id"], t["h"])]["prose_answer"]
        items.append({**meta(t), "gemma_text": "Script: " + ("same answer" if v else "different answers"),
                      "question": {"key": "c1", "type": "single", "prompt": "Are these the same answer (formatting aside)?",
                                   "options": [[True, "Same"], [False, "Different"]], "gemma": v},
                      "blocks": [{"label": "Answer reached in the prose (as extracted by Gemma)", "text": prose, "mode": "target"},
                                 {"label": "Program output" + (" (planner's plan)" if t["task"] == "blocksworld" else ""),
                                  "text": (t["plan"] if t["task"] == "blocksworld" else t["raw_stdout"][:4000]) or "(no output)", "mode": "target"},
                                 {"label": "Problem", "text": t["problem"], "mode": "collapsed"}]})
    sheets["c1"] = items

    pool = [((t["model"], t["task"]), t, onto[t["id"]]["C2"]) for t in comp if onto[t["id"]]["C2"] is not None]
    picks = stratified(pool, [(True, 10), (False, 10)], key=lambda p: p[1]["id"], rng=rng)
    items = []
    for _, t, v in picks:
        prose = jc[(t["id"], t["h"])]["prose_answer"]
        items.append({**meta(t), "gemma_text": "Validator: " + ("correct" if v else "incorrect"),
                      "question": {"key": "c2", "type": "single", "prompt": "Is this prose answer a correct solution to the problem?",
                                   "options": [[True, "Correct"], [False, "Incorrect"], ["unsure", "Can't tell"]], "gemma": v},
                      "blocks": [{"label": "Problem", "text": t["problem"], "mode": "open"},
                                 {"label": "Answer reached in the prose (as extracted by Gemma)", "text": prose, "mode": "target"}]})
    sheets["c2"] = items

    for name, items in sheets.items():
        for n, it in enumerate(items):
            it["id"] = f"{name}-{n:02d}"
        print(name, len(items))
    json.dump(sheets, open(REL / "judge_checks.json", "w"))


if __name__ == "__main__":
    main()
