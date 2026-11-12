"""Bare arms for characters whose shipped skin stops at the wrist (and the shoulder yoke): takes the arm faces of the
CC0 MakeHuman base mesh (same topology and UV layout as the shipped head/hand skin), poses them onto the rig's arm
with a two-bone rigid fit, welds them to the existing skin borders (matched by MakeHuman UV) and joins them into Skin."""
import bpy, bmesh, math
import numpy as np
from mathutils.kdtree import KDTree
from prlib import *; from garlib import sstep

def _load_obj(path):
    V = []; VT = []; F = []; g = None
    for l in open(path):
        p = l.split()
        if not p: continue
        if p[0] == 'v': V.append([float(x) for x in p[1:4]])
        elif p[0] == 'vt': VT.append([float(x) for x in p[1:3]])
        elif p[0] == 'g': g = p[1]
        elif p[0] == 'f' and (g == 'body' or (g or '').startswith('joint-')):
            F.append((g, [tuple(int(a) for a in q.split('/')[:2]) for q in p[1:]]))
    V = np.array(V); V = np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1) * .1
    return V, np.array(VT), F

def _key(uv): return (round(float(uv[0]), 4), round(float(uv[1]), 4))
def _frame(d, n):
    d = d / np.linalg.norm(d); n = n - d * (n @ d); n /= np.linalg.norm(n); return np.stack([d, n, np.cross(d, n)], 1)

