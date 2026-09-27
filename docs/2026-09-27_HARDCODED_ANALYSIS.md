# Hardcoded Detection Analysis - 2026-09-27

## Overview

This document analyzes hardcoded vs computational solutions across models, tasks, and prompt conditions.
Hardcoded solutions contain literal answer values with minimal algorithmic computation.
Computational solutions derive answers algorithmically at runtime.

**Key Metrics:**
- **Hardcoded Count**: Number of solutions with hardcoded literal values
- **Hardcoded %**: Percentage of total solutions that are hardcoded
- **Solver-Like Tokens**: Avg tokens spent solving in natural language (from chunking analysis)
- **Accuracy**: Constraint-based accuracy (from evaluation stage)

## Results by Task

### Calendar

**Hardcoded Counts**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0/95 | 0/100 | 0 | 0/99 | 0 |
| GPT-OSS | 0/99 | 0/98 | 0 | 0/98 | 0 |
| Qwen | 0/96 | 0/98 | 0 | 0/95 | 0 |

**Hardcoded Percentage**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| GPT-OSS | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Qwen | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

**Solver-Like Tokens (Avg)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,634 | 1,885 | +251 | 1,775 | +141 |
| GPT-OSS | 641 | 424 | -217 | 322 | -319 |
| Qwen | 944 | 830 | -114 | 281 | -663 |

**Accuracy**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.93 | 0.99 | +0.06 | 0.97 | +0.04 |
| GPT-OSS | 0.98 | 0.97 | -0.01 | 0.97 | -0.01 |
| Qwen | 0.94 | 0.96 | +0.02 | 0.92 | -0.02 |

---

### Meeting

**Hardcoded Counts**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1/94 | 0/93 | -1 | 1/94 | 0 |
| GPT-OSS | 47/93 | 4/93 | -43 | 1/90 | -46 |
| Qwen | 0/92 | 0/81 | 0 | 0/88 | 0 |

**Hardcoded Percentage**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1.1% | 0.0% | -1.1% | 1.1% | 0.0% |
| GPT-OSS | 50.5% | 4.3% | -46.2% | 1.1% | -49.4% |
| Qwen | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

**Solver-Like Tokens (Avg)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 12,915 | 10,990 | -1,925 | 11,015 | -1,900 |
| GPT-OSS | 1,895 | 840 | -1,055 | 592 | -1,303 |
| Qwen | 8,591 | 6,149 | -2,442 | 7,841 | -750 |

**Accuracy**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.90 | 0.92 | +0.02 | 0.92 | +0.02 |
| GPT-OSS | 0.93 | 0.93 | 0.00 | 0.90 | -0.03 |
| Qwen | 0.89 | 0.79 | -0.10 | 0.83 | -0.06 |

---

### Zebralogic

**Hardcoded Counts**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0/94 | 0/98 | 0 | 0/98 | 0 |
| GPT-OSS | 0/88 | 0/92 | 0 | 0/96 | 0 |
| Qwen | 0/60 | 0/57 | 0 | 0/57 | 0 |

**Hardcoded Percentage**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| GPT-OSS | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Qwen | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

**Solver-Like Tokens (Avg)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 3,812 | 3,257 | -555 | 3,695 | -117 |
| GPT-OSS | 420 | 425 | +5 | 129 | -291 |
| Qwen | 1,771 | 1,024 | -747 | 1,206 | -565 |

**Accuracy**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.94 | 0.94 | 0.00 | 0.96 | +0.02 |
| GPT-OSS | 0.84 | 0.87 | +0.03 | 0.85 | +0.01 |
| Qwen | 0.57 | 0.55 | -0.02 | 0.55 | -0.02 |

---

### Blocksworld

**Hardcoded Counts**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 7/100 | 5/100 | -2 | 7/99 | 0 |
| GPT-OSS | 1/100 | 1/100 | 0 | 1/100 | 0 |
| Qwen | 2/100 | 1/100 | -1 | 0/100 | -2 |

