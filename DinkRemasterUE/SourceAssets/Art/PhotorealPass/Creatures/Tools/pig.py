"""Photoreal domestic pig (v2, 12 Nov 2026 rebuild after review) skinned to the existing 26-bone SK_Pig rig and its clips.
Long deep barrel, sagging belly, short stout legs with cloven trotters and dewclaws, thick neck into a large wedge head, jowls, disc snout,
lashed eyes, large veined ears, curled tail; bristle cards; skin with wrinkles, blotches, scurf, sun-pinked areas, mud and dung.
usage: blender -b -t 4 --python pig.py -- <stage>   stage: look [shots] | final [res] | review tag shots [samples] | export
"""
import bpy, sys, os, math, json, random
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *

A = args(); STAGE = A[0] if A else 'look'
DST = OUT / 'Pig'; (DST / 'Review').mkdir(parents=True, exist_ok=True); (DST / 'Work').mkdir(exist_ok=True)
SRC = ART / 'Creatures/Pig/SK_Pig.blend'
random.seed(407); V = Vector
NCARD = 2200
MUD = THIRD / 'polyhaven/brown_mud_02/brown_mud_02_diff_2k.jpg'
DRY = THIRD / 'polyhaven/mud_cracked_dry_riverbed_002/mud_cracked_dry_riverbed_002_diff_2k.jpg'
MATN = ['MI_Pig_Skin', 'MI_Pig_Muzzle', 'MI_Pig_HornBristle', 'MI_Pig_Eye']
VOX = .007
SZ = .628            # snout disc centre height


def open_rig():
    bpy.ops.wm.open_mainfile(filepath=str(SRC))
    for o in list(bpy.data.objects):
        if o.type != 'ARMATURE': bpy.data.objects.remove(o)
    for c in list(bpy.data.collections):
        if c.name != 'SK_Pig': bpy.data.collections.remove(c)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    for i in list(bpy.data.images): bpy.data.images.remove(i)
    coll = bpy.data.collections['SK_Pig']
    arm = bpy.data.objects['Armature']; arm.animation_data_create(); arm.animation_data.action = None; arm.data.pose_position = 'REST'
    return coll, arm


def seg_dist(co, a, b):
    a = np.array(a); b = np.array(b); ab = b - a; t = np.clip(((co - a) @ ab) / (ab @ ab), 0, 1); return np.linalg.norm(co - (a + t[:, None] * ab), axis=1)
def poly_dist(co, pts):
    d = np.full(len(co), 1e9)
    for a, b in zip(pts[:-1], pts[1:]): d = np.minimum(d, seg_dist(co, a, b))
    return d
def vn(co, scale, seed=0.0):
    """Smooth signed noise per vertex (asymmetric, non-periodic)."""
    o = V((seed, seed * 1.7, seed * 2.3)); return np.array([noise.noise(V(p) * scale + o) for p in co])


