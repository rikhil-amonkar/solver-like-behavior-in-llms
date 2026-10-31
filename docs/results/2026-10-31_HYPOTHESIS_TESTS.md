# Hypothesis tests on all runs (2026-10-31)

Data: assembled labels `*_ontology_gemma_v11_b5t.json` (A gemma_v11t, B gemma_b5t, A2/C gemma_v11c)
for the native runs (3 models × 4 tasks × 3 conditions × 100) and the cross-FL runs of Qwen and
GPT-OSS. Rows: `scripts/paper_ontology_stats.py --root output|output_crossfl`; tests:
`scripts/hypothesis_tests.py` (full tables in `2026-10-31_HYPOTHESIS_TESTS_raw.md`). 95% CIs are
bootstrap over problems. 6,000 traces.

**DeepSeek's cross-FL runs are excluded.** The API model behind `deepseek-v4-flash` changed between
the native runs (2026-08) and the cross-FL runs (2026-10): re-running 10 native Calendar and 10
native ZebraLogic prompts today, with the same settings (medium effort, 131072 max tokens), gives
traces 4-5x shorter (median 35k → 8k characters, 63k → 14k; shorter on 20/20). The cross-FL
DeepSeek traces are shorter by the same factor on every dataset, while Qwen's and GPT-OSS's are not.
DeepSeek therefore counts only in the native-only analyses (H1, H3 native).

## H1.1 SLB is common and takes a practically significant share of the reasoning — supported

Baseline condition:

| model | runs | traces with Values | mean ratio | SLB tokens/trace | share of reasoning tokens |
|---|---|---|---|---|---|
| DeepSeek | native | 96% | .19 | 6,123 | 23% |
| Qwen | native / cross-FL | 90% / 100% | .19 / .19 | 3,662 / 3,912 | 28% / 22% |
| GPT-OSS | native / cross-FL | 66% / 73% | .23 / .21 | 644 / 506 | 35% / 26% |

71% of baseline traces have ratio ≥ .10, 46% ≥ .20, 47% spend ≥ 1,000 tokens on SLB. Of the traces
with Values paragraphs, the program ignores the prose solution (B = independent) in 85% (DeepSeek),
73-74% (Qwen) and 50-57% (GPT-OSS): those tokens are redundant with what the program computes. The
only setting where SLB is rare is BlocksWorld-PDDL (51% of traces, ratio .04).

## H1.2 Kinds of SLB — supported, with clear frequency and harm differences

- **Extent (A2):** when a model solves in prose, it usually solves all of it: 80-95% of Values
  traces state a complete answer. The prose answer is wrong in 3-13% of them (C2).
- **Inheritance (B):** rare. Of 5,357 runnable programs, 54 are hardcoded (41 of them GPT-OSS native
  Meeting baseline), 221 partly fixed, 61 steered.
- **Harm:** inheritance passes prose errors to the program. When the prose answer is wrong, hardcoded
  and partly fixed programs are right 0% and 4% of the time; independent programs are right 36%.
  On average, though, inheriting programs are as accurate as independent programs for the same
  problem and model (hardcoded −.01 [−.14, +.12], partly fixed +.02 [−.05, +.09]; steered +.05
  [+.01, +.09], because steering only tunes a search that already works).

## H1.3 SLB does not hurt accuracy — supported (no harm; a small positive association)

Linear probability model with run fixed effects (model × task × FL × condition) and problem fixed
effects, so SLB is compared within a run and within a problem:

| predictor | coefficient on accuracy |
|---|---|
| solver-like ratio (0-1) | +.13 [+.04, +.23] (+.013 per 10 points) |
| any Values paragraph | +.07 [+.04, +.11] |
| program inherits (B) | +.04 [−.02, +.10] |

Per model and run set, the ratio coefficient's CI includes 0 everywhere (DeepSeek native −.29
[−.55, .00]). The cleanest evidence is causal, from H3: cautionary prompts cut the ratio by about a
quarter and leave accuracy unchanged (−.00 [−.02, +.02]). So SLB costs tokens without buying or
losing accuracy on average; its harm is local (prose errors in inheriting programs).

## H2 SLB depends on the FL, not the dataset — partly supported

Same problems, cross-FL minus native (Qwen and GPT-OSS, all conditions):

