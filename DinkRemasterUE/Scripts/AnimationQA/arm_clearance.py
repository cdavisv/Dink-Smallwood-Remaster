"""Arm-to-trunk clearance of a humanoid from the game's own bone traces, with a posture row's upper-arm value W applied.

The posture rows of Content/Dink/Data/Art/animation_natural.json carry a fourth value W: the upper arms brought in
towards the trunk, in degrees (DinkBodyAnimInstance.cpp turns each upper arm about its joint in mesh space; forearm and
hand follow rigidly). This tool answers "how far can W go" without a rendered game: it reads a `dink.Motion.Trace` CSV
(Scripts/AnimationQA/motion_audit.py; bone positions of every frame), applies W the same way, and measures elbow, wrist
and hand against the character's trunk (a rest-pose profile dumped from its Blender source by trunk_profile.py), per
state: idle, walk, run and every action clip.

  blender -b <SK_<Name>_Photoreal.blend> --python Scripts/AnimationQA/trunk_profile.py -- trunk.json
  python3 -I Scripts/AnimationQA/arm_clearance.py <trace.csv> trunk.json [W,W,...] [--scale 0.975]
  python3 -I Scripts/AnimationQA/arm_clearance.py <trace.csv> --frames frames.json      # review frames for trace_pose.py

Numbers are centimetres between the surfaces (limb radii: elbow 4.2, wrist 3.0, hand 3.6); below zero the limb is in the
trunk. The trunk is an ellipse per height, so in front of the chest and above the shoulders the absolute numbers are
rough: read the CHANGE against W 0 there. `--scale` is the size the game draws the body at against its source (bone
lengths of the trace against the rest pose)."""
import sys, csv, json, math, collections
import numpy as np
CHAIN = ['pelvis', 'spine_01', 'spine_03', 'spine_05', 'neck_01']
LIMB = {'elbow': 4.2, 'wrist': 3.0, 'hand': 3.6}


def qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def turn_arm(shoulder, point, w_deg, side):
    """The game's posture turn: `point` (elbow or wrist, mesh space, x = the body's left) about the shoulder joint, W degrees
    towards the trunk. side = +1 for the left arm, -1 for the right."""
    th = math.radians(w_deg) * side
    v = np.asarray(point, float) - shoulder
    c, s = math.cos(th), math.sin(th)
    return shoulder + np.array([v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c])


def read_trace(path, body='hero'):
    """-> list of (state, bones in mesh space). state: idle / walk / run by speed, or act:<clip> while an action plays."""
    frames = collections.OrderedDict()
    for r in csv.DictReader(open(path)):
        if r['body'] != body:
            continue
        f = frames.setdefault(int(r['frame']), {})
        if r['bone'] == '_anim':
            f['_anim'] = (float(r['x']), int(float(r['qy'])), r['ground_what'])
        elif r['bone'] == '_comp':
            f['_comp'] = (np.array([float(r['x']), float(r['y']), float(r['z'])]), np.array([float(r[k]) for k in ('qx', 'qy', 'qz', 'qw')]))
        elif not r['bone'].startswith('_'):
            f[r['bone']] = np.array([float(r['x']), float(r['y']), float(r['z'])])
    out = []
    for fi, f in frames.items():
        if '_anim' not in f or 'hand_l' not in f or '_comp' not in f:
            continue
        cp, cq = f['_comp']
        inv = np.array([-cq[0], -cq[1], -cq[2], cq[3]])
        bones = {k: qrot(inv, v - cp) for k, v in f.items() if not k.startswith('_')}
        speed, acting, name = f['_anim']
        state = ('act:' + name) if acting else ('idle' if speed < 8 else 'walk' if speed < 330 else 'run')
        out.append((fi, state, bones))
    return out


