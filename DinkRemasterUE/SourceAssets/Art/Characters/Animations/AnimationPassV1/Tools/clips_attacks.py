"""Attack, hurt and stumble clips. makers(rig) -> {name: callable returning a clip dict}.

Gameplay owns the timing: the hit lands 0.175 s after the clip starts and the next attack may
start at 0.4 s. Everything after 0.4 s is cosmetic and may be interrupted.
"""
import math
from attack_tools import D, Keys, arm, pole, action_clip, state_from_pose, apply_steps, build_pose, fit_held, fit_point, world_to_chest
from clips_locomotion import stand_pose

HIT = 0.175
H0, H1 = 10 / 60.0, 11 / 60.0   # the two frames around the hit: both hold the contact pose
EVENTS = {'hit_s': HIT, 'lock_s': 0.4}
PRON = D(70)                     # left forearm roll that turns the knuckles up at contact
PRON_R = D(70)
CAST_BEND = D(-55)              # wrist cocked back so the open palm faces the target
WIDE = 0.075                     # how far the lead foot steps out to the side for the fighting stance


def _keys(rig, c):
    stand = stand_pose(rig, c)
    return stand, Keys(rig, state_from_pose(rig, stand))


def settle(K, t_mid, t_end, duration, **mid_changes):
    """Cosmetic return to the stand: halfway key, then the stand held to the end."""
    mid = {k: 0.5 * (v + K.base[k]) for k, v in K.cur.items()}
    mid.update(mid_changes)
    K.add(t_mid, **mid)
    K.rest(t_end)
    if duration > t_end:
        K.rest(duration)


def jab(rig, c, name):
    stand, K = _keys(rig, c)
    t = 1.0 - c                      # timid share
    b = K.base
    K.step('l', 0.03, 0.155, forward=0.38 + 0.03 * t, lateral=b['lf_x'] + WIDE, height=0.05)
    K.step('l', 0.47, 0.66, forward=0.0, lateral=b['lf_x'], height=0.045)
    K.add(0.0)
    # Anticipation: weight settles onto the rear leg, lead shoulder draws back, hands come up.
    K.add(0.085, pel_x=-0.03, pel_drop=0.015 + 0.01 * t, pel_yaw=D(7), sp_yaw=D(9 + 6 * t), sp_pitch=b['sp_pitch'] + D(3),
          hd_pitch=D(8 + 4 * t), hd_yaw=D(-5 * t), l_shrug=D(6 + 8 * t), r_shrug=D(4 + 8 * t),
          **arm('l', 0.16 + 0.05 * t, 0.20 - 0.06 * t, -0.03 - 0.06 * t, pole=(0.45 + 0.4 * t, -0.2, -1.0), curl=1.0),
          **arm('r', -0.11 - 0.07 * t, 0.17 - 0.07 * t, 0.05 - 0.22 * t, pole=(-0.4 - 0.3 * t, -0.2, -1.0), curl=1.0 - 0.3 * t))
    # Contact: hips have turned, lead foot is down, weight over it, arm straight behind the knuckles.
    contact = dict(pel_f=0.22 + 0.03 * t, pel_x=0.05, pel_drop=0.035 + 0.015 * t, pel_yaw=D(-18 - 4 * t), pel_pitch=b['pel_pitch'] + D(6 + 3 * t),
                   sp_yaw=D(-28 - 4 * t), sp_pitch=b['sp_pitch'] * 0.5 + D(14 + 4 * t), sp_roll=D(-3 - 4 * t),
                   rf_pitch=D(-30 - 4 * t), hd_pitch=D(9 + 5 * t), hd_yaw=D(-12 * t), hd_roll=D(-4 * t), hd_follow=0.1 + 0.1 * t,
                   l_protract=D(18), l_shrug=D(8 + 10 * t), r_shrug=D(4 + 10 * t),
                   la_pron=PRON, la_curl=1.0, **pole('l', 0.7 + 0.2 * t, 0.0, -0.6 + 0.5 * t))
    rear = arm('r', -0.10, 0.17, 0.06, pole=(-0.4, -0.2, -1.0)) if c > 0.5 else \
        arm('r', -0.30, -0.16, -0.20, pole=(-0.9, -0.6, -0.2), curl=0.6)
    K.add(H0, _world={'l': (0.06, 0.93 + 0.02 * t, 1.36 - 0.05 * t)}, **contact, **rear)
    K.hold(H1)
    # Follow-through and retraction
    K.add(0.27, pel_yaw=D(-9), sp_yaw=D(-12), sp_pitch=b['sp_pitch'] * 0.6 + D(8 + 8 * t), pel_f=0.20 + 0.04 * t,
          la_pron=PRON * 0.5, l_protract=D(5), hd_yaw=D(-6 * t), hd_roll=0.0,
          **arm('l', 0.13, 0.36, -0.02, pole=(0.5 + 0.3 * t, -0.2, -1.0)))
    K.add(0.40, pel_yaw=D(-6), sp_yaw=D(-7), sp_pitch=b['sp_pitch'] * 0.7 + D(5 + 6 * t), pel_f=0.17 + 0.03 * t, pel_drop=0.03 + 0.01 * t, pel_x=0.04,
          pel_pitch=b['pel_pitch'] + D(2), rf_pitch=D(-14), la_pron=0.0, l_protract=0.0, hd_yaw=0.0, hd_pitch=D(6 + 6 * t),
          l_shrug=D(4 + 6 * t), r_shrug=D(3 + 6 * t),
          **arm('l', 0.15 + 0.03 * t, 0.24 - 0.05 * t, 0.0 - 0.08 * t, pole=(0.45 + 0.3 * t, -0.2, -1.0)),
          **arm('r', -0.11 - 0.05 * t, 0.17 - 0.05 * t, 0.05 - 0.16 * t, pole=(-0.4 - 0.2 * t, -0.2, -1.0), curl=1.0 - 0.2 * t))
    settle(K, 0.56, 0.72, 0.80, rf_pitch=0.0, pel_f=0.08, pel_x=0.0)
    return action_clip(rig, name, stand, K.rows, 0.80, events=EVENTS, steps=K.steps)


