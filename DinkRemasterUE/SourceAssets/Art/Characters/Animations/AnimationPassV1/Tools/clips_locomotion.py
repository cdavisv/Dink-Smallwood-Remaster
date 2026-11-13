"""Locomotion, idle, jump and NPC clips. makers(rig) -> {name: callable returning a clip dict}."""
import math
from mathutils import Vector
from rig import Pose, rot, smooth, lerp, keyed, ankle_from_contact, FWD, LEFT, UP, ANKLE_H
from gait import params, gait_clip, D


def stand_parts(rig, confidence, body=None):
    """Parameters of the neutral stand; `body` overrides (NPC builds)."""
    c = min(1.0, max(0.0, confidence))
    p = dict(width=lerp(0.085, 0.105, c), foot_yaw=lerp(D(4), D(9), c), pelvis_drop=lerp(0.012, 0.006, c),
             pelvis_tilt=lerp(D(1), D(3), c), slouch=lerp(D(10), D(1), c), head_pitch=lerp(D(9), D(0), c),
             shrug=lerp(D(4), D(0), c), protract=lerp(D(9), D(0), c), abduct=lerp(D(4), D(8), c),
             elbow=lerp(D(20), D(12), c), swing=lerp(D(5), D(-2), c), inward=lerp(D(16), D(6), c), curl=lerp(0.38, 0.26, c),
             lat=0.0, roll=0.0, yaw=0.0)
    if body:
        p.update(body)
    return p


def stand_from(rig, p, **mod):
    """Build a standing pose from stand_parts-style parameters; feet stay exactly planted."""
    q = dict(p)
    q.update(mod)
    pose = Pose(rig)
    z = rig.head['pelvis'].z - q['pelvis_drop'] - q.get('dip', 0.0)
    pose.set_pelvis(Vector((q['lat'], rig.head['pelvis'].y - q.get('fwd', 0.0), z)),
                    rot(UP, q['yaw']) @ rot(FWD, -q['roll']) @ rot(LEFT, q['pelvis_tilt']))
    for side, sign in (('l', 1.0), ('r', -1.0)):
        pitch = q.get('foot_pitch_' + side, 0.0)
        f, lift, toe = q.get('foot_f_' + side, 0.0), q.get('foot_z_' + side, 0.0), q.get('toe_' + side, 0.0)
        x = sign * q['width']
        # Roll over the heel or the ball instead of digging the sole in; `lift` raises the pivot.
        af, az = ankle_from_contact(f, pitch)
        x += sign * (af - f) * math.sin(q['foot_yaw'])
        f, z = f + (af - f) * math.cos(q['foot_yaw']), az + lift
        if pitch < 0:
            toe = -pitch * (1.0 - smooth(lift / 0.05))
        pose.foot(side, Vector((x, rig.head['foot_l'].y - f, z)), yaw=q['foot_yaw'], pitch=pitch, toe=toe)
    pose.spine(yaw=q.get('chest_yaw', 0.0) - q['yaw'], pitch=q['slouch'] + q.get('breath', 0.0), roll=-q['roll'] * 0.8 + q.get('chest_roll', 0.0))
    for side, sign in (('l', 1.0), ('r', -1.0)):
        sh = q['shrug'] + q.get('breath_shrug', 0.0)
        if sh:
            pose.rotate('clavicle_' + side, FWD, -sign * sh)
        if q['protract']:
            pose.rotate('clavicle_' + side, UP, sign * q['protract'])
        pose.arm_fk(side, q['swing'] + q.get('swing_' + side, 0.0), q['abduct'] + q.get('abduct_' + side, 0.0),
                    q['elbow'] + q.get('elbow_' + side, 0.0), inward=q['inward'] + q.get('inward_' + side, 0.0))
        pose.fingers(side, q['curl'])
    pose.head_world(yaw=q.get('head_yaw', 0.0), pitch=q['head_pitch'] + q.get('head_nod', 0.0), roll=q.get('head_roll', 0.0), follow=0.1)
    return pose.finish()


def stand_pose(rig, confidence):
    """The shared neutral stand: 0 = timid Dink, 1 = confident Dink. Attacks start and end here."""
    return stand_from(rig, stand_parts(rig, confidence))


HERO = 'hero_locomotion'
NPC = 'npc_locomotion'

