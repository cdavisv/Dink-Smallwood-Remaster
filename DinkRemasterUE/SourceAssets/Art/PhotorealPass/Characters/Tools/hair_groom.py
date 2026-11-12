"""Stage 4b: strand groom -> card atlas -> game hair cards, plus the strand-vs-card comparison render.
usage: blender -b -t 4 --python hair_groom.py -- <Name> [steps] [tag]
steps (comma list): atlas (re-render the card atlas), strands (re-render the strand reference), cards (re-render the cards),
                    save (write Hair into the head blend + the groom blend). Default: atlas,strands,cards,save
Reads <Name>/Work/<name>_head.blend (Skin, Eyes, old Hair with brow/lash cards); writes the new 'Hair' object back into it,
<Name>/Work/<name>_groom.blend (scalp, guide Curves with the procedural hair modifiers, cards) and T_<Name>_PR_Hair_*."""
import bpy, sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import sstep, fbm, vnoise
import hairlib as hl; import matlib
from hair_styles import STYLES
a = args(); N = a[0]; steps = (a[1] if len(a) > 1 else 'atlas,strands,cards,save').split(','); tag = a[2] if len(a) > 2 else 'h1'
n_ = N.lower(); S = STYLES[N]; rng = np.random.default_rng(S.get('seed', 1))
head_blend = OUT / N / 'Work' / (n_ + '_head.blend'); TX = OUT / N / 'Textures'; PRE = TX / ('T_%s_PR' % N); REV = OUT / N / 'Review'
bpy.ops.wm.open_mainfile(filepath=str(head_blend)); D = bpy.data.objects; sc = bpy.context.scene
LM = json.load(open(str(head_blend) + '.json')); sk = D['Skin']
H = hl.Head(sk, LM, S.get('hairline', (.50, .14, -.52)))
for o_ in D:
    if o_.type == 'MESH' and o_.name not in ('Skin', 'Eyes', 'Hair') and not o_.name.startswith('Old'): o_.hide_render = True
# keep the brow / lash cards (layer 4) of the previous Hair object
old = D.get('Hair'); browlash = None
if old is not None:
    hv = np.zeros(len(old.data.vertices), np.float32)
    if old.data.attributes.get('hl') is not None: old.data.attributes['hl'].data.foreach_get('value', hv)
    bm = bmesh.new(); bm.from_mesh(old.data); bm.verts.ensure_lookup_table()
    uvl_ = bm.loops.layers.uv.active
    dead = set(v for v in bm.verts if abs(hv[v.index] - 4) > .1)
    for f in bm.faces:      # brows (left half of the band) are rebuilt from a strand groom below; the lash cards stay
        if all(l[uvl_].uv.x < .5 for l in f.loops): dead.update(f.verts)
    bmesh.ops.delete(bm, geom=list(dead), context='VERTS'); bm.to_mesh(old.data); bm.free()
    if old.data.attributes.get('hn') is not None: old.data.attributes.remove(old.data.attributes['hn'])
    old.name = 'BrowLash'; browlash = old; log('brow/lash verts kept', len(old.data.vertices))
