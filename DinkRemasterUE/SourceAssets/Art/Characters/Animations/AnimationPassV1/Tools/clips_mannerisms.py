"""Hero mannerisms (13 Nov 2026): the growth arc from a slumped, clumsy pig farmer to a hero.

makers(rig) -> {name: callable returning a clip dict}.

Posture_* and RunArms_Timid are ADDITIVE poses: every bone holds its rotation away from the rest
pose (the pose basis), and the runtime applies that rotation in the bone's own frame on top of
whatever the body is doing (motion capture, an attack), weighted by the hero's confidence. They
are authored with rotations that mean the same thing in any pose: spine and neck flexion, the
collar bones, a twist about the upper arm's own axis, the elbow hinge, the foot about its own
vertical.

Everything else is an ordinary action clip that starts and ends in the neutral stand (NEUTRAL),
so the additive posture can be layered over it at full strength.

Preview_* clips are for the review strips only and are never exported.
"""
import math
from mathutils import Matrix, Vector
from rig import Pose, rot, FWD, LEFT, UP
from attack_tools import D, Keys, arm, pole, action_clip, state_from_pose
from clips_locomotion import stand_pose, stand_parts, stand_from
from clips_attacks import settle, EVENTS, H0, H1

NEUTRAL = 0.8
FAMILY = 'hero_mannerism'
SPINE = ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05')


# ---------------------------------------------------------------- additive poses
def _twist(pose, name, child, angle):
    """Rotation about the bone's own length (pose independent)."""
    r = pose.rig
    pose.rotate(name, (r.head[child] - r.head[name]).normalized(), angle)


def _hinge(pose, name, tip, angle):
    """Flex a hinge about its local Z, whichever sign brings `tip` forward and up."""
    r = pose.rig
    before = pose.pos(tip)
    pose.rotate_local(name, (0.0, 0.0, 1.0), angle)
    moved = pose.pos(tip) - before
    if moved.dot(FWD + UP) < 0:
        pose.rotate_local(name, (0.0, 0.0, 1.0), -2.0 * angle)


def posture_pose(rig, kind):
    p = Pose(rig)
    if kind == 'timid':
        # A rounded upper back, most of it high up, with the neck and head carried forward and
        # down: he looks at the ground a couple of metres ahead of his feet.
        p.spine(pitch=D(19), roll=D(1.5), weights=(0.04, 0.10, 0.20, 0.32, 0.34))
        p.rotate('neck_01', LEFT, D(11))
        p.rotate('neck_02', LEFT, D(7))
        p.rotate('head', LEFT, D(7))
        p.rotate('head', FWD, D(-3))             # a slight tilt: never quite square
        for side, s in (('l', 1.0), ('r', -1.0)):
            p.rotate('clavicle_' + side, UP, s * D(13))       # shoulders drawn forward
            p.rotate('clavicle_' + side, FWD, -s * D(5))      # and a little up towards the ears
            # Arms turned in so the backs of the hands lead, elbows slack, wrists limp.
            _twist(p, 'upperarm_' + side, 'lowerarm_' + side, s * D(20))
            _hinge(p, 'lowerarm_' + side, 'hand_' + side, D(9 if side == 'l' else 14))
            p.rotate_local('hand_' + side, (0.0, 0.0, 1.0), D(-10))
            p.rotate('foot_' + side, UP, -s * D(7))           # pigeon toes
    elif kind == 'confident':
        # Chest lifted and open, shoulders back and down, chin level, arms carried a touch wide.
        p.spine(pitch=D(-6), weights=(0.05, 0.15, 0.25, 0.30, 0.25))
        p.rotate('neck_01', LEFT, D(-1.5))
        p.rotate('head', LEFT, D(-2.5))
        for side, s in (('l', 1.0), ('r', -1.0)):
            p.rotate('clavicle_' + side, UP, -s * D(7))
            p.rotate('clavicle_' + side, FWD, s * D(2.5))
            _twist(p, 'upperarm_' + side, 'lowerarm_' + side, -s * D(6))
            p.rotate('foot_' + side, UP, s * D(2))
    elif kind == 'runarms':
        # The run of someone who was never taught to run: elbows out like wings, forearms
        # dangling, chin poked forward.
        for side, s in (('l', 1.0), ('r', -1.0)):
            p.rotate('clavicle_' + side, FWD, -s * D(9))
            _twist(p, 'upperarm_' + side, 'lowerarm_' + side, s * D(28))
            _hinge(p, 'lowerarm_' + side, 'hand_' + side, D(-22 if side == 'l' else -12))
            p.rotate_local('hand_' + side, (0.0, 0.0, 1.0), D(-22))
        p.rotate('neck_01', LEFT, D(-6))
        p.rotate('head', LEFT, D(-8))
    else:
        raise ValueError(kind)
    return p


def additive_clip(rig, name, kind):
    pose = posture_pose(rig, kind)
    return dict(name=name, fps=30, poses=[pose, pose], loop=False, speed=0.0, stride=0.0, family='hero_posture',
                strip_every=1, note='additive: bone rotations away from the rest pose')


def compose(base, add, weight):
    """What the runtime does: the additive rotation applied in each bone's own frame."""
    out = base.copy()
    identity = Matrix.Identity(4)
    for n, delta in add.basis.items():
        q = Matrix.Identity(3).to_quaternion().slerp(delta.to_quaternion(), weight)
        b = out.basis.get(n, identity)
        m = b @ q.to_matrix().to_4x4()
        out.basis[n] = m
    out._w = None
    return out


