#!/usr/bin/env python3
"""
Agreement between Harry's labels (the reliability sets) and each ontology judge.

Reference labels live in validation/reliability/<labeler>/{seg_labels,prog_labels}/<id>.json:
human (Harry, from the labelling artifact via ArtifactData out_dir) or claude
(Claude subagents, scripts/import_claude_labels.py).
Only items marked done count.

Reports, per split:
- A (paragraphs): SLB vs not (kappa, precision/recall of the judge against Harry),
  type N/V/P (kappa), search flag on paragraphs both call V, each purpose on
  paragraphs both call SLB, and the per-segment SLB share (Pearson r, mean abs error;
  shares weighted by characters, as the solver-like ratio is).
- B (programs): label and specification-change flag (accuracy, kappa, confusion),
  plus the static checker against Harry where it applies (GPT-OSS Meeting).

Usage:
    python scripts/judge_agreement.py --tag gemma_v1 [--split dev|test|all]
"""

import argparse
import collections
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
PURPOSES = ["ans", "chp", "chg", "int"]


def kappa(pairs):
    """Cohen's kappa for a list of (human, judge) labels."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in ca) / n / n
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def pr(pairs, pos):
    tp = sum(a == pos and b == pos for a, b in pairs)
    fp = sum(a != pos and b == pos for a, b in pairs)
    fn = sum(a == pos and b != pos for a, b in pairs)
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    return p, r


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float("nan")


def load_human(coll, labeler="human"):
    d = REL / labeler / coll
    out = {}
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        doc = json.load(open(f))
        body = doc.get("data", doc)
        if body.get("done"):
            out[f.stem] = body
    return out


def load_judge(kind, tag):
    path = REL / f"judge_{kind}_{tag}.jsonl"
    return {json.loads(l)["id"]: json.loads(l) for l in path.open()} if path.exists() else {}


def fmt(x):
    return "n/a" if x != x else f"{x:.2f}"


def report_a(segs, human, judge, split):
    rows, shares, missing = [], [], 0
    for s in segs:
        if (split != "all" and s["split"] != split) or s["id"] not in human or s["id"] not in judge:
            continue
        hp, jp = human[s["id"]].get("paras", {}), judge[s["id"]]["paras"]
        missing += len(judge[s["id"]]["missing"])
        hc = jc = tot = 0
        for i, text in enumerate(s["paragraphs"]):
            h = hp.get(str(i), {"t": "N", "s": False, "p": []})
            j = jp.get(str(i), {"t": "N", "s": False, "p": []})
            rows.append((h, j))
            tot += len(text)
            hc += len(text) * (h["t"] != "N")
            jc += len(text) * (j["t"] != "N")
        shares.append((hc / tot, jc / tot))
    if not rows:
        print("A: no labelled segments in this split yet")
        return
    slb = [(h["t"] != "N", j["t"] != "N") for h, j in rows]
    p, r = pr(slb, True)
    print(f"A judge: {len(shares)} segments, {len(rows)} paragraphs ({missing} paragraphs the judge did not label, counted as N)")
    print(f"  SLB vs not:  agreement {sum(a == b for a, b in slb) / len(slb):.2f}  kappa {fmt(kappa(slb))}  judge precision {fmt(p)} recall {fmt(r)}")
    t = [(h["t"], j["t"]) for h, j in rows]
    print(f"  type N/V/P:  agreement {sum(a == b for a, b in t) / len(t):.2f}  kappa {fmt(kappa(t))}")
    conf = collections.Counter(t)
    print("  confusion (rows Harry, cols judge):  " + "  ".join(
        f"{a}: " + " ".join(f"{conf[(a, b)]:>4}" for b in "NVP") for a in "NVP"))
    sv = [(h["s"], j["s"]) for h, j in rows if h["t"] == "V" and j["t"] == "V"]
    print(f"  search flag (both V, n={len(sv)}):  agreement {fmt(sum(a == b for a, b in sv) / len(sv) if sv else float('nan'))}  kappa {fmt(kappa(sv))}")
    both = [(h, j) for h, j in rows if h["t"] != "N" and j["t"] != "N"]
    for k in PURPOSES:
        pk = [(k in h["p"], k in j["p"]) for h, j in both]
        n_h = sum(a for a, _ in pk)
        print(f"  purpose {k} (both SLB, n={len(pk)}, Harry marks {n_h}):  kappa {fmt(kappa(pk))}  precision/recall {fmt(pr(pk, True)[0])}/{fmt(pr(pk, True)[1])}")
    xs, ys = zip(*shares)
    mae = sum(abs(x - y) for x, y in shares) / len(shares)
    print(f"  per-segment SLB share: Pearson r {fmt(pearson(xs, ys))}  mean abs error {mae:.3f}  mean Harry {sum(xs) / len(xs):.3f} judge {sum(ys) / len(ys):.3f}")


def report_b(progs, human, judge, split, static, tag):
    rows = [(p, human[p["id"]], judge[p["id"]]) for p in progs
            if (split == "all" or p["split"] == split) and p["id"] in human and p["id"] in judge]
    if not rows:
        print("B: no labelled programs in this split yet")
        return
    lab = [(h["b"], j["b"] if p["program"] else "na") for p, h, j in rows]
    print(f"B judge: {len(rows)} programs")
    print(f"  label:  agreement {sum(a == b for a, b in lab) / len(lab):.2f}  kappa {fmt(kappa(lab))}")
    conf = collections.Counter(lab)
    for a in sorted({a for a, _ in lab}):
        print(f"    Harry {a:<13} -> " + ", ".join(f"{b}: {c}" for (x, b), c in sorted(conf.items()) if x == a))
    spec = [(h.get("spec", "none"), j["spec"]) for _, h, j in rows]
    print(f"  spec change:  agreement {sum(a == b for a, b in spec) / len(spec):.2f}  kappa {fmt(kappa(spec))}")
    st = [(h["b"] == "hardcoded" or h["b"] == "partly_fixed", static[(p["cond"], p["example_id"])])
          for p, h, _ in rows if p["model"] == "gpt" and p["task"] == "meeting" and (p["cond"], p["example_id"]) in static]
    cj = load_judge("c", tag)
    ext = [(h.get("extent"), cj[p["id"]]["extent"]) for p, h, _ in rows if h.get("extent") and p["id"] in cj]
    if ext:
        print(f"C judge, A2 extent (n={len(ext)}):  agreement {sum(a == b for a, b in ext) / len(ext):.2f}  kappa {fmt(kappa(ext))}")
        m = [(h["match"], cj[p["id"]]["match"]) for p, h, _ in rows
             if h.get("extent") == "complete" and h.get("match") in ("yes", "no") and p["id"] in cj]
        print(f"C judge, C1 match (Harry: complete with output, n={len(m)}):  agreement {fmt(sum(a == b for a, b in m) / len(m) if m else float('nan'))}  kappa {fmt(kappa(m))}")
    if st:
        print(f"  static checker, GPT-OSS Meeting (hardcoded or partly fixed vs not, n={len(st)}):  agreement {sum(a == b for a, b in st) / len(st):.2f}  kappa {fmt(kappa(st))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--labeler", default="human", help="Reference labels: validation/reliability/<labeler>/ (human or claude)")
    args = ap.parse_args()
    segs = json.load(open(REL / "segments.json"))
    progs = json.load(open(REL / "programs.json"))
    static = {}
    for c in ["baseline", "caution_a", "caution_b"]:
        for e in json.load(open(REPO / f"output/gpt/meeting/{c}_hardcoded_static.json"))["examples"]:
            if e["label"] in ("hardcoded", "not_hardcoded"):
                static[(c, e["example_id"])] = e["label"] == "hardcoded"
    print(f"== split: {args.split}, judge tag: {args.tag}, reference: {args.labeler} ==")
    report_a(segs, load_human("seg_labels", args.labeler), load_judge("a", args.tag), args.split)
    report_b(progs, load_human("prog_labels", args.labeler), load_judge("b", args.tag), args.split, static, args.tag)


if __name__ == "__main__":
    main()
