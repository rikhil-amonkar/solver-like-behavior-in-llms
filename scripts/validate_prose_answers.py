#!/usr/bin/env python3
"""
C2: is the prose answer correct? Runs the C judge's prose answers (rewritten in the
program-output format) through the same parsers and validators that score programs.

- Calendar / Meeting: parse_output_by_task + constraint evaluator (Meeting also checks
  it meets as many friends as the golden itinerary).
- ZebraLogic: parsed grid must equal the golden grid.
- BlocksWorld: the prose plan is validated with VAL against the golden domain and problem.

Writes <judge_c file>.c2.json: {id: {"c2": true|false|null, "detail": ...}}; null when
the extent is not complete or the answer does not parse.

Usage:
    python scripts/validate_prose_answers.py validation/reliability/judge_c_gemma_v1.jsonl validation/reliability/programs.json
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from execution.output_formatter import parse_output_by_task
from general.io_utils import load_constraints_json, load_problems_json, load_problems_with_solutions
from run_evaluation import evaluate_solution
from evaluation.blocksworld_eval import rename_plan_actions
from inference.code_executor_pddl import run_val_validator

VAL = str(REPO / "repos/VAL/build/bin/Validate")


FORMAT_ERRORS = ("first step must be", "unparseable step", "solution cannot be empty")
BW_ACTIONS = {"pickup", "putdown", "stack", "unstack"}  # every golden BlocksWorld domain
NO_PLAN = re.compile(r"\b(no (valid )?(plan|solution)|unsolvable|impossible|not (reachable|achievable|solvable))\b", re.I)


def prose_plan(answer):
    """A BlocksWorld plan as action tuples with normalised names (pick-up -> pickup), written as
    '(unstack a b)' or 'unstack a b' lines; [] if the answer only says no plan exists; None if
    it states neither (2026-10-31: such answers were sent to VAL and counted as wrong)."""
    text = "\n".join(l for l in (answer or "").splitlines() if not l.strip().startswith(";"))
    parts = re.findall(r"\(([^()]+)\)", text) or text.splitlines()
    acts = []
    for p in parts:
        tok = p.lower().replace(",", " ").split()
        if tok and re.sub(r"[-_]", "", tok[0]) in BW_ACTIONS:
            # every problem names its blocks block<n>; prose sometimes writes just the number
            acts.append((re.sub(r"[-_]", "", tok[0]), *(f"block{a}" if a.isdigit() else a for a in tok[1:])))
    if acts:
        return acts
    return [] if NO_PLAN.search(text) else None


def check(task, eid, answer, cache):
    if task not in cache:
        cache[task] = (load_constraints_json(task), load_problems_json(task), load_problems_with_solutions(task))
    constraints, problems, golden = cache[task]
    problem = problems.get(eid, {})
    if task == "blocksworld":
        g = problem.get("golden_solution") or {}
        plan = prose_plan(answer)
        if plan is None:  # e.g. "null", or a goal-state description instead of a plan
            return None, "prose answer did not parse"
        if not plan:
            return not problem.get("plan_exists", True), "prose says no plan exists"
        if not problem.get("plan_exists", True):
            return False, "prose gives a plan, but no plan exists"
        text = "\n".join(f"({' '.join(a)})" for a in plan)
        ok, out, err = run_val_validator(g["domain_pddl"], g["problem_pddl"], rename_plan_actions(text, g["domain_pddl"]), VAL)
        if not ok and not re.search(r"Plan failed to execute|Goal not satisfied", out or ""):
            # VAL could not read the plan (e.g. p10's actions take extra token arguments the prose
            # leaves out): not checkable rather than wrong
            return None, "VAL could not check the plan: " + (out or err)[-200:]
        return bool(ok), "" if ok else (out or err)[-300:]
    parsed = parse_output_by_task(answer, task, problem)
    if parsed is None:
        return None, "prose answer did not parse"
    if task == "zebralogic":
        return parsed == golden.get(eid), "compared with golden grid"
    c = constraints.get(eid, constraints)
    ok, detail = evaluate_solution(task, c.get("constraints", c), parsed, problem=problem, golden_solution=golden.get(eid))
    err = str(detail.get("error", "")) if isinstance(detail, dict) else ""
    if not ok and err.startswith(FORMAT_ERRORS):
        # the extracted itinerary is malformed (2026-10-31: 39 Meeting answers), not checkable
        return None, detail
    return bool(ok), detail


def main():
    judge_path, items_path = Path(sys.argv[1]), Path(sys.argv[2])
    items = {it["id"]: it for it in json.load(open(items_path))}
    out, cache = {}, {}
    for line in judge_path.open():
        r = json.loads(line)
        it = items[r["id"]]
        if r.get("extent") != "complete" or not (r.get("prose_answer") or "").strip():
            out[r["id"]] = {"c2": None, "detail": "extent not complete"}
            continue
        try:
            ok, detail = check(it["task"], it["example_id"], r["prose_answer"], cache)
        except Exception as e:  # a malformed answer must not stop the run
            ok, detail = None, f"validator error: {e}"
        out[r["id"]] = {"c2": ok, "detail": detail if isinstance(detail, str) else json.dumps(detail)[:300]}
    dest = judge_path.with_suffix(".c2.json")
    json.dump(out, open(dest, "w"), indent=1)
    vals = [v["c2"] for v in out.values()]
    print(f"{dest}: correct {vals.count(True)}, incorrect {vals.count(False)}, n/a {vals.count(None)}")


if __name__ == "__main__":
    main()