def add_arms(sk, arm, manny, obj_path, frm=.3, bulk=.1, kmul=1.0):
    V, VT, F = _load_obj(obj_path)
    J = {}
    for g, f in F:
        if g.startswith('joint-'): J.setdefault(g, []).extend(a[0] - 1 for a in f)
    J = {k: V[sorted(set(v))].mean(0) for k, v in J.items()}
    body = [f for g, f in F if g == 'body']
    me = sk.data; uvl = me.uv_layers['UVMH']; co = co_np(me)
    have = set(); pos = {}
    for p in me.polygons:
        ks = [_key(uvl.data[li].uv) for li in p.loop_indices]; have.add(frozenset(ks))
        for k, vi in zip(ks, p.vertices): pos.setdefault(k, co[vi])
    Bn = arm.data.bones
    made = []
    for sg, sd in ((1, 'l'), (-1, 'r')):
        Sb, Eb, Wb = J['joint-%s-shoulder' % sd], J['joint-%s-elbow' % sd], J['joint-%s-hand' % sd]
        St, Et, Wt = [np.array(Bn[n + '_' + sd].head_local) for n in ('upperarm', 'lowerarm', 'hand')]
        dUb, dFb = (Eb - Sb), (Wb - Eb); LUb, LFb = np.linalg.norm(dUb), np.linalg.norm(dFb); dUb /= LUb; dFb /= LFb
        dUt, dFt = (Et - St), (Wt - Et); LUt, LFt = np.linalg.norm(dUt), np.linalg.norm(dFt); dUt /= LUt; dFt /= LFt
        nb = np.cross(dUb, dFb); nt = np.cross(dUt, dFt)
        FUb, FFb, FUt, FFt = _frame(dUb, nb), _frame(dFb, nb), _frame(dUt, nt), _frame(dFt, nt)
        # candidate faces: on the arm, not already in the shipped skin
        def arm_param(P):
            su = (P - Sb) @ dUb; du = np.linalg.norm((P - Sb) - np.outer(su, dUb), axis=1)
            sf = (P - Eb) @ dFb; df = np.linalg.norm((P - Eb) - np.outer(sf, dFb), axis=1)
            fore = sf > 0
            return np.where(fore & (df < du + .02), 1 + sf / LFb, su / LUb), np.where(fore, np.minimum(du, df), du)
        un, dist = arm_param(V)
        okv = (V[:, 0] * sg > .05) & (dist < .085) & (un > frm) & (un < 2.25)
        cand = [f for f in body if all(okv[a[0] - 1] for a in f) and frozenset(_key(VT[a[1] - 1]) for a in f) not in have]
        # keep the component(s) that touch the shipped skin border
        vkeys = {}
        for f in body:
            for a in f: vkeys.setdefault(a[0] - 1, set()).add(_key(VT[a[1] - 1]))
        weld = {vi: next(pos[k] for k in ks if k in pos) for vi, ks in vkeys.items() if any(k in pos for k in ks)}
        adj = {}
        for i, f in enumerate(cand):
            for a in f: adj.setdefault(a[0] - 1, []).append(i)
        seen = set(); stack = [i for i, f in enumerate(cand) if any((a[0] - 1) in weld for a in f)]
        while stack:
            i = stack.pop()
            if i in seen: continue
            seen.add(i)
            for a in cand[i]: stack.extend(j for j in adj[a[0] - 1] if j not in seen)
        faces = [cand[i] for i in sorted(seen)]
        vid = sorted({a[0] - 1 for f in faces for a in f}); remap = {v: i for i, v in enumerate(vid)}
        P = V[vid]
        wf = sstep(-.04, .04, (P - Eb) @ ((dUb + dFb) / np.linalg.norm(dUb + dFb)))
        def fit(k_u, k_f):
            lu = (P - Eb) @ FUb; lf = (P - Eb) @ FFb
            ku = np.interp(lu[:, 0] / LUb, [-1, -.5, 0], [k_u, (k_u + k_f) / 2 * (1 + bulk), k_f * (1 + bulk * .6)])
            kf = np.interp(lf[:, 0] / LFb, [0, .3, 1], [k_f * (1 + bulk * .6), k_f * (1 + bulk * .5), k_f])
            pu = Et + (lu * np.stack([np.full(len(P), LUt / LUb), ku, ku], 1)) @ FUt.T
            pf = Et + (lf * np.stack([np.full(len(P), LFt / LFb), kf, kf], 1)) @ FFt.T
            return pu * (1 - wf[:, None]) + pf * wf[:, None]
        Q = fit(1, 1)
        wi = np.array([i for i, v in enumerate(vid) if v in weld]); wt = np.array([weld[vid[i]] for i in wi])
        hand_end = wf[wi] > .5
        def rad(X, O, d): r = (X - O) - np.outer((X - O) @ d, d); return r
        k_f = np.linalg.norm(rad(wt[hand_end], Et, dFt), axis=1).mean() / np.linalg.norm(rad(Q[wi][hand_end], Et, dFt), axis=1).mean()
        k_u = k_f
        if (~hand_end).sum() > 8:
            k_u = np.linalg.norm(rad(wt[~hand_end], Et, dUt), axis=1).mean() / np.linalg.norm(rad(Q[wi][~hand_end], Et, dUt), axis=1).mean()
        k_f = float(np.clip(k_f, .7, 1.5)); k_u = float(np.clip(k_u, .7, 1.6)) * kmul
        Q = fit(k_u, k_f * (kmul if (~hand_end).sum() <= 8 else 1.0) if False else k_f)
        # forearm twist so the wrist ring lines up with the hand
        a_ = rad(wt[hand_end], Et, dFt); b_ = rad(Q[wi][hand_end], Et, dFt)
        ang = np.arctan2(np.cross(b_, a_) @ dFt, (a_ * b_).sum(1)); dth = float(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()))
        tw = np.clip(((Q - Et) @ dFt) / LFt, 0, 1) * dth
        r_ = rad(Q, Et, dFt); ax = Et + np.outer((Q - Et) @ dFt, dFt)
        Q = ax + r_ * np.cos(tw)[:, None] + np.cross(np.tile(dFt, (len(Q), 1)), r_) * np.sin(tw)[:, None]
        # residual: pull the borders exactly onto the shipped skin, fading over 9 cm
        delta = wt - Q[wi]
        kd = KDTree(len(wi))
        for i, q in enumerate(Q[wi]): kd.insert(q, i)
        kd.balance()
        for i in range(len(Q)):
            nn = kd.find_n(Q[i], 4); w = np.array([1 / (d + 1e-4) ** 2 for _, _, d in nn]); dl = sum(delta[j] * ww for (_, j, _), ww in zip(nn, w)) / w.sum()
            Q[i] = Q[i] + dl * float(sstep(.09, 0.0, nn[0][2]))
        Q[wi] = wt
        log('arm', sd, 'faces', len(faces), 'verts', len(vid), 'welded', len(wi), 'k_u', round(k_u, 3), 'k_f', round(k_f, 3), 'twist deg', round(math.degrees(dth), 1), 'residual max', float(np.linalg.norm(delta, axis=1).max()))
        o = new_obj('ArmSkin_' + sd, Q, [[remap[a[0] - 1] for a in f] for f in faces])
        ul = o.data.uv_layers.new(name='UVMH')
        for p, f in zip(o.data.polygons, faces):
            for li, a in zip(p.loop_indices, f): ul.data[li].uv = VT[a[1] - 1]
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
        # orientation check against the arm axis
        o.data.update(); c = co_np(o.data); nrm = normals_np(o.data)
        if (rad(c, Et, dFt) * nrm).sum() < 0:
            bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
        dt = o.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = manny; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
        activate(o); bpy.ops.object.datalayout_transfer(modifier='dt'); bpy.ops.object.modifier_apply(modifier='dt')
        o.data.materials.append(sk.data.materials[0]); made.append(o)
    for l in list(sk.data.uv_layers):
        if l.name != 'UVMH': sk.data.uv_layers.remove(l)
    nm = sk.name; sk2 = join([sk] + made, nm)
    bm = bmesh.new(); bm.from_mesh(sk2.data); n0 = len(bm.verts); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5); n1 = len(bm.verts)
    bm.to_mesh(sk2.data); bm.free(); smooth_shade(sk2)
    log('arms joined; welded verts', n0 - n1, 'skin tris', tri_count(sk2))
    return sk2

