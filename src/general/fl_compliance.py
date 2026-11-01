"""Check that a program is written in the formal language the prompt asked for."""

import ast
import re
import sys

STDLIB = set(sys.stdlib_module_names)


def imported_modules(code: str) -> set:
    """Top-level module names a Python program imports."""
    tree = ast.parse(code)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            mods.add(node.module.split(".")[0])
    return mods


def fl_compliance(code: str, fl: str) -> dict:
    """
    Flag a program that does not use its formal language.

    python: compliant if it imports only standard-library modules.
    z3: compliant if it imports z3 and calls a solver's check().
    pddl: not checked (the planner validates the PDDL).
    A program that does not parse is not judged (compliant None).

    Returns:
        Dict with keys: compliant (bool or None), reason (str or None), non_stdlib (list)
    """
    if fl == "pddl" or not code or not code.strip():
        return {"compliant": None, "reason": "no code" if fl != "pddl" else None, "non_stdlib": []}
    try:
        ast.parse(code)
    except (SyntaxError, ValueError):
        # Usually prose captured as code; the FL cannot be judged
        return {"compliant": None, "reason": "not valid Python", "non_stdlib": []}
    mods = imported_modules(code)
    non_stdlib = sorted(m for m in mods if m not in STDLIB)
    if fl == "python":
        if non_stdlib:
            return {"compliant": False, "reason": "imports " + ", ".join(non_stdlib), "non_stdlib": non_stdlib}
        return {"compliant": True, "reason": None, "non_stdlib": []}
    if fl == "z3":
        if "z3" not in mods:
            return {"compliant": False, "reason": "no z3 import", "non_stdlib": non_stdlib}
        if not re.search(r"\.check\s*\(", code):
            return {"compliant": False, "reason": "z3 imported but no check()", "non_stdlib": non_stdlib}
        return {"compliant": True, "reason": None, "non_stdlib": non_stdlib}
    raise ValueError(f"unknown fl: {fl}")
