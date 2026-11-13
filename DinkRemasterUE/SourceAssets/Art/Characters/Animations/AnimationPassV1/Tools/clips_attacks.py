"""Attack, hurt and stumble clips. makers(rig) -> {name: callable returning a clip dict}.

Gameplay owns the timing: the hit lands 0.175 s after the clip starts and the next attack may
start at 0.4 s. Everything after 0.4 s is cosmetic and may be interrupted.
"""
import math
from attack_tools import D, Keys, arm, pole, action_clip, state_from_pose
from clips_locomotion import stand_pose

HIT = 0.175
H0, H1 = 10 / 60.0, 11 / 60.0   # the two frames around the hit: both hold the contact pose
EVENTS = {'hit_s': HIT, 'lock_s': 0.4}
PRON = D(70)                     # left forearm roll that turns the knuckles up at contact
PRON_R = D(70)


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
    K.step('l', 0.03, 0.155, forward=0.27 + 0.05 * t, height=0.05)
    K.step('l', 0.47, 0.66, forward=0.0, height=0.045)
    K.add(0.0)
    # Anticipation: weight settles onto the rear leg, lead shoulder draws back, hands come up.
    K.add(0.085, pel_x=-0.03, pel_drop=0.03 + 0.012 * t, pel_yaw=D(7), sp_yaw=D(9 + 6 * t), sp_pitch=b['sp_pitch'] + D(3),
          hd_pitch=D(8 + 6 * t), hd_yaw=D(-10 * t), l_shrug=D(6 + 8 * t), r_shrug=D(4 + 8 * t),
          **arm('l', 0.16 + 0.05 * t, 0.20 - 0.06 * t, -0.03 - 0.06 * t, pole=(0.45 + 0.4 * t, -0.2, -1.0), curl=1.0),
          **arm('r', -0.11 - 0.07 * t, 0.17 - 0.07 * t, 0.05 - 0.22 * t, pole=(-0.4 - 0.3 * t, -0.2, -1.0), curl=1.0 - 0.3 * t))
    # Contact: hips have turned, lead foot is down, weight over it, arm straight behind the knuckles.
    contact = dict(pel_f=0.14 + 0.05 * t, pel_x=0.015, pel_drop=0.015 + 0.03 * t, pel_yaw=D(-16 - 4 * t), pel_pitch=b['pel_pitch'] + D(5 + 4 * t),
                   sp_yaw=D(-24 - 6 * t), sp_pitch=b['sp_pitch'] * 0.5 + D(9 + 8 * t), sp_roll=D(-3 - 4 * t),
                   rf_pitch=D(-26 - 6 * t), hd_pitch=D(9 + 9 * t), hd_yaw=D(-22 * t), hd_roll=D(-8 * t), hd_follow=0.1 + 0.3 * t,
                   l_protract=D(14), l_shrug=D(8 + 10 * t), r_shrug=D(4 + 10 * t),
                   la_pron=PRON, la_curl=1.0, **pole('l', 0.7 + 0.2 * t, 0.0, -0.6 + 0.5 * t))
    rear = arm('r', -0.10, 0.17, 0.06, pole=(-0.4, -0.2, -1.0)) if c > 0.5 else \
        arm('r', -0.30, -0.16, -0.20, pole=(-0.9, -0.6, -0.2), curl=0.6)
    K.add(H0, _world={'l': (0.04, 0.80 + 0.07 * t, 1.35 - 0.05 * t)}, **contact, **rear)
    K.hold(H1)
    # Follow-through and retraction
    K.add(0.27, pel_yaw=D(-9), sp_yaw=D(-12), sp_pitch=b['sp_pitch'] * 0.6 + D(6 + 12 * t), pel_f=0.115 + 0.07 * t,
          la_pron=PRON * 0.5, l_protract=D(5), hd_yaw=D(-12 * t), hd_roll=0.0,
          **arm('l', 0.13, 0.36, -0.02, pole=(0.5 + 0.3 * t, -0.2, -1.0)))
    K.add(0.40, pel_yaw=D(-6), sp_yaw=D(-7), sp_pitch=b['sp_pitch'] * 0.7 + D(4 + 8 * t), pel_f=0.10 + 0.04 * t, pel_drop=0.02 + 0.015 * t,
          pel_pitch=b['pel_pitch'] + D(2), rf_pitch=D(-14), la_pron=0.0, l_protract=0.0, hd_yaw=0.0, hd_pitch=D(6 + 6 * t),
          l_shrug=D(4 + 6 * t), r_shrug=D(3 + 6 * t),
          **arm('l', 0.15 + 0.03 * t, 0.24 - 0.05 * t, 0.0 - 0.08 * t, pole=(0.45 + 0.3 * t, -0.2, -1.0)),
          **arm('r', -0.11 - 0.05 * t, 0.17 - 0.05 * t, 0.05 - 0.16 * t, pole=(-0.4 - 0.2 * t, -0.2, -1.0), curl=1.0 - 0.2 * t))
    settle(K, 0.56, 0.72, 0.80, rf_pitch=0.0, pel_f=0.04, pel_x=-0.02)
    return action_clip(rig, name, stand, K.rows, 0.80, events=EVENTS, steps=K.steps)


