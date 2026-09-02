#!/usr/bin/env python3
"""
Generate results markdown with chunking token breakdowns.
Analyzes chunking JSON files and creates tables for:
1. Accuracy (constraint-based)
2. Average total reasoning tokens
3. Average sound tokens
4. Average solver-like tokens
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


def load_chunking_json(path: str) -> dict:
    """Load chunking JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def calculate_chunking_stats(data: dict) -> Tuple[float, float, float]:
    """
    Calculate average token counts from chunking data.

    Returns:
        (avg_total_tokens, avg_sound_tokens, avg_solver_like_tokens)
    """
    examples = data.get("examples", [])

    total_reasoning_tokens = []
    total_sound_tokens = []
    total_solver_like_tokens = []

    for example in examples:
        stats = example.get("token_statistics", {})

        # Get total reasoning tokens
        reasoning_total = stats.get("reasoning_total_tokens", 0)
        total_reasoning_tokens.append(reasoning_total)

        # Get sound and solver-like tokens
        sound_tokens = stats.get("sound_total_tokens", 0)
        solver_like_tokens = stats.get("solver_like_total_tokens", 0)

        total_sound_tokens.append(sound_tokens)
        total_solver_like_tokens.append(solver_like_tokens)

    # Calculate averages
    n = len(examples) if examples else 1
    avg_total = sum(total_reasoning_tokens) / n if total_reasoning_tokens else 0
    avg_sound = sum(total_sound_tokens) / n if total_sound_tokens else 0
    avg_solver_like = sum(total_solver_like_tokens) / n if total_solver_like_tokens else 0

    return avg_total, avg_sound, avg_solver_like


