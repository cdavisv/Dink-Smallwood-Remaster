"""hairlib: strand grooms on Blender hair Curves (guides on a scalp surface, children / clump / frizz / noise from the
bundled procedural hair node groups), a strand-rendered card atlas, and hair cards derived from the same guide curves.
Used by hair_groom.py."""
import bpy, bmesh, math, json, os, sys
import numpy as np
from prlib import *
from garlib import sstep, fbm, vnoise
HAIR_ASSETS = Path(bpy.utils.system_resource('DATAFILES')) / 'assets/nodes/procedural_hair_node_assets.blend'

def unit(v):
    return v / max(float(np.linalg.norm(v)), 1e-12)

def f1(p, scale, seed, octs=2):
    return float(fbm(np.asarray(p, np.float64)[None, :], scale, octs, seed)[0])

# ------------------------------------------------------------------ head / scalp
class Head:
    def __init__(s, sk, LM, HL):
        s.sk = sk; s.nose = np.array(LM['nose']); s.top = float(LM['top']); s.back = float(LM['back']); s.ctr = np.array(LM['ctr']); s.HL = HL
        s.eyes = {int(k): (np.array(v[0]), v[1]) for k, v in LM['eyes'].items()}
        s.bvh = bvh_of(sk)
    def hairline(s, d):
        a = abs(math.atan2(d[0], -d[1])); front, side, backv = s.HL[:3]
        if a < 1.15: t = a / 1.15; t = t * t * (3 - 2 * t); return front + (side - front) * t
        t = (a - 1.15) / (math.pi - 1.15); t = t * t * (3 - 2 * t); return side + (backv - side) * t
    def params(s, p):
        d = np.asarray(p) - s.ctr; d = d / np.linalg.norm(d); az = math.atan2(d[0], -d[1])
        return az, (1 - d[2]) / (1 - s.hairline(d))
    def near(s, p):
        loc, nrm, _, dist = s.bvh.find_nearest(Vector(p)); return np.array(loc), np.array(nrm)

def build_scalp(H, name='Scalp', split_part=False, edge_noise=.05, seed=0, fade=.90):
    """Scalp surface = head skin faces inside the hairline; UV = azimuthal projection (unique); 'dens' = hairline falloff."""
    me = H.sk.data; co = co_np(me); vn = normals_np(me)
    pe = np.full(len(co), 9.0); paz = np.zeros(len(co))
    for i in np.nonzero(co[:, 2] > 1.53)[0]:
        paz[i], pe[i] = H.params(co[i])
    verts = {}; faces = []
    for p in me.polygons:
        idx = list(p.vertices)
        if max(pe[i] for i in idx) > 1.06: continue
        c = co[idx].mean(0); d = unit(c - H.ctr)
        if np.array(p.normal) @ d < .1: continue
        faces.append([verts.setdefault(i, len(verts)) for i in idx])
    order = sorted(verts, key=verts.get); P = co[order]
    o = new_obj(name, P, faces)
    if split_part:   # two mesh islands either side of the centre line -> children never blend across the parting
        bm = bmesh.new(); bm.from_mesh(o.data)
        es = [e for e in bm.edges if len(e.link_faces) == 2 and (e.link_faces[0].calc_center_median().x > 0) != (e.link_faces[1].calc_center_median().x > 0)
              and e.link_faces[0].calc_center_median().y < H.ctr[1] + split_part]
        bmesh.ops.split_edges(bm, edges=es); bm.to_mesh(o.data); bm.free()
    m2 = o.data; c2 = co_np(m2)
    d = c2 - H.ctr; d /= np.linalg.norm(d, axis=1)[:, None]; th = np.arccos(np.clip(d[:, 2], -1, 1)); az = np.arctan2(d[:, 0], -d[:, 1])
    uvv = np.c_[.5 + .5 * th / math.pi * np.sin(az), .5 - .5 * th / math.pi * np.cos(az)]
    uvl = m2.uv_layers.new(name='UVMap')
    li = np.empty(len(m2.loops), np.int32); m2.loops.foreach_get('vertex_index', li)
    uvl.data.foreach_set('uv', uvv[li].astype(np.float32).ravel())
    e2 = np.array([H.params(p)[1] for p in c2])
    nz = fbm(c2, 55, 3, 400 + seed) - .5 + (vnoise(c2, 260, 401 + seed) - .5) * .5
    dens = 1 - sstep(fade, 1.0, e2 + nz * edge_noise * 2)
    a = m2.attributes.new('dens', 'FLOAT', 'POINT'); a.data.foreach_set('value', dens.astype(np.float32))
    smooth_shade(o); o.hide_render = True
    o['e'] = 1
    return o

class Roots:
    """Area-weighted root sampling on the scalp mesh, with az/e filters."""
    def __init__(s, H, scalp, rng):
        me = scalp.data; me.calc_loop_triangles(); co = co_np(me)
        uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
        n = len(me.loop_triangles); tv = np.empty(n * 3, np.int32); me.loop_triangles.foreach_get('vertices', tv); tl = np.empty(n * 3, np.int32); me.loop_triangles.foreach_get('loops', tl)
        s.P = co[tv].reshape(n, 3, 3); s.UV = uv[tl].reshape(n, 3, 2)
        s.area = np.linalg.norm(np.cross(s.P[:, 1] - s.P[:, 0], s.P[:, 2] - s.P[:, 0]), axis=1) / 2
        c = s.P.mean(1); ae = np.array([H.params(p) for p in c]); s.az = ae[:, 0]; s.e = ae[:, 1]; s.rng = rng; s.total = s.area.sum()
    def sample(s, n, e0=0.0, e1=1.0, azmin=0.0, azmax=4.0, wfun=None):
        m = (s.e >= e0) & (s.e <= e1) & (np.abs(s.az) <= azmax) & (np.abs(s.az) >= azmin)
        idx = np.nonzero(m)[0]
        if not len(idx) or n <= 0: return []
        w = s.area[idx].copy()
        if wfun is not None: w *= np.array([wfun(s.az[i], s.e[i]) for i in idx])
        pick = s.rng.choice(idx, n, p=w / w.sum()); out = []
        for i in pick:
            r1, r2 = s.rng.random(2)
            if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
            b = np.array([1 - r1 - r2, r1, r2]); out.append((b @ s.P[i], b @ s.UV[i]))
        return out

