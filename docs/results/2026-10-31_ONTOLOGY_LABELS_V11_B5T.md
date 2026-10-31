# SLB ontology labels, final judges (2026-10-31)

Native runs (3 models × 4 tasks × 3 conditions × 100 traces), assembled from the judges chosen on
2026-10-30: A = `gemma_v11t` (thinking 8192), B = `gemma_b5t` (thinking 16384), A2/C = `gemma_v11c`
(condensed to Values paragraphs). No judgement is missing: A covers all 29,237 segments, B all
3,591 traces with a program, C all 3,600 traces.

- **Per-trace labels:** `output/<model>/<task>/<cond>_ontology_gemma_v11_b5t.json`.
- **Raw judge outputs (not committed):** `output/ontology/judge_{a_gemma_v11t,b_gemma_b5t,c_gemma_v11c}.shard*.jsonl`.
- **Assembly:** `python scripts/assemble_ontology_labels.py --tag gemma_v11_b5t --a-tag gemma_v11t --b-tag gemma_b5t --c-tag gemma_v11c` (vllm-env, ~40 s, no GPU).
- **Cross-FL runs:** judged with the same tags; labels go to `output_crossfl/` (`scripts/run_crossfl_judges.sh`).

Notes:
- The ontology is values-only since 2026-10-30, so the `props` column is always 0.
- B is n/a (by script) when the program is missing, crashed or printed nothing. Qwen ZebraLogic's
  39–44 n/a are its execution errors (39–42 per run).
- BlocksWorld ratios are now 0.01–0.06 (DeepSeek and Qwen were 0.16–0.20 under `gemma_v1`), in line
  with the earlier sweep estimate of ~0.04–0.06. "Check DeepSeek and Qwen BlocksWorld A labels"
  should be re-scoped to these labels.
- B hardcoded is concentrated in GPT-OSS Meeting baseline (40); every other cell has at most 1.

## C fixes (2026-10-31, while writing Section 5)

