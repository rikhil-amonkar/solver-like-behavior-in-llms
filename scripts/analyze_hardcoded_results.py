#!/usr/bin/env python3
"""
Analyze hardcoded detection results across all models, tasks, and conditions.
Generates a markdown report with hardcoded counts, percentages, and correlations with accuracy.
"""

import json
from pathlib import Path
from collections import defaultdict

# Accuracy data from 2026-08-31_RESULTS_WITH_CHUNKING.md
ACCURACY_DATA = {
    "calendar": {
        "deepseek": {"baseline": 0.93, "caution_a": 0.99, "caution_b": 0.97},
        "gpt": {"baseline": 0.98, "caution_a": 0.97, "caution_b": 0.97},
        "qwen": {"baseline": 0.94, "caution_a": 0.96, "caution_b": 0.92},
    },
    "meeting": {
        "deepseek": {"baseline": 0.90, "caution_a": 0.92, "caution_b": 0.92},
        "gpt": {"baseline": 0.93, "caution_a": 0.93, "caution_b": 0.90},
        "qwen": {"baseline": 0.89, "caution_a": 0.79, "caution_b": 0.83},
    },
    "zebralogic": {
        "deepseek": {"baseline": 0.94, "caution_a": 0.94, "caution_b": 0.96},
        "gpt": {"baseline": 0.84, "caution_a": 0.87, "caution_b": 0.85},
        "qwen": {"baseline": 0.57, "caution_a": 0.55, "caution_b": 0.55},
    },
    "blocksworld": {
        "deepseek": {"baseline": 0.78, "caution_a": 0.72, "caution_b": 0.69},
        "gpt": {"baseline": 0.55, "caution_a": 0.59, "caution_b": 0.47},
        "qwen": {"baseline": 0.72, "caution_a": 0.65, "caution_b": 0.62},
    },
}

# Solver-like token counts from chunking results
SOLVER_LIKE_TOKENS = {
    "calendar": {
        "deepseek": {"baseline": 1634, "caution_a": 1885, "caution_b": 1775},
        "gpt": {"baseline": 641, "caution_a": 424, "caution_b": 322},
        "qwen": {"baseline": 944, "caution_a": 830, "caution_b": 281},
    },
    "meeting": {
        "deepseek": {"baseline": 12915, "caution_a": 10990, "caution_b": 11015},
        "gpt": {"baseline": 1895, "caution_a": 840, "caution_b": 592},
        "qwen": {"baseline": 8591, "caution_a": 6149, "caution_b": 7841},
    },
    "zebralogic": {
        "deepseek": {"baseline": 3812, "caution_a": 3257, "caution_b": 3695},
        "gpt": {"baseline": 420, "caution_a": 425, "caution_b": 129},
        "qwen": {"baseline": 1771, "caution_a": 1024, "caution_b": 1206},
    },
    "blocksworld": {
        "deepseek": {"baseline": 1304, "caution_a": 1084, "caution_b": 986},
        "gpt": {"baseline": 283, "caution_a": 197, "caution_b": 203},
        "qwen": {"baseline": 366, "caution_a": 348, "caution_b": 310},
    },
}


def analyze_hardcoded_file(file_path: Path) -> dict:
    """Analyze a single hardcoded JSON file."""
    with open(file_path) as f:
        data = json.load(f)

    total = len(data["examples"])
    hardcoded_count = sum(1 for ex in data["examples"] if ex["hardcoded"] is True)
    computational_count = sum(1 for ex in data["examples"] if ex["hardcoded"] is False)
    error_count = sum(1 for ex in data["examples"] if ex["hardcoded"] is None)

    return {
        "total": total,
        "hardcoded": hardcoded_count,
        "computational": computational_count,
        "errors": error_count,
        "hardcoded_pct": 100 * hardcoded_count / total if total > 0 else 0,
    }