def cross(rig, c, name):
    stand, K = _keys(rig, c)
    t = 1.0 - c
    b = K.base
    dur = 0.80 + 0.10 * t
    K.step('l', 0.02, 0.135, forward=0.20 + 0.04 * t, height=0.045)
    if t > 0.5:
        # Over-commits: the rear foot has to come through to catch him, then he shuffles back.
        K.step('r', 0.22, 0.37, forward=0.24, height=0.05)
        K.step('r', 0.50, 0.66, forward=0.0, height=0.04)
        K.step('l', 0.62, 0.80, forward=0.0, height=0.04)
    else:
        K.step('l', 0.47, 0.66, forward=0.0, height=0.045)
    K.add(0.0)
    # Coil: weight onto the rear leg, rear hip and shoulder drawn back, fist chambered.
    chamber = arm('r', -0.15, 0.11, 0.03, pole=(-0.5, -0.4, -1.0), curl=1.0) if c > 0.5 else \
        arm('r', -0.36, -0.12, -0.02, pole=(-1.0, -0.5, 0.1), curl=1.0)
    lead = arm('l', 0.12, 0.27, 0.01, pole=(0.45, -0.2, -1.0), curl=1.0) if c > 0.5 else \
        arm('l', 0.22, 0.20, -0.14, pole=(0.8, -0.2, -0.8), curl=0.7)
    K.add(0.085, pel_x=-0.035, pel_drop=0.03 + 0.012 * t, pel_yaw=D(-12 - 4 * t), sp_yaw=D(-13 - 10 * t), sp_pitch=b['sp_pitch'] + D(3),
          hd_pitch=D(8 + 6 * t), hd_yaw=D(8 * t), r_shrug=D(6 + 10 * t), l_shrug=D(4 + 8 * t), **chamber, **lead)
    # Contact: rear hip and shoulder through, rear heel up and turned, weight on the lead leg.
    guard = arm('l', 0.10, 0.15, 0.07, pole=(0.45, -0.3, -1.0)) if c > 0.5 else \
        arm('l', 0.34, -0.14, -0.22, pole=(0.9, -0.6, -0.2), curl=0.6)
    K.add(H0, _world={'r': (0.0, 0.86 + 0.04 * t, 1.34 - 0.05 * t)},
          pel_f=0.15 + 0.05 * t, pel_x=0.04, pel_drop=0.02 + 0.03 * t, pel_yaw=D(30 + 4 * t), pel_pitch=b['pel_pitch'] + D(5 + 4 * t),
          sp_yaw=D(30 + 6 * t), sp_pitch=b['sp_pitch'] * 0.5 + D(10 + 9 * t), sp_roll=D(4 + 4 * t),
          rf_pitch=D(-40), rf_yaw=b['rf_yaw'] - D(28), hd_pitch=D(9 + 10 * t), hd_yaw=D(24 * t), hd_roll=D(8 * t), hd_follow=0.1 + 0.3 * t,
          r_protract=D(14), r_shrug=D(8 + 10 * t), l_shrug=D(4 + 10 * t), ra_pron=PRON_R, ra_curl=1.0,
          **pole('r', -0.7 - 0.2 * t, 0.0, -0.6 + 0.5 * t), **guard)
    K.hold(H1)
    K.add(0.27, pel_yaw=D(22 + 14 * t), sp_yaw=D(20 + 14 * t), sp_pitch=b['sp_pitch'] * 0.6 + D(7 + 14 * t), pel_f=0.14 + 0.10 * t,
          pel_drop=0.025 + 0.05 * t, ra_pron=PRON_R * 0.5, r_protract=D(5), hd_yaw=D(12 * t), hd_roll=0.0,
          **(arm('r', -0.14, 0.34, -0.02, pole=(-0.5, -0.2, -1.0)) if c > 0.5 else arm('r', 0.02, 0.40, -0.22, pole=(-0.8, -0.2, -0.6))))
    K.add(0.40, pel_yaw=D(8 + 10 * t), sp_yaw=D(8 + 6 * t), sp_pitch=b['sp_pitch'] * 0.7 + D(4 + 12 * t), pel_f=0.10 + 0.10 * t,
          pel_drop=0.02 + 0.03 * t, pel_x=0.02, pel_pitch=b['pel_pitch'] + D(2), rf_pitch=D(-16) * c, rf_yaw=b['rf_yaw'] - D(10) * c,
          ra_pron=0.0, r_protract=0.0, hd_yaw=0.0, hd_pitch=D(6 + 8 * t), r_shrug=D(4 + 6 * t), l_shrug=D(3 + 6 * t),
          **arm('r', -0.12 - 0.04 * t, 0.18 - 0.02 * t, 0.05 - 0.18 * t, pole=(-0.4 - 0.3 * t, -0.2, -1.0), curl=1.0 - 0.2 * t),
          **arm('l', 0.14 + 0.06 * t, 0.24 - 0.10 * t, 0.01 - 0.18 * t, pole=(0.45 + 0.3 * t, -0.2, -1.0), curl=1.0 - 0.3 * t))
    settle(K, 0.56 + 0.06 * t, 0.72 + 0.10 * t, dur, rf_pitch=0.0, rf_yaw=b['rf_yaw'], pel_f=0.04 + 0.03 * t, pel_x=0.0)
    return action_clip(rig, name, stand, K.rows, dur, events=EVENTS, steps=K.steps)


