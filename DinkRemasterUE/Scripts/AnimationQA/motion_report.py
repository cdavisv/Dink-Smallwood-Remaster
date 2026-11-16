"""Physical-correctness numbers from a dink.Motion.Trace CSV (one row per frame, body and bone, world space).

  python3 -I Scripts/AnimationQA/motion_report.py <trace.csv> [more.csv ...] [--json out.json]

Per body (hero, NPC, creature) and per state (idle, slow, walk, fast, run, airborne, action:<clip>):
  foot slide   horizontal travel of a planted foot per frame (planted: the foot bone within 2.5 cm of its lowest
               height above the visible ground on two consecutive frames), median / p95 / max, cm per frame and cm/s
  contact      height of the planted foot over the visible ground (negative: through it), and the share of frames
               the lower foot is more than 3 cm above or 2 cm below where it stood on flat ground
  knee         flexion (0 straight, + bent forward); any negative value is a hyperextended knee; max change per frame
  elbow        flexion range; hip flexion and abduction ranges
  pelvis       vertical bob range per gait cycle, lateral sway, yaw and tilt ranges against the body's facing
  trunk        chest-against-pelvis counter-rotation, trunk lean, head pitch range and head height steadiness
  arms         correlation of each hand's forward swing with the opposite foot (+1 = arm swings with the opposite leg)
  support      standing: distance of the pelvis from the middle of the feet (centre of mass over the base)
  root         root bone against the mesh component (the clip's travel must never move the body off the capsule)
  hands        frames a hand is inside the trunk (closer than 9 cm to the spine line)
  pops         the largest frame-to-frame jumps of any traced joint position after the motion of the body is taken out
"""
import csv
import json
import math
import sys
from collections import defaultdict

import numpy as np


def load(path):
    frames = defaultdict(lambda: defaultdict(dict))  # body -> frame -> bone -> row
    meta = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            b = r['body']
            meta[b] = r['kind']
            frames[b][int(r['frame'])][r['bone']] = r
    return frames, meta


def v(r):
    return np.array([float(r['x']), float(r['y']), float(r['z'])])


def quat_rot(q, p):
    x, y, z, w = q
    u = np.array([x, y, z])
    return 2 * np.dot(u, p) * u + (w * w - np.dot(u, u)) * p + 2 * w * np.cross(u, p)


def comp_axes(r):
    q = (float(r['qx']), float(r['qy']), float(r['qz']), float(r['qw']))
    fwd = quat_rot(q, np.array([0., 1., 0.]))   # the mesh faces +Y
    left = quat_rot(q, np.array([1., 0., 0.]))  # +X is the character's left
    up = quat_rot(q, np.array([0., 0., 1.]))
    return fwd, left, up


def ang(a, b):
    c = np.dot(a, b) / max(1e-9, np.linalg.norm(a) * np.linalg.norm(b))
    return math.degrees(math.acos(max(-1., min(1., c))))


def yaw_of(vec):
    return math.degrees(math.atan2(vec[1], vec[0]))


def wrap(d):
    return (d + 180.) % 360. - 180.


def stats(a):
    a = np.asarray([x for x in a if np.isfinite(x)])
    if a.size == 0:
        return None
    return {'n': int(a.size), 'min': round(float(a.min()), 2), 'median': round(float(np.median(a)), 2), 'mean': round(float(a.mean()), 2),
            'p95': round(float(np.percentile(a, 95)), 2), 'max': round(float(a.max()), 2)}


def state_of(fr):
    an = fr.get('_anim')
    ac = fr.get('_actor')
    if an and an['ground_what'] not in ('None', '-', '') and float(an['qy']) > 0.5:
        return 'action:' + an['ground_what']
    spd = float(an['x']) if an else (math.hypot(float(ac['qx']), float(ac['qy'])) if ac else 0.)
    if ac and abs(float(ac['qz'])) > 30:
        return 'airborne'
    if spd < 5: return 'idle'
    if spd < 120: return 'slow'
    if spd < 250: return 'walk'
    if spd < 450: return 'fast'
    return 'run'


