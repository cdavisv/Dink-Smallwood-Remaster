"""Stage 1: collect the rig, skin (head, hands), old wardrobe (as body proxy) into a private work file."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *

SRC = CHARS / 'Dink/HandBindingV2/SK_Dink_Hands.blend'
WORK = OUT / 'Dink/Work'
bpy.ops.wm.open_mainfile(filepath=str(SRC))
save_blend(filepath=str(WORK / 'dink_base.blend'), copy=False)
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT') or (o.type == 'MESH' and not o.name.endswith('LOD0')):
        bpy.data.objects.remove(o, do_unlink=True)
arm = bpy.data.objects['Armature']
lod = [o for o in bpy.data.objects if o.type == 'MESH'][0]
# original MakeHuman UVs for the skin faces from the pre-rig body (same face order)
with bpy.data.libraries.load(str(CHARS / 'Dink/Dink_Working.blend')) as (src, dst):
    dst.objects = ['Dink_AnatomicalBody', 'Rust red linen shirt and sleeves', 'Tan wool trousers']
body, oshirt, otrou = dst.objects
for o in (body, oshirt, otrou): sc.collection.objects.link(o)
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
    if not exact:   # refitted hands: same topology and loop order, moved vertices
        pairs = list(zip(p.loop_indices, bp.loop_indices))
    else: ok += len(pairs)
    for li, bli in pairs: new.data[li].uv = uvs[bli].uv
log('uv loops exact', ok, 'bad polys', bad, 'total loops', sum(len(p.vertices) for p in skin_polys))
bpy.data.objects.remove(body, do_unlink=True)
# split by material
activate(lod); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
names = {'MI_Dink_Skin': 'Skin', 'MI_Dink_Eyes': 'OldEyes', 'MI_Dink_Hair': 'OldHair', 'MI_Dink_BrowLash': 'BrowLash', 'MI_Dink_Wardrobe': 'OldWardrobe'}
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.data.materials and o.data.materials[0] and o.data.materials[0].name in names]:
    o.name = names[o.data.materials[0].name]; o.data.name = o.name
oshirt.name = 'OldShirtTopo'; otrou.name = 'OldTrousersTopo'
for o in bpy.data.objects:
    if o.type == 'MESH':
        c = co_np(o.data); log(o.name, len(c), c.min(0).round(3), c.max(0).round(3), 'tris', tri_count(o))
sk = bpy.data.objects['Skin']; c = co_np(sk.data)
head = c[c[:, 2] > 1.4]; log('head part zmin', head[:, 2].min(), 'neck ring ', head[head[:, 2] < head[:, 2].min() + .01].round(3)[:6])
hands = c[c[:, 0] > .3]; log('left arm skin: max z', hands[:, 2].max(), hands[hands[:, 2] > hands[:, 2].max() - .01].round(3)[:4])
log('vgroups body sample', [g.name for g in sk.vertex_groups][:10])
save_blend()
