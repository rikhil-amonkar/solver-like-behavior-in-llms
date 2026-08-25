# Judge Tests

This directory contains tests for evaluating different models as judges of reasoning chunks.

## Overview

The judge tests evaluate how well different LLMs can classify reasoning chunks as "sound" (formalization-focused) vs "solver-like" (solving in natural language).

## Dataset

`reasoning_chunks_dataset.json` contains 20 unlabeled reasoning chunks from calendar and meeting planning tasks, extracted from various models' reasoning traces.

Each chunk includes:
- `chunk_id`: Unique identifier (1-20)
- `dataset`: Task type (calendar or meeting)
- `model`: Source model (deepseek-reasoner, qwen3-32b, qwen2.5-32b-instruct, gpt-oss-120b)
- `example_id`: Original example identifier
- `chunk_index`: Position in original trace
- `token_count`: Number of tokens in chunk
- `reasoning_chunk`: The actual reasoning text

## Judge Models

Four models are tested as judges:

1. **Gemini-2.5-Pro** (API-based via Vertex AI)
2. **DeepSeek-V4-Flash** (API-based via DeepSeek API)
3. **Qwen3.8-27B** (Local HuggingFace)
4. **GPT-OSS-120B** (Local HuggingFace)

All scripts use the repository's existing model calling infrastructure from `src/models/`.

## Prompts

Two judge prompts are available:

1. **`boolean_judge_prompt.txt`** - Simplified prompt requesting a single boolean output (`solver_like: true/false`)
2. **`prompts/judge/llm_as_judge_for_chunking.txt`** - Original detailed prompt with chunk analysis (located in main prompts directory)

The boolean prompt is recommended for cleaner outputs and easier parsing.

## Usage

### Run DeepSeek Judge

```bash
python tests/judge/run_deepseek_judge.py --prompt tests/judge/boolean_judge_prompt.txt
```

### Run Gemini Judge

```bash
python tests/judge/run_gemini_judge.py --prompt tests/judge/boolean_judge_prompt.txt
```

### Run Qwen Judge

```bash
python tests/judge/run_qwen_judge.py --prompt tests/judge/boolean_judge_prompt.txt
```

### Run GPT-OSS Judge

```bash
python tests/judge/run_gpt_judge.py --prompt tests/judge/boolean_judge_prompt.txt
```

### Custom Dataset or Output

All scripts support optional arguments:

```bash
python tests/judge/run_deepseek_judge.py \
  --prompt tests/judge/boolean_judge_prompt.txt \
  --dataset tests/judge/reasoning_chunks_dataset.json \
  --output tests/judge/judge_results.md
```

## Output

Results are written to `judge_results.md` in this directory. Each judge run appends its results to the file with:

- Timestamp
- Summary statistics (sound, solver-like, errors)
- Detailed results table

Multiple judge runs (from different models) are separated by horizontal rules in the markdown file.

## Classification Logic

### Boolean Prompt (Recommended)

Each judge returns a JSON object with `solver_like` boolean:
- `true` → "solver-like" classification
- `false` → "sound" classification

### Original Detailed Prompt

Returns `chunk_analysis` array with labeled sub-chunks:
1. Count "sound" vs "solver-like" sub-chunks
2. Classify overall chunk based on majority
3. Default to "solver-like" if tied but contains any solver chunks

## File Structure

```
tests/judge/
├── README.md                          # This file
├── reasoning_chunks_dataset.json     # Test dataset (20 chunks)
├── boolean_judge_prompt.txt          # Simplified boolean judge prompt
├── run_deepseek_judge.py             # DeepSeek judge script
├── run_gemini_judge.py               # Gemini judge script
├── run_qwen_judge.py                 # Qwen judge script
├── run_gpt_judge.py                  # GPT-OSS judge script
└── judge_results.md                  # Output file (created on first run)
```

## Model Calling Infrastructure

All judge scripts use the repository's existing model callers:

- **DeepSeek**: `src/models/call_deepseek.py` (OpenAI SDK with reasoning_effort)
- **Gemini**: `src/chunking/judge_caller.py` (Vertex AI)
- **Qwen**: `src/models/call_qwen.py` (Transformers with enable_thinking)
- **GPT-OSS**: `src/models/call_gpt_oss.py` (Transformers with reasoning_effort)

This ensures consistency with the main inference pipeline.

## Notes

- DeepSeek and Gemini require API credentials (see `.env` for DEEPSEEK_API_KEY and Vertex AI setup)
- Qwen and GPT-OSS require local GPU resources
- All scripts use a unified parsing function for boolean outputs
- Results append to the same markdown file for easy comparison across judges
