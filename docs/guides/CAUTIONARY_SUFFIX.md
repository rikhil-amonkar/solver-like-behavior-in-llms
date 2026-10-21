# Cautionary Suffix Feature

## Overview

The cautionary suffix feature allows you to run the entire pipeline with an additional prompt component appended to the standard prompt. This enables comparative studies between:

- **Baseline condition**: Standard CSP prompts
- **Caution A condition**: Standard prompts + cautionary suffix variant A
- **Caution B condition**: Standard prompts + cautionary suffix variant B

## How It Works

### 1. Prompt Construction

**Baseline (default):**
```
[Universal CSP Prefix]
{PROBLEM}
[Task Output Format]
```

**Caution A (with `--caution-a` flag):**
```
[Universal CSP Prefix]
{PROBLEM}
[Task Output Format]
[Universal Cautionary Suffix A]  ← Added
```

**Caution B (with `--caution-b` flag):**
```
[Universal CSP Prefix]
{PROBLEM}
[Task Output Format]
[Universal Cautionary Suffix B]  ← Added
```

### 2. Output File Naming

The condition automatically propagates through all pipeline stages:

**Baseline:**
```
output/deepseek/calendar/
├── baseline_inference.json
├── baseline_evaluation.json
└── baseline_chunking.json
```

**Caution A:**
```
output/deepseek/calendar/
├── caution_a_inference.json
├── caution_a_evaluation.json
└── caution_a_chunking.json
```

**Caution B:**
```
output/deepseek/calendar/
├── caution_b_inference.json
├── caution_b_evaluation.json
└── caution_b_chunking.json
```

### 3. Metadata Tracking

All output JSONs include condition information:

```json
{
  "run_metadata": {
    "task": "calendar",
    "model": "deepseek",
    "condition": "baseline",  // or "caution_a" or "caution_b"
    "cautionary_suffix_enabled": false,  // or true (inference only)
    "cautionary_suffix_variant": null,  // or "a" or "b" (inference only)
    ...
  }
}
```

---

## Usage

### Running Baseline Condition (Default)

```bash
# Inference
python src/run_inference.py --task calendar --model deepseek --n 10

# Evaluation
python src/run_execution.py --input output/deepseek/calendar/baseline_inference.json
python src/run_evaluation.py --input output/deepseek/calendar/baseline_execution.json

# Chunking
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**Output files:**
- `baseline_inference.json`
- `baseline_evaluation.json`
- `baseline_chunking.json`

---

### Running Caution A Condition

```bash
# Inference (add --caution-a flag)
python src/run_inference.py --task calendar --model deepseek --n 10 --caution-a

# Evaluation (same command, detects condition from input)
python src/run_execution.py --input output/deepseek/calendar/caution_a_inference.json
python src/run_evaluation.py --input output/deepseek/calendar/caution_a_execution.json

# Chunking (same command, detects condition from input)
python src/run_chunking.py \
  --input output/deepseek/calendar/caution_a_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**Output files:**
- `caution_a_inference.json`
- `caution_a_evaluation.json`
- `caution_a_chunking.json`

---

### Running Caution B Condition

```bash
# Inference (add --caution-b flag)
python src/run_inference.py --task calendar --model deepseek --n 10 --caution-b

# Evaluation (same command, detects condition from input)
python src/run_execution.py --input output/deepseek/calendar/caution_b_inference.json
python src/run_evaluation.py --input output/deepseek/calendar/caution_b_execution.json

# Chunking (same command, detects condition from input)
python src/run_chunking.py \
  --input output/deepseek/calendar/caution_b_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**Output files:**
- `caution_b_inference.json`
- `caution_b_evaluation.json`
- `caution_b_chunking.json`

---

## Complete Comparative Workflow

To run both conditions for comparison:

```bash
# === BASELINE CONDITION ===
python src/run_inference.py --task calendar --model deepseek --n 10
python src/run_execution.py --input output/deepseek/calendar/baseline_inference.json
python src/run_evaluation.py --input output/deepseek/calendar/baseline_execution.json
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt

# === CAUTION CONDITION ===
python src/run_inference.py --task calendar --model deepseek --n 10 --caution
python src/run_execution.py --input output/deepseek/calendar/caution_inference.json
python src/run_evaluation.py --input output/deepseek/calendar/caution_execution.json
python src/run_chunking.py \
  --input output/deepseek/calendar/caution_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt

