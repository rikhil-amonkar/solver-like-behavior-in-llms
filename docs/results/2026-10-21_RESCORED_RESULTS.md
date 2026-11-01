# Rescored Results - 2026-10-21

Accuracy for all 36 runs re-computed from the stored inference outputs after fixing the evaluation.
Ratio and solver-like tokens are unchanged: they come from the stored chunking files, which were not re-judged.

Regenerate with `python scripts/generate_results_table.py`. The same script run on the outputs at commit 7444890 reproduces the previous table (paper Table 1) exactly.

## What changed

1. **Meeting Planning was not evaluated.** `evaluate_meeting_solution` accepted any non-empty list. It now simulates the itinerary (start location and time, travel times, each friend's location, availability window and minimum duration) and also requires meeting at least as many friends as the golden solution, since the task asks to meet as many as possible. All 100 golden itineraries pass.
2. **BlocksWorld evaluation ignored the golden PDDL.** `run_evaluation.py` passed an empty dict as the problem, so `plan_exists` defaulted to true and the golden domain/problem were never used. The plan was also found with the model's domain plus the *unconstrained* reference problem from the prompt (which differs from the golden problem in 53/100 instances), and VAL-checked against the model's own domain. Now the plan is found by local Fast Downward (lama-first) on the model's domain + problem, and VAL checks it against the golden domain + problem. Unsolvable instances count as correct only if the planner proves the model's PDDL unsolvable. Run on the golden PDDL itself, this scores 99/100: `blocksworld_p03_state_constraint3` cannot be proven unsolvable within 5 minutes, so no model can get it right.
3. **The executed code block was sometimes a draft from the thinking section.** The extractor took the longest tagged code block anywhere in the trace; for Qwen this was a block inside `<think>` in 16-25% of examples. It now prefers blocks after the end-of-thinking marker (`</think>`, `assistantfinal`, `<|channel|>final<|message|>`). This also moves the reasoning/code split for those examples, so `reasoning_before_code` in the execution files no longer matches what the stored chunking files judged.
4. The online planner (solver.planning.domains) is no longer the default, so API timeouts are not scored as model failures.

## Results

| Model | Metric | Calendar Base | Calendar Caut A | Calendar Caut B | Meeting Base | Meeting Caut A | Meeting Caut B | ZebraLogic Base | ZebraLogic Caut A | ZebraLogic Caut B | BlocksWorld Base | BlocksWorld Caut A | BlocksWorld Caut B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek | Accuracy | 0.93 ± 0.26 | 0.99 ± 0.10 | 0.97 ± 0.17 | 0.89 ± 0.31 | 0.91 ± 0.29 | 0.92 ± 0.27 | 0.94 ± 0.24 | 0.94 ± 0.24 | 0.96 ± 0.20 | 0.76 ± 0.43 | 0.76 ± 0.43 | 0.71 ± 0.46 |
|  | Ratio | 0.23 ± 0.17 | 0.21 ± 0.19 | 0.24 ± 0.19 | 0.37 ± 0.17 | 0.31 ± 0.16 | 0.31 ± 0.16 | 0.35 ± 0.24 | 0.25 ± 0.21 | 0.36 ± 0.24 | 0.08 ± 0.17 | 0.06 ± 0.13 | 0.07 ± 0.19 |
|  | Solver Tokens | 1,634 ± 1,593 | 1,886 ± 2,357 | 1,775 ± 1,834 | 12,916 ± 8,555 | 10,991 ± 8,009 | 11,015 ± 7,165 | 3,812 ± 4,181 | 3,258 ± 3,821 | 3,695 ± 4,361 | 1,305 ± 3,426 | 1,085 ± 2,495 | 987 ± 2,251 |
| GPT-OSS | Accuracy | 0.98 ± 0.14 | 0.97 ± 0.17 | 0.97 ± 0.17 | 0.66 ± 0.48 | 0.74 ± 0.44 | 0.79 ± 0.41 | 0.84 ± 0.37 | 0.87 ± 0.34 | 0.85 ± 0.36 | 0.52 ± 0.50 | 0.54 ± 0.50 | 0.45 ± 0.50 |
|  | Ratio | 0.54 ± 0.18 | 0.39 ± 0.20 | 0.35 ± 0.24 | 0.64 ± 0.19 | 0.43 ± 0.22 | 0.35 ± 0.23 | 0.25 ± 0.21 | 0.25 ± 0.21 | 0.10 ± 0.15 | 0.21 ± 0.32 | 0.15 ± 0.28 | 0.19 ± 0.28 |
|  | Solver Tokens | 641 ± 410 | 424 ± 409 | 322 ± 338 | 1,896 ± 2,098 | 840 ± 920 | 593 ± 606 | 420 ± 834 | 425 ± 687 | 130 ± 270 | 284 ± 422 | 198 ± 313 | 203 ± 349 |
| Qwen | Accuracy | 0.94 ± 0.24 | 0.97 ± 0.17 | 0.95 ± 0.22 | 0.82 ± 0.39 | 0.74 ± 0.44 | 0.81 ± 0.39 | 0.58 ± 0.50 | 0.56 ± 0.50 | 0.56 ± 0.50 | 0.71 ± 0.46 | 0.69 ± 0.46 | 0.69 ± 0.46 |
|  | Ratio | 0.26 ± 0.14 | 0.21 ± 0.17 | 0.24 ± 0.17 | 0.45 ± 0.23 | 0.36 ± 0.21 | 0.45 ± 0.23 | 0.35 ± 0.19 | 0.24 ± 0.18 | 0.32 ± 0.22 | 0.05 ± 0.13 | 0.06 ± 0.13 | 0.05 ± 0.14 |
|  | Solver Tokens | 945 ± 790 | 830 ± 773 | 281 ± 617 | 8,592 ± 6,727 | 6,149 ± 5,445 | 7,842 ± 7,222 | 1,771 ± 2,348 | 1,024 ± 1,706 | 1,206 ± 1,818 | 367 ± 882 | 348 ± 725 | 310 ± 612 |

## Accuracy before and after

| Model | Task | Base | Caut A | Caut B |
|---|---|---|---|---|
| DeepSeek | Meeting | 0.90 → 0.89 | 0.92 → 0.91 | 0.92 → 0.92 |
| DeepSeek | BlocksWorld | 0.78 → 0.76 | 0.72 → 0.76 | 0.69 → 0.71 |
| GPT-OSS | Meeting | 0.93 → **0.66** | 0.93 → **0.74** | 0.90 → **0.79** |
| GPT-OSS | BlocksWorld | 0.55 → 0.52 | 0.59 → 0.54 | 0.47 → 0.45 |
| Qwen | Calendar | 0.94 → 0.94 | 0.96 → 0.97 | 0.92 → 0.95 |
| Qwen | Meeting | 0.89 → 0.82 | 0.79 → 0.74 | 0.83 → 0.81 |
| Qwen | ZebraLogic | 0.57 → 0.58 | 0.55 → 0.56 | 0.55 → 0.56 |
| Qwen | BlocksWorld | 0.72 → 0.71 | 0.65 → 0.69 | 0.62 → 0.69 |

All other cells are unchanged.

GPT-OSS Meeting failures are mostly itineraries with wrong travel times, arrival times or too-short meetings; at baseline 47/93 of its Meeting programs hardcode the answer (`2026-09-27_HARDCODED_ANALYSIS.md`).

## Effect on RQ3

Across the 24 baseline→cautionary transitions (change in pooled ratio vs. change in accuracy):

| | Pearson r | Transitions with \|Δacc\| > 0.05 | of which drops |
|---|---|---|---|
| Previous evaluation | -0.07 | 8 | 7 |
| Rescored | **-0.42** | 5 | 2 |

Lowering the solver-like ratio now goes with higher accuracy. The largest gains are GPT-OSS on Meeting (+0.08 under Caut A, +0.13 under Caut B), where the ratio falls 0.64 → 0.43 / 0.35. The claim that Caut B lowers BlocksWorld accuracy for all three models no longer holds (DeepSeek -0.05, GPT-OSS -0.07, Qwen -0.02).