WALK_C = dict(v=2.0, T=0.8, stance=0.58, pelvis_yaw=D(8), pelvis_list=D(4), lean=D(8), chest_yaw=D(5),
              arm_fwd=D(30), arm_back=D(24), elbow=D(12), elbow_fwd=D(22), arm_abduct=D(8), head_pitch=D(1),
              step_width=0.08, foot_yaw=D(8), asym=0.08, pelvis_fwd=0.01)
WALK_T = dict(v=2.0, T=0.7333, stance=0.60, pelvis_yaw=D(5), pelvis_list=D(3), lean=D(7), slouch=D(9), chest_yaw=D(3),
              arm_fwd=D(15), arm_back=D(10), elbow=D(22), elbow_fwd=D(10), arm_abduct=D(5), arm_inward=D(8),
              shrug=D(4), protract=D(9), head_pitch=D(8), head_follow=0.25, hand_curl=0.4,
              step_width=0.07, foot_yaw=D(3), strike_pitch=D(12), toeoff_pitch=D(-44), asym=0.35, swing_lift=0.045)
RUN_C = dict(v=6.0, T=0.6, stance=0.25, strike_pitch=D(6), flat_at=0.2, heel_off=0.42, toeoff_pitch=D(-58),
             swing_lift=0.08, swing_tuck=0.24, swing_tuck_pitch=D(-45), swing_peak=0.35, swing_v0=0.2, swing_v1=0.45, swing_carry=0.13, free_swing=True, strike_bias=-0.03,
             pelvis_top=0.87, pelvis_bob=0.0, flight_bob=0.05, pelvis_lat=0.01, pelvis_yaw=D(10), pelvis_list=D(4),
             pelvis_tilt=D(6), lean=D(15), chest_yaw=D(9), step_width=0.05, foot_yaw=D(4),
             arm_fwd=D(36), arm_back=D(46), elbow=D(88), elbow_fwd=D(14), elbow_back=D(-18), arm_abduct=D(9),
             arm_inward=D(14), hand_curl=0.6, head_pitch=D(0), head_bob=D(1.5), asym=0.05)
RUN_T = dict(RUN_C, T=0.5667, stance=0.27, slouch=D(6), lean=D(8), head_pitch=D(7), head_follow=0.25, shrug=D(5), protract=D(6),
             arm_fwd=D(24), arm_back=D(26), elbow=D(72), arm_abduct=D(16), arm_inward=D(14), chest_yaw=D(12), chest_sway=D(2),
             flight_bob=0.035, swing_tuck=0.16, swing_tuck_pitch=D(-30), asym=0.3, step_width=0.065, strike_pitch=D(12),
             strike_bias=-0.02)
NPCF_WALK = dict(v=1.25, T=0.8667, stance=0.64, step_width=0.06, foot_yaw=D(6), strike_pitch=D(10), toeoff_pitch=D(-36),
                 swing_lift=0.035, pelvis_yaw=D(4), pelvis_list=D(4.5), pelvis_lat=0.02, lean=D(7), slouch=D(3), chest_yaw=D(3),
                 arm_fwd=D(11), arm_back=D(8), elbow=D(12), elbow_fwd=D(6), arm_abduct=D(9), arm_inward=D(6),
                 head_pitch=D(3), hand_curl=0.3, asym=0.1, pelvis_top=0.938, pelvis_bob=0.012)
NPCF_HURRY = dict(v=2.6, T=0.5333, stance=0.46, step_width=0.055, foot_yaw=D(5), strike_pitch=D(8), flat_at=0.18, toeoff_pitch=D(-46),
                  swing_lift=0.05, swing_carry=0.03, free_swing=True, pelvis_top=0.915, pelvis_bob=0.0, flight_bob=0.018,
                  pelvis_yaw=D(6), pelvis_list=D(4), lean=D(8), slouch=D(3), chest_yaw=D(5),
                  arm_fwd=D(16), arm_back=D(14), elbow=D(62), elbow_fwd=D(8), arm_abduct=D(10), arm_inward=D(18),
                  head_pitch=D(4), hand_curl=0.45, asym=0.1)


def idle_clip(rig, name, base, seconds, channels, breath_period, breath=D(1.0), fps=30, family=HERO, every=15):
    """A standing loop. channels: {stand_from key: [(time, value), ...]} offsets that start and end at 0."""
    n = int(round(seconds * fps))
    poses = []
    for i in range(n + 1):
        t = (i % n) / fps
        mod = {k: keyed(rows, t) for k, rows in channels.items()}
        b = math.sin(2 * math.pi * t / breath_period)
        mod['breath'] = -breath * b + mod.get('breath', 0.0)
        mod['breath_shrug'] = 0.6 * breath * max(0.0, b)
        poses.append(stand_from(rig, base, **mod))
    return dict(name=name, fps=fps, poses=poses, loop=True, speed=0.0, stride=0.0, family=family, strip_every=every)


