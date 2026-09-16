#!/usr/bin/env python3
"""
Generate detailed analysis tables and correlation computations.

This script:
1. Extracts accuracy and SL% for all examples from evaluation and chunking files
2. Creates individual tables for each model-task-condition combo
3. Computes point-biserial correlations
4. Generates summary tables
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def load_json(filepath: Path) -> Dict:
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def extract_accuracy(evaluation_data: Dict) -> Dict[str, int]:
    """Extract accuracy (0 or 1) for each example ID."""
    accuracy_map = {}
    examples = evaluation_data.get('examples', [])
    for example in examples:
        example_id = example.get('example_id', example.get('id', ''))
        correct = example.get('correct', False)
        accuracy_map[example_id] = 1 if correct else 0
    return accuracy_map


def extract_sl_percentage(chunking_data: Dict) -> Dict[str, float]:
    """Extract solver-like percentage for each example ID."""
    sl_map = {}
    examples = chunking_data.get('examples', [])
    for example in examples:
        example_id = example.get('example_id', example.get('id', ''))
        chunk_analysis = example.get('chunk_analysis', [])

        total_tokens = 0
        solver_like_tokens = 0

        for chunk in chunk_analysis:
            # Each chunk is a dict with either "sound" or "solver-like" key
            if 'solver-like' in chunk:
                chunk_tokens = chunk.get('tokens', 0)
                solver_like_tokens += chunk_tokens
                total_tokens += chunk_tokens
            elif 'sound' in chunk:
                chunk_tokens = chunk.get('tokens', 0)
                total_tokens += chunk_tokens

        sl_percentage = (solver_like_tokens / total_tokens * 100) if total_tokens > 0 else 0.0
        sl_map[example_id] = sl_percentage

    return sl_map


def compute_point_biserial_correlation(accuracies: List[int], sl_percentages: List[float]) -> float:
    """
    Compute point-biserial correlation between binary accuracy and continuous SL%.

    Formula:
    r_pb = ((M1 - M0) / sn) * sqrt(p * q)

    where:
    - M1 = mean SL% for examples where accuracy = 1
    - M0 = mean SL% for examples where accuracy = 0
    - sn = standard deviation of SL% across all examples
    - p = proportion where accuracy = 1
    - q = proportion where accuracy = 0
    """
    n = len(accuracies)
    if n == 0:
        return 0.0

    # Split SL percentages by accuracy
    sl_correct = [sl_percentages[i] for i in range(n) if accuracies[i] == 1]
    sl_incorrect = [sl_percentages[i] for i in range(n) if accuracies[i] == 0]

    # Handle edge cases
    if len(sl_correct) == 0 or len(sl_incorrect) == 0:
        return 0.0

    # Compute means
    M1 = sum(sl_correct) / len(sl_correct)
    M0 = sum(sl_incorrect) / len(sl_incorrect)

    # Compute standard deviation of all SL percentages
    mean_all = sum(sl_percentages) / n
    variance = sum((x - mean_all) ** 2 for x in sl_percentages) / n
    sn = math.sqrt(variance) if variance > 0 else 0.0

    if sn == 0:
        return 0.0

    # Compute proportions
    p = len(sl_correct) / n
    q = len(sl_incorrect) / n

    # Compute point-biserial correlation
    r_pb = ((M1 - M0) / sn) * math.sqrt(p * q)

    return r_pb


def create_individual_table(model: str, task: str, condition: str,
                           accuracy_map: Dict[str, int],
                           sl_map: Dict[str, float]) -> str:
    """Create markdown table for a single model-task-condition combo."""

    # Get all example IDs (sorted)
    example_ids = sorted(set(accuracy_map.keys()) | set(sl_map.keys()))

    lines = [
        f"# {model.upper()} - {task.capitalize()} - {condition.replace('_', ' ').title()}",
        "",
        "| Example ID | Accuracy | SL% |",
        "|------------|----------|-----|",
    ]

    for example_id in example_ids:
        accuracy = accuracy_map.get(example_id, 0)
        sl_percentage = sl_map.get(example_id, 0.0)
        lines.append(f"| {example_id} | {accuracy} | {sl_percentage:.2f} |")

    lines.append("")
    return "\n".join(lines)


def main():
    # Define paths
    output_dir = Path("output")
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    # Models, tasks, conditions
    models = ["deepseek", "qwen", "gpt"]
    tasks = ["calendar", "meeting", "blocksworld", "zebralogic"]
    conditions = ["baseline", "caution_a", "caution_b"]

    # Storage for all data
    all_data = []  # List of (model, task, condition, accuracies, sl_percentages)
    individual_tables = []

    print("Processing all model-task-condition combinations...")

    for model in models:
        for task in tasks:
            for condition in conditions:
                eval_file = output_dir / model / task / f"{condition}_evaluation.json"
                chunk_file = output_dir / model / task / f"{condition}_chunking.json"

                if not eval_file.exists() or not chunk_file.exists():
                    print(f"  Skipping {model}/{task}/{condition} (files not found)")
                    continue

                print(f"  Processing {model}/{task}/{condition}...")

                # Load data
                eval_data = load_json(eval_file)
                chunk_data = load_json(chunk_file)

                # Extract accuracy and SL%
                accuracy_map = extract_accuracy(eval_data)
                sl_map = extract_sl_percentage(chunk_data)

                # Create individual table
                table_md = create_individual_table(model, task, condition, accuracy_map, sl_map)
                individual_tables.append(table_md)

                # Store for correlation computation
                example_ids = sorted(set(accuracy_map.keys()) & set(sl_map.keys()))
                accuracies = [accuracy_map[eid] for eid in example_ids]
                sl_percentages = [sl_map[eid] for eid in example_ids]

                all_data.append((model, task, condition, accuracies, sl_percentages))

    # Write individual tables to one big file
    print("\nWriting individual tables...")
    with open(docs_dir / "DETAILED_EXAMPLE_TABLES.md", 'w') as f:
        f.write("# Detailed Example Tables\n\n")
        f.write("This file contains individual tables for each model-task-condition combination.\n")
        f.write("Each table shows 100 examples with their accuracy (0/1) and solver-like percentage (SL%).\n\n")
        f.write("---\n\n")
        f.write("\n\n---\n\n".join(individual_tables))

    print(f"  Created: docs/DETAILED_EXAMPLE_TABLES.md")

    # Compute correlations
    print("\nComputing correlations...")

    # Group by model-task
    correlations_by_model_task = defaultdict(dict)

    for model, task, condition, accuracies, sl_percentages in all_data:
        key = f"{model}-{task}"
        r_pb = compute_point_biserial_correlation(accuracies, sl_percentages)
        correlations_by_model_task[key][condition] = r_pb

    # Create correlation summary table
    lines = [
        "# Correlation Analysis Summary",
        "",
        "## Point-Biserial Correlations by Model-Task-Condition",
        "",
        "| Model-Task | Baseline | Caution A | Caution B |",
        "|------------|----------|-----------|-----------|",
    ]

    for key in sorted(correlations_by_model_task.keys()):
        model_task = key.replace('-', ' ').title()
        baseline = correlations_by_model_task[key].get('baseline', 0.0)
        caution_a = correlations_by_model_task[key].get('caution_a', 0.0)
        caution_b = correlations_by_model_task[key].get('caution_b', 0.0)
        lines.append(f"| {model_task} | {baseline:.4f} | {caution_a:.4f} | {caution_b:.4f} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Aggregate correlations
    print("  Computing aggregate correlations...")

    # All data combined
    all_accuracies = []
    all_sl_percentages = []
    for _, _, _, accs, sls in all_data:
        all_accuracies.extend(accs)
        all_sl_percentages.extend(sls)

    r_pb_all = compute_point_biserial_correlation(all_accuracies, all_sl_percentages)

    # Baseline only
    baseline_accuracies = []
    baseline_sl_percentages = []
    for _, _, condition, accs, sls in all_data:
        if condition == 'baseline':
            baseline_accuracies.extend(accs)
            baseline_sl_percentages.extend(sls)

    r_pb_baseline = compute_point_biserial_correlation(baseline_accuracies, baseline_sl_percentages)

    # Caution A only
    caution_a_accuracies = []
    caution_a_sl_percentages = []
    for _, _, condition, accs, sls in all_data:
        if condition == 'caution_a':
            caution_a_accuracies.extend(accs)
            caution_a_sl_percentages.extend(sls)

    r_pb_caution_a = compute_point_biserial_correlation(caution_a_accuracies, caution_a_sl_percentages)

    # Caution B only
    caution_b_accuracies = []
    caution_b_sl_percentages = []
    for _, _, condition, accs, sls in all_data:
        if condition == 'caution_b':
            caution_b_accuracies.extend(accs)
            caution_b_sl_percentages.extend(sls)

    r_pb_caution_b = compute_point_biserial_correlation(caution_b_accuracies, caution_b_sl_percentages)

    # Cautions combined (for comparison)
    caution_accuracies = []
    caution_sl_percentages = []
    for _, _, condition, accs, sls in all_data:
        if condition in ['caution_a', 'caution_b']:
            caution_accuracies.extend(accs)
            caution_sl_percentages.extend(sls)

    r_pb_cautions = compute_point_biserial_correlation(caution_accuracies, caution_sl_percentages)

    lines.extend([
        "## Aggregate Correlations",
        "",
        "| Category | Correlation |",
        "|----------|-------------|",
        f"| All Data (all models, tasks, conditions) | {r_pb_all:.4f} |",
        f"| Baseline Only (all models, tasks) | {r_pb_baseline:.4f} |",
        f"| Caution A Only (all models, tasks) | {r_pb_caution_a:.4f} |",
        f"| Caution B Only (all models, tasks) | {r_pb_caution_b:.4f} |",
        f"| Cautions Combined (all models, tasks) | {r_pb_cautions:.4f} |",
        "",
    ])

    # Write correlation summary
    print("\nWriting correlation summary...")
    with open(docs_dir / "CORRELATION_ANALYSIS.md", 'w') as f:
        f.write("\n".join(lines))

    print(f"  Created: docs/CORRELATION_ANALYSIS.md")
    print("\nDone!")


if __name__ == "__main__":
    main()
