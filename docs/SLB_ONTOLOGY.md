# Solver-like behavior (SLB) ontology

**Status (2026-10-30): final.** The nodes below are frozen; the judges and their measured reliability are in the last two sections. Still open: the full runs with the chosen judges (see Judges).

Adopted 2026-10-22; made more compact the same day after the sweep of 107 traces (`docs/results/2026-10-22_ONTOLOGY_SWEEP.md`). A3 (purpose: answer / check problem / check program / disambiguate) was dropped on 2026-10-29: the purposes were too niche to label reliably, and the judge over-assigned them. Each node gets its own judge (an LLM or a script). This replaces the single sound/solver-like judge.

## Unit and core definition

**Input:** one problem, the model's full reasoning before the code, and the program it wrote.

**Decision variables** are what the answer consists of:

| Task | Decision variables |
|---|---|
| Calendar | the slot (day, start, end) |
| Meeting | which friends to meet, in what order, at what times |
| ZebraLogic | the house assignments |
| BlocksWorld | the action sequence (plan) |

**Solver-like behavior** is reasoning that does the solver's job on this instance: assigning, testing or ruling out values of its decision variables. (Until 2026-10-29 arguments that a solution exists, does not exist, is unique or is optimal, without committing values, counted too, as A1 properties. They were dropped: rare, and too hard to label reliably.)

**Not SLB:** restating the problem's data or constraints, designing the encoding or code, output format, parsing, and interpreting the constraints. The exception is an interpretation chosen by solving under each reading; that is SLB (A1 values). Also not SLB (rules set 2026-10-29):
- checking that the encoding behaves as intended on a hypothetical plan or assignment;
- assuming or hedging about solvability ("we know a solution exists", "add an else branch in case there is none");
- a one-off check of what a constraint means against a single example value that was not obtained by solving ("does 11:30 AM count as morning? It should"). Actively enumerating or deriving candidates and testing them against the constraints is A1 values.

## A. Solving in prose (from the reasoning)

**A1. What it establishes.** Each paragraph is Values or not SLB; a trace is Values if any paragraph is. (The with-search flag and the Properties type were dropped on 2026-10-29.)
- **Values:** assigns, tests or rules out values of decision variables. This includes pruning, e.g. computing free intervals or ruling out a friend's window.
- **None:** A2 and B's inheritance labels don't apply.

**A2. Extent** (only with A1 = values).
- **Complete:** every decision variable gets a value, so a full answer is stated.
- **Partial:** only some decisions are made (e.g. which friends to drop, the order of two blocks). Any value solving short of a full answer is partial, including a tentative schedule that is later dropped: without solver-like behavior it would not be there. So A2 is complete or partial whenever A1 is values.

**Span:** the tokens of every A segment. The solver-like ratio is these tokens divided by all reasoning tokens.

## B. What the program does with it (from the program)

One label; **n/a** if the program doesn't run or prints nothing.
- **Hardcoded:** prints an answer it doesn't compute.
- **Partly fixed:** computes the answer, but some decisions are written into the source: a fixed order or assignment, a constraint deduced in prose, or options ruled out in prose left out. This counts even when the deduced constraint is already implied by the encoded clues (e.g. adding "house 2 is very short" next to "house 1 is not very short" in a two-house puzzle; decided 2026-10-30).
  Partly fixed is not necessarily a fault, unlike hardcoded (Harry, 2026-10-30). A hardcoded program is a performative formalization: the program only prints the prose answer. Prose reasoning written into a partly fixed program shrinks the solver's search space, and is sometimes necessary or preferred: PDDL cannot reason about numbers, so a BlocksWorld constraint stated numerically (e.g. stack heights summing to a value) must be turned into fluents in prose. Such programs are still labelled partly fixed; the paper discusses the distinction.
- **Steered:** searches, but its tie-break, objective, preference reading or iteration order is chosen so that the search returns the prose answer.
- **Independent:** none of the above. With A1 = none this is a pure encoding; with A1 ≠ none the prose solving was wasted.

(A specification-change flag was dropped on 2026-10-30: dropping, relaxing or adding constraints is a formalization error, not solver-like behavior.)

**Consistency rule:** hardcoded, partly fixed and steered require A1 = values. A program with one of these labels and A1 ≠ values means one of the two judges is wrong.

## C. Agreement (only when A2 = complete and the program ran)

- **C1:** does the answer reached in prose match the program's output?
- **C2:** is the prose answer correct, using the same validator as the program?

Otherwise n/a; a crash is not a mismatch. Both are scripts given the prose answer the A2 judge extracts, so they need no human agreement check; the extraction itself is checked with A2.

## How B looks in each formal language

