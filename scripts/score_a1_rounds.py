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
               "a1r3-15": "V",    # 2026-10-29: ruling out slots before 11:30 is Values
               "v004": "N", "v009": "N", "v013": "N", "v017": "N",
               "v006": "VP", "a1r3-19": "N",
               "a1r3-08": "VP"}  # 2026-10-29: a paragraph can be both (it rules out values on the way to a bound)
# Properties check (pcheck tab): Harry's judgments, given in chat on 2026-10-29. 07-09 rule out
# values on the way to the property, so they are both under the VP type adopted the same day.
PCHECK = {"pcheck-00": "VP", **{f"pcheck-{i:02d}": "P" for i in range(1, 7)}, **{f"pcheck-{i:02d}": "VP" for i in (7, 8, 9)}}  # 2026-10-29: testing first actions is Values; "Reachable? Yes." has no argument  # 2026-10-29: encoding checks, a general dominance argument, a solvability hedge
V2_EXAMPLES = {"v010", "v011"}
V9_EXAMPLES = V2_EXAMPLES | {"v016", "a1r2-06", "a1r2-11", "a1r2-12", "a1r2-13", "a1r2-18", "a1r2-19",
                             "a1r3-03", "a1r3-04", "a1r3-08", "a1r3-14", "a1r3-15", "a1r3-17", "a1r3-18"}
IN_PROMPT = {"gemma_v3": V2_EXAMPLES, "gemma_v5": V2_EXAMPLES | {"v016"},
             "gemma_v7": V2_EXAMPLES | {"v016", "a1r2-06", "a1r2-11", "a1r2-18", "a1r2-19"},
             "gemma_v9": V9_EXAMPLES, "gemma_v9t": V9_EXAMPLES, "gemma_v10t": V9_EXAMPLES, "gemma_v11t": V9_EXAMPLES | {"pcheck-00", "pcheck-08"}}


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
    for it in sheets.get("pcheck", []):
        out.append((it["id"], it["segment"], it["para"], PCHECK[it["id"]]))
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
            for rnd, pre in [("r1", "v"), ("r2", "a1r2"), ("r3", "a1r3"), ("pcheck", "pcheck")]:
                part = [x for x in sub if x[0].startswith(pre)]
                print(f"  {name:<14}{rnd}: {sum(g == p for _, g, p in part)}/{len(part)}", end="")
            print(f"   total {sum(g == p for _, g, p in sub)}/{len(sub)}")
        for c, name in (("V", "values"), ("P", "properties")):
            tp = sum(1 for _, g, p in rows if c in g and c in p)
            print(f"  {name}: precision {tp}/{sum(1 for _, _, p in rows if c in p)}, recall {tp}/{sum(1 for _, g, _ in rows if c in g)}")
        dis = [(k, g, p) for k, g, p in rows if g != p]
        print("  disagreements (you, judge):", ", ".join(f"{k}{'*' if k in ex else ''} {g}/{p}" for k, g, p in dis), "  (* = in prompt)")


if __name__ == "__main__":
    main()
