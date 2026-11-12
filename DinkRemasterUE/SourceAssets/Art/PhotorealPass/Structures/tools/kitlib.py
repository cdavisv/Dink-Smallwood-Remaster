"""Shared builder for the exterior structure kits (town houses round 2, Stonebrook, castle, ...).
Loaded with exec() by the build scripts, which run in Blender batch mode. It takes the Module class, noise and UV helpers of
WallKits/tools/wallkit_build.py (read-only) and adds:
  Mod2      a Module whose parts are all closed solids (no welding), three LODs, convex collision hulls, RGBA vertex colour
  slab      closed wall block with relief on both faces          hgrid   closed solid under a displaced top grid (roofs, thatch)
  tube      closed swept pole / rail / rope                       rock    closed irregular stone
  wmat      preview of the Unreal material contract: tiling set + vertex colour weathering
Vertex colour 'Grime' (linear RGBA): R dirt and damp (darker, smoother), G moss / algae (green, rough, in the low parts of the
height map first), B bleaching (silvered timber, lichen, fresh straw), A material switch on timber slots only (1 wood, 0.5 black
iron or lead, 0 window glass)."""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector, Matrix

KL_HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else None
PP = os.environ['DINK_PP']
_src = open(os.path.join(PP, 'WallKits', 'tools', 'wallkit_build.py')).read()
_src = _src[:_src.rindex('\nmain()')]
exec(_src.replace("HERE = os.path.dirname(os.path.abspath(__file__))", "HERE = os.path.join(PP, 'WallKits', 'tools')"))
SETS = os.path.join(PP, 'Structures', 'Sets')
T_TIMBER = 2.0
TAG_GLASS, TAG_PLASTER, TAG_ROOF, TAG_IRON, TAG_LEAD, TAG_END, TAG_THATCH, TAG_ROPE = 5, 6, 7, 8, 9, 10, 11, 12


def set_info(setname):
    for root in (SETS, TERRAIN):
        p = os.path.join(root, setname, 'set.json')
        if os.path.exists(p):
            return root, json.load(open(p))
    raise FileNotFoundError(setname)


def tex(nt, setname, key, cs, uvmap='UVMap'):
    root, info = set_info(setname)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(root, info['files'][key]), check_existing=True)
    t.image.colorspace_settings.name = cs
    return t


def board_rows(setname):
    """v ranges of single boards of a plank set (grain along U), so a timber maps inside one board"""
    root, info = set_info(setname)
    img = bpy.data.images.load(os.path.join(root, info['files']['H']), check_existing=True)
    n = img.size[0]
    px = np.empty(n * n * 4, np.float32); img.pixels.foreach_get(px)
    h = px.reshape(n, n, 4)[:, :, 0].mean(1)
    hs = np.convolve(np.tile(h, 3), np.ones(5) / 5, 'same')[n:2 * n]
    thr = hs.mean() - 1.2 * hs.std()
    gaps = np.where(hs < thr)[0]; groups = []
    for g in gaps:
        if groups and g - groups[-1][-1] <= 3:
            groups[-1].append(g)
        else:
            groups.append([g])
    cs = [float(np.mean(g)) for g in groups]
    rows = [(((a + b) / 2) / n, (b - a - 24) / n) for a, b in zip(cs[:-1], cs[1:]) if 70 < b - a < 520]
    print('boards in', setname, len(rows))
    if len(rows) < 3:
        rows = [(0.06 + 0.125 * i, 0.09) for i in range(8)]
    return rows