scalp = hl.build_scalp(H, split_part=S.get('part_split', False), seed=S.get('seed', 1), fade=S.get('fade', .90))
RT = hl.Roots(H, scalp, rng); log('scalp area m2', round(float(RT.total), 4))
# ------------------------------------------------------------------ guide fields
crown = np.array([S.get('crown_x', .012), H.ctr[1] + S.get('crown_y', .05), H.top])
JS = 1.0
def guide_short(root, r, kind='hair'):
    loc, nrm = H.near(root); az, e = H.params(loc); d0 = hl.unit(loc - H.ctr); front = max(0.0, -d0[1])
    flow = loc - crown + np.array([0, 0, -.03]); flow = hl.unit(flow - nrm * (flow @ nrm)); around = np.cross(nrm, flow)
    flow = hl.unit(flow + around * 1.6 * float(sstep(.045, .0, np.linalg.norm(loc - crown))))     # the crown whorl
    around = np.cross(nrm, flow)
    flow = flow + around * S['sweep'] * (.2 + .9 * front ** 1.3)
    ang = (hl.f1(loc, S.get('tousle_scale', 38), 77 + S.get('seed', 1)) - .5) * 2 * S['tousle'] * (.5 + .5 * JS) + r.normal(0, S.get('jit', .12)) * JS
    flow = hl.unit(flow - nrm * (flow @ nrm)); around = np.cross(nrm, flow); flow = flow * math.cos(ang) + around * math.sin(ang)
    top_w = float(sstep(.80, .30, e)); back = max(0.0, d0[1]); fringe = float(sstep(.45, .70, e)) * float(sstep(1.1, .7, abs(az)))
    L = S['L_side'] + (S['L_top'] - S['L_side']) * top_w; L = L + (S['L_nape'] - L) * float(sstep(.75, 1.0, e)) * float(sstep(.2, .7, back)); L = L + (S['L_fringe'] - L) * fringe
    L *= (.8 + .4 * hl.f1(loc, 60, 91)) * r.uniform(.9, 1.08) * (1 - S.get('edge_short', 0.0) * float(sstep(.8, 1.0, e)) * (1 - fringe))
    el = math.radians(S['el_side'] + (S['el_top'] - S['el_side']) * top_w + r.normal(0, S.get('el_jit', 8)))
    ml = (.0006, S['lift_tip'] * (1 + 1.2 * fringe))
    if kind == 'wisp': L *= r.uniform(.25, .5); el *= .6; ml = (.0004, .002)
    if kind == 'fly': L *= r.uniform(.6, .9); el += math.radians(r.uniform(8, 22))
    return hl.grow(H, loc + nrm * .0004, flow * math.cos(el) + nrm * math.sin(el), L, K=S.get('K', 9), gravity=S['gravity'], minlift=ml, wander=S.get('wander', .05), rng=r)
bun = None
if S['kind'] == 'bun':
    bd = hl.unit(np.array(S['bun_dir'])); ps, bn = H.near(H.ctr + bd * .25); bx = hl.unit(np.cross([0, 0, 1.0], bn)); by = np.cross(bn, bx)
    bun = dict(ps=ps, bn=bn, bx=bx, by=by, c=ps + bn * S['bun_r'][2] * .55)
def guide_bun(root, r, kind='hair'):
    loc, nrm = H.near(root); az, e = H.params(loc); d0 = hl.unit(loc - H.ctr)
    tg = bun['ps'] - loc; dist = np.linalg.norm(tg); tg = hl.unit(tg - nrm * (tg @ nrm))
    # from the centre parting the hair first runs sideways, then back
    partw = (.3 + .7 * (JS == 1.0)) * float(sstep(S.get('part_w', .014), .0, abs(loc[0]))) * float(sstep(H.ctr[1] + .02, H.ctr[1] - .02, loc[1]))
    lat = np.array([1.0 if loc[0] >= 0 else -1.0, 0, 0]); lat = hl.unit(lat - nrm * (lat @ nrm))
    d = hl.unit(tg * (1 - .5 * partw) + lat * .8 * partw + r.normal(0, S.get('jit', .05), 3))
    if kind == 'wisp':   # loose strands that escaped the bun: hang from the temples and nape
        dn = np.array([0, -.25 if d0[1] < 0 else .2, -1.0]); return hl.grow(H, loc + nrm * .0005, hl.unit(dn + nrm * .5), r.uniform(.05, .11), K=10, gravity=.9, minlift=(.0008, .006), wander=.10, rng=r, wave=(.25, 9.0, r.uniform(0, 6)))
    Km = 34; g = hl.grow(H, loc + nrm * .0005, d, .012 * (Km - 1), K=Km, gravity=0.0, minlift=(.0008, S['lift_tip'] * r.uniform(.5, 1.0)), maxlift=(.0015, S['lift_tip'] * 1.6), wander=S.get('wander', .01), rng=r, target=bun['c'], pull=.35, stop_r=S['bun_r'][0] * .6)
    seg = np.linalg.norm(np.diff(g, axis=0), axis=1); last = int(np.nonzero(seg > 1e-6)[0].max()) + 1 if (seg > 1e-6).any() else 1
    g = g[:last + 1]; cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(g, axis=0), axis=1))]; K_ = S.get('K', 16); ti = np.linspace(0, cum[-1], K_)
    return np.stack([np.interp(ti, cum, g[:, a_]) for a_ in range(3)], 1)
