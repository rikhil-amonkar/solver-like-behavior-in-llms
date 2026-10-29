#!/usr/bin/env python3
"""
Sample Gemma B-judge labels (what the program does with the prose answer, plus the
specification-change flag) for a human to verify.

20 programs: 4 hardcoded, 5 partly fixed, 4 steered, 4 independent, and 3 more whose
spec change is "not required" (whatever their label), spread over models and tasks
(each pick takes the least-used model x task cell). B = n/a is decided by script and
is not sampled.

Usage:
    python scripts/build_b_verification.py --tag gemma_v1
"""

import argparse
import glob
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from ontology_items import build_items

PLAN = [("b", "hardcoded", 4), ("b", "partly_fixed", 5), ("b", "steered", 4), ("b", "independent", 4), ("spec", "not_required", 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="gemma_v1")
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args()
    jb = {}
    for f in glob.glob(str(REPO / f"output/ontology/judge_b_{args.tag}*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            if r.get("b"):
                jb[(r["id"], r.get("h"))] = r
    _, traces = build_items()
    pool = [(t, jb[(t["id"], t["h"])]) for t in traces
            if (t["id"], t["h"]) in jb and t["ran"] and (t["raw_stdout"].strip() or t["task"] == "blocksworld")]
    rng = random.Random(args.seed)
    rng.shuffle(pool)
    used, chosen, items = {}, set(), []
    for field, value, k in PLAN:
        for _ in range(k):
            cands = [(t, r) for t, r in pool if r[field] == value and t["id"] not in chosen]
            if not cands:
                break
            t, r = min(cands, key=lambda x: (used.get((x[0]["model"], x[0]["task"]), 0), rng.random()))
            used[(t["model"], t["task"])] = used.get((t["model"], t["task"]), 0) + 1
            chosen.add(t["id"])
            items.append(dict(model=t["model"], task=t["task"], cond=t["cond"], trace=t["id"], problem=t["problem"],
                              reasoning=t["reasoning"], program=t["program"],
                              output=t["output"] if t["task"] == "blocksworld" else t["raw_stdout"][:4000],
                              gemma={"b": r["b"], "spec": r["spec"], "evidence": r.get("evidence", "")}))
    rng.shuffle(items)
    for n, it in enumerate(items):
        it["id"] = f"b{n:02d}"
    out = REPO / "validation/reliability/b_verify.json"
    json.dump(items, open(out, "w"), indent=1)
    print(len(items), "items ->", out)


if __name__ == "__main__":
    main()