# Now you have both sets of outputs for comparison
ls output/deepseek/calendar/
# → baseline_inference.json    caution_inference.json
# → baseline_evaluation.json   caution_evaluation.json
# → baseline_chunking.json     caution_chunking.json
```

---

## Cautionary Suffix Content

The cautionary suffixes are loaded from:
```
prompts/cautionary/universal_cautionary_suffix_a.txt
prompts/cautionary/universal_cautionary_suffix_b.txt
```

**Current Status:**
- Variant A (`_a.txt`): Populated and ready to use
- Variant B (`_b.txt`): Empty placeholder, ready for your content
- Use `--caution-a` or `--caution-b` flags to enable the respective variant
- If file is missing or empty, a warning is shown but pipeline continues

**Example Cautionary Suffix** (future):
```
IMPORTANT: Carefully formalize this problem in code before solving it.
Do not perform calculations or solve the problem in natural language.
Your reasoning should describe the program structure, not compute the answer.
```

---

## Key Features

### Automatic Condition Detection

Evaluation and chunking **automatically detect** the condition from the inference JSON:

```python
# They read this from inference JSON:
condition = inference_data["run_metadata"]["condition"]  # "baseline" or "caution"

# Then use it for output naming:
output_file = f"{condition}_evaluation.json"
```

**No manual flags needed** for evaluation/chunking - just pass the inference JSON path!

### Metadata Consistency

All three stages track the same condition:

```json
// baseline_inference.json
{
  "run_metadata": {
    "condition": "baseline",
    "cautionary_suffix_enabled": false
  }
}

// baseline_evaluation.json
{
  "run_metadata": {
    "condition": "baseline"  // Auto-detected from inference
  }
}

// baseline_chunking.json
{
  "run_metadata": {
    "condition": "baseline"  // Auto-detected from inference
  }
}
```

### Parallel Workflows

You can run both conditions **simultaneously** (if you have resources):

Terminal 1:
```bash
python src/run_inference.py --task calendar --model deepseek
```

Terminal 2:
```bash
python src/run_inference.py --task calendar --model deepseek --caution
```

Both will write to different files, no conflicts!

---

## CLI Reference

### Inference

```bash
python src/run_inference.py \
  --task calendar \
  --model deepseek \
  --caution              # ← Enable cautionary suffix (optional)
```

**Flag:**
- `--caution` / `--use-caution`: Include cautionary suffix in prompts
- **Default**: False (baseline condition)
- **Action**: `store_true` (presence = enabled)

### Evaluation

```bash
python src/run_evaluation.py \
  --input output/deepseek/calendar/baseline_inference.json
```

**No flag needed** - condition is auto-detected from input JSON.

### Chunking

```bash
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**No flag needed** - condition is auto-detected from input JSON.

---

## Comparison Analysis

After running both conditions, you can compare:

### Accuracy Differences

```bash
# Extract accuracy from baseline
grep -A 3 "accuracy" output/deepseek/calendar/baseline_evaluation.json

# Extract accuracy from caution
grep -A 3 "accuracy" output/deepseek/calendar/caution_evaluation.json
```

### Solver-Like Behavior Differences

```bash
# Baseline: count examples with solver-like reasoning
grep "has_solver_like.*true" output/deepseek/calendar/baseline_chunking.json | wc -l

# Caution: count examples with solver-like reasoning
grep "has_solver_like.*true" output/deepseek/calendar/caution_chunking.json | wc -l
```

### Token Usage Differences

Compare `solver_like_fraction` between conditions to see if cautionary suffix reduces solver-like reasoning.

---

## Implementation Details

### Condition Propagation Flow

```
Inference (--caution flag)
  ↓
  Sets condition = "caution"
  ↓
  Saves to inference JSON metadata
  ↓
Evaluation (reads inference JSON)
  ↓
  Extracts condition from metadata
  ↓
  Uses for output naming
  ↓
Chunking (reads inference JSON)
  ↓
  Extracts condition from metadata
  ↓
  Uses for output naming
```

### File Naming Logic

```python
# In inference
condition = "caution" if use_caution else "baseline"
output_path = f"{condition}_inference.json"

# In evaluation
condition = inference_data["run_metadata"]["condition"]
output_path = f"{condition}_evaluation.json"

# In chunking
condition = inference_data["run_metadata"]["condition"]
output_path = f"{condition}_chunking.json"
```

---

## Future Use

When you're ready to use the cautionary suffix:

1. **Populate suffix files** in `prompts/cautionary/`:
   - `universal_cautionary_suffix_a.txt` (already populated)
   - `universal_cautionary_suffix_b.txt` (ready for your content)
2. **Run with `--caution-a` or `--caution-b` flag**
3. **Compare results** against baseline and between variants

The infrastructure is ready - just populate the suffix file when needed!
