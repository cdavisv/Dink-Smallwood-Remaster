"""Round-2 unique bakes for props: a small mesh builder (the same generator makes the high-detail source and the game mesh),
a shader-node helper for procedural high-detail materials (curvature edge wear, AO dirt, rust, soot), the Cycles
high -> game-mesh bake (BC / N OpenGL / ORM, optional E emissive) and the review renders.
Used by props_bake.py (exec'd, runs inside Blender 5.2 batch mode)."""
import bpy, bmesh, math, os, json, sys
import numpy as np
from mathutils import Vector, Matrix

PP = os.environ.get('DINK_PP') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TP = os.path.join(PP, 'ThirdParty')


def use_hip_gpu(scene=None):
    """Render/bake on the RX 6800 via HIP (CYCLES_GPU.md); preferences change in memory only. DINK_CPU=1 forces the CPU"""
    scene = scene or bpy.context.scene; scene.render.engine = 'CYCLES'; found = False
    if not os.environ.get('DINK_CPU'):
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'HIP'; prefs.refresh_devices()
            for d in prefs.devices:
                d.use = (d.type == 'HIP' and 'Radeon RX 6800' in d.name); found |= d.use
        except Exception as e:
            print('HIP not available:', e); found = False
    scene.cycles.device = 'GPU' if found else 'CPU'
    print('Cycles device:', scene.cycles.device); return found


# ---------------------------------------------------------------- noise
def _hash(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 974711) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(P, seed=0, freq=1.0):
    """value noise -1..1 at points P (n, 3)"""
    P = np.asarray(P, float) * freq; i = np.floor(P).astype(np.int64); f = P - i; f = f * f * (3 - 2 * f)
    out = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out * 2 - 1


def fbm(P, seed=0, freq=1.0, oct=4):
    a = 0.5; s = np.zeros(len(P))
    for o in range(oct):
        s += a * vnoise(P, seed + o * 17, freq * 2 ** o); a *= 0.5
    return s


