"""A townsman whose head is larger than the rig's (townsfolk.py `head_scale`, the gnome): two stages around the assembly.

    blender -b -t 4 --python townsfolk_grow.py -- <Name> over        BEFORE the hair stage
    blender -b -t 4 <Characters>/NPC/<Name>/SK_<Name>_Photoreal.blend --python townsfolk_grow.py -- <Name>      AFTER the assembly

`over` writes NPC/<Name>/Work/<name>_over.blend: the clothes of <name>_packed.blend brought DOWN by the head scale about
the base of the neck. The groom lays the beard over that file (hair_styles.py beard `over`); grown with the head it then
lies on the real clothes.

The second stage does on every LOD of the assembled file what seth_build.py does for Seth: skin, eyes, hair and beard
grow about the base of the neck by the weight each vertex has on the head and neck bones. The clothes do not grow. A
hat of the source (`hat`: everything of the Outfit slot above z0) is set on the grown head as one rigid piece: scaled
about the centre of its brim, turned about the x axis there by `tilt` degrees, and the centre moved to `to`. Hair cards that
lie inside the hat (cloth above them and cloth outside them) are cut away, so nothing comes through the cone."""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(__file__))
from townsfolk import TOWNSFOLK

argv = sys.argv[sys.argv.index('--') + 1:]
NAME = argv[0]; ROW = TOWNSFOLK[NAME]; F = float(ROW['head_scale']); n_ = NAME.lower()
CH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARE = {'head': 1.0, 'neck_02': 0.62, 'neck_01': 0.22}      # as seth_build.py

if len(argv) > 1 and argv[1] == 'over':
    bpy.ops.wm.open_mainfile(filepath=os.path.join(CH, 'NPC', NAME, 'Work', f'{n_}_packed.blend'))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    pivot = np.array(arm.matrix_world @ arm.data.bones['neck_01'].head_local)
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        me = o.data; co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        me.vertices.foreach_set('co', (pivot + (co - pivot) / F).reshape(-1)); me.update()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CH, 'NPC', NAME, 'Work', f'{n_}_over.blend'), compress=True)
    print('[PR] townsfolk_grow over', NAME, 'clothes brought down by', F); sys.exit(0)

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if arm.get('head_scale'): raise SystemExit('townsfolk_grow: the head of this file is already grown (x%s); assemble again first' % arm['head_scale'])
pivot = np.array(arm.matrix_world @ arm.data.bones['neck_01'].head_local, np.float64)
lods = sorted((o for o in bpy.data.objects if o.type == 'MESH' and '_LOD' in o.name), key=lambda o: o.name)
assert len(lods) == 4, [o.name for o in lods]
HAT = ROW.get('hat')
hat_fit = None
for o in lods:
    me = o.data; n = len(me.vertices); assert not me.shape_keys
    slot = [m.material.name.rsplit('_', 1)[-1] if m.material else '' for m in o.material_slots]
    co = np.empty(n * 3, np.float64); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    cloth = np.zeros(n, bool); hair = np.zeros(n, bool)
    for p in me.polygons:
        s = slot[p.material_index]
        if s in ('Outfit', 'Gear'): cloth[list(p.vertices)] = True
        elif s == 'Hair': hair[list(p.vertices)] = True
    index = {g.index: SHARE[g.name] for g in o.vertex_groups if g.name in SHARE}
    w = np.zeros(n, np.float64)
    for v in me.vertices:
        total = sum(g.weight for g in v.groups)
        if total > 0: w[v.index] = sum(g.weight * index.get(g.group, 0.0) for g in v.groups) / total
    w = np.clip(w, 0.0, 1.0) ** 0.85
    w[hair] = 1.0       # cards are rigid on the head bone: a beard grows as one piece, whatever weights its lower end was given
    w[cloth] = 0.0
    co = pivot + (co - pivot) * (1.0 + (F - 1.0) * w)[:, None]
    if HAT:
        hat = cloth & (co[:, 2] > HAT['z0'])
        if hat_fit is None:      # measured once, on LOD0: the brim = the lowest part of the hat
            P = co[hat]; low = P[P[:, 2] < HAT['z0'] + HAT.get('brim_h', 0.12)]      # the brim and the foot of the cone (the point of a bent hat lies far off the axis)
            hat_fit = (low.min(axis=0) + low.max(axis=0)) / 2; print('[PR] hat brim centre in the port', np.round(hat_fit, 3), 'brim half extent', np.round((low.max(axis=0) - low.min(axis=0)) / 2, 3), 'vertices', int(hat.sum()))
        a = math.radians(HAT.get('tilt', 0.0)); R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        co[hat] = np.array(HAT['to']) + ((co[hat] - hat_fit) * HAT.get('scale', 1.0)) @ R.T
    me.vertices.foreach_set('co', co.reshape(-1)); me.update()
    cut = 0
    if HAT:
        hv = np.nonzero(hat)[0]; hset = set(hv.tolist())
        tris = [tuple(p.vertices) for p in me.polygons if all(v in hset for v in p.vertices)]
        bvh = BVHTree.FromPolygons([Vector(c) for c in co], tris)
        axis = np.array(HAT['to'])
        dead = []
        for p in me.polygons:
            if slot[p.material_index] != 'Hair': continue
            c = Vector(p.center); d = Vector((c.x - axis[0], c.y - axis[1], 0.0))
            if d.length < 1e-5: d = Vector((1, 0, 0))
            if bvh.ray_cast(c, Vector((0, 0, 1)))[0] is not None and bvh.ray_cast(c, d.normalized())[0] is not None: dead.append(p.index)
        if dead:
            import bmesh
            bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in dead], context='FACES')
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
            bm.to_mesh(me); bm.free(); me.update(); cut = len(dead)
    print('[PR] townsfolk_grow', o.name, 'vertices', n, 'grown', int((w > 0.01).sum()), 'hair faces cut inside the hat', cut, 'triangles', sum(len(p.vertices) - 2 for p in me.polygons),
          'top z', round(float(co[:, 2].max()), 3))
arm['head_scale'] = F
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_mainfile(compress=True, relative_remap=True)
print('[PR] townsfolk_grow saved', os.path.basename(bpy.data.filepath), 'head x', F)
