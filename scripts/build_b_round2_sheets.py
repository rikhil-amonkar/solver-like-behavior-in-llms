#!/usr/bin/env python3
"""
Blind B check sheets balanced by the new B judge's predictions (gemma_b2t: none/changed spec
flag, thinking mode), tabs "br2" and "specr2" in validation/reliability/judge_checks.json:

- br2:    20 traces, 5 each predicted hardcoded, partly fixed, steered, independent;
- specr2: 20 traces, 10 predicted changed, 10 none (none of them on br2).

The pool (validation/reliability/checks/b_pool{0,1}/traces.json) oversamples the rare labels:
every fresh trace that gemma_v1 labelled non-independent or with a specification change, plus
200 random independent ones; no trace from an earlier sheet.

Usage (vllm env, for tiktoken):
    python scripts/build_b_round2_sheets.py
"""
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from build_check_sheets import stratified, trace_blocks, meta, B_OPTS

TAG = "gemma_b2t"
SPEC2_OPTS = [["none", "No change"], ["changed", "Changed (drops, relaxes or adds a constraint, goal or action the problem doesn't call for)"]]


def main():
    rng = random.Random(1030)
    traces, jb = {}, {}
    for k in (0, 1):
        d = REL / f"checks/b_pool{k}"
        traces.update({t["id"]: t for t in json.load(open(d / "traces.json"))})
        for line in open(d / f"judge_b_{TAG}.jsonl"):
            r = json.loads(line)
            jb[r["id"]] = r
    ok = {i: r for i, r in jb.items() if r.get("b") and not r.get("parse_error")}
    pool = [((traces[i]["model"], traces[i]["task"]), traces[i], r["b"]) for i, r in ok.items()]
    picks = stratified(pool, [("hardcoded", 5), ("partly_fixed", 5), ("steered", 5), ("independent", 5)], key=lambda p: p[1]["id"], rng=rng)
    br2 = [{**meta(t), "blind": True, "gemma_text": "",
            "question": {"key": "b", "type": "single", "prompt": "What does the program do with the answer the prose reached?",
                         "options": B_OPTS + [["unsure", "Can't tell"]], "gemma": None},
            "blocks": trace_blocks(t)} for _, t, _ in picks]
    on_b = {it["trace"] for it in br2}
    pool = [((traces[i]["model"], traces[i]["task"]), traces[i], r["spec"]) for i, r in ok.items() if i not in on_b and r.get("spec") in ("none", "changed")]
    picks = stratified(pool, [("changed", 10), ("none", 10)], key=lambda p: p[1]["id"], rng=rng)
    specr2 = [{**meta(t), "blind": True, "gemma_text": "",
               "question": {"key": "spec", "type": "single", "prompt": "Does the program drop, relax or add a constraint, goal or action that the problem doesn't call for?",
                            "options": SPEC2_OPTS + [["unsure", "Can't tell"]], "gemma": None},
               "blocks": trace_blocks(t, output=False)} for _, t, _ in picks]
    sheets = json.load(open(REL / "judge_checks.json"))
    for name, items in (("br2", br2), ("specr2", specr2)):
        for n, it in enumerate(items):
            it["id"] = f"{name}-{n:02d}"
        sheets[name] = items
        print(name, len(items))
    json.dump(sheets, open(REL / "judge_checks.json", "w"))


if __name__ == "__main__":
    main()
