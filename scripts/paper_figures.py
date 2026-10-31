#!/usr/bin/env python3
"""
Figures and the appendix table for the paper's results (Section 5), from the per-trace table
written by scripts/paper_ontology_stats.py:

- figures/ontology_cells.pdf: one row per ontology node over all 36 cells (A1/A2 extent,
  solver-like ratio, B1-B3, program accuracy);
- figures/prose_vs_program.pdf: C, outcomes of traces with a complete prose answer (prose answer
  correct? program correct? same answer?);
- tables/ontology_cells.tex: every number behind both figures.

Palettes were checked with the dataviz validator (categorical slots, adjacent pairs pass).

Usage (env venv, for matplotlib):
    python scripts/paper_figures.py --paper /local-ssd/hz466/solver-like-paper
"""
import argparse
import collections
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parent.parent
MODELS = [("deepseek", "DeepSeek"), ("gpt", "GPT-OSS"), ("qwen", "Qwen")]
TASKS = [("calendar", "Calendar"), ("meeting", "Meeting"), ("zebralogic", "ZebraLogic"), ("blocksworld", "BlocksWorld")]
CONDS = [("baseline", "Base"), ("caution_a", "A"), ("caution_b", "B")]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#dddcd7"
A_COMPLETE, A_PARTIAL = "#6250d6", "#c4bdf2"
B_COLORS = {"hardcoded": "#2a78d6", "partly_fixed": "#eb6834", "steered": "#1baf7a"}
C_CATS = [("both", "prose and program correct", "#d6d5cf"),
          ("lost", "prose correct, program not", "#1baf7a"),
          ("override", "prose wrong, program correct", "#2a78d6"),
          ("astray", "prose wrong, program prints it", "#eb6834"),
          ("other", "prose wrong, program wrong otherwise", "#6250d6")]

plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
                     "font.size": 7, "axes.edgecolor": MUTED, "axes.linewidth": 0.5, "xtick.color": MUTED,
                     "ytick.color": MUTED, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
                     "xtick.major.size": 0, "ytick.major.size": 2, "axes.labelcolor": INK, "text.color": INK,
                     "pdf.fonttype": 42})


def cells(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["model"], r["task"], r["cond"])].append(r)
    out = {}
    for k, g in by.items():
        n = len(g)
        out[k] = dict(n=n, acc=sum(r["correct"] for r in g) / n,
                      complete=sum(r["A2"] == "complete" for r in g) / n,
                      partial=sum(r["A2"] == "partial" for r in g) / n,
                      values=sum(r["values"] for r in g),
                      ratio=sum(r["ratio"] or 0 for r in g) / n,
                      slb_tokens=sum(r["slb_tokens"] for r in g) / n,
                      reasoning_tokens=sum(r["reasoning_tokens"] for r in g) / n,
                      **{b: sum(r["B"] == b for r in g) / n for b in ("hardcoded", "partly_fixed", "steered", "independent", "na")},
                      c1_checked=sum(r["C1"] is not None for r in g), c1_no=sum(r["C1"] is False for r in g),
                      c2_checked=sum(r["C2"] is not None for r in g), c2_no=sum(r["C2"] is False for r in g))
    return out


def c_category(r):
    if r["C2"] is None:
        return None
    if r["C2"]:
        return "both" if r["correct"] else "lost"
    if r["correct"]:
        return "override"
    return "astray" if r["C1"] is True else "other"


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)


