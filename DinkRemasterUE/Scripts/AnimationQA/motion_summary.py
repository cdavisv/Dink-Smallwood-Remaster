"""One line per body and state from motion_report.py --json output: the numbers a reviewer compares before/after.
  python3 -I Scripts/AnimationQA/motion_summary.py report.json [other.json ...]
"""
import json, sys

def g(m, k, f='median'):
    v = m.get(k)
    return '-' if v is None else (v if not isinstance(v, dict) else v.get(f, '-'))

cols = ['n', 'slide med', 'slide p95', 'slide max', 'lowfoot>3', 'lowfoot<-2', 'yaw/fr max', 'yaw>15', 'knee min', 'knee max', 'kneeJump', 'bob', 'pelv yaw rng', 'chest-pelv rng', 'arm corr', 'head rng', 'COM-base', 'stance w', 'hand-trunk min', 'root max']
for path in sys.argv[1:]:
    d = json.load(open(path))
    for body, r in d.items():
        print(f'== {body}  planted {r["planted_height_cm"]}')
        print('  ' + 'state'.ljust(22) + ' '.join(c.rjust(9) for c in cols))
        for st, m in sorted(r['states'].items()):
            n = g(m, 'knee_flex_deg', 'n') if 'knee_flex_deg' in m else g(m, 'slide_cm_frame', 'n')
            fl = m.get('share_lower_foot_float_gt3cm', '-')
            bl = m.get('share_lower_foot_below_2cm', '-')
            def rng(k):
                v = m.get(k); return '-' if not v else round(v['p95'] - v['min'], 1)
            corr = [v for k, v in m.items() if k.startswith('arm_vs')]
            row = [n, g(m, 'slide_cm_frame'), g(m, 'slide_cm_frame', 'p95'), g(m, 'slide_cm_frame', 'max'), fl, bl, g(m, 'body_yaw_change_deg_frame', 'max'), m.get('frames_body_turn_gt15deg', '-'),
                   g(m, 'knee_flex_deg', 'min'), g(m, 'knee_flex_deg', 'max'), g(m, 'knee_change_deg_frame', 'max'), g(m, 'pelvis_bob_range_cm'),
                   rng('pelvis_yaw_deg'), rng('chest_vs_pelvis_yaw_deg'), round(sum(corr) / len(corr), 2) if corr else '-', rng('head_height_cm'),
                   g(m, 'com_over_base_cm'), g(m, 'stance_width_cm'), g(m, 'hand_trunk_cm', 'min'), g(m, 'root_off_cm', 'max')]
            print('  ' + st[:22].ljust(22) + ' '.join(str(x).rjust(9) for x in row))
        print('  pops:', ', '.join(f'{p["bone"]}@{p["frame"]}({p["state"]}) {p["cm"]}' for p in r['top_pops'][:6]))
