#!/usr/bin/env python3
"""Start the deterrence jobs (docs/DETERRENCE_DESIGN.md) on free GPUs as they become available,
following the GPU policy in CLAUDE.md:
  - a GPU is free only if no process at all is on it, and no live tmux session (ours or one started
    by hand) was started for it (CUDA_VISIBLE_DEVICES=<n> or GPU=<n> in its command), since a
    vLLM job shows no GPU process while it loads;
  - at most MAX_MINE GPUs are ours (hz466 processes, plus GPUs this dispatcher reserved);
  - at least one flex GPU stays idle after every launch (GPU 0 is taken last).
Each job is one tmux session (scripts/run_deter.sh for inference cells, or an A-judge run) and
holds its GPU until the session ends. Jobs start in list order once their dependencies are done.
State goes to output_deter/dispatch_state.json (read by the project dashboard).

Run in tmux: tmux new -d -s deter-dispatch 'python scripts/deter_dispatch.py 2>&1 | tee -a logs/deter-dispatch.log'
"""

import getpass
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "output_deter" / "dispatch_state.json"
MAX_MINE = 4
POLL = 60
ME = getpass.getuser()

N = 100
D, X = "output_deter", "output_deter_crossfl"  # native FL / second FL
JUDGE = ("source /local-ssd/hz466/vllm-test/env.sh && export CUDA_VISIBLE_DEVICES={gpu} && "
         "python scripts/deter_judge_items.py --root {root} && python src/run_ontology_judges.py a "
         "--items {root}/ontology/a_items.json --tag gemma_v11t --thinking 8192 --max-num-seqs 128")


def infer(name, model, root, cells):
    return {"name": name, "kind": "infer", "model": model, "root": root, "cells": cells}


INFER = [
    # Python first (most SLB), K = 5 and placeholders
    infer("gpt-py", "gpt", D, "calendar:python:k5 meeting:python:k5 calendar:python:ph meeting:python:ph"),
    infer("qwen-py-k5", "qwen", D, "calendar:python:k5 meeting:python:k5"),
    infer("qwen-py-ph", "qwen", D, "calendar:python:ph meeting:python:ph"),
    # gpt-py ran its placeholder cells with the v2 note; re-run them with v3 (2026-11-01)
    infer("gpt-py-ph", "gpt", D, "calendar:python:ph meeting:python:ph"),
    infer("gpt-xpy", "gpt", X, "zebralogic:python:k5 blocksworld:python:k5"),
    infer("qwen-xpy", "qwen", X, "zebralogic:python:k5 blocksworld:python:k5"),
    # Z3
    infer("gpt-z3", "gpt", X, "calendar:z3:k5 meeting:z3:k5 calendar:z3:ph meeting:z3:ph"),
    infer("gpt-z3n", "gpt", D, "zebralogic:z3:k5"),
    infer("qwen-z3-k5", "qwen", X, "calendar:z3:k5 meeting:z3:k5"),
    infer("qwen-z3-ph", "qwen", X, "calendar:z3:ph meeting:z3:ph"),
    infer("qwen-z3n", "qwen", D, "zebralogic:z3:k5"),
    # K sweep (GPT-OSS, Calendar and Meeting in Python)
    infer("gpt-ksweep", "gpt", D, "calendar:python:k2 calendar:python:k10 meeting:python:k2 meeting:python:k10"),
]
JOBS = [
    # The pilot's last Qwen cell, once that run and the first pilot judge are done
    {"name": "judge-pilot", "kind": "judge", "root": "output_deter_pilot",
     "after_sessions": ["deter-pilot-v3-qwen", "deter-judge2"]},
] + INFER + [
    {"name": "judge-native", "kind": "judge", "root": D, "after_jobs": [j["name"] for j in INFER if j["root"] == D]},
    {"name": "judge-crossfl", "kind": "judge", "root": X, "after_jobs": [j["name"] for j in INFER if j["root"] == X]},
]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def alive(session):
    return subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode == 0


def gpu_owners():
    """GPU index -> set of users with a process on it."""
    uuid_idx = dict(l.split(", ")[::-1] for l in sh("nvidia-smi --query-gpu=index,uuid --format=csv,noheader").splitlines())
    owners = {int(i): set() for i in uuid_idx.values()}
    for line in sh("nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader").splitlines():
        uuid, pid = [x.strip() for x in line.split(",")]
        user = sh(f"ps -o user= -p {pid}").strip() or "?"
        owners[int(uuid_idx[uuid])].add(user)
    return owners


def tmux_gpus():
    """GPUs named in the start command of any live tmux session."""
    out = sh("tmux list-panes -a -F '#{pane_start_command}'")
    return {int(g) for g in re.findall(r"(?:CUDA_VISIBLE_DEVICES|\bGPU)=(\d)\b", out)}


def session_of(job):
    return f"deter-{job['name']}"


def launch(job, gpu):
    session = session_of(job)
    if job["kind"] == "infer":
        env = f"GPU={gpu} MODEL={job['model']} N={N} ROOT={job['root']} NAME={session} CELLS='{job['cells']}'"
        out = sh(f"cd {REPO} && {env} scripts/run_deter.sh 2>&1")
    else:
        cmd = JUDGE.format(gpu=gpu, root=job["root"])
        out = sh(f"cd {REPO} && tmux new -d -s {session} \"{{ {cmd}; }} 2>&1 | tee logs/{session}.log\" 2>&1")
    print(f"{now()} start {job['name']} on GPU {gpu}: {out.strip()}", flush=True)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    jobs = {j["name"]: {**j, **state.get(j["name"], {})} for j in JOBS}
    for j in jobs.values():
        j.setdefault("status", "pending")
    while True:
        for j in jobs.values():
            if j["status"] == "running" and not alive(session_of(j)):
                j["status"], j["ended"] = "done", now()
                print(f"{now()} done {j['name']} (GPU {j['gpu']})", flush=True)
        owners = gpu_owners()
        reserved = {j["gpu"] for j in jobs.values() if j["status"] == "running"} | tmux_gpus()
        for j in jobs.values():
            if j["status"] != "pending":
                continue
            if any(jobs[d]["status"] != "done" for d in j.get("after_jobs", [])):
                continue
            if any(alive(s) for s in j.get("after_sessions", [])):
                continue
            free = sorted((g for g, u in owners.items() if not u and g not in reserved), reverse=True)
            mine = {g for g, u in owners.items() if ME in u} | reserved
            if len(free) < 2 or len(mine) >= MAX_MINE:
                break  # keep list order: later jobs wait too
            gpu = free[0]
            launch(j, gpu)
            j.update(status="running", gpu=gpu, started=now())
            reserved.add(gpu)
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps({n: {k: v for k, v in j.items() if k in ("status", "gpu", "started", "ended")}
                                     for n, j in jobs.items()}, indent=1))
        if all(j["status"] == "done" for j in jobs.values()):
            print(f"{now()} all jobs done", flush=True)
            return
        time.sleep(POLL)


if __name__ == "__main__":
    main()