def posture_at(rig, pose, confidence, share=1.0):
    """The timid and the confident additive mixed as the runtime mixes them."""
    t, c = posture_pose(rig, 'timid'), posture_pose(rig, 'confident')
    mix = Pose(rig)
    identity = Matrix.Identity(4)
    for n in set(t.basis) | set(c.basis):
        q = t.basis.get(n, identity).to_quaternion().slerp(c.basis.get(n, identity).to_quaternion(), confidence)
        mix.basis[n] = q.to_matrix().to_4x4()
    return compose(pose, mix, share)


def preview_posture(rig):
    stand = stand_pose(rig, NEUTRAL)
    poses = [posture_at(rig, stand, c) for c in (0.0, 0.25, 0.5, 0.75, 1.0)]
    return dict(name='Preview_Posture', fps=1, poses=poses, loop=False, speed=0.0, stride=0.0, family='preview', strip_every=1)


def preview_over(rig, name, clip, confidence, every, share=1.0):
    """An action clip with the posture layered on, as the game shows it at one confidence (share: how much of the posture the clip keeps)."""
    out = dict(clip)
    out['name'] = name
    out['poses'] = [posture_at(rig, p, confidence, share) for p in clip['poses']]
    out['family'] = 'preview'
    out['strip_every'] = every
    return out


# ---------------------------------------------------------------- action clips
def _keys(rig, c=NEUTRAL):
    stand = stand_pose(rig, c)
    return stand, Keys(rig, state_from_pose(rig, stand))


def trip(rig, name, run):
    """A toe catches. The trunk pitches after the foot that stayed behind, the arms shoot out,
    two catch steps, and (walking) a hurt look back at the ground that did it."""
    stand, K = _keys(rig)
    b = K.base
    big = 1.0 if run else 0.62
    K.step('r', 0.06, 0.20, forward=0.34 * big + 0.08, height=0.06)
    K.step('l', 0.22, 0.38, forward=0.22 * big + 0.04, height=0.08)
    K.step('r', 0.52, 0.68, forward=0.0, height=0.04)
    K.step('l', 0.66, 0.82, forward=0.0, height=0.04)
    K.add(0.0)
    K.add(0.10, pel_f=0.08, pel_drop=0.03, sp_pitch=b['sp_pitch'] + D(18 * big), pel_pitch=b['pel_pitch'] + D(7), lf_pitch=D(-32),
          hd_pitch=D(-10), hd_follow=0.55, l_shrug=D(14), r_shrug=D(10), sp_yaw=D(8),
          **arm('l', 0.34, 0.30, -0.26, pole=(1.0, -0.4, 0.0), curl=0.05), **arm('r', -0.40, 0.14, -0.18, pole=(-1.0, -0.5, 0.1), curl=0.05))
    K.add(0.24, pel_f=0.18, pel_drop=0.08, sp_pitch=b['sp_pitch'] + D(40 * big), pel_pitch=b['pel_pitch'] + D(12), lf_pitch=D(-46),
          sp_roll=D(-8), pel_yaw=D(9), sp_yaw=D(15), hd_pitch=D(-4), hd_follow=0.7,
          **arm('l', 0.46, 0.22, -0.02 + 0.10 * big, pole=(0.9, -0.7, 0.3)), **arm('r', -0.46, 0.02, -0.34, pole=(-1.0, -0.4, -0.2)))
    K.add(0.42, pel_f=0.20, pel_drop=0.05, sp_pitch=b['sp_pitch'] + D(20 * big), pel_pitch=b['pel_pitch'] + D(7), lf_pitch=0.0,
          sp_roll=D(6), pel_yaw=D(-8), sp_yaw=D(-13), hd_pitch=D(6), hd_follow=0.4,
          **arm('l', 0.40, -0.06, -0.30, pole=(1.0, -0.5, -0.2), curl=0.15), **arm('r', -0.34, 0.32, -0.16, pole=(-1.0, -0.2, -0.2), curl=0.15))
    if run:
        K.add(0.60, pel_f=0.10, pel_drop=0.03, sp_pitch=b['sp_pitch'] + D(8), pel_pitch=b['pel_pitch'] + D(3), sp_roll=0.0, pel_yaw=0.0,
              sp_yaw=D(-4), hd_pitch=D(8), hd_follow=0.2, l_shrug=D(6), r_shrug=D(6),
              **arm('l', 0.30, 0.10, -0.42, pole=(1.0, -0.4, -0.3), curl=0.3), **arm('r', -0.30, 0.10, -0.42, pole=(-1.0, -0.4, -0.3), curl=0.3))
        settle(K, 0.74, 0.86, 0.90)
        return action_clip(rig, name, stand, K.rows, 0.90, events={'catch_s': 0.24}, family=FAMILY, steps=K.steps)
    K.add(0.62, pel_f=0.10, pel_drop=0.02, sp_pitch=b['sp_pitch'] + D(4), pel_pitch=b['pel_pitch'], sp_roll=0.0, pel_yaw=0.0, sp_yaw=D(6),
          hd_pitch=D(4), hd_follow=0.2, l_shrug=D(8), r_shrug=D(8),
          **arm('l', 0.30, 0.06, -0.46, pole=(1.0, -0.4, -0.3), curl=0.3), **arm('r', -0.30, 0.06, -0.46, pole=(-1.0, -0.4, -0.3), curl=0.3))
    # The look back: over the left shoulder, down at the perfectly flat ground.
    look = dict(pel_f=0.0, pel_drop=0.0, sp_pitch=b['sp_pitch'] + D(3), sp_yaw=D(22), pel_yaw=D(6), hd_yaw=D(66), hd_pitch=D(30),
                hd_follow=0.0, l_shrug=D(10), r_shrug=D(4))
    K.rest(0.86, **look)
    K.rest(1.12, **look)
    K.rest(1.34)
    return action_clip(rig, name, stand, K.rows, 1.34, events={'catch_s': 0.24, 'look_s': 0.86}, family=FAMILY, steps=K.steps)


