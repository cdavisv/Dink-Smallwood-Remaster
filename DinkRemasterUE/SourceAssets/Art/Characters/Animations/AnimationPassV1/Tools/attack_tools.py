"""Keyed full-body action clips on the shared rig.

A body state is a flat dict of numbers (pelvis, spine, head, feet, wrist targets in the chest's
frame). A clip is a list of (time, changes) keys; states are interpolated with a monotone cubic,
so a value that is equal on two neighbouring keys holds exactly (planted feet do not creep) and
values that pass through a key keep their speed (no stop-start puppet motion). The first and
the last frames are blended, bone by bone, into the shared stand pose.
"""
import math
from mathutils import Matrix, Vector, Quaternion
from rig import Pose, rot, smooth, lerp, FWD, LEFT, UP, ANKLE_H, HEEL_F, BALL_F, ankle_from_contact

D = math.radians
BALL_X = 0.017


def state_from_pose(rig, pose):
    """Read an action state back from a standing pose (feet flat), so actions start from it."""
    S = {}
    w = pose.world()
    pm = w['pelvis']
    d = pm.to_3x3() @ rig.rest['pelvis'].to_3x3().inverted()
    f = d @ FWD
    S['pel_yaw'] = math.atan2(f.x, -f.y)
    u = (rot(UP, -S['pel_yaw']) @ d) @ UP
    S['pel_pitch'] = math.atan2(-u.y, u.z)
    S['pel_roll'] = math.atan2(u.x, u.z)
    S['pel_x'] = pm.translation.x
    S['pel_f'] = rig.head['pelvis'].y - pm.translation.y
    S['pel_drop'] = rig.head['pelvis'].z - pm.translation.z
    cd = w['spine_05'].to_3x3() @ rig.rest['spine_05'].to_3x3().inverted()
    f = cd @ FWD
    chest_yaw = math.atan2(f.x, -f.y)
    S['sp_yaw'] = chest_yaw - S['pel_yaw']
    u = (rot(UP, -chest_yaw) @ cd) @ UP
    S['sp_pitch'] = math.atan2(-u.y, u.z) - S['pel_pitch']
    S['sp_roll'] = math.atan2(u.x, u.z) - S['pel_roll']
    hd = w['head'].to_3x3() @ rig.rest['head'].to_3x3().inverted()
    f = hd @ FWD
    S['hd_yaw'] = math.atan2(f.x, -f.y)
    S['hd_pitch'] = math.atan2(-f.z, math.hypot(f.x, f.y))
    S['hd_roll'] = 0.0
    S['hd_follow'] = 0.1
    origin, frame = chest_frame(rig, pose)
    inv = frame.inverted()
    for side, sign, k in (('l', 1.0, 'l'), ('r', -1.0, 'r')):
        fm = w['foot_' + side]
        fd = fm.to_3x3() @ rig.rest['foot_' + side].to_3x3().inverted()
        ff = fd @ FWD
        S[k + 'f_yaw'] = sign * math.atan2(ff.x, -ff.y)
        S[k + 'f_x'] = fm.translation.x
        S[k + 'f_f'] = rig.head['foot_' + side].y - fm.translation.y
        S[k + 'f_yaw0'] = S[k + 'f_yaw']
        S[k + 'f_toe'] = 1.0
        S[k + 'f_knee'] = 0.0
        S[k + 'f_lift'] = 0.0
        S[k + 'f_pitch'] = 0.0
        sh, el, wr = (w[n + '_' + side].translation for n in ('upperarm', 'lowerarm', 'hand'))
        t = inv @ (wr - origin)
        S[k + 'a_x'], S[k + 'a_f'], S[k + 'a_z'] = t.x, -t.y, t.z
        p = inv @ (el - (sh + wr) * 0.5)
        if p.length < 1e-4:
            p = Vector((sign * 0.2, 1.0, 0.0))
        p.normalize()
        S[k + 'a_px'], S[k + 'a_pf'], S[k + 'a_pz'] = p.x, -p.y, p.z
        S[k + 'a_pron'] = 0.0
        S[k + 'a_bend'] = 0.0
        S[k + 'a_curl'] = 0.3
        S[k + '_shrug'] = 0.0
        S[k + '_protract'] = 0.0
    return S


def chest_frame(rig, pose):
    """Origin at the top of the spine; axes turned by the chest's yaw only (x left, -y forward)."""
    w = pose.W('spine_05')
    d = w.to_3x3() @ rig.rest['spine_05'].to_3x3().inverted()
    f = d @ FWD
    return w.translation.copy(), rot(UP, math.atan2(f.x, -f.y))


