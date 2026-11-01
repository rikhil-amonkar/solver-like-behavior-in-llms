#!/usr/bin/env python3
"""Merge inference outputs from a run split across GPUs into one inference JSON.

Usage:
    python scripts/merge_inference_parts.py TASK OUT_JSON PART [PART ...]
Each PART is a part's inference .json (finished) or .jsonl (stopped early). Examples are put in the
task's problem order; the merge fails if a problem is missing or appears twice.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROBLEMS = {"calendar": "data/problems/calendar_scheduling_100.json",
            "meeting": "data/problems/meeting_planning_100.json"}


def load_part(path):
    if path.endswith(".jsonl"):
        rows = [json.loads(l) for l in open(path) if l.strip()]
        meta = next((r["_metadata"] for r in rows if "_metadata" in r), {})
        return meta, [r for r in rows if "example_id" in r]
    d = json.load(open(path))
    return d["run_metadata"], d["examples"]


def main(task, out_path, parts):
    order = list(json.load(open(PROBLEMS[task])).keys())
    by_id, metas = {}, []
    for p in parts:
        meta, examples = load_part(p)
        metas.append(meta)
        for e in examples:
            if e["example_id"] in by_id:
                sys.exit(f"duplicate example {e['example_id']} in {p}")
            by_id[e["example_id"]] = e
    missing = [i for i in order if i not in by_id]
    if missing:
        sys.exit(f"missing {len(missing)} examples, e.g. {missing[:3]}")
    examples = [by_id[i] for i in order]
    meta = dict(metas[0])
    meta.update(timestamp=min(m["timestamp"] for m in metas), num_examples=len(examples),
                merged_from=parts, merged_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    out = {"run_metadata": meta,
           "summary": {"total_examples": len(examples), "successful": len(examples), "errors": 0},
           "examples": examples}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=2, ensure_ascii=False)
    print(f"wrote {out_path}: {len(examples)} examples from {len(parts)} parts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
