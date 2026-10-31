#!/usr/bin/env python3
"""
Snapshot of the project's running experiments for the project dashboard.

Writes OUT_DIR/jobs.json (one row per job), OUT_DIR/history.json (progress over
time, appended to on every run) and OUT_DIR/gpus.json (one row per GPU). The
hand-kept milestone and to-do lists live in docs/dashboard/ and are copied next
to them, so the dashboard has every dataset in one place.

Rates and ETAs come from the progress history: the rate is measured over the
last hour of snapshots (or since the job started, when that is shorter).

Usage: python scripts/project_dashboard_snapshot.py [OUT_DIR]   (default output/dashboard)
"""

import glob
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def count_lines(pattern: str) -> int:
    ids = set()
    for f in glob.glob(str(REPO / pattern)):
        with open(f, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.strip():
                    try:
                        ids.add(json.loads(line).get("id") or line[:200])
                    except json.JSONDecodeError:
                        pass  # line still being written
    return len(ids)


def count_examples(prefix: Path) -> int:
    """Records written by run_inference.py: the .jsonl while running, the .json once finished."""
    jsonl, final = prefix.with_suffix(".jsonl"), prefix.with_suffix(".json")
    if final.exists():
        try:
            return len(json.loads(final.read_text())["examples"])
        except Exception:
            return 0
    if jsonl.exists():
        n = 0
        for line in jsonl.read_text(errors="ignore").splitlines():
            try:
                n += "example_id" in json.loads(line)
            except json.JSONDecodeError:
                pass
        return n
    return 0


def tmux_alive(session: str) -> bool:
    return subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode == 0


def tmux_created(session: str):
    out = subprocess.run(["tmux", "display-message", "-p", "-t", session, "#{session_created}"],
                         capture_output=True, text=True)
    return datetime.fromtimestamp(int(out.stdout.strip()), timezone.utc) if out.returncode == 0 else None


def log_text(name: str) -> str:
    path = REPO / "logs" / name
    return path.read_text(errors="ignore") if path.exists() else ""


def crossfl_job(job_id, name, model, gpus, session, after):
    """Cross-FL inference for one model: Calendar and Meeting in Z3-Python, ZebraLogic and BlocksWorld in Python, 3 conditions each."""
    done = 0
    evaluated = 0
    for task in ("calendar", "meeting", "zebralogic", "blocksworld"):
        for cond in ("baseline", "caution_a", "caution_b"):
            base = REPO / "output_crossfl" / model / task
            done += count_examples(base / f"{cond}_inference")
            evaluated += (base / f"{cond}_evaluation.json").exists()
    return {"id": job_id, "name": name, "stage": "Inference, then execution and evaluation",
            "gpus": gpus, "done": done, "total": 1200, "unit": "problems",
            "extra": f"{evaluated}/12 runs evaluated", "session": session, "after": after}


def build_jobs():
    a_done = count_lines("output/ontology/judge_a_gemma_v11t.shard*.jsonl")
    c_done = count_lines("output/ontology/judge_c_gemma_v11c.shard*.jsonl")
    # full-v11 ran the judges on GPUs 0-3; since 2026-10-30 19:00 judge-switch finishes them on 0, 1
    # and hands GPUs 2, 3 to cross-FL (scripts/switch_judges_01_crossfl_23.sh)
    judge_log = log_text("full-v11.log") + log_text("judge-switch.log")
    judge_session = "full-v11" if tmux_alive("full-v11") else "judge-switch"
    jobs = [
        {"id": "a_judge", "name": "A judge rerun (gemma_v11t)", "stage": "Paragraph labels, all traces",
         "gpus": "0, 1", "done": a_done, "total": 29237, "unit": "segments",
         "extra": "", "session": judge_session, "after": None,
         "finished": "A done" in judge_log},
        {"id": "c_judge", "name": "A2/C judge (gemma_v11c)", "stage": "Prose answer per trace",
         "gpus": "0, 1", "done": c_done, "total": 3600, "unit": "traces",
         "extra": "", "session": judge_session, "after": "a_judge",
         "finished": "DONE" in judge_log},
        crossfl_job("crossfl_qwen", "Cross-FL: Qwen", "qwen", "2, 3", "crossfl-qwen", None),
        crossfl_job("crossfl_gpt", "Cross-FL: GPT-OSS", "gpt", "3", "crossfl-gpt", None),
        crossfl_job("crossfl_deepseek", "Cross-FL: DeepSeek (API)", "deepseek", "none (API)",
                    "crossfl-deepseek", None),
    ]
    for j, model in ((jobs[2], "qwen"), (jobs[3], "gpt")):
        j["finished"] = "DONE" in log_text(f"crossfl-{model}.log")
        if model == "qwen":  # second queue on GPU 3 (scripts/run_crossfl_claim.sh) since 21:40
            j["finished"] = j["finished"] and "DONE" in log_text("crossfl-qwen-gpu3.log")
        # waits for judge-switch to free its GPU
        j["queued"] = not tmux_alive(j["session"]) and tmux_alive("judge-switch") and j["done"] == 0
    jobs[4]["finished"] = all("DONE" in log_text(f) for f in ("crossfl-deepseek.log", "crossfl-deepseek-bw.log",
                                                      "crossfl-deepseek-meeting.log"))
    jobs[2]["gpus"] = "0, 2, 3"
    # Judges on the cross-FL runs (scripts/run_crossfl_judges.sh): GPUs 0-3 as they free up; the
    # totals grow as Qwen's runs finish, so each is read from the judge logs ("N items, ...")
    xlog = log_text("crossfl-judges.log")
    for kind, tag, name, stage, unit, total, marker in (
            ("a", "gemma_v11t", "Cross-FL A judge (gemma_v11t)", "Paragraph labels", "segments", 13000, "A done"),
            ("b", "gemma_b5t", "Cross-FL B judge (gemma_b5t)", "Program labels", "traces", 3600, "B done"),
            ("c", "gemma_v11c", "Cross-FL A2/C judge (gemma_v11c)", "Prose answer per trace", "traces", 3600, "DONE")):
        seen = [int(n) for n in re.findall(r"^(\d+) items,", "".join(log_text(f.name) for f in
                (REPO / "logs").glob(f"crossfl-judge-{kind}*.log")), re.M)]
        gpus = re.findall(r"== %s on GPUs ([\d ]+)" % kind, xlog)  # the latest round's GPUs
        jobs.append({"id": f"crossfl_judge_{kind}", "name": name, "stage": stage,
                     "gpus": ", ".join(gpus[-1].split()) if gpus else "1, 2, 3",
                     "done": count_lines(f"output_crossfl/ontology/judge_{kind}_{tag}*.jsonl"),
                     "total": max(seen) if seen else total, "unit": unit,
                     "extra": "", "session": "crossfl-judges",
                     "after": {"a": None, "b": "crossfl_judge_a", "c": "crossfl_judge_b"}[kind],
                     "finished": marker in xlog})
    return jobs


KEEP_FREE = {0}  # the flex GPU left idle while the project uses 1-3 (Harry, 2026-10-31)


def gpu_rows():
    out = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid",
                           "--format=csv,noheader"], capture_output=True, text=True).stdout
    busy = {}
    for line in apps.strip().splitlines():
        uuid, pid = [x.strip() for x in line.split(",")]
        user = subprocess.run(["ps", "-o", "user=", "-p", pid], capture_output=True, text=True).stdout.strip()
        busy.setdefault(uuid, set()).add(user)
    rows = []
    for line in out.strip().splitlines():
        idx, uuid, used, total, util = [x.strip() for x in line.split(",")]
        users = busy.get(uuid, set())
        use = "this project" if "hz466" in users else ("another user" if users else
                                                       "kept free" if int(idx) in KEEP_FREE else "free")
        rows.append({"gpu": int(idx), "use": use, "util_pct": int(util),
                     "mem_gib": round(int(used) / 1024, 1), "mem_total_gib": round(int(total) / 1024)})
    return rows


