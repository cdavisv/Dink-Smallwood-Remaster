"""Procedural tree / plant mesh building for the vegetation pass (Blender batch).
Wind vertex colour convention (colour attribute 'Wind', linear):
  R = trunk sway weight (0 at ground, 1 at full tree height, linear in height)
  G = per-branch phase 0..1 (random per primary limb; cards inherit it)
  B = leaf flutter weight (0 on wood and at the twig attach, 1 at the free card edges)
  A = branch bend weight (0 at the trunk, 1 at the limb tip)
Second UV channel 'UVMask' (trees, stumps): U = ground blend weight (1 at and below ground level, fading to 0 about 0.9 m up the bark),
  for blending soil / moss darkening in the material; V = 0 (spare).
Trees and stumps extend BELOW_GROUND metres below the pivot (buttress roots dive into the soil) so they sit on uneven terrain.
"""
import bpy, numpy as np, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'Export', 'Textures')
PX = 2.0 / 2048
BELOW_GROUND = 0.18
BANDS = {'base': (0.0 + PX, 0.25), 'body': (0.25, 0.75), 'limb': (0.75 + PX, 1.0 - PX)}

def nrm(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-12)

def resample(pts, radii, ds):
    pts = np.asarray(pts, float); radii = np.asarray(radii, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    n = max(1, int(round(cum[-1] / ds)))
    s = np.linspace(0, cum[-1], n + 1)
    out = np.stack([np.interp(s, cum, pts[:, k]) for k in range(3)], 1)
    return out, np.interp(s, cum, radii)

def trunk_resample(pts, radii, ds, base_len, lod=0):
    """dense rings through the root flare (first base_len metres, mapped to the 'base' band), uniform ds above. Returns pts, radii, base_segs."""
    pts = np.asarray(pts, float); radii = np.asarray(radii, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    fr = ([0, .05, .12, .22, .36, .55, .78, 1.0], [0, .1, .3, .6, 1.0], [0, .35, 1.0])[lod]
    n = max(1, int(round((cum[-1] - base_len) / ds)))
    s = np.concatenate([np.array(fr) * base_len, base_len + (cum[-1] - base_len) * np.arange(1, n + 1) / n])
    out = np.stack([np.interp(s, cum, pts[:, k]) for k in range(3)], 1)
    return out, np.interp(s, cum, radii), len(fr) - 1

def chaikin(pts, it=1):
    pts = np.asarray(pts, float)
    for _ in range(it):
        if len(pts) < 3: break
        q = 0.75 * pts[:-1] + 0.25 * pts[1:]; r = 0.25 * pts[:-1] + 0.75 * pts[1:]
        mid = np.empty((2 * len(q), 3)); mid[0::2] = q; mid[1::2] = r
        pts = np.vstack([pts[:1], mid, pts[-1:]])
    return pts

def path(p0, d0, L, n, rng, wander=0.2, bias=None):
    pts = [np.array(p0, float)]; d = nrm(d0)
    for i in range(n):
        t = (i + 0.5) / n
        d = d + rng.normal(0, wander / math.sqrt(n), 3)
        if bias is not None: d = d + np.asarray(bias(t, d, pts[-1])) / n
        d = nrm(d); pts.append(pts[-1] + d * L / n)
    return np.array(pts)

class MeshB:
    def __init__(s):
        s.v = []; s.n = []; s.col = []; s.faces = []; s.uv = []; s.mat = []; s.keep_z = False; s.mask_mats = (0,)
    def nv(s): return len(s.v)
    def tris(s): return sum(len(f) - 2 for f in s.faces)

    def tube(s, pts, radii, sides, band='limb', urep=1, tile_len=1.0, wind=(0, 0, 0, 0), wind1=None, base_segs=0,
             radial=None, cap=True, mat=0, vphase=0, level_base=True):
        """pts must be roughly uniformly spaced. base_segs>0: that many first segments use the 'base' band."""
        pts = np.asarray(pts, float); n = len(pts)
        if n < 2: return
        seglen = np.linalg.norm(pts[-1] - pts[-2])
        k = max(1, int(round(tile_len / max(seglen, 1e-6))))
        lo, hi = BANDS[band]
        d0 = nrm(pts[1] - pts[0])
        a = np.array([0, 0, 1.0]) if abs(d0[2]) < 0.9 else np.array([1.0, 0, 0])
        u = nrm(np.cross(a, d0)); base = s.nv()
        wind1 = wind if wind1 is None else wind1
        for i in range(n):
            d = nrm(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
            u = nrm(u - d * np.dot(u, d)); w = np.cross(d, u)
            t = i / (n - 1)
            for j in range(sides):
                ang = 2 * math.pi * j / sides
                rr = radii[i] * (radial(i, ang) if radial else 1.0)
                o = math.cos(ang) * u + math.sin(ang) * w
                pv = pts[i] + rr * o
                if i == 0 and base_segs > 0 and level_base: pv[2] = pts[0][2]      # a leaning trunk still meets the ground with a level ring
                s.v.append(pv); s.n.append(o)
                s.col.append(tuple(np.array(wind) * (1 - t) + np.array(wind1) * t))
        for i in range(n - 1):
            if i < base_segs:
                blo, bhi = BANDS['base']; v0 = blo + (bhi - blo) * i / base_segs; v1 = blo + (bhi - blo) * (i + 1) / base_segs
            else:
                j = (i - base_segs + vphase) % k; v0 = lo + (hi - lo) * j / k; v1 = lo + (hi - lo) * (j + 1) / k
            for j in range(sides):
                a0 = base + i * sides + j; a1 = base + i * sides + (j + 1) % sides
                s.faces.append((a0, a1, a1 + sides, a0 + sides))
                u0 = urep * j / sides; u1 = urep * (j + 1) / sides
                s.uv.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1))); s.mat.append(mat)
        if cap:
            c = s.nv(); d = nrm(pts[-1] - pts[-2])
            s.v.append(pts[-1] + d * radii[-1] * 0.6); s.n.append(d); s.col.append(tuple(wind1))
            l = base + (n - 1) * sides
            for j in range(sides):
                s.faces.append((l + j, l + (j + 1) % sides, c))
                s.uv.append(((0.1, lo + 0.01), (0.14, lo + 0.01), (0.12, lo + 0.03))); s.mat.append(mat)

    def root_base(s, axis, rfun, seed, lod, top=0.7, urep=1, nroots=None, strength=1.0, mat=0, tubes=True, depth=BELOW_GROUND):
        """Buttressed trunk base as ONE surface from z=-depth to z=top: root ridges grow out of the bole toward the ground and dive under it;
        thinner root ends continue as tapered tubes that start inside the ridge tips. axis(z)->xyz, rfun(z)->trunk radius without flare.
        UVs use the 'base' band (v 0..0.25 over the height). Returns the top ring radius."""
        rng = np.random.default_rng(seed)
        nroots = nroots or int(rng.integers(4, 7))
        raz = np.sort((np.arange(nroots) + rng.uniform(-0.3, 0.3, nroots)) * 2 * math.pi / nroots + rng.uniform(0, 6.28)) % (2 * math.pi)
        ramp = rng.uniform(0.75, 1.5, nroots) * strength; rsig = rng.uniform(0.2, 0.32, nroots)
        zl = ([-depth, -0.07, 0.0, 0.05, 0.12, 0.22, 0.36, 0.52, top], [-depth, 0.0, 0.1, 0.3, top], [-depth, 0.05, top])[lod]
        zl = [z for z in zl if z < top - 1e-6] + [top]
        nuni = (12, 8, 6)[lod]
        angs = list(np.arange(nuni) * 2 * math.pi / nuni)
        if lod < 2:
            for k in range(nroots):
                angs += [raz[k]] + ([raz[k] - rsig[k] * 0.8, raz[k] + rsig[k] * 0.8] if lod == 0 else [])
        angs = np.sort(np.array(angs) % (2 * math.pi)); angs = angs[np.concatenate([[True], np.diff(angs) > 0.04])]
        S = len(angs); R = len(zl); P = np.zeros((R, S, 3))
        def lobes(a, z):
            g = math.exp(-max(z, 0.0) / 0.17) * (1.0 + 0.9 * max(-z, 0.0) / depth); t = 0.0
            for k in range(nroots):
                d = (a - raz[k] + math.pi) % (2 * math.pi) - math.pi; t += ramp[k] * math.exp(-(d / rsig[k]) ** 2)
            return g * t
        for i, z in enumerate(zl):
            c = np.asarray(axis(max(z, 0.0)), float); c = np.array([c[0], c[1], z]); r = rfun(max(z, 0.0)) * (1 + 0.22 * math.exp(-max(z, 0) / 0.4))
            for j, a in enumerate(angs):
                rr = r * (1 + lobes(a, z)) * (1 + 0.03 * math.sin(5 * a + seed + z * 4)) if i < len(zl) - 1 else r * 0.975      # top ring is a plain circle tucked just inside the bole tube, which laps 7 cm down over it
                P[i, j] = c + rr * np.array([math.cos(a), math.sin(a), 0])
        # normals from the grid
        dz = np.gradient(P, axis=0); da = (np.roll(P, -1, 1) - np.roll(P, 1, 1))
        N = np.cross(da, dz); N /= (np.linalg.norm(N, axis=2, keepdims=True) + 1e-9)
        for j, a in enumerate(angs):          # shade the top of the base like the bole tube (radial normals) so no lighting step shows at the join
            ro = np.array([math.cos(a), math.sin(a), 0.0]); N[R - 1, j] = ro; N[R - 2, j] = nrm(N[R - 2, j] + ro)
        blo, bhi = BANDS['base']; base = s.nv()
        for i in range(R):
            for j in range(S):
                s.v.append(P[i, j]); s.n.append(N[i, j]); s.col.append((0, 0, 0, 0))
        for i in range(R - 1):
            v0 = blo + (bhi - blo) * (zl[i] + depth) / (top + depth); v1 = blo + (bhi - blo) * (zl[i + 1] + depth) / (top + depth)
            for j in range(S):
                j1 = (j + 1) % S; da = (angs[j1] - angs[j]) % (2 * math.pi)          # U is phased to the bole tube's own angle origin (-Y) so the bark pattern runs on across the join
                u0 = urep * ((angs[j] + math.pi / 2) % (2 * math.pi)) / (2 * math.pi); u1 = u0 + urep * da / (2 * math.pi)
                s.faces.append((base + i * S + j, base + i * S + j1, base + (i + 1) * S + j1, base + (i + 1) * S + j))
                s.uv.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1))); s.mat.append(mat)
        if tubes and lod < 2:
            r0 = rfun(0.0)
            for k in range(nroots):
                if lod == 1 and ramp[k] < 1.0 * strength: continue
                o = np.array([math.cos(raz[k]), math.sin(raz[k]), 0]); c = np.asarray(axis(0.0), float); c[2] = 0
                rt = r0 * (1 + ramp[k]); wr = max(0.035, r0 * (0.18 + 0.1 * ramp[k]))
                p0 = c + o * rt * 0.72 + np.array([0, 0, wr * 0.55])
                L = r0 * rng.uniform(1.6, 3.2) * (0.6 + 0.4 * ramp[k] / strength)
                pp = path(p0, o + [0, 0, -0.12], L, 5, rng, 0.35, lambda t, d, p: (0, 0, -0.75))
                rad = wr * (1 - np.linspace(0, 1, 6) ** 1.4 * 0.75)
                pp[:, 2] = np.maximum(pp[:, 2], -depth + rad * 0.3)
                sel = [0, 1, 2, 3, 4, 5] if lod == 0 else [0, 2, 4, 5]
                s.tube(pp[sel], rad[sel], (6, 4)[lod], 'body', 1, 0.6, cap=True, mat=mat)
        s.keep_z = True; s.last_base = (base, R, S, angs)
        return rfun(top) * (1 + 0.22 * math.exp(-top / 0.4))

    def card(s, origin, d, w, length, width, tile, segs=2, cols=2, droop=0.3, ridge=0.08, center=None, nblend=0.65,
             wind=(0, 0, 0, 0), mat=1, flip=False, lift=0.0, uvaxis='u', curl=0.0):
        """Bent alpha card: twig base at `origin`, growing along d, width along w. tile=(u0,v0,u1,v1)."""
        d = nrm(d); w = nrm(w - d * np.dot(w, d)); nf = np.cross(d, w)
        down = np.array([0, 0, -1.0])
        base = s.nv(); u0, v0, u1, v1 = tile
        P = np.array(origin, float); dd = d.copy(); row = []
        for a in range(segs + 1):
            ta = a / segs
            if a > 0:
                dd = nrm(dd + down * droop / segs + nf * lift / segs); P = P + dd * length / segs
            wl = nrm(w - dd * np.dot(w, dd)); nl = np.cross(dd, wl)
            for b in range(cols + 1):
                tb = b / cols
                off = (tb - 0.5) * width
                rz = ridge * width * (1 - abs(2 * tb - 1)) - curl * width * ta * ta
                p = P + wl * off + nl * rz
                s.v.append(p)
                if center is not None:
                    no = nrm(p - center); nn = nl if np.dot(nl, no) > 0 else -nl
                    side = wl * (tb - 0.5) * 0.6
                    s.n.append(nrm(nn * (1 - nblend) + no * nblend + side * (1 - nblend)))
                else:
                    nn = nl if nl[2] > 0 else -nl
                    s.n.append(nrm(nn + wl * (tb - 0.5) * 0.8))
                fl = min(1.0, 0.25 + 0.75 * ta + 0.5 * abs(2 * tb - 1)) if a > 0 else 0.5 * abs(2 * tb - 1)
                s.col.append((wind[0], wind[1], fl, wind[3]))
                tv = 1 - tb if flip else tb
                if uvaxis == 'u': row.append((u0 + (u1 - u0) * ta, v0 + (v1 - v0) * tv))
                else: row.append((u0 + (u1 - u0) * tv, v1 - (v1 - v0) * ta))
        C = cols + 1
        for a in range(segs):
            for b in range(cols):
                i0 = a * C + b; i1 = i0 + 1; i2 = i1 + C; i3 = i0 + C
                s.faces.append((base + i0, base + i1, base + i2, base + i3))
                s.uv.append((row[i0], row[i1], row[i2], row[i3])); s.mat.append(mat)

    def poly(s, verts, normals, uvs, mat=0, wind=(0, 0, 0, 0), faces=None):
        """generic geometry: verts (N,3), faces list of index tuples (local), uvs per-vertex (N,2)."""
        base = s.nv()
        for i in range(len(verts)):
            s.v.append(np.asarray(verts[i], float)); s.n.append(nrm(normals[i]))
            s.col.append(tuple(wind[i]) if np.ndim(wind) == 2 else tuple(wind))
        for f in faces:
            s.faces.append(tuple(base + i for i in f)); s.uv.append(tuple(tuple(uvs[i]) for i in f)); s.mat.append(mat)

    def build(s, name, materials):
        me = bpy.data.meshes.new(name)
        used = np.zeros(len(s.v), bool); used[np.fromiter((i for f in s.faces for i in f), dtype=np.int64)] = True
        if not used.all():        # drop vertices no face uses (faces removed for bark holes etc.)
            remap = np.cumsum(used) - 1; s.v = [p for p, u in zip(s.v, used) if u]; s.n = [p for p, u in zip(s.n, used) if u]; s.col = [p for p, u in zip(s.col, used) if u]
            s.faces = [tuple(int(remap[i]) for i in f) for f in s.faces]
        V = np.asarray(s.v, dtype=np.float32)
        # make the winding agree with the authored vertex normals (renderers darken faces whose shading normal opposes the geometric one)
        Nq = np.asarray(s.n, dtype=np.float32)
        for fi, f in enumerate(s.faces):
            g = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
            if np.dot(g, Nq[list(f)].sum(0)) < 0:
                s.faces[fi] = tuple(reversed(f)); s.uv[fi] = tuple(reversed(s.uv[fi]))
        me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
        tot = sum(len(f) for f in s.faces)
        me.loops.add(tot); me.polygons.add(len(s.faces))
        li = np.fromiter((i for f in s.faces for i in f), dtype=np.int32, count=tot)
        me.loops.foreach_set('vertex_index', li)
        lt = np.array([len(f) for f in s.faces], dtype=np.int32)
        me.polygons.foreach_set('loop_start', (np.cumsum(lt) - lt).astype(np.int32)); me.polygons.foreach_set('loop_total', lt)
        me.polygons.foreach_set('material_index', np.array(s.mat, dtype=np.int32))
        me.polygons.foreach_set('use_smooth', np.ones(len(s.faces), dtype=bool))
        me.update(calc_edges=True)
        uv = me.uv_layers.new(name='UVMap')
        uv.data.foreach_set('uv', np.fromiter((c for f in s.uv for p in f for c in p), dtype=np.float32, count=tot * 2))
        if s.keep_z:
            mk = me.uv_layers.new(name='UVMask'); fm = np.repeat(np.isin(np.array(s.mat), s.mask_mats), lt)
            z = V[li, 2]; w = np.clip(1 - z / 0.9, 0, 1) ** 1.6 * fm
            mk.data.foreach_set('uv', np.stack([w, np.zeros_like(w)], 1).astype(np.float32).ravel())
        ca = me.color_attributes.new('Wind', 'BYTE_COLOR', 'CORNER')
        col = np.asarray(s.col, dtype=np.float32)[li]
        ca.data.foreach_set('color', col.ravel())
        Nn = np.asarray(s.n, dtype=np.float32)
        me.normals_split_custom_set_from_vertices(Nn.tolist())
        for m in materials: me.materials.append(m)
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        ob['dink_class'] = 'foliage'
        return ob

