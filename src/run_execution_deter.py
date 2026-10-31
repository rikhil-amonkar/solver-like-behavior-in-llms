#!/usr/bin/env python3
"""
Execution for the deterrence runs (docs/DETERRENCE_DESIGN.md), writing the same per-problem
<condition>_execution.json as run_execution.py, so run_evaluation.py scores it unchanged.

- batch_k<K>: each inference record holds K problems; split_programs() takes the program headed
  `# Problem i` for each, and every member's record carries the group's shared reasoning and a
  "batch" field (group, position, k, unlabelled_blocks).
- placeholder: the program is extracted as usual and run with `VALUES = {...}` (the problem's
  real values, data/placeholders/; for Meeting also `TRAVEL = {...}`) prepended; extracted_code
  stays the model's own code. Placeholder names in its output are mapped back to their values
  before parsing (code_execution.stdout_restored records when that happened).

Usage: python src/run_execution_deter.py --input output_deter/qwen/calendar/batch_k5_inference.json
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import (
    load_json_file,
    load_problems_json,
    get_timestamp,
    get_repo_root,
    IncrementalJSONWriter,
    make_path_relative,
)
from execution.code_extractor import split_reasoning_and_code, clean_extracted_code
from execution.output_formatter import parse_output_by_task
from inference.code_executor import execute_code_by_language, get_language_from_task
from general.fl_compliance import fl_compliance
from run_execution import python_plan_result, count_tokens
from deter.batching import split_programs
from deter.placeholders import values_preamble, restore_output


def run_program(code, task, fl, language, problem_data, timeout, preamble="", values=None):
    if not (code and code.strip()):
        return {"ran": False, "exit_code": None, "stdout": "", "stderr": "", "timed_out": False,
                "timeout_sec": timeout, "error": "no code extracted", "parsed_output": None}
    extra = {"problem_data": problem_data} if task == "zebralogic" else {}
    result = execute_code_by_language(preamble + code, language=language, timeout_sec=timeout, **extra)
    if task == "blocksworld":
        result.update(python_plan_result(result))
    elif result.get("exit_code") == 0 and result.get("stdout"):
        stdout = result["stdout"]
        if values is not None:
            # A program may print placeholder names; the answer is the same once they are mapped back
            stdout = restore_output(stdout, values)
            result["stdout_restored"] = stdout if stdout != result["stdout"] else None
        result["parsed_output"] = parse_output_by_task(stdout, task, problem_data)
    else:
        result["parsed_output"] = None
    result["z3_used"] = "from z3 import" in code or "import z3" in code
    result["fl_compliance"] = fl_compliance(code, fl)
    return result


def member_records(example, condition, task, fl, language, problems, placeholders, timeout):
    """Yield one execution record per problem in an inference record."""
    trace = example.get("reasoning_trace", "")
    if condition.startswith("batch_k"):
        members = example["member_ids"]
        split = split_programs(trace, len(members))
        for pos, eid in enumerate(members, 1):
            code = split["programs"][pos]
            code = clean_extracted_code(code) if code else None
            yield {
                "example_id": eid,
                "reasoning_before_code": split["reasoning"],
                "reasoning_before_code_tokens": count_tokens(split["reasoning"]),
                "extracted_code": code,
                "extracted_code_tokens": count_tokens(code or ""),
                "code_execution": run_program(code, task, fl, language, problems[eid], timeout),
                "batch": {"group_id": example["example_id"], "position": pos, "k": len(members),
                          "unlabelled_blocks": split["unlabelled_blocks"]},
            }
    else:
        eid = example["example_id"]
        reasoning, code = split_reasoning_and_code(trace)
        code = clean_extracted_code(code) if code else None
        preamble = values_preamble(placeholders[eid])
        yield {
            "example_id": eid,
            "reasoning_before_code": reasoning,
            "reasoning_before_code_tokens": count_tokens(reasoning or ""),
            "extracted_code": code,
            "extracted_code_tokens": count_tokens(code or ""),
            "code_execution": run_program(code, task, fl, language, problems[eid], timeout, preamble,
                                          placeholders[eid]["values"]),
        }


def main():
    parser = argparse.ArgumentParser(description="Execute deterrence-run programs")
    parser.add_argument("--input", required=True, help="Path to a batch_k*/placeholder inference JSON")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    data = load_json_file(args.input)
    meta = data["run_metadata"]
    task, condition = meta["task"], meta["condition"]
    fl = meta.get("fl", get_language_from_task(task))
    if not (condition.startswith("batch_k") or condition == "placeholder"):
        raise SystemExit(f"{condition}: not a deterrence run; use run_execution.py")
    if fl == "pddl":
        raise SystemExit("PDDL deterrence runs are not supported yet")
    language = "python" if task == "blocksworld" else get_language_from_task(task)
    problems = load_problems_json(task)
    placeholders = None
    if condition == "placeholder":
        placeholders = load_json_file(str(get_repo_root() / "data" / "placeholders" / f"{task}_placeholders.json"))

    output_path = Path(args.input).parent / f"{condition}_execution.json"
    metadata = {"task": task, "model": meta["model"], "condition": condition, "fl": fl,
                "inference_json": make_path_relative(args.input), "timestamp": get_timestamp(),
                "code_timeout_sec": args.timeout}
    ok = total = 0
    with IncrementalJSONWriter(str(output_path), metadata) as writer:
        for example in data["examples"]:
            for record in member_records(example, condition, task, fl, language, problems,
                                         placeholders, args.timeout):
                writer.write_example(record)
                total += 1
                ok += record["code_execution"].get("exit_code") == 0
        writer.finalize_with_summary({"total_examples": total, "successful_executions": ok,
                                      "failed_executions": total - ok})
    print(f"{condition}: {ok}/{total} programs ran -> {output_path}")


if __name__ == "__main__":
    main()
