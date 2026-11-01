#!/usr/bin/env python3
"""Compare deterrence runs with the baseline on the same problems: solver-like ratio, share of
traces with values (A1), solver-like characters per problem, reasoning length and accuracy.

A labels: <root>/ontology/judge_a_<tag>.jsonl (scripts/deter_judge_items.py, then the A judge).
Baseline: <base>/<model>/<task>/baseline_ontology_gemma_v11_b5t.json and baseline_evaluation.json, where
<base> is output_crossfl for a *_crossfl root (same task and FL) and output otherwise, restricted
to the problems the deterrence run covers. A batch group's trace is compared with its members'
baseline traces: ratio vs their mean ratio, values chars / K vs their mean values chars, "any values" vs the share of members whose trace has values.

Usage: python scripts/deter_compare.py --root output_deter_pilot [--tag gemma_v11t]
"""

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from ontology_items import build_items  # noqa: E402

BASE_TAG = "gemma_v11_b5t"


def a_by_trace(items, labels):
    """trace id -> (values chars, all chars, any values, all segments judged)"""
    out = collections.defaultdict(lambda: [0, 0, False, True])
    for it in items:
        r = labels.get((it["id"], it["h"]))
        acc = out[it["trace"]]
        if r is None:
            acc[3] = False
            continue
        for i, text in enumerate(it["paragraphs"]):
            t = r["paras"].get(str(i), {"t": "N"})["t"]
            acc[1] += len(text)
            if "V" in t:
                acc[0] += len(text)
                acc[2] = True
    return out


def baseline_values_chars(base, model, task, eids):
    """Baseline values chars per problem, from the baseline's A labels."""
    segs, _ = build_items(base, [(model, task, "baseline")])
    labels = {}
    for f in (REPO / base / "ontology").glob("judge_a_gemma_v11t*.jsonl"):
        for line in f.open():
            r = json.loads(line)
            labels[(r["id"], r.get("h"))] = r
    acc = a_by_trace([s for s in segs if s["example_id"] in eids], labels)
    return {k.rsplit("/", 1)[1]: v for k, v in acc.items()}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--tag", default="gemma_v11t")
    args = ap.parse_args()
    root = REPO / args.root
    items = json.load(open(root / "ontology/a_items.json"))
    labels = {}
    jf = root / f"ontology/judge_a_{args.tag}.jsonl"
    if jf.exists():
        for line in jf.open():
            r = json.loads(line)
            labels[(r["id"], r.get("h"))] = r
    acc = a_by_trace(items, labels)
    base = "output_crossfl" if args.root.rstrip("/").endswith("crossfl") else "output"

    rows = []
    for ev_path in sorted(root.glob("*/*/*_evaluation.json")):
        model, task = ev_path.parts[-3], ev_path.parts[-2]
        cond = ev_path.name[: -len("_evaluation.json")]
        ev = {e["example_id"]: e for e in json.load(open(ev_path))["examples"]}
        ex = {e["example_id"]: e for e in json.load(open(ev_path.with_name(f"{cond}_execution.json")))["examples"]}
        eids = set(ev)
        base_ont = {e["example_id"]: e for e in json.load(open(REPO / base / f"{model}/{task}/baseline_ontology_{BASE_TAG}.json"))["examples"]}
        base_ev = {e["example_id"]: e for e in json.load(open(REPO / base / f"{model}/{task}/baseline_evaluation.json"))["examples"]}
        base_ex = {e["example_id"]: e for e in json.load(open(REPO / base / f"{model}/{task}/baseline_execution.json"))["examples"]}
        base_vc = baseline_values_chars(base, model, task, eids)

        # units: a trace of the deterrence run and the baseline problems it covers
        units = collections.defaultdict(list)
        for eid, e in ex.items():
            units[e["batch"]["group_id"] if "batch" in e else eid].append(eid)
        d_ratio, b_ratio, d_vals, b_vals, d_vc, b_vc, d_tok, b_tok, judged = [], [], [], [], [], [], [], [], 0
        for unit, members in units.items():
            k = len(members)
            a = acc.get(f"{model}/{task}/{cond}/{unit}")
            d_tok.append((ex[members[0]].get("reasoning_before_code_tokens") or 0) / k)
            b_tok.append(mean([base_ex[m].get("reasoning_before_code_tokens") for m in members]))
            if not a or not a[3]:
                continue
            judged += 1
            d_ratio.append(a[0] / a[1] if a[1] else None)
            d_vals.append(float(a[2]))
            d_vc.append(a[0] / k)
            b_ratio.append(mean([base_ont[m].get("ratio") for m in members]))
            b_vals.append(mean([float("values" in base_ont[m].get("A1", [])) for m in members]))
            b_vc.append(mean([base_vc.get(m, (0,))[0] for m in members]))
        rows.append(dict(
            cell=f"{model}/{task}/{cond}", problems=len(eids), traces=len(units), judged=judged,
            ratio=(mean(d_ratio), mean(b_ratio)), values=(mean(d_vals), mean(b_vals)),
            values_chars_per_problem=(mean(d_vc), mean(b_vc)), reasoning_tokens_per_problem=(mean(d_tok), mean(b_tok)),
            accuracy=(mean([float(bool(ev[e].get("correct"))) for e in eids]),
                      mean([float(bool(base_ev[e].get("correct"))) for e in eids if e in base_ev])),
            no_program=sum(1 for e in eids if not ex[e].get("extracted_code"))))

    print(f"{'cell':34} {'n':>3} {'jdg':>4}  {'ratio':>11}  {'values':>11}  {'SLB chars/prob':>15}  {'tokens/prob':>13}  {'accuracy':>11}  noprog")
    print(f"{'':34} {'':>3} {'':>4}  {'new  base':>11}  {'new  base':>11}  {'new   base':>15}  {'new   base':>13}  {'new  base':>11}")
    for r in rows:
        f = lambda p, fmt: f"{fmt.format(p[0]):>5} {fmt.format(p[1]):>5}"
        print(f"{r['cell']:34} {r['problems']:>3} {r['judged']:>2}/{r['traces']:<2} {f(r['ratio'], '{:.2f}')}  {f(r['values'], '{:.2f}')}  "
              f"{f(r['values_chars_per_problem'], '{:.0f}'):>15}  {f(r['reasoning_tokens_per_problem'], '{:.0f}'):>13}  "
              f"{f(r['accuracy'], '{:.2f}')}  {r['no_program']}")
    json.dump(rows, open(root / "ontology/compare.json", "w"), indent=1)


if __name__ == "__main__":
    main()