def jump_flail(rig, name):
    """The hop of a lad who is not sure his feet will come down again: arms wheel, legs pedal."""
    stand, K = _keys(rig)
    b = K.base
    K.add(0.0)
    K.add(0.07, sp_pitch=b['sp_pitch'] - D(9), hd_pitch=D(-16), hd_follow=0.3, l_shrug=D(20), r_shrug=D(16),
          lf_lift=0.10, rf_lift=0.03, lf_pitch=D(-28), rf_pitch=D(-34),
          **arm('l', 0.46, 0.08, 0.26, pole=(0.8, -0.8, 0.1), curl=0.0), **arm('r', -0.52, -0.04, 0.02, pole=(-0.6, -1.0, 0.2), curl=0.0))
    K.add(0.20, sp_pitch=b['sp_pitch'] - D(3), sp_yaw=D(15), sp_roll=D(8), hd_pitch=D(-8), hd_yaw=D(-10),
          lf_lift=0.17, lf_f=b['lf_f'] + 0.16, rf_lift=0.05, rf_f=b['rf_f'] - 0.13, rf_pitch=D(-44), lf_pitch=D(-10),
          **arm('l', 0.40, 0.36, -0.08, pole=(1.0, -0.4, 0.0)), **arm('r', -0.36, -0.20, 0.34, pole=(-0.8, -0.8, 0.0)))
    K.add(0.33, sp_pitch=b['sp_pitch'] + D(6), sp_yaw=D(-13), sp_roll=D(-7), hd_pitch=D(4), hd_yaw=D(8),
          lf_lift=0.06, lf_f=b['lf_f'] - 0.06, rf_lift=0.15, rf_f=b['rf_f'] + 0.13, rf_pitch=D(-12), lf_pitch=D(-40),
          **arm('l', 0.50, -0.12, 0.18, pole=(0.7, -0.9, 0.0)), **arm('r', -0.46, 0.30, -0.12, pole=(-1.0, -0.3, 0.0)))
    K.add(0.45, sp_pitch=b['sp_pitch'] + D(11), sp_yaw=0.0, sp_roll=0.0, hd_pitch=D(12), hd_yaw=0.0, l_shrug=D(10), r_shrug=D(10),
          lf_lift=0.03, lf_f=b['lf_f'] + 0.03, rf_lift=0.03, rf_f=b['rf_f'], rf_pitch=D(-16), lf_pitch=D(-16),
          **arm('l', 0.52, 0.10, -0.22, pole=(0.9, -0.5, -0.1), curl=0.1), **arm('r', -0.52, 0.10, -0.22, pole=(-0.9, -0.5, -0.1), curl=0.1))
    K.rest(0.58)
    return action_clip(rig, name, stand, K.rows, 0.58, family=FAMILY, blend_in=0.04, blend_out=0.1)


