#!/usr/bin/env python3
"""Snapshot of the Qwen re-run progress, written as JSON for the progress dashboard.

Usage: python scripts/rerun_progress.py OUT_DIR
Writes OUT_DIR/runs.json (one row per run) and OUT_DIR/traces.json (one row per finished trace).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RUNS = [("calendar", "baseline", "--task calendar"),
        ("calendar", "caution_a", "--task calendar --caution-a"),
        ("meeting", "baseline", "--task meeting")]
LOG = Path("logs/qwen-rerun.log")


def parse_time(s):
    return datetime.strptime(s.strip(), "%a %b %d %I:%M:%S %p %Z %Y").replace(tzinfo=timezone.utc)


def main(out_dir):
    now = datetime.now(timezone.utc)
    log = LOG.read_text(errors="replace") if LOG.exists() else ""
    starts = {m.group(1).strip(): parse_time(m.group(2)) for m in re.finditer(r"^=== START (.+?) (\w{3} \w{3} .+? UTC \d{4})$", log, re.M)}
    ends = {m.group(1).strip(): (int(m.group(2)), parse_time(m.group(3))) for m in re.finditer(r"^=== END (.+?) exit=(\d+) (\w{3} \w{3} .+? UTC \d{4})$", log, re.M)}

    runs, traces = [], []
    tokens_done = minutes_done = 0.0
    for task, cond, args in RUNS:
        old = {x["example_id"]: x for x in json.load(open(f"output/qwen/{task}/{cond}_inference.json"))["examples"]}
        path = Path(f"output_rerun/qwen/{task}/{cond}_inference.jsonl")
        new = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
        new = [r for r in new if "example_id" in r]
        for r in new:
            o = old.get(r["example_id"], {})
            traces.append({"run": f"{task} {cond}", "example_id": r["example_id"],
                           "tokens_new": r["model_metadata"].get("generated_tokens"),
                           "tokens_old": o.get("model_metadata", {}).get("generated_tokens"),
                           "prompt_matches": r["model_metadata"].get("prompt_length") == o.get("model_metadata", {}).get("prompt_length")})
        start = starts.get(args)
        end = ends.get(args)
        if end:
            status = "finished" if end[0] == 0 else "failed"
        elif start:
            status = "running"
        else:
            status = "queued"
        elapsed = ((end[1] if end else now) - start).total_seconds() / 60 if start else 0.0
        gen = sum(r["model_metadata"].get("generated_tokens") or 0 for r in new)
        if start:
            tokens_done += gen
            minutes_done += elapsed
        runs.append({"run": f"{task} {cond}", "task": task, "condition": cond, "status": status,
                     "done": len(new), "total": len(old), "elapsed_min": round(elapsed, 1),
                     "tokens_generated": gen,
                     "old_tokens_total": sum(x["model_metadata"].get("generated_tokens") or 0 for x in old.values()),
                     "started": start.isoformat() if start else None})

    rate = tokens_done / minutes_done if minutes_done else None  # tokens per minute so far
    for r in runs:
        if r["status"] == "finished" or not rate:
            r["eta_min"] = 0 if r["status"] == "finished" else None
            continue
        remaining_tokens = max(r["old_tokens_total"] - r["tokens_generated"], 0)
        r["eta_min"] = round(remaining_tokens / rate, 0)
    snapshot = {"at": now.isoformat(timespec="seconds"), "tokens_per_min": round(rate) if rate else None}
    for r in runs:
        r["snapshot_at"] = snapshot["at"]
        r["tokens_per_min"] = snapshot["tokens_per_min"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "runs.json").write_text(json.dumps({"snapshot": snapshot, "rows": runs}, indent=1))
    (out / "traces.json").write_text(json.dumps({"rows": traces}, indent=1))
    print(json.dumps(snapshot), [(r["run"], r["status"], r["done"], r["eta_min"]) for r in runs])


if __name__ == "__main__":
    main(sys.argv[1])
