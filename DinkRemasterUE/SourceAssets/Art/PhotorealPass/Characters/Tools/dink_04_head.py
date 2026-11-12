"""Stage 4: head geometry work: asymmetry and ears, new eyeballs with cornea bulge, brow/lash cards, layered hair cards.
Writes Work/dink_head.blend with objects Skin, Eyes, Hair (all with final UVs except Skin, which is repacked in stage 5)."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *
CFG = dict(src='Dink/Work/dink_base.blend', out='Dink/Work/dink_head.blend', work_src='Dink/Dink_Working.blend', seed=5,
           ear_out=10.0, hair_len=1.0, review='Dink/Review')
if args(): CFG.update(json.loads(Path(args()[0]).read_text()))
bpy.ops.wm.open_mainfile(filepath=str(OUT / CFG['src']))
D = bpy.data.objects; rng = np.random.default_rng(CFG['seed'])
sk = D['Skin']; me = sk.data; co = co_np(me)
head = co[:, 2] > 1.40
hc = co[head]
mid = np.abs(hc[:, 0]) < .008
nose = hc[mid][np.argmin(hc[mid][:, 1])]
top = hc[:, 2].max(); back = hc[:, 1].max()
log('nose tip', nose.round(4), 'top', top, 'back y', back, 'half width', np.abs(hc[:, 0]).max())
# ---- eyes: fit spheres to the old eyeballs
oe = co_np(D['OldEyes'].data); eyes = {}
for sgn in (1, -1):
    P = oe[oe[:, 0] * sgn > 0]
    A_ = np.c_[2 * P, np.ones(len(P))]; b_ = (P ** 2).sum(1); x, *_ = np.linalg.lstsq(A_, b_, rcond=None)
    c = x[:3]; r = math.sqrt(x[3] + c @ c); eyes[sgn] = (c, r)
    log('eye', sgn, c.round(4), round(r, 4), 'front y', P[:, 1].min())
# ---- asymmetry + ears (head only, small)
W = np.zeros(len(co)); W[head] = 1
warp = np.stack([fbm(co, 14, 2, 61 + k) - .5 for k in range(3)], 1) * .0028
warp *= sstep(1.52, 1.60, co[:, 2])[:, None]      # leave the neck border alone
co2 = co + warp
ez = nose[2]
ear = head & (np.abs(co[:, 0]) > .0715) & (co[:, 2] > ez - .035) & (co[:, 2] < ez + .055) & (co[:, 1] > nose[1] + .075)
log('ear verts', int(ear.sum()))
for sgn in (1, -1):
    m = ear & (co[:, 0] * sgn > 0)
    if not m.any(): continue
    P = co2[m]; root = np.array([sgn * .0715, P[:, 1].min(), P[:, 2].mean()])
    a = math.radians(CFG['ear_out'] * (1.15 if sgn > 0 else .9)) * sgn
    R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    w = sstep(.0715, .080, np.abs(co[m][:, 0]))[:, None]
    co2[m] = P * (1 - w) + (((P - root) * 1.07) @ R.T + root) * w
def blobw(c, r): return np.exp(-(((co[:, 0] - c[0]) / r) ** 2 + ((co[:, 1] - c[1]) / r) ** 2 + ((co[:, 2] - c[2]) / r) ** 2)) * head
set_co(me, co2); me.update(); vn0 = normals_np(me)
FS = CFG.get('face_shape', dict(brow=.0016, jaw=.003, chin=.002, cheek=-.0012))
ezz = eyes[1][0][2]
for sgn in (1, -1):
    co2 = co2 + vn0 * (blobw((sgn * .032, nose[1] + .028, ezz + .022), .018) * FS['brow'])[:, None]
    co2 = co2 + vn0 * (blobw((sgn * .058, nose[1] + .085, nose[2] - .078), .026) * FS['jaw'])[:, None]
    co2 = co2 + vn0 * (blobw((sgn * .05, nose[1] + .045, nose[2] - .03), .022) * FS['cheek'])[:, None]
co2 = co2 + vn0 * (blobw((0, nose[1] + .03, nose[2] - .088), .022) * FS['chin'])[:, None]
for sgn in (1, -1):   # optional ageing forms: jowls, under-eye bags, a soft under-chin
    co2 = co2 + vn0 * (blobw((sgn * .040, nose[1] + .050, nose[2] - .078), .017) * FS.get('jowl', 0))[:, None]
    co2 = co2 + vn0 * (blobw((sgn * eyes[1][0][0], eyes[1][0][1] - .012, ezz - .017), .010) * FS.get('eyebag', 0))[:, None]
co2 = co2 + vn0 * (blobw((0, nose[1] + .060, nose[2] - .112), .030) * FS.get('neck', 0))[:, None]
set_co(me, co2); co = co2
co_pre = co.copy()
if CFG.get('face2'):   # landmark-relative reshape (bone structure, soft tissue, expression asymmetry); see facelib
    import facelib; me.update()
    co = facelib.reshape(co, normals_np(me), nose, eyes, CFG['face2'], head.astype(float), log); set_co(me, co)
    _mid = np.abs(co[:, 0]) < .008; _hc = co[head & _mid]; nose = _hc[np.argmin(_hc[:, 1])]
kd_pre = KDTree(len(co_pre))
for i_, p_ in enumerate(co_pre): kd_pre.insert(p_, i_)
kd_pre.balance(); disp_pre = co - co_pre
def follow_face(c_):
    out_ = c_.copy()
    for i_, p_ in enumerate(c_):
        nb = kd_pre.find_n(p_, 4); w_ = np.array([1 / (d_ + 1e-4) for _, _, d_ in nb]); out_[i_] = p_ + (disp_pre[[j_ for _, j_, _ in nb]] * w_[:, None]).sum(0) / w_.sum()
    return out_
# ---- eyeballs
def eyeball(sgn, nseg=20, nring=14):
    c, r = eyes[sgn]; r = r * 1.0
    verts = []; faces = []; uvs = []
    fwd = np.array([-.03 * sgn * -1, -1, 0.0]); fwd /= np.linalg.norm(fwd)   # tiny divergence, as real eyes have
    xa = np.cross([0, 0, 1.0], fwd); xa /= np.linalg.norm(xa); za = np.cross(fwd, xa)
    for i in range(nring + 1):
        th = math.pi * (i / nring) ** 1.25 * .93           # denser at the front, open at the back
        bulge = .0013 * (1 - sstep(.30, .56, th)) + 0
        rr = r + bulge * (.5 + .5 * math.cos(min(th / .56, 1) * math.pi)) * 1.6
        for j in range(nseg):
            ph = 2 * math.pi * j / nseg
            d = fwd * math.cos(th) + (xa * math.cos(ph) + za * math.sin(ph)) * math.sin(th)
            verts.append(c + d * rr)
            rad = min(th / math.radians(105) * .5, .495)
            uvs.append((.5 + rad * math.cos(ph) * sgn, .5 + rad * math.sin(ph)))
    for i in range(nring):
        for j in range(nseg):
            a = i * nseg + j; b = i * nseg + (j + 1) % nseg; faces.append((a, b, b + nseg, a + nseg))
    o = new_obj('Eye_%d' % sgn, verts, faces)
    uv = o.data.uv_layers.new(name='UVMap')
    for p in o.data.polygons:
        for li, vi in zip(p.loop_indices, p.vertices): uv.data[li].uv = uvs[vi]
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    smooth_shade(o); return o
ey = join([eyeball(1), eyeball(-1)], 'Eyes')
# ---- brows and lashes: CC0 MakeHuman cards, remapped into the bottom band of the hair atlas
with bpy.data.libraries.load(str(CHARS / CFG['work_src'])) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith('Human.eyebrow') or n.startswith('Human.eyelashes')]
bl = []
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)
    uvl = o.data.uv_layers[0]; uv = np.empty(len(o.data.loops) * 2, np.float32); uvl.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    brow = 'eyebrow' in o.name
    # atlas bottom band: v in [0, 0.25]; brows left half, lashes right half
    uv[:, 0] = uv[:, 0] * .5 + (0 if brow else .5); uv[:, 1] = uv[:, 1] * .25
    uvl.data.foreach_set('uv', uv.ravel()); uvl.name = 'UVMap'
    o.data.materials.clear(); o['kind'] = 'brow' if brow else 'lash'
    set_co(o.data, follow_face(co_np(o.data)))
    if brow:   # sit the brow cards a hair above the skin
        o.data.update(); c_ = co_np(o.data); set_co(o.data, c_ + normals_np(o.data) * .0006)
    bl.append(o)
    if brow and CFG.get('brow_double', True):
        o2 = dup(o, o.name + '_b'); c_ = co_np(o2.data); cx = c_.mean(0)
        c_2 = c_.copy(); c_2[:, 2] = cx[2] + (c_[:, 2] - cx[2]) * 1.5 - .0012; c_2[:, 1] -= .0005
        set_co(o2.data, c_2); o2['kind'] = 'brow'; bl.append(o2)
# ---- hair: undercoat cap + layered card groom
hbvh = bvh_of(sk)
ctr = np.array([0, (nose[1] + back) / 2 + .012, top - .105])
HL = CFG.get('hairline', (.50, .14, -.52))
def hairline(d):
    """minimum elevation (sin) for scalp at azimuth; d unit vector from head centre."""
    a = abs(math.atan2(d[0], -d[1])); front, side, backv = HL
    if a < 1.15: t = a / 1.15; t = t * t * (3 - 2 * t); return front + (side - front) * t
    t = (a - 1.15) / (math.pi - 1.15); t = t * t * (3 - 2 * t); return side + (backv - side) * t
def params(p):
    d = np.asarray(p) - ctr; d = d / np.linalg.norm(d); az = math.atan2(d[0], -d[1])
    return az, (1 - d[2]) / (1 - hairline(d))          # e: 0 at the top of the skull, 1 on the hairline
CAPB = None
if CFG.get('groom') == 'bun':   # combed-back cap: strands of the cap tile run from the hairline to the bun
    _b = np.array(CFG.get('bun', {}).get('dir', (0, .80, .60))); _b = _b / np.linalg.norm(_b)
    _l, _n, _, _ = hbvh.find_nearest(Vector(ctr + _b * .25)); _ps = np.array(_l); _bn = np.array(_n)
    _bx = np.cross([0, 0, 1.0], _bn); _bx /= np.linalg.norm(_bx); CAPB = (_ps, _bx, np.cross(_bn, _bx))
me.calc_loop_triangles(); tris = []
vn = normals_np(me)
capv = {}; capf = []; capuv = []
for t in me.loop_triangles:
    idx = list(t.vertices); P = co[idx]; c = P.mean(0)
    if c[2] < 1.55: continue
    az, e = params(c); d = (c - ctr) / np.linalg.norm(c - ctr)
    if t.normal.dot(Vector(d)) < .2: continue
    if e <= 1.0: tris.append((P, t.area, c, az, e))
    if e <= CFG.get('cap_e', 1.10):
        f = []
        azs = [params(co[i])[0] for i in idx] if CAPB is None else [math.atan2((co[i] - CAPB[0]) @ CAPB[2], (co[i] - CAPB[0]) @ CAPB[1]) for i in idx]
        if max(azs) - min(azs) > math.pi: azs = [a_ + 2 * math.pi if a_ < 0 else a_ for a_ in azs]
        for i, a_ in zip(idx, azs):
            f.append(len(capuv)); e_i = params(co[i])[1]; ee = min(e_i, 1.10) / 1.10 if CAPB is None else min(np.linalg.norm(co[i] - CAPB[0]) / .25, 1.0) * .76
            if CAPB is not None: w_h = float(sstep(.80, 1.0, e_i)); ee = ee * (1 - w_h) + (.80 + .16 * min(max((e_i - .80) / .2, 0), 1)) * w_h    # ragged strand-level alpha along the hairline
            capv[len(capuv)] = co[i] + vn[i] * (.0032 if 'cap_lift' not in CFG else CFG['cap_lift'] * (1 - .8 * min(max(e_i, 0), 1) ** 3) + .0012)
            capuv.append((min(max(.004 + .242 * (a_ / (2 * math.pi) + .5), .003), .247), .622 - ee * .366))
        capf.append(f)
areas = np.array([t[1] for t in tris]); log('scalp tris', len(tris), 'area', areas.sum(), 'cap tris', len(capf))
crown = np.array([.012, ctr[1] + .05, top])
verts = [capv[i] for i in range(len(capuv))]; faces = list(capf); uvs = list(capuv); cols = [1.0] * len(capuv); layers_v = [1] * len(capuv); nrms = []
DENSE = [0, 1, 2, 3, 4, 5, 6, 7, 10, 11]; THIN = [12, 13]; FLY = [14, 15]
SW = CFG.get('sweep', 1.0); FLOW_TO = None; LV = CFG.get('volume', 1.0)
def add_card(root, L, width, lift0, lift1, strips, hl_layer, nseg=5, jitter=.12, sweep_k=1.0, gravity=.25):
    loc, nrm, _, _ = hbvh.find_nearest(Vector(root)); p = np.array(loc); n = np.array(nrm)
    az, e = params(p); d0 = (p - ctr) / np.linalg.norm(p - ctr)
    flow = (p - crown) * 1.0 + np.array([0, 0, -.06])
    if FLOW_TO is not None: flow = FLOW_TO - p
    flow -= n * (flow @ n); flow /= max(np.linalg.norm(flow), 1e-9)
    around = np.cross(n, flow)
    frontness = max(0, -d0[1]) ** 1.3
    flow = flow + around * SW * sweep_k * (.22 + .85 * frontness) + rng.normal(0, jitter, 3)
    flow -= n * (flow @ n); flow /= np.linalg.norm(flow)
    strip = int(rng.choice(strips)); roll = rng.normal(0, .14) * (CFG.get('crown_roll', 1.0) if hl_layer == 3 else 1.0)
    cur = p.copy(); dirv = flow.copy(); base = len(verts)
    for k in range(nseg + 1):
        t = k / nseg
        loc, nrm, _, dist = hbvh.find_nearest(Vector(cur)); sp = np.array(loc); sn = np.array(nrm)
        _, ee = params(sp)
        over = max(0.0, ee - 1.0)
        lift = lift0 + (lift1 - lift0) * t ** 1.3 + over * .035      # past the hairline it hangs clear of the face
        q = sp + sn * lift
        w = np.cross(sn, dirv); w /= max(np.linalg.norm(w), 1e-9)
        w = w * math.cos(roll) + sn * math.sin(roll)
        hw = width / 2 * (1 - .25 * t ** 2)
        for a, bow in ((-1, 0), (0, width * .09), (1, 0)):
            verts.append(q + w * a * hw + sn * bow)
            u0 = (strip % 8) / 8; v1 = 1 - (strip // 8) * .375
            uvs.append((u0 + (.5 + a * .47) / 8, v1 - t * .372 - .0015))
            cols.append(1.0); layers_v.append(hl_layer)
        dirv = dirv - sn * (dirv @ sn); dirv /= np.linalg.norm(dirv)
        dirv = dirv + np.array([0, 0, -gravity]) * t + rng.normal(0, .05, 3); dirv /= np.linalg.norm(dirv)
        if FLOW_TO is not None:
            tg_ = FLOW_TO - sp; tg_ -= sn * (tg_ @ sn); tl_ = np.linalg.norm(tg_)
            if tl_ > .02: dirv = dirv * .45 + tg_ / tl_ * .55; dirv /= np.linalg.norm(dirv)
        cur = sp + dirv * (L / nseg)
    for k in range(nseg):
        for a in range(2):
            i0 = base + k * 3 + a; faces.append((i0, i0 + 1, i0 + 4, i0 + 3))
taz = np.array([t[3] for t in tris]); te = np.array([t[4] for t in tris])
def roots(n, e0, e1, azmax=4.0, azmin=0.0):
    m = (te >= e0) & (te <= e1) & (np.abs(taz) <= azmax) & (np.abs(taz) >= azmin)
    if not m.any(): return []
    idx = np.nonzero(m)[0]; pick = rng.choice(idx, n, p=areas[idx] / areas[idx].sum()); out = []
    for i in pick:
        P = tris[i][0]; r1, r2 = rng.random(2)
        if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
        out.append(P[0] + (P[1] - P[0]) * r1 + (P[2] - P[0]) * r2)
    return out
K = CFG.get('hair_len', 1.0); G = CFG.get('groom', 'short'); DN = CFG.get('density', 1.0)
if G == 'short':
    # the cut, from the bottom layer up; hl attribute: 1 undercoat+nape, 2 mid, 3 top, 5 fringe/wisps/flyaways
    for r in roots(int(95 * DN), .74, 1.0, azmin=.9): add_card(r, K * rng.uniform(.045, .06), rng.uniform(.026, .036), .0025, .006, DENSE, 1)                 # nape and sides, over the ear tops
    for r in roots(int(120 * DN), .42, .82): add_card(r, K * rng.uniform(.06, .075), rng.uniform(.028, .038), .004, .010, DENSE, 2)                           # mid
    for r in roots(int(100 * DN), .05, .50): add_card(r, K * rng.uniform(.07, .09), rng.uniform(.028, .040), .006, .015, DENSE, 3, jitter=.2)                 # top, tousled
    for r in roots(int(55 * DN), .50, .97, azmax=1.0): add_card(r, K * rng.uniform(.05, .068), rng.uniform(.022, .032), .005, .013, DENSE, 5, sweep_k=1.6)    # side-swept fringe
    for r in roots(int(90 * DN), .90, 1.0): add_card(r, K * rng.uniform(.018, .032), rng.uniform(.010, .016), .0015, .005, THIN, 5, nseg=3, jitter=.2)        # soft hairline wisps
    for r in roots(int(CFG.get('fly', 26) * DN), .05, .9): add_card(r, K * rng.uniform(.05, .08), rng.uniform(.014, .02), .010 * CFG.get('fly_lift', 1.0), .028 * CFG.get('fly_lift', 1.0), FLY, 5, nseg=4, jitter=.35)             # flyaways
elif G == 'tied':   # long hair drawn back to a knot at the nape, stray strands at the temples
    crown = np.array([0, nose[1] - .01, top - .02])     # flow runs from the forehead back
    SW = 0.0
    for r in roots(150, .55, 1.0): add_card(r, rng.uniform(.07, .10), rng.uniform(.028, .038), .0025, .005, DENSE, 1, gravity=.0)
    for r in roots(130, .0, .65): add_card(r, rng.uniform(.08, .11), rng.uniform(.028, .038), .004, .008, DENSE, 2, gravity=.0)
    for r in roots(70, .88, 1.0): add_card(r, rng.uniform(.02, .035), rng.uniform(.010, .016), .0015, .004, THIN, 5, nseg=3, jitter=.2)
    for r in roots(16, .7, 1.0, azmax=1.4): add_card(r, rng.uniform(.06, .11), rng.uniform(.012, .018), .006, .02, FLY, 5, jitter=.3, gravity=.9)
else:   # 'bun': hair drawn up and back into a coiled bun high on the back of the head, with body over the crown
    BN = CFG.get('bun', {}); bd_ = np.array(BN.get('dir', (0, .80, .60))); bd_ = bd_ / np.linalg.norm(bd_)
    loc, nrm, _, _ = hbvh.find_nearest(Vector(ctr + bd_ * .25)); ps = np.array(loc); bn = np.array(nrm)
    FLOW_TO = ps; SW = 0.0
    nc = BN.get('cards', (120, 100, 60, 12))
    for r in roots(nc[0], .45, .97): add_card(r, rng.uniform(.11, .16), rng.uniform(.034, .046), .0025 * LV, .006 * LV, THIN, 1, gravity=.0, jitter=.05, nseg=8)
    for r in roots(nc[1], .0, .62): add_card(r, rng.uniform(.10, .14), rng.uniform(.034, .046), .004 * LV, .009 * LV, THIN, 2, gravity=.0, jitter=.06, nseg=7)
    for r in roots(nc[2], .90, 1.0): add_card(r, rng.uniform(.13, .18), rng.uniform(.030, .042), .002 * LV, .0075 * LV, THIN, 3, gravity=.0, jitter=.04, nseg=9)   # from the hairline all the way back
    for r in roots(BN.get('wisps', nc[2] // 2), .93, 1.0): add_card(r, rng.uniform(.012, .022), rng.uniform(.008, .013), .001, .003, THIN, 5, nseg=3, jitter=.15)
    FLOW_TO = None; crown = np.array([0, nose[1] - .01, top - .02])
    for r in roots(nc[3], .7, 1.0, azmax=1.5): add_card(r, rng.uniform(.05, .10), rng.uniform(.012, .018), .006, .02, FLY, 5, jitter=.3, gravity=.9)
    # the bun: an opaque core in the combed cap tile, wrapped by coiled card bands
    R3 = np.array(BN.get('r', (.047, .040, .034))); bc = ps + bn * (R3[2] * .62)
    bx = np.cross([0, 0, 1.0], bn); bx /= np.linalg.norm(bx); by = np.cross(bn, bx)
    NS, NRg = 14, 6; base = len(verts)
    for i in range(NRg + 1):
        la = math.pi * (.5 - .96 * i / NRg)            # from the outer pole in to the scalp
        for j in range(NS + 1):
            az = 2 * math.pi * j / NS; wob = 1 + .06 * math.sin(3 * az + i)
            verts.append(bc + bn * R3[2] * math.sin(la) + (bx * R3[0] * math.cos(az) + by * R3[1] * math.sin(az)) * math.cos(la) * wob)
            uvs.append((.02 + .21 * i / NRg, .37 + .24 * j / NS)); cols.append(1.0); layers_v.append(1)
    for i in range(NRg):
        for j in range(NS):
            a = base + i * (NS + 1) + j; faces.append((a, a + 1, a + NS + 2, a + NS + 1))
    def band(lat0, tilt, width, strip, lift, turns=1.0, ph0=0.0, layer=2, nseg=16):
        b0 = len(verts)
        for k in range(nseg + 1):
            t = k / nseg; az = ph0 + 2 * math.pi * turns * t; la = lat0 + tilt * math.sin(az + ph0)
            def pt(l_): return bc + bn * (R3[2] + lift) * math.sin(l_) + (bx * (R3[0] + lift) * math.cos(az) + by * (R3[1] + lift) * math.sin(az)) * math.cos(l_)
            for a, bow in ((-1, 0), (0, .0025), (1, 0)):
                q = pt(la + a * width / (2 * R3[0])); c_ = pt(la); q = q + (c_ - bc) / np.linalg.norm(c_ - bc) * bow
                verts.append(q); u0 = (strip % 8) / 8; v1 = 1 - (strip // 8) * .375
                uvs.append((u0 + (.5 + a * .47) / 8, v1 - (.04 + .84 * t) * .372 - .0015)); cols.append(1.0); layers_v.append(layer)
        for k in range(nseg):
            for a in range(2):
                i0 = b0 + k * 3 + a; faces.append((i0, i0 + 1, i0 + 4, i0 + 3))
    for q_ in range(BN.get('bands', 9)):
        band(rng.uniform(-.25, 1.05), rng.uniform(-.25, .25), rng.uniform(.030, .042), int(rng.choice(DENSE)), rng.uniform(.002, .006), turns=rng.uniform(.55, .95), ph0=rng.uniform(0, 6.28), layer=2 if q_ % 2 else 3)
hair = new_obj('Hair', verts, faces)
uv = hair.data.uv_layers.new(name='UVMap')
for p in hair.data.polygons:
    for li, vi in zip(p.loop_indices, p.vertices): uv.data[li].uv = uvs[vi]
hla = hair.data.attributes.new('hl', 'FLOAT', 'POINT'); hla.data.foreach_set('value', np.array(layers_v, np.float32))
ca = hair.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set('color', np.array([[c, c, c, 1] for c in cols], np.float32).ravel())
smooth_shade(hair)
hair['custom_normals'] = 1
nrm_arr = np.zeros((0, 3))
# brows/lashes join the hair object (one alpha slot)
for o in bl:
    n = len(o.data.vertices); kind = o['kind']
    h2 = o.data.attributes.new('hl', 'FLOAT', 'POINT'); h2.data.foreach_set('value', np.full(n, 4, np.float32))
    c2 = o.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); v = .55 if kind == 'brow' else .25
    c2.data.foreach_set('color', np.array([[v, v, v, 1]] * n, np.float32).ravel())
    o.data.update(); nrm_arr = np.concatenate([nrm_arr, normals_np(o.data)])
for l in list(hair.data.uv_layers):
    pass
hair = join([hair] + bl, 'Hair')
pass  # card normals stay geometric: custom normals did not survive the slot join and shaded the cards black
log('hair tris', tri_count(hair), 'eyes tris', tri_count(ey), 'skin tris', tri_count(sk))
for nm in ('OldHair', 'OldEyes', 'BrowLash'): bpy.data.objects.remove(D[nm], do_unlink=True)
Path(OUT / CFG['out']).parent.mkdir(parents=True, exist_ok=True)
json.dump({'nose': nose.tolist(), 'top': float(top), 'back': float(back), 'ctr': ctr.tolist(), 'eyes': {str(k): [v[0].tolist(), v[1]] for k, v in eyes.items()}}, open(str(OUT / CFG['out']) + '.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / CFG['out']))