| | Python (Calendar, Meeting) | Z3-Python (ZebraLogic) | PDDL (BlocksWorld) |
|---|---|---|---|
| Hardcoded | literal answer printed | literal grid printed; Z3 unused or ignored | domain written to force the plan (e.g. step-counter predicates allowing one sequence) |
| Partly fixed | fixed friend order, times recomputed; friends dropped in prose left out | assignments fixed as `x == k`; deduced facts in place of clues | actions or preconditions written to impose a chosen order |
| Steered | tie-break or objective tuned to the prose itinerary; friends listed so the first permutation is the prose answer | — (Z3 returns any model; rare) | — |
| What finds the answer | the model's own program | Z3 | the planner (Fast Downward), checked by VAL |

The BlocksWorld prompt includes the ground-truth problem PDDL, so hardcoding there can only appear in the domain.

## Judges

Gemma 4 31B-it (FP8, vLLM, temperature 0, thinking mode) where reading is needed; scripts everywhere else. Run with `src/run_ontology_judges.py --items all`, assembled per trace by `scripts/assemble_ontology_labels.py --a-tag … --b-tag … --c-tag …` into `output/<model>/<task>/<cond>_ontology_<tag>.json`. Every judged record carries the prompt's hash (`ph`), and a tag refuses to mix prompts.

| Node | Judge (tag) | How |
|---|---|---|
| A1 per paragraph | Gemma A judge, `gemma_v11t` (`prompts/judge/a_paragraphs.txt`, `--thinking 8192`) | labels every numbered paragraph of each 2k-token segment (`src/ontology_items.py`) V, P, VP or N; V and VP count as Values, P as not SLB (the prompt predates dropping properties; the values-only prompt v12 was less accurate) |
| A1 per trace; solver-like ratio | script | Values if any paragraph is; ratio = characters in Values paragraphs / all characters |
| A2 extent; prose answer | Gemma C judge, `gemma_v11c` (`prompts/judge/c_prose_answer_condensed.txt`, `--condense-a-tag gemma_v11t --condense-values-only`) | reads only the Values paragraphs and the program output; complete if it finds a full answer, else partial; none exactly when A1 is none (script) |
| C1 | script | parse the prose answer and the program output with the task parsers and compare; n/a ("unparsed", counted) when either does not parse |
| C2 | script | the task validators (VAL for BlocksWorld) on the prose answer (`scripts/validate_prose_answers.py`) |
| B = n/a | script | no program, failed run, or no output |
| B label | Gemma B judge, `gemma_b5t` (`prompts/judge/b_program.txt`, `--thinking 16384`) | problem, reasoning (head + tail), program, output |
| B cross-check, GPT-OSS Meeting | script (`src/hardcoded/static_checker.py`) | 30/30 against human labels |
| Consistency | script | flags B ≠ independent without A1 values, and A2 complete without a Values paragraph |

**Full runs.** The first full A run (2026-10-30, launched as `gemma_v11t`) read the prompt file after it had been overwritten by v12, so it is stored as `gemma_v12t` (with `gemma_v12c`, and assembled files `*_ontology_v12run_a12_c12.json`); it must be redone with v11 before results are final. The full B run with `gemma_b5t` is in progress (`scripts/run_full_b5t.sh`).

## Reliability

Details and per-item disagreements: `docs/results/2026-10-30_A_JUDGE_RELIABILITY.md`. Reference labels live in `validation/reliability/`.

| Node | Checked by | Result |
|---|---|---|
| A1 (paragraph Values vs not) | Harry, 70 paragraphs over 3 rounds + a properties check, rulings agreed in chat applied (`scripts/score_a1_rounds.py`) | gemma_v11t 66/70 (49/52 on items not paraphrased in the prompt); Values precision 20/22, recall 20/22. The v12 prompt used by the first full run: 62/70 (46/52), recall 16/22 |
| A2 (extent) | Harry's verified completes + script grounding + Claude reading the passages (traces are too long for a person) | round 1: 20/20; round 3: 19/20 (the miss follows from an A1 error) |
| B (program label) | Claude, blind, 20 traces balanced by predicted label; Harry, precision on 20 held-out programs with the judge's evidence shown (bprec2) | gemma_b5t 19/20 vs Claude (optimistic: its prompt examples came from these traces); Harry: hardcoded 10/10, partly fixed 10/10 (all 10 hardcoded are GPT-OSS Meeting, 9 of the 10 partly fixed BlocksWorld) |
| B n/a, C1, C2, consistency | scripts | deterministic; C's input (the extracted prose answer) is checked with A2 |

## Outside the ontology

- How the model treats the cautionary instruction (acknowledging it, planning to hide solving from the answer) is about compliance, not solving. Note it separately if needed.
- Truncated traces and missing programs: judge the reasoning (A); B and C are n/a.
