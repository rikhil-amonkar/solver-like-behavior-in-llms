#!/usr/bin/env python3
"""
Generate the main results table (paper Table 1) from output/{model}/{task}/ files.

For each model, task and condition it reports:
- Accuracy: mean +/- std of per-problem correctness (from *_evaluation.json)
- Ratio: pooled solver-like tokens / pooled reasoning tokens, with std across
  per-problem ratios (from *_chunking.json)
- Solver-like tokens: mean +/- std of per-problem solver-like tokens (from *_chunking.json)

Usage:
    python scripts/generate_results_table.py
    python scripts/generate_results_table.py --output docs/results/RESULTS_TABLE.md
"""

import argparse
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MODELS = [("deepseek", "DeepSeek"), ("gpt", "GPT-OSS"), ("qwen", "Qwen")]
TASKS = [("calendar", "Calendar"), ("meeting", "Meeting"), ("zebralogic", "ZebraLogic"), ("blocksworld", "BlocksWorld")]
CONDITIONS = [("baseline", "Base"), ("caution_a", "Caut A"), ("caution_b", "Caut B")]


def load_examples(path: Path) -> list:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("examples", [])


def std(values: list) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def compute_cell(output_root: Path, model: str, task: str, condition: str) -> dict:
    run_dir = output_root / model / task
    evaluation = load_examples(run_dir / f"{condition}_evaluation.json")
    chunking = load_examples(run_dir / f"{condition}_chunking.json")

    cell = {}
    if evaluation:
        correct = [1.0 if e.get("correct") else 0.0 for e in evaluation]
        cell["accuracy"] = (statistics.mean(correct), std(correct))

    stats = [e.get("token_statistics") or {} for e in chunking]
    stats = [s for s in stats if "solver_like_total_tokens" in s]
    if stats:
        solver = [s["solver_like_total_tokens"] for s in stats]
        total = [s["reasoning_total_tokens"] for s in stats]
        ratios = [s["solver_like_fraction"] for s in stats]
        cell["ratio"] = (sum(solver) / sum(total) if sum(total) else 0.0, std(ratios))
        cell["tokens"] = (statistics.mean(solver), std(solver))
    return cell


def fmt(value, kind: str) -> str:
    if value is None:
        return "-"
    mean, dev = value
    if kind == "tokens":
        return f"{mean:,.0f} ± {dev:,.0f}"
    return f"{mean:.2f} ± {dev:.2f}"


def build_table(output_root: Path) -> str:
    header = ["Model", "Metric"] + [f"{t} {c}" for _, t in TASKS for _, c in CONDITIONS]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for model, model_name in MODELS:
        cells = {(t, c): compute_cell(output_root, model, t, c) for t, _ in TASKS for c, _ in CONDITIONS}
        for metric, label in [("accuracy", "Accuracy"), ("ratio", "Ratio"), ("tokens", "Solver Tokens")]:
            row = [model_name if metric == "accuracy" else "", label]
            row += [fmt(cells[(t, c)].get(metric), metric) for t, _ in TASKS for c, _ in CONDITIONS]
            lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate the main results table")
    parser.add_argument("--output-root", default=str(REPO_ROOT / "output"), help="Pipeline output root")
    parser.add_argument("--output", default=None, help="Write markdown table to this file (default: print)")
    args = parser.parse_args()

    table = build_table(Path(args.output_root))
    if args.output:
        Path(args.output).write_text(table + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(table)


if __name__ == "__main__":
    main()
