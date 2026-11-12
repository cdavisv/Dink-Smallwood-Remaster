"""Model small meadow plants (clover, plantain, daisy, dandelion, dry leaves) and render them top-down as a decal sheet
(albedo, alpha, normal, height, AO) that build_sets stamps into the grass sets.
blender -b -t 4 --python plants_sheet.py"""
import bpy, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'Plants')
os.makedirs(OUT, exist_ok=True)
CELLS = 8
CELL = 0.20            # metres
PX = 1600              # 1 mm per pixel
rng = np.random.default_rng(77)
V, Q, C = [], [], []
nv_total = 0


def srgb(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def add(v, q, c):
    global nv_total
    V.append(v.reshape(-1, 3)); Q.append(q + nv_total); C.append(c.reshape(-1, 3)); nv_total += v.reshape(-1, 3).shape[0]


def leaf(width_fn, length, width, base_col, vein_col, nu=12, nv=7, fold=0.25, arch=(0.5, -0.9), ribs=0, rib_amp=0.0, mark=None, curl=0.0, edge_col=None):
    """returns local verts (nu+1, nv+1, 3) along +X from the origin, and colours"""
    u = np.linspace(0, 1, nu + 1)[:, None]
    v = np.linspace(-1, 1, nv + 1)[None, :]
    w = width_fn(u) * width * 0.5
    # centre line: pitch angle goes from arch[0] (up) to arch[1] (down) along the leaf
    pitch = arch[0] + (arch[1] - arch[0]) * u ** 1.3
    ds = length / nu
    x = np.concatenate([[0], np.cumsum(np.cos(pitch[:-1, 0]) * ds)])[:, None]
    z = np.concatenate([[0], np.cumsum(np.sin(pitch[:-1, 0]) * ds)])[:, None]
    y = v * w
    zz = z + np.abs(v) * w * fold + curl * (v ** 2) * w * np.sin(np.pi * u)
    if ribs:
        zz = zz + rib_amp * np.cos(np.pi * ribs * v) * np.sin(np.pi * u) ** 0.5
    P = np.stack([np.broadcast_to(x, y.shape), y, zz], -1)
    col = np.broadcast_to(np.asarray(base_col, np.float32), P.shape).copy()
    tone = 1 + 0.18 * np.sin(u * 3.0 + rng.uniform(0, 6)) * np.ones_like(v) + rng.normal(0, 0.03, y.shape)
    col = col * tone[..., None]
    mid = np.exp(-(v / 0.14) ** 2) * np.ones_like(u)
    if ribs:
        mid = np.maximum(mid, (np.cos(np.pi * ribs * v) * 0.5 + 0.5) ** 6 * 0.7 * np.ones_like(u))
    col = col * (1 - mid[..., None] * 0.55) + np.asarray(vein_col, np.float32) * mid[..., None] * 0.55
    if mark is not None:           # clover chevron
        m = np.exp(-((u - (0.42 + 0.22 * np.abs(v))) / 0.07) ** 2) * (np.abs(v) < 0.92)
        col = col * (1 - 0.6 * m[..., None]) + np.asarray(mark, np.float32) * 0.6 * m[..., None]
    if edge_col is not None:
        e = (np.abs(v) ** 6) * np.ones_like(u) + (u ** 10)
        col = col * (1 - 0.5 * np.clip(e, 0, 1)[..., None]) + np.asarray(edge_col, np.float32) * 0.5 * np.clip(e, 0, 1)[..., None]
    return P, col


def place(P, col, origin, yaw, tilt=0.0, scale=1.0):
    c, s = math.cos(yaw), math.sin(yaw)
    ct, st = math.cos(tilt), math.sin(tilt)
    X = P[..., 0] * scale; Y = P[..., 1] * scale; Z = P[..., 2] * scale
    Y2 = Y * ct - Z * st; Z2 = Y * st + Z * ct          # roll about the leaf axis
    W = np.stack([X * c - Y2 * s + origin[0], X * s + Y2 * c + origin[1], Z2 + origin[2]], -1)
    n0, n1 = P.shape[0], P.shape[1]
    idx = np.arange(n0 * n1).reshape(n0, n1)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    add(W, q, col)


G = {'clover': srgb((0.20, 0.36, 0.12)), 'clover2': srgb((0.26, 0.42, 0.14)), 'cmark': srgb((0.62, 0.74, 0.50)), 'vein': srgb((0.50, 0.62, 0.34)),
     'plantain': srgb((0.17, 0.30, 0.10)), 'pvein': srgb((0.46, 0.56, 0.30)), 'daisy': srgb((0.22, 0.38, 0.13)), 'dand': srgb((0.20, 0.34, 0.10)),
     'white': srgb((0.86, 0.86, 0.82)), 'yellow': srgb((0.80, 0.62, 0.10)), 'dry': srgb((0.52, 0.40, 0.22)), 'dry2': srgb((0.40, 0.28, 0.15)), 'straw': srgb((0.70, 0.62, 0.40))}

w_clover = lambda u: np.sin(np.pi * np.clip(u, 0, 1) ** 0.62) ** 0.75 * (1 - 0.25 * np.exp(-((u - 1) / 0.08) ** 2))
w_plantain = lambda u: np.sin(np.pi * np.clip(u, 0, 1) ** 1.5) ** 0.8 * (0.25 + 0.75 * u ** 0.3) + 0.10 * (1 - u) * (u > 0)
w_daisy = lambda u: (0.22 + 0.78 * np.clip((u - 0.35) / 0.4, 0, 1) ** 2) * np.sqrt(np.clip(1 - np.clip((u - 0.72) / 0.28, 0, 1) ** 2.2, 0, 1))
w_dand = lambda u: np.sin(np.pi * np.clip(u, 0, 1) ** 1.2) ** 0.55 * (0.55 + 0.45 * np.abs(np.sin(u * np.pi * 5.5)) ** 0.6)
w_ray = lambda u: np.sin(np.pi * np.clip(u, 0, 1) ** 0.5) ** 0.5
w_dry = lambda u: np.sin(np.pi * np.clip(u, 0, 1) ** 0.8) ** 0.7


def cell_centre(i):
    return np.array([(i % CELLS + 0.5) * CELL, (i // CELLS + 0.5) * CELL, 0.0])


def clover_clump(o):
    n = int(rng.integers(4, 13))
    spread = rng.uniform(0.02, 0.055)
    for _ in range(n):
        a = rng.uniform(0, 6.283); r = spread * math.sqrt(rng.uniform())
        c = o + np.array([r * math.cos(a), r * math.sin(a), rng.uniform(0.012, 0.04)])
        size = rng.uniform(0.009, 0.015)
        yaw0 = rng.uniform(0, 6.283)
        base = G['clover'] if rng.uniform() < 0.6 else G['clover2']
        base = base * rng.uniform(0.8, 1.2)
        for k in range(3):
            P, col = leaf(w_clover, size, size * 1.05, base, G['vein'], nu=8, nv=6, fold=rng.uniform(0.05, 0.35), arch=(rng.uniform(0.0, 0.5), rng.uniform(-0.5, 0.1)), mark=G['cmark'])
            place(P, col, c, yaw0 + k * 2.094 + rng.normal(0, 0.12), rng.normal(0, 0.2))


def rosette(o, kind):
    if kind == 'plantain':
        n = int(rng.integers(5, 9)); L = rng.uniform(0.05, 0.085); W = L * rng.uniform(0.42, 0.6)
        for k in range(n):
            l = L * rng.uniform(0.7, 1.1)
            P, col = leaf(w_plantain, l, W * l / L, G['plantain'] * rng.uniform(0.8, 1.2), G['pvein'], nu=14, nv=10, fold=-0.1, arch=(rng.uniform(0.5, 0.9), rng.uniform(-0.6, -0.2)), ribs=5, rib_amp=0.0009, curl=-0.15)
            place(P, col, o + np.array([0, 0, 0.002 * k]), k * 6.283 / n + rng.normal(0, 0.2), rng.normal(0, 0.12))
    elif kind == 'daisy':
        n = int(rng.integers(7, 12)); L = rng.uniform(0.028, 0.045)
        for k in range(n):
            l = L * rng.uniform(0.7, 1.1)
            P, col = leaf(w_daisy, l, l * 0.42, G['daisy'] * rng.uniform(0.8, 1.2), G['vein'], nu=10, nv=6, fold=0.1, arch=(rng.uniform(0.3, 0.6), rng.uniform(-0.5, -0.1)), curl=0.1)
            place(P, col, o + np.array([0, 0, 0.0015 * k]), k * 6.283 / n + rng.normal(0, 0.25), rng.normal(0, 0.15))
    else:
        n = int(rng.integers(6, 10)); L = rng.uniform(0.06, 0.09)
        for k in range(n):
            l = L * rng.uniform(0.6, 1.1)
            P, col = leaf(w_dand, l, l * 0.26, G['dand'] * rng.uniform(0.8, 1.2), G['pvein'], nu=22, nv=6, fold=0.15, arch=(rng.uniform(0.3, 0.7), rng.uniform(-0.6, -0.2)))
            place(P, col, o + np.array([0, 0, 0.0015 * k]), k * 6.283 / n + rng.normal(0, 0.25), rng.normal(0, 0.15))


def daisy_flower(o):
    c = o + np.array([rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), rng.uniform(0.035, 0.05)])
    n = int(rng.integers(22, 34)); R = rng.uniform(0.008, 0.011)
    for k in range(n):
        P, col = leaf(w_ray, R, R * 0.26, G['white'] * rng.uniform(0.9, 1.05), G['white'], nu=5, nv=2, fold=0.0, arch=(rng.uniform(0.0, 0.25), rng.uniform(-0.2, 0.1)))
        P = P + np.array([0.0025, 0, 0])
        place(P, col, c, k * 6.283 / n + rng.normal(0, 0.05), rng.normal(0, 0.15))
    # disc: little dome
    t = np.linspace(0, 1, 6)[:, None]; a = np.linspace(0, 6.283, 13)[None, :]
    r = 0.0032 * t
    P = np.stack([r * np.cos(a), r * np.sin(a), 0.0016 * np.cos(t * 1.4) * np.ones_like(a) + 0.0005], -1)
    col = np.broadcast_to(G['yellow'], P.shape) * (0.8 + 0.3 * rng.uniform(size=P.shape[:2]))[..., None]
    place(P, col, c, 0.0)


def litter(o):
    for _ in range(int(rng.integers(2, 6))):
        c = o + np.array([rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), rng.uniform(0.002, 0.012)])
        if rng.uniform() < 0.55:
            l = rng.uniform(0.025, 0.05)
            P, col = leaf(w_dry, l, l * rng.uniform(0.4, 0.6), (G['dry'] if rng.uniform() < 0.5 else G['dry2']) * rng.uniform(0.8, 1.2), G['dry2'], nu=10, nv=6, fold=rng.uniform(-0.3, 0.4), arch=(rng.uniform(-0.1, 0.3), rng.uniform(-0.3, 0.3)), curl=rng.uniform(-0.5, 0.5), edge_col=G['dry2'] * 0.6)
            place(P, col, c, rng.uniform(0, 6.283), rng.normal(0, 0.5))
        else:        # dry grass blades
            for _ in range(int(rng.integers(2, 6))):
                l = rng.uniform(0.04, 0.09)
                P, col = leaf(lambda u: (1 - u) ** 0.5 * 0.9 + 0.1, l, 0.0028, G['straw'] * rng.uniform(0.75, 1.15), G['straw'], nu=10, nv=2, fold=0.3, arch=(rng.uniform(0.0, 0.25), rng.uniform(-0.3, 0.0)))
                place(P, col, c + np.array([rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), 0]), rng.uniform(0, 6.283), rng.normal(0, 0.3))


KINDS = []
for i in range(CELLS * CELLS):
    o = cell_centre(i)
    row = i // CELLS
    if row < 3:
        clover_clump(o); KINDS.append('clover')
    elif row < 5:
        rosette(o, 'plantain'); KINDS.append('plantain')
    elif row == 5:
        rosette(o, 'daisy'); KINDS.append('daisy')
        if i % 2 == 0:
            daisy_flower(o); KINDS[-1] = 'daisy_flower'
    elif row == 6:
        rosette(o, 'dandelion'); KINDS.append('dandelion')
    else:
        litter(o); KINDS.append('litter')

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
Vv = np.concatenate(V).astype(np.float32); Qq = np.concatenate(Q).astype(np.int32); Cc = np.concatenate(C).astype(np.float32)
me = bpy.data.meshes.new('plants')
me.vertices.add(len(Vv)); me.vertices.foreach_set('co', Vv.ravel())
me.loops.add(Qq.size); me.loops.foreach_set('vertex_index', Qq.ravel())
me.polygons.add(len(Qq)); me.polygons.foreach_set('loop_start', (np.arange(len(Qq)) * 4).astype(np.int32))
me.polygons.foreach_set('use_smooth', np.ones(len(Qq), bool))
me.update(calc_edges=True)
ca = me.color_attributes.new('col', 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set('color', np.concatenate([np.clip(Cc, 0, 1), np.ones((len(Cc), 1), np.float32)], 1).ravel())
ob = bpy.data.objects.new('plants', me); sc.collection.objects.link(ob)
m = bpy.data.materials.new('leaf'); m.use_nodes = True
nt = m.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(em.outputs[0], out.inputs[0])
at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'col'
geo = nt.nodes.new('ShaderNodeNewGeometry')
vm = nt.nodes.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY_ADD'
vm.inputs[1].default_value = (0.5, 0.5, 0.5); vm.inputs[2].default_value = (0.5, 0.5, 0.5); nt.links.new(geo.outputs['Normal'], vm.inputs[0])
sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
mz = nt.nodes.new('ShaderNodeMath'); mz.operation = 'MULTIPLY'; mz.inputs[1].default_value = 10.0; nt.links.new(sep.outputs[2], mz.inputs[0])
aon = nt.nodes.new('ShaderNodeAmbientOcclusion'); aon.inputs['Distance'].default_value = 0.03; aon.samples = 4
me.materials.append(m)
cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = CELLS * CELL; cam.clip_start = 0.01; cam.clip_end = 5
co = bpy.data.objects.new('c', cam); co.location = (CELLS * CELL / 2, CELLS * CELL / 2, 1.0); sc.collection.objects.link(co); sc.camera = co
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = False
sc.cycles.max_bounces = 0
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.render.resolution_x = PX; sc.render.resolution_y = PX; sc.render.film_transparent = True
sc.view_settings.view_transform = 'Raw' if 'Raw' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_mode = 'RGBA'; sc.render.image_settings.color_depth = '32'
import OpenImageIO as oiio


def shot(sock):
    for l in list(em.inputs[0].links):
        nt.links.remove(l)
    nt.links.new(sock, em.inputs[0])
    exr = os.path.join(OUT, '_p.exr')
    sc.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    inp = oiio.ImageInput.open(exr); spec = inp.spec()
    px = np.asarray(inp.read_image('float')).reshape(spec.height, spec.width, spec.nchannels); inp.close(); os.remove(exr)
    return px


A = shot(at.outputs['Color'])
alpha = A[..., 3]
alb = A[..., :3] / np.maximum(alpha[..., None], 1e-4)
Nn = shot(vm.outputs[0]); nrm = Nn[..., :3] / np.maximum(alpha[..., None], 1e-4) * 2 - 1
Hh = shot(mz.outputs[0]); h = Hh[..., 0] / np.maximum(alpha, 1e-4) / 10.0 * (alpha > 0.3)
Ao = shot(aon.outputs['AO']); ao = np.where(alpha > 0.05, Ao[..., 0] / np.maximum(alpha, 1e-4), 1.0)
print('RANGES alb', float(alb[alpha > 0.9].mean()), 'h', float(h.max()), 'nz', float(nrm[..., 2][alpha > 0.9].mean()), 'ao', float(ao[alpha > 0.9].mean()))
np.savez_compressed(os.path.join(OUT, 'plant_sheet.npz'), albedo=alb.astype(np.float16), alpha=alpha.astype(np.float16), normal=nrm.astype(np.float16),
                    height=h.astype(np.float16), ao=ao.astype(np.float16), kinds=np.array(KINDS), cell_m=CELL, px_per_m=PX / (CELLS * CELL))
# a preview for the eye
prev = np.clip(np.where(alpha[..., None] > 0.02, np.clip(alb, 0, 1) * np.clip(ao, 0, 1)[..., None] ** 0.6, 0.05) ** (1 / 2.2), 0, 1)
im = bpy.data.images.new('p', PX, PX)
im.pixels.foreach_set(np.concatenate([prev[::-1], np.ones((PX, PX, 1), np.float32)], -1).astype(np.float32).ravel())
im.filepath_raw = os.path.join(OUT, 'plant_sheet_preview.png'); im.file_format = 'PNG'; im.save()
print('SHEET DONE', len(Vv), 'verts')
