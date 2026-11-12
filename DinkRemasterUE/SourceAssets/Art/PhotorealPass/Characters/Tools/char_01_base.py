"""Stage 1+2a (generalised from dink_01_base / dink_02a_bodyvol): collect rig, skin, old wardrobe topology and the
transient Manny weight reference into <Name>/Work/<name>_base.blend, then build the BodyVol garment volume and save
<name>_bodyvol.blend.   usage: blender -b --python char_01_base.py -- <Name>"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *; from chars import CHARS_CFG
N = args()[0]; C = CHARS_CFG[N]; n = N.lower()
WORK = OUT / N / 'Work'; WORK.mkdir(parents=True, exist_ok=True); (OUT / N / 'Review').mkdir(exist_ok=True); (OUT / N / 'Textures').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(CHARS / C['src']))
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / (n + '_base.blend')), copy=False)
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT') or (o.type == 'MESH' and not o.name.endswith('LOD0')):
        bpy.data.objects.remove(o, do_unlink=True)
arm = bpy.data.objects['Armature']
lod = [o for o in bpy.data.objects if o.type == 'MESH'][0]
with bpy.data.libraries.load(str(CHARS / C['work'])) as (src, dst):
    dst.objects = [C['body']] + C['old'] + ['Reference_Manny']
body = dst.objects[0]; olds = dst.objects[1:-1]; manny = dst.objects[-1]
for o in dst.objects: sc.collection.objects.link(o)
for m in list(manny.modifiers): manny.modifiers.remove(m)
manny.name = 'Manny'; manny.hide_render = True; manny.data.materials.clear()
for o in list(bpy.data.objects):
    if o.type == 'ARMATURE' and o is not arm: bpy.data.objects.remove(o, do_unlink=True)
me = lod.data
skin_polys = [p for p in me.polygons if p.material_index == 0]
bme = body.data
log('skin polys', len(skin_polys), 'body polys', len(bme.polygons))
uvs = bme.uv_layers[0].data
new = me.uv_layers.new(name='UVMH')
ok = 0; bad = 0
co = co_np(me); bco = co_np(bme)
for p, bp in zip(skin_polys, bme.polygons):
    if len(p.vertices) != len(bp.vertices): bad += 1; continue
    pairs = []; exact = True
    for li, vi in zip(p.loop_indices, p.vertices):
        best = None; bd = 1e9
        for bli, bvi in zip(bp.loop_indices, bp.vertices):
            d = ((co[vi] - bco[bvi]) ** 2).sum()
            if d < bd: bd = d; best = bli
        pairs.append((li, best)); exact &= bd < 1e-8
    if not exact: pairs = list(zip(p.loop_indices, bp.loop_indices))
    else: ok += len(pairs)
    for li, bli in pairs: new.data[li].uv = uvs[bli].uv
log('uv loops exact', ok, 'bad polys', bad, 'total loops', sum(len(p.vertices) for p in skin_polys))
bpy.data.objects.remove(body, do_unlink=True)
activate(lod); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
names = {C['matp'] + 'Skin': 'Skin', C['matp'] + 'Eyes': 'OldEyes', C['matp'] + 'Hair': 'OldHair', C['matp'] + 'BrowLash': 'BrowLash', C['matp'] + 'Wardrobe': 'OldWardrobe'}
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.data.materials and o.data.materials[0] and o.data.materials[0].name in names]:
    o.name = names[o.data.materials[0].name]; o.data.name = o.name
for i, o in enumerate(olds): o.name = 'OldTopo%d' % i
for o in bpy.data.objects:
    if o.type == 'MESH':
        c = co_np(o.data); log(o.name, len(c), c.min(0).round(3), c.max(0).round(3), 'tris', tri_count(o))
if C.get('arms'):
    import armfit; armfit.add_arms(bpy.data.objects['Skin'], arm, bpy.data.objects['Manny'], CHARS / 'ThirdParty/MakeHuman/CC0_BaseMesh.obj', **C['arms'])
if C.get('hand_ratio'):   # the MakeHuman hands are 3.3k triangles each: thin them for the NPC budget
    sk = bpy.data.objects['Skin']; c = co_np(sk.data); m_ = c.copy(); m_[:, 0] = np.abs(m_[:, 0])
    Eh, Wh = np.array(arm.data.bones['lowerarm_l'].head_local), np.array(arm.data.bones['hand_l'].head_local); LFh = np.linalg.norm(Wh - Eh)
    sel = (c[:, 2] < 1.40) & (((m_ - Eh) @ ((Wh - Eh) / LFh)) > LFh - .012)
    vg = sk.vertex_groups.new(name='_dec'); vg.add([int(i) for i in np.nonzero(sel)[0]], 1.0, 'REPLACE'); t0 = tri_count(sk)
    sk.data.calc_loop_triangles(); ht = sum(1 for t_ in sk.data.loop_triangles if all(sel[v] for v in t_.vertices))
    d_ = sk.modifiers.new('dec', 'DECIMATE'); d_.ratio = 1 - ht * (1 - C['hand_ratio']) / t0; d_.vertex_group = '_dec'
    for m in list(sk.modifiers):
        if m.type != 'DECIMATE': sk.modifiers.remove(m)
    activate(sk); bpy.ops.object.modifier_apply(modifier='dec'); sk.vertex_groups.remove(sk.vertex_groups['_dec']); log('hands decimated', t0, '->', tri_count(sk))
bpy.ops.wm.save_mainfile()

# ---------------------------------------------------------------- body volume
B = arm.data.bones
def bh(nm): return np.array(B[nm].head_local)
S, E_, Wr = bh('upperarm_l'), bh('lowerarm_l'), bh('hand_l')
T, K, A, BALL = bh('thigh_l'), bh('calf_l'), bh('foot_l'), bh('ball_l')
D = bpy.data.objects
old_bvh = bvh_of(olds)
up_bvh = bvh_of(olds + [D['Skin']]) if C.get('upper') == 'both' else old_bvh; UG = C.get('upper_grow', .003) if C.get('upper') == 'both' else 0.0
manny_bvh = bvh_of(D['Manny'])
def scan_tube(name, pts, ref, s0, s1, nr, nu, rmax, rdef, shrink=.006, bvh=None, grow=0.0, scale=None):
    bvh = bvh or old_bvh
    poly = Poly(pts, ref=ref); rings = []; R = np.zeros((nr, nu)); Cn = []; FR = []
    for i in range(nr):
        s = s0 + (s1 - s0) * i / (nr - 1); c, d = poly.point(min(max(s, 0), poly.cum[-1])); c = c + d * (s - min(max(s, 0), poly.cum[-1]))
        x, y = poly.frame(d); Cn.append(c); FR.append((x, y))
        for j in range(nu):
            a = 2 * math.pi * j / nu; dr = x * math.cos(a) + y * math.sin(a)
            lim = rmax(s, a) if callable(rmax) else rmax
            hit = bvh.ray_cast(c, dr, lim)
            R[i, j] = (hit[0] - c).length + grow if hit[0] is not None else (rdef(s, a) if callable(rdef) else rdef)
    for _ in range(2):
        R = (np.roll(R, 1, 1) + 2 * R + np.roll(R, -1, 1)) / 4
        R[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4
    R -= shrink
    if scale is not None:
        for i in range(nr): R[i] *= scale(s0 + (s1 - s0) * i / (nr - 1))
    for i in range(nr):
        x, y = FR[i]
        rings.append([tuple(Cn[i] + (x * math.cos(2 * math.pi * j / nu) + y * math.sin(2 * math.pi * j / nu)) * R[i, j]) for j in range(nu)])
    return loft(name, rings, cap_end=True, cap_start=True)
parts = []
def torso_rmax(s, a):
    z = .86 + s; lat = abs(math.sin(a))
    return .30 if z < 1.30 else (.30 - (.30 - .19) * lat * min(1, (z - 1.30) / .08))
parts.append(scan_tube('bv_torso', [(0, -.02, .86), (0, -.02, 1.53)], (0, -1, 0), 0, .612, 62, 72, torso_rmax, lambda s, a: C['torso_rdef'], bvh=up_bvh, grow=UG,
                       scale=(lambda s: 1 + C['stout'] * (math.exp(-((.86 + s - 1.10) / .15) ** 2) + .55 * math.exp(-((.86 + s - 1.27) / .08) ** 2))) if C.get('stout') else None))
for sg in (1, -1):
    M = np.array([sg, 1, 1.0])
    parts.append(scan_tube('bv_arm%d' % sg, [S * M, E_ * M, Wr * M], (0, 0, -1), -.02, np.linalg.norm(E_ - S) + np.linalg.norm(Wr - E_) - .006, 60, 40, .085, .036, bvh=up_bvh, grow=UG))
    parts.append(scan_tube('bv_sho%d' % sg, [np.array([.04, .0, 1.45]) * M, np.array([.215, .026, 1.44]) * M], (0, 0, 1), 0, .176, 22, 40, .115, .075, bvh=up_bvh, grow=UG))
    if C['legs'] == 'old':
        parts.append(scan_tube('bv_leg%d' % sg, [T * M, K * M, A * M], (0, -1, 0), -.06, np.linalg.norm(K - T) + .355, 80, 48, .13, .07))
    else:
        parts.append(scan_tube('bv_leg%d' % sg, [T * M, K * M, A * M], (0, -1, 0), -.06, np.linalg.norm(K - T) + .355, 80, 48, .13, .06, shrink=-.004, bvh=manny_bvh))
bv = join(parts, 'BodyVol')
m = bv.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = .005; m.adaptivity = 0
apply_mods(bv); laplacian_smooth(bv, it=8, lam=.6); smooth_shade(bv)
for l in list(bv.data.uv_layers): bv.data.uv_layers.remove(l)
log('BodyVol', len(bv.data.vertices), co_np(bv.data).min(0), co_np(bv.data).max(0))
if C.get('chest') is not None:
    import armfit; armfit.add_chest(bpy.data.objects['Skin'], arm, bpy.data.objects['Manny'], CHARS / 'ThirdParty/MakeHuman/CC0_BaseMesh.obj', vol=bv, **C['chest'])
cull = C.get('cull')
if cull:   # skin that the new outfit always hides goes before the skin atlas is packed
    import folds
    folds.setup({nm: list(arm.data.bones[nm].head_local) for nm in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')})
    sk = bpy.data.objects['Skin']; c = co_np(sk.data); r = np.sqrt(c[:, 0] ** 2 + (c[:, 1] - .008) ** 2); ah = folds.arm_h(c)
    m = c.copy(); m[:, 0] = np.abs(m[:, 0]); sa = (m - folds.S) @ ((folds.E_ - folds.S) / folds.LU)
    inneck = r < cull['neck_r']
    if 'neck_q' in cull:   # open neckline: keep only the skin inside the dress opening (same ellipsoid as the bodice cut) plus a margin
        qc, qr, qm = cull['neck_q']; q_ = np.sqrt((((c - np.array(qc)) / np.array(qr)) ** 2).sum(1)); inneck = (q_ < qm) | (r < .072)
    keep = (c[:, 2] > cull.get('head_z', 1.50)) | ((c[:, 2] > cull['neck_z']) & inneck)
    keep |= ((ah > 0) & (sa > cull['arm_s'])) if 'arm_s' in cull else (ah > cull['arm_h'])
    bm = bmesh.new(); bm.from_mesh(sk.data); bm.verts.ensure_lookup_table()
    dead = [f for f in bm.faces if not (all if 'neck_q' in cull else any)(keep[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(sk.data); bm.free()
    log('skin culled faces', len(dead), 'skin tris now', tri_count(sk))

bpy.ops.wm.save_as_mainfile(filepath=str(WORK / (n + '_bodyvol.blend')))
if 'norender' in args(): sys.exit(0)
for o in D:
    if o.type == 'MESH': o.hide_render = o.name not in (('Skin',) if 'skinonly' in args() else ('BodyVol', 'Skin'))
mt = bpy.data.materials.new('pv'); mt.use_nodes = True; bv.data.materials.append(mt)
setup_render(samples=16, res=(1100, 800)); sc.world.node_tree.nodes['Background'].inputs[1].default_value = .08
bpy.context.view_layer.material_override = mt
shoot(OUT / N / 'Review/bodyvol.png', (0.9, -3.4, 1.3), (0, 0, .92), lens=60)
if 'skinonly' in args(): shoot(OUT / N / 'Review/bodyvol_b.png', (-1.2, 2.2, 1.6), (0.15, 0, 1.3), lens=60)
