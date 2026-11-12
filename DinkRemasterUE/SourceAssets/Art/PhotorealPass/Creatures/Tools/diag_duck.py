import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Duck/SK_Duck.blend'))
o = bpy.data.objects['SK_Duck_LOD0']; me = o.data; uv = me.uv_layers.active.data
def load(n):
    img = bpy.data.images.load(str(OUT / 'Duck/Textures' / n)); return np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
bc = load('T_Duck_Atlas_BC.png'); nm = load('T_Duck_Atlas_N.png'); orm = load('T_Duck_Atlas_ORM.png'); S = bc.shape[0]
bad = []
for p in me.polygons:
    m = o.material_slots[p.material_index].material.name
    if 'Cards' in m: continue
    u = sum((uv[i].uv for i in p.loop_indices), Vector((0, 0))) / len(p.loop_indices); x = min(S - 1, max(0, int(u.x * S))); y = min(S - 1, max(0, int(u.y * S)))
    if bc[y, x, :3].sum() < .6 or nm[y, x, 2] < .62: bad.append((p.index, tuple(round(c, 3) for c in p.center), m, tuple(round(float(v), 2) for v in bc[y, x, :3]), tuple(round(float(v), 2) for v in nm[y, x, :3]), tuple(round(float(v), 2) for v in orm[y, x, :3]), round(p.area * 1e6, 1)))
log('black faces', len(bad))
for b in bad[:40]: log(b)
