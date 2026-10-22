# SLB ontology labels for all traces (2026-10-22)

First full run of the ontology judges (`docs/SLB_ONTOLOGY.md`, tag `gemma_v1`) over all 3,600 traces (3 models × 4 tasks × 3 conditions × 100). Qwen Calendar baseline/caution_a and Meeting baseline are the vLLM re-runs (commit `3416eb1`); DeepSeek and Qwen Meeting use the fixed code extractor (`7261ef4`).

- **Per-trace labels:** `output/<model>/<task>/<cond>_ontology_gemma_v1.json` (A1, with_search, A3, ratio, A2, B, spec, C1, C2, flags; `b_source`/`c1_source` say whether a script or Gemma decided).
- **Raw judge outputs (not committed, 49 MB):** `output/ontology/judge_{a,b,c}_gemma_v1.shard{0,1}.jsonl`. Re-running `src/run_ontology_judges.py <a|b|c> --items all --tag gemma_v1` reuses them and judges only traces whose text changed.
- **Assembly:** `scripts/assemble_ontology_labels.py --tag gemma_v1` (env venv).
- **Compute:** Gemma 4 31B FP8 on 2 GPUs (flex 0 and 1): A 29,237 segments (786k paragraphs) ≈ 1 h 45 min; B 3,591 programs ≈ 45 min; C 3,600 traces ≈ 40 min; catch-up for changed traces ≈ 20 min.

## Reliability

**Not measured against human labels yet.** The reliability sets and labelling page are ready (`validation/reliability/`, `scripts/judge_agreement.py`). Evidence so far:

- **B vs the static checker (GPT-OSS Meeting, human-validated 30/30):** "hardcoded or partly fixed" vs not agrees on **261/275** programs (92/93 baseline, 86/93 caution_a, 83/89 caution_b). The checker's literal itineraries map to Gemma's *hardcoded* (40/41); its fixed-plan programs mostly to *partly fixed* (14/20), as the ontology intends.
- **Harry's spot check of A1 paragraph labels:** 10/10 agree (`validation/reliability/a1_verify.*`, 75 items, in progress).
- **A2 spot check:** 10 items (`validation/reliability/a2_verify.*`), in progress.
- **Suspicious:** DeepSeek and Qwen BlocksWorld have a ratio of 0.16–0.20, values in ~100% of traces and *interpret* in 41–64%, while the sweep readers estimated ~0.04–0.06. Gemma may count reasoning about the extra constraints as solving. Check BlocksWorld first when labelling.

## Results (% of 100 traces unless a count)

Columns: SLB ratio (mean); A1 values / properties / none; with search; A3 answer / check problem / check program / interpret; A2 complete; B hardcoded / partly fixed / steered / independent / n/a; spec change not required; C1 mismatches and C2 incorrect prose answers (count / traces with a complete prose answer); consistency flags.