def cross(rig, c, name):
    stand, K = _keys(rig, c)
    t = 1.0 - c
    b = K.base
    dur = 0.80 + 0.10 * t
    K.step('l', 0.02, 0.135, forward=0.36 + 0.03 * t, lateral=b['lf_x'] + WIDE, height=0.045)
    if t > 0.5:
        # Over-commits: the rear foot has to come through to catch him, then he shuffles back.
        K.step('r', 0.22, 0.37, forward=0.30, height=0.05)
        K.step('r', 0.50, 0.66, forward=0.0, height=0.04)
        K.step('l', 0.62, 0.80, forward=0.0, lateral=b['lf_x'], height=0.04)
    else:
        K.step('l', 0.47, 0.66, forward=0.0, lateral=b['lf_x'], height=0.045)
    K.add(0.0)
    # Coil: weight onto the rear leg, rear hip and shoulder drawn back, fist chambered.
    chamber = arm('r', -0.15, 0.11, 0.03, pole=(-0.5, -0.4, -1.0), curl=1.0) if c > 0.5 else \
        arm('r', -0.36, -0.12, -0.02, pole=(-1.0, -0.5, 0.1), curl=1.0)
    lead = arm('l', 0.12, 0.27, 0.01, pole=(0.45, -0.2, -1.0), curl=1.0) if c > 0.5 else \
        arm('l', 0.22, 0.20, -0.14, pole=(0.8, -0.2, -0.8), curl=0.7)
    K.add(0.085, pel_x=-0.035, pel_drop=0.015 + 0.01 * t, pel_yaw=D(-12 - 4 * t), sp_yaw=D(-13 - 10 * t), sp_pitch=b['sp_pitch'] + D(3),
          hd_pitch=D(8 + 6 * t), hd_yaw=D(8 * t), r_shrug=D(6 + 10 * t), l_shrug=D(4 + 8 * t), **chamber, **lead)
    # Contact: rear hip and shoulder through, rear heel up and turned, weight on the lead leg.
    guard = arm('l', 0.10, 0.15, 0.07, pole=(0.45, -0.3, -1.0)) if c > 0.5 else \
        arm('l', 0.34, -0.14, -0.22, pole=(0.9, -0.6, -0.2), curl=0.6)
    K.add(H0, _world={'r': (0.02, 0.97 - 0.05 * t, 1.35 - 0.05 * t)},
          pel_f=0.23 + 0.03 * t, pel_x=0.07, pel_drop=0.035 + 0.02 * t, pel_yaw=D(30 + 4 * t), pel_pitch=b['pel_pitch'] + D(5 + 4 * t),
          sp_yaw=D(30 + 6 * t), sp_pitch=b['sp_pitch'] * 0.5 + D(10 + 9 * t), sp_roll=D(4 + 4 * t),
          rf_pitch=D(-40), rf_yaw=b['rf_yaw'] - D(28), hd_pitch=D(9 + 10 * t), hd_yaw=D(24 * t), hd_roll=D(8 * t), hd_follow=0.1 + 0.3 * t,
          r_protract=D(12), r_shrug=D(8 + 10 * t), l_shrug=D(4 + 10 * t), ra_pron=PRON_R, ra_curl=1.0,
          **pole('r', -0.7 - 0.2 * t, 0.0, -0.6 + 0.5 * t), **guard)
    K.hold(H1)
    K.add(0.27, pel_yaw=D(22 + 14 * t), sp_yaw=D(20 + 14 * t), sp_pitch=b['sp_pitch'] * 0.6 + D(8 + 11 * t), pel_f=0.22 + 0.08 * t,
          pel_drop=0.035 + 0.035 * t, ra_pron=PRON_R * 0.5, r_protract=D(5), hd_yaw=D(12 * t), hd_roll=0.0,
          **(arm('r', -0.14, 0.34, -0.02, pole=(-0.5, -0.2, -1.0)) if c > 0.5 else arm('r', 0.02, 0.40, -0.22, pole=(-0.8, -0.2, -0.6))))
    K.add(0.40, pel_yaw=D(8 + 10 * t), sp_yaw=D(8 + 6 * t), sp_pitch=b['sp_pitch'] * 0.7 + D(5 + 9 * t), pel_f=0.17 + 0.10 * t,
          pel_drop=0.03 + 0.02 * t, pel_x=0.05, pel_pitch=b['pel_pitch'] + D(2), rf_pitch=D(-16) * c, rf_yaw=b['rf_yaw'] - D(10) * c,
          ra_pron=0.0, r_protract=0.0, hd_yaw=0.0, hd_pitch=D(6 + 8 * t), r_shrug=D(4 + 6 * t), l_shrug=D(3 + 6 * t),
          **arm('r', -0.12 - 0.04 * t, 0.18 - 0.02 * t, 0.05 - 0.18 * t, pole=(-0.4 - 0.3 * t, -0.2, -1.0), curl=1.0 - 0.2 * t),
          **arm('l', 0.14 + 0.06 * t, 0.24 - 0.10 * t, 0.01 - 0.18 * t, pole=(0.45 + 0.3 * t, -0.2, -1.0), curl=1.0 - 0.3 * t))
    settle(K, 0.56 + 0.06 * t, 0.72 + 0.10 * t, dur, rf_pitch=0.0, rf_yaw=b['rf_yaw'], pel_f=0.08 + 0.04 * t, pel_x=0.0, pel_drop=0.02 + 0.03 * t)
    return action_clip(rig, name, stand, K.rows, dur, events=EVENTS, steps=K.steps)


