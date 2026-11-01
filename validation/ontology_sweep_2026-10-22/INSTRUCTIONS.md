# Task: label reasoning traces against the solver-like behavior (SLB) ontology, and look for SLB the ontology misses

Read the ontology first: /local-ssd/hz466/solver-like-behavior-in-llms/docs/SLB_ONTOLOGY.md

Context: an LLM is given a natural-language constraint problem and asked to write a program (Python, Python+Z3, or PDDL as JSON for BlocksWorld) that a solver/executor runs. "Solver-like behavior" = reasoning that commits to or tests concrete values of decision variables (the slot; which friends/order/times; house assignments; the plan's action sequence) instead of just encoding the problem. Restating data/constraints, output format, parsing, code design, and resolving ambiguity are NOT SLB.

Each packet file contains: the prompt, the reasoning before code, the extracted program, its output, and correctness. Read every packet assigned to you in full (the reasoning is the main object; skim long repetitive parts but do not skip sections).

For EACH packet, produce one JSON object:
{
 "file": "<packet filename>",
 "A1": ["search"|"direct_derivation"|"none", ...],
 "A2": "complete"|"partial"|"abandoned"|null,
 "A3": ["solve_then_encode"|"dry_run"|"test_against_prose", ...],
 "B": "B1"|"B2_fixed_decision"|"B2_pruned"|"B2_derived"|"B2_literal_fallback"|"B3"|"no_program",
 "C1": true|false|null, "C2": true|false|null,
 "approx_slb_fraction": 0.0-1.0,   // your rough estimate of the share of the reasoning that is SLB
 "fit_problems": [ {"node": "...", "issue": "...", "quote": "<short verbatim quote, <=200 chars>"} ],
 "uncovered_slb": [ {"proposed_name": "...", "description": "...", "quote": "<short verbatim quote, <=300 chars>"} ],
 "notes": "<1-2 sentences, optional>"
}

Pay special attention to:
- "fit_problems": cases where a node's definition is ambiguous, where two options both seem to apply, where no option applies, or where the consistency rule (B1/B2 requires A1 != none) is violated. Say exactly what's wrong.
- "uncovered_slb": behavior that does the solver's job (commits to/tests values, prunes, reasons about feasibility/optimality, simulates execution, predicts the answer, verifies a solution, etc.) but that the ontology does not name or classifies badly. Examples of things to check for (not exhaustive, don't force them): feasibility/infeasibility proofs in prose; optimality arguments ("can we meet more friends?"); bounding/pruning the search space without committing values; verifying the program's output after the fact; predicting what the solver will output; simulating the planner; computing derived quantities (e.g. travel arithmetic) that are not decision variables; re-solving after a bug; solving a simplified sub-problem; reasoning about the gold answer format by solving. Also note non-SLB things that a judge would likely mislabel as SLB (or vice versa).
- Whether the "Not SLB" exclusions are sufficient, and whether "restating data" vs. "computing with data" boundary is clear in practice.

Write your output as a JSON list to the output path given in your assignment (use the Write tool). Then reply with a SHORT summary (<=250 words): counts per node, the top 3-5 fit problems, and the top 3-5 uncovered-SLB candidates with how many of your packets show each. Do not modify any other file.

## Revision (applies to all reruns)
- Keep every "quote" to at most 100 characters; prefer paraphrase plus a short anchor phrase over long verbatim excerpts. Do not reproduce long stretches of the traces in your reply or files.
- Save progress after EVERY packet: write the JSON list so far (valid JSON) to your output path, then continue. Your final reply must not repeat the labels; give only the short summary.

## Revision 2 (overrides the "quote" fields above)
- Do NOT copy any text from the traces into your output. Replace every "quote" field with "lines": "<start>-<end>" (line numbers in the packet file, as shown by the Read tool) and a one-sentence paraphrase in your own words.
- Save after every packet as before.