def load_accuracy_from_evaluation(eval_path: str, task: str) -> float:
    """Load accuracy from evaluation JSON."""
    try:
        with open(eval_path, 'r') as f:
            data = json.load(f)
            summary = data.get("summary", {})
            # ZebraLogic uses golden solution accuracy, others use constraint-based
            if task == "zebralogic":
                return summary.get("golden_solution_accuracy", 0.0)
            else:
                return summary.get("constraint_based_accuracy", 0.0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0.0


def generate_results_markdown(output_dir: Path, results_file: Path):
    """Generate results markdown with chunking token breakdowns."""

    models = ["deepseek", "gpt", "qwen"]
    tasks = ["calendar", "meeting", "zebralogic", "blocksworld"]
    conditions = ["baseline", "caution_a", "caution_b"]

    # Collect all data
    data = {}
    for model in models:
        data[model] = {}
        for task in tasks:
            data[model][task] = {}
            for condition in conditions:
                chunking_path = output_dir / model / task / f"{condition}_chunking.json"
                exec_path = output_dir / model / task / f"{condition}_execution.json"
                eval_path = output_dir / model / task / f"{condition}_evaluation.json"

                # Load accuracy from evaluation JSON if it exists
                accuracy = load_accuracy_from_evaluation(str(eval_path), task) if eval_path.exists() else None

                # Load token counts from execution JSON if it exists (for total tokens)
                avg_total = None
                if exec_path.exists():
                    try:
                        exec_data = load_chunking_json(str(exec_path))
                        examples = exec_data.get("examples", [])
                        total_tokens = [ex.get("reasoning_before_code_tokens", 0) for ex in examples]
                        avg_total = sum(total_tokens) / len(total_tokens) if total_tokens else 0
                    except:
                        pass

                # Load chunking data for sound/solver-like breakdown if it exists
                avg_sound = None
                avg_solver = None
                if chunking_path.exists():
                    chunking_data = load_chunking_json(str(chunking_path))
                    _, avg_sound, avg_solver = calculate_chunking_stats(chunking_data)
                    # Also get total from chunking if we don't have it from execution
                    if avg_total is None:
                        avg_total, _, _ = calculate_chunking_stats(chunking_data)

                # Store data if we have at least accuracy or token counts
                if accuracy is not None or avg_total is not None:
                    data[model][task][condition] = {
                        "accuracy": accuracy if accuracy is not None else 0.0,
                        "avg_total": avg_total if avg_total is not None else 0,
                        "avg_sound": avg_sound if avg_sound is not None else 0,
                        "avg_solver": avg_solver if avg_solver is not None else 0
                    }
                else:
                    data[model][task][condition] = None

    # Generate markdown
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Results Summary with Chunking Analysis - {today}",
        "",
        "## Overview",
        "",
        "This document summarizes accuracy and token usage results across models, tasks, and prompt conditions.",
        "Token breakdowns show average sound vs solver-like reasoning tokens from chunking analysis.",
        "",
        "## Results by Task",
        ""
    ]

    task_names = {
        "calendar": "Calendar Scheduling",
        "meeting": "Meeting Planning",
        "zebralogic": "ZebraLogic",
        "blocksworld": "BlocksWorld (PDDL)"
    }

    for task in tasks:
        task_name = task_names.get(task, task.capitalize())

        # Add note for ZebraLogic golden solution accuracy
        accuracy_note = " (Golden Solution)" if task == "zebralogic" else " (Constraint-Based)"

        lines.extend([
            f"### {task_name}",
            "",
            f"**Accuracy{accuracy_note}**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|"
        ])

        for model in models:
            model_name = model.capitalize() if model != "gpt" else "GPT-OSS"
            baseline = data[model][task].get("baseline")
            caution_a = data[model][task].get("caution_a")
            caution_b = data[model][task].get("caution_b")

            if baseline and caution_a and baseline["accuracy"] > 0:
                baseline_acc = baseline["accuracy"]
                caution_a_acc = caution_a["accuracy"]
                delta_a = caution_a_acc - baseline_acc
                delta_a_str = f"{delta_a:+.2f}" if delta_a != 0 else "0.00"

                if caution_b and caution_b["accuracy"] > 0:
                    caution_b_acc = caution_b["accuracy"]
                    delta_b = caution_b_acc - baseline_acc
                    delta_b_str = f"{delta_b:+.2f}" if delta_b != 0 else "0.00"
                    lines.append(f"| {model_name} | {baseline_acc:.2f} | {caution_a_acc:.2f} | {delta_a_str} | {caution_b_acc:.2f} | {delta_b_str} |")
                else:
                    lines.append(f"| {model_name} | {baseline_acc:.2f} | {caution_a_acc:.2f} | {delta_a_str} | - | - |")
            else:
                lines.append(f"| {model_name} | - | - | - | - | - |")

        lines.extend([
            "",
            "**Avg Total Reasoning Tokens (Before Code)**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|"
        ])

        for model in models:
            model_name = model.capitalize() if model != "gpt" else "GPT-OSS"
            baseline = data[model][task].get("baseline")
            caution_a = data[model][task].get("caution_a")
            caution_b = data[model][task].get("caution_b")

            if baseline and caution_a and baseline["avg_total"] > 0:
                baseline_tokens = int(baseline["avg_total"])
                caution_a_tokens = int(caution_a["avg_total"])
                delta_a = caution_a_tokens - baseline_tokens
                delta_a_str = f"{delta_a:+,}" if delta_a != 0 else "0"

                if caution_b and caution_b["avg_total"] > 0:
                    caution_b_tokens = int(caution_b["avg_total"])
                    delta_b = caution_b_tokens - baseline_tokens
                    delta_b_str = f"{delta_b:+,}" if delta_b != 0 else "0"
                    lines.append(f"| {model_name} | {baseline_tokens:,} | {caution_a_tokens:,} | {delta_a_str} | {caution_b_tokens:,} | {delta_b_str} |")
                else:
                    lines.append(f"| {model_name} | {baseline_tokens:,} | {caution_a_tokens:,} | {delta_a_str} | - | - |")
            else:
                lines.append(f"| {model_name} | - | - | - | - | - |")

        lines.extend([
            "",
            "**Avg Sound Reasoning Tokens**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|"
        ])

        for model in models:
            model_name = model.capitalize() if model != "gpt" else "GPT-OSS"
            baseline = data[model][task].get("baseline")
            caution_a = data[model][task].get("caution_a")

            if baseline and caution_a and baseline["avg_sound"] > 0:
                baseline_sound = int(baseline["avg_sound"])
                caution_a_sound = int(caution_a["avg_sound"])
                delta_a = caution_a_sound - baseline_sound
                delta_a_str = f"{delta_a:+,}" if delta_a != 0 else "0"
                # Caution B always shows dashes for chunking data (not complete yet)
                lines.append(f"| {model_name} | {baseline_sound:,} | {caution_a_sound:,} | {delta_a_str} | - | - |")
            else:
                lines.append(f"| {model_name} | - | - | - | - | - |")

        lines.extend([
            "",
            "**Avg Solver-Like Reasoning Tokens**",
            "",
            "| Model | Baseline | Caution A | ΔA | Caution B | ΔB |",
            "|-------|----------|-----------|-----|-----------|-----|"
        ])

        for model in models:
            model_name = model.capitalize() if model != "gpt" else "GPT-OSS"
            baseline = data[model][task].get("baseline")
            caution_a = data[model][task].get("caution_a")

            if baseline and caution_a and baseline["avg_solver"] > 0:
                baseline_solver = int(baseline["avg_solver"])
                caution_a_solver = int(caution_a["avg_solver"])
                delta_a = caution_a_solver - baseline_solver
                delta_a_str = f"{delta_a:+,}" if delta_a != 0 else "0"
                # Caution B always shows dashes for chunking data (not complete yet)
                lines.append(f"| {model_name} | {baseline_solver:,} | {caution_a_solver:,} | {delta_a_str} | - | - |")
            else:
                lines.append(f"| {model_name} | - | - | - | - | - |")

        lines.append("")

    lines.extend([
        "## Notes",
        "",
        "- Accuracy values are constraint-based accuracy from evaluation stage (except ZebraLogic which uses golden solution accuracy)",
        "- Token counts are from Gemini judge chunking analysis with tiktoken cl100k_base encoding",
        "- Sound tokens: reasoning about formalization, constraint modeling, code structure",
        "- Solver-like tokens: reasoning that solves the problem in natural language before coding",
        "- **Caution B** is included in accuracy and total token tables, but **not** in sound/solver-like token breakdowns (chunking incomplete)",
        "- `-` indicates no data available for that model/task/condition combination",
        f"- Results generated on {today}",
        ""
    ])

    # Write to file
    with open(results_file, 'w') as f:
        f.write('\n'.join(lines))

    print(f"✓ Results written to {results_file}")


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "output"
    docs_dir = base_dir / "docs"

    today = datetime.now().strftime("%Y-%m-%d")
    results_file = docs_dir / f"{today}_RESULTS_WITH_CHUNKING.md"

    generate_results_markdown(output_dir, results_file)


if __name__ == "__main__":
    main()