C2/C1 were rescored after spot checks found answers counted as wrong that are not checkable:
- BlocksWorld: prose answers that are not plans ("null", a goal-state description) went to VAL
  and counted as wrong; "no plan exists" was counted as a plan. Now: no recognisable action ->
  n/a; a no-plan claim is right exactly when the instance is unsolvable; bare block numbers map to
  block<n>; a plan VAL cannot read (p10's token arguments) is n/a. Prose wrong fell from 99/182
  to 32/133.
- Meeting: 39 extracted itineraries failed only on format ("first step must be ...", unparseable
  step), now n/a. Of the 53 remaining wrong-travel-time cases, 19 have no matching leg in the
  reasoning (the C judge spliced two tentative itineraries), so Meeting's C2 "wrong" is an upper
  bound.

## Results (counts of 100 traces unless a fraction)

Columns: traces; SLB ratio (mean); A1 values / properties / none; A2 complete; B hardcoded / partly fixed /
steered / independent / n/a; C1 mismatches and C2 incorrect prose answers (count / traces
checked); consistency flags.

| Cell | n | ratio | val | prop | none | A2 cmpl | B hard | B part | B steer | B ind | B n/a | C1 no | C2 no | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek/blocksworld/baseline | 100 | 0.06 | 84 | 0 | 16 | 38 | 0 | 5 | 0 | 94 | 0 | 18/28 | 4/27 | 0 |
| deepseek/blocksworld/caution_a | 100 | 0.05 | 88 | 0 | 12 | 34 | 0 | 5 | 0 | 95 | 0 | 19/30 | 3/29 | 0 |
| deepseek/blocksworld/caution_b | 100 | 0.04 | 67 | 0 | 33 | 28 | 0 | 5 | 0 | 94 | 1 | 11/18 | 5/17 | 0 |
| deepseek/calendar/baseline | 100 | 0.21 | 100 | 0 | 0 | 100 | 0 | 1 | 2 | 91 | 5 | 0/95 | 3/99 | 0 |
| deepseek/calendar/caution_a | 100 | 0.17 | 100 | 0 | 0 | 100 | 0 | 0 | 0 | 100 | 0 | 0/100 | 1/100 | 0 |
| deepseek/calendar/caution_b | 100 | 0.18 | 100 | 0 | 0 | 100 | 0 | 0 | 1 | 97 | 1 | 0/99 | 2/100 | 0 |
| deepseek/meeting/baseline | 100 | 0.28 | 98 | 0 | 2 | 97 | 0 | 2 | 13 | 76 | 7 | 7/89 | 0/90 | 0 |
| deepseek/meeting/caution_a | 100 | 0.22 | 100 | 0 | 0 | 90 | 0 | 0 | 6 | 88 | 6 | 11/83 | 2/87 | 0 |
| deepseek/meeting/caution_b | 100 | 0.24 | 100 | 0 | 0 | 98 | 0 | 0 | 9 | 81 | 6 | 8/90 | 0/90 | 0 |
| deepseek/zebralogic/baseline | 100 | 0.22 | 100 | 0 | 0 | 98 | 0 | 0 | 0 | 94 | 6 | 0/92 | 0/97 | 0 |
| deepseek/zebralogic/caution_a | 100 | 0.16 | 99 | 0 | 1 | 85 | 0 | 0 | 0 | 98 | 2 | 0/84 | 3/85 | 0 |
| deepseek/zebralogic/caution_b | 100 | 0.21 | 100 | 0 | 0 | 95 | 0 | 1 | 0 | 97 | 2 | 0/93 | 1/95 | 0 |
| gpt/blocksworld/baseline | 100 | 0.01 | 7 | 0 | 93 | 2 | 0 | 4 | 0 | 96 | 0 | 1/1 | 0/0 | 3 |
| gpt/blocksworld/caution_a | 100 | 0.02 | 10 | 0 | 90 | 3 | 0 | 5 | 0 | 95 | 0 | 0/0 | 0/0 | 2 |
| gpt/blocksworld/caution_b | 100 | 0.01 | 7 | 0 | 93 | 1 | 0 | 4 | 0 | 96 | 0 | 0/0 | 0/0 | 2 |
| gpt/calendar/baseline | 100 | 0.30 | 99 | 0 | 1 | 98 | 0 | 0 | 0 | 99 | 1 | 2/98 | 2/98 | 0 |
| gpt/calendar/caution_a | 100 | 0.23 | 84 | 0 | 16 | 81 | 0 | 0 | 0 | 98 | 2 | 3/80 | 3/81 | 0 |
| gpt/calendar/caution_b | 100 | 0.16 | 66 | 0 | 34 | 65 | 0 | 0 | 1 | 97 | 2 | 1/64 | 0/65 | 0 |
| gpt/meeting/baseline | 100 | 0.45 | 98 | 0 | 2 | 85 | 40 | 11 | 0 | 42 | 7 | 19/72 | 25/68 | 1 |
| gpt/meeting/caution_a | 100 | 0.26 | 78 | 0 | 22 | 60 | 0 | 15 | 2 | 76 | 7 | 14/40 | 6/35 | 2 |
| gpt/meeting/caution_b | 100 | 0.23 | 68 | 0 | 32 | 56 | 1 | 7 | 0 | 81 | 10 | 22/48 | 10/41 | 0 |
| gpt/zebralogic/baseline | 100 | 0.16 | 60 | 0 | 40 | 47 | 0 | 2 | 0 | 86 | 12 | 1/45 | 2/47 | 0 |
| gpt/zebralogic/caution_a | 100 | 0.17 | 68 | 0 | 32 | 49 | 0 | 5 | 0 | 87 | 8 | 0/47 | 1/49 | 0 |
| gpt/zebralogic/caution_b | 100 | 0.07 | 37 | 0 | 63 | 28 | 0 | 1 | 0 | 95 | 4 | 2/27 | 2/28 | 0 |
| qwen/blocksworld/baseline | 100 | 0.04 | 62 | 0 | 38 | 41 | 0 | 10 | 0 | 90 | 0 | 21/30 | 9/29 | 0 |
| qwen/blocksworld/caution_a | 100 | 0.04 | 63 | 0 | 37 | 21 | 0 | 7 | 0 | 93 | 0 | 9/13 | 4/12 | 0 |
| qwen/blocksworld/caution_b | 100 | 0.03 | 63 | 0 | 37 | 27 | 0 | 7 | 0 | 93 | 0 | 16/21 | 7/19 | 0 |
| qwen/calendar/baseline | 100 | 0.21 | 100 | 0 | 0 | 100 | 0 | 0 | 3 | 96 | 1 | 3/99 | 3/100 | 0 |
| qwen/calendar/caution_a | 100 | 0.15 | 100 | 0 | 0 | 100 | 0 | 0 | 1 | 98 | 1 | 1/99 | 3/100 | 0 |
| qwen/calendar/caution_b | 100 | 0.13 | 100 | 0 | 0 | 100 | 0 | 0 | 1 | 97 | 2 | 3/98 | 4/100 | 0 |
| qwen/meeting/baseline | 100 | 0.31 | 100 | 0 | 0 | 100 | 0 | 0 | 8 | 85 | 7 | 27/91 | 11/92 | 0 |
| qwen/meeting/caution_a | 100 | 0.25 | 100 | 0 | 0 | 90 | 0 | 0 | 3 | 88 | 9 | 19/81 | 7/80 | 0 |
| qwen/meeting/caution_b | 100 | 0.30 | 100 | 0 | 0 | 98 | 0 | 2 | 5 | 88 | 5 | 21/90 | 11/88 | 0 |
| qwen/zebralogic/baseline | 100 | 0.22 | 100 | 0 | 0 | 100 | 0 | 2 | 0 | 59 | 39 | 3/61 | 4/95 | 0 |
| qwen/zebralogic/caution_a | 100 | 0.13 | 95 | 0 | 5 | 78 | 0 | 0 | 0 | 56 | 44 | 1/46 | 2/65 | 0 |
| qwen/zebralogic/caution_b | 100 | 0.15 | 94 | 0 | 6 | 91 | 0 | 2 | 0 | 54 | 44 | 1/54 | 4/78 | 0 |