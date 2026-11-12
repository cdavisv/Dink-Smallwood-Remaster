"""Read-only source front/back/idle/fist/walk-like deformation review. Noexports."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ART=Path(Path(__file__).resolve().parents[1]);CHARS=ART.parents[1]
# Read the existingEpic walk reference into temporary memory only, never into
# the saved candidate or any authored/exported animation asset.
walk_samples=[];walk_rest={};walk_path=Path(Path.home()/'Work/DinkQA/CharacterReference/Manny_Walk_Reference.fbx')
if not walk_path.exists():walk_path=Path('/tmp/dink-character-reference/Manny_Walk_Reference.fbx')
if walk_path.exists():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(walk_path),automatic_bone_orientation=False,use_anim=True)
 reference=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');action=reference.animation_data.action
 start,end=action.frame_range
 def normalized_world(matrix,root):
  out=matrix.to_quaternion().to_matrix().to_4x4();out.translation=matrix.translation-root;return out
 bpy.context.scene.frame_set(round(start));bpy.context.view_layer.update();reference_origin=reference.matrix_world.translation.copy()
 for bone in reference.data.bones:
  walk_rest[bone.name]=normalized_world(reference.matrix_world@bone.matrix_local,reference_origin)
 walk_rest['root']=Matrix.Identity(4)
 for fraction in [.20,.70]:
  frame=round(start+(end-start)*fraction);bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();root=reference.matrix_world.translation.copy();matrices={'root':normalized_world(reference.matrix_world,root)}
  for bone in reference.pose.bones:
   matrices[bone.name]=normalized_world(reference.matrix_world@bone.matrix,root)
  walk_samples.append((frame,matrices))
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.animation_data_create();arm.animation_data.action=None;arm.data.pose_position='POSE'
for ob in scene.objects:
 if ob.type=='MESH' and ob.name.startswith('SK_Dink_OutfitV3_LOD'):ob.hide_render=not ob.name.endswith('LOD0')
for ob in list(scene.objects):
 if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True)
scene.world=bpy.data.worlds.new('OutfitV3_ReviewWorld');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.19,.23,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,location,energy,size in [('Key',(3,-4,5),500,4),('Fill',(-3,-2,3),180,3),('Rim',(1,3,4),450,3)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size;ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=location;ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));floor=bpy.context.object;floor.name='ReviewOnlyFloor';mat=bpy.data.materials.new('ReviewOnlyFloor');mat.diffuse_color=(.07,.08,.09,1);floor.data.materials.append(mat)
cam=scene.camera
if cam is None:
 data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0;scene.view_settings.gamma=1
OUT=ART/'Previews';OUT.mkdir(exist_ok=True);records=[]
def render(name,location,target=(0,0,.96),lens=65):
 cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);records.append({'image':name+'.png','pose':pose,'frame':scene.frame_current,'camera':location,'target':target})
idle=json.loads((CHARS/'Animations/Unarmed/idle_boundary_pose.json').read_text())['bones']
def idle_pose():
 arm.animation_data.action=None
 for b in arm.pose.bones:b.rotation_mode='QUATERNION';b.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 for b in arm.pose.bones:
  if b.name in idle:b.matrix=Matrix(idle[b.name]);bpy.context.view_layer.update()
pose='Existing exactEpic idle boundary, unchanged89rig';idle_pose();scene.frame_set(1)

from mathutils.bvhtree import BVHTree
from mathutils.geometry import closest_point_on_tri

def front_hit(tree,mesh,origin,direction,distance):
 traveled=0.;current=origin.copy();culled=0
 for iteration in range(64):
  hit,normal,face,d=tree.ray_cast(current,direction,distance-traveled)
  if hit is None:return None,None,None,None,culled
  traveled+=d
  if normal.dot(direction)<-1e-6:return hit,normal,mesh.loop_triangles[face].polygon_index,traveled,culled
  culled+=1;current=hit+direction*.00001;traveled+=.00001
  if traveled>=distance:break
 return None,None,None,None,culled

records=[]
def diagnose(label,lod=0):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();vertices=[ob.matrix_world@v.co for v in mesh.vertices];faces=[tuple(p.vertices) for p in mesh.polygons];mesh.calc_loop_triangles();allbvh=BVHTree.FromPolygons(vertices,[tuple(t.vertices) for t in mesh.loop_triangles],all_triangles=True);skinfaces=[p.index for p in mesh.polygons if p.material_index==0];skinbvh=BVHTree.FromPolygons(vertices,[tuple(t.vertices) for t in mesh.loop_triangles if t.polygon_index in set(skinfaces)],all_triangles=True);wardfaces=[p.index for p in mesh.polygons if p.material_index==4];wardbvh=BVHTree.FromPolygons(vertices,[faces[i] for i in wardfaces],all_triangles=False);exposed=[];camera=Vector((1.25,2.1,1.65))
 clothing_skin_roi={i for i in skinfaces if 1.30<ob.data.polygons[i].center.z<1.535+.3*ob.data.polygons[i].center.y and ob.data.polygons[i].center.y>-.005 and abs(ob.data.polygons[i].center.x)<.40}
 exposed_ids=set();visible_samples=0
 for tri in mesh.loop_triangles:
  if tri.polygon_index not in clothing_skin_roi:continue
  points=[vertices[i] for i in tri.vertices];center=sum(points,Vector())/3;samples=[center]+[p*.9+center*.1 for p in points]
  for a,b in zip(points,points[1:]+points[:1]):samples.append((a+b)*.45+center*.10)
  for sample in samples:
   direction=sample-camera;hit,normal,face,dist,culled=front_hit(allbvh,mesh,camera,direction.normalized(),direction.length+.0001)
   if hit is not None and face in clothing_skin_roi and mesh.polygons[face].material_index==0:visible_samples+=1;exposed_ids.add(face)
 for i in sorted(exposed_ids):
  p=mesh.polygons[i];center=sum((vertices[j] for j in p.vertices),Vector())/len(p.vertices);cloth,n,cf,d=wardbvh.find_nearest(center);exposed.append({'protected_skin_face':i,'center':tuple(center),'area_m2':p.area,'nearest_cloth_distance_m':d,'nearest_cloth_point':tuple(cloth),'skin_outside_cloth_signed_m':(center-cloth).dot(p.normal)})
 report=json.loads((ART/'integrated_skin_yoke_report.json').read_text());tiles=report['new_unique_atlas_tiles'];skin_tile_count=len(report['lods'][lod]['selected_skin_source_faces']);skin_tiles={tuple(p) for p in tiles[:skin_tile_count]};tile_indices={tuple(v):i for i,v in enumerate(tiles)};all_tiles={tuple(p) for p in tiles};new_faces=[];outward=[];visible_dots=[];culled_count=0
 for pi in wardfaces:
  p=mesh.polygons[pi];values=[mesh.uv_layers[0].data[i].uv for i in p.loop_indices];mean=sum(values,Vector((0,0)))/len(values);tile=(int(mean.y*4096)//16,int((mean.x-1)*4096)//16)
  if tile not in all_tiles:continue
  new_faces.append(pi);center=sum((vertices[i] for i in p.vertices),Vector())/len(p.vertices)
  if tile in skin_tiles:
   source_id=report['lods'][lod]['selected_skin_source_faces'][tile_indices[tile]];source_tris=[t for t in mesh.loop_triangles if t.polygon_index==source_id];projections=[]
   for source_tri in source_tris:
    a,b,c=[vertices[i] for i in source_tri.vertices];point=closest_point_on_tri(center,a,b,c);projections.append(((center-point).length,point,(b-a).cross(c-a).normalized()))
   d,point,n=min(projections,key=lambda row:row[0])
   if d<.040:outward.append({'face':pi,'skin_distance_m':d,'outward_normal_dot':p.normal.dot(n)})
  for cam in [Vector((1.25,2.1,1.65)),Vector((1.9,3.7,1.8)),Vector((2.6,-4.1,1.9))]:
   direction=center-cam;hit,n,face,d,culled=front_hit(allbvh,mesh,cam,direction.normalized(),direction.length+.003);culled_count+=culled
   if hit is not None and face==pi:visible_dots.append(n.dot(direction.normalized()))
 cloth_ids={j for i in wardfaces for j in faces[i]};inside=[]
 for j in cloth_ids:
  co=vertices[j]
  if not (1.4<co.z<1.57 and abs(co.x)<.24 and co.y>.025):continue
  point,normal,face,d=skinbvh.find_nearest(co);signed=(co-point).dot(normal)
  if signed<-.001:inside.append({'vertex':j,'depth_m':-signed,'position':tuple(co),'skin_surface_point':tuple(point)})
 records.append({'new_cloth_faces':len(new_faces),'outward_skin_samples':len(outward),'minimum_outward_dot':min((r['outward_normal_dot'] for r in outward),default=1),'wrong_outward_faces':[r for r in outward if r['outward_normal_dot']<0],'visible_one_sided_yoke_seam_hits':len(visible_dots),'largest_visible_normal_dot_viewray':max(visible_dots,default=-1),'backface_hits_explicitly_culled':culled_count,'lod':lod,'pose':label,'camera':tuple(camera),'clothing_skin_roi_faces':len(clothing_skin_roi),'visible_skin_samples':visible_samples,'exposed_skin_faces':len(exposed),'exposed_skin_area_m2':sum(r['area_m2'] for r in exposed),'samples':exposed[:24],'inside_wardrobe_vertices':len(inside),'worst_inside':sorted(inside,key=lambda x:-x['depth_m'])[:16]});print('SKIN OCCLUSION',label,'exposedfaces',len(exposed),'area',sum(r['area_m2'] for r in exposed),'clothinside',len(inside),'maxdepth',max((r['depth_m'] for r in inside),default=0),flush=True);ev.to_mesh_clear()
def diagnose_all(label):
 for lod in range(4):diagnose(label,lod)
diagnose_all('ActualEpic idle boundary')
with bpy.data.libraries.load(str(CHARS/'Animations/Unarmed/Dink_Fist.blend'),link=False) as (src,dst):dst.actions=['Dink_Fist_Forward']
action=next(a for a in dst.actions if a);arm.animation_data.action=action;scene.frame_set(8);diagnose_all('OriginalDink fist frame8')
for index,(frame,matrices) in enumerate(walk_samples):
 idle_pose()
 for bone in arm.pose.bones:
  if bone.name in matrices:bone.matrix=matrices[bone.name];bpy.context.view_layer.update()
 diagnose_all('ActualEpic walk'+str(index)+' frame'+str(frame))
(ART/'posed_one_sided_render_triangle_audit.json').write_text(json.dumps({'scope':'Whole back/shoulder clothing ROI: immutable restSkinz>1.30m,absx<.40m,y>-.005m, below the actual tilted collar opening with1cm legitimate-neck inset (z<1.535+.3y). Hands and legitimate neck excluded; rear camera rays at face centers, nearvertices and edge midpoints across actualidle/fist/bothwalks. No anatomy changes','candidate_sha256':__import__('hashlib').sha256((ART/'SK_Dink_OutfitV3.blend').read_bytes()).hexdigest(),'poses':records},indent=2)+'\n')
