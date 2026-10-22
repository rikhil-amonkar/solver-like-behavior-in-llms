"""
Judge items for the SLB ontology (docs/SLB_ONTOLOGY.md), built from the stored runs.

- Segments: each trace's reasoning before the code, cut into the 2k-token segments the
  local judge has always used, and each segment into numbered paragraphs (the unit the
  A judge labels and a human would label).
- Programs / traces: problem, reasoning, program and its output (B and C judges).

Item ids are "<model>/<task>/<cond>/<example_id>" (plus "#<segment>" for segments) and
carry a hash of the text they judge, so a re-run trace invalidates its cached labels.
"""

import hashlib
import json
import re
from pathlib import Path

from chunking.reasoning_splitter import split_reasoning_by_tokens

REPO = Path(__file__).resolve().parent.parent
MODELS = ["deepseek", "gpt", "qwen"]
TASKS = ["calendar", "meeting", "zebralogic", "blocksworld"]
CONDS = ["baseline", "caution_a", "caution_b"]
SEGMENT_TOKENS = 2000


def paragraphs(text):
    """Split a segment into labelling units: blank-line paragraphs, long ones cut at line breaks, then sentences."""
    units = []
    for para in re.split(r"\n\s*\n", text):
        if not para.strip():
            continue
        pieces = [para] if len(para) <= 700 else para.split("\n")
        buf = ""
        for piece in pieces:
            piece_parts = re.split(r"(?<=[.!?])\s+", piece) if len(piece) > 1200 else [piece]
            for p in piece_parts:
                if buf and len(buf) + len(p) > 700:
                    units.append(buf)
                    buf = ""
                buf = f"{buf}\n{p}" if buf else p
        if buf.strip():
            units.append(buf)
    return [u.strip("\n") for u in units if u.strip()]


def text_hash(*parts):
    return hashlib.sha1("\x00".join(parts).encode("utf-8")).hexdigest()[:10]


def load(root, model, task, cond, kind):
    path = REPO / root / model / task / f"{cond}_{kind}.json"
    return {e["example_id"]: e for e in json.load(open(path))["examples"]} if path.exists() else {}


def build_items(root="output", cells=None):
    """Return (segments, traces) for every example in the given cells (default: all 36)."""
    cells = cells or [(m, t, c) for m in MODELS for t in TASKS for c in CONDS]
    segments, traces = [], []
    for m, t, c in cells:
        inf, ex = load(root, m, t, c, "inference"), load(root, m, t, c, "execution")
        for eid, e in ex.items():
            key = f"{m}/{t}/{c}/{eid}"
            reasoning = e.get("reasoning_before_code") or ""
            problem = inf.get(eid, {}).get("problem_text", "")
            ce = e.get("code_execution") or {}
            output = ce.get("stdout") or ""
            if t == "blocksworld":
                output = json.dumps({k: v for k, v in ce.items() if k not in ("domain_pddl", "problem_pddl")}, indent=1)
            program = e.get("extracted_code") or ""
            traces.append(dict(id=key, h=text_hash(reasoning, program, output), model=m, task=t, cond=c, example_id=eid,
                               problem=problem, reasoning=reasoning, program=program, output=output[:6000],
                               ran=bool(ce.get("ran")) and (t == "blocksworld" or ce.get("exit_code") == 0),
                               raw_stdout=ce.get("stdout") or ""))
            segs = split_reasoning_by_tokens(reasoning, SEGMENT_TOKENS) if reasoning.strip() else []
            for j, seg in enumerate(segs):
                paras = paragraphs(seg)
                if paras:
                    segments.append(dict(id=f"{key}#{j}", h=text_hash(seg), trace=key, model=m, task=t, cond=c,
                                         example_id=eid, segment_index=j, n_segments=len(segs),
                                         problem=problem, paragraphs=paras))
    return segments, traces