def idle_timid(rig):
    ch = dict(
        lat=[(0, 0), (1.3, 0), (2.1, -0.046), (3.6, -0.048), (4.4, 0.038), (6.3, 0.042), (7.2, 0), (8, 0)],
        roll=[(0, 0), (1.3, 0), (2.1, D(2.6)), (3.6, D(2.8)), (4.4, D(-2.3)), (6.3, D(-2.5)), (7.2, 0), (8, 0)],
        dip=[(0, 0), (1.3, 0), (2.1, 0.008), (3.6, 0.008), (4.0, 0.003), (4.4, 0.007), (6.3, 0.007), (7.2, 0), (8, 0)],
        yaw=[(0, 0), (1.5, 0), (2.3, D(-3)), (3.6, D(-3)), (4.6, D(2)), (6.3, D(2)), (7.3, 0), (8, 0)],
        head_yaw=[(0, 0), (2.2, 0), (2.55, D(-28)), (3.2, D(-30)), (3.6, D(-4)), (5.4, 0), (5.7, D(16)), (6.1, D(17)), (6.5, 0), (8, 0)],
        head_nod=[(0, 0), (2.2, 0), (2.55, D(-9)), (3.2, D(-9)), (3.7, D(3)), (4.6, 0), (8, 0)],
        chest_yaw=[(0, 0), (2.3, 0), (2.8, D(-6)), (3.3, D(-6)), (3.8, 0), (8, 0)],
        # Wipes his palm on his trouser leg, twice, without looking at it.
        elbow_r=[(0, 0), (4.3, 0), (4.6, D(14)), (4.85, D(2)), (5.1, D(13)), (5.4, D(1)), (5.9, 0), (8, 0)],
        swing_r=[(0, 0), (4.3, 0), (4.6, D(5)), (4.85, D(-3)), (5.1, D(5)), (5.4, D(-2)), (5.9, 0), (8, 0)],
        elbow_l=[(0, 0), (2.4, 0), (2.9, D(7)), (3.5, D(6)), (4.0, 0), (8, 0)],
    )
    return idle_clip(rig, 'Idle_Timid', stand_parts(rig, 0.0), 8.0, ch, breath_period=8.0 / 3, breath=D(1.3))


def idle_confident(rig):
    ch = dict(
        lat=[(0, 0), (1.6, 0), (2.8, 0.04), (5.6, 0.042), (6.9, 0), (8, 0)],
        roll=[(0, 0), (1.6, 0), (2.8, D(-3.2)), (5.6, D(-3.4)), (6.9, 0), (8, 0)],
        dip=[(0, 0), (1.6, 0), (2.8, 0.006), (5.6, 0.006), (6.9, 0), (8, 0)],
        yaw=[(0, 0), (1.6, 0), (2.8, D(3)), (5.6, D(3)), (6.9, 0), (8, 0)],
        head_yaw=[(0, 0), (0.8, 0), (2.0, D(-20)), (3.2, D(-22)), (4.6, D(14)), (5.8, D(16)), (7.0, 0), (8, 0)],
        head_nod=[(0, 0), (2.0, D(-3)), (5.8, D(-2)), (7.0, 0), (8, 0)],
        chest_yaw=[(0, 0), (1.2, 0), (2.4, D(-5)), (3.4, D(-5)), (4.8, D(4)), (5.8, D(4)), (7.0, 0), (8, 0)],
        elbow_l=[(0, 0), (2.8, D(4)), (5.6, D(4)), (6.9, 0), (8, 0)],
        swing_r=[(0, 0), (2.8, D(-3)), (5.6, D(-3)), (6.9, 0), (8, 0)],
    )
    return idle_clip(rig, 'Idle_Confident', stand_parts(rig, 1.0), 8.0, ch, breath_period=4.0, breath=D(1.0))


NPCF_STAND = dict(width=0.07, foot_yaw=D(7), pelvis_drop=0.008, pelvis_tilt=D(3), slouch=D(4), head_pitch=D(3), shrug=0.0,
                  protract=D(3), abduct=D(9), elbow=D(16), swing=D(2), inward=D(10), curl=0.3, lat=0.0, roll=0.0, yaw=0.0)
