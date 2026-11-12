"""Milder Flatstomp, stage 2+3: tan wool hose, short brown leather tabard, riveted-mail skirt, padded blue collar,
steel pauldrons / vambraces / greaves / knee cops with leather straps and iron buckles, belt, baldric, boots.
Game meshes + *_HI bake sources -> Milder/Work/milder_garments_b.blend."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *; import gearlib as G, folds
N = 'Milder'
bpy.ops.wm.open_mainfile(filepath=str(OUT / N / 'Work/milder_bodyvol.blend'))
D = bpy.data.objects; arm = D['Armature']; bv = D['BodyVol']; B = arm.data.bones
folds.setup({n: list(B[n].head_local) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')})
body_bvh = bvh_of([bv, D['Skin']]); G.init(arm, body_bvh)
S, E_, Wr, T, K, A, MIR = G.S, G.E_, G.Wr, G.T, G.K, G.A, G.MIR
dU, dF = G.dU, G.dF
made = []
def _mir(p):
    m = p.copy(); m[:, 0] = np.abs(m[:, 0]); return m
def rr(bvh, c, d, far=.12, default=.05):
    hit = bvh.ray_cast(Vector(c + d * far), Vector(-d), far)
    return float((np.array(hit[0]) - c) @ d) if hit[0] is not None else default
TA = [(0, -.02, .8), (0, -.02, 1.7)]

# ------------------------------------------------------------------ HOSE (trousers)
tr = dup(bv, 'Trousers_Base')
implicit_cut(tr, lambda P: .40 - P[:, 2])
implicit_cut(tr, lambda P: P[:, 2] - .775)      # the mail skirt hides everything above mid-thigh
def tro_class(C, Nn): return np.where(C[:, 2] < .875, np.where(C[:, 0] > 0, 21, 22), np.where((C[:, 1] + .02) < 0, 23, 24))
tro_charts = {21: ('cyl', [T, K, A], (1, 0, 0), .075), 22: ('cyl', [T * MIR, K * MIR, A * MIR], (-1, 0, 0), .075), 23: ('cyl', TA, (0, -1, 0), .17), 24: ('cyl', TA, (0, 1, 0), .17)}
def tro_seams(p):
    s, th, _ = poly_params(_mir(p), [T, K, A], (1, 0, 0)); d = np.minimum(np.abs(th), np.pi - np.abs(th)) * .07
    seam = np.where(p[:, 2] < .9, d, 1.0); return seam, np.abs(seam - .0045)
tro, tro_hi = G.finish(tr, folds.trousers, 1300, tro_class, tro_charts, 'wool_tan', 'Trousers', lip=None, seams=tro_seams)
made += [tro, tro_hi]

# ------------------------------------------------------------------ TABARD (short leather jerkin)
def hemz(P):
    az = np.arctan2(P[:, 0], -P[:, 1]); return .958 + .003 * np.sin(3 * az + 1.0) + .002 * np.sin(7 * az)
def neck_r(P): return np.sqrt(P[:, 0] ** 2 + (P[:, 1] - .004) ** 2)
jk = dup(bv, 'Tabard_Base')
implicit_cut(jk, lambda P: folds.arm_h(P) - .036)     # short cap over the shoulder: the armhole edge sits on the upper arm, under the pauldron
implicit_cut(jk, lambda P: np.minimum(.116 - neck_r(P), P[:, 2] - 1.40))
implicit_cut(jk, lambda P: hemz(P) - P[:, 2])
def tab_fold(p, fine):
    z = p[:, 2]; phi = np.arctan2(p[:, 0], -(p[:, 1] + .02)); n1 = vnoise(p, 6, 311); n2 = vnoise(p, 11, 312)
    d = np.full(len(p), .0105)
    waist = np.exp(-((z - 1.05) / .04) ** 2)
    d += .003 * ridge(2 * np.pi * z / .032 + 5 * n1 + .8 * np.sin(2 * phi), 1.6) * waist * (.3 + .7 * sstep(.3, .7, n2))
    d -= .004 * np.exp(-((z - 1.003) / .022) ** 2)
    skirt = 1 - sstep(.97, 1.0, z); d += skirt * .004
    d += .003 * (fbm(p, 9, 3, 313) - .5)
    if fine:
        d += .0010 * ridge(2 * np.pi * z / .012 + 7 * n2 + 2 * phi, 1.4) * waist * sstep(.35, .7, vnoise(p, 14, 314))
        d += .0015 * (fbm(p, 30, 4, 315) - .5)
        d += .0012 * ridge(2 * np.pi * (p[:, 0] * .6 + z) / .045 + 6 * vnoise(p, 5, 316), 3.0) * sstep(.45, .75, vnoise(p, 4, 317))
    return d
def tab_class(C, Nn):
    front = (C[:, 1] + .02) < 0
    return np.where(C[:, 2] > 1.40, np.where(C[:, 1] < 0, 13, 14), np.where(front, np.where(C[:, 0] > 0, 11, 15), 12))
tab_charts = {13: ('planar', (0, 0, 1.3), (1, 0, 0), (0, -.6, .8)), 14: ('planar', (0, 0, 1.3), (-1, 0, 0), (0, .6, .8)),
              11: ('cyl', TA, (0, -1, 0), .16), 15: ('cyl', TA, (0, -1, 0), .16), 12: ('cyl', TA, (0, 1, 0), .16)}
def tab_seams(p):
    BIG = 1.0; z = p[:, 2]; x = np.abs(p[:, 0]); y = p[:, 1]
    side = np.where((z < 1.36) & (x > .08), np.abs(y + .012), BIG); shoulder = np.where((z > 1.44) & (x > .07), np.abs(y - .012), BIG)
    seam = np.minimum(side, shoulder); ah = folds.arm_h(p)
    st = np.minimum.reduce([np.abs(seam - .0045), np.abs(ah + .003), np.abs(ah + .008), np.abs(neck_r(p) - .124) + (z < 1.39) * 1.0, np.abs(z - hemz(p) - .008), np.abs(z - hemz(p) - .013)])
    return seam, st
tab, tab_hi = G.finish(jk, tab_fold, 1900, tab_class, tab_charts, 'leather_tabard', 'Tabard', lip=(.003, .014), seams=tab_seams)
made += [tab, tab_hi]

# ------------------------------------------------------------------ BLUE PADDED COLLAR
cow_bvh = bvh_of([tab, bv]); sbvh = bvh_of(D['Skin'])
def cowl(nu, nr, name, fine):
    ph = np.linspace(0, 2 * np.pi, nu, endpoint=False) + 2.6; dirs = np.stack([np.sin(ph), -np.cos(ph), np.zeros(nu)], 1); front = (.5 + .5 * np.cos(ph)) ** 2
    NA = 72; pa = np.linspace(0, 2 * np.pi, NA, endpoint=False); rt = []
    for a_ in pa:
        ax = np.array((0, .008 + .25 * (1.530 - 1.5), 1.530)); d = np.array([math.sin(a_), -math.cos(a_), 0]); hit = sbvh.ray_cast(Vector(ax + d * .2), Vector(-d), .2)
        rt.append(float(np.linalg.norm(np.array(hit[0]) - ax)) if hit[0] is not None else .062)
    rt = np.array(rt)
    for _ in range(8): rt = (np.roll(rt, 1) + 2 * rt + np.roll(rt, -1)) / 4
    rt = np.minimum(np.interp(ph % (2 * np.pi), np.concatenate([pa, [2 * np.pi]]), np.concatenate([rt, rt[:1]])), .085)
    kk = np.linspace(0, 1, nr); P = np.zeros((nr, nu, 3))
    for i, k in enumerate(kk):
        if k < .62:      # the cape part lying on the shoulders and chest
            t = k / .62; rho = .134 + (.082 - .134) * t ** .9
            for j in range(nu):
                g = np.array([0, .006, 1.505]) + dirs[j] * rho * (1 + .22 * front[j] * (1 - t)) + np.array([0, 0, -(rho - .08) * 1.15 - .075 * front[j] * (1 - t) ** 1.3])
                loc, nrm, _, _ = cow_bvh.find_nearest(Vector(g)); nrm = np.array(nrm)
                P[i, j] = np.array(loc) + nrm * (.0135 - .004 * t + .0035 * math.exp(-(t / .12) ** 2))
        else:            # the standing neck band
            t = (k - .62) / .38; zt = 1.492 + (1.545 - 1.492) * min(t / .8, 1.0); ax = np.array((0, .008 + .25 * (zt - 1.5), zt))
            off = .0095 - .004 * min(t / .8, 1) if t <= .8 else .0055 - .0045 * (t - .8) / .2
            if t > .8: ax = ax + np.array([0, 0, -.006 * (t - .8) / .2])
            P[i] = ax + dirs * (rt + off)[:, None]
    for _ in range(2):   # relax the cape rows
        m = int(nr * .62); P[1:m - 1] = (P[:m - 2] + 2 * P[1:m - 1] + P[2:m]) / 4; P[:m] = (np.roll(P[:m], 1, 1) + 2 * P[:m] + np.roll(P[:m], -1, 1)) / 4
    flat = P.reshape(-1, 3); phf = np.tile(ph, nr); kf = np.repeat(kk, nu); cape = sstep(.66, .5, kf)
    d = .0022 * ridge(phf * 20 + 2 * vnoise(flat, 9, 321), 1.2) * cape + .0018 * (fbm(flat, 10, 3, 322) - .5)
    if fine: d += .0009 * (fbm(flat, 45, 3, 323) - .5) + .0008 * ridge(phf * 61 + 8 * vnoise(flat, 15, 324), 1.5) * sstep(.4, .7, vnoise(flat, 9, 325))
    o = G.grid_obj(name, P); o.data.update(); set_co(o.data, flat + normals_np(o.data) * d[:, None])
    q = np.abs(((phf * 20 / (2 * np.pi) + .5) % 1.0) - .5) * (2 * np.pi * .11 / 20)
    return o, np.where(cape > .5, q, 1.0), np.minimum.reduce([np.where(cape > .5, q, 1.0), np.abs(kf - .035) * .15 + (kf > .2) * 1.0, np.abs(kf - .93) * .1 + (kf < .7) * 1.0])
col, _, _ = cowl(36, 12, 'Collar', False); col_hi, sm_, st_ = cowl(288, 96, 'Collar_HI', True)
G.put(col_hi, 'd_seam', sm_); G.put(col_hi, 'd_stitch', st_)
for o in (col, col_hi): G.set_chart(o, 1); G.tag(o, 'wool_blue', 'outfit'); smooth_shade(o)
add_lips(col, .004, .010, select=lambda c: c.z < 1.47)
made += [col, col_hi]

# ------------------------------------------------------------------ MAIL SKIRT
leg_bvh = bvh_of([bv, tro])
ZMW, ZMH = 1.012, .640
def mail(nu, nr, name):
    phi = 2.5 + np.linspace(0, 2 * np.pi, nu, endpoint=False); cdir = np.stack([np.sin(phi), -np.cos(phi), np.zeros(nu)], 1)
    NA, NZ = 96, 14; pa = np.linspace(0, 2 * np.pi, NA, endpoint=False); ca = np.stack([np.sin(pa), -np.cos(pa), np.zeros(NA)], 1); TB = np.zeros((NZ, NA)); prev = None
    for i, t in enumerate(np.linspace(0, 1, NZ)):      # radius table at a fixed resolution: low and high meshes sample the same surface
        c = np.array([0, -.02, ZMW + (ZMH - ZMW) * t]); rb = np.array([rr(leg_bvh, c, d, far=.30, default=.15) for d in ca])
        for _ in range(6): rb = (np.roll(rb, 1) + 2 * rb + np.roll(rb, -1)) / 4
        r = rb + .016 + .026 * t
        if prev is not None: r = np.maximum(r, prev - .002)
        prev = r; TB[i] = r
    P = np.zeros((nr, nu, 3))
    for i, t in enumerate(np.linspace(0, 1, nr)):
        fi = t * (NZ - 1); i0 = int(min(fi, NZ - 2)); row = TB[i0] * (1 - (fi - i0)) + TB[i0 + 1] * (fi - i0)
        r = np.interp(phi % (2 * np.pi), np.concatenate([pa, [2 * np.pi]]), np.concatenate([row, row[:1]]))
        P[i] = np.array([0, -.02, ZMW + (ZMH - ZMW) * t]) + cdir * r[:, None]
    flat = P.reshape(-1, 3); t = np.repeat(np.linspace(0, 1, nr), nu); ph = np.tile(phi, nr)
    q = np.stack([np.sin(ph) * .2, -np.cos(ph) * .2, flat[:, 2]], 1)
    d = (.002 + .010 * t) * ridge(9 * ph + 2 * vnoise(q, 4, 331), 1.4) + .004 * t * (fbm(q, 4, 2, 332) - .5) * 2
    rad = flat - np.array([0, -.02, 0]); rad[:, 2] = 0; flat = flat + rad / np.linalg.norm(rad, axis=1)[:, None] * d[:, None]
    flat[:, 2] -= .008 * np.sin(9 * ph + 2 * vnoise(q, 4, 331)) * t ** 3
    return G.grid_obj(name, flat.reshape(nr, nu, 3))
ml = mail(44, 8, 'Mail'); ml_hi = mail(352, 64, 'Mail_HI')
for o in (ml, ml_hi): G.set_chart(o, 5); G.tag(o, 'mail', 'gear'); smooth_shade(o)
add_lips(ml, .003, .012, select=lambda c: c.z < .8)
G.skirt_weights(ml, ZMW, ZMH, leg_max=.92, calf_max=0.0, top=.06, full=.70, xw=.06)
made += [ml, ml_hi]

# ------------------------------------------------------------------ PLATE HELPERS
def plate(name, fn, nu, nv, fine, chart, closed=False, seed=0, groove=True, fabric='steel'):
    """fn(u, v) -> point on the plate's outer surface. Adds rolled edges, a tooled border groove, dents and dings."""
    us = np.linspace(0, 1, nu, endpoint=not closed); vs = np.linspace(0, 1, nv)
    P = np.array([[fn(u, v) for u in us] for v in vs], float)                    # nv, nu, 3
    o = G.grid_obj(name, P, closed_u=closed); o.data.update()
    co = co_np(o.data); nr = normals_np(o.data)
    cen = co.mean(0)
    dv = np.linalg.norm(np.diff(P, axis=0), axis=2).mean(1); cv = np.concatenate([[0], np.cumsum(dv)])
    du = np.linalg.norm(np.diff(P, axis=1), axis=2).mean(0); cu = np.concatenate([[0], np.cumsum(du)])
    ev = np.minimum(cv, cv[-1] - cv)[:, None] * np.ones((1, nu)); eu = np.minimum(cu, cu[-1] - cu)[None, :] * np.ones((nv, 1)) if not closed else np.full((nv, nu), 9.0)
    e = np.minimum(ev, eu).ravel()
    wp = co + seed * 1.7
    d = .0017 * np.exp(-(e / .0035) ** 2) + .0016 * (fbm(wp, 16, 3, 340 + seed) - .5)
    rng = np.random.default_rng(100 + seed)
    for _ in range(5):   # dings from use
        c = co[rng.integers(len(co))]; d -= sstep(.006, .016, e) * rng.uniform(.0008, .002) * np.exp(-(np.linalg.norm(co - c, axis=1) / rng.uniform(.006, .014)) ** 2)
    if fine:
        if groove: d -= .0007 * np.exp(-((e - .010) / .0013) ** 2)
        d += .0004 * (fbm(wp, 80, 3, 350 + seed) - .5)
        for _ in range(14):
            c = co[rng.integers(len(co))]; d -= rng.uniform(.0003, .0009) * np.exp(-(np.linalg.norm(co - c, axis=1) / rng.uniform(.002, .005)) ** 2)
    set_co(o.data, co + nr * d[:, None]); smooth_shade(o)
    G.set_chart(o, chart); G.tag(o, fabric, 'gear')
    return o