def build_high(arm):
    B = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones}
    parts = []
    def add(vs, fs, nm='p'): o = mesh_obj(nm, vs, fs); parts.append(o); return o
    # x, centre z, half height up, half height down, half width, superellipse exponent
    T = [(-.752, .70, .05, .05, .04, 2.0), (-.725, .66, .15, .17, .13, 2.0), (-.66, .63, .245, .27, .225, 2.1), (-.56, .62, .29, .30, .285, 2.2),
         (-.42, .62, .305, .325, .315, 2.25), (-.26, .62, .312, .355, .33, 2.3), (-.10, .62, .312, .375, .335, 2.3), (.06, .62, .305, .35, .33, 2.3),
         (.20, .625, .295, .325, .315, 2.25), (.32, .635, .28, .30, .29, 2.2), (.43, .645, .26, .28, .26, 2.15), (.52, .655, .24, .265, .235, 2.1),
         (.60, .66, .225, .25, .212, 2.1), (.67, .66, .195, .235, .19, 2.1), (.74, .655, .158, .20, .16, 2.1), (.81, .645, .122, .158, .125, 2.15),
         (.875, .637, .098, .122, .10, 2.2), (.93, .631, .083, .098, .086, 2.3), (.972, SZ, .075, .084, .078, 2.6), (.998, SZ, .071, .077, .074, 3.0)]
    add(*loft([((x, 0, zc), (0, hw, 0), (0, 0, hu), (0, 0, hd), e) for x, zc, hu, hd, hw, e in T], 44))
    # shoulder, ham, jowl, cheek, brow/ear root, withers, belly sag, brisket
    for c, r in (((.20, .21, .60), (.20, .135, .25)), ((-.46, .20, .58), (.25, .165, .28)), ((.60, .095, .50), (.13, .09, .10)), ((.69, .105, .60), (.095, .065, .10)),
                 ((.26, 0, .87), (.18, .15, .07)), ((-.12, .02, .40), (.40, .29, .15)), ((.40, 0, .47), (.15, .16, .11)),
                 ((-.50, 0, .62), (.265, .235, .285))):                                                    # the rump between the hams: one rounded mass, no crease
        for s in ((1, -1) if c[1] > .05 else (1,)):
            vs, fs, d = ellipsoid((c[0], c[1] * s, c[2]), r, 24, 14); add(vs, fs)
    def limb(pts, y):
        st = []
        for i, (p, rx, ry) in enumerate(pts):
            a = V((pts[max(0, i - 1)][0][0], 0, pts[max(0, i - 1)][0][1])); b = V((pts[min(len(pts) - 1, i + 1)][0][0], 0, pts[min(len(pts) - 1, i + 1)][0][1])); t = (b - a).normalized()
            fwd = V((-t.z, 0, t.x));  fwd = fwd if fwd.x > 0 else -fwd
            st.append(((p[0], y, p[1]), V((0, ry, 0)), fwd * rx, None, 2.3))
        return loft(st, 22)
    feet = {}
    for s, sd in ((1, 'l'), (-1, 'r')):
        y = B['upperarm_' + sd][0].y * .93; hf = B['hand_' + sd][1]; feet['hand_' + sd] = hf
        add(*limb([((.17, .52), .135, .105), ((.175, .41), .105, .088), ((.195, .31), .082, .074), ((.218, .185), .068, .064), ((.228, .15), .071, .066), ((.243, .105), .058, .058), ((.258, .068), .062, .064), ((.265, .05), .060, .062)], y))
        ft = B['foot_' + sd][1]; feet['foot_' + sd] = ft
        add(*limb([((-.34, .52), .185, .13), ((-.28, .42), .15, .112), ((-.335, .32), .105, .088), ((-.42, .225), .072, .064), ((-.435, .19), .074, .064), ((-.42, .12), .057, .056), ((-.395, .068), .062, .064), ((-.385, .05), .060, .062)], B['thigh_' + sd][0].y * .93))
    body = join(parts, 'PigBody')
    apply_mod(body, 'REMESH', mode='VOXEL', voxel_size=VOX, adaptivity=0)
    apply_mod(body, 'SMOOTH', factor=.6, iterations=16)
    me = body.data; me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.update()
    co = co_np(me); n = nrm_np(me); x, y, z = co[:, 0], co[:, 1], co[:, 2]; ay = np.abs(y)
    N1 = vn(co, 3.1, 1.0); N2 = vn(co, 7.5, 4.0); N3 = vn(co, 19, 9.0)
    def push(c, r, d, axis=None):
        nonlocal co
        g = gauss(np.linalg.norm(co - np.array(c), axis=1), r)[:, None] * d; co += (n if axis is None else np.array(axis)[None, :]) * g
    # narrower topline than belly; flat-ish back; dished face
    co[:, 1] *= (1 - .17 * ss(.70, .95, z) * (1 - ss(.5, .66, x)))
    co[:, 2] -= .018 * gauss(x - .82, .07) * ss(.66, .72, z) * (1 - ss(.05, .12, ay))                                       # dish between brow and snout
    # asymmetry: belly hangs a little to one side, one ham fuller, general organic lumpiness
    co[:, 1] += .006 * gauss(z - .36, .12) * gauss(x + .1, .35)
    co += n * (N1 * .0035 + N2 * .0018 + N3 * .0012)[:, None]                     # was .010/.005: read as lumps, not as flesh
    # spine ridge, hip bones, shoulder blades
    co += n * (.010 * gauss(y, .028) * ss(.8, .9, z) * ss(-.66, -.5, x) * (1 - ss(.3, .5, x)))[:, None]
    for s in (1, -1):
        push((.22, s * .31, .60), .15, .012); push((-.50, s * .31, .56), .19, .012); push((.06, s * .335, .62), .09, -.005); push((-.30, s * .335, .62), .10, -.006); push((-.46, s * .17, .93), .07, .006); push((.36, s * .25, .62), .08, -.004)
        push((-.47, s * .16, .925), .09, .007); push((.2, s * .17, .91), .11, .006); push((-.27, s * .33, .55), .14, -.006); push((.03, s * .33, .58), .12, -.004)
        push((.66, s * .17, .53), .06, .010)                                                              # jowl
    # neck rolls and jowl folds: deep, irregular
    m = ss(.31, .38, x) * (1 - ss(.60, .68, x)) * (1 - ss(.80, .9, z))
    ph = (x - .33) * math.tau / .075 + ay * 4.5 + N2 * 2.2 + (z - .6) * 3
    co += n * (.0038 * np.sin(ph) * m * (.35 + .65 * N1) * (1 - .7 * ss(.62, .84, z)))[:, None]     # folds, not ribs
    m2 = ss(.56, .62, x) * (1 - ss(.74, .8, x)) * (1 - ss(.50, .58, z))                                   # under-jaw dewlap folds
    co += n * (.005 * np.sin((x - .56) * math.tau / .05 + N2 * 2) * m2)[:, None]
    # flank folds at elbow and stifle, belly skin ripples
    for cx_, cz_, dp in ((.075, .48, .011), (-.2, .47, .012)):
        m = gauss(z - cz_, .10) * ss(.2, .29, ay)
        co -= n * (dp * .6 * gauss(x - cx_ - (z - cz_) * .45 + N2 * .012, .022) * m)[:, None]
    co += n * (.003 * np.sin(x * math.tau / .06 + N2 * 3) * (n[:, 2] < -.4) * ss(.44, .34, z) * (ay < .25))[:, None]
    # leg joint wrinkles (carpus, hock, pastern)
    legd = np.full(len(co), 1e9)
    for s in (1, -1):
        for pl in ([(.175, s * .218, .43), (.195, s * .218, .31), (.218, s * .218, .185), (.265, s * .218, .05)], [(-.28, s * .218, .43), (-.335, s * .218, .32), (-.42, s * .218, .225), (-.385, s * .218, .05)]): legd = np.minimum(legd, poly_dist(co, pl))
    leg = (z < .44) * (1 - ss(.10, .135, legd))
    for jz, a_ in ((.07, .0012), (.16, .0018), (.21, .0018), (.33, .002), (.40, .002)):
        co += n * (a_ * np.sin(z * math.tau / .016 + N3 * 2.5) * gauss(z - jz, .03) * leg)[:, None]
    for s in (1, -1): push((-.468, s * .218, .215), .028, .012, (-1, 0, .2))                                # point of hock
    # face: eye sockets, lids, brow
    eyes = []
    for s in (1, -1):
        hit, loc, nor, _ = body.ray_cast(V((.742, s * .5, .752)), V((0, -s, 0)))
        loc = np.array(loc); nn = np.array(nor); eyes.append((loc, nn))
        q = co - loc; d = np.sqrt((q[:, 0] / 1.5) ** 2 + q[:, 1] ** 2 + (q[:, 2] + q[:, 0] * .3) ** 2)       # almond, slanted
        co -= nn[None, :] * (gauss(d, .0148) * .011)[:, None]
        up = np.clip((z - loc[2]) / .02, -1, 1)
        co += nn[None, :] * (gauss(d - .0155, .005) * (.0045 + .0035 * up))[:, None]                     # lid rims, heavier upper lid
        co += nn[None, :] * (gauss(d - .036, .011) * .006 * (up > 0))[:, None]                           # fat brow fold
        co -= nn[None, :] * (gauss(d - .03, .007) * .003 * (up < 0))[:, None]                            # under-eye crease
        co -= nn[None, :] * (gauss(d - .05, .006) * .002 * (up < 0))[:, None]
    # snout: raised disc rim, comma nostrils, mouth with lip roll, bridge wrinkles
    r = np.hypot(y * .95, z - SZ); front = ss(.968, .996, x)
    co[:, 0] += .0045 * gauss(r - .058, .012) * front - .0025 * gauss(r, .035) * front
    co += n * (.007 * gauss(x - .975, .011) * (r > .05))[:, None]                                          # rostral rim flare
    co -= n * (.004 * gauss(x - .945, .010) * (r > .05) * (z > SZ - .03))[:, None]                         # groove behind the disc
    for s in (1, -1):
        d = np.hypot((y - s * .026 - .012 * s * (z - SZ - .008) / .02) * 1.25, (z - SZ - .008) * .8); co[:, 0] -= .034 * gauss(d, .011) * ss(.95, .99, x)
        ml = [(1.0, 0, SZ - .058), (.955, s * .052, SZ - .060), (.88, s * .082, SZ - .066), (.81, s * .108, SZ - .062), (.755, s * .135, SZ - .04)]
        d = poly_dist(co, ml); co -= n * (.009 * gauss(d, .006))[:, None]
        co += n * (.005 * gauss(d - .017, .01) * (z < SZ - .062))[:, None]                                # lower lip roll
    for k in range(5):                                                                                    # snout bridge wrinkles
        xx = .80 + k * .034; co -= n * (.0038 * gauss(x - xx - ay * .3 + N3 * .004, .0055) * ss(SZ + .03, SZ + .07, z) * (x > .76))[:, None]
    for k in range(3):                                                                                    # forehead furrows
        xx = .64 + k * .035; co -= n * (.003 * gauss(x - xx + N2 * .01, .006) * ss(.8, .84, z) * (ay < .09))[:, None]
    # teats: two rows of six along the belly
    for k in range(6):
        for s in (1, -1):
            tx = -.40 + k * .105; ty = s * (.085 + .012 * math.sin(k * 1.7)) + .012; hit, loc, nor, _ = body.ray_cast(V((tx, ty, 0.05)), V((0, 0, 1)))
            if hit and loc.z < .5:
                d = np.hypot(x - tx, y - ty); m_ = (n[:, 2] < -.3) & (z < .55)
                co[:, 2] -= (.018 * gauss(d, .010) + .005 * gauss(d, .03)) * m_
    set_co(me, co)
    # ---------------- masks on the body
    co = co_np(me); n = nrm_np(me); x, y, z = co[:, 0], co[:, 1], co[:, 2]; ay = np.abs(y)
    N1 = vn(co, 2.3, 21.0); N2 = vn(co, 6.0, 33.0); N3 = vn(co, 15, 5.0)
    legd = np.full(len(co), 1e9)
    for s in (1, -1):
        for pl in ([(.175, s * .218, .43), (.195, s * .218, .31), (.218, s * .218, .185), (.265, s * .218, .05)], [(-.28, s * .218, .43), (-.335, s * .218, .32), (-.42, s * .218, .225), (-.385, s * .218, .05)]): legd = np.minimum(legd, poly_dist(co, pl))
    leg = (z < .44) * (1 - ss(.10, .135, legd))
    eyd = np.minimum(np.linalg.norm(co - eyes[0][0], axis=1), np.linalg.norm(co - eyes[1][0], axis=1))
    red = np.clip(.55 * ss(.80, .96, x) + .5 * gauss(eyd, .05) + .85 * ss(.75, .92, z) * ss(.55, .9, n[:, 2]) * (.6 + .6 * N1) + .35 * (1 - ss(.34, .46, z)) * (n[:, 2] < .2) + .25 * (1 - ss(.1, .3, z)), 0, 1)
    mud = (1.0 * (1 - ss(.05, .26, z)) + .55 * (1 - ss(.18, .44, z)) + .75 * (n[:, 2] < -.2) * (1 - ss(.36, .50, z)) + .85 * ss(.925, .985, x) * (1 - ss(SZ - .03, SZ + .035, z))
           + .5 * (1 - ss(.3, .62, z)) * ss(.2, .3, ay) * (.5 + N1) + .55 * ss(.12, .3, y) * (1 - ss(.45, .78, z)) * ss(-.1, .5, N1 + .6 * N2) + .25 * ss(.3, .7, N2) * (1 - ss(.4, .7, z)))
    mud = np.clip(mud + .22 * N2 + .1 * N3, 0, 1)
    rr = np.hypot(y, z - SZ)
    pid = np.where((x > .976) & (rr < .066), .33, 0.0)
    wr = np.clip(.45 * ss(.31, .38, x) * (1 - ss(.60, .68, x)) * (1 - ss(.80, .9, z)), 0, .45)
    wr = np.maximum(wr, np.where((leg > .5) & (z < .36), .55 + .45 * np.maximum.reduce([gauss(z - j, .05) for j in (.07, .16, .21, .33, .40)]), 0))
    set_color_attr(me, 'msk', np.stack([red, mud, pid, wr], 1))
    dung = np.clip(.45 * ss(-.36, -.70, x) * (1 - ss(.50, .86, z)) * (.75 + .9 * N2) + .35 * gauss(np.hypot(x + .72, z - .62), .07) * (ay < .08) * (.4 + N3) + .5 * ss(.35, .7, N1 * N2 * 4) * (x < -.1) * (z < .6), 0, 1)
    hair = np.clip(ss(.36, .5, z) * (1 - ss(.86, .95, x)) * (1 - .6 * (n[:, 2] < -.5)), 0, 1)
    thickm = ss(.62, 1.0, mud + .3 * N3) * (.0045 + .005 * np.abs(vn(co, 28, 3.0)))                       # caked mud has thickness
    co2 = co + n * thickm[:, None]
    rg = np.random.default_rng(12); cand = np.nonzero((x < -.40) & (z > .28) & (z < .84) & (n[:, 0] < .2))[0]
    for i in rg.choice(cand, 34, replace=False):                                                          # dung clumps and their smears running down
        d = np.linalg.norm(co - co[i], axis=1); r_ = rg.uniform(.010, .022); co2 += n * (rg.uniform(.005, .011) * gauss(d, r_))[:, None]
        dung = np.maximum(dung, gauss(d, r_ * 1.3)); dung = np.maximum(dung, .8 * gauss(np.hypot(x - co[i, 0], y - co[i, 1]), r_ * .6) * (z < co[i, 2]) * ss(co[i, 2] - .12 * rg.random(), co[i, 2], z))
    set_co(me, co2)
    set_color_attr(me, 'loc', np.stack([dung, np.zeros(len(co)), np.zeros(len(co)), hair], 1))
    # ---------------- separate shells (same in high and low)
    hard = []
    def hp(vs, fs, msk, part, param=None, sub=0, loc=None):
        o = mesh_obj('hard', vs, fs)
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if bm.calc_volume(signed=True) < 0: bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(o.data); bm.free()
        if sub: apply_mod(o, 'SUBSURF', levels=sub, render_levels=sub)
        k = len(o.data.vertices); c = co_np(o.data)
        set_color_attr(o.data, 'msk', np.tile(np.array(msk, float), (k, 1)) if not callable(msk) else msk(c))
        set_color_attr(o.data, 'loc', np.tile(np.array(loc or (0, 0, 0, 0), float), (k, 1)) if not callable(loc) else loc(c))
        a = o.data.attributes.new('part', 'FLOAT', 'POINT'); a.data.foreach_set('value', [float(part)] * k)
        a = o.data.attributes.new('par', 'FLOAT', 'POINT'); a.data.foreach_set('value', list(param(c)) if param else [0.0] * k)
        hard.append(o); return o
    pidx = {'hand_l': 1, 'hand_r': 2, 'foot_l': 3, 'foot_r': 4}
    for key, hf in feet.items():
        fy = hf.y * .93; hx = hf.x - (.065 if key.startswith('hand') else 0)        # front hooves sit under a straighter cannon; still rigid on hand_*
        for t in (1, -1):                                                      # cloven main toes: wedge hooves, split, slightly splayed
            cy = fy + t * .029; fx = hx - .04; spl = t * .004
            st = [((fx - .012, cy, .082), (0, .024, 0), (.033, 0, 0), None, 2.3), ((fx - .006, cy, .062), (0, .027, 0), (.038, 0, 0), None, 2.4),
                  ((fx + .008, cy + spl, .028), (0, .0285, 0), (.049, 0, 0), None, 2.7), ((fx + .016, cy + spl * 1.5, .0), (0, .029, 0), (.056, 0, 0), None, 3.0)]
            vs, fs = loft(st, 14)
            vs = [V((p.x + .016 * max(0, (p.x - fx)) / .04 * (1 - p.z / .082), p.y - t * .008 * max(0, (p.x - fx)) / .04, p.z)) for p in vs]
            hp(vs, fs, (0, .9, .66, 0), pidx[key], sub=1)
            vs, fs, ts, an = tube([(hx - .098, fy + t * .040, .128), (hx - .112, fy + t * .046, .10), (hx - .12, fy + t * .049, .072)], [.018, .016, .005], 8)   # dewclaws
            hp(vs, fs, (0, .9, .66, 0), pidx[key])
    for s, sd in ((1, 'l'), (-1, 'r')):                                        # ears: large pinnae, thick rolled root buried in the head, cupped, tips tipping forward
        Bp = V((.575, s * .100, .812)); Ax = V((.30, s * .48, .82)).normalized(); Nf = V((.78, s * .55, -.28)).normalized(); Wd = Ax.cross(Nf).normalized() * s
        Nf = Wd.cross(Ax).normalized() * s
        NA, NR = 16, 18; EL = .27 if s > 0 else .26; lean = .8 if s > 0 else 1.25; st = []
        for i in range(NA + 1):
            a = i / NA; w = .122 * (math.sin(math.pi * min(1, a * .80 + .2)) ** .65) * (1 - .55 * a ** 3.5) + .004
            c = Bp + Ax * (EL * a - .03) + Nf * (.05 * lean * a * a) - V((0, 0, .022 * lean * a ** 3)) + Wd * (.012 * math.sin(a * 5 + s))
            th = .016 * (1 - a) ** 1.2 + .0038; cup = .024 * (1 - a * .6) * (1 + .3 * math.sin(a * 7 + s * 2))
            st.append((c, w, th, cup))
        vs = []; fs = []
        for (c, w, th, cup) in st:
            for j in range(NR):
                an_ = math.tau * j / NR; cx = math.cos(an_); sx = math.sin(an_)
                vs.append(c + Wd * (w * cx) + Nf * (th * sx - cup * (1 - cx * cx) + .003 * math.sin(cx * 6 + c.z * 40)))
        for i in range(NA):
            for j in range(NR):
                q = i * NR + j; q2 = i * NR + (j + 1) % NR; fs.append((q, q2, q2 + NR, q + NR))
        vs.append(st[0][0]); vs.append(st[-1][0]); c0 = len(vs) - 2; c1 = c0 + 1; o_ = NA * NR
        fs += [(c0, (j + 1) % NR, j) for j in range(NR)] + [(c1, o_ + j, o_ + (j + 1) % NR) for j in range(NR)]
        bpn = np.array(Bp); axn = np.array(Ax)
        par = lambda c, bpn=bpn, axn=axn, EL=EL: np.clip(((c - bpn) @ axn) / EL, 0, 1)
        hp(vs, fs, lambda c: np.stack([np.full(len(c), .3), .25 * ss(.5, 1, vn(c, 14, 2.0) + .5), np.zeros(len(c)), np.zeros(len(c))], 1), 5 if s > 0 else 6, param=par, sub=1,
           loc=lambda c, par=par: np.stack([np.zeros(len(c)), np.ones(len(c)), par(c), .5 * np.ones(len(c))], 1))
    t0 = B['tail_01'][0]; pts = []; rad = []                                    # curly tail with a flattened tip
    for i in range(17):
        a = i / 16; th = a * math.pi * 2.9
        pts.append(t0 + V((-.03 - .09 * a + .014 * math.sin(th), .036 * math.sin(th) * min(1, a * 3) + .01 * a, -.03 * a + .04 * (1 - math.cos(th)) * min(1, a * 3) * .5))); rad.append(.022 * (1 - a) ** .7 + .0045)
    vs, fs, ts, an = tube(pts, rad, 10)
    tx0 = t0.x
    hp(vs, fs, (.5, .15, 0, 0), 7, param=lambda c: np.clip((tx0 - .02 - c[:, 0]) / .12, 0, 1), loc=(.5, 0, 0, .3))
    for s, (loc, nn) in zip((1, -1), eyes):                                    # eyeballs
        c = loc - nn * .0072; vs, fs, d = ellipsoid(c, (.015, .015, .015), 20, 12); cn = np.array(c)
        hp(vs, fs, (0, 0, 1, 0), 8, loc=lambda q, cn=cn, nn=nn: np.stack([np.clip(((q - cn) / .015) @ (nn + np.array((.25, 0, -.1))) / np.linalg.norm(nn + np.array((.25, 0, -.1))), 0, 1), np.zeros(len(q)), np.zeros(len(q)), np.zeros(len(q))], 1))
    a = body.data.attributes.new('part', 'FLOAT', 'POINT'); a = body.data.attributes.new('par', 'FLOAT', 'POINT')
    return body, hard, eyes


