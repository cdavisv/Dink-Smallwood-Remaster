#!/usr/bin/env python3
"""Static softlock scan of the DinkC ASTs: paths on which a procedure leaves Dink frozen (freeze(1) not followed by
unfreeze(1) before return / kill_this_task / end of procedure), and load_screen / &player_map targets that are not screens.

Usage: python3 -I tools/parity_audit/dinkc_freeze_scan.py <out folder of dinkc_coverage.py> > freeze_paths.csv
"""
import csv, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AST = f'{ROOT}/tools/dinkc/out/ast'
cov = {r['script']: r for r in csv.DictReader(open(os.path.join(sys.argv[1], 'script_coverage.csv')))}

HANDOVER = {'load_screen', 'draw_screen', 'spawn', 'external', 'sp_script', 'load_game', 'restart_game', 'kill_game', 'script_attach'}
findings = []


def arg_int(a):
    return a['value'] if a and a.get('type') == 'int' else None


def body_of(n):
    if n is None:
        return []
    return n['body'] if n['type'] == 'block' else [n]


def explore(script, proc, stmts, i, frozen, freeze_line, seen, handover, out):
    """Walk statements from index i; returns at the procedure end."""
    while i < len(stmts):
        s = stmts[i]
        t = s['type']
        if t == 'call':
            n = s['name'].lower()
            a0 = arg_int(s['args'][0]) if s.get('args') else None
            if n == 'freeze' and a0 == 1:
                frozen, freeze_line = True, s['line']
            elif n == 'unfreeze' and a0 == 1:
                frozen = False
            elif n == 'kill_this_task':
                if frozen:
                    out.append((script, proc, freeze_line, s['line'], 'kill_this_task', tuple(sorted(handover))))
                return
            elif n in HANDOVER:
                handover = handover | {n}
        elif t == 'return':
            if frozen:
                out.append((script, proc, freeze_line, s['line'], 'return', tuple(sorted(handover))))
            return
        elif t == 'goto':
            if frozen:
                out.append((script, proc, freeze_line, s['line'], 'goto (not followed)', tuple(sorted(handover))))
            return
        elif t == 'if':
            key = (id(s), frozen)
            if key not in seen:
                seen.add(key)
                then_b = body_of(s['then'])
                else_b = body_of(s.get('else'))
                rest = stmts[i + 1:]
                explore(script, proc, then_b + rest, 0, frozen, freeze_line, seen, handover, out)
                explore(script, proc, else_b + rest, 0, frozen, freeze_line, seen, handover, out)
            return
        elif t == 'block':
            stmts = s['body'] + stmts[i + 1:]
            i = 0
            continue
        i += 1
    if frozen:
        out.append((script, proc, freeze_line, None, 'end of procedure', tuple(sorted(handover))))


for path in sorted(glob.glob(f'{AST}/*.json')):
    d = json.load(open(path))
    for p in d['procedures']:
        out = []
        explore(d['script'], p['name'], p['body'], 0, False, None, set(), frozenset(), out)
        for o in sorted(set(out), key=str):
            findings.append(o)

w = csv.writer(sys.stdout)
w.writerow(['script', 'procedure', 'freeze_line', 'exit_line', 'exit', 'handover_on_path', 'probe_runs_script', 'probe_runs_proc'])
for (s, p, fl, el, how, ho) in findings:
    c = cov.get(s, {})
    w.writerow([s, p, fl, el or '', how, ';'.join(ho), 'yes' if c.get('procs_run') else 'no',
                'yes' if p.lower() in (c.get('procs_run') or '').split(';') else 'no'])
