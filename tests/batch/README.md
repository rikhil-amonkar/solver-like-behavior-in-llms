# Batch Chunking Test

Quick test of batch chunking pipeline with 5 examples.

## Usage

```bash
# From repo root
./tests/batch/run_test.sh output/deepseek/calendar/baseline_execution.json
```

This will:
1. Extract first 5 examples from the execution JSON
2. Run batch chunking on them
3. Output results to `tests/batch/test_chunking.json`

## Manual steps

If you prefer to run manually:

```bash
# 1. Prepare test data
python tests/batch/prepare_test_data.py \
    --input output/deepseek/calendar/baseline_execution.json \
    --output tests/batch/test_execution.json \
    --n 5

# 2. Run batch chunking
python src/run_chunking.py \
    --input tests/batch/test_execution.json \
    --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt

# 3. Inspect results
cat tests/batch/test_chunking.json | jq '.summary'
cat tests/batch/test_chunking.json | jq '.examples[0].chunk_analysis'
```

## Expected output

- **Input**: 5 examples from execution JSON
- **Output**: `test_chunking.json` with:
  - Chunked reasoning traces
  - Token statistics
  - Solver-like vs sound classification
- **Time**: ~1-2 minutes for 5 examples

## Cleanup

```bash
rm tests/batch/test_*.json
```