def pigskin(mat):
    t = NT(mat); tc = t.node('ShaderNodeTexCoord'); P = tc.outputs['Object']; geo = t.node('ShaderNodeNewGeometry')
    ma = t.attr('msk'); mR, mG, mB = t.sep(ma.outputs['Color'])[:3]; mA = ma.outputs['Alpha']
    la = t.attr('loc'); lR, lG, lB = t.sep(la.outputs['Color'])[:3]; lA = la.outputs['Alpha']
    isMuz = t.math('COMPARE', mB, .33, .12); isHorn = t.math('COMPARE', mB, .66, .12); isEye = t.math('GREATER_THAN', mB, .9); isEar = lG
    up = t.sepxyz(geo.outputs['Normal'])[2]; pz = t.sepxyz(P)[2]
    big, _ = t.noise(P, 2.1, 3, .55, dist=.4); mid, _ = t.noise(P, 8, 4, .62); fine, _ = t.noise(P, 55, 3, .6)
    # --- living skin: cream-pink with macro variation, pale underside, sun-pinked topline, liver blotches, freckles
    c = t.mix(t.smooth(big, .32, .7), (.30, .13, .10), (.48, .25, .19))
    c = t.mix(t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(up, -.7, -.1)), .35), c, (.66, .47, .40))               # paler belly
    blot, _ = t.noise(P, 4.6, 3, .62, dist=.6)
    redf = t.math('ADD', t.math('MULTIPLY', mR, .95), t.math('MULTIPLY', t.smooth(blot, .5, .74), .42), clamp=True)
    c = t.mix(redf, c, (.42, .10, .08))                                                                               # sunburn / blood flush
    lv, _ = t.noise(P, 3.3, 3, .6, dist=1.1); lv2, _ = t.noise(P, 14, 3, .7)
    liver = t.math('MULTIPLY', t.smooth(t.math('ADD', lv, t.math('MULTIPLY', t.math('SUBTRACT', lv2, .5), .16)), .58, .64), .62)
    c = t.mix(liver, c, (.15, .095, .08))                                                                               # grey-brown pigment patches
    vd, vc = t.voronoi(P, 23, 'F1'); spot = t.math('MULTIPLY', t.math('GREATER_THAN', t.sep(vc)[0], .82), t.math('SUBTRACT', 1.0, t.smooth(vd, .08, .24)))
    c = t.mix(t.math('MULTIPLY', spot, .4), c, (.20, .11, .09))
    c = t.mix(1.0, c, t.ramp(mid, [(.28, .78), (.5, 1.0), (.74, 1.16)]), 'MULTIPLY')
    # --- wrinkle network and pores
    wv = t.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); t.link(t.vmath('ADD', t.mapping(P, (90, 150, 150)), t.vmath('SCALE', t.noise(P, 12, 2, .5)[1], s=1.2)), wv.inputs['Vector']); wv.inputs['Scale'].default_value = 1.0
    crease = t.math('SUBTRACT', 1.0, t.smooth(wv.outputs['Distance'], .0, .09))
    wv2 = t.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); t.link(t.mapping(P, (140, 190, 190), (.3, .2, .4)), wv2.inputs['Vector']); wv2.inputs['Scale'].default_value = 1.0
    crease2 = t.math('SUBTRACT', 1.0, t.smooth(wv2.outputs['Distance'], .0, .12))
    c = t.mix(t.math('MULTIPLY', t.math('MAXIMUM', crease, t.math('MULTIPLY', crease2, .5)), .10), c, (.30, .12, .095))
    fol, _ = t.voronoi(P, 210, 'F1'); folm = t.math('SUBTRACT', 1.0, t.smooth(fol, .0, .45))
    c = t.mix(t.math('MULTIPLY', folm, .22), c, (.33, .16, .12))
    # --- lying bristle coat baked into the skin (body flows aft, legs flow down)
    isLegW = t.smooth(mA, .5, .9)
    def strands(scale_b, scale_l, seedv, wd):
        fb, _ = t.noise(t.mapping(P, scale_b, (0, .12, .05), seedv), 1.0, 2, .5, dist=.25); fl, _ = t.noise(t.mapping(P, scale_l, (.1, 0, 0), seedv), 1.0, 2, .5, dist=.25)
        f = t.mixf(isLegW, fb, fl); return t.math('SUBTRACT', 1.0, t.smooth(t.math('ABSOLUTE', t.math('SUBTRACT', f, .5)), .0, wd))
    h1 = strands((7, 330, 330), (330, 330, 9), (0, 0, 0), .10); h2 = strands((10, 420, 420), (420, 420, 12), (3.1, 1.7, .3), .09); h3 = strands((5, 260, 260), (260, 260, 7), (7.7, 4.2, 2.2), .08)
    hden, _ = t.noise(P, 6.5, 3, .6)
    hairf = t.math('MULTIPLY', t.math('MULTIPLY', t.math('MAXIMUM', h1, t.math('MAXIMUM', h2, h3)), lA), t.math('ADD', .35, t.math('MULTIPLY', t.smooth(hden, .3, .7), .65)))
    c = t.mix(t.math('MULTIPLY', hairf, .62), c, t.mix(fine, (.80, .70, .56), (.62, .50, .38)))
    # --- scurf: dry pale flaking on back and neck
    sf, _ = t.noise(P, 90, 3, .7); sfz, _ = t.noise(P, 5, 3, .6)
    scurf = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(sf, .6, .72), t.smooth(sfz, .45, .7)), t.math('MULTIPLY', t.smooth(up, .0, .8), t.math('SUBTRACT', 1.0, isMuz)))
    c = t.mix(t.math('MULTIPLY', scurf, .45), c, (.70, .60, .50))
    # --- ear veins and thin pink ear skin
    ev = t.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); t.link(t.vmath('ADD', t.mapping(P, (55, 55, 22)), t.vmath('SCALE', t.noise(P, 30, 2, .5)[1], s=.5)), ev.inputs['Vector']); ev.inputs['Scale'].default_value = 1.0
    vein = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(ev.outputs['Distance'], .0, .07)), isEar)
    c = t.mix(t.math('MULTIPLY', isEar, .5), c, (.58, .27, .22))
    c = t.mix(t.math('MULTIPLY', vein, .32), c, (.33, .06, .07))
    # --- dust film and grime in folds
    ao = t.node('ShaderNodeAmbientOcclusion'); ao.samples = 8; ao.inputs['Distance'].default_value = .05; cav = t.math('SUBTRACT', 1.0, ao.outputs['AO'])
    gr, _ = t.noise(P, 3.7, 4, .68, dist=.7); gr2, _ = t.noise(P, 12, 4, .7); gr3, _ = t.noise(P, 37, 3, .7)
    dustf = t.math('MULTIPLY', t.smooth(t.math('ADD', gr, t.math('MULTIPLY', t.math('SUBTRACT', gr3, .5), .3)), .33, .58), t.math('ADD', .35, t.math('MULTIPLY', t.smooth(up, -.2, .8), .65)))
    dustf = t.math('MULTIPLY', dustf, t.math('SUBTRACT', 1.0, isMuz))
    c = t.mix(t.math('MULTIPLY', dustf, .8), c, t.mix(gr2, (.13, .09, .055), (.30, .21, .13)))
    dp, _ = t.noise(P, 2.6, 4, .7, dist=1.2); dp2, _ = t.noise(P, 21, 3, .7)
    dirtp = t.smooth(t.math('ADD', t.math('ADD', dp, t.math('MULTIPLY', t.math('SUBTRACT', dp2, .5), .22)), t.math('MULTIPLY', mG, .35)), .53, .60)
    dirtp = t.math('MULTIPLY', dirtp, t.math('MULTIPLY', t.math('SUBTRACT', 1.0, isMuz), t.math('SUBTRACT', 1.0, isEar)))
    c = t.mix(t.math('MULTIPLY', dirtp, .72), c, t.mix(dp2, (.075, .052, .032), (.17, .12, .075)))
    grime = t.math('ADD', t.math('MULTIPLY', cav, 1.7), t.math('MULTIPLY', t.math('MAXIMUM', crease, 0.0), .0), clamp=True)
    grime = t.math('MULTIPLY', grime, t.math('ADD', .5, gr2))
    c = t.mix(t.math('MULTIPLY', grime, .75), c, (.11, .075, .05))
    # --- dung stains: dark olive-brown smears, drips downwards
    dn, _ = t.noise(t.mapping(P, (30, 30, 5)), 1.0, 3, .65, dist=.6)
    dungf = t.smooth(t.math('ADD', lR, t.math('MULTIPLY', t.math('SUBTRACT', dn, .5), .9)), .5, .78)
    c = t.mix(t.math('MULTIPLY', dungf, .88), c, t.mix(gr3, (.03, .025, .012), (.09, .07, .03)))
    # --- muzzle disc, horn, eye
    mz = t.mix(mid, (.60, .27, .25), (.44, .16, .16)); mz = t.mix(t.math('MULTIPLY', t.smooth(fine, .5, .7), .45), mz, (.24, .11, .11))
    c = t.mix(isMuz, c, mz)
    hs, _ = t.noise(t.mapping(P, (60, 60, 5)), 1.0, 3, .6); hb, _ = t.noise(P, 16, 2, .5)
    hc = t.mix(hs, (.07, .055, .04), (.30, .24, .17)); hc = t.mix(t.smooth(hb, .5, .7), hc, (.45, .37, .27)); c = t.mix(isHorn, c, hc)
    ey = t.mix(t.smooth(lR, .60, .66), t.mix(t.smooth(lR, .3, .8), (.42, .22, .19), (.50, .46, .40)), t.mix(fine, (.10, .045, .018), (.05, .02, .008))); ey = t.mix(t.smooth(lR, .945, .96), ey, (.004, .003, .003))
    c = t.mix(isEye, c, ey)                                                                               # sclera with a red corner, dark brown iris, pupil
    # --- mud: wet dark slop low down, drying to pale cracked cake above; spatter
    mi = t.node('ShaderNodeTexImage'); mi.projection = 'BOX'; mi.projection_blend = .35; mi.image = bpy.data.images.load(str(MUD), check_existing=True)
    t.link(t.mapping(P, (2.9, 2.9, 2.9), (.3, .2, .5)), mi.inputs['Vector']); mlum = t.sep(mi.outputs['Color'])[0]
    di = t.node('ShaderNodeTexImage'); di.projection = 'BOX'; di.projection_blend = .35; di.image = bpy.data.images.load(str(DRY), check_existing=True)
    t.link(t.mapping(P, (4.3, 4.3, 4.3), (.7, .1, .2)), di.inputs['Vector']); dlum = t.sep(di.outputs['Color'])[0]
    mn1, _ = t.noise(P, 5.2, 4, .72, dist=.6); mn2, _ = t.noise(P, 19, 3, .65); mn3, _ = t.noise(P, 60, 3, .65)
    sd, sc_ = t.voronoi(t.vmath('ADD', P, t.vmath('SCALE', t.noise(P, 30, 2, .5)[1], s=.02)), 30, 'F1')
    splat = t.math('MULTIPLY', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(sd, .05, .2)), t.math('GREATER_THAN', t.sep(sc_)[1], .72)), t.math('SUBTRACT', 1.0, t.smooth(pz, .38, .78)))
    mraw = t.math('ADD', t.math('ADD', t.math('MULTIPLY', mG, 1.3), t.math('MULTIPLY', t.math('SUBTRACT', mn1, .5), 1.1)), t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', mn2, .5), .6), t.math('MULTIPLY', t.math('SUBTRACT', mn3, .5), .35)))
    thick = t.math('MULTIPLY', t.smooth(mraw, .74, .92), t.math('ADD', .55, t.math('MULTIPLY', t.smooth(mn2, .3, .6), .45)))
    smear = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(mraw, .30, .72), t.smooth(mn3, .38, .56)), .8)
    mudf = t.math('MAXIMUM', t.math('MAXIMUM', thick, smear), splat); mudf = t.math('MULTIPLY', mudf, t.math('SUBTRACT', 1.0, isEye))
    wet = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(t.math('ADD', mn1, t.math('MULTIPLY', isMuz, .4)), .42, .62), t.math('SUBTRACT', 1.0, t.smooth(pz, .12, .36))), thick)
    wet = t.math('MAXIMUM', wet, t.math('MULTIPLY', t.math('MULTIPLY', thick, t.smooth(t.sepxyz(P)[0], .9, .96)), .85))                              # snout has been rooting: wet
    dryc = t.mix(1.0, di.outputs['Color'], t.mix(mn1, (.30, .24, .18), (.72, .60, .46)), 'MULTIPLY')
    wetc = t.mix(1.0, mi.outputs['Color'], (.95, .85, .75), 'MULTIPLY')
    mudc = t.mix(wet, dryc, wetc)
    c = t.mix(mudf, c, mudc)
    # --- roughness
    r = t.math('ADD', .44, t.math('MULTIPLY', mid, .2)); r = t.math('SUBTRACT', r, t.math('MULTIPLY', t.smooth(big, .5, .8), .1)); r = t.math('ADD', r, t.math('MULTIPLY', hairf, .12))
    r = t.math('ADD', r, t.math('MULTIPLY', scurf, .3)); r = t.math('ADD', r, t.math('MULTIPLY', dustf, .3)); r = t.math('ADD', r, t.math('MULTIPLY', dirtp, .35)); r = t.math('ADD', r, t.math('MULTIPLY', grime, .2)); r = t.math('SUBTRACT', r, t.math('MULTIPLY', isEar, .08))
    r = t.mixf(dungf, r, t.math('ADD', .5, t.math('MULTIPLY', gr3, .35)))
    r = t.mixf(isMuz, r, t.math('ADD', .10, t.math('MULTIPLY', fine, .2))); r = t.mixf(isHorn, r, t.math('ADD', .32, t.math('MULTIPLY', hs, .32))); r = t.mixf(isEye, r, .03)
    r = t.mixf(mudf, r, t.math('ADD', .80, t.math('MULTIPLY', dlum, .18))); r = t.mixf(wet, r, t.math('ADD', .12, t.math('MULTIPLY', mn2, .22)))
    # --- height (metres)
    isNeck = t.math('MULTIPLY', t.math('LESS_THAN', mA, .5), t.smooth(mA, .05, .4))
    h = t.math('MULTIPLY', t.noise(P, 30, 3, .55)[0], .0016)
    h = t.math('ADD', h, t.math('MULTIPLY', mid, .002)); h = t.math('SUBTRACT', h, t.math('MULTIPLY', crease, .0004)); h = t.math('SUBTRACT', h, t.math('MULTIPLY', crease2, .0002))
    h = t.math('SUBTRACT', h, t.math('MULTIPLY', folm, .00025)); h = t.math('ADD', h, t.math('MULTIPLY', hairf, .00055)); h = t.math('ADD', h, t.math('MULTIPLY', scurf, .0004))
    lw, _ = t.noise(t.mapping(P, (5, 5, 75)), 1.0, 2, .5); h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', lw, isLegW), .0012))
    nw, _ = t.noise(t.mapping(P, (60, 7, 10)), 1.0, 2, .5); h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', nw, isNeck), .0035))
    h = t.math('ADD', h, t.math('MULTIPLY', vein, .0007))
    mzb, _ = t.voronoi(P, 130, 'F1'); h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(mzb, 0, .4), isMuz), .0008))
    h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', hs, isHorn), .001))
    ck = t.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); t.link(t.vmath('ADD', P, t.vmath('SCALE', t.noise(P, 25, 2, .5)[1], s=.02)), ck.inputs['Vector']); ck.inputs['Scale'].default_value = 55
    crack = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(ck.outputs['Distance'], .0, .07)), t.math('MULTIPLY', thick, t.math('SUBTRACT', 1.0, wet)))
    c = t.mix(t.math('MULTIPLY', crack, .75), c, (.035, .026, .018))
    pv_, _ = t.voronoi(P, 340, 'F1'); h = t.math('SUBTRACT', h, t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(pv_, .0, .35)), .00035))
    dcl = t.math('MULTIPLY', dungf, t.noise(P, 120, 3, .7)[0]); h = t.math('ADD', h, t.math('MULTIPLY', dcl, .0025))
    mh = t.math('SUBTRACT', t.math('ADD', t.math('MULTIPLY', thick, .005), t.math('ADD', t.math('MULTIPLY', dlum, .006), t.math('MULTIPLY', mlum, .003))), t.math('MULTIPLY', crack, .004))
    h = t.math('ADD', t.math('MULTIPLY', h, t.math('SUBTRACT', 1.0, mudf)), t.math('MULTIPLY', mh, mudf))
    n = t.bump(h, 1.0, 1.0)
    skin = t.math('SUBTRACT', 1.0, t.math('MAXIMUM', t.math('MAXIMUM', isHorn, isEye), t.math('MAXIMUM', mudf, dungf)), clamp=True)
    sss = t.math('MULTIPLY', skin, t.math('ADD', t.math('SUBTRACT', .14, t.math('MULTIPLY', isEar, .17)), t.math('MULTIPLY', mR, .2)), clamp=True)
    t.finish(c, r, n, sss=sss, sss_radius=(.012, .005, .003))
    t.bake['pos'] = P
    BAKE[mat.name] = t.bake; return mat


