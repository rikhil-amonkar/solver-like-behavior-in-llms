# Baseline vs Caution Comparison Example

This document shows a complete example of running multiple conditions and comparing results.

## Scenario

You want to compare how DeepSeek performs on calendar scheduling with baseline prompts versus cautionary suffix variants A and B.

---

## Step 1: Run Baseline Condition

```bash
# Inference (no --caution flag = baseline)
python src/run_inference.py --task calendar --model deepseek --n 100

# Evaluation
python src/run_evaluation.py --input output/deepseek/calendar/baseline_inference.json

# Chunking
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**Files Created:**
```
output/deepseek/calendar/
├── baseline_inference.json
├── baseline_evaluation.json
└── baseline_chunking.json
```

---

## Step 2: Run Caution A Condition

```bash
# Inference (with --caution-a flag)
python src/run_inference.py --task calendar --model deepseek --n 100 --caution-a

# Evaluation (same command, auto-detects condition)
python src/run_evaluation.py --input output/deepseek/calendar/caution_a_inference.json

# Chunking (same command, auto-detects condition)
python src/run_chunking.py \
  --input output/deepseek/calendar/caution_a_inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**Files Created:**
```
output/deepseek/calendar/
├── caution_a_inference.json
├── caution_a_evaluation.json
└── caution_a_chunking.json
```

---

## Step 3: Run Caution B Condition

```bash
# Inference (with --caution-b flag)
python src/run_inference.py --task calendar --model deepseek --n 100 --caution-b

# Evaluation (same command, auto-detects condition)
python src/run_evaluation.py --input output/deepseek/calendar/caution_b_inference.json

# Chunking (same command, auto-detects condition)
python src/run_chunking.py \
  --input output/deepseek/calendar/caution_b_inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**Files Created:**
```
output/deepseek/calendar/
├── caution_b_inference.json
├── caution_b_evaluation.json
└── caution_b_chunking.json
```

---

## Step 4: Compare Results

### Directory Structure

```
output/deepseek/calendar/
├── baseline_inference.json      ← Baseline condition
├── baseline_evaluation.json
├── baseline_chunking.json
├── caution_a_inference.json     ← Caution A condition
├── caution_a_evaluation.json
├── caution_a_chunking.json
├── caution_b_inference.json     ← Caution B condition
├── caution_b_evaluation.json
└── caution_b_chunking.json
```

### Accuracy Comparison

**Baseline:**
```bash
$ grep -A 5 '"accuracy"' output/deepseek/calendar/baseline_evaluation.json

# Example output:
# "accuracy": 0.87,
# "correct": 87,
# "incorrect": 13
```

**Caution A:**
```bash
$ grep -A 5 '"accuracy"' output/deepseek/calendar/caution_a_evaluation.json

# Example output:
# "accuracy": 0.92,  ← Improved!
# "correct": 92,
# "incorrect": 8
```

**Caution B:**
```bash
$ grep -A 5 '"accuracy"' output/deepseek/calendar/caution_b_evaluation.json

# Example output:
# "accuracy": 0.89,
# "correct": 89,
# "incorrect": 11
```

### Solver-Like Behavior Comparison

**Baseline:**
```bash
$ python -c "
import json
with open('output/deepseek/calendar/baseline_chunking.json') as f:
    data = json.load(f)
examples = data['examples']
solver_like = sum(1 for ex in examples if ex['has_solver_like'])
print(f'Solver-like examples: {solver_like}/{len(examples)}')
"

# Example output:
# Solver-like examples: 45/100
```

**Caution A:**
```bash
$ python -c "
import json
with open('output/deepseek/calendar/caution_a_chunking.json') as f:
    data = json.load(f)
examples = data['examples']
solver_like = sum(1 for ex in examples if ex['has_solver_like'])
print(f'Solver-like examples: {solver_like}/{len(examples)}')
"

# Example output:
# Solver-like examples: 23/100  ← Reduced!
```

**Caution B:**
```bash
$ python -c "
import json
with open('output/deepseek/calendar/caution_b_chunking.json') as f:
    data = json.load(f)
examples = data['examples']
solver_like = sum(1 for ex in examples if ex['has_solver_like'])
print(f'Solver-like examples: {solver_like}/{len(examples)}')
"

# Example output:
# Solver-like examples: 28/100  ← Also reduced
```

### Token Statistics

**Baseline:**
```bash
$ python -c "
import json
with open('output/deepseek/calendar/baseline_chunking.json') as f:
    data = json.load(f)
fractions = [ex['token_statistics']['solver_like_fraction']
             for ex in data['examples'] if ex['has_solver_like']]
avg_fraction = sum(fractions) / len(fractions) if fractions else 0
print(f'Average solver-like fraction: {avg_fraction:.2%}')
"

# Example output:
# Average solver-like fraction: 42.3%
```

**Caution A:**
```bash
$ python -c "
import json
with open('output/deepseek/calendar/caution_a_chunking.json') as f:
    data = json.load(f)
fractions = [ex['token_statistics']['solver_like_fraction']
             for ex in data['examples'] if ex['has_solver_like']]
avg_fraction = sum(fractions) / len(fractions) if fractions else 0
print(f'Average solver-like fraction: {avg_fraction:.2%}')
"

# Example output:
# Average solver-like fraction: 28.7%  ← Reduced!
```

**Caution B:**
```bash
$ python -c "
import json
with open('output/deepseek/calendar/caution_b_chunking.json') as f:
    data = json.load(f)