def hook(rig, name):
    """Combo hit 3, confident: a tight lead hook thrown with the hips, elbow level with the fist."""
    stand, K = _keys(rig, 1.0)
    b = K.base
    K.step('l', 0.02, 0.12, forward=0.12, height=0.035)
    K.step('l', 0.50, 0.68, forward=0.0, height=0.04)
    K.add(0.0)
    K.add(0.09, pel_x=0.03, pel_drop=0.05, pel_yaw=D(16), sp_yaw=D(20), sp_pitch=b['sp_pitch'] + D(5), sp_roll=D(5),
          hd_pitch=D(8), l_shrug=D(8), r_shrug=D(4),
          **arm('l', 0.33, 0.06, -0.06, pole=(1.0, -0.6, -0.2), curl=1.0, pron=PRON * 0.5),
          **arm('r', -0.10, 0.17, 0.06, pole=(-0.4, -0.2, -1.0), curl=1.0))
    K.add(0.13, lf_pitch=D(-16), pel_yaw=D(-4), sp_yaw=D(-2), pel_f=0.06, pel_pitch=b['pel_pitch'] + D(4),
          **arm('l', 0.34, 0.20, -0.02, pole=(1.0, -0.6, 0.1), pron=PRON * 0.7))
    K.add(H0, _world={'l': (-0.03, 0.56, 1.36)}, pel_x=-0.02, pel_f=0.11, pel_drop=0.035, pel_yaw=D(-30), sp_yaw=D(-36),
          pel_pitch=b['pel_pitch'] + D(6), sp_pitch=b['sp_pitch'] + D(13), sp_roll=D(-4), lf_pitch=D(-30), lf_yaw=b['lf_yaw'] - D(34), hd_pitch=D(9),
          l_shrug=D(12), la_pron=PRON * 0.8, **pole('l', 1.0, -0.5, 0.25))
    K.hold(H1)
    K.add(0.26, pel_yaw=D(-38), sp_yaw=D(-44), pel_x=-0.03, sp_roll=D(-6),
          **arm('l', -0.16, 0.26, -0.03, pole=(1.0, 0.2, 0.0)))
    K.add(0.40, pel_yaw=D(-8), sp_yaw=D(-8), pel_x=0.0, pel_f=0.06, pel_drop=0.025, sp_roll=0.0, sp_pitch=b['sp_pitch'] + D(5),
          pel_pitch=b['pel_pitch'] + D(2),
          lf_pitch=0.0, lf_yaw=b['lf_yaw'], l_shrug=D(4), la_pron=0.0,
          **arm('l', 0.15, 0.24, 0.0, pole=(0.45, -0.2, -1.0)))
    settle(K, 0.56, 0.72, 0.80, pel_f=0.02)
    return action_clip(rig, name, stand, K.rows, 0.80, events=EVENTS, steps=K.steps)


