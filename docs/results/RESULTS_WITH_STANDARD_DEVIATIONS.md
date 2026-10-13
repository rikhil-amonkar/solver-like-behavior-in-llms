# Results with Standard Deviations

This document provides comprehensive accuracy, solver-like ratio, and solver-like token statistics with standard deviations across all models, tasks, and conditions.

**Dataset**: 100 examples per task  
**Models**: DeepSeek-V4-Flash, GPT-OSS-120B, Qwen3.8-27B  
**Tasks**: Calendar Scheduling, Meeting Planning, ZebraLogic Grid Puzzles, BlocksWorld (PDDL)  
**Conditions**: Baseline, Caution A (anti-solver prompt), Caution B (stronger anti-solver prompt)

**Note**: Ratio is calculated as total solver-like tokens / total reasoning tokens (weighted by token count, not averaged per example).

---

## Mean Values

| Model | Metric | | Calendar | | | Meeting | | | ZebraLogic | | | BlocksWorld | |
|-------|--------|---|----------|---|---|---------|---|---|------------|---|---|-------------|---|
| | | **Base** | **Caut A** | **Caut B** | **Base** | **Caut A** | **Caut B** | **Base** | **Caut A** | **Caut B** | **Base** | **Caut A** | **Caut B** |
| DeepSeek | Accuracy | 0.93 | 0.99 | 0.97 | 0.90 | 0.92 | 0.92 | 0.94 | 0.94 | 0.96 | 0.78 | 0.72 | 0.69 |
| | Ratio | 0.23 | 0.21 | 0.24 | 0.37 | 0.31 | 0.31 | 0.35 | 0.25 | 0.36 | 0.08 | 0.06 | 0.07 |
| | Solver Tokens | 1,634 | 1,886 | 1,775 | 12,916 | 10,991 | 11,015 | 3,812 | 3,258 | 3,695 | 1,305 | 1,085 | 987 |
| GPT-OSS | Accuracy | 0.98 | 0.97 | 0.97 | 0.93 | 0.93 | 0.90 | 0.84 | 0.87 | 0.85 | 0.55 | 0.59 | 0.47 |
| | Ratio | 0.54 | 0.39 | 0.35 | 0.64 | 0.43 | 0.35 | 0.25 | 0.25 | 0.10 | 0.21 | 0.15 | 0.19 |
| | Solver Tokens | 641 | 424 | 322 | 1,896 | 840 | 593 | 420 | 425 | 130 | 284 | 198 | 203 |
| Qwen | Accuracy | 0.94 | 0.96 | 0.92 | 0.89 | 0.79 | 0.83 | 0.57 | 0.55 | 0.55 | 0.72 | 0.65 | 0.62 |
| | Ratio | 0.26 | 0.21 | 0.24 | 0.45 | 0.36 | 0.45 | 0.35 | 0.24 | 0.32 | 0.05 | 0.06 | 0.05 |
| | Solver Tokens | 945 | 830 | 281 | 8,592 | 6,149 | 7,842 | 1,771 | 1,024 | 1,206 | 367 | 348 | 310 |

---

## Standard Deviation Values

| Model | Metric | | Calendar | | | Meeting | | | ZebraLogic | | | BlocksWorld | |
|-------|--------|---|----------|---|---|---------|---|---|------------|---|---|-------------|---|
| | | **Base** | **Caut A** | **Caut B** | **Base** | **Caut A** | **Caut B** | **Base** | **Caut A** | **Caut B** | **Base** | **Caut A** | **Caut B** |
| DeepSeek | Accuracy | 0.26 | 0.10 | 0.17 | 0.30 | 0.27 | 0.27 | 0.24 | 0.24 | 0.20 | 0.42 | 0.45 | 0.46 |
| | Ratio | 0.17 | 0.19 | 0.19 | 0.17 | 0.16 | 0.16 | 0.24 | 0.21 | 0.24 | 0.17 | 0.13 | 0.19 |
| | Solver Tokens | 1,593 | 2,357 | 1,834 | 8,555 | 8,009 | 7,165 | 4,181 | 3,821 | 4,361 | 3,426 | 2,495 | 2,251 |
| GPT-OSS | Accuracy | 0.14 | 0.17 | 0.17 | 0.26 | 0.26 | 0.30 | 0.37 | 0.34 | 0.36 | 0.50 | 0.49 | 0.50 |
| | Ratio | 0.18 | 0.20 | 0.24 | 0.19 | 0.22 | 0.23 | 0.21 | 0.21 | 0.15 | 0.32 | 0.28 | 0.28 |
| | Solver Tokens | 410 | 409 | 338 | 2,098 | 920 | 606 | 834 | 687 | 270 | 422 | 313 | 349 |
| Qwen | Accuracy | 0.24 | 0.20 | 0.27 | 0.31 | 0.41 | 0.38 | 0.50 | 0.50 | 0.50 | 0.45 | 0.48 | 0.49 |
| | Ratio | 0.14 | 0.17 | 0.17 | 0.23 | 0.21 | 0.23 | 0.19 | 0.18 | 0.22 | 0.13 | 0.13 | 0.14 |
| | Solver Tokens | 790 | 773 | 617 | 6,727 | 5,445 | 7,222 | 2,348 | 1,706 | 1,818 | 882 | 725 | 612 |

---

## Interpretation Guide

### Metrics

- **Accuracy**: Proportion of examples that passed constraint validation (0.0-1.0)
- **Ratio**: Solver-like fraction calculated as `sum(solver_tokens) / sum(total_tokens)` across all examples (token-weighted, not per-example average)
- **Solver Tokens**: Average number of solver-like reasoning tokens per example

### Standard Deviations

- Computed using Bessel's correction (ddof=1) for unbiased sample estimates
- Sample size: n=100 for all conditions
- **Accuracy SD**: Variance in binary outcomes (higher = more inconsistent constraint satisfaction)
- **Ratio SD**: Variance in individual example ratios (higher = more variable solver-like behavior across examples)
- **Solver Tokens SD**: Variance in solver-like reasoning length (higher = more variable problem-solving approaches)

### Calculation Methods

**Ratio (Mean)**: Uses Method B (Ratio of Totals)
- More interpretable: "X% of all reasoning tokens were solver-like"
- Token-weighted: Reflects actual distribution of reasoning tokens
- Standard for corpus-level NLP metrics

**Ratio (SD)**: Calculated from individual example ratios
- Shows variance in solver-like tendency across different problems
- High SD indicates some problems trigger much more solver-like reasoning than others

### Key Observations

1. **Accuracy trends**: DeepSeek maintains high accuracy on Calendar/ZebraLogic; GPT-OSS strongest on Calendar/Meeting
2. **Cautionary effects**: Mixed - sometimes improve accuracy (DeepSeek Calendar: 0.93→0.99), sometimes degrade (all models BlocksWorld)
3. **Solver-like behavior**: GPT-OSS shows highest baseline ratio on Calendar/Meeting (0.54-0.64), significantly reduced by prompts
4. **Token efficiency**: GPT-OSS uses fewer solver-like tokens overall; DeepSeek uses more but maintains higher accuracy
5. **Variability**: Higher SDs on Meeting/BlocksWorld tasks indicate greater challenge and inconsistency

---

*Generated: 2026-10-12*  
*Calculation: Method B (Ratio of Totals) for token-weighted metrics*  
*Sample size: n=100 per condition*
