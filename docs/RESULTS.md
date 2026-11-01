# Comprehensive Results Summary

> **Legacy.** This document describes the earlier pipeline with the Gemini sound / solver-like chunking judge. The current pipeline (SLB ontology judges, cross-FL and deterrence runs) is described in the [README](../README.md).

This document provides a complete overview of model performance across all tasks, prompt conditions, and evaluation metrics.

**Dataset**: 100 examples per task
**Models**: DeepSeek-V4-Flash, GPT-OSS-120B, Qwen3.8-27B
**Tasks**: Calendar Scheduling, Meeting Planning, ZebraLogic Grid Puzzles, BlocksWorld (PDDL)
**Conditions**: Baseline, Caution A (anti-solver prompt), Caution B (stronger anti-solver prompt)

---

## Executive Summary

### Key Findings

1. **Task Difficulty**: Calendar (93-99% accuracy) and ZebraLogic (55-96%) show highest and most variable performance
2. **Model Performance**: DeepSeek consistently strongest across tasks; GPT-OSS best on Calendar/Meeting; Qwen struggles with ZebraLogic
3. **Cautionary Prompts**: Mixed effects - sometimes improve accuracy (DeepSeek Calendar: 93%→99%), sometimes degrade (GPT BlocksWorld: 55%→47%)
4. **Solver-like Behavior**: GPT shows highest baseline solver-like reasoning (50-56% on Calendar/Meeting), reduced significantly by cautionary prompts

---

## Results by Task

### Calendar Scheduling

**Task**: Find meeting time for multiple participants given availability constraints

#### Accuracy (Constraint-Based)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.93 | 0.99 | **+0.06** | 0.97 | +0.04 |
| GPT-OSS | 0.98 | 0.97 | -0.01 | 0.97 | -0.01 |
| Qwen | 0.94 | 0.96 | +0.02 | 0.92 | **-0.02** |

#### Solver-like Fraction (Average)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.253 | 0.260 | +0.007 | 0.270 | +0.017 |
| GPT-OSS | 0.503 | 0.325 | **-0.177** | 0.270 | **-0.233** |
| Qwen | 0.284 | 0.239 | -0.045 | 0.095 | **-0.189** |

**Observations**:
- GPT shows highest baseline solver-like behavior (50%), dramatically reduced by cautionary prompts
- DeepSeek maintains low solver-like fraction (~25%) but gains accuracy with cautionary prompts
- Qwen's accuracy drops with Caution B despite reduced solver-like reasoning

---

### Meeting Planning

**Task**: Build valid itinerary satisfying travel time and location constraints

#### Accuracy (Constraint-Based)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.90 | 0.92 | +0.02 | 0.92 | +0.02 |
| GPT-OSS | 0.93 | 0.93 | 0.00 | 0.90 | -0.03 |
| Qwen | 0.89 | 0.79 | **-0.10** | 0.83 | -0.06 |

#### Solver-like Fraction (Average)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.370 | 0.305 | -0.065 | 0.309 | -0.061 |
| GPT-OSS | 0.561 | 0.374 | **-0.187** | 0.314 | **-0.247** |
| Qwen | 0.435 | 0.354 | -0.081 | 0.403 | -0.032 |

**Observations**:
- Most complex task (lowest overall accuracy)
- GPT again shows highest solver-like baseline, significant reduction with prompts
- Qwen accuracy degrades substantially with Caution A (-10%)
- DeepSeek shows modest but consistent gains with cautionary prompts

---

### ZebraLogic Grid Puzzles

**Task**: Logic grid puzzles (e.g., "who owns the zebra?") with deductive constraints

#### Accuracy (Golden Solution Match)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.94 | 0.94 | 0.00 | 0.96 | +0.02 |
| GPT-OSS | 0.84 | 0.87 | +0.03 | 0.85 | +0.01 |
| Qwen | 0.57 | 0.55 | -0.02 | 0.55 | -0.02 |

#### Solver-like Fraction (Average)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.299 | 0.230 | -0.069 | 0.335 | +0.036 |
| GPT-OSS | 0.200 | 0.194 | -0.006 | 0.083 | **-0.117** |
| Qwen | 0.272 | 0.205 | -0.067 | 0.252 | -0.020 |

**Observations**:
- Wide performance gap: DeepSeek (94%) vs Qwen (57%)
- Lowest solver-like fractions across all models (~20-30%)
- GPT shows modest accuracy gains with cautionary prompts
- Qwen struggles significantly with this task type

---

### BlocksWorld (PDDL Planning)

**Task**: PDDL formalization and planning with blocksworld domain

