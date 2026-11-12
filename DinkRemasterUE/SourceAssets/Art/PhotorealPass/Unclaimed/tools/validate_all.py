"""Run tools/blender/dinkasset/validate.py on every asset .blend under Unclaimed and write validation_summary.json.

    python3 -I tools/validate_all.py        (one Blender at a time, behind the same lock as tools/bl.sh)
"""
import glob, json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); UNC = os.path.dirname(HERE); REPO = os.path.abspath(os.path.join(UNC, '..', '..', '..', '..', '..'))
VAL = os.path.join(REPO, 'tools', 'blender', 'dinkasset', 'validate.py'); tmp = os.environ.get('TMPDIR', '/tmp'); out = {}
env = dict(os.environ, HOME=os.path.join(tmp, 'dink_unclaimed_home'))
for b in sorted(glob.glob(os.path.join(UNC, '*', '*', 'S[MK]_*.blend'))):
    r = subprocess.run(['flock', os.path.join(tmp, 'dink_unclaimed_blender.lock'), 'blender', '-b', '--factory-startup', '-t', '4', '-P', VAL, '--', '--blend', b], capture_output=True, text=True, env=env)
    t = r.stdout; key = os.path.relpath(b, UNC)
    if '@@DINK_REPORT_BEGIN@@' not in t:
        out[key] = {'error': 'no report'}; continue
    rep = json.loads(t.split('@@DINK_REPORT_BEGIN@@')[1].split('@@DINK_REPORT_END@@')[0])
    for a in rep.get('assets', []):
        fs = a.get('findings', [])
        out[key] = {'asset': a.get('name'), 'class': a.get('class'), 'passed': not any(f['severity'] == 'error' for f in fs),
                    'errors': sorted({f['code'] for f in fs if f['severity'] == 'error'}), 'warnings': sorted({f['code'] for f in fs if f['severity'] == 'warning'}),
                    'error_messages': [f['message'][:200] for f in fs if f['severity'] == 'error']}
    print(key, out.get(key, {}).get('errors'))
json.dump(out, open(os.path.join(UNC, 'validation_summary.json'), 'w'), indent=1)
print(sum(1 for v in out.values() if v.get('passed')), 'of', len(out), 'pass')
