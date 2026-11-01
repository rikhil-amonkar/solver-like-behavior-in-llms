# Health of stored reasoning chains (2026-10-22)

Covers 36 inference files (3 models × 4 tasks × 3 conditions, 100 problems each, 3,600 traces). The check script is `scripts/check_trace_health.py`.

## Fine

- **Complete and consistent.** Every file has 100 examples. The problem IDs are identical across all models and conditions within each task, with no duplicates.
- **No empty or errored traces.** All 3,600 have reasoning.
- **Cautionary suffixes were applied exactly.** Relative to baseline, every caution_a prompt is longer by a fixed amount per model (DeepSeek +525, GPT-OSS +521, Qwen +564 tokens) and every caution_b prompt likewise (+343 / +345 / +361).
- **The reasoning/answer split works.** No `reasoning_before_code` is empty, and only 16 equal the whole trace (no separate final answer). The split keeps only the end-of-reasoning marker (`assistantfinal`, `<|channel|>final<|message|>` or `</think>`), never the final answer text. The final code often appears verbatim inside DeepSeek and Qwen reasoning because they draft it while thinking and then repeat it. That is model behavior, not a split error.
- **BlocksWorld answers are JSON** (`domain_file`, `problem_file`), not fenced code blocks. That explains why most BlocksWorld traces have no code fences.

## Problems

### 1. Two inference engines with different sampling (the main issue)

| Engine | Sampling | Files |
|---|---|---|
| Hugging Face `generate()`, before 2026-08-26 (commit `bf8ea2d`) | model defaults: Qwen T=1.0, top_k=20, top_p=0.95; GPT-OSS T=1.0, top_p=1.0 | GPT-OSS Calendar, Meeting, ZebraLogic (all conditions); Qwen Calendar baseline + caution_a; Qwen Meeting baseline |
| vLLM | T=0.7, top_p=0.9 | GPT-OSS BlocksWorld; Qwen BlocksWorld, ZebraLogic; Qwen Calendar caution_b; Qwen Meeting caution_a + caution_b |
| DeepSeek API (thinking on, `reasoning_effort=medium`) | provider defaults | all DeepSeek files |

- **Qwen Calendar and Qwen Meeting mix engines across conditions.** The baseline-vs-caution comparisons there (RQ2/RQ3) are confounded with a change in sampling temperature (1.0 → 0.7).
- **GPT-OSS is consistent within each task but not across tasks.** BlocksWorld used vLLM at T=0.7, the other tasks used HF at T=1.0. This affects cross-task comparisons such as RQ1's task ranking.
- **The paper should state the sampling settings,** whichever way this is resolved.

### 2. Traces that hit the token limit

There are 9 such traces (out of 3,600), all under a cautionary prompt. 7 of the 9 are degenerate repetition loops.

- **DeepSeek:** BlocksWorld caution_a `p45_baseline_constraint45`, caution_b `p48_action_constraint32` (both loops); Meeting caution_a 835.
- **Qwen:** BlocksWorld caution_a `p19_state_constraint15`; Meeting caution_a 831, 908, 352; Meeting caution_b 901, 335 (all loops except 352/901, whose last 300 lines are near-identical).

None of them has a final answer, but code was still extracted from drafts inside their reasoning. They should count as failures and be flagged, not judged as normal traces.

### 3. Programs with no extracted code

16 in total: Qwen Meeting 9, GPT-OSS Calendar 4, GPT-OSS Meeting 2, DeepSeek BlocksWorld 1. Their reasoning is still usable for the reasoning-side nodes (A) of the ontology, but not for the program-side nodes (B, C).

## Recommendation

- **Re-run (needed):** Qwen Calendar baseline + caution_a and Qwen Meeting baseline on vLLM with the current settings (300 traces). This removes the engine confound inside Qwen's condition comparisons. Qwen 27B fits on GPU 7.
- **Re-run (optional):** GPT-OSS Calendar, Meeting and ZebraLogic on vLLM (900 traces), to match its BlocksWorld settings and make cross-task comparisons clean. gpt-oss-120b already ran on vLLM for BlocksWorld.
- **No re-run:** DeepSeek; the 9 truncated traces (flag them as failures); the 16 programs with no extracted code (judge reasoning only).