def add_chest(sk, arm, manny, obj_path, vol=None, z_lo=.44, x_max=.15, inset=.004):
    """Neck base, collarbones and upper chest / upper back from the CC0 MakeHuman base mesh, welded to the shipped neck
    border (matched by MakeHuman UV), scaled to the neck ring and kept just inside the garment volume."""
    V, VT, F = _load_obj(obj_path); body = [f for g, f in F if g == 'body']
    me = sk.data; uvl = me.uv_layers['UVMH']; co = co_np(me); have = set(); pos = {}
    for p in me.polygons:
        ks = [_key(uvl.data[li].uv) for li in p.loop_indices]; have.add(frozenset(ks))
        for k, vi in zip(ks, p.vertices): pos.setdefault(k, co[vi])
    hz = co[co[:, 2] > 1.40][:, 2]; sk_neck_top = float(hz.min()) + .06
    okv = (np.abs(V[:, 0]) < x_max) & (V[:, 2] > z_lo) & (V[:, 2] < .612)      # below the jaw: never the mouth cavity
    cand = [f for f in body if all(okv[a[0] - 1] for a in f) and frozenset(_key(VT[a[1] - 1]) for a in f) not in have]
    vkeys = {}
    for f in body:
        for a in f: vkeys.setdefault(a[0] - 1, set()).add(_key(VT[a[1] - 1]))
    weld = {vi: next(pos[k] for k in ks if k in pos) for vi, ks in vkeys.items() if any(k in pos for k in ks) and okv[vi]}
    weld = {vi: p for vi, p in weld.items() if p[2] > 1.40 and abs(p[0]) < .09 and p[2] < sk_neck_top}        # the neck ring only, never the arms
    adj = {}
    for i, f in enumerate(cand):
        for a in f: adj.setdefault(a[0] - 1, []).append(i)
    seen = set(); stack = [i for i, f in enumerate(cand) if any((a[0] - 1) in weld for a in f)]
    while stack:
        i = stack.pop()
        if i in seen: continue
        seen.add(i)
        for a in cand[i]: stack.extend(j for j in adj[a[0] - 1] if j not in seen)
    faces = [cand[i] for i in sorted(seen)]
    if not faces: log('add_chest: no faces found'); return sk
    vid = sorted({a[0] - 1 for f in faces for a in f}); remap = {v: i for i, v in enumerate(vid)}; P = V[vid]
    wi = np.array([i for i, v in enumerate(vid) if v in weld]); wt = np.array([weld[vid[i]] for i in wi])
    cb, ct = P[wi].mean(0), wt.mean(0); s = np.linalg.norm(wt - ct, axis=1).mean() / np.linalg.norm(P[wi] - cb, axis=1).mean()
    Q = (P - cb) * s + ct
    delta = wt - Q[wi]; kd = KDTree(len(wi))
    for i, q in enumerate(Q[wi]): kd.insert(q, i)
    kd.balance()
    for i in range(len(Q)):
        nn = kd.find_n(Q[i], 4); w = np.array([1 / (d + 1e-4) ** 2 for _, _, d in nn]); dl = sum(delta[j] * ww for (_, j, _), ww in zip(nn, w)) / w.sum()
        Q[i] = Q[i] + dl * float(sstep(.11, 0.0, nn[0][2]))
    Q[wi] = wt
    if vol is not None:    # stay under the dress: never closer than 'inset' to the garment volume's surface from inside
        vb = bvh_of(vol); moved = 0
        for i in range(len(Q)):
            if i in set(wi.tolist()): continue
            loc, nrm, _, dist = vb.find_nearest(Vector(Q[i]))
            if loc is None: continue
            sd = (Q[i] - np.array(loc)) @ np.array(nrm); fade = float(sstep(ct[2] - .012, ct[2] - .05, Q[i][2]))   # the neck column itself is left alone
            if sd > -inset and fade > 0:
                Q[i] = Q[i] + (np.array(loc) - np.array(nrm) * inset - Q[i]) * fade; moved += 1
        log('chest verts pulled inside the garment volume', moved)
    log('chest', 'faces', len(faces), 'verts', len(vid), 'welded', len(wi), 'scale', round(float(s), 3), 'residual max', float(np.linalg.norm(delta, axis=1).max()), 'z range', float(Q[:, 2].min()), float(Q[:, 2].max()))
    o = new_obj('ChestSkin', Q, [[remap[a[0] - 1] for a in f] for f in faces])
    ul = o.data.uv_layers.new(name='UVMH')
    for p, f in zip(o.data.polygons, faces):
        for li, a in zip(p.loop_indices, f): ul.data[li].uv = VT[a[1] - 1]
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    o.data.update(); c = co_np(o.data); nrm = normals_np(o.data); ax = c.copy(); ax[:, 0] = 0; ax[:, 1] = ct[1]
    if ((c - ax) * nrm).sum() < 0:
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    dt = o.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = manny; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    activate(o); bpy.ops.object.datalayout_transfer(modifier='dt'); bpy.ops.object.modifier_apply(modifier='dt')
    o.data.materials.append(sk.data.materials[0])
    for l in list(sk.data.uv_layers):
        if l.name != 'UVMH': sk.data.uv_layers.remove(l)
    nm = sk.name; sk2 = join([sk, o], nm)
    bm = bmesh.new(); bm.from_mesh(sk2.data); n0 = len(bm.verts); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5); n1 = len(bm.verts)
    bm.to_mesh(sk2.data); bm.free(); smooth_shade(sk2); log('chest joined; welded verts', n0 - n1, 'skin tris', tri_count(sk2))
    return sk2
