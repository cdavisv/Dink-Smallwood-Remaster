"""Modular interior wall kits for the two largest placeholder wall families.
  31 inside/innwalls/walls/inn-   (int_wall_plaster*)      -> SM_Wall_Plaster_*
  80 inside/stnwalls/stonw-       (dungeon_wall_stone*)    -> SM_Wall_Dungeon_*
blender -b -t 4 --python wallkit_build.py            builds every module, LOD1, UCX, FBX, .blend, manifest.json
Pivot grid_wall: left end at x = 0, centre line of the thickness on y = 0, floor at z = 0, wall runs along +X; front face looks down -Y."""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PP = os.path.dirname(OUT)
TERRAIN = os.path.join(PP, 'Terrain')
M_PER_PX = 0.025                       # tools/analyse/regions.toml base_m_per_px
SEG = 100 * M_PER_PX                   # a 100 px wall sprite is one 2.5 m module
T_PLASTER, T_MASON, T_TIMBER = 2.5, 2.5, 1.8
SL_MAIN, SL_SECOND = 0, 1


def rng_for(name):
    return np.random.default_rng(sum(ord(c) * (i + 1) for i, c in enumerate(name)) % (2 ** 31))


def shade(me, deg=28.0):
    """smooth shading with hard edges only where faces meet at more than `deg` degrees: chamfers, timber arrises and stone
    edges stay crisp, the shallow relief of plaster sheets, bent sheets and jittered block faces no longer shows its triangles"""
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.set_sharp_from_angle(angle=math.radians(deg)); me.update()


def vnoise(p, seed, scale):
    """cheap smooth value noise from summed sines, range about -1..1, for vertex-level variation"""
    r = np.random.default_rng(seed)
    o = 0.0
    for k in range(5):
        d = r.normal(size=3); d /= np.linalg.norm(d)
        o = o + np.sin((p @ d) * scale * (1 + k * 0.7) + r.uniform(0, 6.28)) / (1 + k * 0.5)
    return o / 2.2


