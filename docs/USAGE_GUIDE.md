# Usage Guide

Complete guide to running the solver-like behavior analysis pipeline.

## Prerequisites

1. **Environment Setup**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

2. **Configure `.env`**

Required variables:
```bash
# Model API keys
DEEPSEEK_API_KEY=your-deepseek-api-key

# Token limits
MAX_OPENAI_TOKENS=384000
MAX_DEEPSEEK_TOKENS=131072
MAX_QWEN_TOKENS=131072
MAX_JUDGE_TOKENS=65536

# Google Cloud (for judge)
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_JUDGE_BATCH_MODEL=publishers/google/models/gemini-2.5-pro
JUDGE_VERTEX_GCS_BUCKET=your-gcs-bucket
JUDGE_VERTEX_GCS_PREFIX=judge-batch

# HuggingFace (for local models)
HF_CACHE=/path/to/hf/cache
```

---

## Pipeline Stages

### 1. Inference

Call models with CSP problems, extract code, execute it.

**Basic Usage:**
```bash
python src/run_inference.py --task calendar --model deepseek
```

**All Options:**
```bash
python src/run_inference.py \
  --task calendar \           # Task: calendar or meeting
  --model deepseek \          # Model: deepseek, qwen, or gpt
  --n 10 \                    # Number of examples (default: all)
  --max-tokens 50000 \        # Max generation tokens (default: from .env)
  --timeout 60                # Code execution timeout in seconds (default: 30)
```

**Output:** `output/{model}/{task}/inference.json`

**Progress Display:**
```
Processing calendar | 45/100 [00:12<00:15, success=42, errors=3]
```

**Features:**
- ✅ Incremental JSON writing (no memory buildup)
- ✅ Progress bar with success/error counts
- ✅ Error handling (continues on failure)
- ✅ Code execution in isolated subprocess

---

### 2. Evaluation

Validate code outputs against task constraints.

**Usage:**
```bash
python src/run_evaluation.py --input output/deepseek/calendar/inference.json
```

**Output:** `output/{model}/{task}/evaluation.json`

**Features:**
- ✅ Task-specific constraint checking
- ✅ Calendar: duration + time overlap validation
- ✅ Meeting: itinerary validation (basic)
- ✅ Accuracy metrics with error breakdown

**Example Output:**
```
✓ Evaluation complete!
  Accuracy: 87/100 (87.00%)
  Errors: 13/100
  Breakdown:
    constraint_violation: 5
    parse_error: 3
    code_execution_failed: 5
```

---

### 3. Chunking

Classify reasoning traces into sound vs solver-like chunks using Gemini judge.

**Usage:**
```bash
python src/run_chunking.py \
  --input output/deepseek/calendar/inference.json \
  --judge-prompt prompts/formats/llm_as_judge_for_chunking.txt
```

**Output:** `output/{model}/{task}/chunking.json`

**Features:**
- ✅ Vertex AI Gemini judge integration
- ✅ Chunk validation (ensures exact reconstruction)
- ✅ Token counting with tiktoken
- ✅ Solver-like fraction statistics

**Example Output:**
```
✓ Chunking complete!
  Examples with solver-like: 34/100
  Examples sound only: 66/100
  Total chunks: 423
```

---

## Complete Workflow Example

Run full pipeline for DeepSeek on calendar scheduling:

```bash
# Step 1: Inference (run model, execute code)
python src/run_inference.py \
  --task calendar \
  --model deepseek \
  --n 10

# Step 2: Evaluation (check constraints)
python src/run_evaluation.py \
  --input output/deepseek/calendar/inference.json

# Step 3: Chunking (classify reasoning)
python src/run_chunking.py \
  --input output/deepseek/calendar/inference.json \
  --judge-prompt prompts/formats/llm_as_judge_for_chunking.txt
```

**Final Output Structure:**
```
output/deepseek/calendar/
├── inference.json    # Model reasoning + code execution
├── evaluation.json   # Constraint validation results
└── chunking.json     # Sound vs solver-like analysis
```

---

## CLI Flags Reference

