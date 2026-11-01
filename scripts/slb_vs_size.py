#!/usr/bin/env python3
"""
SLB vs problem size (paper H1 "It grows with the problem"): solver-like tokens, ratio and accuracy in the
smallest vs largest third of problems per dataset, and Spearman rho per run. Size: busy intervals (Calendar),
friends (Meeting), houses x attributes (ZebraLogic), blocks (BlocksWorld; -1 if unparsed). Baseline prompt.

Usage: /local-ssd/hz466/env/bin/python scripts/slb_vs_size.py
"""
import sys, json, re, numpy as np
sys.path.insert(0, 'scripts')
import paper_figures_hypotheses as P
from scipy.stats import spearmanr
rows = [r for r in P.load("gemma_v11_b5t", [m for m, _ in P.MODELS]) if r["cond"] == "baseline"]
def size(t, eid, text):
    if t == "zebralogic":
        h, a = map(int, re.search(r"(\d+)x(\d+)", eid).groups()); return h * a
    if t == "blocksworld":
        m = re.search(r"(\d+) (?:uniquely labeled )?blocks", text)
        return int(m.group(1)) if m else -1
    if t == "meeting":
        return text.count("will be at")
    task = text[text.rfind("TASK:"):]
    return len(re.findall(r"\d{1,2}:\d{2} to \d{1,2}:\d{2}", task)) - 1
S = {}
for t in P.TASK_NAMES:
    for e in json.load(open(f"output/qwen/{t}/baseline_inference.json"))["examples"]:
        S[(t, e["example_id"])] = size(t, e["example_id"], e["problem_text"])
for r in rows: r["size"] = S[(r["task"], r["example_id"])]
for t in P.TASK_NAMES:
    g = [r for r in rows if r["task"] == t]
    s = np.array([r["size"] for r in g]); lo, hi = np.percentile(s, [33.3, 66.7])
    small = [r for r in g if r["size"] <= lo]; big = [r for r in g if r["size"] > hi]
    rhos = []
    for run in sorted({(r["model"], r["fl"]) for r in g}):
        h = [r for r in g if (r["model"], r["fl"]) == run]
        rhos.append((run, round(spearmanr([r["size"] for r in h], [r["slb_tokens"] for r in h]).correlation, 2),
                     round(spearmanr([r["size"] for r in h], [r["ratio"] or 0 for r in h]).correlation, 2)))
    print(f"{t:11} size {s.min()}-{s.max()} | SLB tok small {np.mean([r['slb_tokens'] for r in small]):6.0f} big {np.mean([r['slb_tokens'] for r in big]):6.0f}"
          f" | ratio {np.mean([r['ratio'] or 0 for r in small]):.2f}/{np.mean([r['ratio'] or 0 for r in big]):.2f}"
          f" | acc {np.mean([r['correct'] for r in small]):.2f}/{np.mean([r['correct'] for r in big]):.2f} | n {len(small)}/{len(big)}")
    print("   rho(tokens), rho(ratio) per run:", rhos)