# ---------------------------------------------------------------- mesh builder
class MB:
    """accumulates primitives; every primitive writes its own UV chart in metres (v along the grain / length), with duplicated
    vertices on chart seams, so the same call list gives the high source (dense, hi=True) and the game mesh"""

    def __init__(s, seed=0, hi=False, mi=None):
        s.V = []; s.UV = []; s.F = []; s.M = []; s.G = []; s.grp = 0; s.uvoff = True; s.hi = hi; s.rng = np.random.default_rng(seed); s.mi = mi or {}
        s.ru = np.random.default_rng(seed + 7); s.rx = np.random.default_rng(seed + 13)      # rng: shared shape decisions (same draws on hi and lo); ru: UV offsets; rx: hi-only extras

    def d(s, lo, hi):
        """detail switch: lo on the game mesh, hi on the source"""
        return hi if s.hi else lo

    def add(s, V, F, mat=0, uv=None):
        n = len(s.V); o = s.ru.uniform(0, 3.0, 2) * (1.0 if s.uvoff else 0.0); mat = s.mi[mat] if isinstance(mat, str) else mat
        s.V += [tuple(float(c) for c in v) for v in V]; s.G += [s.grp] * len(V)
        s.UV += [(float(u[0] + o[0]), float(u[1] + o[1])) for u in uv] if uv is not None else [(0.0, 0.0)] * len(V)
        s.F += [tuple(n + i for i in f) for f in F]; s.M += [mat] * len(F)
        return n

    def xform_since(s, n0, M):
        M = np.array(M); P = np.array(s.V[n0:]); P = P @ M[:3, :3].T + M[:3, 3]; s.V[n0:] = [tuple(p) for p in P]

    def deform_since(s, n0, fn):
        P = fn(np.array(s.V[n0:])); s.V[n0:] = [tuple(p) for p in P]

    def pose(s, mats):
        """move the vertices of each group by its matrix: {group: 4x4}"""
        P = np.array(s.V); G = np.array(s.G)
        for g, M in (mats or {}).items():
            M = np.array(M); k = G == g; P[k] = P[k] @ M[:3, :3].T + M[:3, 3]
        s.V = [tuple(p) for p in P]

    # -- primitives
    def box(s, lo, hi, mat=0, grain=2, M=None, jit=0.0, taper=None, seg=1):
        """box with a chart per face; grain = axis the UV v runs along. seg > 1 cuts it along the grain (for warps)"""
        lo = np.array(lo, float); hi = np.array(hi, float); n0 = len(s.V)
        ax = [0, 1, 2]; g = grain; a, b = [i for i in ax if i != g]
        ts = np.linspace(0, 1, seg + 1); rings = []
        je = s.rng.uniform(-jit, jit, (2, 4, 3)) if jit else np.zeros((2, 4, 3))
        j8 = np.array([je[0] * (1 - t) + je[1] * t for t in ts])
        for k, t in enumerate(ts):
            r = []
            for q, (ua, ub) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
                p = np.zeros(3); p[g] = lo[g] + (hi[g] - lo[g]) * t; p[a] = hi[a] if ua else lo[a]; p[b] = hi[b] if ub else lo[b]
                if taper is not None:
                    c_ = (lo + hi) / 2; f = 1 + (taper - 1) * t; p[a] = c_[a] + (p[a] - c_[a]) * f; p[b] = c_[b] + (p[b] - c_[b]) * f
                r.append(p + j8[k, q])
            rings.append(r)
        da = hi[a] - lo[a]; db = hi[b] - lo[b]; L = hi[g] - lo[g]
        flip = (g == 1)                                   # keep outward winding for every grain axis
        for q in range(4):                                # four long faces
            q1 = (q + 1) % 4; w = da if q % 2 == 0 else db
            V = []; U = []
            for k, t in enumerate(ts):
                V += [rings[k][q], rings[k][q1]]; U += [(0, t * L), (w, t * L)]
            F = [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(seg)]
            if flip:
                F = [f[::-1] for f in F]
            s.add(V, F, mat, U)
        e0 = [rings[0][3], rings[0][2], rings[0][1], rings[0][0]]; e1 = [rings[-1][0], rings[-1][1], rings[-1][2], rings[-1][3]]
        for E in (e0, e1):
            F = [(0, 1, 2, 3)]
            if flip:
                F = [f[::-1] for f in F]
            s.add(E, F, mat, [(0, 0), (da, 0), (da, db), (0, db)])
        if M is not None:
            s.xform_since(n0, M)
        return n0

    def tube(s, pts, rad, sides=8, mat=0, caps=True, shape=None, twist=0.0, closed=False, up=None, vscale=1.0, rect=None, ups=None):
        """swept tube along pts; rad scalar or per point; shape = per-side radius factors; closed = a ring"""
        P = np.array(pts, float); n = len(P)
        R = np.full(n, rad, float) if np.isscalar(rad) else np.array(rad, float)
        if closed:
            T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
        else:
            T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1)[:, None] + 1e-12
        u0 = np.array(up if up is not None else ([0, 0, 1] if abs(T[0][2]) < 0.9 else [1, 0, 0]), float)
        N = u0 - T[0] * (u0 @ T[0]); N /= np.linalg.norm(N)
        V = []; U = []; arc = 0.0; rm = float(R.mean()) * (float(np.mean(shape)) if shape is not None else 1.0)
        nn = n + 1 if closed else n
        if rect is not None:
            sides = 4; w_, t_ = rect[0] / 2, rect[1] / 2; RC = [(w_, -t_), (w_, t_), (-w_, t_), (-w_, -t_)]; RU = [0, rect[1], rect[0] + rect[1], rect[0] + 2 * rect[1], 2 * (rect[0] + rect[1])]
        for i_ in range(nn):
            i = i_ % n
            if i_ > 0:
                arc += np.linalg.norm(P[i] - P[(i_ - 1) % n])
                N = N - T[i] * (N @ T[i]); N /= np.linalg.norm(N) + 1e-12
            if ups is not None:                       # fixed reference direction per point instead of parallel transport
                N = np.array(ups[i], float); N = N - T[i] * (N @ T[i]); N /= np.linalg.norm(N) + 1e-12
            B = np.cross(T[i], N)
            for k in range(sides + 1):
                if rect is not None:                  # rectangular bar: rect = (size along the up vector, size across), scaled by rad
                    cx, cy = RC[k % 4]; ct, st = math.cos(twist * arc), math.sin(twist * arc)
                    V.append(P[i] + R[i] * ((cx * ct - cy * st) * N + (cx * st + cy * ct) * B)); U.append((RU[k], arc * vscale)); continue
                a = 2 * math.pi * k / sides + twist * arc
                q = R[i] * (shape[k % sides] if shape is not None else 1.0)
                V.append(P[i] + q * (math.cos(a) * N + math.sin(a) * B)); U.append((2 * math.pi * rm * k / sides, arc * vscale))
        F = []
        for i in range(nn - 1):
            for k in range(sides):
                a = i * (sides + 1) + k; F.append((a, a + 1, a + sides + 2, a + sides + 1))
        n0 = s.add(V, F, mat, U)
        if caps and not closed:
            for (i, rev) in ((0, True), (n - 1, False)):
                ring = [V[i * (sides + 1) + k] for k in range(sides)]
                uv = [(R[i] * math.cos(2 * math.pi * k / sides), R[i] * math.sin(2 * math.pi * k / sides)) for k in range(sides)] if rect is None else [(R[i] * c_[0], R[i] * c_[1]) for c_ in RC]
                s.add(ring, [tuple(range(sides))[::-1] if rev else tuple(range(sides))], mat, uv)
        return n0

    def lathe(s, prof, n=24, mat=0, c=(0, 0, 0), deform=None, sub=1, cap=True, planar=False):
        """surface of revolution about +Z through c; prof = [(r, z)], going up the outside (outward faces); open ends are capped"""
        pr = [np.array(p, float) for p in prof]
        if cap and pr[0][0] > 1e-6:
            pr = [np.array([0.0, pr[0][1]])] + pr
        if cap and pr[-1][0] > 1e-6:
            pr = pr + [np.array([0.0, pr[-1][1]])]
        if sub > 1:
            q = []
            for a, b in zip(pr[:-1], pr[1:]):
                q += [a + (b - a) * t for t in np.linspace(0, 1, sub + 1)[:-1]]
            pr = q + [pr[-1]]
        rmax = max(p[0] for p in pr); V = []; U = []; arc = 0.0
        for i, p in enumerate(pr):
            if i:
                arc += np.linalg.norm(p - pr[i - 1])
            for k in range(n + 1):
                a = 2 * math.pi * k / n
                V.append((c[0] + p[0] * math.cos(a), c[1] + p[0] * math.sin(a), c[2] + p[1])); U.append((a * rmax, arc) if not planar else (p[0] * math.cos(a), p[0] * math.sin(a) + 0.35 * p[1]))
        F = []
        for i in range(len(pr) - 1):
            for k in range(n):
                a = i * (n + 1) + k
                if pr[i][0] < 1e-6:
                    F.append((a, a + n + 2, a + n + 1))
                elif pr[i + 1][0] < 1e-6:
                    F.append((a, a + 1, a + n + 1))
                else:
                    F.append((a, a + 1, a + n + 2, a + n + 1))
        n0 = s.add(V, F, mat, U)
        if deform is not None:
            s.deform_since(n0, deform)
        return n0

    def blob(s, c, radii, sub=2, mat=0, lump=0.2, freq=None, seed=None, M=None, flat=0.0):
        """lumpy stone / coal / dollop: displaced icosphere, UV by latitude-longitude"""
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        P = np.array([v.co[:] for v in bm.verts]); F = [[v.index for v in f.verts] for f in bm.faces]; bm.free()
        sd = int(s.rng.integers(1e6)) if seed is None else seed
        k = 1 + lump * fbm(P, sd, freq or 1.3, 3) * 2
        if flat:
            k = np.round(k / flat) * flat * 0.6 + k * 0.4
        P = P * k[:, None] * np.array(radii, float)
        rm = float(np.mean(radii)); V = []; U = []; FF = []
        for f in F:                                        # a chart per face keeps it simple and seam-safe
            i0 = len(V)
            for vi in f:
                p = P[vi]; d = p / (np.linalg.norm(p) + 1e-9)
                V.append(p); U.append((math.atan2(d[1], d[0]) * rm, math.asin(max(-1, min(1, d[2]))) * rm))
            us = [U[i0 + j][0] for j in range(3)]
            if max(us) - min(us) > math.pi * rm:
                for j in range(3):
                    if U[i0 + j][0] < 0:
                        U[i0 + j] = (U[i0 + j][0] + 2 * math.pi * rm, U[i0 + j][1])
            FF.append((i0, i0 + 1, i0 + 2))
        n0 = s.add(V, FF, mat, U)
        T = Matrix.Translation(c) @ (Matrix(M) if M is not None else Matrix.Identity(4))
        s.xform_since(n0, T)
        return n0

    def rivet(s, p, nrm, r=0.006, h=None, mat=0, n=8):
        """domed rivet / nail head at p, standing along nrm"""
        h = h or r * 0.55; nrm = np.array(nrm, float); nrm /= np.linalg.norm(nrm)
        prof = [(r, -0.002), (r, 0.0), (r * 0.85, h * 0.6), (r * 0.5, h * 0.93), (0.0, h)]
        n0 = s.lathe(prof, n=n, mat=mat)
        z = Vector(nrm); q = Vector((0, 0, 1)).rotation_difference(z).to_matrix().to_4x4()
        s.xform_since(n0, Matrix.Translation(p) @ q)
        return n0

    # -- to Blender
    def obj(s, name, mats, sharp=40.0, merge=0.0002, coll=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata([Vector(v) for v in s.V], [], s.F)
        uv = me.uv_layers.new(name='UVMap')
        U = np.array(s.UV, np.float32); li = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', li)
        uv.data.foreach_set('uv', U[li].ravel())
        me.polygons.foreach_set('material_index', np.array(s.M, np.int32))
        for m_ in mats:
            me.materials.append(m_)
        ga = me.attributes.new('grp', 'INT', 'POINT'); ga.data.foreach_set('value', np.array(s.G, np.int32))
        bm = bmesh.new(); bm.from_mesh(me)
        if merge:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
            bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=merge * 0.5)
        bm.to_mesh(me); bm.free()
        me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
        me.set_sharp_from_angle(angle=math.radians(sharp))
        me.update()
        ob = bpy.data.objects.new(name, me); (coll or bpy.context.scene.collection).objects.link(ob)
        return ob


