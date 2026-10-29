#!/usr/bin/env python3
"""
Judge inputs for the spot-check sheets, so a new judge version can be run on just these
items (src/run_ontology_judges.py --items validation/reliability/checks/<kind>.json):

- checks/a.json: the segments containing the A1 and A3 sheets' paragraphs (the A judge
  labels whole segments; agreement is read off the sheet's paragraph).
- checks/c.json: the A2, C1 and C2 sheets' traces (C judge; C1/C2 are then scripts).
- checks/b.json: the B and spec sheets' traces (B judge).

Usage (env venv):
    python scripts/build_check_sets.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
from ontology_items import build_items


def main():
    segments, traces = build_items()
    seg_by_id = {s["id"]: s for s in segments}
    tr_by_id = {t["id"]: t for t in traces}
    checks = json.load(open(REL / "judge_checks.json"))  # a3, b, spec, c1, c2
    a = {it["segment"] for it in json.load(open(REL / "a1_verify.json"))} | {it["segment"] for it in checks["a3"]}
    out = {"a": [seg_by_id[s] for s in sorted(a)]}
    for kind, ids in [("c", [it["trace"] for it in json.load(open(REL / "a2_verify.json"))] + [it["trace"] for k in ("c1", "c2") for it in checks[k]]),
                      ("b", [it["trace"] for it in json.load(open(REL / "b_verify.json"))] + [it["trace"] for it in checks["spec"]])]:
        out[kind] = [tr_by_id[i] for i in dict.fromkeys(ids)]
    for kind, items in out.items():
        json.dump(items, open(REL / "checks" / f"{kind}.json", "w"))
        print(kind, len(items), "items")


if __name__ == "__main__":
    main()