NPCM_STAND = dict(width=0.12, foot_yaw=D(12), pelvis_drop=0.008, pelvis_tilt=D(4), slouch=D(-1), head_pitch=D(-2), shrug=0.0,
                  protract=0.0, abduct=D(13), elbow=D(16), swing=D(-3), inward=D(8), curl=0.35, lat=0.0, roll=0.0, yaw=0.0)


def idle_npcf(rig):
    ch = dict(
        lat=[(0, 0), (2.0, 0), (3.2, -0.03), (6.0, -0.032), (7.2, 0), (8, 0)],
        roll=[(0, 0), (2.0, 0), (3.2, D(3)), (6.0, D(3.2)), (7.2, 0), (8, 0)],
        dip=[(0, 0), (2.0, 0), (3.2, 0.006), (6.0, 0.006), (7.2, 0), (8, 0)],
        head_yaw=[(0, 0), (1.0, 0), (2.2, D(18)), (3.6, D(20)), (4.8, D(-6)), (6.4, 0), (8, 0)],
        head_nod=[(0, 0), (4.8, D(4)), (6.4, 0), (8, 0)],
        chest_yaw=[(0, 0), (1.4, 0), (2.6, D(5)), (3.8, D(5)), (5.0, 0), (8, 0)],
        elbow_r=[(0, 0), (4.4, 0), (5.2, D(10)), (6.2, D(9)), (7.0, 0), (8, 0)],
    )
    return idle_clip(rig, 'NpcF_Idle', NPCF_STAND, 8.0, ch, breath_period=4.0, breath=D(1.1), family=NPC, every=40)


def idle_npcm(rig):
    ch = dict(
        lat=[(0, 0), (1.5, 0), (2.6, 0.035), (5.4, 0.036), (6.6, 0), (8, 0)],
        roll=[(0, 0), (1.5, 0), (2.6, D(-2.5)), (5.4, D(-2.6)), (6.6, 0), (8, 0)],
        dip=[(0, 0), (1.5, 0), (2.6, 0.005), (5.4, 0.005), (6.6, 0), (8, 0)],
        head_yaw=[(0, 0), (2.0, 0), (3.0, D(-24)), (4.2, D(-24)), (5.2, 0), (8, 0)],
        chest_yaw=[(0, 0), (2.2, 0), (3.2, D(-7)), (4.2, D(-7)), (5.4, 0), (8, 0)],
        head_nod=[(0, 0), (5.2, 0), (5.7, D(-5)), (6.3, 0), (8, 0)],
    )
    return idle_clip(rig, 'NpcM_Idle', NPCM_STAND, 8.0, ch, breath_period=4.0, breath=D(1.0), family=NPC, every=40)


def keyed_clip(rig, name, base, keys, fps=30, loop=False, family=HERO, every=2):
    """Poses from (time, {stand_from offsets}) rows; missing offsets are 0; smooth in between."""
    names = sorted({k for _, d in keys for k in d})
    n = int(round(keys[-1][0] * fps))
    poses = []
    for i in range(n + 1):
        t = i / fps
        mod = {k: keyed([(tt, d.get(k, 0.0)) for tt, d in keys], t) for k in names}
        poses.append(stand_from(rig, base, **mod))
    return dict(name=name, fps=fps, poses=poses, loop=loop, speed=0.0, stride=0.0, family=family, strip_every=every)


AIR = dict(foot_z_l=0.10, foot_z_r=0.02, foot_f_l=0.12, foot_f_r=-0.12, foot_pitch_l=D(-18), foot_pitch_r=D(-36),
           abduct=D(26), elbow=D(48), swing=D(8), swing_l=D(-10), swing_r=D(12), breath=D(5), head_nod=D(3), dip=-0.015)


def jump_start(rig):
    base = stand_parts(rig, 0.5)
    crouch = dict(dip=0.07, breath=D(16), swing=D(-30), elbow=D(10), head_nod=D(6), abduct=D(6))
    push = dict(dip=-0.012, breath=D(2), swing=D(28), elbow=D(30), abduct=D(14), foot_pitch_l=D(-38), foot_pitch_r=D(-38),
                foot_z_l=0.0, foot_z_r=0.0)
    return keyed_clip(rig, 'Jump_Start', base, [(0.0, {}), (0.1, crouch), (0.2, push), (0.3333, AIR)], every=1)


