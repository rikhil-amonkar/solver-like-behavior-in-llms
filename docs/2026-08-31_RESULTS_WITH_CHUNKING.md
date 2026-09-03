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
| Deepseek | 7,119 | 8,798 | +1,679 | 13,178 | +6,059 |
| GPT-OSS | 1,181 | 1,091 | -90 | 993 | -188 |
| Qwen | 3,571 | 3,997 | +426 | 6,142 | +2,571 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 5,485 | 6,912 | +1,427 | 5,498 | +13 |
| GPT-OSS | 540 | 667 | +127 | 591 | +51 |
| Qwen | 2,626 | 3,166 | +540 | 914 | -1,712 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,634 | 1,885 | +251 | 1,775 | +141 |
| GPT-OSS | 641 | 424 | -217 | 322 | -319 |
| Qwen | 944 | 830 | -114 | 281 | -663 |

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
| Deepseek | 34,920 | 35,679 | +759 | 51,586 | +16,666 |
| GPT-OSS | 2,962 | 1,974 | -988 | 1,684 | -1,278 |
| Qwen | 18,908 | 17,087 | -1,821 | 23,247 | +4,339 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 22,004 | 24,688 | +2,684 | 24,858 | +2,854 |
| GPT-OSS | 1,067 | 1,134 | +67 | 1,078 | +11 |
| Qwen | 10,316 | 10,938 | +622 | 9,744 | -572 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 12,915 | 10,990 | -1,925 | 11,015 | -1,900 |
| GPT-OSS | 1,895 | 840 | -1,055 | 592 | -1,303 |
| Qwen | 8,591 | 6,149 | -2,442 | 7,841 | -750 |

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
| Deepseek | 10,964 | 12,839 | +1,875 | 14,210 | +3,246 |
| GPT-OSS | 1,704 | 1,733 | +29 | 1,376 | -328 |
| Qwen | 4,991 | 4,255 | -736 | 5,387 | +396 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 7,152 | 9,581 | +2,429 | 6,562 | -590 |
| GPT-OSS | 1,283 | 1,308 | +25 | 1,128 | -155 |
| Qwen | 3,220 | 3,230 | +10 | 2,515 | -705 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 3,812 | 3,257 | -555 | 3,695 | -117 |
| GPT-OSS | 420 | 425 | +5 | 129 | -291 |
| Qwen | 1,771 | 1,024 | -747 | 1,206 | -565 |

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
| Deepseek | 16,602 | 18,641 | +2,039 | 29,506 | +12,904 |
| GPT-OSS | 1,342 | 1,321 | -21 | 1,134 | -208 |
| Qwen | 6,720 | 5,797 | -923 | 14,690 | +7,970 |

**Avg Sound Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 15,297 | 17,556 | +2,259 | 12,400 | -2,897 |
| GPT-OSS | 1,058 | 1,124 | +66 | 884 | -174 |
| Qwen | 6,353 | 5,449 | -904 | 6,006 | -347 |

**Avg Solver-Like Reasoning Tokens**

| Model | Baseline | Caution A | ΔA | Caution B | ΔB |
|-------|----------|-----------|-----|-----------|-----|
| Deepseek | 1,304 | 1,084 | -220 | 986 | -318 |
| GPT-OSS | 283 | 197 | -86 | 203 | -80 |
| Qwen | 366 | 348 | -18 | 310 | -56 |

## Notes

- Accuracy values are constraint-based accuracy from evaluation stage (except ZebraLogic which uses golden solution accuracy)
- Token counts are from Gemini judge chunking analysis with tiktoken cl100k_base encoding
- Sound tokens: reasoning about formalization, constraint modeling, code structure
- Solver-like tokens: reasoning that solves the problem in natural language before coding
- All conditions (Baseline, Caution A, Caution B) include complete chunking analysis
- Results generated on 2026-08-31