| Cell | ratio | val | prop | none | search | ans | chp | chg | int | A2 cmpl | B hard | B part | B steer | B ind | B n/a | spec | C1 no | C2 no | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek/blocksworld/baseline | 0.20 | 100 | 64 | 0 | 70 | 80 | 99 | 55 | 57 | 12 | 0 | 1 | 0 | 99 | 0 | 5 | 1/11 | 5/11 | 0 |
| deepseek/blocksworld/caution_a | 0.20 | 100 | 78 | 0 | 79 | 86 | 99 | 66 | 64 | 9 | 0 | 2 | 0 | 98 | 0 | 2 | 1/8 | 3/8 | 0 |
| deepseek/blocksworld/caution_b | 0.17 | 99 | 61 | 1 | 62 | 78 | 95 | 49 | 47 | 9 | 0 | 1 | 0 | 98 | 1 | 0 | 2/7 | 2/7 | 0 |
| deepseek/calendar/baseline | 0.28 | 100 | 15 | 0 | 99 | 100 | 45 | 87 | 34 | 100 | 0 | 1 | 0 | 94 | 5 | 0 | 0/95 | 3/100 | 0 |
| deepseek/calendar/caution_a | 0.25 | 100 | 17 | 0 | 99 | 100 | 56 | 90 | 30 | 86 | 0 | 0 | 0 | 100 | 0 | 0 | 0/86 | 0/86 | 0 |
| deepseek/calendar/caution_b | 0.25 | 100 | 17 | 0 | 98 | 100 | 54 | 91 | 33 | 83 | 0 | 1 | 0 | 98 | 1 | 0 | 0/83 | 2/83 | 0 |
| deepseek/meeting/baseline | 0.36 | 98 | 95 | 2 | 97 | 98 | 97 | 97 | 4 | 92 | 0 | 1 | 1 | 91 | 7 | 0 | 2/87 | 2/91 | 0 |
| deepseek/meeting/caution_a | 0.32 | 100 | 94 | 0 | 99 | 100 | 97 | 99 | 1 | 70 | 0 | 0 | 1 | 93 | 6 | 0 | 2/67 | 1/70 | 0 |
| deepseek/meeting/caution_b | 0.33 | 100 | 97 | 0 | 97 | 100 | 99 | 97 | 3 | 79 | 0 | 0 | 1 | 93 | 6 | 0 | 0/76 | 1/77 | 0 |
| deepseek/zebralogic/baseline | 0.26 | 100 | 74 | 0 | 88 | 99 | 88 | 86 | 14 | 86 | 0 | 0 | 0 | 94 | 6 | 0 | 0/81 | 0/86 | 0 |
| deepseek/zebralogic/caution_a | 0.22 | 99 | 79 | 1 | 90 | 96 | 93 | 80 | 16 | 60 | 0 | 0 | 0 | 98 | 2 | 0 | 0/60 | 1/60 | 0 |
| deepseek/zebralogic/caution_b | 0.25 | 100 | 63 | 0 | 88 | 99 | 86 | 83 | 15 | 74 | 0 | 1 | 0 | 97 | 2 | 0 | 0/72 | 0/73 | 0 |
| gpt/blocksworld/baseline | 0.07 | 41 | 1 | 59 | 10 | 13 | 18 | 1 | 9 | 5 | 0 | 6 | 0 | 94 | 0 | 18 | 0/1 | 3/3 | 1 |
| gpt/blocksworld/caution_a | 0.09 | 35 | 4 | 65 | 10 | 17 | 10 | 0 | 8 | 4 | 0 | 8 | 0 | 92 | 0 | 13 | 1/2 | 2/4 | 2 |
| gpt/blocksworld/caution_b | 0.07 | 33 | 0 | 67 | 8 | 15 | 12 | 0 | 4 | 3 | 0 | 6 | 0 | 94 | 0 | 17 | 0/1 | 3/3 | 1 |
| gpt/calendar/baseline | 0.30 | 99 | 4 | 1 | 66 | 99 | 8 | 10 | 1 | 98 | 0 | 0 | 3 | 96 | 1 | 0 | 2/98 | 2/98 | 0 |
| gpt/calendar/caution_a | 0.24 | 84 | 7 | 15 | 65 | 83 | 24 | 9 | 1 | 81 | 0 | 2 | 2 | 94 | 2 | 0 | 4/81 | 3/81 | 0 |
| gpt/calendar/caution_b | 0.17 | 69 | 4 | 30 | 45 | 67 | 18 | 13 | 0 | 65 | 0 | 1 | 2 | 95 | 2 | 0 | 1/64 | 0/65 | 0 |
| gpt/meeting/baseline | 0.47 | 99 | 82 | 1 | 51 | 97 | 56 | 39 | 0 | 84 | 46 | 5 | 0 | 42 | 7 | 2 | 20/78 | 32/84 | 0 |
| gpt/meeting/caution_a | 0.31 | 88 | 64 | 12 | 37 | 79 | 46 | 28 | 0 | 67 | 0 | 14 | 1 | 78 | 7 | 0 | 32/63 | 21/63 | 0 |
| gpt/meeting/caution_b | 0.26 | 74 | 54 | 21 | 34 | 65 | 40 | 14 | 0 | 57 | 1 | 7 | 0 | 82 | 10 | 0 | 27/54 | 19/55 | 0 |
| gpt/zebralogic/baseline | 0.18 | 69 | 53 | 16 | 37 | 61 | 51 | 20 | 2 | 49 | 0 | 2 | 0 | 86 | 12 | 1 | 0/47 | 0/49 | 0 |
| gpt/zebralogic/caution_a | 0.18 | 71 | 48 | 18 | 40 | 66 | 49 | 20 | 0 | 51 | 0 | 3 | 0 | 89 | 8 | 1 | 0/49 | 1/51 | 0 |
| gpt/zebralogic/caution_b | 0.08 | 43 | 27 | 46 | 18 | 37 | 33 | 7 | 1 | 28 | 0 | 0 | 0 | 96 | 4 | 0 | 3/28 | 3/28 | 0 |
| qwen/blocksworld/baseline | 0.16 | 96 | 54 | 4 | 48 | 70 | 89 | 36 | 43 | 16 | 0 | 2 | 0 | 98 | 0 | 5 | 1/15 | 10/15 | 0 |
| qwen/blocksworld/caution_a | 0.16 | 100 | 49 | 0 | 51 | 68 | 99 | 35 | 47 | 14 | 0 | 1 | 0 | 99 | 0 | 3 | 0/11 | 5/11 | 0 |
| qwen/blocksworld/caution_b | 0.16 | 99 | 48 | 1 | 45 | 65 | 96 | 31 | 41 | 11 | 0 | 1 | 0 | 99 | 0 | 4 | 0/9 | 6/9 | 0 |
| qwen/calendar/baseline | 0.24 | 100 | 17 | 0 | 96 | 100 | 30 | 87 | 27 | 100 | 0 | 0 | 3 | 96 | 1 | 0 | 3/99 | 3/100 | 0 |
| qwen/calendar/caution_a | 0.20 | 100 | 5 | 0 | 94 | 99 | 38 | 81 | 26 | 97 | 0 | 1 | 0 | 98 | 1 | 0 | 1/96 | 3/97 | 0 |
| qwen/calendar/caution_b | 0.18 | 100 | 9 | 0 | 95 | 100 | 36 | 80 | 39 | 71 | 0 | 0 | 1 | 97 | 2 | 0 | 0/70 | 2/71 | 0 |
| qwen/meeting/baseline | 0.36 | 100 | 92 | 0 | 96 | 100 | 96 | 100 | 0 | 86 | 0 | 0 | 1 | 92 | 7 | 0 | 12/81 | 5/86 | 0 |
| qwen/meeting/caution_a | 0.31 | 100 | 90 | 0 | 95 | 98 | 94 | 97 | 0 | 72 | 0 | 0 | 0 | 91 | 9 | 0 | 7/68 | 2/70 | 0 |
| qwen/meeting/caution_b | 0.34 | 100 | 94 | 0 | 94 | 100 | 93 | 99 | 4 | 78 | 0 | 0 | 0 | 95 | 5 | 0 | 13/73 | 8/74 | 0 |
| qwen/zebralogic/baseline | 0.24 | 100 | 64 | 0 | 83 | 99 | 78 | 66 | 12 | 94 | 0 | 0 | 0 | 61 | 39 | 0 | 3/60 | 2/94 | 0 |
| qwen/zebralogic/caution_a | 0.16 | 97 | 65 | 2 | 71 | 70 | 81 | 26 | 10 | 53 | 0 | 0 | 0 | 56 | 44 | 0 | 1/29 | 1/53 | 1 |
| qwen/zebralogic/caution_b | 0.18 | 99 | 66 | 1 | 81 | 83 | 87 | 46 | 10 | 52 | 0 | 0 | 0 | 56 | 44 | 1 | 0/33 | 0/52 | 0 |

