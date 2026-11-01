#!/usr/bin/env python3
"""Per-problem rows for the deterrence runs (docs/DETERRENCE_DESIGN.md), in the format of
output/paper/ontology_traces_<tag>.json (scripts/paper_ontology_stats.py), so the Section 6 figure
can pair each with the baseline row of the same model, root, task and problem.

Roots: output_deter -> "native" (pairs with output/), output_deter_crossfl -> "crossfl" (pairs with
output_crossfl/). A labels: <root>/ontology/judge_a_<a-tag>.jsonl on <root>/ontology/a_items.json.

A batch group's trace covers its K members, so every member gets the group's ratio and "values",
and 1/K of its reasoning and solver-like tokens; "cluster" is the group (members share a trace, so
the bootstrap resamples groups). Other rows have their own problem as cluster.

Usage: python scripts/deter_traces.py   (writes output/paper/deter_traces_<a-tag>.json)
"""

import argparse
import collections
import json
from pathlib import Path

import tiktoken

REPO = Path(__file__).resolve().parent.parent
ROOTS = ["output_deter", "output_deter_crossfl"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a-tag", default="gemma_v11t")
    ap.add_argument("--roots", nargs="*", default=list(ROOTS), help="deterrence roots (a pilot root counts as native)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    enc = tiktoken.get_encoding("cl100k_base")
    ntok = lambda s: len(enc.encode(s, disallowed_special=()))
    rows = []
    for root in args.roots:
        root_name = "crossfl" if root.endswith("crossfl") else "native"
        items_path = REPO / root / "ontology/a_items.json"
        if not items_path.exists():
            print(f"{root}: no A items yet, skipped")
            continue
        labels = {}
        for jf in (REPO / root / "ontology").glob(f"judge_a_{args.a_tag}*.jsonl"):  # with shard files
            for line in open(jf):
                r = json.loads(line)
                labels[(r["id"], r.get("h"))] = r
        # trace -> [tokens, SLB tokens, chars, SLB chars, values, all judged]; the ratio is in characters, as in
        # the baseline labels
        tok = collections.defaultdict(lambda: [0, 0, 0, 0, False, True])
        for it in json.load(open(items_path)):
            r = labels.get((it["id"], it["h"]))
            acc = tok[it["trace"]]
            if r is None:
                acc[5] = False
                continue
            for i, text in enumerate(it["paragraphs"]):
                n = ntok(text)
                acc[0] += n
                acc[2] += len(text)
                if "V" in r["paras"].get(str(i), {"t": "N"})["t"]:
                    acc[1] += n
                    acc[3] += len(text)
                    acc[4] = True
        for ex_path in sorted((REPO / root).glob("*/*/*_execution.json")):
            model, task = ex_path.parts[-3], ex_path.parts[-2]
            cond = ex_path.name[: -len("_execution.json")]
            ex = json.load(open(ex_path))
            fl = ex["run_metadata"]["fl"]
            ev = {e["example_id"]: e for e in json.load(open(ex_path.with_name(f"{cond}_evaluation.json")))["examples"]}
            for e in ex["examples"]:
                eid = e["example_id"]
                unit, k = (e["batch"]["group_id"], e["batch"]["k"]) if "batch" in e else (eid, 1)
                t = tok.get(f"{model}/{task}/{cond}/{unit}")
                if t is not None and not t[5]:
                    continue  # trace not fully judged
                rt, st, rc, sc, values = t[:5] if t else (0, 0, 0, 0, False)  # no reasoning: no segments
                rows.append(dict(model=model, root=root_name, task=task, cond=cond, fl=fl, example_id=eid,
                                 cluster=f"{task}/{unit}", k=k, values=values, ratio=sc / rc if rc else None,
                                 correct=ev.get(eid, {}).get("correct") in (True, "True"),
                                 reasoning_tokens=rt / k, slb_tokens=st / k))
    out = Path(args.out) if args.out else REPO / f"output/paper/deter_traces_{args.a_tag}.json"
    json.dump(rows, open(out, "w"), indent=0)
    print("wrote", out, len(rows))
    print(collections.Counter((r["root"], r["model"], r["task"], r["fl"], r["cond"]) for r in rows))


if __name__ == "__main__":
    main()
