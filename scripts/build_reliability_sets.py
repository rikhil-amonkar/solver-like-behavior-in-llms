#!/usr/bin/env python3
"""
Build the human reliability sets for the SLB ontology judges (docs/SLB_ONTOLOGY.md).

- segments.json: reasoning segments (the Gemma judge's 2k-token unit), each split
  into numbered paragraphs. Both Harry and the A judge label every paragraph, so
  agreement is measured on identical units.
- programs.json: programs for the B labels (hardcoded / partly fixed / steered /
  independent, plus the specification-change flag), with the problem, the output
  and the reasoning for context.

Each item gets a split: the first DEV_SEGMENTS / DEV_PROGRAMS items (in labelling
order) are a dev set for writing judge prompts; agreement is reported on the rest.

Usage (env venv, for tiktoken):
    python scripts/build_reliability_sets.py
"""

import json
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from chunking.reasoning_splitter import split_reasoning_by_tokens

OUT = REPO / "validation" / "reliability"
MODELS = ["deepseek", "gpt", "qwen"]
TASKS = ["calendar", "meeting", "zebralogic", "blocksworld"]
CONDS = ["baseline", "caution_a", "caution_b"]
# being re-run on vLLM (docs/results/2026-10-22_TRACE_HEALTH.md); sampled later
SKIP_CELLS = {("qwen", "calendar", "baseline"), ("qwen", "calendar", "caution_a"), ("qwen", "meeting", "baseline")}
SEGMENT_TOKENS = 2000
N_SEGMENTS = 150
N_PROGRAMS = 60
DEV_SEGMENTS = 40
DEV_PROGRAMS = 15
SEED = 20261022

# Programs the ontology sweep flagged for rare B labels; included so they appear in the set.
FLAGGED_PROGRAMS = [
    # steered candidates
    ("deepseek", "meeting", "baseline", "meeting_planning_example_66"),
    ("deepseek", "meeting", "baseline", "meeting_planning_example_479"),
    ("deepseek", "meeting", "baseline", "meeting_planning_example_225"),
    ("deepseek", "meeting", "caution_a", "meeting_planning_example_225"),
    ("deepseek", "calendar", "baseline", "calendar_scheduling_example_98"),
    ("deepseek", "calendar", "baseline", "calendar_scheduling_example_784"),
    ("gpt", "calendar", "baseline", "calendar_scheduling_example_707"),
    # specification change / partly fixed
    ("gpt", "meeting", "baseline", "meeting_planning_example_118"),
    ("gpt", "meeting", "baseline", "meeting_planning_example_222"),
    ("qwen", "blocksworld", "baseline", "blocksworld_p64"),
    ("qwen", "blocksworld", "baseline", "blocksworld_p67"),
    ("gpt", "blocksworld", "baseline", "blocksworld_p19"),
]


def load(model, task, cond, kind):
    return {e["example_id"]: e for e in json.load(open(REPO / f"output/{model}/{task}/{cond}_{kind}.json"))["examples"]}


def paragraphs(text):
    """Split a segment into labelling units: blank-line paragraphs, long ones cut at line breaks, then sentences."""
    units = []
    for para in re.split(r"\n\s*\n", text):
        if not para.strip():
            continue
        pieces = [para] if len(para) <= 700 else para.split("\n")
        buf = ""
        for piece in pieces:
            if len(piece) > 1200:
                piece_parts = re.split(r"(?<=[.!?])\s+", piece)
            else:
                piece_parts = [piece]
            for p in piece_parts:
                if buf and len(buf) + len(p) > 700:
                    units.append(buf)
                    buf = ""
                buf = f"{buf}\n{p}" if buf else p
        if buf.strip():
            units.append(buf)
    return [u.strip("\n") for u in units if u.strip()]


def match_id(ids, prefix):
    """Find an example id by exact match or by prefix (BlocksWorld ids carry a constraint suffix)."""
    if prefix in ids:
        return prefix
    hits = [i for i in ids if i.startswith(prefix + "_")]
    return hits[0] if len(hits) == 1 else None


