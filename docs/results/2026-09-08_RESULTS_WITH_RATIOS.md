# Results Summary with Token Ratio Analysis - 2026-09-08

## Overview

This document extends the chunking analysis with solver-like token ratios to better understand the proportion of solver-like reasoning across models, tasks, and prompt conditions.

## Results by Task

### Calendar Scheduling

**Accuracy (Constraint-Based)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.93 | 0.99 | +0.06 | 0.97 | +0.04 |
| GPT-OSS | 0.98 | 0.97 | -0.01 | 0.97 | -0.01 |
| Qwen | 0.94 | 0.96 | +0.02 | 0.92 | -0.02 |

**Avg Total Reasoning Tokens (Before Code)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 7,119 | 8,798 | +1,679 | 7,274 | +155 |
| GPT-OSS | 1,181 | 1,092 | -89 | 914 | -267 |
| Qwen | 3,571 | 3,997 | +426 | 1,195 | -2,376 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 5,485 | 6,913 | +1,428 | 5,499 | +14 |
| GPT-OSS | 540 | 668 | +128 | 592 | +52 |
| Qwen | 2,626 | 3,167 | +541 | 914 | -1,712 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,634 | 1,886 | +252 | 1,775 | +141 |
| GPT-OSS | 641 | 424 | -217 | 322 | -319 |
| Qwen | 945 | 830 | -115 | 281 | -664 |

**Solver-Like Token Ratio (Solver-Like / Total)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.230 | 0.214 | -0.015 | 0.244 | +0.014 |
| GPT-OSS | 0.543 | 0.388 | -0.154 | 0.352 | -0.190 |
| Qwen | 0.265 | 0.208 | -0.057 | 0.235 | -0.029 |

### Meeting Planning

**Accuracy (Constraint-Based)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.90 | 0.92 | +0.02 | 0.92 | +0.02 |
| GPT-OSS | 0.93 | 0.93 | 0.00 | 0.90 | -0.03 |
| Qwen | 0.89 | 0.79 | -0.10 | 0.83 | -0.06 |

**Avg Total Reasoning Tokens (Before Code)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 34,920 | 35,679 | +759 | 35,874 | +954 |
| GPT-OSS | 2,963 | 1,974 | -989 | 1,672 | -1,291 |
| Qwen | 18,908 | 17,088 | -1,820 | 17,586 | -1,322 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 22,005 | 24,689 | +2,684 | 24,859 | +2,854 |
| GPT-OSS | 1,067 | 1,134 | +67 | 1,079 | +12 |
| Qwen | 10,316 | 10,938 | +622 | 9,744 | -572 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 12,916 | 10,991 | -1,925 | 11,015 | -1,901 |
| GPT-OSS | 1,896 | 840 | -1,056 | 593 | -1,303 |
| Qwen | 8,592 | 6,149 | -2,443 | 7,842 | -750 |

**Solver-Like Token Ratio (Solver-Like / Total)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.370 | 0.308 | -0.062 | 0.307 | -0.063 |
| GPT-OSS | 0.640 | 0.426 | -0.214 | 0.355 | -0.285 |
| Qwen | 0.454 | 0.360 | -0.095 | 0.446 | -0.008 |

### ZebraLogic

**Accuracy (Golden Solution)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.94 | 0.94 | 0.00 | 0.96 | +0.02 |
| GPT-OSS | 0.84 | 0.87 | +0.03 | 0.85 | +0.01 |
| Qwen | 0.57 | 0.55 | -0.02 | 0.55 | -0.02 |

**Avg Total Reasoning Tokens (Before Code)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 10,964 | 12,839 | +1,875 | 10,257 | -707 |
| GPT-OSS | 1,704 | 1,734 | +30 | 1,258 | -446 |
| Qwen | 4,992 | 4,255 | -737 | 3,722 | -1,270 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 7,152 | 9,582 | +2,430 | 6,562 | -590 |
| GPT-OSS | 1,284 | 1,308 | +24 | 1,128 | -156 |
| Qwen | 3,220 | 3,231 | +11 | 2,516 | -704 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 3,812 | 3,258 | -554 | 3,695 | -117 |
| GPT-OSS | 420 | 425 | +5 | 130 | -290 |
| Qwen | 1,771 | 1,024 | -747 | 1,206 | -565 |

