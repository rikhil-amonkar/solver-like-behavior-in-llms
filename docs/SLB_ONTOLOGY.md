# Solver-like behavior (SLB) ontology

Adopted 2026-10-22; made more compact the same day after the sweep of 107 traces (`docs/results/2026-10-22_ONTOLOGY_SWEEP.md`). Each node gets its own judge (an LLM or a script). This replaces the single sound/solver-like judge.

## Unit and core definition

**Input:** one problem, the model's full reasoning before the code, and the program it wrote.

**Decision variables** are what the answer consists of:

| Task | Decision variables |
|---|---|
| Calendar | the slot (day, start, end) |
| Meeting | which friends to meet, in what order, at what times |
| ZebraLogic | the house assignments |
| BlocksWorld | the action sequence (plan) |

**Solver-like behavior** is reasoning that establishes facts about the instance's solutions: which values satisfy the constraints (or fail them), or whether a solution exists, is unique, or is optimal. Committing to values is one case.

**Not SLB:** restating the problem's data or constraints, designing the encoding or code, output format, parsing, and interpreting the constraints. The exception is an interpretation chosen by solving under each reading; that is SLB (A3 interpret).

## A. Solving in prose (from the reasoning)

**A1. What it establishes.** More than one can apply.
- **Values:** assigns, tests or rules out values of decision variables. This includes pruning, e.g. computing free intervals or ruling out a friend's window. Flag **with search** if at least one candidate is rejected.
- **Properties:** existence, infeasibility, uniqueness or optimality of solutions, argued without committing values (e.g. "no schedule can meet all four", capacity bounds, dominance arguments).
- **None:** A2, A3 and B's inheritance labels don't apply.

**A2. Extent** (only with A1 = values).
- **Complete:** every decision variable gets a value, so a full answer is stated.
- **Partial:** only some decisions are made (e.g. which friends to drop, the order of two blocks).

**A3. Purpose.** More than one can apply.
- **Answer:** derive the answer, including choosing among equal optima (tie-breaks, secondary objectives).
- **Check the problem:** solve to confirm the instance is solvable or has a unique solution, typically to validate the encoding.
- **Check the program:** run the program by hand, predict its output, or compare it with the prose answer. Flag **traced** if the code is actually stepped through.
- **Interpret:** choose a reading of an ambiguous constraint by solving under each reading.

**Span:** the tokens of every A segment. The solver-like ratio is these tokens divided by all reasoning tokens.

## B. What the program does with it (from the program)

One label; **n/a** if the program doesn't run or prints nothing.
- **Hardcoded:** prints an answer it doesn't compute.
- **Partly fixed:** computes the answer, but some decisions are written into the source: a fixed order or assignment, a constraint deduced in prose, or options ruled out in prose left out.
- **Steered:** searches, but its tie-break, objective, preference reading or iteration order is chosen so that the search returns the prose answer.
- **Independent:** none of the above. With A1 = none this is a pure encoding; with A1 ≠ none the prose solving was wasted.

**Specification-change flag:** the program drops, relaxes or adds constraints, goals or actions (e.g. drops preferences when no slot fits; adds a PDDL action that makes a contradictory goal reachable). Record whether the problem required the change.

**Consistency rule:** hardcoded, partly fixed and steered require A1 = values. A program with one of these labels and A1 ≠ values means one of the two judges is wrong.

## C. Agreement (only when A2 = complete and the program ran)

- **C1:** does the answer reached in prose match the program's output?
- **C2:** is the prose answer correct, using the same validator as the program?

Otherwise n/a; a crash is not a mismatch.

## How B looks in each formal language

| | Python (Calendar, Meeting) | Z3-Python (ZebraLogic) | PDDL (BlocksWorld) |
|---|---|---|---|
| Hardcoded | literal answer printed | literal grid printed; Z3 unused or ignored | domain written to force the plan (e.g. step-counter predicates allowing one sequence) |
| Partly fixed | fixed friend order, times recomputed; friends dropped in prose left out | assignments fixed as `x == k`; deduced facts in place of clues | actions or preconditions written to impose a chosen order |
| Steered | tie-break or objective tuned to the prose itinerary; friends listed so the first permutation is the prose answer | — (Z3 returns any model; rare) | — |
| Specification change | preferences or minimum durations relaxed | clue dropped | goal altered or non-standard action added (check whether a constraint requires it) |
| What finds the answer | the model's own program | Z3 | the planner (Fast Downward), checked by VAL |

The BlocksWorld prompt includes the ground-truth problem PDDL, so hardcoding there can only appear in the domain.

## Judges

| Node | Judge | Status (2026-10-22) |
|---|---|---|
| A1, A2, A3 and the A span | LLM judge, cross-checked by `scripts/analyze_prose_search_outcome.py` | the judge prompt needs rewriting for this version; the scripts exist |
| A3 check the program | `scripts/analyze_prose_search_answer_position.py` (where the answer first appears) | partial (Calendar, Meeting, ZebraLogic) |
| B hardcoded / partly fixed, Python | `src/hardcoded/static_checker.py` | Meeting done (30/30 against human labels); Calendar rule to do |
| B steered | re-run the program with the candidate order shuffled and check whether the answer changes, plus an LLM check of tie-break/objective | to do |
| B, Z3 | static check: match each constraint to a clue; flag `x == k` facts that no clue states | to do |
| B, PDDL | LLM judge, or a diff against a reference domain | to do |
| Specification-change flag | LLM judge comparing the encoding with the problem | to do |
| C1, C2 | script: parse the prose answer, compare it with the output, run the validator | to do |

## Outside the ontology

- How the model treats the cautionary instruction (acknowledging it, planning to hide solving from the answer) is about compliance, not solving. Note it separately if needed.
- Truncated traces and missing programs: judge the reasoning (A); B and C are n/a.