def analyse(frames, kind):
    keys = sorted(frames)
    if len(keys) < 3:
        return None
    human = any('thigh_l' in frames[k] for k in keys[:3])
    feet = [b for b in (['foot_l', 'foot_r'] if human else sorted({n for k in keys[:3] for n in frames[k] if frames[k][n]['ground_z'] not in ('nan', '') and not n.startswith('_')}))]
    out = {'frames': len(keys), 'states': defaultdict(lambda: defaultdict(list))}
    S = out['states']
    # Lowest height of each foot over the ground (its flat-ground planted height).
    h0 = {}
    for b in feet:
        hs = [float(frames[k][b]['z']) - float(frames[k][b]['ground_z']) for k in keys if b in frames[k] and frames[k][b]['ground_z'] not in ('nan', '')]
        h0[b] = float(np.percentile(hs, 2)) if hs else 0.
    out['planted_height_cm'] = {b: round(h, 2) for b, h in h0.items()}
    prev = None
    knee_prev = {}
    pops = []
    cyc_pelvis = defaultdict(list)
    for k in keys:
        fr = frames[k]
        if '_comp' not in fr:
            continue
        st = state_of(fr)
        fwd, left, up = comp_axes(fr['_comp'])
        dt = float(fr['_comp']['dt'])
        C = v(fr['_comp'])
        Sx = S[st]
        # A warp (dink.Goto, a door) is not motion: skip the frame pair.
        if prev is not None and '_comp' in prev and np.linalg.norm(C - v(prev['_comp'])) > 60.:
            prev = None
        if prev is not None and '_comp' in prev:
            pf, _, _ = comp_axes(prev['_comp'])
            Sx['body_yaw_change_deg_frame'].append(abs(wrap(yaw_of(fwd) - yaw_of(pf))))
        # Ground contact of the lower foot (the one that carries the body): above (floating) or below (through) the ground.
        lows = [float(fr[b]['z']) - float(fr[b]['ground_z']) - h0[b] for b in feet if b in fr and fr[b]['ground_z'] not in ('nan', '')]
        if lows and st not in ('airborne',) and not st.startswith('action:Jump'):
            Sx['lower_foot_cm'].append(min(lows))
        if 'root' in fr:
            Sx['root_off_cm'].append(float(np.linalg.norm(v(fr['root']) - C)))
        for b in feet:
            if b not in fr or fr[b]['ground_z'] in ('nan', ''):
                continue
            h = float(fr[b]['z']) - float(fr[b]['ground_z'])
            Sx['contact_' + b].append(h - h0[b])
            if prev is not None and b in prev and prev[b]['ground_z'] not in ('nan', ''):
                hp = float(prev[b]['z']) - float(prev[b]['ground_z'])
                if h - h0[b] < 2.5 and hp - h0[b] < 2.5:
                    d = v(fr[b])[:2] - v(prev[b])[:2]
                    Sx['slide_cm_frame'].append(float(np.linalg.norm(d)))
                    if dt > 0: Sx['slide_cm_s'].append(float(np.linalg.norm(d)) / dt)
        if human and all(n in fr for n in ('thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r', 'pelvis')):
            for s in 'lr':
                T, K, F = v(fr['thigh_' + s]), v(fr['calf_' + s]), v(fr['foot_' + s])
                flex = 180. - ang(T - K, F - K)
                # Sign: the knee must sit in front of the hip-ankle line (forward of the body).
                line = F - T
                t = np.dot(K - T, line) / max(1e-9, np.dot(line, line))
                off = K - (T + t * line)
                sign = 1. if np.dot(off, fwd) >= -0.3 else -1.
                kf = sign * flex
                Sx['knee_flex_deg'].append(kf)
                if s in knee_prev:
                    Sx['knee_change_deg_frame'].append(abs(kf - knee_prev[s]))
                knee_prev[s] = kf
                th = K - T
                Sx['hip_flex_deg'].append(math.degrees(math.atan2(np.dot(th, fwd), -np.dot(th, up))))
                Sx['hip_abd_deg'].append(math.degrees(math.atan2(np.dot(th, left) * (1 if s == 'l' else -1), -np.dot(th, up))))
                if all(n in fr for n in ('upperarm_' + s, 'lowerarm_' + s, 'hand_' + s)):
                    U, E, H = v(fr['upperarm_' + s]), v(fr['lowerarm_' + s]), v(fr['hand_' + s])
                    Sx['elbow_flex_deg'].append(180. - ang(U - E, H - E))
            P = v(fr['pelvis'])
            hipv = v(fr['thigh_l']) - v(fr['thigh_r'])
            pel_yaw = wrap(yaw_of(hipv) - yaw_of(left))
            Sx['pelvis_yaw_deg'].append(pel_yaw)
            Sx['pelvis_tilt_deg'].append(math.degrees(math.atan2(np.dot(hipv, up), np.linalg.norm(hipv))))
            Sx['pelvis_lateral_cm'].append(float(np.dot(P - C, left)))
            Sx['pelvis_height_cm'].append(float(np.dot(P - C, up)))
            cyc_pelvis[st].append((k, float(np.dot(P - C, up))))
            if 'upperarm_l' in fr and 'upperarm_r' in fr:
                sh = v(fr['upperarm_l']) - v(fr['upperarm_r'])
                Sx['chest_vs_pelvis_yaw_deg'].append(wrap(yaw_of(sh) - yaw_of(hipv)))
            if 'neck_01' in fr:
                tr = v(fr['neck_01']) - P
                Sx['trunk_lean_fwd_deg'].append(math.degrees(math.atan2(np.dot(tr, fwd), np.dot(tr, up))))
                Sx['trunk_lean_side_deg'].append(math.degrees(math.atan2(np.dot(tr, left), np.dot(tr, up))))
            if 'head' in fr:
                Sx['head_height_cm'].append(float(np.dot(v(fr['head']) - C, up)))
                if 'neck_01' in fr:
                    hv = v(fr['head']) - v(fr['neck_01'])
                    Sx['neck_pitch_deg'].append(math.degrees(math.atan2(np.dot(hv, fwd), np.dot(hv, up))))
            for s, o in (('l', 'r'), ('r', 'l')):
                if 'hand_' + s in fr:
                    Sx['hand_fwd_' + s].append(float(np.dot(v(fr['hand_' + s]) - P, fwd)))
                    Sx['foot_fwd_' + o].append(float(np.dot(v(fr['foot_' + o]) - P, fwd)))
                    # Hand inside the trunk: distance to the pelvis-neck segment.
                    if 'neck_01' in fr:
                        A, B, Hh = P, v(fr['neck_01']), v(fr['hand_' + s])
                        t = np.clip(np.dot(Hh - A, B - A) / max(1e-9, np.dot(B - A, B - A)), 0, 1)
                        d = float(np.linalg.norm(Hh - (A + t * (B - A))))
                        Sx['hand_trunk_cm'].append(d)
            if st == 'idle':
                mid = (v(fr['foot_l']) + v(fr['foot_r'])) / 2
                Sx['com_over_base_cm'].append(float(np.linalg.norm((P - mid)[:2])))
                Sx['stance_width_cm'].append(float(abs(np.dot(v(fr['foot_l']) - v(fr['foot_r']), left))))
        # Pops: the largest jump of a joint in the body's own frame (the body's travel taken out).
        if prev is not None and '_comp' in prev:
            Cp = v(prev['_comp'])
            for n, r in fr.items():
                if n.startswith('_') or n not in prev:
                    continue
                d = (v(r) - C) - (v(prev[n]) - Cp)
                pops.append((float(np.linalg.norm(d)), k, n, st))
        prev = fr
    # Pelvis bob per gait cycle: range in 0.5 s windows of steady states.
    for st, seq in cyc_pelvis.items():
        if len(seq) > 30:
            z = np.array([x[1] for x in seq])
            w = 30
            S[st]['pelvis_bob_range_cm'] = [float(z[i:i + w].max() - z[i:i + w].min()) for i in range(0, len(z) - w, w)]
    res = {'frames': out['frames'], 'planted_height_cm': out['planted_height_cm'], 'states': {}}
    for st, m in S.items():
        r = {}
        for key, arr in m.items():
            if key.startswith('hand_fwd_') or key.startswith('foot_fwd_'):
                continue
            s = stats(arr)
            if s: r[key] = s
        for s, o in (('l', 'r'), ('r', 'l')):
            a, b = m.get('hand_fwd_' + s), m.get('foot_fwd_' + o)
            if a and b and len(a) > 20 and np.std(a) > 0.5 and np.std(b) > 0.5:
                r['arm_vs_opposite_leg_corr_' + s] = round(float(np.corrcoef(a, b)[0, 1]), 2)
        c = m.get('lower_foot_cm')
        if c:
            c = np.array(c)
            r['share_lower_foot_float_gt3cm'] = round(float(np.mean(c > 3.)), 3)
            r['share_lower_foot_below_2cm'] = round(float(np.mean(c < -2.)), 3)
        y = m.get('body_yaw_change_deg_frame')
        if y:
            r['frames_body_turn_gt15deg'] = int(np.sum(np.array(y) > 15.))
        res['states'][st] = r
    pops.sort(reverse=True)
    res['top_pops'] = [{'cm': round(p[0], 2), 'frame': p[1], 'bone': p[2], 'state': p[3]} for p in pops[:12]]
    return res


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    if js in args: args.remove(js)
    allres = {}
    for path in args:
        frames, meta = load(path)
        for body, fr in frames.items():
            r = analyse(fr, meta[body])
            if r:
                allres[f'{path.split("/")[-1]}:{body}'] = r
    for name, r in allres.items():
        print(f'== {name} ({r["frames"]} frames) planted heights {r["planted_height_cm"]}')
        for st, m in sorted(r['states'].items()):
            print(f'  [{st}]')
            for key, s in sorted(m.items()):
                print(f'    {key:34s} {s}')
        print('  top pops:', ', '.join(f'{p["bone"]}@{p["frame"]}({p["state"]}) {p["cm"]}cm' for p in r['top_pops'][:8]))
    if js:
        with open(js, 'w') as f:
            json.dump(allres, f, indent=1)


if __name__ == '__main__':
    main()
