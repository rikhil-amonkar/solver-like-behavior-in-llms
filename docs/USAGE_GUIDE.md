# Usage Guide

Quick reference for running the solver-like behavior analysis pipeline.

---

## Setup (One-Time)

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in:

```bash
# Required: DeepSeek API
DEEPSEEK_API_KEY=sk-your-key-here

# Required: Google Cloud (for Gemini judge)
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Optional: Token limits (defaults provided)
MAX_DEEPSEEK_TOKENS=131072
MAX_JUDGE_TOKENS=65536
```

---

## Quick Start

### Test Run (5 Examples)

```bash
# Run inference
python src/run_inference.py --task calendar --model deepseek --n 5

# Evaluate results
python src/run_evaluation.py --input output/deepseek/calendar/baseline_inference.json

# Analyze reasoning (optional)
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

### Full Run (100 Examples)

```bash
# Inference (omit --n for all examples)
python src/run_inference.py --task calendar --model deepseek

# Evaluation
python src/run_evaluation.py --input output/deepseek/calendar/baseline_inference.json

# Chunking
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

---

## Pipeline Stages

### 1. Inference - Get Model Reasoning

**What it does**: Calls LLM with CSP problems, extracts and executes code, formats outputs

**Usage**:
```bash
python src/run_inference.py --task TASK --model MODEL [OPTIONS]
```

**Required**:
- `--task`: `calendar`, `meeting`, `zebralogic`, or `blocksworld`
- `--model`: `deepseek`, `qwen`, or `gpt`

**Optional**:
- `--n NUM`: Process only NUM examples (default: all 100)
- `--max-tokens NUM`: Max generation tokens (default: from .env)
- `--timeout SEC`: Code execution timeout in seconds (default: 30)
- `--caution-a`: Add anti-solver prompt variant A
- `--caution-b`: Add anti-solver prompt variant B

**Output**: `output/{model}/{task}/{condition}_inference.json`

**Examples**:
```bash
# Basic run
python src/run_inference.py --task calendar --model deepseek

# Quick test
python src/run_inference.py --task meeting --model deepseek --n 10

# With cautionary prompt
python src/run_inference.py --task calendar --model deepseek --caution-a

# Different model
python src/run_inference.py --task zebralogic --model qwen --n 20
```

---

### 2. Evaluation - Validate Outputs

**What it does**: Checks code outputs against task-specific constraints

**Usage**:
```bash
python src/run_evaluation.py --input INFERENCE_JSON
```

**Required**:
- `--input`: Path to inference JSON from step 1

**Output**: `output/{model}/{task}/{condition}_evaluation.json`

**Examples**:
```bash
# Baseline evaluation
python src/run_evaluation.py --input output/deepseek/calendar/baseline_inference.json

# Caution A evaluation
python src/run_evaluation.py --input output/deepseek/calendar/caution_a_inference.json
```

**What gets validated**:
- **Calendar**: Meeting duration, no time overlaps with busy slots
- **Meeting**: Travel times feasible, itinerary coherent
- **ZebraLogic**: Exact match with golden solution
- **BlocksWorld**: PDDL plan validates against groundtruth problem

---

### 3. Chunking - Analyze Reasoning (Optional)

**What it does**: Classifies reasoning into "sound formalization" vs "solver-like" chunks using Gemini judge

**Usage**:
```bash
python src/run_chunking.py --input INFERENCE_JSON --judge-prompt PROMPT_FILE
```

**Required**:
- `--input`: Path to inference JSON
- `--judge-prompt`: Path to judge prompt (use `prompts/judge/llm_as_judge_for_chunking.txt`)

**Optional**:
- `--sequential`: Use sequential API calls instead of batch mode (slower, no GCS needed)
- `--gcs-bucket`: GCS bucket for batch mode (if not in .env)

**Output**: `output/{model}/{task}/{condition}_chunking.json`

**Examples**:
```bash
# Batch mode (fast, requires GCS)
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt

# Sequential mode (slower, no GCS needed)
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --sequential
```

---

## Common Workflows

### Compare Baseline vs Cautionary Prompts

```bash
# 1. Run baseline
python src/run_inference.py --task calendar --model deepseek --n 100
python src/run_evaluation.py --input output/deepseek/calendar/baseline_inference.json

# 2. Run with caution-a
python src/run_inference.py --task calendar --model deepseek --n 100 --caution-a
python src/run_evaluation.py --input output/deepseek/calendar/caution_a_inference.json

# 3. Run with caution-b
python src/run_inference.py --task calendar --model deepseek --n 100 --caution-b
python src/run_evaluation.py --input output/deepseek/calendar/caution_b_inference.json

# 4. Compare accuracy
grep "constraint_based_accuracy" output/deepseek/calendar/*_evaluation.json
```

### Run Multiple Models on Same Task

```bash
# DeepSeek
python src/run_inference.py --task meeting --model deepseek
python src/run_evaluation.py --input output/deepseek/meeting/baseline_inference.json

# Qwen (requires local GPU)
python src/run_inference.py --task meeting --model qwen
python src/run_evaluation.py --input output/qwen/meeting/baseline_inference.json

# GPT-OSS (requires local GPU)
python src/run_inference.py --task meeting --model gpt
python src/run_evaluation.py --input output/gpt/meeting/baseline_inference.json
```

### Full Experimental Suite

Run all combinations for comprehensive analysis:

