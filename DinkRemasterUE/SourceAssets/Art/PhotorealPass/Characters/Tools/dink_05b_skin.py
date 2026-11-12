"""Stage 5b: skin texture set. Re-packs the head/hand UV islands (head gets most of a 4K sheet), bakes the CC0 MakeHuman
albedo plus position / curvature / AO helper maps with Cycles, then authors colour zones, freckles, scalp underpaint, pore
and crease normal, roughness and a subsurface map in numpy."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *
CFG = dict(head='Dink/Work/dink_head.blend', tex='Dink/Textures', prefix='T_Dink_PR', size=4096,
           skin='ThirdParty/MakeHuman/skins/young_caucasian_male/young_lightskinned_male_diffuse.png',
           hair_col=(.12, .05, .026), freckles=1.0, redness=1.0, age=0.0, tan=(.97, .88, .80), grime=.3, seed=3)
if args(): CFG.update(json.loads(Path(args()[0]).read_text()))
bpy.ops.wm.open_mainfile(filepath=str(OUT / CFG['head']))
LM = json.load(open(str(OUT / CFG['head']) + '.json'))
D = bpy.data.objects; sc = bpy.context.scene; sk = D['Skin']; me = sk.data
SIZE = CFG['size']; HS = SIZE // 2
# ---------------- UV islands of the MakeHuman layout -> repack
bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv['UVMH']; bm.faces.ensure_lookup_table()
isl = [-1] * len(bm.faces); nisl = 0
for f0 in bm.faces:
    if isl[f0.index] >= 0: continue
    st = [f0]; isl[f0.index] = nisl
    while st:
        f = st.pop()
        for l in f.loops:
            r = l.link_loop_radial_next
            if r.face is f or isl[r.face.index] >= 0: continue
            # same uv edge on both sides?
            if (l[uvl].uv - r.link_loop_next[uvl].uv).length < 1e-5 and (l.link_loop_next[uvl].uv - r[uvl].uv).length < 1e-5:
                isl[r.face.index] = nisl; st.append(r.face)
    nisl += 1
area = np.zeros(nisl); zmean = np.zeros(nisl); cnt = np.zeros(nisl)
for f in bm.faces:
    area[isl[f.index]] += f.calc_area(); zmean[isl[f.index]] += f.calc_center_median().z; cnt[isl[f.index]] += 1
zmean /= np.maximum(cnt, 1); bm.free()
big = int(np.argmax(np.where(zmean > 1.4, area, 0)))
wt = np.where(np.arange(nisl) == big, 1.0, np.where(zmean > 1.4, .6, 1.0))
log('skin islands', nisl, 'face island area', area[big])
att = me.attributes.get('chart') or me.attributes.new('chart', 'INT', 'FACE'); att.data.foreach_set('value', np.array(isl, np.int32))
nl = len(me.loops); uv = np.empty(nl * 2, np.float32); me.uv_layers['UVMH'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
ltot = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', ltot); lstart = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', lstart)
srt = np.argsort(lstart); fol = np.repeat(srt, ltot[srt])
um = me.uv_layers.get('UVMetric') or me.uv_layers.new(name='UVMetric')
me.uv_layers['UVMetric'].data.foreach_set('uv', (uv * wt[np.array(isl)[fol]][:, None]).astype(np.float32).ravel())
if me.uv_layers.get('UVMap'): me.uv_layers.remove(me.uv_layers['UVMap'])
pack_charts([sk], SIZE, margin_px=16)
me.uv_layers.remove(me.uv_layers['UVMetric'])
save_blend()
# ---------------- helper bakes
sc.render.engine = 'CYCLES'; use_hip_gpu(sc); sc.cycles.samples = 1; sc.cycles.use_denoising = False; sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
mat = bpy.data.materials.new('SkinBake'); mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(em.outputs[0], out.inputs[0])
tgt = nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active = tgt
src = nt.nodes.new('ShaderNodeTexImage'); src.image = bpy.data.images.load(str(CHARS / CFG['skin'])); uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMH'; nt.links.new(uvn.outputs[0], src.inputs[0])
geo = nt.nodes.new('ShaderNodeNewGeometry')
sk.data.materials.clear(); sk.data.materials.append(mat)
for o in D:
    if o.type == 'MESH': o.hide_render = o.name not in ('Skin', 'Eyes')
activate(sk); me.uv_layers.active = me.uv_layers['UVMap']
def bake(sock, typ='EMIT', size=HS, samples=1):
    im = bpy.data.images.new('b', size, size, alpha=True, float_buffer=True); im.colorspace_settings.name = 'Non-Color'; im.generated_color = (0, 0, 0, 0)
    tgt.image = im
    if sock is not None:
        for l in list(em.inputs[0].links): nt.links.remove(l)
        nt.links.new(sock, em.inputs[0])
    sc.cycles.samples = samples
    bpy.ops.object.bake(type=typ, margin=0, use_clear=True, use_selected_to_active=False)
    a = np.empty(size * size * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im); return a.reshape(size, size, 4)
base = bake(src.outputs[0]); pos = bake(geo.outputs['Position']); pt = bake(geo.outputs['Pointiness'])
ao = bake(None, 'AO', HS // 2, 48)
em.inputs[0].default_value = (1, 1, 1, 1)
for l in list(em.inputs[0].links): nt.links.remove(l)
covb = bake(None); cover = covb[..., 0] > .5
log('bakes done; coverage', cover.mean())
# ---------------- numpy authoring
rng = np.random.default_rng(CFG['seed'])
def blur(a, r):
    """3x box blur ~ gaussian, radius r px, any trailing channels."""
    if r < 1: return a
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.concatenate([np.repeat(np.take(a, [0], axis=ax), r + 1, axis=ax), a, np.repeat(np.take(a, [-1], axis=ax), r, axis=ax)], axis=ax), axis=ax, dtype=np.float64)
            n = a.shape[ax]; a = ((np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=ax) - np.take(c, range(0, n), axis=ax)) / (2 * r + 1)).astype(np.float32)
    return a
def fill(a, cov, it=6, r=3):
    """push covered colours outward over the gutters"""
    w = cov.astype(np.float32); a = a * w[..., None] if a.ndim == 3 else a * w
    out = a.copy(); wo = w.copy()
    for _ in range(it):
        ba = blur(out * (wo[..., None] if a.ndim == 3 else wo), r); bw = blur(wo, r)
        nb = ba / np.maximum(bw[..., None] if a.ndim == 3 else bw, 1e-4)
        m = (wo < .5) & (bw > .05)
        out[m] = nb[m]
        wo = np.maximum(wo, m.astype(np.float32))
    return out
def up(a, s):
    a = np.repeat(np.repeat(a, s, axis=0), s, axis=1); return blur(a, max(1, s // 2))
def dbg(name, a):
    d = os.environ.get('PR_DEBUG')
    if not d: return
    a = np.asarray(a, np.float32)[::4, ::4]; log('DBG', name, 'min', float(np.nanmin(a)), 'max', float(np.nanmax(a)), 'nan', int(np.isnan(a).sum()))
    if a.ndim == 2: a = np.dstack([a, a, a])
    im = bpy.data.images.new('d', a.shape[1], a.shape[0], alpha=True); im.pixels.foreach_set(np.clip(np.dstack([a[..., :3], np.ones(a.shape[:2], np.float32)]), 0, 1).ravel()); im.filepath_raw = d + '/dbg_' + name + '.png'; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
dbg('base', base[..., :3]); dbg('cover', cover.astype(np.float32)); dbg('pos', pos[..., :3] - np.array([0, 0, 1.2]))
base3 = fill(base[..., :3], cover); P = pos[..., :3]
dbg('base3', base3)
P_f = fill(P, cover, it=3)
x, y, z = P_f[..., 0], P_f[..., 1], P_f[..., 2]
nose = np.array(LM['nose']); ctr = np.array(LM['ctr']); eyeL = np.array(LM['eyes']['1'][0]); eyeR = np.array(LM['eyes']['-1'][0])
headm = (z > 1.40) & cover; handm = (z < 1.40) & cover
def blob(c, r, sx=1.0):
    return np.exp(-(((x - c[0]) / (r * sx)) ** 2 + ((y - c[1]) / r) ** 2 + ((z - c[2]) / r) ** 2))
ax = np.abs(x)
cheeks = blob((.043, nose[1] + .032, nose[2] - .004), .026) + blob((-.043, nose[1] + .032, nose[2] - .004), .026)
nosem = blob(nose + np.array([0, .008, .004]), .017)
ears = sstep(.072, .080, ax) * headm * sstep(nose[2] - .03, nose[2] - .01, z)
chin = blob((0, nose[1] + .022, nose[2] - .068), .022)
forehead = sstep(eyeL[2] + .022, eyeL[2] + .045, z) * sstep(-.02, -.06, y - ctr[1]) * headm
tz = np.clip(blob((0, nose[1] + .03, eyeL[2] + .045), .035, 1.3) + nosem + chin * .7, 0, 1)
lips_zone = (ax < .032) & (z < nose[2] - .018) & (z > nose[2] - .048) & (y < nose[1] + .04)
pcur = pt[..., 0]; pcur = fill(pcur, cover, it=2)
ridge_c = sstep(.52, .60, pcur); cav = sstep(.48, .40, pcur)
Pp = P_f.reshape(-1, 3)
def n3(scale, seed, octs=1):
    out = np.zeros(len(Pp), np.float32); step = 400000
    for i in range(0, len(Pp), step):
        out[i:i + step] = (fbm(Pp[i:i + step], scale, octs, seed) if octs > 1 else vnoise(Pp[i:i + step], scale, seed))
    return out.reshape(HS, HS)
col = base3.copy()
# farm-boy tan with redder cheeks / nose / ears / knuckles, paler brow
red = np.clip(cheeks * .55 + nosem * .6 + ears * .7 + chin * .2, 0, 1) * headm + handm * ridge_c * .55
red *= CFG['redness']
col *= np.array(CFG['tan'])[None, None, :]
col = col * (1 - red[..., None] * .26 * np.array([0.0, 1, 1.05])[None, None, :])
col = col * (1 + forehead[..., None] * .05)
blotch = n3(55, 11, 3) - .5
col *= (1 + blotch[..., None] * np.array([.10, .16, .18])[None, None, :])        # mottled circulation
# freckles
fr_d = np.clip(cheeks * 1.0 + blob(nose + np.array([0, .012, .012]), .02) + forehead * .25 + .06, 0, 1) * headm + handm * .16
f1 = n3(520, 21); f2 = n3(900, 22); fm = n3(40, 23, 2)
fre = (sstep(.80 - .16 * fr_d, .93 - .16 * fr_d, f1) * .8 + sstep(.84 - .14 * fr_d, .95 - .14 * fr_d, f2) * .6) * sstep(.25, .6, fm + fr_d * .5) * (fr_d > .05)
fre = np.clip(fre * CFG['freckles'], 0, 1)
col = col * (1 - fre[..., None] * (1 - np.array([.62, .42, .30]))[None, None, :] * .75)
dbg('col_freckle', col)
# scalp underpaint below the hair cards
d = P_f - ctr[None, None, :]; dl = np.linalg.norm(d, axis=2) + 1e-9; dz = d[..., 2] / dl; az = np.abs(np.arctan2(d[..., 0], -d[..., 1]))
t1 = np.clip(az / 1.15, 0, 1); t1 = t1 * t1 * (3 - 2 * t1); t2 = np.clip((az - 1.15) / (np.pi - 1.15), 0, 1); t2 = t2 * t2 * (3 - 2 * t2)
HLc = CFG.get('hairline', (.50, .14, -.52))
hl = np.where(az < 1.15, HLc[0] + (HLc[1] - HLc[0]) * t1, HLc[1] + (HLc[2] - HLc[1]) * t2)
edge = (n3(45, 31, 3) - .5) * .12
scalp = sstep(-.07, .06, dz - hl + edge - .06) * headm * (z > 1.56)
hc = np.array(CFG['hair_col'])
SM = CFG.get('scalp_mix', .8)
col = col * (1 - scalp[..., None] * SM) + hc[None, None, :] * (scalp * SM)[..., None] * (.8 + .4 * n3(400, 33, 2))[..., None]
dbg('col_scalp', col)
# brows: soft shadow under the cards
for e in (eyeL, eyeR):
    bx = np.exp(-((x - e[0] * 1.02) / .024) ** 2 - ((z - (e[2] + .0215 - .004 * np.abs(x - e[0]) / .02)) / .0058) ** 2) * (y < e[1] + .02)
    col = col * (1 - bx[..., None] * .32) + hc[None, None, :] * (bx * .32)[..., None]
# lips: a real colour break against the skin; stubble shadow on a young man's lip, chin and jaw
ratio = base3[..., 0] / np.maximum(base3[..., 1], 1e-4)
lipm = sstep(float(np.percentile(ratio[lips_zone & headm], 55)) if (lips_zone & headm).any() else 1.5, float(np.percentile(ratio[lips_zone & headm], 92)) if (lips_zone & headm).any() else 1.8, ratio) * (lips_zone & headm)
col = col * (1 - lipm[..., None] * np.array([.10, .30, .26])[None, None, :])
stb = np.clip(blob((0, nose[1] + .022, nose[2] - .020), .017, 1.7) + blob((0, nose[1] + .03, nose[2] - .075), .028, 1.4) + blob((.05, nose[1] + .07, nose[2] - .07), .03) + blob((-.05, nose[1] + .07, nose[2] - .07), .03), 0, 1) * headm * (1 - lipm) * CFG.get('stubble', .16)
col = col * (1 - stb[..., None]) + np.array([.16, .12, .10])[None, None, :] * stb[..., None] * (.6 + .8 * n3(2200, 61))[..., None]
# worked hands: grime in creases and round the nails
gr = np.clip(cav * 1.1 + sstep(.45, .7, n3(120, 41, 3)) * .35, 0, 1) * handm * CFG['grime']
col = col * (1 - gr[..., None] * .45) + np.array([.10, .07, .045])[None, None, :] * (gr * .45)[..., None]
if CFG['age'] > 0:   # sallow, less even, age spots
    col *= np.array([.97, .93, .88])[None, None, :] ** CFG['age']
    spots = sstep(.83, .92, n3(300, 51)) * sstep(.4, .7, n3(30, 52, 2)) * CFG['age']
    col = col * (1 - spots[..., None] * (1 - np.array([.7, .52, .40]))[None, None, :] * .6)
# sun and weather: uneven tan on the exposed planes, broken capillaries on cheeks and nose, a paler under-chin, moles, hand veins
sunm = np.clip(forehead * .6 + nosem * .55 + cheeks * .4, 0, 1) * headm * CFG.get('sun', .3)
col = col * (1 - sunm[..., None] * np.array([.05, .12, .17])[None, None, :])
underchin = sstep(nose[2] - .085, nose[2] - .105, z) * headm * (y < ctr[1] + .03)
col = col * (1 + underchin[..., None] * .07)
cap = sstep(.52, .78, n3(420, 81, 2)) * np.clip(cheeks + nosem * .8, 0, 1) * headm * CFG.get('capillary', .25)
col = col * (1 - cap[..., None] * np.array([0.0, .20, .17])[None, None, :])
vein = (1 - np.abs(2 * n3(70, 91, 2) - 1)) ** 9 * (handm * ridge_c + headm * blob((.062, nose[1] + .06, eyeL[2] + .02), .02) + headm * blob((-.062, nose[1] + .06, eyeL[2] + .02), .02)) * CFG.get('veins', .3)
col = col * (1 - vein[..., None] * np.array([.14, .07, .0])[None, None, :])
mrng = np.random.default_rng(CFG['seed'] + 77); cand = np.argwhere(headm & (y < ctr[1] - .01) & (scalp < .05) & (z > nose[2] - .12))
mole = np.zeros((HS, HS), np.float32)
for _ in range(int(CFG.get('moles', 5))):
    iy, ix = cand[mrng.integers(len(cand))]; p0 = P_f[iy, ix]; rr = mrng.uniform(.0006, .0015)
    mole = np.maximum(mole, np.exp(-(((P_f - p0[None, None, :]) ** 2).sum(2)) / rr ** 2) * mrng.uniform(.5, .95))
col = col * (1 - mole[..., None]) + np.array([.10, .055, .035])[None, None, :] * mole[..., None]
# eyes: wet pink lid margin and tear duct
rim = np.zeros((HS, HS), np.float32); car = np.zeros((HS, HS), np.float32)
for e_, r_ in ((eyeL, LM['eyes']['1'][1]), (eyeR, LM['eyes']['-1'][1])):
    de = np.linalg.norm(P_f - e_[None, None, :], axis=2); rim = np.maximum(rim, np.exp(-((de - (r_ + .0005)) / .0011) ** 2) * (y < e_[1] - .004) * headm)
    sg = 1.0 if e_[0] > 0 else -1.0
    car = np.maximum(car, np.exp(-(((x - (e_[0] - sg * (r_ - .001))) / .0030) ** 2 + ((z - (e_[2] - .0022)) / .0026) ** 2)) * (y < e_[1] + .004) * headm)
col = col * (1 - rim[..., None] * np.array([.02, .26, .22])[None, None, :] * .8) * (1 - car[..., None] * np.array([.0, .34, .28])[None, None, :])
glove = np.zeros((HS, HS), np.float32)
if CFG.get('glove'):     # the hands wear thin leather gloves under the steel gauntlet plates
    _arm = D['Armature'].data.bones
    for sd_ in 'lr':
        W_ = np.array(_arm['hand_' + sd_].head_local); dF_ = W_ - np.array(_arm['lowerarm_' + sd_].head_local); dF_ /= np.linalg.norm(dF_)
        glove = np.maximum(glove, sstep(-.030, -.018, (P_f - W_[None, None, :]) @ dF_) * (np.linalg.norm(P_f - W_[None, None, :], axis=2) < .26) * handm)
    gl = np.array(CFG['glove'])[None, None, :] * (.75 + .5 * n3(90, 95, 3))[..., None] * (1 - cav * .35)[..., None] * (1 + ridge_c * .25)[..., None]
    col = col * (1 - glove[..., None]) + gl * glove[..., None]
age_h = np.zeros((HS, HS), np.float32)
if CFG['age'] > 0:   # authored lines of a lived-in face: nasolabial and marionette folds, crow's feet, brow lines, lower-lid crease, neck rings
    AG = CFG['age']; ex, ey, ez = abs(eyeL[0]), eyeL[1], eyeL[2]; nz_ = nose[2]
    def seg(a, b, w):
        ax_, az_ = a; bx_, bz_ = b; px, pz = ax - ax_, z - az_; vx, vz = bx_ - ax_, bz_ - az_
        t_ = np.clip((px * vx + pz * vz) / (vx * vx + vz * vz), 0, 1); d_ = np.hypot(px - vx * t_, pz - vz * t_)
        return np.exp(-(d_ / w) ** 2) * np.sin(np.pi * np.clip(t_ * .9 + .1, 0, 1)) ** .6
    frontm = (y < nose[1] + .075) * headm
    naso = seg((.0175, nz_ - .004), (.0315, nz_ - .044), .0022) * frontm
    mario = seg((.0265, nz_ - .041), (.0300, nz_ - .066), .0020) * frontm
    cx_, cz_ = ex + .0165, ez - .001
    rr_ = np.hypot(ax - cx_, z - cz_); an_ = np.arctan2(z - cz_, ax - cx_)
    crow = (.5 + .5 * np.cos(an_ * 10 + 1.0)) ** 7 * sstep(.002, .006, rr_) * sstep(.024, .010, rr_) * (ax > cx_) * (np.abs(an_) < 1.1) * headm * (y < ey + .05)
    fore = (.5 + .5 * np.cos(2 * np.pi * z / .0068 + 3.0 * n3(60, 71) + 1.5 * np.cos(ax / .03))) ** 5 * forehead * sstep(.062, .035, ax) * sstep(ez + .024, ez + .034, z) * sstep(.45, .7, n3(35, 72, 2) + .25)
    bagl = np.exp(-((z - (ez - .0185 + .22 * np.abs(ax - ex) ** 1.3 * 6)) / .0013) ** 2) * (np.abs(ax - ex) < .017) * frontm
    glab = np.exp(-((ax - .0045) / .0012) ** 2) * sstep(ez + .004, ez + .012, z) * sstep(ez + .030, ez + .020, z) * frontm
    neckl = (.5 + .5 * np.cos(2 * np.pi * z / .016 + 2 * n3(40, 73))) ** 6 * sstep(nz_ - .095, nz_ - .110, z) * headm * (y < ctr[1] + .02) * sstep(.3, .6, n3(30, 74, 2) + .2)
    lines = np.clip(naso * 1.0 + mario * .75 + crow * .55 + fore * .30 + bagl * .7 + glab * .5 + neckl * .5, 0, 1.2) * AG
    age_h = -(lines * 1.5).astype(np.float32)
    col = col * (1 - lines[..., None] * np.array([.16, .22, .22])[None, None, :])
    ueye = np.clip(blob((ex, ey + .004, ez - .013), .0105, 1.5) + blob((-ex, ey + .004, ez - .013), .0105, 1.5), 0, 1) * headm * AG
    col = col * (1 - ueye[..., None] * np.array([.10, .16, .12])[None, None, :])
    col = col * (1 - lipm[..., None] * np.array([-.02, .05, .03])[None, None, :] * 0) * (1 + (n3(160, 75, 2) - .5)[..., None] * .07 * AG)
dbg('col_final', col)
if os.environ.get('PR_DEBUG') == 'stop': sys.exit(0)
# ---------------- upsample to full size, add micro
S = SIZE // HS
colF = up(col, S); covF = np.repeat(np.repeat(cover, S, 0), S, 1)
lum = colF @ np.array([.2126, .7152, .0722], np.float32)
hp = (lum - blur(lum, 6)) * (1 - np.clip(up(fre.astype(np.float32), S) * 3, 0, 1))   # albedo creases become relief; freckles stay flat
r1 = rng.random((SIZE, SIZE), dtype=np.float32)
pore = blur(r1, 1) - blur(r1, 3); pore = pore / (pore.std() + 1e-6)
def cells(cell, seed):
    """Skin micro-relief: polygonal plateaus (F2-F1 furrows) with a pore pit in a share of the cells. Returns (furrow, pit) in 0..1."""
    g = np.random.default_rng(seed); n = SIZE // cell + 3; jx = g.random((n, n), dtype=np.float32); jy = g.random((n, n), dtype=np.float32); pp = g.random((n, n), dtype=np.float32)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32); cx = (xx / cell).astype(np.int32); cy = (yy / cell).astype(np.int32)
    f1 = np.full((SIZE, SIZE), 9.0, np.float32); f2 = np.full((SIZE, SIZE), 9.0, np.float32); pit = np.zeros((SIZE, SIZE), np.float32)
    for oy in (0, 1, 2):
        for ox in (0, 1, 2):
            ix = cx + ox; iy = cy + oy
            d = np.hypot((ix - 1 + jx[iy, ix]) - xx / cell, (iy - 1 + jy[iy, ix]) - yy / cell)
            pit = np.maximum(pit, (pp[iy, ix] > .55) * np.clip(1 - d / .30, 0, 1))
            f2 = np.minimum(f2, np.maximum(f1, d)); f1 = np.minimum(f1, d)
    return np.clip(1 - (f2 - f1) / .16, 0, 1), pit
fu1, pi1 = cells(5, CFG['seed'] + 5); fu2, pi2 = cells(9, CFG['seed'] + 6)
pore_dip = -np.clip(pore - .6, 0, 2.5)                   # sparse pits
r2 = rng.random((SIZE, SIZE), dtype=np.float32); tex2 = blur(r2, 2) - blur(r2, 7); tex2 /= (tex2.std() + 1e-6)
headF = np.repeat(np.repeat(headm, S, 0), S, 1); handF = np.repeat(np.repeat(handm, S, 0), S, 1)
scalpF = up(scalp.astype(np.float32), S); tzF = up(tz.astype(np.float32), S); lipsF = up((lips_zone & headm).astype(np.float32), S)
# skin lines: anisotropic streak noise (dermatoglyph-like) stronger on hands, forehead lines with age
r3 = rng.random((SIZE, SIZE), dtype=np.float32)
streak = blur(np.roll(r3, 3, 1) + r3, 1); sx = streak - blur(streak, 4); sx /= (sx.std() + 1e-6)
ageF = CFG['age']
lipF = up(lipm.astype(np.float32), S); xF = up(x.astype(np.float32), S)
cheekF = up(np.clip(cheeks + nosem, 0, 1).astype(np.float32), S); MK = CFG.get('micro', 1.0)
micro = -(fu1 * .55 + pi1 * .9) * (1 - .6 * cheekF) - (fu2 * .35 + pi2 * 1.5) * (.25 + .75 * cheekF) * (.6 + .5 * tzF)
lip_cr = -(1 - np.abs(np.sin(xF * (2 * np.pi / .0026) + 5 * blur(tex2, 6)))) ** 3 * 1.6 + tex2 * .25
rimF = up(rim, S); carF = up(car, S)
height = micro * (.34 + .20 * ageF) * MK * (1 - scalpF) * (1 - lipF) * (1 - .8 * rimF) + tex2 * .05 + lipF * lip_cr + hp * (14 + 40 * ageF) * (1 - .55 * handF) + sx * (.06 + .12 * handF + .3 * ageF) + up(age_h, S) + pore_dip * .03
height = height * (1 - scalpF * .6) + scalpF * blur(rng.random((SIZE, SIZE), dtype=np.float32), 1) * 1.2   # stubbly scalp
# meso-scale breakup (2-6 mm): uneven skin surface and oil, by zone; strongest on the T-zone, cheeks and with age
r4 = rng.random((SIZE, SIZE), dtype=np.float32); meso = blur(r4, 6) - blur(r4, 18); meso /= (meso.std() + 1e-6); RM = CFG.get('rough_meso', 0.0)
height = height + meso * RM * 2.2 * (1 - scalpF) * (1 - lipF) * (.6 + .4 * cheekF + .5 * ageF * .5)
k = CFG.get('nrm_k', .18)
gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * k; gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * k
nrm = np.dstack([-gx, -gy, np.ones_like(gx)]); nrm /= np.linalg.norm(nrm, axis=2)[..., None]
gloveF = up(glove, S)
rough = .50 + .14 * gloveF - .15 * tzF - .16 * lipF + .07 * handF + .16 * scalpF - micro * CFG.get('rough_micro', .05) + meso * RM * (.7 + .6 * tzF) + tex2 * .03 + up(gr.astype(np.float32), S) * .2 + .05 * ageF - .28 * rimF - .25 * carF + up(blotch, S) * .06
aoF = up(np.repeat(np.repeat(fill(ao[..., 0], cover[::2, ::2], it=3), 2, 0), 2, 1), S)
aoF = np.clip(aoF * 1.15, 0, 1) * (1 - up(cav.astype(np.float32), S) * .25) * (1 + np.clip(pore_dip, -2, 0) * .04)
thin = np.clip(up((ears + nosem * .6).astype(np.float32), S) + handF * .45, 0, 1)
sss = np.dstack([np.ones_like(thin), np.full_like(thin, .36), np.full_like(thin, .26)]) * (.55 + .45 * thin)[..., None] * (1 - scalpF * .7)[..., None] * (1 - gloveF * .92)[..., None]
colF = colF * (1 + (micro * .035 * (1 - scalpF) * (1 - lipF))[..., None] * np.array([.6, 1.0, 1.0], np.float32)[None, None, :]) * (1 + (tex2 * .012)[..., None])
def save(name, arr, srgb):
    h, w = arr.shape[:2]; im = bpy.data.images.new(name, w, h, alpha=True)
    if arr.shape[2] == 3: arr = np.dstack([arr, np.ones((h, w), np.float32)])
    if not srgb: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.clip(arr, 0, 1).astype(np.float32).ravel()); im.filepath_raw = str(OUT / CFG['tex'] / (CFG['prefix'] + name + '.png')); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
# everything above is scene-linear; byte PNGs want display-referred values
def enc(c): c = np.clip(c, 0, 1); return np.where(c <= .0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - .055)
bc8 = enc(colF)
lumc = (bc8 @ np.array([.2126, .7152, .0722], np.float32))[covF]
log('skin BC luma p1/p99', np.percentile(lumc, 1) * 255, np.percentile(lumc, 99) * 255)
save('_Skin_BC', bc8, True); save('_Skin_N', nrm * .5 + .5, False)
save('_Skin_ORM', np.dstack([aoF, np.clip(rough, .15, .95), np.zeros_like(aoF)]), False); save('_Skin_SSS', enc(sss), True)
log('skin textures written')
