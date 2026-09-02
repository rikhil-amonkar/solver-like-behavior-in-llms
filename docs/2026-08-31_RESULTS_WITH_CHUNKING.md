# Results Summary with Chunking Analysis - 2026-08-31

## Overview

This document summarizes accuracy and token usage results across models, tasks, and prompt conditions.
Token breakdowns show average sound vs solver-like reasoning tokens from chunking analysis.

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
| Deepseek | 9,959 | 14,254 | +4,295 | 13,178 | +3,219 |
| GPT-OSS | 1,189 | 1,103 | -86 | 993 | -196 |
| Qwen | 4,735 | 5,743 | +1,008 | 6,142 | +1,407 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 5,485 | 6,912 | +1,427 | - | - |
| GPT-OSS | 540 | 667 | +127 | - | - |
| Qwen | 2,626 | 3,166 | +540 | - | - |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,634 | 1,885 | +251 | - | - |
| GPT-OSS | 641 | 424 | -217 | - | - |
| Qwen | 944 | 830 | -114 | - | - |

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
| Deepseek | 47,976 | 52,888 | +4,912 | 51,586 | +3,610 |
| GPT-OSS | 2,991 | 1,978 | -1,013 | 1,684 | -1,307 |
| Qwen | 24,711 | 22,303 | -2,408 | 23,247 | -1,464 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 22,004 | 24,688 | +2,684 | - | - |
| GPT-OSS | 1,067 | 1,134 | +67 | - | - |
| Qwen | 10,316 | 10,938 | +622 | - | - |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 12,915 | 10,990 | -1,925 | - | - |
| GPT-OSS | 1,895 | 840 | -1,055 | - | - |
| Qwen | 8,591 | 6,149 | -2,442 | - | - |

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
| Deepseek | 14,369 | 18,552 | +4,183 | 14,210 | -159 |
| GPT-OSS | 1,705 | 1,741 | +36 | 1,376 | -329 |
| Qwen | 5,522 | 4,916 | -606 | 5,387 | -135 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 7,152 | 9,581 | +2,429 | - | - |
| GPT-OSS | 1,283 | 1,308 | +25 | - | - |
| Qwen | 3,220 | 3,230 | +10 | - | - |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 3,812 | 3,257 | -555 | - | - |
| GPT-OSS | 420 | 425 | +5 | - | - |
| Qwen | 1,771 | 1,024 | -747 | - | - |

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
| Deepseek | 33,638 | 40,158 | +6,520 | 29,506 | -4,132 |
| GPT-OSS | 1,383 | 1,356 | -27 | 1,134 | -249 |
| Qwen | 15,815 | 15,528 | -287 | 14,690 | -1,125 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 15,297 | 17,556 | +2,259 | - | - |
| GPT-OSS | 1,058 | 1,124 | +66 | - | - |
| Qwen | 6,353 | 5,449 | -904 | - | - |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,304 | 1,084 | -220 | - | - |
| GPT-OSS | 283 | 197 | -86 | - | - |
| Qwen | 366 | 348 | -18 | - | - |

## Notes

- Accuracy values are constraint-based accuracy from evaluation stage (except ZebraLogic which uses golden solution accuracy)
- Token counts are from Gemini judge chunking analysis with tiktoken cl100k_base encoding
- Sound tokens: reasoning about formalization, constraint modeling, code structure
- Solver-like tokens: reasoning that solves the problem in natural language before coding
- **Caution B** is included in accuracy and total token tables, but **not** in sound/solver-like token breakdowns (chunking incomplete)
- `-` indicates no data available for that model/task/condition combination
- Results generated on 2026-08-31
