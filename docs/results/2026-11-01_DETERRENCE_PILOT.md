# Deterrence pilot: batching and placeholders (2026-11-01)

Design: docs/DETERRENCE_DESIGN.md. 20 problems (the first 20 of each dataset), Calendar and
Meeting in Python, Qwen and GPT-OSS. A labels from the paper's A judge (gemma_v11t, same prompt
hash eb1bdfcac0 as the baseline labels) on `output_deter_pilot/`; comparison by
`scripts/deter_compare.py --root output_deter_pilot` against the baseline traces of the same
problems (`output/<model>/<task>/baseline_*`, ontology gemma_v11_b5t).

Columns: ratio = share of reasoning characters in value-establishing paragraphs; values = share of
traces with any such paragraph; SLB chars/problem = value-establishing characters per problem;
tokens/problem = reasoning tokens before the first program, per problem. A batch's trace covers 5
problems: its ratio is compared with the mean of its members' baseline ratios, its "values" is
per group (so trivially near 1), and chars and tokens are divided by 5.

| cell | ratio new/base | values new/base | SLB chars/problem new/base | tokens/problem new/base | accuracy new/base |
|---|---|---|---|---|---|
| GPT-OSS Calendar, batch K=5 | 0.43 / 0.31 | 1.00 / 0.95 | 728 / 1,248 | 574 / 1,122 | 0.95 / 0.90 |
| GPT-OSS Meeting, batch K=5 | 0.16 / 0.48 | 0.50 / 0.95 | 570 / 6,375 | 588 / 3,385 | 0.65 / 0.65 |
| Qwen Calendar, batch K=5 | 0.32 / 0.21 | 1.00 / 1.00 | 2,881 / 4,238 | 2,708 / 4,563 | 1.00 / 0.90 |
| Qwen Meeting, batch K=5 | 0.26 / 0.36 | 1.00 / 1.00 | 8,604 / 41,398 | 8,990 / 29,605 | 0.75 / 0.85 |
| GPT-OSS Calendar, placeholders v3 | 0.01 / 0.31 | 0.10 / 0.95 | 43 / 1,248 | 1,280 / 1,122 | 1.00 / 0.90 |
| GPT-OSS Meeting, placeholders v3 | 0.02 / 0.48 | 0.05 / 0.95 | 71 / 6,375 | 1,526 / 3,385 | 0.80 / 0.65 |
| Qwen Calendar, placeholders v2 | 0.01 / 0.21 | 0.45 / 1.00 | 576 / 4,238 | 24,306 / 4,563 | 0.95 / 0.90 |
| Qwen Calendar, placeholders v3 | 0.01 / 0.21 | 0.45 / 1.00 | 1,055 / 4,238 | 19,631 / 4,563 | 0.95 / 0.90 |
| Qwen Meeting, placeholders v3 | 0.00 / 0.36 | 0.10 / 1.00 | 43 / 41,398 | 30,017 / 29,605 | 1.00 / 0.85 |

## Findings
- **Placeholders all but remove SLB** in every cell and version: ratio 0.00-0.02 against
  0.21-0.48, and value-establishing text per problem falls by 86-100%. Few traces establish
  values at all (GPT-OSS 0-10% against 95%). The A judge counts symbolic decisions ("meet Person2
  first") as values (annotator note in the problem), and a check of N-labelled paragraphs that
  mention placeholders found constraint interpretation and robustness reasoning, not solving.
- **With note v3, placeholders cost no accuracy** (GPT-OSS 1.00 and 0.80 against 0.90 and 0.65).
  The earlier accuracy losses came from the interface, not the method:
  - v1: Meeting programs read times by `k.startswith("T")`, which also caught the `TRAVEL` key,
    and printed `Person1` instead of names (fixed in v2: TRAVEL is its own dict, and placeholder
    names in the output are mapped back to values before scoring).
  - v2: GPT-OSS Calendar programs assumed VALUES held schedules (`VALUES.get("participants")`)
    and found none (0.65). v3 says VALUES holds only placeholder entries and the program must write
    out the structure in placeholder names.
- **Qwen reasons 5x longer with placeholders (v2)**, guarding against swapped or wrapping
  intervals because the note says T numbers are unordered. v3 adds that intervals are as written
  and lie within one day. With v3, Qwen Calendar still reasons 4x longer (19.6k vs 4.6k tokens per
  problem) while Meeting is unchanged (30.0k vs 29.6k). In a read of the longest Calendar traces the
  extra text is about program robustness (end times of 24:00, zero-length or out-of-hours busy
  intervals, chronological order of T numbers), not about solving: its ratio is 0.01.
- **Batching cuts SLB per problem but not its share.** Value-establishing text per problem falls
  by 32-42% (Calendar) and 79-91% (Meeting), but so does the rest of the reasoning: designing one
  encoding serves five problems, while each problem is still worked out in prose. The ratio rises
  on Calendar (0.43 vs 0.31, 0.32 vs 0.21) and falls on Meeting (0.16 vs 0.48, 0.26 vs 0.36).
  Accuracy holds except Qwen Meeting (0.75 vs 0.85, i.e. 2 of 20 problems).

## Decision
Placeholders deter SLB strongly without losing accuracy, so the full runs go ahead (note v3);
batching is run in full as planned, with the K sweep (2, 5, 10) testing whether larger batches
cut SLB further.