guide = guide_short if S['kind'] == 'short' else guide_bun
# ------------------------------------------------------------------ strand groom (hair Curves + procedural hair node groups)
gr = np.random.default_rng(S.get('seed', 1) + 100)
roots = RT.sample(S['guides'], 0, 1.0)
G = np.array([guide(p, gr) for p, _ in roots]); UVr = np.array([uv for _, uv in roots])
log('guides', G.shape, 'mean length', float(np.linalg.norm(np.diff(G, axis=1), axis=2).sum(1).mean()))
smat = hl.strand_material('M_%s_HairStrands' % N, **S['strand'])
strands = hl.make_curves('HairStrands', G, radius=S.get('radius', 4.5e-5), surface=scalp, root_uv=UVr)
chain = [('Interpolate Hair Curves', {'Density': S['density'], 'Density Mask': ('attr', 'dens'), 'Interpolation Guides': S.get('interp', 4), 'Part by Mesh Islands': True, 'Seed': 3}),
         ('Clump Hair Curves', {'Factor': S['clump'], 'Shape': S.get('clump_shape', .45), 'Tip Spread': S.get('tip_spread', .002), 'Existing Guide Map': False, 'Guide Distance': S.get('clump_d', .009), 'Seed': 5}),
         ('Hair Curves Noise', {'Distance': S.get('noise_d', .003), 'Scale': S.get('noise_s', 14.0), 'Shape': .4, 'Scale along Curve': 1.0, 'Offset per Curve': .4, 'Seed': 7}),
         ('Frizz Hair Curves', {'Distance': S.get('frizz_d', .0012), 'Shape': .5, 'Seed': 9}),
         ('Trim Hair Curves', {'Replace Length': False, 'Length Factor': 1.0, 'Random Offset': S.get('trim_rand', .012), 'Seed': 11}),
         ('Set Hair Curve Profile', {'Replace Radius': True, 'Radius': S.get('radius', 4.5e-5), 'Shape': .35})]
hl.gn_chain(strands, 'GN_%s_Hair' % N, chain, material=smat, surface=scalp, resample=S.get('resample', 14), streak=S.get('streak_scale'))
extra = []          # further strand objects (bun bundles, loose wisps)
BUNP = []
if S['kind'] == 'bun':
    R3 = S['bun_r']; c = bun['c']; nb = S.get('bun_bundles', 9)
    for q in range(nb):   # wound bundles: each wraps the bun on a tilted coil, twisting with its neighbour
        ph = 2 * math.pi * q / nb + gr.uniform(-.2, .2); turns = gr.uniform(1.1, 1.6); lat0 = gr.uniform(-.1, .35); Kb = 40; pts = []
        tw_r = gr.uniform(.003, .006); tw_f = gr.uniform(2.5, 4.0); tw_p = gr.uniform(0, 6.28)
        for k in range(Kb):
            t = k / (Kb - 1); az = ph + 2 * math.pi * turns * t; la = lat0 + (1.15 - lat0) * t ** 1.3 * (.55 + .45 * (q % 3) / 2)
            rr = 1.0 + .10 * math.sin(tw_p + tw_f * az)
            p = c + bun['bn'] * (R3[2] * rr * math.sin(la) + tw_r * math.cos(tw_p + tw_f * az)) + (bun['bx'] * R3[0] * math.cos(az) + bun['by'] * R3[1] * math.sin(az)) * math.cos(la) * rr
            pts.append(p)
        BUNP.append(np.array(pts))
    bobj = hl.make_curves('HairBun', np.array(BUNP), radius=S.get('radius', 4.5e-5))
    hl.gn_chain(bobj, 'GN_%s_Bun' % N, [('Duplicate Hair Curves', {'Amount': S.get('bun_amount', 420), 'Radius': S.get('bun_bundle_r', .0075), 'Distribution Shape': .3, 'Tip Roundness': .6, 'Seed': 2}),
                                       ('Frizz Hair Curves', {'Distance': S.get('frizz_d', .0012) * 1.3, 'Shape': .3, 'Seed': 6}),
                                       ('Set Hair Curve Profile', {'Replace Radius': True, 'Radius': S.get('radius', 4.5e-5), 'Shape': .35})], material=smat, resample=60, streak=S.get('streak_scale'))
    extra.append(bobj)
    wr = [p for p, _ in RT.sample(S.get('wisps', 14), .86, 1.0, azmin=.75, azmax=1.5)] + [p for p, _ in RT.sample(S.get('wisps_nape', 10), .86, 1.0, azmin=2.2)]
    WP = np.array([guide(p, gr, 'wisp') for p in wr])
    wobj = hl.make_curves('HairWisps', WP, radius=S.get('radius', 4.5e-5))
    hl.gn_chain(wobj, 'GN_%s_Wisps' % N, [('Duplicate Hair Curves', {'Amount': 5, 'Radius': .0013, 'Seed': 2}), ('Frizz Hair Curves', {'Distance': .0015, 'Seed': 6}),
                                          ('Set Hair Curve Profile', {'Replace Radius': True, 'Radius': S.get('radius', 4.5e-5) * .9, 'Shape': .35})], material=smat, resample=16)
    extra.append(wobj)