def main():
    rng = random.Random(SEED)
    cells = [(m, t, c) for m in MODELS for t in TASKS for c in CONDS if (m, t, c) not in SKIP_CELLS]
    data = {cell: (load(*cell, "inference"), load(*cell, "execution"), load(*cell, "evaluation")) for cell in cells}

    # ---- segments: spread N_SEGMENTS over cells, one segment per trace ----
    per_cell = [N_SEGMENTS // len(cells) + (i < N_SEGMENTS % len(cells)) for i in range(len(cells))]
    segments = []
    for cell, k in zip(cells, per_cell):
        inf, ex, ev = data[cell]
        ids = [i for i in sorted(ex) if (ex[i].get("reasoning_before_code") or "").strip()]
        for eid in rng.sample(ids, k):
            segs = split_reasoning_by_tokens(ex[eid]["reasoning_before_code"], SEGMENT_TOKENS)
            j = rng.randrange(len(segs))
            segments.append(dict(
                model=cell[0], task=cell[1], cond=cell[2], example_id=eid,
                segment_index=j, n_segments=len(segs),
                problem=inf[eid]["problem_text"], paragraphs=paragraphs(segs[j])))
    rng.shuffle(segments)
    for n, s in enumerate(segments):
        s["id"] = f"s{n:03d}"
        s["split"] = "dev" if n < DEV_SEGMENTS else "test"

    # ---- programs: flagged ones, then GPT-OSS Meeting by static label, then random ----
    chosen = []
    for m, t, c, prefix in FLAGGED_PROGRAMS:
        if (m, t, c) in data:
            eid = match_id(data[(m, t, c)][1], prefix)
            if eid:
                chosen.append((m, t, c, eid))
    static = {}
    for c in CONDS:
        for e in json.load(open(REPO / f"output/gpt/meeting/{c}_hardcoded_static.json"))["examples"]:
            static[(c, e["example_id"])] = e["reason"]
    for reason, k in [("literal", 4), ("fixed_plan", 4), ("replay", 1), ("search", 3)]:
        pool = sorted(key for key, r in static.items() if r == reason and ("gpt", "meeting", *key) not in chosen)
        for c, eid in rng.sample(pool, min(k, len(pool))):
            chosen.append(("gpt", "meeting", c, eid))
    while len(chosen) < N_PROGRAMS:
        cell = rng.choice(cells)
        eid = rng.choice(sorted(data[cell][1]))
        if (*cell, eid) not in chosen and (data[cell][1][eid].get("extracted_code") or "").strip():
            chosen.append((*cell, eid))
    rng.shuffle(chosen)
    programs = []
    for n, (m, t, c, eid) in enumerate(chosen):
        inf, ex, ev = data[(m, t, c)]
        ce = ex[eid].get("code_execution") or {}
        output = ce.get("stdout") or ce.get("stderr") or ""
        if t == "blocksworld":
            output = json.dumps({k: v for k, v in ce.items() if k not in ("domain_pddl", "problem_pddl")}, indent=1)
        programs.append(dict(
            id=f"p{n:03d}", split="dev" if n < DEV_PROGRAMS else "test",
            model=m, task=t, cond=c, example_id=eid,
            problem=inf[eid]["problem_text"], reasoning=ex[eid].get("reasoning_before_code") or "",
            program=ex[eid].get("extracted_code") or "", output=str(output)[:6000],
            correct=bool(ev.get(eid, {}).get("correct"))))

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(segments, open(OUT / "segments.json", "w"), indent=1)
    json.dump(programs, open(OUT / "programs.json", "w"), indent=1)
    print(f"{len(segments)} segments, {sum(len(s['paragraphs']) for s in segments)} paragraphs; {len(programs)} programs")


if __name__ == "__main__":
    main()