def carry_barrel(ob):
    """The barrel (belly, flank, ham top, shoulder) is carried by pelvis and spine; thigh/arm chains keep only the leg columns.
    Bone heat alone let the thighs drag the belly and ham skin, which ballooned the hindquarters in the run."""
    me = ob.data; co = co_np(me); legd = np.full(len(co), 1e9)
    for s in (1, -1):
        for pl in ([(.175, s * .218, .43), (.195, s * .218, .31), (.218, s * .218, .185), (.265, s * .218, .05)], [(-.28, s * .218, .43), (-.335, s * .218, .32), (-.42, s * .218, .225), (-.385, s * .218, .05)]): legd = np.minimum(legd, poly_dist(co, pl))
    legness = (1 - ss(.085, .15, legd)) * ss(.52, .40, co[:, 2])
    limb = ('thigh', 'calf', 'foot', 'upperarm', 'lowerarm', 'hand'); cen = [(-.42, 'pelvis'), (-.13, 'spine_01'), (.15, 'spine_02'), (.33, 'spine_03')]
    G = {g.name: g for g in ob.vertex_groups}; names = {g.index: g.name for g in ob.vertex_groups}
    for v in me.vertices:
        L = float(legness[v.index]); moved = 0.0
        for ge in v.groups:
            if names[ge.group].startswith(limb): moved += ge.weight * (1 - L); ge.weight *= L
        if moved > 1e-6:
            x_ = co[v.index, 0]; k = max(0, min(len(cen) - 2, sum(1 for c_ in cen if c_[0] < x_) - 1)); f = float(np.clip((x_ - cen[k][0]) / (cen[k + 1][0] - cen[k][0]), 0, 1))
            for nm, w in ((cen[k][1], 1 - f), (cen[k + 1][1], f)):
                if w > 0: (G.get(nm) or ob.vertex_groups.new(name=nm)).add([v.index], moved * w, 'ADD')