# ------------------------------------------------------------------ brows: a short strand groom per brow, baked into the atlas band
BR = dict(z0=.0185, arch=.0055, th=.0048, x0=-.021, span=.054, n=600, len=(.0095, .006), r=4.0e-5); BR.update(S.get('brow', {}))
KE = abs(H.eyes[1][0][0]) / .031
for k_ in ('z0', 'arch', 'th', 'x0', 'span'): BR[k_] *= KE
def brow_zc(sgn, s_):
    e_ = H.eyes[sgn][0]; return e_[2] + BR['z0'] + BR['arch'] * math.sin(math.pi * min(max(s_, 0), 1.15) * .72) - .0035 * float(sstep(.7, 1.1, s_))
def brow_th(s_): return BR['th'] * (1 - .72 * float(sstep(.4, 1.0, s_))) * (.55 + .45 * float(sstep(0, .12, s_)))
def brow_pt(sgn, s_, dz):
    e_ = H.eyes[sgn][0]; x = sgn * (abs(e_[0]) + BR['x0'] + s_ * BR['span']); z = brow_zc(sgn, s_) + dz
    loc, nrm, _, _ = H.bvh.ray_cast(Vector((x, e_[1] - .09, z)), Vector((0, 1, 0)))
    if loc is None: return H.near(np.array([x, e_[1] + .01, z]))
    return np.array(loc), np.array(nrm)
BROWP = []; BROWB = []; brng = np.random.default_rng(S.get('seed', 1) + 400); bcol = np.array(S['albedo']) * S.get('brow_dark', .6)
BW = BR['th'] * 2.4     # card half height
for sgn in (1, -1):
    k = 0
    while k < BR['n']:
        s_ = brng.uniform(-.02, .97); w_ = brng.uniform(-1, 1)
        if brng.random() < abs(w_) ** 2.5 * .7 or brng.random() < .5 * float(sstep(.75, 1.05, s_)): continue
        p, nrm = brow_pt(sgn, s_, w_ * brow_th(s_))
        if p is None: continue
        p2, _ = brow_pt(sgn, s_ + .05, 0); p1, _ = brow_pt(sgn, s_, 0); T = hl.unit(p2 - p1); U = hl.unit(np.array([0, 0, 1.0]) - nrm * nrm[2])
        th = math.radians(78 - 50 * float(sstep(0, .2, s_))) if s_ < .2 else math.radians(-26 * w_ + 6)
        th += brng.normal(0, .14); d = T * math.cos(th) + U * math.sin(th)
        L = (BR['len'][0] + (BR['len'][1] - BR['len'][0]) * min(max(s_, 0), 1)) * brng.uniform(.75, 1.2) * (1 - .5 * float(sstep(.8, 1.0, s_)))
        g = hl.grow(H, p + nrm * .0002, hl.unit(d + nrm * .22), L, K=5, gravity=0.0, minlift=(.0002, .0014), wander=.03, rng=brng)
        BROWP.append(g); k += 1
        e_ = H.eyes[sgn][0]; ss = (sgn * g[:, 0] - (abs(e_[0]) + BR['x0'])) / BR['span']; zz = np.array([g[i, 2] - brow_zc(sgn, ss[i]) for i in range(len(g))])
        u = (ss + .10) / 1.25 * .5; v = (.125 if sgn > 0 else 0.0) + (zz / (2 * BW) + .5) * .125
        BROWB.append(dict(P=np.c_[np.clip(u, .002, .498), np.clip(v, .002, .248), np.full(len(g), .5)], r=S.get('brow_px', 2.8), col=bcol * math.exp(brng.normal(0, .2))))
