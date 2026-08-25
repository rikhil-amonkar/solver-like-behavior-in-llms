# Pipeline Output JSON Schemas

This document defines the expected JSON structure for each pipeline stage.

---

## 1. Inference Output (`output/{model}/{task}/inference.json`)

**Purpose**: Contains reasoning traces, extracted code, and execution results for each problem.

```json
{
  "run_metadata": {
    "task": "calendar",
    "model": "deepseek",
    "model_id": "deepseek-v4-flash",
    "condition": "baseline",
    "cautionary_suffix_enabled": false,
    "timestamp": "2026-08-18T18:30:00Z",
    "num_examples": 100,
    "max_tokens": 32768,
    "reasoning_enabled": true
  },
  "examples": [
    {
      "example_id": "calendar_scheduling_example_543",
      "problem_text": "You need to schedule a meeting for James and John...",

      "reasoning_trace": "This is a constraint satisfaction problem. We need to find...",
      "reasoning_before_code": "This is a constraint satisfaction problem...",
      "extracted_code": "def solve():\n    # code here\n    return ['Monday', '13:30', '14:30']\n\nprint(solve())",

      "code_execution": {
        "ran": true,
        "exit_code": 0,
        "stdout": "['Monday', '13:30', '14:30']\n",
        "stderr": "",
        "timed_out": false,
        "timeout_sec": 30.0,
        "error": null,
        "parsed_output": ["Monday", "13:30", "14:30"]
      },

      "model_metadata": {
        "model": "deepseek-v4-flash",
        "max_tokens": 32768,
        "reasoning_effort": "medium",
        "completion_tokens": 1523,
        "prompt_tokens": 412
      }
    }
  ]
}
```

### Key Fields:

- **`run_metadata`**: Information about the inference run
  - `task`: Task name (calendar, meeting)
  - `model`: Short model name (deepseek, qwen, gpt)
  - `model_id`: Full model identifier
  - `timestamp`: ISO 8601 timestamp
  - `num_examples`: Number of examples processed
  - `max_tokens`: Max tokens used for generation
  - `reasoning_enabled`: Whether reasoning/thinking was enabled

- **`examples`**: Array of results, one per problem
  - `example_id`: Unique identifier from problem JSON
  - `problem_text`: The problem given to the model
  - `reasoning_trace`: Full model output (raw)
  - `reasoning_before_code`: Text before first code block (for judge)
  - `extracted_code`: Python code extracted from fenced block
  - `code_execution`: Results from running the code
    - `ran`: Whether execution was attempted
    - `exit_code`: Process exit code (0 = success)
    - `stdout`/`stderr`: Output streams
    - `timed_out`: Whether execution exceeded timeout
    - `error`: Error message if any
    - `parsed_output`: Parsed result (via ast.literal_eval)
  - `model_metadata`: Token counts and model settings

---

## 2. Evaluation Output (`output/{model}/{task}/evaluation.json`)

**Purpose**: Validates code outputs against task constraints and computes accuracy.

```json
{
  "run_metadata": {
    "task": "calendar",
    "model": "deepseek",
    "inference_json": "output/deepseek/calendar/inference.json",
    "constraints_json": "data/constraints/calendar_scheduling_constraints.json",
    "timestamp": "2026-08-18T18:45:00Z",
    "num_examples": 100
  },

  "accuracy_summary": {
    "total": 100,
    "correct": 87,
    "incorrect": 13,
    "accuracy": 0.87,
    "error_breakdown": {
      "code_execution_failed": 3,
      "code_not_extracted": 2,
      "constraint_violation": 5,
      "parse_error": 3
    }
  },

  "examples": [
    {
      "example_id": "calendar_scheduling_example_543",
      "correct": true,
      "classification": "correct",

      "solution": ["Monday", "13:30", "14:30"],

      "constraints": {
        "meeting_duration": 1.0,
        "disallowed_ranges": [
          {"day": "Monday", "start": 11.5, "end": 12.0},
          {"day": "Monday", "start": 14.5, "end": 15.0}
        ]
      },

      "validation": {
        "shape_valid": true,
        "duration_valid": true,
        "no_conflicts": true,
        "error_detail": null
      }
    },
    {
      "example_id": "calendar_scheduling_example_544",
      "correct": false,
      "classification": "constraint_violation",

      "solution": ["Monday", "14:00", "15:00"],

      "constraints": {
        "meeting_duration": 1.0,
        "disallowed_ranges": [
          {"day": "Monday", "start": 14.5, "end": 15.0}
        ]
      },

      "validation": {
        "shape_valid": true,
        "duration_valid": true,
        "no_conflicts": false,
        "error_detail": {
          "disallowed_overlap": {"day": "Monday", "start": 14.5, "end": 15.0}
        }
      }
    }
  ]
}
```