# ------------------------------------------------------------------ materials (preview of the game material)
def game_mat(name, tex, alpha=False, translucency=0.0, bc_gain=1.0, nstrength=1.0, basemask=False, tint=None):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); p = N.new('ShaderNodeBsdfPrincipled')
    def img(suffix, cs):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(f'{tex}_{suffix}.png' if os.path.isabs(tex) else os.path.join(TEX, f'{tex}_{suffix}.png'), check_existing=True)
        n.image.colorspace_settings.name = cs; return n
    bc = img('BC', 'sRGB'); nm = img('N', 'Non-Color'); orm = img('ORM', 'Non-Color')
    sep = N.new('ShaderNodeSeparateColor'); L.new(orm.outputs[0], sep.inputs[0])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 0.6
    L.new(bc.outputs[0], mul.inputs[6]); L.new(sep.outputs[0], mul.inputs[7])
    bcs = mul.outputs[2]
    if tint is not None:
        tn = N.new('ShaderNodeMix'); tn.data_type = 'RGBA'; tn.blend_type = 'MULTIPLY'; tn.inputs[0].default_value = 1.0
        L.new(bcs, tn.inputs[6]); tn.inputs[7].default_value = (*tint, 1); bcs = tn.outputs[2]
    if basemask:   # preview of the UVMask.u ground blend: damp soil darkening with a moss cast
        uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMask'; sx = N.new('ShaderNodeSeparateXYZ'); L.new(uvn.outputs[0], sx.inputs[0])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9.0; nz.inputs['Detail'].default_value = 5.0
        mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(sx.outputs[0], mm.inputs[0]); L.new(nz.outputs[0], mm.inputs[1])
        m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.use_clamp = True; L.new(mm.outputs[0], m2.inputs[0]); m2.inputs[1].default_value = 1.7
        dk = N.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'
        L.new(m2.outputs[0], dk.inputs[0]); L.new(bcs, dk.inputs[6]); dk.inputs[7].default_value = (0.42, 0.40, 0.30, 1); bcs = dk.outputs[2]
    L.new(bcs, p.inputs['Base Color'])
    L.new(sep.outputs[1], p.inputs['Roughness'])
    nmap = N.new('ShaderNodeNormalMap'); nmap.inputs['Strength'].default_value = nstrength
    L.new(nm.outputs[0], nmap.inputs['Color']); L.new(nmap.outputs[0], p.inputs['Normal'])
    if alpha:
        try: p.inputs['Specular IOR Level'].default_value = 0.2
        except Exception: pass
    surf = p.outputs[0]
    if translucency > 0:
        ss = img('SSS', 'sRGB'); tr = N.new('ShaderNodeBsdfTranslucent'); L.new(ss.outputs[0], tr.inputs['Color'])
        L.new(nmap.outputs[0], tr.inputs['Normal'])
        mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = translucency
        L.new(p.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); surf = mx.outputs[0]
    if alpha:
        # masked, like the UE material (clip at 0.33)
        th = N.new('ShaderNodeMath'); th.operation = 'GREATER_THAN'; th.inputs[1].default_value = 0.33
        L.new(bc.outputs['Alpha'], th.inputs[0])
        tb = N.new('ShaderNodeBsdfTransparent'); mx2 = N.new('ShaderNodeMixShader')
        L.new(th.outputs[0], mx2.inputs[0]); L.new(tb.outputs[0], mx2.inputs[1]); L.new(surf, mx2.inputs[2]); surf = mx2.outputs[0]
    L.new(surf, out.inputs[0])
    m['dink_two_sided'] = 1 if alpha else 0
    return m