def land_stagger(rig, name):
    """He comes down off balance: the knees give, the trunk dives, two lunging catch steps, an
    over-correction backwards with the arms wheeling, and he is upright again."""
    stand, K = _keys(rig)
    b = K.base
    K.step('r', 0.10, 0.26, forward=0.42, height=0.07)
    K.step('l', 0.30, 0.46, forward=0.30, height=0.05)
    K.step('r', 0.66, 0.84, forward=0.0, height=0.05)
    K.step('l', 0.82, 0.99, forward=0.0, height=0.04)
    K.add(0.0)
    K.add(0.08, pel_drop=0.12, sp_pitch=b['sp_pitch'] + D(22), pel_pitch=b['pel_pitch'] + D(8), hd_pitch=D(10), hd_follow=0.5,
          l_shrug=D(12), r_shrug=D(12),
          **arm('l', 0.46, 0.20, -0.24, pole=(1.0, -0.5, 0.0), curl=0.05), **arm('r', -0.46, 0.20, -0.24, pole=(-1.0, -0.5, 0.0), curl=0.05))
    K.add(0.26, pel_f=0.22, pel_drop=0.09, sp_pitch=b['sp_pitch'] + D(36), pel_pitch=b['pel_pitch'] + D(12), sp_roll=D(-9), sp_yaw=D(12),
          hd_pitch=D(-2), hd_follow=0.7,
          **arm('l', 0.42, 0.02, 0.24, pole=(0.8, -0.8, 0.2)), **arm('r', -0.32, -0.24, -0.38, pole=(-1.0, -0.6, 0.0)))
    K.add(0.46, pel_f=0.30, pel_drop=0.05, sp_pitch=b['sp_pitch'] + D(12), pel_pitch=b['pel_pitch'] + D(4), sp_roll=D(7), sp_yaw=D(-11),
          hd_pitch=D(2), hd_follow=0.4,
          **arm('l', 0.46, 0.30, -0.20, pole=(1.0, -0.3, -0.1)), **arm('r', -0.50, 0.00, 0.12, pole=(-0.8, -0.8, 0.2)))
    # Too far: now he is going over backwards and the arms come forward to save him.
    K.add(0.64, pel_f=0.25, pel_drop=0.03, sp_pitch=b['sp_pitch'] - D(11), pel_pitch=b['pel_pitch'] - D(4), sp_roll=D(-3), sp_yaw=D(4),
          hd_pitch=D(-6), hd_follow=0.5, l_shrug=D(16), r_shrug=D(16),
          **arm('l', 0.26, 0.42, -0.08, pole=(1.0, -0.2, -0.3)), **arm('r', -0.26, 0.42, -0.14, pole=(-1.0, -0.2, -0.3)))
    K.add(0.84, pel_f=0.12, pel_drop=0.03, sp_pitch=b['sp_pitch'] + D(6), pel_pitch=b['pel_pitch'], sp_roll=0.0, sp_yaw=0.0,
          hd_pitch=D(6), hd_follow=0.2, l_shrug=D(6), r_shrug=D(6),
          **arm('l', 0.32, 0.12, -0.40, pole=(1.0, -0.4, -0.3), curl=0.25), **arm('r', -0.32, 0.12, -0.40, pole=(-1.0, -0.4, -0.3), curl=0.25))
    K.rest(1.02)
    K.rest(1.15)
    return action_clip(rig, name, stand, K.rows, 1.15, events={'land_s': 0.0}, family=FAMILY, steps=K.steps)


def land_faceplant(rig, name):
    """He goes down like a felled tree, face first, heels kicking up; lies there for a beat;
    looks up; pushes his backside into the air, walks his weight back over his feet, stands
    and beats the dirt off his front. The feet never leave the spot where he landed."""
    stand, K = _keys(rig)
    b = K.base
    flat = dict(pel_f=0.87, pel_drop=0.785, pel_pitch=b['pel_pitch'] + D(86), sp_pitch=D(-3), lf_pitch=D(-96), rf_pitch=D(-96),
                l_shrug=D(18), r_shrug=D(14))
    hands_down = {'l': (0.40, 1.40, 0.035), 'r': (-0.33, 1.52, 0.035)}
    K.add(0.0)
    K.add(0.10, pel_drop=0.10, sp_pitch=b['sp_pitch'] + D(20), pel_pitch=b['pel_pitch'] + D(8), hd_pitch=D(-6), hd_follow=0.4,
          **arm('l', 0.34, 0.40, -0.10, pole=(1.0, -0.4, 0.0), curl=0.0), **arm('r', -0.34, 0.40, -0.14, pole=(-1.0, -0.4, 0.0), curl=0.0))
    K.add(0.22, pel_f=0.36, pel_drop=0.30, pel_pitch=b['pel_pitch'] + D(46), sp_pitch=D(4), lf_pitch=D(-42), rf_pitch=D(-42),
          hd_pitch=D(24), hd_follow=0.6,
          **arm('l', 0.36, 0.44, -0.30, pole=(1.0, -0.2, 0.3)), **arm('r', -0.36, 0.46, -0.30, pole=(-1.0, -0.2, 0.3)))
    K.add(0.34, _world=hands_down, hd_pitch=D(80), hd_yaw=D(0), hd_follow=0.0, la_curl=0.05, ra_curl=0.05,
          **pole('l', 1.0, 0.1, 0.5), **pole('r', -1.0, 0.1, 0.5), **flat)
    # The bounce: heels up, one more than the other.
    K.add(0.44, lf_lift=0.24, rf_lift=0.13, pel_drop=0.795)
    K.add(0.62, lf_lift=0.0, rf_lift=0.0, pel_drop=0.795)
    K.hold(1.05)
    # He looks up, and to one side, to see who saw.
    K.add(1.25, hd_pitch=D(14), hd_yaw=D(28), sp_pitch=D(-9))
    K.hold(1.45)
    # Hands under the shoulders.
    K.add(1.62, _world={'l': (0.30, 1.16, 0.035), 'r': (-0.30, 1.16, 0.035)}, hd_pitch=D(40), hd_yaw=0.0, sp_pitch=D(-4),
          **pole('l', 1.0, -0.2, 0.6), **pole('r', -1.0, -0.2, 0.6))
    # Backside up, weight walked back onto the feet.
    K.add(1.88, _world={'l': (0.27, 0.98, 0.035), 'r': (-0.27, 0.98, 0.035)}, pel_f=0.34, pel_drop=0.33,
          pel_pitch=b['pel_pitch'] + D(74), sp_pitch=D(6), lf_pitch=D(-22), rf_pitch=D(-22), hd_pitch=D(70), l_shrug=D(8), r_shrug=D(8))
    K.add(2.10, pel_f=0.10, pel_drop=0.40, pel_pitch=b['pel_pitch'] + D(34), sp_pitch=b['sp_pitch'] + D(26), lf_pitch=0.0, rf_pitch=0.0,
          hd_pitch=D(30), hd_follow=0.3, l_shrug=0.0, r_shrug=0.0,
          **arm('l', 0.26, 0.34, -0.52, pole=(1.0, -0.3, -0.2), curl=0.2), **arm('r', -0.26, 0.34, -0.52, pole=(-1.0, -0.3, -0.2), curl=0.2))
    # Up, and two slaps at the dirt on his jerkin.
    K.add(2.36, pel_f=0.0, pel_drop=0.02, pel_pitch=b['pel_pitch'], sp_pitch=b['sp_pitch'] + D(8), hd_pitch=D(26), hd_follow=0.1,
          **arm('l', 0.24, 0.02, -0.52, pole=(1.0, -0.4, -0.3), curl=0.3), **arm('r', -0.06, 0.20, -0.20, pole=(-1.0, -0.2, -0.5), curl=0.0))
    K.add(2.48, **arm('r', -0.02, 0.19, -0.36, pole=(-1.0, -0.2, -0.5)))
    K.add(2.58, **arm('r', -0.10, 0.20, -0.22, pole=(-1.0, -0.2, -0.5)))
    K.add(2.70, hd_pitch=D(18), **arm('r', -0.04, 0.19, -0.38, pole=(-1.0, -0.2, -0.5)))
    K.rest(2.92)
    K.rest(3.0)
    clip = action_clip(rig, name, stand, K.rows, 3.0, events={'land_s': 0.0, 'impact_s': 0.34, 'up_s': 2.36, 'posture_off_s': 0.1, 'posture_on_s': 2.4}, family=FAMILY,
                       blend_in=0.04)
    clip['view_forward'] = 0.55
    clip['strip_every'] = 4
    return clip


