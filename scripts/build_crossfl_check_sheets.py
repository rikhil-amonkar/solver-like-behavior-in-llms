#!/usr/bin/env python3
"""
Cross-FL spot checks of the final judges (A gemma_v11t, B gemma_b5t): every earlier reliability
sheet used native-FL traces, while H2 compares FLs, so these tabs check that the judges carry over
to Calendar and Meeting in Z3, and ZebraLogic and BlocksWorld in Python. Qwen and GPT-OSS only
(DeepSeek's cross-FL runs are excluded, docs/CROSS_FL_DESIGN.md).

Tabs in validation/reliability/judge_checks.json:
- a1x: 40 paragraphs, blind, from baseline traces; per dataset 5 the judge calls Values and 5 not,
       one per trace, spread over models.
- bx:  20 programs (all conditions), judge label and evidence shown: 10 the judge says inherit
       from the prose (hardcoded 3, partly fixed 4, steered 3; precision) and 10 it calls
       independent although the prose reached a complete answer, shown next to the program
       (a recall check: does the program use that answer after all?). No trace is on both tabs.

Steps:
    python scripts/build_crossfl_check_sheets.py sheets   # vllm env (tiktoken)
    python scripts/build_crossfl_check_sheets.py score    # after the marks are in human/checks/
"""
import argparse
import glob
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
ROOT = "output_crossfl"
MODELS = ("qwen", "gpt")
FL = {"calendar": "Z3", "meeting": "Z3", "zebralogic": "Python", "blocksworld": "Python"}
A1_OPTS = [["V", "Values"], ["N", "Not SLB"], ["unsure", "Can't tell"]]


def latest(kind, tag):
    """Latest judge record per id over all shards."""
    out = {}
    for f in sorted((REPO / ROOT / "ontology").glob(f"judge_{kind}_{tag}*.jsonl")):
        for line in f.open():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def sheets():
    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(REPO / "scripts"))
    from ontology_items import build_items
    from build_check_sheets import stratified, trace_blocks, meta, B_OPTS

    segments, traces = build_items(ROOT)
    tr = {t["id"]: t for t in traces if t["model"] in MODELS}
    ja, jb, jc = latest("a", "gemma_v11t"), latest("b", "gemma_b5t"), latest("c", "gemma_v11c")
    out = json.load(open(REL / "judge_checks.json"))

    # ---- B first, so A1 can avoid its traces ----
    rng = random.Random(1101)
    inherit = [((t["model"], t["task"]), t, jb[i]["b"]) for i, t in tr.items()
               if i in jb and jb[i]["h"] == t["h"] and jb[i].get("b") in ("hardcoded", "partly_fixed", "steered")]
    picks = stratified(inherit, [("hardcoded", 3), ("partly_fixed", 4), ("steered", 3)], key=lambda p: p[1]["id"], rng=rng)
    indep = [((t["model"], t["task"]), t, "independent") for i, t in tr.items()
             if i in jb and jb[i]["h"] == t["h"] and jb[i].get("b") == "independent"
             and jc.get(i, {}).get("extent") == "complete" and jc[i].get("prose_answer")]
    used = {p[1]["id"] for p in picks}
    picks += stratified([p for p in indep if p[1]["id"] not in used], [("independent", 10)], key=lambda p: p[1]["id"], rng=rng)
    rng.shuffle(picks)
    names = dict(B_OPTS)
    bx = []
    for n, (_, t, lab) in enumerate(picks):
        blocks = trace_blocks(t)
        if t["task"] == "blocksworld":  # in Python the program prints its own plan; no planner runs
            blocks[-1]["label"] = "Program output (its plan)"
        if lab == "independent":
            blocks.insert(2, {"label": "Answer the prose reached (extracted by the A2 judge)", "text": jc[t["id"]]["prose_answer"], "mode": "open"})
        bx.append({**meta(t), "fl": FL[t["task"]], "id": f"bx-{n:02d}",
                   "gemma_text": f"{names[lab]}. Evidence: {jb[t['id']]['evidence']}",
                   "question": {"key": "b", "type": "single", "prompt": "Do you agree with this label?",
                                "options": B_OPTS + [["unsure", "Can't tell"]], "gemma": lab},
                   "blocks": blocks})
    on_b = {it["trace"] for it in bx}

    # ---- A1: baseline paragraphs, 5 Values + 5 not per dataset ----
    rng = random.Random(1102)
    pool = {task: [] for task in FL}
    for s in segments:
        r = ja.get(s["id"])
        if s["model"] not in MODELS or s["cond"] != "baseline" or s["trace"] in on_b or not r or r["h"] != s["h"]:
            continue
        for i, text in enumerate(s["paragraphs"]):
            if len(text) < 60:
                continue
            t = r["paras"].get(str(i), {"t": "N"})["t"]
            pool[s["task"]].append(((s["model"], s["task"]), (s, i), "V" if "V" in t else "N"))
    a1 = []
    for task in FL:
        for _, (s, i), lab in stratified(pool[task], [("V", 5), ("N", 5)], key=lambda p: p[1][0]["trace"], rng=rng):
            a1.append({**{k: s[k] for k in ("model", "task", "cond")}, "fl": FL[task], "trace": s["trace"], "segment": s["id"],
                       "para": i, "blind": True, "gemma_text": "",
                       "question": {"key": "a1", "type": "single", "prompt": "What does the highlighted paragraph do?",
                                    "options": A1_OPTS, "gemma": lab},
                       "blocks": [{"label": "Problem", "text": s["problem"], "mode": "collapsed"},
                                  {"label": "", "text": s["paragraphs"][i - 1] if i else "", "mode": "context"},
                                  {"label": "Paragraph", "text": s["paragraphs"][i], "mode": "target"},
                                  {"label": "", "text": s["paragraphs"][i + 1] if i + 1 < len(s["paragraphs"]) else "", "mode": "context"}]})
    rng.shuffle(a1)
    for k, it in enumerate(a1):
        it["id"] = f"a1x-{k:02d}"

    out["a1x"], out["bx"] = a1, bx
    json.dump(out, open(REL / "judge_checks.json", "w"))
    print("a1x", len(a1), Counter((it["task"], it["question"]["gemma"]) for it in a1))
    print("bx", len(bx), Counter((it["task"], it["question"]["gemma"]) for it in bx))


