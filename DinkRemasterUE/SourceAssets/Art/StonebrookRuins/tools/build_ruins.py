"""Stonebrook house-fire kit: burning (vision 1) and burnt (vision 2) states of Dink's cottage
(screen 439) and the burnt interior modules of SCR_001.  Blender 5.2 background build:

    blender -b --factory-startup -t 3 -P SourceAssets/Art/StonebrookRuins/tools/build_ruins.py

Deterministic (ruin_common.SEED; build_exterior.py's seed-439 random stream is replayed so stones
and thatch bundles sit exactly where the intact cottage's do).  Reads, never writes, the existing
kits: StonebrookExterior/KIT_StonebrookExterior.blend (collision hulls and pivot of the intact
cottage) - opened read-only and never saved.  Writes only inside StonebrookRuins/.
Textures come from make_textures.py (run it first).
"""
import bpy, bmesh, math, json, random, sys
from pathlib import Path
from mathutils import Vector, Matrix, noise

HERE = Path(__file__).resolve().parent
KIT = HERE.parent                                     # SourceAssets/Art/StonebrookRuins
UE = KIT.parents[2]                                   # DinkRemasterUE
sys.path.insert(0, str(HERE))
for cand in [UE.parent / 'tools/blender', UE.parent / 'Dink-Smallwood-Remaster/tools/blender']:
    if (cand / 'dinkasset').exists():
        sys.path.insert(0, str(cand)); break
import ruin_common as R
from dinkasset import conventions as C
from dinkasset import common, make_lods

TEX = KIT / 'Textures'
EXT_BLEND = UE / 'SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend'
INT_BLEND = UE / 'SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend'
PATH = 'StonebrookRuins'

# ------------------------------------------------------------------ read the intact cottage (read-only)
bpy.ops.wm.open_mainfile(filepath=str(EXT_BLEND))
orig = bpy.data.objects['SM_Cottage_Stonebrook_01']
ORIG_DIMS = list(orig.dimensions)
ORIG_HULLS = []
for ob in bpy.data.objects:
    if ob.name.startswith('UCX_SM_Cottage_Stonebrook_01'):
        ORIG_HULLS.append((ob.name, [tuple(ob.matrix_world @ v.co) for v in ob.data.vertices], [tuple(p.vertices) for p in ob.data.polygons]))
ORIG_HULLS.sort()
# Pivot of the intact build: its finish() subtracted the construction-space bounds centre (x, y)
# and the sill bottom (z).  Construction min x is the roof panel edge, exactly -9.4 m; y is symmetric.
ov = [orig.matrix_world @ v.co for v in orig.data.vertices]
omn = Vector([min(v[i] for v in ov) for i in range(3)]); omx = Vector([max(v[i] for v in ov) for i in range(3)])
COTTAGE_PIVOT = Vector((-9.4 - omn.x, 0.0, 0.0))     # construction-space position of the asset origin
print('INTACT COTTAGE dims', ORIG_DIMS, 'bounds', tuple(omn), tuple(omx), 'hulls', len(ORIG_HULLS), 'pivot', tuple(COTTAGE_PIVOT))
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1.0

# ------------------------------------------------------------------ materials
MATS = {}
MAT_SPECS = {
    'MI_Ruin_FacadeFrontBack': ('Ruin_FacadeFrontBack', .9, None),
    'MI_Ruin_FacadeSides': ('Ruin_FacadeSides', .9, None),
    'MI_Ruin_Timber': ('Ruin_Timber', .8, None),
    'MI_Ruin_Thatch': ('Ruin_Thatch', .88, None),
    'MI_Ruin_AshEmber': ('Ruin_AshEmber', .93, 'E'),
    'MI_Ruin_ScorchGround': ('Ruin_ScorchGround', .92, 'A'),
    'MI_RuinInt_PlasterSoot': ('RuinInt_PlasterSoot', .9, None),
    'MI_RuinInt_FloorAsh': ('RuinInt_FloorAsh', .8, None),
    'MI_RuinInt_ScorchFloor': ('RuinInt_ScorchFloor', .9, 'A'),
    'MI_RuinInt_ScorchWall': ('RuinInt_ScorchWall', .9, 'A'),
    'MI_Ruin_FacadeFrontBack_Burning': ('Ruin_FacadeFrontBack_Burning', .9, None),
    'MI_Ruin_FacadeSides_Burning': ('Ruin_FacadeSides_Burning', .9, None),
    'MI_RuinInt_Blood': ('RuinInt_Blood', .3, 'A'),
    'MI_RuinMother_Body': ('RuinMother_Atlas', .6, None),
    'MI_RuinMother_Hair': ('RuinMother_Atlas', .5, 'A'),
}
MANIFEST_MATERIALS = {}


def load_img(name, linear):
    im = bpy.data.images.load(str(TEX / (name + '.png')), check_existing=True)
    im.name = name
    im.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'
    return im


def make_material(mname):
    tex, rough, extra = MAT_SPECS[mname]
    m = bpy.data.materials.new(mname); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value = rough
    bc = nodes.new('ShaderNodeTexImage'); bc.image = load_img(f'T_{tex}_BC', False); bc.label = 'BC'
    links.new(bc.outputs['Color'], bs.inputs['Base Color'])
    n = nodes.new('ShaderNodeTexImage'); n.image = load_img(f'T_{tex}_N', True); n.label = 'N'
    nm = nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .38
    links.new(n.outputs['Color'], nm.inputs['Color']); links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    o = nodes.new('ShaderNodeTexImage'); o.image = load_img(f'T_{tex}_ORM', True); o.label = 'ORM'
    sep = nodes.new('ShaderNodeSeparateColor'); links.new(o.outputs['Color'], sep.inputs[0])
    links.new(sep.outputs['Green'], bs.inputs['Roughness']); links.new(sep.outputs['Blue'], bs.inputs['Metallic'])
    textures = {'BC': f'Textures/T_{tex}_BC.png', 'N': f'Textures/T_{tex}_N.png', 'ORM': f'Textures/T_{tex}_ORM.png'}
    entry = {'name': mname, 'roughness': rough, 'metallic': 0, 'textures': textures,
             'normal_flip_green': True, 'normal_strength': .38}
    if extra == 'E':
        e = nodes.new('ShaderNodeTexImage'); e.image = load_img(f'T_{tex}_E', False); e.label = 'E'
        mul = nodes.new('ShaderNodeValue'); mul.name = 'EmberIntensity'; mul.outputs[0].default_value = 0.0
        links.new(e.outputs['Color'], bs.inputs['Emission Color'])
        links.new(mul.outputs[0], bs.inputs['Emission Strength'])
        textures['E'] = f'Textures/T_{tex}_E.png'
        entry['emissive'] = {'texture': 'E', 'default_intensity_burnt': 0.0, 'suggested_intensity_burning': 6.0}
    if extra == 'A':
        links.new(bc.outputs['Alpha'], bs.inputs['Alpha'])
        try:
            m.surface_render_method = 'DITHERED'
        except Exception:
            pass
        entry['blend_mode'] = 'masked'; entry['opacity_mask'] = 'BC alpha'; entry['opacity_clip'] = .5
    if mname.startswith('MI_Ruin_Thatch'):
        entry['notes'] = 'Atlas: U<0.5 weathered/smoke-stained thatch, U>=0.5 charred thatch.'
    if mname == 'MI_Ruin_Timber':
        entry['notes'] = 'Atlas: U<0.5 deep alligatored char, U>=0.5 scorched oak with char patches.'
    MANIFEST_MATERIALS[mname] = entry
    MATS[mname] = m
    return m


for k in MAT_SPECS:
    make_material(k)

# ------------------------------------------------------------------ raw mesh builder
class MB:
    """Accumulates raw polygons with per-corner UVs, material names and smooth flags."""
    def __init__(self):
        self.v = []; self.f = []; self.uv = []; self.mat = []; self.smooth = []

    def poly(self, pts, uvs, mat, smooth=False):
        base = len(self.v)
        self.v.extend(tuple(p) for p in pts)
        self.f.append(tuple(range(base, base + len(pts))))
        self.uv.append([tuple(u) for u in uvs]); self.mat.append(mat); self.smooth.append(smooth)

    def polys_shared(self, verts, faces, uvs, mat, smooth):
        base = len(self.v)
        self.v.extend(tuple(p) for p in verts)
        for fi, face in enumerate(faces):
            self.f.append(tuple(base + i for i in face)); self.uv.append([tuple(u) for u in uvs[fi]])
            self.mat.append(mat if isinstance(mat, str) else mat[fi]); self.smooth.append(smooth)

    def to_object(self, name, coll):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        names = []
        for m in self.mat:
            if m not in names:
                names.append(m)
        for m in names:
            me.materials.append(MATS[m])
        idx = {m: i for i, m in enumerate(names)}
        me.polygons.foreach_set('material_index', [idx[m] for m in self.mat])
        me.polygons.foreach_set('use_smooth', self.smooth)
        uvl = me.uv_layers.new(name='UVMap')
        flat = [c for face in self.uv for uv in face for c in uv]
        uvl.data.foreach_set('uv', flat)
        me.validate(clean_customdata=False); me.update()
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
        return ob


# ------------------------------------------------------------------ UV mappings
def uv_planar(mode, p, n):
    x, y, z = p
    if mode == 'fb_front':
        return ((x + 9.6) / 19.2, .5 + z / 16.0)
    if mode == 'fb_back':
        return ((x + 9.6) / 19.2, z / 16.0)
    if mode == 'side_west':
        return ((y + 4.8) / 19.2, z / 8.0)
    if mode == 'side_east':
        return (.5 + (y + 4.8) / 19.2, z / 8.0)
    if mode == 'chimney':
        if abs(n[0]) > abs(n[1]):
            return (((y - 1.9) - 5.4 + 9.6) / 19.2, z / 16.0)
        return ((x + 9.6) / 19.2, z / 16.0)
    if mode == 'intplaster':
        h = y if abs(n[0]) > abs(n[1]) else x
        return (h / 2.0, z / 3.5)
    if mode.startswith('floor'):
        uo, vo = {'floor1': (0, 0), 'floor2': (.5, 0), 'floor3': (0, .5), 'floor4': (.5, .5)}[mode]
        return (x / 4.0 + uo, y / 4.0 + vo)
    if mode == 'ash':
        return (x / 2.0, y / 2.0)
    raise ValueError(mode)