def plate_pair(name, fn, lo, hi, chart, closed=False, seed=0, lip=(.0022, .010), rigid=None):
    a = plate(name, fn, lo[0], lo[1], False, chart, closed, seed); b = plate(name + '_HI', fn, hi[0], hi[1], True, chart, closed, seed)
    if lip: add_lips(a, lip[0], lip[1])
    if rigid: a['rigidw'] = rigid
    made.extend([a, b]); return a
def orient_out(o, ref):
    """Flip so normals face away from ref point."""
    o.data.update(); c = co_np(o.data); nrm = normals_np(o.data)
    if ((c - np.asarray(ref)) * nrm).sum() < 0:
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free(); o.data.update()
ci = [100]
def nci(): ci[0] += 1; return ci[0]
buckles = []
def small_buckle(q, nrm, tan, rigid, w=.0105, h=.0085, wire=.0013):
    nrm = nrm / np.linalg.norm(nrm); tan = tan - nrm * (tan @ nrm); tan /= np.linalg.norm(tan); bt = np.cross(nrm, tan)
    fr = []
    for k in range(10):
        a_ = 2 * np.pi * k / 10; cx_, cz_ = math.cos(a_), math.sin(a_); r_ = 1.0 / (abs(cx_ / w) ** 4 + abs(cz_ / h) ** 4) ** .25
        fr.append(q + nrm * .0016 + tan * r_ * cx_ + bt * r_ * cz_)
    b1 = G.tube('bk', fr, wire, 3, closed=True); b2 = G.tube('bkt', [q + nrm * .0022 - tan * w, q + nrm * .0028 + tan * w * 1.05], wire * .8, 3)
    b = join([b1, b2], 'bk%d' % len(buckles)); G.set_chart(b, nci()); G.tag(b, 'iron', 'gear', scale=1.5); b['rigidw'] = rigid; buckles.append(b)