### Inference (`run_inference.py`)

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--task` | choice | Yes | - | calendar or meeting |
| `--model` | choice | Yes | - | deepseek, qwen, or gpt |
| `--n` / `--num-examples` | int | No | all | Number of examples to process |
| `--max-tokens` | int | No | from .env | Max tokens for generation |
| `--timeout` | float | No | 30.0 | Code execution timeout (seconds) |

### Evaluation (`run_evaluation.py`)

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--input` / `--inference-json` | path | Yes | - | Path to inference JSON |

### Chunking (`run_chunking.py`)

| Flag | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `--input` / `--inference-json` | path | Yes | - | Path to inference JSON |
| `--judge-prompt` | path | Yes | - | Path to judge prompt file |

---

## Error Handling

All pipelines are **fail-safe**:

1. **Continue on error**: If one example fails, pipeline continues
2. **Error logging**: Failures printed to console with example ID
3. **Error tracking**: Progress bar shows success/error counts
4. **Error output**: Failed examples written with error details

**Example Error Handling:**
```
Processing calendar | 45/100 [00:12<00:15, success=42, errors=3]

Error on calendar_scheduling_example_67: timeout after 30s
```

---

## Performance Optimizations

### Incremental JSON Writing

Instead of accumulating all results in memory:
```python
# Traditional (memory issue with 100s of examples):
results = []
for example in examples:
    results.append(process(example))
save_json(results)  # OOM risk

# Incremental (constant memory):
with IncrementalJSONWriter(path, metadata) as writer:
    for example in examples:
        result = process(example)
        writer.write_example(result)  # Flush immediately
```

### Model Loading

Local models (Qwen, GPT-OSS) use **lazy loading**:
- Models loaded once on first call
- Cached in memory for subsequent calls
- Prevents reloading overhead

### Progress Tracking

Live progress bars show:
- Current example / total
- Elapsed / estimated remaining time
- Success/error counts

---

## Troubleshooting

### "DEEPSEEK_API_KEY not found"
Add to `.env`:
```bash
DEEPSEEK_API_KEY=sk-...
```

### "GOOGLE_CLOUD_PROJECT not found"
Add to `.env`:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### "Problems file not found"
Ensure data files exist:
```
data/problems/calendar_scheduling_100.json
data/problems/meeting_planning_100.json
```

### Code execution timeouts
Increase timeout:
```bash
python src/run_inference.py --task calendar --model deepseek --timeout 60
```

### Out of memory errors
- Reduce `--n` (process fewer examples at once)
- Incremental writing should prevent this, but if it persists:
  - Check model token limits
  - Reduce `--max-tokens`

---

## Data Files

### Problems (`data/problems/`)

Format:
```json
{
  "example_id_1": {
    "problem": "Natural language problem description..."
  },
  "example_id_2": { ... }
}
```

### Constraints (`data/constraints/`)

**Calendar Scheduling:**
```json
{
  "example_id": {
    "meeting_duration": 1.0,
    "disallowed_ranges": [
      {"day": "Monday", "start": 11.5, "end": 12.0}
    ]
  }
}
```

**Meeting Planning:**
```json
{
  "example_id": {
    "locations": [...],
    "travel_times": {...},
    "meeting_windows": [...]
  }
}
```

---

## Adding New Tasks

1. **Add problem dataset**: `data/problems/{task}_100.json`
2. **Add constraints**: `data/constraints/{task}_constraints.json`
3. **Add output format prompt**: `prompts/formats/{task}_output_format.txt`
4. **Implement evaluator**: `src/evaluation/{task}_eval.py`
5. **Update mappings**:
   - `src/general/io_utils.py`: `TASK_TO_PROBLEMS_FILE`, `TASK_TO_CONSTRAINTS_FILE`
   - `src/general/prompt_utils.py`: `get_task_prompts()`
   - `src/run_evaluation.py`: `evaluate_solution()`
6. **Update CLI choices** in all three `run_*.py` scripts

---

## Best Practices

1. **Start small**: Use `--n 5` to test before full runs
2. **Check outputs**: Inspect JSON files after each stage
3. **Monitor progress**: Watch for error patterns in progress bar
4. **Version control**: Commit before major runs
5. **Document experiments**: Note flags/settings used for each run
