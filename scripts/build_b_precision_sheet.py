#!/usr/bin/env python3
"""
B precision check (tab "bprec" in validation/reliability/judge_checks.json): programs the final
B judge (gemma_b3t) labels hardcoded or partly fixed, 10 each, with its evidence shown, so Harry
can confirm each label from the cited line and the program (as for the B examples). Drawn from
the 343-trace candidate pool, excluding the round-2 sheet; spread over model x task.

Usage (vllm env):
    python scripts/build_b_precision_sheet.py
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

TAG = "gemma_b3t"


def main():
    rng = random.Random(1031)
    sheets = json.load(open(REL / "judge_checks.json"))
    skip = {it["trace"] for it in sheets.get("br2", [])}
    traces, jb = {}, {}
    for k in (0, 1):
        d = REL / f"checks/b_pool{k}"
        traces.update({t["id"]: t for t in json.load(open(d / "traces.json"))})
        for line in open(d / f"judge_b_{TAG}.jsonl"):
            r = json.loads(line)
            jb[r["id"]] = r
    pool = [((traces[i]["model"], traces[i]["task"]), traces[i], r["b"]) for i, r in jb.items() if i not in skip and r.get("b")]
    picks = stratified(pool, [("hardcoded", 10), ("partly_fixed", 10)], key=lambda p: p[1]["id"], rng=rng)
    names = dict(B_OPTS)
    items = []
    for n, (_, t, lab) in enumerate(picks):
        items.append({**meta(t), "id": f"bprec-{n:02d}", "gemma_text": f"Gemma: {names[lab]}. Evidence: {jb[t['id']]['evidence']}",
                      "question": {"key": "b", "type": "single", "prompt": "Do you agree with this label?",
                                   "options": B_OPTS + [["unsure", "Can't tell"]], "gemma": lab},
                      "blocks": trace_blocks(t)})
    sheets["bprec"] = items
    json.dump(sheets, open(REL / "judge_checks.json", "w"))
    print("bprec", len(items), {l: sum(1 for *_, x in picks if x == l) for l in ("hardcoded", "partly_fixed")})


if __name__ == "__main__":
    main()
