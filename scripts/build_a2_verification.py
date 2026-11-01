#!/usr/bin/env python3
"""
Sample Gemma C-judge A2 labels (extent of the prose answer) for a human to verify.
20 items: 8 complete, 6 partial, 6 none, spread over models and tasks (each pick takes
the least-used model x task cell that has that extent). Item e00 of the first sheet
(already checked) is kept as e00.

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

PLAN = {"complete": 8, "partial": 6, "none": 6}
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
    keep = json.load(open(REPO / "validation/reliability/a2_verify.json"))[0]  # e00, already checked
    used = {(keep["model"], keep["task"]): 1}
    chosen = {keep["trace"]}
    items = [keep]
    plan = dict(PLAN)
    plan[keep["gemma"]["extent"]] -= 1
    for extent, k in plan.items():
        pool = pools.get(extent, [])
        rng.shuffle(pool)
        for _ in range(k):
            cands = [(t, r) for t, r in pool if t["id"] not in chosen]
            if not cands:
                break
            t, r = min(cands, key=lambda x: (used.get((x[0]["model"], x[0]["task"]), 0), rng.random()))
            used[(t["model"], t["task"])] = used.get((t["model"], t["task"]), 0) + 1
            chosen.add(t["id"])
            items.append(dict(model=t["model"], task=t["task"], cond=t["cond"], trace=t["id"], problem=t["problem"],
                              reasoning=t["reasoning"], output=t["output"] if t["task"] == "blocksworld" else t["raw_stdout"][:4000],
                              gemma={"extent": r["extent"], "match": r["match"], "prose_answer": r.get("prose_answer", "")}))
    rest = items[1:]
    rng.shuffle(rest)
    items = [keep] + rest
    for n, it in enumerate(items):
        it["id"] = f"e{n:02d}"
    out = REPO / "validation/reliability/a2_verify.json"
    json.dump(items, open(out, "w"), indent=1)
    print(len(items), "items ->", out, [(it["task"], it["model"], it["gemma"]["extent"]) for it in items])


if __name__ == "__main__":
    main()
