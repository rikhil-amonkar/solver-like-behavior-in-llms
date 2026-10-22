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


def check(task, eid, answer, cache):
    if task not in cache:
        cache[task] = (load_constraints_json(task), load_problems_json(task), load_problems_with_solutions(task))
    constraints, problems, golden = cache[task]
    problem = problems.get(eid, {})
    if task == "blocksworld":
        g = problem.get("golden_solution") or {}
        if not problem.get("plan_exists", True):
            return False, "prose gives a plan, but no plan exists"
        ok, out, err = run_val_validator(g["domain_pddl"], g["problem_pddl"], rename_plan_actions(answer, g["domain_pddl"]), VAL)
        return bool(ok), "" if ok else (out or err)[-300:]
    parsed = parse_output_by_task(answer, task, problem)
    if parsed is None:
        return None, "prose answer did not parse"
    if task == "zebralogic":
        return parsed == golden.get(eid), "compared with golden grid"
    c = constraints.get(eid, constraints)
    ok, detail = evaluate_solution(task, c.get("constraints", c), parsed, problem=problem, golden_solution=golden.get(eid))
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
