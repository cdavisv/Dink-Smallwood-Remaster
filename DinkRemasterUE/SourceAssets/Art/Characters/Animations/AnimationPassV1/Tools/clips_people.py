"""Poses of single people. makers(rig) -> {name: callable returning a clip dict}.

Seth_Pose: the standing picture of Seth (graphics/effects/magic/pose, loaded as sequence 580 by s7-mil): feet wide
apart, arms crossed high on the chest, chin up. A loop: he breathes, shifts his weight once and looks his visitor over."""
import math
from mathutils import Vector, Matrix
from rig import Pose, rot, smooth, lerp, keyed, FWD, LEFT, UP
from gait import D
from clips_locomotion import stand_from

PEOPLE = 'people_pose'
SETH_STAND = dict(width=0.205, foot_yaw=D(17), pelvis_drop=0.014, pelvis_tilt=D(2), slouch=D(-4), head_pitch=D(-3), shrug=D(5),
                  protract=D(10), abduct=D(10), elbow=D(60), swing=D(10), inward=D(30), curl=0.3, lat=0.0, roll=0.0, yaw=0.0)
# Wrists in the rest space of the chest (spine_05), metres: the right forearm lies on top, its hand on the left upper arm;
# the left forearm under it, its hand tucked behind the right elbow. Poles send the elbows down and out.
CROSS = dict(
    r=dict(wrist=Vector((0.080, -0.222, 1.292)), pole=Vector((-0.80, -0.12, -0.60)), flex=D(34), curl=0.30),
    l=dict(wrist=Vector((-0.100, -0.196, 1.240)), pole=Vector((0.80, -0.10, -0.62)), flex=D(40), curl=0.36),
)


def palm_normal(pose, side):
    hand = pose.pos('hand_' + side)
    n = (pose.pos('middle_01_' + side) - hand).cross(pose.pos('index_01_' + side) - pose.pos('pinky_01_' + side)).normalized()
    return n if (pose.pos('thumb_02_' + side) - hand).dot(n) >= 0 else -n


def crossed_arms(pose, lift=0.0, hug=0.0):
    """Arms crossed on the chest; the wrists ride on the chest (they follow spine_05), `lift` raises them, `hug` pulls
    the forearms tighter. Each hand is turned palm to the body and bent round the arm it rests on."""
    r = pose.rig
    chest = pose.W('spine_05') @ r.rest['spine_05'].inverted()
    turn = chest.to_3x3()
    for side in 'lr':
        c = CROSS[side]
        hand = 'hand_' + side
        pose.ik('arm', side, chest @ (c['wrist'] + Vector((0.0, 0.012 * hug, lift))), turn @ c['pole'])
        pose.hand_follow(side)
        axis = (pose.pos(hand) - pose.pos('lowerarm_' + side)).normalized()
        n = palm_normal(pose, side)
        want = turn @ Vector((0.0, 1.0, -0.25))
        n_p = (n - axis * n.dot(axis)).normalized()
        w_p = (want - axis * want.dot(axis)).normalized()
        pose.rotate(hand, axis, math.atan2(axis.dot(n_p.cross(w_p)), n_p.dot(w_p)))
        pose.rotate(hand, axis.cross(palm_normal(pose, side)).normalized(), c['flex'])
        pose.forearm_twist(side)
        pose.fingers(side, c['curl'], thumb=0.15)
    return pose


def seth_pose(rig, seconds=8.0, fps=30):
    ch = dict(
        lat=[(0, 0), (2.0, 0), (3.2, 0.03), (5.6, 0.032), (6.8, 0), (8, 0)],
        roll=[(0, 0), (2.0, 0), (3.2, D(-2.0)), (5.6, D(-2.2)), (6.8, 0), (8, 0)],
        dip=[(0, 0), (2.0, 0), (3.2, 0.004), (5.6, 0.004), (6.8, 0), (8, 0)],
        head_yaw=[(0, 0), (0.6, 0), (1.5, D(-9)), (2.6, D(-10)), (3.8, D(4)), (5.4, D(5)), (6.6, 0), (8, 0)],
        head_roll=[(0, 0), (1.5, D(4)), (2.6, D(5)), (3.8, D(-2)), (5.4, D(-2)), (6.6, 0), (8, 0)],
        head_nod=[(0, 0), (3.8, 0), (4.4, D(-4)), (5.4, D(-4)), (6.6, 0), (8, 0)],
        chest_yaw=[(0, 0), (1.5, D(-3)), (2.6, D(-3)), (3.8, D(2)), (5.4, D(2)), (6.6, 0), (8, 0)],
    )
    n = int(round(seconds * fps))
    poses = []
    for i in range(n + 1):
        t = (i % n) / fps
        mod = {k: keyed(rows, t) for k, rows in ch.items()}
        b = math.sin(2 * math.pi * t / 4.0)
        mod['breath'] = -D(1.1) * b
        mod['breath_shrug'] = 0.6 * D(1.1) * max(0.0, b)
        pose = stand_from(rig, SETH_STAND, **mod)
        crossed_arms(pose, lift=0.004 * max(0.0, b))
        poses.append(pose.finish())
    return dict(name='Seth_Pose', fps=fps, poses=poses, loop=True, speed=0.0, stride=0.0, family=PEOPLE, strip_every=40,
                note='Seth standing, arms crossed (1997 picture pose, sequence 580)')


