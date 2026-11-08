import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(__file__).resolve().parent;P=W/'Stonebrook_InteriorVista_Candidate_V3.blend';bpy.ops.wm.open_mainfile(filepath=str(P));bpy.context.view_layer.update();j=json.loads((W/'placement_proposal.json').read_text());room=j['room_clear_rectangle_blender_m'];violations=[];transforms=[];trees=[];grounds=[]
for row in j['instances']:
 o=bpy.data.objects.get(row['name']);assert o is not None,row['name'];assert (o.location-Vector(row['local_blender_m'])).length<1.e-4,row['name'];assert row['collision'] is False and row['camera_occluder'] is False
 pts=[o.matrix_world@Vector(p) for p in o.bound_box];lo=[min(p[k] for p in pts) for k in range(3)];hi=[max(p[k] for p in pts) for k in range(3)]
 outside=hi[0]<=room[0]+.001 or lo[0]>=room[1]-.001 or hi[1]<=.001 or lo[1]>=room[3]-.001
 if not outside:violations.append(row['name'])
 transforms.append({'name':row['name'],'min_scene_m':lo,'max_scene_m':hi,'blender_location_matches_proposal':True})
 if row['name'].startswith('SM_VistaGround'):
  verts=[o.matrix_world@v.co for v in o.data.vertices];faces=[tuple(p.vertices) for p in o.data.polygons];grounds.append(BVHTree.FromPolygons(verts,faces))
assert not violations,violations
uncovered=[];covered=0
for xi in range(-30,31,2):
 for yi in range(-30,23,2):
  x=xi+.25;y=yi+.25 # Interior samples avoid BVH half-open ownership of shared tile edges.
  if -8<x<8 and 0<y<13.5:continue
  found=any(b.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),20)[0] is not None for b in grounds)
  if found:covered+=1
  else:uncovered.append([x,y])
assert not uncovered,uncovered
for x,y in [(-6,2),(0,2),(6,2),(-6,8),(0,8),(6,8),(-6,12),(0,12),(6,12)]:assert not any(b.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),20)[0] is not None for b in grounds),'Vista ground beneath room'
by={x['name']:x for x in transforms};left=by['Vista_FenceSouth5']['max_scene_m'][0];right=by['Vista_FenceSouth7']['min_scene_m'][0];assert right-left>3.7
path=by['Vista_DirtPath0'];assert path['max_scene_m'][1]<0 and path['min_scene_m'][0]<0<path['max_scene_m'][0]
step=by['SM_Doorstep_StonebrookVista_01'];assert abs(step['max_scene_m'][2])<1e-5 and step['max_scene_m'][1]<=.001
out={'candidate_scene_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'all_instance_count':len(j['instances']),'new_asset_count':len(j['new_meshes']),'original_cottage_instance_omitted':not any(x['name']=='Vista_DinksCottage' for x in j['instances']),'room_intrusion_count':0,'actual_mesh_ground_samples':covered,'uncovered_ground_samples':uncovered,'nine_independent_inside_room_samples_have_no_vista_ground':True,'gate_clear_width_m':right-left,'lane_starts_outside_door_and_spans_anchor':True,'threshold_top_matches_room_z0':True,'all_proposed_collisions_disabled':True,'all_proposed_camera_occluders_disabled':True,'instance_bounds':transforms,'scope':'Actual saved Blender scene transforms and BVH geometry; no UE import or runtime changes'};(W/'scene_geometry_checks.json').write_text(json.dumps(out,indent=2)+'\n');print('VISTA_SCENE_GEOMETRY_PASS',covered,'ground samples')