# ------------------------------------------------------------------ export / stats
def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)

def export_fbx(ob, path):
    for o in bpy.context.scene.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    loc = ob.location.copy(); ob.location = (0, 0, 0)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'MESH'}, use_mesh_modifiers=True, mesh_smooth_type='OFF',
        use_triangles=True, use_tspace=False, use_custom_props=False, colors_type='LINEAR',
        apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL', axis_forward='Y', axis_up='Z',
        bake_space_transform=False, use_space_transform=True, add_leaf_bones=False, bake_anim=False,
        path_mode='STRIP', embed_textures=False, batch_mode='OFF')
    ob.location = loc

def bounds(ob):
    V = np.array([v.co[:] for v in ob.data.vertices]); return V.min(0), V.max(0)

def recenter(mb, xy=True):
    """base_center pivot: min z = 0; bbox centre XY at the origin (xy=True) or, for single trees (xy=False), the trunk base kept at the
    origin as long as that stays inside the 10 % tolerance of CONVENTIONS.md (else shifted just enough). Returns the applied offset."""
    V = np.asarray(mb.v); lo = V.min(0); hi = V.max(0)
    off = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    if getattr(mb, 'keep_z', False):                       # roots are authored to dive below the pivot, never deeper than BELOW_GROUND
        off[2] = 0.0; V = V.copy(); V[:, 2] = np.maximum(V[:, 2], -BELOW_GROUND); mb.v = list(V)
    if not xy:
        for k in (0, 1):
            tol = 0.09 * (hi[k] - lo[k]); off[k] = off[k] - np.clip(off[k], -tol, tol)
    mb.v = [p + off for p in mb.v]
    return off

