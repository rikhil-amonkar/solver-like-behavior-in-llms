# PDDL and BlocksWorld Workflow

This document provides a complete overview of how PDDL and BlocksWorld tasks are handled in this repository, including the evaluation pipeline, data structure, and integration with Cassie Huang's [llm-as-formalizer-constraints](https://github.com/CassieHuang22/llm-as-formalizer-constraints) dataset.

## Table of Contents
- [Overview](#overview)
- [Pipeline Workflow](#pipeline-workflow)
- [Data Structure](#data-structure)
- [Prompt Engineering](#prompt-engineering)
- [Evaluation with VAL](#evaluation-with-val)
- [Comparison with Cassie's Repo](#comparison-with-cassies-repo)
- [Usage Examples](#usage-examples)

---

## Overview

**PDDL (Planning Domain Definition Language)** is a standardized language for describing planning problems. In the context of BlocksWorld, PDDL defines:
- **Domain**: The actions available (pickup, putdown, stack, unstack) and their preconditions/effects
- **Problem**: The objects (blocks), initial state, and goal state

Our pipeline evaluates whether LLMs can:
1. **Formalize constraints** into valid PDDL domain definitions
2. **Generate executable plans** that work with groundtruth problem specifications
3. **Encode additional constraints** (e.g., "Block 1 is fragile") correctly in PDDL

---

## Pipeline Workflow

### 1. **Inference Stage** (`src/run_inference.py`)

**Purpose**: Get model to generate PDDL domain and problem definitions

**Input**:
- Problem description (natural language)
- Groundtruth problem PDDL (for reference - initial/goal states)
- Domain description (what BlocksWorld is)
- Constraint description (e.g., "Block 1 is fragile")

**Output**: JSON with model's PDDL formalization
```json
{
  "domain_file": "(define (domain blocksworld) ...)",
  "problem_file": "(define (problem blocksworld-p01) ...)"
}
```

**Key Features**:
- Prompts include **groundtruth problem PDDL** as reference for correct initial/goal states
- Models must create their own **domain PDDL** that encodes constraints
- Uses PDDL 1.0 syntax (compatible with VAL validator)

### 2. **Execution Stage** (`src/run_execution.py`)

**Purpose**: Extract PDDL, generate plan, validate with VAL

**Process**:
1. Extract `domain_file` and `problem_file` from model output
2. **Replace model's problem with groundtruth problem PDDL**
3. Call online PDDL solver with: `model's domain + groundtruth problem`
4. Generate plan using solver
5. Validate plan with VAL: `model's domain + groundtruth problem + plan`

**Why use groundtruth problem?**
- We want to test if the model's **domain PDDL** correctly encodes constraints
- The groundtruth problem ensures we're testing against the **correct** initial/goal states
- This prevents models from "cheating" by modifying the problem to match their domain

**Output**:
```json
{
  "domain_pddl": "...",
  "problem_pddl": "...",
  "plan": "(pickup block1)\n(stack block1 block2)\n...",
  "plan_found": true,
  "val_valid": true
}
```

### 3. **Evaluation Stage** (`src/run_evaluation.py`)

**Purpose**: Determine if solution is correct

**Evaluation Criteria**:
1. ✅ PDDL syntax is valid (domain and problem extracted)
2. ✅ Domain includes required actions (pickup, putdown, stack, unstack)
3. ✅ Problem has correct structure (objects, init, goal)
4. ✅ Planner found a plan (using model's domain + groundtruth problem)
5. ✅ Plan is valid according to VAL (tested against groundtruth problem)
6. ✅ Constraints are properly encoded (comments like `;; CONSTRAINT` present)

**Validation Pipeline**:
```
Model Domain + Groundtruth Problem → Solver → Plan → VAL Validator → Pass/Fail
```

**Output**: Accuracy metrics and error categorization

---

## Data Structure

### Our Dataset Format (`data/problems/blocksworld_100.json`)

Each problem instance contains:

```json
{
  "blocksworld_p86_initial_constraint6": {
    "problem": "Natural language description with constraint...",
    "golden_solution": {
      "domain_pddl": "Reference domain with constraint encoded...",
      "problem_pddl": "Reference problem PDDL..."
    },
    "groundtruth_problem_pddl": "PDDL from Cassie's repo (correct init/goal)...",
    "domain_description": "General BlocksWorld description...",
    "problem_description": "Specific problem instance description...",
    "action_heads": "(pickup block)\n(putdown block)\n...",
    "plan_exists": true,
    "domain": "blocksworld",
    "problem_id": "p86"
  }
}
```

**Key Fields**:
- `problem`: Full natural language description (includes constraint)
- `golden_solution`: Reference PDDL with constraints properly encoded
- `groundtruth_problem_pddl`: **Cassie's problem PDDL** (correct initial/goal states)
- `domain_description`: General BlocksWorld explanation
- `problem_description`: Specific instance details
- `plan_exists`: Whether a valid plan should exist (for unsolvable instances)

### Why Multiple PDDL Fields?

| Field | Purpose | Used For |
|-------|---------|----------|
| `golden_solution.domain_pddl` | Reference domain with constraints | Constraint validation, semantic checks |
| `golden_solution.problem_pddl` | Reference problem PDDL | Legacy/comparison |
| `groundtruth_problem_pddl` | **Cassie's problem PDDL** | **Plan generation and VAL validation** |

---

## Prompt Engineering

### Universal PDDL Prefix (`prompts/prefix/universal_csp_prefix_pddl.txt`)

The prompt provides models with:

1. **Task Description**: What PDDL is and what they need to do
2. **Groundtruth Problem PDDL**: Reference for correct initial/goal states
3. **Domain Description**: General BlocksWorld overview
4. **Problem Description**: Specific instance details
5. **Full Problem with Constraints**: Natural language description

**Key Insight**: Models see the groundtruth problem PDDL but must create their own domain PDDL that properly encodes the constraint.

### Output Format (`prompts/formats/blocksworld_output_format.txt`)

Specifies the required JSON structure:
```json
{
  "domain_file": "(define (domain blocksworld) ...)",
  "problem_file": "(define (problem blocksworld-p01) ...)"
}
```

**Requirements**:
- Use PDDL 1.0 syntax (VAL-compatible)
- Include `:requirements :strips` at minimum
- Mark constraint modifications with `;; CONSTRAINT` comments
- Output **only** the JSON object (no markdown fences)

---

## Evaluation with VAL

### VAL (Value Analysis Tool)

**Location**: `repos/VAL/build/bin/Validate`

**Purpose**: Validate that a plan is executable given a domain and problem

**Usage in Pipeline**:
```bash
Validate <domain.pddl> <problem.pddl> <plan.txt>
```

### Our Evaluation Approach

**Standard PDDL Evaluation**:
```
Model Domain + Model Problem → Planner → Plan → VAL(Model Domain, Model Problem, Plan)
```
**Problem**: Models could modify the problem to make their domain work

**Our Approach**:
```
Model Domain + Groundtruth Problem → Planner → Plan → VAL(Model Domain, Groundtruth Problem, Plan)
```
**Benefit**: Tests model's domain against the **correct** initial/goal states

### Validation Steps

1. **Syntax Validation**: Check PDDL structure (balanced parentheses, required sections)
2. **Domain Validation**: Verify all required actions are present
3. **Plan Generation**: Use online solver (solver.planning.domains API) with model's domain + groundtruth problem
4. **VAL Validation**: Verify plan executes correctly against groundtruth problem
5. **Constraint Validation**: Check for proper constraint markers and encoding

---

## Comparison with Cassie's Repo

### Dataset Origin

Our BlocksWorld dataset is derived from:
- **Cassie's Repo**: [llm-as-formalizer-constraints](https://github.com/CassieHuang22/llm-as-formalizer-constraints)
- **Original Work**: Based on [Huang and Zhang (2025) - llm-as-pddl-formalizer](https://github.com/CassieHuang22/llm-as-pddl-formalizer)

### Cassie's Repository Structure

```
BlocksWorld-100/
├── descriptions/           # Natural language descriptions
│   ├── p01_domain.txt     # General BlocksWorld description
│   └── p01_problem.txt    # Specific problem instance
├── pddl/                  # Groundtruth PDDL files
│   ├── domain.pddl        # Standard BlocksWorld domain
│   └── p01.pddl           # Problem instance (init + goal)
├── constraints/           # Constraint categories
│   ├── baseline/          # No constraints
│   ├── goal/              # New goal constraints
│   ├── initial/           # Initial state constraints
│   ├── action/            # Action-based constraints
│   └── state/             # State space constraints
└── action_heads/
    └── action_heads.txt   # PDDL action signatures
```

**Each constraint category** contains:
- `descriptions/`: Natural language constraint descriptions
- `pddl/`: Groundtruth domain/problem files with constraints
- `action_heads/`: Modified action signatures

### Key Differences

| Aspect | Cassie's Repo | Our Repo |
|--------|---------------|----------|
| **Purpose** | LLM-as-PDDL-Formalizer research | Solver-like behavior analysis |
| **Data Format** | Separate files per constraint category | Single JSON with all data |
| **Evaluation** | Multi-step revision pipeline | Single-shot with groundtruth reference |
| **Validation** | VAL + custom constraint checking | VAL with groundtruth problem PDDL |
| **Output Format** | Raw PDDL text | JSON with `domain_file`/`problem_file` |
| **Models Tested** | DeepSeek, Qwen (various versions) | DeepSeek, Qwen, GPT-OSS |
| **Focus** | PDDL formalization quality | Reasoning trace analysis (solver-like vs sound) |

### Our Enhancements

1. **Integrated Dataset**: All groundtruth info in a single JSON file
2. **Groundtruth Reference**: Models see correct initial/goal states in prompt
3. **Standardized JSON Output**: Consistent format for parsing
4. **Automated Pipeline**: Single command runs full inference → execution → evaluation
5. **Reasoning Analysis**: Chunking stage analyzes reasoning traces (not in Cassie's repo)

### Accuracy Metrics in Cassie's Work

From their paper (approximate numbers):

| Model | Baseline Accuracy | Action Constraints | State Constraints |
|-------|-------------------|-------------------|-------------------|
| GPT-4 | ~85% | ~65% | ~55% |
| DeepSeek-Reasoner | ~80% | ~60% | ~50% |
| Qwen2.5-Coder-32B | ~75% | ~55% | ~45% |

**Note**: These are approximate numbers for BlocksWorld-100. Actual results vary by constraint type and evaluation criteria.

Our repo focuses on **reasoning trace analysis** rather than pure accuracy optimization, so we track:
- How much reasoning is "solver-like" (tries solutions in natural language)
- How much is "sound" (properly formalizes then solves)

---

## Usage Examples

### Running the Full Pipeline

```bash
# 1. Inference (generate PDDL with DeepSeek)
python src/run_inference.py \
  --task blocksworld \
  --model deepseek \
  --n 10 \
  --output output/deepseek/blocksworld/baseline_inference.jsonl

# 2. Execution (extract PDDL, generate plan, validate with VAL)
python src/run_execution.py \
  --input output/deepseek/blocksworld/baseline_inference.jsonl \
  --output output/deepseek/blocksworld/baseline_execution.jsonl

# 3. Evaluation (check correctness)
python src/run_evaluation.py \
  --input output/deepseek/blocksworld/baseline_execution.jsonl \
  --output output/deepseek/blocksworld/baseline_evaluation.json
```

### Expected Outputs

**After Inference**:
```json
{
  "example_id": "blocksworld_p01_initial_constraint1",
  "full_response": "{\n  \"domain_file\": \"(define (domain blocksworld) ...)\",\n  \"problem_file\": \"...\"\n}",
  "model_metadata": {...}
}
```

**After Execution**:
```json
{
  "example_id": "blocksworld_p01_initial_constraint1",
  "domain_pddl": "(define (domain blocksworld) ...)",
  "problem_pddl": "(define (problem blocksworld-p01) ...)",
  "plan": "(pickup block1)\n(putdown block1)\n...",
  "plan_found": true,
  "val_valid": true,
  "used_online_solver": true
}
```

**After Evaluation**:
```json
{
  "total": 10,
  "passed": 8,
  "failed": 2,
  "accuracy": 0.8,
  "error_breakdown": {
    "pddl_syntax_error": 1,
    "planning_failure": 1
  }
}
```

---

## Technical Details

### PDDL Version
- **Standard**: PDDL 1.0 (compatible with VAL)
- **Requirements**: Minimum `:strips`, can add `:typing`, `:equality`, etc. for constraints

### Planner
- **Default**: Online solver API (`solver.planning.domains`)
- **Solver**: `dual-bfws-ffparser` (fast, supports advanced PDDL features)
- **Timeout**: 60 seconds (configurable)

### VAL Validator
- **Binary**: `repos/VAL/build/bin/Validate`
- **Version**: PDDL 1.0 compatible
- **Timeout**: 10 seconds (configurable)

### Code Locations

| Component | File |
|-----------|------|
| PDDL Executor | `src/inference/code_executor_pddl.py` |
| BlocksWorld Evaluator | `src/evaluation/blocksworld_eval.py` |
| PDDL Prompts | `prompts/prefix/universal_csp_prefix_pddl.txt` |
| Output Format | `prompts/formats/blocksworld_output_format.txt` |
| Dataset | `data/problems/blocksworld_100.json` |

---

## Future Enhancements

Potential improvements to the pipeline:

1. **Local Planner Support**: Add Fast Downward or pyperplan for offline planning
2. **Constraint Categories**: Separate baseline/action/state/goal/initial like Cassie's repo
3. **Multi-Step Revision**: Implement iterative refinement pipeline
4. **Richer Metrics**: Track constraint-specific accuracy (fragile blocks, max stacks, etc.)
5. **Plan Quality**: Measure plan optimality (length, makespan)
6. **Semantic Validation**: More rigorous constraint encoding checks

---

## References

- **Cassie's Repository**: https://github.com/CassieHuang22/llm-as-formalizer-constraints
- **Original PDDL Formalizer Work**: https://github.com/CassieHuang22/llm-as-pddl-formalizer
- **VAL Validator**: https://github.com/KCL-Planning/VAL
- **PDDL Specification**: https://planning.wiki/ref/pddl
- **Online Solver**: https://solver.planning.domains

---

## Quick Reference

### Key Concepts

- **Domain PDDL**: Defines actions and their preconditions/effects (what the model must create)
- **Problem PDDL**: Defines objects, initial state, goal state (provided as groundtruth reference)
- **Plan**: Sequence of actions to achieve the goal
- **VAL**: Validator that checks if a plan is executable
- **Groundtruth Problem**: Cassie's correct problem PDDL used for evaluation

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Plan not found" | Constraint too restrictive | Check if `plan_exists=false` in dataset |
| "VAL validation failed" | Domain doesn't match problem | Verify constraint encoding in domain |
| "JSON parsing error" | Model output not valid JSON | Check model's response format |
| "Missing action" | Constraint removed required action | Verify all 4 actions present (or document removal) |

---

**Last Updated**: 2026-08-26
**Maintainer**: See `CLAUDE.md` for development guidelines