def place_foot(pose, side, S):
    """Foot from its flat-footed ankle reference; yaw pivots on the ball, pitch on heel or ball."""
    rig = pose.rig
    k = side
    s = 1.0 if side == 'l' else -1.0
    yaw0 = S.get(k + 'f_yaw0', S[k + 'f_yaw'])
    yaw = S[k + 'f_yaw']
    pitch = S[k + 'f_pitch']
    a0 = Vector((S[k + 'f_x'], rig.head['foot_' + side].y - S[k + 'f_f'], 0.0))
    ball = a0 + rot(UP, s * yaw0) @ (s * BALL_X * LEFT + BALL_F * FWD)
    flat = ball - rot(UP, s * yaw) @ (s * BALL_X * LEFT + BALL_F * FWD)
    df, z = ankle_from_contact(0.0, pitch, S[k + 'f_lift'])
    ankle = flat + (rot(UP, s * yaw) @ FWD) * df
    ankle.z = z
    pose.foot(side, ankle, pitch=pitch, yaw=yaw, toe=(-pitch if pitch < 0 else 0.0) * S.get(k + 'f_toe', 1.0),
              knee_out=S.get(k + 'f_knee', 0.0))


def build_pose(rig, S):
    pose = Pose(rig)
    pr = rot(UP, S['pel_yaw']) @ rot(FWD, -S['pel_roll']) @ rot(LEFT, S['pel_pitch'])
    pose.set_pelvis(Vector((S['pel_x'], rig.head['pelvis'].y - S['pel_f'], rig.head['pelvis'].z - S['pel_drop'])), pr)
    place_foot(pose, 'l', S)
    place_foot(pose, 'r', S)
    pose.spine(yaw=S['sp_yaw'], pitch=S['sp_pitch'], roll=S['sp_roll'])
    for side, sign in (('l', 1.0), ('r', -1.0)):
        if S[side + '_shrug']:
            pose.rotate('clavicle_' + side, FWD, -sign * S[side + '_shrug'])
        if S[side + '_protract']:
            pose.rotate('clavicle_' + side, UP, sign * S[side + '_protract'])
    origin, frame = chest_frame(rig, pose)
    for side in 'lr':
        k = side
        target = origin + frame @ Vector((S[k + 'a_x'], -S[k + 'a_f'], S[k + 'a_z']))
        pole = frame @ Vector((S[k + 'a_px'], -S[k + 'a_pf'], S[k + 'a_pz']))
        pose.ik('arm', side, target, pole)
        pose.basis.pop('hand_' + side, None)
        pose._w = None
        if S[k + 'a_bend']:
            pose.rotate_local('hand_' + side, (0.0, 0.0, 1.0), S[k + 'a_bend'])
        if S[k + 'a_pron']:
            # Roll about the forearm: the hand's own X runs along it.
            b = pose.basis.get('hand_' + side, Matrix.Identity(4))
            pose.basis['hand_' + side] = Matrix.Rotation(S[k + 'a_pron'], 4, 'X') @ b
            pose._w = None
        pose.forearm_twist(side)
        pose.fingers(side, S[k + 'a_curl'], thumb=min(1.0, S[k + 'a_curl']) * 0.9)
    pose.head_world(yaw=S['hd_yaw'], pitch=S['hd_pitch'], roll=S['hd_roll'], follow=S['hd_follow'])
    return pose.finish()


def world_to_chest(rig, S, side, x, f, z):
    """Chest-frame wrist target that puts the wrist at an armature-space point for this body state."""
    T = dict(S)
    pose = build_pose(rig, T)
    origin, frame = chest_frame(rig, pose)
    t = frame.inverted() @ (Vector((x, rig.head['pelvis'].y - f, z)) - origin)
    return {side + 'a_x': t.x, side + 'a_f': -t.y, side + 'a_z': t.z}


def _tangents(ts, vs):
    n = len(ts)
    m = [0.0] * n
    for i in range(n):
        if i == 0 or i == n - 1:
            continue
        d0 = (vs[i] - vs[i - 1]) / (ts[i] - ts[i - 1])
        d1 = (vs[i + 1] - vs[i]) / (ts[i + 1] - ts[i])
        if d0 * d1 <= 0:
            continue
        m[i] = 2.0 * d0 * d1 / (d0 + d1)  # harmonic mean: monotone, no overshoot past a hold
    return m