#### Accuracy (Plan Validation)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.78 | 0.72 | -0.06 | 0.69 | **-0.09** |
| GPT-OSS | 0.55 | 0.59 | +0.04 | 0.47 | **-0.08** |
| Qwen | 0.72 | 0.65 | -0.07 | 0.62 | **-0.10** |

#### Solver-like Fraction (Average)

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| DeepSeek | 0.087 | 0.062 | -0.025 | 0.105 | +0.018 |
| GPT-OSS | 0.231 | 0.176 | -0.055 | 0.182 | -0.049 |
| Qwen | 0.064 | 0.082 | +0.018 | 0.080 | +0.016 |

**Observations**:
- Most challenging task (47-78% accuracy)
- Cautionary prompts generally **degrade** performance across all models
- Lowest solver-like fractions overall (~6-23%)
- PDDL formalization appears less susceptible to solver-like shortcuts

---

## Cross-Task Analysis

### Model Rankings by Task

| Task | 1st Place | 2nd Place | 3rd Place |
|------|-----------|-----------|-----------|
| Calendar | GPT-OSS (0.98) | DeepSeek (0.93-0.99) | Qwen (0.92-0.96) |
| Meeting | GPT-OSS (0.93) | DeepSeek (0.90-0.92) | Qwen (0.79-0.89) |
| ZebraLogic | DeepSeek (0.94-0.96) | GPT-OSS (0.84-0.87) | Qwen (0.55-0.57) |
| BlocksWorld | DeepSeek (0.69-0.78) | Qwen (0.62-0.72) | GPT-OSS (0.47-0.59) |

### Cautionary Prompt Effects

**When Prompts Help (Accuracy Gain ≥ +2%)**:
- DeepSeek Calendar: +6% (Caution A), +4% (Caution B)
- GPT-OSS ZebraLogic: +3% (Caution A)
- GPT-OSS BlocksWorld: +4% (Caution A)

**When Prompts Hurt (Accuracy Loss ≥ -5%)**:
- Qwen Meeting: -10% (Caution A), -6% (Caution B)
- DeepSeek BlocksWorld: -6% (Caution A), -9% (Caution B)
- GPT-OSS BlocksWorld: -8% (Caution B)
- Qwen BlocksWorld: -7% (Caution A), -10% (Caution B)

### Solver-like Behavior Patterns

**High Baseline Solver-like Reasoning (>40%)**:
- GPT-OSS: Calendar (50%), Meeting (56%)
- Qwen: Meeting (44%)

**Low Baseline Solver-like Reasoning (<15%)**:
- All models on BlocksWorld (6-23%)
- DeepSeek on Calendar (25%)

**Largest Reductions from Cautionary Prompts**:
- GPT-OSS Calendar: -23.3 percentage points (Caution B)
- GPT-OSS Meeting: -24.7 percentage points (Caution B)
- Qwen Calendar: -18.9 percentage points (Caution B)

---

## Methodology Notes

### Accuracy Metrics

- **Calendar/Meeting**: Constraint-based validation (checks all problem constraints satisfied)
- **ZebraLogic**: Golden solution match (exact match with reference solution)
- **BlocksWorld**: PDDL plan validation (VAL validator against groundtruth problem)

### Solver-like Fraction

- Proportion of reasoning tokens spent solving the problem in natural language vs. formalizing it in code
- Measured via Gemini-2.5-Pro judge chunking reasoning traces
- Range: 0.0 (fully sound formalization) to 1.0 (fully solver-like)

### Cautionary Prompts

- **Caution A**: Mild anti-solver prompt ("formalize first, then solve")
- **Caution B**: Strong anti-solver prompt ("do not attempt natural language solution")
- See `docs/CAUTIONARY_SUFFIX.md` for full prompt text

---

## Research Implications

1. **Task Type Matters**: Cautionary prompts help on simpler CSPs (Calendar) but hurt on complex planning (BlocksWorld)

2. **Model-Specific Effects**: GPT shows highest solver-like behavior but also largest reductions from prompts; DeepSeek maintains low solver-like behavior across conditions

3. **Accuracy-Behavior Trade-off**: Reducing solver-like reasoning doesn't always improve accuracy (see Qwen Meeting, all models BlocksWorld)

4. **Formalization vs. Solution**: Tasks requiring explicit formalization (PDDL) show naturally lower solver-like behavior

---

## Data Availability

All results are derived from JSON files in `output/{model}/{task}/`:
- `{condition}_inference.json` - Model outputs and reasoning traces
- `{condition}_evaluation.json` - Constraint validation results
- `{condition}_chunking.json` - Solver-like behavior analysis

See `docs/OUTPUT_SCHEMA.md` for complete data format specification.

---

*Last updated: 2026-10-09*
