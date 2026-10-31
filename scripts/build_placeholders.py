#!/usr/bin/env python3
"""Write data/placeholders/<task>_placeholders.json: each problem with its values replaced by
placeholders (src/deter/placeholders.py), and the VALUES dict its program gets at run time.

Fails unless, for every problem, restoring the surfaces gives back the original text exactly and
no concrete value is left in the placeholder text.

Usage: python scripts/build_placeholders.py [--task calendar meeting]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from deter.placeholders import convert, restore, leaked_values  # noqa: E402
from general.io_utils import load_problems_json  # noqa: E402


def build(task: str) -> Path:
    problems = load_problems_json(task)
    out, failures = {}, []
    for example_id, data in problems.items():
        converted = convert(task, data["problem"], seed=example_id)
        if restore(task, converted) != data["problem"]:
            failures.append(f"{example_id}: round trip differs")
        leaks = leaked_values(task, converted)
        if leaks:
            failures.append(f"{example_id}: leaks {leaks[:5]}")
        out[example_id] = converted
    if failures:
        print("\n".join(failures))
        raise SystemExit(f"{task}: {len(failures)} failures")
    path = ROOT / "data" / "placeholders" / f"{task}_placeholders.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{task}: {len(out)} problems, round trip and leak checks pass -> {path.relative_to(ROOT)}")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", nargs="+", default=["calendar", "meeting"])
    for task in parser.parse_args().task:
        build(task)
