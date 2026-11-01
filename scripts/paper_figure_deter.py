#!/usr/bin/env python3
"""
Section 6 figure (figures/deter.pdf): how much each deterrence method changes solver-like behavior and
accuracy relative to the baseline prompt, on the same problems.

Each method is paired with the baseline generation of the same model, root (native / cross-FL), dataset
and problem, so each is measured on the cells it was run in:
  - Cautionary A / B: every model, dataset and FL (DeepSeek: one FL per dataset);
  - Batching (K = 5): Qwen and GPT-OSS, every dataset and FL but PDDL;
  - Placeholders: Qwen and GPT-OSS, Calendar and Meeting, Python and Z3.
Rows: output/paper/ontology_traces_<tag>[_output_crossfl].json (baseline, cautionary prompts) and
output/paper/deter_traces_<a-tag>.json (scripts/deter_traces.py). A batch member carries its group's
ratio and 1/K of its solver-like tokens; the bootstrap resamples problems, or batch groups.
Panels: change in solver-like tokens per problem (% of the baseline mean), in solver-like ratio, and in
program accuracy (points); pooled estimate with 95% CI, and one marker per model.
Also writes output/paper/deter_numbers.json with the numbers quoted in the text.

Usage (env venv, for matplotlib):
    /local-ssd/hz466/env/bin/python scripts/paper_figure_deter.py --paper /local-ssd/hz466/solver-like-paper
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from hypothesis_tests import load, rng  # noqa: E402
from paper_figures_hypotheses import MODELS, MODEL_COLORS, INK, MUTED, style  # noqa: E402

METHODS = [("caution_a", "Cautionary A"), ("caution_b", "Cautionary B"), ("batch_k5", "Batching ($K$=5)"),
           ("placeholder", "Placeholders")]
METRICS = [("slb", "Solver-like tokens per problem (%)"), ("ratio", "Solver-like ratio"),
           ("accuracy", "Program accuracy (points)")]


def pairs(base, rows, cond):
    """(baseline row, method row) for every problem the method covers."""
    b = {(r["model"], r["root"], r["task"], r["example_id"]): r for r in base}
    return [(b[k], r) for r in rows if r["cond"] == cond
            for k in [(r["model"], r["root"], r["task"], r["example_id"])] if k in b]


def stats(ps):
    n = lambda p: p[1]
    slb_b, slb_n = np.mean([p[0]["slb_tokens"] for p in ps]), np.mean([n(p)["slb_tokens"] for p in ps])
    return dict(slb=100 * (slb_n - slb_b) / slb_b,
                ratio=np.mean([(n(p)["ratio"] or 0) - (p[0]["ratio"] or 0) for p in ps]),
                accuracy=100 * np.mean([float(n(p)["correct"]) - float(p[0]["correct"]) for p in ps]),
                values=100 * np.mean([float(n(p)["values"]) - float(p[0]["values"]) for p in ps]),
                tokens=100 * (np.mean([n(p)["reasoning_tokens"] for p in ps]) /
                              np.mean([p[0]["reasoning_tokens"] for p in ps]) - 1),
                base_slb=slb_b, new_slb=slb_n,
                base_ratio=np.mean([p[0]["ratio"] or 0 for p in ps]), new_ratio=np.mean([n(p)["ratio"] or 0 for p in ps]),
                base_acc=np.mean([p[0]["correct"] for p in ps]), new_acc=np.mean([n(p)["correct"] for p in ps]),
                base_values=np.mean([p[0]["values"] for p in ps]), new_values=np.mean([n(p)["values"] for p in ps]),
                n=len(ps))


def boot_stats(ps, n=1000):
    """Point estimates and 95% CIs, resampling clusters (a problem, or a batch group)."""
    groups = collections.defaultdict(list)
    for p in ps:
        groups[p[1].get("cluster") or f"{p[1]['task']}/{p[1]['example_id']}"].append(p)
    groups = list(groups.values())
    est = stats(ps)
    draws = [stats([p for i in rng.integers(len(groups), size=len(groups)) for p in groups[i]]) for _ in range(n)]
    return {k: (v, *np.nanpercentile([d[k] for d in draws], [2.5, 97.5])) if k in ("slb", "ratio", "accuracy", "values", "tokens")
            else v for k, v in est.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="/local-ssd/hz466/solver-like-paper")
    ap.add_argument("--tag", default="gemma_v11_b5t")
    ap.add_argument("--a-tag", default="gemma_v11t")
    args = ap.parse_args()
    rows = load(args.tag, [m for m, _ in MODELS])
    deter = json.load(open(REPO / f"output/paper/deter_traces_{args.a_tag}.json"))
    base = [r for r in rows if r["cond"] == "baseline"]
    nums = {}
    for c, _ in METHODS:
        ps = pairs(base, rows if c.startswith("caution") else deter, c)
        nums[c] = {"pooled": boot_stats(ps)}
        for m, _ in MODELS:
            mp = [p for p in ps if p[0]["model"] == m]
            if mp:
                nums[c][m] = stats(mp)
        nums[c]["cells"] = sorted({f"{p[0]['model']}/{p[0]['task']}/{p[1]['fl']}" for p in ps})
    # Cautionary prompts on the placeholder cells, for a like-for-like comparison
    cells = {(p[0]["model"], p[0]["root"], p[0]["task"]) for p in pairs(base, deter, "placeholder")}
    for c in ("caution_a", "caution_b"):
        ps = [p for p in pairs(base, rows, c) if (p[0]["model"], p[0]["root"], p[0]["task"]) in cells]
        nums[c]["on_placeholder_cells"] = stats(ps) if ps else None
    # K sweep: batches of 2, 5 and 10 on the cells run with every K
    ks = [c for c in sorted({r["cond"] for r in deter}) if c.startswith("batch_k")]
    kcells = set.intersection(*[{(r["model"], r["root"], r["task"]) for r in deter if r["cond"] == c} for c in ks]) if ks else set()
    nums["k_sweep"] = {c: stats([p for p in pairs(base, deter, c) if (p[0]["model"], p[0]["root"], p[0]["task"]) in kcells])
                       for c in ks} if kcells else {}
    nums["k_sweep_cells"] = sorted("/".join(k) for k in kcells)

    fig, axes = plt.subplots(1, 3, figsize=(6.3, 1.45), sharey=True, gridspec_kw={"wspace": 0.12})
    y = np.arange(len(METHODS))[::-1]
    for ax, (k, name) in zip(axes, METRICS):
        ax.axvline(0, color=MUTED, lw=0.5, zorder=0)
        for yi, (c, _) in zip(y, METHODS):
            est, lo, hi = nums[c]["pooled"][k]
            ax.plot([lo, hi], [yi, yi], color=INK, lw=0.8, solid_capstyle="butt", zorder=2)
            ax.plot(est, yi, "D", color=INK, ms=3, zorder=3)
            for j, (m, _) in enumerate(MODELS):
                if m in nums[c]:
                    ax.plot(nums[c][m][k], yi - 0.28, "o", color=MODEL_COLORS[m], ms=2.6, mew=0, zorder=2)
        ax.set_title(name, fontsize=6.5)
        style(ax, grid="x")
    axes[0].set_yticks(y, [n for _, n in METHODS])
    axes[0].set_ylim(-0.6, len(METHODS) - 0.4)
    axes[0].set_xlim(-105, 15)
    handles = [Line2D([], [], marker="D", color=INK, lw=0.8, ms=3, label="Pooled (95% CI)")]
    handles += [Line2D([], [], marker="o", color=MODEL_COLORS[m], lw=0, ms=2.6, label=n) for m, n in MODELS]
    axes[1].legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.12), ncol=4, frameon=False,
                   fontsize=6.5, handlelength=1.2)
    dest = Path(args.paper) / "figures/deter.pdf"
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    out = REPO / "output/paper/deter_numbers.json"
    json.dump(nums, open(out, "w"), indent=1, default=lambda x: float(x) if isinstance(x, (np.floating, np.bool_)) else str(x))
    print("wrote", dest, out)
    for c, n in METHODS:
        p = nums[c]["pooled"]
        print(f"{n:22} n={p['n']:4}  SLB {p['slb'][0]:+6.1f}% [{p['slb'][1]:+.1f}, {p['slb'][2]:+.1f}]  "
              f"ratio {p['ratio'][0]:+.3f} [{p['ratio'][1]:+.3f}, {p['ratio'][2]:+.3f}]  "
              f"acc {p['accuracy'][0]:+.1f} [{p['accuracy'][1]:+.1f}, {p['accuracy'][2]:+.1f}]  "
              f"values {p['values'][0]:+.1f}  tokens {p['tokens'][0]:+.1f}%")


if __name__ == "__main__":
    main()