fractions = [ex['token_statistics']['solver_like_fraction']
             for ex in data['examples'] if ex['has_solver_like']]
avg_fraction = sum(fractions) / len(fractions) if fractions else 0
print(f'Average solver-like fraction: {avg_fraction:.2%}')
"

# Example output:
# Average solver-like fraction: 34.2%  ← Different reduction
```

---

## Analysis Script Example

Create a simple comparison script:

```python
#!/usr/bin/env python3
"""Compare baseline vs caution variants results."""

import json
from pathlib import Path

def analyze_condition(condition, model="deepseek", task="calendar"):
    """Load and analyze results for a condition."""
    base_path = Path(f"output/{model}/{task}")

    # Load all three JSONs
    with open(base_path / f"{condition}_evaluation.json") as f:
        eval_data = json.load(f)

    with open(base_path / f"{condition}_chunking.json") as f:
        chunk_data = json.load(f)

    # Extract metrics
    accuracy = eval_data["run_metadata"].get("accuracy", 0)

    examples = chunk_data["examples"]
    solver_like_count = sum(1 for ex in examples if ex["has_solver_like"])

    fractions = [
        ex["token_statistics"]["solver_like_fraction"]
        for ex in examples
        if ex["has_solver_like"]
    ]
    avg_fraction = sum(fractions) / len(fractions) if fractions else 0

    return {
        "condition": condition,
        "accuracy": accuracy,
        "solver_like_examples": solver_like_count,
        "total_examples": len(examples),
        "solver_like_percentage": solver_like_count / len(examples) * 100,
        "avg_solver_like_fraction": avg_fraction * 100,
    }

# Compare all conditions
baseline = analyze_condition("baseline")
caution_a = analyze_condition("caution_a")
caution_b = analyze_condition("caution_b")

# Print comparison
print("=" * 70)
print("BASELINE VS CAUTION A VS CAUTION B COMPARISON")
print("=" * 70)
print(f"\nAccuracy:")
print(f"  Baseline:   {baseline['accuracy']:.2%}")
print(f"  Caution A:  {caution_a['accuracy']:.2%}  (Δ {(caution_a['accuracy'] - baseline['accuracy']):+.2%})")
print(f"  Caution B:  {caution_b['accuracy']:.2%}  (Δ {(caution_b['accuracy'] - baseline['accuracy']):+.2%})")

print(f"\nSolver-Like Examples:")
print(f"  Baseline:   {baseline['solver_like_examples']}/{baseline['total_examples']} ({baseline['solver_like_percentage']:.1f}%)")
print(f"  Caution A:  {caution_a['solver_like_examples']}/{caution_a['total_examples']} ({caution_a['solver_like_percentage']:.1f}%)")
print(f"  Caution B:  {caution_b['solver_like_examples']}/{caution_b['total_examples']} ({caution_b['solver_like_percentage']:.1f}%)")

print(f"\nAverage Solver-Like Token Fraction:")
print(f"  Baseline:   {baseline['avg_solver_like_fraction']:.1f}%")
print(f"  Caution A:  {caution_a['avg_solver_like_fraction']:.1f}%  (Δ {baseline['avg_solver_like_fraction'] - caution_a['avg_solver_like_fraction']:+.1f}%)")
print(f"  Caution B:  {caution_b['avg_solver_like_fraction']:.1f}%  (Δ {baseline['avg_solver_like_fraction'] - caution_b['avg_solver_like_fraction']:+.1f}%)")
print("=" * 70)
```

**Example Output:**
```
============================================================
BASELINE VS CAUTION COMPARISON
============================================================

Accuracy:
  Baseline: 87.00%
  Caution:  92.00%
  Δ:        5.00%

Solver-Like Examples:
  Baseline: 45/100 (45.0%)
  Caution:  23/100 (23.0%)
  Δ:        22 examples

Average Solver-Like Token Fraction:
  Baseline: 42.3%
  Caution:  28.7%
  Δ:        13.6%
============================================================
```

---

## Key Takeaways

### File Organization

Both conditions coexist peacefully in the same directory:
```
output/deepseek/calendar/
├── baseline_*     ← Standard prompts
└── caution_*      ← Prompts + cautionary suffix
```

### No Manual Tracking

The condition is **automatically tracked** in metadata:
- Set once in inference (via `--caution` flag)
- Auto-detected by evaluation (reads inference JSON)
- Auto-detected by chunking (reads inference JSON)

### Comparative Analysis

You can easily compare:
- **Accuracy changes**: Did caution improve correctness?
- **Solver-like behavior**: Did caution reduce solver-like reasoning?
- **Token distributions**: How did reasoning patterns shift?

---

## Running Both in Parallel

If you have resources, run both simultaneously:

**Terminal 1** (baseline):
```bash
python src/run_inference.py --task calendar --model deepseek
python src/run_evaluation.py --input output/deepseek/calendar/baseline_inference.json
python src/run_chunking.py --input output/deepseek/calendar/baseline_inference.json --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**Terminal 2** (caution):
```bash
python src/run_inference.py --task calendar --model deepseek --caution
python src/run_evaluation.py --input output/deepseek/calendar/caution_inference.json
python src/run_chunking.py --input output/deepseek/calendar/caution_inference.json --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**No conflicts** - they write to different files!
