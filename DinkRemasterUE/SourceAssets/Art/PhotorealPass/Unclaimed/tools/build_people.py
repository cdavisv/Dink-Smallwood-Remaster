"""Civilian NPC families built on the CC0 MakeHuman base mesh (people.py): merchants, peasant, old man, girl, gnome wizard, king.

  tools/bl.sh build_people.py <name[,name]|all> [review|final]
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import mhlib as M
import people as Pp
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_people.py'
SKIN_M = os.path.join(M.MH, 'skins', 'young_caucasian_male', 'young_lightskinned_male_diffuse.png')
SKIN_F = os.path.join(M.MH, 'skins', 'middleage_caucasian_female', 'middleage_lightskinned_female_diffuse.png')


# ---------------------------------------------------------------------------------------------- parts
def body_pts(P):
    if not hasattr(P, '_bp'):
        P._bp = P.V[sorted({i for g, vi, ti in P.B.F if g == 'body' for i in vi})]
    return P._bp


def lip_z(P):
    """height of the lip line (the base mesh's mouth joint sits higher, behind the nose)"""
    return P.zJ('jaw') + 0.040 * P.k * P.spec.get('build', {}).get('head', 1.0)


def head_ring(P, z):
    """centre and half-sizes of the head outline at height z"""
    Q = body_pts(P); q = Q[(np.abs(Q[:, 2] - z) < 0.012 * P.k) & (np.abs(Q[:, 0]) < 0.14 * P.k)]; return float(q[:, 0].mean()), float((q[:, 1].min() + q[:, 1].max()) / 2), float((q[:, 0].max() - q[:, 0].min()) / 2), float((q[:, 1].max() - q[:, 1].min()) / 2)


def place(ob, M_):
    ob.matrix_world = M_; L.apply_xf(ob); return ob


def lo_of(hi, name, tris, c):
    lo = L.dup(hi, name, c); lo.data.materials.clear()
    if L.tri_count(lo) > tris:
        L.mod(lo, 'DECIMATE', ratio=tris / L.tri_count(lo)); L.apply_mods(lo)
    L.clean_mesh(lo); lo.data.polygons.foreach_set('use_smooth', [True] * len(lo.data.polygons))
    for l_ in list(lo.data.uv_layers):
        lo.data.uv_layers.remove(l_)
    L.smart_uv(lo, angle=66, margin=0.004); return lo


def cowl(P, col, radius=0.25, roll=0.017):
    """short shoulder cape with a rolled collar (the cape of a hood worn down): hangs over the shoulder caps and the top of the chest and back"""
    k = P.k; nk = P.J['neck'] + np.array([0, 0.0, -0.012 * k]); dist = lambda Q: np.linalg.norm((Q - nk) * np.array([1.0, 1.0, 1.25]), axis=-1); mat = Pp.cloth_mat('cowl', col, weave=1.3, dirt=0.1, rough=0.9, worn=0.7)
    P.piece('cowl', 'helper-tights', lambda Q: dist(Q) < radius * k, lambda Q: 0.017 + 0.022 * smoothstep(0.07 * k, radius * k, dist(Q)), mat, smooth=8, thick=0.006, folds=Pp.fold_fn(k, drape=0.007))
    if not roll:
        return
    cx, cy, rx, ry = head_ring(P, P.zJ('neck') + 0.012 * k)
    for hi_ in (False, True):
        o = L.ring('collar' + ('_hi' if hi_ else ''), 1.0, roll * k, P.hi if hi_ else P.lo, seg=64 if hi_ else 20, sides=14 if hi_ else 7, squash=0.85); Q = L.co(o); r = np.hypot(Q[:, 0], Q[:, 1]); th = np.arctan2(Q[:, 1], Q[:, 0])
        Q[:, 0] = cx + np.cos(th) * (rx + 0.012 * k + (r - 1.0)); Q[:, 1] = cy + 0.004 * k + np.sin(th) * (ry + 0.012 * k + (r - 1.0)); Q[:, 2] += P.zJ('neck') - 0.004 * k - 0.02 * k * np.sin(th); L.set_co(o, Q)
        if hi_:
            L.displace_np(o, Pp.fold_fn(k, drape=0.004)); hi = o
        else:
            lo = o
    P.solid(lo, hi, mat)


def buckle(P, waist, belt):
    k = P.k; Q = L.co(belt); q = Q[(np.abs(Q[:, 0]) < 0.02 * k) & (Q[:, 1] < P.J['pelvis'][1])]; y = float(q[:, 1].min()); m = Pp.gold_mat('brass')
    for hi_ in (False, True):
        o = L.ring('buckle' + ('_hi' if hi_ else ''), 0.017 * k, 0.0035 * k, P.hi if hi_ else P.lo, seg=32 if hi_ else 10, sides=10 if hi_ else 5); place(o, Matrix.Translation((0, y - 0.002 * k, waist)) @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Diagonal((1.0, 1.25, 1.0, 1.0)))
        if hi_:
            hi = o
        else:
            lo = o
    P.solid(lo, hi, m, bone='pelvis')


def pouch(P, waist, belt, side=-1, col=(0.14, 0.075, 0.035)):
    """drawstring purse hanging from the belt"""
    k = P.k; Q = L.co(belt); a0 = math.radians(-90 + side * -55); q = Q[np.abs(np.angle(np.exp(1j * (np.arctan2(Q[:, 1] - Q[:, 1].mean(), Q[:, 0]) - a0)))) < 0.2]; c = q.mean(0); out = np.array([math.cos(a0), math.sin(a0), 0.0]); c = c + out * 0.022 * k
    prof = [(0.0, -0.075), (0.02, -0.074), (0.036, -0.062), (0.04, -0.04), (0.034, -0.018), (0.018, -0.006), (0.013, 0.0), (0.02, 0.012), (0.012, 0.014), (0.0, 0.014)]
    hi = L.lathe('pouch_hi', [(r * k, z * k) for r, z in prof], seg=40, c=P.hi); L.subsurf(hi, 2); place(hi, Matrix.Translation(tuple(c)) @ Matrix.Diagonal((1.0, 0.75, 1.0, 1.0))); L.displace_np(hi, lambda Q_: 0.002 * k * (fbm(Q_, 3, 50 / k, 3) - 0.5) + 0.0015 * k * np.sin(np.arctan2(Q_[:, 1] - c[1], Q_[:, 0] - c[0]) * 9) * smoothstep(c[2] - 0.03 * k, c[2], Q_[:, 2]))
    lo = L.lathe('pouch', [(r * k, z * k) for r, z in prof], seg=10, c=P.lo); place(lo, Matrix.Translation(tuple(c)) @ Matrix.Diagonal((1.0, 0.75, 1.0, 1.0))); P.solid(lo, hi, Pp.leather_mat('pouch', col), bone='pelvis')


def palm(P, sd):
    a = P.J[sd + '-hand']; b = P.J.get(sd + '-finger-3-1', a); return (a + b) / 2


def staff(P, sd, z0, z1, rad=0.014, col=(0.22, 0.14, 0.075), lean=(0.0, 0.0), curve=0.0, name='staff'):
    """a pole standing through the hand (rigid to that hand)"""
    k = P.k; c = palm(P, sd) + np.array([0.0, -0.022 * k, 0.0]); pts = []; n = 24
    for i in range(n + 1):
        t = i / n; z = z0 + (z1 - z0) * t; dz = z - c[2]; pts.append((c[0] + lean[0] * dz + 0.006 * k * math.sin(t * 9.0), c[1] + lean[1] * dz + 0.005 * k * math.sin(t * 7.0 + 1.0) - curve * k * max(0.0, t - 0.75) ** 2 * 16, z))
    rr = [rad * k * (1.0 - 0.25 * i / n) for i in range(n + 1)]; hi = L.tube(name + '_hi', pts, rr, sides=20, c=P.hi); L.subsurf(hi, 2); L.displace_np(hi, lambda Q: 0.0015 * k * (fbm(Q * np.array([1, 1, 0.1]), 5, 90 / k, 3) - 0.5))
    lo = L.tube(name, pts[::3], rr[::3], sides=8, c=P.lo); P.solid(lo, hi, Pp.wood_mat(name, col), bone='hand_' + sd); return lo


def straw_hat(P, tilt=-8.0):
    k = P.k * P.spec.get('build', {}).get('head', 1.0); zr = P.zJ('head-2') - 0.062 * k; cx, cy, rx, ry = head_ring(P, zr); s_ = (rx + 0.004 * k) / 0.086
    prof = [(0, 0.098), (0.04, 0.095), (0.074, 0.08), (0.089, 0.05), (0.092, 0.012), (0.12, 0.002), (0.17, -0.008), (0.218, -0.026), (0.216, -0.031), (0.17, -0.014), (0.12, -0.005), (0.087, 0.0), (0.084, 0.05), (0.07, 0.073), (0.0, 0.09)]
    Mx = Matrix.Translation((cx, cy, zr)) @ Matrix.Rotation(math.radians(tilt), 4, 'X') @ Matrix.Diagonal((1.0, (ry + 0.004 * k) / (rx + 0.004 * k), 1.0, 1.0)); prof = [(r * s_, z * s_) for r, z in prof]
    hi = L.lathe('straw_hat_hi', prof, seg=96, c=P.hi); L.subsurf(hi, 1); Q = L.co(hi); r = np.hypot(Q[:, 0], Q[:, 1]); Q[:, 2] += smoothstep(0.1 * s_, 0.22 * s_, r) * 0.012 * k * (fbm(Q, 3, 14 / k, 2) - 0.5) * 2; L.set_co(hi, Q)
    t = Pp.straw_mat('straw'); hi.data.materials.append(t); lo = L.lathe('straw_hat', prof, seg=20, c=P.lo); Q = L.co(lo); r = np.hypot(Q[:, 0], Q[:, 1]); Q[:, 2] += smoothstep(0.1 * s_, 0.22 * s_, r) * 0.012 * k * (fbm(Q, 3, 14 / k, 2) - 0.5) * 2; L.set_co(lo, Q)
    # the straw pattern is concentric about the hat axis: the dense source is baked before it is moved onto the head, through a mapping of its own
    mp = next(n for n in t.node_tree.nodes if n.type == 'TEX_COORD'); mp.object = bpy.data.objects.new('hat_axis', None); L.link(mp.object, P.hi); mp.object.matrix_world = Mx
    place(hi, Mx); place(lo, Mx); P.solid(lo, hi, None, bone='head'); P.trim_hair(lambda Q_: Q_[2] > zr + 0.004 * k); return lo


def wizard_hat(P, col, stars):
    k = P.k * P.spec.get('build', {}).get('head', 1.0); zr = P.zJ('head-2') - 0.058 * k; cx, cy, rx, ry = head_ring(P, zr); s_ = (rx + 0.005 * k) / 0.088
    prof = [(0, 0.40), (0.012, 0.36), (0.03, 0.28), (0.058, 0.16), (0.082, 0.065), (0.093, 0.014), (0.118, 0.0), (0.165, -0.014), (0.163, -0.02), (0.112, -0.007), (0.088, 0.0), (0.08, 0.06), (0.0, 0.10)]; prof = [(r * s_, z * s_) for r, z in prof]
    Mx = Matrix.Translation((cx, cy, zr)) @ Matrix.Rotation(math.radians(-10), 4, 'X') @ Matrix.Diagonal((1.0, (ry + 0.005 * k) / (rx + 0.005 * k), 1.0, 1.0))

    def bend(o):
        Q = L.co(o); t = np.clip(Q[:, 2] / (0.40 * s_), 0, 1); Q[:, 1] += 0.16 * s_ * t ** 2.2; Q[:, 0] += 0.05 * s_ * t ** 3; Q[:, 2] -= 0.05 * s_ * t ** 3; L.set_co(o, Q); return o
    hi = bend(L.lathe('wizard_hat_hi', prof, seg=64, c=P.hi)); L.subsurf(hi, 2); L.displace_np(hi, lambda Q: 0.004 * k * (fbm(Q * np.array([1, 1, 0.5]), 3, 20 / k, 3) - 0.5) + 0.004 * k * np.sin(Q[:, 2] * 70 / k + 3 * fbm(Q, 5, 8 / k, 2)) * smoothstep(0.1 * s_, 0.2 * s_, Q[:, 2]))
    lo = bend(L.lathe('wizard_hat', prof, seg=18, c=P.lo)); place(hi, Mx); place(lo, Mx)
    P.solid(lo, hi, Pp.cloth_mat('hat', col, weave=1.2, dirt=0.0, worn=0.6, pattern=(stars, 34.0 / k, 0.95)), bone='head'); P.trim_hair(lambda Q_: Q_[2] > zr + 0.004 * k); return lo


def crown(P):
    k = P.k * P.spec.get('build', {}).get('head', 1.0); zr = P.zJ('head-2') - 0.05 * k; cx, cy, rx, ry = head_ring(P, zr); Mx = Matrix.Translation((cx, cy, zr)) @ Matrix.Rotation(math.radians(-6), 4, 'X'); gm = Pp.gold_mat('crown_gold')

    def band(nu, name, c):
        V = []; F = []
        for i in range(nu):
            a = 2 * math.pi * i / nu; tri = 1 - abs(((a * 8 / (2 * math.pi)) % 1.0) * 2 - 1); h = (0.028 + 0.05 * tri ** 1.4) * k
            for (dr, z) in ((0.003, -0.012 * k), (0.004, 0.006 * k), (0.002, h), (-0.002, h), (-0.004, 0.006 * k), (-0.003, -0.012 * k)):
                V.append(((rx + 0.006 * k + dr * k) * math.cos(a), (ry + 0.006 * k + dr * k) * math.sin(a), z))
        for i in range(nu):
            i1 = (i + 1) % nu
            for j in range(6):
                j1 = (j + 1) % 6; F.append((i * 6 + j, i1 * 6 + j, i1 * 6 + j1, i * 6 + j1))
        o = L.new_obj(name, V, F, c); L.fix_normals(o); return o
    hi = band(256, 'crown_hi', P.hi); hi.data.materials.append(gm); lo = band(32, 'crown', P.lo); parts_hi = [hi]; parts_lo = [lo]; red = NT('ruby'); red.set(base=(0.5, 0.01, 0.015), rough=0.12, coat=1.0)
    for i in range(8):
        a = 2 * math.pi * (i + 0.5) / 8
        for hi_ in (True, False):
            j = L.icosphere('jewel', 0.0075 * k, 3 if hi_ else 1, P.hi if hi_ else P.lo, scale=(1, 0.6, 1.2)); place(j, Matrix.Translation(((rx + 0.011 * k) * math.cos(a), (ry + 0.011 * k) * math.sin(a), 0.004 * k)) @ Matrix.Rotation(a + math.pi / 2, 4, 'Z'))
            b = L.icosphere('ball', 0.0055 * k, 3 if hi_ else 1, P.hi if hi_ else P.lo); place(b, Matrix.Translation(((rx + 0.006 * k) * math.cos(a), (ry + 0.006 * k) * math.sin(a), 0.08 * k)))
            if hi_:
                j.data.materials.append(red.mat); b.data.materials.append(gm); parts_hi += [j, b]
            else:
                parts_lo += [j, b]
    hi = L.join(parts_hi, 'crown_hi'); lo = L.join(parts_lo, 'crown'); place(hi, Mx); place(lo, Mx); P.solid(lo, hi, None, bone='head'); return lo


def beard(P, length, col, moustache=True, width=1.0):
    """solid beard: the jaw, chin and cheeks of the face grown outwards, fused with a hanging mass below the chin"""
    hs = P.k * P.spec.get('build', {}).get('head', 1.0); zm = lip_z(P); yc = float(P.J['jaw'][1]) - 0.006 * hs; zc = float(P.J['jaw'][2]) + 0.008 * hs            # chin point

    def keep(Qc):
        dz = (Qc[2] - zm) / hs; ax = abs(Qc[0]) / hs; y = (Qc[1] - yc) / hs
        if y > 0.115 or Qc[2] < zc - 0.05 * hs:
            return False
        if moustache and 0.004 < dz < 0.027 and ax < 0.048 and y < 0.06:
            return True
        if ax < 0.03 and dz > -0.024:
            return False
        return dz < -0.012 + 0.045 * smoothstep(0.03, 0.062, ax) and dz > -0.115
    sh, _ = P.B.mesh('beard_sheet', {'body'}, P.hi, V=P.V, keep=keep); Qs = L.co(sh); N = L.vnormals(sh); L.set_co(sh, Qs + N * 0.009 * hs); L.mod(sh, 'SOLIDIFY', thickness=0.016 * hs, offset=-1.0); L.apply_mods(sh)
    for l_ in list(sh.data.uv_layers):
        sh.data.uv_layers.remove(l_)
    parts = [sh]
    if length > 0.02:
        w = width; rows = [(0, yc + 0.03 * hs, zc + 0.035 * hs, 0.046 * hs * w, 0.03 * hs, 2.4), (0, yc + 0.016 * hs, zc - 0.012 * hs, 0.052 * hs * w, 0.034 * hs, 2.4), (0, yc + 0.004 * hs, zc - 0.5 * length, 0.042 * hs * w, 0.027 * hs, 2.2), (0, yc - 0.012 * hs, zc - length, 0.01 * hs, 0.008 * hs, 2.0)]
        parts.append(L.sweep('beard_hang', rows, nu=20, nv=20, c=P.hi, up=(0, 1, 0)))
    hi = L.join(parts, 'beard_hi') if len(parts) > 1 else parts[0]; hi.name = 'beard_hi'; L.mod(hi, 'REMESH', mode='VOXEL', voxel_size=0.003 * hs, adaptivity=0.0, use_smooth_shade=True); L.apply_mods(hi); L.mod(hi, 'SMOOTH', factor=0.5, iterations=5); L.apply_mods(hi)
    L.displace_np(hi, lambda Q_: 0.004 * hs * (fbm(Q_ * np.array([1.0, 1.0, 0.12]), 3, 160 / hs, 3) - 0.5) + 0.004 * hs * (fbm(Q_, 9, 22 / hs, 2) - 0.5)); lo = lo_of(hi, 'beard', 700, P.lo); P.solid(lo, hi, Pp.hairmass_mat('beard', col), bone='head'); return lo


def basket(P, sd='l'):
    k = P.k; c = palm(P, sd) + np.array([0.0, -0.01 * k, -0.19 * k]); prof = [(0.0, 0.0), (0.06, 0.0), (0.085, 0.03), (0.095, 0.085), (0.1, 0.09), (0.096, 0.094), (0.088, 0.086), (0.078, 0.032), (0.055, 0.008), (0.0, 0.008)]; mat = Pp.straw_mat('wicker', (0.42, 0.27, 0.11))
    hi = L.lathe('basket_hi', [(r * k, z * k) for r, z in prof], seg=64, c=P.hi); L.subsurf(hi, 1); lo = L.lathe('basket', [(r * k, z * k) for r, z in prof], seg=14, c=P.lo); hs_ = []
    for hi_ in (True, False):
        n = 24 if hi_ else 8; pts = [(0.092 * k * math.cos(math.pi * i / n), 0.0, 0.088 * k + 0.105 * k * math.sin(math.pi * i / n)) for i in range(n + 1)]; h = L.tube('handle', pts, 0.006 * k, sides=10 if hi_ else 5, c=P.hi if hi_ else P.lo); hs_.append(h)
    hi = L.join([hi, hs_[0]], 'basket_hi'); lo = L.join([lo, hs_[1]], 'basket'); mp = next(n for n in mat.node_tree.nodes if n.type == 'TEX_COORD'); mp.object = bpy.data.objects.new('basket_axis', None); L.link(mp.object, P.hi); mp.object.matrix_world = Matrix.Translation(tuple(c))
    cloth = L.icosphere('basket_cloth_hi', 0.08 * k, 4, P.hi, scale=(1, 1, 0.45)); place(cloth, Matrix.Translation((0, 0, 0.07 * k))); L.displace_np(cloth, lambda Q: 0.008 * k * (fbm(Q, 3, 30 / k, 3) - 0.5)); cloth.data.materials.append(Pp.cloth_mat('basket_cloth', (0.75, 0.2, 0.2), dirt=0.0, pattern=((0.9, 0.85, 0.8), 60.0 / k, 0.9)))
    hi.data.materials.append(mat); cl = lo_of(cloth, 'basket_cloth', 120, P.lo); hi = L.join([hi, cloth], 'basket_hi'); lo = L.join([lo, cl], 'basket')
    for l_ in list(lo.data.uv_layers):
        lo.data.uv_layers.remove(l_)
    place(hi, Matrix.Translation(tuple(c))); place(lo, Matrix.Translation(tuple(c))); P.solid(lo, hi, None, bone='hand_' + sd); return lo


def flowers(P, sd='r'):
    """a picked bunch of white flowers held in the fist"""
    k = P.k; c = palm(P, sd) + np.array([0.0, -0.015 * k, 0.0]); rng = np.random.RandomState(5); his = []; green = NT('stem'); green.set(base=green.mix(green.noise(60, 3, 0.6), (0.05, 0.16, 0.03), (0.12, 0.3, 0.06)), rough=0.5)
    wt = NT('petal'); n = wt.noise(260 / k, 3, 0.6); wt.set(base=wt.mix(wt.ramp(n, [(0.35, 0.0), (0.7, 1.0)]), (0.78, 0.76, 0.66), (0.93, 0.92, 0.88)), rough=0.6, sss=0.2, sss_scale=0.004); ye = NT('pollen'); ye.set(base=(0.75, 0.5, 0.05), rough=0.7)
    for i in range(9):
        a = rng.uniform(0, 2 * math.pi); sp_ = rng.uniform(0.25, 1.0); top = c + np.array([math.cos(a) * 0.06 * k * sp_, math.sin(a) * 0.05 * k * sp_ - 0.02 * k, (0.15 + rng.uniform(-0.03, 0.03)) * k]); bot = c + np.array([math.cos(a) * 0.006 * k, math.sin(a) * 0.006 * k, -0.07 * k])
        st = L.tube('stem', [tuple(bot + (top - bot) * t + np.array([0, 0, 0.0])) for t in np.linspace(0, 1, 6)], 0.0022 * k, sides=6, c=P.hi); st.data.materials.append(green.mat); his.append(st)
        fl = L.icosphere('bloom', 0.021 * k, 3, P.hi, scale=(1, 1, 0.55)); Q = L.co(fl); th = np.arctan2(Q[:, 1], Q[:, 0]); r = np.hypot(Q[:, 0], Q[:, 1]); pet = 1.0 + 0.28 * np.cos(th * 7) * smoothstep(0.004 * k, 0.018 * k, r); Q[:, 0] *= pet; Q[:, 1] *= pet; Q[:, 2] += 0.3 * r; L.set_co(fl, Q)
        d = (top - bot) / np.linalg.norm(top - bot); rot = Vector((0, 0, 1)).rotation_difference(Vector(d)).to_matrix().to_4x4(); place(fl, Matrix.Translation(tuple(top)) @ rot); fl.data.materials.append(wt.mat); his.append(fl)
        ce = L.icosphere('centre', 0.006 * k, 2, P.hi); place(ce, Matrix.Translation(tuple(top + d * 0.006 * k))); ce.data.materials.append(ye.mat); his.append(ce)
        if i % 2 == 0:
            lf = L.icosphere('leaf', 0.03 * k, 2, P.hi, scale=(0.35, 1.0, 0.06)); mid = bot + (top - bot) * 0.55; place(lf, Matrix.Translation(tuple(mid)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(math.radians(50), 4, 'X')); lf.data.materials.append(green.mat); his.append(lf)
    hi = L.join(his, 'flowers_hi'); lo = lo_of(hi, 'flowers', 500, P.lo); P.solid(lo, hi, None, bone='hand_' + sd); return lo


def shoes(P, top, col=(0.085, 0.05, 0.03)):
    return P.boots(top, Pp.leather_mat('boots', col))


# ---------------------------------------------------------------------------------------------- outfits
def robe_parts(P, col, hem, trim=None, sleeves=None, flare=1.22, ripple=(9, 0.012), belt='leather', sleeve_end=None, pattern=None, dirt=0.35, name='tunic', loose_=0.012):
    """the common cut: a loose tunic body with sleeves (cut from the body-suit helper), a hanging skirt from the waist, and a belt over the join"""
    k = P.k; waist = P.zJ('spine-3') + 0.015 * k
    loose = lambda Q: loose_ + 0.010 * smoothstep(0.20 * k, 0.26 * k, np.abs(Q[:, 0])) - (loose_ - 0.006) * np.exp(-((Q[:, 2] - waist) / (0.035 * k)) ** 2)
    keep = (lambda Q: Q[2] > waist - 0.03 * k) if sleeve_end is None else (lambda Q: Q[2] > waist - 0.03 * k and abs(Q[0]) < sleeve_end)
    if sleeves:
        sx = abs(P.J['l-shoulder'][0]) + 0.035 * k; body = P.piece(name, 'helper-tights', lambda Q: keep(Q) and abs(Q[0]) < sx + 0.012 * k, loose, Pp.cloth_mat(name, col, hem_z=hem, dirt=0.2, pattern=pattern), smooth=5, folds=Pp.fold_fn(k, belt=waist))
        P.piece('sleeves', 'helper-tights', lambda Q: keep(Q) and abs(Q[0]) > sx - 0.012 * k, lambda Q: loose(Q) + 0.004, Pp.cloth_mat('sleeves', sleeves, dirt=0.15), smooth=5, folds=Pp.fold_fn(k, sleeves=0.005))
    else:
        body = P.piece(name, 'helper-tights', keep, loose, Pp.cloth_mat(name, col, hem_z=hem, dirt=0.2, pattern=pattern), smooth=5, folds=Pp.fold_fn(k, belt=waist, sleeves=0.004))
    P.skirt(name + '_skirt', waist - 0.01 * k, hem, Pp.cloth_mat(name + '_skirt', col, hem_z=hem, dirt=dirt, pattern=pattern, trim=(hem - 0.01, hem + 0.022 * k, trim) if trim else None), flare=flare, ripple=ripple, top=[body], folds=Pp.fold_fn(k, belt=waist, drape=0.006))
    if belt == 'leather':
        b = P.band('belt', waist, half=0.020, out=0.003, mat=Pp.leather_mat('belt', (0.16, 0.085, 0.04)), around=[body]); buckle(P, waist, b)
    elif belt == 'rope':
        b = P.band('belt', waist, half=0.009, out=0.002, mat=Pp.straw_mat('rope', (0.5, 0.4, 0.22)), around=[body], squash=1.6)
    elif belt == 'gold':
        b = P.band('belt', waist, half=0.016, out=0.003, mat=Pp.gold_mat('belt_gold'), around=[body]); buckle(P, waist, b)
    else:
        b = None
    return waist, body, b


def bare(P, collar, hem=None, shoe_top=None, sleeve_end=None):
    """which body faces the clothes hide: everything below the collar except the hands, the forearms past a short sleeve, and the legs between hem and shoe"""
    k = P.k

    def hidden(Q):
        if Q[2] >= collar or P.hand_side(Q, 0.035):
            return False
        if sleeve_end is not None and abs(Q[0]) > sleeve_end - 0.03 * k and Q[2] > P.zJ('l-hand') - 0.12 * k:
            return False
        if hem is not None and Q[2] < hem + 0.14 * k and (shoe_top is None or Q[2] > shoe_top - 0.035 * k) and abs(Q[0]) < 0.3 * k:
            return False
        return True
    P.cull(hidden)


def dress_merchant(P, col, trim):
    k = P.k; zJ = P.zJ; hem = zJ('l-knee') + 0.13 * k
    P.piece('hose', 'helper-tights', lambda Q: Q[2] < zJ('spine-3') - 0.005 * k, 0.003, Pp.cloth_mat('hose', (0.17, 0.11, 0.06), weave=0.6, dirt=0.5, hem_z=0.1), thick=0.002, folds=Pp.fold_fn(k, drape=0.0015), under=True)
    waist, body, b = robe_parts(P, col, hem, trim=trim); cowl(P, (0.06, 0.045, 0.035)); pouch(P, waist, b); shoes(P, zJ('l-knee') - 0.14 * k); bare(P, zJ('neck') - 0.015 * k)


def dress_peasant(P):
    k = P.k; zJ = P.zJ; hem = zJ('l-knee') + 0.02 * k; top = zJ('l-ankle') + 0.05 * k
    waist, body, b = robe_parts(P, (0.33, 0.27, 0.19), hem, belt='rope', flare=1.16, dirt=0.7); shoes(P, top, (0.12, 0.075, 0.04))
    if not P.corpse:
        straw_hat(P); staff(P, 'r', 0.0, 2.05 * k, rad=0.012, curve=0.012, name='pole')
    bare(P, zJ('neck') - 0.015 * k, hem=hem, shoe_top=top)


def dress_oldman(P):
    k = P.k; zJ = P.zJ; hem = zJ('l-ankle') + 0.05 * k; col = (0.115, 0.07, 0.04)
    waist, body, b = robe_parts(P, col, hem, belt='rope', flare=1.3, ripple=(11, 0.016), dirt=0.6, loose_=0.016); cowl(P, tuple(v * 0.8 for v in col), radius=0.27, roll=0)
    nk = P.J['neck']; hood = L.icosphere('hood_hi', 1.0, 4, P.hi, scale=(0.105 * k, 0.07 * k, 0.12 * k)); place(hood, Matrix.Translation((nk[0], nk[1] + 0.085 * k, nk[2] - 0.035 * k)) @ Matrix.Rotation(math.radians(-25), 4, 'X'))
    L.displace_np(hood, lambda Q: 0.012 * k * (fbm(Q * np.array([1, 1, 0.4]), 3, 18 / k, 3) - 0.5)); P.solid(lo_of(hood, 'hood', 260, P.lo), hood, Pp.cloth_mat('hood', tuple(v * 0.8 for v in col), weave=1.3, dirt=0.1, rough=0.9), bone='spine_05')
    shoes(P, zJ('l-ankle') + 0.05 * k, (0.1, 0.065, 0.04)); beard(P, 0.11 * k, (0.36, 0.35, 0.33)); staff(P, 'r', 0.0, zJ('r-hand') + 0.2 * k, rad=0.015, col=(0.2, 0.13, 0.07), name='stick'); bare(P, zJ('neck') - 0.02 * k)


def dress_girl(P):
    k = P.k; zJ = P.zJ; hem = zJ('l-knee') - 0.1 * k; top = zJ('l-ankle') + 0.045 * k; se = abs(P.J['l-elbow'][0]) - 0.035 * k; col = (0.42, 0.035, 0.07); pat = ((0.55, 0.3, 0.5), 55.0 / k, 0.9)
    waist, body, b = robe_parts(P, col, hem, belt=None, flare=1.55, ripple=(12, 0.02), sleeve_end=se, pattern=pat, dirt=0.25, name='dress')
    P.band('sash', waist, half=0.022, out=0.003, mat=Pp.cloth_mat('sash', (0.3, 0.02, 0.04), dirt=0.0), around=[body]); shoes(P, top, (0.1, 0.055, 0.03)); flowers(P, 'r')
    if not P.corpse:
        basket(P, 'l')
    bare(P, zJ('neck') - 0.02 * k, hem=hem, shoe_top=top, sleeve_end=se)


def dress_gnome(P):
    k = P.k; zJ = P.zJ; hem = zJ('l-knee') - 0.02 * k; col = (0.085, 0.035, 0.26); gold = (0.6, 0.4, 0.06)
    P.piece('hose', 'helper-tights', lambda Q: Q[2] < zJ('spine-3') - 0.005 * k, 0.003, Pp.cloth_mat('hose', (0.2, 0.13, 0.07), weave=0.6, dirt=0.4, hem_z=0.1), thick=0.002, folds=Pp.fold_fn(k, drape=0.0015), under=True)
    waist, body, b = robe_parts(P, col, hem, sleeves=gold, trim=gold, flare=1.3, pattern=(gold, 30.0 / k, 0.9)); shoes(P, zJ('l-knee') - 0.08 * k, (0.16, 0.085, 0.04)); wizard_hat(P, col, gold); beard(P, 0.2 * k, (0.4, 0.39, 0.37), width=1.15); bare(P, zJ('neck') - 0.02 * k)


def dress_king(P):
    k = P.k; zJ = P.zJ; hem = zJ('l-knee') + 0.2 * k; col = (0.3, 0.014, 0.018)
    P.piece('hose', 'helper-tights', lambda Q: Q[2] < zJ('spine-3') - 0.005 * k, 0.003, Pp.cloth_mat('hose', (0.26, 0.012, 0.016), weave=0.6, dirt=0.1, hem_z=0.1), thick=0.002, folds=Pp.fold_fn(k, drape=0.0015), under=True)
    waist, body, b = robe_parts(P, col, hem, trim=(0.7, 0.5, 0.1), belt='gold', flare=1.15, dirt=0.05); gm = Pp.gold_mat('buttons'); Q = L.co(body)
    for i in range(5):
        z = waist + 0.05 * k + i * 0.065 * k; q = Q[(np.abs(Q[:, 0]) < 0.02 * k) & (np.abs(Q[:, 2] - z) < 0.02 * k) & (Q[:, 1] < P.J['pelvis'][1])]; y = float(q[:, 1].min())
        hi = L.icosphere('button%d_hi' % i, 0.011 * k, 3, P.hi, scale=(1, 0.5, 1)); place(hi, Matrix.Translation((0, y - 0.002 * k, z))); lo = L.icosphere('button%d' % i, 0.011 * k, 1, P.lo, scale=(1, 0.5, 1)); place(lo, Matrix.Translation((0, y - 0.002 * k, z))); P.solid(lo, hi, gm)
    shoes(P, zJ('l-knee') - 0.12 * k, (0.025, 0.05, 0.025)); crown(P); beard(P, 0.07 * k, (0.13, 0.12, 0.115)); bare(P, zJ('neck') - 0.015 * k)


# ---------------------------------------------------------------------------------------------- catalogue
def rehue(target):
    """colour variant of an outfit map: the blue cloth becomes `target`, shading kept"""
    def fn(a):
        m = np.clip((a[..., 2] - np.maximum(a[..., 0], a[..., 1]) - 0.02) * 10.0, 0, 1)[..., None]; lum = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]; ref = float((lum * m).sum() / max(1e-6, m.sum()))
        return a * (1 - m) + m * np.clip(lum / max(ref, 1e-4), 0, 2.5) * np.array(target, np.float32)
    return fn


W_COMMON = ('Built on the CC0 MakeHuman base mesh and its bundled skin, eye, brow, lash and hair assets, morphed here by simple region scaling: the face is the base face (no likeness work), and the hair is the bundled card cap, '
            'not groomed strands. Clothes are cut from the base mesh\'s garment helpers and loosened, with folds only in the normal map: no cloth simulation, so skirts follow the thighs through skin weights and will clip on long strides. '
            'Skeleton is the project humanoid core set (25 bones, no fingers or twist bones); weights are automatic (bone heat) and unreviewed in motion; no animation, Physics Asset or facial rig. Hands are open (the base A pose). '
            'Hair has no ORM map. Not imported into Unreal.')
SPECS = {
    'Merchant': dict(fam='npc_merchant_blue', fams=['npc_merchant_blue', '371 people/merchant/blue/c09w1-', 'npc_merchant_green', '381 people/merchant/green/c09w1-'],
                     build=dict(male=1.0, girth=1.07, belly=0.012), skin=dict(tex=SKIN_M, beard=((0.10, 0.07, 0.05), 0.45)), hair='short02', hair_col=(0.10, 0.065, 0.04), eye='brown',
                     dress=lambda P: dress_merchant(P, (0.028, 0.055, 0.15), (0.42, 0.32, 0.12)), variants={'Green': rehue((0.05, 0.12, 0.035))},
                     dresses='travelling merchant: belted wool tunic to mid thigh with a darker shoulder cape and rolled collar, purse on the belt, brown hose, soft leather boots; blue (default) and green outfit maps cover both merchant families',
                     weak=W_COMMON + ' The green variant is a recolour of the blue base-colour map (shared N and ORM).'),
    'Peasant': dict(fam='npc_peasant', fams=['npc_peasant', '411 people/peasant2/c11w1-'], build=dict(male=1.0, girth=0.96, limbs=0.94), skin=dict(tex=SKIN_M, beard=((0.16, 0.11, 0.07), 0.5), grime=0.35), hair='short02', hair_col=(0.2, 0.13, 0.07), eye='grey',
                    dress=dress_peasant, dresses='field peasant: undyed linen tunic to the knee with a rope belt, bare shins, low leather shoes, plaited straw hat, a long pole in the right hand',
                    weak=W_COMMON + ' The pole is rigid to the right hand bone and passes by the open hand rather than being gripped.'),
    'Old_Man': dict(fam='npc_old_man', fams=['npc_old_man', '231 people/oldman/c1-w1-'], build=dict(male=1.0, girth=0.95, limbs=0.9, stoop=20.0, height=0.95), skin=dict(tex=SKIN_M, age=1.0, pale=0.5), hair='short02', hair_col=(0.5, 0.49, 0.47), eye='grey',
                    dress=dress_oldman, dresses='stooped old man: ankle-length brown wool robe with a rope belt, hood worn down as a heavy cowl, grey beard, walking stick in the right hand',
                    weak=W_COMMON + ' The stoop is modelled into the rest pose (bent back), so standard humanoid clips will read slightly more upright at the hips than the mesh. The stick is rigid to the hand bone, not gripped.'),
    'Girl': dict(fam='npc_girl', fams=['npc_girl', '331 people/girl/c03w1-', '339 people/girl/c03w9-'], build=dict(height=0.72, head=1.24, legs=0.9, chest=1.0, girth=0.94, limbs=0.97), skin=dict(tex=SKIN_F, tint=(1.0, 0.97, 0.95)), hair='ponytail01', hair_col=(0.62, 0.45, 0.16), brow_col=(0.35, 0.24, 0.1), eye='blue',
                 dress=dress_girl, dresses='village girl (child proportions, 1.2 m): red patterned dress with short sleeves and a sash, fair hair tied back, a wicker basket in the left hand and a bunch of white flowers in the right',
                 weak=W_COMMON + ' Child proportions come from scaling the adult base (larger head, shorter body), so the face is an adult face made small. Basket and flowers are rigid to the hand bones, not gripped.'),
    'Gnome_Wizard': dict(fam='npc_gnome_purple', fams=['npc_gnome_purple', '561 people/gnome/purple/c13w1-'], build=dict(male=1.0, height=0.66, head=1.3, legs=0.8, girth=1.22, belly=0.03), skin=dict(tex=SKIN_M, age=0.7, tint=(1.0, 0.93, 0.9)), hair='short02', hair_col=(0.55, 0.53, 0.5), eye='blue',
                         dress=dress_gnome, dresses='gnome wizard (1.1 m with a large head): purple robe sewn with gold dots, gold sleeves and hem, bent pointed hat with gold stars, long grey beard, belt, brown boots',
                         weak=W_COMMON + ' The stars are round embroidered dots, not five-pointed stars. Gnome proportions come from scaling the human base.'),
    'King': dict(fam='king_on_throne', fams=['king_on_throne', '421 items/food/food- frame 31'], build=dict(male=1.0, girth=1.12, belly=0.022), skin=dict(tex=SKIN_M, age=0.5, beard=((0.2, 0.19, 0.18), 0.5)), hair='short02', hair_col=(0.2, 0.19, 0.18), eye='brown',
                 dress=dress_king, dresses='King Daniel: crimson tunic with gold buttons, hem and belt, crimson hose, green boots, gold crown set with rubies, greying beard', weak=W_COMMON),
}


def build(name, mode, px=2048, keep=False, asset=None, outdir=None, corpse=False):
    L.reset(); spec = SPECS[name]; asset = asset or 'SK_%s_PR' % name; outdir = outdir or (os.path.join(L.UNC, spec['fam'], name) if mode == 'final' else os.path.join(L.REVIEW, 'people', name)); os.makedirs(outdir, exist_ok=True)
    P = Pp.Person(name, spec); P.corpse = corpse; k = P.k; P.head_parts(hair=spec.get('hair'), hair_root=spec.get('hair_root'), eye=spec.get('eye', 'brown')); spec['dress'](P)
    sk = dict(spec['skin']); bd = sk.pop('beard', None)
    if bd:
        sk['beard'] = (bd[0], bd[1], P.zJ('jaw'), lip_z(P))
    skin = Pp.skin_mat('skin_src', zscale=k, **sk)
    A = Pp.assemble(P, asset, outdir, skin=skin, px_skin=px, px_outfit=px, px_hair=px); lo, arm = A['lo'], A['arm']; A['P'] = P; print('TRIS', name, L.tri_count(lo), 'WEIGHTS', A['weights']); name_ = asset[3:]
    for suf, fn in (spec.get('variants') or {}).items():
        bc = np.asarray(Image.open(A['files']['Outfit']['BC']).convert('RGB'), np.float32) / 255.0; p = os.path.join(outdir, 'T_%s_Outfit_%s_BC.png' % (name_, suf)); Image.fromarray((np.clip(fn(bc), 0, 1) * 255 + 0.5).astype(np.uint8)).save(p, optimize=True); A.setdefault('variants', {})[suf] = p
    for o in bpy.data.collections['Source_Hi'].objects:
        o.hide_render = True
    if keep:
        return A
    R = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0); H = float(P.J['head-2'][2]); hc = P.J['head']; A['R'] = R
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], az=25, el=6, fill=1.1, lens=70, res=(900, 1200), spp=160)
    L.shot(R, os.path.join(outdir, 'render_close.png'), center=(hc[0], hc[1], H - 0.16 * k), radius=0.33 * k * max(1.0, spec['build'].get('head', 1.0)), az=22, el=4, fill=0.9, lens=85, res=(1000, 800), spp=160, fstop=8)
    if mode != 'final':
        L.shot(R, os.path.join(outdir, 'render_back.png'), [lo], az=205, el=10, fill=1.1, lens=70, res=(900, 1200), spp=64)
        C.pose(arm, {'upperarm_l': (0, 0, -35), 'upperarm_r': (0, 0, 35), 'thigh_l': (-30, 0, 0), 'thigh_r': (25, 0, 0), 'calf_l': (35, 0, 0), 'lowerarm_l': (40, 0, 0), 'head': (0, 20, 0)})
        L.shot(R, os.path.join(outdir, 'render_pose.png'), [lo], az=60, el=8, fill=1.1, lens=70, res=(900, 1200), spp=64); C.pose(arm, {})
        return A
    extra = {}
    if A.get('variants'):
        extra['outfit_variants'] = [{'file': L.rel(p), 'variant': s_, 'note': 'base colour only; shares the Outfit N and ORM maps'} for s_, p in A['variants'].items()]
    Pp.export_person(asset, 'character_humanoid', A, outdir, spec['fams'], L.origin_ids([f for f in spec['fams'] if not f[0].isdigit()]), spec['dresses'], spec['weak'], '%s %s final' % (SCRIPT, name), extra=extra,
                     third=['forrest_ground_01 (render ground)'])
    return A


