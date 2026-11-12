"""Photoreal white domestic duck (v2, 12 Nov 2026 rebuild after review) on the existing 23-bone SK_Duck rig, with the headless gore variant and the severed head prop.
Wedge head with sloping forehead, spatulate bill with nail, nostrils and lamellae edge, layered feather cards (contour, down, wing tracts, tail), webbed leathery feet, neck-stump anatomy.
usage: blender -b -t 4 --python duck.py -- <stage>   stage: look [shots] | final [res] | review tag shots [samples] | export
"""
import bpy, sys, os, math, json, random
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *
from mathutils.kdtree import KDTree

A = args(); STAGE = A[0] if A else 'look'
DST = OUT / 'Duck'; (DST / 'Review').mkdir(parents=True, exist_ok=True); (DST / 'Work').mkdir(exist_ok=True); (DST / 'Textures').mkdir(exist_ok=True)
SRC = ART / 'Creatures/Duck/SK_Duck.blend'
random.seed(21); V = Vector
MATN = ['MI_Duck_Feather', 'MI_Duck_Bill', 'MI_Duck_Feet', 'MI_Duck_Eye']
NCONTOUR = 1800
CUT_P = V((.1035, 0, .335)); CUT_N = V((.12, 0, 1)).normalized()       # decapitation plane across the neck


def open_rig():
    bpy.ops.wm.open_mainfile(filepath=str(SRC))
    for o in list(bpy.data.objects):
        if o.type != 'ARMATURE': bpy.data.objects.remove(o)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    for i in list(bpy.data.images): bpy.data.images.remove(i)
    for c in list(bpy.data.collections):
        if c.name not in ('SK_Duck', 'SK_Duck_Headless', 'SM_Duck_Head'): bpy.data.collections.remove(c)
    arm = bpy.data.objects['Armature']; arm.animation_data_create(); arm.animation_data.action = None; arm.data.pose_position = 'REST'
    return arm


def wingS(s, a, b):
    """Folded-wing surface: a 0 front (wrist/shoulder) .. 1 rear (beyond 1 = free feather tips), b -1 bottom .. 1 top."""
    C = V((.080, s * .090, .232)); ex = V((-1, 0, -.19)).normalized(); ez = V((-.19, 0, 1)).normalized()
    bulge = .010 * math.sqrt(max(0.0, 1 - (2 * min(a, 1.0) - 1) ** 2 * .85 - b * b * .8))
    inw = .10 * max(0.0, a - .5) ** 2 + .014 * max(0, -b) * a + .010 * max(0, b) ** 2
    p = C + ex * (a * .215) + ez * (b * .055 * max(.04, 1 - .93 * min(max(a, 0.0), 1.2) ** 2.2) - .016 * a * a) + V((0, s * (bulge - inw), 0))
    return p