class Module:
    def __init__(self, name, length, height, timber_rows=None):
        self.name, self.length, self.height = name, length, height
        self.V, self.F, self.FM, self.UV, self.VT = [], [], [], [], []
        self.rng = rng_for(name)
        self.uvoff = self.rng.uniform(0, 1, 2)
        self.timber_rows = timber_rows
        self.col_fn = None
        self.bend_R = None
        self.clamp = False
        self.cls = 'kit_wall'
        self.ucx = []

    # ---- low level
    def add(self, verts, faces, mat, tile, mode='planar', uvoff=None, board=None, tag=0):
        """verts (n,3) in module space; faces lists of indices. UVs: planar by dominant face normal at `tile` metres per repeat,
        or 'board': u along the longest axis of the part, v squeezed inside one board of the timber texture"""
        base = len(self.V)
        verts = np.asarray(verts, np.float64)
        self.V.extend(verts.tolist())
        self.VT.extend([tag] * len(verts))
        off = self.uvoff if uvoff is None else uvoff
        if mode == 'board':
            ext = verts.max(0) - verts.min(0)
            ax = int(np.argmax(ext))
            others = [a for a in range(3) if a != ax]
            v0, w = board
        for f in faces:
            p = verts[f]
            n = np.cross(p[1] - p[0], p[2] - p[0])
            if len(f) > 3 and np.linalg.norm(n) < 1e-12:
                n = np.cross(p[2] - p[0], p[3] - p[0])
            a = int(np.argmax(np.abs(n)))
            if mode == 'stone':
                # the whole face shows the face of one big block of the masonry scan: no mortar lines on cap stones and quoins
                u0, v0_, u1, v1_ = STONE_WIN[int(self.rng.integers(len(STONE_WIN)))]
                ax2 = [k for k in range(3) if k != a]
                q2 = p[:, ax2]
                lo2 = q2.min(0); sp = np.maximum(q2.max(0) - lo2, 1e-6)
                if (sp[1] > sp[0]) != ((v1_ - v0_) > (u1 - u0)):
                    q2 = q2[:, ::-1]; lo2 = lo2[::-1]; sp = sp[::-1]
                sc = min((u1 - u0) / sp[0], (v1_ - v0_) / sp[1], 1.0 / tile)
                uv = [((u0 + u1) / 2 + (qq[0] - lo2[0] - sp[0] / 2) * sc, (v0_ + v1_) / 2 + (qq[1] - lo2[1] - sp[1] / 2) * sc) for qq in q2]
            elif mode == 'board':
                # across-grain coordinate: the face's other in-plane axis
                cross = [o for o in others if o != a]
                c = cross[0] if cross else others[0]
                lo = verts[:, c].min(); span = max(ext[c], 1e-6)
                uv = [((q[ax] / T_TIMBER + off[0]), v0 + ((q[c] - lo) / span - 0.5) * w * min(1.0, span / 0.15)) for q in p]
            else:
                if a == 1:
                    uv = [((q[0] * (1 if n[1] < 0 else -1)) / tile + off[0], q[2] / tile + off[1]) for q in p]
                elif a == 0:
                    uv = [((q[1] * (1 if n[0] > 0 else -1)) / tile + off[0] + 0.37, q[2] / tile + off[1]) for q in p]
                else:
                    uv = [(q[0] / tile + off[0] + 0.19, q[1] / tile + off[1] + 0.53) for q in p]
            self.F.append([base + i for i in f]); self.FM.append(mat); self.UV.append(uv)

    def block(self, lo, hi, mat, tile, bevel=0.012, jitter=0.004, mode='planar', own_uv=True, board=None, segs_x=1, tag=2, rot=None):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        lo = np.asarray(lo, float); hi = np.asarray(hi, float)
        if segs_x > 1:
            bmesh.ops.bisect_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 0.5], cuts=segs_x - 1)
            # connect the new verts into loops
            bmesh.ops.triangulate(bm, faces=[]) if False else None
        for v in bm.verts:
            v.co = Vector(lo + (np.array(v.co) + 0.5) * (hi - lo))
        if bevel > 0:
            b = min(bevel, 0.3 * float((hi - lo).min()))
            bmesh.ops.bevel(bm, geom=bm.edges[:], offset=b, segments=1, affect='EDGES', clamp_overlap=True)
        if jitter > 0:
            for v in bm.verts:
                v.co += Vector(self.rng.normal(0, jitter, 3))
        if rot is not None:
            c = Vector((lo + hi) / 2)
            R_ = Matrix.Rotation(rot[0], 3, 'Z') @ Matrix.Rotation(rot[1], 3, 'X') @ Matrix.Rotation(rot[2], 3, 'Y')
            for v in bm.verts:
                v.co = c + R_ @ (v.co - c)
        bm.verts.ensure_lookup_table()
        verts = [v.co[:] for v in bm.verts]
        faces = [[v.index for v in f.verts] for f in bm.faces]
        bm.free()
        self.add(verts, faces, mat, tile, mode, self.rng.uniform(0, 1, 2) if own_uv else None, board, tag=tag)

    def beam(self, lo, hi, bevel=0.012, warp=0.006, segs=5, hew=0.0022):
        """a timber: long box cut in `segs` along its long axis, chamfered, slightly bowed and twisted, mapped onto one board"""
        lo = np.asarray(lo, float); hi = np.asarray(hi, float)
        ext = hi - lo; ax = int(np.argmax(ext)); o = [a for a in range(3) if a != ax]
        b = min(bevel, 0.3 * ext[o].min())
        # octagonal-ish cross section (chamfered rectangle), ring of 8
        a0, a1 = lo[o[0]], hi[o[0]]; b0, b1 = lo[o[1]], hi[o[1]]
        ring = [(a0 + b, b0), (a1 - b, b0), (a1, b0 + b), (a1, b1 - b), (a1 - b, b1), (a0 + b, b1), (a0, b1 - b), (a0, b0 + b)]
        verts = []
        ph = self.rng.uniform(0, 6.28, 2); amp = self.rng.normal(0, warp, 2)
        for i in range(segs + 1):
            t = i / segs
            s = lo[ax] + t * ext[ax]
            d0 = amp[0] * math.sin(t * math.pi + ph[0] * 0) + self.rng.normal(0, 0.0015)
            d1 = amp[1] * math.sin(t * math.pi) + self.rng.normal(0, 0.0015)
            tw = self.rng.normal(0, 0.004)
            for (p, q) in ring:
                p += self.rng.normal(0, hew); q += self.rng.normal(0, hew)
                c = [0, 0, 0]
                c[ax] = s; c[o[0]] = p + d0 + tw * (q - (b0 + b1) / 2); c[o[1]] = q + d1 - tw * (p - (a0 + a1) / 2)
                verts.append(c)
        faces = []
        flip = (ax == 1)
        for i in range(segs):
            for k in range(8):
                a = i * 8 + k; b_ = i * 8 + (k + 1) % 8; c = (i + 1) * 8 + (k + 1) % 8; d = (i + 1) * 8 + k
                faces.append([a, d, c, b_] if not flip else [a, b_, c, d])
        e0 = list(range(8)); e1 = [segs * 8 + k for k in range(8)]
        faces.append(e0 if not flip else e0[::-1]); faces.append(e1[::-1] if not flip else e1)
        # orientation check: make the first side face point outward
        vv = np.array(verts); f = faces[0]
        n = np.cross(vv[f[1]] - vv[f[0]], vv[f[2]] - vv[f[0]]); cen = vv[f].mean(0) - vv.mean(0); cen[ax] = 0
        if np.dot(n, cen) < 0:
            faces = [x[::-1] for x in faces]
        rows = self.timber_rows
        v0, w = rows[self.rng.integers(len(rows))]
        self.add(verts, faces, SL_SECOND, T_TIMBER, 'board', self.rng.uniform(0, 1, 2), (v0, w), tag=1)

    def sheet(self, x0, x1, z0, z1, y, facing, mat, tile, nx=10, nz=8, relief=0.004, ztop_fn=None, zbot_fn=None, xs=None, yfn=None):
        """a wall face: grid in x,z at depth y, facing -1 (front, -Y) or +1 (back, +Y), with a shallow undulation"""
        xs = np.linspace(x0, x1, nx + 1) if xs is None else np.asarray(xs, float)
        nx = len(xs) - 1; verts = []
        for i, x in enumerate(xs):
            zt = z1 if ztop_fn is None else ztop_fn(x)
            zb = z0 if zbot_fn is None else zbot_fn(x)
            for j in range(nz + 1):
                z = zb + (zt - zb) * j / nz
                verts.append([x, y, z])
        verts = np.array(verts)
        und = vnoise(verts + np.array([0, facing * 3.1, 0]), int(self.rng.integers(1e6)), 2.2) * relief
        row = np.tile(np.arange(nz + 1), nx + 1)
        edge = (np.minimum.reduce([verts[:, 0] - xs[0], xs[-1] - verts[:, 0]]) < 1e-6) | (row == 0) | (row == nz)
        verts[:, 1] += facing * und * (~edge)
        if yfn is not None:
            verts[:, 1] += facing * yfn(verts)
        faces = []
        for i in range(nx):
            for j in range(nz):
                a = i * (nz + 1) + j; b = (i + 1) * (nz + 1) + j; c = b + 1; d = a + 1
                faces.append([a, b, c, d] if facing < 0 else [a, d, c, b])
        self.add(verts, faces, mat, tile)

    def quad(self, pts, mat, tile):
        self.add(pts, [[0, 1, 2, 3]], mat, tile)

    def strip(self, pa, pb, mat, tile):
        """quads between two equal-length polylines (pa[i], pa[i+1], pb[i+1], pb[i])"""
        n = len(pa)
        self.add(list(pa) + list(pb), [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)], mat, tile)

    # ---- finish
    def build(self, coll_parent):
        V = np.array(self.V, np.float64)
        if self.clamp:                                  # keep the bounds on the grid: jitter and bevels must not move the pivot or the snap size
            V[:, 0] = np.clip(V[:, 0], 0.0, self.length); V[:, 2] = np.clip(V[:, 2], 0.0, self.height)
        P = V.copy()                                    # param space kept for colours and the grime UV
        col = self.col_fn(P, np.array(self.VT)) if self.col_fn else np.zeros((len(V), 4))
        if self.bend_R:
            R = self.bend_R
            th = P[:, 0] / R
            rad = R - P[:, 1]
            V = np.stack([rad * np.sin(th), R - rad * np.cos(th), P[:, 2]], -1)
        me = bpy.data.meshes.new(self.name + '_LOD0')
        me.from_pydata([tuple(v) for v in V], [], self.F)
        me.update()
        uv0 = me.uv_layers.new(name='UVMap'); uv1 = me.uv_layers.new(name='UVGrime')
        k = 0
        for poly, uvs in zip(me.polygons, self.UV):
            assert poly.loop_total == len(uvs)
            for li, uv in zip(range(poly.loop_start, poly.loop_start + poly.loop_total), uvs):
                uv0.data[li].uv = uv
                vi = me.loops[li].vertex_index
                uv1.data[li].uv = (P[vi, 0] / SEG, min(max(P[vi, 2] / self.height, 0.0), 1.0))
        ca = me.color_attributes.new('Grime', 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set('color', np.clip(col, 0, 1).astype(np.float32).ravel())
        me.polygons.foreach_set('material_index', self.FM)
        # shading is set after the weld (shade below): flat faces showed every triangle of the uneven plaster and of the jittered stone faces
        ob = bpy.data.objects.new(self.name + '_LOD0', me)
        coll = bpy.data.collections.new(self.name); coll_parent.children.link(coll)
        coll['dink_class'] = self.cls; coll['dink_path'] = 'WallKits'; coll['dink_tex_px'] = 2048
        coll['dink_source'] = 'authored in Blender (wallkit_build.py), photoreal pass 11-12 Nov 2026; materials are the Terrain sets (CC0 scan based)'
        coll.objects.link(ob)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=2e-5)          # sheets, strips and end faces share their border verts: weld them into closed shells
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-6)
        nonman = sum(1 for e in bm.edges if not e.is_manifold)
        bm.to_mesh(me); bm.free(); me.update(); shade(me)
        # LOD1
        me1 = me.copy(); me1.name = self.name + '_LOD1'
        l1 = bpy.data.objects.new(self.name + '_LOD1', me1); coll.objects.link(l1)
        m = l1.modifiers.new('d', 'DECIMATE'); m.ratio = 0.45; m.use_collapse_triangulate = True; m.delimit = {'MATERIAL'}
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        me1b = bpy.data.meshes.new_from_object(l1.evaluated_get(dg)); l1.modifiers.clear(); l1.data = me1b; me1b.name = self.name + '_LOD1'; shade(me1b)
        # collision
        ucx = []
        for i, (lo, hi) in enumerate(self.ucx):
            bmc = bmesh.new(); bmesh.ops.create_cube(bmc, size=1.0)
            lo = np.array(lo); hi = np.array(hi)
            for v in bmc.verts:
                p = lo + (np.array(v.co) + 0.5) * (hi - lo)
                if self.bend_R:
                    R = self.bend_R; th = p[0] / R; rad = R - p[1]
                    p = np.array([rad * math.sin(th), R - rad * math.cos(th), p[2]])
                v.co = Vector(p)
            mc = bpy.data.meshes.new('UCX_%s_LOD0_%02d' % (self.name, i + 1)); bmc.to_mesh(mc); bmc.free()
            oc = bpy.data.objects.new(mc.name, mc); coll.objects.link(oc); oc.display_type = 'WIRE'; oc.hide_render = True
            ucx.append(oc)
        self.ob, self.lod1, self.ucx_obs, self.coll = ob, l1, ucx, coll
        me.calc_loop_triangles(); me1b.calc_loop_triangles()
        d = ob.dimensions
        return {'lod0_triangles': len(me.loop_triangles), 'lod1_triangles': len(me1b.loop_triangles), 'dimensions_m': [round(x, 3) for x in d],
                'open_edges': nonman, 'collision_hulls': len(ucx)}


# ---------------------------------------------------------------- colour functions (vertex colour 'Grime')
STONE_WIN = []
TAG_SHEET, TAG_TIMBER, TAG_STONE, TAG_LEAF, TAG_STEM = 0, 1, 2, 3, 4