# ---------------------------------------------------------------- shader helper
CH = {}            # material name -> {'bc': socket, 'orm': socket, 'e': socket|None, 'out': node, 'surf': socket}


class NT:
    def __init__(s, name):
        s.m = bpy.data.materials.new(name); s.m.use_nodes = True; s.t = s.m.node_tree; s.L = s.t.links
        for n in list(s.t.nodes):
            s.t.nodes.remove(n)
        s.tc = s.t.nodes.new('ShaderNodeTexCoord'); s.P = s.tc.outputs['Object']; s.UV = s.tc.outputs['UV']
        s.geo = s.t.nodes.new('ShaderNodeNewGeometry'); s._ao = {}; s._edge = {}

    def node(s, typ, **kw):
        n = s.t.nodes.new(typ)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def set(s, sock, v):
        if hasattr(v, 'is_linked'):
            s.L.new(v, sock)
        elif v is not None:
            if hasattr(sock.default_value, '__len__') and not hasattr(v, '__len__'):
                v = (v,) * len(sock.default_value) if len(sock.default_value) != 4 else (v, v, v, 1)
            elif hasattr(sock.default_value, '__len__') and len(sock.default_value) == 4 and len(v) == 3:
                v = (*v, 1)
            sock.default_value = v

    def math(s, op, a, b=None, c=None, clamp=False):
        n = s.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        for sock, v in zip(n.inputs, (a, b, c)):
            s.set(sock, v)
        return n.outputs[0]

    def mul(s, a, b): return s.math('MULTIPLY', a, b)
    def add(s, a, b): return s.math('ADD', a, b)
    def sub(s, a, b): return s.math('SUBTRACT', a, b)
    def inv(s, a): return s.math('SUBTRACT', 1.0, a, clamp=True)
    def sat(s, a): return s.math('ADD', a, 0.0, clamp=True)
    def mx(s, a, b): return s.math('MAXIMUM', a, b)
    def mn(s, a, b): return s.math('MINIMUM', a, b)

    def step(s, x, lo, hi):
        n = s.node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP'); s.set(n.inputs[0], x); n.inputs[1].default_value = lo; n.inputs[2].default_value = hi
        return n.outputs[0]

    def mix(s, a, b, f, blend='MIX'):
        n = s.node('ShaderNodeMix', data_type='RGBA', blend_type=blend, clamp_factor=True)
        s.set(n.inputs[0], f); s.set(n.inputs[6], a); s.set(n.inputs[7], b); return n.outputs[2]

    def mixf(s, a, b, f):
        n = s.node('ShaderNodeMix', data_type='FLOAT', clamp_factor=True)
        s.set(n.inputs[0], f); s.set(n.inputs[2], a); s.set(n.inputs[3], b); return n.outputs[0]

    def vec(s, v, scale=None, loc=None, rot=None):
        n = s.node('ShaderNodeMapping'); s.set(n.inputs[0], v)
        if loc is not None: n.inputs['Location'].default_value = loc
        if rot is not None: n.inputs['Rotation'].default_value = rot
        if scale is not None: n.inputs['Scale'].default_value = scale if hasattr(scale, '__len__') else (scale,) * 3
        return n.outputs[0]

    def noise(s, scale, detail=4.0, rough=0.55, vec=None, distort=0.0, col=False):
        n = s.node('ShaderNodeTexNoise', noise_dimensions='3D'); s.set(n.inputs['Vector'], vec if vec is not None else s.P)
        n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = distort
        return n.outputs['Color' if col else 0]

    def voro(s, scale, feature='F1', vec=None, out='Distance', rand=1.0, smooth=None):
        n = s.node('ShaderNodeTexVoronoi', voronoi_dimensions='3D', feature=feature); s.set(n.inputs['Vector'], vec if vec is not None else s.P)
        n.inputs['Scale'].default_value = scale; n.inputs['Randomness'].default_value = rand
        if smooth is not None and 'Smoothness' in n.inputs: n.inputs['Smoothness'].default_value = smooth
        return n.outputs[out]

    def img(s, rel, vec=None, cs='sRGB', box=False):
        n = s.node('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(TP, rel), check_existing=True); n.image.colorspace_settings.name = cs
        if box:
            n.projection = 'BOX'; n.projection_blend = 0.25
        s.set(n.inputs[0], vec if vec is not None else s.UV); return n.outputs[0]

    def ramp(s, x, stops, interp='LINEAR'):
        n = s.node('ShaderNodeValToRGB'); cr = n.color_ramp; cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p; e.color = (*c, 1) if hasattr(c, '__len__') else (c, c, c, 1)
        s.set(n.inputs[0], x); return n.outputs[0]

    def bw(s, c):
        n = s.node('ShaderNodeRGBToBW'); s.set(n.inputs[0], c); return n.outputs[0]

    def sep(s, v):
        n = s.node('ShaderNodeSeparateXYZ'); s.set(n.inputs[0], v); return n.outputs

    def rand(s):
        return s.geo.outputs['Random Per Island']

    def ao(s, dist=0.12, samples=8):
        """1 = open, 0 = buried (crevices, contact)"""
        k = (dist, samples)
        if k not in s._ao:
            n = s.node('ShaderNodeAmbientOcclusion', samples=samples, only_local=False); n.inputs['Distance'].default_value = dist; s._ao[k] = n.outputs['AO']
        return s._ao[k]

    def edge(s, radius=0.006, gain=3.5):
        """0..1 mask of creases (convex and concave) from the bevel-normal trick"""
        k = (radius, gain)
        if k not in s._edge:
            b = s.node('ShaderNodeBevel', samples=6); b.inputs['Radius'].default_value = radius
            d = s.node('ShaderNodeVectorMath', operation='DOT_PRODUCT'); s.L.new(b.outputs[0], d.inputs[0]); s.L.new(s.geo.outputs['Normal'], d.inputs[1])
            s._edge[k] = s.math('MULTIPLY', s.math('SUBTRACT', 1.0, d.outputs['Value']), gain, clamp=True)
        return s._edge[k]

    def wear(s, radius=0.006, gain=3.5, breakup=60.0, amount=0.5):
        """convex-edge wear: creases that are open to the sky, broken by noise"""
        e = s.mul(s.edge(radius, gain), s.step(s.ao(0.03, 6), 0.55, 0.9))
        return s.step(s.add(e, s.mul(s.sub(s.noise(breakup, 3.0), 0.5), 0.9)), 1.0 - amount, 1.15 - amount * 0.6)

    def finish(s, bc, rough, metal=0.0, height=None, bump=0.002, emis=None, bevel=0.0025, nmap=None, kind='opaque', sss=None):
        P = s.node('ShaderNodeBsdfPrincipled'); out = s.node('ShaderNodeOutputMaterial')
        s.set(P.inputs['Base Color'], bc); s.set(P.inputs['Roughness'], rough); s.set(P.inputs['Metallic'], metal)
        nrm = None
        if bevel:
            b = s.node('ShaderNodeBevel', samples=6); b.inputs['Radius'].default_value = bevel; nrm = b.outputs[0]
        if nmap is not None:
            nm = s.node('ShaderNodeNormalMap'); s.set(nm.inputs['Color'], nmap[0]); nm.inputs['Strength'].default_value = nmap[1]
            if nrm is not None:                       # the scan normal goes in first, the bevel is laid over it near edges only
                mixn = s.node('ShaderNodeMix', data_type='VECTOR'); s.set(mixn.inputs[0], s.edge(bevel * 1.5, 6.0)); s.L.new(nm.outputs[0], mixn.inputs[4]); s.L.new(nrm, mixn.inputs[5])
                nv = s.node('ShaderNodeVectorMath', operation='NORMALIZE'); s.L.new(mixn.outputs[1], nv.inputs[0]); nrm = nv.outputs[0]
            else:
                nrm = nm.outputs[0]
        if height is not None:
            bp = s.node('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = bump
            s.set(bp.inputs['Height'], height)
            if nrm is not None: s.L.new(nrm, bp.inputs['Normal'])
            nrm = bp.outputs[0]
        if nrm is not None:
            s.L.new(nrm, P.inputs['Normal'])
        if emis is not None:
            s.set(P.inputs['Emission Color'], emis); P.inputs['Emission Strength'].default_value = 1.0
        s.L.new(P.outputs[0], out.inputs[0])
        orm = s.node('ShaderNodeCombineColor')
        ao = s.math('POWER', s.ao(0.25, 8), 0.8)
        s.set(orm.inputs[0], ao); s.set(orm.inputs[1], rough); s.set(orm.inputs[2], metal)
        em = s.node('ShaderNodeEmission'); CH[s.m.name] = {'bc': bc, 'orm': orm.outputs[0], 'e': emis, 'out': out, 'surf': P.outputs[0], 'em': em, 'nt': s}
        return s.m


def _swap(ch):
    """route channel ch of every high material to an emission shader (None restores the BSDF)"""
    for d in CH.values():
        s = d['nt']
        for l in list(d['out'].inputs[0].links):
            s.L.remove(l)
        if ch is None:
            s.L.new(d['surf'], d['out'].inputs[0]); continue
        for l in list(d['em'].inputs[0].links):
            s.L.remove(l)
        v = d[ch]
        if v is None:
            d['em'].inputs[0].default_value = (0, 0, 0, 1)
        elif hasattr(v, 'is_linked'):
            s.L.new(v, d['em'].inputs[0])
        else:
            d['em'].inputs[0].default_value = (*v, 1) if hasattr(v, '__len__') else (v, v, v, 1)
        s.L.new(d['em'].outputs[0], d['out'].inputs[0])


# ---------------------------------------------------------------- game mesh
def game_material(name, asset, kind='opaque', params=None):
    """preview of the Unreal material of a baked prop slot: T_<asset>_BC / _N / _ORM / _E at UV0"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; P = nt.nodes['Principled BSDF']; L = nt.links
    m['dink_kind'] = kind; m['dink_asset'] = asset
    for ch in ('BC', 'N', 'ORM', 'E'):
        n = nt.nodes.new('ShaderNodeTexImage'); n.name = ch; n.label = ch
    nt.nodes.active = nt.nodes['BC']
    return m


def wire_game_material(m, files, emis_strength=0.0, params=None):
    params = params or {}
    nt = m.node_tree; P = nt.nodes['Principled BSDF']; L = nt.links; kind = m['dink_kind']
    for ch, cs in (('BC', 'sRGB'), ('N', 'Non-Color'), ('ORM', 'Non-Color'), ('E', 'sRGB')):
        n = nt.nodes[ch]
        if ch in files:
            n.image = bpy.data.images.load(files[ch], check_existing=False); n.image.colorspace_settings.name = cs; n.image.name = os.path.basename(files[ch])[:-4]
        else:
            nt.nodes.remove(n)
    L.new(nt.nodes['BC'].outputs[0], P.inputs['Base Color'])
    sp = nt.nodes.new('ShaderNodeSeparateColor'); L.new(nt.nodes['ORM'].outputs[0], sp.inputs[0])
    L.new(sp.outputs[1], P.inputs['Roughness']); L.new(sp.outputs[2], P.inputs['Metallic'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); L.new(nt.nodes['N'].outputs[0], nm.inputs['Color']); L.new(nm.outputs[0], P.inputs['Normal'])
    if 'E' in files and emis_strength:
        L.new(nt.nodes['E'].outputs[0], P.inputs['Emission Color']); P.inputs['Emission Strength'].default_value = emis_strength
    if kind == 'subsurface':
        P.inputs['Subsurface Weight'].default_value = 1.0; P.inputs['Subsurface Radius'].default_value = params.get('sss_radius', (0.012, 0.007, 0.004)); P.inputs['Subsurface Scale'].default_value = 1.0
    if kind == 'translucent':
        if params.get('thin'):                        # horn / parchment: a diffusing sheet. Preview = half lit surface, half light carried through from behind
            tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); L.new(nt.nodes['BC'].outputs[0], tr.inputs['Color']); L.new(nm.outputs[0], tr.inputs['Normal'])
            ad = nt.nodes.new('ShaderNodeMixShader'); ad.inputs[0].default_value = params.get('transmission', 0.5); out = nt.nodes['Material Output']
            L.new(P.outputs[0], ad.inputs[1]); L.new(tr.outputs[0], ad.inputs[2]); L.new(ad.outputs[0], out.inputs[0])
        else:
            P.inputs['Transmission Weight'].default_value = params.get('transmission', 0.9); P.inputs['IOR'].default_value = params.get('ior', 1.5)
    nt.nodes.active = nt.nodes['BC']


def finish_lo(ob, lods=(0.5, 0.22), margin=0.004):
    """pack the primitive charts into 0-1 without overlap and make LOD1 / LOD2"""
    for o in [x_ for x_ in bpy.context.view_layer.objects if x_ is not None]:
        o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=margin, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    out = [ob]
    for i, r in enumerate(lods):
        o = ob.copy(); o.data = ob.data.copy(); o.name = ob.name.replace('_LOD0', '_LOD%d' % (i + 1)); o.data.name = o.name
        for c in ob.users_collection:
            c.objects.link(o)
        md = o.modifiers.new('d', 'DECIMATE'); md.ratio = r; md.delimit = {'UV'} if False else set()
        bpy.context.view_layer.objects.active = o; ob.select_set(False); o.select_set(True)
        bpy.ops.object.modifier_apply(modifier='d'); o.select_set(False); o.hide_render = True
        out.append(o)
    for o in out:                                         # the validator wants closed solids: weld and fill what decimation opened
        bm = bmesh.new(); bm.from_mesh(o.data)
        for it in range(2):
            be = [e for e in bm.edges if len(e.link_faces) == 1]
            if not be:
                break
            if it == 0:
                bmesh.ops.remove_doubles(bm, verts=list({v for e in be for v in e.verts}), dist=0.0006)
            else:
                bmesh.ops.holes_fill(bm, edges=be, sides=0)
        be = [e for e in bm.edges if len(e.link_faces) == 1]
        if be:                                            # a thin plate that decimation flattened to one sheet: give it its back again
            seen = set(); todo = [f for e in be for f in e.link_faces]
            while todo:
                f = todo.pop()
                if f in seen:
                    continue
                seen.add(f); todo += [g for e in f.edges for g in e.link_faces if g not in seen]
            bmesh.ops.solidify(bm, geom=list(seen), thickness=0.0015); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.00005)
        fixed = False
        for it in range(4):                               # fins left by decimation (an edge with three faces): drop the smallest face, refill
            bad = [e for e in bm.edges if len(e.link_faces) > 2]
            if not bad:
                break
            fixed = True
            bmesh.ops.delete(bm, geom=list({min(e.link_faces, key=lambda f: f.calc_area()) for e in bad}), context='FACES_ONLY')
            be = [e for e in bm.edges if len(e.link_faces) == 1]
            if be:
                bmesh.ops.holes_fill(bm, edges=be, sides=0)
            loose = [e for e in bm.edges if not e.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context='EDGES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')
        if fixed:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        nb = len([e for e in bm.edges if len(e.link_faces) != 2])
        if nb:
            print('OPEN EDGES LEFT', o.name, nb, [tuple(round(c, 2) for c in (e.verts[0].co + e.verts[1].co) / 2) + (len(e.link_faces),) for e in bm.edges if len(e.link_faces) != 2][:8])
        bm.to_mesh(o.data); bm.free(); o.data.update()
        if nb and o is not out[0]:                        # still not a closed solid: reuse the next finer LOD rather than ship a broken one
            prev = out[out.index(o) - 1]; old = o.data; done = False
            for ratio in (0.5, 0.33, 0.2):                # planar dissolve of the finer LOD (never opens a mesh), kept only if closed and lighter
                o.data = prev.data.copy(); md = o.modifiers.new('d', 'DECIMATE'); md.decimate_type = 'DISSOLVE'; md.angle_limit = ratio; md.delimit = {'UV'}
                for q in [x_ for x_ in bpy.context.view_layer.objects if x_ is not None]:
                    q.select_set(False)
                hr = o.hide_render; bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.modifier_apply(modifier='d'); o.select_set(False); o.hide_render = hr
                b2 = bmesh.new(); b2.from_mesh(o.data); bmesh.ops.triangulate(b2, faces=b2.faces); ok = all(len(e.link_faces) == 2 for e in b2.edges) and len(b2.faces) < 0.85 * tris(prev)
                b2.to_mesh(o.data); b2.free()
                if ok:
                    done = True; break
            if not done:
                o.data = prev.data.copy()
            o.data.name = o.name; print('LOD FALLBACK', o.name, ratio if done else 'copy')
    return out


def tris(ob):
    ob.data.calc_loop_triangles(); return len(ob.data.loop_triangles)


# ---------------------------------------------------------------- bake
def _save_png(name, px, arr, path, srgb):
    """arr (px, px, 3|4) float 0..1 already encoded for the file"""
    a = np.ones((px, px, 4), np.float32); a[..., :arr.shape[2]] = np.clip(arr, 0, 1)
    im = bpy.data.images.new(name + '_save', px, px, alpha=False, float_buffer=False, is_data=True)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(a.ravel()); im.filepath_raw = path; im.file_format = 'PNG'
    sc = bpy.context.scene; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.color_depth = '8'; sc.render.image_settings.compression = 60
    im.save_render(path, scene=None) if False else im.save()
    bpy.data.images.remove(im)


def lin2srgb(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def bake(asset, hi_obs, lo, px, outdir, extrude=0.006, maxdist=0.02, emissive=False, spp=None, post=None):
    """bake the high source onto the game mesh; writes T_<asset>_BC/_N/_ORM(/_E).png into outdir; returns {ch: path} and stats"""
    spp = dict(dict(bc=20, orm=28, n=10, e=6), **(spp or {}))
    sc = bpy.context.scene; use_hip_gpu(sc); sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.cycles.use_denoising = False; sc.cycles.max_bounces = 2; sc.cycles.use_adaptive_sampling = False
    os.makedirs(outdir, exist_ok=True)
    tname = 'T_' + asset[3:] if asset.startswith('SM_') else 'T_' + asset
    for o in [x_ for x_ in bpy.context.view_layer.objects if x_ is not None]:
        o.select_set(False)
    for o in hi_obs:
        o.hide_render = False; o.select_set(True)
    lo.hide_render = False; lo.select_set(True); bpy.context.view_layer.objects.active = lo
    for k_ in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):      # the game mesh must not occlude the source's AO rays
        setattr(lo, k_, False)
    img = bpy.data.images.new('bake_tmp', px, px, alpha=False, float_buffer=True, is_data=True)
    for m in lo.data.materials:
        m.node_tree.nodes['BC'].image = img; m.node_tree.nodes.active = m.node_tree.nodes['BC']
    res = {}; files = {}
    passes = [('bc', 'EMIT'), ('orm', 'EMIT'), ('n', 'NORMAL')] + ([('e', 'EMIT')] if emissive else [])
    import time
    for ch, typ in passes:
        t0 = time.time()
        _swap(ch if typ == 'EMIT' else None)
        sc.cycles.samples = spp[ch]
        kw = dict(type=typ, use_selected_to_active=True, cage_extrusion=extrude, max_ray_distance=maxdist, margin=12, margin_type='EXTEND', normal_space='TANGENT', use_clear=True, save_mode='INTERNAL')
        try:
            bpy.ops.object.bake(**kw)
        except RuntimeError as e:                     # out of VRAM: fall back to the CPU
            print('GPU bake failed, CPU retry:', e); sc.cycles.device = 'CPU'; bpy.ops.object.bake(**kw)
        a = np.zeros(px * px * 4, np.float32); img.pixels.foreach_get(a); res[ch] = a.reshape(px, px, 4)[..., :3].copy()
        print('BAKED', asset, ch, '%.0fs' % (time.time() - t0)); sys.stdout.flush()
    _swap(None)
    if post:
        post(res)
    bc = res['bc']; lum = lin2srgb(bc) @ np.array([0.2126, 0.7152, 0.0722]) * 255
    stats = {'albedo_luma_srgb': {'p1': round(float(np.percentile(lum, 1)), 1), 'mean': round(float(lum.mean()), 1), 'p99': round(float(np.percentile(lum, 99)), 1)},
             'roughness': {'p5': round(float(np.percentile(res['orm'][..., 1], 5)), 3), 'mean': round(float(res['orm'][..., 1].mean()), 3), 'p95': round(float(np.percentile(res['orm'][..., 1], 95)), 3)},
             'metallic_mean': round(float(res['orm'][..., 2].mean()), 3)}
    for ch, key, srgb in (('bc', 'BC', True), ('n', 'N', False), ('orm', 'ORM', False), ('e', 'E', True)):
        if ch not in res:
            continue
        p = os.path.join(outdir, '%s_%s.png' % (tname, key)); _save_png(tname + key, px, lin2srgb(res[ch]) if srgb else res[ch], p, srgb); files[key] = p
    bpy.data.images.remove(img)
    for k_ in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):
        setattr(lo, k_, True)
    for o in hi_obs:
        o.hide_render = True; o.select_set(False)
    return files, stats


# ---------------------------------------------------------------- review renders
def review_setup(floor='PlankFloor', wall=None, exposure=-4.6):
    sc = bpy.context.scene
    use_hip_gpu(sc); sc.cycles.use_denoising = True; sc.cycles.max_bounces = 5; sc.cycles.use_adaptive_sampling = True
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; nt = w.node_tree; sky = nt.nodes.new('ShaderNodeTexSky')
    ids = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
        if t in ids:
            sky.sky_type = t; break
    sky.sun_elevation = math.radians(40); sky.sun_rotation = math.radians(-150)
    nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0])
    made = []

    def setmat(setname, root):
        info = json.load(open(os.path.join(root, setname, 'set.json')))
        fm = bpy.data.materials.new('rv_' + setname); fm.use_nodes = True; n2 = fm.node_tree; b = n2.nodes['Principled BSDF']

        def t(k, cs):
            n = n2.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(root, info['files'][k])); n.image.colorspace_settings.name = cs; return n
        bc = t('BC', 'sRGB'); nm = t('N', 'Non-Color'); orm = t('ORM', 'Non-Color')
        n2.links.new(bc.outputs[0], b.inputs['Base Color'])
        sp = n2.nodes.new('ShaderNodeSeparateColor'); n2.links.new(orm.outputs[0], sp.inputs[0]); n2.links.new(sp.outputs[1], b.inputs['Roughness'])
        nn = n2.nodes.new('ShaderNodeNormalMap'); n2.links.new(nm.outputs[0], nn.inputs['Color']); n2.links.new(nn.outputs[0], b.inputs['Normal'])
        return fm, info['tile_size_m']

    def plane(name, co, mat, tile, ax):
        me = bpy.data.meshes.new(name); me.from_pydata(co, [], [[0, 1, 2, 3]]); uv = me.uv_layers.new()
        for li in range(4):
            c = co[me.loops[li].vertex_index]; uv.data[li].uv = (c[ax[0]] / tile, c[ax[1]] / tile)
        me.materials.append(mat); o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); made.append(o); return o
    fm, tile = setmat(floor, os.path.join(PP, 'Terrain')); S = 40.0
    plane('rv_floor', [(-S, -S, 0), (S, -S, 0), (S, S, 0), (-S, S, 0)], fm, tile, (0, 1))
    if wall:
        wm, wt = setmat(wall, os.path.join(PP, 'Terrain'))
        plane('rv_wall', [(-4, 0.0, 0), (4, 0.0, 0), (4, 0.0, 3.2), (-4, 0.0, 3.2)], wm, wt, (0, 2))
    camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam); sc.camera = cam; camd.clip_start = 0.02
    return {'sky': sky, 'bg': nt.nodes['Background'], 'cam': cam, 'exposure': exposure, 'made': made}


def review_shot(R, path, loc, tgt, lens=35, res=(900, 680), spp=40, interior=None, watts=40.0, fill=14.0, exposure=None):
    sc = bpy.context.scene; cam = R['cam']
    cam.location = loc; cam.data.lens = lens; cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100; sc.cycles.samples = spp
    tmp = []
    if interior:
        R['bg'].inputs[1].default_value = 0.004; R['sky'].sun_disc = False; sc.view_settings.exposure = 1.2 if exposure is None else exposure
        ld = bpy.data.lights.new('fire', 'POINT'); ld.energy = watts; ld.color = (1.0, 0.56, 0.26); ld.shadow_soft_size = 0.05
        lo_ = bpy.data.objects.new('fire', ld); sc.collection.objects.link(lo_); lo_.location = interior; tmp.append(lo_)
        ld2 = bpy.data.lights.new('fill', 'AREA'); ld2.energy = fill; ld2.color = (0.55, 0.65, 1.0); ld2.size = 2.0
        lo2 = bpy.data.objects.new('fill', ld2); sc.collection.objects.link(lo2); lo2.location = (-3.0, -4.0, 2.5); lo2.rotation_euler = (math.radians(60), 0, math.radians(-35)); tmp.append(lo2)
    else:
        R['bg'].inputs[1].default_value = 1.0; R['sky'].sun_disc = True; sc.view_settings.exposure = R['exposure'] if exposure is None else exposure
    sc.render.filepath = path
    try:
        bpy.ops.render.render(write_still=True)
    except RuntimeError as e:
        print('GPU render failed, CPU retry:', e); sc.cycles.device = 'CPU'; bpy.ops.render.render(write_still=True)
    print('RENDERED', path); sys.stdout.flush()
    for o in tmp:
        bpy.data.objects.remove(o)


def pose_object(ob, mats):
    """move the vertices of a built mesh by the 'grp' attribute: {group: 4x4}"""
    me = ob.data; n = len(me.vertices); G = np.zeros(n, np.int32); me.attributes['grp'].data.foreach_get('value', G)
    P = np.zeros(n * 3, np.float32); me.vertices.foreach_get('co', P); P = P.reshape(n, 3)
    for g, M in mats.items():
        M = np.array(M, np.float32); k = G == g; P[k] = P[k] @ M[:3, :3].T + M[:3, 3]
    me.vertices.foreach_set('co', P.ravel()); me.update()