# ---------------------------------------------------------------------------------------------- corpses (the gore stays: see the art brief)
W_DEAD = ('A posed, frozen copy of the %s character of this folder tree (same build script, maps baked again at 1024 px with blood painted into the base colour): no ragdoll, no wounds cut into the mesh, eyes open, '
          'clothes not draped by simulation. Decimated to about %d triangles for a floor prop, so the face and hands are coarse close up. The blood pool is a separate decal (companion_decal), not part of this mesh. '
          'Hair has no ORM map. Not imported into Unreal.')
CORPSES = {
    'Corpse_Merchant': dict(base='Merchant', fam='corpse_merchant', fams=['corpse_merchant', '345 people/merchant/death-', '385 people/merchant/green/death-'], yaw=25, wound=(0.02, 0.1, 0.17), variants={'Green': rehue((0.05, 0.12, 0.035))},
                            pose=[('upperarm_l', 'Y', -18), ('lowerarm_l', 'X', -35), ('upperarm_r', 'Y', -30), ('thigh_l', 'X', -14), ('calf_l', 'X', 30), ('thigh_r', 'Y', -10), ('head', 'Y', 28)],
                            dresses='dead merchant on his back in a pool of blood, tunic soaked from a chest wound; blue and green outfit maps for the two placements'),
    'Corpse_Peasant': dict(base='Peasant', fam='corpse_peasant', fams=['corpse_peasant', '415 people/peasant2/death-'], yaw=-35, wound=(-0.05, 0.2, 0.16),
                           pose=[('upperarm_l', 'Y', 25), ('upperarm_r', 'Y', -12), ('lowerarm_r', 'X', -50), ('thigh_r', 'X', -20), ('calf_r', 'X', 38), ('head', 'Y', -30)],
                           dresses='dead peasant on his back, linen tunic soaked in blood; hat and pole gone (the sprite shows the pole lying beside him: place the Peasant pole or any pole prop next to it)'),
    'Corpse_Girl': dict(base='Girl', fam='corpse_girl', fams=['corpse_girl', '335 people/girl/death-'], yaw=150, wound=(0.0, 0.05, 0.12), amount=0.9,
                        pose=[('upperarm_l', 'Y', -25), ('upperarm_r', 'Y', 15), ('lowerarm_l', 'X', -30), ('thigh_l', 'X', -12), ('calf_l', 'X', 26), ('head', 'Y', 35)],
                        dresses='the dead village girl on her back in blood, red dress soaked, the bunch of white flowers still in her hand (the basket is left out)'),
}


