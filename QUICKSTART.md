# Quick Start Guide

## Setup (One-Time)

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# venv\Scripts\activate   # On Windows

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Edit `.env` with your credentials:

```bash
# Required for DeepSeek model
DEEPSEEK_API_KEY=sk-your-key-here

# Required for Gemini judge
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Token limits (already configured)
MAX_DEEPSEEK_TOKENS=131072
MAX_JUDGE_TOKENS=65536

# Other settings already configured in .env
```

---

## Running the Pipeline

### Option 1: Quick Test (5 Examples)

Test with just 5 examples to make sure everything works:

```bash
# Step 1: Run inference
python src/run_inference.py --task calendar --model deepseek --n 5

# Step 2: Evaluate results
python src/run_evaluation.py --input output/deepseek/calendar/inference.json

# Step 3: Chunk reasoning
python src/run_chunking.py \
  --input output/deepseek/calendar/inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

### Option 2: Full Run (All 100 Examples)

```bash
# Step 1: Run inference (no --n flag = all examples)
python src/run_inference.py --task calendar --model deepseek

# Step 2: Evaluate
python src/run_evaluation.py --input output/deepseek/calendar/inference.json

# Step 3: Chunk
python src/run_chunking.py \
  --input output/deepseek/calendar/inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

---

## Common Commands

### Different Tasks

```bash
# Calendar scheduling
python src/run_inference.py --task calendar --model deepseek --n 10

# Meeting planning
python src/run_inference.py --task meeting --model deepseek --n 10
```

### Different Models

```bash
# DeepSeek (API - fastest)
python src/run_inference.py --task calendar --model deepseek --n 10

# Qwen (local - requires GPU)
python src/run_inference.py --task calendar --model qwen --n 10

# GPT-OSS (local - requires GPU)
python src/run_inference.py --task calendar --model gpt --n 10
```

### Adjust Parameters

```bash
# More tokens for generation
python src/run_inference.py --task calendar --model deepseek --max-tokens 100000

# Longer code execution timeout
python src/run_inference.py --task calendar --model deepseek --timeout 60

# Specific number of examples
python src/run_inference.py --task calendar --model deepseek --n 50

# Include cautionary suffix variants (for comparative studies)
python src/run_inference.py --task calendar --model deepseek --n 10 --caution-a
python src/run_inference.py --task calendar --model deepseek --n 10 --caution-b
```

---

## Viewing Results

### Check Output Files

```bash
# List output files
ls output/deepseek/calendar/

# View inference results (first few lines)
head -n 50 output/deepseek/calendar/inference.json

# Check evaluation accuracy
grep -A 5 "run_metadata" output/deepseek/calendar/evaluation.json

# See chunking summary
grep -A 10 "run_metadata" output/deepseek/calendar/chunking.json
```

### Verify Progress

During a run, you'll see:
```
Processing calendar | 45/100 [00:12<00:15, success=42, errors=3]
```

This shows:
- **45/100**: Processing example 45 of 100
- **00:12<00:15**: 12 seconds elapsed, 15 seconds remaining
- **success=42**: 42 examples succeeded
- **errors=3**: 3 examples failed

---

## Troubleshooting

### "DEEPSEEK_API_KEY not found"
Add to `.env`:
```bash
DEEPSEEK_API_KEY=sk-your-actual-key
```

### "GOOGLE_CLOUD_PROJECT not found"
Add to `.env`:
```bash
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### Code execution timeouts
Increase timeout:
```bash
python src/run_inference.py --task calendar --model deepseek --timeout 60
```

### Import errors
Make sure you activated the virtual environment:
```bash
source venv/bin/activate
```

### "Problems file not found"
Make sure you're in the repo root:
```bash
cd /path/to/solver-like-behavior-in-llms
python src/run_inference.py ...
```

---

## Full Documentation

For detailed information, see:
- **[docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - Complete usage guide with all options
- **[docs/OUTPUT_SCHEMA.md](docs/OUTPUT_SCHEMA.md)** - JSON output format
- **[CLAUDE.md](CLAUDE.md)** - Architecture and design decisions

---

## Example Workflow

Here's a complete workflow from start to finish:

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Test with 5 examples
python src/run_inference.py --task calendar --model deepseek --n 5

# 3. Check that it worked
ls output/deepseek/calendar/inference.json

# 4. Evaluate
python src/run_evaluation.py --input output/deepseek/calendar/inference.json

# 5. Chunk
python src/run_chunking.py \
  --input output/deepseek/calendar/inference.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt

# 6. View all results
ls output/deepseek/calendar/
# → inference.json  evaluation.json  chunking.json

# 7. If everything looks good, run full dataset
python src/run_inference.py --task calendar --model deepseek
# ... repeat steps 4-5 ...
```

---

## Tips

✅ **Start small**: Always test with `--n 5` before full runs
✅ **Monitor progress**: Watch the progress bar for errors
✅ **Check outputs**: Inspect JSON files after each stage
✅ **Use version control**: Commit before major runs
✅ **Document runs**: Keep notes on which flags you used
