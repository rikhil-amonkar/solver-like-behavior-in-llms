#!/usr/bin/env python3
"""
Assemble per-trace SLB ontology labels (docs/SLB_ONTOLOGY.md) from the Gemma judges
(src/run_ontology_judges.py --items all) plus deterministic script judges.

Per trace:
- A1 (script over Gemma paragraph labels): "values" if any paragraph is V (or VP), else none.
- Solver-like ratio (script): characters in SLB paragraphs / characters in all paragraphs.
- A2 (Gemma C judge on the Values paragraphs): complete if it finds a full answer, else partial;
  none exactly when A1 is none.
- B (script, then Gemma): "na" if there is no program, it failed, or printed nothing;
  otherwise the Gemma B label. Spec change from the Gemma B judge.
- C1 (script, Gemma fallback): when A2 is complete and the program ran, parse the prose
  answer and the program output with the task parsers and compare; if either does not
  parse, use the C judge's own yes/no. c1_source records which.
- C2 (script): the task validator on the prose answer (scripts/validate_prose_answers.py).
- Flags (script): B hardcoded/partly_fixed/steered without A1 values; A2 complete without
  any V paragraph; paragraphs the A judge did not label (counted as not SLB).

Writes output/<model>/<task>/<cond>_ontology_<tag>.json and prints a summary table.

Usage (env venv):
    python scripts/assemble_ontology_labels.py --tag gemma_v1
"""

import argparse
import collections
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from ontology_items import build_items
from execution.output_formatter import parse_output_by_task
from general.io_utils import load_problems_json
from validate_prose_answers import check as validate_prose



def load_judge(kind, tag):
    """Latest result per (id, hash) over all shards."""
    out = {}
    for f in sorted((REPO / "output/ontology").glob(f"judge_{kind}_{tag}*.jsonl")):
        for line in f.open():
            r = json.loads(line)
            out[(r["id"], r.get("h"))] = r
    return out


def plan_actions(text):
    """Normalized action tuples from a plan written as '(unstack a b)' lines or 'unstack a b'."""
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith(";"))  # planner comments, e.g. "; cost = 4 (unit cost)"
    acts = re.findall(r"\(([^()]+)\)", text) or [l for l in text.splitlines() if l.strip()]
    return [tuple(a.lower().replace(",", " ").split()) for a in acts if a.strip() and not a.strip().startswith(";")]


_PROBLEMS = {}


def problem_data(task, eid):
    """Problem dict the task parsers need (ZebraLogic needs its attribute list)."""
    if task not in _PROBLEMS:
        _PROBLEMS[task] = load_problems_json(task)
    return _PROBLEMS[task].get(eid, {})


def answer_parses(task, eid, answer):
    if not (answer or "").strip():
        return False
    if task == "blocksworld":
        return bool(plan_actions(answer))
    return parse_output_by_task(answer, task, problem_data(task, eid)) is not None


def extent_from_segments(trace, seg_results):
    """A2 and prose answer from the per-segment C judge (cs): complete if any segment states a
    complete answer that parses (the prose answer is the last such one), else partial if any
    segment commits some decisions, else none. Returns (extent, answer, segment index)."""
    last, partial = None, False
    for j, r in enumerate(seg_results):
        if r is None:
            continue
        if r.get("extent") == "complete" and answer_parses(trace["task"], trace["example_id"], r.get("answer")):
            last = (j, r["answer"])
        elif r.get("extent") in ("complete", "partial"):
            partial = True
    if last:
        return "complete", last[1], last[0]
    return ("partial" if partial else "none"), "", None


