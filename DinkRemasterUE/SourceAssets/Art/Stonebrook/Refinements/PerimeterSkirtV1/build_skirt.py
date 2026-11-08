"""Render-only closed rim inside the actual floor contour; no native writes."""
from pathlib import Path
import hashlib
import json
import math
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PLAN = json.loads((ROOT / 'underfloor_plan.json').read_text())
PINS = json.loads((ROOT / 'input_pins.json').read_text())
for name, digest in PINS.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
NAME = 'SM_Stonebrook_PerimeterSkirt_V1'
CENTER = PLAN['placement_world_cm']
points = [((p[0] - CENTER[0]) / 100, -(p[1] - CENTER[1]) / 100)
          for p in PLAN['actual_floor_outer_convex_contour_world_cm']]
area = sum(points[i][0] * points[(i + 1) % len(points)][1] -
           points[(i + 1) % len(points)][0] * points[i][1] for i in range(len(points))) / 2
if area < 0:
    points.reverse()
n = len(points)
assert n == 12
low = [min(p[k] for p in points) for k in range(2)]
high = [max(p[k] for p in points) for k in range(2)]
mid = [(a + b) / 2 for a, b in zip(low, high)]

def shrink(inset_m):
    # Preserve all tiny bevel facets. A normal offset larger than their radius
    # would collapse those facets; nested affine rings retain their topology.
    return [tuple(mid[k] + (p[k] - mid[k]) * (1 - 2 * inset_m / (high[k] - low[k]))
                  for k in range(2)) for p in points]

def inside(p, polygon):
    return all((polygon[(i + 1) % len(polygon)][0] - a[0]) * (p[1] - a[1]) -
               (polygon[(i + 1) % len(polygon)][1] - a[1]) * (p[0] - a[0]) >= -1e-10
               for i, a in enumerate(polygon))

outer, inner = shrink(.001), shrink(.008)
assert all(inside(p, points) for p in outer + inner)
assert all(inside(p, outer) for p in inner)
bottom, top = 0., .178  # world -18cm to -0.2cm
vertices = [(x, y, z) for z in (bottom, top) for ring in (outer, inner) for x, y in ring]
faces = []
for i in range(n):
    j = (i + 1) % n
    faces.extend([(i, j, 2*n+j, 2*n+i),
                  (n+j, n+i, 3*n+i, 3*n+j),
                  (2*n+i, 2*n+j, 3*n+j, 3*n+i),
                  (j, i, n+i, n+j)])

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    bpy.data.collections.remove(collection)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
collection = bpy.data.collections.new(NAME)
scene.collection.children.link(collection)
collection['dink_class'] = 'building'
collection['dink_path'] = 'Stonebrook/Refinements/PerimeterSkirtV1'
collection['dink_nanite'] = 'yes'
collection['dink_render_only'] = True
collection['dink_collision_exception'] = 'Authorized render-only seam closure; no UCX, collision, navigation or overlaps.'
mesh = bpy.data.meshes.new(NAME)
mesh.from_pydata(vertices, [], faces)
mesh.update()
assert not mesh.validate()
obj = bpy.data.objects.new(NAME, mesh)
collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
if bm.calc_volume(signed=True) < 0:
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
assert all(e.is_manifold for e in bm.edges)
assert all(f.calc_area() > 1e-10 for f in bm.faces)
volume = bm.calc_volume(signed=True)
assert volume > 0
bm.to_mesh(mesh)
bm.free()
uv = mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    # Disjoint face squares, without implying a texture-density/bake contract.
    for loop, coord in zip(poly.loop_indices, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop].uv = ((poly.index % 8 + .05 + .9 * coord[0]) / 8,
                            (poly.index // 8 + .05 + .9 * coord[1]) / 6)
mat = bpy.data.materials.new(PLAN['material']['name'])
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (*PLAN['material']['base_color_linear'], 1)
bsdf.inputs['Roughness'].default_value = .96
bsdf.inputs['Metallic'].default_value = 0
bsdf.inputs['Specular IOR Level'].default_value = .25
mesh.materials.append(mat)
for key, value in {'native_collision': 'NoCollision', 'native_navigation': False,
                   'native_overlaps': False, 'camera_occluder': False}.items():
    obj[key] = value
bpy.context.view_layer.update()
size = [float(x) for x in obj.dimensions]
assert len(mesh.vertices) == 48
assert sum(len(p.vertices) - 2 for p in mesh.polygons) == 96
blend = ROOT / 'PerimeterSkirtV1.blend'
fbx = ROOT / (NAME + '.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
    global_scale=1, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
    axis_forward='Y', axis_up='Z', bake_space_transform=False,
    use_mesh_modifiers=True, use_triangles=True, mesh_smooth_type='FACE',
    use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
package = '/Game/Dink/Kits/Stonebrook/Refinements/PerimeterSkirtV1/' + NAME
manifest = {'schema': 'dink-perimeter-skirt/1', 'name': NAME,
    'files': {p.name: sha(p) for p in (blend, fbx)},
    'dimensions_m': size, 'vertices': 48, 'triangles': 96, 'material_slots': 1,
    'manifold': True, 'signed_volume_m3': volume,
    'placement_world_cm': CENTER, 'world_top_cm': -.2, 'world_base_cm': -18,
    'outer_axis_inset_cm': .1, 'inner_axis_inset_cm': .8,
    'offset_method': 'Nested axiswise contraction about actual contour bounds; retains all12 bevel corners.',
    'inside_original_floor_contour': True, 'source_UCX_count': 0,
    'floor_binding_signature': PLAN['floor_transform_signature_sha256'],
    'native_source_vertices_sha256': PLAN['native_source_vertices_sha256'],
    'input_sha256': PINS, 'material': PLAN['material'],
    'runtime_policy': PLAN['runtime_policy'],
    'guide_collision_exception': collection['dink_collision_exception'],
    'proposed_package': package,
    'qualification': 'Observed perimeter-escape rays require FBX/native checks; residual0.2cm top clearance is not a universal coverage proof.',
    'previous_underfloor_or_floor_modified': False, 'native_published': False}
(ROOT / 'asset_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
context = {'schema': 'dink-art/1', 'screen': 1,
    'context': {'visibility': 'owner_screen_only', 'render_only': True},
    'source': 'SourceAssets/Art/Stonebrook/Refinements/PerimeterSkirtV1/asset_manifest.json',
    'assets': [{'mesh': package + '.' + NAME, 'expected_size_cm': [v*100 for v in size],
                'expected_lods': 1, 'bounds_tolerance_cm': 1}],
    'elements': [{'name': 'StartingHousePerimeterSkirtV1', 'mesh': package + '.' + NAME,
        'world_cm': CENTER, 'rotation_deg': [0, 0, 0], 'scale': [1, 1, 1],
        'collision': False, 'camera_occluder': False}]}
(ROOT / 'stonebrook_perimeter_skirt_v1.context.draft.json').write_text(json.dumps(context, indent=2) + '\n')
print('SKIRT_SOURCE_READY', json.dumps(manifest), flush=True)
