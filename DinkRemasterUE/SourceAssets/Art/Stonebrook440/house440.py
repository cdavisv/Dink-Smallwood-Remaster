"""SM_House_Stonebrook_TwoStorey_01: the taller two-storey fieldstone and thatch house of SCR_440.

Original reference: graphics/struct<HOME> (seq 63 frame 4), placements S440_P03/P11 with the
door S440_P04/P06 and windows S440_P08/P09.  The sprite shows two stacked storeys of coursed
fieldstone, a thick rounded thatched pent roof skirting the lower storey, a domed hipped thatch roof on
the set-back upper storey, protruding joist ends under both eaves, a planked double door and small
dark lattice windows.  Remastered at real scale, axis aligned like the SCR_439 cottage (door to the
south / Blender -Y / Unreal +Y).
"""
import bpy, bmesh, math, json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, noise
import lib440 as L

# ------------------------------------------------------------------ dimensions (metres)
W1, D1, T1 = 11.0, 8.5, .62           # lower storey outer footprint, wall thickness
H1 = 3.75                              # lower wall skin top (buried in the pent thatch)
W2, D2, CY2 = 8.8, 6.3, .30            # upper storey footprint, centre offset north
Z2A, Z2B = 3.30, 7.60                  # upper wall skin range
PENT = dict(eave=(0, 0, W1 / 2 + .75, D1 / 2 + .75, 1.25), inner=(0, CY2, W2 / 2 - .12, D2 / 2 - .12, .55), z_eave=3.15, z_inner=4.95, T=.50)
UPPER = dict(eave=(0, CY2, W2 / 2 + .80, D2 / 2 + .80, 1.45), z_eave=6.90, rise=3.60, T=.52, ridge_b=.16)
DOOR_X = -1.73                         # door centre (aligns the original warp trigger, see layout)
DOOR_W, DOOR_H, DOOR_RECESS = 1.36, 2.36, .46
RUBBLE_TILE, THATCH_TILE, OAK_TILE = 2.4, 2.0, 1.0


class HeightMap:
    def __init__(self, path, lo, hi, blur_px=0):
        img = bpy.data.images.load(str(path), check_existing=True)
        img.colorspace_settings.name = 'Non-Color'
        a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
        h = a.reshape(img.size[1], img.size[0], 4)[..., 0].astype(np.float64)   # row 0 = bottom = v 0
        if blur_px:
            n = h.shape[0]; f = np.fft.fftfreq(n) * n
            k = np.exp(-2 * (math.pi * blur_px / n) ** 2 * (f[None, :] ** 2 + f[:, None] ** 2))
            h = np.real(np.fft.ifft2(np.fft.fft2(h) * k))
        self.h = lo + h * (hi - lo); self.n = h.shape[0]
        bpy.data.images.remove(img)

    def __call__(self, u, v):
        n = self.n; x = (u % 1.0) * n; y = (v % 1.0) * n
        x0 = int(x) % n; y0 = int(y) % n; fx = x - int(x); fy = y - int(y)
        x1 = (x0 + 1) % n; y1 = (y0 + 1) % n
        h = self.h
        return (h[y0, x0] * (1 - fx) + h[y0, x1] * fx) * (1 - fy) + (h[y1, x0] * (1 - fx) + h[y1, x1] * fx) * fy


def uv_local(ob, R, origin, grain_axis, tile, offset=(0.0, 0.0), rot90=False):
    """Box-style projection in a part-local frame; V follows the grain axis where possible."""
    me = ob.data
    uvl = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    Rm = np.array(R)
    co = np.array([v.co[:] for v in me.vertices]) - np.array(origin[:])
    loc = co @ Rm
    for p in me.polygons:
        nl = np.array(p.normal[:]) @ Rm
        k = int(np.argmax(np.abs(nl)))
        axes = [i for i in range(3) if i != k]
        if grain_axis in axes:
            va = grain_axis; ua = axes[0] if axes[1] == grain_axis else axes[1]
        else:
            ua, va = axes
        if rot90:
            ua, va = va, ua
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            uvl.data[li].uv = (loc[vi, ua] / tile + offset[0], loc[vi, va] / tile + offset[1])