def main(out_dir: Path):
    now = datetime.now(timezone.utc)
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = build_jobs()

    history_path = out_dir / "history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    history += [{"t": stamp, "job": j["id"], "done": j["done"]} for j in jobs]
    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    history = [h for h in history if h["t"] >= cutoff]

    by_id = {j["id"]: j for j in jobs}
    for j in jobs:
        alive = tmux_alive(j["session"])
        if j.get("finished") or j["done"] >= j["total"]:
            j["status"] = "done"
        elif j.pop("queued", False) or (j["after"] and by_id[j["after"]]["status"] != "done"):
            j["status"] = "queued"
        elif j["done"] > 0 or (alive and not j["after"]):
            j["status"] = "running" if alive else "stopped"
        else:
            j["status"] = "starting" if alive else "stopped"

        # Rate over the last hour of history (or since the first nonzero point)
        points = [(datetime.strptime(h["t"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc), h["done"])
                  for h in history if h["job"] == j["id"]]
        recent = [p for p in points if p[0] >= now - timedelta(hours=1)]
        first_moving = next((p for p in points if p[1] > 0), None)
        base = recent[0] if recent and recent[0][1] < j["done"] else first_moving
        rate = None
        if base and j["done"] > base[1] and (now - base[0]).total_seconds() > 300:
            rate = (j["done"] - base[1]) / ((now - base[0]).total_seconds() / 3600)
        j["rate_per_hour"] = round(rate, 1) if rate else None
        if j["status"] == "running" and rate:
            hours = (j["total"] - j["done"]) / rate
            j["eta_hours"] = round(hours, 1)
            j["eta_at"] = (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%MZ")
        else:
            j["eta_hours"] = None
            j["eta_at"] = None
        j["pct"] = round(100 * j["done"] / j["total"], 1) if j["total"] else 0.0
        started = tmux_created(j["session"]) if alive else None
        j["session_started"] = started.strftime("%Y-%m-%dT%H:%MZ") if started else None
        j.pop("finished", None)
        j.pop("queued", None)
        j["after_name"] = by_id[j["after"]]["name"] if j["after"] else ""
        j.pop("after", None)
        j["snapshot_at"] = stamp

    (out_dir / "jobs.json").write_text(json.dumps(jobs, indent=1))
    history_path.write_text(json.dumps(history))
    (out_dir / "gpus.json").write_text(json.dumps(gpu_rows(), indent=1))
    for name in ("milestones.json", "todo.json"):
        src = REPO / "docs" / "dashboard" / name
        if src.exists():
            shutil.copy(src, out_dir / name)
    print(f"{stamp}: " + ", ".join(f"{j['id']} {j['done']}/{j['total']} {j['status']}" for j in jobs))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "output" / "dashboard")