def haymaker(rig, name):
    """Combo hit 3, timid: a wild looping right that spins him round and needs a catch step."""
    stand, K = _keys(rig, 0.0)
    b = K.base
    K.step('l', 0.02, 0.13, forward=0.18, height=0.045)
    K.step('r', 0.21, 0.37, forward=0.30, lateral=b['rf_x'] + 0.07, height=0.06)
    K.step('r', 0.52, 0.68, forward=0.0, lateral=b['rf_x'], height=0.04)
    K.step('l', 0.64, 0.82, forward=0.0, height=0.04)
    K.add(0.0)
    K.add(0.085, pel_x=-0.04, pel_drop=0.045, pel_yaw=D(-20), sp_yaw=D(-26), sp_pitch=b['sp_pitch'] + D(2), sp_roll=D(-5),
          hd_pitch=D(14), hd_yaw=D(-6), r_shrug=D(16), l_shrug=D(10),
          **arm('r', -0.50, -0.20, 0.04, pole=(-0.6, -1.0, 0.2), curl=1.0),
          **arm('l', 0.26, 0.22, -0.12, pole=(0.8, -0.2, -0.8), curl=0.6))
    K.add(0.135, pel_yaw=D(4), sp_yaw=D(2), pel_x=0.0, pel_f=0.08,
          **arm('r', -0.52, 0.20, 0.03, pole=(-1.0, -0.5, 0.25), pron=PRON_R * 0.5))
    K.add(H0, _world={'r': (-0.04, 0.76, 1.32)}, pel_f=0.20, pel_x=0.04, pel_drop=0.05, pel_yaw=D(34), pel_pitch=b['pel_pitch'] + D(8),
          sp_yaw=D(38), sp_pitch=b['sp_pitch'] * 0.5 + D(18), sp_roll=D(8), rf_pitch=D(-38), rf_yaw=b['rf_yaw'] - D(26),
          hd_pitch=D(20), hd_yaw=D(26), hd_roll=D(10), hd_follow=0.45, r_shrug=D(20), l_shrug=D(14), ra_pron=PRON_R * 0.8,
          **pole('r', -1.0, -0.3, 0.35), **arm('l', 0.36, -0.16, -0.20, pole=(0.9, -0.6, -0.2), curl=0.5))
    K.hold(H1)
    # The swing carries on across the body and drags him after it.
    K.add(0.29, pel_yaw=D(52), sp_yaw=D(50), sp_pitch=b['sp_pitch'] * 0.5 + D(30), sp_roll=D(10), pel_f=0.27, pel_x=0.06, pel_drop=0.08,
          rf_pitch=0.0, rf_yaw=b['rf_yaw'], hd_yaw=D(14), hd_roll=D(4),
          **arm('r', 0.20, 0.34, -0.26, pole=(-1.0, -0.2, -0.1), pron=PRON_R * 0.4),
          **arm('l', 0.38, -0.20, -0.10, pole=(0.9, -0.6, 0.0)))
    K.add(0.41, pel_yaw=D(26), sp_yaw=D(16), sp_pitch=b['sp_pitch'] * 0.7 + D(20), sp_roll=D(2), pel_f=0.24, pel_x=0.03, pel_drop=0.06,
          pel_pitch=b['pel_pitch'] + D(4), hd_yaw=0.0, hd_pitch=D(16), hd_follow=0.2, r_shrug=D(10), l_shrug=D(8),
          **arm('r', -0.10, 0.26, -0.24, pole=(-0.8, -0.2, -0.8), pron=0.0, curl=0.8),
          **arm('l', 0.24, 0.12, -0.22, pole=(0.8, -0.2, -0.8), curl=0.5))
    settle(K, 0.62, 0.82, 0.90, pel_f=0.10, pel_x=0.0)
    return action_clip(rig, name, stand, K.rows, 0.90, events=EVENTS, steps=K.steps)