def hook(rig, name):
    """Combo hit 3, confident: a tight lead hook thrown with the hips, elbow level with the fist."""
    stand, K = _keys(rig, 1.0)
    b = K.base
    K.step('l', 0.02, 0.13, forward=0.30, lateral=b['lf_x'] + WIDE, height=0.04)
    K.step('l', 0.50, 0.68, forward=0.0, lateral=b['lf_x'], height=0.04)
    K.add(0.0)
    K.add(0.09, pel_x=0.03, pel_drop=0.03, pel_yaw=D(16), sp_yaw=D(20), sp_pitch=b['sp_pitch'] + D(5), sp_roll=D(5),
          hd_pitch=D(8), l_shrug=D(8), r_shrug=D(4),
          **arm('l', 0.33, 0.06, -0.06, pole=(1.0, -0.6, -0.2), curl=1.0, pron=PRON * 0.5),
          **arm('r', -0.10, 0.17, 0.06, pole=(-0.4, -0.2, -1.0), curl=1.0))
    K.add(0.135, pel_yaw=D(-4), sp_yaw=D(-2), pel_f=0.12, pel_pitch=b['pel_pitch'] + D(4),
          **arm('l', 0.34, 0.20, -0.02, pole=(1.0, -0.6, 0.1), pron=PRON * 0.7))
    K.add(H0, _world={'l': (-0.03, 0.70, 1.37)}, pel_x=0.05, pel_f=0.19, pel_drop=0.04, rf_pitch=D(-24), pel_yaw=D(-30), sp_yaw=D(-36),
          pel_pitch=b['pel_pitch'] + D(6), sp_pitch=b['sp_pitch'] + D(13), sp_roll=D(-4), lf_pitch=D(-30), lf_yaw=b['lf_yaw'] - D(34), hd_pitch=D(9),
          l_shrug=D(12), la_pron=PRON * 0.8, **pole('l', 1.0, -0.5, 0.25))
    K.hold(H1)
    K.add(0.26, pel_yaw=D(-38), sp_yaw=D(-44), pel_x=0.04, sp_roll=D(-6),
          **arm('l', -0.16, 0.26, -0.03, pole=(1.0, 0.2, 0.0)))
    K.add(0.40, pel_yaw=D(-8), sp_yaw=D(-8), pel_x=0.03, pel_f=0.15, pel_drop=0.03, rf_pitch=D(-12), sp_roll=0.0, sp_pitch=b['sp_pitch'] + D(5),
          pel_pitch=b['pel_pitch'] + D(2),
          lf_pitch=0.0, lf_yaw=b['lf_yaw'], l_shrug=D(4), la_pron=0.0,
          **arm('l', 0.15, 0.24, 0.0, pole=(0.45, -0.2, -1.0)))
    settle(K, 0.56, 0.72, 0.80, pel_f=0.07, rf_pitch=0.0, pel_x=0.0)
    return action_clip(rig, name, stand, K.rows, 0.80, events=EVENTS, steps=K.steps)


def haymaker(rig, name):
    """Combo hit 3, timid: a wide untrained right that over-rotates him and needs a catch step."""
    stand, K = _keys(rig, 0.0)
    b = K.base
    K.step('l', 0.02, 0.13, forward=0.34, lateral=b['lf_x'] + WIDE, height=0.045)
    K.step('r', 0.22, 0.38, forward=0.36, lateral=b['rf_x'] + 0.05, height=0.06)
    K.step('r', 0.54, 0.70, forward=0.0, lateral=b['rf_x'], height=0.04)
    K.step('l', 0.66, 0.84, forward=0.0, lateral=b['lf_x'], height=0.04)
    K.add(0.0)
    # Wind-up: the shoulder and hip turn away and the fist drops back beside the hip, elbow out.
    K.add(0.085, pel_x=-0.04, pel_drop=0.025, pel_yaw=D(-18), sp_yaw=D(-24), sp_pitch=b['sp_pitch'] + D(3), sp_roll=D(-4),
          hd_pitch=D(11), hd_yaw=D(-4), r_shrug=D(14), l_shrug=D(9),
          **arm('r', -0.40, -0.06, -0.20, pole=(-0.9, -0.7, 0.0), curl=1.0),
          **arm('l', 0.24, 0.22, -0.12, pole=(0.8, -0.2, -0.8), curl=0.6))
    # The arm comes round wide at shoulder height, elbow only partly bent.
    K.add(0.135, pel_yaw=D(6), sp_yaw=D(4), pel_x=0.0, pel_f=0.12,
          **arm('r', -0.50, 0.24, -0.04, pole=(-0.8, -0.7, 0.25), pron=PRON_R * 0.5))
    K.add(H0, _world={'r': (0.03, 1.02, 1.33)}, pel_f=0.24, pel_x=0.07, pel_drop=0.05, pel_yaw=D(34), pel_pitch=b['pel_pitch'] + D(7),
          sp_yaw=D(40), sp_pitch=b['sp_pitch'] * 0.5 + D(15), sp_roll=D(7), rf_pitch=D(-38), rf_yaw=b['rf_yaw'] - D(26),
          hd_pitch=D(14), hd_yaw=D(14), hd_roll=D(5), hd_follow=0.25, r_shrug=D(18), l_shrug=D(12), ra_pron=PRON_R * 0.8,
          **pole('r', -1.0, -0.4, 0.3), **arm('l', 0.36, -0.14, -0.20, pole=(0.9, -0.6, -0.2), curl=0.5))
    K.hold(H1)
    # The swing carries on across the body and drags him after it.
    K.add(0.29, pel_yaw=D(52), sp_yaw=D(50), sp_pitch=b['sp_pitch'] * 0.5 + D(25), sp_roll=D(9), pel_f=0.34, pel_x=0.07, pel_drop=0.07,
          rf_pitch=0.0, rf_yaw=b['rf_yaw'], hd_yaw=D(10), hd_roll=D(3),
          **arm('r', 0.16, 0.32, -0.22, pole=(-1.0, -0.2, -0.1), pron=PRON_R * 0.4),
          **arm('l', 0.38, -0.20, -0.10, pole=(0.9, -0.6, 0.0)))
    K.add(0.41, pel_yaw=D(26), sp_yaw=D(16), sp_pitch=b['sp_pitch'] * 0.7 + D(17), sp_roll=D(2), pel_f=0.33, pel_x=0.04, pel_drop=0.05,
          pel_pitch=b['pel_pitch'] + D(4), hd_yaw=0.0, hd_pitch=D(13), hd_follow=0.2, r_shrug=D(10), l_shrug=D(8),
          **arm('r', -0.10, 0.26, -0.24, pole=(-0.8, -0.2, -0.8), pron=0.0, curl=0.8),
          **arm('l', 0.24, 0.12, -0.22, pole=(0.8, -0.2, -0.8), curl=0.5))
    settle(K, 0.63, 0.84, 0.90, pel_f=0.14, pel_x=0.0)
    return action_clip(rig, name, stand, K.rows, 0.90, events=EVENTS, steps=K.steps)


