# Solver-Like Behavior In LLMs

This repository supports a research project investigating solver-like behavior in LLM reasoning chains during formalization tasks, and understand what influences this behavior, as well as how it impacts accuracy.

## Overview

This research pipeline analyzes how LLMs approach constraint satisfaction problems (CSPs) when asked to formalize and solve them. We track whether models solve problems in natural language reasoning ("solver-like") versus properly formalizing them in code ("sound").

### Pipeline Architecture

![Pipeline Flowchart](images/solver-like-behavior-flowchart.png)

The pipeline consists of five stages, each reading the previous stage's JSON from `output/{model}/{task}/`:

1. **Inference** (`run_inference.py`) → LLM receives a CSP problem and generates a reasoning trace with code
2. **Execution** (`run_execution.py`) → The final-answer code block is extracted and run (Python, Z3, or PDDL via a local Fast Downward planner)
3. **Evaluation** (`run_evaluation.py`) → Outputs are validated against task-specific constraints
4. **Chunking** (`run_chunking.py`) → An LLM judge classifies reasoning into "sound" (formalization) vs "solver-like" (natural language solution) segments
5. **Hardcoded detection** (`run_hardcoded.py`) → An LLM judge labels each program as hardcoded or computational

How each task is scored:
- **Calendar**: the meeting fits the duration and overlaps no busy interval.
- **Meeting Planning**: the itinerary is simulated step by step (start location/time, travel times, each friend's location, window and minimum duration) and must meet at least as many friends as the golden solution.
- **ZebraLogic**: the printed grid matches the golden solution.
- **BlocksWorld**: the plan Fast Downward finds for the model's domain + problem must be valid (VAL) under the golden domain + problem; for the 10 unsolvable instances, the planner must prove the model's PDDL unsolvable. One unsolvable instance (`blocksworld_p03_state_constraint3`) cannot be proven unsolvable within 5 minutes even from the golden PDDL.

### Key Results

![Results Table](images/solver-like-behavior-in-llms-table-results.png)

> The table above uses the previous evaluation. Meeting Planning and BlocksWorld accuracy changed after the evaluation fixes; see [2026-10-21_RESCORED_RESULTS.md](docs/results/2026-10-21_RESCORED_RESULTS.md).

**Key Findings:**
- **Accuracy**: Models achieve 47-99% accuracy across tasks (Calendar highest, BlocksWorld lowest)
- **Solver-like Ratio**: Proportion of reasoning spent solving vs formalizing (0.05-0.64)
- **Cautionary Prompts**: Anti-solver prompts (CautA, CautB) have mixed effects—sometimes improve accuracy (DeepSeek Calendar: 0.93→0.99), sometimes degrade (all models on BlocksWorld)
- **Token Efficiency**: Average reasoning tokens range from 130 (ZebraLogic) to 12,916 (Meeting)

---

## Quick Start

### 1. Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Build Fast Downward and VAL into repos/ (needed for BlocksWorld)
scripts/setup_planners.sh

# Configure API keys and token limits
cp .env.example .env
```

### 2. Run Pipeline

```bash
# Stage 1: Inference
python src/run_inference.py --task calendar --model deepseek --n 10

# Stage 2: Execution (extract and run code)
python src/run_execution.py --input output/deepseek/calendar/baseline_inference.json

# Stage 3: Evaluation (check constraints)
python src/run_evaluation.py --input output/deepseek/calendar/baseline_execution.json

# Stage 4: Chunking (classify reasoning)
python src/run_chunking.py \
  --input output/deepseek/calendar/baseline_execution.json \
  --judge-prompt prompts/judge/llm_as_judge_for_chunking.txt
```

Local models (Qwen, GPT-OSS) run with vLLM. `scripts/run_inference_gpu7.sh` starts `run_inference.py` on GPU 7 in a detached tmux session with a log in `logs/`; pass `--output-root output_test` for test runs so the stored results in `output/` are not overwritten.

### 3. View Results

```bash
# Results are in output/{model}/{task}/{condition}_{stage}.json
ls output/deepseek/calendar/
# → baseline_inference.json baseline_execution.json baseline_evaluation.json baseline_chunking.json ...
```

---

## Features

✅ **Clean, modular architecture** - DRY principles, no duplicated logic
✅ **Incremental JSON writing** - Memory-efficient processing of large datasets
✅ **Progress visualization** - Live progress bars with success/error counts
✅ **Fail-safe error handling** - Continue on errors, track failures
✅ **Task-specific validation** - Calendar scheduling & meeting planning constraints
✅ **Vertex AI integration** - Gemini judge for reasoning classification
✅ **Token counting** - Precise metrics using tiktoken

---

## Documentation

- **[USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - ⚡ Quick start and complete usage guide (start here!)
- **[RESULTS.md](docs/RESULTS.md)** - Comprehensive experimental results across models and tasks
- **[OUTPUT_SCHEMA.md](docs/guides/OUTPUT_SCHEMA.md)** - JSON output format specification
- **[CAUTIONARY_SUFFIX.md](docs/guides/CAUTIONARY_SUFFIX.md)** - Baseline vs caution condition comparison
- **[PROMPT_ARCHITECTURE.md](prompts/PROMPT_ARCHITECTURE.md)** - How prompts are assembled

---

## Models Supported

- **DeepSeek-V4-Flash** (API) - Reasoning via `thinking` + `reasoning_effort`
- **Qwen3.8-27B** (Local, vLLM) - Thinking mode via the chat template
- **GPT-OSS-120B** (Local, vLLM) - Reasoning via `reasoning_effort`

---

## Tasks Supported

- **Calendar Scheduling** - Find meeting time for multiple participants
- **Meeting Planning** - Build consistent itinerary with travel/waiting
- **ZebraLogic** - Logic grid puzzles solved with Z3
- **BlocksWorld** - Classical planning in PDDL

---

## Project Structure

```
.
├── src/
│   ├── run_inference.py      # Stage 1: Model inference
│   ├── run_evaluation.py     # Stage 2: Constraint validation
│   ├── run_chunking.py       # Stage 3: Reasoning classification
│   ├── general/              # Shared utilities (I/O, prompts, parsing, CLI)
│   ├── inference/            # Model calling, code execution
│   ├── evaluation/           # Task-specific constraint checking
│   └── chunking/             # Judge calling, chunk parsing
├── data/
│   ├── problems/             # Problem datasets (100 examples each)
│   └── constraints/          # Constraint definitions for evaluation
├── prompts/                  # Prompt templates (CSP framing, output formats, judge)
├── output/                   # Pipeline outputs (organized by model/task)
└── docs/                     # Documentation
```

---

## Example Output

```bash
$ python src/run_inference.py --task calendar --model deepseek --n 5

=== Inference Pipeline ===
Task: calendar
Model: deepseek
Examples: 5

Loading problems...
Loaded 5 examples
Loading prompts...
Prompts loaded
Output: output/deepseek/calendar/inference.json

Processing calendar | 5/5 [00:23<00:00, success=5, errors=0]

✓ Inference complete!
  Success: 5/5
  Errors: 0/5
  Output: output/deepseek/calendar/inference.json
```

---

## Requirements

- Python 3.10+
- DeepSeek API key (for DeepSeek model)
- Google Cloud project with Vertex AI enabled (for judge)
- Fast Downward and VAL (built by `scripts/setup_planners.sh`, for BlocksWorld)
- Optional: GPU for local models (Qwen, GPT-OSS)

---

## Authors

[ANONYMOUS AUTHORS]

## Advisors

[ANONYMOUS ADVISORS]

## License

This project is licensed under the terms in `LICENSE`.