def fidget_scratch(rig, name):
    """Weight on one leg, eyes on nothing, a good long scratch of the backside."""
    stand, K = _keys(rig)
    b = K.base
    lean = dict(pel_x=0.045, pel_roll=D(-4), pel_drop=0.008, sp_roll=D(5), sp_yaw=D(-10), hd_yaw=D(24), hd_pitch=D(-4), r_shrug=D(6))
    at = lambda z, x=-0.13: arm('r', x, -0.105, z, pole=(-0.8, -1.0, 0.3), curl=0.75, bend=D(-25))
    K.add(0.0)
    K.add(0.55, **lean, **at(-0.43))
    t = 0.55
    for i in range(4):
        K.add(t + 0.13, **at(-0.475, -0.15))
        K.add(t + 0.26, **at(-0.415, -0.12))
        t += 0.26
    K.add(t + 0.16, **at(-0.47, -0.14))
    K.add(t + 0.45, hd_yaw=D(-8), hd_pitch=D(8), **at(-0.45))
    K.rest(t + 0.95)
    K.rest(t + 1.05)
    return action_clip(rig, name, stand, K.rows, t + 1.05, family=FAMILY, blend_in=0.2, blend_out=0.25)


def fidget_scuff(rig, name):
    """Eyes down, one hand rubbing the back of his neck, the toe of a boot grinding at the dirt.

    Played by an unsure Dink only, so always UNDER the timid stoop (19 degrees of spine, 25 of neck and head): the clip's
    own nod is small. With the 30 degrees it had, the game (23 Nov 2026) showed him bent double with his head hanging
    at 80 degrees."""
    stand, K = _keys(rig)
    b = K.base
    K.step('r', 0.45, 0.72, forward=0.24, height=0.035)
    K.step('r', 1.95, 2.25, forward=0.0, height=0.035)
    neck = lambda z: arm('l', 0.07, -0.085, z, pole=(1.0, -0.5, 0.5), curl=0.35)
    K.add(0.0)
    K.add(0.45, pel_x=0.03, sp_pitch=b['sp_pitch'] + D(2), hd_pitch=D(9), hd_yaw=D(-8), l_shrug=D(12), r_shrug=D(8), **neck(0.19))
    K.add(0.78, rf_pitch=D(-26), rf_yaw=b['rf_yaw'] + D(14), **neck(0.15))
    K.add(1.02, rf_pitch=D(-30), rf_yaw=b['rf_yaw'] - D(18), **neck(0.20))
    K.add(1.26, rf_pitch=D(-26), rf_yaw=b['rf_yaw'] + D(16), **neck(0.15))
    K.add(1.50, rf_pitch=D(-30), rf_yaw=b['rf_yaw'] - D(16), **neck(0.20))
    K.add(1.74, rf_pitch=D(-24), rf_yaw=b['rf_yaw'] + D(10), **neck(0.16))
    K.add(1.95, rf_pitch=D(-10), rf_yaw=b['rf_yaw'], hd_pitch=D(6), **neck(0.18))
    K.rest(2.55)
    K.rest(2.65)
    return action_clip(rig, name, stand, K.rows, 2.65, family=FAMILY, blend_in=0.2, blend_out=0.25, steps=K.steps)


