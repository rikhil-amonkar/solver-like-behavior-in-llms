#!/usr/bin/env python3
"""
Section 5 figures, one per hypothesis, from the per-trace rows of the native and cross-FL runs
(output/paper/ontology_traces_<tag>[_output_crossfl].json, written by paper_ontology_stats.py).
DeepSeek's cross-FL runs are excluded (API drift; docs/CROSS_FL_DESIGN.md).

- figures/h1_prevalence.pdf   H1: traces with SLB, solver-like ratio, SLB tokens (baseline)
- figures/h2_kinds.pdf        H2: inheriting programs per dataset and FL (one column)
- figures/h3_accuracy.pdf     H3: within-problem effect of SLB on accuracy
- figures/h4_fl_dataset.pdf   H4: ratio by FL per dataset (Qwen and GPT-OSS pooled; one column; R^2 drops in nums only)
- figures/caution.pdf         Section 6: baseline vs cautionary prompts
H1-H4 (Section 5) use the baseline prompt only; the cautionary prompts are Section 6.
The paper treats a dataset's two FLs alike, so no FL is marked as native; Python comes first in every dataset.
Also writes output/paper/hypothesis_numbers.json with the numbers quoted in the text.
Palette: the validated slots of paper_figures.py.

Usage (env venv, for matplotlib):
    /local-ssd/hz466/env/bin/python scripts/paper_figures_hypotheses.py --paper /local-ssd/hz466/solver-like-paper
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from hypothesis_tests import load, boot, by_example, ols, dummies, INHERIT  # noqa: E402

MODELS = [("deepseek", "DeepSeek"), ("gpt", "GPT-OSS"), ("qwen", "Qwen")]
MODEL_COLORS = {"deepseek": "#2a78d6", "gpt": "#eb6834", "qwen": "#1baf7a"}
DATASET_COLORS = {"calendar": "#2a78d6", "meeting": "#eb6834", "zebralogic": "#1baf7a", "blocksworld": "#6250d6"}
COMBOS = [("calendar", "python"), ("calendar", "z3"), ("meeting", "python"), ("meeting", "z3"),
          ("zebralogic", "python"), ("zebralogic", "z3"), ("blocksworld", "python"), ("blocksworld", "pddl")]
TASK_NAMES = {"calendar": "Calendar", "meeting": "Meeting", "zebralogic": "ZebraLogic", "blocksworld": "BlocksWorld"}
FL_NAMES = {"python": "Python", "z3": "Z3", "pddl": "PDDL"}
NATIVE = {"calendar": "python", "meeting": "python", "zebralogic": "z3", "blocksworld": "pddl"}
B_COLORS = {"hardcoded": "#2a78d6", "partly_fixed": "#eb6834", "steered": "#1baf7a"}
B_NAMES = {"hardcoded": "B1 hardcoded", "partly_fixed": "B2 partly fixed", "steered": "B3 steered", "independent": "B4 independent"}
COND_COLORS = {"baseline": "#52514e", "caution_a": "#6250d6", "caution_b": "#c4bdf2"}
COND_NAMES = {"baseline": "Baseline", "caution_a": "Cautionary A", "caution_b": "Cautionary B"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#dddcd7"

plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
                     "font.size": 7, "axes.edgecolor": MUTED, "axes.linewidth": 0.5, "xtick.color": MUTED,
                     "ytick.color": MUTED, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
                     "xtick.major.size": 0, "ytick.major.size": 2, "axes.labelcolor": INK, "text.color": INK,
                     "pdf.fonttype": 42})


def style(ax, grid="y"):
    ax.spines[["top", "right"]].set_visible(False)
    getattr(ax, f"{grid}axis").grid(True, color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)


def mean_ci(vals):
    vals = np.asarray(vals, dtype=float)
    if len(vals) < 2:
        return float(vals.mean()) if len(vals) else np.nan, 0.0
    return float(vals.mean()), 1.96 * float(vals.std(ddof=1)) / np.sqrt(len(vals))


SHORT = {"calendar": "Cal.", "meeting": "Meet.", "zebralogic": "Zebra", "blocksworld": "BW"}


def combo_label(t, fl, short=False):
    return f"{(SHORT if short else TASK_NAMES)[t]}\n{FL_NAMES[fl]}"


def fig_h11(rows, dest, nums):
    base = [r for r in rows if r["cond"] == "baseline"]
    fig, axes = plt.subplots(3, 1, figsize=(6.3, 3.6), sharex=True, gridspec_kw={"hspace": 0.25})
    w = 0.26
    metrics = [("Traces with SLB (%)", lambda g: (100 * np.mean([r["values"] for r in g]), 0)),
               ("Solver-like ratio", lambda g: mean_ci([r["ratio"] or 0 for r in g])),
               ("SLB tokens per trace", lambda g: mean_ci([r["slb_tokens"] for r in g]))]
    for ax, (name, f) in zip(axes, metrics):
        for i, (t, fl) in enumerate(COMBOS):
            for j, (m, _) in enumerate(MODELS):
                g = [r for r in base if r["task"] == t and r["fl"] == fl and r["model"] == m]
                x = i + (j - 1) * w
                if not g:
                    if ax is axes[0]:
                        ax.text(x, 3, "–", ha="center", va="bottom", color=MUTED, fontsize=6)
                    continue
                v, ci = f(g)
                ax.bar(x, v, w * 0.9, color=MODEL_COLORS[m], yerr=ci or None, error_kw=dict(lw=0.5, capsize=0, ecolor=INK))
        ax.set_ylabel(name, fontsize=6.5)
        style(ax)
    axes[2].set_yscale("log")
    axes[2].set_ylim(10, 30000)
    axes[0].set_ylim(0, 105)
    for i in range(len(COMBOS)):
        if i % 2:
            for ax in axes:
                ax.axvspan(i - 0.5, i + 0.5, color="#f3f2ee", zorder=-1, lw=0)
    axes[2].set_xticks(range(len(COMBOS)), [combo_label(*c) for c in COMBOS])
    axes[0].legend(handles=[Patch(color=MODEL_COLORS[m], label=n) for m, n in MODELS], ncol=3, frameon=False,
                   loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=6.5, handlelength=1.0)
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    v = [r for r in base if r["values"]]
    nums["h11"] = dict(
        traces=len(base), with_values=np.mean([r["values"] for r in base]),
        ratio_ge_10=np.mean([(r["ratio"] or 0) >= 0.1 for r in base]),
        ratio_mean=np.mean([r["ratio"] or 0 for r in base]),
        tok_ge_1000=np.mean([r["slb_tokens"] >= 1000 for r in base]),
        token_share=sum(r["slb_tokens"] for r in base) / sum(r["reasoning_tokens"] for r in base),
        independent_given_values={m: np.mean([r["B"] == "independent" for r in v if r["model"] == m]) for m, _ in MODELS},
        slb_tokens={m: np.mean([r["slb_tokens"] for r in base if r["model"] == m]) for m, _ in MODELS},
        reasoning_tokens={m: np.mean([r["reasoning_tokens"] for r in base if r["model"] == m]) for m, _ in MODELS},
        values_excl_pddl=np.mean([r["values"] for r in base if r["fl"] != "pddl"]),
        values_pddl=np.mean([r["values"] for r in base if r["fl"] == "pddl"]),
        ratio_pddl=np.mean([r["ratio"] or 0 for r in base if r["fl"] == "pddl"]))


def fig_h12(rows, dest, nums):
    # One column, inheriting programs only; accuracy by prose correctness is quoted in the text (nums["h12"]).
    fig, a = plt.subplots(figsize=(3.1, 1.9))
    bottom = np.zeros(len(COMBOS))
    for k in INHERIT:
        h = np.array([sum(r["B"] == k for r in rows if (r["task"], r["fl"]) == c) for c in COMBOS])
        a.bar(range(len(COMBOS)), h, 0.6, bottom=bottom, color=B_COLORS[k], label=B_NAMES[k], edgecolor="white", linewidth=0.6)
        bottom += h
    a.set_xticks(range(len(COMBOS)), [combo_label(*c, short=True) for c in COMBOS], fontsize=5.8)
    a.set_ylabel("Programs (of 200–300)", fontsize=6.5)
    a.legend(frameon=False, fontsize=6, handlelength=1.0, loc="upper right")
    style(a)
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    kinds = list(INHERIT) + ["independent"]
    v = [r for r in rows if r["values"]]
    ran = [r for r in rows if r["B"] != "na"]
    nums["h12"] = dict(
        complete_given_values={m: np.mean([r["A2"] == "complete" for r in v if r["model"] == m]) for m, _ in MODELS},
        prose_wrong={m: np.mean([not r["C2"] for r in v if r["model"] == m and r["C2"] is not None]) for m, _ in MODELS},
        programs=len(ran), **{k: sum(r["B"] == k for r in rows) for k in kinds},
        correct_given_prose_wrong={k: (np.mean([r["correct"] for r in rows if r["B"] == k and r["C2"] is False]),
                                       sum(r["B"] == k and r["C2"] is False for r in rows)) for k in kinds},
        correct_given_prose_right={k: (np.mean([r["correct"] for r in rows if r["B"] == k and r["C2"] is True]),
                                       sum(r["B"] == k and r["C2"] is True for r in rows)) for k in kinds},
        hardcoded_gpt_meeting_native=sum(r["B"] == "hardcoded" and r["model"] == "gpt" and r["task"] == "meeting"
                                         and r["root"] == "native" for r in rows))


def lpm(rows, f, fe):
    def stat(s):
        y = np.array([float(r["correct"]) for r in s])
        X = np.column_stack([np.array([f(r) for r in s]), np.ones(len(s)), dummies(s, fe),
                             dummies(s, lambda r: (r["task"], r["example_id"]))])
        return ols(y, X)[0][0]
    return boot(by_example(rows), stat, n=200)


def fig_h13(rows, dest, nums):
    run = lambda r: (r["model"], r["task"], r["fl"])
    items = [("Solver-like ratio (+0.1)", lambda r: (r["ratio"] or 0) * 10, rows, run),
             ("SLB tokens (+1,000)", lambda r: r["slb_tokens"] / 1000, rows, run),
             ("Any SLB", lambda r: float(r["values"]), rows, run),
             ("Program inherits (B1–B3)", lambda r: float(r["B"] in INHERIT), [r for r in rows if r["B"] != "na"], run)]
    for t, name in TASK_NAMES.items():
        items.append((f"{name}: ratio (+0.1)", lambda r: (r["ratio"] or 0) * 10, [r for r in rows if r["task"] == t], run))
    res = [(name, *lpm(g, f, fe)) for name, f, g, fe in items]
    fig, ax = plt.subplots(figsize=(3.0, 2.2))
    for i, (name, e, lo, hi) in enumerate(res):
        y = len(res) - 1 - i - (0.6 if i >= 4 else 0)
        ax.plot([lo, hi], [y, y], color=INK, lw=0.8)
        ax.plot(e, y, "o", ms=3.5, color="#6250d6" if i < 4 else "#9e9d98", mec="white", mew=0.5)
    ax.axvline(0, color=MUTED, lw=0.5, ls="--")
    ax.set_yticks([len(res) - 1 - i - (0.6 if i >= 4 else 0) for i in range(len(res))], [r[0] for r in res], fontsize=6)
    ax.set_xlabel("Change in program accuracy (within run and problem)", fontsize=6.5)
    style(ax, "x")
    ax.tick_params(axis="y", length=0)
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    nums["h13"] = {name: (e, lo, hi) for name, e, lo, hi in res}
    nums["h13"]["prose correct (C2)"] = lpm([r for r in rows if r["C2"] is not None], lambda r: float(r["C2"]), run)


def r2_drops(rows):
    y = np.array([r["ratio"] or 0 for r in rows])
    keys = {"FL": lambda r: r["fl"], "Dataset": lambda r: r["task"], "Prompt": lambda r: r["cond"], "Model": lambda r: r["model"]}
    keys = {n: k for n, k in keys.items() if len({k(r) for r in rows}) > 1}
    tss = float(((y - y.mean()) ** 2).sum())
    full = 1 - ols(y, np.column_stack([np.ones(len(rows))] + [dummies(rows, k) for k in keys.values()]))[1] / tss
    out = {}
    for name in keys:
        X = np.column_stack([np.ones(len(rows))] + [dummies(rows, k) for n, k in keys.items() if n != name])
        out[name] = full - (1 - ols(y, X)[1] / tss)
    return full, out


def fig_h2(rows, dest, nums):
    # One column: Qwen and GPT-OSS pooled; each dataset is a line from Python to its declarative FL.
    both = [r for r in rows if r["model"] in ("gpt", "qwen")]
    fig, ax = plt.subplots(figsize=(3.0, 2.0))
    nums["h2"] = {"contrast": {}}
    for i, t in enumerate(["calendar", "meeting", "zebralogic", "blocksworld"]):
        fls = [NATIVE[t], next(fl for tt, fl in COMBOS if tt == t and fl != NATIVE[t])]
        fls = sorted(fls, key=lambda fl: fl != "python")  # Python first
        pts = [mean_ci([r["ratio"] or 0 for r in both if r["task"] == t and r["fl"] == fl]) for fl in fls]
        ax.errorbar([0, 1], [p[0] for p in pts], yerr=[p[1] for p in pts], color=DATASET_COLORS[t], marker="o", ms=3,
                    lw=1.2, capsize=0, elinewidth=0.6, label=f"{TASK_NAMES[t]} ({FL_NAMES[fls[1]]})")
        pairs = collections.defaultdict(dict)
        for r in both:
            if r["task"] == t:
                pairs[(r["model"], r["cond"], r["example_id"])][r["fl"]] = r
        pairs = [p for p in pairs.values() if len(p) == 2]
        groups = collections.defaultdict(list)
        for p in pairs:
            groups[p[fls[0]]["example_id"]].append(p)
        nums["h2"]["contrast"][t] = (fls, boot(groups.values(), lambda s: np.mean([(p[fls[0]]["ratio"] or 0) - (p[fls[1]]["ratio"] or 0) for p in s]), n=1000))
    ax.set_xticks([0, 1], ["Python", "Z3 / PDDL"])
    ax.set_xlim(-0.2, 1.2)
    ax.set_ylim(0, 0.45)
    ax.set_ylabel("Solver-like ratio", fontsize=6.5)
    ax.legend(frameon=False, fontsize=6, handlelength=1.2, loc="upper right", borderaxespad=0.1)
    style(ax)
    full, drops = r2_drops(both)  # variance explained per factor: quoted in the text, not drawn
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    nums["h2"]["r2_full"], nums["h2"]["r2_drops"] = full, drops
    nat = [r for r in rows if r["root"] == "native"]
    nums["h2"]["native_only_r2"] = r2_drops(nat)
    nums["h2"]["by_fl_task"] = {f"{t}/{fl}": np.mean([r["ratio"] or 0 for r in both if r["task"] == t and r["fl"] == fl]) for t, fl in COMBOS}


def fig_h3(rows, dest, nums):
    conds = ["baseline", "caution_a", "caution_b"]
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 1.7), gridspec_kw={"wspace": 0.35})
    metrics = [("Solver-like ratio", lambda r: r["ratio"] or 0, 1), ("Traces with SLB (%)", lambda r: r["values"], 100),
               ("Program accuracy (%)", lambda r: r["correct"], 100)]
    w = 0.26
    for ax, (name, f, scale) in zip(axes, metrics):
        for i, (m, _) in enumerate(MODELS):
            for j, c in enumerate(conds):
                v, ci = mean_ci([scale * f(r) for r in rows if r["model"] == m and r["cond"] == c])
                ax.bar(i + (j - 1) * w, v, w * 0.9, color=COND_COLORS[c], yerr=ci, error_kw=dict(lw=0.5, capsize=0, ecolor=INK),
                       label=COND_NAMES[c] if i == 0 else None)
        ax.set_xticks(range(len(MODELS)), [n for _, n in MODELS])
        ax.set_title(name, fontsize=7)
        style(ax)
    axes[0].legend(loc="lower center", bbox_to_anchor=(1.75, 1.12), ncol=3, frameon=False, fontsize=6.5, handlelength=1.0)
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    out = {}
    for c in conds[1:]:
        pairs = collections.defaultdict(dict)
        for r in rows:
            if r["cond"] in ("baseline", c):
                pairs[(r["model"], r["root"], r["task"], r["example_id"])][r["cond"]] = r
        pairs = [p for p in pairs.values() if len(p) == 2]
        groups = collections.defaultdict(list)
        for p in pairs:
            groups[(p["baseline"]["task"], p["baseline"]["example_id"])].append(p)
        out[c] = {k: boot(groups.values(), lambda s: np.mean([f(q[c]) - f(q["baseline"]) for q in s]), n=1000)
                  for k, f in (("ratio", lambda r: r["ratio"] or 0), ("values", lambda r: float(r["values"])),
                               ("slb_tokens", lambda r: r["slb_tokens"]), ("inherits", lambda r: float(r["B"] in INHERIT)),
                               ("accuracy", lambda r: float(r["correct"])))}
        out[c]["values_by_model"] = {m: np.mean([float(q[c]["values"]) - float(q["baseline"]["values"]) for q in pairs
                                                 if q["baseline"]["model"] == m]) for m, _ in MODELS}
    out["baseline_ratio"] = np.mean([r["ratio"] or 0 for r in rows if r["cond"] == "baseline"])
    nums["h3"] = out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="/local-ssd/hz466/solver-like-paper")
    ap.add_argument("--tag", default="gemma_v11_b5t")
    args = ap.parse_args()
    rows = load(args.tag, [m for m, _ in MODELS])
    fig_dir = Path(args.paper) / "figures"
    base = [r for r in rows if r["cond"] == "baseline"]
    nums = {"traces": len(rows), "baseline_traces": len(base)}
    fig_h11(base, fig_dir / "h1_prevalence.pdf", nums)
    fig_h12(base, fig_dir / "h2_kinds.pdf", nums)
    fig_h13(base, fig_dir / "h3_accuracy.pdf", nums)
    fig_h2(base, fig_dir / "h4_fl_dataset.pdf", nums)
    fig_h3(rows, fig_dir / "caution.pdf", nums)
    out = REPO / "output/paper/hypothesis_numbers.json"
    json.dump(nums, open(out, "w"), indent=1, default=lambda x: float(x) if isinstance(x, np.floating) else str(x))
    print(json.dumps(nums, indent=1, default=lambda x: round(float(x), 4) if isinstance(x, np.floating) else str(x)))


if __name__ == "__main__":
    main()