def grime_fn(height, seed, damp_h=0.7, soot_h=0.6, extra_b=None, damp_gain=1.0, plaster=False):
    def f(P, tags):
        z = P[:, 2]
        n = vnoise(P, seed, 2.5)
        damp = np.clip((damp_h * (1 + 0.5 * n) - z) / (damp_h * 0.8), 0, 1) * damp_gain
        soot = np.clip((z - (height - soot_h * (1 + 0.4 * n))) / soot_h, 0, 1) ** 1.4
        b = np.zeros_like(z) if extra_b is None else extra_b(P)
        if plaster:
            # hands and shoulders: a greasy band about 0.9-1.4 m, patchy
            hand = np.exp(-((z - 1.15) / 0.28) ** 2) * np.clip(0.5 + 0.9 * vnoise(P, seed + 5, 1.3), 0, 1) * 0.45
            damp = np.clip(damp + hand, 0, 1)
            t = tags == TAG_TIMBER
            # timber: B = pale limewashed (top plate, posts, rails as in the sprite), R = dark handling and joints, sill stays dark
            pale = (z > 0.17) * np.clip(0.8 + 0.3 * vnoise(P, seed + 9, 3.0), 0, 1)
            dark = np.where(z < 0.17, 0.92, 0.0) + np.exp(-((z - 1.1) / 0.3) ** 2) * 0.2
            b = np.where(t, pale, b); damp = np.where(t, np.clip(dark, 0, 1), damp)
        damp = np.where(tags == TAG_STEM, 1.0, damp)
        return np.stack([damp, soot, b, np.ones_like(z)], -1)
    return f


def patch_b(centres):
    def f(P):
        o = np.zeros(len(P))
        for (cx, cz, r, side) in centres:
            d = np.sqrt((P[:, 0] - cx) ** 2 + (P[:, 2] - cz) ** 2)
            o = np.maximum(o, np.clip(1.25 - d / r, 0, 1) * ((P[:, 1] * side) > 0 if side else 1))
        return o
    return f


# ---------------------------------------------------------------- plaster family: timber frame with plaster infill
PH = 3.0           # wall height (kit walls snap to 0.5 m)
PT = 0.15          # timber depth = wall thickness
SILL = 0.14
PLATE = 0.15
POST = 0.14
SETBACK = 0.016


def panel(m, x0, x1, z0, z1):
    """plaster infill between timbers, both faces: set back from the timber face, built up against the timber, uneven"""
    def axis(a, b, step):
        n = max(2, int(round((b - a) / step)))
        inner = np.linspace(a + 0.035, b - 0.035, n + 1)
        return np.concatenate([[a, a + 0.012], inner, [b - 0.012, b]])
    xs = axis(x0, x1, 0.22); zs = axis(z0, z1, 0.28)
    nxs, nz = len(xs), len(zs)
    V = []; F = []
    for facing in (-1, 1):
        verts = []
        for x in xs:
            for z in zs:
                e = min(x - x0, x1 - x, z - z0, z1 - z)
                build = 0.011 * max(0.0, 1 - e / 0.035) ** 1.5              # fillet of plaster against the timber
                verts.append([x, facing * (PT / 2 - SETBACK + build), z])
        verts = np.array(verts)
        und = vnoise(verts + np.array([0, facing * 3.1, 0]), int(m.rng.integers(1e6)), 3.0) * 0.004 + vnoise(verts, int(m.rng.integers(1e6)), 11.0) * 0.0015
        e = np.minimum.reduce([verts[:, 0] - x0, x1 - verts[:, 0], verts[:, 2] - z0, z1 - verts[:, 2]])
        verts[:, 1] += facing * und * (e > 0.02)
        base = len(V); V += verts.tolist()
        for i in range(nxs - 1):
            for j in range(nz - 1):
                a = base + i * nz + j; b = base + (i + 1) * nz + j; c = b + 1; d = a + 1
                F.append([a, b, c, d] if facing < 0 else [a, d, c, b])
    o = nxs * nz                                    # back sheet offset; join the borders so the infill is a closed slab
    for i in range(nxs - 1):
        a, b = i * nz, (i + 1) * nz
        F.append([a, a + o, b + o, b]); F.append([a + nz - 1, b + nz - 1, b + nz - 1 + o, a + nz - 1 + o])
    for j in range(nz - 1):
        a, b = j, j + 1
        F.append([a, b, b + o, a + o]); c = (nxs - 1) * nz
        F.append([c + a, c + a + o, c + b + o, c + b])
    m.add(V, F, SL_MAIN, T_PLASTER, tag=TAG_SHEET)


def peg(m, x, z):
    for s in (-1, 1):
        a, b = sorted([s * (PT / 2 - 0.004), s * (PT / 2 + 0.011)])
        m.block([x - 0.011, a, z - 0.011], [x + 0.011, b, z + 0.011], SL_SECOND, T_TIMBER, 0.004, 0.0015, own_uv=True, tag=TAG_TIMBER)