def sample(keys, t):
    """keys: [(time, full state dict)], increasing times."""
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return dict(keys[0][1])
    if t >= ts[-1]:
        return dict(keys[-1][1])
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    h = ts[i + 1] - ts[i]
    u = (t - ts[i]) / h
    u2, u3 = u * u, u * u * u
    out = {}
    cache = keys[0][2]
    for name in keys[0][1]:
        m = cache.get(name)
        if m is None:
            m = cache[name] = _tangents(ts, [k[1][name] for k in keys])
        p0, p1 = keys[i][1][name], keys[i + 1][1][name]
        if p0 == p1 and m[i] == 0.0 and m[i + 1] == 0.0:
            out[name] = p0
        else:
            out[name] = ((2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * h * m[i] +
                         (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * h * m[i + 1])
    return out


def expand(base, rows):
    """rows: [(time, {changes})]; each key carries the previous key's values forward."""
    keys, cur, cache = [], dict(base), {}
    for t, changes in rows:
        cur = dict(cur)
        cur.update(changes)
        keys.append((t, cur, cache))
    return keys


def blend_pose(a, b, w):
    """Bone-by-bone blend of two poses of the same rig (w = 0 gives a, 1 gives b)."""
    if w <= 0.0:
        return a
    if w >= 1.0:
        return b
    out = Pose(a.rig)
    identity = Matrix.Identity(4)
    for n in set(a.basis) | set(b.basis):
        ma, mb = a.basis.get(n, identity), b.basis.get(n, identity)
        q = ma.to_quaternion().slerp(mb.to_quaternion(), w)
        m = q.to_matrix().to_4x4()
        m.translation = ma.translation.lerp(mb.translation, w)
        out.basis[n] = m
    out.clamped = list(b.clamped)
    return out


def apply_steps(S, base, steps, t):
    """Foot steps: the foot only travels while it is clear of the ground, so it cannot skim.
    steps: {side: [(t0, t1, forward, lateral, height)]}; forward/lateral are flat ankle references."""
    for side, rows in (steps or {}).items():
        f, x = base[side + 'f_f'], base[side + 'f_x']
        lift = 0.0
        for (t0, t1, f1, x1, h) in rows:
            x1 = x if x1 is None else x1
            if t >= t1:
                f, x = f1, x1
            elif t > t0:
                u = (t - t0) / (t1 - t0)
                m = smooth(min(1.0, max(0.0, (u - 0.14) / 0.72)))
                f, x = lerp(f, f1, m), lerp(x, x1, m)
                lift = h * math.sin(math.pi * u) ** 0.8
        S[side + 'f_f'], S[side + 'f_x'], S[side + 'f_lift'] = f, x, lift
    return S


def action_clip(rig, name, stand, rows, duration, fps=60, blend_in=0.05, blend_out=0.12, family='hero_attack',
                events=None, end_stand=None, steps=None):
    """Sample the keyed states; frame 0 and the last frame are exactly the stand pose."""
    base = state_from_pose(rig, stand)
    keys = expand(base, rows(base) if callable(rows) else rows)
    n = int(round(duration * fps))
    end_stand = end_stand or stand
    poses = []
    for i in range(n + 1):
        t = i / fps
        pose = build_pose(rig, apply_steps(sample(keys, t), base, steps, t))
        if t < blend_in:
            pose = blend_pose(stand, pose, smooth(t / blend_in))
        tail = duration - t
        if tail < blend_out:
            pose = blend_pose(end_stand, pose, smooth(tail / blend_out))
        poses.append(pose)
    clip = dict(name=name, fps=fps, poses=poses, loop=False, family=family, strip_every=3)
    if events:
        clip['events'] = events
        hit = events.get('hit_s')
        if hit is not None:
            pose = build_pose(rig, apply_steps(sample(keys, hit), base, steps, hit))
            chest = pose.pos('spine_05')
            reach = {s: round(chest.y - pose.pos('hand_' + s).y, 3) for s in 'lr'}
            clip['note'] = 'wrist ahead of chest at hit (m): L %.3f R %.3f; wrist height L %.2f R %.2f' % (
                reach['l'], reach['r'], pose.pos('hand_l').z, pose.pos('hand_r').z)
    return clip


class Keys:
    """Row builder: add(t, **changes) carries values forward; world() converts a wrist target."""
    def __init__(self, rig, base):
        self.rig, self.base, self.cur, self.rows, self.steps = rig, dict(base), dict(base), [], {}

    def step(self, side, t0, t1, forward=0.0, lateral=None, height=0.05):
        """forward is relative to the stand position of that foot; lateral is absolute (None keeps it)."""
        self.steps.setdefault(side, []).append((t0, t1, self.base[side + 'f_f'] + forward, lateral, height))
        return self

    def add(self, t, _world=None, **changes):
        self.cur = dict(self.cur)
        self.cur.update(changes)
        if _world:
            at = apply_steps(dict(self.cur), self.base, self.steps, t)
            for side, (x, f, z) in _world.items():
                self.cur.update(world_to_chest(self.rig, at, side, x, f, z))
        self.rows.append((t, dict(self.cur)))
        return self

    def hold(self, t):
        self.rows.append((t, dict(self.cur)))
        return self

    def rest(self, t, **changes):
        self.cur = dict(self.base)
        self.cur.update(changes)
        self.rows.append((t, dict(self.cur)))
        return self


def arm(side, x, f, z, pole=None, pron=None, curl=None, bend=None):
    out = {side + 'a_x': x, side + 'a_f': f, side + 'a_z': z}
    if pole is not None:
        out.update({side + 'a_px': pole[0], side + 'a_pf': pole[1], side + 'a_pz': pole[2]})
    if pron is not None:
        out[side + 'a_pron'] = pron
    if curl is not None:
        out[side + 'a_curl'] = curl
    if bend is not None:
        out[side + 'a_bend'] = bend
    return out


def pole(side, x, f, z):
    return {side + 'a_px': x, side + 'a_pf': f, side + 'a_pz': z}
