# Code extraction and empty-plan fixes (2026-10-31)

Found while checking the B judge on second-FL programs (bx-13, bx-06; see
`2026-10-30_A_JUDGE_RELIABILITY.md`). Harry asked for both to be fixed.

**Extraction.** `split_reasoning_and_code` prefers a code block in the final answer (after the last
end-of-thinking marker), but it found blocks by scanning the whole trace. Unbalanced fences in the
thinking (e.g. a quoted "```python from z3 import *```", or a "```\nVariables: ...```" sketch) paired
out of phase, swallowed the answer's opening fence, and a draft or a one-line snippet from the thinking
was taken as the program. The answer is now scanned on its own (`src/execution/code_extractor.py`).
Re-extracting every stored trace changes 43 programs (native: Qwen 14, GPT-OSS 1; cross-FL: Qwen 16,
DeepSeek 12); each new program is the final answer's code. The Qwen Meeting-Z3 programs that are
just `from z3 import *` are traces that loop until the token limit and never reach an answer, so
they stay without a program.

**Empty plan.** A Python BlocksWorld program that exits cleanly and prints nothing now gives the
empty plan, which VAL checks like any other (`python_plan_result` in `src/run_execution.py`; the
evaluator treats `""` as a plan, `None` as no plan). It is valid only when the goal already holds:
p42 (all blocks on the table) now passes, a non-trivial instance still fails.

**Re-run.** `scripts/reexecute_changed.py output output_crossfl` re-ran only the changed programs
(`run_execution.execute_example`) and recomputed the plan fields from stored stdout, then re-scored
each patched file (backup of every execution/evaluation file before the patch:
`output_backup/extract_fix_2026-10-31/`, git-ignored). 68 records changed in 27 files; 40 are now
correct and none got worse. The judges re-labelled only the changed traces (their cache is keyed on
the text hash): `scripts/rejudge_changed.sh` on GPUs 1 and 2 (A 60 + 98 segments, B 15 + 38
programs, C 15 + 40 traces), then reassembly.

| run | records changed | correct before → after |
|---|---|---|
| output/gpt/zebralogic/baseline | 1 | 84 → 84 |
| output/qwen/calendar/caution_b | 3 | 95 → 96 |
| output/qwen/meeting/baseline | 1 | 88 → 89 |
| output/qwen/meeting/caution_a | 3 | 85 → 88 |
| output/qwen/meeting/caution_b | 3 | 93 → 96 |
| output/qwen/zebralogic/baseline | 1 | 58 → 59 |
| output/qwen/zebralogic/caution_a | 3 | 56 → 59 |
| output_crossfl/deepseek/blocksworld/baseline | 3 | 78 → 81 |
| output_crossfl/deepseek/blocksworld/caution_a | 12 | 74 → 76 |
| output_crossfl/deepseek/blocksworld/caution_b | 9 | 73 → 77 |
| output_crossfl/deepseek/calendar/baseline | 1 | 98 → 99 |
| output_crossfl/deepseek/calendar/caution_a | 1 | 98 → 99 |
| output_crossfl/deepseek/calendar/caution_b | 1 | 96 → 97 |
| output_crossfl/deepseek/meeting/baseline | 1 | 94 → 95 |
| output_crossfl/deepseek/meeting/caution_a | 1 | 88 → 89 |
| output_crossfl/deepseek/meeting/caution_b | 2 | 85 → 87 |
| output_crossfl/deepseek/zebralogic/caution_a | 1 | 97 → 98 |
| output_crossfl/gpt/blocksworld/baseline | 4 | 32 → 34 |
| output_crossfl/gpt/blocksworld/caution_a | 1 | 27 → 28 |
| output_crossfl/qwen/blocksworld/baseline | 2 | 64 → 66 |
| output_crossfl/qwen/blocksworld/caution_a | 3 | 67 → 67 |
| output_crossfl/qwen/blocksworld/caution_b | 4 | 67 → 67 |
| output_crossfl/qwen/calendar/baseline | 2 | 84 → 85 |
| output_crossfl/qwen/calendar/caution_a | 1 | 87 → 88 |
| output_crossfl/qwen/calendar/caution_b | 2 | 79 → 81 |
| output_crossfl/qwen/zebralogic/caution_a | 1 | 94 → 95 |
| output_crossfl/qwen/zebralogic/caution_b | 1 | 95 → 96 |

**Paper numbers (baseline traces) that moved:** programs that ran 1,788 → 1,791, inheriting 162 → 163
(steered 27 → 28); H3 ratio effect +0.005 → +0.007 per 10 points [-0.011, +0.022], no-solving traces
-0.08 → -0.09, inheriting programs -0.02 → -0.00 [-0.09, +0.07]; convergent check 87% of 1,311 → 88% of
1,314 complete prose answers match the output; caution prompts' token drop 696/450 → 689/443. H4
contrasts and R² are unchanged at the reported precision. Not updated (old text, waiting for the
rehaul): the intro's RQ3 numbers and the conclusion's "94% of programs formalize independently".
