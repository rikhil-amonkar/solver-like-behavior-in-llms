"""Among traces that search in prose, does the search reach the final answer?

search-heavy : >= 3 lines that reject a concrete candidate (a time or a house
               assignment next to a rejection word)
completed    : the program's printed answer already appears in the reasoning
  meeting    : >= 80% of derived itinerary times (not in the problem) appear in the reasoning
  calendar   : the answer's start-end pair appears in the reasoning more often than in the problem
  zebralogic : >= 80% of houses have all but at most one attribute value within one line
"""
import json, glob, re, sys, collections

REJECT = re.compile(r"\b(fail|fails|failed|impossible|infeasible|not feasible|too late|contradiction|"
                    r"conflict|doesn'?t work|does not work|not enough|insufficient|violat\w*|discard|no good|"
                    r"can'?t|cannot|not possible)\b", re.I)
TIME = re.compile(r'(\d{1,2}):(\d{2})\s*([AP]\.?M\.?)?', re.I)
ZEBRA_CAND = re.compile(r'(\b[A-Za-z]+\s*=\s*\d|\bhouse\s*\d|\bH\d\b|\bpos\w*\s*\d)', re.I)


def minutes(h, m, ap):
    h, m = int(h), int(m)
    if ap:
        h = h % 12 + (12 if ap.upper().startswith('P') else 0)
        return {h * 60 + m}
    return {h * 60 + m, (h + 12) * 60 + m} if h < 12 else {h * 60 + m}


def times(text):
    out = set()
    for g in TIME.findall(text or ''):
        out |= minutes(*g)
    return out


def exact_times(text):  # times with AM/PM resolved, for the answer side
    return {(int(h) % 12 + (12 if ap.upper().startswith('P') else 0)) * 60 + int(m) if ap else int(h) * 60 + int(m)
            for h, m, ap in TIME.findall(text or '')}


def rejections(task, reasoning):
    n = 0
    for line in re.split(r'[\n.;]', reasoning):
        if not REJECT.search(line):
            continue
        if task == 'zebralogic' and ZEBRA_CAND.search(line):
            n += 1
        elif task != 'zebralogic' and TIME.search(line):
            n += 1
    return n


def completed(task, reasoning, sol, problem):
    if task == 'meeting':
        derived = set()
        for s in sol:
            derived |= exact_times(s)
        derived -= exact_times(problem)
        if not derived:
            return None
        rt = times(reasoning)
        return sum(t in rt for t in derived) / len(derived) >= 0.8
    if task == 'calendar':
        st, en = sol[1].lstrip('0'), sol[2].lstrip('0')
        pair = re.compile(r'0?%s\s*(-|–|to|until)\s*0?%s\b' % (re.escape(st), re.escape(en)))
        return len(pair.findall(reasoning)) > len(pair.findall(problem))
    if task == 'zebralogic':
        rows = sol.get('rows') or []
        lines = [l.lower() for l in reasoning.splitlines()]
        ok = 0
        for r in rows:
            cells = [c.strip().lower() for c in r[1:] if c.strip()]
            if any(sum(1 for c in cells if re.search(r'\b%s\b' % re.escape(c), l)) >= len(cells) - 1 for l in lines):
                ok += 1
        return ok / len(rows) >= 0.8 if rows else None


def load(path):
    try:
        return {x['example_id']: x for x in json.load(open(path))['examples']}
    except FileNotFoundError:
        return {}


rows = []
for f in sorted(glob.glob('output/*/*/*_execution.json')):
    model, task, fn = f.split('/')[-3:]
    if task not in ('meeting', 'calendar', 'zebralogic'):
        continue
    cond = fn.replace('_execution.json', '')
    base = f[:-len('_execution.json')]
    ev, inf = load(base + '_evaluation.json'), load(base + '_inference.json')
    for eid, x in load(f).items():
        r = x.get('reasoning_before_code') or ''
        sol = ev.get(eid, {}).get('solution')
        rej = rejections(task, r)
        done = completed(task, r, sol, inf.get(eid, {}).get('problem_text', '')) if sol else None
        rows.append(dict(model=model, task=task, cond=cond, id=eid, rej=rej, done=done,
                         correct=ev.get(eid, {}).get('correct'), chars=len(r)))

json.dump(rows, open(sys.argv[1], 'w'))
print('model task cond | search-heavy | completed | half-baked | no answer parsed')
agg = collections.defaultdict(collections.Counter)
for r in rows:
    k = (r['model'], r['task'], r['cond'])
    agg[k]['n'] += 1
    if r['rej'] >= 3:
        agg[k]['search'] += 1
        agg[k]['done' if r['done'] else ('none' if r['done'] is None else 'half')] += 1
        if r['done'] and r['correct']: agg[k]['done_correct'] += 1
        if r['done'] is False and r['correct']: agg[k]['half_correct'] += 1
for k in sorted(agg):
    a = agg[k]
    print(*k, '|', f"{a['search']}/{a['n']}", '|', a['done'], f"(correct {a['done_correct']})", '|', a['half'],
          f"(correct {a['half_correct']})", '|', a['none'])
