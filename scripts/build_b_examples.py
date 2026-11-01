#!/usr/bin/env python3
"""
B examples (tab "bex" in validation/reliability/judge_checks.json): a few traces per B label and
for the specification-change flag, so Harry can check the B ontology itself. Labels and evidence
come from the gemma_v1 full run; Claude picked items it read as clear cases, plus a few marked
as boundary cases, and adds a short note to each (2026-10-30).

Usage (vllm env, for tiktoken):
    python scripts/build_b_examples.py
"""
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REL = REPO / "validation/reliability"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from ontology_items import build_items
from build_check_sheets import trace_blocks, meta, B_OPTS, SPEC_OPTS

M, C, D, G = "meeting_planning_example", "calendar_scheduling_example", "deepseek", "gpt"
PICKS = [  # (trace, question key, Claude's note)
    (f"gpt/meeting/baseline/{M}_389", "b", "Clear: a list literal of the itinerary, printed."),
    (f"gpt/meeting/baseline/{M}_624", "b", "Boundary with partly fixed: it computes arrival times, but every decision (order, waits, durations) is fixed."),
    (f"gpt/meeting/baseline/{M}_144", "b", "Same pattern as the previous one: a fixed sequence of events with computed times."),
    ("gpt/zebralogic/caution_a/zebralogic_grid_lgp-test-2x4-5", "b", "Adds height[1] == very short, a deduction from clue 2, next to the clue's own encoding."),
    ("gpt/blocksworld/baseline/blocksworld_p74_goal_constraint14", "b", "The goal lists specific towers worked out in prose instead of the stated constraint."),
    (f"gpt/meeting/caution_a/{M}_385", "b", "Boundary with hardcoded: a fixed meeting order with hardcoded waits."),
    (f"deepseek/meeting/caution_b/{M}_728", "b", "The friends list is in the prose itinerary's order, so a first-found DFS returns it."),
    (f"qwen/calendar/baseline/{C}_429", "b", "Takes the latest feasible slot (candidates[-1]) to match the answer reached in prose."),
    (f"gpt/calendar/baseline/{C}_778", "b", "Boundary: the day order follows a stated preference (avoid Tuesday), which the problem itself justifies."),
    ("deepseek/zebralogic/caution_b/zebralogic_grid_lgp-test-2x6-9", "b", "Independent although the prose solved it fully (wasted prose solving)."),
    (f"qwen/calendar/caution_b/{C}_678", "b", "Independent although the prose solved it fully."),
    ("gpt/zebralogic/caution_b/zebralogic_grid_lgp-test-6x6-0", "b", "Independent with no solving in prose: a pure encoding."),
    (f"gpt/meeting/caution_b/{M}_629", "b", "Independent with no solving in prose: a pure encoding."),
    ("gpt/blocksworld/baseline/blocksworld_p66_goal_constraint6", "spec", "Goal changed to (holding block4) because the problem's extra constraint requires it."),
    ("qwen/blocksworld/caution_a/blocksworld_p70_goal_constraint10", "spec", "Replaces the stated goal with one built from the extra constraint; the problem does not require dropping the goal."),
]
B_NAMES = dict(B_OPTS)
SPEC_NAMES = dict(SPEC_OPTS)


def main():
    _, traces = build_items()
    tr = {t["id"]: t for t in traces}
    jb = {}
    for f in glob.glob(str(REPO / "output/ontology/judge_b_gemma_v1*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            jb[r["id"]] = r
    items = []
    for n, (tid, key, note) in enumerate(PICKS):
        t, r = tr[tid], jb[tid]
        lab = r[key]
        name = (B_NAMES if key == "b" else SPEC_NAMES)[lab]
        items.append({**meta(t), "id": f"bex-{n:02d}",
                      "gemma_text": f"Gemma: {name}. Evidence: {r['evidence']}  Claude: {note}",
                      "question": {"key": key, "type": "single",
                                   "prompt": "Do you agree with this label?" if key == "b" else "Do you agree with this specification-change flag?",
                                   "options": (B_OPTS if key == "b" else SPEC_OPTS) + [["unsure", "Can't tell"]], "gemma": lab},
                      "blocks": trace_blocks(t, output=key == "b")})
    sheets = json.load(open(REL / "judge_checks.json"))
    sheets["bex"] = items
    json.dump(sheets, open(REL / "judge_checks.json", "w"))
    print("bex", len(items))


if __name__ == "__main__":
    main()
