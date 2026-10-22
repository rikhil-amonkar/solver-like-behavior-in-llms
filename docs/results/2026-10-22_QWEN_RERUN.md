# Qwen re-run on vLLM and Meeting re-scoring (2026-10-22)

## What was re-run

Three Qwen files had been generated with Hugging Face `generate()` (model defaults: temperature 1.0, top_k 20, top_p 0.95), while the rest of Qwen used vLLM (temperature 0.7, top_p 0.9). See `2026-10-22_TRACE_HEALTH.md`. They were regenerated on vLLM with the current settings:

| File | GPU(s) | Notes |
|---|---|---|
| Calendar baseline | 7 | 100/100 |
| Calendar caution_a | 7 | 100/100 |
| Meeting baseline | 4 and 7 | run in parts (problems 1–48 on GPU 4, 51–100 then 49–50 on GPU 7), merged with `scripts/merge_inference_parts.py` |

- **Same problems and prompts:** every re-run trace has the same problem text and prompt length as the original.
- **Old files kept:** they are in `output_backup/qwen_hf_2026-08/` (git-ignored) and in git history.
- **Judge outputs removed for these three files:** their chunking, re-keyed chunking and hardcoded-judge files were removed, because they describe the old traces. The `*_ontology_gemma_v1.json` files from another session were left in place; for these three files they describe the old traces.

## Code-extraction bug (affects Meeting only)

`select_best_code_block` treated any code block containing a line that starts with `maybe`, `actually` or `wait` as leaked reasoning. Meeting programs often have a variable named `wait` (`wait = meeting_start - arrival`). The final answer was then rejected, and a placeholder sketch from the thinking (e.g. `import itertools\n...`) was executed instead. Fixed in `src/execution/code_extractor.py`, with a test in `tests/execution/test_code_extraction.py`. The fix changes the extracted program for 6 DeepSeek and 34 Qwen Meeting examples in the stored files, and none for GPT-OSS or any other task.

## Accuracy after the re-run and the fix

| Model | Task | Baseline | Caution A | Caution B |
|---|---|---|---|---|
| DeepSeek | Calendar | 0.93 | 0.99 | 0.97 |
| DeepSeek | Meeting | 0.92 (was 0.89) | 0.93 (was 0.91) | 0.93 (was 0.92) |
| GPT-OSS | Calendar | 0.98 | 0.97 | 0.97 |
| GPT-OSS | Meeting | 0.66 | 0.74 | 0.79 |
| Qwen | Calendar | **0.97** (was 0.94, HF) | 0.97 (was 0.97, HF) | 0.95 |
| Qwen | Meeting | **0.88** (was 0.82, HF) | **0.85** (was 0.74) | **0.93** (was 0.81) |

How the old and new Qwen Meeting baselines compare:
- Old run (HF, temperature 1.0), re-scored with the fix: 0.91.
- New run (vLLM, temperature 0.7): 0.88.

So the extraction bug explains most of the old Qwen Meeting numbers; the change of engine moves baseline accuracy by only −0.03.

## What changes in the paper

- **Main table:** Qwen Calendar baseline 0.94 → 0.97; Qwen Meeting 0.82/0.74/0.81 → 0.88/0.85/0.93; DeepSeek Meeting 0.89/0.91/0.92 (as rescored 2026-10-21) → 0.92/0.93/0.93.
- **RQ3's "Qwen Meeting under Cautionary A, 0.82 → 0.74" no longer holds:** it is now 0.88 → 0.85, and Cautionary B gives 0.93.
- **The Ratio and #Tokens rows for the three re-run files need new judge outputs.** Judging is on hold.