def c1_script(trace, prose):
    """True/False if both answers parse and can be compared, else None."""
    task = trace["task"]
    if task == "blocksworld":
        a, b = plan_actions(prose), plan_actions(trace["plan"])
        return (a == b) if a and b else None
    pd = problem_data(task, trace["example_id"])
    a = parse_output_by_task(prose, task, pd)
    b = parse_output_by_task(trace["raw_stdout"], task, pd)
    if a is None or b is None:
        return None
    return a == b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="gemma_v1")
    args = ap.parse_args()
    segments, traces = build_items()
    ja, jb, jc = load_judge("a", args.tag), load_judge("b", args.tag), load_judge("c", args.tag)
    by_trace = collections.defaultdict(list)
    for s in segments:
        by_trace[s["trace"]].append(s)

    cache, per_cell = {}, collections.defaultdict(list)
    missing_judgements = collections.Counter()
    for t in traces:
        # ---- A from paragraph labels ----
        chars = slb_chars = 0
        types, n_missing, judged = set(), 0, True
        for s in by_trace[t["id"]]:
            r = ja.get((s["id"], s["h"]))
            if r is None:
                judged = False
                missing_judgements["a"] += 1
                continue
            n_missing += len(r["missing"])
            for i, text in enumerate(s["paragraphs"]):
                lab = r["paras"].get(str(i), {"t": "N", "s": False, "p": []})
                chars += len(text)
                if "V" in lab["t"]:  # V or VP; A1 properties dropped on 2026-10-29, so P alone is not SLB
                    slb_chars += len(text)
                    types.add("values")
        a1 = sorted(types) or ["none"]
        rec = dict(example_id=t["example_id"], a_judged=judged and bool(by_trace[t["id"]]),
                   A1=a1,
                   ratio=round(slb_chars / chars, 4) if chars else None, unlabelled_paragraphs=n_missing)

        # ---- A2, C from the C judge + scripts ----
        c = jc.get((t["id"], t["h"]))
        if c is None and t["reasoning"].strip():
            missing_judgements["c"] += 1
        # A2 (2026-10-30): with any Values paragraph the extent is at least partial (a tentative
        # schedule counts); "none" only when A1 is none
        rec["A2"] = None if c is None and "values" in a1 else "none" if "values" not in a1 else ("complete" if c["extent"] == "complete" else "partial")
        prose = (c or {}).get("prose_answer") or ""
        has_output = t["ran"] and bool(t["raw_stdout"].strip() if t["task"] != "blocksworld" else t["output"])
        rec["C1"] = rec["c1_source"] = rec["C2"] = None
        if rec["A2"] == "complete" and prose.strip():
            if has_output:
                v = c1_script(t, prose)
                rec["C1"], rec["c1_source"] = (v, "script") if v is not None else (
                    {"yes": True, "no": False}.get(c["match"]), "gemma")
            try:
                rec["C2"] = validate_prose(t["task"], t["example_id"], prose, cache)[0]
            except Exception:
                rec["C2"] = None

        # ---- B: script n/a, else Gemma ----
        if not t["program"].strip() or not has_output:
            rec["B"], rec["b_source"] = "na", "script"
        else:
            b = jb.get((t["id"], t["h"]))
            if b is None:
                missing_judgements["b"] += 1
            rec["B"], rec["b_source"] = (b["b"] if b else None), "gemma"
        b = jb.get((t["id"], t["h"]))
        rec["spec"] = b["spec"] if (b and t["program"].strip()) else None

        # ---- consistency flags ----
        flags = []
        if rec["B"] in ("hardcoded", "partly_fixed", "steered") and "values" not in a1:
            flags.append("B_without_values")
        if rec["A2"] == "complete" and "values" not in a1:
            flags.append("complete_without_values")
        rec["flags"] = flags
        per_cell[(t["model"], t["task"], t["cond"])].append(rec)

    for (m, task, cond), recs in per_cell.items():
        dest = REPO / f"output/{m}/{task}/{cond}_ontology_{args.tag}.json"
        json.dump({"tag": args.tag, "ontology": "docs/SLB_ONTOLOGY.md", "examples": recs}, open(dest, "w"), indent=1)

    print("missing judgements:", dict(missing_judgements) or "none")
    hdr = ["cell", "n", "ratio", "values", "props", "none",
           "A2 cmpl", "B hard", "B part", "B steer", "B ind", "B na", "spec!", "C1 no", "C2 no", "flags"]
    print("\t".join(hdr))
    for key in sorted(per_cell):
        r = per_cell[key]
        n = len(r)
        pct = lambda f: f"{100 * sum(map(f, r)) / n:.0f}"
        ratios = [x["ratio"] for x in r if x["ratio"] is not None]
        c1 = [x["C1"] for x in r if x["C1"] is not None]
        c2 = [x["C2"] for x in r if x["C2"] is not None]
        print("\t".join([
            "/".join(key), str(n), f"{sum(ratios) / len(ratios):.2f}" if ratios else "-",
            pct(lambda x: "values" in x["A1"]), pct(lambda x: "properties" in x["A1"]), pct(lambda x: x["A1"] == ["none"]),
            pct(lambda x: x["A2"] == "complete"),
            *[pct(lambda x, b=b: x["B"] == b) for b in ["hardcoded", "partly_fixed", "steered", "independent", "na"]],
            pct(lambda x: x["spec"] == "not_required"),
            f"{c1.count(False)}/{len(c1)}", f"{c2.count(False)}/{len(c2)}", str(sum(bool(x["flags"]) for x in r))]))


if __name__ == "__main__":
    main()
