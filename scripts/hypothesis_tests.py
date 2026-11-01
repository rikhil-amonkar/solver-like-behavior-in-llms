#!/usr/bin/env python3
"""
Tests of the paper's hypotheses on the per-trace ontology rows of the native and cross-FL runs
(output/paper/ontology_traces_<tag>.json and ..._output_crossfl.json, from paper_ontology_stats.py).

H1.1 SLB is common and takes a practically significant share of the reasoning.
H1.2 The kinds of SLB (A2 extent, B inheritance) and how often each is harmful.
H1.3 SLB and program accuracy (controlling for the problem with example fixed effects).
H2   FL vs dataset as the source of SLB differences.
H3   Cautionary prompts vs baseline.

Confidence intervals: 95% bootstrap over problems (example ids), 2000 resamples.
DeepSeek cross-FL runs are always excluded (API drift).
Usage: python scripts/hypothesis_tests.py [--no-deepseek] > docs/results/<date>_HYPOTHESES.md
"""
import argparse
import collections
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
TASKS = ["calendar", "meeting", "zebralogic", "blocksworld"]
MODELS = ["deepseek", "qwen", "gpt"]
INHERIT = ("hardcoded", "partly_fixed", "steered")
rng = np.random.default_rng(0)


def load(tag, models):
    rows = []
    for suffix, root in (("", "native"), ("_output_crossfl", "crossfl")):
        for r in json.load(open(REPO / f"output/paper/ontology_traces_{tag}{suffix}.json")):
            # DeepSeek's cross-FL runs are excluded: the API model changed between the native runs
            # (2026-08) and the cross-FL runs (2026-10); see docs/CROSS_FL_DESIGN.md.
            if r["model"] in models and not (root == "crossfl" and r["model"] == "deepseek"):
                r["root"] = root
                rows.append(r)
    return rows


def boot(groups, stat, n=2000):
    """Point estimate and 95% CI of stat(list of rows), resampling the groups (lists of rows)."""
    groups = list(groups)
    est = stat([r for g in groups for r in g])
    vals = []
    for _ in range(n):
        idx = rng.integers(len(groups), size=len(groups))
        vals.append(stat([r for i in idx for r in groups[i]]))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return est, lo, hi


def by_example(rows):
    g = collections.defaultdict(list)
    for r in rows:
        g[(r["task"], r["example_id"])].append(r)
    return g.values()


def fmt(e, lo, hi, p=2):
    return f"{e:+.{p}f} [{lo:+.{p}f}, {hi:+.{p}f}]"


def mean(rows, f):
    return float(np.mean([f(r) for r in rows])) if rows else float("nan")