def fall(rig):
    base = stand_parts(rig, 0.5)
    a = dict(AIR)
    b = dict(AIR, foot_z_l=0.08, foot_z_r=0.035, foot_f_l=0.09, foot_f_r=-0.10, abduct=D(31), swing=D(5), elbow=D(42), breath=D(7))
    return keyed_clip(rig, 'Fall', base, [(0.0, a), (0.5, b), (1.0, a)], loop=True, every=5)


def land(rig):
    base = stand_parts(rig, 0.5)
    touch = dict(foot_pitch_l=D(-8), foot_pitch_r=D(-8), dip=0.02, abduct=D(18), elbow=D(34), swing=D(10), breath=D(8))
    absorb = dict(dip=0.15, breath=D(24), swing=D(16), elbow=D(26), abduct=D(12), head_nod=D(8), fwd=0.02)
    rise = dict(dip=0.05, breath=D(9), swing=D(4), elbow=D(8), abduct=D(4), head_nod=D(2))
    return keyed_clip(rig, 'Land', base, [(0.0, touch), (0.1333, absorb), (0.3, rise), (0.4667, {})], every=1)


SHUFFLE = dict(v=0.9, T=1.0, stance=0.66, step_width=0.08, foot_yaw=D(6), strike_pitch=D(8), toeoff_pitch=D(-30), swing_lift=0.03,
               pelvis_yaw=D(3), pelvis_list=D(2.5), pelvis_lat=0.022, pelvis_top=0.945, pelvis_bob=0.008, lean=D(3), slouch=D(5),
               chest_yaw=D(2), arm_fwd=D(9), arm_back=D(7), elbow=D(16), elbow_fwd=D(5), arm_abduct=D(6), head_pitch=D(5),
               hand_curl=0.32, asym=0.15)
NPCM_WALK = dict(v=1.4, T=1.0, stance=0.62, step_width=0.115, foot_yaw=D(13), strike_pitch=D(15), toeoff_pitch=D(-46),
                 pelvis_yaw=D(5), pelvis_list=D(2.5), pelvis_lat=0.03, lean=D(3), slouch=D(-1), chest_yaw=D(6), chest_sway=D(1.5),
                 arm_fwd=D(20), arm_back=D(16), elbow=D(18), elbow_fwd=D(12), arm_abduct=D(14), head_pitch=D(-1),
                 hand_curl=0.4, asym=0.05, pelvis_top=0.94)
NPCM_RUN = dict(RUN_C, v=5.9, T=0.6333, step_width=0.075, foot_yaw=D(8), arm_abduct=D(20), arm_inward=D(4), elbow=D(80), lean=D(13), chest_yaw=D(10),
                flight_bob=0.04, swing_tuck=0.2, asym=0.03, strike_bias=-0.05, pelvis_top=0.862)


def walk(rig, name, spec, family=HERO):
    return dict(gait_clip(rig, params(**spec), name), family=family)


def makers(rig):
    m = {}
    m['Walk_Confident'] = lambda: walk(rig, 'Walk_Confident', WALK_C)
    m['Walk_Timid'] = lambda: walk(rig, 'Walk_Timid', WALK_T)
    m['Run_Confident'] = lambda: walk(rig, 'Run_Confident', RUN_C)
    m['Run_Timid'] = lambda: walk(rig, 'Run_Timid', RUN_T)
    m['Idle_Timid'] = lambda: idle_timid(rig)
    m['Idle_Confident'] = lambda: idle_confident(rig)
    m['NpcF_Idle'] = lambda: idle_npcf(rig)
    m['NpcM_Idle'] = lambda: idle_npcm(rig)
    m['Shuffle'] = lambda: walk(rig, 'Shuffle', SHUFFLE)
    m['Jump_Start'] = lambda: jump_start(rig)
    m['Fall'] = lambda: fall(rig)
    m['Land'] = lambda: land(rig)
    m['NpcM_Walk'] = lambda: walk(rig, 'NpcM_Walk', NPCM_WALK, NPC)
    m['NpcM_Run'] = lambda: walk(rig, 'NpcM_Run', NPCM_RUN, NPC)
    m['NpcF_Walk'] = lambda: walk(rig, 'NpcF_Walk', NPCF_WALK, NPC)
    m['NpcF_Hurry'] = lambda: walk(rig, 'NpcF_Hurry', NPCF_HURRY, NPC)
    return m