GUARD_STAND = dict(width=0.115, foot_yaw=D(11), pelvis_drop=0.008, pelvis_tilt=D(3), slouch=D(-2), head_pitch=D(-1), shrug=0.0,
                   protract=0.0, abduct=D(11), elbow=D(14), swing=D(-2), inward=D(8), curl=0.4, lat=0.0, roll=0.0, yaw=0.0)
# Where the shaft of a polearm stands (armature space, metres, on the right; npc_port.py stands the pole of a ported
# figure at the same spot: NPCS[...]['pole_xy'] = (-x, y)) and how high the fist closes on it.
POLE = dict(x=-0.30, y=-0.10, grip_z=1.17)


def orient_hand(pose, side, palm_to, index_to):
    """Turn the hand so that its palm faces `palm_to` and the line from the little finger's knuckle to the index
    finger's points along `index_to` (armature space)."""
    hand = 'hand_' + side
    def frame(n, l):
        n = n.normalized(); l = (l - n * l.dot(n)).normalized(); c = n.cross(l)
        return Matrix((n, l, c)).transposed()
    n0 = palm_normal(pose, side); l0 = pose.pos('index_01_' + side) - pose.pos('pinky_01_' + side)
    turn = frame(Vector(palm_to), Vector(index_to)) @ frame(n0, l0).transposed()
    pose.set_world_rot(hand, turn @ pose.W(hand).to_3x3())


def grip_pole(pose, side='r', pole=POLE):
    """The fist of one hand closed on an upright shaft that stands still beside the body (the shaft is bound to the root
    bone, so the wrist is placed in armature space every frame: the hand does not slide on it while the body breathes
    and sways). Palm to the body, thumb side up, the shaft across the palm 7.5 cm in front of the wrist."""
    s = 1.0 if side == 'l' else -1.0
    inward = Vector((-s, 0.0, 0.0)); along = Vector((0.0, -1.0, 0.0))
    shaft = Vector((s * abs(pole['x']), pole['y'], pole['grip_z']))
    wrist = shaft - along * 0.075 + inward * (-0.030)
    pose.ik('arm', side, wrist, Vector((s * 0.60, 0.55, -0.58)))
    pose.hand_follow(side)
    orient_hand(pose, side, inward, Vector((0.0, 0.0, 1.0)))
    pose.forearm_twist(side)
    pose.fingers(side, 0.82, thumb=0.45)
    return pose


def guard_stand(rig, seconds=8.0, fps=30):
    ch = dict(
        lat=[(0, 0), (2.4, 0), (3.6, 0.018), (5.8, 0.02), (7.0, 0), (8, 0)],
        roll=[(0, 0), (2.4, 0), (3.6, D(-1.4)), (5.8, D(-1.5)), (7.0, 0), (8, 0)],
        head_yaw=[(0, 0), (1.0, 0), (2.0, D(14)), (3.4, D(15)), (4.6, D(-8)), (6.0, D(-8)), (7.0, 0), (8, 0)],
        chest_yaw=[(0, 0), (1.4, 0), (2.4, D(3)), (3.4, D(3)), (4.8, D(-2)), (6.0, D(-2)), (7.0, 0), (8, 0)],
    )
    n = int(round(seconds * fps))
    poses = []
    for i in range(n + 1):
        t = (i % n) / fps
        mod = {k: keyed(rows, t) for k, rows in ch.items()}
        b = math.sin(2 * math.pi * t / 4.0)
        mod['breath'] = -D(0.9) * b
        mod['breath_shrug'] = 0.6 * D(0.9) * max(0.0, b)
        pose = stand_from(rig, GUARD_STAND, **mod)
        grip_pole(pose, 'r')
        poses.append(pose.finish())
    return dict(name='Guard_Stand', fps=fps, poses=poses, loop=True, speed=0.0, stride=0.0, family=PEOPLE, strip_every=40,
                note='a guard standing with a polearm upright in his right fist (the shaft stands on the root bone)')


def makers(rig):
    return {'Seth_Pose': lambda: seth_pose(rig), 'Guard_Stand': lambda: guard_stand(rig)}