def grow(H, root, d0, L, K=10, gravity=.5, minlift=(.0006, .003), wander=.0, rng=None, target=None, pull=.6, stop_r=.0, noise_seed=0, wave=None, maxlift=None):
    """March a guide from a scalp root. Keeps clear of the head (min lift profile root->tip). Returns (K,3)."""
    p = np.array(root, float); d = unit(np.array(d0, float)); pts = [p.copy()]; step = L / (K - 1)
    mind = 9.0; done = False
    for k in range(1, K):
        t = k / (K - 1)
        if target is not None:
            loc, nrm = H.near(p); tg = target - p; dist = np.linalg.norm(tg)
            if dist > .05: tg = tg - nrm * (tg @ nrm)          # far away: steer along the scalp; close: straight at the knot
            mind = min(mind, dist)
            if dist < stop_r or done or (mind < .08 and dist > mind + .003):
                done = True; pts.append(pts[-1].copy()); continue
            d = unit(d * (1 - pull) + unit(tg) * pull)
        d = d + np.array([0, 0, -1.0]) * gravity * step * 14 * (.3 + .7 * t)
        if wander and rng is not None: d = d + rng.normal(0, wander, 3)
        if wave is not None:
            loc, nrm = H.near(p); side = unit(np.cross(nrm, d)); d = d + side * wave[0] * math.sin(wave[2] + t * wave[1])
        d = unit(d); p = p + d * step
        loc, nrm = H.near(p); h = (p - loc) @ nrm; ml = minlift[0] + (minlift[1] - minlift[0]) * t
        if h < ml:
            p = loc + nrm * ml
            dn = d @ nrm
            if dn < 0: d = unit(d - nrm * dn)
        elif maxlift is not None and h > maxlift[0] + (maxlift[1] - maxlift[0]) * t:      # combed, tied hair hugs the head
            mx = maxlift[0] + (maxlift[1] - maxlift[0]) * t; p = loc + nrm * mx; d = unit(d - nrm * (d @ nrm))
        pts.append(p.copy())
    return np.array(pts)

# ------------------------------------------------------------------ curves + node groups
def make_curves(name, P, radius=4e-5, surface=None, root_uv=None, cattrs=None):
    """P: (n,K,3). Hair Curves object; optional attachment surface + surface_uv_coordinate; cattrs: per-curve float/colour."""
    P = np.asarray(P, np.float32); n, K = P.shape[:2]
    cd = bpy.data.hair_curves.new(name); cd.add_curves([K] * n)
    cd.attributes['position'].data.foreach_set('vector', P.ravel())
    ra = cd.attributes.get('radius') or cd.attributes.new('radius', 'FLOAT', 'POINT')
    r = np.asarray(radius, np.float32); ra.data.foreach_set('value', (np.full(n * K, float(r), np.float32) if r.ndim == 0 else r.ravel()))
    if root_uv is not None:
        a = cd.attributes.new('surface_uv_coordinate', 'FLOAT2', 'CURVE'); a.data.foreach_set('vector', np.asarray(root_uv, np.float32).ravel())
    for k, v in (cattrs or {}).items():
        v = np.asarray(v, np.float32)
        if v.ndim == 1: cd.attributes.new(k, 'FLOAT', 'CURVE').data.foreach_set('value', v)
        else: cd.attributes.new(k, 'FLOAT_COLOR', 'CURVE').data.foreach_set('color', np.c_[v, np.ones(n, np.float32)].ravel() if v.shape[1] == 3 else v.ravel())
    o = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(o)
    if surface is not None: cd.surface = surface; cd.surface_uv_map = 'UVMap'
    return o

_groups = {}
def hair_group(name):
    if name not in _groups:
        if name not in bpy.data.node_groups:
            with bpy.data.libraries.load(str(HAIR_ASSETS)) as (s, d): d.node_groups = [name]
        _groups[name] = bpy.data.node_groups[name]
    return _groups[name]

def gn_chain(o, name, steps, material=None, surface=None, resample=0, streak=None):
    """Geometry-nodes modifier: [Set Attachment Surface] -> the given procedural hair groups in order -> material.
    steps: [(group name, {input name: value | ('attr', name) | ('surf', name)})]"""
    nt = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    nt.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry'); nt.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = nt.nodes.new('NodeGroupInput'); go = nt.nodes.new('NodeGroupOutput'); cur = gi.outputs[0]
    def group(gname, vals):
        nonlocal cur
        n = nt.nodes.new('GeometryNodeGroup'); n.node_tree = hair_group(gname); nt.links.new(cur, n.inputs[0])
        for k, v in vals.items():
            if isinstance(v, tuple) and v and v[0] == 'attr':
                a = nt.nodes.new('GeometryNodeInputNamedAttribute'); a.data_type = v[2] if len(v) > 2 else 'FLOAT'; a.inputs[0].default_value = v[1]; nt.links.new(a.outputs[0], n.inputs[k])
            else:
                try: n.inputs[k].default_value = v
                except Exception as ex: log('gn input failed', gname, k, v, ex)
        cur = n.outputs[0]; return n
    if surface is not None:
        group('Set Attachment Surface', {'Mode': 'Object', 'Surface Object': surface, 'Surface UV Map': ('attr', 'UVMap', 'FLOAT_VECTOR')})
    for i, (gname, vals) in enumerate(steps):
        group(gname, vals)
        if resample and gname in ('Interpolate Hair Curves', 'Duplicate Hair Curves'):
            rs = nt.nodes.new('GeometryNodeResampleCurve'); nt.links.new(cur, rs.inputs[0])
            try: rs.inputs['Count'].default_value = resample
            except Exception: pass
            cur = rs.outputs[0]
            if streak is not None:   # per-curve coherent streak value (grey streaks): noise of the root position, stored before clumping
                nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = streak; nz.inputs['Detail'].default_value = 1.0
                st = nt.nodes.new('GeometryNodeStoreNamedAttribute'); st.data_type = 'FLOAT'; st.domain = 'CURVE'; st.inputs['Name'].default_value = 'streak'
                nt.links.new(cur, st.inputs[0]); nt.links.new(nz.outputs[0], st.inputs['Value']); cur = st.outputs[0]
    if material is not None:
        sm = nt.nodes.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = material; nt.links.new(cur, sm.inputs[0]); cur = sm.outputs[0]
    nt.links.new(cur, go.inputs[0])
    m = o.modifiers.new(name, 'NODES'); m.node_group = nt
    return m