def hurt(rig, name):
    """Startled flinch from a blow to the front: head and chest snap back and turn away, the
    shoulders hunch, the near arm comes up loosely across the body, a half step back, recovery."""
    stand, K = _keys(rig, 0.3)
    b = K.base
    K.step('r', 0.03, 0.16, forward=-0.26, height=0.035)
    K.step('r', 0.27, 0.40, forward=0.0, height=0.03)
    K.add(0.0)
    K.add(0.06, pel_f=-0.06, sp_pitch=b['sp_pitch'] - D(12), pel_pitch=b['pel_pitch'] - D(2), hd_pitch=D(-12), hd_yaw=D(-20), hd_roll=D(-7),
          hd_follow=0.55, l_shrug=D(20), r_shrug=D(16), sp_yaw=D(-17), pel_yaw=D(-6), sp_roll=D(-5),
          **arm('l', 0.20, 0.10, -0.24, pole=(0.9, -0.3, -0.3), curl=0.2), **arm('r', -0.32, -0.04, -0.30, pole=(-0.9, -0.5, -0.2), curl=0.2))
    K.add(0.15, pel_f=-0.14, pel_drop=0.03, sp_pitch=b['sp_pitch'] - D(8), hd_pitch=D(-2), hd_yaw=D(-24), sp_yaw=D(-22), pel_yaw=D(-10),
          lf_pitch=D(8), **arm('l', 0.02, 0.20, -0.10, pole=(0.9, -0.2, -0.4), curl=0.3),
          **arm('r', -0.34, -0.06, -0.26, pole=(-0.9, -0.5, -0.2), curl=0.25))
    K.add(0.26, pel_f=-0.12, pel_drop=0.04, sp_pitch=b['sp_pitch'] + D(6), hd_pitch=D(12), hd_yaw=D(-8), hd_roll=0.0, hd_follow=0.3,
          sp_yaw=D(-9), pel_yaw=D(-5), sp_roll=0.0, lf_pitch=0.0, l_shrug=D(10), r_shrug=D(8),
          **arm('l', 0.10, 0.16, -0.20, pole=(0.9, -0.2, -0.5), curl=0.3), **arm('r', -0.26, 0.02, -0.28, curl=0.3))
    settle(K, 0.35, 0.44, 0.45, pel_f=-0.05)
    return action_clip(rig, name, stand, K.rows, 0.45, events={'peak_s': 0.06}, family='hero_reaction', steps=K.steps, blend_out=0.08)


def stumble(rig, name):
    """A toe catches at speed: the trunk pitches, two quick catch steps, arms out, recovery."""
    stand, K = _keys(rig, 0.3)
    b = K.base
    K.step('r', 0.08, 0.23, forward=0.42, height=0.06)
    K.step('l', 0.25, 0.41, forward=0.24, height=0.09)
    K.step('r', 0.47, 0.63, forward=0.0, height=0.04)
    K.step('l', 0.61, 0.76, forward=0.0, height=0.04)
    K.add(0.0)
    # The left toe stubs: the foot stays behind while the body keeps going.
    K.add(0.10, pel_f=0.10, pel_drop=0.03, sp_pitch=b['sp_pitch'] + D(14), pel_pitch=b['pel_pitch'] + D(8), lf_pitch=D(-30),
          hd_pitch=D(-4), hd_follow=0.6, l_shrug=D(8), r_shrug=D(12), sp_yaw=D(10),
          **arm('l', 0.36, -0.06, -0.22, pole=(1.0, -0.6, 0.1), curl=0.15), **arm('r', -0.26, 0.34, -0.20, pole=(-1.0, -0.4, -0.3), curl=0.15))
    K.add(0.23, pel_f=0.20, pel_drop=0.085, sp_pitch=b['sp_pitch'] + D(32), pel_pitch=b['pel_pitch'] + D(13), lf_pitch=D(-44),
          sp_roll=D(-7), pel_yaw=D(10), sp_yaw=D(14), hd_pitch=D(-2), hd_follow=0.75,
          **arm('l', 0.46, -0.10, -0.12, pole=(0.8, -0.8, 0.3), curl=0.1), **arm('r', -0.22, 0.40, -0.29, pole=(-1.0, -0.3, -0.2), curl=0.1))
    K.add(0.41, pel_f=0.22, pel_drop=0.06, sp_pitch=b['sp_pitch'] + D(20), pel_pitch=b['pel_pitch'] + D(8), lf_pitch=0.0,
          sp_roll=D(5), pel_yaw=D(-8), sp_yaw=D(-12), hd_pitch=D(4), hd_follow=0.4,
          **arm('l', 0.30, 0.30, -0.26, pole=(1.0, -0.4, -0.3), curl=0.2), **arm('r', -0.42, -0.02, -0.20, pole=(-1.0, -0.6, 0.0), curl=0.2))
    settle(K, 0.58, 0.76, 0.80, pel_f=0.11, pel_drop=0.03)
    return action_clip(rig, name, stand, K.rows, 0.80, events={'catch_s': 0.23}, family='hero_reaction', steps=K.steps)