# ------------------------------------------------------------------ review scene
def use_hip_gpu(scene=None):
    """Render on the RX 6800 via HIP (see CYCLES_GPU.md): only that device, preferences changed in memory only. VEG_CPU=1 forces the CPU."""
    scene = scene or bpy.context.scene
    if os.environ.get('VEG_CPU') == '1': scene.cycles.device = 'CPU'; return False
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'HIP'; prefs.refresh_devices(); found = False
        for d in prefs.devices:
            d.use = (d.type == 'HIP' and 'Radeon RX 6800' in d.name); found |= d.use
    except Exception as e:
        print('HIP not available:', e); found = False
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'GPU' if found else 'CPU'
    print('Cycles device:', scene.cycles.device, flush=True); return found

def setup_review(scene, sun_elev=40, sun_az=135, samples=64, res=(900, 1200), ground=True, ground_size=120):
    r = scene.render; r.engine = 'CYCLES'; scene.cycles.samples = samples; use_hip_gpu(scene)
    scene.cycles.use_denoising = True
    try: scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    scene.cycles.max_bounces = 6; scene.cycles.transparent_max_bounces = 24; scene.cycles.diffuse_bounces = 3
    scene.cycles.transmission_bounces = 4
    r.resolution_x, r.resolution_y = res; r.film_transparent = False
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'
    try: scene.view_settings.view_transform = 'AgX'
    except Exception: scene.view_settings.view_transform = 'Filmic'
    try: scene.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    w = bpy.data.worlds.new('Sky'); scene.world = w; w.use_nodes = True
    nt = w.node_tree; sky = nt.nodes.new('ShaderNodeTexSky')
    ids = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
    for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'SINGLE_SCATTERING'):
        if t in ids: sky.sky_type = t; break
    sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_az)
    try: sky.sun_intensity = 1.0
    except Exception: pass
    bg = nt.nodes['Background']; nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.08
    scene.view_settings.exposure = 0.0
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=ground_size, location=(0, 0, 0))
        g = bpy.context.active_object; g.name = 'ReviewGround'
        m = bpy.data.materials.new('ReviewGround'); m.use_nodes = True
        N = m.node_tree.nodes; L = m.node_tree.links; p = N['Principled BSDF']
        n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 0.35; n1.inputs['Detail'].default_value = 8
        n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 40; n2.inputs['Detail'].default_value = 6
        cr = N.new('ShaderNodeValToRGB'); L.new(n1.outputs[0], cr.inputs[0])
        cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[0].color = (0.02, 0.032, 0.008, 1)
        cr.color_ramp.elements[1].position = 0.7; cr.color_ramp.elements[1].color = (0.04, 0.034, 0.02, 1)
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 0.7
        L.new(cr.outputs[0], mx.inputs[6]); L.new(n2.outputs[0], mx.inputs[7]); L.new(mx.outputs[2], p.inputs['Base Color'])
        bmp = N.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.6; L.new(n2.outputs[0], bmp.inputs['Height'])
        L.new(bmp.outputs[0], p.inputs['Normal']); p.inputs['Roughness'].default_value = 0.95
        turf = os.path.abspath(os.path.join(HERE, '..', '..', 'Terrain', 'MeadowTurf', 'T_Terrain_MeadowTurf'))
        if os.path.exists(turf + '_BC.png') and os.environ.get('VEG_PLAIN_GROUND') != '1':     # in-repo terrain set as the review ground (2.8 m tile)
            m = game_mat('ReviewTurf', turf); tc = m.node_tree.nodes.new('ShaderNodeTexCoord'); mp = m.node_tree.nodes.new('ShaderNodeMapping')
            mp.inputs['Scale'].default_value = (0.357, 0.357, 0.357); m.node_tree.links.new(tc.outputs['Object'], mp.inputs[0])
            for nd in m.node_tree.nodes:
                if nd.type == 'TEX_IMAGE': m.node_tree.links.new(mp.outputs[0], nd.inputs[0])
        g.data.materials.append(m)
        return g