def uv_stone(ob, R, origin, stone):
    """Map every face of a dressed block into one large stone of the rubble texture, so quoins,
    sills and steps read as single stones instead of miniature walls."""
    me = ob.data
    uvl = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    Rm = np.array(R); co = (np.array([v.co[:] for v in me.vertices]) - np.array(origin[:])) @ Rm
    mn, mx = co.min(0), co.max(0)
    (su0, su1) = stone['u']; sv0, sv1 = .5 + stone['v'][0] / 2, .5 + stone['v'][1] / 2
    iu = (su1 - su0) * .14; iv = (sv1 - sv0) * .14
    for p in me.polygons:
        nl = np.array(p.normal[:]) @ Rm
        k = int(np.argmax(np.abs(nl))); a, b = [i for i in range(3) if i != k]
        if (mx[b] - mn[b]) > (mx[a] - mn[a]) * 1.4:
            a, b = b, a
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            fu = (co[vi, a] - mn[a]) / max(mx[a] - mn[a], 1e-6); fv = (co[vi, b] - mn[b]) / max(mx[b] - mn[b], 1e-6)
            uvl.data[li].uv = (su0 + iu + fu * (su1 - su0 - 2 * iu), sv0 + iv + fv * (sv1 - sv0 - 2 * iv))


class Wall:
    """Counter-clockwise wall frame: world = O + U*s + I*d + Z*z (I points into the house)."""
    def __init__(self, O, U, length, u_off):
        self.O = Vector(O); self.U = Vector(U).normalized(); self.Z = Vector((0, 0, 1))
        self.I = self.Z.cross(self.U); self.N = -self.I; self.length = length; self.u_off = u_off
        self.R = Matrix((self.U, self.I, self.Z)).transposed()

    def p(self, s, d, z):
        return self.O + self.U * s + self.I * d + self.Z * z


