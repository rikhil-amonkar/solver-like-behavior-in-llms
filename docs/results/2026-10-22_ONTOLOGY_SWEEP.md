# Ontology sweep: do the SLB nodes occur, and what do they miss? (2026-10-22)

Checks `docs/SLB_ONTOLOGY.md` against the stored reasoning chains.

## Method

- **Sample:** 108 traces, 3 per model × task × condition (36 cells). Each cell includes at least one incorrect trace where one exists (seed 0). Each packet holds the prompt, the reasoning before code, the extracted program, its output and correctness. Reasoning longer than 60k characters was cut in the middle (mostly DeepSeek/Qwen Meeting and BlocksWorld).
- **Labelling:** 9 LLM readers (Claude Opus and Sonnet subagents) each read every packet in their slice in full. For each trace they gave A1–C2 labels, a rough share of solver-like reasoning, places where a node didn't fit, and solver-like behavior the ontology doesn't name. 107 of 108 traces are labelled; one Qwen Meeting caution_b trace failed to label. Labels (no trace text, line references only) are in `validation/ontology_sweep_2026-10-22/labels.json`, along with the instructions and the sample index.
- **Prevalence:** frequent new candidates were then searched for by keyword across all 3,600 traces (table below). Keyword hits are loose upper bounds, not labels.
- **Caveat:** these labels are LLM readings. No human has checked them.

## 1. Do the existing nodes occur?

Counts over 107 traces (Calendar 27, Meeting 26, ZebraLogic 27, BlocksWorld 27). A1 and A3 can have several values per trace.

| Node | Cal | Meet | Zebra | BW | All | Verdict |
|---|---|---|---|---|---|---|
| A1 search | 20 | 19 | 19 | 4 | 62 | occurs |
| A1 direct derivation | 13 | 23 | 20 | 12 | 68 | occurs |
| A1 none | 2 | 3 | 5 | 14 | 24 | occurs (mostly BW) |
| A2 complete | 25 | 21 | 20 | 4 | 70 | occurs |
| A2 partial | 0 | 1 | 1 | 8 | 10 | occurs (mostly BW) |
| A2 abandoned | 0 | 1 | 1 | 1 | 3 | rare |
| A3 solve, then encode | 25 | 22 | 17 | 3 | 67 | occurs |
| A3 dry-run | 14 | 10 | 5 | 1 | 30 | occurs |
| A3 test against prose | 2 | 3 | 7 | 0 | 12 | occurs |
| B1 full hardcode | 0 | 1 | 0 | 0 | 1 | occurs (GPT-OSS Meeting: 40/93 baseline per the static check) |
| B2 fixed decision | 0 | 1 | 0 | 0 | 1 | occurs (static check: 10/93) |
| B2 derived constraint | 0 | 0 | 0 | 3 | 3 | occurs, but see 3.4 |
| B2 pruned encoding | 0 | 0 | 0 | 0 | 0 | **not observed** |
| B2 literal fallback | 0 | 0 | 0 | 0 | 0 | **not observed** |
| B3 none | 26 | 19 | 27 | 24 | 96 | dominant |
| C1 false | 1 | 6 | 5 | 2 | 14 | mostly crashes, not disagreement (see 3.6) |
| C2 false | 6 | 2 | 1 | 1 | 10 | occurs; Calendar errors come from misreading a preference |

Mean reader-estimated share of solver-like reasoning: DeepSeek Cal 0.44 / Meet 0.53 / Zebra 0.33 / BW 0.04; GPT-OSS 0.37 / 0.37 / 0.16 / 0.03; Qwen 0.21 / 0.35 / 0.18 / 0.06.

**Takeaways.** Every A node occurs. Pruned encoding and literal fallback were never seen, in this sample or in the full static sweep (`2026-10-22_HARDCODING_STATIC_CHECK.md`). Keep them only as hypothetical options, or drop them. B is almost always B3: outside GPT-OSS Meeting, the programs don't inherit the prose answer. The variety is in A.

## 2. Solver-like behavior the ontology misses

Grouped from 111 free-text candidate names. "Packets" counts sampled traces flagged by readers. "Keyword hits" is the share of all 3,600 traces matching a loose pattern (DS = DeepSeek, GPT = GPT-OSS).

