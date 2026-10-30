# A judge reliability (2026-10-29/30)

Ontology changes on 2026-10-29: the with-search flag and A1 properties were dropped; solver-like
behavior is value solving only (a paragraph is Values or not SLB).

## A1 (paragraph Values vs not), against Harry's labels

60 paragraphs from rounds 1-3 (round 3 was balanced by judge prediction); rulings agreed in chat
are applied (`scripts/score_a1_rounds.py`, CORRECTIONS). Gemma 4 31B-it, FP8, temperature 0.

| judge | all 60 | not paraphrased in its prompt | Values precision | Values recall |
|---|---|---|---|---|
| gemma_v7 | 53 | 47/53 | 14/17 | 14/18 |
| gemma_v9 | 53 | 42/44 | 14/17 | 14/18 |
| gemma_v9t (thinking) | 56 | 42/44 | 15/16 | 15/18 |
| gemma_v10t (thinking) | 58 | 43/44 | 17/18 | 17/18 |
| **gemma_v11t (thinking)** | **58** | **43/44** | 16/16 | 16/18 |

With the 10 Properties-check paragraphs added (70), scored as the final ontology does (Values = V
or VP, vs not; `scripts/score_a1_rounds.py` "binary"), v11t gets 66/70 (49/52 not paraphrased in its
prompt; Values precision and recall 20/22); a Values-only prompt (gemma_v12t) was worse (63/70,
recall 16/22). Chosen: **gemma_v11t**, reading V and VP as Values and P as not SLB. Thinking mode:
`--thinking 8192`.

**The first full A run used the wrong prompt.** It was launched as `gemma_v11t` after the prompt
file had been overwritten with v12 (commit 74fb5f4), and its labels are V/N only. Scored with
`python scripts/score_a1_rounds.py full:gemma_v12t` it gets 62/70 (46/52), Values recall 16/22,
like v12. Its outputs were renamed `gemma_v12t` / `gemma_v12c`, the v11 prompt restored, and the
runner now stores a prompt hash per record and refuses to mix prompts under one tag. The A and
A2 full runs must be redone with v11.

## A2 (extent), judged from v11t's Values paragraphs (gemma_v11c, `--condense-values-only`)

Harry can only verify "complete" by hand (traces are too long), so partial/none were checked by
script (`scripts/check_a2_against_output.py --traces`: is the program's answer, or the extracted
prose answer, written out in the reasoning?) plus Claude reading the passages the script points to.

- Round 1 (20 traces): all 10 of Harry's verified completes are judged complete (incl. e14, e16).
  The 3 disagreements with his unverified labels (e03, e10, e13: partial/none, judge complete)
  were read by Claude; each states a full answer (e03 plan = planner's; e10 full grid with a
  uniqueness argument; e13 itinerary derived step by step), so the judge is right on 20/20.
- Round 3 (20 traces, balanced 7/7/6 by gemma_v8): 9 complete, 4 partial, 7 none by v11c.
  Complete: 6 grounded by script, 3 read by Claude (meeting 546, BlocksWorld p17, p97: plans
  written in words) - all confirmed. Partial/none: the program's answer is not written out in any
  (one script hit was a false positive, a restated attribute list). Claude disagrees on 2:
  ZebraLogic 6x5-3 (none; commits Carol=2, fish=2, Kailyn=4 -> partial) and meeting 900 (none;
  sketches then drops a schedule -> partial or none). 18/20.

These A2 checks are script + second-model (Claude), not human, except the verified completes.

## Summary (2026-10-30)

| Node | Checked by | Result |
|---|---|---|
| A1 | Harry (70 paragraphs) | gemma_v11t 66/70; precision and recall of Values 20/22 |
| A2 | Harry's verified completes + script + Claude | 20/20 (round 1), 19/20 (round 3, under the final rule that any value solving is at least partial; the miss is an A1 error) |
| B | Claude, blind (20) | gemma_b5t 19/20, optimistic; Harry's held-out precision set bprec2 pending |
| C1, C2 | scripts | no agreement check needed |

## B (program label), gemma_b3t (thinking; specification-change flag dropped 2026-10-30)

Harry cannot read whole traces, so B agreement is measured against Claude's labels (made blind to
the judge, by reading each program and searching the reasoning for why an order or constraint was
chosen) on the 20-trace round-2 sheet, balanced 5/5/5/5 by gemma_b2t predictions
(`validation/reliability/claude_b_labels_br2.json`).

gemma_b3t agrees on 17/20 (gemma_b2t also 17/20). Per label (precision / recall):
hardcoded 5/5, 5/5; partly fixed 3/4, 3/4; steered 4/4, 4/5; independent 5/7, 5/6.
Disagreements:
- br2-10 (Claude steered, judge independent): the friends dict is ordered so the first DFS path
  is the prose schedule ("we can control to find our manual schedule by ordering friends").
- br2-13 (Claude independent, judge partly fixed): "would rather not meet on Tuesday" encoded as
  a hard exclusion; Claude reads this as a preference interpretation, not prose solving.
- br2-00 (Claude partly fixed, judge independent; borderline): stacking restricted to table
  blocks because "a three-block stack sums to 6", a deduction replacing the sum constraint.

Harry will separately check precision of hardcoded and partly fixed with the judge's evidence
shown (as for the B examples, where he agreed 13/13).

## C

C1 and C2 are scripts on the prose answer extracted by the A2 judge (C1 parser comparison, no
Gemma fallback; C2 the task validators), so they need no agreement check; the extracted answer
is checked with A2 above.

### B prompt revisions (2026-10-30)

Harry's precision marks on the first set (bprec-00, 02, 03 are independent: a restriction read off
the goal, a conflict resolved as the problem instructs, an added action) showed the judge counting
choices made by READING the problem as inherited. The prompt now says only decisions the prose had
to SOLVE for count, with examples on both sides (gemma_b4t, then gemma_b5t, thinking 16384).
Claude relabelled br2-02 and br2-07 (stray day word read as a preference) as independent under this
rule. Against Claude's labels on the 20 round-2 traces: b3t 15/20, b4t 17/20, **b5t 19/20**
(only br2-07 differs: judge steered). The b5t prompt examples were written from these traces, so
19/20 is optimistic; Harry's fresh precision set (bprec2, 10 hardcoded + 10 partly fixed by b5t,
no overlap) is the held-out check. b5t still calls bprec-00 partly fixed.