def face_normal(pts):
    n = Vector((0, 0, 0))
    for i in range(len(pts)):
        a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
        n.x += (a.y - b.y) * (a.z + b.z); n.y += (a.z - b.z) * (a.x + b.x); n.z += (a.x - b.x) * (a.y + b.y)
    return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))


def cbox(mb, center, dim, mat, mode, chamfer=.02, rot_z=0.0, mapper=None):
    """Chamfered box (6 faces + 12 edge bevels + 8 corner tris), planar-mapped UVs."""
    hx, hy, hz = dim[0] / 2, dim[1] / 2, dim[2] / 2
    c = min(chamfer, hx * .45, hy * .45, hz * .45)
    rot = Matrix.Rotation(rot_z, 3, 'Z'); cen = Vector(center)
    corners = [(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    verts = []
    for sx, sy, sz in corners:
        for ax in range(3):
            p = [sx * (hx - c), sy * (hy - c), sz * (hz - c)]
            p[ax] = (sx, sy, sz)[ax] * (hx, hy, hz)[ax]
            verts.append(cen + rot @ Vector(p))

    def vid(s, ax):
        return corners.index(s) * 3 + ax
    faces = []
    for ax in range(3):
        for sgn in (-1, 1):
            o = [a for a in range(3) if a != ax]
            quad = []
            for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
                s = [0, 0, 0]; s[ax] = sgn; s[o[0]] = a; s[o[1]] = b
                quad.append(vid(tuple(s), ax))
            faces.append(quad)
    for ax in range(3):                       # edges running along ax
        o = [a for a in range(3) if a != ax]
        for a in (-1, 1):
            for b in (-1, 1):
                s0 = [0, 0, 0]; s0[ax] = -1; s0[o[0]] = a; s0[o[1]] = b
                s1 = list(s0); s1[ax] = 1
                faces.append([vid(tuple(s0), o[0]), vid(tuple(s0), o[1]), vid(tuple(s1), o[1]), vid(tuple(s1), o[0])])
    for s in corners:
        faces.append([vid(s, 0), vid(s, 1), vid(s, 2)])
    uvs = []
    for f in faces:
        pts = [verts[i] for i in f]; n = face_normal(pts)
        uvs.append([(mapper or uv_planar)(mode, p, n) for p in pts])
    mb.polys_shared(verts, faces, uvs, mat, False)


# timber atlas halves
CHAR, SCORCH = 0.0, 0.5


def profile_beam(mb, a, b, w, d, up=(0, 0, 1), half=CHAR, char=0.0, seed=0, seg_len=.25,
                 ragged_end=0.0, ragged_start=0.0, sag=0.0, mat='MI_Ruin_Timber', taper=1.0, rp=3):
    """Timber with a rounded-rectangle section; 'char' = depth (m) of burnt-away, uneven surface."""
    a = Vector(a); b = Vector(b); L = (b - a).length
    if L < 1e-4:
        return
    ax = (b - a) / L
    upv = Vector(up) - ax * ax.dot(Vector(up))
    if upv.length < 1e-6:
        upv = Vector((1, 0, 0)) - ax * ax.x
    upv.normalize(); side = ax.cross(upv)
    hw, hd = w / 2, d / 2
    rc = min(hw, hd) * .38
    prof = []
    for (sx, sy), a0 in [((1, 1), 0), ((-1, 1), 90), ((-1, -1), 180), ((1, -1), 270)]:
        cx, cy = sx * (hw - rc), sy * (hd - rc)
        steps = [0, 45, 90] if rp == 3 else ([0, 90] if rp == 2 else [45])
        for k, st in enumerate(steps):
            ang = math.radians(a0 + st)
            rr = rc if rp > 1 else 0.0
            px_ = cx + rr * math.cos(ang) if rp > 1 else sx * hw
            py_ = cy + rr * math.sin(ang) if rp > 1 else sy * hd
            prof.append((px_, py_, 1.0 if st == 45 else .55))
    npf = len(prof)
    # arc length for U
    arc = [0.0]
    for i in range(npf):
        p, q = prof[i], prof[(i + 1) % npf]
        arc.append(arc[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
    per = arc[-1]; uscale = .48 / max(per, .96) * 1.0
    nseg = max(1, math.ceil(L / seg_len))
    rng = random.Random(seed)
    off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    voff = rng.uniform(0, 1)
    rings = []
    for i in range(nseg + 1):
        t = i / nseg
        cen = a + ax * (L * t) - upv * (sag * 4 * t * (1 - t))
        sc = 1.0 + (taper - 1.0) * t
        ring = []
        for k, (px, py, ew) in enumerate(prof):
            pos = cen + side * px * sc + upv * py * sc
            if char > 0:
                nz = noise.noise(pos * 9.0 + off) * .5 + .5
                nz2 = noise.noise(pos * 31.0 + off) * .5 + .5
                depth = char * (.25 + .75 * ew) * (.35 + .9 * nz) + char * .25 * nz2
                inward = (side * px + upv * py)
                if inward.length > 1e-6:
                    pos = pos - inward.normalized() * min(depth, min(hw, hd) * .55)
            if i == nseg and ragged_end > 0:
                pos = pos - ax * ragged_end * rng.random()
            if i == 0 and ragged_start > 0:
                pos = pos + ax * ragged_start * rng.random()
            ring.append(pos)
        rings.append(ring)
    verts = [p for ring in rings for p in ring]
    faces = []; uvs = []
    for i in range(nseg):
        v0 = voff + (L * i / nseg) / 2.0; v1 = voff + (L * (i + 1) / nseg) / 2.0
        for k in range(npf):
            k2 = (k + 1) % npf
            faces.append([i * npf + k, i * npf + k2, (i + 1) * npf + k2, (i + 1) * npf + k])
            u0 = half + .01 + arc[k] * uscale; u1 = half + .01 + arc[k + 1] * uscale
            uvs.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    for cap, ring_i in [(0, 0), (1, nseg)]:
        idx = [ring_i * npf + k for k in range(npf)]
        if cap == 0:
            idx = idx[::-1]
        faces.append(idx)
        uvs.append([(half + .01 + (prof[i % npf][0] + hw) * .45, voff + (prof[i % npf][1] + hd) * .45) for i in
                    ([k for k in range(npf)][::-1] if cap == 0 else range(npf))])
    mb.polys_shared(verts, faces, uvs, mat, True)


def split_beam(mb, a, b, w, d, up, half, char, seed, split_len=.45, gap=.03, **kw):
    a = Vector(a); b = Vector(b); L = (b - a).length; ax = (b - a) / L
    p = b - ax * min(split_len, L * .5)
    profile_beam(mb, a, p + ax * .01, w, d, up, half, char, seed, **kw)
    upv = Vector(up) - ax * ax.dot(Vector(up)); upv.normalize(); side = ax.cross(upv)
    rng = random.Random(seed + 7)
    for s in (-1, 1):
        tip = b + side * s * (gap + rng.uniform(.0, .05)) + upv * rng.uniform(-.03, .03)
        profile_beam(mb, p + side * s * w * .26, tip, w * .46, d * rng.uniform(.8, 1.0), up, half, char * .8,
                     seed + 11 * s, ragged_end=.08, seg_len=.1)


def tube(mb, a, b, r0, r1, mat, half, sides=5, seed=0, vlen=1.0):
    """Tapered polygon tube (thatch reed bundle) with UVs along the stalks."""
    a = Vector(a); b = Vector(b); d = b - a; L = d.length
    rot = d.to_track_quat('Z', 'Y').to_matrix()
    verts = []
    for cen, r in [(a, r0), (b, r1)]:
        for i in range(sides):
            ang = i * math.tau / sides
            verts.append(cen + rot @ Vector((r * math.cos(ang), r * math.sin(ang), 0)))
    rng = random.Random(seed); voff = rng.random()
    faces = []; uvs = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append([i, j, j + sides, i + sides])
        u0 = half + .01 + .48 * i / sides; u1 = half + .01 + .48 * (i + 1) / sides
        uvs.append([(u0, voff), (u1, voff), (u1, voff + L / vlen), (u0, voff + L / vlen)])
    faces.append(list(range(sides))[::-1]); uvs.append([(half + .25, voff)] * sides)
    faces.append([sides + i for i in range(sides)]); uvs.append([(half + .25, voff + L / vlen)] * sides)
    mb.polys_shared(verts, faces, uvs, mat, True)


def slab(mb, W, H, n, ztop, thick, mat, wall=False):
    """Closed thin slab over [0,W]x[0,H] (n x n cells) with UV 0-1; ztop(u,v) gives the top offset.
    wall=True lays it in the XZ plane (thickness along +Y, visible face toward -Y)."""
    def P(i, j, top):
        u, v = i / n, j / n
        h = ztop(u * W, v * H) if top else -thick
        return (u * W, -h, v * H) if wall else (u * W, v * H, h)
    for i in range(n):
        for j in range(n):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            uvq = [(a / n, b / n) for a, b in q]
            mb.poly([P(a, b, 1) for a, b in q], uvq, mat, True)
            mb.poly([P(a, b, 0) for a, b in q][::-1], uvq[::-1], mat, False)
    for k in range(n):
        for (a0, a1) in [((k, 0), (k + 1, 0)), ((n, k), (n, k + 1)), ((k + 1, n), (k, n)), ((0, k + 1), (0, k))]:
            quad = [P(*a0, 1), P(*a1, 1), P(*a1, 0), P(*a0, 0)]
            mb.poly(quad, [(a0[0] / n, a0[1] / n), (a1[0] / n, a1[1] / n), (a1[0] / n, a1[1] / n), (a0[0] / n, a0[1] / n)], mat, False)


def heightfield(mb, x0, x1, y0, y1, step, zfun, mat, mode='ash', keep=None, base=None):
    nx = max(1, round((x1 - x0) / step)); ny = max(1, round((y1 - y0) / step))
    grid = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny
            grid[i, j] = (x, y, zfun(x, y))
    for i in range(nx):
        for j in range(ny):
            cx = x0 + (x1 - x0) * (i + .5) / nx; cy = y0 + (y1 - y0) * (j + .5) / ny
            if keep and not keep(cx, cy):
                continue
            pts = [grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]]
            mb.poly(pts, [uv_planar(mode, p, (0, 0, 1)) for p in pts], mat, True)


def mound(mb, cx, cy, z0, rx, ry, h, seed, rings=10, segs=28, mat='MI_Ruin_AshEmber'):
    """Irregular ash heap: closed radial height field."""
    off = Vector((seed * 3.7, seed * 1.3, 0))
    pts = {}
    for i in range(rings + 1):
        r = i / rings
        for j in range(segs):
            th = j / segs * math.tau
            edge = 1 + .22 * noise.noise(Vector((math.cos(th) * 1.7, math.sin(th) * 1.7, seed)) + off)
            x = cx + math.cos(th) * rx * r * edge; y = cy + math.sin(th) * ry * r * edge
            bump = noise.noise(Vector((x * 2.3, y * 2.3, seed * .7))) * .5 + noise.noise(Vector((x * 7, y * 7, seed))) * .04
            z = z0 + h * max(0.0, (1 - r * r)) ** 1.3 * (1 + .3 * bump) + (0 if i < rings else -.01)
            pts[i, j] = (x, y, max(z0 - .01, z))
    centre = (cx, cy, z0 + h * (1 + .2 * noise.noise(Vector((cx, cy, seed)))))
    for j in range(segs):
        j2 = (j + 1) % segs
        tri = [centre, pts[1, j], pts[1, j2]]
        mb.poly(tri, [uv_planar('ash', p, (0, 0, 1)) for p in tri], mat, True)
        for i in range(1, rings):
            q = [pts[i, j], pts[i + 1, j], pts[i + 1, j2], pts[i, j2]]
            mb.poly(q, [uv_planar('ash', p, (0, 0, 1)) for p in q], mat, True)
    bottom = [pts[rings, j] for j in range(segs)][::-1]
    mb.poly(bottom, [uv_planar('ash', p, (0, 0, -1)) for p in bottom], mat, False)


# ------------------------------------------------------------------ asset bookkeeping
ASSETS = {}
SOCKETS = {}


def new_collection(name, cls):
    coll = bpy.data.collections.new(name); scene.collection.children.link(coll)
    coll['dink_class'] = cls; coll['dink_path'] = PATH
    coll['dink_source'] = ('Original deterministic Blender geometry and procedural numpy textures; '
                           f'StonebrookRuins/tools/build_ruins.py + make_textures.py seed {R.SEED}; no third-party images or meshes')
    return coll


def finish_asset(name, cls, mb, hulls, pivot=None, notes=None, extra=None):
    coll = new_collection(name, cls)
    ob = mb.to_object(name, coll)
    co = [v.co.copy() for v in ob.data.vertices]
    mn = Vector([min(v[i] for v in co) for i in range(3)]); mx = Vector([max(v[i] for v in co) for i in range(3)])
    if pivot is None:
        if cls in ('kit_floor', 'kit_ceiling'):
            pivot = Vector((mn.x, mn.y, mx.z if cls == 'kit_floor' else mn.z))
        elif cls == 'kit_wall':
            pivot = Vector((mn.x, (mn.y + mx.y) / 2, mn.z))     # same rule as build_stonebrook.py
        else:
            pivot = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    for v in ob.data.vertices:
        v.co -= pivot
    ob.data.update()
    if hulls == 'bbox':
        hulls = [(tuple((mn[i] + mx[i]) / 2 for i in range(3)), tuple(max(.004, mx[i] - mn[i]) for i in range(3)))]
    for i, h in enumerate(hulls, 1):
        if isinstance(h[0], (list, tuple)) and len(h) == 2 and isinstance(h[1], (list, tuple)) and len(h[0]) == 3 and not isinstance(h[0][0], (list, tuple)):
            pos, dim = h
            bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
            for v in bm.verts:
                v.co = Vector((v.co.x * dim[0] + pos[0], v.co.y * dim[1] + pos[1], v.co.z * dim[2] + pos[2])) - pivot
            me = bpy.data.meshes.new(f'UCX_{name}_{i:02d}'); bm.to_mesh(me); bm.free()
        else:
            verts, faces = h
            me = bpy.data.meshes.new(f'UCX_{name}_{i:02d}')
            me.from_pydata([tuple(Vector(v) - pivot) for v in verts], [], faces)
        hob = bpy.data.objects.new(f'UCX_{name}_{i:02d}', me); coll.objects.link(hob)
        hob.hide_render = True; hob.display_type = 'WIRE'
    dims = [mx[i] - mn[i] for i in range(3)]
    ASSETS[name] = {'class': cls, 'dimensions_m': dims, 'materials': [s.material.name for s in ob.material_slots],
                    'fbx': 'Export/' + C.content_path(cls, name, PATH).lstrip('/') + '.fbx', 'blend_collection': name,
                    'pivot_offset_from_construction_m': list(pivot), 'notes': notes or ''}
    if extra:
        ASSETS[name].update(extra)
    return coll, ob, pivot


def add_sockets(coll, pivot, sockets, asset):
    out = []
    for s in sockets:
        e = bpy.data.objects.new(s['socket'], None); coll.objects.link(e)
        e.empty_display_type = 'SINGLE_ARROW'; e.empty_display_size = .6
        loc = Vector(s['cottage_m']) - pivot
        e.location = loc
        n = Vector(s.get('normal', (0, 0, 1)))
        e.rotation_euler = n.to_track_quat('Z', 'Y').to_euler()
        rec = dict(s); rec['local_m'] = [round(c, 4) for c in loc]
        rec['local_ue_cm'] = [round(loc.x * 100, 2), round(-loc.y * 100, 2), round(loc.z * 100, 2)]
        rec['normal_ue'] = [round(n.x, 4), round(-n.y, 4), round(n.z, 4)]
        rec.pop('cottage_m', None)
        out.append(rec)
    SOCKETS[asset] = out
    return out


# ================================================================== the cottage, both states
LAYOUT = R.cottage_layout()


def hole_dist(x, y, holes, salt=0.0):
    """Signed distance (m) to the nearest burnt opening, with ragged noisy edges (<0 inside)."""
    best = 9e9; rim = 0
    for (hx, hy, r, rimw) in holes:
        dx, dy = x - hx, y - hy
        ang = math.atan2(dy, dx)
        rr = r * (1 + .28 * noise.noise(Vector((math.cos(ang) * 1.6 + hx, math.sin(ang) * 1.6 + hy, salt)))
                  + .12 * noise.noise(Vector((x * 4, y * 4, salt + 3))))
        d = math.hypot(dx, dy) - rr
        if d < best:
            best, rim = d, rimw
    return best, rim


def roof_z(y):
    """Top surface of the intact thatch base (original roof panel top)."""
    return 3.5 + 3.75 * (1 - abs(y) / 5.0)


def thatch_mass(mb, holes, rng, norm_f, norm_b):
    """Burnt roof (realism pass 2): the surviving thatch as one charred, matted, sagging mass
    instead of discrete reed bundles; ragged collapsed edges with loose straw hanging into the
    openings; exposed (charred, broken) hazel wattle under the openings.  Returns clump count."""
    step = .16
    nx = round(18.8 / step); ny = round(5.12 / step)   # keeps the intact envelope (±5.27 m with the thatch thickness)
    seen_strands = 0; clumps = 0
    for side, nrm in [(-1, norm_f), (1, norm_b)]:
        def cell_xy(i, j):
            return -9.4 + (i + .5) * step, side * (j + .5) * 5.12 / ny
        keep = {}
        for i in range(nx):
            for j in range(ny):
                x, y = cell_xy(i, j)
                keep[i, j] = hole_dist(x, y, holes, 11)[0] > 0
        edge = {}
        for i in range(nx + 1):
            for j in range(ny + 1):
                cells = [keep.get((i + di, j + dj)) for di in (-1, 0) for dj in (-1, 0)]
                edge[i, j] = any(c is False for c in cells)

        def vtx(i, j, top):
            x = -9.4 + i * step; y = side * j * 5.12 / ny
            ay = abs(y)
            base = 3.5 + 3.75 * (1 - min(ay, 5.0) / 5.0) - .75 * max(0.0, ay - 5.0)
            d = hole_dist(x, y, holes, 11)[0]
            sag = .045 * math.sin(math.pi * (x + 9.0) / .6) ** 2 + .16 * max(0.0, 1 - d / 1.5) + .05 * math.sin(math.pi * min(ay, 5) / 5)
            clump = .07 * noise.noise(Vector((x * 1.3, y * 1.3, 2.0))) + .03 * noise.noise(Vector((x * 4.1, y * 4.1, 5.0)))
            p = Vector((x, y, base))
            if edge[i, j] and 0 < j < ny:
                jr = random.Random(i * 7919 + j * 104729 + side)
                p += Vector((jr.uniform(-.06, .06), jr.uniform(-.06, .06), 0))
                sag += .1 + jr.uniform(0, .12)
            if top:
                return p + nrm * (.27 + clump - sag)
            return p - nrm * (.12 + sag * .7)

        def thalf(x, y):
            d, rim = hole_dist(x, y, holes, 11)
            charred = d < rim * 1.7 or noise.noise(Vector((x * .55, y * .55, 8.0))) > .2
            return .5 if charred else 0.0

        V = {}
        for i in range(nx + 1):
            for j in range(ny + 1):
                V[i, j, 1] = vtx(i, j, True); V[i, j, 0] = vtx(i, j, False)
        for (i, j), kp in keep.items():
            if not kp:
                continue
            x, y = cell_xy(i, j)
            h = thalf(x, y)
            u0 = h + .01 + (i % 6) * .072
            v0 = j * 5.12 / ny; v1 = (j + 1) * 5.12 / ny
            top = [V[i, j, 1], V[i + 1, j, 1], V[i + 1, j + 1, 1], V[i, j + 1, 1]]
            mb.poly(top, [(u0, v0), (u0 + .072, v0), (u0 + .072, v1), (u0, v1)], 'MI_Ruin_Thatch', True)
            bot = [V[i, j, 0], V[i, j + 1, 0], V[i + 1, j + 1, 0], V[i + 1, j, 0]]
            mb.poly(bot, [(.51 + (i % 6) * .072, v0), (.51 + (i % 6) * .072, v1), (.58 + (i % 6) * .072, v1), (.58 + (i % 6) * .072, v0)], 'MI_Ruin_Thatch', True)
            for (di, dj), (a0, a1) in [((-1, 0), ((i, j), (i, j + 1))), ((1, 0), ((i + 1, j + 1), (i + 1, j))),
                                       ((0, -1), ((i + 1, j), (i, j))), ((0, 1), ((i, j + 1), (i + 1, j + 1)))]:
                nb = keep.get((i + di, j + dj))
                if nb is None and dj == -1 and j == 0:
                    continue                               # ridge: the other slope continues the mass
                if nb is None or not nb:
                    wall = [V[a0[0], a0[1], 1], V[a1[0], a1[1], 1], V[a1[0], a1[1], 0], V[a0[0], a0[1], 0]]
                    mb.poly(wall, [(.52, 0), (.6, 0), (.6, .4), (.52, .4)], 'MI_Ruin_Thatch', True)
                    # loose, charred straw hanging off torn edges into the openings
                    if nb is not None and rng.random() < .75:
                        pa = (V[a0[0], a0[1], 1] + V[a1[0], a1[1], 1]) * .5
                        cx, cy = cell_xy(i + di, j + dj)
                        inward = Vector((cx, cy, 0)) - Vector((pa.x, pa.y, 0))
                        if inward.length > 1e-6:
                            inward.normalize()
                        for _k in range(rng.randint(2, 4)):
                            L = rng.uniform(.18, .5)
                            st = pa + Vector((rng.uniform(-.06, .06), rng.uniform(-.06, .06), rng.uniform(-.12, 0)))
                            tip = st + inward * L * rng.uniform(.4, .9) + Vector((rng.uniform(-.08, .08), rng.uniform(-.08, .08), -L * rng.uniform(.4, .9)))
                            tube(mb, st, tip, .012, .004, 'MI_Ruin_Thatch', .5, 3, seed=rng.randint(0, 99999))
                            seen_strands += 1
        # matted clumps lying on the surviving thatch (break up the regular surface)
        for _k in range(170):
            i, j = rng.randrange(5, nx - 5), rng.randrange(2, ny - 5)
            if not keep[i, j]:
                continue
            p = (V[i, j, 1] + V[i + 1, j + 1, 1]) * .5
            ang = rng.uniform(-.6, .6)
            dirv = Vector((math.sin(ang), side * math.cos(ang) * .8, -.6 * math.cos(ang))).normalized()
            L = rng.uniform(.35, .9)
            x, y = p.x, p.y
            tube(mb, p - dirv * L * .5 + nrm * .03, p + dirv * L * .5 + nrm * .01, rng.uniform(.05, .09), rng.uniform(.03, .06),
                 'MI_Ruin_Thatch', thalf(x, y), 5, seed=rng.randint(0, 99999))
            clumps += 1
        # charred hazel wattle under the openings, woven over and under the battens
        for j in range(int(5.0 / .11)):
            y = side * (j + .5) * .11
            p_of = lambda xx, w: Vector((xx, y, roof_z(y))) - nrm * (.115 - w)
            xs_in = [x for x in [-9.0 + k * .6 for k in range(31)]
                     if hole_dist(x + .3, y, holes, 11)[0] < .3]
            for x in xs_in:
                if rng.random() < .3:
                    continue                                  # burnt through
                w0 = .012 if (j + int((x + 9) / .6)) % 2 else -.012
                profile_beam(mb, p_of(x, w0), p_of(x + .6, -w0), .022, .022, nrm, CHAR, .004, rng.randint(0, 99999),
                             seg_len=.6, rp=1, ragged_end=.1 if rng.random() < .3 else 0)
    return clumps


def build_cottage(state):
    burnt = state == 'burnt'
    rng = random.Random(R.SEED + (1 if burnt else 2))
    mb = MB()
    holes = R.roof_holes(state)
    if burnt:
        # Remaster addition (not visible from the 1997 viewpoint): the back slope burned too.
        holes += [(-2.6, 2.4, 1.35, 1.2), (4.2, 1.6, .9, .9)]
    scorches = R.roof_scorches(state)
    FB = 'MI_Ruin_FacadeFrontBack' if burnt else 'MI_Ruin_FacadeFrontBack_Burning'
    SD = 'MI_Ruin_FacadeSides' if burnt else 'MI_Ruin_FacadeSides_Burning'
    tim_main = CHAR if burnt else SCORCH
    char_main = .022 if burnt else .006

    def near_fire(x, y, extra=1.2):
        d, _ = hole_dist(x, y, holes) if holes else (9, 0)
        if d < extra:
            return True
        return any(math.hypot(x - sx, y - sy) < sr + .6 for sx, sy, sr in scorches)

    # --- sill and masonry
    cbox(mb, (0, 0, .11), (18, 9, .22), FB, 'fb_front', .02)
    # random-bond rubble (realism pass 2) inside the intact wall envelope, on a recessed lime-mortar core
    RL = R.rubble_layout()
    srng = random.Random(R.SEED + 91)
    for key, fy, mode, mat in [('front', -4.5, 'fb_front', FB), ('back', 4.5, 'fb_back', FB),
                               ('west', -9.0, 'side_west', SD), ('east', 9.0, 'side_east', SD)]:
        side = key in ('west', 'east')
        out_sign = (-1 if fy < 0 else 1)
        segs = [(-9.0, R.DOOR_X - .85), (R.DOOR_X + .85, 9.0)] if key == 'front' else ([(-4.5, 4.5)] if side else [(-9.0, 9.0)])
        for (a0, a1) in segs:
            c, L_ = (a0 + a1) / 2, a1 - a0
            if side:
                cbox(mb, (fy, c, .69), (.40, L_, 1.12), mat, mode, .01)
            else:
                cbox(mb, (c, fy, .69), (L_, .40, 1.12), mat, mode, .01)
        for (c, z, w, h, proud, _s) in RL[key]:
            tmp = MB()
            if side:
                cbox(tmp, (fy + out_sign * proud, c, z), (.5, w, h), mat, mode, min(.035, h * .2))
            else:
                cbox(tmp, (c, fy + out_sign * proud, z), (w, .5, h), mat, mode, min(.035, h * .2))
            spall = burnt and R.spall_mask(key, c, z) and srng.random() < .45
            jit = []
            for v in tmp.v:
                v = list(v)
                ax = 0 if not side else 1; dax = 1 if not side else 0      # along-wall axis, depth axis
                v[ax] += srng.uniform(-.09, .09) * w
                v[2] += srng.uniform(-.1, .1) * h
                outward = (v[dax] - (fy if not side else fy)) * out_sign
                if outward > .2:                                           # front face: bulge / dish
                    v[dax] += out_sign * srng.uniform(-.012, .03)
                    if spall:
                        v[dax] -= out_sign * srng.uniform(.02, .05)        # heat-spalled face
                jit.append(tuple(v))
            tmp.v = jit
            base = len(mb.v)
            mb.v.extend(tmp.v)
            for f, uv, m_, sm in zip(tmp.f, tmp.uv, tmp.mat, tmp.smooth):
                mb.f.append(tuple(base + i for i in f)); mb.uv.append(uv); mb.mat.append(m_); mb.smooth.append(sm)
    # --- limewashed panels
    for key, fy in [('front', -4.5), ('back', 4.5)]:
        for i in range(12):
            x = -8.25 + i * 1.5
            if key == 'front' and abs(x - R.DOOR_X) < 1.5:
                continue
            cbox(mb, (x, fy, 2.40), (1.40, .25, 2.35), FB, 'fb_' + key, .018)
    for fx, mode in [(-9, 'side_west'), (9, 'side_east')]:
        cbox(mb, (fx, 0, 2.4), (.25, 9, 2.3), SD, mode, .012)
        # plastered gable triangle (prism)
        tri = [(fx - .13, -4.5, 3.5), (fx - .13, 4.5, 3.5), (fx - .13, 0, 7.0)]
        tri2 = [(fx + .13, -4.5, 3.5), (fx + .13, 4.5, 3.5), (fx + .13, 0, 7.0)]
        for poly in [tri, tri2[::-1], [tri[0], tri[1], tri2[1], tri2[0]], [tri[1], tri[2], tri2[2], tri2[1]], [tri[2], tri[0], tri2[0], tri2[2]]]:
            n = face_normal(poly)
            mb.poly(poly, [uv_planar(mode, p, n) for p in poly], SD)
    # --- timber frame
    seed = 100
    for key, fy in [('front', -4.5), ('back', 4.5)]:
        for i in range(13):
            x = -9 + i * 1.5
            if key == 'front' and abs(x - R.DOOR_X) < .72:
                continue
            seed += 1
            hot = burnt or near_fire(x, -3 if key == 'front' else 3)
            profile_beam(mb, (x, fy - .04, 1.14), (x, fy - .04, 3.64), .17, .38, (0, 1, 0),
                         CHAR if hot else SCORCH, char_main if hot else .006, seed)
        for z in [1.24, 3.53]:
            segs = [(-9, 9)]
            if key == 'front' and z < 2.5:
                segs = [(-9, R.DOOR_X - .85), (R.DOOR_X + .85, 9)]
            for (x0, x1) in segs:
                seed += 1
                if burnt and z > 3 and key == 'front':
                    # the front wall plate checked and split where the roof fell in
                    split_beam(mb, (x0, fy, z), (x1, fy, z), .38, .20, (0, 0, 1), CHAR, char_main * 1.3, seed, split_len=.6)
                else:
                    profile_beam(mb, (x0, fy, z), (x1, fy, z), .38, .20, (0, 0, 1), tim_main, char_main, seed)
    for fx in [-9, 9]:
        for i in range(7):
            seed += 1
            profile_beam(mb, (fx, -4.5 + i * 1.5, 1.14), (fx, -4.5 + i * 1.5, 3.64), .38, .17, (1, 0, 0), tim_main, char_main, seed)
        for z in [1.24, 3.53]:
            seed += 1
            profile_beam(mb, (fx, -4.5, z), (fx, 4.5, z), .38, .20, (0, 0, 1), tim_main, char_main, seed)
        seed += 1
        profile_beam(mb, (fx, 0, 3.5), (fx, 0, 6.9), .22, .22, (1, 0, 0), CHAR, char_main * 1.2, seed)
        profile_beam(mb, (fx, -4.5, 3.55), (fx, 0, 7.0), .20, .20, (1, 0, 0), CHAR, char_main * 1.2, seed + 1)
        profile_beam(mb, (fx, 0, 7.0), (fx, 4.5, 3.55), .20, .20, (1, 0, 0), CHAR, char_main * 1.2, seed + 2)
        seed += 3
    # --- windows: dark recess, charred frames and shutters
    for x in R.WINDOWS_X:
        for y in [-4.72, 4.72]:
            front = y < 0
            hot = burnt or near_fire(x, -3 if front else 3, 1.8)
            half = CHAR if hot else SCORCH; ch = char_main if hot else .006
            cbox(mb, (x, y + (.03 if front else -.03), 2.28), (1.15, .11, 1.25), 'MI_Ruin_Timber', 'dark', .01,
                 mapper=lambda m, p, n: (.02 + (p[0] % 1.0) * .45, p[2] / 2.0))      # charred, burnt-out window void
            for dx in [-.61, .61]:
                seed += 1; profile_beam(mb, (x + dx, y - .06 * (1 if front else -1), 1.58), (x + dx, y - .06 * (1 if front else -1), 2.98), .11, .18, (0, 1, 0), half, ch, seed)
            for z in [1.61, 2.95]:
                seed += 1; profile_beam(mb, (x - .675, y - .06 * (1 if front else -1), z), (x + .675, y - .06 * (1 if front else -1), z), .22, .12, (0, 0, 1), half, ch, seed)
            seed += 1; profile_beam(mb, (x, y - .07, 1.68), (x, y - .07, 2.88), .055, .09, (0, 1, 0), half, ch * .5, seed)
            seed += 1; profile_beam(mb, (x - .6, y - .07, 2.28), (x + .6, y - .07, 2.28), .09, .055, (0, 0, 1), half, ch * .5, seed)
            for side in [-1, 1]:
                for k in range(3):
                    sx = x + side * (.80 + k * .14)
                    top = 2.865
                    if burnt:
                        roll = rng.random()
                        if roll < .3:
                            continue                       # burnt away / fallen
                        top = 1.695 + 1.17 * rng.uniform(.45, 1.0)
                    seed += 1
                    profile_beam(mb, (sx, y, 1.695), (sx, y, top), .13, .08, (0, 1, 0), half, ch, seed,
                                 ragged_end=.12 if burnt else 0)
    # --- doorway: frame vented the fire, heavily charred; one jamb split at the head
    dx0 = R.DOOR_X
    seed += 1
    profile_beam(mb, (dx0 - .85, -4.57, 0), (dx0 - .85, -4.57, 2.52), .20, .45, (0, 1, 0), CHAR if burnt else SCORCH, char_main * 1.3, seed)
    seed += 1
    if burnt:
        split_beam(mb, (dx0 + .85, -4.57, 0), (dx0 + .85, -4.57, 2.52), .20, .45, (0, 1, 0), CHAR, char_main * 1.3, seed, split_len=.7, gap=.02)
    else:
        profile_beam(mb, (dx0 + .85, -4.57, 0), (dx0 + .85, -4.57, 2.52), .20, .45, (0, 1, 0), SCORCH, .008, seed)
    seed += 1
    profile_beam(mb, (dx0 - .96, -4.57, 2.62), (dx0 + .96, -4.57, 2.62), .45, .22, (0, 0, 1), CHAR if burnt else SCORCH,
                 char_main * 1.3, seed, sag=.035 if burnt else 0)
    cbox(mb, (dx0, -4.5, 3.13), (1.55, .25, .80), FB, 'fb_front', .012)
    # --- roof structure: rafters, ridge, battens (hidden under thatch where it survived)
    k = 3.75 / 5.0
    norm_f = Vector((0, -k, 1)).normalized(); norm_b = Vector((0, k, 1)).normalized()
    big_holes = [h for h in holes if h[2] > 1.0]
    fallen = []
    xs = [round(-9.0 + i * .6, 3) for i in range(31)]
    for side, nrm in [(-1, norm_f), (1, norm_b)]:
        cosn = norm_f.z
        for x in xs:
            seed += 1
            # rafter centreline 0.11 m (perpendicular) below the thatch base underside (base 0.12 thick)
            def rp(y):
                return Vector((x, y, roof_z(y))) - nrm * (.12 + .11)
            ye, yr = side * 4.62, 0.0
            pts_in = [i / 40 for i in range(41) if hole_dist(x, side * 4.62 * (1 - i / 40), big_holes)[0] < -.25] if big_holes else []
            hot = burnt or near_fire(x, side * 2.5, 1.0)
            half = CHAR if hot else SCORCH; ch = char_main * (1.4 if hot else 1)
            if burnt and pts_in:
                t0, t1 = min(pts_in), max(pts_in)
                # lower piece from the wall plate to the hole edge, upper piece hangs from the ridge
                if t0 > .12:
                    profile_beam(mb, rp(ye), rp(ye * (1 - t0 + .04)), .12, .16, nrm, CHAR, ch, seed, ragged_end=.18, seg_len=.2)
                if t1 < .9 and rng.random() < .7:
                    profile_beam(mb, rp(ye * (1 - t1 - .04)), rp(0), .12, .16, nrm, CHAR, ch, seed + 3, ragged_start=.18, seg_len=.2)
                if rng.random() < .55:
                    fallen.append((x, side * 4.62 * (1 - (t0 + t1) / 2), (t1 - t0) * 4.62))
            else:
                profile_beam(mb, rp(ye), rp(0), .12, .16, nrm, half, ch, seed, seg_len=.25)
    seed += 1
    profile_beam(mb, (-9.3, 0, 7.25 - .12 - .14), (9.3, 0, 7.25 - .12 - .14), .16, .22, (0, 0, 1), CHAR if burnt else SCORCH, char_main, seed, seg_len=.3)
    for side, nrm in [(-1, norm_f), (1, norm_b)]:
        for j in range(14):
            t = (j + .5) / 14; y = side * 5 * (1 - t)
            p_of = lambda xx: Vector((xx, y, roof_z(y))) - nrm * (.12 + .02)
            # split the batten where it crosses openings
            xs_keep = []
            cur = None
            for i in range(95):
                xx = -9.35 + i * .2
                inside = holes and hole_dist(xx, y, holes, 7)[0] < -.05
                if not inside and cur is None:
                    cur = xx
                if inside and cur is not None:
                    xs_keep.append((cur, xx - .05)); cur = None
            if cur is not None:
                xs_keep.append((cur, 9.35))
            for (x0, x1) in xs_keep:
                if x1 - x0 < .15:
                    continue
                seed += 1
                hot = burnt or near_fire((x0 + x1) / 2, y)
                profile_beam(mb, p_of(x0), p_of(x1), .05, .03, nrm, CHAR if hot else SCORCH, .004 if hot else 0, seed,
                             seg_len=1.2, rp=1, ragged_end=.06 if x1 < 9.3 else 0, ragged_start=.06 if x0 > -9.3 else 0)
    if burnt:
        kept = thatch_mass(mb, holes, rng, norm_f, norm_b)
    else:
        # --- thatch base layer with burnt-through openings (12 cm thick, edges walled)
        step = .25
        for side, nrm in [(-1, norm_f), (1, norm_b)]:
            nx = int(18.8 / step); ny = int(5.0 / step)
            keep = {}
            for i in range(nx):
                for j in range(ny):
                    cx = -9.4 + (i + .5) * step; cy = side * 5 * (1 - (j + .5) / ny)
                    d, rim = hole_dist(cx, cy, holes, 11) if holes else (9, 0)
                    keep[i, j] = (d > 0, d < rim * .7)

            def P(i, j, below):
                x = -9.4 + i * step; y = side * 5 * (1 - j / ny)
                p = Vector((x, y, roof_z(y)))
                return p - nrm * .12 if below else p
            for (i, j), (kp, ch) in keep.items():
                if not kp:
                    continue
                top = [P(i, j, 0), P(i + 1, j, 0), P(i + 1, j + 1, 0), P(i, j + 1, 0)]
                bot = [P(i, j, 1), P(i, j + 1, 1), P(i + 1, j + 1, 1), P(i + 1, j, 1)]
                hu = .5 if (ch or burnt) else 0.0
                mb.poly(top, [(hu + .01 + .48 * (q.x % 1.0) * .5 / .5 * .5, q.y * .5) for q in top], 'MI_Ruin_Thatch')
                mb.poly(bot, [(.51 + .48 * ((q.x % 1.0)) * .5, q.y * .5) for q in bot], 'MI_Ruin_Thatch')
                for (di, dj), (a0, a1) in [((-1, 0), ((i, j), (i, j + 1))), ((1, 0), ((i + 1, j + 1), (i + 1, j))),
                                           ((0, -1), ((i + 1, j), (i, j))), ((0, 1), ((i, j + 1), (i + 1, j + 1)))]:
                    nb = keep.get((i + di, j + dj))
                    if nb is None or not nb[0]:
                        wall = [P(*a0, 0), P(*a1, 0), P(*a1, 1), P(*a0, 1)]
                        mb.poly(wall, [(.52, 0), (.6, 0), (.6, .12), (.52, .12)], 'MI_Ruin_Thatch')
        # --- reed bundles (exact intact layout), burnt away / charred / shortened around openings
        kept = 0
        for (side, row, col, a, b) in LAYOUT['bundles']:
            mx = (a[0] + b[0]) / 2; my = (a[1] + b[1]) / 2
            d, rim = hole_dist(mx, my, holes, 11) if holes else (9, 0)
            a = Vector(a); b = Vector(b)
            half = 0.0; r0, r1 = .10, .09
            if d < .08:
                continue
            if d < rim:
                half = .5
                f = d / rim
                b = a + (b - a) * (.45 + .45 * f + .1 * rng.random())
                sink = (1 - f) * .07
                a.z -= sink; b.z -= sink
                r0, r1 = .085, .06
            elif any(math.hypot(mx - sx, my - sy) < sr * (.75 + .5 * rng.random()) for sx, sy, sr in scorches):
                half = .5
            elif burnt and (rng.random() < .10 or d < rim * 1.7):
                half = .5
            tube(mb, a, b, r0, r1, 'MI_Ruin_Thatch', half, 5, seed=row * 100 + col + side * 7)
            kept += 1
        # ridge cap
        for xr in [-9.2 + i * .28 for i in range(67)]:
            d, rim = hole_dist(xr, 0, holes, 11) if holes else (9, 0)
            if d < .3:
                continue
            hu = .5 if (d < rim or (burnt and rng.random() < .15)) else 0.0
            seed += 1
            tube(mb, (xr - .15, 0, 7.25 + .11), (xr + .15, 0, 7.25 + .11), .17, .16, 'MI_Ruin_Thatch', hu, 6, seed, vlen=1.0)
            profile_beam(mb, (xr, -.45, 7.0), (xr, .45, 7.0), .035, .035, (0, 0, 1), CHAR if hu else SCORCH, 0, seed + 1, seg_len=1, rp=1)
    # --- chimney (survived, soot-crowned)
    for course in range(12):
        for c in range(3):
            cbox(mb, (-5.8 + c * .38, 1.9, 4.55 + course * .27), (.36, .9, .25), FB, 'chimney', .025)
    cbox(mb, (-5.4, 1.9, 7.78), (1.42, 1.13, .22), FB, 'chimney', .025)
    cbox(mb, (-5.4, 1.9, 7.90), (.75, .55, .06), FB, 'chimney', .01)
    # --- floor ash, collapse mounds and fallen timber inside the walls
    def floor_z(x, y):
        z = .22 + .012 + .02 * (noise.noise(Vector((x * 1.3, y * 1.3, 4.0))) * .5 + .5)
        return z + .015 * noise.noise(Vector((x * 6, y * 6, 2.0)))
    heightfield(mb, -8.7, 8.7, -4.2, 4.2, .3, floor_z, 'MI_Ruin_AshEmber')
    debris_sockets = []
    if burnt:
        for n_, (hx, hy, r, rim) in enumerate(holes):
            mx_ = max(-7.8, min(7.8, hx)); my_ = max(-3.3, min(3.3, hy))
            h = .25 + .22 * min(r, 2.0)
            mound(mb, mx_, my_, .22, r * .95 + .3, r * .7 + .3, h, seed=n_ + 1)
            debris_sockets.append((mx_, my_, .22 + h))
            for q in range(int(4 + r * 6)):
                ang = rng.uniform(0, math.tau); rr = rng.uniform(0, r * .8)
                cx, cy = mx_ + math.cos(ang) * rr, my_ + math.sin(ang) * rr * .7
                ln = rng.uniform(.4, .8); th = rng.uniform(0, math.tau)
                pa = Vector((cx - math.cos(th) * ln / 2, cy - math.sin(th) * ln / 2, .22 + h * rng.uniform(.3, .8)))
                pb = Vector((cx + math.cos(th) * ln / 2, cy + math.sin(th) * ln / 2, .22 + h * rng.uniform(.1, .6)))
                seed += 1
                tube(mb, pa, pb, .07, .05, 'MI_Ruin_Thatch', .5, 5, seed)
        for (fx_, fy_, ln) in fallen:
            cx = max(-8.2, min(8.2, fx_ + rng.uniform(-.3, .3))); cy = max(-3.8, min(3.8, fy_ * .7))
            th = rng.uniform(-.6, .6) + (math.pi / 2)
            L = max(.8, min(2.6, ln + rng.uniform(.2, .8)))
            pa = Vector((cx - math.cos(th) * L / 2, cy - math.sin(th) * L / 2, .30))
            pb = Vector((cx + math.cos(th) * L / 2, cy + math.sin(th) * L / 2, .30 + rng.uniform(.15, .9)))
            seed += 1
            if rng.random() < .4:
                split_beam(mb, pa, pb, .12, .16, (0, 0, 1), CHAR, .03, seed, split_len=.35)
            else:
                profile_beam(mb, pa, pb, .12, .16, (0, 0, 1), CHAR, .03, seed, ragged_end=.2, ragged_start=.15, seg_len=.2)
    return mb, kept, holes, scorches, debris_sockets


for state in ['burning', 'burnt']:
    name = f'SM_Cottage_Stonebrook_{state.capitalize()}_01'
    mb, kept, holes, scorches, debris = build_cottage(state)
    # Intact hulls are stored in that asset's local frame; we subtract the same pivot from our geometry.
    coll, ob, pivot = finish_asset(name, 'building', mb, [], pivot=COTTAGE_PIVOT.copy(),
                                   notes=f'{state} state of SM_Cottage_Stonebrook_01; {kept} reed bundles; {len(holes)} roof openings',
                                   extra={'state': state, 'vision': 1 if state == 'burning' else 2,
                                          'roof_openings_m': [[round(c, 3) for c in h] for h in holes],
                                          'replaces': 'SM_Cottage_Stonebrook_01 (same pivot, same collision hulls)'})
    # identical collision: the intact hulls, renamed to this asset
    for i, (_n, verts, faces) in enumerate(ORIG_HULLS, 1):
        me = bpy.data.meshes.new(f'UCX_{name}_{i:02d}')
        me.from_pydata(verts, [], faces)
        h = bpy.data.objects.new(f'UCX_{name}_{i:02d}', me); coll.objects.link(h)
        h.hide_render = True; h.display_type = 'WIRE'
    socks = []
    if state == 'burning':
        n_f = 0; n_s = 0
        for e in R.exterior_effects():
            if e['vision'] != 1:
                continue
            kind = R.EFFECT_KIND[e['seq']]
            x, y, z = e['cottage_m']; nrm = Vector(e['normal'])
            p = Vector((x, y, z)) + nrm * (.18 if e['surface'].startswith('roof') else .08)
            if kind == 'smoke_vent':
                n_s += 1; sname = f'SOCKET_Smoke_{n_s:02d}'
            else:
                n_f += 1; sname = f'SOCKET_Fire_{n_f:02d}'
            socks.append({'socket': sname, 'origin': e['id'], 'effect': kind, 'original_sequence': e['seq'],
                          'original_sequence_path': R.SEQ_NAMES[e['seq']], 'original_frame': e['frame'],
                          'source_pixel': e['source_pixel'], 'surface': e['surface'],
                          'cottage_m': tuple(p), 'normal': tuple(nrm),
                          'scale_hint': round(R.FRAMES[(e['seq'], e['frame'])][0] / 80.0, 2)})
        # chimney draws smoke while the house burns (remaster addition)
        socks.append({'socket': 'SOCKET_Smoke_Chimney', 'origin': None, 'effect': 'smoke_column', 'original_sequence': None,
                      'surface': 'chimney', 'cottage_m': (-5.4, 1.9, 8.0), 'normal': (0, 0, 1), 'scale_hint': 1.0,
                      'remaster_addition': True})
        for i, (dx_, dz_) in enumerate([(-.45, 1.2), (.4, 1.9)], 1):
            socks.append({'socket': f'SOCKET_Fire_Door_{i:02d}', 'origin': None, 'effect': 'flame_medium',
                          'original_sequence': None, 'surface': 'doorway_interior', 'cottage_m': (R.DOOR_X + dx_, -3.9, dz_),
                          'normal': (0, -1, 0), 'scale_hint': .8, 'remaster_addition': True,
                          'why': 'fire visible through the open doorway; interior is burning (SCR_001 vision 1)'})
    else:
        for i, (x, y, z) in enumerate(debris, 1):
            socks.append({'socket': f'SOCKET_Smoulder_{i:02d}', 'origin': None, 'effect': 'smoulder_wisp',
                          'original_sequence': None, 'surface': 'debris', 'cottage_m': (x, y, z), 'normal': (0, 0, 1),
                          'scale_hint': .5, 'optional': True, 'default_enabled': False,
                          'why': 'vision 2 shows no fire in 1997; enable only for an immediately-after variant'})
    add_sockets(coll, pivot, socks, name)

# ================================================================== loose exterior pieces
# fallen door: board-and-ledge oak door, burnt from its top, lying face up
mb = MB(); rng = random.Random(R.SEED + 50)
W, H = 1.35, 2.30
for i in range(6):
    x = -W / 2 + (i + .5) * W / 6
    top = H / 2 - (rng.uniform(.15, .55) if i in (1, 2, 4) else rng.uniform(0, .18))
    bot = -H / 2 + rng.uniform(0, .04)
    if i == 5:
        top = H / 2 - .9                                   # a board burnt through near the latch side
    profile_beam(mb, (x, bot, .065 + .006 * math.sin(i)), (x, top, .065 + .012 * math.sin(i * 1.7)), W / 6 - .006, .05, (0, 0, 1),
                 CHAR if i in (1, 2, 5) else SCORCH, .012, 900 + i, ragged_end=.14, seg_len=.12)
for yl in [-.7, .55]:
    profile_beam(mb, (-W / 2 + .05, yl, .02), (W / 2 - .05, yl, .02), .16, .04, (0, 0, 1), SCORCH, .006, 920 + int(yl * 10), seg_len=.2)
profile_beam(mb, (-W / 2 + .12, -.62, .021), (W / 2 - .15, .46, .021), .13, .04, (0, 0, 1), SCORCH, .006, 930, seg_len=.2)
for yl in [-.7, .42]:                                       # wrought strap hinges, blackened
    profile_beam(mb, (-W / 2 + .02, yl, .093), (.25, yl, .093), .05, .008, (0, 0, 1), CHAR, 0, 940 + int(yl * 10), seg_len=.3)
coll, ob, piv = finish_asset('SM_Door_Cottage_Fallen_01', 'kit_piece', mb, 'bbox',
                             notes='Fallen, top-burnt plank door for the burnt cottage; lies outside the doorway clear of the walk-in path.')

# ash/debris piles
for nm, rx, ry, h, ntim, nth, sd in [('SM_Debris_AshPile_Large_01', 1.25, .95, .45, 9, 26, 61), ('SM_Debris_AshPile_Small_01', .55, .45, .22, 3, 9, 62)]:
    mb = MB(); rng = random.Random(R.SEED + sd)
    mound(mb, 0, 0, 0, rx, ry, h, sd, rings=12, segs=36)
    for q in range(ntim):
        ang = rng.uniform(0, math.tau); rr = rng.uniform(.1, .75)
        cx, cy = math.cos(ang) * rr * rx, math.sin(ang) * rr * ry
        L = rng.uniform(.4, 1.3) * (rx / 1.25 + .3); th = rng.uniform(0, math.tau)
        za = h * (1 - rr * rr) * rng.uniform(.4, .9) + .04
        pa = Vector((cx - math.cos(th) * L / 2, cy - math.sin(th) * L / 2, za))
        pb = Vector((cx + math.cos(th) * L / 2, cy + math.sin(th) * L / 2, max(.04, za + rng.uniform(-.25, .3))))
        w = rng.uniform(.07, .15)
        profile_beam(mb, pa, pb, w, w * rng.uniform(.8, 1.3), (0, 0, 1), CHAR, .02, sd * 100 + q, ragged_end=.15, ragged_start=.1, seg_len=.12)
    for q in range(nth):
        ang = rng.uniform(0, math.tau); rr = rng.uniform(0, .95)
        cx, cy = math.cos(ang) * rr * rx, math.sin(ang) * rr * ry
        L = rng.uniform(.25, .6); th = rng.uniform(0, math.tau)
        z = h * max(0, 1 - rr * rr) ** 1.3 * .8 + .02
        tube(mb, (cx - math.cos(th) * L / 2, cy - math.sin(th) * L / 2, z), (cx + math.cos(th) * L / 2, cy + math.sin(th) * L / 2, z + rng.uniform(-.05, .08)),
             .05, .035, 'MI_Ruin_Thatch', .5, 5, sd * 1000 + q)
    finish_asset(nm, 'kit_piece', mb, [((0, 0, h * .4), (rx * 1.6, ry * 1.6, h * .8))],
                 notes='Ash, charcoal, collapsed thatch and charred timber; ember emissive mask in MI_Ruin_AshEmber (E).')

# ground scorch decals (masked, realism pass 2): four small feathered patches, one texture quadrant each,
# with ash-drift / stubble height relief.  Top surface at z = 0 (kit_floor rule).
for nm, size, quad in [('SM_Decal_Scorch_Ground_3m_01', 3.0, 0), ('SM_Decal_Scorch_Ground_2m_01', 2.0, 1),
                       ('SM_Decal_Scorch_Ground_2m_02', 2.0, 2), ('SM_Decal_Scorch_Ground_1m5_01', 1.5, 3)]:
    mb = MB()
    uo, vo = (quad % 2) * .5, (1 - quad // 2) * .5      # quadrant (row 0 = top of the image = V .5..1)
    def gz(x, y, S=size, q=quad):
        r = math.hypot(x / S - .5, y / S - .5) * 2
        fall = max(0.0, 1 - r)
        drift = noise.noise(Vector((x * 1.6 + q * 7, y * .7, 3.0))) * .5 + .5
        return (.018 * drift * fall + .006 * (noise.noise(Vector((x * 9, y * 9, q))) * .5 + .5)) * min(1.0, fall * 3)
    slab(mb, size, size, 18, gz, .01, 'MI_Ruin_ScorchGround')
    mb.uv = [[(uo + u * .5, vo + v * .5) for (u, v) in face] for face in mb.uv]
    zmax = max(v[2] for v in mb.v)
    mb.v = [(v[0], v[1], v[2] - zmax) for v in mb.v]
    finish_asset(nm, 'kit_floor', mb, 'bbox',
                 notes='Masked, feathered burn patch (singed grass, stubble, partial char, ash drift). Scatter several, '
                       'rotated, 0.3-0.6 cm above the meadow; collision off in layout.')

# ================================================================== the mother's body (SCR_001 vision 1, S001_P34)
with bpy.data.libraries.load(str(KIT / 'Working/MotherRemains_posed.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith('MotherRemains_LOD')]
coll = new_collection('SM_Mother_Remains_Fire_01', 'foliage')   # non-Nanite, open cloth/hair-card surfaces, authored LOD chain
coll['dink_source'] = ('Posed static copy of Characters/SK_Mother.blend (CC0 MakeHuman anatomy + original project wardrobe; '
                       'see Characters/README.md) via StonebrookRuins/tools/pose_mother_remains.py; smoke/blood pass on a copy of its atlas')
for lod, ob in enumerate(sorted(dst.objects, key=lambda o: o.name)):
    ob.name = f'SM_Mother_Remains_Fire_01_LOD{lod}'
    me = ob.data
    names = [m.name if m else '' for m in me.materials]
    remap = [('MI_RuinMother_Hair' if any(k in n for k in ('Hair', 'BrowLash')) else 'MI_RuinMother_Body') for n in names]
    order = ['MI_RuinMother_Body', 'MI_RuinMother_Hair']
    idx = [order.index(r) for r in remap]
    mi = [idx[p.material_index] for p in me.polygons]
    me.materials.clear()
    for m in order:
        me.materials.append(MATS[m])
    me.polygons.foreach_set('material_index', mi)
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    coll.objects.link(ob)
lod0 = bpy.data.objects['SM_Mother_Remains_Fire_01_LOD0']
co = [v.co for v in lod0.data.vertices]
mn = Vector([min(c[i] for c in co) for i in range(3)]); mx = Vector([max(c[i] for c in co) for i in range(3)])
bm_ = bmesh.new(); bmesh.ops.create_cube(bm_, size=1.0)
for v in bm_.verts:
    v.co = Vector((v.co.x * (mx.x - mn.x) * .8, v.co.y * (mx.y - mn.y) * .9, (v.co.z + .5) * .25))
hm = bpy.data.meshes.new('UCX_SM_Mother_Remains_Fire_01_LOD0_01'); bm_.to_mesh(hm); bm_.free()
hob = bpy.data.objects.new('UCX_SM_Mother_Remains_Fire_01_LOD0_01', hm); coll.objects.link(hob); hob.hide_render = True; hob.display_type = 'WIRE'
ASSETS['SM_Mother_Remains_Fire_01'] = {'class': 'foliage', 'dimensions_m': list(mx - mn), 'materials': ['MI_RuinMother_Body', 'MI_RuinMother_Hair'],
    'fbx': 'Export/' + C.content_path('foliage', 'SM_Mother_Remains_Fire_01', PATH).lstrip('/') + '.fbx',
    'blend_collection': 'SM_Mother_Remains_Fire_01', 'lods_authored': 'posed copies of SK_Mother LOD1-LOD3 (not decimated)', 'class_note': 'foliage class used for its technical profile (non-Nanite, open surfaces allowed, 3 LODs); it is a static prop',
    'replaces': "S001_P34 seq 355 'people/mom/death-' (vision 1 only)", 'vision': 1,
    'notes': "The mother lies dead face-down in the burning room, as in the 1997 vision-1 sprite. Owner decision: keep the original's grim content."}

# blood pool under her (the 1997 sprite is drawn in a spread of blood)
mb = MB()
slab(mb, 2.0, 2.0, 12, lambda u, v: 0.0, .004, 'MI_RuinInt_Blood')
finish_asset('SM_Decal_Blood_Floor_01', 'kit_floor', mb, 'bbox',
             notes='Masked blood pool + cast-off droplets for S001_P34 (vision 1). Wet glossy centre, drying rim. Collision off.')

# ================================================================== interior (SCR_001) burnt modules
def int_wall(mb, hole_mode=None, rng=None):
    cbox(mb, (1, 0, 1.75), (1.8, .22, 3.5), 'MI_RuinInt_PlasterSoot', 'intplaster', .018)


def wall_timbers(mb, seed, top_char=True):
    for x in [.1, 1.9]:
        profile_beam(mb, (x, 0, 0), (x, 0, 3.5), .20, .30, (0, 1, 0), SCORCH, .006, seed + int(x * 10))
    for z, s in [(.12, 1), (2.2, 2), (3.38, 3)]:
        hot = z > 3 and top_char
        profile_beam(mb, (0, -.045, z), (2, -.045, z), .27, .24, (0, 0, 1), CHAR if hot else SCORCH, .014 if hot else .006, seed + 20 + s)
    profile_beam(mb, (.19, -.17, 2.3), (.82, -.17, 3.29), .12, .08, (0, 1, 0), SCORCH, .006, seed + 30)
    profile_beam(mb, (1.18, -.17, 3.29), (1.81, -.17, 2.3), .12, .08, (0, 1, 0), SCORCH, .006, seed + 31)


mb = MB(); int_wall(mb); wall_timbers(mb, 3000)
finish_asset('SM_Wall_Limewash_Burnt_2m_01', 'kit_wall', mb, [((1, 0, 1.75), (2, .30, 3.5))],
             notes='Burnt twin of SM_Wall_Limewash_2m_01 (same 2.0 x 3.5 m grid footprint and hull).')

mb = MB()
cbox(mb, (1, 0, .55), (2, .22, 1.10), 'MI_RuinInt_PlasterSoot', 'intplaster', .012)
cbox(mb, (1, 0, 3.05), (2, .22, .90), 'MI_RuinInt_PlasterSoot', 'intplaster', .012)
for x in [.25, 1.75]:
    cbox(mb, (x, 0, 1.85), (.50, .22, 1.5), 'MI_RuinInt_PlasterSoot', 'intplaster', .01)
for x in [.1, 1.9]:
    profile_beam(mb, (x, 0, 0), (x, 0, 3.5), .20, .30, (0, 1, 0), SCORCH, .006, 3100 + int(x * 10))
for x in [.50, 1.5]:
    profile_beam(mb, (x, 0, 1.04), (x, 0, 2.66), .12, .36, (0, 1, 0), CHAR, .012, 3110 + int(x * 10))
for z in [1.1, 2.6]:
    profile_beam(mb, (.4, -.02, z), (1.6, -.02, z), .42, .14, (0, 0, 1), CHAR, .012, 3120 + int(z * 10))
profile_beam(mb, (1, 0, 1.15), (1, 0, 2.55), .055, .1, (0, 1, 0), CHAR, .008, 3130, ragged_end=.25)
profile_beam(mb, (.525, 0, 1.85), (1.475, 0, 1.85), .1, .055, (0, 0, 1), CHAR, .008, 3131)
finish_asset('SM_Window_Limewash_Burnt_2m_01', 'kit_wall', mb,
             [((1, 0, .55), (2, .30, 1.1)), ((1, 0, 3.05), (2, .30, .90)), ((.25, 0, 1.85), (.5, .30, 1.5)), ((1.75, 0, 1.85), (.5, .30, 1.5))],
             notes='Burnt twin of SM_Window_Limewash_2m_01; casement mullion burnt short, frame charred.')

mb = MB()
for x in [.625, 3.375]:
    cbox(mb, (x, 0, 1.75), (1.25, .22, 3.5), 'MI_RuinInt_PlasterSoot', 'intplaster', .018)
cbox(mb, (2, 0, 3.0), (1.496, .22, 1.0), 'MI_RuinInt_PlasterSoot', 'intplaster', .018)
for x in [.1, 1.25, 2.75, 3.9]:
    full = x in [.1, 3.9]
    profile_beam(mb, (x, 0, 0), (x, 0, 3.5 if full else 2.5), .18, .32, (0, 1, 0), SCORCH if full else CHAR, .006 if full else .016, 3200 + int(x * 10))
for z in [2.5, 3.38]:
    profile_beam(mb, (0, 0, z), (4, 0, z), .3, .24, (0, 0, 1), CHAR, .016, 3210 + int(z * 10))
finish_asset('SM_Doorway_Limewash_Burnt_4m_01', 'kit_piece', mb,
             [((.625, 0, 1.75), (1.25, .32, 3.5)), ((3.375, 0, 1.75), (1.25, .32, 3.5)), ((2, 0, 3.0), (1.5, .32, 1))],
             pivot=Vector((0, 0, 0)), notes='Burnt twin of SM_Doorway_Limewash_4m_01; the 1.5 m clear opening is unchanged.')

for vi in range(1, 5):
    mb = MB(); rng = random.Random(R.SEED + 300 + vi)
    for i in range(8):
        for j in range(2):
            cx, cy = .125 + i * .25, .5 + j
            cbox(mb, (cx, cy, -.055), (.244, .992, .11), 'MI_RuinInt_FloorAsh', f'floor{vi}', .006)
            for y in [.07 + j, .93 + j]:
                profile_beam(mb, (cx, y, -.002), (cx, y, 0.0), .014, .014, (0, 1, 0), CHAR, 0, 3300 + i * 10 + j, seg_len=.1, rp=1)
    finish_asset(f'SM_Floor_Oak_Burnt_2m_0{vi}', 'kit_floor', mb, [((1, 1, -.07), (2, 2, .14))],
                 notes=f'Burnt twin of SM_Floor_Oak_2m_01, UV variant {vi} of 4 (different 2 m quadrant of the 4 m ash/char sheet).')

for nm, holed in [('SM_Ceiling_Oak_Burnt_2m_01', False), ('SM_Ceiling_Oak_BurntHole_2m_01', True)]:
    mb = MB(); rng = random.Random(R.SEED + (401 if holed else 400))
    for i in range(8):
        x = .125 + i * .25
        if holed and 2 <= i <= 5:
            g0 = .55 + rng.uniform(-.15, .15); g1 = 1.45 + rng.uniform(-.15, .15)
            if i in (3, 4):
                g0 -= .2; g1 += .2
            profile_beam(mb, (x, 0, .10), (x, g0, .10), .247, .2, (0, 0, 1), CHAR, .03, 3400 + i, ragged_end=.25, seg_len=.12)
            profile_beam(mb, (x, g1, .10), (x, 2, .10), .247, .2, (0, 0, 1), CHAR, .03, 3410 + i, ragged_start=.25, seg_len=.12)
        else:
            profile_beam(mb, (x, 0, .10), (x, 2, .10), .25 if i in (0, 7) else .247, .2, (0, 0, 1), CHAR, 0 if i in (0, 7) else .012, 3400 + i, seg_len=.2)
    profile_beam(mb, (1, 0, .05), (1, 2, .05), .16, .10, (0, 0, 1), CHAR, .02, 3420, seg_len=.2, sag=.03 if holed else 0)
    finish_asset(nm, 'kit_ceiling', mb, [((1, 1, .10), (2, 2, .20))] if not holed else
                 [((1, .3, .10), (2, .6, .20)), ((1, 1.7, .10), (2, .6, .20))],
                 notes='Burnt ceiling module; the Hole variant is burnt through between y 0.4-1.6 m (sky/roof shows through).')

# interior decals (closed 4 mm slabs, masked material)
for nm, cls, W_, H_, mat in [('SM_Decal_Scorch_Floor_01', 'kit_floor', 1.5, 1.5, 'MI_RuinInt_ScorchFloor'),
                             ('SM_Decal_Scorch_Wall_01', 'kit_wall', 1.5, 2.0, 'MI_RuinInt_ScorchWall')]:
    mb = MB()
    slab(mb, W_, H_, 12, lambda u, v: 0.0, .004, mat, wall=(cls == 'kit_wall'))
    finish_asset(nm, cls, mb, 'bbox',
                 notes='Masked burn-mark decal mesh replacing the original seq-158 "hole" sprites; place 3 mm proud of the surface, collision off.')

# ------------------------------------------------------------------ LOD chains (3 levels) for every asset
lod_log = {}
for asset in common.find_assets():
    if asset.name == 'SM_Mother_Remains_Fire_01':
        lod_log[asset.name] = [{'action': 'authored', 'why': 'posed copies of the character LOD0-LOD2'}]
        continue
    log = make_lods.make_lods(asset, [.5, .25], force=True)
    asset.refresh()
    lod_log[asset.name] = log

# ------------------------------------------------------------------ outputs
manifest = {'schema': 'dink-stonebrook-art/1', 'units': 'metres; FBX UnitScaleFactor 100 converts to Unreal cm', 'seed': R.SEED,
            'source': 'KIT_StonebrookRuins.blend', 'assets': ASSETS, 'materials': MANIFEST_MATERIALS,
            'intact_cottage': {'asset': 'SM_Cottage_Stonebrook_01', 'dimensions_m': ORIG_DIMS,
                               'bounds_local_m': [list(omn), list(omx)], 'collision_hulls_copied': len(ORIG_HULLS)},
            'lod_generation': lod_log,
            'notes': ['Fire-ruin variants of Dink\'s cottage (SCR_439 vision 1 burning, vision 2 burnt) and burnt SCR_001 modules.',
                      'Cottage variants share the intact cottage pivot and its six UCX hulls exactly, so the walkable/blocked footprint is unchanged.',
                      'The original vision 1/2 hardness maps equal vision 0 (checked: 0 differing pixels for SCR_001 and SCR_439).',
                      'Ruin debris, decals and the fallen door have collision only for the kit contract; layouts set collision false.']}
(KIT / 'ruins_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
(KIT / 'emitter_sockets_draft.json').write_text(json.dumps(SOCKETS, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(KIT / 'KIT_StonebrookRuins.blend'), compress=True)
print('STONEBROOK RUINS: built', len(ASSETS), 'assets')