def ring_strap(name, bvh, c, axis, rigid, hw=.0085, t=.0022, n=16, n_hi=88, buckle_at=None, far=.12, fabric='leather_belt'):
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis); x = np.cross(axis, [0, 0, 1.0])
    if np.linalg.norm(x) < .2: x = np.cross(axis, [0, 1.0, 0])
    x /= np.linalg.norm(x); y = np.cross(axis, x); res = None
    for hi in (False, True):
        m = n_hi if hi else n; rs = []; ds = []
        for k in range(m):
            a_ = 2 * np.pi * k / m; d = x * math.cos(a_) + y * math.sin(a_); ds.append(d); rs.append(rr(bvh, c, d, far))
        rs = np.array(rs)
        for _ in range(2): rs = (np.roll(rs, 1) + 2 * rs + np.roll(rs, -1)) / 4
        rings = [[tuple(c + d * (r + a_) + axis * b_) for a_, b_ in ((.0004, -hw), (t, -hw * .9), (t, hw * .9), (.0004, hw))] for d, r in zip(ds, rs)]
        rings.append(rings[0])
        o = loft(name + ('_HI' if hi else ''), rings, closed=False)
        G.put_lat(o, [-hw, -hw * .9, hw * .9, hw] * len(rings), hw - .0028)
        activate(o); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
        orient_out(o, c); G.set_chart(o, nci()); G.tag(o, fabric, 'gear'); smooth_shade(o); made.append(o)
        if not hi:
            o['rigidw'] = rigid; res = o
            if buckle_at is not None:
                d = x * math.cos(buckle_at) + y * math.sin(buckle_at); r = rr(bvh, c, d, far)
                small_buckle(c + d * (r + t), d, np.cross(axis, d), rigid)
    return res