def ref_box(loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], 0.9)); b = bpy.context.active_object
    b.scale = (0.5, 0.3, 1.8); b.name = 'Ref180'
    m = bpy.data.materials.get('Ref180') or bpy.data.materials.new('Ref180'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.6, 0.12, 0.08, 1)
    b.data.materials.append(m); return b

def camera(scene, loc, target, lens=50, name='Cam'):
    from mathutils import Vector
    cam = bpy.data.cameras.new(name); cam.lens = lens; cam.clip_end = 500
    co = bpy.data.objects.new(name, cam); scene.collection.objects.link(co)
    co.location = loc
    dirv = Vector(target) - Vector(loc)
    co.rotation_euler = dirv.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co; return co

def render(scene, path, res=None, samples=None, exposure=None):
    scene.view_settings.exposure = exposure if exposure is not None else 0.0
    if res: sc_ = float(os.environ.get('VEG_SCALE', '1')); scene.render.resolution_x, scene.render.resolution_y = int(res[0] * sc_), int(res[1] * sc_)
    if samples: scene.cycles.samples = samples
    scene.render.filepath = path
    if os.path.exists(path): os.remove(path)
    try: bpy.ops.render.render(write_still=True)
    except Exception as e: print('render failed on', scene.cycles.device, e, flush=True)
    if not os.path.exists(path) and scene.cycles.device == 'GPU':       # out of memory on the card: retry on the CPU
        scene.cycles.device = 'CPU'; bpy.ops.render.render(write_still=True)
    print('rendered', path, flush=True)
