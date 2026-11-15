#!/usr/bin/env python3
"""Probe coverage of the DinkC scripts: which scripts / procedures / command lines the probe traces execute.

Usage: python3 -I tools/parity_audit/dinkc_coverage.py <trace folder> <out folder>  (writes <out>/script_coverage.csv)
Needs tools/dinkc/out and tools/dinkink/out (their build commands). DINKC_PARITY.md, 15 Nov 2026.
"""
import csv, collections, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACES = sys.argv[1]  # folder with probe_ch*_trace.txt and stonebrook_probe_trace.txt (Saved/Narrative of a probe run)
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

entry = {}
for r in csv.DictReader(open(f'{ROOT}/tools/dinkink/out/names.csv')):
    if r['kind'] == 'entry':
        entry[r['ink']] = tuple(r['original'].split(':', 1))
kinds = {r['script']: r for r in csv.DictReader(open(f'{ROOT}/tools/dinkc/out/script_kinds.csv'))}

NOOP = {'preload_seq', 'debug', 'load_sound', 'make_global_int'}
calls = collections.defaultdict(set)      # (script, proc) -> command lines
for r in csv.DictReader(open(f'{ROOT}/tools/dinkc/out/calls.csv')):
    if r['engine_executes'] == '1' and r['kind'] == 'builtin' and r['name'] not in NOOP:
        calls[(r['script'], r['procedure'].lower())].add(int(r['line']))

start_re = re.compile(r' start (d_[\w]+\.on_\w+) sprite=(-?\d+) instance=(\d+)')
cmd_re = re.compile(r'^[\d.]+ (\d+) cmd (\S+).* src=(\d+)')
procs_run = collections.Counter()
lines_hit = collections.defaultdict(set)
chapters = collections.defaultdict(set)
for path in sorted(glob.glob(f'{TRACES}/*trace*.txt')):
    ch = os.path.basename(path).replace('_trace.txt', '')
    inst = {}
    cur = {}
    for line in open(path, errors='replace'):
        m = start_re.search(line)
        if m:
            sp = entry.get(m.group(1))
            if sp:
                inst[int(m.group(3))] = sp
                procs_run[sp] += 1
                chapters[sp[0]].add(ch)
            continue
        m = cmd_re.match(line)
        if m:
            sp = inst.get(int(m.group(1)))
            if sp:
                lines_hit[sp[0]].add(int(m.group(3)))

scripts = sorted({s for s, _ in entry.values()})
rows = []
for s in scripts:
    procs = sorted({p for (ss, p) in entry.values() if ss == s})
    ran = [p for p in procs if procs_run[(s, p)]]
    total = set().union(*[calls.get((s, p), set()) for p in procs]) if procs else set()
    hit = lines_hit[s] & total
    k = kinds.get(s, {})
    rows.append({'script': s, 'kind': k.get('kind', ''), 'placed_count': k.get('placed_count', ''),
                 'screens': k.get('screens', ''), 'called_by': k.get('called_by', ''),
                 'procedures': ';'.join(procs), 'procs_run': ';'.join(ran),
                 'procs_not_run': ';'.join(p for p in procs if p not in ran),
                 'cmd_lines': len(total), 'cmd_lines_hit': len(hit),
                 'chapters': ';'.join(sorted(chapters[s]))})
with open(f'{OUT}/script_coverage.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
never = [r for r in rows if not r['procs_run']]
partial = [r for r in rows if r['procs_run'] and r['procs_not_run']]
print(f'scripts with an entry point: {len(rows)}; run by the probe: {len(rows) - len(never)}; never run: {len(never)}; partly run: {len(partial)}')
tot = sum(r['cmd_lines'] for r in rows); hit = sum(r['cmd_lines_hit'] for r in rows)
print(f'director command lines: {tot}; executed by the probe: {hit} ({100.0 * hit / max(1, tot):.1f}%)')
print('never run by kind:', collections.Counter(r['kind'] for r in never).most_common())
