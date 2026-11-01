"""For completed searches: does the answer appear before the model starts drafting code?"""
import json, re, collections, random, sys
S = sys.argv[1] if len(sys.argv) > 1 else './'
rows = json.load(open(S + 'search_outcome.json'))  
CODE = re.compile(r'^\s*(def \w+\(|import \w|from \w+ import \w|s(olver)?\.add\()', re.M)
TIME = re.compile(r'(\d{1,2}):(\d{2})\s*([AP]\.?M\.?)?', re.I)

def exact(text):
    return {(int(h) % 12 + (12 if ap.upper().startswith('P') else 0)) * 60 + int(m) if ap else int(h) * 60 + int(m)
            for h, m, ap in TIME.findall(text or '')}

def answer_pos(task, r, sol, problem):
    if task == 'meeting':
        derived = set().union(*[exact(s) for s in sol]) - exact(problem)
        first = {}
        for mm in TIME.finditer(r):
            h, m, ap = mm.groups(); h, m = int(h), int(m)
            cands = {(h % 12 + (12 if ap.upper().startswith('P') else 0)) * 60 + m} if ap else {h * 60 + m, (h + 12) * 60 + m}
            for c in cands & derived:
                first.setdefault(c, mm.start())
        if len(first) < 0.8 * len(derived): return None
        return sorted(first.values())[int(0.8 * len(derived)) - 1] if derived else None
    if task == 'calendar':
        st, en = sol[1].lstrip('0'), sol[2].lstrip('0')
        mm = re.search(r'0?%s\s*(-|–|to|until)\s*0?%s\b' % (re.escape(st), re.escape(en)), r)
        return mm.start() if mm else None
    if task == 'zebralogic':
        pos = []
        for row in sol['rows']:
            cells = [c.strip().lower() for c in row[1:] if c.strip()]
            off = 0; found = None
            for line in r.splitlines(True):
                l = line.lower()
                if sum(1 for c in cells if re.search(r'\b%s\b' % re.escape(c), l)) >= len(cells) - 1:
                    found = off; break
                off += len(line)
            if found is not None: pos.append(found)
        return sorted(pos)[int(0.8 * len(sol['rows'])) - 1] if len(pos) >= 0.8 * len(sol['rows']) else None

cache = {}
def get(m, t, c, kind):
    k = (m, t, c, kind)
    if k not in cache:
        cache[k] = {x['example_id']: x for x in json.load(open(f'output/{m}/{t}/{c}_{kind}.json'))['examples']}
    return cache[k]

agg = collections.defaultdict(collections.Counter); samples = collections.defaultdict(list)
for r in rows:
    if r['rej'] < 3 or not r['done']: continue
    m, t, c, eid = r['model'], r['task'], r['cond'], r['id']
    tr = get(m, t, c, 'execution')[eid]['reasoning_before_code']
    sol = get(m, t, c, 'evaluation')[eid]['solution']; prob = get(m, t, c, 'inference')[eid]['problem_text']
    a = answer_pos(t, tr, sol, prob); cm = CODE.search(tr); cpos = cm.start() if cm else len(tr)
    key = (m, t)
    if a is None: agg[key]['unknown'] += 1
    elif a < cpos: agg[key]['before_code'] += 1; samples[(key, 'before')].append((c, eid, a, cpos, len(tr)))
    else: agg[key]['after_code'] += 1; samples[(key, 'after')].append((c, eid, a, cpos, len(tr)))
for k in sorted(agg): print(k, dict(agg[k]))
json.dump({f'{k[0][0]}|{k[0][1]}|{k[1]}': v for k, v in samples.items()}, open(S + 'answer_pos_samples.json', 'w'))
