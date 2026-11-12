"""Replace selected asset collections in KIT_Stonebrook440.blend with freshly built ones from another
.blend (used after `build_440.py -- --only ...` wrote a partial kit).  Existing same-named materials and
images are reused, so no '.001' duplicates are introduced.

    blender -b --factory-startup -P merge_assets_440.py -- <partial.blend> SM_A[,SM_B]
"""
import bpy, sys
from pathlib import Path
ART = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index('--') + 1:]
src, names = argv[0], argv[1].split(',')
bpy.ops.wm.open_mainfile(filepath=str(ART / 'KIT_Stonebrook440.blend'))
for n in names:
    c = bpy.data.collections.get(n)
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
before_mats = set(bpy.data.materials.keys()); before_imgs = set(bpy.data.images.keys())
with bpy.data.libraries.load(src, link=False) as (s, d):
    d.collections = names
for c in d.collections:
    bpy.context.scene.collection.children.link(c)
    for ob in c.objects:
        for slot in ob.material_slots:
            m = slot.material
            base = m.name.rsplit('.', 1)[0] if m.name not in before_mats else m.name
            if base in before_mats and m.name != base:
                slot.material = bpy.data.materials[base]
for m in [m for m in bpy.data.materials if m.name not in before_mats and m.users == 0]:
    bpy.data.materials.remove(m)
for m in [m for m in bpy.data.materials if m.name not in before_mats]:
    base = m.name.rsplit('.', 1)[0]
    if base in before_mats:
        m.user_remap(bpy.data.materials[base]); bpy.data.materials.remove(m)
for im in [i for i in bpy.data.images if i.name not in before_imgs]:
    base = im.name.rsplit('.', 1)[0]
    if base in before_imgs:
        im.user_remap(bpy.data.images[base]); bpy.data.images.remove(im)
for im in bpy.data.images:
    if im.filepath:
        im.reload()
bpy.ops.wm.save_mainfile(compress=True)
print('MERGED', names)
