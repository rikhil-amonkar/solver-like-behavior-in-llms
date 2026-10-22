#!/usr/bin/env python3
"""Snapshot of the Qwen re-run progress, written as JSON for the progress dashboard.

Usage: python scripts/rerun_progress.py OUT_DIR
Writes OUT_DIR/runs.json (one row per run) and OUT_DIR/traces.json (one row per finished trace).
Meeting baseline runs in parts reported as one run: half A (problems 1-48, GPU 4), half B (51-100, GPU 7),
and part C (49-50, GPU 7 after half B).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BATCH = 16  # run_inference.py's default vLLM batch size
TIME = r"(\w{3} \w{3} .+? UTC \d{4})"
# (task, condition, GPUs, [(output prefix, log file, START marker, END marker)])
RUNS = [
    ("calendar", "baseline", "7",
     [("output_rerun/qwen/calendar/baseline_inference", "logs/qwen-rerun.log", "--task calendar", "--task calendar")]),
    ("calendar", "caution_a", "7",
     [("output_rerun/qwen/calendar/caution_a_inference", "logs/qwen-rerun.log", "--task calendar --caution-a", None)]),
    ("meeting", "baseline", "4 + 7",
     [("output_rerun_parts/a/qwen/meeting/baseline_inference", "logs/qwen-meeting-a.log", "meeting half A", "meeting half A"),
      ("output_rerun_parts/b/qwen/meeting/baseline_inference", "logs/qwen-meeting-b.log", "meeting half B", "meeting half B"),
      # half A is stopped after 48 problems; its last 2 run as part C on GPU 7
      ("output_rerun_parts/c/qwen/meeting/baseline_inference", "logs/qwen-meeting-c.log", "meeting part C", "meeting part C")]),
]


def parse_time(s):
    return datetime.strptime(s.strip(), "%a %b %d %I:%M:%S %p %Z %Y").replace(tzinfo=timezone.utc)


def marker(log, kind, label):
    if not label:
        return None
    # not anchored: progress bars end lines with \r, so a marker can land mid-line
    m = re.search(r"=== %s %s(?: exit=\d+)? %s" % (kind, re.escape(label), TIME), log)
    return parse_time(m.group(1)) if m else None


def records(prefix):
    jsonl, final = Path(prefix + ".jsonl"), Path(prefix + ".json")
    if jsonl.exists():
        rows = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    elif final.exists():  # a finished run replaces its .jsonl with the final .json
        rows = json.load(open(final))["examples"]
    else:
        rows = []
    return [r for r in rows if "example_id" in r], final.exists()


def main(out_dir):
    now = datetime.now(timezone.utc)
    runs, traces = [], []
    tokens_done = gpu_minutes = 0.0
    for task, cond, gpus, parts in RUNS:
        old = {x["example_id"]: x for x in json.load(open(f"output/qwen/{task}/{cond}_inference.json"))["examples"]}
        new, starts, ends, finished_parts, active = [], [], [], 0, 0
        part_eta = []  # minutes left per unfinished part, from its measured batch time
        for prefix, logf, start_label, end_label in parts:
            log = Path(logf).read_text(errors="replace") if Path(logf).exists() else ""
            recs, done = records(prefix)
            done = done or bool(start_label and re.search(r"=== STOP %s" % re.escape(start_label), log))
            new += recs
            st, en = marker(log, "START", start_label), marker(log, "END", end_label)
            if done:
                finished_parts += 1
            elif st or recs:
                active += 1
            size = {"meeting half A": 48, "meeting part C": 2}.get(start_label, len(old) // 2 if len(parts) > 1 else len(old))
            if st and recs and not done:
                batches_done = len(recs) // BATCH
                per_batch = (now - st).total_seconds() / 60 / max(1, batches_done)
                part_eta.append(-(-(size - len(recs)) // BATCH) * per_batch - ((now - st).total_seconds() / 60 - batches_done * per_batch))
            if st:
                starts.append(st)
                end = en or (now if not done else None)
                if end:
                    gpu_minutes += (end - st).total_seconds() / 60
                    ends.append(end)
        for r in new:
            o = old.get(r["example_id"], {})
            traces.append({"run": f"{task} {cond}", "example_id": r["example_id"],
                           "tokens_new": r["model_metadata"].get("generated_tokens"),
                           "tokens_old": o.get("model_metadata", {}).get("generated_tokens"),
                           "prompt_matches": r["model_metadata"].get("prompt_length") == o.get("model_metadata", {}).get("prompt_length")})
        gen = sum(r["model_metadata"].get("generated_tokens") or 0 for r in new)
        if starts:
            tokens_done += gen
        status = "finished" if finished_parts == len(parts) else ("running" if active or starts else "queued")
        elapsed = ((max(ends) if ends else now) - min(starts)).total_seconds() / 60 if starts else 0.0
        runs.append({"run": f"{task} {cond}", "task": task, "condition": cond, "gpus": gpus, "status": status,
                     "done": len(new), "total": len(old), "elapsed_min": round(elapsed, 1),
                     "tokens_generated": gen, "active_parts": active, "parts": len(parts),
                     "old_tokens_total": sum(x["model_metadata"].get("generated_tokens") or 0 for x in old.values()),
                     "started": min(starts).isoformat() if starts else None,
                     "batch_eta_min": round(max(part_eta)) if part_eta else None})

    rate = tokens_done / gpu_minutes if gpu_minutes else None  # tokens per GPU-minute so far
    for r in runs:
        if r["status"] == "finished" or not rate:
            r["eta_min"] = 0 if r["status"] == "finished" else None
            continue
        if r.get("batch_eta_min") is not None:  # measured batch time beats the token estimate
            r["eta_min"] = r["batch_eta_min"]
            continue
        remaining = max(r["old_tokens_total"] - r["tokens_generated"], 0)
        r["eta_min"] = round(remaining / (rate * max(1, r["active_parts"] or r["parts"])), 0)
    at = now.isoformat(timespec="seconds")
    for r in runs:
        r["snapshot_at"] = at
        r["tokens_per_min"] = round(rate) if rate else None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "runs.json").write_text(json.dumps({"rows": runs}, indent=1))
    (out / "traces.json").write_text(json.dumps({"rows": traces}, indent=1))
    print(at, [(r["run"], r["status"], r["done"], r["eta_min"]) for r in runs])


if __name__ == "__main__":
    main(sys.argv[1])