bmat = hl.strand_material('M_%s_BrowStrands' % N, **{**S['strand'], 'melanin': min(1.0, S['strand']['melanin'] + S.get('brow_melanin', .12)), 'grey': 0.0})
brows = hl.make_curves('BrowStrands', np.array(BROWP), radius=np.tile(BR['r'] * (1 - .8 * sstep(.4, 1.0, np.linspace(0, 1, 5)))[None, :], (len(BROWP), 1)))
brows.data.materials.append(bmat)
# ------------------------------------------------------------------ cap: the evaluated groom projected about the head centre
CM = hl.CapMap(H); CM.build_skull()
SP = hl.evaluated_strands(strands, 14)
cu0, cv0, r0 = CM.uv(SP); th_ = np.hypot(cu0 - .5, cv0 - .5) * 2 * CM.th_max; CM.th_max = float(min(2.75, np.percentile(th_, 99.9) + .08)); CM.build_skull()
cu, cv, hh = CM.fields(SP); log('cap: strands', len(SP), 'th_max', round(CM.th_max, 3), 'height p50/p99', round(float(np.percentile(hh, 50)), 4), round(CM.hmax, 4))
# ------------------------------------------------------------------ atlas
NT = S.get('ntiles', ['n_dense'] * 9 + ['n_mid'] * 10 + ['n_thin'] * 7 + ['n_wisp'] * 4 + ['n_fly'] * 2)
TILES = NT + ['dense'] * 4
TI = {k: [i for i, t in enumerate(TILES) if t == k] for k in set(TILES)}
if 'atlas' in steps or not (TX / ('T_%s_PR_Hair_FLOW.png' % N)).exists():
    ar = np.random.default_rng(S.get('seed', 1) + 200); base = np.array(S['albedo']); grey = S.get('grey', 0.0)
    def col_fun(r):
        if r.random() < grey: return np.array(S.get('grey_col', (.42, .40, .36))) * r.uniform(.8, 1.15)
        c = base * math.exp(r.normal(0, S.get('col_var', .22))); c = c * (1 + r.normal(0, .06, 3)); return np.clip(c, .004, .9)
    CR = hl.CAP_RECT; near = np.clip(hh / max(CM.hmax, 1e-4), 0, 1)
    capP = np.stack([CR[0] + cu * (CR[2] - CR[0]), near, CR[1] + cv * (CR[3] - CR[1])], -1)
    # the cap carries the inner part of every strand; the free tips belong to the cards (ragged, feathered cap edge)
    te = ar.uniform(S.get('cap_tip', (.5, 1.0))[0], S.get('cap_tip', (.5, 1.0))[1], len(capP)); Kc = capP.shape[1]; ti = np.linspace(0, 1, Kc)[None, :] * te[:, None] * (Kc - 1)
    i0_ = np.clip(np.floor(ti).astype(int), 0, Kc - 2); f_ = (ti - i0_)[..., None]; ar_ = np.arange(len(capP))[:, None]; capP = capP[ar_, i0_] * (1 - f_) + capP[ar_, i0_ + 1] * f_
    lowf = np.array([.75 + .5 * hl.f1(p, 70, 311) for p in SP[:, 0]])         # lock-scale colour coherence
    capC = np.array([col_fun(ar) for _ in range(len(SP))]) * lowf[:, None]
    A, B = hl.render_atlas(str(PRE) + '_Hair', S.get('tile', {}), ar, TILES, col_fun, band=BROWB, cap=dict(P=capP, col=capC, r_px=S.get('cap_px', 2.2)))
    hl.compose_atlas(str(PRE) + '_Hair', A, B, S.get('tile', {}), alpha_gain=S.get('alpha_gain', 1.6), under_mask=CM.rgrid)
    MH = CHARS / 'ThirdParty/MakeHuman'
    r_ = subprocess.run(['python3', '-I', str(Path(__file__).parent / 'hair_band.py'), str(PRE) + '_Hair', str(MH / 'eyebrows/eyebrow001/eyebrow001.png'), str(MH / 'eyelashes/eyelashes01/eyelashes01.png'), S['brow_rgb'], S['lash_rgb'], 'lashonly'], capture_output=True, text=True)
    log('band', r_.stdout.strip(), r_.stderr.strip()[-300:])