# ------------------------------------------------------------------ BOOTS (first: the greaves sit over the shafts)
boots = []
for side in 'lr':
    for hi in (False, True):
        b = G.boot(side, 96 if hi else 12, 160 if hi else 15, hi, 'Boot_%s%s' % (side, '_HI' if hi else ''))
        s = G.sole(side, 80 if hi else 14, 'Sole_%s%s' % (side, '_HI' if hi else ''))
        G.set_chart(b, 31 if side == 'l' else 32); G.set_chart(s, 33 if side == 'l' else 34)
        G.tag(b, 'leather_grey', 'gear'); G.tag(s, 'leather_sole', 'gear')
        if not hi: add_lips(b, .003, .012, select=lambda c: c.z > .3); boots.append(b)
        made += [b, s]

# ------------------------------------------------------------------ PAULDRONS, VAMBRACES, GREAVES, KNEE COPS
for sg, sd in ((1, 'l'), (-1, 'r')):
    M = np.array([sg, 1, 1.0]); Sx, Ex, Wx, Kx, Ax = S * M, E_ * M, Wr * M, K * M, A * M
    du_, df_ = dU * M, dF * M
    upv = np.array([sg * .6, 0, .8]); upv = upv - du_ * (upv @ du_); upv /= np.linalg.norm(upv); fw = np.cross(du_, upv) * sg
    arm_bvh = body_bvh
    # main shoulder cop: an ellipsoidal dome over the deltoid
    Cd = Sx - upv * .004
    def dome(u, v, Rr=.076, Ra=.088):
        a_ = (u - .5) * 2 * 1.75; la = -.80 + 1.42 * v
        return Cd + (upv * math.cos(a_) + fw * math.sin(a_)) * Rr * math.cos(la) * (1 + .05 * math.cos(a_)) + du_ * Ra * math.sin(la)
    p1 = plate_pair('Pauldron_%s' % sd, dome, (15, 9), (150, 96), nci(), seed=1 + (sg < 0), rigid='upperarm_%s:.55,clavicle_%s:.45' % (sd, sd))
    orient_out(p1, Sx); orient_out(D['Pauldron_%s_HI' % sd], Sx)
    def lame(b0, b1, r0, r1, Aw):
        def f(u, v):
            a_ = (u - .5) * 2 * Aw; b = b0 + (b1 - b0) * v; r = r0 + (r1 - r0) * v + .004 * math.sin(math.pi * v)
            return Sx + du_ * b + (upv * math.cos(a_) + fw * math.sin(a_)) * r
        return f
    for k, (b0, b1, r0, r1, Aw) in enumerate(((.060, .112, .0665, .0625, 1.60), (.100, .150, .0620, .058, 1.50))):
        pl = plate_pair('Lame%d_%s' % (k, sd), lame(b0, b1, r0, r1, Aw), (13, 4), (130, 44), nci(), seed=5 + k + 3 * (sg < 0), rigid='upperarm_%s:1' % sd)
        orient_out(pl, Sx + du_ * b0); orient_out(D['Lame%d_%s_HI' % (k, sd)], Sx + du_ * b0)
    pl_bvh = bvh_of([D['Lame1_%s' % sd], D['Skin'], bv])
    ring_strap('ArmStrap_%s' % sd, bvh_of([D['Skin'], bv]), Sx + du_ * .138, du_, 'upperarm_%s:1' % sd, hw=.009, buckle_at=math.pi * .9, far=.10)
    # vambrace
    LFx = np.linalg.norm(Wx - Ex); xv = np.cross(df_, [0, 0, 1.0]); xv /= np.linalg.norm(xv); yv = np.cross(df_, xv)
    def vamb(u, v):
        f = .080 + .182 * v; a_ = 2 * np.pi * u; d = xv * math.cos(a_) + yv * math.sin(a_); c = Ex + df_ * f
        r = rr(arm_bvh, c, d, .10, .04) + .0058 + .006 * float(sstep(.16, 0, v)) + .002 * float(sstep(.9, 1, v))
        return c + d * r
    def smooth_tube(fn, nu, nv):
        Pg = np.array([[fn(u, v) for u in np.linspace(0, 1, nu, endpoint=False)] for v in np.linspace(0, 1, nv)])
        for _ in range(3): Pg = (np.roll(Pg, 1, 1) + 2 * Pg + np.roll(Pg, -1, 1)) / 4
        Pg[1:-1] = (Pg[:-2] + 2 * Pg[1:-1] + Pg[2:]) / 4
        def g(u, v):
            i = min(int(round(v * (nv - 1))), nv - 1); j = int(round(u * nu)) % nu; return Pg[i, j]
        return g
    gv = smooth_tube(vamb, 96, 40)
    def gvi(u, v):   # bilinear lookup so the low and high meshes describe the same surface
        return gv(u, v)
    va = plate('Vambrace_%s' % sd, gvi, 24, 9, False, nci(), True, 11 + (sg < 0)); vb = plate('Vambrace_%s_HI' % sd, gvi, 96, 40, True, va.data.attributes['chart'].data[0].value, True, 11 + (sg < 0))
    for o in (va, vb): orient_out(o, Ex + df_ * .17)
    add_lips(va, .0022, .010); va['rigidw'] = 'lowerarm_%s:1' % sd; made += [va, vb]
    vbvh = bvh_of(va)
    # gauntlet: a flared steel cuff over the wrist and a plate on the back of the hand (the fingers are gloved in the skin set)
    def gcuff(u, v):
        f = LFx - .088 + .086 * v; a_ = 2 * np.pi * u; d = xv * math.cos(a_) + yv * math.sin(a_); c = Ex + df_ * f
        return c + d * (rr(arm_bvh, c, d, .10, .035) + .0090 + .015 * float(sstep(.8, 0, v)) + .0015 * float(sstep(.92, 1, v)))
    gcs = smooth_tube(gcuff, 96, 30)
    ca = plate('GauntletCuff_%s' % sd, gcs, 18, 6, False, nci(), True, 41 + (sg < 0)); cb = plate('GauntletCuff_%s_HI' % sd, gcs, 96, 30, True, ca.data.attributes['chart'].data[0].value, True, 41 + (sg < 0))
    for o in (ca, cb): orient_out(o, Ex + df_ * (LFx - .045))
    add_lips(ca, .0022, .010); ca['rigidw'] = 'lowerarm_%s:1' % sd; made += [ca, cb]
    HB = {n_: np.array(arm.data.bones[n_ + '_' + sd].head_local) for n_ in ('hand', 'index_01', 'pinky_01', 'middle_01')}
    hx = HB['middle_01'] - HB['hand']; Lh = np.linalg.norm(hx); hx /= Lh; hy = HB['index_01'] - HB['pinky_01']; hy = hy - hx * (hy @ hx); Wh = np.linalg.norm(hy); hy /= Wh; hn_ = np.cross(hx, hy)
    if hn_ @ np.array([sg * 1.0, 0, .5]) < 0: hn_ = -hn_
    sk_bvh = bvh_of(D['Skin'])
    def hplate(u, v):
        p0 = HB['hand'] + hx * (Lh * (-.02 + 1.10 * v)) + hy * ((u - .5) * Wh * 1.75 * (.82 + .18 * v))
        hit = sk_bvh.ray_cast(Vector(p0 + hn_ * .05), Vector(-hn_), .10)
        q = np.array(hit[0]) if hit[0] is not None else p0 + hn_ * .010
        return q + hn_ * (.0042 + .0035 * math.sin(math.pi * u) ** .7 + .0025 * float(sstep(.78, 1.0, v)))
    hp_ = plate_pair('HandPlate_%s' % sd, hplate, (8, 6), (80, 64), nci(), seed=51 + (sg < 0), rigid='hand_%s:1' % sd)
    orient_out(hp_, HB['hand'] + hx * Lh * .5 - hn_ * .02); orient_out(D['HandPlate_%s_HI' % sd], HB['hand'] + hx * Lh * .5 - hn_ * .02)
    for f_ in (.125, .225): ring_strap('VamStrap%d_%s' % (int(f_ * 1000), sd), vbvh, Ex + df_ * f_, df_, 'lowerarm_%s:1' % sd, hw=.0075, buckle_at=3.5, far=.10)
    # greave over the boot shaft
    gb = bvh_of([bv] + [b for b in boots if b.name.endswith('_' + sd)])
    dk = (Ax - Kx); Lk = np.linalg.norm(dk); dk /= Lk; xg = np.array([sg * 1.0, 0, 0]); xg = xg - dk * (xg @ dk); xg /= np.linalg.norm(xg); yg = np.cross(dk, xg)
    def grv(u, v):
        s_ = .050 + (.345 - .050) * v; a_ = 2 * np.pi * u; d = xg * math.cos(a_) + yg * math.sin(a_); c = Kx + dk * s_
        front = max(0.0, -d[1])
        r = rr(gb, c, d, .12, .05) + .0062 + .0035 * front ** 4 + .004 * float(sstep(.9, 1, v)) + .003 * float(sstep(.08, 0, v))
        return c + d * r
    gg = smooth_tube(grv, 96, 48)
    ga = plate('Greave_%s' % sd, gg, 22, 10, False, nci(), True, 21 + (sg < 0)); gh = plate('Greave_%s_HI' % sd, gg, 96, 48, True, ga.data.attributes['chart'].data[0].value, True, 21 + (sg < 0))
    for o in (ga, gh): orient_out(o, Kx + dk * .2)
    add_lips(ga, .0022, .010); ga['rigidw'] = 'calf_%s:1' % sd; made += [ga, gh]
    gbv = bvh_of(ga)
    for s_ in (.11, .29): ring_strap('GreaveStrap%d_%s' % (int(s_ * 100), sd), gbv, Kx + dk * s_, dk, 'calf_%s:1' % sd, hw=.008, buckle_at=(0.25 if sg > 0 else math.pi - .25), far=.12)
    # knee cop
    Ck = Kx + np.array([0, .006, -.004])
    def cop(u, v):
        a_ = (u - .5) * 2 * 1.55; la = -.80 + 1.60 * v
        return Ck + np.array([math.sin(a_) * .066 * math.cos(la), -math.cos(a_) * .078 * math.cos(la) * (1 + .10 * math.cos(a_) ** 6), .072 * math.sin(la)])
    kc = plate_pair('KneeCop_%s' % sd, cop, (13, 8), (130, 84), nci(), seed=31 + (sg < 0), rigid='calf_%s:.6,thigh_%s:.4' % (sd, sd))
    orient_out(kc, Kx); orient_out(D['KneeCop_%s_HI' % sd], Kx)
    if False: ring_strap('KneeStrap_%s' % sd, bvh_of([bv]), Kx + np.array([0, 0, .0]), dk, 'calf_%s:.6,thigh_%s:.4' % (sd, sd), hw=.008, far=.12)

