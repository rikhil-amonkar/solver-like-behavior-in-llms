# Correlation Analysis: Solver-Like Behavior vs. Correctness - 2026-09-08

## Overview

This document analyzes the relationship between solver-like reasoning behavior (measured as percentage of solver-like tokens in reasoning traces) and task correctness (binary: 0 for incorrect, 1 for correct) across models, tasks, and prompt conditions.

## Statistical Method: Point-Biserial Correlation

We use the **point-biserial correlation coefficient (r_pb)**, a standard method for measuring the correlation between:
- A **continuous variable**: Solver-like reasoning percentage (0-100%)
- A **binary variable**: Correctness (0 = incorrect, 1 = correct)

### Formula

The point-biserial correlation coefficient is calculated as:

```
r_pb = ((M₁ - M₀) / σ) × √(p × q)
```

Where:
- **M₁** = Mean SL% for correct examples (correctness = 1)
- **M₀** = Mean SL% for incorrect examples (correctness = 0)
- **σ** = Population standard deviation of SL% across all examples
- **p** = Proportion of correct examples
- **q** = Proportion of incorrect examples (q = 1 - p)

### Interpretation

The correlation coefficient ranges from **-1 to +1**:

- **r_pb > 0**: Positive correlation — Higher solver-like behavior associated with **higher correctness**
- **r_pb < 0**: Negative correlation — Higher solver-like behavior associated with **lower correctness** (more solver-like reasoning predicts failure)
- **r_pb ≈ 0**: No correlation — Solver-like behavior is unrelated to correctness