| Candidate | What it is | Packets | Keyword hits (all traces) |
|---|---|---|---|
| **Uniqueness / satisfiability check** | Solving the instance only to confirm it has exactly one, or at least one, solution, often after the code is drafted. Has no effect on the program. | ~20 (ZebraLogic, BW) | Zebra: DS 52%, Qwen 45%, GPT 20% |
| **Program-output prediction** | Stating what the program/solver/planner will print, without hand-tracing it | ~15 | 49% overall (DS Meet 97%, Qwen Meet 85%) |
| **Feasibility / optimality arguments** | Proving a friend, pair or goal infeasible; capacity bounds; "can we meet more?"; dominance and greedy arguments. Facts about the solution set without fixed values. | ~20 (Meeting, BW) | "infeasible/impossible": 60%; Meeting optimality: DS 94%, Qwen 93%, GPT 57% |
| **Post-hoc verification** | Checking a prose answer clue by clue, or "compute it to check the code later" | ~15 | 58% overall, though the pattern also catches code checks |
| **Tie-break / secondary objective** | Choosing among equal optima (earliest slot, earliest finish), often by enumerating them | ~10 (Meeting, Cal) | Meet: DS 95%, Qwen 91%, GPT 38% |
| **Ambiguity resolved by solving** | Solving under each reading of an ambiguous constraint and keeping the one that gives a unique or feasible answer | 6 (Cal, Zebra) | not measured |
| **Domain pruning / derived quantities** | Free-interval computation, travel-time arithmetic, propagating equalities between attributes without placing them | ~8 | not measured |
| **Concealed solving** | Under a cautionary prompt, solving anyway and planning to omit it from the answer | 4 (Qwen Cal) | ≈0% for the phrasings tried; unconfirmed |

## 3. Where nodes don't fit

1. **"Not SLB: resolving ambiguity" conflicts with solving** (6 packets). When the reading is chosen by solving under each one, the trace is both excluded and solver-like.
2. **A1 has no option for a single candidate that is checked and accepted** (several Cal/Meet packets). "Search" needs a rejection, and "derivation" doesn't fit a guess. The search/derivation boundary is also fuzzy for case splits mixed with forced chains (most ZebraLogic packets).
3. **A3 has no option for solving to check the encoding** (≈15 packets: Zebra, BW). The order "draft code → solve in prose → rewrite code" breaks "before the program is drafted".
4. **B misses programs that search but whose answer is steered by the prose** (≈8 packets: DS Meeting ×4, DS/Qwen Calendar ×4). The tie-break, objective, preference reading or even iteration order is chosen so the search returns the prose answer. These are labelled B3 today, and a static check can't see them.
5. **B has no "specification change" option** (6 packets). Examples: falling back to dropping preferences when no slot fits (Cal); adding a non-standard action so a contradictory goal becomes satisfiable, which the planner then exploits (Qwen BW ×2); relaxing minimum durations after proving them infeasible, then hardcoding (GPT Meet). The PDDL row's "goal relaxed or altered → B2" also misfires when a constraint *requires* altering the goal (GPT BW ×3, A1 = none, which breaks the consistency rule).
6. **B3 is overloaded.** It covers "prose solving was wasted" and also "there was nothing to inherit" (A1 = none; all DeepSeek BW). Broken programs (crash, ignores the instance, typo) also end up as B3. C1 records "did not run" as false (most of the 14 C1 = false).
7. **Restating vs. computing** is clear for Meeting travel arithmetic, but unclear for free intervals, unit conversion, and derived initial-state facts in PDDL. In BW, counting parentheses or escaping JSON can look like a dry-run to a judge.

## 4. Proposed revisions

1. **Define SLB by the solution set, not just by values.** SLB is reasoning that establishes facts about the instance's solutions: which values satisfy the constraints, whether any or exactly one do, and which is optimal. Committing to values is one case. This brings in feasibility/optimality arguments and uniqueness checks.
2. **A1 Mode:** keep *search* and *derivation*. Add *check*: testing given candidate(s) without rejecting any (verification, a single guess, the format example as the answer). Add *property*: existence, infeasibility, uniqueness or optimality arguments without committed values. Optionally add *prune*: narrowing domains (free intervals, propagation) without committing.
3. **A3 Role:** add *verify the formalization* (solving to confirm the encoding admits one, or any, answer). Merge *dry-run* and *output prediction* into one role, with a flag for whether the code is actually traced. Add *select among optima* (tie-break / secondary objective).
4. **Exclusions:** keep ambiguity resolution as not SLB *unless* the reading is chosen by solving under it. Then it is A1 search.
5. **B:**
   - Split B3 into *B3 independent* (A1 ≠ none, prose wasted) and *B0 nothing to inherit* (A1 = none).
   - Add *B2 steered selection*: the program searches, but its tie-break, objective, preference reading or iteration order is chosen to reproduce the prose answer. This needs an LLM or a re-run with a perturbed order to detect.
   - Mark pruned encoding and literal fallback as unobserved.
   - Add a separate node, *B4 specification change*: the program relaxes, drops or adds constraints, goals or actions. Record whether a constraint required it.
   - Programs that crash or don't run get B = n/a, not B3.
6. **C:** C1 is n/a when the program doesn't run or prints nothing. Consider allowing C for A2 = partial (compare the decided part).
7. **Not worth a node yet:** concealed solving (4 packets, no keyword support). Re-check with a targeted judge question.

## Next steps

- Decide which revisions to adopt, then update `docs/SLB_ONTOLOGY.md`, the paper section and figure, and the A-judge prompt.
- To report node frequencies in the paper, have humans label a subset (e.g. 30 traces) to calibrate these LLM readings.
- Detecting steered selection: re-run the program with the candidate order shuffled and check whether the answer changes.
