"""Deterministic in-place duck actions with analytic two-bone leg IK and ground solves.

All clips keep `root` at identity (no root motion).  Locomotion plants the toe
base on Z=0.014 m during stance and lifts/curls the toes during swing.  Peck and
Death solve their depth against the evaluated skinned mesh so the bill touches,
and the body rests on, the ground without sinking into it.
"""
import math

import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion

import duck_common as D

TAU = math.tau
WALK = dict(duty=0.62, half=0.040)
RUN = dict(duty=0.42, half=0.046)
HEADLESS = dict(duty=0.42, half=0.044)
GAITS = {'Duck_Walk': WALK, 'Duck_Run': RUN, 'Duck_HeadlessRun': HEADLESS}


def gait_speed_cm_s(name):
    g = GAITS[name]
    period = (D.ACTIONS[name]['frames'] - 1) / D.FPS
    return round(100 * 2 * g['half'] / (g['duty'] * period), 1)


def create_duck_actions(arm, mesh_ob, scene):
    arm.data.pose_position = 'POSE'
    arm.animation_data_create()
    arm.animation_data.action = None
    for name in D.ACTIONS:
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
    rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    bones = arm.pose.bones
    part = np.zeros(len(mesh_ob.data.vertices), np.int32)
    mesh_ob.data.attributes['duck_part'].data.foreach_get('value', part)
    bill_mask = np.isin(part, [D.PART_BILL_UP, D.PART_BILL_LO])
    feet_mask = np.isin(part, [D.PART_LEG, D.PART_TOE, D.PART_WEB, D.PART_CLAW])
    death_lifts = []
    dpos = np.zeros(len(part) * 3, np.float32)
    mesh_ob.data.attributes['duck_dpos'].data.foreach_get('vector', dpos)
    dpos = dpos.reshape(-1, 3)
    side = (dpos - np.array(D.CUT_POINT)) @ (np.array(D.CUT_NORMAL) / np.linalg.norm(D.CUT_NORMAL))
    # vertices that exist on the headless variant (body side of the cut, no head-side gore)
    headless_mask = ((side <= 1e-5) | np.isin(part, [D.PART_LEG, D.PART_TOE, D.PART_WEB, D.PART_CLAW])) & ~np.isin(part, list(D.GORE_HEAD))
    intact_mask = ~np.isin(part, list(D.GORE))
    head_mask = np.isin(part, [D.PART_BILL_UP, D.PART_BILL_LO, D.PART_EYE, D.PART_LID])
    upd = bpy.context.view_layer.update

    def reset():
        for pb in bones:
            pb.matrix_basis = Matrix.Identity(4)

    def rot(name, axis, ang):
        if abs(ang) < 1e-9:
            return
        local = rest[name].to_3x3().inverted() @ Vector(axis)
        pb = bones[name]
        pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(local.normalized(), ang)

    def move(name, offset):
        bones[name].location += rest[name].to_3x3().inverted() @ Vector(offset)

    def posed(name, head, tail):
        b = arm.data.bones[name]
        q = (b.tail_local - b.head_local).rotation_difference(tail - head)
        m = q.to_matrix().to_4x4() @ rest[name]
        m.translation = head
        return m

    TOE_REACH = 0.072       # toe bone plus claw tip beyond the bone tail (m)
    TOE_REST_DROP = 0.13    # toes already slope down at rest (rad)
    REST_ANGLE = {}
    for bn in ('neck_01', 'neck_02', 'neck_03', 'head'):
        v = arm.data.bones[bn].tail_local - arm.data.bones[bn].head_local
        REST_ANGLE[bn] = math.atan2(v.z, v.x)
    F_rest = {s: arm.data.bones['foot_' + s].tail_local.copy() for s in 'lr'}
    perp_rest = {}
    for s in 'lr':
        K = arm.data.bones['calf_' + s].head_local
        J = arm.data.bones['calf_' + s].tail_local
        T = F_rest[s]
        d = (T - K).normalized()
        p = (J - K) - d * (J - K).dot(d)
        perp_rest[s] = p.normalized()

    def leg(s, target, curl=0.0, follow=None):
        """Two-bone IK (calf, foot) from the posed knee to the toe base; toes flat or curled."""
        upd()
        pelvis_delta = bones['pelvis'].matrix @ rest['pelvis'].inverted()
        K = bones['calf_' + s].head.copy()
        l1 = arm.data.bones['calf_' + s].length
        l2 = arm.data.bones['foot_' + s].length
        delta = target - K
        dist = max(abs(l1 - l2) + 1e-4, min(delta.length, (l1 + l2) * 0.9995))
        dvec = delta.normalized()
        perp = pelvis_delta.to_3x3() @ perp_rest[s]
        perp = (perp - dvec * perp.dot(dvec)).normalized()
        a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
        h = math.sqrt(max(0.0, l1 * l1 - a * a))
        J = K + dvec * a + perp * h
        T2 = K + dvec * dist
        bones['calf_' + s].matrix = posed('calf_' + s, K, J)
        upd()
        bones['foot_' + s].matrix = posed('foot_' + s, J, T2)
        upd()
        base = follow.to_3x3() if follow is not None else Matrix.Identity(3)
        R = (base @ Quaternion((0, 1, 0), curl).to_matrix()).to_4x4()
        m = R @ rest['toes_' + s]
        m.translation = T2
        bones['toes_' + s].matrix = m
        upd()
        return (target - T2).length

    def key(frame):
        for pb in bones:
            pb.keyframe_insert('location', frame=frame, group=pb.name)
            pb.keyframe_insert('rotation_quaternion', frame=frame, group=pb.name)
            pb.keyframe_insert('scale', frame=frame, group=pb.name)

    def eval_z(mask=None):
        dg = bpy.context.evaluated_depsgraph_get()
        eo = mesh_ob.evaluated_get(dg)
        m = eo.to_mesh()
        co = np.zeros(len(m.vertices) * 3, np.float32)
        m.vertices.foreach_get('co', co)
        eo.to_mesh_clear()
        z = co.reshape(-1, 3)[:, 2]
        return float(z[mask].min() if mask is not None else z.min())

    def planted(s, dx=0.0, lift=0.0, dy=0.0):
        return F_rest[s] + Vector((dx, dy, lift))

    # ------------------------------------------------------------------ shared secondary motion
    def breathe(t, amp=1.0):
        ph = TAU * t
        move('pelvis', (0, 0, 0.0012 * amp * math.sin(ph)))
        rot('spine_01', (0, 1, 0), -0.010 * amp * math.sin(ph))

    report = {}
    leg_err = {}

    # ------------------------------------------------------------------ Idle
    def idle(t):
        ph = TAU * t
        reset()
        breathe(2 * t)
        rot('neck_01', (0, 1, 0), 0.03 * math.sin(ph))
        rot('neck_03', (0, 0, 1), 0.22 * math.sin(ph) + 0.05 * math.sin(3 * ph))
        rot('head', (0, 0, 1), 0.10 * math.sin(ph + 0.4))
        rot('head', (1, 0, 0), 0.10 * math.sin(2 * ph + 0.8))
        rot('head', (0, 1, 0), -0.05 * math.sin(2 * ph))
        rot('tail_01', (0, 0, 1), 0.06 * math.sin(3 * ph))
        rot('tail_02', (0, 0, 1), 0.16 * math.sin(3 * ph + 0.7))
        for s, sd in (('l', 1), ('r', -1)):
            rot('wing_' + s, (1, 0, 0), sd * 0.012 * (1 + math.sin(2 * ph)))
        e = 0.0
        for s in 'lr':
            e = max(e, leg(s, planted(s)))
        return e

    # ------------------------------------------------------------------ locomotion
    def gait(t, duty, half, lift, roll, bob, lean, run=False, headless=False):
        ph = TAU * t
        reset()
        if headless:
            # the body does not know it is dead yet: frantic, lurching, wings thrashing
            rot('pelvis', (0, 0, 1), 0.16 * math.sin(ph) + 0.05 * math.sin(3 * ph + 0.7))
            rot('pelvis', (1, 0, 0), 0.10 * math.sin(2 * ph + 1.3))
            rot('neck_01', (1, 0, 0), 0.35 * math.sin(2 * ph))
            rot('neck_01', (0, 1, 0), 0.25 * math.sin(3 * ph + 0.4))
            rot('neck_02', (0, 1, 0), -0.30 * math.sin(2 * ph + 0.9))
            rot('neck_02', (1, 0, 0), 0.25 * math.sin(ph + 2.0))
            for s_, sd_ in (('l', 1), ('r', -1)):
                rot('wing_' + s_, (1, 0, 0), sd_ * (0.75 + 0.45 * math.sin(2 * ph + (0.0 if sd_ > 0 else 1.1))))
                rot('wing_' + s_, (0, 0, 1), sd_ * 0.20 * math.sin(3 * ph + sd_))
                rot('wingtip_' + s_, (1, 0, 0), sd_ * (0.35 + 0.30 * math.sin(2 * ph - 0.7)))
            rot('tail_02', (0, 0, 1), 0.35 * math.sin(2 * ph))
        stance_l = 0.5 * duty  # mid stance of left foot at phase duty/2
        w = math.cos(TAU * (t - stance_l))          # +1 when left supports
        move('pelvis', (0, 0.006 * w * (0.5 if run else 1), bob * math.cos(2 * TAU * (t - stance_l)) - (0.012 if run else 0.0)))
        rot('pelvis', (1, 0, 0), -roll * w)
        rot('pelvis', (0, 0, 1), 0.06 * math.sin(TAU * (t - stance_l)) * (0.5 if run else 1))
        rot('pelvis', (0, 1, 0), lean)
        rot('spine_02', (1, 0, 0), 0.4 * roll * w)
        rot('neck_01', (0, 1, 0), (-0.25 if run else -0.06) + 0.04 * math.cos(2 * TAU * t))
        rot('neck_02', (0, 1, 0), (0.10 if run else 0.02))
        rot('neck_03', (1, 0, 0), 0.5 * roll * w)
        rot('head', (0, 1, 0), (0.18 if run else 0.02) - 0.035 * math.cos(2 * TAU * t))
        rot('tail_02', (0, 0, 1), 0.20 * w)
        rot('tail_01', (0, 1, 0), -0.06 if run else 0.0)
        for s, sd in (('l', 1), ('r', -1)):
            if headless:
                pass
            elif run:
                flap = 0.45 + 0.30 * math.sin(2 * ph)
                rot('wing_' + s, (1, 0, 0), sd * flap)
                rot('wing_' + s, (0, 0, 1), sd * 0.10 * math.sin(2 * ph))
                rot('wingtip_' + s, (1, 0, 0), sd * (0.20 + 0.20 * math.sin(2 * ph - 0.8)))
            else:
                rot('wing_' + s, (1, 0, 0), sd * 0.02)
        upd()
        err = 0.0
        for s, off in (('l', 0.0), ('r', 0.5)):
            phi = (t + off) % 1.0
            if phi < duty:
                dx = half - 2 * half * (phi / duty)
                lz = 0.0
                curl = 0.0
            else:
                u = (phi - duty) / (1 - duty)
                sm = u * u * (3 - 2 * u)
                dx = -half + 2 * half * sm
                lz = lift * math.sin(math.pi * u)
                curl = 0.9 * math.sin(math.pi * min(1.0, u * 1.15))
                # toes fold downward in the swing but never through the ground
                curl = min(curl, max(0.0, math.asin(max(0.0, min(1.0, (F_rest[s].z + lz - 0.004) / TOE_REACH))) - TOE_REST_DROP))
            sd = 1 if s == 'l' else -1
            rot('thigh_' + s, (0, 1, 0), -dx * 3.0)
            upd()
            err = max(err, leg(s, planted(s, dx, lz, -sd * 0.004 * math.sin(math.pi * min(1, phi / duty)) if phi < duty else 0.0), curl))
        return err

    def walk(t):
        return gait(t, duty=WALK['duty'], half=WALK['half'], lift=0.026, roll=0.11, bob=0.0035, lean=0.0)

    def run(t):
        return gait(t, duty=RUN['duty'], half=RUN['half'], lift=0.040, roll=0.07, bob=0.0060, lean=0.20, run=True)

    def headless_run(t):
        return gait(t, duty=HEADLESS['duty'], half=HEADLESS['half'], lift=0.042, roll=0.16, bob=0.0070, lean=0.10, run=True, headless=True)

    # ------------------------------------------------------------------ Peck / eat
    peck_k = [1.0]

    def peck(t):
        reset()
        k = peck_k[0]
        env = D.smoothstep(t / 0.28) * D.smoothstep((1 - t) / 0.28)
        dab = 0.0
        if 0.28 < t < 0.76:
            dab = math.sin(math.pi * (t - 0.28) / 0.48 * 4) ** 2
        breathe(t, 0.5)
        # Sagittal chain posed by target world angles (deg): neck reaches forward-down, bill steep.
        acc0 = 0.30 + 0.10
        rot('pelvis', (0, 1, 0), env * 0.30)
        rot('tail_01', (0, 1, 0), -env * 0.12)
        rot('spine_02', (0, 1, 0), env * 0.10)
        prev = acc0
        for bn, want in (('neck_01', -35 * k), ('neck_02', -50 * k), ('neck_03', -60 * k), ('head', -72 - 8 * dab)):
            acc = REST_ANGLE[bn] - math.radians(want)
            rot(bn, (0, 1, 0), env * (acc - prev))
            prev = acc
        rot('jaw', (0, 1, 0), env * 0.22 * dab)
        rot('tail_02', (0, 1, 0), -env * 0.20)
        e = 0.0
        for s in 'lr':
            e = max(e, leg(s, planted(s)))
        return e

    # ------------------------------------------------------------------ Quack
    def quack(t):
        reset()
        env = D.smoothstep(t / 0.25) * D.smoothstep((1 - t) / 0.30)
        q = max(0.0, math.sin(math.pi * min(1.0, max(0.0, (t - 0.18) / 0.62)) * 2)) ** 1.2
        breathe(t, 0.6)
        rot('neck_01', (0, 1, 0), -env * 0.10)
        rot('neck_02', (0, 1, 0), env * 0.06)
        rot('head', (0, 1, 0), -env * 0.20 - 0.06 * q)
        rot('jaw', (0, 1, 0), 0.40 * q)
        rot('tail_02', (0, 0, 1), 0.12 * q)
        for s, sd in (('l', 1), ('r', -1)):
            rot('wing_' + s, (1, 0, 0), sd * 0.05 * q)
        e = 0.0
        for s in 'lr':
            e = max(e, leg(s, planted(s)))
        return e

    # ------------------------------------------------------------------ Hit reaction
    def hit(t):
        reset()
        x = t * 0.4
        imp = math.sin(min(1.0, x / 0.06) * math.pi / 2) * math.exp(-max(0.0, x - 0.06) / 0.09) * D.smoothstep((1 - t) / 0.35)
        wob = math.sin(x * 38) * imp
        move('pelvis', (-0.002 * imp, 0, -0.002 * imp))
        rot('pelvis', (0, 1, 0), -0.09 * imp)
        rot('pelvis', (1, 0, 0), 0.10 * wob)
        rot('neck_01', (0, 1, 0), -0.30 * imp)
        rot('neck_02', (0, 1, 0), -0.20 * imp)
        rot('head', (0, 1, 0), 0.25 * imp)
        rot('head', (1, 0, 0), 0.15 * wob)
        rot('jaw', (0, 1, 0), 0.30 * imp)
        rot('tail_02', (0, 1, 0), -0.4 * imp)
        for s, sd in (('l', 1), ('r', -1)):
            rot('wing_' + s, (1, 0, 0), sd * 0.75 * imp)
            rot('wingtip_' + s, (1, 0, 0), sd * 0.35 * imp)
        e = 0.0
        for s in 'lr':
            e = max(e, leg(s, planted(s)))
        return e

    # ------------------------------------------------------------------ Death
    death_p = {'drop': 0.10, 'slump': 1.0, 'hdrop': 0.10}

    def headless_death(t, foot_lift=0.0):
        return death(t, foot_lift, headless=True)

    def death(t, foot_lift=0.0, headless=False):
        reset()
        if headless:
            # a last lurching run, then over onto its side, kicking, then still
            t0 = t
            run_phase = min(t0 / 0.30, 1.0)
            t = max(0.0, (t0 - 0.18) / 0.82)
            ph = TAU * 2 * run_phase
            rot('neck_01', (1, 0, 0), 0.4 * math.sin(ph) * (1 - D.smoothstep(t / 0.5)))
            rot('neck_02', (0, 1, 0), 0.3 * math.sin(1.5 * ph) * (1 - D.smoothstep(t / 0.5)))
        stag = D.smoothstep(t / 0.30)
        fall = D.smoothstep((t - 0.22) / 0.50)
        settle = D.smoothstep((t - 0.62) / 0.38)
        flap = math.sin(TAU * 2.2 * min(t, 0.62) / 0.62) * (1 - fall * 0.8) * D.smoothstep(t / 0.08)
        move('pelvis', (0.010 * stag, -0.04 * fall, -(death_p['hdrop'] if headless else death_p['drop']) * fall))
        rot('pelvis', (1, 0, 0), 1.30 * fall)
        rot('pelvis', (0, 1, 0), 0.12 * stag - 0.10 * fall)
        rot('spine_02', (1, 0, 0), 0.15 * fall)
        sl = 0.8 if headless else death_p['slump']
        rot('neck_01', (1, 0, 0), -sl * 0.40 * settle - 0.20 * fall)
        rot('neck_01', (0, 1, 0), -0.25 * stag * (1 - fall) + sl * 0.30 * settle)
        rot('neck_02', (1, 0, 0), -sl * 0.30 * settle)
        rot('neck_02', (0, 1, 0), sl * 0.15 * settle)
        rot('neck_03', (1, 0, 0), -sl * 0.20 * settle)
        rot('head', (1, 0, 0), -sl * 0.25 * settle)
        rot('head', (0, 1, 0), 0.15 * stag * (1 - fall))
        rot('jaw', (0, 1, 0), 0.18 * fall)
        rot('tail_02', (0, 1, 0), 0.25 * fall)
        for s, sd in (('l', 1), ('r', -1)):
            open_ = 0.9 * max(0.0, flap) * (1 - settle) + (0.25 * settle if s == 'l' else 0.05 * settle)
            rot('wing_' + s, (1, 0, 0), sd * open_)
            rot('wingtip_' + s, (1, 0, 0), sd * 0.4 * max(0.0, flap) * (1 - settle))
        upd()
        pelvis_delta = bones['pelvis'].matrix @ rest['pelvis'].inverted()
        e = 0.0
        release = D.smoothstep((t - 0.30) / 0.30)
        for s, sd in (('l', 1), ('r', -1)):
            buckle = 0.012 * D.smoothstep(t / 0.3)
            ground = planted(s, 0.004 * sd, 0.0)
            kick = Vector((0, 0, 0))
            if headless:
                # two dying kicks of the feet after the fall
                kk = math.sin(TAU * 2.0 * max(0.0, t - 0.55) / 0.30 + (0.0 if sd > 0 else 1.2)) * D.smoothstep((t - 0.52) / 0.06) * (1 - D.smoothstep((t - 0.80) / 0.12))
                kick = Vector((0.030 * kk, 0.0, 0.006 * kk))
            tucked = pelvis_delta @ (F_rest[s] + Vector((0.020 + 0.02 * (sd > 0), 0.010 * sd, 0.040)) + kick)
            target = ground.lerp(tucked, release)
            target.z += foot_lift * release
            # released feet may fold, but toes and claws never sink below the ground plane
            target.z = max(target.z, 0.004 + TOE_REACH * math.sin(min(1.4, 0.7 * release + TOE_REST_DROP)) if release > 0 else target.z)
            rot('thigh_' + s, (0, 1, 0), -0.4 * release)
            upd()
            # toes keep a world-level orientation (curled) so the folded foot cannot rotate into the ground
            err = leg(s, target, 0.7 * release)
            if release < 0.01:
                e = max(e, err)
        return e

    # ------------------------------------------------------------------ ground solves
    def solve(fn, t_samples, mask, goal, param, setter, lo, hi):
        for _ in range(14):
            mid = 0.5 * (lo + hi)
            setter(mid)
            z = 1e9
            for t in t_samples:
                fn(t)
                upd()
                z = min(z, eval_z(mask))
            if z > goal:
                lo = mid
            else:
                hi = mid
        val = 0.5 * (lo + hi)
        setter(val)
        return val

    scene.frame_set(1)
    arm.animation_data.action = bpy.data.actions.new('_solve')
    k = solve(peck, [0.30 + 0.48 * i / 12 for i in range(13)], bill_mask, 0.0030, 'k',
              lambda v: peck_k.__setitem__(0, v), 0.2, 1.8)
    report['peck_depth_scale'] = round(k, 4)
    drop = solve(death, [1.0], intact_mask & ~head_mask, 0.0005, 'drop', lambda v: death_p.__setitem__('drop', v), 0.0, 0.25)
    report['death_pelvis_drop_m'] = round(drop, 4)
    slump = solve(death, [1.0], head_mask, 0.0010, 'slump', lambda v: death_p.__setitem__('slump', v), 0.0, 2.5)
    report['death_neck_slump'] = round(slump, 4)
    hdrop = solve(headless_death, [1.0], headless_mask, 0.0005, 'hdrop', lambda v: death_p.__setitem__('hdrop', v), 0.0, 0.25)
    report['headless_death_pelvis_drop_m'] = round(hdrop, 4)
    bpy.data.actions.remove(arm.animation_data.action)

    fns = {'Duck_Idle': idle, 'Duck_Walk': walk, 'Duck_Run': run, 'Duck_Peck': peck,
           'Duck_Quack': quack, 'Duck_Hit': hit, 'Duck_Death': death,
           'Duck_HeadlessRun': headless_run, 'Duck_HeadlessDeath': headless_death}
    dying = {'Duck_Death': death, 'Duck_HeadlessDeath': headless_death}
    actions = {}
    for name, spec in D.ACTIONS.items():
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm.animation_data.action = act
        n = spec['frames']
        worst = 0.0
        for f in range(1, n + 1):
            scene.frame_set(f)
            t = (f - 1) / (n - 1)
            if spec['loop']:
                t = t % 1.0 if f < n else 0.0  # exact loop seam: last frame repeats frame 1
            worst = max(worst, fns[name](t))
            if name in dying:
                # keep released, folding feet above the ground plane (measured on the skinned mesh)
                lift = 0.0
                for _ in range(4):
                    upd()
                    z = eval_z(feet_mask)
                    if z > -0.0005:
                        break
                    lift += -z + 0.001
                    dying[name](t, lift)
                death_lifts.append(round(lift, 4))
            key(f)
        actions[name] = {'frames': [1, n], 'fps': D.FPS, 'duration_s': round((n - 1) / D.FPS, 6), 'loop': spec['loop'],
                         'root_motion': False,
                         'nominal_speed_cm_s': gait_speed_cm_s(name) if name in GAITS else 0,
                         'max_planted_foot_ik_error_m': round(worst, 6)}
    report['death_foot_lift_max_m'] = max(death_lifts) if death_lifts else 0.0
    actions['_solves'] = report
    arm.animation_data.action = bpy.data.actions['Duck_Idle']
    scene.frame_start = 1
    scene.frame_end = 61
    scene.frame_set(1)
    return actions