**Hardcoded Percentage**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 7.0% | 5.0% | -2.0% | 7.1% | +0.1% |
| GPT-OSS | 1.0% | 1.0% | 0.0% | 1.0% | 0.0% |
| Qwen | 2.0% | 1.0% | -1.0% | 0.0% | -2.0% |

**Solver-Like Tokens (Avg)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,304 | 1,084 | -220 | 986 | -318 |
| GPT-OSS | 283 | 197 | -86 | 203 | -80 |
| Qwen | 366 | 348 | -18 | 310 | -56 |

**Accuracy**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.78 | 0.72 | -0.06 | 0.69 | -0.09 |
| GPT-OSS | 0.55 | 0.59 | +0.04 | 0.47 | -0.08 |
| Qwen | 0.72 | 0.65 | -0.07 | 0.62 | -0.10 |

---

## Observations

### Hardcoded Solutions by Task

**Calendar Scheduling**: Very low hardcoding across all models (0%). Calendar problems require
algorithmic time slot searching, making hardcoded solutions impractical.

**Meeting Planning**: Moderate to high hardcoding, especially in GPT-OSS baseline (50.5%).
Meeting itineraries can be more easily hardcoded as sequential lists of actions. Cautionary
prompts dramatically reduce this (Caution A: 4.3%, Caution B: 1.1%).

**ZebraLogic**: Very low hardcoding (0-1%). Logic grid puzzles typically require constraint solving
(Z3) or backtracking algorithms, difficult to hardcode.

**BlocksWorld (PDDL)**: Low to moderate hardcoding (1-7%). PDDL planning problems require complex
state space search, but some simple problems may allow hardcoded action sequences.

### Effect of Cautionary Prompts

**Dramatic Impact on Meeting Tasks**: GPT-OSS meeting baseline has 50.5% hardcoding, which drops
to 4.3% (Caution A) and 1.1% (Caution B). This is the most striking effect observed.

**General Reduction**: Cautionary prompts generally reduce hardcoding across tasks and models.
The warnings about proper formalization appear to discourage literal solution embedding.

**Solver-Like vs Hardcoded**: Solver-like reasoning (solving in natural language) does NOT strongly
correlate with hardcoded solutions. Models can solve problems in reasoning traces while still
implementing proper algorithmic code. For example, Deepseek Meeting has high solver-like tokens
(~13k baseline) but very low hardcoding (1.1%).

### Accuracy Correlation

**No Strong Negative Correlation**: Hardcoded solutions do not consistently predict lower accuracy.
GPT-OSS Meeting Baseline has both high hardcoding (50.5%) and high accuracy (0.93), suggesting
the hardcoded values are often correct for those specific problems.

**Task Complexity Matters**: The relationship between hardcoding and accuracy varies by task.
Calendar and ZebraLogic (0% hardcoding) require proper algorithms. Meeting tasks allow some
hardcoding with maintained accuracy. BlocksWorld shows mixed results.

**Cautionary Prompts**: While cautionary prompts reduce hardcoding, their effect on accuracy
varies. In some cases accuracy improves (Deepseek Calendar), in others it stays stable or
decreases (GPT-OSS Meeting Caution B: 0.90 vs 0.93 baseline).

## Key Findings

1. **GPT-OSS Meeting Baseline**: 50.5% hardcoded - the highest rate observed
2. **Cautionary Prompts Work**: Reduce GPT-OSS meeting hardcoding by ~46-49 percentage points
3. **Task Dependency**: Calendar (0%), ZebraLogic (0-1%), BlocksWorld (1-7%), Meeting (0-50.5%)
4. **Solver-Like ≠ Hardcoded**: High natural language solving doesn't imply hardcoded code
5. **Accuracy Independence**: Hardcoded solutions can be accurate if values are correct

## Notes

- Hardcoded detection performed using Gemini 2.5 Pro judge via Vertex AI Batch API
- Only examples with successful code execution (`exit_code == 0`) were judged
- Solver-like token counts from chunking analysis (Gemini judge with tiktoken encoding)
- Accuracy values are constraint-based from evaluation stage (except ZebraLogic: golden solution)
- Results generated on 2026-09-27
- Missing file: gpt/blocksworld/caution_b_hardcoded.json (marked as N/A in tables)