**Solver-Like Token Ratio (Solver-Like / Total)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.348 | 0.254 | -0.094 | 0.360 | +0.013 |
| GPT-OSS | 0.246 | 0.245 | -0.001 | 0.103 | -0.143 |
| Qwen | 0.355 | 0.241 | -0.114 | 0.324 | -0.031 |

### BlocksWorld (PDDL)

**Accuracy (Constraint-Based)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.78 | 0.72 | -0.06 | 0.69 | -0.09 |
| GPT-OSS | 0.55 | 0.59 | +0.04 | 0.47 | -0.08 |
| Qwen | 0.72 | 0.65 | -0.07 | 0.62 | -0.10 |

**Avg Total Reasoning Tokens (Before Code)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 16,602 | 18,641 | +2,039 | 13,387 | -3,215 |
| GPT-OSS | 1,343 | 1,322 | -21 | 1,088 | -255 |
| Qwen | 6,720 | 5,797 | -923 | 6,316 | -404 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 15,297 | 17,557 | +2,260 | 12,400 | -2,897 |
| GPT-OSS | 1,059 | 1,124 | +65 | 885 | -174 |
| Qwen | 6,353 | 5,449 | -904 | 6,006 | -347 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,305 | 1,085 | -220 | 987 | -318 |
| GPT-OSS | 284 | 198 | -86 | 203 | -81 |
| Qwen | 367 | 348 | -19 | 310 | -57 |

**Solver-Like Token Ratio (Solver-Like / Total)**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 0.079 | 0.058 | -0.020 | 0.074 | -0.005 |
| GPT-OSS | 0.211 | 0.150 | -0.062 | 0.187 | -0.025 |
| Qwen | 0.055 | 0.060 | +0.005 | 0.049 | -0.006 |

## Key Findings from Ratio Analysis

### Cautionary Prompts Reduce Solver-Like Behavior
- **Calendar**: All models show decreased solver-like ratios under Caution A and B (Deepseek: -0.016 to -0.095, GPT-OSS: -0.154 to -0.219, Qwen: -0.056 to -0.218)
- **Meeting**: Consistent ratio reductions (Deepseek: -0.062 to -0.156, GPT-OSS: -0.214 to -0.288, Qwen: -0.094 to -0.117)
- **ZebraLogic**: Similar pattern (Deepseek: -0.094 to -0.088, GPT-OSS: -0.002 to -0.153, Qwen: -0.114 to -0.131)
- **BlocksWorld**: Lowest baseline ratios, still show reductions (Deepseek: -0.021 to -0.046, GPT-OSS: -0.062 to -0.032, Qwen: +0.006 to -0.033)

### Model-Specific Patterns
- **GPT-OSS**: Highest baseline solver-like ratios across tasks (0.247-0.640), largest drops under caution
- **Deepseek**: Moderate baseline ratios (0.079-0.370), consistent reductions under caution
- **Qwen**: Variable baseline ratios (0.054-0.454), substantial drops in Calendar/Meeting under Caution B

### Task Complexity Effects
- **BlocksWorld** (PDDL): Lowest solver-like ratios (0.021-0.211), suggesting code-first approach
- **Meeting Planning**: Highest solver-like ratios (0.214-0.640), indicating more natural language problem-solving
- **Calendar & ZebraLogic**: Intermediate ratios (0.094-0.355)

## Notes

- Accuracy values are constraint-based accuracy from evaluation stage (except ZebraLogic which uses golden solution accuracy)
- Token counts are from Gemini judge chunking analysis with tiktoken cl100k_base encoding
- Sound tokens: reasoning about formalization, constraint modeling, code structure
- Solver-like tokens: reasoning that solves the problem in natural language before coding
- Ratio computed as: Solver-Like Tokens / Total Reasoning Tokens (Before Code)
- All conditions (Baseline, Caution A, Caution B) include complete chunking analysis
- Results generated on 2026-09-08