### Key Fields:

- **`run_metadata`**: Evaluation run information
  - `inference_json`: Path to input inference JSON
  - `constraints_json`: Path to constraints file used

- **`accuracy_summary`**: Aggregate statistics
  - `total`: Total examples evaluated
  - `correct`: Number passing all constraints
  - `incorrect`: Number failing
  - `accuracy`: Fraction correct (0.0 to 1.0)
  - `error_breakdown`: Counts by error type

- **`examples`**: Per-example results
  - `example_id`: Matches inference JSON
  - `correct`: Boolean pass/fail
  - `classification`: Error category or "correct"
  - `solution`: Parsed output from code execution
  - `constraints`: Constraints checked for this example
  - `validation`: Detailed validation results
    - Task-specific checks (shape, duration, conflicts, etc.)
    - `error_detail`: Specifics of what failed

---

## 3. Chunking Output (`output/{model}/{task}/chunking.json`)

**Purpose**: Judge model classification of reasoning into "sound" vs "solver-like" chunks.

```json
{
  "run_metadata": {
    "task": "calendar",
    "model": "deepseek",
    "inference_json": "output/deepseek/calendar/inference.json",
    "judge_model": "publishers/google/models/gemini-2.5-pro",
    "judge_prompt": "prompts/judge/llm_as_judge_for_chunking.txt",
    "timestamp": "2026-08-18T19:00:00Z",
    "num_examples": 100,
    "max_judge_tokens": 65536
  },

  "summary_statistics": {
    "total_examples": 100,
    "examples_with_solver_like": 34,
    "examples_sound_only": 66,
    "avg_reasoning_tokens": 1247,
    "avg_solver_like_tokens": 312,
    "avg_sound_tokens": 935,
    "total_chunks": 423
  },

  "examples": [
    {
      "example_id": "calendar_scheduling_example_543",
      "reasoning_before_code": "This is a constraint satisfaction problem. We need to identify the decision variables, constraints, and objective. The decision variable is the meeting time. James is busy from 11:30-12:00 (11.5-12.0 hours) and 14:30-15:00 (14.5-15.0 hours). John is busy from 9:30-11:00, 11:30-12:00, 12:30-13:30, and 14:30-16:30. Computing the free windows: James is free 9:00-11:30, 12:00-14:30, 15:00-17:00. Now I'll implement this in Python using a constraint solver approach.",

      "judge_response": {
        "chunk_analysis": [
          {
            "sound": "This is a constraint satisfaction problem. We need to identify the decision variables, constraints, and objective. The decision variable is the meeting time."
          },
          {
            "solver-like": "James is busy from 11:30-12:00 (11.5-12.0 hours) and 14:30-15:00 (14.5-15.0 hours). John is busy from 9:30-11:00, 11:30-12:00, 12:30-13:30, and 14:30-16:30. Computing the free windows: James is free 9:00-11:30, 12:00-14:30, 15:00-17:00."
          },
          {
            "sound": "Now I'll implement this in Python using a constraint solver approach."
          }
        ]
      },

      "enriched_chunk_analysis": [
        {
          "sound": "This is a constraint satisfaction problem. We need to identify the decision variables, constraints, and objective. The decision variable is the meeting time.",
          "tokens": 87
        },
        {
          "solver-like": "James is busy from 11:30-12:00 (11.5-12.0 hours) and 14:30-15:00 (14.5-15.0 hours). John is busy from 9:30-11:00, 11:30-12:00, 12:30-13:30, and 14:30-16:30. Computing the free windows: James is free 9:00-11:30, 12:00-14:30, 15:00-17:00.",
          "tokens": 156
        },
        {
          "sound": "Now I'll implement this in Python using a constraint solver approach.",
          "tokens": 23
        }
      ],

      "token_statistics": {
        "encoding": "cl100k_base",
        "reasoning_total_tokens": 266,
        "solver_like_total_tokens": 156,
        "sound_total_tokens": 110,
        "solver_like_fraction": 0.586
      },

      "has_solver_like": true,

      "judge_metadata": {
        "model": "publishers/google/models/gemini-2.5-pro",
        "temperature": 0.0,
        "max_output_tokens": 65536,
        "finish_reason": "STOP"
      }
    },
    {
      "example_id": "calendar_scheduling_example_544",
      "reasoning_before_code": "I need to formalize this scheduling problem. Variables: meeting_start (time), Constraints: meeting_start + duration <= 17:00, meeting_start >= 9:00, for each person p: meeting overlaps no busy time in p.schedule.",

      "judge_response": {
        "chunk_analysis": [
          {
            "sound": "I need to formalize this scheduling problem. Variables: meeting_start (time), Constraints: meeting_start + duration <= 17:00, meeting_start >= 9:00, for each person p: meeting overlaps no busy time in p.schedule."
          }
        ]
      },

      "enriched_chunk_analysis": [
        {
          "sound": "I need to formalize this scheduling problem. Variables: meeting_start (time), Constraints: meeting_start + duration <= 17:00, meeting_start >= 9:00, for each person p: meeting overlaps no busy time in p.schedule.",
          "tokens": 142
        }
      ],

      "token_statistics": {
        "encoding": "cl100k_base",
        "reasoning_total_tokens": 142,
        "solver_like_total_tokens": 0,
        "sound_total_tokens": 142,
        "solver_like_fraction": 0.0
      },

      "has_solver_like": false,

      "judge_metadata": {
        "model": "publishers/google/models/gemini-2.5-pro",
        "temperature": 0.0,
        "max_output_tokens": 65536,
        "finish_reason": "STOP"
      }
    }
  ]
}
```

