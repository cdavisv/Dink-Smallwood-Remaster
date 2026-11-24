"""The iron-bound chest while its lid goes up (175 / 176 / 177 frames 2 to 6), as static meshes on the chest's own bake.

The Props kit has the chest closed (SM_Chest_Small_PR) and thrown open at 102 degrees (SM_Chest_Small_Open_PR): the same
vertices, the lid turned on its back hinges. The 1997 animation has six pictures: closed, ajar, a third open, two thirds,
nearly up, right up and leaning back; the save keeps frame 4 (two thirds) or frame 6. This script reads the two Props
exports (never writes them), finds the lid as the vertices that differ, and writes one mesh per picture with the lid
turned to that picture's angle about the same hinge. All of them use the chest's normal and ORM maps and one colour map of their own, the Props map with the inside darkened.

    DINK_CPU=1 blender -b --factory-startup -t 4 --python tools/build_chest_states.py -- <repository root with real Props files> [--review <png>]
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'
HINGE = (0.257, 0.36)            # y, z of the hinge axis (along x), from Props/Chest_Small_Open/manifest.json
# picture frame -> lid angle in degrees, read off the 1997 frames (175-177 chst1..3-, frames 2 to 6)
STATES = {2: 13.0, 3: 44.0, 4: 74.0, 5: 96.0, 6: 110.0}


def args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    o = {'repo': a[0], 'review': None}
    if '--review' in a:
        o['review'] = a[a.index('--review') + 1]
    return o


def load(repo):
    P = os.path.join(repo, 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Props')
    bpy.ops.import_scene.fbx(filepath=os.path.join(P, 'Chest_Small/SM_Chest_Small_PR.fbx'))
    bpy.ops.import_scene.fbx(filepath=os.path.join(P, 'Chest_Small_Open/SM_Chest_Small_Open_PR.fbx'))
    lods = []
    for i in range(3):
        a = bpy.data.objects['SM_Chest_Small_PR_LOD%d' % i]
        b = bpy.data.objects['SM_Chest_Small_Open_PR_LOD%d' % i]
        pa = np.array([v.co for v in a.data.vertices]); pb = np.array([v.co for v in b.data.vertices])
        lid = np.linalg.norm(pa - pb, axis=1) > 1e-4
        lods.append((a, lid))
    return lods


def state_mesh(src, lid, angle, name):
    ob = src.copy()
    ob.data = src.data.copy()
    ob.name = name
    ob.data.name = name
    bpy.context.scene.collection.objects.link(ob)
    M = Matrix.Translation((0, HINGE[0], HINGE[1])) @ Matrix.Rotation(math.radians(-angle), 4, 'X') @ Matrix.Translation((0, -HINGE[0], -HINGE[1]))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.transform(bm, matrix=M, verts=[v for v in bm.verts if lid[v.index]])
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def dark_inside(repo, closed, lid):
    """The chest's colour map with its inside darkened (1997: the open chest is dark red-brown inside, the bands show
    in the lid): the texels of the faces that look into the cavity (body and lid, found on the closed LOD0 mesh) are
    multiplied down. Written beside the states as T_Chest_Open_PR_BC.png; normal and ORM maps stay the Props chest's."""
    from PIL import Image, ImageDraw, ImageFilter
    src = os.path.join(repo, 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Props/Chest_Small/T_Chest_Small_PR_BC.png')
    img = Image.open(src).convert('RGB')
    w, h = img.size
    mask = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(mask)
    me = closed.data
    uv = me.uv_layers.active.data
    rise = 0.165
    R = (0.25 * 0.25 + rise * rise) / (2 * rise); cz = 0.36 + rise - R
    n = 0
    for poly in me.polygons:
        c = poly.center; nrm = poly.normal
        is_lid = all(lid[v] for v in poly.vertices)
        if is_lid:
            # inside of the staves and of the two D ends: looking at the lid's axis, and not on the outer skin
            to_axis = Vector((0.0, -c.y, cz - c.z))
            inside = (nrm.dot(to_axis) > 0.25 * to_axis.length and math.hypot(c.y, c.z - cz) < R - 0.012 and abs(c.x) < 0.43) or (abs(nrm.x) > 0.8 and nrm.x * c.x < 0 and abs(c.x) < 0.425 and c.z > 0.365)
        else:
            in_box = abs(c.x) < 0.425 and abs(c.y) < 0.245 and 0.04 < c.z < 0.362
            to_mid = Vector((-c.x, -c.y, 0.0))
            inside = in_box and ((nrm.z > 0.8 and c.z < 0.07) or (to_mid.length > 1e-4 and nrm.dot(to_mid) > 0.5 * to_mid.length and (abs(c.x) > 0.37 or abs(c.y) > 0.2)))
        if not inside:
            continue
        pts = [(uv[li].uv.x * w, (1.0 - uv[li].uv.y) * h) for li in poly.loop_indices]
        draw.polygon(pts, fill=255)
        n += 1
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(img, np.float32) / 255.0
    m = np.asarray(mask, np.float32)[..., None] / 255.0
    lin = np.power(a, 2.2)
    grey = lin.mean(-1, keepdims=True)
    dark = (lin * 0.75 + grey * 0.25) * np.array((0.30, 0.25, 0.23), np.float32)       # darker, a little less red: old dry wood in shadow
    out = np.power(np.clip(lin * (1 - m) + dark * m, 0, 1), 1 / 2.2)
    dest = os.path.join(KIT, 'chest_states', 'T_Chest_Open_PR_BC.png')
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGB').save(dest, optimize=True)
    print('CHEST inside faces', n, 'of', len(me.polygons), 'texels darkened %.1f %%' % (100.0 * float(m.mean())))
    return dest


def export(obs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    # the same settings as Props/tools/props_merge.py, so the states stand exactly where the Props chest stands
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='Y', axis_up='Z', bake_space_transform=False, use_triangles=True, mesh_smooth_type='EDGE',
                             use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', object_types={'MESH', 'EMPTY'}, colors_type='NONE')


def review(repo, states, path):
    """the six pictures' states in a row, seen as the 1997 pictures of 175 see the chest (from the front right, above), sun and sky"""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    P = os.path.join(repo, 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Props/Chest_Small')
    mat = bpy.data.materials.new('Review_Chest')
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes['Principled BSDF']
    def tex(name, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(P, name)); t.image.colorspace_settings.name = cs; return t
    bc = tex(os.path.join(KIT, 'chest_states', 'T_Chest_Open_PR_BC.png'), 'sRGB'); orm = tex('T_Chest_Small_PR_ORM.png', 'Non-Color'); nm = tex('T_Chest_Small_PR_N.png', 'Non-Color')
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nmap = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(bc.outputs['Color'], b.inputs['Base Color']); nt.links.new(orm.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], b.inputs['Roughness']); nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    nt.links.new(nm.outputs['Color'], nmap.inputs['Color']); nt.links.new(nmap.outputs['Normal'], b.inputs['Normal'])
    for i, ob in enumerate(states):
        ob.data.materials.clear(); ob.data.materials.append(mat)
        ob.location = ((i - (len(states) - 1) / 2) * 1.45, 0, 0)
        ob.rotation_euler = (0, 0, math.radians(-40))
        ob.hide_render = False
    for o in bpy.data.objects:
        if o not in states and o.type == 'MESH':
            o.hide_render = True
    bpy.ops.mesh.primitive_plane_add(size=40)
    g = bpy.context.object
    gm = bpy.data.materials.new('Ground'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.10, 0.19, 0.06, 1)
    gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0
    g.data.materials.append(gm)
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 4.0; sun.data.angle = math.radians(2.0); sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    w = bpy.data.worlds.new('Sky'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.68, 0.9, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    sc.world = w
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 8.9
    d = Vector((0.0, -1.0, 1.0)).normalized()
    cam.location = Vector((0, 0, 0.35)) + d * 20; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 1780, 420
    sc.view_settings.view_transform = 'Standard'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    o = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lods = load(o['repo'])
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            bpy.context.view_layer.objects.active = ob
            assert all(abs(v) < 1e-6 for v in ob.location) and all(abs(v) < 1e-6 for v in ob.rotation_euler), (ob.name, tuple(ob.location), tuple(ob.rotation_euler))
    shown = [lods[0][0]]
    bc = dark_inside(o['repo'], lods[0][0], lods[0][1])
    for frame, angle in sorted(STATES.items()):
        name = 'SM_Chest_Small_Lid%03d_PR' % round(angle)
        obs = [state_mesh(src, lid, angle, '%s_LOD%d' % (name, i)) for i, (src, lid) in enumerate(lods)]
        folder = os.path.join(KIT, 'chest_states', name[3:-3])
        os.makedirs(folder, exist_ok=True)
        export(obs, os.path.join(folder, name + '.fbx'))
        co = np.array([v.co for v in obs[0].data.vertices])
        lo, hi = co.min(0), co.max(0)
        rel = '%s/chest_states/%s/' % (ROOT, name[3:-3])
        m = {'name': name, 'class': 'prop', 'fbx': rel + name + '.fbx', 'material_name': 'MI_Chest_Small_Open',
             'textures': [{'file': ROOT + '/chest_states/T_Chest_Open_PR_BC.png', 'size_px': [2048, 2048], 'channels': 'the Props chest\'s colour map with the inside of body and lid darkened'}],
             'textures_shared': {'N': '/Game/Dink/Photoreal/Props/Textures/T_Chest_Small_PR_N', 'ORM': '/Game/Dink/Photoreal/Props/Textures/T_Chest_Small_PR_ORM'}, 'lod0_triangles': len(obs[0].data.polygons), 'lod1_triangles': len(obs[1].data.polygons), 'lod2_triangles': len(obs[2].data.polygons),
             'bounds_min_m': [round(float(x), 3) for x in lo], 'bounds_max_m': [round(float(x), 3) for x in hi], 'dimensions_m': [round(float(x), 3) for x in hi - lo], 'collision_hulls': 0,
             'lid_angle_deg': angle, 'picture_frame': frame,
             'families': ['175 bonuses/chest/chst1- frame %d' % frame, '176 bonuses/chest/chst2- frame %d' % frame, '177 bonuses/chest/chst3- frame %d' % frame],
             'supersedes': 'SM_Chest_Small_Open_PR (lid at 102 degrees) on this frame' if frame > 2 else 'SM_Chest_Small_PR (closed) on this frame',
             'dresses': 'the iron-bound chest of the Props kit with its lid at %g degrees: the same vertices, normal and ORM maps (Props T_Chest_Small_PR_*), the lid turned about its back hinges; its own colour map only to make the inside dark' % angle,
             'source_note': 'FableF/tools/build_chest_states.py from Props/Chest_Small/SM_Chest_Small_PR.fbx and Props/Chest_Small_Open/SM_Chest_Small_Open_PR.fbx (the lid = the vertices that differ between the two); no new bake',
             'build': 'DINK_CPU=1 blender -b --factory-startup -t 4 --python FableF/tools/build_chest_states.py -- <repository root>',
             'fit': {'pivot': 'base centre, identical to SM_Chest_Small_PR: swap the mesh in place', 'hinge': 'axis along X through (y %g, z %g) m' % HINGE},
             'third_party': [], 'status': 'source delivered'}
        json.dump(m, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
        open(os.path.join(folder, 'manifest.json'), 'a').write('\n')
        shown.append(obs[0])
        print('CHEST state', name, 'frame', frame, 'bounds', m['bounds_min_m'], m['bounds_max_m'])
    if o['review']:
        review(o['repo'], shown, o['review'])


if __name__ == '__main__':
    main()