# ------------------------------------------------------------------ game hair: opaque cap shell + narrow lock cards from the same guide field
cr = np.random.default_rng(S.get('seed', 1) + 300); CB = hl.Cards(H); DN = S.get('card_density', 1.0)
def cap_mesh(NR=S.get('cap_rings', 20), NS=S.get('cap_segs', 44), kh=S.get('cap_h', .3)):
    CR = hl.CAP_RECT; base = len(CB.v); idx = {}; dens = {}
    def vert(i, j):
        key = (i, j % NS) if i else (0, 0)
        if key in idx: return idx[key]
        rho = i / NR; az = 2 * math.pi * (j % NS) / NS; c_u = .5 + .5 * rho * math.sin(az); c_v = .5 - .5 * rho * math.cos(az)
        d = CM.dirs(np.array(c_u), np.array(c_v)); loc, nrm = CM.cast(d); h = float(CM.lookup(CM.hgrid, c_u, c_v)); dn = float(CM.lookup(CM.dgrid, c_u, c_v))
        kk = kh + (S.get('cap_h_hi', kh) - kh) * float(sstep(.012, .03, h))
        pv = loc + d * (S.get('cap_off', .0010) + min(kk * h, S.get('cap_hmax', .02))); l2, n2 = H.near(pv); sd_ = float((pv - l2) @ n2)
        if sd_ < .0010: pv = pv + n2 * (.0010 - sd_)
        CB.v.append(pv); CB.uv.append((CR[0] + c_u * (CR[2] - CR[0]), CR[1] + c_v * (CR[3] - CR[1]))); CB.hl.append(1); CB.hn.append(hl.unit(nrm * .6 + d * .4))
        idx[key] = len(CB.v) - 1; dens[idx[key]] = dn; return idx[key]
    nf = 0
    for i in range(NR):
        for j in range(NS):
            if i == 0: f = (vert(0, 0), vert(1, j), vert(1, j + 1))
            else: f = (vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1))
            if max(dens[q] for q in f) > .04: CB.f.append(f); nf += 1
    sd = []
    for q in range(base, len(CB.v)):
        l_, n_ = H.near(CB.v[q]); sd.append(float((CB.v[q] - l_) @ n_))
    sd = np.array(sd); log('cap faces', nf, 'verts', len(sd), 'signed dist to skin min/p5/median', round(float(sd.min()), 4), round(float(np.percentile(sd, 5)), 4), round(float(np.median(sd)), 4), 'below skin', int((sd < .0003).sum()), 'dens<.5', int(sum(1 for v_ in dens.values() if v_ < .5)))
cap_mesh()
def cap_floor(p, kh=S.get('cap_h', .3)):
    c_u, c_v, _ = CM.uv(np.asarray(p)); h = float(CM.lookup(CM.hgrid, c_u, c_v)); kk = kh + (S.get('cap_h_hi', kh) - kh) * float(sstep(.012, .03, h))
    return S.get('cap_off', .0010) + min(kk * h, S.get('cap_hmax', .02))
CB.floor = cap_floor
def nseg_for(g, n0, seg_len):
    if not seg_len: return n0
    L = float(np.linalg.norm(np.diff(g, axis=0), axis=1).sum()); return int(min(max(round(L / seg_len), 2), n0))
def shell(n, layer, tiles, e0, e1, width, nseg, across, lift_scale, lift_off, flare=(0.0, 0.0), kind='hair', roll=.03, bow=.05, azmin=0.0, azmax=4.0, t_range=(0.0, 1.0), wfun=None, nblend=.92, len_var=0.0, root_ext=0.0, v_span=(0.0, 1.0), seg_len=0.0, taper=.3):
    tl = [i for k in ([tiles] if isinstance(tiles, str) else tiles) for i in TI[k]]
    for p, _ in RT.sample(int(n * DN), e0, e1, azmin, azmax, wfun):
        if S['kind'] == 'short' and np.linalg.norm(p - crown) < S.get('crown_clear', .016): continue     # the whorl centre is carried by the cap
        g = guide(p, cr, kind); wk = 1 - S.get('edge_narrow', .3) * float(sstep(.72, 1.0, H.params(p)[1]))
        CB.ribbon(g, cr.uniform(*width) * wk, int(cr.choice(tl)), layer, cr, nseg=nseg_for(g, nseg, seg_len), across=across, lift_scale=lift_scale, lift_off=lift_off, roll=roll, bow=bow, taper=taper, flare=cr.uniform(*flare), t_range=(t_range[0], t_range[1] * (1 - len_var * cr.random())), nblend=nblend, root_ext=root_ext, v_span=v_span)