def brace(m, xa, za, xb, zb, w=0.11):
    """diagonal brace as a sheared timber between two points (centre line), full wall depth less a little"""
    d = np.array([xb - xa, zb - za]); L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]]) * w / 2
    y = PT / 2 - 0.006
    verts = []
    for t in (0.0, 0.5, 1.0):
        c = np.array([xa, za]) + d * L * t
        for (sn, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append([c[0] + sn * n[0] + m.rng.normal(0, 0.002), sy * y, c[1] + sn * n[1] + m.rng.normal(0, 0.002)])
    faces = [[3, 2, 1, 0], [8, 9, 10, 11]]
    for i in range(2):
        for k in range(4):
            a = i * 4 + k; b = i * 4 + (k + 1) % 4
            faces.append([a, b, b + 4, a + 4])
    rows = m.timber_rows; v0, wv = rows[m.rng.integers(len(rows))]
    vv = np.array(verts); f = faces[2]
    nn = np.cross(vv[f[1]] - vv[f[0]], vv[f[2]] - vv[f[0]]); cc = vv[f].mean(0) - vv.mean(0)
    if np.dot(nn, cc) < 0:
        faces = [x[::-1] for x in faces]
    m.add(verts, faces, SL_SECOND, T_TIMBER, 'board', m.rng.uniform(0, 1, 2), (v0, wv), tag=TAG_TIMBER)


def frame(m, x0, x1, posts, variant_b=False, z0=0.0, sill=True, plate=True, brace_bay=None):
    """posts: list of (x_left, width). Bays between posts get plaster panels; module ends without a post get a plaster end."""
    zb = z0 + (SILL if sill else 0.0); zt = m.height - (PLATE if plate else 0.0)
    if sill:
        m.beam([x0, -PT / 2 - 0.012, z0], [x1, PT / 2 + 0.012, z0 + SILL], 0.012, 0.003, max(3, int((x1 - x0) / 0.35)))
    if plate:
        m.beam([x0, -PT / 2 - 0.022, zt], [x1, PT / 2 + 0.022, m.height], 0.014, 0.004, max(3, int((x1 - x0) / 0.35)))
    edges = [x0]
    for (px, pw) in posts:
        m.beam([px, -PT / 2, zb - 0.005], [px + pw, PT / 2, zt + 0.005], 0.012, 0.004, 8)
        for z in (zb + 0.07, zt - 0.07):
            peg(m, px + pw * 0.5, z)
        edges += [px, px + pw]
    edges.append(x1)
    for k in range(0, len(edges), 2):
        a, b = edges[k], edges[k + 1]
        if b - a < 0.04:
            continue
        if variant_b and (zt - zb) > 1.8:
            zr = 1.40
            m.beam([a - 0.004, -PT / 2 + 0.004, zr], [b + 0.004, PT / 2 - 0.004, zr + 0.11], 0.010, 0.003, max(2, int((b - a) / 0.35)))
            panel(m, a, b, zr + 0.11, zt)
            if brace_bay == k // 2:
                brace(m, a + 0.06, zb + 0.02, b - 0.06, zr - 0.02)
                # the brace divides the lower panel: plaster on both sides of it (one sheet behind is enough at this depth)
            panel(m, a, b, zb, zr)
        else:
            panel(m, a, b, zb, zt)


def plaster_modules(rows):
    out = []
    ucx = lambda L, z0=0.0: [([0, -PT / 2 - 0.02, z0], [L, PT / 2 + 0.02, PH])]

    def mk(name, length=SEG):
        return Module('SM_Wall_Plaster_' + name, length, PH, rows)
    mid = SEG / 2 + POST / 2
    m = mk('Straight_A'); frame(m, 0, SEG, [(0.0, POST), (mid - POST / 2, POST)])
    m.col_fn = grime_fn(PH, 11, 0.5, 0.8, plaster=True); m.ucx = ucx(SEG)
    out.append((m, ['int_wall_plaster', 'int_wall_plaster_side'], 'frames 26-30 (100x100 px) and frame 23 (18x100 px edge-on strip)',
                'straight 2.5 m run: sill beam, top plate, a post at the left end and one mid-span, two plaster bays. The right end has no post: the next module\'s left post (or an End/CornerPost module) closes it. For int_wall_plaster_side the same module is yawed 90 degrees'))
    m = mk('Straight_B'); frame(m, 0, SEG, [(0.0, POST), (mid - POST / 2, POST)], variant_b=True, brace_bay=1)
    m.col_fn = grime_fn(PH, 12, 0.7, 0.8, patch_b([(0.7, 0.55, 0.4, -1), (1.95, 1.9, 0.3, 1)]), 1.2, plaster=True); m.ucx = ucx(SEG)
    out.append((m, ['int_wall_plaster'], 'frames 27-30 (texture variants of 26)', 'the same run with a mid rail at 1.4 m and a diagonal brace in the right-hand lower bay; vertex colour B marks two fallen-plaster patches. Use for about one module in four'))
    for side in ('L', 'R'):
        m = mk('CornerPost_' + side); CP = 0.18
        if side == 'L':
            frame(m, CP, SEG, [(mid - POST / 2, POST)])
            m.beam([0.0, -CP / 2, 0.0], [CP, CP / 2, PH + 0.015], 0.02, 0.004, 9); px = CP / 2
        else:
            frame(m, 0, SEG - CP, [(0.0, POST), (mid - POST / 2, POST)])
            m.beam([SEG - CP, -CP / 2, 0.0], [SEG, CP / 2, PH + 0.015], 0.02, 0.004, 9); px = SEG - CP / 2
        for z in (0.07, PH - 0.07, 1.4):
            peg(m, px, z)
        m.col_fn = grime_fn(PH, 13 + (side == 'R'), 0.5, 0.8, plaster=True); m.ucx = ucx(SEG)
        fr = 'frame 22 (post at the left)' if side == 'L' else 'frame 21 (post at the right)'
        out.append((m, ['int_wall_plaster_corner_' + side.lower()], fr, 'run with a full-height 18 cm chamfered corner post at its %s end, standing 1.5 cm proud of the frame on both faces; the post centre is 9 cm in from the module end' % ('left' if side == 'L' else 'right')))
    for side in ('L', 'R'):
        m = mk('End_' + side)
        posts = [(0.0, POST), (mid - POST / 2, POST)] + ([(SEG - POST, POST)] if side == 'R' else [])
        frame(m, 0, SEG, posts)
        m.col_fn = grime_fn(PH, 15 + (side == 'R'), 0.5, 0.8, plaster=True); m.ucx = ucx(SEG)
        fr = 'frame 20 (free end at the left)' if side == 'L' else 'frame 19 (free end at the right)'
        out.append((m, ['int_wall_plaster_end_' + side.lower()], fr, 'run whose free %s end is a full post, so the wall reads solid edge-on' % ('left' if side == 'L' else 'right')))
    JW = 18 * M_PER_PX
    for side in ('L', 'R'):
        m = Module('SM_Wall_Plaster_DoorJamb_' + side, JW, PH, rows)
        if side == 'L':                 # stands left of the door: door post on its right end
            frame(m, 0, JW, [(0.0, 0.10), (JW - POST, POST)])
        else:
            frame(m, 0, JW, [(0.0, POST), (JW - 0.10, 0.10)])
        m.col_fn = grime_fn(PH, 17 + (side == 'R'), 0.5, 0.8, plaster=True); m.ucx = [([0, -PT / 2 - 0.02, 0], [JW, PT / 2 + 0.02, PH])]
        fr = 'frame 35 (left of the door)' if side == 'L' else 'frame 36 (right of the door)'
        out.append((m, ['int_wall_plaster_doorjamb'], fr, '45 cm stub: a 14 cm door post on the door side, a 10 cm stud on the wall side, a narrow plaster bay between, sill and plate. One class covers both frames: bind frame 35 to _L and frame 36 to _R by sequence row, or use yaw_from_sprite'))
    m = Module('SM_Wall_Plaster_DoorHeader', 1.0, PH, rows)
    m.beam([-0.05, -PT / 2 - 0.008, 2.06], [1.05, PT / 2 + 0.008, 2.22], 0.014, 0.004, 4)                 # lintel, housed 5 cm into each door post
    frame(m, 0, 1.0, [], z0=2.22, sill=False)
    peg(m, 0.03, 2.14); peg(m, 0.97, 2.14)
    m.col_fn = grime_fn(PH, 19, 0.0, 0.8, None, 0.0, plaster=True); m.ucx = [([0, -PT / 2 - 0.02, 2.06], [1.0, PT / 2 + 0.02, PH])]
    out.append((m, [], 'no sprite: the original leaves the door gap open to the top', 'authored architecture: pegged lintel beam with a plaster bay and the top plate over a 1.0 m x 2.06 m door opening (pivot on the floor line, so the mesh starts 2.06 m up), between a DoorJamb_L and a DoorJamb_R. Not family-bound; place by hand per doorway'))
    return out


# ---------------------------------------------------------------- dungeon family
DH = 3.0
DT = 30 * M_PER_PX        # 0.75 m: the edge-on strip is 30 px
CAP = 0.22
PLINTH = 0.34


def stone(m, lo, hi, bevel=0.016, jitter=0.005, rot=None):
    m.block(lo, hi, SL_MAIN, T_MASON, bevel, jitter, mode='stone', tag=TAG_STONE, rot=rot)


def course(m, x0, x1, y0, y1, z0, z1, lmin, lmax, bevel=0.016, jitter=0.005, hvar=0.012, gap=0.012, skip=None, miss=0.0):
    x = x0
    while x < x1 - 1e-6:
        l = float(m.rng.uniform(lmin, lmax))
        if x1 - (x + l) < lmin * 0.6:
            l = x1 - x
        xa, xb = x + gap / 2, min(x + l, x1) - gap / 2
        if (skip is None or not skip((xa + xb) / 2)) and m.rng.uniform() >= miss:
            dz = float(m.rng.normal(0, hvar))
            stone(m, [xa, y0 + m.rng.normal(0, 0.006), z0], [xb, y1 + m.rng.normal(0, 0.006), z1 + dz], bevel, jitter,
                  rot=(m.rng.normal(0, 0.012), m.rng.normal(0, 0.01), m.rng.normal(0, 0.01)))
        x += l


def coping(m, x0, x1, skip=None):
    """the wall top as the camera sees it: big individual coping stones, two staggered rows across the thickness, weathered round,
    uneven in height, a few missing so the rubble core shows"""
    for (ya, yb) in ((-DT / 2 - 0.02, -0.008), (0.008, DT / 2 + 0.02)):
        course(m, x0, x1, ya, yb, m.height - CAP, m.height, 0.30, 0.58, bevel=0.03, jitter=0.006, hvar=0.018, gap=0.016, skip=skip, miss=0.05)


def quoins(m, x_end, direction, z0, z1):
    """a column of dressed blocks at a wall end, alternately long and short, a little proud of both faces, edges bevelled,
    one or two pushed in or out: the end profile is not a ruler line"""
    z = z0; i = int(m.rng.integers(2))
    while z < z1 - 1e-6:
        h = min(float(m.rng.uniform(0.27, 0.36)), z1 - z)
        if z1 - (z + h) < 0.14:
            h = z1 - z
        l = (0.46 if i % 2 == 0 else 0.27) + float(m.rng.normal(0, 0.02))
        inset = abs(float(m.rng.normal(0, 0.008))) + (0.03 if m.rng.uniform() < 0.12 else 0.0)
        proud = 0.018 + float(m.rng.normal(0, 0.006))
        xa, xb = sorted([x_end + direction * inset, x_end + direction * (inset + l)])
        stone(m, [xa, -DT / 2 - proud, z + 0.006], [xb, DT / 2 + proud, z + h - 0.006], 0.018, 0.005)
        z += h; i += 1


def dungeon_run(m, x0, x1, ztop=None, cap=True, plinth=True, nx=None, cap_skip=None, xs=None, ends=(True, True)):
    zt = (m.height - (CAP if cap else 0)) if ztop is None else None
    nx = nx or max(2, int(round((x1 - x0) / 0.25)))
    y = DT / 2 - 0.03
    tf = (lambda x: zt) if ztop is None else ztop
    xs = np.linspace(x0, x1, nx + 1) if xs is None else np.asarray(xs, float)
    for facing in (-1, 1):
        m.sheet(x0, x1, 0.0, 0.0, facing * y, facing, SL_MAIN, T_MASON, nx, 9, 0.009, ztop_fn=tf, xs=xs)
    # top (under the coping, or the exposed core in a breach), bottom and ends: with the faces they weld into one closed shell
    m.strip([[x, -y, tf(x)] for x in xs], [[x, y, tf(x)] for x in xs], SL_MAIN, T_MASON * 0.5)
    m.strip([[x, y, 0.0] for x in xs], [[x, -y, 0.0] for x in xs], SL_MAIN, T_MASON)
    for (xe, fl) in ((xs[0], False), (xs[-1], True)):
        zt_ = tf(xe); col_a = [[xe, y, zt_ * k / 9] for k in range(10)]; col_b = [[xe, -y, zt_ * k / 9] for k in range(10)]
        m.strip(col_b, col_a, SL_MAIN, T_MASON) if not fl else m.strip(col_a, col_b, SL_MAIN, T_MASON)
    if cap:
        coping(m, x0, x1, cap_skip)
    qw = 0.5
    if plinth:
        for s in (-1, 1):
            ya, yb = sorted([s * (DT / 2 - 0.05), s * (DT / 2 + 0.04)])
            course(m, x0 + (qw if ends[0] else 0), x1 - (qw if ends[1] else 0), ya, yb, 0.0, PLINTH, 0.38, 0.8, 0.018, 0.005, 0.02)
    if ends[0]:
        quoins(m, x0, 1, 0.0, min(tf(x0), m.height - (CAP if cap else 0)))
    if ends[1]:
        quoins(m, x1, -1, 0.0, min(tf(x1), m.height - (CAP if cap else 0)))


def ivy(m, x0, x1, ztop, yface):
    """woody stems climbing from the base, branching, with dense leaf masses (alpha cards from the leaf atlas), hanging tips at the top"""
    r = m.rng
    cells = [(c, rw) for rw in range(3) for c in range(3) if not (rw == 2 and c in (1, 2))]       # skip the two yellowed leaves mostly

    def tube(pts, r0, r1, sides=5):
        verts = []
        for i, p in enumerate(pts):
            rr = r0 + (r1 - r0) * i / max(1, len(pts) - 1)
            for k in range(sides):
                a = 2 * math.pi * k / sides
                verts.append([p[0] + rr * math.cos(a), p[1] - rr * (0.6 + 0.6 * math.sin(a)), p[2] + rr * math.sin(a) * 0.3])
        faces = [[i * sides + k, i * sides + (k + 1) % sides, (i + 1) * sides + (k + 1) % sides, (i + 1) * sides + k] for i in range(len(pts) - 1) for k in range(sides)]
        m.add(verts, faces, SL_MAIN, T_MASON, mode='stone', tag=TAG_STEM)

    def leaf(x, y, z, size, hang=1.0):
        c, rw = cells[r.integers(len(cells))] if r.uniform() > 0.04 else (int(r.integers(1, 3)), 2)
        u0, v0 = c / 3.0, 1 - (rw + 1) / 3.0
        a = math.pi + r.normal(0, 0.55)                       # tip points down, give or take
        ca, sa = math.cos(a), math.sin(a)
        tilt = r.uniform(0.15, 0.7) * hang; out = r.uniform(0.0, 0.035)
        # two quads folded along the midrib; local (s along the leaf from stalk to tip, t across)
        P = []; UVs = []
        for (sl, tl, lift) in ((0, -0.5, 0.012), (0, 0, 0.0), (0, 0.5, 0.012), (1, -0.5, 0.012), (1, 0, 0.0), (1, 0.5, 0.012)):
            px = (tl * ca - (sl - 0.15) * sa * -1) * size
            pz = (tl * sa + (sl - 0.15) * ca * -1) * size
            # hang: the tip end falls away from the wall less than the stalk end stands off it
            py = y - out - (1 - sl) * size * tilt * 0.5 - lift - abs(tl) * size * 0.15
            P.append([x + px, py, z - pz * -1 if False else z + pz])
            UVs.append((u0 + (tl + 0.5) / 3.0, v0 + (1 - sl) / 3.0))
        base = len(m.V)
        m.V.extend(P); m.VT.extend([TAG_LEAF] * 6)
        for f in ([0, 1, 4, 3], [1, 2, 5, 4]):
            m.F.append([base + i for i in f]); m.FM.append(SL_SECOND); m.UV.append([UVs[i] for i in f])

    nleaf = 0
    for s in range(6):
        x = r.uniform(x0 + 0.2, x1 - 0.2); z = 0.0; pts = [[x, yface - 0.02, 0.0]]
        top = ztop + 0.05 if s < 4 else r.uniform(1.2, 2.2)
        while z < top:
            z += r.uniform(0.12, 0.2); x = float(np.clip(x + r.normal(0, 0.06), x0 + 0.08, x1 - 0.08))
            pts.append([x, yface - 0.015 - r.uniform(0, 0.01), min(z, ztop + 0.04)])
        tube(pts, r.uniform(0.016, 0.028), 0.005)
        # side shoots with leaves, denser higher up where the light is
        for i, p in enumerate(pts[2:]):
            dens = 0.35 + 0.65 * min(1.0, p[2] / 1.6)
            for _ in range(int(r.poisson(0.95 * dens))):
                d = r.choice([-1, 1]); L = r.uniform(0.15, 0.5); q = list(p); sp = [list(p)]
                for k in range(4):
                    q = [q[0] + d * L / 4, q[1] - r.uniform(0, 0.006), q[2] + r.normal(0.02, 0.04)]
                    if not (x0 + 0.03 < q[0] < x1 - 0.03):
                        break
                    sp.append(list(q))
                    for _ in range(int(r.integers(2, 4))):
                        leaf(q[0] + r.normal(0, 0.04), q[1], min(q[2] + r.normal(0, 0.05), ztop + 0.1), r.uniform(0.075, 0.125)); nleaf += 1
                if len(sp) > 1 and r.uniform() < 0.4:
                    tube(sp, 0.005, 0.002, 3)
        if s < 4:      # over the coping and hanging tips down the front
            xt = pts[-1][0]
            for k in range(int(r.integers(2, 4))):
                hx = xt + r.normal(0, 0.25); hz = ztop + 0.06; hp = [[hx, yface + 0.05, hz], [hx, yface - 0.05, hz - 0.02]]
                for j in range(int(r.integers(3, 7))):
                    hz -= r.uniform(0.07, 0.11); hx += r.normal(0, 0.012)
                    hp.append([hx, yface - 0.06 - 0.01 * j, hz])
                    leaf(hx + r.normal(0, 0.02), yface - 0.06 - 0.01 * j, hz, r.uniform(0.055, 0.085), 1.6); nleaf += 1
                    leaf(hx + r.normal(0, 0.03), yface - 0.05, hz + 0.03, r.uniform(0.05, 0.08), 1.3); nleaf += 1
                tube(hp, 0.004, 0.0015, 3)
            for k in range(14):
                leaf(xt + r.normal(0, 0.3), yface + r.uniform(0.0, 0.3), ztop + 0.05, r.uniform(0.06, 0.09), 0.3); nleaf += 1
    print('ivy leaves', nleaf)


def dungeon_modules():
    out = []

    def mk(name, length=SEG, height=DH):
        return Module('SM_Wall_Dungeon_' + name, length, height)
    box = lambda L, H=DH: [([0, -DT / 2, 0], [L, DT / 2, H])]
    m = mk('Straight_A'); dungeon_run(m, 0, SEG); m.col_fn = grime_fn(DH, 31, 0.8, 0.7); m.ucx = box(SEG)
    out.append((m, ['dungeon_wall_stone', 'dungeon_wall_stone_side'], 'frames 1-4, 12, 14, 15 (100x100 px) and frame 5 (30x100 px edge-on strip)',
                'straight 2.5 m run, 0.75 m thick (the 30 px strip), with a coping of individual stones, a plinth course and dressed quoin columns at both ends. For dungeon_wall_stone_side frame 5 the same module is yawed 90 degrees'))
    m = mk('Straight_B'); dungeon_run(m, 0, SEG); m.col_fn = grime_fn(DH, 32, 1.5, 0.7, None, 1.4); m.ucx = box(SEG)
    out.append((m, ['dungeon_wall_stone'], 'frames 2-4 (texture variants)', 'same run with different coping, plinth and quoin stones, damp and moss risen to about 1.5 m; alternate with _A'))
    m = mk('Half', SEG / 2); dungeon_run(m, 0, SEG / 2); m.col_fn = grime_fn(DH, 33, 0.8, 0.7); m.ucx = box(SEG / 2)
    out.append((m, ['dungeon_wall_stone_side'], 'frame 6 (30x50 px half strip)', '1.25 m run; yawed 90 degrees for the half-length edge-on strip'))
    R = SEG
    L = R * math.pi / 2
    m = mk('Curve', L); dungeon_run(m, 0, L, nx=20); m.col_fn = grime_fn(DH, 34, 0.8, 0.7); m.bend_R = R
    m.ucx = [([L * i / 4, -DT / 2, 0], [L * (i + 1) / 4, DT / 2, DH]) for i in range(4)]
    out.append((m, ['dungeon_wall_stone_curve'], 'frames 7-10 (100x150 px, four orientations)',
                'quarter-circle wall, centre-line radius 2.5 m: starts at the pivot heading +X, ends at (2.5, 2.5) heading +Y. One mesh for all four frames by yaw (7: 0, 8: 90, 9: 180, 10: 270 degrees is my reading of the sprites; verify per screen)'))
    AH = 3.5                    # the sprite is 129 px (3.2 m); kit pieces snap to 0.5 m
    m = mk('Arch', SEG, AH)
    pier_w = 0.5; open_w = SEG - 2 * pier_w; spring = 2.2; r0 = open_w / 2; r1 = AH - spring
    for (xa, xb) in ((0.0, pier_w), (SEG - pier_w, SEG)):
        i = 0
        stone(m, [xa - 0.05, -DT / 2 - 0.04, 0.0], [xb + 0.05, DT / 2 + 0.04, 0.26], 0.02, 0.005)
        # mortar core behind the pier stones so the joints are dark mortar, not daylight
        m.block([xa + 0.03, -DT / 2 + 0.06, 0.2], [xb - 0.03, DT / 2 - 0.06, spring + 0.05], SL_MAIN, T_MASON, 0.0, 0.0, tag=TAG_SHEET)
        z = 0.26
        while z < spring - 1e-6:
            h = min(float(m.rng.uniform(0.26, 0.38)), spring - z)
            if spring - (z + h) < 0.15:
                h = spring - z
            if i % 2 == 0:
                stone(m, [xa, -DT / 2 + 0.03, z + 0.005], [xb, DT / 2 - 0.03, z + h - 0.005])
            else:
                mid = xa + (xb - xa) * float(m.rng.uniform(0.4, 0.6))
                stone(m, [xa, -DT / 2 + 0.03, z + 0.005], [mid - 0.005, DT / 2 - 0.03, z + h - 0.005])
                stone(m, [mid + 0.005, -DT / 2 + 0.03, z + 0.005], [xb, DT / 2 - 0.03, z + h - 0.005])
            z += h; i += 1
    nvs = 11
    cx = SEG / 2
    for i in range(nvs):
        a0 = math.pi * i / nvs + 0.008; a1 = math.pi * (i + 1) / nvs - 0.008
        key = (i == nvs // 2)
        ro = r1 + (0.06 if key else float(m.rng.normal(0, 0.02)))
        d = DT / 2 - 0.03 + (0.03 if key else float(m.rng.normal(0, 0.008)))
        bm = bmesh.new()
        for (a, rr) in ((a0, r0), (a1, r0), (a1, ro), (a0, ro)):
            for yy in (-d, d):
                bm.verts.new((cx - rr * math.cos(a), yy, spring + rr * math.sin(a)))
        bmesh.ops.convex_hull(bm, input=bm.verts[:])
        bmesh.ops.dissolve_limit(bm, angle_limit=0.02, verts=bm.verts[:], edges=bm.edges[:])
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.016, segments=1, affect='EDGES', clamp_overlap=True)
        for v in bm.verts:
            v.co += Vector(m.rng.normal(0, 0.004, 3))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.verts.ensure_lookup_table()
        m.add([v.co[:] for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces], SL_MAIN, T_MASON, mode='stone', tag=TAG_STONE)
        bm.free()
    m.col_fn = grime_fn(AH, 35, 0.7, 0.6)
    m.ucx = [([0, -DT / 2, 0], [pier_w, DT / 2, spring]), ([SEG - pier_w, -DT / 2, 0], [SEG, DT / 2, spring]), ([0.15, -DT / 2, spring + r0 * 0.75], [SEG - 0.15, DT / 2, AH])]
    out.append((m, ['dungeon_wall_stone_arch'], 'frame 16 (100x129 px)', 'free-standing arch as drawn: two 0.5 m piers on plinths and a ring of eleven voussoirs with a proud keystone; clear opening 1.5 m wide, 2.95 m at the crown; 3.5 m overall. Walk-through: collision is the two piers and the crown only'))
    m = mk('Ivy', SEG, DH); dungeon_run(m, 0, SEG); ivy(m, 0.05, SEG - 0.05, DH, -DT / 2 + 0.03)
    m.col_fn = grime_fn(DH, 36, 1.2, 0.6, None, 1.2); m.ucx = box(SEG)
    out.append((m, ['dungeon_wall_stone_ivy'], 'frames 18, 19 (100x118 px)', 'straight run with ivy on the front (-Y) face: woody stems from the base, leaf masses as alpha cards from a scanned ivy leaf atlas, growth over the coping and hanging tips. Second material MI_Wall_Ivy (WallKits/Textures/T_Wall_Ivy_BC/N/ORM, alpha-tested, two-sided)'))
    # breach: a stepped collapse along the courses
    m = mk('Breach', SEG, DH)
    xc = 1.5; ch = 0.31
    steps_l = [(xc - 0.28, 4), (xc - 0.52, 3), (xc - 0.70, 2), (xc - 0.95, 1)]        # (x where the wall reaches this many courses below the top, counted from the centre outwards)
    steps_r = [(xc + 0.22, 5), (xc + 0.5, 3), (xc + 0.62, 2), (xc + 0.9, 1)]
    top = DH - CAP

    def ztop(x):
        if x <= steps_l[-1][0] or x >= steps_r[-1][0]:
            return top
        if x < xc - 0.28:
            for (sx, n) in steps_l:
                if x >= sx:
                    return top - n * ch
        if x > xc + 0.22:
            for (sx, n) in steps_r:
                if x <= sx:
                    return top - n * ch
        return top - 5 * ch
    e = 0.004
    brk = sorted([sx for sx, _ in steps_l] + [sx for sx, _ in steps_r] + [xc - 0.28, xc + 0.22])
    xs = sorted(set([0.0, SEG] + [b - e for b in brk] + [b + e for b in brk] + list(np.linspace(0, SEG, 9))))
    dungeon_run(m, 0, SEG, ztop=ztop, xs=xs, cap_skip=lambda x: steps_l[-1][0] - 0.1 < x < steps_r[-1][0] + 0.1)
    r = m.rng
    # stones left sitting loose on the steps
    for (sx, n) in steps_l[:-1] + steps_r[:-1]:
        zz = ztop(sx + (0.05 if sx < xc else -0.05))
        l = r.uniform(0.2, 0.34); yy = r.uniform(-0.2, 0.2); d = 1 if sx < xc else -1
        stone(m, [sx + d * 0.02 - (l if d < 0 else 0), yy - 0.16, zz], [sx + d * 0.02 + (l if d > 0 else 0), yy + 0.16, zz + r.uniform(0.14, 0.24)], 0.02, 0.01, rot=(r.normal(0, 0.25), r.normal(0, 0.08), r.normal(0, 0.08)))
    # the heap: fallen blocks on both sides over a low dust-and-mortar mound
    for s in (-1, 1):
        cx_, cy_ = xc, s * (DT / 2 + 0.35)
        ring = 12; verts = [[cx_, cy_ - s * 0.2, 0.34]]
        for k in range(ring):
            a = 2 * math.pi * k / ring; rr = 0.95 + r.normal(0, 0.08)
            verts.append([cx_ + rr * math.cos(a) * 1.0, cy_ + rr * math.sin(a) * 0.62, 0.0])
        mid = []
        for k in range(ring):
            a = 2 * math.pi * k / ring; rr = 0.5 + r.normal(0, 0.05)
            mid.append([cx_ + rr * math.cos(a), cy_ - s * 0.1 + rr * math.sin(a) * 0.6, 0.2 + r.normal(0, 0.02)])
        verts += mid
        faces = [[0, 1 + ring + k, 1 + ring + (k + 1) % ring] for k in range(ring)] + [[1 + ring + k, 1 + k, 1 + (k + 1) % ring, 1 + ring + (k + 1) % ring] for k in range(ring)]
        faces.append([1 + k for k in range(ring)][::-1])                    # closed underneath
        m.add(verts, faces, SL_MAIN, T_MASON * 0.4, uvoff=r.uniform(0, 1, 2), tag=TAG_STONE)
        for k in range(16):
            a = r.uniform(0, 6.28); rr = r.uniform(0.0, 0.95) ** 0.8
            bx = cx_ + rr * math.cos(a); by = cy_ + rr * math.sin(a) * 0.6
            if abs(by) < DT / 2 + 0.06:
                by = s * (DT / 2 + 0.1)
            sz = r.uniform(0.12, 0.34) * (1.0 - 0.4 * rr)
            zb = max(0.0, 0.3 * (1 - rr / 0.95))
            stone(m, [bx - sz * 0.7, by - sz * 0.45, zb], [bx + sz * 0.7, by + sz * 0.45, zb + sz * r.uniform(0.45, 0.75)], 0.025, 0.012,
                  rot=(r.uniform(0, 3.14), r.normal(0, 0.3), r.normal(0, 0.3)))
    m.col_fn = grime_fn(DH, 37, 0.9, 0.5)
    m.ucx = [([0, -DT / 2, 0], [steps_l[-1][0], DT / 2, DH]), ([steps_r[-1][0], -DT / 2, 0], [SEG, DT / 2, DH]), ([steps_l[-1][0], -DT / 2, 0], [steps_r[-1][0], DT / 2, top - 4 * ch])]
    out.append((m, ['dungeon_wall_stone_cracked'], 'frame 20 (100x103 px)', 'run with a collapse stepped down the courses to 1.5 m below the top, the rubble core exposed between the faces, loose stones on the steps and a heap of fallen blocks over a mound on both sides (up to 1.3 m out from each face: outside the wall footprint). The class notes call this the likely visual for breached walls, so keep its script binding'))
    return out


# ---------------------------------------------------------------- materials (preview of the Unreal material contract)
def tex(nt, setname, key, cs, uvmap='UVMap'):
    info = json.load(open(os.path.join(TERRAIN, setname, 'set.json')))
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TERRAIN, info['files'][key]), check_existing=True)
    t.image.colorspace_settings.name = cs
    return t


