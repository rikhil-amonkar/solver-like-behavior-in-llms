#!/usr/bin/env python3
"""
Sample Gemma A-judge paragraph labels for a human to verify (agree / correct them).

5 paragraphs per task x Gemma type (V, P, N) = 60, stratified across models, each with
the paragraph before and after for context. BlocksWorld gets 10 per type because its
labels look suspicious (high ratio and 'interpret' rate). The 75 are shuffled; the human
check uses the first 20 (balanced across models, tasks and types), so the file keeps 20.

Usage:
    python scripts/build_a1_verification.py --tag gemma_v1
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

SEED = 7
PER = {"calendar": 5, "meeting": 5, "zebralogic": 5, "blocksworld": 10}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="gemma_v1")
    args = ap.parse_args()
    ja = {}
    for f in glob.glob(str(REPO / f"output/ontology/judge_a_{args.tag}*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            ja[(r["id"], r.get("h"))] = r
    segments, _ = build_items()
    pools = {}
    for s in segments:
        r = ja.get((s["id"], s["h"]))
        if not r:
            continue
        for i, text in enumerate(s["paragraphs"]):
            lab = r["paras"].get(str(i), {"t": "N", "s": False, "p": []})
            if len(text) < 40:  # skip connective one-liners
                continue
            pools.setdefault((s["task"], lab["t"]), []).append((s, i, lab))
    rng = random.Random(SEED)
    items = []
    for task, k in PER.items():
        for t in "VPN":
            pool = pools.get((task, t), [])
            by_model = {}
            for x in pool:
                by_model.setdefault(x[0]["model"], []).append(x)
            picks = []
            models = sorted(by_model)
            while len(picks) < k and any(by_model.values()):
                m = models[len(picks) % len(models)]
                if by_model[m]:
                    picks.append(by_model[m].pop(rng.randrange(len(by_model[m]))))
                else:
                    models.remove(m)
            for s, i, lab in picks:
                items.append(dict(model=s["model"], task=task, cond=s["cond"], segment=s["id"], para=i,
                                  problem=s["problem"], before=s["paragraphs"][i - 1] if i else "",
                                  text=s["paragraphs"][i], after=s["paragraphs"][i + 1] if i + 1 < len(s["paragraphs"]) else "",
                                  gemma=lab))
    rng.shuffle(items)
    items = items[:20]
    for n, it in enumerate(items):
        it["id"] = f"v{n:03d}"
    out = REPO / "validation/reliability/a1_verify.json"
    json.dump(items, open(out, "w"), indent=1)
    print(len(items), "items ->", out)


if __name__ == "__main__":
    main()
