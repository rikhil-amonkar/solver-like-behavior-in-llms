# Smoke Tests

Quick smoke tests to verify the pipeline works correctly before running full experiments.

## Overview

These tests run the complete pipeline (inference → evaluation → chunking) on a small random sample:
- **3 random calendar scheduling examples**
- **3 random meeting planning examples**

Total: **6 examples** (very fast to run)

---

## Quick Start

### Run All Tests (Recommended)

```bash
# From repo root
cd tests/smoke

# 1. Run inference test (calls model, executes code)
python test_inference.py

# 2. Run evaluation test (validates outputs)
python test_evaluation.py

# 3. Run chunking test (classifies reasoning)
python test_chunking.py
```

### View Results

```bash
ls tests/smoke/output/

# Output files:
# - smoke_calendar_inference.json
# - smoke_calendar_evaluation.json
# - smoke_calendar_chunking.json
# - smoke_meeting_inference.json
# - smoke_meeting_evaluation.json
# - smoke_meeting_chunking.json
```

---

## Individual Test Details

### 1. Inference Test (`test_inference.py`)

**What it does:**
- Samples 3 random calendar + 3 random meeting examples
- Calls the model with CSP prompts
- Extracts and executes code
- Saves results to `smoke_{task}_inference.json`

**Usage:**
```bash
# Default: DeepSeek, 3 examples per task
python test_inference.py

# Use different model
python test_inference.py --model qwen

# More examples per task
python test_inference.py --n 5
```

**Options:**
- `--model`: Model to test (deepseek, qwen, gpt) - default: deepseek
- `--n`: Number of examples per task - default: 3

**Output:**
- `tests/smoke/output/smoke_calendar_inference.json`
- `tests/smoke/output/smoke_meeting_inference.json`

---

### 2. Evaluation Test (`test_evaluation.py`)

**What it does:**
- Loads smoke test inference outputs
- Validates code outputs against constraints
- Computes accuracy
- Saves results to `smoke_{task}_evaluation.json`

**Usage:**
```bash
# Run evaluation on smoke test outputs
python test_evaluation.py
```

**No options** - automatically finds and processes smoke test inference files.

**Output:**
- `tests/smoke/output/smoke_calendar_evaluation.json`
- `tests/smoke/output/smoke_meeting_evaluation.json`

---

### 3. Chunking Test (`test_chunking.py`)

**What it does:**
- Loads smoke test inference outputs
- Calls Gemini judge to classify reasoning
- Enriches chunks with token counts
- Saves results to `smoke_{task}_chunking.json`

**Usage:**
```bash
# Run chunking on smoke test outputs
python test_chunking.py
```

**No options** - automatically finds and processes smoke test inference files.

**Output:**
- `tests/smoke/output/smoke_calendar_chunking.json`
- `tests/smoke/output/smoke_meeting_chunking.json`

**Requirements:**
- Google Cloud credentials configured (for Gemini judge)
- `.env` file with `GOOGLE_CLOUD_PROJECT` set

---

## Example Workflow

```bash
# From repo root, navigate to smoke tests
cd tests/smoke

# Activate virtual environment
source ../../venv/bin/activate

# Run all three tests in sequence
python test_inference.py
python test_evaluation.py
python test_chunking.py

# Check results
ls -lh output/
cat output/smoke_calendar_evaluation.json | grep -A 3 "run_metadata"

# Clean up for next test
rm -rf output/
```

---

## What Gets Tested

### Inference
✅ Model calling (DeepSeek/Qwen/GPT-OSS)
✅ Prompt construction
✅ Code extraction from fenced blocks
✅ Code execution in subprocess
✅ Output parsing
✅ JSON writing (incremental)

### Evaluation
✅ Loading inference JSON
✅ Calendar constraint checking (duration, time overlap)
✅ Meeting constraint checking (basic validation)
✅ Accuracy computation
✅ Error classification

### Chunking
✅ Loading inference JSON
✅ Vertex AI judge calling
✅ JSON response parsing
✅ Chunk validation (sound/solver-like)
✅ Token counting with tiktoken
✅ Statistics computation

---

## Output Structure

```
tests/smoke/
├── test_inference.py       # Inference smoke test
├── test_evaluation.py      # Evaluation smoke test
├── test_chunking.py        # Chunking smoke test
├── README.md               # This file
└── output/                 # Test outputs (gitignored)
    ├── smoke_calendar_inference.json
    ├── smoke_calendar_evaluation.json
    ├── smoke_calendar_chunking.json
    ├── smoke_meeting_inference.json
    ├── smoke_meeting_evaluation.json
    └── smoke_meeting_chunking.json
```

---

## Interpreting Results

### Success Indicators

**Inference:**
```
✓ calendar test complete: 3 success, 0 errors
✓ meeting test complete: 3 success, 0 errors
```

**Evaluation:**
```
✓ calendar evaluation complete:
  Accuracy: 2/3 (66.7%)
  Errors:
    constraint_violation: 1
```

**Chunking:**
```
✓ calendar chunking complete:
  Solver-like: 1/3
  Sound only: 2/3
  Total chunks: 12
```

### Common Issues

**"DEEPSEEK_API_KEY not found"**
- Add API key to `.env` file

**"GOOGLE_CLOUD_PROJECT not found"**
- Add Google Cloud project to `.env` for chunking test
- Or skip chunking test if not using judge

**"No smoke test outputs found"**
- Run `test_inference.py` first
- Evaluation and chunking depend on inference outputs

**Import errors**
- Make sure you're running from `tests/smoke/` directory
- Virtual environment must be activated

---

## Cleanup

```bash
# Remove test outputs
rm -rf tests/smoke/output/

# Test outputs are gitignored, so this won't affect git
```

---

## When to Run Smoke Tests

✅ **Before full experiments** - Verify everything works
✅ **After code changes** - Ensure no regressions
✅ **When debugging** - Test small sample quickly
✅ **First time setup** - Validate configuration

---

## Differences from Production Pipeline

| Feature | Smoke Tests | Production |
|---------|-------------|------------|
| Examples | 3 per task (random) | 100 per task (all) |
| Output location | `tests/smoke/output/` | `output/{model}/{task}/` |
| File naming | `smoke_{task}_{stage}.json` | `{condition}_{stage}.json` |
| Random sampling | Yes (seed=42) | No (all examples) |
| Metadata | Includes `test_type: smoke_test` | Production metadata |

---

## Tips

💡 **Fast iteration**: Smoke tests run in minutes, not hours
💡 **Reproducible**: Random seed is fixed (42) for consistent sampling
💡 **Safe**: Test outputs are isolated from production outputs
💡 **Complete**: Tests all three pipeline stages
💡 **Realistic**: Uses actual pipeline code, not mocks
