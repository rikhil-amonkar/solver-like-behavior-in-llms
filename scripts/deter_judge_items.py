#!/usr/bin/env python3
"""A-judge items (segments of numbered paragraphs) for deterrence runs, in the format of
src/ontology_items.py, written to <root>/ontology/a_items.json for
`run_ontology_judges.py a --items <root>/ontology/a_items.json`.

- batch_k<K>: one trace per group (members share it); the judge's problem is the K problems,
  as numbered in the prompt. Item ids "<model>/<task>/<cond>/<group_id>#<segment>".
- placeholder: one trace per problem; the problem is the placeholder text, preceded by a note
  that assigning placeholder values to decision variables counts as values (Harry, 2026-10-31).
  The judge prompt itself is unchanged.

Usage: python scripts/deter_judge_items.py --root output_deter_pilot
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ontology_items import paragraphs, text_hash, SEGMENT_TOKENS  # noqa: E402
from chunking.reasoning_splitter import split_reasoning_by_tokens  # noqa: E402
from deter.batching import strip_cue, PROBLEM_CUES  # noqa: E402

PLACEHOLDER_NOTE = ("[Note for the annotator: the model saw this problem with its values replaced by placeholders "
                    "(Person1, T3, L2, D1, ...); it never saw the real values. Assigning, testing or ruling out "
                    "placeholder values of decision variables (e.g. \"meet Person2 first, from T3\", \"the slot "
                    "T5-T7 on Day1 works\") counts as V, exactly as concrete values would.]\n\n")


def traces(root: Path):
    for path in sorted(root.glob("*/*/*_execution.json")):
        model, task = path.parts[-3], path.parts[-2]
        cond = path.name[: -len("_execution.json")]
        inf = {e["example_id"]: e for e in json.load(open(path.with_name(f"{cond}_inference.json")))["examples"]}
        seen = set()
        for e in json.load(open(path))["examples"]:
            if "batch" in e:
                gid = e["batch"]["group_id"]
                if gid in seen:
                    continue
                seen.add(gid)
                yield (f"{model}/{task}/{cond}/{gid}", e["reasoning_before_code"] or "",
                       group_problem(inf[gid], task), model, task, cond, gid)
            else:
                eid = e["example_id"]
                yield (f"{model}/{task}/{cond}/{eid}", e["reasoning_before_code"] or "",
                       PLACEHOLDER_NOTE + inf[eid]["problem_text"], model, task, cond, eid)


def group_problem(rec: dict, task: str) -> str:
    from general.io_utils import load_problems_json
    problems = load_problems_json(task)
    return "\n\n".join(f"### Problem {i}\n\n{strip_cue(problems[eid]['problem'].strip(), PROBLEM_CUES)}"
                       for i, eid in enumerate(rec["member_ids"], 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    root = REPO / ap.parse_args().root
    items = []
    for key, reasoning, problem, model, task, cond, eid in traces(root):
        segs = split_reasoning_by_tokens(reasoning, SEGMENT_TOKENS) if reasoning.strip() else []
        for j, seg in enumerate(segs):
            paras = paragraphs(seg)
            if paras:
                items.append(dict(id=f"{key}#{j}", h=text_hash(seg), trace=key, model=model, task=task, cond=cond,
                                  example_id=eid, segment_index=j, n_segments=len(segs),
                                  problem=problem, paragraphs=paras))
    out = root / "ontology" / "a_items.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(items, open(out, "w"), ensure_ascii=False)
    print(f"{len(items)} segments from {len({i['trace'] for i in items})} traces -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
