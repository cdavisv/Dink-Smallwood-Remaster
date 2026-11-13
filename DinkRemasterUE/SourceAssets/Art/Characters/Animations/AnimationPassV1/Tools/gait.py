"""Parametric walk/run cycles on the shared rig, in place.

The planted foot is driven backwards at exactly the clip's travel speed about a heel pivot, then
flat, then a ball pivot, so a mesh moved forward at that speed has no foot sliding at all. Every
number that shapes the gait is a parameter, so the timid and the confident hero, Mother in her
skirt and Milder are the same code with different bodies.
"""
import math
from mathutils import Vector
from rig import (Pose, rot, smooth, lerp, hermite, keyed, ankle_from_contact, FWD, LEFT, UP, ANKLE_H)

D = math.radians
HIP_F = 0.036   # the hip joint sits this far ahead of the rest ankle

BASE = dict(
    v=1.4, T=1.0, stance=0.62, fps=30,
    strike_f=None,             # flat-ankle reference at heel strike (None: stance centred under the hip)
    strike_bias=0.0,           # shift the whole stance forward (+) or back (-)
    step_width=0.085,          # ankle distance from the midline
    foot_yaw=D(7),             # toes out
    strike_pitch=D(17), flat_at=0.14, heel_off=0.52, toeoff_pitch=D(-52),
    swing_lift=0.055, swing_peak=0.42, swing_v0=0.35, swing_v1=1.0, swing_tuck=0.0, swing_tuck_pitch=0.0, swing_carry=0.0,
    pelvis_top=0.945, pelvis_bob=0.022, pelvis_margin=0.004, pelvis_lat=0.018,
    pelvis_yaw=D(6), pelvis_list=D(3.5), pelvis_tilt=D(3), pelvis_fwd=0.0,
    flight_bob=0.0,            # running: extra rise in the flight phase
    lean=D(4), chest_yaw=D(5), chest_counter_roll=0.7, slouch=0.0, chest_sway=0.0,
    head_pitch=D(2), head_follow=0.12, head_bob=D(1.0),
    arm_fwd=D(22), arm_back=D(16), arm_lag=0.03, arm_abduct=D(7), elbow=D(14), elbow_fwd=D(16),
    elbow_back=D(0), arm_inward=D(8), arm_offset=0.0, shrug=0.0, protract=0.0, hand_curl=0.28,
    asym=0.0,                  # 0..1: left/right difference (an uneven, unsure gait)
    knee_in=0.0,
)


def params(**over):
    p = dict(BASE)
    p.update(over)
    n = int(round(p['T'] * p['fps']))
    p['T'] = n / p['fps']
    if p['strike_f'] is None:
        # Centre the real ankle extremes (after heel and toe roll) about the hip.
        a0 = ankle_from_contact(0.0, p['strike_pitch'])[0]
        a1 = ankle_from_contact(-p['v'] * p['stance'] * p['T'], p['toeoff_pitch'])[0]
        p['strike_f'] = HIP_F - 0.5 * (a0 + a1) + p['strike_bias']
    return p


def foot_track(P, u):
    """Sagittal track of one foot at its own cycle phase u (0 = heel strike): returns
    (ankle forward, ankle height, pitch, toe bend, planted)."""
    v, T, s = P['v'], P['T'], P['stance']
    f0 = P['strike_f']
    if u < s:
        x = u / s
        flat_f = f0 - v * u * T
        if x < P['flat_at']:
            pitch = P['strike_pitch'] * (1.0 - smooth(x / P['flat_at']))
        elif x < P['heel_off']:
            pitch = 0.0
        else:
            pitch = P['toeoff_pitch'] * smooth((x - P['heel_off']) / (1.0 - P['heel_off'])) ** 1.25
        f, z = ankle_from_contact(flat_f, pitch)
        return f, z, pitch, (-pitch if pitch < 0 else 0.0), True
    w = (u - s) / (1.0 - s)
    span = (1.0 - s) * T
    fa, za = ankle_from_contact(f0 - v * s * T, P['toeoff_pitch'])
    fb, zb = ankle_from_contact(f0, P['strike_pitch'])
    f = hermite(fa, -v * P['swing_v0'], fb, -v * P['swing_v1'], w, span)
    pk = P['swing_peak']
    bump = math.sin(math.pi * 0.5 * w / pk) if w < pk else math.cos(math.pi * 0.5 * (w - pk) / (1 - pk))
    z = lerp(za, zb, smooth(w)) + P['swing_lift'] * max(0.0, bump) ** 1.2 + P['swing_tuck'] * math.sin(math.pi * min(1.0, w / 0.8)) ** 2
    z += P['swing_carry'] * smooth(w / 0.3) * (1.0 - smooth((w - 0.78) / 0.22))
    pitch = keyed([(0.0, P['toeoff_pitch']), (0.30, P['toeoff_pitch'] * 0.55 + P['swing_tuck_pitch']),
                   (0.80, P['strike_pitch'] * 1.1), (1.0, P['strike_pitch'])], w)
    toe = -P['toeoff_pitch'] * (1.0 - smooth(w / 0.25))
    return f, z, pitch, toe, False


def _pelvis_height(rig, P, tracks):
    """Highest pelvis that lets both legs reach their ankles with a little knee left in them."""
    hip_drop = rig.head['pelvis'].z - rig.head['thigh_l'].z
    leg = rig.length('thigh_l', 'calf_l') + rig.length('calf_l', 'foot_l')
    best = 9.0
    gain = 0.1 * math.sin(P['pelvis_yaw']) * 0.6
    for (f, z, _, _, planted) in tracks:
        if not planted and P.get('free_swing'):
            continue
        reach = leg * (0.996 if planted else 0.998)
        horizontal = math.hypot(max(0.0, abs(f - HIP_F - P['pelvis_fwd']) - gain), 0.1 - P['step_width'])
        if horizontal < reach:
            best = min(best, z + math.sqrt(reach * reach - horizontal * horizontal) + hip_drop)
        else:
            best = min(best, z + hip_drop + 0.2)
    return best