def main():
    output_dir = Path("output")

    # Collect all results by reading actual JSON files
    results = defaultdict(lambda: defaultdict(dict))

    models = ["deepseek", "gpt", "qwen"]
    tasks = ["calendar", "meeting", "zebralogic", "blocksworld"]
    conditions = ["baseline", "caution_a", "caution_b"]

    print("Reading hardcoded JSON files...")
    for model in models:
        for task in tasks:
            for condition in conditions:
                file_path = output_dir / model / task / f"{condition}_hardcoded.json"
                if file_path.exists():
                    results[task][model][condition] = analyze_hardcoded_file(file_path)
                    stats = results[task][model][condition]
                    print(f"  {model}/{task}/{condition}: {stats['hardcoded']}/{stats['total']} hardcoded ({stats['hardcoded_pct']:.1f}%)")
                else:
                    print(f"  ⚠ Missing: {file_path}")

    # Generate markdown report
    report_lines = [
        "# Hardcoded Detection Analysis - 2026-09-27",
        "",
        "## Overview",
        "",
        "This document analyzes hardcoded vs computational solutions across models, tasks, and prompt conditions.",
        "Hardcoded solutions contain literal answer values with minimal algorithmic computation.",
        "Computational solutions derive answers algorithmically at runtime.",
        "",
        "**Key Metrics:**",
        "- **Hardcoded Count**: Number of solutions with hardcoded literal values",
        "- **Hardcoded %**: Percentage of total solutions that are hardcoded",
        "- **Solver-Like Tokens**: Avg tokens spent solving in natural language (from chunking analysis)",
        "- **Accuracy**: Constraint-based accuracy (from evaluation stage)",
        "",
        "## Results by Task",
        "",
    ]

    for task in tasks:
        task_name = task.replace("_", " ").title()
        report_lines.extend([
            f"### {task_name}",
            "",
            "**Hardcoded Counts**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|",
        ])

        for model in models:
            model_name = "GPT-OSS" if model == "gpt" else model.capitalize()
            baseline = results[task][model].get("baseline", {})
            caution_a = results[task][model].get("caution_a", {})
            caution_b = results[task][model].get("caution_b", {})

            b_count = baseline.get("hardcoded", "N/A")
            a_count = caution_a.get("hardcoded", "N/A")
            b_count_b = caution_b.get("hardcoded", "N/A")

            # Get total examples (denominator) from the hardcoded results
            b_total = baseline.get("total", "N/A")
            a_total = caution_a.get("total", "N/A")
            b_total_b = caution_b.get("total", "N/A")

            # Format as fractions: hardcoded/total
            b_str = f"{b_count}/{b_total}" if isinstance(b_count, int) and isinstance(b_total, int) else "N/A"
            a_str = f"{a_count}/{a_total}" if isinstance(a_count, int) and isinstance(a_total, int) else "N/A"
            b_str_b = f"{b_count_b}/{b_total_b}" if isinstance(b_count_b, int) and isinstance(b_total_b, int) else "N/A"

            # Calculate deltas only if all values exist
            if isinstance(b_count, int) and isinstance(a_count, int):
                delta_a = a_count - b_count
                delta_a_str = f"+{delta_a}" if delta_a > 0 else str(delta_a)
            else:
                delta_a_str = "N/A"

            if isinstance(b_count, int) and isinstance(b_count_b, int):
                delta_b = b_count_b - b_count
                delta_b_str = f"+{delta_b}" if delta_b > 0 else str(delta_b)
            else:
                delta_b_str = "N/A"

            report_lines.append(
                f"| {model_name} | {b_str} | {a_str} | {delta_a_str} | {b_str_b} | {delta_b_str} |"
            )

        report_lines.extend([
            "",
            "**Hardcoded Percentage**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|",
        ])

        for model in models:
            model_name = "GPT-OSS" if model == "gpt" else model.capitalize()
            baseline = results[task][model].get("baseline", {})
            caution_a = results[task][model].get("caution_a", {})
            caution_b = results[task][model].get("caution_b", {})

            b_pct = baseline.get("hardcoded_pct")
            a_pct = caution_a.get("hardcoded_pct")
            b_pct_b = caution_b.get("hardcoded_pct")

            # Format percentages
            b_pct_str = f"{b_pct:.1f}%" if b_pct is not None else "N/A"
            a_pct_str = f"{a_pct:.1f}%" if a_pct is not None else "N/A"
            b_pct_b_str = f"{b_pct_b:.1f}%" if b_pct_b is not None else "N/A"

            # Calculate deltas
            if b_pct is not None and a_pct is not None:
                delta_a = a_pct - b_pct
                delta_a_str = f"+{delta_a:.1f}%" if delta_a > 0 else f"{delta_a:.1f}%"
            else:
                delta_a_str = "N/A"

            if b_pct is not None and b_pct_b is not None:
                delta_b = b_pct_b - b_pct
                delta_b_str = f"+{delta_b:.1f}%" if delta_b > 0 else f"{delta_b:.1f}%"
            else:
                delta_b_str = "N/A"

            report_lines.append(
                f"| {model_name} | {b_pct_str} | {a_pct_str} | {delta_a_str} | {b_pct_b_str} | {delta_b_str} |"
            )

        report_lines.extend([
            "",
            "**Solver-Like Tokens (Avg)**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|",
        ])

        for model in models:
            model_name = "GPT-OSS" if model == "gpt" else model.capitalize()
            b_tokens = SOLVER_LIKE_TOKENS[task][model]["baseline"]
            a_tokens = SOLVER_LIKE_TOKENS[task][model]["caution_a"]
            b_tokens_b = SOLVER_LIKE_TOKENS[task][model]["caution_b"]

            delta_a = a_tokens - b_tokens
            delta_b = b_tokens_b - b_tokens

            delta_a_str = f"+{delta_a:,}" if delta_a > 0 else f"{delta_a:,}"
            delta_b_str = f"+{delta_b:,}" if delta_b > 0 else f"{delta_b:,}"

            report_lines.append(
                f"| {model_name} | {b_tokens:,} | {a_tokens:,} | {delta_a_str} | {b_tokens_b:,} | {delta_b_str} |"
            )

        report_lines.extend([
            "",
            "**Accuracy**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|",
        ])

        for model in models:
            model_name = "GPT-OSS" if model == "gpt" else model.capitalize()
            b_acc = ACCURACY_DATA[task][model]["baseline"]
            a_acc = ACCURACY_DATA[task][model]["caution_a"]
            b_acc_b = ACCURACY_DATA[task][model]["caution_b"]

            delta_a = a_acc - b_acc
            delta_b = b_acc_b - b_acc

            delta_a_str = f"+{delta_a:.2f}" if delta_a > 0 else f"{delta_a:.2f}"
            delta_b_str = f"+{delta_b:.2f}" if delta_b > 0 else f"{delta_b:.2f}"

            report_lines.append(
                f"| {model_name} | {b_acc:.2f} | {a_acc:.2f} | {delta_a_str} | {b_acc_b:.2f} | {delta_b_str} |"
            )

        report_lines.extend(["", "---", ""])

    # Add correlation analysis
    report_lines.extend([
        "## Observations",
        "",
        "### Hardcoded Solutions by Task",
        "",
        "**Calendar Scheduling**: Very low hardcoding across all models (0%). Calendar problems require",
        "algorithmic time slot searching, making hardcoded solutions impractical.",
        "",
        "**Meeting Planning**: Moderate to high hardcoding, especially in GPT-OSS baseline (50.5%).",
        "Meeting itineraries can be more easily hardcoded as sequential lists of actions. Cautionary",
        "prompts dramatically reduce this (Caution A: 4.3%, Caution B: 1.1%).",
        "",
        "**ZebraLogic**: Very low hardcoding (0-1%). Logic grid puzzles typically require constraint solving",
        "(Z3) or backtracking algorithms, difficult to hardcode.",
        "",
        "**BlocksWorld (PDDL)**: Low to moderate hardcoding (1-7%). PDDL planning problems require complex",
        "state space search, but some simple problems may allow hardcoded action sequences.",
        "",
        "### Effect of Cautionary Prompts",
        "",
        "**Dramatic Impact on Meeting Tasks**: GPT-OSS meeting baseline has 50.5% hardcoding, which drops",
        "to 4.3% (Caution A) and 1.1% (Caution B). This is the most striking effect observed.",
        "",
        "**General Reduction**: Cautionary prompts generally reduce hardcoding across tasks and models.",
        "The warnings about proper formalization appear to discourage literal solution embedding.",
        "",
        "**Solver-Like vs Hardcoded**: Solver-like reasoning (solving in natural language) does NOT strongly",
        "correlate with hardcoded solutions. Models can solve problems in reasoning traces while still",
        "implementing proper algorithmic code. For example, Deepseek Meeting has high solver-like tokens",
        "(~13k baseline) but very low hardcoding (1.1%).",
        "",
        "### Accuracy Correlation",
        "",
        "**No Strong Negative Correlation**: Hardcoded solutions do not consistently predict lower accuracy.",
        "GPT-OSS Meeting Baseline has both high hardcoding (50.5%) and high accuracy (0.93), suggesting",
        "the hardcoded values are often correct for those specific problems.",
        "",
        "**Task Complexity Matters**: The relationship between hardcoding and accuracy varies by task.",
        "Calendar and ZebraLogic (0% hardcoding) require proper algorithms. Meeting tasks allow some",
        "hardcoding with maintained accuracy. BlocksWorld shows mixed results.",
        "",
        "**Cautionary Prompts**: While cautionary prompts reduce hardcoding, their effect on accuracy",
        "varies. In some cases accuracy improves (Deepseek Calendar), in others it stays stable or",
        "decreases (GPT-OSS Meeting Caution B: 0.90 vs 0.93 baseline).",
        "",
        "## Key Findings",
        "",
        "1. **GPT-OSS Meeting Baseline**: 50.5% hardcoded - the highest rate observed",
        "2. **Cautionary Prompts Work**: Reduce GPT-OSS meeting hardcoding by ~46-49 percentage points",
        "3. **Task Dependency**: Calendar (0%), ZebraLogic (0-1%), BlocksWorld (1-7%), Meeting (0-50.5%)",
        "4. **Solver-Like ≠ Hardcoded**: High natural language solving doesn't imply hardcoded code",
        "5. **Accuracy Independence**: Hardcoded solutions can be accurate if values are correct",
        "",
        "## Notes",
        "",
        "- Hardcoded detection performed using Gemini 2.5 Pro judge via Vertex AI Batch API",
        "- Only examples with successful code execution (`exit_code == 0`) were judged",
        "- Solver-like token counts from chunking analysis (Gemini judge with tiktoken encoding)",
        "- Accuracy values are constraint-based from evaluation stage (except ZebraLogic: golden solution)",
        "- Results generated on 2026-09-27",
        "- Missing file: gpt/blocksworld/caution_b_hardcoded.json (marked as N/A in tables)",
        "",
    ])

    # Write report
    report_path = Path("docs/2026-09-27_HARDCODED_ANALYSIS.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))

    print(f"\n✓ Report generated: {report_path}")

    # Print summary stats
    print("\n=== Summary Statistics ===")
    for task in tasks:
        print(f"\n{task.upper()}:")
        for model in models:
            for condition in conditions:
                stats = results[task][model].get(condition)
                if stats:
                    print(f"  {model:10s} {condition:10s}: {stats['hardcoded']:3d}/{stats['total']:3d} hardcoded ({stats['hardcoded_pct']:5.1f}%)")


if __name__ == "__main__":
    main()