def death(rig, name):
    """Sequence 436 (dinfo.c die), as its sixteen pictures: the blow doubles him over (436/04-08), his knees give and he
    drops onto them (436/10-12), he pitches forward onto his chest and face with his heels kicking up (436/14) and lies
    face down, one arm stretched past his head, the shins still half raised and crossed (436/16). His feet never leave
    their spot, so the body ends in front of the root: chest about 1.2 m, head about 1.5 m ahead (the blood pool of 436/16
    lies under the chest and head). The last frame is the dead pose and is held."""
    stand, K = _keys(rig, 0.3)
    b = K.base
    gut_l = arm('l', 0.10, 0.22, -0.34, pole=(1.0, -0.4, -0.2), curl=0.7)
    gut_r = arm('r', -0.08, 0.24, -0.30, pole=(-1.0, -0.4, -0.2), curl=0.7)
    K.add(0.0)
    # the blow: he folds over it
    K.add(0.10, pel_f=-0.05, pel_drop=0.04, sp_pitch=b['sp_pitch'] + D(26), pel_pitch=b['pel_pitch'] + D(6), hd_pitch=D(18), hd_follow=0.5,
          l_shrug=D(16), r_shrug=D(18), **gut_l, **gut_r)
    K.add(0.30, pel_f=-0.02, pel_drop=0.11, pel_x=0.02, sp_pitch=b['sp_pitch'] + D(52), sp_roll=D(5), pel_pitch=b['pel_pitch'] + D(14),
          hd_pitch=D(34), hd_roll=D(6), hd_follow=0.7, l_shrug=D(10), r_shrug=D(12),
          **arm('l', 0.14, 0.30, -0.52, pole=(1.0, -0.4, -0.1), curl=0.4), **gut_r)
    # he hangs there, swaying, and the knees start to go
    K.add(0.50, pel_f=0.06, pel_drop=0.20, pel_x=-0.02, sp_pitch=b['sp_pitch'] + D(58), sp_roll=D(-4), pel_pitch=b['pel_pitch'] + D(16),
          hd_pitch=D(40), hd_roll=D(-5), lf_pitch=D(-16), rf_pitch=D(-12), lf_knee=0.03, rf_knee=0.03,
          **arm('l', 0.20, 0.34, -0.62, pole=(1.0, -0.3, 0.0), curl=0.2), **arm('r', -0.16, 0.34, -0.56, pole=(-1.0, -0.3, 0.0), curl=0.3))
    # onto his knees: the shins go flat, the hips stay over the knees for a moment
    K.add(0.68, pel_f=0.40, pel_drop=0.47, pel_x=0.0, pel_pitch=b['pel_pitch'] + D(30), sp_pitch=b['sp_pitch'] + D(36), sp_roll=0.0,
          hd_pitch=D(30), hd_roll=0.0, hd_follow=0.5, lf_pitch=D(-92), rf_pitch=D(-92), lf_knee=0.02, rf_knee=0.02, l_shrug=D(4), r_shrug=D(4),
          **arm('l', 0.30, 0.56, -0.40, pole=(1.0, -0.2, 0.2), curl=0.1), **arm('r', -0.26, 0.60, -0.36, pole=(-1.0, -0.2, 0.2), curl=0.1))
    # he tips forward off his knees
    K.add(0.80, pel_f=0.62, pel_drop=0.62, pel_pitch=b['pel_pitch'] + D(60), sp_pitch=D(8), hd_pitch=D(40), hd_follow=0.3,
          lf_pitch=D(-96), rf_pitch=D(-96), lf_lift=0.10, rf_lift=0.06, lf_prone=0.5, rf_prone=0.5,
          **arm('l', 0.34, 0.60, -0.36, pole=(1.0, -0.1, 0.4), curl=0.05), **arm('r', -0.30, 0.66, -0.30, pole=(-1.0, -0.1, 0.4), curl=0.05))
    # chest and face hit; the heels kick up
    flat = dict(pel_f=0.87, pel_drop=0.785, pel_pitch=b['pel_pitch'] + D(86), sp_pitch=D(-3), lf_pitch=D(-96), rf_pitch=D(-96), l_shrug=D(18), r_shrug=D(10))
    K.add(0.92, _world={'l': (0.46, 1.22, 0.04), 'r': (-0.26, 1.80, 0.04)}, hd_pitch=D(74), hd_yaw=D(10), hd_roll=0.0, hd_follow=0.0, la_curl=0.1, ra_curl=0.05,
          lf_lift=0.36, rf_lift=0.26, lf_prone=1.0, rf_prone=1.0, lf_f=b['lf_f'] + 0.10, rf_f=b['rf_f'] + 0.06,
          **pole('l', 1.0, -0.3, 0.4), **pole('r', -1.0, 0.3, 0.3), **flat)
    K.add(1.02, lf_lift=0.44, rf_lift=0.24, lf_f=b['lf_f'] + 0.14, rf_f=b['rf_f'] + 0.05, pel_drop=0.795, hd_pitch=D(66), hd_yaw=D(34))
    # he lies still: the head rolled to one side, one arm stretched past it, the shins sinking, the right across the left
    K.add(1.16, _world={'l': (0.33, 0.92, 0.05), 'r': (-0.16, 2.00, 0.04)}, lf_lift=0.30, rf_lift=0.14, lf_f=b['lf_f'] + 0.10, rf_f=b['rf_f'] + 0.02, lf_x=b['lf_x'] - 0.05, hd_pitch=D(62), hd_yaw=D(52), hd_roll=D(8),
          la_curl=0.3, ra_curl=0.2, l_shrug=D(4), r_shrug=D(22), **pole('l', 1.0, -0.6, 0.2), **pole('r', -1.0, 0.4, 0.1))
    K.add(1.22, lf_lift=0.28, rf_lift=0.13)
    K.hold(1.25)
    return action_clip(rig, name, stand, K.rows, 1.25, events={'knees_s': 0.68, 'chest_s': 0.92}, family='hero_death', steps=K.steps, blend_out=0.0)