# ------------------------------------------------------------------ BELT, BUCKLE, BALDRIC
torso_bvh = bvh_of([tab, ml])
(belt, belt_hi), bp, bt = G.make_belt('Belt', torso_bvh, 1.000, 'leather_belt', h=.019, t=.0045, drop=.008, n_lo=48)
bk, bk_hi = G.make_buckle('Buckle', bp, 'brass', W=.024, H=.024, t=bt)
belt['rigidw'] = 'pelvis:.6,spine_01:.4'; bk['rigidw'] = 'pelvis:.6,spine_01:.4'
made += [belt, belt_hi, bk, bk_hi]
tb = bvh_of([tab, col])
g = [(-.105, .020, 1.52), (-.085, -.085, 1.47), (-.045, -.135, 1.36), (.02, -.15, 1.24), (.085, -.14, 1.13), (.145, -.075, 1.045), (.165, .01, 1.035),
     (.13, .09, 1.07), (.06, .12, 1.18), (-.02, .125, 1.31), (-.075, .10, 1.43), (-.105, .045, 1.515)]
bd_ = G.strap_on('Baldric', g, tb, 56, .034, .0034, .0014, nci(), 'leather_belt'); made.append(bd_)
h = dup(bd_, 'Baldric_HI'); subdivide(h, 2, simple=True); made.append(h)
q, nrm = G.on_surface(tb, (-.02, -.15, 1.31), .0048)
small_buckle(q, nrm, np.array([.45, -.05, -.85]), 'spine_04:1', w=.021, h=.016, wire=.0022)
for b in buckles:
    made.append(b); hh = dup(b, b.name + '_HI'); subdivide(hh, 1); made.append(hh)

