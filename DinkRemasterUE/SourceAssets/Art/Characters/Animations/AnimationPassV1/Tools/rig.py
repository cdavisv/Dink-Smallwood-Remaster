"""Kinematics toolkit for the shared 89-bone rig (metres, armature space).

The character stands at the origin, faces -Y (FWD), +X is its left, +Z is up. A Pose holds one
rotation basis per bone (plus a translation for the pelvis); everything else is rest geometry, so
bone lengths never change. Bones follow the Unreal convention found in the rig: the bone runs
along its local X and hinges (knee, elbow, finger) about its local Z.

Only mathutils is needed: the module can be unit-tested without a scene.
"""
import math
from mathutils import Matrix, Vector, Quaternion

FWD = Vector((0.0, -1.0, 0.0))
LEFT = Vector((1.0, 0.0, 0.0))
UP = Vector((0.0, 0.0, 1.0))

# Sole geometry relative to the ankle joint (foot bone head) with the foot flat, from the hero
# mesh: forward (along FWD) and up. Heel is the back edge of the sole, ball the toe joint.
ANKLE_H = 0.082
HEEL_F, BALL_F, TOE_F = -0.078, 0.149, 0.230
AIM_CHILD = {'thigh': 'calf', 'calf': 'foot', 'upperarm': 'lowerarm', 'lowerarm': 'hand'}


def rot(axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis).normalized())


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def smoother(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6.0 * u - 15.0) + 10.0)


def lerp(a, b, u):
    return a + (b - a) * u