def gait_pose(rig, P, phase, pelvis_z=None):
    pose = Pose(rig)
    s = P['stance']
    two_pi = 2.0 * math.pi
    tl = foot_track(P, phase % 1.0)
    tr = foot_track(P, (phase + 0.5) % 1.0)
    a = P['asym']
    # Pelvis: towards the stance leg, forward with the swinging leg, dropping on the swing side
    mid_l = s * 0.5
    lat = P['pelvis_lat'] * math.cos(two_pi * (phase - mid_l))
    yaw = -P['pelvis_yaw'] * math.cos(two_pi * phase)
    roll = -P['pelvis_list'] * math.sin(two_pi * (phase + 0.05)) * (1.0 + 0.5 * a * math.sin(two_pi * phase))
    z = pelvis_z if pelvis_z is not None else P['pelvis_top']
    pelvis_r = rot(UP, yaw) @ rot(FWD, -roll) @ rot(LEFT, P['pelvis_tilt'] + P['lean'] * 0.35)
    pose.set_pelvis(Vector((lat, rig.head['pelvis'].y - P['pelvis_fwd'], z)), pelvis_r)
    # Feet. The heel/ball pivot offset is applied along the foot's own (toed-out) direction.
    for side, (f, fz, pitch, toe, planted), sign, u in (('l', tl, 1.0, phase % 1.0), ('r', tr, -1.0, (phase + 0.5) % 1.0)):
        width = P['step_width'] * (1.0 + (0.25 * a if side == 'l' else -0.1 * a))
        yaw_f = P['foot_yaw'] * (1.0 - (0.9 * a if side == 'r' else 0.0))
        x = sign * width
        if planted:
            flat_f = P['strike_f'] - P['v'] * u * P['T']
            df = f - flat_f
            f = flat_f + df * math.cos(yaw_f)
            x += sign * df * math.sin(yaw_f)
        ankle = Vector((x, rig.head['foot_l'].y - f, fz))
        pose.foot(side, ankle, pitch=pitch, yaw=yaw_f, toe=toe, knee_out=-P['knee_in'])
    # Trunk: lean, counter-rotation against the pelvis, shoulders kept nearly level
    chest_yaw = P['chest_yaw'] * math.cos(two_pi * (phase - 0.02))
    pose.spine(yaw=chest_yaw - yaw, pitch=P['lean'] * 0.65 + P['slouch'],
               roll=-roll * P['chest_counter_roll'] + P['chest_sway'] * math.cos(two_pi * (phase - mid_l)))
    for side, sign in (('l', 1.0), ('r', -1.0)):
        if P['shrug']:
            pose.rotate('clavicle_' + side, FWD, -sign * P['shrug'])
        if P['protract']:
            pose.rotate('clavicle_' + side, UP, sign * P['protract'])
    # Arms: opposite the same-side leg, a touch late, elbow closing on the forward swing
    for side, off in (('l', 0.0), ('r', 0.5)):
        c = -math.cos(two_pi * (phase + off - P['arm_lag']))
        amp = 1.0 - (0.3 * a if side == 'l' else 0.0)
        swing = (P['arm_fwd'] if c > 0 else P['arm_back']) * c * amp + P['arm_offset']
        fwd = max(0.0, c)
        flex = P['elbow'] + P['elbow_fwd'] * smooth(fwd) + P['elbow_back'] * smooth(max(0.0, -c))
        pose.arm_fk(side, swing, P['arm_abduct'], flex, inward=P['arm_inward'] * (0.4 + 0.6 * fwd))
        pose.fingers(side, P['hand_curl'])
    bob = P['head_bob'] * math.cos(2 * two_pi * (phase - 0.08))
    pose.head_world(pitch=P['head_pitch'] + bob, follow=P['head_follow'])
    return pose.finish()


def gait_clip(rig, P, name):
    """One full stride (left + right step), sampled at P['fps']; first frame = left heel strike."""
    n = int(round(P['T'] * P['fps']))
    T = n / P['fps']
    P = dict(P, T=T)
    phases = [i / n for i in range(n)]
    heights = []
    for ph in phases:
        tracks = (foot_track(P, ph % 1.0), foot_track(P, (ph + 0.5) % 1.0))
        nominal = P['pelvis_top'] - P['pelvis_bob'] * 0.5 * (1.0 + math.cos(2 * 2 * math.pi * (ph - 0.03)))
        nominal += P['flight_bob'] * 0.5 * (1.0 - math.cos(2 * 2 * math.pi * (ph - P['stance'] * 0.5)))
        heights.append(min(nominal, _pelvis_height(rig, P, tracks) - P['pelvis_margin']))
    for _ in range(P.get('height_smooth', 1)):
        heights = [min(heights[i], 0.25 * heights[i - 1] + 0.5 * heights[i] + 0.25 * heights[(i + 1) % n]) for i in range(n)]
    poses = [gait_pose(rig, P, ph, heights[i]) for i, ph in enumerate(phases)]
    poses.append(poses[0])
    return dict(name=name, fps=P['fps'], poses=poses, loop=True, speed=P['v'], stride=P['v'] * T,
                pelvis_range_m=round(max(heights) - min(heights), 4),
                contacts=[dict(l=foot_track(P, ph % 1.0)[4], r=foot_track(P, (ph + 0.5) % 1.0)[4]) for ph in phases + [0.0]])