JS = S.get('card_jit', .7)
for sh in S['shells']: shell(**sh)
if S['kind'] == 'bun':
    for q, pts in enumerate(BUNP):
        CB.wound(pts, S.get('bun_bundle_r', .0075) * 1.05, TI['n_dense'] + TI['n_mid'], 2, cr, strips=S.get('bun_strips', 5), nseg=S.get('bun_nseg', 14))
        off = cr.normal(0, .002, 3); CB.ribbon(pts[2:-2] + off, cr.uniform(.007, .010), int(cr.choice(TI['n_thin'])), 3, cr, nseg=10, across=1, lift_scale=1.0, lift_off=0.0, roll=.6, bow=.1, nblend=.0)
    # core: an opaque ellipsoid of wound hair under the ribbons (wide dense tile, strands run round the azimuth)
    Rc = np.array(S['bun_r']) * S.get('bun_core', .96); NS, NR = 14, 6; base = len(CB.v); u0, v0, u1, v1 = hl.tile_rect(TI['dense'][0])
    for i in range(NR + 1):
        la = math.pi * (.5 - .92 * i / NR)
        for j in range(NS + 1):
            az = 2 * math.pi * j / NS - math.pi / 2; nn = bun['bn'] * math.sin(la) + (bun['bx'] * math.cos(az) + bun['by'] * math.sin(az)) * math.cos(la)
            CB.v.append(bun['c'] + bun['bn'] * Rc[2] * math.sin(la) + (bun['bx'] * Rc[0] * math.cos(az) + bun['by'] * Rc[1] * math.sin(az)) * math.cos(la))
            CB.uv.append((u0 + (.12 + .76 * i / NR) * (u1 - u0), v0 + (.5 + .4 * j / NS) * (v1 - v0))); CB.hl.append(1); CB.hn.append(nn)
    for i in range(NR):
        for j in range(NS):
            a_ = base + i * (NS + 1) + j; CB.f.append((a_, a_ + 1, a_ + NS + 2, a_ + NS + 1))
    wr2 = [p for p, _ in RT.sample(S.get('card_wisps', 16), .84, 1.0, azmin=.7, azmax=1.6)] + [p for p, _ in RT.sample(S.get('card_wisps_nape', 12), .86, 1.0, azmin=2.2)]
    for p in wr + wr2:
        g = guide(p, cr, 'wisp'); CB.ribbon(g, cr.uniform(.005, .008), int(cr.choice(TI['n_fly'] + TI['n_wisp'])), 5, cr, nseg=5, across=1, lift_scale=1.0, lift_off=0.0, roll=.5, bow=.05, nblend=.3)
for sgn in (1, -1):     # brow cards: a patch on the brow ridge carrying the baked brow groom
    NS_ = 14; NW_ = 4; base = len(CB.v); e_ = H.eyes[sgn][0]
    for i in range(NS_ + 1):
        s_ = -.10 + 1.25 * i / NS_
        for j in range(NW_ + 1):
            p, nrm = brow_pt(sgn, s_, (j / NW_ * 2 - 1) * BW)
            CB.v.append(p + nrm * .0016); CB.uv.append((i / NS_ * .5, (.125 if sgn > 0 else 0.0) + j / NW_ * .125)); CB.hl.append(4); CB.hn.append(nrm)
    for i in range(NS_):
        for j in range(NW_):
            a_ = base + i * (NW_ + 1) + j; A_ = NW_ + 1; CB.f.append((a_, a_ + A_, a_ + A_ + 1, a_ + 1) if sgn > 0 else (a_, a_ + 1, a_ + A_ + 1, a_ + A_))
hair = CB.build('HairCards'); log('hair card tris', tri_count(hair))
cmat = hl.card_material('MI_%s_PR_Hair' % N, str(PRE) + '_Hair_BC.png', str(PRE) + '_Hair_N.png', str(PRE) + '_Hair_ORM.png', **S.get('card_mat', {}))
hair.data.materials.append(cmat)
if browlash is not None: browlash.data.materials.clear(); browlash.data.materials.append(cmat)
dg_ = bpy.context.evaluated_depsgraph_get()
for o_ in [strands, brows] + extra:
    ed_ = o_.evaluated_get(dg_).data; pp_ = np.empty(len(ed_.points) * 3, np.float32); ed_.attributes['position'].data.foreach_get('vector', pp_); pp_ = pp_.reshape(-1, 3)
    rr_ = np.empty(len(ed_.points), np.float32); ed_.attributes['radius'].data.foreach_get('value', rr_) if ed_.attributes.get('radius') else rr_.fill(-1)
    log('strand object', o_.name, 'curves', len(ed_.curves), 'bbox', pp_.min(0).round(3).tolist(), pp_.max(0).round(3).tolist(), 'radius mean', float(rr_.mean()), 'mats', [m_.name if m_ else None for m_ in ed_.materials])