## Observations (pending reliability)

- **Solving in prose is near-universal outside GPT-OSS BlocksWorld.** DeepSeek and Qwen commit values in ≥96% of traces in every cell. GPT-OSS is the only model where the cautionary prompts clearly reduce it: traces with no values rise from 1% to 12% to 21% on Meeting and 1% to 15% to 30% on Calendar.
- **Programs almost never inherit the prose answer, except GPT-OSS Meeting.** Hardcoded programs appear only in GPT-OSS Meeting baseline (46%) and vanish under caution (0–1%), replaced by partly fixed programs (5% → 14% → 7%). Elsewhere B is independent or n/a in ≥90% of programs, so the prose solving is wasted rather than copied.
- **Steered programs are rare** (≤3% in any cell; GPT-OSS and Qwen Calendar, DeepSeek Meeting).
- **Specification changes cluster in GPT-OSS BlocksWorld** (13–18% "not required"), mostly altered goals or added actions; check these before reporting.
- **Prose answers are often wrong where the program is right.** GPT-OSS Meeting baseline: 32 of 84 complete prose answers fail the validator. Qwen BlocksWorld: 21 of 35 prose plans fail VAL.
- **Qwen ZebraLogic has 39–44% B = n/a:** the programs crash or print nothing (execution errors), so B and C1 are undefined there.
- **Few consistency flags** (5 traces in all), all in GPT-OSS BlocksWorld and Qwen ZebraLogic.
