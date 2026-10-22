"""Health checks on stored reasoning chains (inference files)."""
import json, glob, re, collections, sys

def gen_tokens(mm):
    return mm.get('generated_tokens') or mm.get('completion_tokens') or 0

def repetition(trace):
    lines = [l.strip() for l in trace.splitlines()[-300:] if l.strip()]
    if len(lines) < 50: return 0.0
    c = collections.Counter(lines)
    return sum(v for v in c.values() if v >= 5) / len(lines)

def tail_loop(trace, w=200):
    t = trace[-4000:]
    if len(t) < 4000: return False
    chunk = t[-w:]
    return t.count(chunk[:80]) >= 8

rows = []
ids = collections.defaultdict(dict)
for f in sorted(glob.glob('output/*/*/*_inference.json')):
    model, task, fn = f.split('/')[-3:]
    cond = fn.replace('_inference.json', '')
    d = json.load(open(f))
    ids[(task)][(model, cond)] = [e['example_id'] for e in d['examples']]
    ex = {x['example_id']: x for x in json.load(open(f.replace('_inference', '_execution')))['examples']}
    for e in d['examples']:
        t = e.get('reasoning_trace') or ''
        mm = e.get('model_metadata') or {}
        g = gen_tokens(mm); mx = mm.get('max_tokens') or 0
        fences = t.count('```')
        r = dict(model=model, task=task, cond=cond, id=e['example_id'], chars=len(t), gen=g, max=mx,
                 empty=not t.strip(), at_limit=bool(mx and g >= 0.98 * mx),
                 no_code_block=fences < 2, odd_fences=fences % 2 == 1,
                 gpt_no_final=(model == 'gpt' and 'assistantfinal' not in t),
                 error=bool(e.get('error')), rep=repetition(t), loop=tail_loop(t),
                 prompt_len=mm.get('prompt_length') or mm.get('prompt_tokens'),
                 engine=mm.get('inference_engine'),
                 exec_no_code=not (ex.get(e['example_id'], {}).get('extracted_code') or '').strip())
        rows.append(r)

json.dump(rows, open(sys.argv[1], 'w'))
flags = ['empty', 'at_limit', 'no_code_block', 'odd_fences', 'gpt_no_final', 'error', 'loop', 'exec_no_code']
print('file', *flags, 'rep>0.5', 'median_gen', 'max_gen', sep=' | ')
for k in sorted({(r['model'], r['task'], r['cond']) for r in rows}):
    rs = [r for r in rows if (r['model'], r['task'], r['cond']) == k]
    gens = sorted(r['gen'] for r in rs)
    print('/'.join(k), *[sum(r[f] for r in rs) for f in flags], sum(r['rep'] > 0.5 for r in rs), gens[len(gens)//2], gens[-1], sep=' | ')

print('\n== same problem ids across models and conditions? ==')
for task, d in ids.items():
    sets = {k: tuple(sorted(v)) for k, v in d.items()}
    ref = next(iter(sets.values()))
    print(task, 'all identical' if all(s == ref for s in sets.values()) else
          {k: len(set(v) ^ set(ref)) for k, v in sets.items()}, '| dup ids:', {k: len(v) - len(set(v)) for k, v in d.items() if len(v) != len(set(v))})