def blend_material(name, set_a, set_b, blend_channel, damp_tint, damp_dark, soot=True, damp_rough=-0.12):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'Grime'
    sep = nt.nodes.new('ShaderNodeSeparateColor'); L.new(at.outputs['Color'], sep.inputs[0])
    damp, sootv, bl = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    fac = {'R': damp, 'B': bl}[blend_channel]

    def mix(a, b_, f, dt='RGBA', bt='MIX'):
        n = nt.nodes.new('ShaderNodeMix'); n.data_type = dt
        if dt == 'RGBA':
            n.blend_type = bt
        i0 = {'RGBA': (6, 7, 2), 'FLOAT': (2, 3, 0)}[dt]
        for sock, v in ((n.inputs[0], f), (n.inputs[i0[0]], a), (n.inputs[i0[1]], b_)):
            if hasattr(v, 'links'):
                L.new(v, sock)
            else:
                sock.default_value = v
        return n.outputs[i0[2]]
    ta = {k: tex(nt, set_a, k, cs) for k, cs in (('BC', 'sRGB'), ('N', 'Non-Color'), ('ORM', 'Non-Color'), ('H', 'Non-Color'))}
    if set_b:
        tb = {k: tex(nt, set_b, k, cs) for k, cs in (('BC', 'sRGB'), ('N', 'Non-Color'), ('ORM', 'Non-Color'))}
        # height-aware hand-over so the blend edge follows the relief instead of a soft gradient
        mr = nt.nodes.new('ShaderNodeMath'); mr.operation = 'MULTIPLY_ADD'; mr.inputs[1].default_value = 2.2
        L.new(fac, mr.inputs[0])
        hs = nt.nodes.new('ShaderNodeMath'); hs.operation = 'SUBTRACT'; hs.inputs[0].default_value = -0.6; L.new(ta['H'].outputs[0], hs.inputs[1]); hs.use_clamp = False
        L.new(hs.outputs[0], mr.inputs[2]); mr.use_clamp = True
        f2 = mr.outputs[0]
        bc = mix(ta['BC'].outputs[0], tb['BC'].outputs[0], f2); nn = mix(ta['N'].outputs[0], tb['N'].outputs[0], f2); orm = mix(ta['ORM'].outputs[0], tb['ORM'].outputs[0], f2)
    else:
        bc, nn, orm = ta['BC'].outputs[0], ta['N'].outputs[0], ta['ORM'].outputs[0]
    so = nt.nodes.new('ShaderNodeSeparateColor'); L.new(orm, so.inputs[0])
    if damp_dark and blend_channel != 'R':
        bc = mix(bc, damp_tint, nt_mul(nt, damp, damp_dark), 'RGBA', 'MULTIPLY')
    if soot:
        bc = mix(bc, (0.20, 0.19, 0.18, 1), nt_mul(nt, sootv, 0.8), 'RGBA', 'MULTIPLY')
    bc = mix(bc, so.outputs[0], 0.45, 'RGBA', 'MULTIPLY')
    L.new(bc, b.inputs['Base Color'])
    r = so.outputs[1]
    if blend_channel != 'R':
        ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; L.new(damp, ad.inputs[0]); ad.inputs[1].default_value = damp_rough; L.new(r, ad.inputs[2]); r = ad.outputs[0]
    L.new(r, b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); L.new(nn, nm.inputs['Color']); L.new(nm.outputs[0], b.inputs['Normal'])
    return m


