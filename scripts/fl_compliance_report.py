#!/usr/bin/env python3
"""
Flag programs not written in the formal language the prompt asked for, in every run.

Reads output/*/*/*_execution.json and output_crossfl/*/*/*_execution.json. Writes the per-example
flags to <root>/fl_compliance.json and prints a Markdown table of non-compliance rates.
Usage: python scripts/fl_compliance_report.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from general.fl_compliance import fl_compliance
from inference.code_executor import get_language_from_task

print("| Root | Model | Task | FL | Condition | Programs | Not valid Python | Non-compliant | Rate | Reasons |")
print("|---|---|---|---|---|---|---|---|---|---|")
for root in ("output", "output_crossfl"):
    flags = {}
    for path in sorted((REPO / root).glob("*/*/*_execution.json")):
        data = json.loads(path.read_text())
        meta = data["run_metadata"]
        fl = meta.get("fl") or get_language_from_task(meta["task"])
        if fl == "pddl":
            continue
        key = str(path.relative_to(REPO))
        flags[key] = {}
        reasons = Counter()
        n = bad = invalid = 0
        for ex in data["examples"]:
            code = ex.get("extracted_code") or ""
            if not code.strip():
                continue
            c = fl_compliance(code, fl)
            flags[key][ex["example_id"]] = c
            if c["compliant"] is None:
                invalid += 1
                continue
            n += 1
            if c["compliant"] is False:
                bad += 1
                reasons[c["reason"]] += 1
        cond = path.name.replace("_execution.json", "")
        rate = f"{bad / n:.2f}" if n else "-"
        why = "; ".join(f"{r} ({k})" for r, k in reasons.most_common(3))
        print(f"| {root} | {meta['model']} | {meta['task']} | {fl} | {cond} | {n} | {invalid} | {bad} | {rate} | {why} |")
    if flags:
        (REPO / root / "fl_compliance.json").write_text(json.dumps(flags, indent=1))