### Key Fields:

- **`run_metadata`**: Chunking run information
  - `inference_json`: Path to input inference JSON
  - `judge_model`: Full Gemini model identifier
  - `judge_prompt`: Path to judge prompt file used
  - `max_judge_tokens`: Token limit for judge outputs

- **`summary_statistics`**: Aggregate analysis
  - `total_examples`: Examples processed
  - `examples_with_solver_like`: Count with any solver-like chunks
  - `examples_sound_only`: Count with only sound reasoning
  - Token averages and totals
  - `total_chunks`: Sum of all chunks across examples

- **`examples`**: Per-example chunking results
  - `example_id`: Matches inference JSON
  - `reasoning_before_code`: Input to judge (from inference)
  - `judge_response`: Raw judge output (only `chunk_analysis`)
    - `chunk_analysis`: Array of chunks in order
      - Each element is an object with exactly one key: `"sound"` or `"solver-like"`
      - Value is verbatim excerpt from reasoning trace
      - Concatenating all chunks reproduces `reasoning_before_code` exactly
  - `enriched_chunk_analysis`: Chunks with token counts added
    - Same structure as `chunk_analysis` but with `tokens` field added
  - `token_statistics`: Aggregated token metrics
    - `encoding`: Tokenizer used (cl100k_base for Gemini)
    - Token counts per category
    - `solver_like_fraction`: Ratio of solver-like to total
  - `has_solver_like`: Boolean - true if any chunk is solver-like
  - `judge_metadata`: Model settings and finish reason

---

## Design Principles

1. **Self-contained**: Each JSON includes run metadata for reproducibility
2. **Traceable**: `example_id` links results across all three stages
3. **Hierarchical**: Run-level metadata + example-level details
4. **Detailed errors**: Error fields capture what went wrong and why
5. **Statistics**: Summary stats at both run and example levels
6. **Metadata**: Model settings, timestamps, paths preserved

---

## File Paths

```
output/
├── deepseek/
│   ├── calendar/
│   │   ├── inference.json      # Stage 1 output
│   │   ├── evaluation.json     # Stage 2 output
│   │   └── chunking.json       # Stage 3 output
│   └── meeting/
│       └── ...
├── qwen/
│   └── ...
└── gpt/
    └── ...
```

Each stage reads the previous stage's JSON and adds its own analysis.
