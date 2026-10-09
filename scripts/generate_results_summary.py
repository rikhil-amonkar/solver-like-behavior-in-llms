#!/usr/bin/env python3
"""
Generate results summary markdown from output JSON files.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def extract_metrics(eval_path, exec_path, task):
    """Extract accuracy and token metrics from evaluation and execution files."""
    metrics = {}

    # Get accuracy from evaluation file
    if eval_path.exists():
        with open(eval_path) as f:
            eval_data = json.load(f)
            summary = eval_data.get('summary', {})

            # Use golden_solution_accuracy for zebralogic, constraint_based_accuracy for others
            if task == 'zebralogic':
                metrics['accuracy'] = summary.get('golden_solution_accuracy')
            else:
                metrics['accuracy'] = summary.get('constraint_based_accuracy')
    else:
        metrics['accuracy'] = None

    # Get average reasoning tokens from execution file
    if exec_path.exists():
        with open(exec_path) as f:
            exec_data = json.load(f)
            examples = exec_data.get('examples', [])

            if examples:
                total_tokens = 0
                count = 0
                for ex in examples:
                    reasoning = ex.get('reasoning_before_code', '')
                    if reasoning:
                        # Rough token count estimate: ~4 chars per token
                        tokens = len(reasoning) // 4
                        total_tokens += tokens
                        count += 1

                metrics['avg_reasoning_tokens'] = total_tokens // count if count > 0 else 0
            else:
                metrics['avg_reasoning_tokens'] = 0
    else:
        metrics['avg_reasoning_tokens'] = None

    return metrics

def main():
    # Use relative path from script location
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / 'output'

    # Structure: results[task][model][condition] = metrics
    results = defaultdict(lambda: defaultdict(dict))

    models = ['deepseek', 'gpt', 'qwen']
    tasks = ['calendar', 'meeting', 'zebralogic', 'blocksworld']
    conditions = ['baseline', 'caution_a', 'caution_b']

    for task in tasks:
        for model in models:
            for condition in conditions:
                eval_path = output_dir / model / task / f"{condition}_evaluation.json"
                exec_path = output_dir / model / task / f"{condition}_execution.json"

                metrics = extract_metrics(eval_path, exec_path, task)
                results[task][model][condition] = metrics

    # Generate markdown
    today = datetime.now().strftime('%Y-%m-%d')
    md_lines = [
        f"# Results Summary - {today}",
        "",
        "## Overview",
        "",
        "This document summarizes accuracy results across models, tasks, and prompt conditions.",
        "",
        "## Results by Task",
        "",
    ]

    # Task display names
    task_names = {
        'calendar': 'Calendar Scheduling',
        'meeting': 'Meeting Planning',
        'zebralogic': 'ZebraLogic',
        'blocksworld': 'BlocksWorld (PDDL)'
    }

    for task in tasks:
        md_lines.append(f"### {task_names[task]}")
        md_lines.append("")

        if task == 'zebralogic':
            md_lines.append("*Note: ZebraLogic uses golden solution accuracy instead of constraint-based accuracy*")
            md_lines.append("")

        # Accuracy table
        md_lines.append("**Accuracy (Constraint-Based)**" if task != 'zebralogic' else "**Accuracy (Golden Solution)**")
        md_lines.append("")
        md_lines.append("| Model | Baseline | Caution A | ΔA | Caution B | ΔB |")
        md_lines.append("|-------|----------|-----------|-----|-----------|-----|")

        for model in models:
            model_name = model.upper() if model == 'gpt' else model.capitalize()
            if model == 'gpt':
                model_name = 'GPT-OSS'

            baseline_acc = results[task][model]['baseline']['accuracy']
            caution_a_acc = results[task][model]['caution_a']['accuracy']
            caution_b_acc = results[task][model]['caution_b']['accuracy']

            baseline_str = f"{baseline_acc:.2f}" if baseline_acc is not None else "-"
            caution_a_str = f"{caution_a_acc:.2f}" if caution_a_acc is not None else "-"
            caution_b_str = f"{caution_b_acc:.2f}" if caution_b_acc is not None else "-"

            # Calculate deltas
            if baseline_acc is not None and caution_a_acc is not None:
                delta_a = caution_a_acc - baseline_acc
                delta_a_str = f"{delta_a:+.2f}" if delta_a != 0 else "0.00"
            else:
                delta_a_str = "-"

            if baseline_acc is not None and caution_b_acc is not None:
                delta_b = caution_b_acc - baseline_acc
                delta_b_str = f"{delta_b:+.2f}" if delta_b != 0 else "0.00"
            else:
                delta_b_str = "-"

            md_lines.append(f"| {model_name} | {baseline_str} | {caution_a_str} | {delta_a_str} | {caution_b_str} | {delta_b_str} |")

        md_lines.append("")

        # Reasoning tokens table
        md_lines.append("**Avg Reasoning Tokens (Before Code)**")
        md_lines.append("")
        md_lines.append("| Model | Baseline | Caution A | ΔA | Caution B | ΔB |")
        md_lines.append("|-------|----------|-----------|-----|-----------|-----|")

        for model in models:
            model_name = model.upper() if model == 'gpt' else model.capitalize()
            if model == 'gpt':
                model_name = 'GPT-OSS'

            baseline_tok = results[task][model]['baseline']['avg_reasoning_tokens']
            caution_a_tok = results[task][model]['caution_a']['avg_reasoning_tokens']
            caution_b_tok = results[task][model]['caution_b']['avg_reasoning_tokens']

            baseline_str = f"{baseline_tok:,}" if baseline_tok is not None and baseline_tok > 0 else "-"
            caution_a_str = f"{caution_a_tok:,}" if caution_a_tok is not None and caution_a_tok > 0 else "-"
            caution_b_str = f"{caution_b_tok:,}" if caution_b_tok is not None and caution_b_tok > 0 else "-"

            # Calculate deltas
            if baseline_tok is not None and baseline_tok > 0 and caution_a_tok is not None and caution_a_tok > 0:
                delta_a = caution_a_tok - baseline_tok
                delta_a_str = f"{delta_a:+,}" if delta_a != 0 else "0"
            else:
                delta_a_str = "-"

            if baseline_tok is not None and baseline_tok > 0 and caution_b_tok is not None and caution_b_tok > 0:
                delta_b = caution_b_tok - baseline_tok
                delta_b_str = f"{delta_b:+,}" if delta_b != 0 else "0"
            else:
                delta_b_str = "-"

            md_lines.append(f"| {model_name} | {baseline_str} | {caution_a_str} | {delta_a_str} | {caution_b_str} | {delta_b_str} |")

        md_lines.append("")

    # Add notes
    md_lines.extend([
        "## Notes",
        "",
        "- All accuracy values represent constraint-based accuracy from evaluation stage",
        "- ZebraLogic uses golden solution accuracy (exact match with expected solution)",
        "- `-` indicates no completed evaluation/execution JSON found or metric not available",
        "- Token counts are estimated from reasoning_before_code length (chars / 4)",
        f"- Results generated on {today}",
        ""
    ])

    # Write to file
    output_path = script_dir / 'docs' / f'{today}_RESULTS.md'
    with open(output_path, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f"✓ Results summary written to: {output_path}")

if __name__ == '__main__':
    main()
