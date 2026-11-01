# Deterrence full runs: batching and placeholders (2026-11-01)

Design and decisions: docs/DETERRENCE_DESIGN.md. Pilot: docs/results/2026-11-01_DETERRENCE_PILOT.md.
100 problems per cell (the paper's problems), Qwen and GPT-OSS, every dataset and FL except PDDL.
Placeholder note v3. A labels from the paper's A judge (gemma_v11t) on `output_deter/` (native FL)
and `output_deter_crossfl/` (second FL), compared with the baseline of the same problems in
`output/` and `output_crossfl/` (`scripts/deter_compare.py`). Paper: Section 6 and Figure 6
(`figures/deter.pdf`, from `scripts/deter_traces.py` then `scripts/paper_figure_deter.py`; numbers in
`output/paper/deter_numbers.json`).

## Pooled change from the baseline (Figure 6)
Same problems; 95% bootstrap CI over problems (batching: over batch groups). Batch members carry their
group's ratio and 1/K of its tokens.

| method | pairs | SLB tokens/problem | ratio | accuracy (points) | traces with SLB | reasoning tokens |
|---|---|---|---|---|---|---|
| Cautionary A | 2,000 | -23% [-29, -17] | -0.053 | +0.7 [-1.2, +2.6] | -4 pts | +7% |
| Cautionary B | 2,000 | -15% [-19, -11] | -0.058 | -0.4 [-2.4, +1.4] | -9 pts | +0% |
| Batching K=5 | 1,400 | -62% [-68, -55] | -0.022 [-0.045, +0.001] | -5.9 [-11.0, -0.5] | (per group) | -61% |
| Placeholders | 800 | -97% [-98, -96] | -0.246 (0.25 -> 0.005) | +2.6 [-0.5, +5.9] | 94% -> 15% | +45% (Qwen +54%, GPT-OSS -31%) |

On the placeholder cells, the cautionary prompts cut SLB tokens by 32% and 18%.
K sweep (GPT-OSS, Calendar and Meeting in Python): SLB tokens/problem -56%, -78%, -91% at K = 2, 5, 10;
accuracy +2, +6, +3 points (K = 10 Calendar: 5 problems got no program, 0.89 vs 0.98).

## Per cell
SLB chars/problem = characters of value-establishing paragraphs per problem (a batch's divided by K);
reasoning tokens/problem likewise.

| model | dataset | FL | condition | ratio new/base | SLB chars/problem new/base | reasoning tokens/problem new/base | accuracy new/base |
|---|---|---|---|---|---|---|---|
| GPT-OSS | Calendar | Python | batch_k10 | 0.29 / 0.30 | 403 / 1,232 | 348 / 1,196 | 0.89 / 0.98 |
| GPT-OSS | Calendar | Python | batch_k2 | 0.35 / 0.30 | 1,066 / 1,232 | 961 / 1,196 | 0.97 / 0.98 |
| GPT-OSS | Calendar | Python | batch_k5 | 0.35 / 0.30 | 763 / 1,232 | 655 / 1,196 | 1.00 / 0.98 |
| GPT-OSS | Calendar | Python | placeholder | 0.00 / 0.30 | 15 / 1,232 | 1,219 / 1,196 | 0.99 / 0.98 |
| GPT-OSS | Meeting | Python | batch_k10 | 0.09 / 0.45 | 128 / 5,509 | 215 / 3,005 | 0.81 / 0.66 |
| GPT-OSS | Meeting | Python | batch_k2 | 0.27 / 0.45 | 1,695 / 5,509 | 1,335 / 3,005 | 0.71 / 0.66 |
| GPT-OSS | Meeting | Python | batch_k5 | 0.17 / 0.45 | 582 / 5,509 | 560 / 3,005 | 0.76 / 0.66 |
| GPT-OSS | Meeting | Python | placeholder | 0.01 / 0.45 | 26 / 5,509 | 1,539 / 3,005 | 0.82 / 0.66 |
| GPT-OSS | ZebraLogic | Z3 | batch_k5 | 0.06 / 0.16 | 269 / 1,307 | 688 / 1,711 | 0.66 / 0.84 |
| Qwen | Calendar | Python | batch_k5 | 0.29 / 0.21 | 3,037 / 4,010 | 2,999 / 4,753 | 0.99 / 0.97 |
| Qwen | Calendar | Python | placeholder | 0.01 / 0.21 | 1,048 / 4,010 | 17,825 / 4,753 | 0.96 / 0.97 |
| Qwen | Meeting | Python | batch_k5 | 0.31 / 0.31 | 9,159 / 31,547 | 8,174 / 25,766 | 0.80 / 0.89 |
| Qwen | Meeting | Python | placeholder | 0.00 / 0.31 | 218 / 31,547 | 29,665 / 25,766 | 0.97 / 0.89 |
| Qwen | ZebraLogic | Z3 | batch_k5 | 0.34 / 0.22 | 5,382 / 6,323 | 4,348 / 6,228 | 0.42 / 0.59 |
| GPT-OSS | BlocksWorld | Python | batch_k5 | 0.18 / 0.18 | 366 / 1,461 | 462 / 1,753 | 0.22 / 0.34 |
| GPT-OSS | Calendar | Z3 | batch_k5 | 0.17 / 0.22 | 341 / 943 | 571 / 1,226 | 0.96 / 0.96 |
| GPT-OSS | Calendar | Z3 | placeholder | 0.00 / 0.22 | 20 / 943 | 1,181 / 1,226 | 0.95 / 0.96 |
| GPT-OSS | Meeting | Z3 | batch_k5 | 0.12 / 0.19 | 602 / 2,278 | 724 / 2,733 | 0.43 / 0.38 |
| GPT-OSS | Meeting | Z3 | placeholder | 0.00 / 0.19 | 10 / 2,278 | 1,694 / 2,733 | 0.36 / 0.38 |
| GPT-OSS | ZebraLogic | Python | batch_k5 | 0.08 / 0.24 | 323 / 2,095 | 718 / 2,151 | 0.60 / 0.86 |
| Qwen | BlocksWorld | Python | batch_k5 | 0.21 / 0.20 | 6,730 / 19,059 | 8,516 / 24,942 | 0.57 / 0.66 |
| Qwen | Calendar | Z3 | batch_k5 | 0.27 / 0.17 | 2,987 / 3,606 | 3,397 / 5,702 | 0.89 / 0.85 |
| Qwen | Calendar | Z3 | placeholder | 0.01 / 0.17 | 675 / 3,606 | 19,933 / 5,702 | 0.87 / 0.85 |
| Qwen | Meeting | Z3 | batch_k5 | 0.08 / 0.17 | 2,537 / 19,559 | 8,789 / 31,241 | 0.28 / 0.27 |
| Qwen | Meeting | Z3 | placeholder | 0.00 / 0.17 | 65 / 19,559 | 36,576 / 31,241 | 0.25 / 0.27 |
| Qwen | ZebraLogic | Python | batch_k5 | 0.25 / 0.20 | 6,186 / 7,568 | 6,777 / 8,107 | 0.80 / 0.95 |

## Findings
- **Placeholders all but remove SLB without costing accuracy**, in both models and both FLs (ratio
  0.00-0.01). GPT-OSS Meeting in Python gains the most (0.66 -> 0.82): of the 28 baseline failures
  placeholders fix, 13 had a program that inherited the reasoning answer (10 hardcoded, 3 partly
  fixed) and 6 had no output; 12 baseline successes fail. Qwen reasons longer (Calendar 3.5-3.75x),
  about program robustness rather than the solution.
- **Batching shortens all reasoning, not only SLB**, so the ratio barely moves (Qwen's rises), and
  it costs accuracy, most on ZebraLogic (-15 to -26 points in each model and FL) and on BlocksWorld
  in Python (GPT-OSS -12, Qwen -9).
- **Recommendation (paper):** keep the instance's values out of the prompt (placeholders, values bound
  at run time) when they separate from the structure; otherwise warnings remove about a quarter of SLB
  and batching saves tokens at a risk to accuracy.

## Process notes
- The cross-FL A judge was restarted as 4 shards (GPUs 1-4) after its first wave; with `--items <path>`
  all shards had written to one file, so `run_ontology_judges.py` now gives each shard its own file.
