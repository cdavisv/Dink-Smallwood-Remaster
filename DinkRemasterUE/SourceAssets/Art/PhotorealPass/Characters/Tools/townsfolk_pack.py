"""A townsman's parts file and gear maps: the hero's clothes without what he does not wear, plus his hat, staff and neck cloth.

    blender -b -t 4 --python townsfolk_pack.py -- <Name>        (after dink_04_head.py: the hat is fitted to his head)

Reads Dink/Work/dink_packed.blend and NPC/<Name>/Work/<name>_head.blend.json; writes NPC/<Name>/Work/<name>_packed.blend
(the input of dink_06_assemble.py) and NPC/<Name>/Textures/T_<Name>_PR_Gear_BC / _N / _ORM.png: the hero's gear maps
with the hat and the staff painted into rectangles that the junked pack leaves free (townsfolk.py `props`;
the rectangles are checked against the UVs of every gear part that stays).

The hat is a lathe (low crown, wide brim that droops and wavers a little, 4 mm thick) mapped from straight above: the
top into a square of its rectangle, the underside smaller beside it. Its maps are plaited straw: rings of braid, every
strand with its own tone, a dark cord round the crown. The staff is a peeled pole, not quite straight, mapped along its
length. Hat: rigid on the head bone. Staff: rigid on the root bone where the idle clip Guard_Stand closes the right fist."""
import bpy, sys, os, math, json
import numpy as np
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from prlib import OUT, log, args, new_obj, smooth_shade, save_blend
from townsfolk import TOWNSFOLK
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
NAME = args()[0]; ROW = TOWNSFOLK[NAME]; DIR = OUT / 'NPC' / NAME; n_ = NAME.lower()
LM = json.load(open(DIR / 'Work' / f'{n_}_head.blend.json'))
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/Work/dink_packed.blend'))
D = bpy.data.objects
for nm in ROW['junk']:
    for o in (D.get(nm), D.get(nm + '_HI')):
        if o is not None: bpy.data.objects.remove(o, do_unlink=True)
SIZE = 2048
# ---- what the gear parts that stay use of the atlas
used = np.zeros((512, 512), bool)
for o in D:
    if o.type != 'MESH' or o.get('mat') != 'gear' or o.name.endswith('_HI'): continue
    me = o.data; uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    for p in me.polygons:
        q = uv[list(p.loop_indices)]; a = np.floor(q.min(0) * 512 - 1).astype(int).clip(0, 511); b = np.ceil(q.max(0) * 512 + 1).astype(int).clip(0, 511)
        used[a[1]:b[1] + 1, a[0]:b[0] + 1] = True       # the polygon's box: coarse, and on the safe side
for key, pr in ROW['props'].items():
    u0, v0, u1, v1 = pr['rect']; blk = used[int(v0 * 512):int(math.ceil(v1 * 512)), int(u0 * 512):int(math.ceil(u1 * 512))]
    if blk.any(): raise RuntimeError(f'{NAME}: the {key} rectangle {pr["rect"]} overlaps gear that stays ({int(blk.sum())} cells)')
SRC = OUT / 'Dink/Textures'
bc = np.asarray(Image.open(SRC / 'T_Dink_PR_Gear_BC.png').convert('RGB'), np.float32) / 255.0
nm_ = np.asarray(Image.open(SRC / 'T_Dink_PR_Gear_N.png').convert('RGB'), np.float32) / 255.0
orm = np.asarray(Image.open(SRC / 'T_Dink_PR_Gear_ORM.png').convert('RGB'), np.float32) / 255.0
assert bc.shape[0] == SIZE, bc.shape
if ROW.get('gear_red'):      # the hero's red bracer leather in the figure's own colour (light, dark and stitching of the bake stay)
    target, gain = ROW['gear_red']; m = np.clip((bc[..., 0] - np.maximum(bc[..., 1], bc[..., 2]) - .05) * 8.0, 0, 1)[..., None]
    lum = (bc @ np.array([.2126, .7152, .0722], np.float32))[..., None]
    bc = bc * (1 - m) + m * (bc * .12 + .88 * np.clip(lum * gain, 0, 1.2) * np.array(target, np.float32)); log('gear red leather recoloured, share', round(float(m.mean()), 3))


