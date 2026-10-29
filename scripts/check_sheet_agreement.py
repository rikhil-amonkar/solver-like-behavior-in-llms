#!/usr/bin/env python3
"""
Agreement of a judge version with Harry's 20-item check sheets, per ontology node.

Reference labels:
- A1: validation/reliability/human/verify/ (type; the rejects flag where Harry checked it).
- A2: validation/reliability/human/verify_a2/, plus two corrections confirmed by script and
  reading (e14, e16 are complete). Partial/none labels Harry could not fully verify count
  as given, so A2 agreement on them is an upper bound.
- A3, B, spec, C1, C2: validation/reliability/human/checks/ (the judge-check page).

Judge labels for a tag come from the full run (output/ontology/judge_*_<tag>*.jsonl) or
from the check-set run (validation/reliability/checks/judge_*_<tag>.jsonl). C1 and C2 are
recomputed by script from that version's extracted prose answers.

Items shown to the judge as prompt examples (A1 v010, v011 from gemma_v2 on) are excluded.

Usage (env venv):
    python scripts/check_sheet_agreement.py --tag gemma_v1
    python scripts/check_sheet_agreement.py --tag gemma_v2
"""

import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from ontology_items import build_items
from assemble_ontology_labels import c1_script
from validate_prose_answers import check as validate_prose

A2_CORRECTIONS = {"e14": "complete", "e16": "complete"}  # docs/results/2026-10-22_ONTOLOGY_LABELS.md
IN_PROMPT = {"gemma_v2": {"v010", "v011"}}  # used as negative examples in prompts/judge/a_paragraphs.txt


def load_judge(kind, tag):
    out = {}
    files = glob.glob(str(REPO / f"output/ontology/judge_{kind}_{tag}*.jsonl")) + glob.glob(str(REL / f"checks/judge_{kind}_{tag}.jsonl"))
    for f in sorted(files):
        for line in open(f):
            r = json.loads(line)
            out[(r["id"], r.get("h"))] = r
    return out


def marks(sub):
    out = {}
    for f in glob.glob(str(REL / "human" / sub / "*.json")):
        d = json.load(open(f))
        out[Path(f).stem] = d.get("data", d)
    return out


def report(name, pairs, note=""):
    pairs = [(h, j) for h, j in pairs if h is not None]
    if not pairs:
        print(f"{name:<14} no reference labels yet")
        return
    judged = [(h, j) for h, j in pairs if j is not None]
    agree = sum(h == j for h, j in judged)
    print(f"{name:<14} {agree}/{len(judged)} agree" + (f"  ({len(pairs) - len(judged)} not judged by this version)" if len(judged) < len(pairs) else "") + (f"  {note}" if note else ""))
    for h, j in judged:
        if h != j:
            print(f"{'':<16}reference {h!r}, judge {j!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    segments, traces = build_items()
    seg = {s["id"]: s for s in segments}
    tr = {t["id"]: t for t in traces}
    ja, jb, jc = load_judge("a", args.tag), load_judge("b", args.tag), load_judge("c", args.tag)
    excluded = IN_PROMPT.get(args.tag, set())
    print(f"== judge {args.tag} vs Harry's check sheets ==")

    def para_label(seg_id, i):
        s = seg[seg_id]
        r = ja.get((s["id"], s["h"]))
        return None if r is None else r["paras"].get(str(i), {"t": "N", "s": False, "p": []})

    # A1 type and rejects flag
    a1 = {it["id"]: it for it in json.load(open(REL / "a1_verify.json"))}
    m = marks("verify")
    types, flags = [], []
    for k, v in m.items():
        if k in excluded or k not in a1 or "human" not in v:
            continue
        it = a1[k]
        lab = para_label(it["segment"], it["para"])
        types.append((v["human"], lab["t"] if lab else None))
        if "searchOk" in v and v["human"] == "V":
            gold = it["gemma"]["s"] if v["searchOk"] else not it["gemma"]["s"]
            flags.append((gold, (lab["s"] if lab and lab["t"] == "V" else (False if lab else None))))
    report("A1 type", types, f"excluding {sorted(excluded)}" if excluded else "")
    report("A1 rejects", flags)

    # A2 extent
    a2 = {it["id"]: it for it in json.load(open(REL / "a2_verify.json"))}
    pairs = []
    for k, v in marks("verify_a2").items():
        if k not in a2 or not v.get("extent"):
            continue
        t = tr[a2[k]["trace"]]
        r = jc.get((t["id"], t["h"]))
        pairs.append((A2_CORRECTIONS.get(k, v["extent"]), r["extent"] if r else None))
    report("A2 extent", pairs, "(partial/none not fully verified by hand)")

    # Judge-check page sheets
    sheets = json.load(open(REL / "judge_checks.json"))
    cm = marks("checks")
    for name in ("a3", "b", "spec", "c1", "c2"):
        pairs = []
        for it in sheets[name]:
            v = cm.get(it["id"])
            if not v or "human" not in v or v["human"] == "unsure":
                continue
            gold = v["human"]
            t = tr.get(it["trace"])
            if name == "a3":
                lab = para_label(it["segment"], it["para"])
                pairs.append((sorted(gold), sorted(lab["p"]) if lab else None))
            elif name in ("b", "spec"):
                r = jb.get((t["id"], t["h"]))
                pairs.append((gold, r[name] if r else None))
            else:
                r = jc.get((t["id"], t["h"]))
                if r is None:
                    pairs.append((gold, None))
                    continue
                prose = r.get("prose_answer") or ""
                if r.get("extent") != "complete" or not prose.strip():
                    pairs.append((gold, "no complete prose answer"))
                elif name == "c1":
                    pairs.append((gold, c1_script(t, prose)))
                else:
                    try:
                        pairs.append((gold, validate_prose(t["task"], t["example_id"], prose, {})[0]))
                    except Exception as e:
                        pairs.append((gold, f"validator error: {e}"))
        report(name.upper() if name != "spec" else "Spec change", pairs)


if __name__ == "__main__":
    main()
