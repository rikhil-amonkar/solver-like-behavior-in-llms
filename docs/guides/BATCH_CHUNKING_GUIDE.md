# Batch Chunking Guide

> **Legacy.** This document describes the earlier pipeline with the Gemini sound / solver-like chunking judge. The current pipeline (SLB ontology judges, cross-FL and deterrence runs) is described in the [README](../../README.md).

## Overview

The chunking pipeline (`src/run_chunking.py`) supports two modes:

**Performance comparison:**
- **Batch mode** (default): ~10-30 minutes for 100 examples via Vertex AI Batch API
- **Sequential mode** (`--sequential` flag): ~3-4 hours for 100 examples with one-by-one API calls

Batch mode is recommended for production workloads. Sequential mode is useful for debugging or when GCS is not available.

## Prerequisites

### For Batch Mode (default)

1. **GCS bucket** for batch I/O:
   ```bash
   gsutil mb -p $GOOGLE_CLOUD_PROJECT gs://your-batch-bucket
   ```

2. **Environment variables** in `.env`:
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   JUDGE_VERTEX_GCS_BUCKET=your-batch-bucket  # Optional, can use --gcs-bucket flag instead
   GOOGLE_CLOUD_LOCATION=us-central1  # Optional, defaults to us-central1
   VERTEX_JUDGE_BATCH_MODEL=publishers/google/models/gemini-2.5-pro  # Optional
   MAX_JUDGE_TOKENS=65536  # Optional
   ```

3. **Google Cloud authentication**:
   ```bash
   gcloud auth application-default login
   gcloud config set project $GOOGLE_CLOUD_PROJECT
   ```

4. **Required Python packages** (already in requirements.txt):
   ```
   google-genai
   google-cloud-storage
   ```

### For Sequential Mode (`--sequential` flag)

Only requires:
- `GOOGLE_CLOUD_PROJECT` in `.env`
- `gcloud auth application-default login`

No GCS bucket needed.

## Usage

### Batch mode (default, recommended)

```bash
# Basic usage (with bucket in .env as JUDGE_VERTEX_GCS_BUCKET)
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt

# Or specify bucket explicitly
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --gcs-bucket your-batch-bucket

# With custom GCS prefix
python src/run_chunking.py \
  --input output/qwen/meeting/caution_a_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --gcs-prefix my-experiments/run-001
```

### Sequential mode (slower, for debugging)

```bash
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --sequential
```

## How it works

### Batch Mode

1. **Prepare requests**: Converts all examples into batch JSONL format
   - Handles splitting long reasoning traces into segments
   - Each segment becomes a separate batch request

2. **Upload to GCS**: Writes request JSONL to `gs://bucket/prefix/input.jsonl`

3. **Submit batch job**: Creates Vertex AI batch prediction job
   - Model: `gemini-2.5-pro` (configurable)
   - Output location: `gs://bucket/prefix/output/`

4. **Poll for completion**: Checks job status every 30 seconds
   - Typical completion time: 10-30 minutes
   - Max wait: 2 hours (configurable)

5. **Download results**: Fetches output JSONL from GCS
   - Handles multiple output shards
   - Maps results back to original examples

6. **Process segments**: Stitches multi-segment responses together

7. **Write output**: Saves final chunking JSON locally

### Sequential Mode

1. **Load examples**: Read execution JSON
2. **Process one-by-one**: For each example:
   - Call Gemini API with reasoning trace
   - Parse judge response
   - Enrich with token counts
3. **Rate limiting**: 2.5s delay between requests
4. **Write output**: Incremental JSON writing for memory efficiency

## Output format

Both modes produce identical output format:

```json
{
  "run_metadata": {
    "task": "calendar",
    "model": "deepseek",
    "condition": "baseline",
    "judge_model": "publishers/google/models/gemini-2.5-pro",
    "batch_job_name": "projects/.../batchPredictionJobs/...",
    "gcs_input": "gs://bucket/prefix/input.jsonl",
    "gcs_output": "gs://bucket/prefix/output/",
    ...
  },
  "examples": [
    {
      "example_id": "...",
      "reasoning_before_code": "...",
      "chunk_analysis": [...],
      "token_statistics": {...},
      "has_solver_like": true,
      "judge_metadata": {...}
    }
  ],
  "summary": {
    "total_examples": 100,
    "examples_with_solver_like": 45,
    "examples_sound_only": 55
  }
}
```

## GCS cleanup

Batch files are kept in GCS for debugging. To clean up:

```bash
# List batch runs
gsutil ls gs://your-batch-bucket/judge-batch/

# Delete specific run
gsutil -m rm -r gs://your-batch-bucket/judge-batch/deepseek/calendar/baseline/20260827_123456/

# Delete all batch data
gsutil -m rm -r gs://your-batch-bucket/judge-batch/
```

## Troubleshooting

### "GOOGLE_CLOUD_PROJECT not set"
Add to `.env`:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
```

### "No API key was provided"
This error is misleading - it means authentication failed. Run:
```bash
gcloud auth application-default login
```

### "Batch job failed"
Check Vertex AI console for detailed error:
```
https://console.cloud.google.com/vertex-ai/batch-predictions?project=YOUR_PROJECT
```

### "No output files found"
Job may have failed silently. Check:
1. Batch job status in console
2. GCS bucket permissions
3. Model ID is correct

### Job timeout
Increase `max_wait` in `run_chunking_batch.py` line 173:
```python
completed_job = poll_batch_job(
    batch_job_name=batch_job.name,
    poll_interval=30,
    max_wait=10800  # 3 hours instead of 2
)
```

## Cost considerations

Batch prediction is ~50% cheaper than online API calls:
- **Online API**: ~$0.000125/1k input tokens, ~$0.000375/1k output tokens (Gemini 2.5 Pro)
- **Batch API**: ~50% discount

Example cost for 100 examples (avg 30k tokens each):
- Input: 100 × 30k = 3M tokens → ~$1.90
- Output: 100 × 10k = 1M tokens → ~$1.90
- **Total: ~$3.80** (vs ~$7.60 for sequential online mode)

## Monitoring

View batch job in Vertex AI console:
```
https://console.cloud.google.com/vertex-ai/batch-predictions?project=YOUR_PROJECT
```

Or use gcloud:
```bash
gcloud ai batch-prediction-jobs list \
  --region=$GOOGLE_CLOUD_LOCATION \
  --project=$GOOGLE_CLOUD_PROJECT
```

## Migration notes

The old sequential-only `run_chunking.py` has been replaced with a unified script supporting both modes:

**Old (sequential only):**
```bash
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

**New (batch by default, sequential with flag):**
```bash
# Batch mode (default, fast)
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --gcs-bucket your-batch-bucket

# Sequential mode (same as old behavior)
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --sequential
```

The old sequential implementation is preserved in `src/run_chunking_sequential.py` for reference.