def nt_mul(nt, a, k):
    n = nt.nodes.new('ShaderNodeMath'); n.operation = 'MULTIPLY'; nt.links.new(a, n.inputs[0]); n.inputs[1].default_value = k
    return n.outputs[0]


def timber_material():
    m = bpy.data.materials.new('MI_Wall_Timber'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'Grime'
    sep = nt.nodes.new('ShaderNodeSeparateColor'); L.new(at.outputs['Color'], sep.inputs[0])
    bc = tex(nt, 'TimberBeam', 'BC', 'sRGB'); nn = tex(nt, 'TimberBeam', 'N', 'Non-Color'); orm = tex(nt, 'TimberBeam', 'ORM', 'Non-Color')
    so = nt.nodes.new('ShaderNodeSeparateColor'); L.new(orm.outputs[0], so.inputs[0])
    def mix(a, b_, f, bt='MIX'):
        n = nt.nodes.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = bt
        for sock, v in ((n.inputs[0], f), (n.inputs[6], a), (n.inputs[7], b_)):
            if hasattr(v, 'links'):
                L.new(v, sock)
            else:
                sock.default_value = v
        return n.outputs[2]
    # limewash: pale where vertex colour B says so, worn through on the grain highs (bright texels keep more wash)
    lum = nt.nodes.new('ShaderNodeRGBToBW'); L.new(bc.outputs[0], lum.inputs[0])
    k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY_ADD'; L.new(lum.outputs[0], k.inputs[0]); k.inputs[1].default_value = 2.0; k.inputs[2].default_value = 0.55; k.use_clamp = True
    f = nt.nodes.new('ShaderNodeMath'); f.operation = 'MULTIPLY'; L.new(sep.outputs[2], f.inputs[0]); L.new(k.outputs[0], f.inputs[1])
    f2 = nt_mul(nt, f.outputs[0], 0.95)
    c = mix(bc.outputs[0], (0.42, 0.41, 0.36, 1), f2)
    c = mix(c, (0.10, 0.07, 0.05, 1), nt_mul(nt, sep.outputs[0], 0.95), 'MULTIPLY')
    c = mix(c, (0.20, 0.19, 0.18, 1), nt_mul(nt, sep.outputs[1], 0.8), 'MULTIPLY')
    c = mix(c, so.outputs[0], 0.5, 'MULTIPLY')
    L.new(c, b.inputs['Base Color']); L.new(so.outputs[1], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); L.new(nn.outputs[0], nm.inputs['Color']); L.new(nm.outputs[0], b.inputs['Normal'])
    return m


def stone_windows():
    """UV rectangles of the biggest single block faces in the DungeonMasonry set (high, mortar-free areas of its height map)"""
    info = json.load(open(os.path.join(TERRAIN, 'DungeonMasonry', 'set.json')))
    img = bpy.data.images.load(os.path.join(TERRAIN, info['files']['H']), check_existing=True)
    n = img.size[0]
    px = np.empty(n * n * 4, np.float32); img.pixels.foreach_get(px)
    h = px.reshape(n, n, 4)[::4, ::4, 0]                 # row 0 = v 0
    k = h.shape[0]
    mask = (h > np.quantile(h, 0.42)).astype(np.float64)
    I = np.zeros((k + 1, k + 1)); I[1:, 1:] = mask.cumsum(0).cumsum(1)
    wins = []
    for (wu, wv) in ((0.20, 0.11), (0.17, 0.10), (0.15, 0.085), (0.12, 0.07)):
        a, b = int(wu * k), int(wv * k)
        fill = (I[b:, a:] - I[:-b, a:] - I[b:, :-a] + I[:-b, :-a]) / (a * b)
        taken = np.zeros_like(fill, bool)
        order = np.argsort(-fill, axis=None)
        for o in order[:20000]:
            y, x = divmod(int(o), fill.shape[1])
            if fill[y, x] < 0.965:
                break
            if any(abs(x - wx) < a and abs(y - wy) < b for (wx, wy, _, _) in wins):
                continue
            wins.append((x, y, a, b))
            if len(wins) >= 24:
                break
        if len(wins) >= 10:
            break
    out = [((x + 0.08 * a) / k, (y + 0.08 * b) / k, (x + 0.92 * a) / k, (y + 0.92 * b) / k) for (x, y, a, b) in wins]
    print('stone windows:', len(out), 'first', out[:1])
    return out or [(0.1, 0.1, 0.25, 0.2)]


def ivy_leaf_material():
    m = bpy.data.materials.new('MI_Wall_Ivy'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
    def t(k, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(OUT, 'Textures', 'T_Wall_Ivy_%s.png' % k)); n.image.colorspace_settings.name = cs; return n
    bc = t('BC', 'sRGB'); nn = t('N', 'Non-Color'); orm = t('ORM', 'Non-Color')
    L.new(bc.outputs[0], b.inputs['Base Color']); L.new(bc.outputs[1], b.inputs['Alpha'])
    so = nt.nodes.new('ShaderNodeSeparateColor'); L.new(orm.outputs[0], so.inputs[0]); L.new(so.outputs[1], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); L.new(nn.outputs[0], nm.inputs['Color']); L.new(nm.outputs[0], b.inputs['Normal'])
    try:
        b.inputs['Subsurface Weight'].default_value = 0.0
    except Exception:
        pass
    return m


def ivy_material():
    m = bpy.data.materials.new('MI_Wall_Ivy'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 9.0
    n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 60.0
    r = nt.nodes.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].position = 0.3; r.color_ramp.elements[0].color = (0.012, 0.035, 0.008, 1)
    r.color_ramp.elements[1].position = 0.7; r.color_ramp.elements[1].color = (0.045, 0.10, 0.018, 1)
    nt.links.new(n.outputs[0], r.inputs[0])
    nt.links.new(r.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.42
    return m


def timber_rows():
    """v ranges of single boards in the PlankFloor set, so beams map inside one board (no gaps across a beam)"""
    info = json.load(open(os.path.join(TERRAIN, 'TimberBeam', 'set.json')))
    img = bpy.data.images.load(os.path.join(TERRAIN, info['files']['H']))
    n = img.size[0]
    px = np.empty(n * n * 4, np.float32); img.pixels.foreach_get(px)
    h = px.reshape(n, n, 4)[:, :, 0].mean(1)             # row 0 = bottom = v 0
    hs = np.convolve(np.tile(h, 3), np.ones(5) / 5, 'same')[n:2 * n]
    thr = hs.mean() - 1.2 * hs.std()
    gaps = np.where(hs < thr)[0]
    groups = []
    for g in gaps:
        if groups and g - groups[-1][-1] <= 3:
            groups[-1].append(g)
        else:
            groups.append([g])
    cs = [float(np.mean(g)) for g in groups]
    rows = []
    for a, b in zip(cs[:-1], cs[1:]):
        if 70 < b - a < 420:
            rows.append((((a + b) / 2) / n, (b - a - 20) / n))
    print('timber boards found:', len(rows), 'mean width m', np.mean([w for _, w in rows]) * T_TIMBER if rows else 0)
    if len(rows) < 3:
        rows = [(0.02 + 0.04 * i, 0.03) for i in range(20)]
    return rows


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
    rows = timber_rows()
    STONE_WIN.extend(stone_windows())
    mats = {
        'plaster': blend_material('MI_Wall_Plaster', 'PlasterWall', 'PlasterWallBroken', 'B', (0.30, 0.29, 0.20, 1), 0.95),
        'timber': timber_material(),
        'masonry': blend_material('MI_Wall_DungeonMasonry', 'DungeonMasonry', 'DungeonMasonryDamp', 'R', None, 0.0),
        'ivy': ivy_leaf_material(),
    }
    mods = [(m, f, fr, note, ('plaster', 'timber')) for (m, f, fr, note) in plaster_modules(rows)]
    mods += [(m, f, fr, note, ('masonry', 'ivy' if m.name.endswith('Ivy') else None)) for (m, f, fr, note) in dungeon_modules()]
    recs = []
    x = 0.0
    for (m, fams, frames, note, slots) in mods:
        m.clamp = not m.bend_R and not any(k in m.name for k in ('Ivy', 'Breach'))
        if any(k in m.name for k in ('Curve', 'Arch', 'Ivy', 'Breach')):
            m.cls = 'kit_piece'
        st = m.build(sc.collection)
        for ob in (m.ob, m.lod1):
            ob.data.materials.append(mats[slots[0]])
            if slots[1]:
                ob.data.materials.append(mats[slots[1]])
        # export at the origin, then lay the modules out side by side in the .blend
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in [m.ob, m.lod1] + m.ucx_obs:
            o.hide_render = False
            o.select_set(True)
        bpy.context.view_layer.objects.active = m.ob
        fbx = os.path.join(OUT, m.name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                                 axis_forward='Y', axis_up='Z', bake_space_transform=False, use_triangles=True, mesh_smooth_type='EDGE',
                                 use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', object_types={'MESH', 'EMPTY'}, colors_type='LINEAR')
        for o in m.ucx_obs:
            o.hide_render = True
        m.lod1.hide_render = True; m.lod1.hide_viewport = True
        fam_kind = 'plaster' if 'Plaster' in m.name else 'dungeon'
        rec = {'name': m.name, 'class': m.cls, 'fbx': os.path.basename(fbx), 'pivot': 'grid_wall (left end x=0, thickness centred on y=0, floor z=0, runs +X, front faces -Y)',
               'module_length_m': round(m.length, 3), 'height_m': round(m.height, 3), 'thickness_m': 0.19 if fam_kind == 'plaster' else DT,
               'families': fams, 'sprite_family': '31 inside/innwalls/walls/inn-' if fam_kind == 'plaster' else '80 inside/stnwalls/stonw-', 'sprite_frames': frames,
               'dresses': note, 'materials': [mats[s].name for s in slots if s],
               'uv_channels': {'0': 'tiling, world-planar at the set tile size (2.5 m plaster and masonry, 3 m timber) with a per-module offset; timbers map inside single boards', '1': 'UVGrime: U = distance along the wall / 2.5 m, V = height / module height (0 floor, 1 top), for the WallGrime mask'},
               'vertex_colour': 'Grime (linear). Plaster and masonry verts: R damp and hand-height grime, G soot at the top, B fallen-plaster blend. Timber verts: R dark handling and sill, G soot, B limewash (pale plate, posts and rails)',
               'source_blend': 'WallKits.blend', **st}
        recs.append(rec)
        print('MODULE', m.name, st)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'WallKits.blend'), compress=True)
    json.dump(recs, open(os.path.join(OUT, 'modules.json'), 'w'), indent=1)
    print('KIT DONE', len(recs))


main()