def hermite(p0, v0, p1, v1, u, span):
    """Cubic through p0/p1 with end velocities v0/v1 (units per second) over `span` seconds."""
    u2, u3 = u * u, u * u * u
    return ((2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * v0 * span +
            (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * v1 * span)


def keyed(keys, t):
    """Piecewise smooth interpolation of (time, value...) rows; values may be floats or Vectors."""
    if t <= keys[0][0]:
        return keys[0][1:] if len(keys[0]) > 2 else keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            u = smooth((t - a[0]) / (b[0] - a[0])) if b[0] > a[0] else 1.0
            out = [lerp(x, y, u) for x, y in zip(a[1:], b[1:])]
            return out if len(out) > 1 else out[0]
    return keys[-1][1:] if len(keys[-1]) > 2 else keys[-1][1]


def frame3(d, h):
    """Orthonormal 3x3 whose first column is d and second the part of h perpendicular to d."""
    d = Vector(d).normalized()
    h = Vector(h)
    h = (h - d * h.dot(d))
    if h.length < 1e-8:
        h = d.orthogonal()
    h.normalize()
    n = d.cross(h)
    m = Matrix((d, h, n))
    m.transpose()
    return m


class Rig:
    def __init__(self, bones):
        """bones: iterable of (name, parent_name_or_None, 4x4 rest matrix in armature space)."""
        rows = list(bones)
        self.parent = {n: p for n, p, _ in rows}
        self.rest = {n: Matrix(m) for n, _, m in rows}
        order, done = [], set()
        while len(order) < len(rows):
            for n, p, _ in rows:
                if n not in done and (p is None or p in done):
                    order.append(n)
                    done.add(n)
        self.order = order
        self.restlocal = {n: (self.rest[self.parent[n]].inverted() @ self.rest[n]) if self.parent[n] else self.rest[n].copy()
                          for n in order}
        self.head = {n: self.rest[n].translation.copy() for n in order}

    @classmethod
    def from_armature(cls, arm):
        return cls((b.name, b.parent.name if b.parent else None, b.matrix_local.copy()) for b in arm.data.bones)

    def length(self, a, b):
        return (self.head[b] - self.head[a]).length


class Pose:
    def __init__(self, rig):
        self.rig = rig
        self.basis = {}
        self._w = None
        self.clamped = []

    def copy(self):
        p = Pose(self.rig)
        p.basis = {k: v.copy() for k, v in self.basis.items()}
        return p

    # ---- forward kinematics
    def world(self):
        if self._w is None:
            w = {}
            r = self.rig
            for n in r.order:
                m = r.restlocal[n] if r.parent[n] is None else w[r.parent[n]] @ r.restlocal[n]
                b = self.basis.get(n)
                w[n] = m @ b if b is not None else m
            self._w = w
        return self._w

    def W(self, name):
        return self.world()[name]

    def pos(self, name):
        return self.world()[name].translation.copy()

    def _parent_frame(self, name):
        r = self.rig
        p = r.parent[name]
        return (self.world()[p] @ r.restlocal[name]) if p else r.restlocal[name]

    # ---- setters
    def set_world_rot(self, name, r3):
        m = self._parent_frame(name)
        b = (m.to_3x3().inverted() @ Matrix(r3)).to_4x4()
        old = self.basis.get(name)
        if old is not None:
            b.translation = old.translation
        self.basis[name] = b
        self._w = None

    def set_delta(self, name, r3):
        """World rotation = r3 applied to the bone's REST orientation (armature space)."""
        self.set_world_rot(name, Matrix(r3) @ self.rig.rest[name].to_3x3())

    def rotate(self, name, axis, angle):
        """Add an armature-space rotation to the bone as it is now posed."""
        if abs(angle) < 1e-9:
            return
        self.set_world_rot(name, rot(axis, angle) @ self.W(name).to_3x3())

    def rotate_local(self, name, axis, angle):
        b = self.basis.get(name, Matrix.Identity(4))
        self.basis[name] = b @ Matrix.Rotation(angle, 4, Vector(axis))
        self._w = None

    def set_pelvis(self, position, r3delta):
        """Pelvis joint at `position` with r3delta applied to its rest orientation."""
        m = self._parent_frame('pelvis')
        target = (Matrix(r3delta) @ self.rig.rest['pelvis'].to_3x3()).to_4x4()
        target.translation = Vector(position)
        self.basis['pelvis'] = m.inverted() @ target
        self._w = None

    def aim(self, name, direction, hinge):
        r = self.rig
        base, side = name.rsplit('_', 1)
        child = AIM_CHILD[base] + '_' + side
        d_rest = r.head[child] - r.head[name]
        h_rest = r.rest[name].to_3x3().col[2]
        delta = frame3(direction, hinge) @ frame3(d_rest, h_rest).transposed()
        self.set_world_rot(name, delta @ r.rest[name].to_3x3())

    def ik(self, limb, side, target, pole):
        """Two-bone IK. limb 'leg' or 'arm'; pole is the direction the knee/elbow points."""
        upper, lower, end = (('thigh', 'calf', 'foot') if limb == 'leg' else ('upperarm', 'lowerarm', 'hand'))
        upper, lower, end = upper + '_' + side, lower + '_' + side, end + '_' + side
        r = self.rig
        h0 = self.pos(upper)
        l1, l2 = r.length(upper, lower), r.length(lower, end)
        t = Vector(target) - h0
        dist = t.length
        reach = (l1 + l2) * 0.9992
        if dist > reach:
            self.clamped.append((end, dist - reach))
            dist = reach
        dist = max(dist, abs(l1 - l2) + 1e-4)
        dirn = t.normalized()
        pole = Vector(pole)
        perp = pole - dirn * pole.dot(dirn)
        if perp.length < 1e-6:
            perp = dirn.orthogonal()
        perp.normalize()
        a = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
        knee = h0 + dirn * a + perp * math.sqrt(max(0.0, l1 * l1 - a * a))
        d1 = knee - h0
        d2 = h0 + dirn * dist - knee
        hinge = d1.cross(perp)
        self.aim(upper, d1, hinge)
        self.aim(lower, d2, hinge)
        return h0 + dirn * dist

    def arm_fk(self, side, swing, abduct, flex, inward=0.0, pole_out=0.25):
        """Hanging-arm FK. swing: upper arm forward (+) / back (-) from vertical; abduct: away from
        the body; flex: elbow; inward: rotates the forearm across the front of the body."""
        s = 1.0 if side == 'l' else -1.0
        d1 = Vector((s * math.sin(abduct), -math.sin(swing) * math.cos(abduct), -math.cos(swing) * math.cos(abduct)))
        pole = Vector((s * pole_out, 1.0, 0.0))
        pole = pole - d1 * pole.dot(d1)
        pole.normalize()
        hinge = d1.cross(pole)
        hinge = rot(d1, s * inward) @ hinge
        d2 = rot(hinge, -flex) @ d1
        if d2.dot(FWD) < d1.dot(FWD) - 1e-6 and flex > 0:
            d2 = rot(hinge, flex) @ d1
        self.aim('upperarm_' + side, d1, hinge)
        self.aim('lowerarm_' + side, d2, hinge)

    def hand_follow(self, side):
        """Drop any hand basis so the hand keeps its rest relation to the forearm."""
        self.basis.pop('hand_' + side, None)
        self._w = None

    def forearm_twist(self, side):
        """Spread the hand's roll about the forearm over the two forearm twist bones."""
        r = self.rig
        hand = 'hand_' + side
        b = self.basis.get(hand)
        for n in ('lowerarm_twist_01_' + side, 'lowerarm_twist_02_' + side):
            self.basis.pop(n, None)
        if b is None:
            self._w = None
            return
        axis = r.restlocal[hand].translation.normalized()
        q = (r.restlocal[hand].to_3x3() @ b.to_3x3() @ r.restlocal[hand].to_3x3().inverted()).to_quaternion()
        proj = Vector((q.x, q.y, q.z)).dot(axis)
        twist = Quaternion((q.w, *(axis * proj)))
        if twist.magnitude < 1e-8:
            return
        twist.normalize()
        angle = 2.0 * math.atan2(Vector((twist.x, twist.y, twist.z)).dot(axis), twist.w)
        if angle > math.pi:
            angle -= 2 * math.pi
        if angle < -math.pi:
            angle += 2 * math.pi
        for n, frac in (('lowerarm_twist_01_' + side, 0.66), ('lowerarm_twist_02_' + side, 0.33)):
            local_axis = r.restlocal[n].to_3x3().inverted() @ axis
            self.basis[n] = Matrix.Rotation(angle * frac, 4, local_axis)
        self._w = None

    def fingers(self, side, curl, thumb=None, spread=0.0):
        """curl 0 = rest hand, 1 = closed fist. Flexion is about each finger bone's local Z."""
        s = self.finger_sign(side)
        for finger in ('index', 'middle', 'ring', 'pinky'):
            for joint, angle in ((1, 1.25), (2, 1.45), (3, 0.95)):
                n = '%s_%02d_%s' % (finger, joint, side)
                self.basis[n] = Matrix.Rotation(s * angle * curl, 4, 'Z')
        t = curl if thumb is None else thumb
        for joint, angle in ((1, 0.45), (2, 0.55), (3, 0.75)):
            n = 'thumb_%02d_%s' % (joint, side)
            self.basis[n] = Matrix.Rotation(s * angle * t, 4, 'Z')
        self._w = None

    def finger_sign(self, side):
        cache = self.rig.__dict__.setdefault('_finger_sign', {})
        if side not in cache:
            r = self.rig
            hand = r.head['hand_' + side]
            mid = r.head['middle_01_' + side] - hand
            lat = r.head['index_01_' + side] - r.head['pinky_01_' + side]
            palm = mid.cross(lat).normalized()
            # Palm side is where the thumb sits relative to the back of the hand.
            if (r.head['thumb_02_' + side] - hand).dot(palm) < 0:
                palm = -palm
            n = 'middle_01_' + side
            tip = r.head['middle_02_' + side] - r.head[n]
            z = r.rest[n].to_3x3().col[2]
            moved = rot(z, 0.3) @ tip
            cache[side] = 1.0 if (moved - tip).dot(palm) > 0 else -1.0
        return cache[side]

    def spine(self, yaw=0.0, pitch=0.0, roll=0.0, weights=(0.12, 0.18, 0.22, 0.26, 0.22)):
        """Distribute an armature-space rotation over spine_01..05. yaw: turn left (+); pitch:
        bend forward (+); roll: lean to the character's left (+)."""
        for n, w in zip(('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'), weights):
            self.rotate(n, UP, yaw * w)
            self.rotate(n, LEFT, pitch * w)
            self.rotate(n, FWD, -roll * w)

    def head_world(self, yaw=0.0, pitch=0.0, roll=0.0, follow=0.0):
        """Head orientation in armature space (0 = level, looking along FWD; pitch + looks down). `follow` in 0..1
        lets it keep that share of what the chest is doing instead of fully stabilising."""
        r = self.rig
        chest = self.W('spine_05').to_3x3() @ r.rest['spine_05'].to_3x3().inverted()
        want = rot(UP, yaw) @ rot(LEFT, pitch) @ rot(FWD, -roll)
        qc, qw = chest.to_quaternion(), want.to_quaternion()
        target = qw.slerp(qc @ qw, follow) if follow > 0 else qw
        for n, share in (('neck_01', 0.3), ('neck_02', 0.6), ('head', 1.0)):
            q = qc.slerp(target, share)
            self.set_delta(n, q.to_matrix())

    def foot(self, side, ankle, pitch=0.0, yaw=0.0, toe=0.0, roll=0.0, knee_out=0.0):
        """Plant the leg: ankle position, foot pitch (toes up +), yaw (toes out +), toe bend (toes up +)."""
        s = 1.0 if side == 'l' else -1.0
        r3 = rot(UP, s * yaw) @ rot(FWD, -s * roll) @ rot(LEFT, -pitch)
        pole = rot(UP, s * (yaw * 0.6 + knee_out)) @ FWD
        self.ik('leg', side, ankle, pole)
        self.set_delta('foot_' + side, r3)
        self.set_delta('ball_' + side, rot(UP, s * yaw) @ rot(LEFT, -(pitch + toe)))

    def finish(self):
        """IK helper bones follow the limbs, as Unreal expects of this skeleton."""
        w = self.world()
        for n, src in (('ik_foot_l', 'foot_l'), ('ik_foot_r', 'foot_r'), ('ik_hand_gun', 'hand_r')):
            self.basis[n] = self._parent_frame(n).inverted() @ w[src]
        self._w = None
        w = self.world()
        for n, src in (('ik_hand_l', 'hand_l'), ('ik_hand_r', 'hand_r')):
            self.basis[n] = self._parent_frame(n).inverted() @ w[src]
        self._w = None
        return self


def ankle_from_contact(flat_f, pitch, lift=0.0):
    """Sagittal ankle position (forward, up) for a foot whose flat-footed ankle would sit at
    forward coordinate flat_f. Toes-up pitch pivots on the heel, toes-down on the ball, so the
    pivot stays exactly where the flat foot had it: no sliding by construction."""
    if pitch >= 0:
        pf, c, s = HEEL_F, math.cos(pitch), math.sin(pitch)
        rel_f, rel_z = -pf, ANKLE_H
        return flat_f + pf + rel_f * c - rel_z * s, lift + rel_f * s + rel_z * c
    pf, c, s = BALL_F, math.cos(pitch), math.sin(pitch)
    rel_f, rel_z = -pf, ANKLE_H
    return flat_f + pf + rel_f * c - rel_z * s, lift + rel_f * s + rel_z * c


def sole_points(pose, side):
    """World positions of the heel and ball contact points for the posed foot."""
    m = pose.W('foot_' + side)
    r = pose.rig
    inv = r.rest['foot_' + side].inverted()
    s = 1.0 if side == 'l' else -1.0
    ankle = r.head['foot_' + side]
    heel = Vector((ankle.x, ankle.y - HEEL_F, 0.0))
    ball = Vector((ankle.x + s * 0.017, ankle.y - BALL_F, 0.0))
    return m @ (inv @ heel), m @ (inv @ ball)