def fig_cells(st, dest):
    xs, labels = [], []
    for i in range(3):
        for j in range(3):
            xs.append(i * 3.7 + j)
            labels.append(CONDS[j][1])
    keys = [(m, c) for m, _ in MODELS for c, _ in CONDS]
    rows = [("A1/A2: traces\nsolving values", (0, 1)), ("Solver-like\nratio", (0, 0.5)),
            ("B: traces\ninheriting it", (0, 0.6)), ("Program\naccuracy", (0, 1))]
    fig, axes = plt.subplots(4, 4, figsize=(6.3, 5.0), sharey="row", gridspec_kw=dict(hspace=0.28, wspace=0.08))
    w = 0.78
    for col, (t, tname) in enumerate(TASKS):
        s = [st[(m, t, c)] for m, c in keys]
        ax = axes[0, col]
        ax.bar(xs, [x["complete"] for x in s], w, color=A_COMPLETE, edgecolor="white", linewidth=0.5)
        ax.bar(xs, [x["partial"] for x in s], w, bottom=[x["complete"] for x in s], color=A_PARTIAL, edgecolor="white", linewidth=0.5)
        ax.set_title(tname, fontsize=8, pad=3)
        axes[1, col].bar(xs, [x["ratio"] for x in s], w, color=MUTED)
        ax = axes[2, col]
        bottom = [0] * 9
        for b, colr in B_COLORS.items():
            v = [x[b] for x in s]
            ax.bar(xs, v, w, bottom=bottom, color=colr, edgecolor="white", linewidth=0.5)
            bottom = [p + q for p, q in zip(bottom, v)]
        axes[3, col].bar(xs, [x["acc"] for x in s], w, color=MUTED)
        for r, (ylab, lim) in enumerate(rows):
            ax = axes[r, col]
            style(ax)
            ax.set_ylim(*lim)
            ax.set_xlim(-0.7, xs[-1] + 0.7)
            ax.set_xticks(xs)
            ax.set_xticklabels(labels if r == 3 else [], fontsize=5.5)
            if col == 0:
                ax.set_ylabel(ylab, fontsize=7)
        for i, (_, mname) in enumerate(MODELS):
            axes[3, col].text(i * 3.7 + 1, -0.2, mname, ha="center", va="top", fontsize=6.5,
                              transform=axes[3, col].get_xaxis_transform())
    fig.legend(handles=[Patch(color=A_COMPLETE, label="A2 complete"), Patch(color=A_PARTIAL, label="A2 partial"),
                        Patch(color=B_COLORS["hardcoded"], label="B1 hardcoded"),
                        Patch(color=B_COLORS["partly_fixed"], label="B2 partly fixed"),
                        Patch(color=B_COLORS["steered"], label="B3 steered")],
               loc="upper center", ncol=5, frameon=False, fontsize=7, bbox_to_anchor=(0.5, 1.0), handlelength=1.2)
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def fig_c(rows, dest):
    fig, ax = plt.subplots(figsize=(3.1, 1.75))
    names = []
    for i, (t, tname) in enumerate(TASKS):
        g = [c for c in map(c_category, (r for r in rows if r["task"] == t)) if c]
        n = len(g)
        names.append(f"{tname} ({n})")
        left = 0
        for key, _, colr in C_CATS:
            v = g.count(key) / n
            ax.barh(i, v, 0.72, left=left, color=colr, edgecolor="white", linewidth=0.5)
            if v >= 0.07:
                ax.text(left + v / 2, i, f"{100 * v:.0f}", ha="center", va="center", fontsize=6,
                        color=INK if key == "both" else "white")
            left += v
    ax.set_yticks(range(len(TASKS)))
    ax.set_yticklabels(names, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["0%", "50%", "100%"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(handles=[Patch(color=c, label=l) for _, l, c in C_CATS], loc="upper center", bbox_to_anchor=(0.42, -0.16),
              ncol=2, frameon=False, fontsize=6, handlelength=1.0, columnspacing=0.8)
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def table(st, dest):
    lines = [r"\begin{tabular}{lll|r|rrrrr|rrrrr|rr}", r"\toprule",
             r"Model & Task & Cond. & Acc. & Val. & Cmpl. & Part. & Ratio & SLB tok. & B1 & B2 & B3 & B4 & n/a & C1 no & C2 no \\",
             r"\midrule"]
    for mi, (m, mname) in enumerate(MODELS):
        for ti, (t, tname) in enumerate(TASKS):
            for c, cname in CONDS:
                x = st[(m, t, c)]
                pct = lambda v: f"{round(100 * v)}"
                lines.append(" & ".join([mname if (ti, c) == (0, "baseline") else "", tname if c == "baseline" else "", cname,
                                         f"{x['acc']:.2f}", str(x["values"]), pct(x["complete"]), pct(x["partial"]),
                                         f"{x['ratio']:.2f}", f"{x['slb_tokens']:,.0f}".replace(",", "{,}"),
                                         *[pct(x[b]) for b in ("hardcoded", "partly_fixed", "steered", "independent", "na")],
                                         f"{x['c1_no']}/{x['c1_checked']}", f"{x['c2_no']}/{x['c2_checked']}"]) + r" \\")
            if ti < 3:
                lines.append(r"\cmidrule(lr){2-16}")
        if mi < 2:
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}"]
    dest.write_text("% generated by solver-like-behavior-in-llms/scripts/paper_figures.py; do not edit\n" + "\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="/local-ssd/hz466/solver-like-paper")
    ap.add_argument("--tag", default="gemma_v11_b5t")
    args = ap.parse_args()
    rows = json.load(open(REPO / f"output/paper/ontology_traces_{args.tag}.json"))
    st = cells(rows)
    paper = Path(args.paper)
    (paper / "tables").mkdir(exist_ok=True)
    fig_cells(st, paper / "figures/ontology_cells.pdf")
    fig_c(rows, paper / "figures/prose_vs_program.pdf")
    table(st, paper / "tables/ontology_cells.tex")
    for t, _ in TASKS:
        g = [c for c in map(c_category, (r for r in rows if r["task"] == t)) if c]
        print(t, len(g), {k: g.count(k) for k, _, _ in C_CATS})


if __name__ == "__main__":
    main()
