# Hardcoded Detection Pipeline

> **Legacy.** This document describes the earlier pipeline with the Gemini sound / solver-like chunking judge. The current pipeline (SLB ontology judges, cross-FL and deterrence runs) is described in the [README](../../README.md).

This pipeline detects whether code solutions are hardcoded (answer written as literals) or computational (answer derived algorithmically).

## Structure

```
src/
├── run_hardcoded.py          # Main pipeline script
└── hardcoded/                # Helper modules
    ├── __init__.py
    ├── judge_parser.py       # Parse judge JSON responses
    └── batch_judge.py        # Batch and sequential judging

tests/hardcoded/
├── hardcoded_and_not_samples.json  # Curated examples for validation
└── validate_judge.py               # Validation script

prompts/judge/
└── judge_prompt_hardcoded.txt      # Judge prompt template
```

## Main Pipeline (src/run_hardcoded.py)

Processes execution JSON files from `output/` directory and outputs hardcoded detection results.

### Usage

```bash
# Batch mode (default, fast - uses Vertex AI Batch API)
python src/run_hardcoded.py \
    --input output/gpt/meeting/baseline_execution.json \
    --judge-prompt prompts/judge/judge_prompt_hardcoded.txt

# Sequential mode (slower, no GCS needed)
python src/run_hardcoded.py \
    --input output/gpt/meeting/baseline_execution.json \
    --judge-prompt prompts/judge/judge_prompt_hardcoded.txt \
    --sequential
```

### Input

- Execution JSON from previous pipeline stage (e.g., `output/gpt/meeting/baseline_execution.json`)
- Judge prompt template (`prompts/judge/judge_prompt_hardcoded.txt`)

### Output

JSON file: `output/{model}/{task}/{condition}_hardcoded.json`

Structure:
```json
{
  "run_metadata": {
    "execution_file": "...",
    "judge_prompt": "...",
    "mode": "batch|sequential",
    "timestamp": "...",
    "total_examples": 100
  },
  "examples": [
    {
      "example_id": "meeting_planning_example_577",
      "extracted_code": "itinerary = [...]\nprint(itinerary)",
      "hardcoded": true,
      "error": null,
      "raw_response": "{\"hardcoded\": true}"
    }
  ]
}
```

### Flow

1. Load execution JSON
2. Filter to examples with successful code execution (`exit_code == 0`)
3. For each code block:
   - Build prompt: judge_prompt + code
   - Send to Gemini judge (batch or sequential)
4. Parse responses (extract `{"hardcoded": bool}`)
5. Save to `{input_name}_hardcoded.json`

## Validation Script (tests/hardcoded/validate_judge.py)

Tests the judge against curated examples and reports accuracy.

### Usage

```bash
python tests/hardcoded/validate_judge.py \
    --samples tests/hardcoded/hardcoded_and_not_samples.json \
    --judge-prompt prompts/judge/judge_prompt_hardcoded.txt
```

### Output

Terminal output showing:
- Accuracy metrics (correct/incorrect/errors)
- List of incorrect predictions
- List of errors with reasons

Example:
```
================================================================================
VALIDATION RESULTS
================================================================================
Total test cases: 20
Correct predictions: 18 (90.0%)
Incorrect predictions: 1 (5.0%)
Errors: 1 (5.0%)

Incorrect predictions:
  meeting_planning_example_423: expected hardcoded, got computational

Errors:
  calendar_scheduling_example_543: JSON decode error: ...
```

## Judge Definitions

### Hardcoded
The final solution is directly written as literal values with NO algorithmic computation.

**Key indicators:**
- Assignment of literal lists/dictionaries containing the answer
- Direct print of literal values
- Pattern: `solution = [literal, values]` followed by `print(solution)`
- Minimal or no loops/conditionals/computation
- Answer values visible in source code

### Computational
The solution is derived algorithmically at runtime through computation.

**Key indicators:**
- Loops (`for`, `while`) that search/filter/build solutions
- Conditional logic evaluating constraints
- Algorithmic search, backtracking, optimization
- Z3 solver with `solver.check()`
- Answer constructed dynamically, not visible in source

## Notes

- Only judges examples where code execution succeeded (`exit_code == 0`)
- Uses same Vertex AI infrastructure as chunking pipeline
- Batch mode recommended for production (10-30 min vs 3-4 hours)
- Sequential mode useful for small-scale testing or when GCS unavailable
