"""Layout preview for render_previews.py: places layout_440.json in Blender exactly as the Unreal
importer + runtime would (bilinear screen transform, FBX Y mirror, FRotationMatrix), shown in a
north-up Blender frame (preview y = -Unreal y).  Reused kits are linked read-only."""
import bpy, json, math
import numpy as np
from mathutils import Matrix, Vector

SCREEN = 440


def rot_matrix(pitch, yaw, roll):
    P, Y, R = map(math.radians, (pitch, yaw, roll))
    SP, CP, SY, CY, SR, CR = math.sin(P), math.cos(P), math.sin(Y), math.cos(Y), math.sin(R), math.cos(R)
    return np.array([[CP * CY, CP * SY, SP], [SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP],
                     [-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP]])


def build(scene, assets, link_kit, instance, ground, sky_and_sun, camera, ART, UE):
    layout = json.loads((ART / 'layout_440.json').read_text())
    screens = {s['screen']: s for s in json.loads((UE / 'ImportData/screens.json').read_text())['screens']}
    placements = {p['id']: p for p in json.loads((UE / 'ImportData/placements.json').read_text())['placements']}
    c = screens[SCREEN]['corners']; nw, ne, se, sw = [np.array(c[k]) for k in ('nw', 'ne', 'se', 'sw')]
    def world(px, py):
        u, v = px / 600, py / 400
        return nw * (1 - u) * (1 - v) + ne * u * (1 - v) + se * u * v + sw * (1 - u) * v
    center = world(300, 200)
    kits = {}
    kits.update(link_kit(UE / 'SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend',
                         ['SM_Ground_Meadow_20m_01', 'SM_Fence_SplitRail_4m_01', 'SM_Oak_Stonebrook_01', 'SM_Boulder_Fieldstone_01', 'SM_Grass_Meadow_01']))
    kits.update(link_kit(UE / 'SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend', ['SM_Barrel_Oak_01']))
    def render_mesh(name):
        coll = assets.get(name) or kits.get(name)
        obs = [o for o in coll.all_objects if o.type == 'MESH' and not o.name.startswith('UCX_')]
        best = [o for o in obs if o.name == name or o.name.endswith('_LOD0')] or obs
        return best[0].data
    for c_ in assets.values():
        for ob in c_.objects:
            ob.hide_render = True
    S = np.diag([1, -1, 1])
    def place(name, mesh, px, py, z_cm, rot, scale):
        w = world(px, py) - center
        Mr = rot_matrix(*rot) * np.array(scale)[:, None]          # rows scaled (scale applies in local space first)
        A = S @ Mr.T @ S
        M = Matrix(A.tolist()).to_4x4(); M.translation = Vector((w[0], -w[1], z_cm / 100))
        ob = bpy.data.objects.new('L_' + name, render_mesh(mesh)); scene.collection.objects.link(ob); ob.matrix_world = M
        return ob
    for e in layout['elements']:
        place(e['name'], e['mesh'], *e['source_pixel'], e.get('height_cm', 0), e.get('rotation_deg', [0, 0, 0]), e.get('scale', [1, 1, 1]))
    for r in layout['replacements']:
        place(r['origin'], r['mesh'], *r['source_pixel'], r.get('height_cm', 0), r.get('rotation_deg', [0, 0, 0]), r.get('scale', [1, 1, 1]))
    # live originals that stay (Quackers) shown as a small marker only when visible in vision 0: none for 440
    for wv in layout.get('warp_overrides', []):
        w = world(*wv['source_pixel']) - center; ex = wv['extent_cm']
        bpy.ops.mesh.primitive_cube_add(size=1, location=(w[0], -w[1], wv['height_cm'] / 100))
        m = bpy.context.object; m.dimensions = (ex[0] / 50, ex[1] / 50, ex[2] / 50); m.name = 'WarpTriggerMarker'
        mat = bpy.data.materials.new('TriggerMarker'); mat.use_nodes = True
        bs = mat.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value = (1, .1, .05, 1); bs.inputs['Alpha'].default_value = .35
        m.data.materials.append(mat)
    # screen boundary posts at the four corners (helps reading the framing)
    for k in ('nw', 'ne', 'se', 'sw'):
        w = np.array(c[k]) - center
        bpy.ops.mesh.primitive_cylinder_add(radius=.12, depth=3, location=(w[0], -w[1], 1.5))
    sky_and_sun(sun_rot=(math.radians(48), 0, math.radians(-30)), energy=3.0)
    cam_mode = scene.get('layout_cam', 'game')
    camera((0, -40, 34), (0, 2, 0), lens=30)