def assemble(coll, arm, body, hard, tris_body):
    """Low game mesh: decimated body + shells, skinned to the rig."""
    low = body.copy(); low.data = body.data.copy(); bpy.context.scene.collection.objects.link(low)
    decimate_to(low, tris_body); clean_mesh(low)
    arm.data.pose_position = 'REST'
    auto_weights(low, arm); carry_barrel(low)
    low_body = low.copy(); low_body.data = low.data.copy()
    hl = []
    for o in hard:
        c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c); hl.append(c)
    hj = join(hl, 'hardlow') if len(hl) > 1 else hl[0]
    if tri_count(hj) > 3600: decimate_to(hj, 3600)
    low = join([low, hj], 'SK_Pig_LOD0')
    for c in list(low.users_collection): c.objects.unlink(low)
    coll.objects.link(low)
    me = low.data; part = np.zeros(len(me.vertices), np.float32); me.attributes['part'].data.foreach_get('value', part); par = np.zeros(len(me.vertices), np.float32); me.attributes['par'].data.foreach_get('value', par)
    part = np.round(part).astype(int)
    rig = {1: 'hand_l', 2: 'hand_r', 3: 'foot_l', 4: 'foot_r', 8: 'head'}
    for k, b in rig.items(): set_rigid(low, np.nonzero(part == k)[0], {b: 1.0})
    for k, b in ((5, 'ear_l'), (6, 'ear_r')):
        for i in np.nonzero(part == k)[0]:
            w = float(np.clip((par[i] - .12) * 2.0, 0, 1)); set_rigid(low, [i], {b: w, 'head': 1 - w} if w < 1 else {b: 1.0})
    for i in np.nonzero(part == 7)[0]:
        a = float(par[i]) * 2.999; k = int(a); f = a - k; names = ['tail_01', 'tail_02', 'tail_03']
        set_rigid(low, [i], {names[k]: 1 - f * .5, names[min(2, k + 1)]: f * .5} if k < 2 else {'tail_03': 1.0})
    for v in me.vertices:
        if not any(g.weight > 1e-5 for g in v.groups): set_rigid(low, [v.index], {'spine_02': 1.0})
    b = get_color_attr(me, 'msk')[:, 2]
    for p in me.polygons:
        v = float(np.mean([b[i] for i in p.vertices])); p.material_index = 3 if v > .85 else (2 if v > .5 else (1 if v > .2 else 0))
    low.parent = arm
    if not any(m.type == 'ARMATURE' for m in low.modifiers): md = low.modifiers.new('Armature', 'ARMATURE'); md.object = arm
    return low, low_body