class Mod2(Module):
    def __init__(self, name, length, height, rows, cls='kit_piece', path='Structures'):
        Module.__init__(self, name, length, height, rows)
        self.cls = cls; self.path = path; self.FS = []; self.paint = []; self.hulls = []; self.slots = []
        self.lod_ratio = (0.45, 0.2); self.floor0 = False

    def add(self, verts, faces, mat, tile, mode='planar', uvoff=None, board=None, tag=0, smooth=False):
        n0 = len(self.F)
        Module.add(self, verts, faces, mat, tile, mode, uvoff, board, tag)
        self.FS.extend([smooth] * (len(self.F) - n0))

    def add_uv(self, verts, faces, uvs, mat, tag=0, smooth=False):
        base = len(self.V)
        self.V.extend(np.asarray(verts, float).tolist()); self.VT.extend([tag] * len(verts))
        for f, uv in zip(faces, uvs):
            self.F.append([base + i for i in f]); self.FM.append(mat); self.UV.append(uv); self.FS.append(smooth)

    # ---- closed parts
    def slab(self, x0, x1, z0, z1, y0, y1, mat, tile, nx=None, nz=None, relief=0.006, tag=0, ztop=None, uvoff=None):
        """closed block from y0 (street face, -Y) to y1, both big faces subdivided and gently undulating; ztop(x) for raking tops"""
        nx = nx or max(1, int(round((x1 - x0) / 0.32))); nz = nz or max(1, int(round((z1 - z0) / 0.36)))
        xs = np.linspace(x0, x1, nx + 1); V = []; sd = int(self.rng.integers(1e6))
        for y, fc in ((y0, -1.0), (y1, 1.0)):
            for i, x in enumerate(xs):
                zt = z1 if ztop is None else ztop(x)
                for j in range(nz + 1):
                    V.append([x, y, z0 + (zt - z0) * j / nz])
        V = np.array(V); G = (nx + 1) * (nz + 1)
        und = vnoise(V * np.array([1, 0, 1.0]) + np.array([0, 0, 0]), sd, 2.4) * relief + vnoise(V * np.array([1, 0, 1.0]), sd + 5, 7.0) * relief * 0.5
        ii = np.tile(np.repeat(np.arange(nx + 1), nz + 1), 2); jj = np.tile(np.tile(np.arange(nz + 1), nx + 1), 2)
        inner = (ii > 0) & (ii < nx) & (jj > 0) & (jj < nz)
        sgn = np.where(np.arange(2 * G) < G, -1.0, 1.0)
        V[:, 1] += sgn * und * inner
        F = []
        idx = lambda s, i, j: s * G + i * (nz + 1) + j
        for i in range(nx):
            for j in range(nz):
                F.append([idx(0, i, j), idx(0, i + 1, j), idx(0, i + 1, j + 1), idx(0, i, j + 1)])
                F.append([idx(1, i, j), idx(1, i, j + 1), idx(1, i + 1, j + 1), idx(1, i + 1, j)])
        for i in range(nx):                                   # bottom and top
            F.append([idx(0, i, 0), idx(1, i, 0), idx(1, i + 1, 0), idx(0, i + 1, 0)])
            F.append([idx(0, i, nz), idx(0, i + 1, nz), idx(1, i + 1, nz), idx(1, i, nz)])
        for j in range(nz):                                   # ends
            F.append([idx(0, 0, j), idx(0, 0, j + 1), idx(1, 0, j + 1), idx(1, 0, j)])
            F.append([idx(0, nx, j), idx(1, nx, j), idx(1, nx, j + 1), idx(0, nx, j + 1)])
        self.add(V, F, mat, tile, tag=tag, smooth=True, uvoff=uvoff)

    def hgrid(self, top, under, mat, tile, tag=0, up=(0, 0, 1), uvfn=None, smooth=False, uvface=None, grid_under=False):
        """closed solid: `top` (R,C,3) grid, a skirt from its border down to `under` (same shape; only the border is used) and a fan
        underneath. uvfn(P) -> (n,2) overrides the planar UVs."""
        top = np.asarray(top, float); under = np.asarray(under, float); R, C = top.shape[:2]
        ring = [(0, c) for c in range(C)] + [(r, C - 1) for r in range(1, R)] + [(R - 1, c) for c in range(C - 2, -1, -1)] + [(r, 0) for r in range(R - 2, 0, -1)]
        V = top.reshape(-1, 3).tolist(); nb = len(V)
        V += [under[r, c].tolist() for (r, c) in ring]
        cen = np.mean([under[r, c] for (r, c) in ring], 0); V.append(cen.tolist()); ci = len(V) - 1
        F = []
        for r in range(R - 1):
            for c in range(C - 1):
                F.append([r * C + c, r * C + c + 1, (r + 1) * C + c + 1, (r + 1) * C + c])
        n = len(ring)
        if grid_under:                                  # a second grid underneath instead of the fan (for outlines that are not convex)
            V = top.reshape(-1, 3).tolist() + under.reshape(-1, 3).tolist(); G_ = R * C
            for r in range(R - 1):
                for c in range(C - 1):
                    F.append([G_ + r * C + c, G_ + (r + 1) * C + c, G_ + (r + 1) * C + c + 1, G_ + r * C + c + 1])
            for k in range(n):
                a = ring[k]; b = ring[(k + 1) % n]
                F.append([a[0] * C + a[1], G_ + a[0] * C + a[1], G_ + b[0] * C + b[1], b[0] * C + b[1]])
        else:
            for k in range(n):
                a = ring[k]; b = ring[(k + 1) % n]
                F.append([a[0] * C + a[1], nb + k, nb + (k + 1) % n, b[0] * C + b[1]])
                F.append([nb + (k + 1) % n, nb + k, ci])
        Va = np.array(V); nrm = np.zeros(3)
        for f in F[:(R - 1) * (C - 1)]:
            nrm += np.cross(Va[f[2]] - Va[f[0]], Va[f[3]] - Va[f[1]])
        if np.dot(nrm, np.array(up, float)) < 0:
            F = [x[::-1] for x in F]
        if uvface is not None:
            self.add_uv(Va, F, [uvface(Va[f]) for f in F], mat, tag, smooth)
        elif uvfn is None:
            self.add(Va, F, mat, tile, tag=tag, smooth=smooth, uvoff=self.rng.uniform(0, 1, 2))
        else:
            uv = uvfn(Va)
            self.add_uv(Va, F, [[tuple(uv[i]) for i in f] for f in F], mat, tag, smooth)

    def tube(self, pts, radii, mat, sides=8, tag=1, tile=None, shape=None, rough=0.0, smooth=True, vrange=None, twist=0.0):
        """closed swept pole along a polyline. shape: list of radius factors per side (split or hewn sections). UV: u along the
        length, v around inside one board row of the timber set."""
        pts = np.asarray(pts, float); n = len(pts); tile = tile or T_TIMBER
        radii = np.broadcast_to(np.asarray(radii, float), (n,)) if np.ndim(radii) <= 1 else np.asarray(radii, float)
        shape = np.ones(sides) if shape is None else np.asarray(shape, float)
        v0, w = vrange if vrange else self.timber_rows[self.rng.integers(len(self.timber_rows))]
        V = []; U = []; s = 0.0; ph = self.rng.uniform(0, 6.28); u0 = self.rng.uniform(0, 1)
        prev_n = None
        for i in range(n):
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]; t /= np.linalg.norm(t) + 1e-12
            ref = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
            a = np.cross(t, ref); a /= np.linalg.norm(a); b = np.cross(t, a)
            if i > 0:
                s += np.linalg.norm(pts[i] - pts[i - 1])
            for k in range(sides):
                ang = 2 * math.pi * k / sides + twist * s
                r = radii[i] * shape[k] * (1 + rough * math.sin(3.1 * s / max(radii[i], 1e-3) * 0.15 + k * 1.7 + ph) + self.rng.normal(0, rough * 0.5))
                V.append(pts[i] + r * (math.cos(ang) * a + math.sin(ang) * b))
                U.append((s / tile + u0, k))
        V.append(pts[0].tolist()); V.append(pts[-1].tolist()); c0, c1 = len(V) - 2, len(V) - 1
        F = []; UVs = []
        vv = lambda k: v0 + (k / sides - 0.5) * w
        for i in range(n - 1):
            for k in range(sides):
                a_, b_ = i * sides + k, i * sides + (k + 1) % sides; c_, d_ = (i + 1) * sides + (k + 1) % sides, (i + 1) * sides + k
                F.append([a_, d_, c_, b_]); UVs.append([(U[a_][0], vv(k)), (U[d_][0], vv(k)), (U[c_][0], vv(k + 1)), (U[b_][0], vv(k + 1))])
        cap0 = len(F)
        for k in range(sides):
            F.append([c0, k, (k + 1) % sides]); F.append([c1, (n - 1) * sides + (k + 1) % sides, (n - 1) * sides + k])
            for q in range(2):
                e = 2 * math.pi * k / sides; e2 = 2 * math.pi * (k + 1) / sides; rr = 0.04
                UVs.append([(u0 + 0.5, v0), (u0 + 0.5 + rr * math.cos(e), v0 + rr * math.sin(e)), (u0 + 0.5 + rr * math.cos(e2), v0 + rr * math.sin(e2))])
        Va = np.array(V); f = F[0]
        nrm = np.cross(Va[f[1]] - Va[f[0]], Va[f[2]] - Va[f[0]]); out = Va[f].mean(0) - (pts[0] + pts[1]) / 2
        if np.dot(nrm, out) < 0:
            F = [x[::-1] for x in F]; UVs = [u[::-1] for u in UVs]
        base = len(self.V)
        self.V.extend(Va.tolist()); self.VT.extend([tag] * len(Va))
        for q, (f, uv) in enumerate(zip(F, UVs)):
            self.F.append([base + i for i in f]); self.FM.append(mat); self.UV.append(uv); self.FS.append(smooth and q < cap0)

    def rock(self, c, size, mat, tile, seed=None, sub=2, tag=2, flat=0.0, lump=0.22, smooth=True, facets=4, crease=0.0):
        """closed irregular stone: displaced icosphere scaled to `size` (full extents); flat > 0 cuts the underside off"""
        seed = int(self.rng.integers(1e6)) if seed is None else seed
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        P = np.array([v.co[:] for v in bm.verts])
        d = 1 + lump * vnoise(P, seed, 1.3) + lump * 0.45 * vnoise(P, seed + 1, 3.1) + lump * 0.15 * vnoise(P, seed + 2, 7.0)
        # a few flat facets, as a split or weathered stone has
        r = np.random.default_rng(seed)
        d = d - crease * np.abs(vnoise(P, seed + 5, 2.3)) - crease * 0.5 * np.abs(vnoise(P, seed + 6, 5.5))
        for _ in range(facets):
            nrm = r.normal(size=3); nrm /= np.linalg.norm(nrm); lim = r.uniform(0.62, 0.9)
            k = P @ nrm; over = np.maximum(k * d - lim, 0)
            d = d - over / np.maximum(k, 1e-3) * 0.85
        P = P * d[:, None] * (np.asarray(size, float) / 2)
        if flat > 0:
            zc = -size[2] / 2 * (1 - flat)
            P[:, 2] = np.maximum(P[:, 2], zc)
        P = P + np.asarray(c, float)
        F = [[v.index for v in f.verts] for f in bm.faces]; bm.free()
        self.add(P, F, mat, tile, tag=tag, smooth=smooth, uvoff=r.uniform(0, 1, 2))

    def prism(self, poly, y0, y1, mat, tile, tag=1, axis=1, mode='planar', board=None):
        """closed prism: polygon in the plane normal to `axis` (list of 2D points), extruded from y0 to y1 along it"""
        k = len(poly); V = []
        o = [a for a in range(3) if a != axis]
        for yy in (y0, y1):
            for p in poly:
                q = [0, 0, 0]; q[axis] = yy; q[o[0]] = p[0]; q[o[1]] = p[1]; V.append(q)
        F = [[i, (i + 1) % k, k + (i + 1) % k, k + i] for i in range(k)] + [list(range(k))[::-1], [k + i for i in range(k)]]
        Va = np.array(V, float); f = F[0]
        nrm = np.cross(Va[f[1]] - Va[f[0]], Va[f[2]] - Va[f[0]]); out = Va[f].mean(0) - Va.mean(0)
        if np.dot(nrm, out) < 0:
            F = [x[::-1] for x in F]
        if mode == 'board' and board is None:
            board = self.timber_rows[self.rng.integers(len(self.timber_rows))]
        self.add(Va, F, mat, tile, mode, self.rng.uniform(0, 1, 2), board, tag=tag)

    def xform_since(self, n0, M):
        """apply a 4x4 matrix to every vertex added since vertex index n0 (UVs stay)"""
        M = np.array(M, float)
        for i in range(n0, len(self.V)):
            p = M @ np.array(self.V[i] + [1.0]); self.V[i] = p[:3].tolist()

    # ---- finish
    def build(self, coll_parent):
        V = np.array(self.V, np.float64)
        if self.floor0:
            V[:, 2] = np.maximum(V[:, 2], 0.0)
        P = V.copy(); tags = np.array(self.VT)
        me = bpy.data.meshes.new(self.name + '_LOD0')
        me.from_pydata([tuple(v) for v in V], [], self.F); me.update()
        N = np.zeros(len(V) * 3, np.float32); me.vertices.foreach_get('normal', N); N = N.reshape(-1, 3)
        col = self.col_fn(P, tags) if self.col_fn else np.concatenate([np.zeros((len(V), 3)), np.ones((len(V), 1))], 1)
        for fn in self.paint:
            col = fn(P, tags, N, col)
        uv0 = me.uv_layers.new(name='UVMap')
        flat = [c for uvs in self.UV for uv in uvs for c in uv]
        uv0.data.foreach_set('uv', np.array(flat, np.float32))
        ca = me.color_attributes.new('Grime', 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set('color', np.clip(col, 0, 1).astype(np.float32).ravel())
        me.polygons.foreach_set('material_index', self.FM)
        me.polygons.foreach_set('use_smooth', self.FS + [False] * (len(me.polygons) - len(self.FS)))
        try:
            me.set_sharp_from_angle(angle=math.radians(38))
        except Exception as ex:
            print('sharp', ex)
        ob = bpy.data.objects.new(self.name + '_LOD0', me)
        coll = bpy.data.collections.new(self.name); coll_parent.children.link(coll)
        coll['dink_class'] = self.cls; coll['dink_path'] = self.path; coll['dink_tex_px'] = 2048
        coll['dink_source'] = 'authored in Blender (photoreal pass, Structures/tools/kitlib.py); materials are tiling sets built from CC0 scans'
        coll.objects.link(ob)
        bm = bmesh.new(); bm.from_mesh(me)
        nonman = sum(1 for e in bm.edges if not e.is_manifold); bm.free()
        lods = [ob]
        for li, ratio in enumerate(self.lod_ratio):
            l1 = bpy.data.objects.new('%s_LOD%d' % (self.name, li + 1), me.copy()); coll.objects.link(l1)
            md = l1.modifiers.new('d', 'DECIMATE'); md.ratio = ratio; md.use_collapse_triangulate = True; md.delimit = {'MATERIAL'}
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            meb = bpy.data.meshes.new_from_object(l1.evaluated_get(dg)); l1.modifiers.clear(); old = l1.data; l1.data = meb
            bpy.data.meshes.remove(old); meb.name = l1.name
            bmx = bmesh.new(); bmx.from_mesh(meb)
            bmesh.ops.dissolve_degenerate(bmx, edges=bmx.edges[:], dist=1e-5)
            loose = [v for v in bmx.verts if not v.link_faces]
            bmesh.ops.delete(bmx, geom=loose, context='VERTS')
            bmx.to_mesh(meb); bmx.free(); meb.update()
            lods.append(l1)
        ucx = []
        hulls = [('box', lo, hi) for (lo, hi) in self.ucx] + [('pts', p, None) for p in self.hulls]
        for i, (kind, a, b) in enumerate(hulls):
            bmc = bmesh.new()
            if kind == 'box':
                bmesh.ops.create_cube(bmc, size=1.0); lo = np.array(a, float); hi = np.array(b, float)
                for v in bmc.verts:
                    v.co = Vector(lo + (np.array(v.co) + 0.5) * (hi - lo))
            else:
                for p in a:
                    bmc.verts.new(tuple(p))
                r = bmesh.ops.convex_hull(bmc, input=bmc.verts[:])
                bmesh.ops.delete(bmc, geom=list({g for g in r.get('geom_interior', []) + r.get('geom_unused', []) if isinstance(g, bmesh.types.BMVert)}), context='VERTS')
                bmesh.ops.recalc_face_normals(bmc, faces=bmc.faces[:])
            mc = bpy.data.meshes.new('UCX_%s_LOD0_%02d' % (self.name, i + 1)); bmc.to_mesh(mc); bmc.free()
            oc = bpy.data.objects.new(mc.name, mc); coll.objects.link(oc); oc.display_type = 'WIRE'; oc.hide_render = True
            ucx.append(oc)
        self.ob, self.lods, self.ucx_obs, self.coll = ob, lods, ucx, coll
        tr = []
        for o in lods:
            o.data.calc_loop_triangles(); tr.append(len(o.data.loop_triangles))
        lo = V.min(0); hi = V.max(0)
        return {'lod0_triangles': tr[0], 'lod1_triangles': tr[1], 'lod2_triangles': tr[2], 'dimensions_m': [round(float(x), 3) for x in (hi - lo)],
                'bounds_min_m': [round(float(x), 3) for x in lo], 'bounds_max_m': [round(float(x), 3) for x in hi],
                'open_edges': nonman, 'collision_hulls': len(ucx)}


# ---------------------------------------------------------------- materials
MATREG = {}


def wmat(name, setname, dirt=(0.30, 0.26, 0.20), moss=(0.045, 0.058, 0.02), pale=(0.42, 0.41, 0.38), pale_amt=0.75, dirt_amt=0.85,
         special=False, moss_rough=0.95, macro=0.22, tint=None, glass_tint=(0.035, 0.05, 0.065), dirt_mix=False, soot=False, lead=True):
    """Preview of the Unreal material: BC x macro variation; R dirt multiply; G moss mixed in from the low parts of the height map;
    B bleach toward `pale` on the raised parts; with special=True alpha 0.5 = black iron / lead, alpha 0 = glass."""
    MATREG[name] = dict(set=setname, dirt=list(dirt), dirt_amount=dirt_amt, dirt_mode='mix' if dirt_mix else 'multiply', moss=list(moss), moss_roughness=moss_rough, pale=list(pale), pale_amount=pale_amt,
                        macro=macro, tint=list(tint[:3]) if tint else [1, 1, 1], alpha_switch=bool(special), alpha_lead=bool(special and lead), alpha_soot=bool(soot), glass_tint=list(glass_tint) if special else None)
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'Grime'
    sep = nt.nodes.new('ShaderNodeSeparateColor'); L.new(at.outputs['Color'], sep.inputs[0])
    bc = tex(nt, setname, 'BC', 'sRGB'); nn = tex(nt, setname, 'N', 'Non-Color'); orm = tex(nt, setname, 'ORM', 'Non-Color'); hh = tex(nt, setname, 'H', 'Non-Color')
    mac = tex(nt, setname, 'Macro', 'Non-Color')
    uvn = nt.nodes.new('ShaderNodeUVMap'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / 7.0, 1 / 7.0, 1)
    L.new(uvn.outputs[0], mp.inputs[0]); L.new(mp.outputs[0], mac.inputs[0])
    so = nt.nodes.new('ShaderNodeSeparateColor'); L.new(orm.outputs[0], so.inputs[0])
    sm = nt.nodes.new('ShaderNodeSeparateColor'); L.new(mac.outputs[0], sm.inputs[0])

    def math_(op, a, b_=None, c=None, clamp=False):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for sock, v in zip(n.inputs, (a, b_, c)):
            if v is None:
                continue
            if hasattr(v, 'links'):
                L.new(v, sock)
            else:
                sock.default_value = v
        return n.outputs[0]

    def mix(a, b_, f, bt='MIX', dt='RGBA'):
        n = nt.nodes.new('ShaderNodeMix'); n.data_type = dt
        if dt == 'RGBA':
            n.blend_type = bt
        i0 = {'RGBA': (6, 7, 2), 'FLOAT': (2, 3, 0)}[dt]
        for sock, v in ((n.inputs[0], f), (n.inputs[i0[0]], a), (n.inputs[i0[1]], b_)):
            if hasattr(v, 'links'):
                L.new(v, sock)
            else:
                sock.default_value = v if not isinstance(v, tuple) or len(v) == 4 else (*v, 1)
        return n.outputs[i0[2]]
    c = bc.outputs[0]
    if tint:
        c = mix(c, tint, 1.0, 'MULTIPLY')
    mv = math_('MULTIPLY_ADD', sm.outputs[0], 2 * macro, 1 - macro)                    # 1 +- macro
    c = mix(c, mv, 1.0, 'MULTIPLY')
    c = mix(c, so.outputs[0], 0.5, 'MULTIPLY')                                        # scan AO
    R, G, B = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    H = hh.outputs[0]
    # dirt: stronger in the hollows
    fd = math_('MULTIPLY', R, math_('MULTIPLY_ADD', H, -0.5, 1.15), clamp=True)
    if dirt_mix:                                     # weathering that also greys the surface (thatch): mix toward the dirt colour, keeping the texture's values
        lum0 = nt.nodes.new('ShaderNodeRGBToBW'); L.new(c, lum0.inputs[0])
        dc = mix(dirt, math_('MULTIPLY_ADD', lum0.outputs[0], 3.0, 0.35), 1.0, 'MULTIPLY')
        c = mix(c, dc, math_('MULTIPLY', fd, dirt_amt))
    else:
        c = mix(c, dirt, math_('MULTIPLY', fd, dirt_amt), 'MULTIPLY')
    # bleach: raised parts first
    fb = math_('MULTIPLY', B, math_('MULTIPLY_ADD', H, 0.9, 0.35, clamp=True), clamp=True)
    lum = nt.nodes.new('ShaderNodeRGBToBW'); L.new(c, lum.inputs[0])
    pl = mix(pale, math_('MULTIPLY_ADD', lum.outputs[0], 2.2, 0.55, clamp=False), 1.0, 'MULTIPLY')
    c = mix(c, pl, math_('MULTIPLY', fb, pale_amt))
    # moss: low parts first, broken up by the small macro channel
    fm = math_('MULTIPLY', math_('SUBTRACT', math_('MULTIPLY_ADD', sm.outputs[2], 0.5, G), math_('MULTIPLY_ADD', H, 0.55, 0.62)), 4.0, clamp=True)
    fm = math_('MULTIPLY', fm, math_('GREATER_THAN', G, 0.02))
    mc = mix(moss, math_('MULTIPLY_ADD', sm.outputs[1], 0.9, 0.55), 1.0, 'MULTIPLY')
    c = mix(c, mc, fm)
    rough = mix(so.outputs[1], moss_rough, fm, dt='FLOAT')
    rough = math_('MULTIPLY_ADD', fd, -0.10, rough)
    nrm = nn.outputs[0]
    if special:
        A = at.outputs['Alpha']
        lead = math_('LESS_THAN', A, 0.875 if lead else -1.0); iron = math_('LESS_THAN', A, 0.625 if lead else 0.75); glass = math_('LESS_THAN', A, 0.25)
        lc = mix((0.15, 0.16, 0.17), math_('MULTIPLY_ADD', sm.outputs[1], 0.7, 0.65), 1.0, 'MULTIPLY')     # lead: dull blue-grey, patchy patina
        c = mix(c, lc, lead); c = mix(c, (0.016, 0.015, 0.014), iron); c = mix(c, glass_tint, glass)
        rough = mix(rough, 0.42, lead, dt='FLOAT'); rough = mix(rough, math_('MULTIPLY_ADD', R, 0.42, 0.5), iron, dt='FLOAT'); rough = mix(rough, 0.06, glass, dt='FLOAT')
        nrm = mix(nrm, (0.5, 0.5, 1.0), math_('MAXIMUM', math_('SUBTRACT', lead, iron), glass))
    if soot:                                         # alpha below 1: fire soot, black and matt
        fs = math_('SUBTRACT', 1.0, at.outputs['Alpha'], clamp=True)
        fs = math_('MULTIPLY', fs, math_('MULTIPLY_ADD', sm.outputs[1], 0.7, 1.0), clamp=True)
        c = mix(c, (0.012, 0.011, 0.010), fs); rough = mix(rough, 0.97, fs, dt='FLOAT')
    L.new(c, b.inputs['Base Color']); L.new(rough, b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); L.new(nrm, nm.inputs['Color']); L.new(nm.outputs[0], b.inputs['Normal'])
    return m


# ---------------------------------------------------------------- colour helpers
def base_col(n):
    c = np.zeros((n, 4)); c[:, 3] = 1.0
    return c


def streaks(P, seed, fx=5.0, axis=0):
    """vertical run-off streak pattern 0..1, varying along the given horizontal axis"""
    Q = np.zeros_like(P); Q[:, 0] = P[:, axis] * fx; Q[:, 2] = P[:, 2] * 0.35
    return np.clip(0.5 + 0.9 * vnoise(Q, seed, 1.0), 0, 1)


def export_modules(mods, mats, out_dir, blend_name, extra_rec=None):
    """mods: list of dicts {m, families, frames, note, ...}; builds, exports one FBX per module (LOD0-2 + UCX), saves the .blend"""
    sc = bpy.context.scene; recs = []
    for d in mods:
        m = d['m']
        st = m.build(sc.collection)
        for ob in m.lods:
            for s in m.slots:
                ob.data.materials.append(mats[s])
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in m.lods + m.ucx_obs:
            o.hide_render = False; o.hide_viewport = False; o.select_set(True)
        bpy.context.view_layer.objects.active = m.ob
        fbx = os.path.join(out_dir, m.name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                                 axis_forward='Y', axis_up='Z', bake_space_transform=False, use_triangles=True, mesh_smooth_type='EDGE',
                                 use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', object_types={'MESH', 'EMPTY'}, colors_type='LINEAR')
        for o in m.ucx_obs + m.lods[1:]:
            o.hide_render = True
        rec = {'name': m.name, 'class': m.cls, 'fbx': os.path.basename(fbx), 'materials': [mats[s].name for s in m.slots], 'source_blend': blend_name, **st}
        rec.update({k: v for k, v in d.items() if k != 'm'})
        recs.append(rec)
        print('MODULE', m.name, st)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, blend_name), compress=True)
    json.dump({k: v for k, v in MATREG.items() if any(k in r['materials'] for r in recs)}, open(os.path.join(out_dir, 'materials.json'), 'w'), indent=1)
    return recs


def new_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
    return sc
