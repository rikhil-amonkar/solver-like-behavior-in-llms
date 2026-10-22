#!/usr/bin/env python3
"""
Sample Gemma C-judge A2 labels (extent of the prose answer) for a human to verify.
Stratified: 4 complete, 3 partial, 3 none, spread over tasks and models.

Usage:
    python scripts/build_a2_verification.py --tag gemma_v1
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

PLAN = {"complete": 4, "partial": 3, "none": 3}
TASKS = ["calendar", "meeting", "zebralogic", "blocksworld"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="gemma_v1")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    jc = {}
    for f in glob.glob(str(REPO / f"output/ontology/judge_c_{args.tag}*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            if r.get("extent"):
                jc[(r["id"], r.get("h"))] = r
    _, traces = build_items()
    rng = random.Random(args.seed)
    pools = {}
    for t in traces:
        r = jc.get((t["id"], t["h"]))
        if r:
            pools.setdefault(r["extent"], []).append((t, r))
    items = []
    for extent, k in PLAN.items():
        pool = pools.get(extent, [])
        rng.shuffle(pool)
        seen_tasks, picks = set(), []
        for t, r in pool:  # first pass: one per task
            if len(picks) < k and t["task"] not in seen_tasks:
                picks.append((t, r)); seen_tasks.add(t["task"])
        for t, r in pool:
            if len(picks) < k and (t, r) not in picks:
                picks.append((t, r))
        for t, r in picks:
            items.append(dict(model=t["model"], task=t["task"], cond=t["cond"], trace=t["id"], problem=t["problem"],
                              reasoning=t["reasoning"], output=t["output"] if t["task"] == "blocksworld" else t["raw_stdout"][:4000],
                              gemma={"extent": r["extent"], "match": r["match"], "prose_answer": r.get("prose_answer", "")}))
    rng.shuffle(items)
    for n, it in enumerate(items):
        it["id"] = f"e{n:02d}"
    out = REPO / "validation/reliability/a2_verify.json"
    json.dump(items, open(out, "w"), indent=1)
    print(len(items), "items ->", out, [(it["task"], it["model"], it["gemma"]["extent"]) for it in items])


if __name__ == "__main__":
    main()