class Trunk:
    def __init__(self, data, scale=1.0):
        self.slices = np.array(data['slices']) * scale
        self.rest = {k: np.array(v) * scale for k, v in data['bones'].items()}

    def clearance(self, point, bones, limb_radius):
        best = None
        for a, b in zip(CHAIN[:-1], CHAIN[1:]):
            d = bones[b] - bones[a]
            t = float(np.clip((point - bones[a]) @ d / (d @ d), 0, 1))
            centre = bones[a] + d * t
            dist = np.linalg.norm(point - centre)
            if best is None or dist < best[0]:
                best = (dist, a, b, t, centre, d / np.linalg.norm(d))
        _, a, b, t, centre, up = best
        zr = self.rest[a][2] + (self.rest[b][2] - self.rest[a][2]) * t
        cr = self.rest[a][:2] + (self.rest[b][:2] - self.rest[a][:2]) * t
        s = self.slices[int(np.clip(np.searchsorted(self.slices[:, 0], zr), 0, len(self.slices) - 1))]
        hi = float(np.clip((zr - self.rest['pelvis'][2]) / (self.rest['spine_05'][2] - self.rest['pelvis'][2]), 0, 1))
        side = (bones['upperarm_l'] - bones['upperarm_r']) * hi + (bones['thigh_l'] - bones['thigh_r']) * (1 - hi)
        side = side - up * (side @ up)
        side /= np.linalg.norm(side)
        fwd = -np.cross(up, side)
        off = point - centre
        dx, dy = float(off @ side), float(off @ fwd)
        half_w = max(abs(s[1]), abs(s[2]))
        half_d = max((s[4] - cr[1]) if dy > 0 else (cr[1] - s[3]), 3.0)
        ang = math.atan2(dy, dx)
        reach = 1 / math.sqrt((math.cos(ang) / half_w) ** 2 + (math.sin(ang) / half_d) ** 2)
        return math.hypot(dx, dy) - reach - limb_radius


def measure(frames, trunk, ws):
    """-> {state: {W: array [frame, side, (elbow, wrist, hand)]}} plus the least distance between the two hands."""
    res = collections.defaultdict(lambda: collections.defaultdict(list))
    for _, state, bones in frames:
        for w in ws:
            row = []
            for sd, side in (('l', 1.0), ('r', -1.0)):
                sh = bones['upperarm_' + sd]
                elbow, wrist = turn_arm(sh, bones['lowerarm_' + sd], w, side), turn_arm(sh, bones['hand_' + sd], w, side)
                fore = wrist - elbow
                hand = wrist + fore / np.linalg.norm(fore) * 8.0
                row.append([trunk.clearance(elbow, bones, LIMB['elbow']), trunk.clearance(wrist, bones, LIMB['wrist']),
                            trunk.clearance(hand, bones, LIMB['hand'])] + list(hand))
            res[state][w].append(row)
    return res


def report(res, ws, min_frames=12):
    lines = []
    for state in sorted(res, key=lambda s: (s.startswith('act'), s)):
        if len(res[state][ws[0]]) < min_frames:
            continue
        lines.append('%-24s frames %d' % (state, len(res[state][ws[0]])))
        for w in ws:
            a = np.array(res[state][w])
            elbow, wrist, hand = a[..., 0], a[..., 1], a[..., 2]
            apart = np.linalg.norm(a[:, 0, 3:] - a[:, 1, 3:], axis=1)
            lines.append('   W %4.1f  elbow mean %5.1f min %5.1f | wrist min %5.1f | hand min %5.1f | frames with a wrist or hand in the trunk %4.1f%% | hands apart min %5.1f'
                         % (w, elbow.mean(), elbow.min(), wrist.min(), hand.min(), 100 * float((np.minimum(wrist, hand).min(1) < 0).mean()), apart.min()))
    return '\n'.join(lines)


def pick_frames(frames, min_frames=12):
    """Three review frames per state for trace_pose.py: the hands nearest the middle of the body, a middle frame, the widest."""
    by = collections.defaultdict(list)
    for fi, state, bones in frames:
        by[state].append((fi, bones))
    out = {}
    for state, rows in by.items():
        if len(rows) < min_frames:
            continue
        key = lambda r: min(abs(r[1]['hand_l'][0] - r[1]['spine_03'][0]), abs(r[1]['hand_r'][0] - r[1]['spine_03'][0]))
        ordered = sorted(rows, key=key)
        out[state] = {name: {'frame': fi, 'bones': {b: [round(float(x), 3) for x in p] for b, p in bones.items()}}
                      for name, (fi, bones) in (('near', ordered[0]), ('mid', rows[len(rows) // 2]), ('far', ordered[-1]))}
    return out


def main(argv):
    if '--frames' in argv:      # arm_clearance.py <trace.csv> --frames <out.json>
        json.dump(pick_frames(read_trace(argv[1])), open(argv[argv.index('--frames') + 1], 'w'))
        return
    scale = 1.0
    if '--scale' in argv:
        i = argv.index('--scale')
        scale = float(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    ws = [float(x) for x in (argv[3] if len(argv) > 3 else '0,4,6,8,11').split(',')]
    trunk = Trunk(json.load(open(argv[2])), scale)
    print(report(measure(read_trace(argv[1]), trunk, ws), ws))


if __name__ == '__main__':
    main(sys.argv)
