# Chunking Pipeline Quick Start

> **Legacy.** This document describes the earlier pipeline with the Gemini sound / solver-like chunking judge. The current pipeline (SLB ontology judges, cross-FL and deterrence runs) is described in the [README](../../README.md).

## TL;DR

```bash
# Fast batch mode (10-30 min for 100 examples) - RECOMMENDED
# Set JUDGE_VERTEX_GCS_BUCKET in .env, then:
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt

# Or specify bucket explicitly:
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --gcs-bucket your-batch-bucket

# Slow sequential mode (3-4 hours for 100 examples) - for debugging
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt \
  --sequential
```

## What changed?

The chunking pipeline now defaults to **batch mode** for 10-20x speedup:

| Mode | Time (100 examples) | Requires GCS? | Use case |
|------|---------------------|---------------|----------|
| **Batch** (default) | 10-30 minutes | ✅ Yes | Production, large datasets |
| **Sequential** (`--sequential`) | 3-4 hours | ❌ No | Debugging, small tests |

## Setup for batch mode

1. Create GCS bucket:
   ```bash
   gsutil mb gs://your-batch-bucket
   ```

2. Add to `.env`:
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   JUDGE_VERTEX_GCS_BUCKET=your-batch-bucket
   ```

3. Authenticate:
   ```bash
   gcloud auth application-default login
   ```

## How it works

### Batch mode (parallel processing)
1. Upload all requests to GCS as JSONL
2. Submit Vertex AI batch prediction job
3. Wait 10-30 minutes (automatic polling)
4. Download and parse results
5. Save final chunking JSON

### Sequential mode (one-by-one)
1. Call Gemini API for each example
2. Rate limited to 2.5s between requests
3. Incremental JSON writing
4. Same output format as batch mode

## Output

Both modes produce identical output format:
```json
{
  "run_metadata": {
    "mode": "batch",  // or "sequential"
    "batch_job_name": "...",  // batch mode only
    ...
  },
  "examples": [
    {
      "example_id": "...",
      "chunk_analysis": [...],
      "has_solver_like": true,
      ...
    }
  ],
  "summary": {...}
}
```

## Cost comparison

**Batch mode** is ~50% cheaper than sequential:
- Sequential (online API): ~$7.60 for 100 examples
- Batch (batch API): ~$3.80 for 100 examples

## Troubleshooting

### "GCS bucket required"
Add `--gcs-bucket your-bucket` or use `--sequential` mode.

### "GOOGLE_CLOUD_PROJECT not set"
Add to `.env`: `GOOGLE_CLOUD_PROJECT=your-project-id`

### "Authentication failed"
Run: `gcloud auth application-default login`

## Full documentation

See `docs/BATCH_CHUNKING_GUIDE.md` for complete details.
