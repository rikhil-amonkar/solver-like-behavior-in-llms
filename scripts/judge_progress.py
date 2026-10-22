#!/usr/bin/env python3
"""
Terminal dashboard for a running src/run_chunking_local.py job.

Progress is measured in judged characters (segments run longest first, so
segment counts alone would make the ETA far too pessimistic early on).
The ETA uses the character rate between the last few completed waves.

Usage:
    python scripts/judge_progress.py --tag gemma            # refresh every 30 s
    python scripts/judge_progress.py --tag gemma --once
"""

import argparse
import glob
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def segment_lengths(tag: str, segment_tokens: int) -> dict:
    """Character length of every judge segment, computed once and cached."""
    path = REPO_ROOT / "output" / f"judge_segments_{tag}.json"
    if path.exists():
        return json.loads(path.read_text())
    from run_chunking_local import build_requests
    inputs = sorted(glob.glob(str(REPO_ROOT / "output" / "*" / "*" / "*_execution.json")))
    requests, _ = build_requests(inputs, segment_tokens)
    lengths = {r["id"]: len(r["text"]) for r in requests}
    path.write_text(json.dumps(lengths))
    return lengths


def read_cache(tag: str) -> list:
    path = REPO_ROOT / "output" / f"judge_cache_{tag}.jsonl"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # line still being written
    return rows


def wave_times(log_path: Path) -> list:
    """(timestamp, segments done) for each completed wave in the run log."""
    if not log_path.exists():
        return []
    pattern = re.compile(r"\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\] (\d+)/(\d+) segments")
    waves = []
    for line in log_path.read_text(errors="ignore").splitlines():
        m = pattern.search(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            waves.append((ts, int(m.group(2))))
    return waves


def gpu_status(index: int) -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--id={index}", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.strip()
        util, used, total = [x.strip() for x in out.split(",")]
        return f"{util}% util, {int(used) / 1024:.1f}/{int(total) / 1024:.0f} GiB"
    except Exception:
        return "unavailable"


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    return (f"{days}d " if days else "") + f"{hours}h {minutes:02d}m"


def bar(fraction: float, width: int = 40) -> str:
    filled = int(round(fraction * width))
    return "█" * filled + "░" * (width - filled)


def render(args, lengths: dict) -> str:
    rows = read_cache(args.tag)
    log_path = REPO_ROOT / "logs" / f"{args.log_name}.log"
    waves = wave_times(log_path)
    now = datetime.now(timezone.utc)

    total_chars = sum(lengths.values())
    done_ids = {r["id"] for r in rows}
    done_chars = sum(lengths.get(i, 0) for i in done_ids)
    frac_chars = done_chars / total_chars if total_chars else 0
    out_tokens = sum(r.get("output_tokens", 0) for r in rows)
    truncated = sum(r.get("finish_reason") == "length" for r in rows)

    running = subprocess.run(["tmux", "has-session", "-t", args.session],
                             capture_output=True).returncode == 0
    started = datetime.fromtimestamp(log_path.stat().st_ctime, timezone.utc) if log_path.exists() else None

    # Character rate over the last few waves (falls back to the whole run)
    eta = rate_line = "waiting for the first wave to finish"
    if waves:
        ordered = sorted(lengths, key=lambda i: lengths[i], reverse=True)
        cum = [0]
        for i in ordered:
            cum.append(cum[-1] + lengths[i])
        recent = waves[-4:]
        t0, n0 = (recent[0] if len(recent) > 1 else (started, 0))
        t1, n1 = recent[-1]
        chars = cum[min(n1, len(ordered))] - cum[min(n0, len(ordered))]
        secs = (t1 - t0).total_seconds()
        if secs > 0 and chars > 0:
            rate = chars / secs
            remaining = total_chars - done_chars
            eta_secs = remaining / rate
            finish = datetime.fromtimestamp(now.timestamp() + eta_secs, timezone.utc)
            eta = f"{fmt_duration(eta_secs)}  (finishes ~{finish.strftime('%a %H:%M UTC')})"
            rate_line = f"{rate * 60 / 1e6:.2f}M chars/min over the last {max(len(recent) - 1, 1)} wave(s)"

    elapsed = fmt_duration((now - started).total_seconds()) if started else "-"
    last_wave = (fmt_duration((now - waves[-1][0]).total_seconds()) + " ago") if waves else "-"
    lines = [
        f"  Gemma re-judge  ·  tag '{args.tag}'  ·  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        f"  Status       {'RUNNING' if running else 'NOT RUNNING'} (tmux session '{args.session}')",
        f"  Text judged  {bar(frac_chars)} {frac_chars:6.1%}",
        f"  Segments     {len(done_ids):,} / {len(lengths):,}  (longest first)",
        f"  Output       {out_tokens:,} tokens   ·   {truncated} segment(s) hit the length limit",
        f"  Rate         {rate_line}",
        f"  Elapsed      {elapsed}   ·   last wave finished {last_wave}",
        f"  Remaining    {eta}",
        f"  GPU {args.gpu}        {gpu_status(args.gpu)}",
        "",
        "  Progress updates once per wave of 512 segments. Ctrl-C closes this view; the job keeps running.",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Dashboard for a local judge run")
    parser.add_argument("--tag", default="gemma")
    parser.add_argument("--session", default="gemma-rejudge")
    parser.add_argument("--log-name", default="gemma-rejudge")
    parser.add_argument("--gpu", type=int, default=7)
    parser.add_argument("--segment-tokens", type=int, default=6000)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    print("Computing segment sizes (first time only)...", flush=True)
    lengths = segment_lengths(args.tag, args.segment_tokens)
    while True:
        text = render(args, lengths)
        if args.once:
            print(text)
            return
        print("\033[2J\033[H" + text, flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