def sword(rig, name, kind):
    """One-handed cuts, right hand; the blade is imagined along the thumb side of the fist."""
    stand, K = _keys(rig, 0.6)
    b = K.base
    off = arm('l', 0.27, 0.07, -0.30, pole=(0.9, -0.5, -0.3), curl=0.5)
    K.add(0.0)
    if kind == 'slash1':      # forehand diagonal: high right to low left
        K.step('l', 0.02, 0.14, forward=0.22, height=0.045)
        K.step('l', 0.48, 0.66, forward=0.0, height=0.04)
        K.add(0.085, pel_x=-0.035, pel_drop=0.03, pel_yaw=D(-14), sp_yaw=D(-24), sp_roll=D(-4), hd_pitch=D(6), r_shrug=D(10),
              **arm('r', -0.30, -0.06, 0.26, pole=(-1.0, -0.5, -0.2), curl=1.0), **off)
        K.add(0.135, pel_yaw=D(6), sp_yaw=D(2), pel_f=0.08, **arm('r', -0.40, 0.28, 0.22, pole=(-1.0, -0.3, -0.3)))
        K.add(H0, _world={'r': (-0.04, 0.72, 1.26)}, pel_f=0.14, pel_x=0.03, pel_drop=0.04, pel_yaw=D(22), sp_yaw=D(28),
              pel_pitch=b['pel_pitch'] + D(5), sp_pitch=b['sp_pitch'] + D(10), sp_roll=D(5), rf_pitch=D(-34), rf_yaw=b['rf_yaw'] - D(20),
              hd_pitch=D(10), **pole('r', -0.8, -0.2, -0.6), **arm('l', 0.30, -0.06, -0.20, pole=(0.9, -0.5, -0.2), curl=0.5))
        K.hold(H1)
        K.add(0.27, pel_yaw=D(32), sp_yaw=D(40), sp_pitch=b['sp_pitch'] + D(18), pel_drop=0.06,
              **arm('r', 0.12, 0.22, -0.32, pole=(-1.0, 0.0, -0.3)))
        K.add(0.40, pel_yaw=D(14), sp_yaw=D(14), sp_pitch=b['sp_pitch'] + D(8), pel_f=0.10, pel_drop=0.035, pel_pitch=b['pel_pitch'] + D(2),
              sp_roll=0.0, rf_pitch=D(-14), rf_yaw=b['rf_yaw'], r_shrug=D(3),
              **arm('r', 0.02, 0.26, -0.24, pole=(-0.8, -0.2, -0.8)), **off)
    elif kind == 'slash2':    # backhand: from the left shoulder out to the right
        K.step('r', 0.02, 0.14, forward=0.20, height=0.045)
        K.step('r', 0.48, 0.66, forward=0.0, height=0.04)
        K.add(0.085, pel_x=0.035, pel_drop=0.03, pel_yaw=D(14), sp_yaw=D(28), sp_roll=D(4), hd_pitch=D(6), hd_yaw=D(-4),
              **arm('r', 0.20, 0.16, 0.12, pole=(-0.5, 0.3, -1.0), curl=1.0), **arm('l', 0.30, -0.02, -0.22, pole=(0.9, -0.5, -0.2), curl=0.5))
        K.add(0.135, pel_yaw=D(2), sp_yaw=D(6), pel_f=0.08, **arm('r', 0.06, 0.40, 0.06, pole=(-0.9, 0.0, -0.6)))
        K.add(H0, _world={'r': (-0.06, 0.61, 1.30)}, pel_f=0.13, pel_x=-0.02, pel_drop=0.035, pel_yaw=D(-12), sp_yaw=D(-20),
              pel_pitch=b['pel_pitch'] + D(4), sp_pitch=b['sp_pitch'] + D(8), lf_pitch=D(-30), hd_pitch=D(8),
              **pole('r', -1.0, -0.3, -0.1), **arm('l', 0.26, 0.02, -0.24, pole=(0.9, -0.4, -0.3), curl=0.5))
        K.hold(H1)
        K.add(0.27, pel_yaw=D(-22), sp_yaw=D(-34), sp_pitch=b['sp_pitch'] + D(6),
              **arm('r', -0.50, 0.18, 0.02, pole=(-0.6, -1.0, -0.2)))
        K.add(0.40, pel_yaw=D(-8), sp_yaw=D(-10), sp_pitch=b['sp_pitch'] + D(5), pel_f=0.09, pel_drop=0.03, pel_pitch=b['pel_pitch'] + D(2),
              sp_roll=0.0, lf_pitch=D(-10), **arm('r', -0.26, 0.22, -0.20, pole=(-0.8, -0.3, -0.7)), **off)
    else:                     # overhead chop
        K.step('l', 0.02, 0.14, forward=0.24, height=0.045)
        K.step('l', 0.50, 0.68, forward=0.0, height=0.04)
        K.add(0.085, pel_x=-0.02, pel_drop=0.014, pel_yaw=D(-8), sp_yaw=D(-12), sp_pitch=b['sp_pitch'] - D(9), hd_pitch=D(-4),
              hd_follow=0.3, r_shrug=D(16), **arm('r', -0.17, -0.04, 0.46, pole=(-0.7, 0.6, 0.2), curl=1.0), **off)
        K.add(0.135, pel_yaw=D(4), sp_yaw=D(4), sp_pitch=b['sp_pitch'] + D(2), pel_f=0.08, **arm('r', -0.15, 0.28, 0.38, pole=(-0.8, 0.2, -0.4)))
        K.add(H0, _world={'r': (-0.05, 0.74, 1.30)}, pel_f=0.14, pel_x=0.02, pel_drop=0.05, pel_yaw=D(12), sp_yaw=D(14),
              pel_pitch=b['pel_pitch'] + D(6), sp_pitch=b['sp_pitch'] + D(15), rf_pitch=D(-32), hd_pitch=D(10), hd_follow=0.15,
              r_shrug=D(6), **pole('r', -0.7, -0.2, -0.8), **arm('l', 0.28, -0.04, -0.22, pole=(0.9, -0.5, -0.2), curl=0.5))
        K.hold(H1)
        K.add(0.27, pel_drop=0.085, sp_pitch=b['sp_pitch'] + D(26), pel_pitch=b['pel_pitch'] + D(9), pel_yaw=D(14), sp_yaw=D(16),
              **arm('r', -0.10, 0.32, -0.35, pole=(-0.9, -0.3, -0.4)))
        K.add(0.40, pel_yaw=D(6), sp_yaw=D(6), sp_pitch=b['sp_pitch'] + D(10), pel_f=0.10, pel_drop=0.04, pel_pitch=b['pel_pitch'] + D(3),
              rf_pitch=D(-12), r_shrug=D(3), **arm('r', -0.16, 0.24, -0.22, pole=(-0.8, -0.3, -0.7)), **off)
    settle(K, 0.57, 0.74, 0.82, pel_f=0.04, rf_pitch=0.0, lf_pitch=0.0, rf_yaw=b['rf_yaw'])
    return action_clip(rig, name, stand, K.rows, 0.82, events=EVENTS, steps=K.steps)


# The bow in the draw (art row AN-05). 1997 holds it upright at arm's length with the arrow level and the string hand at the
# chin (graphics/dink/bow/hit, six pictures a direction). The bow's place in the left hand is the hero_weapons.json row of
# the bows (hand_l, location (7, -3, 0.5) cm, pitch -90, yaw 0, roll 90): its mesh has +X up the upper limb, +Y to the
# target, the string on -Y. Each key from the raise on FITS the bow wrist to that row (attack_tools.fit_held), so the
# stave stands upright and points where Dink faces whatever the arm does, and puts the string fingers ON the bow's draw
# line, where the runtime's string follows them (UDinkHeroBowSubsystem). Before this the pose was made without a bow in
# the hand: the stave leaned 64 degrees and pointed 52 degrees at the sky, the string hand 39 cm up the limb.
BOW_ROW = dict(location_cm=(7.0, -3.0, 0.5), rotation_deg=(-90.0, 0.0, 90.0))
BOW_BRACE = 0.153                # grip centre to the string at rest (build_weapons._bow)
BOW_NOCK_UP = 0.035              # the arrow sits this far up the stave from the grip centre, on the hand
BOW_DRAW = 0.54                  # the string hand's travel at full draw: 69 cm from the grip, to the cheek
BOW_CANT = D(7)                  # the top limb leans a little to the archer's right, as a held bow does
STRING_FINGERS = ('index_03_r', 'middle_03_r', 'ring_03_r')   # the last joints of the three hooked fingers (rig.HOOK)