| dataset | FL change | Δ ratio | Δ traces with Values | Δ program inherits |
|---|---|---|---|---|
| BlocksWorld | PDDL → Python | **+.12** [+.11, +.14] | **+.36** | +.01 |
| Meeting | Python → Z3 | **−.15** [−.17, −.14] | −.10 | −.09 |
| Calendar | Python → Z3 | −.03 [−.04, −.02] | −.02 | .00 |
| ZebraLogic | Z3 → Python | +.02 [+.01, +.04] | +.06 | +.06 |

- The direction matches the imperative-FL hypothesis in all four datasets (Python has more SLB than
  Z3 or PDDL), and FL explains more of the ratio's variance than dataset (ΔR² .080 vs .041; condition
  .037, model .001).
- But the size depends on the dataset. Python vs Z3 is large only for Meeting; Calendar and ZebraLogic
  barely move. With the FL fixed, datasets still differ: in Python, Meeting .30 vs .15-.20 for the
  others; in Z3 they are flat (.14-.17).
- The big effects are where the FL takes the search away from the model: PDDL hands the whole search
  to the planner; Z3 hands Meeting's optimisation to the solver, while in Python the model has to write
  it (and pre-solves in prose to do so). Calendar's search is trivial in either FL, and ZebraLogic is
  solved by permutation in Python, so the FL matters little there.

Caveats: the cross-FL prompts differ in more than the FL (the Z3 prompts add coding steps; the
BlocksWorld-Python prompt lacks the reference PDDL). Cross-FL accuracy also falls sharply for Qwen
Meeting-Z3 (−.65, mostly programs that do not run) and rises for Qwen ZebraLogic-Python (+.38).

## H3 Cautionary prompts do not deter SLB — partly supported (reduce, not remove)

Paired with baseline, all models and runs: caution A reduces the ratio by .05 [−.06, −.05] and
caution B by .06, about a quarter of the baseline .20; SLB tokens by 450-700 per trace; traces with
Values by 4-9 points; inheriting programs by 4 points; accuracy unchanged. For the reasoning models
the share of traces with SLB barely moves (DeepSeek +.01/−.04, Qwen −.01/−.02); GPT-OSS responds
more (−.06 to −.21). So the prompts dent SLB but most traces still solve in prose.

## Suggested changes to the hypotheses

- **H1.1:** fix the threshold for "practically significant" before writing (e.g. ≥ 10% of reasoning
  tokens or ≥ 1,000 tokens per trace), and say "redundant" (the program recomputes it in 50-85% of
  cases) rather than "wasteful", which implies it has no benefit; H1.3 and H3 then show it has none.
- **H1.3:** state it as "SLB does not change accuracy on average, but inheriting programs pass on
  prose errors", and use the H3 intervention as the main evidence.
- **H2:** "the FL matters more than the dataset, most where the FL delegates search to a solver",
  i.e. the effect is FL × dataset, not FL alone. The plain version is too strong.
- **H3:** "cautionary prompting reduces SLB by about a quarter, without eliminating it or changing
  accuracy".
- **Possible H4:** SLB is model-general. Model explains almost none of the ratio's variance
  (ΔR² .001) and every model shows it, although GPT-OSS writes far fewer tokens.

## Limits

- Judge reliability was measured on native traces only (see `2026-10-30_A_JUDGE_RELIABILITY.md`);
  cross-FL rows rely on the judges transferring to Z3 Calendar and Meeting and to Python ZebraLogic
  and BlocksWorld.
- DeepSeek cross-FL excluded (above), so H2 rests on two models.

## Paper version (2026-10-31, later)
Harry: the hypotheses as reworded above, with model folded into H2 (FL, dataset and model) and the
cautionary prompts moved out of H3 into a separate Section 6 on deterring SLB. Section 5 uses
the baseline prompt only (2,000 traces), so its numbers differ slightly from the all-condition
tables above: `scripts/paper_figures_hypotheses.py` makes one figure per hypothesis and writes the
quoted numbers to `output/paper/hypothesis_numbers.json`. Baseline-only H1.3: ratio +0.007 per 10
points [-0.011, +0.022] (+0.005 [-0.013, +0.022] before the extraction and empty-plan fixes of
2026-10-31); H2 ΔR²: FL .123, dataset .057, model .008 (full .27).
