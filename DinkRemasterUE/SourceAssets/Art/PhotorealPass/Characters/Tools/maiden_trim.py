"""The trim of the maidens' dress as a mask over the Mother's outfit atlas (NPC/Maiden/Textures/T_Maiden_PR_Outfit_Trim.png).

The 1997 maidens (pictures 221-259) wear the Mother's cut of dress with a white band closing each puffed sleeve at the
elbow, a pale edge at the neckline and two light stripes round the skirt above the hem. The dress mesh is shared, so the
trim is painted: this stage measures on the dress parts of Mother/Work/mother_packed.blend where the trim lies and
writes it in the atlas's own UVs; npc_variants.py lays white linen and the stripe colour over each twin's dress map.

    blender -b -t 4 --python maiden_trim.py

Red: white linen (sleeve bands `CUFF` metres wide measured from the sleeve's hem, the neckline's edge `COLLAR` wide).
Green: the skirt's stripes (`STRIPES`: height above the hem and width, metres, in the rest pose)."""
import bpy, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from prlib import OUT, log, co_np
from PIL import Image
from mathutils.kdtree import KDTree
SIZE = 2048; CUFF = .032; COLLAR = .011; STRIPES = ((.105, .014), (.150, .007))
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Mother/Work/mother_packed.blend'))
D = bpy.data.objects; mask = np.zeros((SIZE, SIZE, 3), np.float32)


def loops(me):
    """boundary loops as lists of vertex indices"""
    cnt = {}
    for p in me.polygons:
        for k in p.edge_keys: cnt[k] = cnt.get(k, 0) + 1
    nb = {}
    for (a, b), n in cnt.items():
        if n == 1: nb.setdefault(a, []).append(b); nb.setdefault(b, []).append(a)
    seen = set(); out = []
    for s in nb:
        if s in seen: continue
        st = [s]; loop = []
        while st:
            v = st.pop()
            if v in seen: continue
            seen.add(v); loop.append(v); st.extend(nb[v])
        out.append(loop)
    return out


def raster(o, ring, width, channel, soft=.0015):
    """a band `width` metres wide along the ring of vertices, drawn per texel: every texel of the part's UV triangles
    takes its own place on the cloth and its distance to the ring (per-vertex weights smeared the edge over a whole
    polygon of this coarse dress: a white fringe instead of a sewn band)"""
    me = o.data; me.calc_loop_triangles(); uvl = me.uv_layers['UVMap'].data; co = co_np(me); rs = set(ring); pts = []
    for e in me.edges:      # the ring as points every millimetre along its edges
        a_, b_ = e.vertices
        if a_ in rs and b_ in rs:
            n = max(2, int(np.linalg.norm(co[b_] - co[a_]) / .001)); pts.extend(co[a_] + (co[b_] - co[a_]) * t for t in np.linspace(0, 1, n))
    kd = KDTree(len(pts))
    for i, p in enumerate(pts): kd.insert(p, i)
    kd.balance(); rc = co[ring]
    for t in me.loop_triangles:
        P = co[list(t.vertices)]
        if np.sqrt(((P[:, None, :] - rc[None, :, :]) ** 2).sum(2)).min() > width + .08: continue
        q = np.array([uvl[l].uv[:] for l in t.loops]) * SIZE; q[:, 1] = SIZE - q[:, 1]
        x0, y0 = np.floor(q.min(0)).astype(int) - 1; x1, y1 = np.ceil(q.max(0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, SIZE - 1), min(y1, SIZE - 1)
        d = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
        if abs(d) < 1e-9: continue
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                px, py = xx + .5, yy + .5
                a = ((q[1, 1] - q[2, 1]) * (px - q[2, 0]) + (q[2, 0] - q[1, 0]) * (py - q[2, 1])) / d
                b = ((q[2, 1] - q[0, 1]) * (px - q[2, 0]) + (q[0, 0] - q[2, 0]) * (py - q[2, 1])) / d
                c = 1 - a - b
                if a < -.03 or b < -.03 or c < -.03: continue        # a hair over the edge: no unpainted seam texels
                dist = kd.find(P[0] * a + P[1] * b + P[2] * c)[2]
                v = min(max((width + soft - dist) / soft, 0.0), 1.0)
                if v > mask[yy, xx, channel]: mask[yy, xx, channel] = v


for nm in ('Sleeve_l', 'Sleeve_r'):
    o = D[nm]; co = co_np(o.data); ls = loops(o.data)
    hem = max(ls, key=lambda l: np.abs(co[l, 0]).mean())            # the loop farther out along the arm
    raster(o, hem, CUFF, 0); log('cuff', nm, 'hem loop', len(hem), 'x', round(float(np.abs(co[hem, 0]).mean()), 3))
o = D['Bodice']; co = co_np(o.data); ls = [l for l in loops(o.data) if len(l) > 12]
neck = max(ls, key=lambda l: co[l, 2].mean() - 2.0 * np.abs(co[l, 0].mean()))      # the high loop that is centred on the body, not an armhole
raster(o, neck, COLLAR, 0); log('neckline loop', len(neck), 'z', round(float(co[neck, 2].mean()), 3), 'of loops', [len(l) for l in ls])
o = D['Skirt']; co = co_np(o.data); z0 = float(co[:, 2].min())
me = o.data; me.calc_loop_triangles(); uvl = me.uv_layers['UVMap'].data
for t in me.loop_triangles:      # stripes by the texel's own height above the hem (per-vertex weights would smear a 7 mm stripe over a 5 cm ring)
    zs = np.array([co[v][2] for v in t.vertices]) - z0
    if zs.min() > .2 or zs.max() < .08: continue
    q = np.array([uvl[l].uv[:] for l in t.loops]) * SIZE; q[:, 1] = SIZE - q[:, 1]
    x0, y0 = np.floor(q.min(0)).astype(int) - 1; x1, y1 = np.ceil(q.max(0)).astype(int) + 1
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, SIZE - 1), min(y1, SIZE - 1)
    ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]; px = xs + .5; py = ys + .5
    d = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
    if abs(d) < 1e-9: continue
    a = ((q[1, 1] - q[2, 1]) * (px - q[2, 0]) + (q[2, 0] - q[1, 0]) * (py - q[2, 1])) / d
    b = ((q[2, 1] - q[0, 1]) * (px - q[2, 0]) + (q[0, 0] - q[2, 0]) * (py - q[2, 1])) / d
    c = 1 - a - b; ins = (a >= -.02) & (b >= -.02) & (c >= -.02); z = a * zs[0] + b * zs[1] + c * zs[2]; val = np.zeros_like(z)
    for h, wd in STRIPES: val = np.maximum(val, np.clip((wd / 2 + .0015 - np.abs(z - h)) / .0015, 0, 1))
    blk = mask[y0:y1 + 1, x0:x1 + 1, 1]; blk[ins] = np.maximum(blk[ins], val[ins])
dst = OUT / 'NPC/Maiden/Textures/T_Maiden_PR_Outfit_Trim.png'
Image.fromarray((mask * 255 + .5).astype(np.uint8)).save(dst, optimize=True)
log('trim mask', dst.name, 'linen share', round(float(mask[..., 0].mean()), 4), 'stripe share', round(float(mask[..., 1].mean()), 4))
