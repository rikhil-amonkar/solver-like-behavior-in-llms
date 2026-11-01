#!/usr/bin/env python3
"""
Script check of the C judge's A2 labels against the program output (no LLM).

For each trace, find whether the program's answer is written out in the reasoning:
- Calendar: day, start and end of the program's slot within one 300-character window.
- Meeting: every meeting start time of the program's itinerary appears in the reasoning.
- ZebraLogic: every house of the program's grid has all its values on one line, and all
  houses lie within 2,000 characters (a written-out grid).
- BlocksWorld: the program's plan actions appear in the reasoning in order.

Then, per Gemma extent:
- complete: C1 by parser (prose answer == program output) and whether the extracted
  prose answer's values occur in the reasoning (grounded) or not (possibly invented);
- partial / none: "answer_in_prose" means the program's full answer is written in the
  reasoning, which makes partial/none suspect (the prose may reach a complete answer).

Usage (env venv):
    python scripts/check_a2_against_output.py --sheet validation/reliability/a2_verify.json
    python scripts/check_a2_against_output.py --all
"""

import argparse
import collections
import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from ontology_items import build_items
from execution.output_formatter import parse_output_by_task
from assemble_ontology_labels import plan_actions, problem_data

TIME = re.compile(r"\b(\d{1,2}):(\d{2})\s*([AaPp][Mm])?")


def norm_times(text):
    """All clock times in the text as minutes since midnight (12h with AM/PM, else 24h)."""
    out = []
    for h, m, ap in TIME.findall(text):
        h, m = int(h), int(m)
        if ap:
            h = h % 12 + (12 if ap.lower() == "pm" else 0)
        out.append((h * 60 + m, len(out)))
    return out


def window_has(text, needles, width):
    """True if all needles (lowercase strings) occur within one window of the text."""
    low = text.lower()
    first = needles[0]
    for m in re.finditer(re.escape(first), low):
        seg = low[max(0, m.start() - width): m.start() + width]
        if all(n in seg for n in needles):
            return True
    return False


def answer_in_text(task, answer, text, raw_answer=""):
    """Is the given (parsed) answer written out in the text? None if it cannot be decided."""
    if task == "calendar":
        if not answer or len(answer) < 3:
            return None
        day, start, end = (str(x).lower() for x in answer[:3])
        times = {"start": start, "end": end}
        # accept 9:00 / 09:00
        variants = lambda t: {t, t.lstrip("0")}
        low = text.lower()
        for m in re.finditer(day, low):
            seg = low[max(0, m.start() - 300): m.start() + 300]
            if all(any(v in seg for v in variants(t)) for t in times.values()):
                return True
        return False
    if task == "meeting":
        starts = [s for s in (answer or []) if "meet" in s.lower()]
        if not starts:
            return None
        times = {t for t, _ in norm_times(" ".join(starts))}
        found = {t for t, _ in norm_times(text)}
        return times <= found
    if task == "zebralogic":
        if not isinstance(answer, dict) or not answer:
            return None
        rows = answer.get("rows") or []
        if not rows:
            return None
        # each house's values on one line, all houses within 2,000 characters (a written-out grid,
        # not a restatement of the attribute lists or clues)
        lines = text.lower().splitlines()
        offs, pos = [], 0
        for l in lines:
            offs.append(pos)
            pos += len(l) + 1
        hits = []
        for row in rows:
            vals = [str(v).lower() for v in row[1:] if str(v).strip()]  # row[0] is the house number
            hits.append([offs[i] for i, l in enumerate(lines) if all(v in l for v in vals)])
        if not all(hits):
            return False
        return any(all(any(abs(o - a) <= 2000 for o in h) for h in hits) for a in hits[0])
    if task == "blocksworld":
        acts = plan_actions(raw_answer)
        if not acts:
            return None
        low = " ".join(text.lower().replace("(", " ( ").replace(")", " ) ").split())
        pos = 0
        for a in acts:
            needle = " ".join(a)
            i = low.find(needle, pos)
            if i < 0:
                return False
            pos = i + len(needle)
        return True
    return None


def snippet(t, c, before=700, after=900):
    """The passage of the reasoning to read: around the last place the program's answer (or,
    for complete, the extracted prose answer) starts to be written out; else the reasoning's end."""
    text = t["reasoning"]
    raw = (c.get("prose_answer") or "") if c.get("extent") == "complete" else (t["plan"] if t["task"] == "blocksworld" else t["raw_stdout"])
    keys = []
    if t["task"] == "blocksworld":
        acts = plan_actions(raw or "")
        keys = [" ".join(acts[0])] if acts else []
    else:
        keys = [m.group(0) for m in TIME.finditer(raw or "")][:1] or [w for w in re.findall(r"[A-Za-z]{4,}", raw or "")][:1]
    low = " ".join(text.lower().replace("(", " ( ").replace(")", " ) ").split()) if t["task"] == "blocksworld" else text.lower()
    pos = low.rfind(keys[0].lower()) if keys else -1
    if pos < 0:
        return "[end of reasoning] " + low[-(before + after):]
    return low[max(0, pos - before): pos + after]


