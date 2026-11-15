"""Scripts the probe does not run in full, with their commands whose remaster semantics differ from dink.cpp (dinkc_commands.py).

Usage: python3 -I tools/parity_audit/dinkc_not_covered.py <out folder holding script_coverage.csv and freeze_paths.csv> > table.md
"""
import csv, collections, importlib.util, os, sys
spec = importlib.util.spec_from_file_location('v', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dinkc_commands.py'))
src = open(spec.origin).read().split("rows = list(")[0]
ns = {'__file__': spec.origin}; exec(src, ns); V = ns['V']
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cov = list(csv.DictReader(open(os.path.join(sys.argv[1], 'script_coverage.csv'))))
calls = collections.defaultdict(lambda: collections.Counter())
for r in csv.DictReader(open(f'{ROOT}/tools/dinkc/out/calls.csv')):
    calls[r['script']][r['name']] += 1
NOTE = {'F', 'D', 'd'}
SKIP = {'editor_type', 'fade_down', 'fade_up', 'say_stop', 'say_stop_npc', 'say_stop_xy', 'say_xy', 'wait'}
GAME_R = {'sp_nocontrol', 'sp_base_death', 'show_bmp', 'sp_disabled', 'sp_kill_wait'}
fz = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(sys.argv[1], 'freeze_paths.csv'))):
    fz[r['script']].append(r)
out = []
for r in cov:
    if r['procs_run'] and not r['procs_not_run']: continue
    s = r['script']
    notable = sorted(n for n in calls[s] if n in V and n not in SKIP and (V[n][0] in NOTE or n in GAME_R))
    status = 'never run' if not r['procs_run'] else 'partly: not ' + r['procs_not_run'].replace(';', ', ')
    flags = []
    for f in fz.get(s, []):
        if f['exit'] != 'goto (not followed)':
            flags.append(f"freeze l{f['freeze_line']} -> {f['exit']} {f['exit_line']}".strip())
    opn = [n for n in notable if V[n][0] != 'F']; fx = [n for n in notable if V[n][0] == 'F']
    txt = '; '.join(x for x in ((('open: ' + ', '.join(opn)) if opn else ''), (('fixed: ' + ', '.join(fx)) if fx else '')) if x)
    out.append((s, r['kind'], (r['screens'] or r['called_by']).replace(';', ' '), status, txt, '; '.join(sorted(set(flags)))))
print('| script | kind | screens / called by | probe | commands with a divergence | freeze paths |')
print('|---|---|---|---|---|---|')
for o in out:
    print('| ' + ' | '.join(x.replace('|', '/') for x in o) + ' |')
print(len(out), file=sys.stderr)