def corpse(name, mode):
    import build_npcs as NP
    v = CORPSES[name]; asset = 'SM_%s_PR' % name; name_ = asset[3:]; outdir = os.path.join(L.UNC, v['fam'], name) if mode == 'final' else os.path.join(L.REVIEW, 'people', name)
    A = build(v['base'], mode, px=1024, keep=True, asset=asset, outdir=outdir, corpse=True); src, arm = A['lo'], A['arm']
    for b, ax, deg in v['pose']:
        NP.world_rot(arm, b, ax, deg)
    lo = L.dup(src, asset); src.hide_render = True; names = [g.name for g in lo.vertex_groups]; legw = np.zeros(len(lo.data.vertices), np.float32)
    for vert in lo.data.vertices:
        legw[vert.index] = sum(g.weight for g in vert.groups if names[g.group].startswith(('thigh', 'calf', 'pelvis')))
    L.apply_mods(lo); lo.vertex_groups.clear(); lo.parent = None; C.set_attr(lo, 'legw', legw)
    if L.tri_count(lo) > 9000:
        L.mod(lo, 'DECIMATE', ratio=9000 / L.tri_count(lo)); L.apply_mods(lo); L.clean_mesh(lo)
    lw = np.zeros(len(lo.data.vertices), np.float32); lo.data.attributes['legw'].data.foreach_get('value', lw); lo.data.attributes.remove(lo.data.attributes['legw'])
    for an in ('rigid_id', 'under'):
        if lo.data.attributes.get(an):
            lo.data.attributes.remove(lo.data.attributes[an])
    NP.lay_down(lo, v.get('yaw', 0.0) + 80.0, flatten=np.clip(lw, 0, 1) * 0.8)
    files = NP.blood_bake(lo, v['wound'], outdir, name_, px=1024, amount=v.get('amount', 1.0), slots=('Skin', 'Outfit')); vf = {}
    for suf, fn in (v.get('variants') or {}).items():
        bc = np.asarray(Image.open(files['Outfit']).convert('RGB'), np.float32) / 255.0; p = os.path.join(outdir, 'T_%s_Outfit_%s_BC.png' % (name_, suf)); Image.fromarray((np.clip(fn(bc), 0, 1) * 255 + 0.5).astype(np.uint8)).save(p, optimize=True); vf[suf] = p
    R = NP.gore_ground()
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], az=25, el=38, fill=1.05, lens=60, spp=160); L.shot(R, os.path.join(outdir, 'render_close.png'), [lo], az=-40, el=24, fill=1.3, lens=80, res=(1000, 800), spp=160, fstop=8)
    if mode != 'final':
        return
    ac = L.coll(asset); ac['dink_class'] = 'prop'; L.link(lo, ac); ucx = L.make_ucx(lo); st = L.mesh_stats(lo); fbx = os.path.join(outdir, asset + '.fbx'); L.export_fbx(fbx, [lo, ucx])
    for o in list(bpy.data.objects):                       # a static prop: the rig and the standing source are not kept in its file
        if o.type == 'ARMATURE' or (o.type == 'MESH' and o is not lo and o is not ucx and o.name not in bpy.data.collections['Review'].objects):
            bpy.data.objects.remove(o)
    for im in bpy.data.images:
        if im.name.lower().endswith('.png'):
            im.name = im.name[:-4]
    L.save_blend(os.path.join(outdir, asset + '.blend')); tx = []
    for slot, fs in A['files'].items():
        for key, p in fs.items():
            tx.append({'file': L.rel(p), 'size_px': list(Image.open(p).size), 'slot': slot, 'channels': {'BC': 'base colour sRGB' + (' with baked blood' if slot in files else (' + alpha' if slot == 'Hair' else '')), 'N': 'tangent normal, OpenGL', 'ORM': 'R occlusion, G roughness, B metallic'}[key]})
    tx += [{'file': L.rel(p), 'size_px': list(Image.open(p).size), 'slot': 'Outfit', 'channels': 'base colour sRGB with baked blood, colour variant "%s" (shares N and ORM)' % s_} for s_, p in vf.items()]
    NP.write_manifest(outdir, {
        'name': asset, 'class': 'prop', 'fbx': L.rel(fbx), 'source_blend': L.rel(os.path.join(outdir, asset + '.blend')), 'build': 'Unclaimed/tools/bl.sh %s %s final' % (SCRIPT, name),
        'derived_from': 'Unclaimed/%s/%s (SK_%s_PR), rebuilt, posed and frozen' % (SPECS[v['base']]['fam'], v['base'], v['base']), 'dimensions_m': st['dimensions_m'], 'bounds_min_m': st['bounds_min_m'], 'bounds_max_m': st['bounds_max_m'], 'lod0_triangles': st['triangles'],
        'triangle_budget': {'soft': 6000, 'hard': 20000, 'within_soft': st['triangles'] <= 6000}, 'textures': tx, 'materials': [m.name for m in lo.data.materials], 'collision_hulls': 1,
        'material_slots_note': 'Skin and Outfit are baked BC/N/ORM sets (blood in the base colour); Hair is an alpha-tested atlas with a strand normal; Eyes is a base-colour iris map',
        'companion_decal': 'Unclaimed/blood_splat/Blood_Pool_02 (2.2 m), centred under the body; the render shows it', 'pivot': 'base centre, lying on z = 0', 'families': v['fams'], 'origin_ids': L.origin_ids([v['fam']]),
        'supersedes': 'none (placeholder greybox cards)', 'dresses': v['dresses'], 'third_party': ['MakeHuman CC0 base mesh, skin, eyes, eyebrows, eyelashes and hair (Art/Characters/ThirdParty/MakeHuman)', 'park_dirt (render ground)'],
        'status': 'source delivered; not imported into Unreal, not bound to any placement', 'known_weaknesses': W_DEAD % (v['base'], st['triangles'])})