def program_answer(t):
    if t["task"] == "blocksworld":
        return t["plan"], t["plan"]
    return parse_output_by_task(t["raw_stdout"], t["task"], problem_data(t["task"], t["example_id"])), t["raw_stdout"]


def prose_answer(t, prose):
    if t["task"] == "blocksworld":
        return prose, prose
    return parse_output_by_task(prose, t["task"], problem_data(t["task"], t["example_id"])), prose


def check(t, c):
    extent = c.get("extent")
    prog, prog_raw = program_answer(t)
    row = {"trace": t["id"], "task": t["task"], "model": t["model"], "extent": extent}
    row["answer_in_prose"] = answer_in_text(t["task"], prog, t["reasoning"], prog_raw) if prog or prog_raw else None
    if extent == "complete":
        pa, pa_raw = prose_answer(t, c.get("prose_answer") or "")
        row["prose_parses"] = pa is not None and pa != ""
        row["grounded"] = answer_in_text(t["task"], pa, t["reasoning"], pa_raw) if row["prose_parses"] else None
        if t["task"] == "blocksworld":
            row["c1_parser"] = (plan_actions(pa_raw) == plan_actions(prog_raw)) if plan_actions(pa_raw) and plan_actions(prog_raw) else None
        else:
            row["c1_parser"] = (pa == prog) if (pa is not None and prog is not None) else None
        row["gemma_match"] = c.get("match")
    return row


def load_c(tag):
    out = {}
    for f in sorted(glob.glob(str(REPO / f"output/ontology/judge_c_{tag}*.jsonl")) + glob.glob(str(REPO / f"validation/reliability/checks/judge_c_{tag}.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            out[(r["id"], r.get("h"))] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", help="a2_verify.json: check its items")
    ap.add_argument("--all", action="store_true", help="check every trace and summarize")
    ap.add_argument("--tag", default="gemma_v1")
    ap.add_argument("--traces", help="JSON list of trace ids (or items with a 'trace' field): check these, with snippets for reading")
    ap.add_argument("--out", help="with --traces: write rows (with snippets) here")
    args = ap.parse_args()
    _, traces = build_items()
    by_id = {t["id"]: t for t in traces}
    jc = load_c(args.tag)
    if args.sheet:
        for it in json.load(open(args.sheet)):
            t = by_id[it["trace"]]
            c = jc.get((t["id"], t["h"])) or it["gemma"]
            r = check(t, c)
            print(it["id"], r)
    if args.traces:
        ids = [x if isinstance(x, str) else x.get("trace", x.get("id")) for x in json.load(open(args.traces))]
        rows = []
        for i in ids:
            t = by_id[i]
            c = jc.get((t["id"], t["h"])) or next((v for k, v in jc.items() if k[0] == t["id"]), None)  # condensed runs hash differently
            if c is None:
                continue
            r = check(t, c)
            r["prose_answer"] = c.get("prose_answer", "")
            r["snippet"] = snippet(t, c)
            rows.append(r)
        json.dump(rows, open(args.out, "w"), indent=1)
        for r in rows:
            print(r["trace"], {k: r.get(k) for k in ("extent", "answer_in_prose", "grounded", "c1_parser")})
    if args.all:
        rows = [check(t, jc[(t["id"], t["h"])]) for t in traces if (t["id"], t["h"]) in jc]
        summ = collections.defaultdict(collections.Counter)
        for r in rows:
            key = (r["model"], r["task"])
            summ[key][(r["extent"], "in_prose" if r["answer_in_prose"] else "not_in_prose" if r["answer_in_prose"] is False else "undecided")] += 1
            if r["extent"] == "complete":
                summ[key][("complete", "grounded" if r["grounded"] else "ungrounded" if r["grounded"] is False else "grounded?")] += 1
                summ[key][("complete", f"c1_parser={r['c1_parser']}", f"gemma={r['gemma_match']}")] += 1
        for k in sorted(summ):
            print("/".join(k), dict(sorted(summ[k].items(), key=str)))
        json.dump(rows, open(REPO / "validation/reliability/a2_script_check.json", "w"), indent=1)


if __name__ == "__main__":
    main()