def fidget_nose(rig, name):
    """A sniff, and the nose dragged along the whole length of a sleeve."""
    stand, K = _keys(rig)
    b = K.base
    sleeve = lambda x, z=0.165: arm('l', x, 0.150, z, pole=(1.0, 0.5, 0.1), curl=0.4, pron=D(40))
    K.add(0.0)
    K.add(0.22, hd_pitch=D(-10), l_shrug=D(8), r_shrug=D(8))                       # the sniff
    K.add(0.55, hd_pitch=D(6), hd_yaw=D(8), sp_yaw=D(-6), l_shrug=D(14), **sleeve(0.13, 0.15))
    K.add(0.95, hd_pitch=D(2), hd_yaw=D(-14), hd_roll=D(5), sp_yaw=D(4), **sleeve(-0.10))
    K.add(1.15, hd_yaw=D(-10), **sleeve(-0.12, 0.14))
    K.add(1.50, hd_pitch=D(-4), hd_yaw=D(20), hd_roll=0.0, sp_yaw=0.0, l_shrug=D(4), **arm('l', 0.26, 0.12, -0.34, pole=(1.0, -0.3, -0.3), curl=0.3, pron=0.0))
    K.add(1.80, hd_yaw=D(-16), hd_pitch=D(2))                                       # did anyone see
    K.rest(2.15)
    K.rest(2.25)
    return action_clip(rig, name, stand, K.rows, 2.25, family=FAMILY, blend_in=0.15, blend_out=0.25)


def fidget_proud(rig, name):
    """The hero's idle: shoulders rolled back, fists closed and opened, a slow look over the land."""
    stand, K = _keys(rig)
    b = K.base
    K.add(0.0)
    K.add(0.40, l_shrug=D(13), r_shrug=D(13), l_protract=D(6), r_protract=D(6), sp_pitch=b['sp_pitch'] + D(2), la_curl=0.95, ra_curl=0.95)
    K.add(0.80, l_shrug=D(9), r_shrug=D(9), l_protract=D(-13), r_protract=D(-13), sp_pitch=b['sp_pitch'] - D(7), hd_pitch=D(-4))
    K.add(1.15, l_shrug=D(-2), r_shrug=D(-2), l_protract=D(-8), r_protract=D(-8), sp_pitch=b['sp_pitch'] - D(5), hd_yaw=D(-30), hd_pitch=D(-3),
          sp_yaw=D(-8), la_curl=0.4, ra_curl=0.4)
    K.hold(1.60)
    K.add(2.25, hd_yaw=D(28), sp_yaw=D(8))
    K.hold(2.60)
    K.rest(3.10)
    K.rest(3.2)
    return action_clip(rig, name, stand, K.rows, 3.2, family=FAMILY, blend_in=0.2, blend_out=0.3)


