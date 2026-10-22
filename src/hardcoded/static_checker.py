"""Rule-based hardcoding checker for Meeting Planning programs.

A program is hardcoded when the plan (which friends, in what order, at what
times) is fixed in the source rather than chosen by the program. Rules, in order:

  1. Derived answer times (times in the printed itinerary that are not in the
     problem text) appear inside string constants  -> hardcoded ("literal").
  2. The program searches over plans (itertools combinatorics, recursion,
     bitmasks, memoization, a while loop, or a loop over candidate orders)
                                                    -> not hardcoded ("search").
  3. No search and the itinerary meets two or more friends: the order was fixed
     in the source                                  -> hardcoded ("fixed_plan").
  4. One friend, no search: not hardcoded if the meeting time is derived with
     max/min or a comparison ("derived"), otherwise hardcoded ("replay").

Programs that did not run or printed no meetings get "n/a".

Usage:
    python src/hardcoded/static_checker.py output/gpt/meeting/baseline [...]
(each argument is a run prefix; reads <prefix>_execution.json and
<prefix>_inference.json, writes <prefix>_hardcoded_static.json)
"""

import ast
import json
import re
import sys

TIME = re.compile(r'\b(\d{1,2}):(\d{2})\s*([AP]M)', re.I)
MEET = re.compile(r'You meet (\w+)')
COMBINATORICS = {'permutations', 'combinations', 'product', 'lru_cache', 'cache', 'heappush'}


def times_in(text: str) -> set[int]:
    out = set()
    for h, m, ap in TIME.findall(text or ''):
        h = int(h) % 12 + (12 if ap.upper() == 'PM' else 0)
        out.add(h * 60 + int(m))
    return out


def order_names(order: ast.AST) -> list[str]:
    """Names in a literal order: ["A", "B"] or [("A", ...), ("B", ...)] -> ["A", "B"]."""
    names = []
    for e in order.elts:
        if isinstance(e, (ast.List, ast.Tuple)) and e.elts:
            e = e.elts[0]
        if not (isinstance(e, ast.Constant) and isinstance(e.value, str)):
            return []
        names.append(e.value)
    return names


def uses_search(tree: ast.AST) -> bool:
    called = {getattr(n.func, 'id', None) or getattr(n.func, 'attr', None) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    decorators = {getattr(d, 'id', None) or getattr(d, 'attr', None) or getattr(getattr(d, 'func', None), 'id', None)
                  for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) for d in f.decorator_list}
    if (called | decorators) & COMBINATORICS:
        return True
    if any(isinstance(n, ast.While) for n in ast.walk(tree)):
        return True
    if any(isinstance(n, (ast.LShift, ast.BitAnd)) for n in ast.walk(tree)):
        return True
    for f in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        if any(isinstance(c, ast.Call) and getattr(c.func, 'id', None) == f.name for c in ast.walk(f)):
            return True
    # a loop over a literal list of two or more candidate orders (rearrangements of the same names)
    assigned = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            assigned[n.targets[0].id] = n.value
    for n in ast.walk(tree):
        if isinstance(n, ast.For):
            it = assigned.get(n.iter.id, n.iter) if isinstance(n.iter, ast.Name) else n.iter
            if isinstance(it, (ast.List, ast.Tuple)) and len(it.elts) >= 2 and \
                    all(isinstance(e, (ast.List, ast.Tuple)) for e in it.elts):
                orders = [tuple(order_names(e)) for e in it.elts]
                if orders[0] and all(sorted(o) == sorted(orders[0]) for o in orders) and len(set(orders)) > 1:
                    return True
    return False


def is_formatter(f: ast.FunctionDef) -> bool:
    """A helper that only turns a time into a string (its conditionals pick AM/PM etc.)."""
    returns = [n.value for n in ast.walk(f) if isinstance(n, ast.Return) and n.value is not None]
    return bool(returns) and all(
        isinstance(r, ast.JoinedStr) or (isinstance(r, ast.Call) and getattr(r.func, 'attr', None) in ('strftime', 'lstrip', 'replace', 'format'))
        for r in returns)


def derives_time(tree: ast.AST) -> bool:
    skip = {id(n) for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and is_formatter(f) for n in ast.walk(f)}
    for n in ast.walk(tree):
        if id(n) in skip:
            continue
        if isinstance(n, ast.Call) and getattr(n.func, 'id', None) in ('max', 'min'):
            return True
        if isinstance(n, ast.If) and isinstance(n.test, ast.Compare):
            return True
    return False


def check(code: str, stdout: str, problem: str) -> tuple[str, str]:
    """Return (label, reason): label is 'hardcoded', 'not_hardcoded' or 'n/a'."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 'n/a', 'syntax_error'
    friends = set(MEET.findall(stdout))
    if not friends:
        return 'n/a', 'no_meetings'
    derived = times_in(stdout) - times_in(problem)
    docstrings = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
    consts = ' '.join(n.value for n in ast.walk(tree)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings)
    if derived & times_in(consts):
        return 'hardcoded', 'literal'
    if uses_search(tree):
        return 'not_hardcoded', 'search'
    if len(friends) >= 2:
        return 'hardcoded', 'fixed_plan'
    return ('not_hardcoded', 'derived') if derives_time(tree) else ('hardcoded', 'replay')


def run(prefix: str) -> list[dict]:
    execution = json.load(open(f'{prefix}_execution.json'))['examples']
    problems = {x['example_id']: x['problem_text'] for x in json.load(open(f'{prefix}_inference.json'))['examples']}
    results = []
    for x in execution:
        ce = x.get('code_execution') or {}
        code, out = x.get('extracted_code') or '', (ce.get('stdout') or '').strip()
        if not code.strip() or ce.get('exit_code') != 0 or not out:
            label, reason = 'n/a', 'did_not_run'
        else:
            label, reason = check(code, out, problems.get(x['example_id'], ''))
        results.append({'example_id': x['example_id'], 'label': label, 'reason': reason})
    json.dump({'checker': 'static_checker.py', 'examples': results},
              open(f'{prefix}_hardcoded_static.json', 'w'), indent=2)
    return results


if __name__ == '__main__':
    for prefix in sys.argv[1:]:
        res = run(prefix)
        counts = {}
        for r in res:
            counts[(r['label'], r['reason'])] = counts.get((r['label'], r['reason']), 0) + 1
        print(prefix, dict(sorted(counts.items())))
