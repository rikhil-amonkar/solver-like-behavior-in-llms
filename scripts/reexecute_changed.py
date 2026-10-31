#!/usr/bin/env python3
"""
Patch stored execution records after an extractor or plan-reading fix, without re-running
every program:

- re-extract the program from every inference record; where the program (or the reasoning
  before it) changes, re-run it with run_execution.execute_example;
- for Python BlocksWorld programs, recompute the plan fields from the stored stdout
  (python_plan_result), so an empty output reads as the empty plan.

Each patched file is then re-scored with run_evaluation. Prints the changed examples and the
accuracy before and after.

Usage (env venv, z3 installed):
    python scripts/reexecute_changed.py output output_crossfl
"""
import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from execution.code_extractor import split_reasoning_and_code, clean_extracted_code
from general.io_utils import load_problems_json
from inference.code_executor import get_language_from_task
from run_execution import execute_example, python_plan_result
from run_evaluation import run_evaluation_pipeline


def records(path):
    d = json.load(open(path))
    return d, d["examples"]


def accuracy(path):
    if not Path(path).exists():
        return None
    return {r["example_id"]: bool(r.get("correct")) for r in json.load(open(path))["examples"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    args = ap.parse_args()
    problems = {}
    for root in args.roots:
        for f in sorted(glob.glob(str(REPO / root / "*/*/*_execution.json"))):
            data, ex = records(f)
            meta = data["run_metadata"]
            task = meta["task"]
            inf_data, inf = records(f.replace("_execution.json", "_inference.json"))
            fl = meta.get("fl") or inf_data["run_metadata"].get("fl", get_language_from_task(task))
            language = "python" if task == "blocksworld" and fl == "python" else get_language_from_task(task)
            inf = {r["example_id"]: r for r in inf}
            problems.setdefault(task, load_problems_json(task))
            changed = []
            for i, r in enumerate(ex):
                rb, code = split_reasoning_and_code(inf[r["example_id"]].get("reasoning_trace", ""))
                code = clean_extracted_code(code) if code else code
                if (code or "") != (r.get("extracted_code") or "") or rb != (r.get("reasoning_before_code") or ""):
                    ex[i] = execute_example(inf[r["example_id"]], task, fl, language, problems[task],
                                            meta.get("code_timeout_sec", 30.0))
                    changed.append(r["example_id"])
                elif language == "python" and task == "blocksworld":
                    ce = r["code_execution"]
                    new = python_plan_result(ce)
                    if any(ce.get(k) != v for k, v in new.items()):
                        ce.update(new)
                        changed.append(r["example_id"])
            if not changed:
                continue
            json.dump(data, open(f, "w"), indent=2, ensure_ascii=False)
            ev = f.replace("_execution.json", "_evaluation.json")
            before = accuracy(ev)
            run_evaluation_pipeline(f)
            after = accuracy(ev)
            flips = {k: (before.get(k), v) for k, v in after.items() if before and before.get(k) != v}
            rel = Path(f).relative_to(REPO)
            print(f"PATCHED {rel}: {len(changed)} changed {changed}; accuracy {sum(before.values()) if before else '?'}"
                  f" -> {sum(after.values())}; flips {flips}", flush=True)


if __name__ == "__main__":
    main()