def _bow_local():
    from mathutils import Matrix, Vector
    p, y, r = (math.radians(v) for v in BOW_ROW['rotation_deg'])
    cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(r), math.sin(r)
    m = Matrix(((cp * cy, cp * sy, sp), (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
                (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp))).transposed().to_4x4()
    m.translation = Vector(BOW_ROW['location_cm']) / 100.0
    s = Matrix.Diagonal((1, -1, 1, 1))
    return s @ m @ s


def _bow_keys(rig, K, keys, report=None):
    """Keys with the bow upright at `grip` (x left, f forward of the stand, z up; metres) and the string fingers `draw`
    behind the braced string, on the draw line. keys: [(t, grip, draw, changes)], in time order; they are fitted from the
    last to the first, each starting from the answer of the one after it (the stand's hanging arm is too far from any of
    them for the fit to find its way)."""
    from mathutils import Vector
    y0 = rig.head['pelvis'].y
    up = Vector((-math.sin(BOW_CANT), 0.0, math.cos(BOW_CANT)))
    aim = Vector((0.0, -1.0, 0.0))
    fitted = ('la_x', 'la_f', 'la_z', 'la_pron', 'la_bend', 'la_dev', 'ra_x', 'ra_f', 'ra_z')
    states, cur = [], dict(K.cur)
    for t, grip, draw, changes in keys:
        cur = dict(cur)
        cur.update(changes)
        states.append(cur)
    seed, rows = None, []
    for (t, grip, draw, changes), cur in zip(reversed(keys), reversed(states)):
        if seed:
            cur.update({k: seed[k] for k in fitted})
        S = apply_steps(dict(cur), K.base, K.steps, t)
        if not seed:
            # a first guess near the answer: the wrist a hand's length behind the grip, the forearm rolled thumb up
            S.update(world_to_chest(rig, S, 'l', grip[0] + 0.03, grip[1] - 0.07, grip[2] + 0.01), la_pron=D(-30), la_bend=0.0, la_dev=0.0)
        origin = Vector((grip[0], y0 - grip[1], grip[2]))
        e1 = fit_held(rig, S, 'l', _bow_local(), origin, up, aim)
        e2 = fit_point(rig, S, 'r', STRING_FINGERS, origin + up * BOW_NOCK_UP - aim * (BOW_BRACE + draw))
        seed = {k: S[k] for k in fitted}
        cur.update(seed)
        rows.append((t, dict(cur)))
        if report is not None:
            report.append((t, e1, e2, S['la_pron'], S['la_bend'], S['la_dev']))
    K.rows.extend(reversed(rows))
    K.cur = dict(states[-1])
    return K


def _draw_keys(rig, report=None):
    """Keys of the bow draw; the release starts from its last state."""
    stand, K = _keys(rig, 0.6)
    b = K.base
    K.step('l', 0.03, 0.19, forward=0.24, lateral=b['lf_x'] + 0.02, height=0.045)
    K.step('r', 0.16, 0.30, forward=-0.06, lateral=b['rf_x'] - 0.05, height=0.03)
    K.add(0.0)
    # Turn side-on, the bow coming up in front, the string hand taking the string; then push the bow out and bring the
    # string to the chin: half way, nearly there, there.
    up_ = dict(pel_yaw=D(-34), sp_yaw=D(-14), pel_f=0.06, pel_drop=0.015, hd_yaw=D(0), hd_pitch=D(2), hd_follow=0.0, la_curl=0.85, ra_curl=0.62, ra_hook=1.0,
               ra_pron=D(-60), **pole('l', 0.5, -0.2, -0.9), **pole('r', -0.7, -0.2, -0.5))
    full = dict(pel_yaw=D(-56), sp_yaw=D(-26), pel_f=0.10, pel_x=0.0, pel_drop=0.02, sp_roll=D(-2), l_shrug=D(4), r_shrug=D(2), r_protract=D(12), rf_yaw=b['rf_yaw'] + D(48),
                la_curl=0.85, ra_curl=0.62, ra_hook=1.0, ra_pron=D(-60), **pole('l', 0.6, -0.1, -0.8), **pole('r', -0.81, 0.28, 0.51))
    # At full draw the string fingers lie against the right cheek, 12 cm to the chest side of the middle of the face: there
    # the drawing forearm lies behind the arrow with its elbow a little high. At the middle of the face the hand is inside
    # the head, and under the chin the wrist is so near its own shoulder that the elbow can only go behind the neck.
    _bow_keys(rig, K, [(0.20, (0.0, 0.69, 1.36), 0.0, up_), (0.30, (-0.03, 0.80, 1.46), 0.45 * BOW_DRAW, full),
                       (0.40, (-0.09, 0.85, 1.505), 0.90 * BOW_DRAW, full), (0.50, (-0.116, 0.87, 1.52), BOW_DRAW, full)], report)
    return stand, K


def bow_draw(rig, name):
    stand, K = _draw_keys(rig)
    return action_clip(rig, name, stand, K.rows, 0.50, steps=K.steps, blend_out=0.0)


def bow_release(rig, name):
    stand, D0 = _draw_keys(rig)
    K = Keys(rig, D0.base)
    drawn = dict(D0.cur)
    # The feet start where the draw left them.
    K.step('l', -1.0, -0.9, forward=0.24, lateral=K.base['lf_x'] + 0.02, height=0.0)
    K.step('r', -1.0, -0.9, forward=-0.06, lateral=K.base['rf_x'] - 0.05, height=0.0)
    K.step('l', 0.20, 0.36, forward=0.0, lateral=K.base['lf_x'], height=0.04)
    K.step('r', 0.30, 0.42, forward=0.0, lateral=K.base['rf_x'], height=0.03)
    K.add(0.0, **drawn)
    # Loose: the fingers open and the hand springs back along the arrow's line, past the ear; the bow arm holds.
    w = build_pose(rig, apply_steps(dict(drawn), D0.base, D0.steps, 0.5)).pos('hand_r')
    x, f, z = w.x, rig.head['pelvis'].y - w.y, w.z
    K.add(0.05, ra_curl=0.05, ra_hook=0.0, _world={'r': (x - 0.01, f - 0.07, z)})
    K.add(0.16, ra_curl=0.15, _world={'r': (x - 0.02, f - 0.10, z - 0.02)})
    half = {k: 0.5 * (v + K.base[k]) for k, v in K.cur.items()}
    half.update(rf_yaw=K.base['rf_yaw'] + D(48))
    K.add(0.30, **half)
    K.add(0.34, rf_yaw=K.base['rf_yaw'])
    K.rest(0.42)
    K.rest(0.45)
    return action_clip(rig, name, stand, K.rows, 0.45, steps=K.steps, blend_in=0.0, blend_out=0.06)


def cast(rig, name):
    """A spell thrown from an open palm: gather at the chest, thrust, hold, recover. Not a punch."""
    stand, K = _keys(rig, 0.6)
    b = K.base
    K.step('l', 0.03, 0.15, forward=0.20, lateral=b['lf_x'] + 0.03, height=0.04)
    K.step('l', 0.48, 0.64, forward=0.0, lateral=b['lf_x'], height=0.04)
    K.add(0.0)
    K.add(0.07, pel_x=-0.02, sp_yaw=D(-10), pel_yaw=D(-5), hd_pitch=D(4),
          **arm('r', -0.16, 0.14, -0.10, pole=(-0.8, -0.3, -0.6), curl=0.25), **arm('l', 0.16, 0.14, -0.20, pole=(0.8, -0.3, -0.6), curl=0.2))
    thrust = dict(pel_f=0.11, pel_drop=0.02, pel_yaw=D(10), sp_yaw=D(16), sp_pitch=b['sp_pitch'] + D(8), pel_pitch=b['pel_pitch'] + D(3),
                  rf_pitch=D(-18), hd_pitch=D(3), r_protract=D(12), ra_curl=-0.12, ra_bend=CAST_BEND,
                  **pole('r', -0.6, -0.1, -0.8), **arm('l', 0.27, 0.05, -0.40, pole=(0.5, -0.9, -0.2), curl=0.3))
    K.add(0.17, _world={'r': (-0.06, 0.70, 1.36)}, **thrust)
    K.add(0.40, _world={'r': (-0.06, 0.72, 1.37)}, **thrust)
    settle(K, 0.52, 0.64, 0.70, pel_f=0.04, rf_pitch=0.0, ra_bend=CAST_BEND * 0.4)
    return action_clip(rig, name, stand, K.rows, 0.70, events={'cast_s': 0.0}, steps=K.steps)


# The carry of an armed weapon (art row AN-05): where the hand that holds it is while no action plays, as the 1997 idle and
# walk pictures of the armed Dink have it (graphics/dink/sword/idle and bow/idle: he stands on guard, the forearm raised and
# the blade up and out to his side; the bow upright in the left hand). Wrist in the chest frame (out to the side, forward,
# up; metres), forearm roll, and the elbow's pole (out, forward, up): the forearm is about level at the waist, the upper
# arm hangs, and the blade (the hand's +Z, see hero_weapons.json) stands 61 degrees up, leaning 0.42 outward and 0.23
# forward. From the hanging arm of the idle the blade lay level at the hip, pointing forward and across the body.
CARRY = dict(side=0.26, forward=0.222, up=-0.303, roll=-1.05, pole=(0.2, -0.6, -0.8))


def grip(rig, name, side):
    """The stand with one hand closed round a handle and that arm on guard: a sword or the axe in the right hand (Grip_R),
    a bow in the left (Grip_L). A POSE, not an action: the hand closes and the arm rises over the first 0.1 s and the clip
    ends held (no blend out). The runtime layers its last frame under every clip the body plays
    (UDinkBodyAnimInstance::SetGrip): on the fifteen finger bones of the hand that holds a weapon always, and on that arm
    (upper arm, forearm, hand, twist bones) while no action plays, so a cut keeps its own arm and wrist. The fingers wrap
    the handle where hero_weapons.json puts it (rig.GRIP), they do not close into a fist: the attack clips' fist put the
    last finger joints inside the handle. Without it the idle hand lay open round every weapon (art row AN-05, bug A203)."""
    stand, K = _keys(rig, 0.5)
    K.add(0.0)
    sign = 1.0 if side == 'l' else -1.0
    px, pf, pz = CARRY['pole']
    K.add(0.10, **{side + 'a_grip': 1.0},
          **arm(side, sign * CARRY['side'], CARRY['forward'], CARRY['up'], pron=CARRY['roll'], pole=(sign * px, pf, pz)))
    K.add(0.30)
    return action_clip(rig, name, stand, K.rows, 0.30, family='hero_pose', events={'hold_s': 0.2}, blend_out=0.0)


def makers(rig):
    m = {}
    m['Fist_Jab_Timid'] = lambda: jab(rig, 0.0, 'Fist_Jab_Timid')
    m['Fist_Jab_Confident'] = lambda: jab(rig, 1.0, 'Fist_Jab_Confident')
    m['Fist_Cross_Timid'] = lambda: cross(rig, 0.0, 'Fist_Cross_Timid')
    m['Fist_Cross_Confident'] = lambda: cross(rig, 1.0, 'Fist_Cross_Confident')
    m['Fist_Swing_Timid'] = lambda: haymaker(rig, 'Fist_Swing_Timid')
    m['Fist_Swing_Confident'] = lambda: hook(rig, 'Fist_Swing_Confident')
    m['Death_436'] = lambda: death(rig, 'Death_436')
    m['Sword_Slash_1'] = lambda: sword(rig, 'Sword_Slash_1', 'slash1')
    m['Sword_Slash_2'] = lambda: sword(rig, 'Sword_Slash_2', 'slash2')
    m['Sword_Chop'] = lambda: sword(rig, 'Sword_Chop', 'chop')
    m['Bow_Draw'] = lambda: bow_draw(rig, 'Bow_Draw')
    m['Bow_Release'] = lambda: bow_release(rig, 'Bow_Release')
    m['Cast'] = lambda: cast(rig, 'Cast')
    m['Grip_R'] = lambda: grip(rig, 'Grip_R', 'r')
    m['Grip_L'] = lambda: grip(rig, 'Grip_L', 'l')
    m['Hurt'] = lambda: hurt(rig, 'Hurt')
    m['Stumble'] = lambda: stumble(rig, 'Stumble')
    return m