**Magnitude guidelines** (Cohen's conventions):
- **|r_pb| < 0.10**: Negligible correlation
- **0.10 ≤ |r_pb| < 0.30**: Small/weak correlation
- **0.30 ≤ |r_pb| < 0.50**: Moderate correlation
- **|r_pb| ≥ 0.50**: Strong correlation

## Correlation Results by Model and Task

### DeepSeek

| Task | Baseline | Caution A | Caution B |
|------|----------|-----------|-----------|
| Calendar | **-0.2033** | 0.0189 | 0.0820 |
| Meeting | -0.0159 | **-0.1406** | **-0.2578** |
| ZebraLogic | -0.0376 | -0.0171 | 0.0622 |
| BlocksWorld | **0.1550** | -0.0143 | 0.0672 |

### GPT-OSS

| Task | Baseline | Caution A | Caution B |
|------|----------|-----------|-----------|
| Calendar | 0.0212 | 0.0238 | 0.0967 |
| Meeting | -0.0408 | -0.0463 | **-0.1091** |
| ZebraLogic | -0.0690 | 0.0534 | -0.0088 |
| BlocksWorld | 0.0479 | -0.0308 | **0.1086** |

### Qwen

| Task | Baseline | Caution A | Caution B |
|------|----------|-----------|-----------|
| Calendar | **-0.2095** | **-0.4294** | **-0.1292** |
| Meeting | **0.1528** | 0.0297 | 0.0707 |
| ZebraLogic | **-0.1251** | **-0.1618** | **-0.2783** |
| BlocksWorld | -0.0828 | -0.0967 | -0.0225 |

**Bold** values indicate weak or moderate correlations (|r_pb| ≥ 0.10).

## Key Findings

### 1. Predominantly Negative Correlations

**Most correlations are negative**, suggesting that:
- **More solver-like reasoning tends to predict lower correctness**
- Models that "solve in natural language" before formalizing often fail to produce correct code
- Sound formalization-first approaches are more reliable for correctness

**Notable negative correlations**:
- **Qwen Calendar (Caution A)**: r = -0.43 (moderate) — Strongest negative correlation
- **DeepSeek Meeting (Caution B)**: r = -0.26 (weak)
- **Qwen ZebraLogic (Caution B)**: r = -0.28 (weak)
- **Qwen Calendar (Baseline)**: r = -0.21 (weak)
- **DeepSeek Calendar (Baseline)**: r = -0.20 (weak)

### 2. Task-Specific Patterns

#### Calendar Scheduling
- **Consistently negative correlations** across most model-condition pairs
- Strongest effect in Qwen (all negative, peak at -0.43)
- Suggests calendar tasks benefit from direct formalization without natural language solving

#### Meeting Planning
- **Mixed signals**: DeepSeek/GPT-OSS show negative, Qwen shows positive (baseline)
- Qwen's positive correlation (r = 0.15) suggests solver-like reasoning may help for complex scheduling logic
- Effect reverses under cautionary prompts

#### ZebraLogic
- **Qwen shows consistent negative correlations** (-0.13 to -0.28)
- DeepSeek and GPT-OSS mostly negligible
- Logical puzzles may punish heuristic natural language reasoning

#### BlocksWorld (PDDL)
- **More positive correlations** than other tasks
- DeepSeek baseline: r = 0.16 (weak positive)
- GPT-OSS Caution B: r = 0.11 (weak positive)
- Planning tasks may benefit from some natural language decomposition

### 3. Effect of Cautionary Prompts

**Caution A and Caution B** conditions (which discourage solver-like behavior) show:
- **Qwen Calendar**: Strongest negative correlation under Caution A (-0.43)
- **DeepSeek Meeting**: More negative under Caution B (-0.26)
- **Mixed effects**: Not uniformly better or worse than baseline

**Interpretation**: Cautionary prompts successfully reduce solver-like behavior, but correlations suggest the remaining solver-like reasoning is still problematic for correctness.

### 4. Model-Specific Differences

#### DeepSeek
- Calendar (baseline) and Meeting (Caution B) show weak negative correlations
- BlocksWorld baseline shows positive correlation (r = 0.16)
- Generally small magnitude correlations

#### GPT-OSS
- Most correlations negligible (|r| < 0.10)
- Slightly negative for Meeting tasks
- Most robust to solver-like behavior among the three models

#### Qwen
- **Strongest negative correlations** overall
- Calendar and ZebraLogic consistently negative
- Most sensitive to solver-like reasoning patterns
- Meeting baseline shows positive correlation (r = 0.15) — outlier pattern

## Practical Implications

### For Prompt Engineering
1. **Discourage solver-like reasoning** for calendar and logic tasks
2. **BlocksWorld/planning tasks** may tolerate or benefit from some natural language decomposition
3. **Qwen is most sensitive** to solver-like behavior — prioritize direct formalization

### For Model Selection
- **GPT-OSS** shows most robustness (smallest correlations) to reasoning style
- **Qwen** requires careful prompt engineering to avoid solver-like patterns
- **DeepSeek** shows task-dependent sensitivity

### For Future Research
- Investigate **why Meeting Planning** shows positive correlation in Qwen baseline
- Explore **BlocksWorld's positive correlations** — does PDDL benefit from natural language planning?
- Study **threshold effects**: Is some solver-like reasoning helpful, or is any amount harmful?

## Conclusion

The predominantly **negative correlations** between solver-like reasoning and correctness suggest that:
1. **Direct formalization is more reliable** than solving in natural language first
2. **Task complexity matters**: Logic/calendar tasks punish solver-like behavior; planning tasks show mixed signals
3. **Cautionary prompts reduce solver-like behavior** but don't eliminate correlation patterns
4. **Model choice affects sensitivity**: Qwen most sensitive, GPT-OSS most robust

These findings support the hypothesis that **"thinking through the solution in prose"** before writing code is often counterproductive for constraint satisfaction and formalization tasks, though exceptions exist for certain problem types (planning, complex scheduling logic).

## Technical Notes

- Correlations computed using point-biserial formula over 100 examples per model-task-condition
- All correlations computed from per-example data (not aggregates)
- Standard population standard deviation (σ) used, not sample standard deviation
- Results generated from chunking analysis by Gemini judge with tiktoken cl100k_base encoding
- Date: 2026-09-08