def wilson(k, n, z=1.96):
    if not n:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - w, c + w


def score():
    items = json.load(open(REL / "judge_checks.json"))
    marks = {Path(f).stem: json.load(open(f)) for f in glob.glob(str(REL / "human/checks/*x-*.json"))}
    for tab in ("a1x", "bx"):
        rows = [(it, marks[it["id"]]["human"]) for it in items[tab] if it["id"] in marks and "human" in marks[it["id"]]]
        sure = [(it, h) for it, h in rows if h != "unsure"]
        agree = [(it, h) for it, h in sure if h == it["question"]["gemma"]]
        lo, hi = wilson(len(agree), len(sure))
        print(f"{tab}: marked {len(rows)}/{len(items[tab])}, can't tell {len(rows) - len(sure)}, "
              f"agree {len(agree)}/{len(sure)} [{lo:.2f}, {hi:.2f}]")
        for key in sorted({it["task"] for it, _ in sure}) + sorted({it["question"]["gemma"] for it, _ in sure}):
            sub = [(it, h) for it, h in sure if key in (it["task"], it["question"]["gemma"])]
            print(f"  {key:<14} {sum(h == it['question']['gemma'] for it, h in sub)}/{len(sub)}")
        if tab == "a1x":
            tp = sum(1 for it, h in sure if h == "V" and it["question"]["gemma"] == "V")
            print(f"  Values precision {tp}/{sum(it['question']['gemma'] == 'V' for it, _ in sure)}, "
                  f"recall {tp}/{sum(h == 'V' for _, h in sure)}")
        dis = [f"{it['id']} {h}/{it['question']['gemma']}" for it, h in sure if h != it["question"]["gemma"]]
        print("  disagreements (Harry/judge):", ", ".join(dis) or "none")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["sheets", "score"])
    sheets() if ap.parse_args().step == "sheets" else score()


if __name__ == "__main__":
    main()
