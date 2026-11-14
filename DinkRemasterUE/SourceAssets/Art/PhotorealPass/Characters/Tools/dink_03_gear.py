"""Stage 3: boots, bracers, belt + buckle + tail, backpack + straps. Analytic lofts, built at game resolution;
bake sources (*_HI) are the same generators at higher density with the fine folds switched on."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/Work/dink_garments_a.blend'))
arm = bpy.data.objects['Armature']; B = arm.data.bones
def bh(n): return np.array(B[n].head_local)
S, E_, Wr = bh('upperarm_l'), bh('lowerarm_l'), bh('hand_l')
T, K, A, BALL = bh('thigh_l'), bh('calf_l'), bh('foot_l'), bh('ball_l')
MIR = np.array([-1, 1, 1.0])
D = bpy.data.objects
body_bvh = bvh_of([D['BodyVol'], D['Skin']])
made = []

def catmull(pts, n):
    pts = [np.asarray(p, float) for p in pts]; P = [pts[0]] + pts + [pts[-1]]; out = []
    segs = len(pts) - 1
    for k in range(n):
        u = k / (n - 1) * segs; i = min(int(u), segs - 1); t = u - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)

def interp(x, xs, ys):
    return np.interp(x, xs, ys)

def put_lat(o, lat, c):
    """Per-vertex signed lateral coordinate -> 'd_stitch' = |lat| - c after subdivision (see bake stage)."""
    a = o.data.attributes.new('lat', 'FLOAT', 'POINT'); v = np.zeros(len(o.data.vertices), np.float32); v[:len(lat)] = lat
    a.data.foreach_set('value', v); o['lat_c'] = c

def tag(o, fabric, mat='gear', scale=1.0):
    o['fabric'] = fabric; o['mat'] = mat; o['texel_scale'] = scale
    if not o.data.attributes.get('chart'):
        o.data.attributes.new('chart', 'INT', 'FACE')
    return o

def set_chart(o, cid):
    a = o.data.attributes.get('chart') or o.data.attributes.new('chart', 'INT', 'FACE')
    a.data.foreach_set('value', [cid] * len(o.data.polygons))

# ================================================================== BOOTS
def boot(side, nu, nrings, fine, name):
    sg = 1 if side == 'l' else -1
    f = BALL - A; f[2] = 0; f /= np.linalg.norm(f); up = np.array([0, 0, 1.0]); lat = np.cross(f, up)
    calf = lambda z: A + (K - A) * ((z - A[2]) / (K[2] - A[2]))
    ctrl = [calf(.352), calf(.27), calf(.19), A - f * .004 + up * .018, A + f * .034 - up * .020, A + f * .095 - up * .040, A + f * .160 - up * .047, A + f * .200 - up * .052, A + f * .2105 - up * .058]
    C = catmull(ctrl, nrings); 
    seg = np.linalg.norm(np.diff(C, axis=0), axis=1); arc = np.concatenate([[0], np.cumsum(seg)]); u = arc / arc[-1]
    tan = np.gradient(C, axis=0); tan /= np.linalg.norm(tan, axis=1)[:, None]
    # control arclengths of ctrl points
    ku = np.linspace(0, 1, len(ctrl))  # catmull is uniform in control index, approx.
    kidx = np.linspace(0, len(ctrl) - 1, nrings)
    a_prof = interp(kidx, range(9), [.057, .053, .044, .040, .043, .049, .046, .030, .010])
    bf_prof = interp(kidx, range(9), [.059, .055, .045, .044, .046, .038, .030, .020, .008])   # toward +nvec (front / top)
    bb_prof = interp(kidx, range(9), [.061, .061, .049, .064, .072, .042, .035, .026, .010])   # toward -nvec (back / bottom)
    phi = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    rings = []
    rngp = np.random.default_rng(3 if side == 'l' else 11)
    for i in range(nrings):
        t = tan[i]; nv = np.cross(lat, t); nv /= np.linalg.norm(nv)   # shaft: forward; foot: up
        if nv @ (f + up) < 0: nv = -nv
        cs, sn = np.cos(phi), np.sin(phi)
        b = np.where(sn > 0, bf_prof[i], bb_prof[i])
        # superellipse-ish on the foot for a flatter top
        ex = np.where(sn > 0, 2.0, 2.0 + 2.2 * sstep(3.6, 4.6, kidx[i]) * (1 - sstep(7.0, 8.0, kidx[i])))   # flat, full bottom under the foot
        r = 1.0 / (np.abs(cs / a_prof[i]) ** ex + np.abs(sn / b) ** ex) ** (1 / ex)
        P = C[i][None, :] + (lat[None, :] * (cs * r)[:, None] + nv[None, :] * (sn * r)[:, None])
        rings.append(P)
    P = np.array(rings)  # nr, nu, 3
    # keep the shaft outside the tucked trouser
    for i in range(nrings):
        if C[i][2] > .255:
            for j in range(nu):
                d = P[i, j] - C[i]; L = np.linalg.norm(d); d /= L
                hit = body_bvh.ray_cast(Vector(C[i] * (MIR if 0 else 1) + d * .2), Vector(-d), .2)
                if hit[0] is not None:
                    need = (np.array(hit[0]) - C[i]) @ d + .0055
                    if need > L: P[i, j] = C[i] + d * need
    flat = P.reshape(-1, 3)
    # folds: slouch on the shaft, creases over the instep
    kk = np.repeat(kidx, nu); ph = np.tile(phi, nrings); sn = np.sin(ph)
    wp = flat * np.array([sg, 1, 1.0]) + (0 if side == 'l' else 3.7)
    n1 = vnoise(wp, 9, 31); n2 = vnoise(wp, 16, 32)
    shaft = 1 - sstep(2.2, 3.0, kk); zz = flat[:, 2]
    d = .005 * ridge(2 * np.pi * zz / .040 + 9 * fbm(wp, 8, 2, 37) + 1.2 * sn, 1.6) * shaft * sstep(.5, 1.3, kk) * (.3 + .7 * sstep(.35, .65, n2))
    instep = np.exp(-((kk - 3.3) / .7) ** 2) * np.maximum(sn, 0)
    d += (.003 if fine else .0012) * ridge(2 * np.pi * kk / .42 + 4 * n1, 1.5) * instep
    d += .0038 * sstep(.312, .316, zz) * shaft      # turned-down cuff at the top of the shaft
    d += .002 * (fbm(wp, 12, 3, 33) - .5)
    d += .004 * sstep(.25, 0, kk)   # flared, rolled top
    if fine:
        d += .0010 * ridge(2 * np.pi * zz / .011 + 7 * n2 + 2 * sn, 1.4) * shaft * sstep(.4, .7, vnoise(wp, 14, 34))
        d += .0012 * ridge(2 * np.pi * kk / .16 + 6 * n2, 1.4) * instep
        d += .0008 * (fbm(wp, 60, 3, 35) - .5)
        toe = sstep(5.6, 7, kk) * (1 - sstep(7.6, 8, kk)); d += .0012 * (fbm(wp, 25, 3, 36) - .5) * toe   # scuffed toe dents
    cen = np.repeat(C, nu, axis=0); rad = flat - cen; rl = np.linalg.norm(rad, axis=1)
    flat = cen + rad * ((rl + d) / rl)[:, None]
    flat[:, 2] = np.maximum(flat[:, 2], .0125)
    if side == 'r': flat = flat * MIR
    P = flat.reshape(nrings, nu, 3)
    o = loft(name, [list(map(tuple, r)) for r in P], cap_end=True)
    return o

def sole(side, nx, name):
    f = BALL - A; f[2] = 0; f /= np.linalg.norm(f); up = np.array([0, 0, 1.0]); lat = np.cross(f, up)
    xs = np.linspace(-.071, .2135, nx)
    w = interp(xs, [-.071, -.066, -.05, -.02, .03, .07, .12, .165, .195, .209, .2135], [.004, .020, .036, .042, .043, .045, .0505, .047, .034, .018, .004])
    sh = interp(xs, [-.071, .05, .12, .2135], [0, .0, -.004, .004])   # outer-side swing of the forepart
    rings = []
    for x, ww, s_ in zip(xs, w, sh):
        c = A * np.array([1, 1, 0]) + f * x + lat * s_
        ww += .0005
        sec = [(-ww, .0015), (-ww - .0012, .006), (-ww - .0008, .0115), (-ww + .003, .0145), (ww - .003, .0145), (ww + .0008, .0115), (ww + .0012, .006), (ww, .0015)]
        heel = .004 * sstep(.0, -.03, x)  # slightly thicker heel lift
        rings.append([c + lat * a + up * (b + (heel if b > .01 else 0)) for a, b in sec])
    if side == 'r': rings = [[p * MIR for p in r] for r in rings]
    return loft(name, [list(map(tuple, r)) for r in rings], cap_end=True, cap_start=True)

for side in 'lr':
    for hi in (False, True):
        nm = 'Boot_%s%s' % (side, '_HI' if hi else '')
        b = boot(side, 96 if hi else 26, 160 if hi else 34, hi, nm)
        s = sole(side, 80 if hi else 22, 'Sole_%s%s' % (side, '_HI' if hi else ''))
        set_chart(b, 31 if side == 'l' else 32); set_chart(s, 33 if side == 'l' else 34)
        tag(b, 'leather_boot'); tag(s, 'leather_sole')
        if not hi: add_lips(b, .003, .012, select=lambda c: c.z > .3)
        made += [b, s]

# ================================================================== BRACERS
def bracer(side, nu, nr, fine, name):
    sg = 1 if side == 'l' else -1
    dF = (Wr - E_) / np.linalg.norm(Wr - E_)
    x = np.cross(dF, [0, 0, 1.0]); x /= np.linalg.norm(x); y = np.cross(dF, x)
    fs = np.linspace(.110, .259, nr); phi = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    R = np.zeros((nr, nu))
    for i, f in enumerate(fs):
        c = E_ + dF * f
        for j, p in enumerate(phi):
            d = x * np.cos(p) + y * np.sin(p)
            hit = body_bvh.ray_cast(Vector(c + d * .12), Vector(-d), .12)
            R[i, j] = ((np.array(hit[0]) - c) @ d if hit[0] is not None else .04)
    for _ in range(3): R = (np.roll(R, 1, 1) + R * 2 + np.roll(R, -1, 1)) / 4
    R = np.maximum(R, np.maximum.accumulate(R[::-1], axis=0)[::-1] * .0 + R)  # keep
    R += .0050
    rings = []
    L = fs[-1] - fs[0]
    for i, f in enumerate(fs):
        c = E_ + dF * f; t = (f - fs[0]); te = L - t
        prof = .0022 * (np.exp(-(t / .005) ** 2) + np.exp(-(te / .005) ** 2))   # rolled rims
        prof += .003 * sstep(.03, 0, t)                                            # flare toward the elbow
        prof -= .0012 * (np.exp(-((t - .016) / .0018) ** 2) + np.exp(-((te - .016) / .0018) ** 2))  # tooled border line
        ring = []
        for j, p in enumerate(phi):
            d = x * np.cos(p) + y * np.sin(p)
            lace = np.exp(-(((p - 3.6) + np.pi) % (2 * np.pi) - np.pi) ** 2 / .012)   # lacing gap along the inner side
            r = R[i, j] + prof - .0022 * lace
            ring.append(c + d * r)
        rings.append(ring)
    P = np.array(rings).reshape(-1, 3)
    wp = P + (0 if side == 'l' else 2.3)
    dd = .0012 * (fbm(wp, 14, 3, 41) - .5)
    if fine: dd += .0008 * ridge(2 * np.pi * np.repeat(fs, nu) / .013 + 6 * vnoise(wp, 18, 42), 1.5) * sstep(.45, .75, vnoise(wp, 9, 43)) + .0006 * (fbm(wp, 60, 3, 44) - .5)
    cen = np.repeat(np.array([E_ + dF * f for f in fs]), nu, axis=0); rad = P - cen; rl = np.linalg.norm(rad, axis=1)
    P = cen + rad * ((rl + dd) / rl)[:, None]
    if side == 'r': P = P * MIR
    o = loft(name, [list(map(tuple, r)) for r in P.reshape(nr, nu, 3)])
    # laces: zigzag cord over the gap (game mesh only; baked flat on HI too)
    pts = []
    n_x = 8
    for k in range(n_x + 1):
        f = fs[0] + .012 + (L - .024) * k / n_x
        i = int(round((f - fs[0]) / L * (nr - 1)))
        p = 3.6 + (.17 if k % 2 else -.17)
        j = int(round(p / (2 * np.pi) * nu)) % nu
        d = x * np.cos(p) + y * np.sin(p); c = E_ + dF * f
        q = c + d * (R[i, j] + .0018)
        pts.append(q * (MIR if side == 'r' else 1))
    return o, pts

def tube(name, pts, r, sides=5, closed=False):
    pts = [np.asarray(p, float) for p in pts]; rings = []
    n = len(pts)
    prev_x = None
    for i in range(n):
        a = pts[(i - 1) % n] if (closed or i > 0) else pts[i]; b = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        t = b - a; t /= max(np.linalg.norm(t), 1e-9)
        x = np.cross(t, [0, 0, 1.0]) if prev_x is None else prev_x - t * (prev_x @ t)
        if np.linalg.norm(x) < 1e-6: x = np.cross(t, [1.0, 0, 0])
        x /= np.linalg.norm(x); y = np.cross(t, x); prev_x = x
        rr = r(i / (n - 1)) if callable(r) else r
        rings.append([tuple(pts[i] + (x * math.cos(k * 2 * math.pi / sides) + y * math.sin(k * 2 * math.pi / sides)) * rr) for k in range(sides)])
    if closed: rings.append(rings[0])
    o = loft(name, rings, cap_end=not closed, cap_start=not closed)
    if closed:
        activate(o); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
    return o

for side in 'lr':
    lo, lace_pts = bracer(side, 28, 14, False, 'Bracer_' + side); hi, _ = bracer(side, 128, 96, True, 'Bracer_%s_HI' % side)
    for o in (lo, hi): set_chart(o, 41 if side == 'l' else 42); tag(o, 'leather_red')
    add_lips(lo, .003, .010)
    lc = tube('BracerLace_' + side, lace_pts, .0014, 5); set_chart(lc, 43); tag(lc, 'cord', scale=.5)
    made += [lo, hi, lc]

# ================================================================== BELT
jerkin_bvh = bvh_of(D['Jerkin'])
def belt_path(n):
    out = []
    for k in range(n):
        p = 2 * np.pi * k / n
        z = 1.003 - .010 * np.cos(p)        # sits a little lower in front
        d = np.array([np.sin(p), -np.cos(p), 0]); c = np.array([0, -.02, z])
        hit = jerkin_bvh.ray_cast(Vector(c + d * .4), Vector(-d), .4)
        r = (np.array(hit[0]) - c) @ d if hit[0] is not None else .15
        out.append((p, c, d, r))
    rr = np.array([o[3] for o in out])
    for _ in range(4): rr = (np.roll(rr, 1) + 2 * rr + np.roll(rr, -1)) / 4
    return [(p, c, d, r) for (p, c, d, _), r in zip(out, rr)]
def belt(n, name):
    rings = []
    for p, c, d, r in belt_path(n):
        r0 = r + .0012; up = np.array([0, 0, 1.0]); h = .0175; t = .0042
        sec = [(0, -h), (t * .75, -h - .0006), (t, -h + .003), (t * 1.08, 0), (t, h - .003), (t * .75, h + .0006), (0, h)]
        rings.append([tuple(c + d * (r0 + a) + up * b) for a, b in sec] + [tuple(c + d * (r0 - .001) + up * 0)])
    rings.append(rings[0])
    o = loft(name, rings)
    put_lat(o, [-.0175, -.0181, -.0145, 0, .0145, .0181, .0175, 0] * len(rings), .0135)
    activate(o); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
    return o
for hi in (False, True):
    o = belt(256 if hi else 72, 'Belt' + ('_HI' if hi else '')); set_chart(o, 51); tag(o, 'leather_belt'); made.append(o)
bp = belt_path(256)
def belt_pt(p, out=0.0, dz=0.0):
    k = int(round((p % (2 * np.pi)) / (2 * np.pi) * 256)) % 256; _, c, d, r = bp[k]
    return c + d * (r + .0012 + .0045 + out) + np.array([0, 0, dz]), d
# buckle: cast brass frame lying on the belt at centre front
p0, d0 = belt_pt(0.0, .0026)
xax = np.array([1.0, 0, 0]); zax = np.array([0, 0, 1.0])
def on_belt(xo, zo, out=0.0):
    """Point at lateral offset xo (m along the belt), height zo, following the belt curve."""
    r = bp[0][3]; ang = xo / r
    q, d = belt_pt(ang, .0026 + out); return q + zax * zo
W_, H_ = .023, .022; cr = .008
frame = []
for k in range(40):
    a = 2 * np.pi * k / 40; cx, cz = math.cos(a), math.sin(a)
    ex = 4.0; rr = 1.0 / (abs(cx / W_) ** ex + abs(cz / H_) ** ex) ** (1 / ex)
    frame.append(on_belt(rr * cx - .004, rr * cz, .0008))
buck = tube('Buckle', frame, .0030, 8, closed=True)
bar = tube('BuckleBar', [on_belt(-.004 - W_ * .55, z_, .0004) for z_ in np.linspace(-H_, H_, 5)], .0022, 6)
tongue = tube('BuckleTongue', [on_belt(-.004 - W_ * .55, 0, .0030), on_belt(-.004, 0, .0034), on_belt(-.004 + W_ * .85, 0, .0036), on_belt(-.004 + W_ * 1.02, 0, .0030)], lambda t: .0024 - .0009 * t, 6)
bk = join([buck, bar, tongue], 'Buckle'); set_chart(bk, 52); tag(bk, 'brass', scale=1.5); made.append(bk)
bkh = dup(bk, 'Buckle_HI'); subdivide(bkh, 2); made.append(bkh)
# belt tail: through the buckle, along the belt to the wearer's left, through a keeper, then hanging
tail = []
for k in range(14):
    ang = (.012 + .11 * k / 13) / bp[0][3]
    q, d = belt_pt(ang, .0015 + .002 * math.sin(k / 13 * math.pi)); tail.append((q, d, np.array([0, 0, 1.0])))
qk, dk = belt_pt(.125 / bp[0][3], .003)
hang = []
for k in range(1, 13):
    z = qk[2] - .011 * k; ang = (.125 + .004 * k) / bp[0][3]
    dd = np.array([math.sin(ang), -math.cos(ang), 0]); c = np.array([0, -.02, z])
    hit = jerkin_bvh.ray_cast(Vector(c + dd * .4), Vector(-dd), .4)
    r = (np.array(hit[0]) - c) @ dd if hit[0] is not None else .16
    q = c + dd * (r + .006 + .003 * math.sin(k * .9))
    hang.append((q, dd, None))
rings = []
allp = tail + hang
for i, (q, d, wdir) in enumerate(allp):
    a = allp[max(i - 1, 0)][0]; b = allp[min(i + 1, len(allp) - 1)][0]; t = b - a; t /= np.linalg.norm(t)
    w = np.cross(d, t); w /= np.linalg.norm(w)
    hw = .0165 * (1 - .9 * sstep(len(allp) - 4, len(allp) - 1, i))  # pointed tip
    th = .0019
    rings.append([tuple(q + w * a_ + d * b_) for a_, b_ in ((-hw, -th), (-hw, th), (hw, th), (hw, -th))])
tl = loft('BeltTail', rings, cap_end=True, cap_start=True); set_chart(tl, 53); tag(tl, 'leather_belt'); made.append(tl)
tlh = dup(tl, 'BeltTail_HI'); subdivide(tlh, 2, simple=True); made.append(tlh)
# keeper loop
kq, kd = belt_pt(.085 / bp[0][3], 0)
kp = [kq + kd * a_ + np.array([0, 0, b_]) for a_, b_ in ((-.0058, -.021), (.0045, -.021), (.0045, .021), (-.0058, .021))]
keeper = tube('BeltKeeper', [kp[0], kp[1], kp[2], kp[3]], .0019, 4, closed=True); set_chart(keeper, 54); tag(keeper, 'leather_belt'); made.append(keeper)
kh = dup(keeper, 'BeltKeeper_HI'); made.append(kh)

# ================================================================== BACKPACK
back_bvh = bvh_of([D['Jerkin'], D['Shirt']])
def back_y(x, z):
    hit = back_bvh.ray_cast(Vector((x, .6, z)), Vector((0, -1, 0)), 1.0)
    return hit[0].y if hit[0] is not None else .1
ZB, ZT = 1.165, 1.435
def pack_surface(nz, nu, fine, seed=51):
    zs = np.linspace(0, 1, nz); phi = np.linspace(0, 2 * np.pi, nu, endpoint=False); rings = []
    for t in zs:
        z = ZB + (ZT - ZB) * t
        endr = min(1, (np.sin(np.pi * min(t, 1 - t) / .22) if min(t, 1 - t) < .11 else 1) ** .55 + .0)   # rounded top and bottom
        endr = max(endr, .12)
        hw = (.118 - .012 * t + .006 * math.sin(t * 3.1)) * (.55 + .45 * endr)
        hd = (.050 - .012 * t) * (.45 + .55 * endr) + .008 * math.exp(-((t - .3) / .25) ** 2)   # sags and bulges low (a slimmer satchel: 10 cm deep, was 11.6)
        yb = max(back_y(0, z), back_y(.07, z), back_y(-.07, z)) + .006
        cy = yb + hd
        ring = []
        for p in phi:
            cx, sy = math.cos(p), math.sin(p); ex = 3.2
            r = 1.0 / (abs(cx / hw) ** ex + abs(sy / hd) ** ex) ** (1 / ex)
            y = cy + r * sy
            if sy < 0:
                # the side that lies on the back follows the back across its width. It was flat, level with the
                # shoulder blades, so from the side the pack stood off the ribs by up to 4 cm.
                y += (back_y(r * cx, z) + .005 - y) * min(1.0, (-sy) ** .5 * 1.2)
            ring.append((r * cx, y, z))
        rings.append(ring)
    P = np.array(rings).reshape(-1, 3)
    cen = np.repeat(np.array([[0, np.mean([q[1] for q in r]), r[0][2]] for r in rings]), nu, axis=0)
    rad = P - cen; rl = np.linalg.norm(rad, axis=1)
    d = .005 * (fbm(P, 9, 3, seed) - .5) + .003 * ridge(2 * np.pi * P[:, 2] / .05 + 5 * vnoise(P, 7, seed + 1), 1.8) * sstep(.4, .7, vnoise(P, 5, seed + 2))
    if fine: d += .0012 * (fbm(P, 40, 4, seed + 3) - .5) + .001 * ridge(2 * np.pi * (P[:, 0] + P[:, 2]) / .02 + 6 * vnoise(P, 11, seed + 4), 1.5) * sstep(.5, .8, vnoise(P, 6, seed + 5))
    P = cen + rad * ((rl + d) / rl)[:, None]
    return P.reshape(nz, nu, 3)
for hi in (False, True):
    P = pack_surface(60 if hi else 16, 160 if hi else 28, hi)
    o = loft('Pack' + ('_HI' if hi else ''), [list(map(tuple, r)) for r in P], cap_end=True, cap_start=True)
    set_chart(o, 61); tag(o, 'leather_pack'); made.append(o)
pack = D['Pack']; pack_hi = D['Pack_HI']
pbvh = bvh_of(pack_hi)
def on_surface(bvh, q, off):
    loc, nrm, idx, dist = bvh.find_nearest(Vector(q))
    return np.array(loc) + np.array(nrm) * off, np.array(nrm)
def sheet(name, guide, bvh, off, nu_, nv_):
    """guide(u,v)->approximate point; projected to bvh and lifted by off(u,v)."""
    verts = []; 
    for j in range(nv_):
        for i in range(nu_):
            u, v = i / (nu_ - 1), j / (nv_ - 1); q, n = on_surface(bvh, guide(u, v), off(u, v)); verts.append(q)
    faces = [(j * nu_ + i, j * nu_ + i + 1, (j + 1) * nu_ + i + 1, (j + 1) * nu_ + i) for j in range(nv_ - 1) for i in range(nu_ - 1)]
    o = new_obj(name, verts, faces)
    uv = o.data.uv_layers.new(name='UVMetric'); V = np.array(verts).reshape(nv_, nu_, 3)
    du = np.concatenate([np.zeros((nv_, 1)), np.cumsum(np.linalg.norm(np.diff(V, axis=1), axis=2), 1)], 1).mean(0)
    dv = np.concatenate([np.zeros((1, nu_)), np.cumsum(np.linalg.norm(np.diff(V, axis=0), axis=2), 0)], 0).mean(1)
    for p in o.data.polygons:
        for li, vi in zip(p.loop_indices, p.vertices): uv.data[li].uv = (du[vi % nu_], dv[vi // nu_])
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # make sure it faces away from the surface
    bm.to_mesh(o.data); bm.free(); smooth_shade(o)
    return o
ymid = np.mean(co_np(pack.data)[:, 1]); ymax = co_np(pack.data)[:, 1].max()
def flap_guide(u, v):
    x = (u - .5) * .212
    # path: from the top rear (body side), over the top, down the outer face; centre hangs lower
    L = .30 + .035 * (1 - (2 * u - 1) ** 2) ** .8
    s = v * L
    if s < .07: return (x, ymid - .03 + s * .9, ZT + .03)
    return (x, ymax + .05, ZT - (s - .07))
for hi in (False, True):
    o = sheet('PackFlap' + ('_HI' if hi else ''), flap_guide, pbvh, lambda u, v: .0045 + .002 * math.sin(v * 9 + u * 3), 60 if hi else 18, 80 if hi else 20)
    cen = np.mean(co_np(o.data), axis=0); o.data.update()
    nr = normals_np(o.data); cc = co_np(o.data)
    if ((cc - np.array([0, ymid, (ZB + ZT) / 2])) * nr).sum() < 0:
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    set_chart(o, 62); tag(o, 'leather_pack_flap')
    if not hi: add_lips(o, .003, .008)
    made.append(o)
fbvh = bvh_of([pack_hi, D['PackFlap_HI']])
def on_outer(bvh, q, off, reach=.04):
    """on_surface, on the outermost layer: the nearest surface to a point under the leather is the shirt beneath it, so
    look outwards from the point found and take the last layer within reach."""
    p, nrm = on_surface(bvh, q, 0.0)
    for _ in range(4):
        hit = bvh.ray_cast(Vector(p + nrm * .0008), Vector(nrm), reach)
        if hit[0] is None: break
        hn = np.array(hit[1]); hn = hn if float(np.dot(hn, nrm)) > 0 else -hn
        p = np.array(hit[0]); nrm = hn
    return p + nrm * off, nrm
def strap_on(name, guide_pts, bvh, n, width, thick, off, chart, fabric, outer=False):
    G = catmull(guide_pts, n); Q = []; N = []
    on_surface_ = on_outer if outer else on_surface
    for g in G:
        q, nrm = on_surface_(bvh, g, off); Q.append(q); N.append(nrm)
    Q = np.array(Q); N = np.array(N)
    for _ in range(2):
        Q[1:-1] = (Q[:-2] + 2 * Q[1:-1] + Q[2:]) / 4; N[1:-1] = (N[:-2] + 2 * N[1:-1] + N[2:]) / 4
    N /= np.linalg.norm(N, axis=1)[:, None]
    # the smoothing cuts the corner where the surface curves along the strap (over the top of a shoulder), which put the
    # strap level with the leather or under it there: a point that has sunk below its offset goes back onto the surface
    sunk = 0
    for i in range(n):
        q, nrm = on_surface_(bvh, Q[i], off)
        if float(np.dot(Q[i] - q, nrm)) < 0: Q[i] = q; sunk += 1
    if sunk: log(name, 'guide points lifted back onto the surface', sunk, 'of', n)
    rings = []
    w_prev = None; hw = width / 2
    for i in range(n):
        t = Q[min(i + 1, n - 1)] - Q[max(i - 1, 0)]; w = np.cross(N[i], t)
        # two guide points that land on the same spot of the surface give no direction: keep the last cross axis
        if np.linalg.norm(w) < 1e-7:
            if w_prev is None: continue
            w = w_prev
        w = w / np.linalg.norm(w); w_prev = w
        rings.append([tuple(Q[i] + w * a_ + N[i] * b_) for a_, b_ in ((-hw, 0), (-hw, thick * .8), (-hw * .7, thick), (hw * .7, thick), (hw, thick * .8), (hw, 0))])
    o = loft(name, rings, cap_end=True, cap_start=True); set_chart(o, chart); tag(o, fabric)
    put_lat(o, [-hw, -hw, -hw * .7, hw * .7, hw, hw] * len(rings), hw - .0045)
    return o
ci = 63
for sx in (-1, 1):
    g = [(sx * .055, ymax + .03, ZT - .11), (sx * .055, ymax + .03, ZT - .17), (sx * .055, ymax + .03, ZT - .23), (sx * .055, ymax + .03, ZB + .035)]
    o = strap_on('PackStrap_%s' % ('l' if sx > 0 else 'r'), g, fbvh, 14, .020, .0028, .0006, ci, 'leather_belt'); made.append(o); ci += 1
    h = dup(o, o.name + '_HI'); subdivide(h, 2, simple=True); made.append(h)
    # small iron buckle on each closure strap
    q, nrm = on_surface(fbvh, (sx * .055, ymax + .03, ZT - .245), .004)
    xa = np.array([1.0, 0, 0]); za = np.cross(xa, nrm); za /= np.linalg.norm(za)
    fr = []
    for k in range(20):
        a_ = 2 * np.pi * k / 20; cx_, cz_ = math.cos(a_), math.sin(a_); rr = 1.0 / (abs(cx_ / .0135) ** 4 + abs(cz_ / .011) ** 4) ** .25
        fr.append(q + xa * rr * cx_ + za * rr * cz_)
    b1 = tube('PackBuckle_%d' % ci, fr, .0019, 6, closed=True)
    b2 = tube('PackBuckleT_%d' % ci, [q - za * .011 + nrm * .0012, q + za * .0115 + nrm * .0016], .0014, 5)
    b = join([b1, b2], 'PackBuckle_%s' % ('l' if sx > 0 else 'r')); set_chart(b, 70 + ci); tag(b, 'iron', scale=1.5); made.append(b)
    h = dup(b, b.name + '_HI'); subdivide(h, 1); made.append(h)
# shoulder straps: over the shoulder, down the chest, under the arm, back to the pack
tb = bvh_of([D['Jerkin'], D['Shirt'], pack])
for sx in (-1, 1):
    yp = ymid - .02
    g = [(sx * .070, yp + .01, ZT - .03), (sx * .088, yp - .07, 1.50), (sx * .100, -.01, 1.53), (sx * .112, -.085, 1.47), (sx * .128, -.12, 1.39), (sx * .150, -.10, 1.31),
         (sx * .180, -.03, 1.255), (sx * .165, .06, 1.235), (sx * .115, yp - .02, 1.215), (sx * .09, yp + .01, 1.20)]
    o = strap_on('ShoulderStrap_%s' % ('l' if sx > 0 else 'r'), g, tb, 44, .030, .0034, .0012, 80 + (sx > 0), 'leather_belt', outer=True); made.append(o)
    h = dup(o, o.name + '_HI'); subdivide(h, 2, simple=True); made.append(h)

for o in made:
    smooth_shade(o)
    if 'UVMetric' not in o.data.uv_layers: log('NO UV', o.name)
log('gear', {o.name: tri_count(o) for o in made if not o.name.endswith('_HI')})
log('gear total game tris', sum(tri_count(o) for o in made if not o.name.endswith('_HI')))
save_blend(filepath=str(OUT / 'Dink/Work/dink_garments_b.blend'))
if 'norender' in args(): sys.exit(0)
# preview
cols = {'leather_boot': (.16, .09, .05), 'leather_sole': (.08, .06, .04), 'leather_red': (.42, .07, .05), 'cord': (.5, .4, .3), 'leather_belt': (.14, .08, .04), 'brass': (.7, .5, .2),
        'leather_pack': (.22, .13, .07), 'leather_pack_flap': (.25, .14, .07), 'iron': (.3, .3, .3), 'linen': (.42, .5, .6), 'leather_brown': (.25, .14, .08), 'wool': (.3, .33, .15)}
for o in D:
    if o.type != 'MESH': continue
    o.hide_render = o.name.endswith('_HI') or o.name in ('OldHair', 'OldEyes', 'BrowLash', 'OldWardrobe', 'OldShirtTopo', 'OldTrousersTopo', 'BodyVol')
    if 'fabric' in o:
        mt = bpy.data.materials.new('pv'); mt.use_nodes = True; bs = mt.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value = (*cols[o['fabric']], 1); bs.inputs['Roughness'].default_value = .7
        if o['fabric'] in ('brass', 'iron'): bs.inputs['Metallic'].default_value = 1; bs.inputs['Roughness'].default_value = .4
        o.data.materials.clear(); o.data.materials.append(mt)
setup_render(samples=32, res=(1500, 1000))
bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = .08
shoot(OUT / 'Dink/Review/g_b_front.png', (0.9, -3.4, 1.3), (0, 0, .92), lens=60)
shoot(OUT / 'Dink/Review/g_b_back.png', (-1.2, 3.2, 1.5), (0, 0, .92), lens=60)
shoot(OUT / 'Dink/Review/g_b_boots.png', (0.6, -1.0, .45), (0.05, 0, .17), lens=50)