def leaf(base, fdir, side, nrm, L, W, lift=.1, na=5, nb=3, droop=.12, shape=.6, asym=0.0):
    """Modelled feather vane (bake source). Returns verts, faces, per-vertex (u along, v across)."""
    vs = []; fs = []; uv = []
    for i in range(na):
        a = i / (na - 1); w = W * (max(0.0, 1 - (2 * (a * .93 + .07) - 1) ** 2) ** (shape * .62))
        for j in range(nb):
            b = -1 + 2 * j / (nb - 1)
            vs.append(base + fdir * (a * L) + side * (b * w * .5 * (1 + asym * b)) + nrm * (lift * L * a ** 1.3 - droop * w * b * b + (.0012 if j == nb // 2 else 0))); uv.append((a, b))
    for i in range(na - 1):
        for j in range(nb - 1):
            q = i * nb + j; fs.append((q, q + 1, q + nb + 1, q + nb))
    return vs, fs, uv


def orient(o, nrs):
    """Leaf soups: mesh_obj's normal recalculation orients every loose island at random; back-facing vanes baked inverted normals (black shading)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    bmesh.ops.reverse_faces(bm, faces=[f_ for f_ in bm.faces if f_.normal.dot(V(nrs[f_.verts[0].index])) < 0]); bm.to_mesh(o.data); bm.free(); o.data.update()


def build_high(arm):
    B = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones}
    parts = []
    def add(vs, fs): o = mesh_obj('p', vs, fs); parts.append(o); return o
    # trunk: deep keeled breast carried forward and up, tapering to the rump
    T = [(-.236, .220, .008, .008, .018, 2.0), (-.214, .212, .022, .02, .042, 2.0), (-.18, .200, .044, .04, .066, 2.0), (-.13, .187, .068, .064, .088, 2.05), (-.075, .178, .086, .083, .100, 2.1),
         (-.02, .175, .093, .094, .105, 2.15), (.035, .184, .09, .098, .10, 2.15), (.08, .200, .078, .094, .088, 2.1), (.112, .216, .057, .078, .066, 2.0), (.130, .224, .03, .045, .036, 2.0)]
    add(*loft([((x, 0, zc), (0, hw, 0), (0, 0, hu), (0, 0, hd), e) for x, zc, hu, hd, hw, e in T], 36))
    # neck: S-curve, thick at the base, slimmest below the head
    npts = [(V((.070, 0, .232)), .050), (V((.087, 0, .266)), .039), (V((.098, 0, .30)), .0295), (V((.1035, 0, .335)), .0245), (V((.106, 0, .368)), .0235), (V((.110, 0, .392)), .026)]
    st = []
    for i, (p, r) in enumerate(npts):
        t = (npts[min(i + 1, len(npts) - 1)][0] - npts[max(0, i - 1)][0]).normalized(); fw = V((t.z, 0, -t.x))
        st.append((p, V((0, r, 0)), fw * r * 1.1, None, 2.0))
    add(*loft(st, 24))
    # head: wedge skull, crown highest behind the eye, forehead sloping straight into the culmen, full cheeks
    H = [(.081, .404, .008, .008, .008, 2.0), (.089, .406, .024, .022, .020, 2.0), (.101, .410, .0305, .028, .027, 2.1), (.116, .4115, .0325, .0305, .0292, 2.2), (.130, .410, .0295, .030, .0272, 2.2),
         (.142, .4075, .0235, .027, .0245, 2.15), (.153, .4045, .0185, .023, .0212, 2.15), (.160, .4025, .0145, .019, .0190, 2.2)]
    add(*loft([((x, 0, zc), (0, hw, 0), (0, 0, hu), (0, 0, hd), e) for x, zc, hu, hd, hw, e in H], 28))
    for s in (1, -1):
        vs, fs, d = ellipsoid((.126, s * .015, .397), (.028, .0135, .020), 14, 8); add(vs, fs)              # cheeks
        vs, fs, d = ellipsoid((-.035, s * .06, .125), (.055, .04, .05), 14, 8); add(vs, fs)               # feathered thighs
    body = join(parts, 'DuckBody')
    apply_mod(body, 'REMESH', mode='VOXEL', voxel_size=.003, adaptivity=0)
    apply_mod(body, 'SMOOTH', factor=.6, iterations=12)
    me = body.data; me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.update()
    co = co_np(me); n = nrm_np(me); x, y, z = co[:, 0], co[:, 1], co[:, 2]
    N1 = np.array([noise.noise(V(p) * 14) for p in co]); N2 = np.array([noise.noise(V(p) * 37 + V((5, 2, 1))) for p in co])
    co += n * (N1 * .0035 + N2 * .0012)[:, None]                                                          # asymmetric organic lumps
    co -= n * (.004 * gauss(y, .012) * ss(.2, .26, z) * (x < .03) * (x > -.16))[:, None]                  # spine furrow between the wings
    co += n * (.004 * gauss(y, .018) * (z < .13) * (x > 0))[:, None]                                       # keel
    co -= n * (.0025 * gauss(y, .006) * ss(.435, .445, z) * (x > .1) * (x < .15))[:, None]                 # slight median furrow on the crown
    eyes = []
    for s in (1, -1):
        hit, loc, nor, _ = body.ray_cast(V((.1385, s * .2, .4215)), V((0, -s, 0)))
        loc = np.array(loc); nn = np.array(nor); eyes.append((loc, nn)); q = co - loc; d = np.sqrt((q[:, 0] / 1.25) ** 2 + q[:, 1] ** 2 + q[:, 2] ** 2)
        co -= nn[None, :] * (gauss(d, .0062) * .0055)[:, None]; co += nn[None, :] * (gauss(d - .0082, .0024) * .0016)[:, None]   # socket and lid ring
        co -= nn[None, :] * (gauss(np.hypot(q[:, 0] - .013, q[:, 2] + .004), .006) * .0012 * (np.abs(q[:, 1]) < .02))[:, None]   # lore groove toward the bill
    set_co(me, co); co = co_np(me); n = nrm_np(me); x, y, z = co[:, 0], co[:, 1], co[:, 2]
    N1 = np.array([noise.noise(V(p) * 9 + V((3, 1, 7))) for p in co])
    stain = np.clip(.8 * (n[:, 2] < -.2) * (1 - ss(.1, .2, z)) + .55 * (1 - ss(-.2, -.12, x)) + .5 * ss(.1, .5, N1) * (z < .26), 0, 1)
    dirt = np.clip(.95 * (1 - ss(.08, .135, z)) + .45 * (1 - ss(-.21, -.15, x)) + .35 * ss(.2, .6, N1) * (z < .2) * (n[:, 2] < .3), 0, 1)
    headm = ss(.375, .40, z)
    set_color_attr(me, 'msk', np.stack([stain, dirt, np.zeros(len(co)), headm], 1))
    set_color_attr(me, 'loc', np.zeros((len(co), 4)))
    hard = []
    def hp(vs, fs, msk, part, sub=0, par=0.0):
        o = mesh_obj('hard', vs, fs)
        if sub: apply_mod(o, 'SUBSURF', levels=sub, render_levels=sub)
        k = len(o.data.vertices); set_color_attr(o.data, 'msk', np.tile(np.array(msk, float), (k, 1))); set_color_attr(o.data, 'loc', np.zeros((k, 4)))
        a = o.data.attributes.new('part', 'FLOAT', 'POINT'); a.data.foreach_set('value', [float(part)] * k)
        a = o.data.attributes.new('par', 'FLOAT', 'POINT'); a.data.foreach_set('value', [float(par)] * k)
        hard.append(o); return o
    # --- bill: broad spatulate upper mandible continuing the forehead slope; culmen, nostrils, nail, lamellae edge (1 head, 2 jaw)
    U = [(.148, .4045, .0160, .0060, .0178, 2.2), (.160, .4040, .0125, .0056, .0183, 2.25), (.174, .4025, .0092, .0052, .0195, 2.4), (.190, .4005, .0068, .0048, .0212, 2.6), (.206, .3988, .0052, .0044, .0228, 2.8),
         (.221, .3974, .0043, .0040, .0232, 2.9), (.233, .3964, .0037, .0036, .0205, 2.6), (.241, .3955, .0031, .0032, .0140, 2.3), (.2462, .3948, .0020, .0024, .0055, 2.0)]
    vs, fs = loft([((x_, 0, zc), (0, hw, 0), (0, 0, hu), (0, 0, hd), e) for x_, zc, hu, hd, hw, e in U], 24)
    o = hp(vs, fs, (0, 0, .33, 0), 1, sub=2)
    c = co_np(o.data); cx, cy, cz = c[:, 0], c[:, 1], c[:, 2]; hwx = np.interp(cx, [u_[0] for u_ in U], [u_[4] for u_ in U]); top = cz > np.interp(cx, [u_[0] for u_ in U], [u_[1] for u_ in U])
    for s in (1, -1):
        d = np.hypot((cx - .1735) / 2.2, (cy - s * .0072)); c[:, 2] -= .0030 * gauss(d, .0022) * top; c[:, 2] += .0007 * gauss(d - .0042, .0014) * top      # nostrils with a raised rim
    c[:, 2] += .0011 * gauss(cy, .0035) * top * ss(.25, .15, (cx - .148) / .1) * 0 + .0009 * gauss(cy, .004) * top * (cx < .2)                              # culmen ridge
    nd = np.hypot((cx - .2395) / 1.25, cy); c[:, 2] += (.0016 * ss(.0072, .0048, nd) + .0006 * gauss(nd - .0068, .001) * -1) * top                          # nail: raised plate with a groove round it
    c[:, 2] -= .0018 * ss(.236, .2465, cx) * (np.abs(cy) < .006)                                                                                            # nail hooks down
    c[:, 2] += .0010 * gauss(np.abs(cy) - hwx * .86, .0022) * top * (cx > .175) * (cx < .236)                                                               # raised lateral rim
    c[:, 2] -= .0007 * gauss(np.abs(cy) - hwx * .62, .0030) * top * (cx > .175) * (cx < .232)                                                               # shallow groove inside the rim
    c[:, 2] += .0010 * np.array([noise.noise(V(p) * 60) for p in c]) * .5
    set_co(o.data, c)
    edge = ss(.72, .92, np.abs(cy) / np.maximum(hwx, 1e-4)) * (1 - top) * (cx > .158) * (cx < .24)                                                          # tomial edge: lamellae
    m = np.zeros((len(c), 4)); m[:, 0] = edge; m[:, 1] = ss(.006, .0045, nd) * top; m[:, 2] = .33; set_color_attr(o.data, 'msk', m)
    Lw = [(.148, .3995, .0040, .0115, .0165, 2.2), (.166, .3978, .0030, .0085, .0172, 2.3), (.188, .3958, .0026, .0062, .0188, 2.5), (.208, .3942, .0022, .0048, .0200, 2.6), (.226, .3930, .0018, .0036, .0188, 2.5), (.2385, .3922, .0014, .0024, .0115, 2.2)]
    vs, fs = loft([((x_, 0, zc), (0, hw, 0), (0, 0, hu), (0, 0, hd), e) for x_, zc, hu, hd, hw, e in Lw], 18)
    o = hp(vs, fs, (0, 0, .33, 0), 2, sub=1); c = co_np(o.data); hwl = np.interp(c[:, 0], [u_[0] for u_ in Lw], [u_[4] for u_ in Lw])
    m = np.zeros((len(c), 4)); m[:, 0] = ss(.72, .92, np.abs(c[:, 1]) / np.maximum(hwl, 1e-4)) * (c[:, 2] > .393) * (c[:, 0] > .158); m[:, 2] = .33; set_color_attr(o.data, 'msk', m)
    # --- legs and webbed feet (3..8: calf/foot/toes per side): scaled tarsus, knuckled toes, sagging webs with thickness
    for s, sd, base in ((1, 'l', 3), (-1, 'r', 6)):
        knee, ank = B['calf_' + sd]; tb = B['toes_' + sd][0]
        vs, fs, ts, an = tube([knee + V((0, 0, .014)), knee.lerp(ank, .35), knee.lerp(ank, .7), ank + V((0, 0, .004))], [.0140, .0108, .0088, .0080], 12, squash=(1, .85)); hp(vs, fs, (0, .2, .66, 0), base)
        vs, fs, d = ellipsoid(ank + V((-.002, 0, 0)), (.0105, .0085, .0098), 12, 8); hp(vs, fs, (0, .3, .66, 0), base + 1)                                   # hock joint
        vs, fs, ts, an = tube([ank, ank.lerp(tb, .33), ank.lerp(tb, .66), tb + V((0, 0, .004))], [.0076, .0064, .0062, .0078], 12, squash=(1.2, .8)); hp(vs, fs, (0, .4, .66, 0), base + 1)
        tips = []
        for ti, (ang, L) in enumerate(((-29 * s, .050), (0, .063), (27 * s, .056))):
            dr = V((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0)); tip = V((tb.x + dr.x * L, tb.y + dr.y * L, .0035)); tips.append(tip)
            qs = (0, .14, .28, .42, .56, .70, .84, .95); pts = [tb.lerp(tip, q) + V((0, 0, .0030 * math.sin(q * math.pi) + (.009 * (1 - q) ** 2))) for q in qs]
            rad = [.0062, .0050, .0056, .0044, .0050, .0040, .0044, .0033]                                                                                  # knuckles
            vs, fs, ts, an = tube(pts, rad, 10, squash=(1, .78)); hp(vs, fs, (0, .5, .66, 0), base + 2)
            vs, fs, ts, an = tube([tip - dr * .004 + V((0, 0, .0012)), tip + dr * .003 + V((0, 0, .0008)), tip + dr * .0075 + V((0, 0, -.0012)), tip + dr * .0105 + V((0, 0, -.003))], [.0030, .0026, .0017, .0004], 6, squash=(.8, 1)); hp(vs, fs, (.9, .3, .66, 0), base + 2)   # nail
        for wi, (t0, t1) in enumerate(((tips[0], tips[1]), (tips[1], tips[2]))):                          # webs
            vs = []; fs = []; N = 8
            for up in (1, -1):
                for i in range(N + 1):
                    for j in range(N + 1):
                        a = i / N; b = j / N; e = t0.lerp(t1, b); e = e - (e - tb) * (.20 * math.sin(math.pi * b))      # concave trailing edge
                        p = V((tb.x, tb.y, .006)).lerp(e, a); mid = math.sin(b * math.pi)
                        zz = .0030 + up * (.0010 * (1 - .55 * a) * (1 - .5 * mid) + .0003) - .0016 * mid * math.sin(a * math.pi * .9) + .0005 * math.sin(a * 23 + b * 17 + wi)
                        vs.append(V((p.x, p.y, max(.0004, zz))))
            sz = (N + 1) ** 2
            for k in (0, 1):
                for i in range(N):
                    for j in range(N):
                        q = k * sz + i * (N + 1) + j; f = (q, q + N + 1, q + N + 2, q + 1); fs.append(f if k == 0 else tuple(reversed(f)))
            for j in range(N):
                q = N * (N + 1) + j; fs.append((q, q + sz, q + 1 + sz, q + 1))
            hp(vs, fs, (.5, .5, .66, 0), base + 2)
        hb = tb + V((-.014, -s * .006, .004)); vs, fs, ts, an = tube([tb + V((-.002, 0, .004)), hb, hb + V((-.006, 0, -.003))], [.004, .003, .0006], 6); hp(vs, fs, (0, .5, .66, 0), base + 1)    # hind toe
    for s, (loc, nn) in zip((1, -1), eyes):
        c = loc - nn * .0046; vs, fs, d = ellipsoid(c, (.0058, .0058, .0058), 16, 10); hp(vs, fs, (0, 0, 1, 0), 9)
    # --- wings: thin low shell (parts 10/11) under the feather tracts; modelled feathers are bake source, the same placements become cards
    feath = []
    def fadd(vs, fs, uv, tint, nr):
        o = mesh_obj('f', vs, fs); k = len(vs); orient(o, [nr] * k)
        m = np.zeros((k, 4)); m[:, 0] = tint; set_color_attr(o.data, 'msk', m)
        l = np.zeros((k, 4)); l[:, 0] = [q[0] for q in uv]; l[:, 1] = [q[1] for q in uv]; l[:, 3] = 1; set_color_attr(o.data, 'loc', l)
        a = o.data.attributes.new('part', 'FLOAT', 'POINT'); a.data.foreach_set('value', [99.0] * k); o.data.attributes.new('par', 'FLOAT', 'POINT'); feath.append(o)
    wing_feathers = {}
    for s, part in ((1, 10), (-1, 11)):
        NA, NB = 14, 7; vs = []; fs = []
        for inner in (0, 1):
            for i in range(NA + 1):
                for j in range(NB + 1):
                    a = i / NA; b = -1 + 2 * j / NB; rim = max(0.0, 1 - (2 * a - 1) ** 2 * .85 - b * b * .8)
                    p = wingS(s, a * 1.0, b * (1 - .35 * (2 * a - 1) ** 4)); vs.append(p + V((0, -s * (.0015 + .018 * math.sqrt(rim)) * inner, 0)))
        sz = (NA + 1) * (NB + 1)
        for k in (0, 1):
            for i in range(NA):
                for j in range(NB):
                    q = k * sz + i * (NB + 1) + j; f = (q, q + NB + 1, q + NB + 2, q + 1); fs.append(f if k == 0 else tuple(reversed(f)))
        for i in range(NA):
            for j in (0, NB):
                q = i * (NB + 1) + j; fs.append((q, q + sz, q + NB + 1 + sz, q + NB + 1) if j == 0 else (q, q + NB + 1, q + NB + 1 + sz, q + sz))
        for j in range(NB):
            for i in (0, NA):
                q = i * (NB + 1) + j; fs.append((q, q + 1, q + 1 + sz, q + sz) if i == 0 else (q, q + sz, q + 1 + sz, q + 1))
        hp(vs, fs, (0, 0, 0, .0), part)
        # tracts: (a0, a1, count, b, length, width, angle_down, lift offset, card cell)  marginal/lesser, median, greater coverts, scapulars/tertials, secondaries, primaries
        rows = [(-.04, .40, 16, .86, .026, .022, -.08, .0004, 6), (-.03, .48, 16, .58, .032, .024, -.04, .0008, 6), (-.02, .60, 17, .30, .040, .026, .0, .0012, 6), (.02, .72, 16, .02, .052, .028, .04, .0018, 6),
                (.42, .80, 6, .46, .090, .030, .0, .0030, 2), (.18, .74, 12, -.40, .098, .024, .09, .0010, 1), (.66, .90, 8, -.48, .135, .020, .12, .0004, 0)]
        ex = V((-1, 0, -.19)).normalized(); ez = V((-.19, 0, 1)).normalized(); allf = []
        for ri, (a0, a1, cnt, b, L, W, ang, off, cell) in enumerate(rows):
            for k in range(cnt):
                a = a0 + (a1 - a0) * (k + random.uniform(-.2, .2)) / max(1, cnt - 1); bb = b + random.uniform(-.06, .06) - (.22 * k / cnt if ri == 6 else 0)
                L_ = L * random.uniform(.9, 1.1) * (1 + .25 * k / cnt if ri == 6 else 1)
                base = wingS(s, a, bb); fd = (ex * math.cos(ang + random.uniform(-.06, .06)) - ez * math.sin(ang + .05 * k * (ri >= 5))).normalized()
                tip = wingS(s, a + L_ / .215, bb - math.sin(ang) * L_ / .05); fd = ((tip - base).normalized() * .7 + fd * .3).normalized()
                side = ez - fd * ez.dot(fd); side.normalize(); nr = V((0, s, .25)).normalized(); nr = (nr - fd * nr.dot(fd)).normalized(); side = nr.cross(fd).normalized() * s
                vs, fs, uv = leaf(base + nr * (off + .0005 * k / cnt), fd, side, nr, L_, W, lift=.02, na=8, nb=5, droop=.06, shape=.5 if ri >= 4 else .75)
                fadd(vs, fs, uv, random.random(), nr)
                allf.append((base + nr * (off + .0006), fd, side, nr, L_, W, cell, ri))
        for k in range(40):                                                                               # breast and flank feathers lapping over the wing's leading and lower edges
            if k < 22: a = random.uniform(-.10, .10); bb = random.uniform(-1.0, 1.0); L_ = random.uniform(.034, .046)
            else: a = random.uniform(.0, .72); bb = random.uniform(-1.12, -.82); L_ = random.uniform(.036, .05)
            base = wingS(s, a, bb); fd = (ex + ez * (random.uniform(-.2, .2) + (.5 if k >= 22 else 0))).normalized(); nr = V((0, s, .15)).normalized(); nr = (nr - fd * nr.dot(fd)).normalized(); side = nr.cross(fd).normalized() * s
            vs, fs, uv = leaf(base + nr * .003, fd, side, nr, L_, L_ * .7, lift=.05, na=6, nb=5, droop=.07, shape=.8); fadd(vs, fs, uv, random.random(), nr)
            allf.append((base + nr * .0035, fd, side, nr, L_, L_ * .62, 4 + k % 2, 3))
        wing_feathers[s] = allf
    EYES[:] = eyes
    return body, hard, feath, eyes, wing_feathers


EYES = []


def body_feathers(body):
    """Modelled contour feathers shingled over the body and neck (high-poly bake source only)."""
    me = body.data; co = co_np(me); n = nrm_np(me); order = list(range(len(co))); random.shuffle(order)
    kd = KDTree(len(co)); [kd.insert(co[i], i) for i in range(len(co))]; kd.balance()
    taken = np.zeros(len(co), bool); vs_all = []; fs_all = []; uv_all = []; tint = []; nr_all = []; cnt = 0
    for i in order:
        if taken[i]: continue
        p = V(co[i]); nr = V(n[i])
        if p.x > .147 and p.z > .38: continue                      # bill base: shader plumage
        neck = ss(.25, .29, np.array([p.z]))[0] * (p.x > .03); hd = ss(.37, .39, np.array([p.z]))[0]
        if hd > .5 and min((p - V(e_[0])).length for e_ in EYES) < .0095: continue
        L = (.030 - .008 * (p.x > .06) + .008 * (p.z < .16)) * (1 - neck) + .012 * neck; L = L * (1 - hd) + .0062 * hd
        L *= random.uniform(.8, 1.25)
        for (_, j, _) in kd.find_range(p, L * .33): taken[j] = True
        flow = (V((-1, 0, -.12)) * (1 - neck) + V((-.25, 0, -1)) * neck); flow = flow + V((0, .5 * (p.y / .1) * (p.x < -.1), 0)) + V((random.uniform(-.12, .12), random.uniform(-.12, .12), 0))
        if hd > .5: flow = V((-1, 0, -.55)) + V((random.uniform(-.35, .35), random.uniform(-.35, .35), random.uniform(-.3, .3)))
        f = flow - nr * flow.dot(nr)
        if f.length < 1e-4: continue
        f.normalize(); side = nr.cross(f).normalized(); base = p - f * (L * .3) + nr * .0006
        vs, fs, uv = leaf(base, f, side, nr, L, L * random.uniform(.55, .72) * (1.25 if hd > .5 else 1), lift=random.uniform(.03, .07) if hd < .5 else random.uniform(.0, .02), na=6, nb=5, droop=.07 if hd < .5 else .02, shape=.8)
        o = len(vs_all); vs_all += vs; fs_all += [tuple(o + q for q in fc) for fc in fs]; uv_all += uv; tint += [random.random()] * len(vs); nr_all += [tuple(nr)] * len(vs); cnt += 1
    o = mesh_obj('bodyfeathers', vs_all, fs_all); orient(o, nr_all); k = len(vs_all); m = np.zeros((k, 4)); m[:, 0] = np.array(tint)
    bm_ = get_color_attr(me, 'msk')
    for q, v in enumerate(vs_all):
        _, j, _ = kd.find(v); m[q, 1] = bm_[j, 1]; m[q, 2] = 0; m[q, 3] = 0; m[q, 0] = .35 * m[q, 0] + .65 * bm_[j, 0]
    set_color_attr(o.data, 'msk', m); l = np.zeros((k, 4)); l[:, 0] = [q[0] for q in uv_all]; l[:, 1] = [q[1] for q in uv_all]; l[:, 3] = 1; set_color_attr(o.data, 'loc', l)
    a = o.data.attributes.new('part', 'FLOAT', 'POINT'); a.data.foreach_set('value', [99.0] * k); o.data.attributes.new('par', 'FLOAT', 'POINT')
    log('body feathers', cnt); return o


def duckmat(mat):
    t = NT(mat); tc = t.node('ShaderNodeTexCoord'); P = tc.outputs['Object']; geo = t.node('ShaderNodeNewGeometry')
    ma = t.attr('msk'); mR, mG, mB = t.sep(ma.outputs['Color'])[:3]; mA = ma.outputs['Alpha']
    la = t.attr('loc'); fu, fv, _x = t.sep(la.outputs['Color'])[:3]; isF = la.outputs['Alpha']
    isBill = t.math('COMPARE', mB, .33, .12); isFoot = t.math('COMPARE', mB, .66, .12); isEye = t.math('GREATER_THAN', mB, .9); isHead = t.smooth(mA, .2, .8)
    isPl = t.math('SUBTRACT', 1.0, t.math('MAXIMUM', t.math('MAXIMUM', isBill, isFoot), isEye), clamp=True)
    big, _ = t.noise(P, 9, 3, .55); mid, _ = t.noise(P, 40, 4, .6); fine, _ = t.noise(P, 260, 3, .6); pz = t.sepxyz(P)[2]; px = t.sepxyz(P)[0]
    # plumage: white with warm and cool drift, cream preen-oil staining below, shadowed grey feather bases, soil on belly and vent
    c = t.mix(big, (.62, .615, .575), (.74, .735, .70))
    c = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', mR, isPl), .55), c, (.60, .50, .30))
    c = t.mix(t.math('MULTIPLY', t.smooth(mid, .5, .72), .16), c, (.60, .58, .50))
    afv = t.math('ABSOLUTE', fv)
    basef = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(fu, .0, .55)), isF)
    c = t.mix(t.math('MULTIPLY', basef, .42), c, (.40, .42, .45))                                          # feather bases sit in the shadow of the row in front
    barb = t.math('SINE', t.math('MULTIPLY', t.math('SUBTRACT', t.math('MULTIPLY', fu, 1.4), t.math('MULTIPLY', afv, .5)), 150.0))
    c = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(barb, -.2, .9), isF), .07), c, (.52, .52, .50))
    rach = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(afv, .0, .09)), isF)
    c = t.mix(t.math('MULTIPLY', rach, .25), c, (.66, .62, .50))
    ao = t.node('ShaderNodeAmbientOcclusion'); ao.samples = 8; ao.inputs['Distance'].default_value = .012; cav = t.math('SUBTRACT', 1.0, ao.outputs['AO'])
    c = t.mix(t.math('MULTIPLY', cav, .34), c, (.44, .43, .40))
    dn, _ = t.noise(P, 22, 4, .7); dn2, _ = t.noise(P, 75, 3, .7)
    dirt = t.math('MULTIPLY', t.smooth(t.math('ADD', t.math('MULTIPLY', mG, 1.15), t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', dn, .5), 1.2), t.math('MULTIPLY', t.math('SUBTRACT', dn2, .5), .5))), .45, .9), t.math('SUBTRACT', 1.0, isEye))
    hf1, _ = t.noise(t.mapping(P, (220, 900, 900), (0, .35, 0)), 1.0, 3, .6); hf2, _ = t.noise(t.mapping(P, (300, 1300, 1300), (0, .5, .3)), 1.0, 2, .6)
    c = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(hf1, .35, .6), isHead), .16), c, (.55, .55, .50))
    # bill: waxy orange-yellow, paler horn nail, dark nostrils, grime in the grooves, darker lamellae edge
    bn, _ = t.noise(P, 70, 4, .65); bb, _ = t.noise(P, 14, 3, .6)
    bc = t.mix(bb, (.70, .30, .03), (.86, .47, .06))
    bc = t.mix(t.smooth(px, .15, .19), t.mix(bn, (.60, .22, .03), (.74, .34, .04)), bc)                    # deeper orange toward the base
    bc = t.mix(mG, bc, t.mix(bn, (.78, .58, .34), (.62, .44, .26)))                                         # nail
    bc = t.mix(t.math('MULTIPLY', t.smooth(bn, .52, .74), .42), bc, (.42, .19, .035))
    lam = t.math('SINE', t.math('MULTIPLY', px, 3300.0)); lamf = t.math('MULTIPLY', mR, isBill)
    bc = t.mix(t.math('MULTIPLY', lamf, t.math('ADD', .35, t.math('MULTIPLY', t.smooth(lam, -.3, .6), .45))), bc, (.22, .09, .02))
    bc = t.mix(t.math('MULTIPLY', cav, .9), bc, (.12, .06, .025))
    bsc, _ = t.noise(t.mapping(P, (500, 40, 500)), 1.0, 2, .5)
    bc = t.mix(t.math('MULTIPLY', t.smooth(bsc, .62, .7), .25), bc, (.90, .66, .30))                        # fine scratches
    c = t.mix(isBill, c, bc)
    # legs and feet: leathery reticulate scales, darker in the creases, horn nails
    sd, sc_ = t.voronoi(t.mapping(P, (1, 1, 1.5)), 330, 'F1'); scale_edge = t.smooth(sd, .28, .52)
    fc = t.mix(bb, (.66, .22, .025), (.84, .40, .05)); fc = t.mix(t.math('MULTIPLY', scale_edge, .55), fc, (.36, .11, .015))
    fc = t.mix(t.math('MULTIPLY', t.smooth(bn, .5, .75), .3), fc, (.50, .20, .04))
    fc = t.mix(t.math('MULTIPLY', mR, t.math('GREATER_THAN', mR, .8)), fc, (.26, .20, .14))               # horn nails
    c = t.mix(isFoot, c, fc)
    c = t.mix(isEye, c, (.010, .007, .006))
    dirtc = t.mix(dn, (.11, .085, .055), (.27, .22, .15))
    c = t.mix(t.math('MULTIPLY', dirt, t.mixf(isFoot, .78, .9)), c, dirtc)
    # roughness
    r = t.math('ADD', .55, t.math('MULTIPLY', mid, .2)); r = t.math('SUBTRACT', r, t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(barb, 0, 1), isF), .08))
    r = t.mixf(isBill, r, t.math('ADD', t.math('ADD', .22, t.math('MULTIPLY', bn, .22)), t.math('MULTIPLY', lamf, .25)))
    r = t.mixf(isFoot, r, t.math('ADD', .30, t.math('MULTIPLY', scale_edge, .3))); r = t.mixf(isEye, r, .03); r = t.mixf(dirt, r, .9)
    # height
    h = t.math('MULTIPLY', fine, .00025); h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', t.math('ADD', hf1, hf2), isHead), .00035))
    h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', barb, isF), .00012)); h = t.math('ADD', h, t.math('MULTIPLY', rach, .0003))
    hb = t.math('ADD', t.math('MULTIPLY', bn, .0004), t.math('ADD', t.math('MULTIPLY', fine, .0002), t.math('MULTIPLY', t.math('MULTIPLY', lam, lamf), .00035)))
    h = t.mixf(isBill, h, hb)
    h = t.mixf(isFoot, h, t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, scale_edge), .0008), t.math('MULTIPLY', bn, .0004)))
    h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', dirt, dn2), .0009))
    n = t.bump(h, 1.0, 1.0)
    sss = t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.math('MAXIMUM', isEye, dirt), clamp=True), .25), t.math('MULTIPLY', isFoot, .25))
    t.finish(c, r, n, sss=sss, sss_radius=(.006, .004, .003))
    t.bake['pos'] = P
    BAKE[mat.name] = t.bake; return mat


def gore_textures():
    """Procedural neck cross-section: skin and fat rim, muscle, trachea, oesophagus, vertebra, wet blood. 512 px."""
    from PIL import Image
    N = 512; yy, xx = np.mgrid[0:N, 0:N]; u = (xx + .5) / N * 2 - 1; v = (yy + .5) / N * 2 - 1; r = np.hypot(u, v); th = np.arctan2(v, u)
    rng = np.random.default_rng(5)
    def vn(sc, seed):
        g = np.random.default_rng(seed).random((sc + 1, sc + 1)); fx = (u * .5 + .5) * (sc - 1e-6); fy = (v * .5 + .5) * (sc - 1e-6); ix = fx.astype(int); iy = fy.astype(int); tx = fx - ix; ty = fy - iy
        tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty); return g[iy, ix] * (1 - tx) * (1 - ty) + g[iy, ix + 1] * tx * (1 - ty) + g[iy + 1, ix] * (1 - tx) * ty + g[iy + 1, ix + 1] * tx * ty
    n1 = vn(6, 1); n2 = vn(24, 2); n3 = vn(90, 3)
    rr = r * (1 + .08 * (n1 - .5))
    col = np.zeros((N, N, 3)); col[:] = (.15, .010, .010)                                                   # muscle
    fib = n2; col *= (.75 + .35 * fib * n3)[..., None]
    col = np.where((rr > .80)[..., None], np.array((.42, .26, .14)) * (.7 + .5 * n2[..., None]), col)      # fat
    col = np.where((rr > .92)[..., None], np.array((.48, .30, .25)), col)                                  # skin edge
    h = .25 * fib * n3
    def disc(cx, cy, rad): return np.hypot(u - cx, v - cy) / rad
    d = disc(.0, -.28, .26); col = np.where((d < 1)[..., None], np.array((.74, .68, .58)) * (.85 + .3 * n3[..., None]), col); h = np.where(d < 1, .8 - .2 * d, h)   # vertebra
    d2 = disc(.0, -.28, .08); col = np.where((d2 < 1)[..., None], np.array((.42, .08, .05)), col); h = np.where(d2 < 1, .3, h)                                        # cord
    d = disc(-.06, .26, .2); ring = (d < 1) & (d > .62); col = np.where(ring[..., None], np.array((.72, .66, .60)), col); col = np.where((d <= .62)[..., None], np.array((.06, .008, .008)), col); h = np.where(ring, .9, np.where(d <= .62, -.6, h))   # trachea
    d = disc(.3, .05, .15); col = np.where((d < 1)[..., None], np.array((.46, .10, .09)) * (.8 + .4 * n2[..., None]), col); col = np.where((d < .3)[..., None], np.array((.05, .005, .005)), col); h = np.where(d < 1, .5 - .6 * (d < .3), h)        # oesophagus
    for cx, cy in ((-.42, -.05), (.44, -.3)):
        d = disc(cx, cy, .07); col = np.where((d < 1)[..., None], np.array((.16, .0, .0)), col); h = np.where(d < 1, .1, h)                                          # vessels
    blood = np.clip((n1 - .30) * 4 + (n3 - .5) * .8, 0, 1) * (rr < 1.05); blood = np.maximum(blood, .85 * np.clip((rr - .62) / .25, 0, 1)); col = col * (1 - blood[..., None] * .85) + np.array((.085, .002, .002)) * blood[..., None] * .85
    rough = np.clip(.34 - .22 * blood + .12 * n3, .06, 1); h = h * (1 - .6 * blood)
    def srgb(x_): return np.where(x_ <= .0031308, x_ * 12.92, 1.055 * np.clip(x_, 0, 1) ** (1 / 2.4) - .055)
    P_ = DST / 'Textures'
    Image.fromarray((np.clip(srgb(col), 0, 1) * 255 + .5).astype(np.uint8)[::-1]).save(P_ / 'T_Duck_Gore_BC.png')
    gy, gx = np.gradient(h); s_ = 3.0; nx = -gx * s_ * 40 / 40; ny = -gy * s_; nz_ = np.ones_like(nx); ln = np.sqrt(nx * nx + ny * ny + 1)
    Image.fromarray((np.clip(np.stack([nx / ln * .5 + .5, ny / ln * .5 + .5, nz_ / ln * .5 + .5], -1), 0, 1) * 255 + .5).astype(np.uint8)[::-1]).save(P_ / 'T_Duck_Gore_N.png')
    Image.fromarray((np.clip(np.stack([np.clip(.7 + .3 * h, 0, 1), rough, np.zeros_like(rough)], -1), 0, 1) * 255 + .5).astype(np.uint8)[::-1]).save(P_ / 'T_Duck_Gore_ORM.png')
    return {'BC': P_ / 'T_Duck_Gore_BC.png', 'N': P_ / 'T_Duck_Gore_N.png', 'ORM': P_ / 'T_Duck_Gore_ORM.png'}


def bloody_variant(tex, pos):
    """Blood-soaked plumage around the cut, composited in texture space from the baked position map."""
    from PIL import Image
    bc = np.asarray(Image.open(tex['BC']).convert('RGB'), dtype=np.float64)[::-1] / 255.0; orm = np.asarray(Image.open(tex['ORM']).convert('RGB'), dtype=np.float64)[::-1] / 255.0
    p = pos[..., :3]; d = (p - np.array(CUT_P)) @ np.array(CUT_N)                                         # signed distance to the cut plane
    near = np.hypot(p[..., 0] - CUT_P.x, p[..., 1]) < .13
    n1 = np.sin(p[..., 0] * 310 + np.sin(p[..., 1] * 170) * 2) * np.sin(p[..., 1] * 290 + 1.3) * .5 + .5; n2 = np.sin(np.arctan2(p[..., 1], p[..., 0] - .09) * 9 + np.sin(p[..., 2] * 60) * 1.5) * .5 + .5
    below = np.clip(1 - (-d) / (.045 + .11 * n2 ** 2), 0, 1) * (d < 0) * (p[..., 2] > .2)                # soaked collar and runs down the breast
    above = np.clip(1 - d / (.018 + .02 * n1), 0, 1) * (d >= 0)
    m = np.clip(np.maximum(below, above) * (1.0 + .6 * n1) * 1.5, 0, 1) * near; m = m ** .7
    lin = np.where(bc <= .04045, bc / 12.92, ((bc + .055) / 1.055) ** 2.4)
    red = np.array((.075, .003, .003)) * (.5 + .7 * n1[..., None]); lin = lin * (1 - m[..., None]) + (lin * np.array((.35, .01, .01)) * .35 + red * .8) * m[..., None]
    out = np.where(lin <= .0031308, lin * 12.92, 1.055 * np.clip(lin, 0, 1) ** (1 / 2.4) - .055)
    pb = DST / 'Textures/T_Duck_Atlas_Bloody_BC.png'; Image.fromarray((np.clip(out, 0, 1) * 255 + .5).astype(np.uint8)[::-1]).save(pb)
    orm[..., 1] = orm[..., 1] * (1 - m) + (.16 + .2 * n1) * m
    po = DST / 'Textures/T_Duck_Atlas_Bloody_ORM.png'; Image.fromarray((np.clip(orm, 0, 1) * 255 + .5).astype(np.uint8)[::-1]).save(po)
    return {'BC': pb, 'N': tex['N'], 'ORM': po, 'SSS': tex.get('SSS')}


def card(base, fd, side, nr, L, W, cell, segs=3, lift=.06, droop=.0):
    """Alpha feather card; cell index in the 4x2 atlas. Returns verts, faces, per-face-corner uvs."""
    c0 = cell % 4; r0 = cell // 4; u0 = c0 * .25; v1 = 1 - r0 * .5; v0 = v1 - .5; vs = []; fs = []; uv = []
    for i in range(segs + 1):
        a = i / segs; p = base + fd * (a * L) + nr * (lift * L * a * a)
        vs += [p - side * W * .5 - nr * droop * W, p + side * W * .5 - nr * droop * W]
    for i in range(segs + 1): uv += [(u0 + .004, v0 + .004 + .492 * i / segs), (u0 + .246, v0 + .004 + .492 * i / segs)]      # per vertex
    for i in range(segs):
        q = i * 2; fs.append((q, q + 1, q + 3, q + 2))
    return vs, fs, uv


def build_cards(low_body, wing_feathers, arm):
    """Low-poly alpha feather cards: contour and down cards over the body and neck, wing tracts (coverts, scapulars, secondaries,
    primaries crossing over the rump), tail coverts and rectrices. Skinned from the nearest body vertex or to wing/tail bones.
    Each card carries the skin normal ('bn') so the plumage shades as one soft surface."""
    B = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones}
    vs_all = []; fs_all = []; uv_all = []; wts = []; nrs = []
    def put(vs, fs, uv, w, nr, blend=.3):
        o = len(vs_all); vs_all.extend(vs); fs_all.extend([tuple(o + q for q in f) for f in fs]); uv_all.extend(uv); wts.extend([w] * len(vs)); nrs.extend([(tuple(nr), blend)] * len(vs))
    for s in (1, -1):
        sd = 'l' if s > 0 else 'r'; x0 = B['wing_' + sd][0].x; x1 = B['wingtip_' + sd][0].x
        for k, (base, fd, side, nr, L, W, cell, ri) in enumerate(wing_feathers[s]):
            vs, fs, uv = card(base + nr * (.0012 + .0004 * ri), fd, side, nr, L * 1.06, W * (1.45 if ri < 4 else 1.25), cell, segs=2 if ri >= 4 else 1, lift=.03 if ri < 4 else .0)
            w = float(np.clip((x0 - (base.x - .4 * L)) / (x0 - x1) - .35, 0, 1)) if ri < 6 else 1.0
            put(vs, fs, uv, {'wingtip_' + sd: w, 'wing_' + sd: 1 - w} if 0 < w < 1 else ({'wingtip_' + sd: 1.0} if w >= 1 else {'wing_' + sd: 1.0}), nr, .45)
    for k in range(12):                                                                                   # rectrices: fan, slightly raised
        a = (k - 5.5) / 5.5; ang = a * .50; fd = V((-math.cos(ang), math.sin(ang), .20 - .07 * abs(a))).normalized(); side = V((0, 0, 1)).cross(fd).normalized(); nr = fd.cross(side) * -1
        base = V((-.178, a * .032, .206 - .010 * abs(a) + .0012 * (k % 2)))
        vs, fs, uv = card(base, fd, side, nr, .088 - .016 * abs(a), .040, 3, segs=2, lift=.05); put(vs, fs, uv, {'tail_02': 1.0}, V((0, 0, 1)), .4)
    for k in range(9):                                                                                    # upper tail coverts
        a = (k - 4) / 4; ang = a * .45; fd = V((-math.cos(ang), math.sin(ang), .10)).normalized(); side = V((0, 0, 1)).cross(fd).normalized(); nr = fd.cross(side) * -1
        vs, fs, uv = card(V((-.150, a * .035, .222 - .012 * abs(a))), fd, side, nr, .058, .042, 4 + k % 2, segs=1, lift=.03); put(vs, fs, uv, {'tail_01': .5, 'tail_02': .5}, V((0, 0, 1)), .3)
    me = low_body.data; co = co_np(me); n = nrm_np(me); gn = {g.index: g.name for g in low_body.vertex_groups}
    tris = []; areas = []
    for pl in me.polygons:
        vv = list(pl.vertices)
        for k in range(1, len(vv) - 1):
            tris.append((vv[0], vv[k], vv[k + 1])); areas.append(.5 * np.linalg.norm(np.cross(co[vv[k]] - co[vv[0]], co[vv[k + 1]] - co[vv[0]])))
    areas = np.array(areas); rng = np.random.default_rng(11); pick = rng.choice(len(tris), size=NCONTOUR * 4, p=areas / areas.sum()); cnt = 0
    for ti in pick:
        if cnt >= NCONTOUR: break
        ia, ib, ic = tris[ti]; u, v_ = rng.random(), rng.random()
        if u + v_ > 1: u, v_ = 1 - u, 1 - v_
        p = V(co[ia] * (1 - u - v_) + co[ib] * u + co[ic] * v_); nr = V(n[ia] * (1 - u - v_) + n[ib] * u + n[ic] * v_).normalized(); i = (ia, ib, ic)[int(np.argmax((1 - u - v_, u, v_)))]
        if p.z > .392 or p.z < .085 or (abs(p.y) > .078 and -.15 < p.x < .055 and p.z > .165): continue    # not on the face, between the legs or under the folded wings
        neck = float(ss(.25, .29, np.array([p.z]))[0]) * (p.x > .03); hd = p.z > .365; low = p.z < .165
        if hd and rng.random() < .5: continue
        L = (.034 - .012 * (p.x > .05)) * (1 - neck) + .018 * neck
        if low: L = .040 - .012 * (p.x > .05)
        breast = p.x > .05 and p.z < .27
        if hd: L = .012
        L *= rng.uniform(.85, 1.2)
        flow = (V((-1, 0, -.12)) * (1 - neck) + V((-.25, 0, -1)) * neck); flow = flow + V((0, .5 * (p.y / .1) * (p.x < -.1), 0)) + V((rng.uniform(-.15, .15), rng.uniform(-.15, .15), 0))
        f = flow - nr * flow.dot(nr)
        if f.length < 1e-4: continue
        f.normalize(); side = nr.cross(f).normalized()
        cell = (7 if rng.random() < .35 else 5) if (low or (breast and rng.random() < .6)) else int(rng.choice((4, 5, 4, 6)))
        vs, fs, uv = card(p - f * L * .4 + nr * .0015, f, side, nr, L * 1.3, L * (.85 if cell != 7 else .9), cell, segs=1, lift=rng.uniform(.08, .18) if not (low or breast) else rng.uniform(.03, .08), droop=.0)
        w = {gn[g.group]: g.weight for g in me.vertices[i].groups if g.weight > .01}
        if not w: continue
        put(vs, fs, uv, w, nr, .08 if (low or breast) else .25); cnt += 1
    o = mesh_obj('cards', vs_all, fs_all)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()                               # every card faces out of the plumage
    bmesh.ops.reverse_faces(bm, faces=[f_ for f_ in bm.faces if f_.normal.dot(V(nrs[f_.verts[0].index][0])) < 0]); bm.to_mesh(o.data); bm.free()
    o.data.uv_layers.new(name='UVMap'); uvl = o.data.uv_layers.active.data
    for lp in o.data.loops: uvl[lp.index].uv = uv_all[lp.vertex_index]
    for i, w in enumerate(wts):
        for k, x in w.items():
            g = o.vertex_groups.get(k) or o.vertex_groups.new(name=k); g.add([i], x, 'REPLACE')
    o.data.update(); vnn = nrm_np(o.data); bn = []
    for i, (nr, bl) in enumerate(nrs):
        g = V(vnn[i]); nrv = V(nr)
        if g.dot(nrv) < 0: g = -g
        bn.append(tuple((nrv * (1 - bl) + g * bl).normalized()))
    a = o.data.attributes.new('bn', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', np.asarray(bn, np.float32).ravel())
    log('cards', len(fs_all), 'quads; contour', cnt); return o


def card_normals(ob):
    me = ob.data; k = len(me.vertices)
    if 'bn' not in me.attributes: return
    bn = np.zeros(k * 3, np.float32); me.attributes['bn'].data.foreach_get('vector', bn); bn = bn.reshape(-1, 3)
    vnn = np.zeros(k * 3, np.float32); me.vertices.foreach_get('normal', vnn); vnn = vnn.reshape(-1, 3)
    use = np.linalg.norm(bn, axis=1) > .5; vnn[use] = bn[use]
    me.normals_split_custom_set_from_vertices([tuple(v) for v in vnn]); me.update()


def card_material(name='MI_Duck_FeatherCards', prefix='T_Duck_FeatherCards'):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    def im(suffix, linear):
        x = nt.nodes.new('ShaderNodeTexImage'); x.image = bpy.data.images.load(str(DST / 'Textures' / (prefix + suffix)), check_existing=True); x.image.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'; return x
    bc = im('_BC.png', False); nt.links.new(bc.outputs[0], b.inputs['Base Color']); nt.links.new(bc.outputs['Alpha'], b.inputs['Alpha'])
    orm = im('_ORM.png', True); sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs[0], sp.inputs[0]); nt.links.new(sp.outputs[1], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .6; nt.links.new(im('_N.png', True).outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    b.inputs['Subsurface Weight'].default_value = .25; b.inputs['Subsurface Radius'].default_value = (.006, .004, .003); b.inputs['Subsurface Scale'].default_value = 1.0
    # feather cards cast no shadow on the body (set the same on the Unreal material)
    out = nt.nodes['Material Output']; mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); lp = nt.nodes.new('ShaderNodeLightPath')
    nt.links.new(lp.outputs['Is Shadow Ray'], mx.inputs[0]); nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    m.use_backface_culling = False
    return m


def assemble(coll, arm, body, hard, tris_body):
    low = body.copy(); low.data = body.data.copy(); bpy.context.scene.collection.objects.link(low)
    decimate_to(low, tris_body); clean_mesh(low); arm.data.pose_position = 'REST'
    auto_weights(low, arm)
    # body plumage must not follow wing, shin, foot or jaw bones
    # (their weight is handed to the bone the plumage really sits on; dropping it left vertices behind as stretched black faces)
    drop = [g for g in low.vertex_groups if g.name.startswith(('wing', 'calf', 'foot', 'toes', 'jaw'))]
    to = lambda nm: 'head' if nm == 'jaw' else ('spine_01' if nm.startswith('wing') else 'pelvis')
    for g in drop:
        tg = low.vertex_groups.get(to(g.name)) or low.vertex_groups.new(name=to(g.name))
        for v in low.data.vertices:
            for ge in v.groups:
                if ge.group == g.index and ge.weight > 0: tg.add([v.index], ge.weight, 'ADD')
    for g in drop: low.vertex_groups.remove(g)
    for v in low.data.vertices:
        tot = sum(g.weight for g in v.groups)
        if tot < 1e-5: low.vertex_groups['spine_01' if 'spine_01' in low.vertex_groups else 0].add([v.index], 1.0, 'REPLACE'); continue
        for g in v.groups: g.weight /= tot
    low_body = low.copy(); low_body.data = low.data.copy()                                                # kept for card skinning
    hl = []
    for o in hard:
        c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c); hl.append(c)
    hj = join(hl, 'hardlow') if len(hl) > 1 else hl[0]
    if tri_count(hj) > 5200: decimate_to(hj, 5200)
    low = join([low, hj], 'SK_Duck_LOD0')
    for c in list(low.users_collection): c.objects.unlink(low)
    coll.objects.link(low)
    me = low.data; part = np.zeros(len(me.vertices), np.float32); me.attributes['part'].data.foreach_get('value', part); part = np.round(part).astype(int); co = co_np(me)
    rig = {1: 'head', 2: 'jaw', 3: 'calf_l', 4: 'foot_l', 5: 'toes_l', 6: 'calf_r', 7: 'foot_r', 8: 'toes_r', 9: 'head'}
    for k, b in rig.items(): set_rigid(low, np.nonzero(part == k)[0], {b: 1.0})
    B = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones}
    for k, sd in ((10, 'l'), (11, 'r')):
        x0 = B['wing_' + sd][0].x; x1 = B['wingtip_' + sd][0].x
        for i in np.nonzero(part == k)[0]:
            w = float(np.clip((x0 - co[i, 0]) / (x0 - x1) - .35, 0, 1)); set_rigid(low, [i], {'wingtip_' + sd: w, 'wing_' + sd: 1 - w} if 0 < w < 1 else ({'wingtip_' + sd: 1.0} if w >= 1 else {'wing_' + sd: 1.0}))
    for v in me.vertices:
        if not any(g.weight > 1e-5 for g in v.groups): set_rigid(low, [v.index], {'spine_01': 1.0})
    b = get_color_attr(me, 'msk')[:, 2]
    for p in me.polygons:
        v = float(np.mean([b[i] for i in p.vertices])); p.material_index = 3 if v > .85 else (2 if v > .5 else (1 if v > .2 else 0))
    low.parent = arm
    if not any(m.type == 'ARMATURE' for m in low.modifiers): md = low.modifiers.new('Armature', 'ARMATURE'); md.object = arm
    return low, low_body


def stump_parts(head_side):
    """Neck-stump anatomy in rest space, UV-mapped onto regions of the neck cross-section texture: torn skin collar,
    cervical vertebra stub, ringed trachea (open), collapsed oesophagus, hanging vessels / clotted strings."""
    rng = random.Random(9 if head_side else 4); Nn = CUT_N * (-1 if head_side else 1); ax = CUT_N.cross(V((0, 1, 0))).normalized(); ay = V((0, 1, 0)); out = []
    def uvp(cx, cy, r, th): return (cx + r * math.cos(th), cy + r * math.sin(th))
    def tube_uv(pts, rad, n, centre, r0, r1, cap=True, inner=None):
        vs, fs, ts, an = tube(pts, rad, n, cap=(False, cap)); uv = [uvp(centre[0], centre[1], r0 + (r1 - r0) * t_, a_ * math.tau) for t_, a_ in zip(ts, an)]
        out.append((vs, fs, uv))
        if inner:                                                    # dark lumen
            vs2, fs2, ts2, an2 = tube(pts, [r_ * inner for r_ in rad], n, cap=(False, False)); out.append((vs2, [tuple(reversed(f)) for f in fs2], [uvp(centre[0], centre[1], .02, a_ * math.tau) for a_ in an2]))
    R = .0235
    # torn skin: jagged collar of flaps, some folded outward
    K = 22; ring = []
    for i in range(K):
        th = math.tau * i / K; rr = R * (1.0 + .06 * math.sin(3 * th + 1)); ring.append((th, CUT_P + ax * (rr * math.cos(th) * 1.08) + ay * (rr * math.sin(th)) - Nn * .004))
    vs = []; fs = []; uv = []
    for i in range(K):
        th0, p0 = ring[i]; th1, p1 = ring[(i + 1) % K]; thm = (th0 + (th1 if i < K - 1 else th1 + math.tau)) / 2
        h = rng.uniform(.003, .008) * (1.2 if head_side else 1.0) * (1.8 if rng.random() < .2 else 1); flare = rng.uniform(.1, 1.1)
        radial = (ax * math.cos(thm) + ay * math.sin(thm)); sagv = V((0, 0, -.5 * h if not head_side else 0)); j0 = rng.uniform(.6, 1.0); j1 = rng.uniform(.6, 1.0)
        q0 = p0.lerp(p1, .22) + Nn * (h * j0 + .004) + radial * (h * flare * j0) + sagv; q1 = p0.lerp(p1, .78) + Nn * (h * j1 + .004) + radial * (h * flare * j1) + sagv
        o = len(vs); vs += [p0, p1, q1, q0]; fs += [(o, o + 1, o + 2, o + 3)]
        uv += [uvp(.5, .5, .46, th0), uvp(.5, .5, .46, th1), uvp(.5, .5, .37, th1), uvp(.5, .5, .37, th0)]
    out.append((vs, fs, uv))
    # vertebra: bone stub with a flared articular end, dorsal side
    b0 = CUT_P - ax * (R * .30) - Nn * .003; L = .006 if head_side else .013
    tube_uv([b0, b0 + Nn * (L * .5), b0 + Nn * (L * .85), b0 + Nn * L], [.0058, .0050, .0060, .0048], 10, (.5, .36), .12, .05)
    for sg in (1, -1):                                               # transverse processes
        tube_uv([b0 + Nn * (L * .55), b0 + Nn * (L * .7) + ay * (sg * .006) - ax * .002], [.0024, .0008], 5, (.5, .36), .10, .06)
    # trachea: cartilage rings, open end, pulled forward and drooping
    t0 = CUT_P + ax * (R * .30) - ay * .0015 - Nn * .003; L = .010 if head_side else .020; pts = []; rad = []
    for i in range(9):
        a = i / 8; pts.append(t0 + Nn * (L * a) + ax * (.006 * a * a) + V((0, 0, -.004 * a * a if not head_side else 0))); rad.append(.0042 + .00045 * (i % 2))
    tube_uv(pts, rad, 10, (.47, .63), .068, .095, cap=False, inner=.72)
    # oesophagus: collapsed wet tube
    e0 = CUT_P + ay * (R * .34) - Nn * .003; L = .007 if head_side else .012
    tube_uv([e0, e0 + Nn * (L * .6) + ay * .002, e0 + Nn * L + ay * .005 + V((0, 0, -.004))], [.0038, .0032, .0022], 8, (.65, .525), .07, .03)
    # vessels and clotted strings
    for i in range(0 if head_side else 4):
        th = rng.uniform(0, math.tau); s0 = CUT_P + (ax * math.cos(th) + ay * math.sin(th)) * (R * rng.uniform(.5, .95)); L = rng.uniform(.008, .022) * (.6 if head_side else 1)
        dr = (Nn * .5 + (ax * math.cos(th) + ay * math.sin(th)) * .6 + V((0, 0, -.9 if not head_side else -.2))).normalized()
        tube_uv([s0, s0 + dr * (L * .3) + Nn * .004, s0 + dr * (L * .65) + Nn * .003, s0 + dr * L + V((0, 0, -.003))], [.0014, .0010, .0009, .0017], 5, (.29, .475), .03, .01)
    return out


def cut_variant(src, name, keep_upper, coll, gore_mat, bloody_cards=None):
    """Bisect a copy of the finished duck at the neck, cap the wound with the gore section and add the stump anatomy."""
    o = src.copy(); o.data = src.data.copy(); o.name = name; o.data.name = name; coll.objects.link(o)
    ci = next((i for i, s_ in enumerate(o.material_slots) if s_.material and s_.material.name == 'MI_Duck_FeatherCards'), -1)
    o.data.materials.append(gore_mat); gi = len(o.data.materials) - 1
    bi = -1
    if bloody_cards is not None: o.data.materials.append(bloody_cards); bi = len(o.data.materials) - 1
    bm = bmesh.new(); bm.from_mesh(o.data)
    geom = [e for e in bm.verts[:] + bm.edges[:] + bm.faces[:]]
    res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=CUT_P, plane_no=CUT_N, clear_outer=not keep_upper, clear_inner=keep_upper)
    cut_edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and all(f.material_index != ci for f in e.link_faces)]
    fill = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
    uvl = bm.loops.layers.uv.verify(); ax = CUT_N.cross(V((0, 1, 0))).normalized(); ay = V((0, 1, 0))
    newf = fill['faces']
    if newf:
        res2 = bmesh.ops.triangulate(bm, faces=newf); newf = res2['faces']
        for f in newf:
            f.material_index = gi; f.smooth = False
            for l in f.loops:
                d = l.vert.co - CUT_P; l[uvl].uv = (.5 + d.dot(ay) / .068, .5 + d.dot(ax) / .068)
    for vs, fs, uv in stump_parts(keep_upper):
        bv = [bm.verts.new(p) for p in vs]
        for f in fs:
            try: fc = bm.faces.new([bv[i] for i in f])
            except ValueError: continue
            fc.material_index = gi; fc.smooth = True
            for l, i in zip(fc.loops, f): l[uvl].uv = uv[i]
    if bi >= 0:                                                      # feathers round the wound are soaked
        for f in bm.faces:
            if f.material_index == ci:
                c = f.calc_center_median(); d = (c - CUT_P).length
                if d < .06 + .025 * math.sin(c.x * 300 + c.y * 170) + (.035 if c.x > CUT_P.x else 0): f.material_index = bi
    bm.to_mesh(o.data); bm.free(); clean_mesh(o)
    if not keep_upper and 'neck_02' in o.vertex_groups:
        for v in o.data.vertices:
            if not any(g.weight > 1e-5 for g in v.groups): o.vertex_groups['neck_02'].add([v.index], 1.0, 'REPLACE')
    return o


def shots(arm, tag, which, samples=48, scale=1.0, objs=None):
    R = lambda w, h: (int(w * scale), int(h * scale)); fl = []; D = DST / 'Review'
    def vis(nm):
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.name.startswith(('SK_Duck', 'SM_Duck')): o.hide_render = o.name != nm
    if objs is None: vis('SK_Duck_LOD0')
    if 'game' in which:
        set_action(arm, 'Duck_Idle', 10); f = D / (tag + '_game.png'); shoot(f, game_cam((0, 0, .2), 6.0, -55, 45), (0, 0, .2), 300, R(1200, 900), samples, exposure=-.7); fl.append(f)
    if 'mid' in which:
        set_action(arm, 'Duck_Idle', 10); f = D / (tag + '_mid.png'); shoot(f, game_cam((0, 0, .22), 2.2, -62, 30), (0, 0, .22), 135, R(1200, 900), samples, exposure=-.7); fl.append(f)
    if 'close' in which:
        set_action(arm, 'Duck_Idle', 10); f = D / (tag + '_close.png'); shoot(f, (.78, -.62, .52), (.08, 0, .30), 85, R(1200, 900), samples, exposure=-.7); fl.append(f)
    if 'side' in which:
        set_action(arm, 'Duck_Idle', 30); f = D / (tag + '_side.png'); shoot(f, (0, -1.2, .26), (0, 0, .22), 70, R(1200, 900), samples, exposure=-.7); fl.append(f)
    if 'back' in which:
        set_action(arm, 'Duck_Idle', 30); f = D / (tag + '_back.png'); shoot(f, (-.85, .55, .40), (-.03, 0, .2), 70, R(1200, 900), samples, exposure=-.7); fl.append(f)
    if 'under' in which:
        g = bpy.data.objects['CR_Ground']; g.hide_render = True; set_action(arm, 'Duck_Idle', 30)
        f = D / (tag + '_under.png'); shoot(f, (.15, -.35, -.55), (0, 0, .12), 60, R(1200, 900), samples, exposure=2.6); fl.append(f); g.hide_render = False
    if 'pose' in which:
        for act, fr, az in (('Duck_Walk', 4, -70), ('Duck_Peck', 18, -50), ('Duck_Quack', 8, -30)):
            set_action(arm, act, fr); f = D / ('%s_%s%02d.png' % (tag, act[5:].lower(), fr)); shoot(f, game_cam((0, 0, .2), 1.5, az, 20), (0, 0, .2), 80, R(1000, 750), samples, exposure=-.7); fl.append(f)
    if 'gore' in which:
        vis('SK_Duck_Headless_LOD0'); set_action(arm, 'Duck_HeadlessRun', 4); f = D / (tag + '_headless.png'); shoot(f, game_cam((0, 0, .2), 1.3, -50, 32), (0, 0, .2), 80, R(1000, 750), samples, exposure=-.7); fl.append(f)
        set_action(arm, None, 1); vis('SM_Duck_Head_LOD0'); f = D / (tag + '_head.png'); shoot(f, (-.12, -.42, .22), (0.0, 0, .03), 85, R(1000, 750), samples, exposure=-.7); fl.append(f); vis('SK_Duck_LOD0')
    set_action(arm, None, 1); return fl


if STAGE in ('look', 'final'):
    arm = open_rig(); coll = bpy.data.collections['SK_Duck']
    mats = [duckmat(bpy.data.materials.new(nm)) for nm in MATN]
    body, hard, feath, eyes, wing_feathers = build_high(arm)
    bf = body_feathers(body)
    a = body.data.attributes.new('part', 'FLOAT', 'POINT'); a = body.data.attributes.new('par', 'FLOAT', 'POINT')
    for o in [body, bf] + hard + feath:
        for m in mats: o.data.materials.append(m)
    log('high body tris', tri_count(body))
    if STAGE == 'look':
        setup_review(samples=32, ground='leafy_grass', ground_scale=1.2)
        shots(arm, 'look', A[1].split(',') if len(A) > 1 else ('mid', 'close'), 32, .75, objs=True)
    else:
        res = int(A[1]) if len(A) > 1 else 2048
        low, low_body = assemble(coll, arm, body, hard, 6200)
        high = join([body, bf] + hard + feath, 'DuckHigh')
        hc = bpy.data.collections.new('DuckHigh_Source'); bpy.context.scene.collection.children.link(hc)
        for c in list(high.users_collection): c.objects.unlink(high)
        hc.objects.link(high)
        log('LOD0 body+hard triangles', tri_count(low), 'high', tri_count(high))
        uv = uv_unwrap(low, angle=70, hidden_scale=1.0)
        tex = bake_set(low, DST / 'Textures', 'T_Duck_Atlas', res=res, extra=('sss', 'pos'), source=high, cage=.012, maxray=.04)
        pos = tex.pop('_pos')
        # texels the bake left black (rays that found no source surface) are filled from their neighbours
        from PIL import Image as _I
        bcA = np.asarray(_I.open(tex['BC']).convert('RGB'), dtype=np.float64) / 255.0; ok = (np.abs(pos[::-1, :, :3]).sum(-1) > 1e-6)
        imgs = {k: np.asarray(_I.open(tex[k]).convert('RGB'), dtype=np.float64) / 255.0 for k in ('BC', 'N', 'ORM', 'SSS')}
        m = ok.astype(np.float64)
        for _ in range(48):
            cnt_ = np.zeros_like(m); acc = {k: np.zeros_like(v) for k, v in imgs.items()}
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                rm = np.roll(m, (dy, dx), (0, 1)); cnt_ += rm
                for k, v in imgs.items(): acc[k] += np.roll(v * m[..., None], (dy, dx), (0, 1))
            fill = (m == 0) & (cnt_ > 0)
            if not fill.any(): break
            for k, v in imgs.items(): v[fill] = acc[k][fill] / cnt_[fill][:, None]
            m = np.maximum(m, fill)
        nn_ = imgs['N'] * 2 - 1; inv = nn_[..., 2] < 0; nn_[inv] *= -1; nn_[..., 2] = np.maximum(nn_[..., 2], .25); nn_ /= np.linalg.norm(nn_, axis=-1, keepdims=True); imgs['N'] = nn_ * .5 + .5
        log('filled unbaked texels', int((~ok).sum()), 'inverted normal texels', int(inv.sum()))
        for k, v in imgs.items(): _I.fromarray((np.clip(v, 0, 1) * 255 + .5).astype(np.uint8)).save(tex[k])
        for im_ in bpy.data.images:
            if im_.filepath and 'T_Duck_Atlas' in im_.filepath: im_.reload()
        for i, nme in enumerate(MATN):
            old = low.material_slots[i].material; old.name = nme + '_Procedural'; old.use_fake_user = True
            low.material_slots[i].material = game_material(nme, tex, sss=True, sss_scale=1.0, sss_radius=(.006, .004, .003))
        high.hide_render = True; high.hide_viewport = True
        # feather cards
        cards = build_cards(low_body, wing_feathers, arm); cm = card_material(); cards.data.materials.append(cm)
        low.data.attributes.new('bn', 'FLOAT_VECTOR', 'POINT')
        low.data.materials.append(cm); ci = len(low.data.materials) - 1
        nf0 = len(low.data.polygons)
        low = join([low, cards], 'SK_Duck_LOD0')
        for p in low.data.polygons[nf0:]: p.material_index = ci
        for v in low.data.vertices:
            if not any(g.weight > 1e-5 for g in v.groups): low.vertex_groups['spine_01'].add([v.index], 1.0, 'REPLACE')
        low.parent = arm
        # gore variants
        gt = gore_textures(); gm = game_material('MI_Duck_Gore', gt); gm.use_backface_culling = False; bcm = card_material('MI_Duck_FeatherCards_Bloody', 'T_Duck_FeatherCards_Bloody')
        bt = bloody_variant(tex, pos)
        hcoll = bpy.data.collections['SK_Duck_Headless']; pcoll = bpy.data.collections['SM_Duck_Head']
        if arm.name not in hcoll.objects: hcoll.objects.link(arm)
        headless = cut_variant(low, 'SK_Duck_Headless_LOD0', False, hcoll, gm, bcm)
        head = cut_variant(low, 'SM_Duck_Head_LOD0', True, pcoll, gm, bcm)
        for o, pre in ((headless, 'H'), (head, 'P')):
            for i, s in enumerate(o.material_slots):
                if s.material and s.material.name in MATN[:1]:
                    s.material = game_material('MI_Duck_Feather_Bloody', bt, sss=True, sss_scale=1.0, sss_radius=(.006, .004, .003))
        # severed head becomes a static prop lying on its side at the origin
        head.parent = None
        for m in list(head.modifiers): head.modifiers.remove(m)
        head.vertex_groups.clear()
        c = co_np(head.data); ctr = np.array(CUT_P); c -= ctr; rot = Matrix.Rotation(math.radians(90), 3, 'X') @ Matrix.Rotation(math.radians(-25), 3, 'Y')
        c = c @ np.array(rot).T; c[:, 2] -= c[:, 2].min(); c[:, 0] -= (c[:, 0].min() + c[:, 0].max()) / 2; c[:, 1] -= (c[:, 1].min() + c[:, 1].max()) / 2; set_co(head.data, c)
        bnv = np.zeros(len(head.data.vertices) * 3, np.float32); head.data.attributes['bn'].data.foreach_get('vector', bnv); head.data.attributes['bn'].data.foreach_set('vector', (bnv.reshape(-1, 3) @ np.array(rot).T).astype(np.float32).ravel())
        from dinkasset import common, make_lods
        report = {}
        for cn, o in (('SK_Duck', low), ('SK_Duck_Headless', headless), ('SM_Duck_Head', head)):
            asset = common.Asset(bpy.data.collections[cn]); lg = make_lods.make_lods(asset, [.5, .25], replace=True, force=True); asset.refresh()
            for m in asset.renders:
                clean_mesh(m)
                if cn != 'SM_Duck_Head': limit_weights(m)
                m.hide_render = m.name != 'SK_Duck_LOD0'
            report[cn] = [{'name': m.name, 'triangles': tri_count(m)} for m in asset.renders]
            card_normals(o)
        (DST / 'duck_build.json').write_text(json.dumps({'uv': uv, 'texture_px': res, 'lods': report, 'dimensions_m': list(low.dimensions), 'high_triangles': tri_count(high)}, indent=1, default=str))
        for im in bpy.data.images:
            if im.filepath and str(DST / 'Textures') in bpy.path.abspath(im.filepath): im.filepath = '//Textures/' + Path(im.filepath).name
        bpy.ops.wm.save_as_mainfile(filepath=str(DST / 'SK_Duck.blend'), relative_remap=False); log('FINAL SAVED')
if STAGE == 'review':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Duck.blend')); arm = bpy.data.objects['Armature']
    sm = int(A[3]) if len(A) > 3 else 64; setup_review(samples=sm, ground='leafy_grass', ground_scale=1.2); shots(arm, A[1], A[2].split(','), sm)
if STAGE == 'export':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Duck.blend')); arm = bpy.data.objects['Armature']
    for o in list(bpy.data.objects):
        if o.name == 'DuckHigh': bpy.data.objects.remove(o)
    which = A[1] if len(A) > 1 else 'SK_Duck'
    acts = {'Idle': 'Duck_Idle', 'Walk': 'Duck_Walk', 'Run': 'Duck_Run', 'Peck': 'Duck_Peck', 'Quack': 'Duck_Quack', 'Hit': 'Duck_Hit', 'Death': 'Duck_Death', 'HeadlessRun': 'Duck_HeadlessRun', 'HeadlessDeath': 'Duck_HeadlessDeath'}
    if which == 'SK_Duck': export_skeletal('SK_Duck', arm, DST / 'Export', acts, 'A_Duck', 30, DST / 'duck_validation.json')
    elif which == 'SK_Duck_Headless': export_skeletal('SK_Duck_Headless', arm, DST / 'Export', {}, 'A_Duck', 30, DST / 'duck_headless_validation.json')
    else:
        from dinkasset import export_ue
        sc = bpy.context.scene
        for o in bpy.data.collections['SM_Duck_Head'].objects:
            if o.type != 'MESH': continue
            for v in o.data.vertices: v.co *= 100
        sc.unit_settings.scale_length = .01
        for material in bpy.data.materials:
            if material.node_tree: material.node_tree.nodes.clear()
        for o in sorted(bpy.data.collections['SM_Duck_Head'].objects, key=lambda o: o.name):
            if o.type != 'MESH': continue
            proxy = type('ExportAsset', (), {'renders': [o], 'collision': [], 'armatures': [], 'sockets': []})()
            with export_ue.unhidden([o]): export_ue.export_fbx(proxy, str(DST / 'Export' / (o.name + '.fbx')), 'all', 'Armature')
        log('exported head prop')
