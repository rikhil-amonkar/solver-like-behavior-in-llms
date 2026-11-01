# Hypothesis tests (6000 traces; models: deepseek, qwen, gpt)

## H1.1 Prevalence and share of reasoning (baseline condition)

| model | runs | traces | with Values | mean ratio | SLB tokens/trace | reasoning tokens/trace | token share | Values but program independent | SLB tokens/trace there |
|---|---|---|---|---|---|---|---|---|---|
| deepseek | native | 400 | 96% | 0.19 | 6123 | 26572 | 23% | 85% | 6234 |
| qwen | native | 400 | 90% | 0.19 | 3662 | 13122 | 28% | 73% | 4111 |
| qwen | crossfl | 400 | 100% | 0.19 | 3912 | 17469 | 22% | 74% | 3308 |
| gpt | native | 400 | 66% | 0.23 | 644 | 1821 | 35% | 50% | 703 |
| gpt | crossfl | 400 | 73% | 0.21 | 506 | 1964 | 26% | 57% | 613 |

Traces with ratio >= 0.1: 71% of baseline traces.
Traces with ratio >= 0.2: 46% of baseline traces. Traces with >= 1,000 SLB tokens: 47%.

Per dataset and FL (baseline, all models):

| task | FL | with Values | mean ratio | SLB tokens/trace | token share |
|---|---|---|---|---|---|
| calendar | python | 100% | 0.24 | 1421 | 27% |
| calendar | z3 | 94% | 0.19 | 752 | 22% |
| meeting | python | 99% | 0.34 | 9242 | 36% |
| meeting | z3 | 84% | 0.18 | 3560 | 21% |
| zebralogic | python | 89% | 0.22 | 1454 | 28% |
| zebralogic | z3 | 87% | 0.20 | 2182 | 29% |
| blocksworld | pddl | 51% | 0.04 | 1060 | 6% |
| blocksworld | python | 78% | 0.19 | 3070 | 23% |

## H1.2 Kinds of SLB and their harm (all conditions)

| model | runs | Values traces | complete | partial | prose answer wrong (C2) | prose ≠ program (C1) | hardcoded | partly fixed | steered |
|---|---|---|---|---|---|---|---|---|---|
| deepseek | native | 1136 | 85% | 15% | 3% (n=916) | 8% (n=901) | 0 | 19 | 31 |
| qwen | native | 1077 | 88% | 12% | 8% (n=858) | 16% (n=783) | 0 | 30 | 21 |
| qwen | crossfl | 1190 | 95% | 5% | 13% (n=1016) | 12% (n=880) | 0 | 28 | 6 |
| gpt | native | 682 | 84% | 16% | 10% (n=512) | 12% (n=522) | 41 | 54 | 3 |
| gpt | crossfl | 750 | 80% | 20% | 11% (n=493) | 12% (n=500) | 13 | 90 | 0 |

Accuracy by B label, compared with independent programs for the same problem and model (pairs of traces of one problem, any condition and FL, one label inherited and one independent):

| B label | traces | accuracy | accuracy of independent programs, same problems | difference |
|---|---|---|---|---|
| hardcoded | 54 | 0.54 | 0.58 (50 problems) | -0.01 [-0.14, +0.12] |
| partly_fixed | 221 | 0.73 | 0.72 (135 problems) | +0.02 [-0.05, +0.09] |
| steered | 61 | 1.00 | 0.95 (50 problems) | +0.05 [+0.01, +0.09] |

Wrong prose answers (C2 false) and the program:

| B label | prose wrong | of these, program correct | prose right | of these, program correct |
|---|---|---|---|---|
| hardcoded | 23 | 0% | 28 | 100% |
| partly_fixed | 26 | 4% | 106 | 94% |
| steered | 3 | 100% | 57 | 100% |
| independent | 238 | 36% | 3041 | 98% |

## H1.3 SLB and accuracy

Linear probability model: correct ~ x + run fixed effects (model × task × FL × condition) + problem fixed effects, so x is compared within a run and within a problem. CI: bootstrap over problems.