def sword_wild(rig, name, kind):
    """The same three cuts as Sword_* swung by someone who has only ever swung a feed bucket:
    a wind-up from behind the ear, contact at the same instant (0.175 s, gameplay owns it), and
    then the blade keeps going and takes him with it: he spins past the target, catches himself
    with a stumbling step and wobbles back to his feet."""
    stand, K = _keys(rig, 0.3)
    b = K.base
    off = arm('l', 0.36, -0.10, -0.16, pole=(0.9, -0.6, 0.1), curl=0.1)        # the off arm flaps for balance
    K.add(0.0)
    if kind == 'slash1':
        K.step('l', 0.02, 0.14, forward=0.26, height=0.05)
        K.step('r', 0.30, 0.50, forward=0.34, lateral=b['rf_x'] + 0.10, height=0.07)   # dragged round by the swing
        K.step('r', 0.74, 0.92, forward=0.0, lateral=b['rf_x'], height=0.05)
        K.step('l', 0.90, 1.06, forward=0.0, height=0.04)
        K.add(0.085, pel_x=-0.05, pel_drop=0.03, pel_yaw=D(-22), sp_yaw=D(-38), sp_roll=D(-8), sp_pitch=b['sp_pitch'] - D(8), hd_pitch=D(2),
              r_shrug=D(20), l_shrug=D(10), **arm('r', -0.26, -0.20, 0.36, pole=(-1.0, -0.6, 0.2), curl=1.0), **off)
        K.add(0.135, pel_yaw=D(4), sp_yaw=D(0), pel_f=0.08, **arm('r', -0.44, 0.24, 0.26, pole=(-1.0, -0.3, -0.2)))
        K.add(H0, _world={'r': (-0.04, 0.74, 1.24)}, pel_f=0.16, pel_x=0.03, pel_drop=0.05, pel_yaw=D(26), sp_yaw=D(32),
              pel_pitch=b['pel_pitch'] + D(7), sp_pitch=b['sp_pitch'] + D(14), sp_roll=D(7), rf_pitch=D(-36), hd_pitch=D(12),
              **pole('r', -0.8, -0.2, -0.6), **arm('l', 0.40, -0.16, -0.06, pole=(0.9, -0.6, 0.2), curl=0.1))
        K.hold(H1)
        K.add(0.30, pel_yaw=D(52), sp_yaw=D(70), sp_pitch=b['sp_pitch'] + D(30), pel_drop=0.10, sp_roll=D(12), hd_follow=0.6,
              **arm('r', 0.30, 0.10, -0.40, pole=(-0.6, 0.6, -0.4)), **arm('l', 0.30, -0.30, 0.10, pole=(1.0, -0.5, 0.3)))
        K.add(0.50, pel_yaw=D(40), sp_yaw=D(50), sp_pitch=b['sp_pitch'] + D(34), pel_f=0.26, pel_drop=0.12, pel_x=0.06, rf_pitch=0.0,
              **arm('r', 0.34, -0.06, -0.44, pole=(-0.5, 0.8, -0.3)), **arm('l', 0.46, 0.20, 0.00, pole=(1.0, -0.4, 0.2)))
        K.add(0.72, pel_yaw=D(12), sp_yaw=D(10), sp_pitch=b['sp_pitch'] - D(6), pel_f=0.20, pel_drop=0.04, pel_x=-0.03, sp_roll=D(-8),
              hd_pitch=D(-2), hd_follow=0.3, r_shrug=D(8),
              **arm('r', -0.30, 0.24, -0.30, pole=(-1.0, -0.3, -0.4)), **arm('l', 0.44, 0.10, -0.16, pole=(1.0, -0.4, 0.0)))
    elif kind == 'slash2':
        K.step('r', 0.02, 0.14, forward=0.24, height=0.05)
        K.step('l', 0.30, 0.50, forward=0.30, lateral=b['lf_x'] - 0.08, height=0.07)
        K.step('l', 0.74, 0.92, forward=0.0, lateral=b['lf_x'], height=0.05)
        K.step('r', 0.90, 1.06, forward=0.0, height=0.04)
        K.add(0.085, pel_x=0.05, pel_drop=0.03, pel_yaw=D(20), sp_yaw=D(40), sp_roll=D(7), hd_pitch=D(6), hd_yaw=D(-6), r_shrug=D(16),
              **arm('r', 0.26, 0.10, 0.20, pole=(-0.4, 0.4, -1.0), curl=1.0), **arm('l', 0.40, -0.10, -0.14, pole=(0.9, -0.6, 0.1), curl=0.1))
        K.add(0.135, pel_yaw=D(2), sp_yaw=D(8), pel_f=0.08, **arm('r', 0.08, 0.40, 0.10, pole=(-0.9, 0.0, -0.6)))
        K.add(H0, _world={'r': (-0.06, 0.63, 1.30)}, pel_f=0.15, pel_x=-0.03, pel_drop=0.045, pel_yaw=D(-16), sp_yaw=D(-24),
              pel_pitch=b['pel_pitch'] + D(5), sp_pitch=b['sp_pitch'] + D(10), lf_pitch=D(-32), hd_pitch=D(8),
              **pole('r', -1.0, -0.3, -0.1), **arm('l', 0.34, 0.06, -0.20, pole=(0.9, -0.4, -0.2), curl=0.1))
        K.hold(H1)
        K.add(0.30, pel_yaw=D(-44), sp_yaw=D(-66), sp_pitch=b['sp_pitch'] + D(4), sp_roll=D(-12), pel_drop=0.07, hd_follow=0.6,
              **arm('r', -0.50, -0.14, 0.14, pole=(-0.4, -1.0, 0.0)), **arm('l', 0.20, 0.34, -0.10, pole=(1.0, -0.2, -0.2)))
        K.add(0.50, pel_yaw=D(-36), sp_yaw=D(-52), sp_pitch=b['sp_pitch'] - D(8), pel_f=0.22, pel_drop=0.09, pel_x=-0.06, lf_pitch=0.0,
              **arm('r', -0.46, -0.26, 0.00, pole=(-0.4, -1.0, 0.2)), **arm('l', 0.16, 0.42, 0.00, pole=(1.0, -0.2, -0.2)))
        K.add(0.72, pel_yaw=D(-10), sp_yaw=D(-8), sp_pitch=b['sp_pitch'] + D(14), pel_f=0.18, pel_drop=0.04, pel_x=0.03, sp_roll=D(7),
              hd_pitch=D(8), hd_follow=0.3, r_shrug=D(6),
              **arm('r', -0.34, 0.20, -0.30, pole=(-1.0, -0.3, -0.4)), **arm('l', 0.40, 0.14, -0.24, pole=(1.0, -0.4, -0.1)))
    else:
        K.step('l', 0.02, 0.14, forward=0.28, height=0.05)
        K.step('r', 0.32, 0.50, forward=0.26, height=0.06)
        K.step('r', 0.76, 0.93, forward=0.0, height=0.05)
        K.step('l', 0.91, 1.06, forward=0.0, height=0.04)
        # Both hands, right over the top, bending over backwards to get there.
        K.add(0.085, pel_x=-0.02, pel_drop=0.0, pel_yaw=D(-6), sp_yaw=D(-8), sp_pitch=b['sp_pitch'] - D(20), pel_pitch=b['pel_pitch'] - D(5),
              hd_pitch=D(-14), hd_follow=0.4, r_shrug=D(22), l_shrug=D(22),
              **arm('r', -0.10, -0.14, 0.50, pole=(-0.9, 0.5, 0.2), curl=1.0), **arm('l', 0.06, -0.12, 0.46, pole=(0.9, 0.5, 0.2), curl=0.9))
        K.add(0.135, pel_yaw=D(2), sp_yaw=D(2), sp_pitch=b['sp_pitch'] - D(2), pel_f=0.08,
              **arm('r', -0.10, 0.26, 0.44, pole=(-0.9, 0.2, -0.3)), **arm('l', 0.04, 0.24, 0.40, pole=(0.9, 0.2, -0.3)))
        K.add(H0, _world={'r': (-0.05, 0.76, 1.28)}, pel_f=0.16, pel_x=0.02, pel_drop=0.06, pel_yaw=D(10), sp_yaw=D(10),
              pel_pitch=b['pel_pitch'] + D(8), sp_pitch=b['sp_pitch'] + D(20), rf_pitch=D(-34), hd_pitch=D(12), hd_follow=0.2,
              r_shrug=D(8), l_shrug=D(8), **pole('r', -0.7, -0.2, -0.8), **arm('l', 0.10, 0.52, -0.14, pole=(0.9, -0.2, -0.6), curl=0.9))
        K.hold(H1)
        # The blade buries itself in the ground and he folds over it.
        K.add(0.30, pel_drop=0.16, sp_pitch=b['sp_pitch'] + D(48), pel_pitch=b['pel_pitch'] + D(16), pel_yaw=D(12), sp_yaw=D(12), hd_follow=0.7,
              **arm('r', -0.08, 0.36, -0.62, pole=(-0.9, -0.3, -0.3)), **arm('l', 0.10, 0.36, -0.58, pole=(0.9, -0.3, -0.3)))
        K.add(0.50, pel_f=0.24, pel_drop=0.14, sp_pitch=b['sp_pitch'] + D(42), pel_pitch=b['pel_pitch'] + D(13), rf_pitch=0.0,
              **arm('r', -0.10, 0.32, -0.60, pole=(-0.9, -0.3, -0.3)), **arm('l', 0.34, 0.10, -0.30, pole=(1.0, -0.4, 0.0), curl=0.1))
        K.add(0.72, pel_f=0.20, pel_drop=0.04, sp_pitch=b['sp_pitch'] - D(8), pel_pitch=b['pel_pitch'] - D(2), pel_yaw=D(4), sp_yaw=D(-6),
              sp_roll=D(-6), hd_pitch=D(-4), hd_follow=0.3, r_shrug=D(10), l_shrug=D(10),
              **arm('r', -0.30, 0.22, -0.26, pole=(-1.0, -0.3, -0.4)), **arm('l', 0.44, 0.06, -0.10, pole=(1.0, -0.5, 0.1), curl=0.1))
    K.add(0.92, pel_yaw=0.0, sp_yaw=D(3), sp_pitch=b['sp_pitch'] + D(5), pel_f=0.08, pel_drop=0.02, pel_x=0.0, sp_roll=D(3),
          pel_pitch=b['pel_pitch'], hd_pitch=b['hd_pitch'], hd_follow=0.1, r_shrug=D(3), l_shrug=D(3), rf_pitch=0.0, lf_pitch=0.0,
          **arm('r', -0.26, 0.14, -0.40, pole=(-1.0, -0.3, -0.5), curl=0.9), **arm('l', 0.30, 0.06, -0.40, pole=(1.0, -0.4, -0.3), curl=0.3))
    K.rest(1.10)
    K.rest(1.16)
    return action_clip(rig, name, stand, K.rows, 1.16, events=EVENTS, family=FAMILY, steps=K.steps)


