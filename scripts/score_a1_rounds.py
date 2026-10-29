#!/usr/bin/env python3
"""
A1 type agreement (V / P / N; the rejects flag is no longer part of the ontology) of A-judge
versions with Harry's labels from all three rounds:
- round 1: validation/reliability/human/verify/ (a1_verify.json items v000-v019);
- rounds 2, 3: validation/reliability/human/checks/ (judge_checks.json tabs a1r2, a1r3).

Reference corrections agreed with Harry are applied (CORRECTIONS). Items whose content a
version's prompt paraphrases as an example are reported separately (IN_PROMPT), since
agreement on them is not a fair test.

Usage:
    python scripts/score_a1_rounds.py gemma_v5 gemma_v7 gemma_v9
"""
import glob
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"

CORRECTIONS = {"v016": "N",      # 2026-10-29: assuming a solution exists is not SLB
               "a1r3-15": "V"}   # 2026-10-29: ruling out slots before 11:30 is Values
V2_EXAMPLES = {"v010", "v011"}
V9_EXAMPLES = V2_EXAMPLES | {"v016", "a1r2-06", "a1r2-11", "a1r2-12", "a1r2-13", "a1r2-18", "a1r2-19",
                             "a1r3-03", "a1r3-04", "a1r3-08", "a1r3-14", "a1r3-15", "a1r3-17", "a1r3-18"}
IN_PROMPT = {"gemma_v3": V2_EXAMPLES, "gemma_v5": V2_EXAMPLES | {"v016"},
             "gemma_v7": V2_EXAMPLES | {"v016", "a1r2-06", "a1r2-11", "a1r2-18", "a1r2-19"},
             "gemma_v9": V9_EXAMPLES}


def references():
    """[(item id, segment id, paragraph index, label V/P/N)]"""
    out = []
    items = {it["id"]: it for it in json.load(open(REL / "a1_verify.json"))}
    for f in glob.glob(str(REL / "human/verify/*.json")):
        k = Path(f).stem
        v = json.load(open(f))
        v = v.get("data", v)
        if k in items and v.get("human"):
            out.append((k, items[k]["segment"], items[k]["para"], v["human"]))
    sheets = json.load(open(REL / "judge_checks.json"))
    for tab in ("a1r2", "a1r3"):
        for it in sheets[tab]:
            f = REL / "human/checks" / f"{it['id']}.json"
            if f.exists():
                v = json.load(open(f))
                v = v.get("data", v)
                if v.get("human") not in (None, "unsure"):
                    out.append((it["id"], it["segment"], it["para"], v["human"][0]))  # V_rej -> V
    return [(k, s, i, CORRECTIONS.get(k, lab)) for k, s, i, lab in sorted(out)]


def judge(tag):
    out = {}
    for f in glob.glob(str(REL / f"checks/judge_a_{tag}.jsonl")) + glob.glob(str(REPO / f"output/ontology/judge_a_{tag}*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            out[r["id"]] = r
    return out


def main():
    refs = references()
    for tag in sys.argv[1:]:
        j = judge(tag)
        ex = IN_PROMPT.get(tag, set())
        rows = []
        for k, seg, i, gold in refs:
            r = j.get(seg)
            if r is None:
                continue
            rows.append((k, gold, r["paras"].get(str(i), {"t": "N"})["t"]))
        print(f"== {tag}")
        for name, sub in [("all", rows), ("not in prompt", [x for x in rows if x[0] not in ex])]:
            for rnd, pre in [("r1", "v"), ("r2", "a1r2"), ("r3", "a1r3")]:
                part = [x for x in sub if x[0].startswith(pre)]
                print(f"  {name:<14}{rnd}: {sum(g == p for _, g, p in part)}/{len(part)}", end="")
            print(f"   total {sum(g == p for _, g, p in sub)}/{len(sub)}")
        pred = Counter(p for _, _, p in rows)
        print("  precision by judge label:", {lab: f"{sum(1 for _, g, p in rows if p == lab and g == lab)}/{n}" for lab, n in sorted(pred.items())})
        dis = [(k, g, p) for k, g, p in rows if g != p]
        print("  disagreements (you, judge):", ", ".join(f"{k}{'*' if k in ex else ''} {g}/{p}" for k, g, p in dis), "  (* = in prompt)")


if __name__ == "__main__":
    main()