| x | rows | coefficient on accuracy |
|---|---|---|
| solver-like ratio (0-1) | 6000 | +0.130 [+0.042, +0.227] |
| any Values paragraph | 6000 | +0.069 [+0.039, +0.108] |
| SLB tokens (per 10k) | 6000 | +0.065 [+0.026, +0.106] |
| program inherits (B hardcoded/partly fixed/steered) | 5357 | +0.040 [-0.019, +0.097] |
| prose answer correct (C2) | 3795 | +0.438 [+0.374, +0.503] |

The same, per model and run set (solver-like ratio):

| model | runs | coefficient |
|---|---|---|
| deepseek | native | -0.285 [-0.547, +0.002] |
| qwen | native | -0.045 [-0.368, +0.301] |
| qwen | crossfl | +0.272 [-0.162, +0.731] |
| gpt | native | -0.013 [-0.194, +0.189] |
| gpt | crossfl | +0.005 [-0.143, +0.159] |

## H2 FL vs dataset

Models with runs in both FLs: gpt, qwen.

Within-dataset FL contrast (cross-FL minus native, same problems, paired; all conditions):

| task | native → new FL | model | Δ ratio | Δ with Values | Δ program inherits | Δ accuracy |
|---|---|---|---|---|---|---|
| calendar | python → z3 | qwen | -0.02 [-0.03, -0.01] | -0.00 [-0.01, +0.00] | -0.00 [-0.03, +0.02] | -0.13 [-0.17, -0.09] |
| calendar | python → z3 | gpt | -0.04 [-0.05, -0.01] | -0.04 [-0.11, +0.02] | +0.01 [-0.01, +0.02] | -0.03 [-0.07, -0.00] |
| calendar | python → z3 | all | -0.03 [-0.04, -0.02] | -0.02 [-0.06, +0.01] | +0.00 [-0.01, +0.01] | -0.08 [-0.11, -0.06] |
| meeting | python → z3 | qwen | -0.14 [-0.16, -0.12] | -0.01 [-0.03, -0.00] | -0.05 [-0.08, -0.03] | -0.65 [-0.71, -0.60] |
| meeting | python → z3 | gpt | -0.17 [-0.19, -0.14] | -0.18 [-0.25, -0.12] | -0.13 [-0.19, -0.07] | -0.35 [-0.42, -0.27] |
| meeting | python → z3 | all | -0.15 [-0.17, -0.14] | -0.10 [-0.13, -0.07] | -0.09 [-0.12, -0.06] | -0.50 [-0.54, -0.46] |
| zebralogic | z3 → python | qwen | +0.00 [-0.01, +0.02] | +0.02 [-0.01, +0.05] | +0.01 [-0.02, +0.03] | +0.38 [+0.33, +0.44] |
| zebralogic | z3 → python | gpt | +0.05 [+0.02, +0.07] | +0.10 [+0.03, +0.17] | +0.10 [+0.05, +0.16] | +0.00 [-0.05, +0.05] |
| zebralogic | z3 → python | all | +0.02 [+0.01, +0.04] | +0.06 [+0.02, +0.10] | +0.06 [+0.03, +0.09] | +0.19 [+0.15, +0.23] |
| blocksworld | pddl → python | qwen | +0.14 [+0.13, +0.15] | +0.37 [+0.30, +0.45] | -0.01 [-0.07, +0.04] | -0.04 [-0.12, +0.04] |
| blocksworld | pddl → python | gpt | +0.11 [+0.09, +0.13] | +0.35 [+0.29, +0.41] | +0.04 [-0.01, +0.09] | -0.19 [-0.27, -0.11] |
| blocksworld | pddl → python | all | +0.12 [+0.11, +0.14] | +0.36 [+0.32, +0.40] | +0.01 [-0.03, +0.05] | -0.12 [-0.18, -0.05] |

Variance in the solver-like ratio explained by each factor (OLS on all traces; the drop in R² when the factor is removed from model + condition + task + FL):

Full model R² = 0.218.

| factor | ΔR² when removed |
|---|---|
| model | 0.001 |
| condition | 0.037 |
| task | 0.041 |
| FL | 0.080 |

FL coefficients in the full model (vs PDDL, the first level): python +0.124, z3 +0.056

Same FL, different datasets (baseline + cautions, all models): mean ratio

| FL | calendar | meeting | zebralogic | blocksworld |
|---|---|---|---|---|
| python | 0.20 | 0.30 | 0.17 | 0.15 |
| z3 | 0.17 | 0.14 | 0.15 | - |
| pddl | - | - | - | 0.03 |