def hash2(a, b, s=0):
    h = np.sin(a * 127.1 + b * 311.7 + s * 74.7) * 43758.5453
    return h - np.floor(h)


def vnoise(x, y, s=0):
    xi, yi = np.floor(x), np.floor(y); fx, fy = x - xi, y - yi; fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    return (hash2(xi, yi, s) * (1 - fx) + hash2(xi + 1, yi, s) * fx) * (1 - fy) + (hash2(xi, yi + 1, s) * (1 - fx) + hash2(xi + 1, yi + 1, s) * fx) * fy


def paint(rect_px, col, height, rough, depth):
    """write colour, a normal from the height field (OpenGL, +Y up; `depth` in texels of slope) and roughness into the atlas; image rows run down"""
    x0, y0, x1, y1 = rect_px      # pixel box, y from the TOP of the image
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5; gy = (np.roll(height, 1, 0) - np.roll(height, -1, 0)) * .5
    n = np.dstack([-gx * depth, -gy * depth, np.ones_like(height)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    bc[y0:y1, x0:x1] = np.clip(col, 0, 1); nm_[y0:y1, x0:x1] = n * .5 + .5
    orm[y0:y1, x0:x1, 0] = np.clip(.55 + .45 * height, 0, 1); orm[y0:y1, x0:x1, 1] = np.clip(rough, 0, 1); orm[y0:y1, x0:x1, 2] = 0.0


def box(u0, v0, u1, v1):      # uv rectangle -> pixel box
    return int(round(u0 * SIZE)), int(round((1 - v1) * SIZE)), int(round(u1 * SIZE)), int(round((1 - v0) * SIZE))


def straw(px, metres, pr, under):
    """plaited straw seen from straight above, `metres` across the square of `px` texels; the centre is the hat's axis"""
    y, x = np.mgrid[0:px, 0:px].astype(np.float32); u = (x + .5) / px - .5; v = .5 - (y + .5) / px
    rho = np.hypot(u, v) * metres; th = np.arctan2(v, u); seed = pr['seed']
    pitch = .0105; row = np.floor(rho / pitch); f = rho / pitch - row
    lean = np.where(row % 2 == 0, 1.0, -1.0)
    s = th * np.maximum(rho, .004) / .0062 + row * .37 + (f - .5) * 1.25 * lean       # strands cross each braid row at a slant, the other way in the next row
    strand = np.floor(s); fs = s - strand
    h = (np.sin(np.pi * fs) ** .7) * (np.sin(np.pi * f) ** .5)
    tone = hash2(strand, row, seed); tone2 = vnoise(u * 9, v * 9, seed + 1); stain = vnoise(u * 3.1, v * 3.1, seed + 2)
    base = np.array([.74, .60, .33], np.float32) if not under else np.array([.62, .50, .27], np.float32)
    col = base[None, None, :] * (.70 + .34 * tone + .16 * (tone2 - .5))[..., None]
    col *= np.array([1.0, .96, .86])[None, None, :] ** ((stain - .45).clip(0, 1) * 2.4)[..., None]      # old straw goes grey-brown in patches
    col *= (.50 + .50 * h ** .6)[..., None]                                                     # the gaps between the strands are dark
    edge = np.clip((rho - (pr['radius'] - .035)) / .035, 0, 1); col *= (1 - .22 * edge * vnoise(th * 9, rho * 40, seed + 3))[..., None]      # the rim is weathered
    if not under:
        r0 = pr['crown_r']; band = np.clip(1 - np.abs(rho - (r0 + .004)) / .008, 0, 1) ** .5      # a dark cord round the foot of the crown
        twist = .5 + .5 * np.sin(th * r0 / .0045 * 2 * np.pi + rho / .002)      # the cord's lay: one turn every 4.5 mm
        cord = np.array([.11, .065, .04])[None, None, :] * (.6 + .6 * twist)[..., None]
        col = col * (1 - band[..., None]) + cord * band[..., None]; h = h * (1 - band) + band * (.5 + .5 * twist)
        col *= (1 - .30 * np.clip(1 - rho / r0, 0, 1) ** .7)[..., None]                         # the crown is worn darker by the hand that lifts it
    rough = .78 - .10 * h + .06 * tone
    return col, h.astype(np.float32), rough


def wood(w, h_px, pr):
    """a peeled pole unrolled: length along x, girth along y"""
    y, x = np.mgrid[0:h_px, 0:w].astype(np.float32); seed = pr['seed']
    g = vnoise(x * .012, y * .55, seed) * .6 + vnoise(x * .05, y * 1.3, seed + 1) * .4      # long streaks of grain
    knots = np.clip(vnoise(x * .02, y * .12, seed + 2) - .78, 0, 1) * 4.0
    col = np.array([.36, .24, .13], np.float32)[None, None, :] * (.62 + .62 * g)[..., None] * (1 - .55 * knots)[..., None]
    grip = np.exp(-((x / w - pr.get('grip_z', 1.05) / pr['length']) / .06) ** 2); col *= (1 - .28 * grip)[..., None]        # darkened where the hand holds it
    foot = np.clip(1 - x / (w * .07), 0, 1); col = col * (1 - .5 * foot[..., None]) + np.array([.10, .08, .06])[None, None, :] * .5 * foot[..., None]      # the foot is dirty
    hgt = (g * .6 + (1 - knots) * .4).astype(np.float32)
    return col, hgt, .62 + .16 * g - .12 * grip


def lathe(profile, nseg, wobble=None):
    """rings of (r, z) about the z axis; wobble(k, j) -> (dr, dz) per ring k and segment j"""
    verts = []; faces = []
    for k, (r, z) in enumerate(profile):
        for j in range(nseg):
            a = 2 * math.pi * j / nseg; dr, dz = wobble(k, j) if wobble else (0.0, 0.0)
            verts.append(((r + dr) * math.cos(a), (r + dr) * math.sin(a), z + dz))
    for k in range(len(profile) - 1):
        for j in range(nseg):
            a = k * nseg + j; b = k * nseg + (j + 1) % nseg; faces.append((a, b, b + nseg, a + nseg))
    return verts, faces


def uv_planar(o, rect, metres, flip):
    """top-down planar UVs into the square at the bottom-left of rect; flip mirrors x (the underside)"""
    u0, v0, side = rect; me = o.data; uvl = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            c = me.vertices[vi].co; uvl.data[li].uv = (u0 + side * (.5 + (-c.x if flip else c.x) / metres), v0 + side * (.5 + c.y / metres))


made = []
if 'hat' in ROW['props']:
    pr = ROW['props']['hat']; R = pr['radius']; r0 = pr['crown_r']; ch = pr['crown_h']; NS = 40
    prof = [(1e-4, ch)] + [(r0 * math.sin(t), ch * (.25 + .75 * math.cos(t) ** .8)) for t in np.linspace(.25, 1.35, 5)] + [(r0, .012), (r0 + .012, 0.0)]
    nb = 7
    for i in range(1, nb + 1):
        t = i / nb; prof.append((r0 + .012 + (R - r0 - .012) * t, -pr['drop'] * t ** 1.6))
    nring = len(prof)
    def wob(k, j):
        t = max(0.0, (k - (nring - nb - 1)) / nb); a = 2 * math.pi * j / NS
        dz = t ** 1.5 * (.010 * math.sin(2 * a + 1.3) + .007 * math.sin(3 * a + 4.1) + .004 * math.sin(7 * a))      # an old brim does not lie in one plane
        dr = t * (.006 * math.sin(5 * a + .7) + .004 * math.sin(11 * a + 2.0)) if k == nring - 1 else 0.0           # nor is its rim a circle
        return dr, dz
    vt, ft = lathe(prof, NS, wob)
    top = new_obj('HatTop', vt, ft)
    und = new_obj('HatUnder', [(x, y, z - .004) for x, y, z in vt], [tuple(reversed(f)) for f in ft])
    # the rim: a strip that joins the two skins
    rim_v = vt[-NS:] + [(x, y, z - .004) for x, y, z in vt[-NS:]]; rim = new_obj('HatRim', rim_v, [(j, j + NS, (j + 1) % NS + NS, (j + 1) % NS) for j in range(NS)])
    u0, v0, u1, v1 = pr['rect']; side = min(u1 - u0, v1 - v0); span = 2 * (R + .012); small = min(v1 - v0 - side, u1 - u0) if (v1 - v0 - side) > .05 else side * .45
    uv_planar(top, (u0, v0, side), span, False); uv_planar(rim, (u0, v0, side), span * .985, False)
    uv_planar(und, (u0, v0 + side, small), span, True)
    px = int(round(side * SIZE)); col, hgt, rough = straw(px, span, pr, False); b = box(u0, v0, u0 + side, v0 + side); paint((b[0], b[3] - px, b[0] + px, b[3]), col, hgt, rough, 2.2)
    px2 = int(round(small * SIZE)); col, hgt, rough = straw(px2, span, pr, True); b = box(u0, v0 + side, u0 + small, v0 + side + small); paint((b[0], b[3] - px2, b[0] + px2, b[3]), col[:, ::-1], hgt[:, ::-1], rough[:, ::-1], 1.6)
    for o in (top, und, rim): o.select_set(True)
    bpy.context.view_layer.objects.active = top; bpy.ops.object.join(); hat = top; hat.name = 'Hat'; hat.data.name = 'Hat'
    for o in bpy.context.selected_objects: o.select_set(False)
    # onto the head: the brim plane `sink` below the top of the skull, tilted back a little
    tilt = math.radians(pr['tilt']); ctr = LM['ctr']; top_z = LM['top']
    for v in hat.data.vertices:
        y, z = v.co.y, v.co.z; v.co.y = y * math.cos(tilt) - z * math.sin(tilt) + ctr[1] - .004; v.co.z = y * math.sin(tilt) + z * math.cos(tilt) + top_z - pr['sink']
    smooth_shade(hat); hat['fabric'] = 'straw'; hat['mat'] = 'gear'; hat['rigidw'] = 'head:1.0'; made.append(hat)
    log('hat', len(hat.data.polygons), 'faces, brim', R, 'crown', r0, 'top square px', px, 'under px', px2)
if 'staff' in ROW['props']:
    pr = ROW['props']['staff']; L = pr['length']; NS = 10; NR = 16; rng = np.random.default_rng(pr['seed'])
    bend = np.cumsum(rng.normal(0, .004, (NR + 1, 2)), axis=0); bend -= np.linspace(0, 1, NR + 1)[:, None] * bend[-1][None, :]      # a pole that is not quite straight, ends on the axis
    verts = []; faces = []
    for k in range(NR + 1):
        t = k / NR; r = pr['radius'] * (1.18 - .36 * t) * (1 + .05 * math.sin(k * 2.3))
        for j in range(NS):
            a = 2 * math.pi * j / NS; verts.append((pr['xy'][0] + bend[k, 0] + r * math.cos(a), pr['xy'][1] + bend[k, 1] + r * math.sin(a), .003 + L * t))
    for k in range(NR):
        for j in range(NS):
            a = k * NS + j; b = k * NS + (j + 1) % NS; faces.append((a, b, b + NS, a + NS))
    faces.append(tuple(range(NS - 1, -1, -1))); faces.append(tuple(range(NR * NS, NR * NS + NS)))
    st = new_obj('Staff', verts, faces); me = st.data; uvl = me.uv_layers.new(name='UVMap')
    u0, v0, u1, v1 = pr['rect']; girth = min(.05, v1 - v0)
    for p in me.polygons:
        js = [vi % NS for vi in p.vertices]; wrap = max(js) - min(js) > NS / 2
        for li, vi in zip(p.loop_indices, p.vertices):
            k, j = divmod(vi, NS); jj = j + NS if wrap and j < NS / 2 else j
            if len(p.vertices) > 4: uvl.data[li].uv = (u0 + (u1 - u0) * (.01 if k == 0 else .99), v0 + girth * (.5 + .3 * math.sin(2 * math.pi * j / NS)))
            else: uvl.data[li].uv = (u0 + (u1 - u0) * (k / NR), v0 + girth * jj / NS)
    b = box(u0, v0, u1, v0 + girth); col, hgt, rough = wood(b[2] - b[0], b[3] - b[1], pr); paint(b, col[::-1], hgt[::-1], rough[::-1], 1.2)
    smooth_shade(st); st['fabric'] = 'wood'; st['mat'] = 'gear'; st['rigidw'] = 'root:1.0'; made.append(st)
    log('staff', len(me.polygons), 'faces, length', L, 'at', pr['xy'])
if 'scarf' in ROW['props']:
    # A neck cloth: a rolled cloth wound once round the neck over the collar, knotted at the throat, two ends lying on the chest.
    # The roll is a tube swept round the neck's axis (lower in front, riding up on the shoulders), twisted folds in its girth,
    # pushed clear of the skin and of the clothes it lies on; the ends are flat sleeves swept down the chest 6 mm off the cloth.
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    pr = ROW['props']['scarf']; rng = np.random.default_rng(pr['seed']); AX = (0.0, 0.010)
    with bpy.data.libraries.load(str(DIR / 'Work' / f'{n_}_head.blend')) as (s_, d_): d_.objects = ['Skin']
    sk_ = d_.objects[0]
    def tree(objs):
        vs = []; fs = []
        for o in objs:
            n0 = len(vs); vs += [v.co.copy() for v in o.data.vertices]; fs += [[n0 + i for i in p.vertices] for p in o.data.polygons]
        return BVHTree.FromPolygons(vs, fs)
    body = tree([sk_] + [D[nm] for nm in ('Jerkin', 'Shirt') if D.get(nm) is not None]); cloth = tree([D[nm] for nm in ('Jerkin', 'Shirt') if D.get(nm) is not None])
    def clear(co, gap):      # a point inside or closer than `gap` to the body or the clothes goes out to `gap` along the surface normal
        for _ in range(3):
            loc, nrm, _i, _d = body.find_nearest(Vector(co))
            if loc is None: break
            d = (Vector(co) - loc).dot(nrm)
            if d >= gap: break
            co = tuple(loc + nrm * gap + (Vector(co) - loc - nrm * d) * 1.0)
        return co
    def sweep(name, path, frames, radii, nseg, closed, phase=0.0, folds=(3, .16), caps=True):
        """a tube along `path` (n,3) with cross-section axes frames[k] = (a, b) unit vectors and radii[k] = (ra, rb); twisted folds in the girth"""
        n = len(path); verts = []; faces = []
        for k in range(n):
            a, b = frames[k]; ra, rb = radii[k]
            for j in range(nseg):
                ph = 2 * math.pi * j / nseg
                f = 1 + folds[1] * math.sin(folds[0] * ph + phase + k * .55) + .07 * math.sin(7 * ph + k * 1.3 + phase)
                verts.append(tuple(np.asarray(path[k]) + (np.asarray(a) * ra * math.cos(ph) + np.asarray(b) * rb * math.sin(ph)) * f))
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            for j in range(nseg):
                j2 = (j + 1) % nseg; faces.append((k * nseg + j, k * nseg + j2, k2 * nseg + j2, k2 * nseg + j))
        if not closed and caps: faces.append(tuple(range(nseg - 1, -1, -1))); faces.append(tuple(range((n - 1) * nseg, n * nseg)))
        return new_obj(name, verts, faces)
    def uv_tube(o, n, nseg, rect, closed, flip=False):
        u0, v0, u1, v1 = rect; me = o.data; uvl = me.uv_layers.new(name='UVMap'); nk = n if closed else n - 1
        for p in me.polygons:
            if len(p.vertices) > 4:
                for li in p.loop_indices: uvl.data[li].uv = (u0 + (u1 - u0) * .5, v0 + (v1 - v0) * .5)
                continue
            ks = [vi // nseg for vi in p.vertices]; js = [vi % nseg for vi in p.vertices]; wk = closed and max(ks) - min(ks) > 1; wj = max(js) - min(js) > 1
            for li, vi in zip(p.loop_indices, p.vertices):
                k, j = divmod(vi, nseg); kk = k + n if wk and k == 0 else k; jj = j + nseg if wj and j == 0 else j
                uvl.data[li].uv = (u0 + (u1 - u0) * kk / nk, v0 + (v1 - v0) * jj / nseg)
    u0, v0, u1, v1 = pr['rect']; h_ring = (v1 - v0) * .50; h_tail = (v1 - v0) * .22
    NR = 36; NS = 10; zf, zs, zb = pr['z']; ra, rb = pr['ring']; tube = pr['tube']; path = []; frames = []; radii = []
    for k in range(NR):
        a = 2 * math.pi * k / NR; c, s_ = math.cos(a), math.sin(a)          # a = 0 in front (-y), pi behind
        z = (zf * max(c, 0) ** 2 + zb * max(-c, 0) ** 2 + zs * s_ ** 2) + .004 * math.sin(3 * a + 1.0)
        rad = np.array([s_ * ra, -c * rb, 0.0]); p_ = np.array([AX[0] + rad[0], AX[1] + rad[1], z])
        tan = np.array([c * ra, s_ * rb, 0.0]); tan /= np.linalg.norm(tan); out = rad / np.linalg.norm(rad)
        knot = math.exp(-(min(a, 2 * math.pi - a) / .30) ** 2)             # the knot: the roll thickens at the throat
        path.append(p_ + out * .006 * knot + np.array([0, 0, -.008 * knot])); frames.append((out, np.array([0.0, 0.0, 1.0]))); radii.append((tube * (.80 + .45 * knot), tube * (1.0 + .30 * knot) * (1 + .10 * math.sin(2 * a + .6))))
    ring = sweep('ScarfRing', path, frames, radii, NS, True, phase=rng.uniform(0, 6.28), folds=(2, .20))
    for v in ring.data.vertices: v.co = clear(tuple(v.co), .007)
    # what the roll hides of the coat goes: in a pose the collar under it came out through the cloth (dark jagged patches in the game)
    import bmesh
    ctr_ = np.array(path); gone = 0
    for nm in ('Jerkin', 'Shirt'):
        o_ = D.get(nm)
        if o_ is None: continue
        bm_ = bmesh.new(); bm_.from_mesh(o_.data)
        def inside(co):
            c_ = np.array(co); d_ = np.linalg.norm(ctr_ - c_[None, :], axis=1); return float(d_.min()) < tube * .80
        dead_ = [f for f in bm_.faces if all(inside(v.co) for v in f.verts)]; gone += len(dead_)
        bmesh.ops.delete(bm_, geom=dead_, context='FACES'); bmesh.ops.delete(bm_, geom=[v for v in bm_.verts if not v.link_faces], context='VERTS'); bm_.to_mesh(o_.data); bm_.free(); o_.data.update()
    log('scarf: coat faces inside the roll removed', gone)
    uv_tube(ring, NR, NS, (u0, v0, u1, v0 + h_ring), True)
    parts_ = [ring]
    for i_, (sx, L) in enumerate(zip((1.0, -1.0), pr['tails'])):
        NT = 9; path = []; frames = []; radii = []
        for k in range(NT):
            t = k / (NT - 1); x = sx * (.014 + .030 * t ** 1.2); z = zf - .012 - L * t
            hit = cloth.ray_cast(Vector((x, -.6, z)), Vector((0, 1, 0)), 1.2); y = (hit[0].y if hit[0] is not None else -.08) - .0075 - .010 * (1 - t) ** 2
            path.append(np.array([x, y, z])); w = .020 + .012 * math.sin(math.pi * min(t * 1.15, 1.0)) ; th = .0055 * (1 - .35 * t)
            if k == NT - 1: w *= .75
            frames.append((np.array([1.0, 0.0, 0.0]), np.array([0.0, -1.0, 0.0]))); radii.append((w, th))
        tail = sweep('ScarfTail%d' % i_, path, frames, radii, 8, False, phase=rng.uniform(0, 6.28), folds=(2, .10))
        for v in tail.data.vertices: v.co = clear(tuple(v.co), .006)
        uv_tube(tail, NT, 8, (u0 + (u1 - u0) * (.52 * i_), v0 + h_ring + .008, u0 + (u1 - u0) * (.52 * i_ + .46), v0 + h_ring + .008 + h_tail), False); parts_.append(tail)
    for o in parts_: o.select_set(True)
    bpy.context.view_layer.objects.active = ring; bpy.ops.object.join(); scarf = ring; scarf.name = 'Scarf'; scarf.data.name = 'Scarf'
    for o in bpy.context.selected_objects: o.select_set(False)
    bpy.data.objects.remove(sk_, do_unlink=True)
    # the cloth: a coarse plain weave, undyed and long unwashed; folds run across the roll (round its girth they are modelled)
    b = box(u0, v0, u1, v1); w_px, h_px = b[2] - b[0], b[3] - b[1]; y, x = np.mgrid[0:h_px, 0:w_px].astype(np.float32)
    weave = (.5 + .5 * np.sin(x * math.pi / 1.5)) * (.5 + .5 * np.sin(y * math.pi / 1.5)); slub = vnoise(x * .9, y * .05, pr['seed']) * .5 + vnoise(x * .05, y * .9, pr['seed'] + 1) * .5
    fold = vnoise(x * .020, y * .11, pr['seed'] + 2) * .65 + vnoise(x * .06, y * .30, pr['seed'] + 3) * .35
    dirt = vnoise(x * .012, y * .012, pr['seed'] + 4)
    col = np.array(pr['col'], np.float32)[None, None, :] * (.70 + .22 * fold + .12 * slub + .06 * weave)[..., None]
    col *= np.array([1.0, .95, .84])[None, None, :] ** (np.clip(dirt - .40, 0, 1) * 2.2)[..., None]
    hgt = (fold * .70 + weave * .18 + slub * .12).astype(np.float32)
    paint(b, col, hgt, .86 - .06 * weave, 2.4)
    smooth_shade(scarf); scarf['fabric'] = 'linen'; scarf['mat'] = 'gear'; made.append(scarf)
    log('scarf', len(scarf.data.polygons), 'faces, ring', pr['ring'], 'tube', tube, 'ends', pr['tails'])
TX = DIR / 'Textures'; TX.mkdir(parents=True, exist_ok=True)
for arr, role in ((bc, 'BC'), (nm_, 'N'), (orm, 'ORM')):
    Image.fromarray((np.clip(arr, 0, 1) * 255 + .5).astype(np.uint8)).save(TX / f'T_{NAME}_PR_Gear_{role}.png', optimize=True)
(DIR / 'Work').mkdir(parents=True, exist_ok=True)
save_blend(filepath=str(DIR / 'Work' / f'{n_}_packed.blend'))
log('packed', NAME, 'junked', len(ROW['junk']), 'made', [o.name for o in made])