def hurt(rig, name):
    """Flinch from a blow to the front left: recoil and twist away, half step back, cover, recover."""
    stand, K = _keys(rig, 0.3)
    b = K.base
    K.step('r', 0.02, 0.15, forward=-0.22, height=0.035)
    K.step('r', 0.25, 0.39, forward=0.0, height=0.03)
    K.add(0.0)
    K.add(0.06, pel_f=-0.05, sp_pitch=b['sp_pitch'] - D(15), hd_pitch=D(-12), hd_yaw=D(-16), hd_roll=D(-6), hd_follow=0.5,
          l_shrug=D(18), r_shrug=D(10), sp_yaw=D(-16), pel_yaw=D(-7), sp_roll=D(-5),
          **arm('l', 0.16, 0.20, -0.04, pole=(0.9, -0.2, -0.5), curl=0.5), **arm('r', -0.30, 0.02, -0.26, pole=(-0.9, -0.4, -0.3), curl=0.4))
    K.add(0.14, pel_f=-0.12, pel_drop=0.045, sp_pitch=b['sp_pitch'] - D(3), hd_pitch=D(6), hd_yaw=D(-10), sp_yaw=D(-18), pel_yaw=D(-10),
          lf_pitch=D(8), **arm('l', 0.10, 0.24, 0.04, pole=(0.7, -0.2, -0.8), curl=0.6),
          **arm('r', -0.20, 0.16, -0.14, pole=(-0.8, -0.2, -0.7), curl=0.5))
    K.add(0.24, pel_f=-0.10, pel_drop=0.055, sp_pitch=b['sp_pitch'] + D(10), hd_pitch=D(18), hd_yaw=D(-4), hd_roll=0.0, hd_follow=0.3,
          sp_yaw=D(-8), pel_yaw=D(-5), sp_roll=0.0, lf_pitch=0.0, l_shrug=D(10), r_shrug=D(8),
          **arm('l', 0.12, 0.20, -0.06, curl=0.6), **arm('r', -0.15, 0.16, -0.14, curl=0.5))
    settle(K, 0.33, 0.42, 0.42, pel_f=-0.04)
    return action_clip(rig, name, stand, K.rows, 0.42, events={'peak_s': 0.06}, family='hero_reaction', steps=K.steps, blend_out=0.08)


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


def makers(rig):
    m = {}
    m['Fist_Jab_Timid'] = lambda: jab(rig, 0.0, 'Fist_Jab_Timid')
    m['Fist_Jab_Confident'] = lambda: jab(rig, 1.0, 'Fist_Jab_Confident')
    m['Fist_Cross_Timid'] = lambda: cross(rig, 0.0, 'Fist_Cross_Timid')
    m['Fist_Cross_Confident'] = lambda: cross(rig, 1.0, 'Fist_Cross_Confident')
    m['Fist_Swing_Timid'] = lambda: haymaker(rig, 'Fist_Swing_Timid')
    m['Fist_Swing_Confident'] = lambda: hook(rig, 'Fist_Swing_Confident')
    m['Sword_Slash_1'] = lambda: sword(rig, 'Sword_Slash_1', 'slash1')
    m['Sword_Slash_2'] = lambda: sword(rig, 'Sword_Slash_2', 'slash2')
    m['Sword_Chop'] = lambda: sword(rig, 'Sword_Chop', 'chop')
    m['Hurt'] = lambda: hurt(rig, 'Hurt')
    m['Stumble'] = lambda: stumble(rig, 'Stumble')
    return m
