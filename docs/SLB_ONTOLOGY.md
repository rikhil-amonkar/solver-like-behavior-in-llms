# Solver-like behavior (SLB) ontology

Adopted 2026-10-22. Each node gets its own judge (an LLM or a script). This replaces the single sound/solver-like judge.

## Unit and core definition

**Input:** one problem, the model's full reasoning before the code, and the program it wrote.

**Decision variables** are what the answer consists of:

| Task | Decision variables |
|---|---|
| Calendar | the slot (day, start, end) |
| Meeting | which friends to meet, in what order, at what times |
| ZebraLogic | the house assignments |
| BlocksWorld | the action sequence (plan) |

**Solver-like behavior** is any part of the reasoning that commits to concrete values of decision variables. Restating the problem's data or constraints doesn't count; choosing or testing values does.

## A. Solving in prose (from the reasoning)

**A1. Mode.** More than one can apply.
- **Search:** tries candidate values and rejects at least one.
- **Direct derivation:** computes values step by step without exploring alternatives.
- **None:** no values are committed. A2, A3 and B are skipped.

**A2. Extent.**
- **Complete:** every decision variable gets a value, so a full answer is stated.
- **Partial:** some decisions are made (e.g. which friends to drop, the order) and the rest are left to the program.
- **Abandoned:** solving starts but stops without committing to anything, handing over to the program.

**A3. Role.** More than one can apply.
- **Solve, then encode:** solving happens before the program is drafted.
- **Dry-run:** the model runs its own program by hand.
- **Test against the prose answer:** the prose answer is used as the expected output to check or adjust the code.

**Span:** the tokens of every A segment. The solver-like ratio is these tokens divided by all reasoning tokens.

## B. What the program does with it (from the program)

- **B1. Full hardcode:** the program prints an answer it doesn't compute.
- **B2. Partial hardcode:** the program computes the answer, but some decisions are fixed in its source.
  - **Fixed decision:** an order, assignment or plan chosen in prose is written in; the program fills in only the rest.
  - **Pruned encoding:** friends, constraints or options ruled out in prose are left out of the encoding.
  - **Derived constraint:** facts deduced in prose are encoded in place of, or on top of, the problem's own constraints.
  - **Literal fallback:** a real search, with a pasted answer if the search fails.
- **B3. None:** the program solves the problem independently, so any solving in prose was wasted.

**Consistency rule:** B1 or B2 requires A ≠ none. A program marked B1/B2 with A = none means one of the two judges is wrong.

## C. Agreement (only when A2 = complete)

- **C1:** does the answer reached in prose match the program's output?
- **C2:** is the prose answer correct, using the same validator as the program?

## How B looks in each formal language

| | Python (Calendar, Meeting) | Z3-Python (ZebraLogic) | PDDL (BlocksWorld) |
|---|---|---|---|
| B1 full hardcode | literal answer printed | literal grid printed; Z3 unused or ignored | domain written to force the plan (e.g. step-counter predicates allowing one sequence) |
| B2 fixed decision | fixed friend order, times recomputed | assignments fixed as `x == k` | actions or preconditions written to impose a chosen order |
| B2 pruned / derived | friends or constraints dropped; deduced feasibility facts added | deduced facts added in place of clues | constraints left out of the domain; goal relaxed or altered |
| What finds the answer | the model's own program | Z3 | the planner (Fast Downward), checked by VAL |

The BlocksWorld prompt includes the ground-truth problem PDDL, so hardcoding there can only appear in the domain.

## Judges

| Node | Judge | Status (2026-10-22) |
|---|---|---|
| A1, A2 and the A span | LLM judge, cross-checked by `scripts/analyze_prose_search_outcome.py` | the judge prompt needs rewriting; the scripts exist |
| A3 | `scripts/analyze_prose_search_answer_position.py` | exists (Calendar, Meeting, ZebraLogic) |
| B, Python | `src/hardcoded/static_checker.py` | Meeting done (30/30 against human labels); Calendar rule to do |
| B, Z3 | static check: match each constraint to a clue; flag `x == k` facts that no clue states | to do |
| B, PDDL | LLM judge, or a diff against a reference domain | to do |
| C1, C2 | script: parse the prose answer, compare it with the output, run the validator | to do |

## Outside the ontology

- **Not SLB (judges should ignore it):** reasoning about the output format, parsing, code design, resolving ambiguous or contradictory constraints, and restating problem data.
- **Flagged separately:** changing the specification after judging the problem infeasible in prose (e.g. dropping a goal).
