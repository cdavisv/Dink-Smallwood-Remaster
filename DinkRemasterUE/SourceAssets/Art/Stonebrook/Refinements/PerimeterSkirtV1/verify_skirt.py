"""Independent exported-FBX geometry and seven native gap-ray replays."""
from pathlib import Path
import hashlib
import json
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import intersect_ray_tri

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'asset_manifest.json').read_text())
for name, digest in manifest['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
fbx = next(name for name in manifest['files'] if name.endswith('.fbx'))
bpy.ops.import_scene.fbx(filepath=str(root / fbx))
objects = list(bpy.context.scene.objects)
assert len(objects) == 1 and objects[0].type == 'MESH'
obj = objects[0]
mesh = obj.data
mesh.calc_loop_triangles()
vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
assert len(vertices) == 48 and len(mesh.loop_triangles) == 96
assert len(mesh.materials) == 1 and len(mesh.uv_layers) == 1
assert all(math.isfinite(x) for uv in mesh.uv_layers[0].data for x in uv.uv)
bounds = [[min(v[k] for v in vertices) for k in range(3)],
          [max(v[k] for v in vertices) for k in range(3)]]
size = [bounds[1][k] - bounds[0][k] for k in range(3)]
assert all(abs(a - b) < .00001 for a, b in zip(size, manifest['dimensions_m']))
bm = bmesh.new()
bm.from_mesh(mesh)
assert all(e.is_manifold for e in bm.edges)
volume = bm.calc_volume(signed=True)
assert volume > 0
bm.free()
diagnosis = json.loads((root / 'north_floor_right_ray_diagnosis.json').read_text())
center = manifest['placement_world_cm']
camera = diagnosis['camera']
origin = Vector(((camera[0]-center[0])/100, -(camera[1]-center[1])/100,
                 (camera[2]-center[2])/100))
misses = [r for r in diagnosis['rays'] if r['blue_mask'] and
          r['hit_distance_cm']['floor'] is None and r['hit_distance_cm']['underfloor'] is None]
assert len(misses) == 7
results = []
for ray in misses:
    d = ray['direction']
    direction = Vector((d[0], -d[1], d[2]))
    hits = []
    normal_matrix = obj.matrix_world.inverted().transposed().to_3x3()
    for triangle in mesh.loop_triangles:
        hit = intersect_ray_tri(*(vertices[i] for i in triangle.vertices), direction, origin, True)
        if hit is not None and (hit-origin).dot(direction) > 0:
            facing = (normal_matrix @ triangle.normal).normalized().dot(direction)
            hits.append((hit, float(facing)))
    assert hits, ray['pixel']
    nearest, facing = min(hits, key=lambda h: (h[0]-origin).length)
    assert facing < 0, 'Nearest source surface must face the measured ray camera'
    world = [center[0]+nearest.x*100, center[1]-nearest.y*100, center[2]+nearest.z*100]
    assert -18.01 <= world[2] <= -.19
    results.append({'pixel': ray['pixel'], 'original_RGB': ray['RGB'],
                    'new_skirt_hit_world_cm': world, 'intersections': len(hits),
                    'nearest_front_facing_normal_dot_ray': facing})
report = {'passed': True, 'fbx_sha256': manifest['files'][fbx],
    'vertices': 48, 'triangles': 96, 'closed_manifold': True, 'signed_volume_m3': volume,
    'finite_nonmissing_UV0': True, 'materials': 1, 'UCX': 0,
    'roundtrip_dimensions_m': size, 'dimension_tolerance_cm': .001,
    'actual_native_gap_rays_replayed': len(results), 'ray_results': results,
    'native_imported': False, 'native_rendered': False,
    'qualification': 'Only the seven measured source-geometry misses are proven. Residual0.2cm upper clearance, Nanite, additional angles and lighting require native review.'}
(root / 'export_verification.json').write_text(json.dumps(report, indent=2) + '\n')
print('EXPORTED_SKIRT_AND_SEVEN_NATIVE_GAP_RAYS_PASS', flush=True)
