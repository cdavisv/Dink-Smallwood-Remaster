"""NPC variants derived from the photoreal pass characters (PhotorealPass/Characters/<Base>): open the finished character,
re-point its textures, swap in recoloured maps, pose it, render, and export either the rigged LOD chain or a posed static mesh."""
import bpy, os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L

CHARS = os.path.join(L.PP, 'Characters')


def open_char(base):
    """open Characters/<base>/SK_<base>_Photoreal.blend; returns (armature, {lod index: mesh})"""
    bpy.ops.wm.open_mainfile(filepath=os.path.join(CHARS, base, 'SK_%s_Photoreal.blend' % base)); sc = bpy.context.scene; L.use_hip_gpu(sc); sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    tex = os.path.join(CHARS, base, 'Textures')
    for im in bpy.data.images:                       # the stored paths were scrubbed: find each map by its file name
        fn = os.path.basename(im.filepath.replace('\\', '/'))
        if fn and os.path.exists(os.path.join(tex, fn)):
            im.filepath = os.path.join(tex, fn); im.reload()
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); lods = {}
    for o in bpy.data.objects:
        if o.type == 'MESH' and '_LOD' in o.name:
            lods[int(o.name[-1])] = o
    for o in bpy.data.objects:
        if o.type in ('LIGHT', 'CAMERA') or (o.type == 'MESH' and o not in lods.values()):
            o.hide_render = True
    return arm, lods


def mat_image(mat, key):
    """the image node of a material whose file name ends with _<key>.png"""
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and os.path.basename(n.image.filepath).upper().endswith('_%s.PNG' % key.upper()):
            return n
    return None


def swap_image(mat, key, path):
    n = mat_image(mat, key); im = bpy.data.images.load(path, check_existing=False); im.colorspace_settings.name = n.image.colorspace_settings.name; n.image = im; return im


def drop_slot_faces(ob, slot_name):
    """delete the faces of one material slot (used to take armour off)"""
    import bmesh
    idx = next(i for i, m in enumerate(ob.data.materials) if m and slot_name in m.name); bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == idx], context='FACES'); bm.to_mesh(ob.data); bm.free(); ob.data.update()