def ols(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta, float(((y - X @ beta) ** 2).sum())


def dummies(rows, key):
    levels = sorted({key(r) for r in rows})
    ix = {l: i for i, l in enumerate(levels)}
    D = np.zeros((len(rows), len(levels)))
    for i, r in enumerate(rows):
        D[i, ix[key(r)]] = 1
    return D[:, 1:]  # drop the first level


def h1_1(rows):
    print("## H1.1 Prevalence and share of reasoning (baseline condition)\n")
    print("| model | runs | traces | with Values | mean ratio | SLB tokens/trace | reasoning tokens/trace | token share | Values but program independent | SLB tokens/trace there |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        for root in ("native", "crossfl"):
            g = [r for r in rows if r["model"] == m and r["root"] == root and r["cond"] == "baseline"]
            if not g:
                continue
            v = [r for r in g if r["values"]]
            wasted = [r for r in v if r["B"] == "independent"]
            share = sum(r["slb_tokens"] for r in g) / sum(r["reasoning_tokens"] for r in g)
            print(f"| {m} | {root} | {len(g)} | {len(v) / len(g):.0%} | {mean(g, lambda r: r['ratio'] or 0):.2f} | "
                  f"{mean(g, lambda r: r['slb_tokens']):.0f} | {mean(g, lambda r: r['reasoning_tokens']):.0f} | {share:.0%} | "
                  f"{len(wasted) / len(g):.0%} | {mean(wasted, lambda r: r['slb_tokens']):.0f} |")
    g = [r for r in rows if r["cond"] == "baseline"]
    for thr in (0.1, 0.2):
        print(f"\nTraces with ratio >= {thr}: {mean(g, lambda r: (r['ratio'] or 0) >= thr):.0%} of baseline traces.", end="")
    print(f" Traces with >= 1,000 SLB tokens: {mean(g, lambda r: r['slb_tokens'] >= 1000):.0%}.\n")
    print("Per dataset and FL (baseline, all models):\n")
    print("| task | FL | with Values | mean ratio | SLB tokens/trace | token share |")
    print("|---|---|---|---|---|---|")
    for t in TASKS:
        for fl in sorted({r["fl"] for r in rows if r["task"] == t}):
            g = [r for r in rows if r["task"] == t and r["fl"] == fl and r["cond"] == "baseline"]
            share = sum(r["slb_tokens"] for r in g) / max(1, sum(r["reasoning_tokens"] for r in g))
            print(f"| {t} | {fl} | {mean(g, lambda r: r['values']):.0%} | {mean(g, lambda r: r['ratio'] or 0):.2f} | "
                  f"{mean(g, lambda r: r['slb_tokens']):.0f} | {share:.0%} |")
    print()


def h1_2(rows):
    print("## H1.2 Kinds of SLB and their harm (all conditions)\n")
    print("| model | runs | Values traces | complete | partial | prose answer wrong (C2) | prose ≠ program (C1) | hardcoded | partly fixed | steered |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        for root in ("native", "crossfl"):
            g = [r for r in rows if r["model"] == m and r["root"] == root]
            if not g:
                continue
            v = [r for r in g if r["values"]]
            c2 = [r for r in v if r["C2"] is not None]
            c1 = [r for r in v if r["C1"] is not None]
            print(f"| {m} | {root} | {len(v)} | {mean(v, lambda r: r['A2'] == 'complete'):.0%} | {mean(v, lambda r: r['A2'] == 'partial'):.0%} | "
                  f"{mean(c2, lambda r: not r['C2']):.0%} (n={len(c2)}) | {mean(c1, lambda r: not r['C1']):.0%} (n={len(c1)}) | "
                  + " | ".join(f"{sum(r['B'] == b for r in g)}" for b in INHERIT) + " |")
    print("\nAccuracy by B label, compared with independent programs for the same problem and model "
          "(pairs of traces of one problem, any condition and FL, one label inherited and one independent):\n")
    print("| B label | traces | accuracy | accuracy of independent programs, same problems | difference |")
    print("|---|---|---|---|---|")
    for b in INHERIT:
        diffs = []
        for (task, eid, m), g in group(rows, lambda r: (r["task"], r["example_id"], r["model"])).items():
            x, y = [r for r in g if r["B"] == b], [r for r in g if r["B"] == "independent"]
            if x and y:
                diffs.append((mean(x, lambda r: r["correct"]), mean(y, lambda r: r["correct"])))
        n = sum(r["B"] == b for r in rows)
        if diffs:
            d = np.array(diffs)
            bs = [d[rng.integers(len(d), size=len(d))] for _ in range(2000)]
            lo, hi = np.percentile([(s[:, 0] - s[:, 1]).mean() for s in bs], [2.5, 97.5])
            print(f"| {b} | {n} | {mean([r for r in rows if r['B'] == b], lambda r: r['correct']):.2f} | "
                  f"{d[:, 1].mean():.2f} ({len(d)} problems) | {fmt((d[:, 0] - d[:, 1]).mean(), lo, hi)} |")
    print("\nWrong prose answers (C2 false) and the program:\n")
    print("| B label | prose wrong | of these, program correct | prose right | of these, program correct |")
    print("|---|---|---|---|---|")
    for b in INHERIT + ("independent",):
        g = [r for r in rows if r["B"] == b and r["C2"] is not None]
        w, ok = [r for r in g if not r["C2"]], [r for r in g if r["C2"]]
        print(f"| {b} | {len(w)} | {mean(w, lambda r: r['correct']):.0%} | {len(ok)} | {mean(ok, lambda r: r['correct']):.0%} |")
    print()


def group(rows, key):
    g = collections.defaultdict(list)
    for r in rows:
        g[key(r)].append(r)
    return g


def h1_3(rows):
    print("## H1.3 SLB and accuracy\n")
    print("Linear probability model: correct ~ x + run fixed effects (model × task × FL × condition) "
          "+ problem fixed effects, so x is compared within a run and within a problem. "
          "CI: bootstrap over problems.\n")
    print("| x | rows | coefficient on accuracy |")
    print("|---|---|---|")
    for name, f, sub in (("solver-like ratio (0-1)", lambda r: r["ratio"] or 0, lambda r: True),
                         ("any Values paragraph", lambda r: float(r["values"]), lambda r: True),
                         ("SLB tokens (per 10k)", lambda r: r["slb_tokens"] / 1e4, lambda r: True),
                         ("program inherits (B hardcoded/partly fixed/steered)", lambda r: float(r["B"] in INHERIT),
                          lambda r: r["B"] != "na"),
                         ("prose answer correct (C2)", lambda r: float(bool(r["C2"])), lambda r: r["C2"] is not None)):
        g = [r for r in rows if sub(r)]
        def stat(s):
            y = np.array([float(r["correct"]) for r in s])
            X = np.column_stack([np.array([f(r) for r in s]), np.ones(len(s)),
                                 dummies(s, lambda r: (r["model"], r["task"], r["fl"], r["cond"])),
                                 dummies(s, lambda r: (r["task"], r["example_id"]))])
            return ols(y, X)[0][0]
        e, lo, hi = boot(by_example(g), stat, n=200)
        print(f"| {name} | {len(g)} | {fmt(e, lo, hi, 3)} |")
    print("\nThe same, per model and run set (solver-like ratio):\n")
    print("| model | runs | coefficient |")
    print("|---|---|---|")
    for m in MODELS:
        for root in ("native", "crossfl"):
            g = [r for r in rows if r["model"] == m and r["root"] == root]
            if not g:
                continue
            def stat(s):
                y = np.array([float(r["correct"]) for r in s])
                X = np.column_stack([np.array([r["ratio"] or 0 for r in s]), np.ones(len(s)),
                                     dummies(s, lambda r: (r["task"], r["cond"])),
                                     dummies(s, lambda r: (r["task"], r["example_id"]))])
                return ols(y, X)[0][0]
            e, lo, hi = boot(by_example(g), stat, n=200)
            print(f"| {m} | {root} | {fmt(e, lo, hi, 3)} |")
    print()


def h2(rows):
    print("## H2 FL vs dataset\n")
    both = {r["model"] for r in rows if r["root"] == "crossfl"}
    rows = [r for r in rows if r["model"] in both]
    print(f"Models with runs in both FLs: {', '.join(sorted(both))}.\n")
    print("Within-dataset FL contrast (cross-FL minus native, same problems, paired; all conditions):\n")
    print("| task | native → new FL | model | Δ ratio | Δ with Values | Δ program inherits | Δ accuracy |")
    print("|---|---|---|---|---|---|---|")
    for t in TASKS:
        for m in MODELS + ["all"]:
            g = [r for r in rows if r["task"] == t and (m == "all" or r["model"] == m)]
            if len({r["root"] for r in g}) < 2:
                continue
            fls = {r["root"]: r["fl"] for r in g}
            pairs = collections.defaultdict(dict)
            for r in g:
                pairs[(r["model"], r["cond"], r["example_id"])][r["root"]] = r
            pairs = [p for p in pairs.values() if len(p) == 2]
            groups = group(pairs, lambda p: p["native"]["example_id"]).values()
            cells = []
            for f in (lambda r: r["ratio"] or 0, lambda r: float(r["values"]),
                      lambda r: float(r["B"] in INHERIT), lambda r: float(r["correct"])):
                e, lo, hi = boot(groups, lambda s: np.mean([f(p["crossfl"]) - f(p["native"]) for p in s]), n=1000)
                cells.append(fmt(e, lo, hi))
            print(f"| {t} | {fls['native']} → {fls['crossfl']} | {m} | " + " | ".join(cells) + " |")
    print("\nVariance in the solver-like ratio explained by each factor (OLS on all traces; "
          "the drop in R² when the factor is removed from model + condition + task + FL):\n")
    y = np.array([r["ratio"] or 0 for r in rows])
    keys = {"model": lambda r: r["model"], "condition": lambda r: r["cond"], "task": lambda r: r["task"],
            "FL": lambda r: r["fl"]}
    tss = float(((y - y.mean()) ** 2).sum())
    full = np.column_stack([np.ones(len(rows))] + [dummies(rows, k) for k in keys.values()])
    r2 = 1 - ols(y, full)[1] / tss
    print(f"Full model R² = {r2:.3f}.\n")
    print("| factor | ΔR² when removed |")
    print("|---|---|")
    for name in keys:
        X = np.column_stack([np.ones(len(rows))] + [dummies(rows, k) for n, k in keys.items() if n != name])
        print(f"| {name} | {r2 - (1 - ols(y, X)[1] / tss):.3f} |")
    beta = ols(y, full)[0]
    print("\nFL coefficients in the full model (vs PDDL, the first level): "
          + ", ".join(f"{l} {b:+.3f}" for l, b in zip(sorted({r['fl'] for r in rows})[1:], beta[-2:])))
    print("\nSame FL, different datasets (baseline + cautions, all models): mean ratio\n")
    print("| FL | " + " | ".join(TASKS) + " |")
    print("|---|" + "---|" * len(TASKS))
    for fl in ("python", "z3", "pddl"):
        print(f"| {fl} | " + " | ".join(
            (f"{mean(g, lambda r: r['ratio'] or 0):.2f}" if (g := [r for r in rows if r['fl'] == fl and r['task'] == t]) else "-")
            for t in TASKS) + " |")
    print()


def h3(rows):
    print("## H3 Cautionary prompts (vs baseline, same problems, paired)\n")
    print("| model | runs | caution | Δ ratio | Δ with Values | Δ SLB tokens | Δ program inherits | Δ accuracy | ratio, baseline |")
    print("|---|---|---|---|---|---|---|---|---|")
    for m in MODELS + ["all"]:
        for root in ("native", "crossfl", "both"):
            g = [r for r in rows if (m == "all" or r["model"] == m) and (root == "both" or r["root"] == root)]
            if not g or (m != "all" and root == "both") or not any(r["cond"] == "baseline" for r in g):
                continue
            for c in ("caution_a", "caution_b"):
                pairs = collections.defaultdict(dict)
                for r in g:
                    if r["cond"] in ("baseline", c):
                        pairs[(r["model"], r["root"], r["task"], r["example_id"])][r["cond"]] = r
                pairs = [p for p in pairs.values() if len(p) == 2]
                groups = group(pairs, lambda p: (p["baseline"]["task"], p["baseline"]["example_id"])).values()
                cells = []
                for f, p in ((lambda r: r["ratio"] or 0, 2), (lambda r: float(r["values"]), 2),
                             (lambda r: r["slb_tokens"], 0), (lambda r: float(r["B"] in INHERIT), 2),
                             (lambda r: float(r["correct"]), 2)):
                    e, lo, hi = boot(groups, lambda s: np.mean([f(q[c]) - f(q["baseline"]) for q in s]), n=1000)
                    cells.append(fmt(e, lo, hi, p))
                print(f"| {m} | {root} | {c[-1].upper()} | " + " | ".join(cells)
                      + f" | {mean(pairs, lambda q: q['baseline']['ratio'] or 0):.2f} |")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="gemma_v11_b5t")
    ap.add_argument("--no-deepseek", action="store_true")
    args = ap.parse_args()
    models = [m for m in MODELS if not (args.no_deepseek and m == "deepseek")]
    rows = load(args.tag, models)
    print(f"# Hypothesis tests ({len(rows)} traces; models: {', '.join(models)})\n")
    for f in (h1_1, h1_2, h1_3, h2, h3):
        f(rows)


if __name__ == "__main__":
    main()
