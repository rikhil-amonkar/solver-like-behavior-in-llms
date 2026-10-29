#!/usr/bin/env python3
"""
Properties check (tab "pcheck" in validation/reliability/judge_checks.json): paragraphs
Claude picked on 2026-10-29 as candidates for A1 = Properties under the strict definition
(a conclusion about the whole solution set, argued in the paragraph from the instance's data,
without committing values), so Harry can confirm or reject them and settle the definition.

Picked by reading Gemma's Properties labels (gemma_v7 on the round-3 pool, gemma_v1 on the
full run) and keyword hits; none of the traces is on an earlier sheet. Kinds:
- clean: bound, infeasibility or existence argued in the paragraph;
- boundary: the argument rules out values or subsets on the way (Values vs Properties).

Usage (vllm env, for tiktoken):
    python scripts/build_p_check.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
from ontology_items import build_items

PICKS = [  # (segment id, paragraph index, kind)
    ("deepseek/meeting/caution_b/meeting_planning_example_268#2", 5, "clean"),
    ("deepseek/meeting/caution_b/meeting_planning_example_937#24", 2, "clean"),
    ("deepseek/meeting/caution_a/meeting_planning_example_356#5", 4, "clean"),
    ("deepseek/meeting/baseline/meeting_planning_example_225#0", 18, "clean"),
    ("qwen/blocksworld/caution_b/blocksworld_p40_action_constraint24#7", 12, "clean"),
    ("qwen/blocksworld/caution_a/blocksworld_p06_state_constraint6#3", 3, "clean"),
    ("qwen/blocksworld/caution_b/blocksworld_p56_action_constraint40#2", 7, "clean"),
    ("deepseek/meeting/caution_b/meeting_planning_example_937#5", 11, "boundary"),
    ("gpt/zebralogic/baseline/zebralogic_grid_lgp-test-2x3-17#0", 23, "boundary"),
    ("qwen/zebralogic/caution_a/zebralogic_grid_lgp-test-4x5-34#1", 19, "boundary"),
]
OPTS = [["P", "Properties"], ["V", "Values"], ["N", "Not SLB"], ["unsure", "Can't tell"]]


def main():
    segments, _ = build_items()
    seg = {s["id"]: s for s in segments}
    items = []
    for n, (sid, i, kind) in enumerate(PICKS):
        s = seg[sid]
        items.append({**{k: s[k] for k in ("model", "task", "cond")}, "trace": s["trace"], "segment": sid, "para": i,
                      "kind": kind, "blind": True, "gemma_text": "", "id": f"pcheck-{n:02d}",
                      "question": {"key": "a1", "type": "single", "prompt": "Is the highlighted paragraph Properties?", "options": OPTS, "gemma": None},
                      "blocks": [{"label": "Problem", "text": s["problem"], "mode": "collapsed"},
                                 {"label": "", "text": s["paragraphs"][i - 1] if i else "", "mode": "context"},
                                 {"label": "Paragraph", "text": s["paragraphs"][i], "mode": "target"},
                                 {"label": "", "text": s["paragraphs"][i + 1] if i + 1 < len(s["paragraphs"]) else "", "mode": "context"}]})
    sheets = json.load(open(REL / "judge_checks.json"))
    sheets["pcheck"] = items
    json.dump(sheets, open(REL / "judge_checks.json", "w"))
    print("pcheck", len(items))


if __name__ == "__main__":
    main()
