# Hardcoded programs: static checker results (2026-10-22)

Checker: `src/hardcoded/static_checker.py` (rule-based, no LLM). Outputs: `output/gpt/meeting/{baseline,caution_a,caution_b}_hardcoded_static.json`.

## Definition

A program is **hardcoded** when the plan (which friends, in what order, at what times) is fixed in the source instead of being chosen by the program. That includes literal itineraries, and programs that replay one fixed plan with arithmetic, with or without window checks. It is **not hardcoded** when the program searches over plans (permutations or subsets, recursion or DFS, bitmask DP, memoization, or trying several orders). A one-friend program is also not hardcoded if it derives the meeting time from the availability window (with `max`/`min` or a comparison).

The rules are applied in order:

| Reason | Label | Rule |
|---|---|---|
| `literal` | hardcoded | answer times that do not appear in the problem text are written in string constants (docstrings ignored) |
| `search` | not | the program searches over plans (see above) |
| `fixed_plan` | hardcoded | no search, and the itinerary meets 2 or more friends |
| `derived` | not | one friend, and the time is derived with `max`/`min` or a comparison |
| `replay` | hardcoded | one friend, no derivation |
| `n/a` | — | the program did not run, or printed no meetings |

## Validation

- **Labels:** I put the 93 runnable GPT-OSS baseline programs in random order (seed 20261022) and labelled them by reading, in that order, until I had 10 hardcoded and 10 not hardcoded. That took 30 programs.
  - Sample of 20 — hardcoded: 66, 502, 210, 908, 73, 974, 372, 612, 88, 174; not hardcoded: 6, 831, 385, 900, 937, 629, 592, 482, 309, 225.
  - The other 10 labelled along the way — hardcoded: 118, 143, 912, 203, 624, 170, 137, 222, 575; not hardcoded: 956.
- **Agreement:** the checker matches **20/20** on the sample and **10/10** on the extra 10. These labels are mine and still need checking by a human.
- **Fixes made during development:**
  - A time-formatting helper's AM/PM `if` was being counted as deriving the time (example 73).
  - Example times in docstrings fired the literal rule (baseline 444, caution_b 624).
  - A list of `(action, arg)` steps was mistaken for a list of alternative orders (caution_a 940).
  - Alternative orders written as tuples containing variables were missed (caution_b 131).
- **Spot checks after the fixes:** I read all 7 caution_a/caution_b programs labelled `fixed_plan` that contain loops, and 8 randomly chosen programs labelled `search`. All were labelled as I would label them.

## Results (GPT-OSS, Meeting Planning, 300 outputs)

| Condition | Labelled | Hardcoded | literal | fixed_plan | replay | Not hardcoded | n/a |
|---|---|---|---|---|---|---|---|
| baseline | 93 | **52 (56%)** | 40 | 10 | 2 | 41 | 7 |
| caution_a | 93 | **13 (14%)** | 1 | 10 | 2 | 80 | 7 |
| caution_b | 89 | **6 (7%)** | 1 | 5 | 0 | 83 | 11 |

- The cautionary prompts almost eliminate literal itineraries (40 → 1 → 1). Fixed-plan programs fall less (10 → 10 → 5): GPT-OSS moves from pasting the answer to re-deriving times along an order it chose in its reasoning.
- **Accuracy:** in baseline, hardcoded programs are correct 34/52 (65%) and the rest 32/41 (78%). Under caution_a it is 11/13 vs 63/80; under caution_b, 6/6 vs 73/83.
- **The Gemini hardcoded judge agrees with the checker on only 42/93 baseline programs.** The judge flags 47 and the checker 52, but they overlap on just 24. Under caution_a the judge flags 4 and under caution_b 1, against 13 and 6 from the checker.

## Other models and tasks

A separate sweep (`/tmp/claude-1713869604/-local-ssd-hz466/19be6061-851b-41f3-8d0a-45a11cafcfae/scratchpad/sweep.py`) covered every program from all 3 models on Calendar, Meeting and ZebraLogic. It flagged programs that showed no search, contained answer values as literals, or were marked by the judge; I read every flagged program. It found **no** hardcoded Calendar or ZebraLogic program from any model, and **no** hardcoded DeepSeek or Qwen program on any task. Every DeepSeek/Qwen program that looked like it had no search was bitmask DP, enumeration, or a one-friend computation. The checker itself is Meeting-specific and was run only on GPT-OSS.