```bash
#!/bin/bash
# run_full_experiment.sh

MODELS="deepseek qwen gpt"
TASKS="calendar meeting zebralogic blocksworld"
CONDITIONS="baseline caution_a caution_b"

for model in $MODELS; do
  for task in $TASKS; do
    # Baseline
    python src/run_inference.py --task $task --model $model
    python src/run_evaluation.py --input output/$model/$task/baseline_inference.json

    # Caution A
    python src/run_inference.py --task $task --model $model --caution-a
    python src/run_evaluation.py --input output/$model/$task/caution_a_inference.json

    # Caution B
    python src/run_inference.py --task $task --model $model --caution-b
    python src/run_evaluation.py --input output/$model/$task/caution_b_inference.json
  done
done

echo "Experiment complete! Check output/ for results."
```

---

## Output Files

### File Naming Convention

```
output/{model}/{task}/{condition}_{stage}.json
```

- **model**: `deepseek`, `qwen`, or `gpt`
- **task**: `calendar`, `meeting`, `zebralogic`, or `blocksworld`
- **condition**: `baseline`, `caution_a`, or `caution_b`
- **stage**: `inference`, `evaluation`, or `chunking`

### Example Output Structure

```
output/
├── deepseek/
│   ├── calendar/
│   │   ├── baseline_inference.json      # Reasoning traces
│   │   ├── baseline_evaluation.json     # Accuracy results
│   │   ├── baseline_chunking.json       # Solver-like analysis
│   │   ├── caution_a_inference.json
│   │   ├── caution_a_evaluation.json
│   │   ├── caution_a_chunking.json
│   │   ├── caution_b_inference.json
│   │   ├── caution_b_evaluation.json
│   │   └── caution_b_chunking.json
│   └── meeting/
│       └── ...
├── qwen/
│   └── ...
└── gpt/
    └── ...
```

---

## Progress Tracking

All scripts show live progress:

```
Processing calendar | 45/100 [00:12<00:15, success=42, errors=3]
```

- **45/100**: Processing example 45 of 100
- **00:12<00:15**: 12 seconds elapsed, ~15 remaining
- **success=42**: 42 examples succeeded
- **errors=3**: 3 examples failed

---

## Troubleshooting

### API Key Errors

**Error**: `DEEPSEEK_API_KEY not found`

**Fix**: Add to `.env`:
```bash
DEEPSEEK_API_KEY=sk-your-actual-key-here
```

### Google Cloud Errors

**Error**: `GOOGLE_CLOUD_PROJECT not found`

**Fix**: Add to `.env`:
```bash
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'openai'`

**Fix**: Activate virtual environment:
```bash
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### File Not Found

**Error**: `Problems file not found`

**Fix**: Make sure you're in the repo root:
```bash
cd /path/to/solver-like-behavior-in-llms
python src/run_inference.py ...
```

### Code Execution Timeouts

**Error**: Examples timing out during code execution

**Fix**: Increase timeout:
```bash
python src/run_inference.py --task calendar --model deepseek --timeout 60
```

### Out of Memory

**Error**: OOM errors during inference

**Fix**:
1. Process fewer examples: `--n 50`
2. Reduce max tokens: `--max-tokens 50000`
3. Use smaller model (DeepSeek API instead of local models)

---

## Advanced Usage

### Custom Output Locations

By default, outputs go to `output/{model}/{task}/`. To customize, edit the output path in the scripts.

### Custom Prompts

Prompts are stored in `prompts/`:
- **CSP framing**: `prompts/prefix/universal_csp_prefix_python.txt`
- **Output formats**: `prompts/formats/{task}_output_format.txt`
- **Cautionary**: `prompts/cautionary/universal_cautionary_suffix_{a,b}.txt`
- **Judge**: `prompts/judge/llm_as_judge_for_chunking.txt`

Modify these files to experiment with different prompting strategies.

### Batch Processing

For parallel processing of multiple configurations:

```bash
# Create a batch script
cat > batch_run.sh << 'EOF'
#!/bin/bash
tasks=(calendar meeting)
models=(deepseek qwen)

for task in "${tasks[@]}"; do
  for model in "${models[@]}"; do
    python src/run_inference.py --task $task --model $model --n 20 &
  done
done
wait
echo "All runs complete!"
EOF

chmod +x batch_run.sh
./batch_run.sh
```

---

## Next Steps

After running experiments:

1. **View results**: See `docs/RESULTS.md` for comprehensive result analysis
2. **Understand outputs**: See `docs/OUTPUT_SCHEMA.md` for JSON structure
3. **Read architecture**: See `CLAUDE.md` for design decisions

---

## Quick Reference

| Task | Command |
|------|---------|
| Test 5 examples | `python src/run_inference.py --task calendar --model deepseek --n 5` |
| Full run | `python src/run_inference.py --task calendar --model deepseek` |
| Evaluate | `python src/run_evaluation.py --input output/deepseek/calendar/baseline_inference.json` |
| Chunk reasoning | `python src/run_chunking.py --input output/deepseek/calendar/baseline_inference.json --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt` |
| With caution | `python src/run_inference.py --task calendar --model deepseek --caution-a` |
| Check accuracy | `grep "constraint_based_accuracy" output/deepseek/calendar/baseline_evaluation.json` |

---

*For more details, see the [architecture documentation](../CLAUDE.md) or [output schema](OUTPUT_SCHEMA.md).*
