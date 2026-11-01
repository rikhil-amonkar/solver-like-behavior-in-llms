#!/usr/bin/env python3
"""
Test that the final answer's program is extracted, not a draft from the thinking.

Run: python tests/execution/test_code_extraction.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from execution.code_extractor import split_reasoning_and_code

# A real-looking Meeting program: `wait` is a variable, not leaked reasoning
FINAL = ('import itertools\n\n'
         'def plan(order, t=540):\n'
         '    steps = []\n'
         '    for f in order:\n'
         '        wait = max(0, f["start"] - t)\n'
         '        wait += 0\n'
         '        t += wait\n'
         '        steps.append(f["name"])\n'
         '    return steps\n\n'
         'print(plan([{"name": "A", "start": 600}]))')


def trace_with_draft(final):
    return ("Draft:\n```python\nimport itertools\n...\n```\nLooks fine.</think>\n\n"
            "SOLUTION:\n```python\n" + final + "\n```")


def test_variable_named_wait_is_kept():
    _, code = split_reasoning_and_code(trace_with_draft(FINAL))
    assert code == FINAL, code


def test_leaked_reasoning_is_still_rejected():
    leaked = FINAL.replace("    return steps", "    wait I think this is wrong\n    return steps")
    _, code = split_reasoning_and_code(trace_with_draft(leaked))
    assert code != leaked, "a line of prose starting with 'wait' should still reject the block"


def test_no_answer_marker_falls_back():
    _, code = split_reasoning_and_code("Here is the program:\n```python\n" + FINAL + "\n```")
    assert code == FINAL, code


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