class House:
    def __init__(self, M, tex_dir, stones):
        self.M = M; self.stones = [s for s in stones if (s['u'][1] - s['u'][0]) * RUBBLE_TILE > .30]
        self.rubbleH = HeightMap(tex_dir / 'T_S440_Rubble_H.png', -.02, .06, blur_px=26)
        self.thatchH = HeightMap(tex_dir / 'T_S440_Thatch_H.png', -.04, .08, blur_px=6)
        self.rng = L.rng()

    # -------------------------------------------------------------- generic parts
    def part_box(self, center, dims, R, mat, tile=OAK_TILE, grain_axis=0, bevel=.012, stone=None, segments=2):
        ob = L.box(center, dims, mat, bevel=bevel, rot=R, attrs=False, segments=segments)
        if stone is not None:
            uv_stone(ob, R, Vector(center), stone)
        else:
            uv_local(ob, R, Vector(center), grain_axis, tile, (self.rng.uniform(0, 1), self.rng.uniform(0, 1)))
        return ob

    def stone(self, long=False):
        pool = [s for s in self.stones if ((s['u'][1] - s['u'][0]) * RUBBLE_TILE > .42) == long] or self.stones
        return pool[int(self.rng.integers(0, len(pool)))]

    # -------------------------------------------------------------- rubble wall skins
    def skin(self, w, z0, z1, openings, spacing=.10, v0=0.0, record=None, drop=.9):
        su = sorted(set([0.0, w.length] + [o[k] for o in openings for k in (0, 1)] +
                        list(np.arange(spacing, w.length, spacing))))
        sz = sorted(set([z0, z1] + [o[k] for o in openings for k in (2, 3)] + list(np.arange(z0 + spacing, z1, spacing))))
        su = [s for i, s in enumerate(su) if i == 0 or s - su[i - 1] > .012]
        sz = [z for i, z in enumerate(sz) if i == 0 or z - sz[i - 1] > .012]
        bm = bmesh.new(); uvk = bm.loops.layers.uv.new('UVMap'); grid = {}; uvs = {}
        for i, s in enumerate(su):
            for j, z in enumerate(sz):
                u = (w.u_off + s) / RUBBLE_TILE; v = v0 + (z - z0) / (2 * RUBBLE_TILE)
                d = self.rubbleH(u, 2 * v)
                # near the rounded thatch corners the roof sits lower: pull the buried wall top down
                zc = z1 - drop * max(0.0, 1 - min(s, w.length - s) / 1.3)
                z = min(z, zc)
                p = w.p(s, 0, z)
                bulge = .012 * noise.noise(Vector((p.x * .7, p.y * .7, z * .9)))
                on_open = any(o[0] - 1e-6 <= s <= o[1] + 1e-6 and o[2] - 1e-6 <= z <= o[3] + 1e-6 for o in openings)
                disp = (d + bulge) * (.35 if on_open else 1.0)
                if z <= z0 + 1e-6:
                    disp = min(disp, .015) + .01
                grid[i, j] = bm.verts.new(p + w.N * disp); uvs[i, j] = (u, v)
                if record is not None:
                    record.append((s, z, disp))
        for i in range(len(su) - 1):
            for j in range(len(sz) - 1):
                cs, cz = (su[i] + su[i + 1]) / 2, (sz[j] + sz[j + 1]) / 2
                if any(o[0] < cs < o[1] and o[2] < cz < o[3] for o in openings):
                    continue
                f = bm.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
                for loop, key in zip(f.loops, [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]):
                    loop[uvk].uv = uvs[key]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # outward facing check
        f0 = bm.faces[0]
        if f0.normal.dot(w.N) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        return L.obj_from_bm(bm, 'WallSkin', self.M['rubble'])

    def quoins(self, cx, cy, sx, sy, z0, z1):
        z = z0; k = 0
        while z < z1 - .05:
            h = min(float(self.rng.uniform(.27, .36)), z1 - z)
            la, lb = (.58, .34) if k % 2 == 0 else (.34, .58)
            la += self.rng.uniform(-.06, .06); lb += self.rng.uniform(-.06, .06)
            pr = .065 + self.rng.uniform(0, .02)
            x0, x1 = sorted((cx + sx * pr, cx - sx * la)); y0, y1 = sorted((cy + sy * pr, cy - sy * lb))
            ctr = Vector(((x0 + x1) / 2, (y0 + y1) / 2, z + h / 2))
            dims = (x1 - x0, y1 - y0, h - .012)
            R = Matrix.Rotation(self.rng.uniform(-.012, .012), 3, 'Z')
            self.part_box(ctr, dims, R, self.M['rubble'], bevel=.022, stone=self.stone(True), segments=2)
            z += h; k += 1

    # -------------------------------------------------------------- openings
    def window(self, w, s0, s1, z0, z1, depth=.30):
        M = self.M; cs = (s0 + s1) / 2; ww = s1 - s0; hh = z1 - z0
        R = w.R
        # limewashed reveals (sides, soffit, sill board)
        for s in (s0 + .02, s1 - .02):
            self.part_box(w.p(s, depth / 2 - .01, (z0 + z1) / 2), (.04, depth + .02, hh), R, M['limewash'], tile=1.0, bevel=.004)
        self.part_box(w.p(cs, depth / 2 - .01, z1 - .02), (ww, depth + .02, .04), R, M['limewash'], tile=1.0, bevel=.004)
        self.part_box(w.p(cs, depth / 2 - .01, z0 + .02), (ww, depth + .02, .04), R, M['limewash'], tile=1.0, bevel=.004)
        # oak casement frame and glazing
        fd = depth - .04
        for s in (s0 + .06, s1 - .06):
            self.part_box(w.p(s, fd, (z0 + z1) / 2), (.08, .08, hh - .04), R, M['oak'], grain_axis=2, bevel=.008)
        for z in (z0 + .06, z1 - .06):
            self.part_box(w.p(cs, fd, z), (ww - .04, .08, .08), R, M['oak'], grain_axis=0, bevel=.008)
        if ww > .8:
            self.part_box(w.p(cs, fd - .005, (z0 + z1) / 2), (.07, .07, hh - .08), R, M['oak'], grain_axis=2, bevel=.008)
        g = self.part_box(w.p(cs, fd + .015, (z0 + z1) / 2), (ww - .1, .012, hh - .1), R, M['glass'], bevel=0)
        uv_local(g, R, w.p(s0, 0, z0), 2, .48, (0, 0))
        # projecting stone sill and an oak lintel bedded into the rubble
        self.part_box(w.p(cs, -.02, z0 - .05), (ww + .22, .16, .10), R, M['rubble'], bevel=.018, stone=self.stone(True))
        self.part_box(w.p(cs, .06, z1 + .12), (ww + .46, .28, .22), R, M['oak'], grain_axis=0, bevel=.02)

    def door(self, w, cs):
        M = self.M; R = w.R; s0, s1 = cs - DOOR_W / 2, cs + DOOR_W / 2; dep = DOOR_RECESS
        for s in (s0 + .02, s1 - .02):
            self.part_box(w.p(s, dep / 2, DOOR_H / 2), (.04, dep, DOOR_H), R, M['limewash'], tile=1.0, bevel=.004)
        self.part_box(w.p(cs, dep / 2, DOOR_H - .02), (DOOR_W, dep, .04), R, M['limewash'], tile=1.0, bevel=.004)
        # threshold and outside step stones
        self.part_box(w.p(cs, dep / 2 - .02, .04), (DOOR_W + .04, dep + .04, .08), R, M['rubble'], bevel=.015, stone=self.stone(True))
        self.part_box(w.p(cs, -.30, .07), (DOOR_W + .45, .58, .14), R, M['rubble'], bevel=.03, stone=self.stone(True))
        # oak door frame
        fd = dep - .06
        for s in (s0 + .07, s1 - .07):
            self.part_box(w.p(s, fd, (DOOR_H + .08) / 2), (.13, .13, DOOR_H - .08), R, M['oak'], grain_axis=2, bevel=.01)
        self.part_box(w.p(cs, fd, DOOR_H - .07), (DOOR_W - .02, .13, .13), R, M['oak'], grain_axis=0, bevel=.01)
        # ledged double door, 3 planks a leaf, fitted inside the frame
        leaf_w = (DOOR_W - .28) / 2; pd = dep - .03
        for side in (-1, 1):
            base = cs + side * (leaf_w / 2 + .004)
            for k in range(3):
                pw = leaf_w / 3
                ps = base - leaf_w / 2 + pw * (k + .5)
                hgt = DOOR_H - .17 - self.rng.uniform(0, .015)
                self.part_box(w.p(ps, pd + self.rng.uniform(-.004, .004), .085 + hgt / 2), (pw - .006, .045, hgt), R, M['oak'], grain_axis=2, bevel=.006)
            for z in (.45, 1.95):
                L_s = leaf_w * .85
                outer = base + side * leaf_w / 2
                self.part_box(w.p(outer - side * L_s / 2, pd - .028, z), (L_s, .008, .045), R, M['iron'], bevel=.003)
                for bs in (outer - side * .05, outer - side * L_s * .5, outer - side * (L_s - .03)):
                    L.lathe([(0, -.006), (.011, -.006), (.011, .004), (.006, .008), (0, .009)], M['iron'], sides=10,
                            center=w.p(bs, pd - .032, z), axis_m=Matrix((w.U, w.Z, w.N)).transposed())
            # ring pull
            bpy.ops.mesh.primitive_torus_add(major_radius=.05, minor_radius=.007, major_segments=20, minor_segments=8)
            tor = bpy.context.object
            tor.matrix_world = Matrix.Translation(w.p(cs + side * .09, pd - .035, 1.05)) @ Matrix((w.U, w.Z, w.N)).transposed().to_4x4()
            for c in list(tor.users_collection):
                c.objects.unlink(tor)
            L.STATE['coll'].objects.link(tor); bpy.context.view_layer.objects.active = tor
            bpy.ops.object.select_all(action='DESELECT'); tor.select_set(True)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            tor.data.materials.append(M['iron']); L.STATE['pieces'].append(tor)
        # heavy oak lintel bearing on the rubble
        self.part_box(w.p(cs, .05, DOOR_H + .17), (DOOR_W + .80, .30, .30), R, M['oak'], grain_axis=0, bevel=.025)

    def joists(self, w, z, out, spacing, skip=()):
        n = int(w.length / spacing)
        for k in range(n):
            s = (k + .5) * w.length / n
            if any(a < s < b for a, b in skip) or s < 1.25 or s > w.length - 1.25:
                continue   # rounded thatch corners sit inside the wall line there
            c = w.p(s, -out / 2 + .12, z)
            self.part_box(c, (.19, out + .24, .21), w.R @ Matrix.Rotation(self.rng.uniform(-.02, .02), 3, 'Z'),
                          self.M['oak'], grain_axis=1, bevel=.018)

    # -------------------------------------------------------------- thatch shells
    @staticmethod
    def ring(cx, cy, a, b, r, counts):
        """Rounded rectangle, CCW from the front middle.  Returns points (x,y) and outward normals."""
        r = max(min(r, a - 1e-4, b - 1e-4), 0.0) if a > 1e-4 and b > 1e-4 else 0.0
        nf, ns, nc = counts
        pts = []; nrm = []
        def seg(p0, p1, n, nv, include_end=False):
            for i in range(n + (1 if include_end else 0)):
                t = i / n
                pts.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)); nrm.append(nv)
        def arc(c, a0, n):
            for i in range(n):
                ang = a0 + (math.pi / 2) * i / n
                pts.append((c[0] + r * math.cos(ang), c[1] + r * math.sin(ang))); nrm.append((math.cos(ang), math.sin(ang)))
        ax, by = a - r, b - r
        seg((cx, cy - b), (cx + ax, cy - b), nf, (0, -1))
        arc((cx + ax, cy - by), -math.pi / 2, nc)
        seg((cx + a, cy - by), (cx + a, cy + by), ns, (1, 0))
        arc((cx + ax, cy + by), 0, nc)
        seg((cx + ax, cy + b), (cx - ax, cy + b), 2 * nf, (0, 1))
        arc((cx - ax, cy + by), math.pi / 2, nc)
        seg((cx - a, cy + by), (cx - a, cy - by), ns, (-1, 0))
        arc((cx - ax, cy - by), math.pi, nc)
        seg((cx - ax, cy - b), (cx, cy - b), nf, (0, -1))
        return pts, nrm

    def shell(self, rings, counts, name, uref=None):
        """rings: list of dict(shape=(cx,cy,a,b,r), z, o (outward), disp (bool), vlen).  Consecutive
        rings are bridged; the list is treated as an open strip (closures handled by degenerate rings)."""
        bm = bmesh.new(); uvk = bm.loops.layers.uv.new('UVMap')
        verts = []; vrow = []; vcum = 0.0; prev_mid = None; ring_n = None
        rp, _ = self.ring(*uref, counts)
        uacc = [0.0]
        for i in range(1, len(rp)):
            uacc.append(uacc[-1] + math.hypot(rp[i][0] - rp[i - 1][0], rp[i][1] - rp[i - 1][1]))
        utot = uacc[-1] + math.hypot(rp[0][0] - rp[-1][0], rp[0][1] - rp[-1][1])
        for k, rg in enumerate(rings):
            cx, cy, a, b, r = rg['shape']; o = rg.get('o', 0.0)
            pts, nrm = self.ring(cx, cy, a + o, b + o, r + o if r > 0 else 0.0, counts)
            ring_n = nrm
            mid = Vector((pts[0][0], pts[0][1], rg['z']))
            if prev_mid is not None:
                vcum += (mid - prev_mid).length
            prev_mid = mid
            v_m = rg.get('v', vcum)
            row = []
            for i, ((x, y), (nx, ny)) in enumerate(zip(pts, nrm)):
                p = Vector((x, y, rg['z']))
                if rg.get('disp'):
                    # planar strand coordinate: x on the north/south slopes, y on the hips/gables
                    u = uacc[i] / THATCH_TILE; v = v_m / THATCH_TILE
                    d = self.thatchH(u, v) * rg.get('disp_scale', 1.0)
                    lump = .045 * noise.noise(Vector((x * .55, y * .55, rg['z'] * .55))) + .015 * noise.noise(Vector((x * 2.1, y * 2.1, rg['z'] * 2.1)))
                    d += lump + rg.get('extra', lambda xx, yy, uu: 0.0)(x, y, u * THATCH_TILE)
                    n3 = Vector((nx * rg.get('nh', .75), ny * rg.get('nh', .75), rg.get('nz', .66))).normalized()
                    p += n3 * d
                row.append(bm.verts.new(p))
            verts.append(row); vrow.append(v_m)
        m = len(verts[0])
        for k in range(len(verts) - 1):
            A, B = verts[k], verts[k + 1]; va, vb = vrow[k], vrow[k + 1]
            for i in range(m):
                j = (i + 1) % m
                quad = (A[i], A[j], B[j], B[i])
                if len(set(quad)) < 3:
                    continue
                try:
                    f = bm.faces.new(quad)
                except ValueError:
                    continue
                ui, uj = uacc[i], (uacc[j] if j else utot)
                for loop, uu, vv in zip(f.loops, (ui, uj, uj, ui), (va, va, vb, vb)):
                    loop[uvk].uv = (uu / THATCH_TILE, vv / THATCH_TILE)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=2e-4)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ob = L.obj_from_bm(bm, name, self.M['thatch'])
        return ob

    def pent_roof(self):
        P = PENT; T = P['T']
        (ex, ey, ea, eb, er), (ix, iy, ia, ib, ir) = P['eave'], P['inner']
        def shape(t):
            return (ex + (ix - ex) * t, ey + (iy - ey) * t, ea + (ia - ea) * t, eb + (ib - eb) * t, er + (ir - er) * t)
        def zf(t):
            return P['z_eave'] + (P['z_inner'] - P['z_eave']) * (1 - (1 - t) ** 1.15)
        rings = []
        ts = np.linspace(0, 1, 8)
        for t in ts[::-1]:                             # underside, from the upper wall out to the eave
            rings.append(dict(shape=shape(t), z=zf(t) - T * (.9 if t > .5 else 1.0), v=-1.0 - (1 - t) * 1.8))
        for ang in np.linspace(-math.pi / 2, math.pi / 2, 7)[1:-1]:     # rolled eave lip
            rings.append(dict(shape=shape(0), z=P['z_eave'] - T / 2 + math.sin(ang) * T / 2, o=math.cos(ang) * T * .72,
                              disp=True, nh=1.0, nz=.05, v=-(1 - math.sin(ang)) * T * .8, disp_scale=.6))
        nslope = 40
        for t in np.linspace(0, 1, nslope):
            rings.append(dict(shape=shape(t), z=zf(t), disp=t < .985, disp_scale=1 - .6 * t ** 4))
        # v for outer rings is the cumulative slope distance from the eave line (course alignment)
        vc = 0.0; prev = None
        for rg in rings:
            if 'v' in rg:
                continue
            cx, cy, a, b, r = rg['shape']; p = Vector((cx, cy - b, rg['z']))
            vc += (p - prev).length if prev is not None else 0.0; prev = p; rg['v'] = vc
        rings.append(dict(rings[0]))                   # close the annulus inside the upper wall
        return self.shell(rings, (24, 40, 12), 'PentThatch', uref=shape(0))

    def upper_roof(self):
        P = UPPER; T = P['T']; cx, cy, A, B, R = P['eave']; rb = P['ridge_b']
        def shape(t):
            inset = (B - rb) * t
            return (cx, cy, A - inset, B - inset, max(R - inset * .55, rb * .98))
        def zf(t):
            return P['z_eave'] + P['rise'] * (1 - (1 - t) ** 1.28)
        rings = [dict(shape=(cx, cy, max(A - B, .1), 0.0, 0.0), z=zf(.45) - T, v=-3.0)]
        for t in np.linspace(.45, 0, 6):
            rings.append(dict(shape=shape(t), z=zf(t) - T, v=-1.0 - t * 2))
        for ang in np.linspace(-math.pi / 2, math.pi / 2, 7)[1:-1]:
            rings.append(dict(shape=shape(0), z=P['z_eave'] - T / 2 + math.sin(ang) * T / 2, o=math.cos(ang) * T * .72,
                              disp=True, nh=1.0, nz=.05, v=-(1 - math.sin(ang)) * T * .8, disp_scale=.6))
        def ridge_band(x, y, acc):
            return 0.0
        nslope = 78
        for t in np.linspace(0, 1, nslope):
            # block-cut ridge: a thicker top band with a scalloped lower edge
            def band(x, y, acc, t=t):
                edge = .80 + .035 * abs(math.sin(acc / .45 * math.pi))
                return .075 * (1 / (1 + math.exp(-(t - edge) * 90)))
            rings.append(dict(shape=shape(t), z=zf(t) + (.0 if t < 1 else .06), disp=True, extra=band,
                              disp_scale=1 - .4 * t ** 3))
        rings.append(dict(shape=(cx, cy, max(A - B + rb * .2, .05), 0.0, 0.0), z=zf(1) + .13))
        vc = 0.0; prev = None
        for rg in rings:
            if 'v' in rg:
                continue
            c0, c1, a, b, r = rg['shape']; p = Vector((c0, c1 - b, rg['z']))
            vc += (p - prev).length if prev is not None else 0.0; prev = p; rg['v'] = vc
        ob = self.shell(rings, (20, 28, 14), 'UpperThatch', uref=shape(0))
        # hazel liggers pinning the ridge band
        for t in (.86, .93):
            c0, c1, a, b, r = shape(t)
            pts, nrm = self.ring(c0, c1, a + .07, b + .07, r + .07, (8, 6, 6))
            path = [(x, y, zf(t) + .12) for x, y in pts] + [(pts[0][0], pts[0][1], zf(t) + .12)]
            L.tube(path, .017, self.M['oak'], sides=6, grain=False)
            tb = L.STATE['pieces'][-1]
            uv_local(tb, Matrix.Identity(3), Vector((0, 0, 0)), 0, OAK_TILE)
        return ob

    def chimney(self):
        M = self.M; x, y = 2.35, CY2 + D2 / 2 - .40; z0, z1 = 6.2, 11.15
        R = Matrix.Identity(3)
        ob = L.box((x, y, (z0 + z1) / 2), (1.02, .78, z1 - z0), M['rubble'], bevel=.03, attrs=False)
        uv_local(ob, R, Vector((x, y, 8.0)), 2, 2 * RUBBLE_TILE, (.37, .15), rot90=False)
        for d in ob.data.uv_layers['UVMap'].data:
            d.uv.x = .37 + (d.uv.x - .37) * 2   # keep 2.4 m horizontal tiling on the 2.4 x 4.8 m texture
        self.part_box(Vector((x, y, z1 + .07)), (1.18, .94, .14), R, M['rubble'], bevel=.02, stone=self.stone(True))
        self.part_box(Vector((x, y, z1 + .30)), (.62, .46, .32), R, M['rubble'], bevel=.02, stone=self.stone(True))
        for qx in (-1, 1):   # simple quoins on the visible chimney corners
            for k in range(14):
                z = z0 + 1.7 + k * .23
                if z > z1 - .2:
                    break
                la = .34 if k % 2 else .22
                self.part_box(Vector((x + qx * (.51 - la / 2 + .02), y - .39 - .01, z + .1)), (la, .06, .2), R, M['rubble'], bevel=.012, stone=self.stone(False))

    # -------------------------------------------------------------- assembly
    def build(self):
        M = self.M
        lower = [Wall((-W1 / 2, -D1 / 2, 0), (1, 0, 0), W1, 0.0), Wall((W1 / 2, -D1 / 2, 0), (0, 1, 0), D1, W1),
                 Wall((W1 / 2, D1 / 2, 0), (-1, 0, 0), W1, W1 + D1), Wall((-W1 / 2, D1 / 2, 0), (0, -1, 0), D1, 2 * W1 + D1)]
        y2a, y2b = CY2 - D2 / 2, CY2 + D2 / 2
        upper = [Wall((-W2 / 2, y2a, 0), (1, 0, 0), W2, .31), Wall((W2 / 2, y2a, 0), (0, 1, 0), D2, W2 + .31),
                 Wall((W2 / 2, y2b, 0), (-1, 0, 0), W2, W2 + D2 + .31), Wall((-W2 / 2, y2b, 0), (0, -1, 0), D2, 2 * W2 + D2 + .31)]
        ds = DOOR_X + W1 / 2
        openings = {
            0: [('door', ds - DOOR_W / 2, ds + DOOR_W / 2, 0.0, DOOR_H), ('win', 7.45, 8.35, 1.05, 2.05)],
            1: [('win', 4.30, 5.20, 1.05, 2.05)],
            2: [('win', 7.55, 8.35, 1.15, 2.00)],
            3: [('win', 6.85, 7.65, 1.15, 1.95)],
        }
        uopen = {0: [('win', 1.85, 2.65, 5.30, 6.20), ('win', 6.15, 6.95, 5.30, 6.20)], 1: [('win', 2.75, 3.55, 5.30, 6.20)],
                 2: [('win', 4.05, 4.75, 5.35, 6.15)], 3: [('win', 2.75, 3.55, 5.30, 6.20)]}
        for k, w in enumerate(lower):
            ops = openings.get(k, [])
            rec = [] if k == 1 else None
            self.skin(w, 0.0, H1, [o[1:] for o in ops], v0=0.0, record=rec)
            if rec is not None:
                self.east_relief = rec
            for kind, s0, s1, z0, z1 in ops:
                if kind == 'door':
                    self.door(w, (s0 + s1) / 2)
                else:
                    self.window(w, s0, s1, z0, z1)
            skip = [(o[1] - .25, o[2] + .25) for o in ops if o[0] == 'door']
            self.joists(w, 2.99, .26, 1.15, skip)
        for k, w in enumerate(upper):
            ops = uopen.get(k, [])
            self.skin(w, Z2A, Z2B, [o[1:] for o in ops], v0=.15)
            for kind, s0, s1, z0, z1 in ops:
                self.window(w, s0, s1, z0, z1, depth=.26)
            self.joists(w, 6.79, .30, 1.1)
        # inner cores close the solids behind the skins (never seen except through openings)
        L.box((0, 0, H1 / 2), (W1 - 2 * T1, D1 - 2 * T1, H1), M['rubble'], bevel=0, attrs=False)
        L.box((0, CY2, (Z2A + Z2B) / 2), (W2 - 1.0, D2 - 1.0, Z2B - Z2A), M['rubble'], bevel=0, attrs=False)
        for ob in L.STATE['pieces'][-2:]:
            uv_local(ob, Matrix.Identity(3), Vector((0, 0, 0)), 2, RUBBLE_TILE)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.quoins(sx * W1 / 2, sy * D1 / 2, sx, sy, 0.0, 2.95)   # stop under the rounded pent corner
                self.quoins(sx * W2 / 2, CY2 + sy * D2 / 2, sx, sy, 4.7, 6.5)
        self.pent_roof()
        self.upper_roof()
        self.chimney()
        rel = np.array(self.east_relief)          # s along +Y from y=-D1/2, z, outward displacement
        cell = .25; ny = int(D1 / cell) + 1; nz = int(H1 / cell) + 1
        grid = np.zeros((ny, nz))
        for s_, z_, d_ in rel:
            iy, iz = min(int(s_ / cell), ny - 1), min(int(z_ / cell), nz - 1)
            grid[iy, iz] = max(grid[iy, iz], d_)
        relief = dict(x_face=W1 / 2, y0=-D1 / 2, cell=cell, max_outward_m=grid.round(4).tolist())
        return dict(east_wall_relief=relief, door_local_m=[DOOR_X, -D1 / 2, 0.0], door_recess_m=DOOR_RECESS,
                    footprint_m=[W1, D1], upper_footprint_m=[W2, D2], upper_center_y_m=CY2)

    def collision(self, coll, base):
        hulls = []
        dx0, dx1 = DOOR_X - DOOR_W / 2, DOOR_X + DOOR_W / 2
        y_back_of_recess = -D1 / 2 + DOOR_RECESS
        hulls.append(((0, (y_back_of_recess + D1 / 2) / 2, 3.6), (W1 + .1, D1 / 2 - y_back_of_recess + .05, 7.2)))
        fy = (-D1 / 2 - .05 + y_back_of_recess) / 2; fd = y_back_of_recess - (-D1 / 2 - .05)
        hulls.append((((-W1 / 2 - .05 + dx0) / 2, fy, 3.6), (dx0 - (-W1 / 2 - .05), fd, 7.2)))
        hulls.append((((W1 / 2 + .05 + dx1) / 2, fy, 3.6), (W1 / 2 + .05 - dx1, fd, 7.2)))
        hulls.append(((0, CY2, 8.6), (W2 + .1, D2 + .1, 2.8)))
        hulls.append(((2.35, CY2 + D2 / 2 - .40, 9.6), (1.05, .8, 3.2)))
        for i, (c, d) in enumerate(hulls, 1):
            L.collision_box(coll, base, i, c, d)
        return hulls