# ---------------------------------------------------------------------------------------------- the king, seated
W_THRONE = ('The king is the rigged SK_King_PR of the sibling folder, posed seated and frozen (about half its triangles): a static set piece, no animation, eyes open, and his tunic skirt is bent at the hips by skin weights, not draped. '
            'The cloak is two modelled wings that fall from the shoulders over the arm rests to the floor; it is not simulated, it does not continue behind his back (the throne back hides the gap from the front and sides), '
            'and its lining shows only where the dense source was baked from outside (the game mesh is one sheet: use a two-sided material). Throne carving is limited to mouldings, studs and a crest; no heraldry. '
            'One hull for collision. Not imported into Unreal.')


def king_on_throne(mode):
    import build_npcs as NP
    A = build('King', mode); P = A['P']; src, arm, R = A['lo'], A['arm'], A['R']; k = P.k; asset = 'SM_King_On_Throne_PR'; name_ = asset[3:]
    outdir = os.path.join(L.UNC, 'king_on_throne', 'King_On_Throne') if mode == 'final' else os.path.join(L.REVIEW, 'people', 'King_On_Throne'); os.makedirs(outdir, exist_ok=True)
    for o in list(bpy.data.objects):                       # the standing king's LODs are saved in his own .blend already
        if o.type == 'MESH' and '_LOD' in o.name and o is not src:
            bpy.data.objects.remove(o)
    for b, ax, deg in [('thigh_l', 'X', -86), ('thigh_r', 'X', -86), ('thigh_l', 'Z', 7), ('thigh_r', 'Z', -7), ('calf_l', 'X', 84), ('calf_r', 'X', 84), ('upperarm_l', 'Y', 30), ('upperarm_r', 'Y', -30), ('lowerarm_l', 'X', -45), ('lowerarm_r', 'X', -45), ('head', 'X', 6)]:
        NP.world_rot(arm, b, ax, deg)
    king = L.dup(src, 'king_seated'); L.apply_mods(king); king.vertex_groups.clear(); king.parent = None; src.hide_render = True; C.pose(arm, {})
    for an in ('rigid_id', 'under'):
        if king.data.attributes.get(an):
            king.data.attributes.remove(king.data.attributes[an])
    L.mod(king, 'DECIMATE', ratio=16000 / L.tri_count(king)); L.apply_mods(king); L.clean_mesh(king)
    Q = L.co(king); stool = 0.15; dz = stool - float(Q[:, 2].min()); Q[:, 2] += dz; L.set_co(king, Q); hy = float(P.J['pelvis'][1]); zs = float(P.J['l-shoulder'][2]) + dz
    seat = float(Q[(Q[:, 1] > hy - 0.30 * k) & (Q[:, 1] < hy - 0.12 * k) & (np.abs(Q[:, 0]) < 0.25)][:, 2].min()) - 0.004; yb = float(Q[Q[:, 2] > seat + 0.25][:, 1].max()) + 0.015; arm_top = seat + 0.21; top = seat + 1.2
    wood = Pp.wood_mat('throne_wood', (0.12, 0.065, 0.03)); gold = Pp.gold_mat('throne_gold'); red = Pp.cloth_mat('cushion_red', (0.28, 0.014, 0.02), dirt=0.0, worn=0.8, sheen=0.8, rough=0.75); green = Pp.cloth_mat('cushion_green', (0.03, 0.14, 0.04), dirt=0.1, worn=0.8, sheen=0.8, rough=0.75)
    his = []; los = []; hc = L.coll('Throne_Hi'); lc = L.coll('Throne')

    def blk(nm, mn, mx, mat, bevel=0.008, warp=0.0015, soft=False):
        h = L.box(nm + '_hi', mn, mx, hc, hi=True, bevel=bevel, warp=warp, seed=len(his))
        if soft:                                        # cushions: puffed
            Qh = L.co(h); c_ = (np.array(mn) + np.array(mx)) / 2; hs_ = (np.array(mx) - np.array(mn)) / 2; u = (Qh - c_) / hs_; Qh[:, 2] += hs_[2] * 0.9 * (1 - u[:, 0] ** 2) * (1 - u[:, 1] ** 2) * (u[:, 2] > 0); L.set_co(h, Qh)
        h.data.materials.append(mat); l = L.box(nm, mn, mx, lc)
        if soft:
            L.mod(l, 'SUBSURF', levels=2, render_levels=2).subdivision_type = 'SIMPLE'; L.apply_mods(l); Ql = L.co(l); c_ = (np.array(mn) + np.array(mx)) / 2; hs_ = (np.array(mx) - np.array(mn)) / 2; u = (Ql - c_) / hs_; Ql[:, 2] += hs_[2] * 0.9 * (1 - u[:, 0] ** 2) * (1 - u[:, 1] ** 2) * (u[:, 2] > 0); L.set_co(l, Ql); l.data.polygons.foreach_set('use_smooth', [True] * len(l.data.polygons))
        his.append(h); los.append(l); return l
    yf = hy - 0.34 * k
    blk('seat', (-0.34, yf, 0.0), (0.34, yb + 0.02, seat - 0.055), wood); blk('cushion', (-0.31, yf + 0.01, seat - 0.055), (0.31, yb, seat - 0.012), red, bevel=0.02, soft=True)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 0.34, sx * 0.45)); blk('arm%d' % sx, (x0, yf - 0.01, 0.0), (x1, yb + 0.02, arm_top - 0.03), wood); blk('armcap%d' % sx, (x0 - 0.012, yf - 0.03, arm_top - 0.03), (x1 + 0.012, yb + 0.02, arm_top), wood, bevel=0.012)
        blk('armtrim%d' % sx, (x0 - 0.004, yf - 0.016, 0.03), (x1 + 0.004, yf - 0.006, arm_top - 0.04), gold, bevel=0.003, warp=0.0)
        for i in range(4):
            for hi_ in (True, False):
                b = L.icosphere('stud', 0.012, 3 if hi_ else 1, hc if hi_ else lc); place(b, Matrix.Translation((sx * 0.452, yf + 0.06 + i * 0.13, arm_top - 0.08)))
                if hi_:
                    b.data.materials.append(gold); his.append(b)
                else:
                    los.append(b)
        for hi_ in (True, False):                          # finials on the back posts
            f = L.lathe('finial', [(0.0, 0.0), (0.03, 0.0), (0.034, 0.02), (0.018, 0.04), (0.03, 0.07), (0.042, 0.10), (0.03, 0.135), (0.0, 0.15)], seg=32 if hi_ else 10, c=hc if hi_ else lc); place(f, Matrix.Translation((sx * 0.41, yb + 0.065, top)))
            if hi_:
                L.subsurf(f, 1); f.data.materials.append(gold); his.append(f)
            else:
                los.append(f)
    blk('back', (-0.45, yb + 0.02, 0.0), (0.45, yb + 0.11, top), wood); blk('backpad', (-0.33, yb, seat + 0.05), (0.33, yb + 0.03, top - 0.14), red, bevel=0.02, soft=False); blk('rail', (-0.47, yb + 0.005, top - 0.09), (0.47, yb + 0.125, top), gold, bevel=0.012, warp=0.0)
    for hi_ in (True, False):                              # crest: a sun disc on the top rail
        d = L.lathe('crest', [(0.0, 0.03), (0.07, 0.028), (0.1, 0.018), (0.115, 0.0), (0.1, -0.018), (0.07, -0.028), (0.0, -0.03)], seg=48 if hi_ else 14, c=hc if hi_ else lc); place(d, Matrix.Translation((0, yb + 0.065, top + 0.08)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        if hi_:
            L.subsurf(d, 1); Qd = L.co(d); th = np.arctan2(Qd[:, 2] - (top + 0.08), Qd[:, 0]); r = np.hypot(Qd[:, 0], Qd[:, 2] - (top + 0.08)); f_ = 1 + 0.16 * np.cos(th * 12) * smoothstep(0.07, 0.115, r); Qd[:, 0] *= f_; Qd[:, 2] = (top + 0.08) + (Qd[:, 2] - (top + 0.08)) * f_; L.set_co(d, Qd); d.data.materials.append(gold); his.append(d)
        else:
            los.append(d)
    blk('stool', (-0.25, hy - 0.76 * k, 0.0), (0.25, hy - 0.38 * k, stool - 0.045), wood); blk('stoolpad', (-0.23, hy - 0.745 * k, stool - 0.045), (0.23, hy - 0.395 * k, stool - 0.012), green, bevel=0.02, soft=True)
    # cloak: two wings from the shoulders over the arm rests to the floor
    velvet = NT('cloak'); n = velvet.noise(6, 5, 0.6); n2 = velvet.noise(70, 3, 0.6); uvs = velvet.sep(velvet.uv); col = (0.085, 0.012, 0.19); base = velvet.mix(n, tuple(v * 0.7 for v in col), tuple(v * 1.3 for v in col))
    edge = velvet.math('MAXIMUM', velvet.maprange(uvs[1], 0.93, 0.945, 0.0, 1.0), velvet.maprange(uvs[0], 0.06, 0.045, 0.0, 1.0)); edge2 = velvet.math('MAXIMUM', velvet.maprange(uvs[1], 0.965, 0.98, 0.0, 1.0), velvet.maprange(uvs[0], 0.03, 0.018, 0.0, 1.0))
    base = velvet.mix(edge, base, (0.42, 0.02, 0.03)); base = velvet.mix(edge2, base, (0.2, 0.34, 0.7)); ao = velvet.ao(0.06, 10); base = velvet.mix(velvet.math('MULTIPLY', velvet.ramp(ao, [(0.35, 1.0), (0.85, 0.0)]), 0.6), base, tuple(v * 0.2 for v in col))
    velvet.set(base=base, rough=velvet.mixf(n2, 0.7, 0.85), sheen=1.0, normal=velvet.bump(n2, 0.3, 0.0006)); lining = Pp.cloth_mat('lining', (0.025, 0.06, 0.26), dirt=0.0, worn=0.2, sheen=0.8, rough=0.6)
    knots = np.array([(0.0, 0.11, zs + 0.085), (0.12, 0.255, zs + 0.048), (0.30, 0.36, zs - 0.14), (0.48, 0.485, arm_top + 0.035), (0.62, 0.54, arm_top - 0.14), (0.85, 0.64, 0.10), (0.93, 0.76, 0.022), (1.0, 1.02, 0.012)]); kf = L.curve_fn(knots[:, 1:])

    def wing(sx, nu, nv, c, nm):
        def fn(U, V):
            a = np.radians(38 + U * 72); q = kf(V); r = q[:, 0]; z = q[:, 1]; r = r * (1 + 0.06 * np.sin(a * 13 + 2 * np.sin(a * 5)) * smoothstep(0.45, 1.0, V)) + 0.012 * np.sin(a * 17 + 1.0) * smoothstep(0.8, 1.0, V)
            z = np.maximum(z + 0.02 * np.sin(a * 13 + 2 * np.sin(a * 5) + 1.2) * smoothstep(0.3, 0.6, V) * (1 - smoothstep(0.85, 0.95, V)), 0.012); return np.stack([sx * r * np.sin(a), hy - r * np.cos(a), z], 1)
        o = L.grid_surface(nm, fn, nu, nv, c, closed_u=False); Qw = L.co(o); Nw = L.vnormals(o); out = Qw - np.array([0.0, hy, 0.0]); out[:, 2] = 0.3            # the outside of the cloak faces away from the king and up
        if float((Nw * out).sum()) < 0:
            o.data.flip_normals(); o.data.update()
        return o
    for sx in (-1, 1):
        h = wing(sx, 70, 90, hc, 'cloak%d_hi' % sx); L.displace_np(h, Pp.fold_fn(1.0, drape=0.01, fine=0.002)); h.data.materials.append(velvet.mat); h.data.materials.append(lining); L.mod(h, 'SOLIDIFY', thickness=0.007, offset=-1.0, material_offset=1, material_offset_rim=0); L.apply_mods(h); his.append(h)
        l = wing(sx, 30, 24, lc, 'cloak%d' % sx); Pp.rim(l, 0.007); los.append(l)
    fur = NT('ermine'); fn_ = fur.noise(260, 3, 0.6); spots = fur.ramp(fur.voronoi(22, feature='F1', vec=fur.mapping(scale=(1.0, 1.0, 0.45))), [(0.0, 1.0), (0.13, 1.0), (0.2, 0.0)]); fb = fur.mix(fn_, (0.62, 0.6, 0.54), (0.86, 0.85, 0.8)); fb = fur.mix(spots, fb, (0.02, 0.018, 0.015))
    fur.set(base=fb, rough=0.8, sheen=0.6, normal=fur.bump(fur.noise(500, 2, 0.5), 0.8, 0.001))
    for hi_ in (True, False):
        o = L.ring('ermine' + ('_hi' if hi_ else ''), 1.0, 0.06, hc if hi_ else lc, seg=64 if hi_ else 18, sides=16 if hi_ else 7, squash=0.8); Qe = L.co(o); r = np.hypot(Qe[:, 0], Qe[:, 1]); th = np.arctan2(Qe[:, 1], Qe[:, 0])
        Qe[:, 0] = np.cos(th) * (0.235 + (r - 1.0)); Qe[:, 1] = hy - 0.012 + np.sin(th) * (0.11 + (r - 1.0)); Qe[:, 2] += zs + 0.06 + 0.05 * np.sin(th) - 0.035 * np.abs(np.cos(th)); L.set_co(o, Qe)
        if hi_:
            L.displace_np(o, lambda Q_: 0.006 * (fbm(Q_, 3, 40, 3) - 0.5)); o.data.materials.append(fur.mat); his.append(o)
        else:
            los.append(o)
    for o in his:                                          # every source part carries a UV layer of the same name, so joining them for the bake keeps the cloak's UVs (its borders are drawn in UV space)
        if not o.data.uv_layers:
            o.data.uv_layers.new(name='UVMap')
        o.data.uv_layers[0].name = 'UVMap'
    his.sort(key=lambda o: 0 if o.name.startswith('cloak') else 1)
    for o in los:
        if not o.data.uv_layers:
            L.smart_uv(o, angle=66, margin=0.004)
        o.data.uv_layers[0].name = 'UVMap'
    thr = L.join(los, 'throne'); L.clean_mesh(thr, dist=1e-6); L.pack_uv(thr, margin=0.004); files, stats = L.bake_set(thr, his, 2048, outdir, name_ + '_Throne', extrude=0.012, maxdist=0.03); L.assign(thr, L.game_material('MI_%s_Throne' % name_, files))
    king.data.uv_layers[0].name = 'UVMap'; lo = L.join([king, thr], asset); ac = L.coll(asset); ac['dink_class'] = 'prop_large'; L.link(lo, ac); P_ = L.co(lo); c = (P_.min(0) + P_.max(0)) / 2; c[2] = 0.0; lo.matrix_world = Matrix.Translation(tuple(-c)); L.apply_xf(lo)
    for o in his:
        o.matrix_world = Matrix.Translation(tuple(-c)); L.apply_xf(o); o.hide_render = True
    lo2, hi2 = L.bounds([lo]); L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], az=22, el=12, fill=1.0, lens=60, res=(1200, 1000), spp=160)
    L.shot(R, os.path.join(outdir, 'render_close.png'), center=(0, -c[1] + hy - 0.1, zs + 0.1), radius=0.5, az=-25, el=8, fill=0.9, lens=80, res=(1000, 800), spp=160, fstop=8)
    if mode != 'final':
        L.shot(R, os.path.join(outdir, 'render_back.png'), [lo], az=150, el=20, fill=1.0, lens=60, res=(1200, 1000), spp=64); return
    ucx = L.make_ucx(lo); st = L.mesh_stats(lo); fbx = os.path.join(outdir, asset + '.fbx'); L.export_fbx(fbx, [lo, ucx])
    for o in list(bpy.data.objects):
        if o is src or o.type == 'ARMATURE' or (o.type == 'MESH' and o.name.startswith(('body', 'outfit')) and o is not lo):
            bpy.data.objects.remove(o)
    for cn in ('Source_Hi',):
        for o in list(bpy.data.collections[cn].objects):
            bpy.data.objects.remove(o)
    L.save_blend(os.path.join(outdir, asset + '.blend'))
    NP.write_manifest(outdir, {
        'name': asset, 'class': 'prop_large', 'fbx': L.rel(fbx), 'source_blend': L.rel(os.path.join(outdir, asset + '.blend')), 'build': 'Unclaimed/tools/bl.sh %s King final' % SCRIPT,
        'derived_from': 'Unclaimed/king_on_throne/King (SK_King_PR): the same build, posed seated and frozen', 'dimensions_m': st['dimensions_m'], 'bounds_min_m': st['bounds_min_m'], 'bounds_max_m': st['bounds_max_m'], 'lod0_triangles': st['triangles'],
        'triangle_budget': {'soft': 20000, 'hard': 60000, 'within_soft': st['triangles'] <= 20000},
        'textures': [{'file': L.rel(p_), 'size_px': list(Image.open(p_).size), 'slot': 'Throne', 'channels': {'BC': 'base colour sRGB', 'N': 'tangent normal, OpenGL (green up; flip green on import)', 'ORM': 'R occlusion, G roughness, B metallic'}[k_]} for k_, p_ in files.items()],
        'shared_textures': 'the king\'s Skin, Outfit, Hair and Eyes maps are those of Unclaimed/king_on_throne/King (not copied)', 'materials': [m.name for m in lo.data.materials], 'collision_hulls': 1, 'bake_stats': stats,
        'material_exception': 'unique BC/N/ORM bake private to this asset for the throne, cloak, collar and footstool', 'pivot': 'base centre on the floor, front on -Y', 'families': ['king_on_throne', '421 items/food/food- frame 31'], 'origin_ids': L.origin_ids(['king_on_throne']),
        'supersedes': 'none (placeholder greybox cards)', 'dresses': 'King Daniel seated on his throne: crowned, bearded, in crimson with gold buttons, a purple cloak with a blue lining and red and blue borders spilling over the arm rests to the floor, ermine collar, feet on a green footstool; dark wood throne with gold rail, studs, finials and a sun crest',
        'third_party': ['MakeHuman CC0 base mesh, skin, eyes, eyebrows, eyelashes and hair (Art/Characters/ThirdParty/MakeHuman)', 'forrest_ground_01 (render ground)'], 'status': 'source delivered; not imported into Unreal, not bound to any placement', 'known_weaknesses': W_THRONE})


if __name__ == '__main__':
    a = L.args(); names = (list(SPECS) + list(CORPSES)) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        if n in CORPSES:
            corpse(n, mode)
        elif n == 'King':
            king_on_throne(mode)
        else:
            build(n, mode)