def makers(rig):
    m = {}
    m['Posture_Timid'] = lambda: additive_clip(rig, 'Posture_Timid', 'timid')
    m['Posture_Confident'] = lambda: additive_clip(rig, 'Posture_Confident', 'confident')
    m['RunArms_Timid'] = lambda: additive_clip(rig, 'RunArms_Timid', 'runarms')
    m['Trip_Walk'] = lambda: trip(rig, 'Trip_Walk', False)
    m['Trip_Run'] = lambda: trip(rig, 'Trip_Run', True)
    m['Jump_Timid'] = lambda: jump_flail(rig, 'Jump_Timid')
    m['Botch_Stagger'] = lambda: land_stagger(rig, 'Botch_Stagger')
    m['Botch_Faceplant'] = lambda: land_faceplant(rig, 'Botch_Faceplant')
    m['Fidget_Scratch'] = lambda: fidget_scratch(rig, 'Fidget_Scratch')
    m['Fidget_Scuff'] = lambda: fidget_scuff(rig, 'Fidget_Scuff')
    m['Fidget_Nose'] = lambda: fidget_nose(rig, 'Fidget_Nose')
    m['Fidget_Proud'] = lambda: fidget_proud(rig, 'Fidget_Proud')
    m['Sword_Slash_1_Timid'] = lambda: sword_wild(rig, 'Sword_Slash_1_Timid', 'slash1')
    m['Sword_Slash_2_Timid'] = lambda: sword_wild(rig, 'Sword_Slash_2_Timid', 'slash2')
    m['Sword_Chop_Timid'] = lambda: sword_wild(rig, 'Sword_Chop_Timid', 'chop')
    m['Preview_Posture'] = lambda: preview_posture(rig)
    for c, tag in ((0.0, 'C0'), (1.0, 'C1')):
        m['Preview_Stagger_' + tag] = lambda c=c, tag=tag: preview_over(rig, 'Preview_Stagger_' + tag, land_stagger(rig, 'x'), c, 4)
    # Preview_<clip>_C0: an action clip as the game shows it on an unsure Dink (the timid stoop over it; the sword cuts keep 0.4 of it,
    # FDinkMannerMaths::PostureShareFor). Review strips only.
    for n in [k for k in m if not k.startswith(('Posture_', 'RunArms_', 'Preview_'))]:
        m['Preview_%s_C0' % n] = lambda n=n: preview_over(rig, 'Preview_%s_C0' % n, m[n](), 0.0, 6, share=0.4 if n.startswith('Sword_') else 1.0)
    return m