# ------------------------------------------------------------------ comparison render: strands vs cards, same cameras
if 'strands' in steps or 'cards' in steps:
    P_ = 'T_%s_PR' % N
    sk.data.materials.clear(); sk.data.materials.append(matlib.game_material('MI_%s_PR_Skin' % N, TX / (P_ + '_Skin_BC.png'), TX / (P_ + '_Skin_N.png'), TX / (P_ + '_Skin_ORM.png'), sss=TX / (P_ + '_Skin_SSS.png'), ao_mix=.5))
    ey = D['Eyes']; ey.data.materials.clear(); ey.data.materials.append(matlib.game_material('MI_%s_PR_Eyes' % N, TX / (P_ + '_Eyes_BC.png'), TX / (P_ + '_Eyes_N.png'), TX / (P_ + '_Eyes_ORM.png'), ao_mix=.8, spec=.8))
    setup_render(samples=int(os.environ.get('HAIR_SPP', 96)), res=(640, 640)); sc.world.node_tree.nodes['Background'].inputs[1].default_value = .085
    try: sc.cycles.use_curves = True
    except Exception: pass
    sky = next(n for n in sc.world.node_tree.nodes if n.type == 'TEX_SKY'); hc = H.ctr + np.array([0, 0, .0])
    shots = [('sun2m', (hc[0] + .55, hc[1] - 1.9, hc[2] + .25), 215, False), ('sun05', (hc[0] + .14, hc[1] - .47, hc[2] + .07), 55, False), ('ovc05', (hc[0] - .2, hc[1] - .43, hc[2] + .1), 55, True), ('back', (hc[0] - .45, hc[1] + 1.1, hc[2] + .25), 140, False), ('crown', (hc[0] + .1, hc[1] + .32, hc[2] + .45), 60, False)]
    only = os.environ.get('HAIR_SHOTS'); shots = [s_ for s_ in shots if not only or s_[0] in only.split(',')]
    REV.mkdir(parents=True, exist_ok=True)
    for mode in ('strands', 'cards'):
        if mode not in steps: continue
        for o in [strands, brows] + extra: o.hide_render = mode != 'strands'
        hair.hide_render = mode != 'cards'
        for nm, loc, lens, ovc in shots:
            try: sky.sun_intensity = 0.0 if ovc else 1.0
            except Exception: pass
            sc.world.node_tree.nodes['Background'].inputs[1].default_value = .22 if ovc else .085
            shoot(REV / ('%s_%s_%s.png' % (tag, mode, nm)), loc, tuple(hc + np.array([0, 0, .015])), lens=lens)
    from PIL import Image
    rows = []
    for mode in ('strands', 'cards'):
        fs = [REV / ('%s_%s_%s.png' % (tag, mode, s_[0])) for s_ in shots]
        if all(f.exists() for f in fs): rows.append(np.concatenate([np.asarray(Image.open(f).convert('RGB')) for f in fs], 1))
    if rows: Image.fromarray(np.concatenate(rows, 0)).save(REV / ('%s_hair_compare.png' % tag)); log('compare', REV / ('%s_hair_compare.png' % tag))
if 'save' in steps:
    save_blend(filepath=str(OUT / N / 'Work' / (n_ + '_groom.blend')), copy=True)
    for o in [strands, scalp, brows] + extra: bpy.data.objects.remove(o, do_unlink=True)
    for nm in ('PR_GroundPlane', 'PR_Cam'):
        if nm in D: bpy.data.objects.remove(D[nm], do_unlink=True)
    final = join([hair] + ([browlash] if browlash is not None else []), 'Hair'); hl.apply_hn(final)
    log('Hair object tris', tri_count(final))
    save_blend(filepath=str(head_blend))
log('HAIR_DONE', N)