def strand_material(name, melanin=.5, redness=.8, rough=.3, radial=.35, rand_col=.12, grey=0.0, tint=(1, 1, 1), coat=.0):
    """Principled Hair BSDF (melanin model); 'streak' curve attribute turns a fraction of strands grey."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); h = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
    h.parametrization = 'MELANIN'
    try: h.model = 'CHIANG'
    except Exception: pass
    h.inputs['Melanin'].default_value = melanin; h.inputs['Melanin Redness'].default_value = redness; h.inputs['Roughness'].default_value = rough
    h.inputs['Radial Roughness'].default_value = radial; h.inputs['Random Color'].default_value = rand_col; h.inputs['Random Roughness'].default_value = .25
    h.inputs['Coat'].default_value = coat; h.inputs['Tint'].default_value = (*tint, 1)
    if grey > 0:
        ci = nt.nodes.new('ShaderNodeHairInfo'); at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'streak'
        # grey where (random*.6 + streak*.6) under a threshold
        ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'
        m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = .55; nt.links.new(ci.outputs['Random'], m1.inputs[0])
        m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.inputs[1].default_value = .75; nt.links.new(at.outputs['Fac'], m2.inputs[0])
        nt.links.new(m1.outputs[0], ad.inputs[0]); nt.links.new(m2.outputs[0], ad.inputs[1])
        lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = .30 + grey * 1.1; nt.links.new(ad.outputs[0], lt.inputs[0])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'FLOAT'; mx.inputs['A'].default_value = melanin; mx.inputs['B'].default_value = .035
        nt.links.new(lt.outputs[0], mx.inputs['Factor']); nt.links.new(mx.outputs[0], h.inputs['Melanin'])
    nt.links.new(h.outputs[0], out.inputs[0]); return m

# ------------------------------------------------------------------ card atlas (strand clumps rendered orthographically)
ATLAS = 4096
# atlas layout (uv): cap texture u 0-.5, v .5-1 (the whole groom projected azimuthally about the head centre);
# 32 narrow card tiles (128 x 1536 px) in u .5-1, v .25-1; 4 wide tiles (512 x 1024 px) in u 0-.5, v .25-.5; bottom quarter = brow / lash band
CAP_RECT = (0.0, .5, .5, 1.0)
NARROW = 32
def tile_rect(i):
    """uv rect (u0, v_root, u1, v_tip) of tile i; the root is at the top. 0..31 narrow lock tiles, 32..35 wide tiles."""
    if i < NARROW:
        c, r = i % 16, i // 16
        return .5 + c / 32, 1 - r * .375, .5 + (c + 1) / 32, 1 - (r + 1) * .375
    j = i - NARROW
    return j * .125, .5, (j + 1) * .125, .25

class CapMap:
    """Azimuthal projection of the hair volume about the head centre: direction -> cap uv, radial height above the skull."""
    def __init__(s, H, G=384):
        s.H = H; s.G = G; s.th_max = 2.2; s.rs = None
    def dirs(s, cu, cv):
        x = (cu - .5) * 2; y = (cv - .5) * 2; rho = np.hypot(x, y); az = np.arctan2(x, -y); th = rho * s.th_max
        return np.stack([np.sin(th) * np.sin(az), -np.sin(th) * np.cos(az), np.cos(th)], -1)
    def uv(s, P):
        d = np.asarray(P) - s.H.ctr; r = np.linalg.norm(d, axis=-1); d = d / np.maximum(r, 1e-9)[..., None]
        th = np.arccos(np.clip(d[..., 2], -1, 1)); az = np.arctan2(d[..., 0], -d[..., 1]); rho = th / s.th_max
        return .5 + .5 * rho * np.sin(az), .5 - .5 * rho * np.cos(az), r
    def cast(s, d):
        """skull point and outward normal along direction d from the head centre (inside-out ray)."""
        loc, nrm, _, _ = s.H.bvh.ray_cast(Vector(s.H.ctr), Vector(d), .4)
        if loc is None: loc, nrm = s.H.near(s.H.ctr + np.asarray(d) * .1); loc = Vector(loc); nrm = Vector(nrm)
        nrm = np.array(nrm); loc = np.array(loc)
        if nrm @ np.asarray(d) < 0: nrm = -nrm
        return loc, nrm
    def build_skull(s):
        G = s.G; g = (np.arange(G) + .5) / G; cu, cv = np.meshgrid(g, g); D = s.dirs(cu, cv); R_ = np.zeros((G, G), np.float32)
        for i in range(G):
            for j in range(G):
                loc, _ = s.cast(D[i, j]); R_[i, j] = np.linalg.norm(loc - s.H.ctr)
        s.rs = R_
    def lookup(s, grid, cu, cv):
        G = grid.shape[0]; x = np.clip(np.asarray(cu) * G - .5, 0, G - 1.001); y = np.clip(np.asarray(cv) * G - .5, 0, G - 1.001)
        x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
        return grid[y0, x0] * (1 - fx) * (1 - fy) + grid[y0, x0 + 1] * fx * (1 - fy) + grid[y0 + 1, x0] * (1 - fx) * fy + grid[y0 + 1, x0 + 1] * fx * fy
    def fields(s, P):
        """P (n,K,3) strand points -> per point cap uv + radial height; stores the height / density grids used by the cap mesh."""
        cu, cv, r = s.uv(P); h = np.clip(r - s.lookup(s.rs, cu, cv), 0, None)
        G = 192; ix = np.clip((cu * G).astype(int), 0, G - 1).ravel(); iy = np.clip((cv * G).astype(int), 0, G - 1).ravel()
        hm = np.zeros((G, G), np.float32); np.maximum.at(hm, (iy, ix), h.ravel().astype(np.float32)); cnt = np.zeros((G, G), np.float32); np.add.at(cnt, (iy, ix), 1.0)
        occ = (cnt > 0).astype(np.float32); s.hgrid = _blur(hm, 3) / np.maximum(_blur(occ, 3), .08); s.dgrid = np.clip(_blur(np.minimum(cnt / max(float(np.percentile(cnt[cnt > 0], 50)), 1.0), 1.0), 2), 0, 1)
        # scalp region = where the roots are: only there the cap gets its opaque under-fill
        rx = np.clip((cu[:, 0] * G).astype(int), 0, G - 1); ry = np.clip((cv[:, 0] * G).astype(int), 0, G - 1); rc = np.zeros((G, G), np.float32); np.add.at(rc, (ry, rx), 1.0)
        s.rgrid = np.clip(_blur((rc > 0).astype(np.float32), 2) * 1.6 - .3, 0, 1)
        s.hmax = float(np.percentile(h, 99.5)); return cu, cv, h

def evaluated_strands(o, K=14):
    """Evaluated hair Curves of an object as (n,K,3), resampled by index to K points."""
    dg = bpy.context.evaluated_depsgraph_get(); ed = o.evaluated_get(dg).data; n = len(ed.curves)
    pp = np.empty(len(ed.points) * 3, np.float32); ed.attributes['position'].data.foreach_get('vector', pp); pp = pp.reshape(-1, 3).astype(np.float64)
    off = np.empty(n + 1, np.int32); ed.curve_offset_data.foreach_get('value', off); cnt = np.diff(off)
    t = np.linspace(0, 1, K)[None, :] * (cnt[:, None] - 1); i0 = np.clip(np.floor(t).astype(int), 0, np.maximum(cnt[:, None] - 2, 0)); f = (t - i0)[..., None]
    a = pp[off[:-1, None] + i0]; b = pp[np.minimum(off[:-1, None] + i0 + 1, off[1:, None] - 1)]
    return a * (1 - f) + b * f

def tile_strands(rng, kind, sty, K=14):
    """Flat strand clump for one tile, in tile units x in [-.5,.5], t in [0,1] root->tip, depth y in [0,1]. Returns list of (K,3), widths."""
    kinds = {  # n strands, coverage half-width, locks, tip raggedness, root spread along the length, strand radius scale
        'dense': (sty.get('n_dense', 260), .47, 6, .22, .45, 1.0),
        'mid': (sty.get('n_mid', 120), .42, 4, .45, .30, 1.0),
        'thin': (sty.get('n_thin', 46), .36, 3, .7, .15, .9),
        'wisp': (sty.get('n_wisp', 18), .32, 3, .5, .05, .75),
        'fly': (sty.get('n_fly', 7), .30, 7, .3, .0, .7),
        'fill': (sty.get('n_dense', 260), .47, 6, .0, .0, 1.0),      # a soft-edged patch of parallel strands (short crops): fades at root, tip and sides
        # narrow lock tiles (one card = a clump of 20-70 hairs, 6-10 mm wide)
        'n_dense': (sty.get('nn_dense', 70), .42, 2, .30, .22, 1.0),
        'n_mid': (sty.get('nn_mid', 40), .40, 2, .45, .18, 1.0),
        'n_thin': (sty.get('nn_thin', 22), .34, 2, .6, .10, .95),
        'n_wisp': (sty.get('nn_wisp', 10), .28, 2, .5, .05, .85),
        'n_fly': (sty.get('nn_fly', 4), .22, 3, .3, .0, .8),
    }
    nk = sty.get('narrow_k', 2.2) if kind.startswith('n_') else 1.0
    n, hw, nl, rag, along, rs = kinds[kind]
    lc = rng.uniform(-hw * .85, hw * .85, nl); lt = lc * rng.uniform(.55, 1.0, nl) + rng.normal(0, .03, nl)   # lock centre at root / tip
    if kind == 'dense': lt = lc + rng.normal(0, .02, nl)
    lw = rng.uniform(.5, 1.0, nl); wave_a = nk * sty.get('wave', .02) * rng.uniform(.4, 1.5, nl); wave_f = rng.uniform(.6, 1.8, nl) * sty.get('wave_f', 1.0); wave_p = rng.uniform(0, 6.28, nl)
    out = []; rad = []
    for i in range(n):
        l = int(rng.integers(nl)); spread = hw / nl * (1.25 if kind in ('dense', 'mid') else .8) * lw[l]
        x0 = lc[l] + rng.normal(0, spread); t0 = rng.uniform(0, along) ** 1.5 if along else 0.0
        if kind == 'dense': x0 = rng.uniform(-hw, hw); t0 = rng.uniform(0, along)
        if kind in ('n_dense', 'n_mid'): x0 = lc[l] * .5 + rng.normal(0, hw * .5)
        if kind == 'fill': x0 = float(np.clip(rng.normal(0, hw * .55), -hw, hw)); t0 = rng.uniform(0, .38) ** 1.4
        x0 = float(np.clip(x0, -hw, hw))
        t1 = 1 - rag * rng.uniform(0, 1) ** 1.25
        if kind == 'dense': t1 = min(1.0, t0 + rng.uniform(.45, 1.0)) if rng.random() < .6 else 1 - rag * rng.uniform(0, 1) ** 2
        if kind == 'fill': t1 = 1 - rng.uniform(0, .38) ** 1.4
        if sty.get('smooth') and kind.startswith('n_'): t0 = 0.0 if rng.random() < .8 else rng.uniform(0, .5); t1 = 1 - sty['smooth'] * rag * rng.uniform(0, 1) ** 2      # combed long hair: full-length strands
        if t1 - t0 < .2: t1 = min(1.0, t0 + .2)
        tt = np.linspace(0, 1, K); t = t0 + (t1 - t0) * tt
        conv = sstep(.25, 1.0, tt) * ({'dense': .15, 'fill': .08, 'mid': .4, 'thin': .55, 'n_dense': .12, 'n_mid': .22, 'n_thin': .32, 'n_wisp': .4, 'n_fly': .3}.get(kind, .75)) * sty.get('clump', 1.0)
        xt = lt[l] + (x0 - lc[l]) * (.35 if kind not in ('dense', 'fill') else .9)
        x = x0 + (xt - x0) * conv + wave_a[l] * np.sin(wave_p[l] + t * 6.28 * wave_f[l]) * tt
        fz = nk * sty.get('frizz', .012) * (1.6 if kind in ('fly', 'wisp', 'n_fly', 'n_wisp') else 1.0)
        x = x + np.cumsum(rng.normal(0, fz, K)) * .45 + rng.normal(0, fz * .35, K)
        x = x + rng.normal(0, nk * sty.get('stray', .02)) * tt ** 1.5 * (3 if rng.random() < .08 else 1)
        y = np.clip(rng.uniform(.05, .95) + np.cumsum(rng.normal(0, .02, K)), 0, 1)
        if kind == 'dense' and rng.random() < .5: y = y * .5      # an under layer that fills the tile
        out.append(np.c_[np.clip(x, -.49, .49), y, t]); rad.append(rs * rng.uniform(.8, 1.15))
    return out, rad

def render_atlas(path_prefix, sty, rng, tiles, col_fun, card_w=.028, card_l=.085, band=None, samples=24, cap=None):
    """Builds every tile's strand clump as hair Curves in one scene, renders colour+alpha / depth-id-intercept with an
    orthographic Cycles camera, and composes BC(+alpha), N, ORM and MSK (R depth, G strand id, B root-to-tip)."""
    sc = bpy.data.scenes.new('Atlas'); win = bpy.context.window; prev = win.scene; win.scene = sc
    S = 1.0                                           # scene units: the atlas is 1 x 1 in the XZ plane
    P = []; R = []; C = []; ID = []
    base_r = sty.get('strand_px', 1.25) / ATLAS / 2
    for i, kind in enumerate(tiles):
        if kind is None: continue
        u0, v0, u1, v1 = tile_rect(i); st, rd = tile_strands(rng, kind, sty)
        for s_, r_ in zip(st, rd):
            x = u0 + (s_[:, 0] + .5) * (u1 - u0); z = v0 + s_[:, 2] * (v1 - v0) * .985 - .002
            P.append(np.c_[x, -s_[:, 1] * .05, z]); tt = np.linspace(0, 1, len(x))
            R.append(base_r * r_ * (1 - .8 * sstep(.6, 1.0, tt)) * (.6 + .4 * sstep(0, .08, tt)))
            C.append(col_fun(rng)); ID.append(rng.random())
    if band is not None:
        for s_ in band:   # dict(P (K,3) in atlas uv + depth, r px, col)
            P.append(np.c_[s_['P'][:, 0], -s_['P'][:, 2] * .05, s_['P'][:, 1]]); K = len(s_['P']); tt = np.linspace(0, 1, K)
            R.append(np.full(K, s_['r'] / ATLAS / 2) * (1 - .85 * sstep(.45, 1.0, tt))); C.append(s_['col']); ID.append(rng.random())
    if cap is not None:   # the whole groom, projected into the cap rect: dict(P (n,K,3) = atlas u, nearness 0..1, atlas v; col (n,3); r_px)
        Kc = cap['P'].shape[1]; tt = np.linspace(0, 1, Kc); rr = cap.get('r_px', 2.0) / ATLAS / 2 * (1 - .7 * sstep(.7, 1.0, tt))
        for q in range(len(cap['P'])):
            c_ = cap['P'][q]; P.append(np.c_[c_[:, 0], -c_[:, 1] * .05, c_[:, 2]]); R.append(rr); C.append(cap['col'][q]); ID.append(rng.random())
    K = max(len(p) for p in P)
    def rs(a):
        a = np.asarray(a, float)
        if len(a) == K: return a
        ti = np.linspace(0, len(a) - 1, K); i0 = np.floor(ti).astype(int).clip(0, len(a) - 2); f = ti - i0
        return a[i0] * (1 - f)[..., None] + a[i0 + 1] * f[..., None] if a.ndim == 2 else a[i0] * (1 - f) + a[i0 + 1] * f
    P = np.array([rs(p) for p in P]); R = np.array([rs(r) for r in R])
    cd = bpy.data.hair_curves.new('AtlasStrands'); cd.add_curves([K] * len(P))
    cd.attributes['position'].data.foreach_set('vector', P.astype(np.float32).ravel())
    (cd.attributes.get('radius') or cd.attributes.new('radius', 'FLOAT', 'POINT')).data.foreach_set('value', R.astype(np.float32).ravel())
    cd.attributes.new('col', 'FLOAT_COLOR', 'CURVE').data.foreach_set('color', np.c_[np.array(C), np.ones(len(C))].astype(np.float32).ravel())
    cd.attributes.new('sid', 'FLOAT', 'CURVE').data.foreach_set('value', np.array(ID, np.float32))
    o = bpy.data.objects.new('AtlasStrands', cd); sc.collection.objects.link(o)
    mat = bpy.data.materials.new('AtlasEmit'); mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(em.outputs[0], out.inputs[0])
    acol = nt.nodes.new('ShaderNodeAttribute'); acol.attribute_name = 'col'; asid = nt.nodes.new('ShaderNodeAttribute'); asid.attribute_name = 'sid'
    hi = nt.nodes.new('ShaderNodeHairInfo'); geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
    dm = nt.nodes.new('ShaderNodeMath'); dm.operation = 'MULTIPLY_ADD'; dm.inputs[1].default_value = -20.0; dm.inputs[2].default_value = 0.0; nt.links.new(sep.outputs[1], dm.inputs[0])   # y in [-.05,0] -> depth 0 (far) .. 1 (near)
    comb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(dm.outputs[0], comb.inputs[0]); nt.links.new(asid.outputs['Fac'], comb.inputs[1]); nt.links.new(hi.outputs['Intercept'], comb.inputs[2])
    cd.materials.append(mat)
    cam = bpy.data.cameras.new('AtlasCam'); cam.type = 'ORTHO'; cam.ortho_scale = 1.0; co_ = bpy.data.objects.new('AtlasCam', cam); sc.collection.objects.link(co_)
    co_.location = (.5, -1, .5); co_.rotation_euler = (math.pi / 2, 0, 0); sc.camera = co_
    sc.render.engine = 'CYCLES'; use_hip_gpu(sc); sc.cycles.samples = samples; sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False
    sc.cycles.max_bounces = 0; sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = ATLAS; sc.render.resolution_percentage = 100
    sc.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'; sc.cycles.filter_width = 1.2
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
    try: sc.display_settings.display_device = 'sRGB'
    except Exception: pass
    w = bpy.data.worlds.new('AtlasW'); sc.world = w
    def shot(sock, tag):
        for l in list(em.inputs[0].links): nt.links.remove(l)
        nt.links.new(sock, em.inputs[0]); f = str(path_prefix) + '_tmp_' + tag + '.exr'; sc.render.filepath = f
        bpy.ops.render.render(write_still=True, scene=sc.name)
        im = bpy.data.images.load(f); a = np.empty(ATLAS * ATLAS * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im); os.remove(f)
        return a.reshape(ATLAS, ATLAS, 4)
    gr = nt.nodes.new('ShaderNodeMath'); gr.operation = 'MULTIPLY_ADD'; gr.inputs[1].default_value = sty.get('tip_gain', .55); gr.inputs[2].default_value = 1 - sty.get('tip_gain', .55) * .45; nt.links.new(hi.outputs['Intercept'], gr.inputs[0])
    vs = nt.nodes.new('ShaderNodeVectorMath'); vs.operation = 'SCALE'; nt.links.new(acol.outputs['Color'], vs.inputs[0]); nt.links.new(gr.outputs[0], vs.inputs['Scale'])
    A = shot(vs.outputs[0], 'c'); B = shot(comb.outputs[0], 'd')
    # flow: the strand tangent in the atlas plane (x -> u, z -> v), encoded .5 + .5 t
    tsep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(hi.outputs['Tangent Normal'], tsep.inputs[0])
    def half(sock):
        m_ = nt.nodes.new('ShaderNodeMath'); m_.operation = 'MULTIPLY_ADD'; m_.inputs[1].default_value = .5; m_.inputs[2].default_value = .5; nt.links.new(sock, m_.inputs[0]); return m_.outputs[0]
    fcomb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(half(tsep.outputs[0]), fcomb.inputs[0]); nt.links.new(half(tsep.outputs[2]), fcomb.inputs[1])
    F = shot(fcomb.outputs[0], 'f'); B = np.dstack([B[..., :3], F[..., 0], F[..., 1]])
    win.scene = prev; bpy.data.objects.remove(o); bpy.data.objects.remove(co_); bpy.data.scenes.remove(sc)
    return A, B

def _blur(a, r):
    if r < 1: return a
    for _ in range(2):
        for ax in (0, 1):
            pad = [(0, 0)] * a.ndim; pad[ax] = (r + 1, r); c = np.cumsum(np.pad(a, pad, mode='edge'), axis=ax, dtype=np.float64)
            n = a.shape[ax]; a = ((np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=ax) - np.take(c, range(0, n), axis=ax)) / (2 * r + 1)).astype(np.float32)
    return a

def _flood(val, cov, fill):
    """Spread covered values into the empty texels (so mips and alpha edges never pull in a foreign colour)."""
    fc = val * cov[..., None]; fw = cov.copy()
    for r in (2, 4, 8, 16, 48):
        b_ = _blur(fc, r); bw = _blur(fw, r); m = (fw < .5) & (bw > .02)
        fc[m] = (b_ / np.maximum(bw[..., None], 1e-5))[m]; fw = np.maximum(fw, m.astype(np.float32))
    fc[fw < .5] = fill; return np.where(cov[..., None] > .5, val, fc)

def compose_atlas(prefix, A, B, sty, alpha_gain=1.6, cap_under=.45, under_mask=None):
    """A: premultiplied linear colour + alpha (rows bottom-up, as Blender pixels); B: nearness, strand id, intercept, flow x, flow y.
    Writes _BC (sRGB+alpha), _N, _ORM, _MSK (R depth, G strand id, B root-to-tip) and _FLOW (RG strand direction in uv space, B back-light mask)."""
    al = A[..., 3]; ia = 1 / np.maximum(al, 1e-4); col = A[..., :3] * ia[..., None]
    dep = B[..., 0] * ia; sid = B[..., 1] * ia; icp = B[..., 2] * ia; flow = np.dstack([B[..., 3] * ia, B[..., 4] * ia])
    cov = (al > .25).astype(np.float32); n = al.shape[0]
    mean = col[cov > .5].mean(0) if cov.any() else np.array([.1, .05, .03])
    colF = _flood(col, cov, mean)
    fl = flow * 2 - 1
    # the tangent sign is arbitrary per strand: make it root-to-tip (down the tile; outward from the crown in the cap rect) before filtering
    yy, xx = np.mgrid[0:n, 0:n]; cx_ = (CAP_RECT[0] + CAP_RECT[2]) / 2 * n; cy_ = (CAP_RECT[1] + CAP_RECT[3]) / 2 * n
    incap = (xx < CAP_RECT[2] * n) & (yy >= CAP_RECT[1] * n)
    ref = np.where(incap[..., None], np.dstack([xx - cx_, yy - cy_]), np.array([0, -1.0])[None, None, :]); del yy, xx
    fl = np.where(((fl * ref).sum(2) < 0)[..., None], -fl, fl); del ref
    fl = _flood(fl, cov, np.array([0, -1.0])); fl = np.dstack([_blur(fl[..., 0], 1), _blur(fl[..., 1], 1)]); fl /= np.maximum(np.linalg.norm(fl, axis=2), 1e-4)[..., None]
    depF = np.where(cov > .5, dep, 0)
    alpha = np.clip(al * alpha_gain, 0, 1)
    # cap rect: local self-shadowing from the relative depth, and an opaque dark under-fill wherever the groom is dense
    y0, y1, x0, x1 = int(CAP_RECT[1] * n), int(CAP_RECT[3] * n), int(CAP_RECT[0] * n), int(CAP_RECT[2] * n)
    cc = cov[y0:y1, x0:x1]; cd = depF[y0:y1, x0:x1]; r_ = max(2, n // 256)
    loc = _blur(cd * cc, r_ * 2) / np.maximum(_blur(cc, r_ * 2), .05); rel = np.where(cc > .5, cd - loc, 0)
    sh = np.clip(1 + sty.get('cap_shade', 2.2) * rel / max(float(np.percentile(np.abs(rel[cc > .5]), 90)) if (cc > .5).any() else 1, 1e-3) * .22, .5, 1.3)
    dens = _blur(cc, r_ * 3); under = sstep(.30, .62, dens)
    if under_mask is not None:
        g_ = (np.arange(y1 - y0) + .5) / (y1 - y0); gu, gv = np.meshgrid(g_, g_); G_ = under_mask.shape[0]
        um = under_mask[np.clip((gv * G_).astype(int), 0, G_ - 1), np.clip((gu * G_).astype(int), 0, G_ - 1)]; um = _blur(um, r_ * 2); under = np.maximum(under * sstep(.05, .5, um), sstep(.75, .95, um))
    cap_col = colF[y0:y1, x0:x1] * sh[..., None]
    cap_col = np.where(cc[..., None] > .5, cap_col, cap_col * cap_under)
    colF[y0:y1, x0:x1] = cap_col; alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], under)
    occ = np.clip(.72 + .4 * depF, 0, 1); occ[y0:y1, x0:x1] = np.clip(np.where(cc > .5, .55 + .45 * sh, .4), 0, 1)
    hgt = depF * cov; hs = _blur(hgt, 1)
    k = sty.get('nrm_k', 3.0)
    gx = (np.roll(hs, -1, 1) - np.roll(hs, 1, 1)) * k; gy = (np.roll(hs, -1, 0) - np.roll(hs, 1, 0)) * k
    nrm = np.dstack([-gx, -gy, np.ones_like(gx)]); nrm /= np.linalg.norm(nrm, axis=2)[..., None]
    nrm = np.where(cov[..., None] > .5, nrm, np.array([0, 0, 1.0])[None, None, :])
    rough = np.clip(sty.get('rough', .42) + (sid - .5) * .16 + (1 - depF) * .08, .2, .9)
    back = np.ones_like(al); back[y0:y1, x0:x1] = sty.get('cap_back', 0.0)
    def enc(c): c = np.clip(c, 0, 1); return np.where(c <= .0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - .055)
    out = {'_BC': np.dstack([enc(colF), alpha]), '_N': nrm * .5 + .5, '_ORM': np.dstack([occ, rough, np.zeros_like(occ)]), '_MSK': np.dstack([depF, sid * cov, icp * cov]),
           '_FLOW': np.dstack([fl[..., 0] * .5 + .5, fl[..., 1] * .5 + .5, back])}
    for suf, arr in out.items():
        h, w = arr.shape[:2]; im = bpy.data.images.new('atl', w, h, alpha=True)
        if suf != '_BC': im.colorspace_settings.name = 'Non-Color'
        a4 = arr if arr.shape[2] == 4 else np.dstack([arr, np.ones((h, w), np.float32)])
        im.alpha_mode = 'STRAIGHT'
        im.pixels.foreach_set(np.clip(a4, 0, 1).astype(np.float32).ravel()); im.filepath_raw = str(prefix) + suf + '.png'; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
    log('atlas written', prefix, 'coverage', float(cov.mean()), 'cap coverage', float(cc.mean()), 'mean lin colour', mean.round(4).tolist())
    return alpha, mean

# ------------------------------------------------------------------ cards
class Cards:
    def __init__(s, H):
        s.H = H; s.v = []; s.f = []; s.uv = []; s.hl = []; s.hn = []; s.floor = None      # floor(p) -> height of the cap shell above the skin at p
    def ribbon(s, pts, width, tile, layer, rng, nseg=4, across=1, lift_scale=1.0, lift_off=0.0, roll=.0, bow=.08, taper=.25, v_span=(0.0, 1.0), flipu=None, nblend=.92, t_range=(0.0, 1.0), root_ext=0.0, flare=0.0):
        """One card along a guide polyline (root first). lift_scale flattens the guide towards the scalp (under shells)."""
        H = s.H; pts = np.asarray(pts)
        if root_ext:
            l0, n0 = H.near(pts[0] - unit(pts[1] - pts[0]) * root_ext); pts = np.vstack([l0 + n0 * .0008, pts])
        K = len(pts)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]; Ltot = cum[-1]
        if Ltot < 1e-5: return
        u0, v0, u1, v1 = tile_rect(tile); base = len(s.v); flip = (rng.random() < .5) if flipu is None else flipu
        roll_a = rng.normal(0, roll) if roll else 0.0
        for k in range(nseg + 1):
            t = t_range[0] + (t_range[1] - t_range[0]) * k / nseg; d = t * Ltot; i = min(int(np.searchsorted(cum, d, side='right')) - 1, K - 2); i = max(i, 0)
            f = (d - cum[i]) / max(seg[i], 1e-9); p = pts[i] * (1 - f) + pts[i + 1] * f; tg = unit(pts[i + 1] - pts[i])
            loc, nrm = H.near(p); h = (p - loc) @ nrm
            if lift_scale != 1.0 or lift_off: p = loc + nrm * (max(h, 0) * lift_scale + lift_off * (.4 + .6 * t))
            if flare: p = p + nrm * flare * (k / nseg) ** 2
            if s.floor is not None:      # a card never dives under the cap shell
                fl_ = s.floor(p) + .0013 + .0009 * (layer - 2); h2 = (p - loc) @ nrm
                if h2 < fl_: p = loc + nrm * fl_
            w = np.cross(nrm, tg)
            if np.linalg.norm(w) < 1e-4: w = np.cross(nrm, [0, 0, 1.0])
            w = unit(w); cn = unit(np.cross(tg, w));
            if cn @ nrm < 0: cn = -cn
            wr = w * math.cos(roll_a) + cn * math.sin(roll_a)
            hw = width / 2 * (1 - taper * (k / nseg) ** 2)
            for a in range(across + 1):
                x = a / across * 2 - 1
                s.v.append(p + wr * x * hw + cn * bow * width * (1 - x * x))
                uu = (.5 + x * .485 * (-1 if flip else 1)); s.uv.append((u0 + uu * (u1 - u0), v0 + (v_span[0] + (v_span[1] - v_span[0]) * k / nseg) * (v1 - v0)))
                s.hl.append(layer); s.hn.append(unit(nrm * nblend + cn * (1 - nblend) + wr * x * .15))
        A = across + 1
        for k in range(nseg):
            for a in range(across):
                i0 = base + k * A + a; s.f.append((i0, i0 + A, i0 + A + 1, i0 + 1))
    def tube(s, pts, radius, tile, layer, rng, sides=5, nseg=None, v_rep=1.0, twist=0.0):
        """A wound bundle as a closed ribbon tube (bun strands)."""
        pts = np.asarray(pts); K = len(pts); nseg = nseg or K - 1; u0, v0, u1, v1 = tile_rect(tile); base = len(s.v)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]; Ltot = cum[-1]; up = np.array([0, 0, 1.0]); prev = None
        for k in range(nseg + 1):
            t = k / nseg; d = t * Ltot; i = max(min(int(np.searchsorted(cum, d, side='right')) - 1, K - 2), 0); f = (d - cum[i]) / max(seg[i], 1e-9)
            p = pts[i] * (1 - f) + pts[i + 1] * f; tg = unit(pts[i + 1] - pts[i])
            a_ = (prev if prev is not None else np.cross(tg, up)); a_ = unit(a_ - tg * (a_ @ tg)); b_ = np.cross(tg, a_); prev = a_
            r = radius * (1 - .55 * sstep(.82, 1.0, t)) * (.75 + .25 * sstep(0, .1, t))
            for j in range(sides + 1):
                an = 2 * math.pi * j / sides + twist * t; n_ = a_ * math.cos(an) + b_ * math.sin(an)
                s.v.append(p + n_ * r); s.uv.append((u0 + (.03 + .94 * j / sides) * (u1 - u0), v0 + ((t * v_rep) % 1.0 if t * v_rep < 1 else .999) * (v1 - v0) * .9)); s.hl.append(layer); s.hn.append(n_)
        A = sides + 1
        for k in range(nseg):
            for j in range(sides):
                i0 = base + k * A + j; s.f.append((i0, i0 + 1, i0 + A + 1, i0 + A))
    def strip(s, P, Nn, Wd, width, tile, layer, rng, v_span=(0.0, 1.0), taper=.2, flip=None):
        """A free ribbon: explicit centre points P, facing normals Nn and width directions Wd (wound bun ribbons)."""
        u0, v0, u1, v1 = tile_rect(tile); base = len(s.v); n = len(P); flip = (rng.random() < .5) if flip is None else flip
        for k in range(n):
            t = k / (n - 1); hw = width / 2 * (1 - taper * abs(2 * t - 1) ** 3)
            for x in (-1, 1):
                s.v.append(P[k] + Wd[k] * x * hw - Nn[k] * abs(x) * width * .12); uu = .5 + x * .485 * (-1 if flip else 1)
                s.uv.append((u0 + uu * (u1 - u0), v0 + (v_span[0] + (v_span[1] - v_span[0]) * t) * (v1 - v0))); s.hl.append(layer); s.hn.append(unit(Nn[k] + Wd[k] * x * .35))
        for k in range(n - 1):
            i0 = base + k * 2; s.f.append((i0, i0 + 2, i0 + 3, i0 + 1))
    def wound(s, pts, radius, tiles, layer, rng, strips=5, nseg=16, twist=.7, width_k=1.8):
        """A wound bundle as overlapping narrow ribbons spiralling round its centre line (replaces the closed tube)."""
        pts = np.asarray(pts); K = len(pts); seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]; Ltot = cum[-1]; up = np.array([0, 0, 1.0]); prev = None; FR = []
        for k in range(nseg + 1):
            t = k / nseg; d = t * Ltot; i = max(min(int(np.searchsorted(cum, d, side='right')) - 1, K - 2), 0); f = (d - cum[i]) / max(seg[i], 1e-9)
            p = pts[i] * (1 - f) + pts[i + 1] * f; tg = unit(pts[i + 1] - pts[i]); a_ = (prev if prev is not None else np.cross(tg, up)); a_ = unit(a_ - tg * (a_ @ tg)); b_ = np.cross(tg, a_); prev = a_
            FR.append((p, tg, a_, b_, radius * (1 - .5 * sstep(.85, 1.0, t)) * (.7 + .3 * sstep(0, .1, t))))
        for j in range(strips):
            ph = 2 * math.pi * j / strips + rng.uniform(-.2, .2); tw = twist * rng.uniform(.6, 1.4); rk = rng.uniform(.94, 1.06); P = []; Nn = []; Wd = []
            for k, (p, tg, a_, b_, r) in enumerate(FR):
                an = ph + tw * k / nseg; n_ = a_ * math.cos(an) + b_ * math.sin(an); P.append(p + n_ * r * rk); Nn.append(n_); Wd.append(unit(np.cross(tg, n_)))
            s.strip(P, Nn, Wd, 2 * math.pi * radius / strips * width_k, int(rng.choice(tiles)), layer, rng, v_span=(.04, .9))
    def build(s, name='Hair'):
        V_ = np.array(s.v); HN_ = np.array(s.hn); F_ = []
        for f in s.f:      # geometric normal on the side of the shading normal (a two-sided card whose two normals disagree renders black)
            gn = np.cross(V_[f[1]] - V_[f[0]], V_[f[2]] - V_[f[0]]); F_.append(tuple(reversed(f)) if gn @ HN_[list(f)].sum(0) < 0 else f)
        s.f = F_
        o = new_obj(name, s.v, s.f); me = o.data
        uv = me.uv_layers.new(name='UVMap'); li = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', li)
        uv.data.foreach_set('uv', np.array(s.uv, np.float32)[li].ravel())
        me.attributes.new('hl', 'FLOAT', 'POINT').data.foreach_set('value', np.array(s.hl, np.float32))
        me.attributes.new('hn', 'FLOAT_VECTOR', 'POINT').data.foreach_set('vector', np.array(s.hn, np.float32).ravel())
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); ca.data.foreach_set('color', np.ones(len(s.v) * 4, np.float32))
        smooth_shade(o); apply_hn(o); return o

def apply_hn(o):
    """Card shading normals: the stored 'hn' point attribute (scalp-blended) becomes the custom split normals."""
    me = o.data; a = me.attributes.get('hn')
    if a is None: return
    hn = np.empty(len(me.vertices) * 3, np.float32); a.data.foreach_get('vector', hn); hn = hn.reshape(-1, 3)
    me.update(); vn = normals_np(me); ln = np.linalg.norm(hn, axis=1); use = ln > .5
    nn = np.where(use[:, None], hn / np.maximum(ln, 1e-9)[:, None], vn)
    me.normals_split_custom_set_from_vertices([tuple(x) for x in nn.astype(float)])

def card_material(name, bc, n, orm, flow=None, spec=.02, rough_u=.42, rough_v=.8, shift=.0, diffuse=.8, shadow=.3, ao=.6, transl=.4, spec2=9.0):
    """Preview material for the game hair cards: albedo with alpha, baked normal, an anisotropic strand highlight
    whose tangent runs along UV V (the strand direction), two-sided."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name); mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    out = N('ShaderNodeOutputMaterial')
    def img(path, noncolor):
        im = bpy.data.images.load(str(path), check_existing=True); im.reload()
        if noncolor: im.colorspace_settings.name = 'Non-Color'
        t = N('ShaderNodeTexImage'); t.image = im; return t
    b = img(bc, False); o_ = img(orm, True); nn = img(n, True)
    if flow is None and os.path.exists(str(bc).replace('_BC.png', '_FLOW.png')): flow = str(bc).replace('_BC.png', '_FLOW.png')
    nm = N('ShaderNodeNormalMap'); L(nn.outputs[0], nm.inputs['Color']); nm.inputs['Strength'].default_value = .5
    sep = N('ShaderNodeSeparateColor'); L(o_.outputs[0], sep.inputs[0])
    aom = N('ShaderNodeMix'); aom.data_type = 'RGBA'; aom.blend_type = 'MULTIPLY'; aom.inputs['Factor'].default_value = ao; L(b.outputs[0], aom.inputs['A']); L(sep.outputs[0], aom.inputs['B'])
    dif = N('ShaderNodeBsdfDiffuse'); L(aom.outputs['Result'], dif.inputs['Color']); L(nm.outputs[0], dif.inputs['Normal'])
    # backlit translucency so thin outer cards glow like strands do
    tr = N('ShaderNodeBsdfTranslucent'); L(aom.outputs['Result'], tr.inputs['Color']); L(nm.outputs[0], tr.inputs['Normal'])
    # the back-light lobe is ADDED to the full diffuse (scaled by transl x FLOW.b), so a card and the cap under it shade alike when front-lit
    trc = N('ShaderNodeMix'); trc.data_type = 'RGBA'; trc.blend_type = 'MULTIPLY'; trc.inputs['Factor'].default_value = 1.0; L(aom.outputs['Result'], trc.inputs['A']); trc.inputs['B'].default_value = (transl, transl, transl, 1)
    L(trc.outputs['Result'], tr.inputs['Color'])
    dmix = N('ShaderNodeAddShader'); L(dif.outputs[0], dmix.inputs[0]); L(tr.outputs[0], dmix.inputs[1])
    tan = N('ShaderNodeTangent'); tan.direction_type = 'UV_MAP'; tan.uv_map = 'UVMap'
    geo = N('ShaderNodeNewGeometry'); cr = N('ShaderNodeVectorMath'); cr.operation = 'CROSS_PRODUCT'; L(geo.outputs['Normal'], cr.inputs[0]); L(tan.outputs[0], cr.inputs[1])
    hdir = cr.outputs[0]
    if flow is not None:   # strand direction = flow.x * dP/du + flow.y * dP/dv ; flow.b masks the back-light translucency (0 on the opaque cap)
        ft = img(flow, True); fs = N('ShaderNodeSeparateColor'); L(ft.outputs[0], fs.inputs[0])
        def sgn(sock):
            m_ = N('ShaderNodeMath'); m_.operation = 'MULTIPLY_ADD'; m_.inputs[1].default_value = 2.0; m_.inputs[2].default_value = -1.0; L(sock, m_.inputs[0]); return m_.outputs[0]
        v1_ = N('ShaderNodeVectorMath'); v1_.operation = 'SCALE'; L(tan.outputs[0], v1_.inputs[0]); L(sgn(fs.outputs[0]), v1_.inputs['Scale'])
        v2_ = N('ShaderNodeVectorMath'); v2_.operation = 'SCALE'; L(cr.outputs[0], v2_.inputs[0]); L(sgn(fs.outputs[1]), v2_.inputs['Scale'])
        va = N('ShaderNodeVectorMath'); va.operation = 'ADD'; L(v1_.outputs[0], va.inputs[0]); L(v2_.outputs[0], va.inputs[1])
        vn_ = N('ShaderNodeVectorMath'); vn_.operation = 'NORMALIZE'; L(va.outputs[0], vn_.inputs[0]); hdir = vn_.outputs[0]
        tm = N('ShaderNodeMix'); tm.data_type = 'RGBA'; tm.blend_type = 'MULTIPLY'; tm.inputs['Factor'].default_value = 1.0; L(trc.outputs['Result'], tm.inputs['A']); L(fs.outputs[2], tm.inputs['B']); L(tm.outputs['Result'], tr.inputs['Color'])
    g1 = N('ShaderNodeBsdfHair'); g1.component = 'Reflection'; g1.inputs['RoughnessU'].default_value = rough_u; g1.inputs['RoughnessV'].default_value = rough_v; g1.inputs['Offset'].default_value = shift
    g1.inputs['Color'].default_value = (spec, spec, spec, 1); L(hdir, g1.inputs['Tangent'])
    g2 = N('ShaderNodeBsdfHair'); g2.component = 'Reflection'; g2.inputs['RoughnessU'].default_value = rough_u * 1.8; g2.inputs['RoughnessV'].default_value = rough_v; g2.inputs['Offset'].default_value = shift - .12
    sc2 = N('ShaderNodeMix'); sc2.data_type = 'RGBA'; sc2.blend_type = 'MULTIPLY'; sc2.inputs['Factor'].default_value = 1.0; L(b.outputs[0], sc2.inputs['A']); sc2.inputs['B'].default_value = (spec * spec2, spec * spec2, spec * spec2, 1)
    L(sc2.outputs['Result'], g2.inputs['Color']); L(hdir, g2.inputs['Tangent'])
    a1 = N('ShaderNodeAddShader'); L(dmix.outputs[0], a1.inputs[0]); L(g1.outputs[0], a1.inputs[1])
    a2 = N('ShaderNodeAddShader'); L(a1.outputs[0], a2.inputs[0]); L(g2.outputs[0], a2.inputs[1])
    tp = N('ShaderNodeBsdfTransparent'); mx = N('ShaderNodeMixShader'); L(tp.outputs[0], mx.inputs[1]); L(a2.outputs[0], mx.inputs[2])
    # shadow rays see the cards as partly transparent: stands in for the forward scattering of real strands (deep-shadow look)
    lp = N('ShaderNodeLightPath'); sm = N('ShaderNodeMath'); sm.operation = 'MULTIPLY'; sm.inputs[1].default_value = 1 - shadow; L(lp.outputs['Is Shadow Ray'], sm.inputs[0])
    s1 = N('ShaderNodeMath'); s1.operation = 'SUBTRACT'; s1.inputs[0].default_value = 1.0; L(sm.outputs[0], s1.inputs[1])
    am = N('ShaderNodeMath'); am.operation = 'MULTIPLY'; L(b.outputs[1], am.inputs[0]); L(s1.outputs[0], am.inputs[1]); L(am.outputs[0], mx.inputs[0])
    L(mx.outputs[0], out.inputs[0])
    mat.use_backface_culling = False
    try: mat.surface_render_method = 'DITHERED'
    except Exception: pass
    return mat