def build_bristles(low_body, eyes):
    """Sparse coarse bristle cards: flank and back coat lying aft, raised spinal crest, eyelashes. Skinned from the nearest body vertex;
    card normals are the skin normal at the root so the coat shades with the body instead of as separate tabs."""
    from mathutils.kdtree import KDTree
    me = low_body.data; co = co_np(me); n = nrm_np(me); kd = KDTree(len(co)); [kd.insert(co[i], i) for i in range(len(co))]; kd.balance()
    gn = {g.index: g.name for g in low_body.vertex_groups}; order = list(range(len(co))); random.shuffle(order); taken = np.zeros(len(co), bool)
    vs = []; fs = []; uvs = []; wts = []; nrs = []; cnt = [0]
    def quad(p, f, side, nr, L, Wd, lift, cell, w):
        d = (f * math.cos(lift) + nr * math.sin(lift)); o = len(vs); u0 = cell * .25
        vs.extend([p - side * Wd * .5, p + side * Wd * .5, p + side * Wd * .5 + d * L, p - side * Wd * .5 + d * L]); fs.append((o, o + 1, o + 2, o + 3))
        uvs.append([(u0 + .01, 0.01), (u0 + .24, 0.01), (u0 + .24, .99), (u0 + .01, .99)]); wts.extend([w] * 4)
        nn_ = (nr + d * .25).normalized(); nrs.extend([tuple(nr), tuple(nr), tuple(nn_), tuple(nn_)]); cnt[0] += 1
    tris = []; areas = []
    for pl in me.polygons:
        vv = list(pl.vertices)
        for k in range(1, len(vv) - 1):
            a_, b_, c_ = co[vv[0]], co[vv[k]], co[vv[k + 1]]; tris.append((vv[0], vv[k], vv[k + 1])); areas.append(.5 * np.linalg.norm(np.cross(b_ - a_, c_ - a_)))
    areas = np.array(areas); rng = np.random.default_rng(7); pick = rng.choice(len(tris), size=NCARD * 3, p=areas / areas.sum()); made = 0
    for ti in pick:
        if made >= NCARD: break
        ia, ib, ic = tris[ti]; u, v_ = rng.random(), rng.random()
        if u + v_ > 1: u, v_ = 1 - u, 1 - v_
        p = V(co[ia] * (1 - u - v_) + co[ib] * u + co[ic] * v_); nr = V(n[ia] * (1 - u - v_) + n[ib] * u + n[ic] * v_).normalized(); i = (ia, ib, ic)[int(np.argmax((1 - u - v_, u, v_)))]
        if p.z < .37 or p.x > .93 or nr.z < -.3: continue
        if p.z < .5 and rng.random() < .6: continue
        crest = abs(p.y) < .06 and nr.z > .8 and -.66 < p.x < .62
        head = p.x > .55
        if head and (V(eyes[0][0]) - p).length < .035 or (V(eyes[1][0]) - p).length < .035: continue
        flow = V((-1, 0, -.6 * (1 - abs(nr.z)))); f = flow - nr * flow.dot(nr)
        if f.length < 1e-4: continue
        f.normalize(); f = (f + nr.cross(f) * random.uniform(-.12, .12)).normalized(); side = nr.cross(f).normalized()
        w = {gn[g.group]: g.weight for g in me.vertices[i].groups if g.weight > .01}
        if not w: continue
        if head and rng.random() < .55: continue
        made += 1
        if crest and rng.random() < .7: quad(p - nr * .004, f, side, nr, random.uniform(.05, .075), .06, math.radians(random.uniform(28, 50)), 1, w)
        else: quad(p - nr * .003, f, side, nr, random.uniform(.05, .075) * (.6 if head else 1), .065 * (.6 if head else 1), math.radians(random.uniform(7, 16)), random.choice((0, 0, 2, 3)), w)
    for s, (loc, nn) in zip((1, -1), eyes):                                    # lashes on the upper lid
        for k in range(7):
            a = -.9 + k * .3; nrv = V(nn); p = V(loc) + V((.016 * a, 0, .011 - .004 * a * a)) + nrv * .004
            _, j, _ = kd.find(p); w = {gn[g.group]: g.weight for g in me.vertices[j].groups if g.weight > .01}
            quad(p, (nrv + V((.2 * a, 0, -.25))).normalized(), V((1, 0, 0)), V((0, 0, 1)), .024, .016, 0.0, 2, w)
    o = mesh_obj('bristles', vs, fs)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()                 # every card faces out of the skin
    bmesh.ops.reverse_faces(bm, faces=[f_ for f_ in bm.faces if f_.normal.dot(V(nrs[f_.verts[0].index])) < 0]); bm.to_mesh(o.data); bm.free()
    o.data.uv_layers.new(name='UVMap'); uvl = o.data.uv_layers.active.data
    for pl, q in zip(o.data.polygons, uvs):
        base = min(pl.vertices)
        for li in pl.loop_indices: uvl[li].uv = q[o.data.loops[li].vertex_index - base]
    for i, w in enumerate(wts):
        for k, x in w.items():
            g = o.vertex_groups.get(k) or o.vertex_groups.new(name=k); g.add([i], x, 'REPLACE')
    a = o.data.attributes.new('bn', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', np.asarray(nrs, np.float32).ravel())
    log('bristle cards', cnt[0]); return o


def card_normals(low, ci):
    """Custom normals: cards take the stored skin normal, everything else keeps its smooth vertex normal."""
    me = low.data; k = len(me.vertices); bn = np.zeros(k * 3, np.float32); me.attributes['bn'].data.foreach_get('vector', bn); bn = bn.reshape(-1, 3)
    vnn = np.zeros(k * 3, np.float32); me.vertices.foreach_get('normal', vnn); vnn = vnn.reshape(-1, 3)
    use = np.linalg.norm(bn, axis=1) > .5; vnn[use] = bn[use]
    me.normals_split_custom_set_from_vertices([tuple(v) for v in vnn]); me.update()


def bristle_material():
    m = bpy.data.materials.new('MI_Pig_BristleCards'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    def im(suffix, linear):
        x = nt.nodes.new('ShaderNodeTexImage'); x.image = bpy.data.images.load(str(DST / 'Textures' / ('T_Pig_BristleCards' + suffix)), check_existing=True); x.image.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'; return x
    bc = im('_BC.png', False); nt.links.new(bc.outputs[0], b.inputs['Base Color']); nt.links.new(bc.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = .55; b.inputs['Specular IOR Level'].default_value = .25
    # cards cast no shadow (set the same on the Unreal material: no dynamic shadow from the bristle slot)
    out = nt.nodes['Material Output']; mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); lp = nt.nodes.new('ShaderNodeLightPath')
    nt.links.new(lp.outputs['Is Shadow Ray'], mx.inputs[0]); nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    m.use_backface_culling = False; return m


def shots(arm, tag, which, samples=48, scale=1.0):
    R = lambda w, h: (int(w * scale), int(h * scale)); fl = []; D = DST / 'Review'
    if 'game' in which:
        set_action(arm, 'Pig_Idle', 10); f = D / (tag + '_game.png'); shoot(f, game_cam((.1, 0, .5), 6.0, -55, 45), (.1, 0, .5), 105, R(1200, 900), samples); fl.append(f)
    if 'close' in which:
        set_action(arm, 'Pig_Idle', 10); f = D / (tag + '_close.png'); shoot(f, (1.62, -.78, .86), (.70, 0, .66), 45, R(1200, 900), samples); fl.append(f)
    if 'side' in which:
        set_action(arm, 'Pig_Idle', 30); f = D / (tag + '_side.png'); shoot(f, (.1, -3.4, .75), (.1, 0, .55), 60, R(1200, 900), samples); fl.append(f)
    if 'back' in which:
        set_action(arm, 'Pig_Idle', 30); f = D / (tag + '_back.png'); shoot(f, (-1.9, 1.2, .55), (-.25, 0, .5), 45, R(1200, 900), samples); fl.append(f)
    if 'under' in which:
        g = bpy.data.objects['CR_Ground']; g.hide_render = True; set_action(arm, 'Pig_Idle', 30)
        f = D / (tag + '_under.png'); shoot(f, (.3, -.9, -1.4), (0, 0, .4), 40, R(1200, 900), samples, exposure=2.6); fl.append(f); g.hide_render = False
    if 'pose' in which:
        for act, fr, az in (('Pig_Walk', 6, -60), ('Pig_Run', 4, -110), ('Pig_Feed', 7, -40)):
            set_action(arm, act, fr); f = D / ('%s_%s%02d.png' % (tag, act[4:].lower(), fr)); shoot(f, game_cam((.05, 0, .5), 3.6, az, 22), (.05, 0, .5), 55, R(1000, 750), samples); fl.append(f)
    if 'strip' in which:                                                                                  # every second frame of every clip
        for act in ('Pig_Idle', 'Pig_Walk', 'Pig_Run', 'Pig_Feed'):
            a_ = bpy.data.actions[act]; fr = list(range(int(a_.frame_range[0]), int(a_.frame_range[1]) + 1, 6 if act == 'Pig_Idle' else 2))[:10]; tmp = []
            for k in fr:
                set_action(arm, act, k); f = D / ('_strip_%s_%02d.png' % (act, k)); shoot(f, game_cam((0, 0, .45), 4.4, -100, 24), (0, 0, .45), 50, (300, 220), 24); tmp.append(f)
            montage(tmp, D / ('%s_strip_%s.png' % (tag, act[4:].lower())), cols=10)
            for f in tmp: f.unlink()
    if 'lods' in which:
        tmp = []
        for nm in ('SK_Pig_LOD0', 'SK_Pig_LOD1', 'SK_Pig_LOD2'):
            for o in bpy.data.objects:
                if o.name.startswith('SK_Pig_LOD'): o.hide_render = o.name != nm
            set_action(arm, 'Pig_Walk', 6); f = D / ('_lod_%s.png' % nm); shoot(f, game_cam((.1, 0, .5), 6.0, -55, 45), (.1, 0, .5), 105, (600, 450), 64); tmp.append(f)
        montage(tmp, D / (tag + '_lods.png'), cols=3)
        for f in tmp: f.unlink()
        for o in bpy.data.objects:
            if o.name.startswith('SK_Pig_LOD'): o.hide_render = o.name != 'SK_Pig_LOD0'
    set_action(arm, None, 1); return fl


if STAGE in ('look', 'final'):
    coll, arm = open_rig()
    mats = [pigskin(bpy.data.materials.new(n)) for n in MATN]
    body, hard, eyes = build_high(arm)
    for o in [body] + hard:
        for m in mats: o.data.materials.append(m)
    log('high body tris', tri_count(body), 'dims', tuple(round(x, 3) for x in body.dimensions))
    if STAGE == 'look':
        for o in [body] + hard: o.parent = arm
        setup_review(samples=48)
        shots(arm, 'look', A[1].split(',') if len(A) > 1 else ('game', 'close'), 48, .75)
    else:
        res = int(A[1]) if len(A) > 1 else 2048
        high = join([body] + hard, 'PigHigh')
        hc = bpy.data.collections.new('PigHigh_Source'); bpy.context.scene.collection.children.link(hc)
        for c in list(high.users_collection): c.objects.unlink(high)
        hc.objects.link(high)
        body2 = high.copy(); body2.data = high.data.copy(); bpy.context.scene.collection.objects.link(body2)
        bm = bmesh.new(); bm.from_mesh(body2.data); lay = bm.verts.layers.float['part']
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v[lay] > .5], context='VERTS'); bm.to_mesh(body2.data); bm.free()
        hard2 = high.copy(); hard2.data = high.data.copy(); bpy.context.scene.collection.objects.link(hard2)
        bm = bmesh.new(); bm.from_mesh(hard2.data); lay = bm.verts.layers.float['part']
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v[lay] < .5], context='VERTS'); bm.to_mesh(hard2.data); bm.free()
        low, low_body = assemble(coll, arm, body2, [hard2], 9600)
        bpy.data.objects.remove(body2); bpy.data.objects.remove(hard2)
        log('LOD0 triangles before cards', tri_count(low))
        uv = uv_unwrap(low, angle=70, hidden_scale=1.0)
        tex = bake_set(low, DST / 'Textures', 'T_Pig_Atlas', res=res, extra=('sss', 'pos'), source=high, cage=.005, maxray=.02)
        fill_unbaked(tex, tex.pop('_pos'))
        for i, nme in enumerate(MATN):
            old = low.material_slots[i].material; old.name = nme + '_Procedural'; old.use_fake_user = True
            low.material_slots[i].material = game_material(nme, tex, sss=True, sss_scale=1.0, sss_radius=(.012, .005, .003))
        high.hide_render = True; high.hide_viewport = True
        # four slots as before: hooves move to the skin slot (same atlas); MI_Pig_HornBristle now carries only the bristle cards
        for pl in low.data.polygons:
            if pl.material_index == 2: pl.material_index = 0
        low.material_slots[2].material.name = 'MI_Pig_Horn_unused'
        br = build_bristles(low_body, eyes); bmat = bristle_material(); bmat.name = 'MI_Pig_HornBristle'; br.data.materials.append(bmat)
        a = low.data.attributes.new('bn', 'FLOAT_VECTOR', 'POINT')
        low.material_slots[2].material = bmat; ci = 2; nf0 = len(low.data.polygons)
        low = join([low, br], 'SK_Pig_LOD0')
        for pl in low.data.polygons[nf0:]: pl.material_index = ci
        for v in low.data.vertices:
            if not any(g.weight > 1e-5 for g in v.groups): low.vertex_groups['spine_02'].add([v.index], 1.0, 'REPLACE')
        low.parent = arm
        from dinkasset import common, make_lods
        asset = common.Asset(coll); make_lods.make_lods(asset, [.5, .25], replace=True, force=True); asset.refresh()
        for m in asset.renders: clean_mesh(m); limit_weights(m); m.hide_render = m.name != low.name
        card_normals(low, ci)
        (DST / 'pig_build.json').write_text(json.dumps({'uv': uv, 'texture_px': res, 'lods': [{'name': m.name, 'triangles': tri_count(m)} for m in asset.renders], 'dimensions_m': list(low.dimensions), 'high_triangles': tri_count(high)}, indent=1, default=str))
        for im in bpy.data.images:
            if im.filepath and str(DST / 'Textures') in bpy.path.abspath(im.filepath): im.filepath = '//Textures/' + Path(im.filepath).name
        bpy.ops.wm.save_as_mainfile(filepath=str(DST / 'SK_Pig.blend'), relative_remap=False); log('FINAL SAVED')
if STAGE == 'review':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Pig.blend')); arm = bpy.data.objects['Armature']
    sm = int(A[3]) if len(A) > 3 else 128; setup_review(samples=sm, ground='dirt'); shots(arm, A[1], A[2].split(','), sm)
if STAGE == 'export':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Pig.blend')); arm = bpy.data.objects['Armature']
    for o in list(bpy.data.objects):
        if o.name == 'PigHigh': bpy.data.objects.remove(o)
    export_skeletal('SK_Pig', arm, DST / 'Export', {'Idle': 'Pig_Idle', 'Walk': 'Pig_Walk', 'Run': 'Pig_Run', 'Feed': 'Pig_Feed'}, 'A_Pig', 30, DST / 'pig_validation.json')