## H3 Cautionary prompts (vs baseline, same problems, paired)

| model | runs | caution | Δ ratio | Δ with Values | Δ SLB tokens | Δ program inherits | Δ accuracy | ratio, baseline |
|---|---|---|---|---|---|---|---|---|
| deepseek | native | A | -0.04 [-0.05, -0.03] | +0.01 [-0.01, +0.04] | -712 [-1309, -197] | -0.03 [-0.06, -0.01] | +0.02 [-0.01, +0.05] | 0.19 |
| deepseek | native | B | -0.03 [-0.03, -0.02] | -0.04 [-0.07, -0.01] | -540 [-1087, -38] | -0.02 [-0.04, +0.01] | +0.01 [-0.03, +0.04] | 0.19 |
| qwen | native | A | -0.05 [-0.07, -0.04] | -0.01 [-0.04, +0.02] | -1046 [-1616, -533] | -0.03 [-0.06, -0.01] | -0.02 [-0.07, +0.03] | 0.19 |
| qwen | native | B | -0.04 [-0.05, -0.03] | -0.01 [-0.04, +0.01] | -335 [-669, +5] | -0.01 [-0.04, +0.01] | -0.00 [-0.04, +0.04] | 0.19 |
| qwen | crossfl | A | -0.05 [-0.05, -0.04] | -0.02 [-0.03, -0.01] | -1208 [-1653, -804] | -0.01 [-0.04, +0.01] | +0.01 [-0.04, +0.05] | 0.19 |
| qwen | crossfl | B | -0.05 [-0.06, -0.04] | -0.01 [-0.02, +0.00] | -726 [-1158, -341] | -0.01 [-0.04, +0.01] | -0.03 [-0.07, +0.02] | 0.19 |
| gpt | native | A | -0.06 [-0.08, -0.04] | -0.06 [-0.10, -0.02] | -275 [-409, -153] | -0.07 [-0.11, -0.04] | +0.03 [-0.02, +0.08] | 0.23 |
| gpt | native | B | -0.11 [-0.13, -0.09] | -0.21 [-0.26, -0.17] | -413 [-541, -297] | -0.11 [-0.14, -0.07] | +0.01 [-0.04, +0.07] | 0.23 |
| gpt | crossfl | A | -0.07 [-0.09, -0.05] | -0.14 [-0.20, -0.09] | -240 [-314, -167] | -0.03 [-0.07, +0.01] | -0.01 [-0.05, +0.03] | 0.21 |
| gpt | crossfl | B | -0.07 [-0.09, -0.05] | -0.17 [-0.23, -0.11] | -234 [-313, -148] | -0.04 [-0.07, -0.01] | -0.01 [-0.06, +0.04] | 0.21 |
| all | native | A | -0.05 [-0.06, -0.04] | -0.02 [-0.04, +0.00] | -678 [-976, -411] | -0.04 [-0.06, -0.03] | +0.01 [-0.01, +0.04] | 0.20 |
| all | native | B | -0.06 [-0.07, -0.05] | -0.09 [-0.11, -0.07] | -429 [-619, -250] | -0.05 [-0.06, -0.03] | +0.01 [-0.02, +0.03] | 0.20 |
| all | crossfl | A | -0.06 [-0.07, -0.05] | -0.08 [-0.10, -0.05] | -724 [-961, -522] | -0.02 [-0.04, -0.01] | -0.00 [-0.03, +0.03] | 0.20 |
| all | crossfl | B | -0.06 [-0.07, -0.05] | -0.09 [-0.11, -0.06] | -480 [-700, -279] | -0.03 [-0.04, -0.01] | -0.02 [-0.05, +0.01] | 0.20 |
| all | both | A | -0.05 [-0.06, -0.05] | -0.04 [-0.06, -0.03] | -696 [-930, -479] | -0.04 [-0.05, -0.02] | +0.01 [-0.01, +0.03] | 0.20 |
| all | both | B | -0.06 [-0.06, -0.05] | -0.09 [-0.10, -0.07] | -450 [-601, -303] | -0.04 [-0.05, -0.03] | -0.00 [-0.02, +0.02] | 0.20 |

