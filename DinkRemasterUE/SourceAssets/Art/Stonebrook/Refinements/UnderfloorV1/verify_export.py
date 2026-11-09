"""Independent FBX roundtrip and actual matching-gap-ray triangle witness."""
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import intersect_ray_tri
O=Path(__file__).resolve().parent
p=json.loads((O/'underfloor_plan.json').read_text());m=json.loads((O/'asset_manifest.json').read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
for r in m['files'].values():assert sha(O/r['file'])==r['sha256']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(O/m['files']['fbx']['file']))
objs=list(bpy.context.scene.objects);assert len(objs)==1 and objs[0].type=='MESH'
a=objs[0];me=a.data;me.calc_loop_triangles();vs=[a.matrix_world@v.co for v in me.vertices]
assert len(vs)==24 and len(me.loop_triangles)==44 and len(me.materials)==1 and len(me.uv_layers)==1
bounds=[[min(v[k] for v in vs) for k in range(3)],[max(v[k] for v in vs) for k in range(3)]]
dims=[bounds[1][k]-bounds[0][k] for k in range(3)]
assert all(abs(dims[k]-p['dimensions_m'][k])<.0005 for k in range(3))
assert abs(bounds[0][2])<1e-6 and abs(bounds[1][2]-.02)<1e-6
# Replay in UE world centimetres, including Blender -> UE Y sign.
c=Vector(p['placement_world_cm']);world=[c+Vector((v.x*100,-v.y*100,v.z*100)) for v in vs]
w=p['blue_gap_witness'];origin=Vector(w['camera_world_cm']);target=Vector(w['underfloor_plane_hit_world_cm']);direction=(target-origin).normalized();hits=[]
for tri in me.loop_triangles:
 q=[world[i] for i in tri.vertices];hit=intersect_ray_tri(*q,direction,origin,True)
 if hit is not None and (hit-origin).dot(direction)>0:hits.append(tuple(hit))
error=lambda h:math.dist(h,w['underfloor_plane_hit_world_cm'])
assert hits and min(map(error,hits))<.05
# Confirm closed shell and outward normals after source FBX roundtrip.
edges={}
for poly in me.polygons:
 for i,j in zip(poly.vertices,list(poly.vertices[1:])+[poly.vertices[0]]):edges[tuple(sorted((i,j)))]=edges.get(tuple(sorted((i,j))),0)+1
assert all(n==2 for n in edges.values())
centroid=sum(vs,Vector())/len(vs)
assert all((a.matrix_world.to_3x3()@q.normal).dot(a.matrix_world@q.center-centroid)>0 for q in me.polygons)
assert all(math.isfinite(x) for uv in me.uv_layers[0].data for x in uv.uv)
r={'passed':True,'checks':{'single_mesh':True,'closed_manifold':True,'outward_normals':True,'finite_UV0':True,'one_material':True,'no_UCX':True,'source_hashes_match':True},'fbx_sha256':sha(O/m['files']['fbx']['file']),'vertices':len(vs),'triangles':len(me.loop_triangles),'actual_roundtrip_dimensions_m':dims,'dimension_tolerance_cm':.05,'actual_exported_triangle_gap_ray':{'matching_camera_sha256':w['matching_camera_sha256'],'pixel':w['pixel'],'intersections_world_cm':hits,'expected_top_hit_world_cm':w['underfloor_plane_hit_world_cm'],'nearest_error_cm':min(map(error,hits))},'native_import_tested':False,'runtime_published':False}
(O/'export_verification.json').write_text(json.dumps(r,indent=2)+'\n');print('EXPORTED_GEOMETRY_AND_GAP_RAY_PASS')