for o in made:
    if not o.name.endswith('_HI'): G.fix_lip_charts(o)
    smooth_shade(o)
    if 'UVMetric' not in o.data.uv_layers: log('NO UV', o.name)
log('game tris', {o.name: tri_count(o) for o in made if not o.name.endswith('_HI')}, 'total', sum(tri_count(o) for o in made if not o.name.endswith('_HI')))
save_blend(filepath=str(OUT / N / 'Work/milder_garments_b.blend'))
if 'norender' in args(): sys.exit(0)
cols = {'wool_tan': (.30, .17, .07), 'leather_tabard': (.33, .13, .04), 'wool_blue': (.03, .05, .18), 'mail': (.4, .4, .42), 'steel': (.4, .4, .42), 'leather_grey': (.07, .07, .07),
        'leather_sole': (.04, .03, .02), 'leather_belt': (.09, .04, .02), 'brass': (.7, .5, .2), 'iron': (.3, .3, .3)}
hi_view = 'hi' in args()
for o in D:
    if o.type != 'MESH': continue
    o.hide_render = not ((o.name == 'Skin') or ('fabric' in o and (o.name.endswith('_HI') == hi_view)))
    if 'fabric' in o:
        mt = bpy.data.materials.new('pv'); mt.use_nodes = True; bs = mt.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value = (*cols[o['fabric']], 1); bs.inputs['Roughness'].default_value = .6
        if o['fabric'] in ('steel', 'mail', 'iron', 'brass'): bs.inputs['Metallic'].default_value = 1; bs.inputs['Roughness'].default_value = .4
        o.data.materials.clear(); o.data.materials.append(mt)
sm = bpy.data.materials.new('pvs'); sm.use_nodes = True; sm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.6, .42, .33, 1); D['Skin'].data.materials.clear(); D['Skin'].data.materials.append(sm)
setup_render(samples=24, res=(1500, 1000)); bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = .08
tg = 'g_hi' if hi_view else 'g_lo'
shoot(OUT / N / ('Review/%s_front.png' % tg), (0.9, -3.6, 1.2), (0, 0, .92), lens=55)
shoot(OUT / N / ('Review/%s_back.png' % tg), (-1.2, 3.4, 1.4), (0, 0, .92), lens=55)
