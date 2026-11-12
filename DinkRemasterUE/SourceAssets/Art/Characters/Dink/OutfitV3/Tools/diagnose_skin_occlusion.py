"""Read-only source front/back/idle/fist/walk-like deformation review. Noexports."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3');CHARS=ART.parents[1]
# Read the existingEpic walk reference into temporary memory only, never into
# the saved candidate or any authored/exported animation asset.
walk_samples=[];walk_rest={};walk_path=Path('<HOME>/Work/DinkQA/CharacterReference/Manny_Walk_Reference.fbx')
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
records=[]
def diagnose(label):
 ob=bpy.data.objects['SK_Dink_OutfitV3_LOD0'];bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();vertices=[ob.matrix_world@v.co for v in mesh.vertices];faces=[tuple(p.vertices) for p in mesh.polygons];allbvh=BVHTree.FromPolygons(vertices,faces,all_triangles=False);skinfaces=[p.index for p in mesh.polygons if p.material_index==0];skinbvh=BVHTree.FromPolygons(vertices,[faces[i] for i in skinfaces],all_triangles=False);wardfaces=[p.index for p in mesh.polygons if p.material_index==4];wardbvh=BVHTree.FromPolygons(vertices,[faces[i] for i in wardfaces],all_triangles=False);exposed=[];camera=Vector((1.25,2.1,1.65))
 for i in skinfaces:
  p=mesh.polygons[i];center=sum((vertices[j] for j in p.vertices),Vector())/len(p.vertices)
  if not (1.35<center.z<1.54 and .055<abs(center.x)<.24 and center.y>.025):continue
  direction=center-camera;hit,normal,face,dist=allbvh.ray_cast(camera,direction.normalized(),direction.length+.002)
  if hit is None or mesh.polygons[face].material_index!=0 or (hit-center).length>.003:continue
  cloth,n,cf,d=wardbvh.find_nearest(center);exposed.append({'protected_skin_face':i,'center':tuple(center),'area_m2':p.area,'nearest_cloth_distance_m':d,'nearest_cloth_point':tuple(cloth),'skin_outside_cloth_signed_m':(center-cloth).dot(p.normal)})
 cloth_ids={j for i in wardfaces for j in faces[i]};inside=[]
 for j in cloth_ids:
  co=vertices[j]
  if not (1.4<co.z<1.57 and abs(co.x)<.24 and co.y>.025):continue
  point,normal,face,d=skinbvh.find_nearest(co);signed=(co-point).dot(normal)
  if signed<-.001:inside.append({'vertex':j,'depth_m':-signed,'position':tuple(co),'skin_surface_point':tuple(point)})
 records.append({'pose':label,'camera':tuple(camera),'exposed_skin_faces':len(exposed),'exposed_skin_area_m2':sum(r['area_m2'] for r in exposed),'samples':exposed[:24],'inside_wardrobe_vertices':len(inside),'worst_inside':sorted(inside,key=lambda x:-x['depth_m'])[:16]});print('SKIN OCCLUSION',label,'exposedfaces',len(exposed),'area',sum(r['area_m2'] for r in exposed),'clothinside',len(inside),'maxdepth',max((r['depth_m'] for r in inside),default=0),flush=True);ev.to_mesh_clear()
diagnose('ActualEpic idle boundary')
with bpy.data.libraries.load(str(CHARS/'Animations/Unarmed/Dink_Fist.blend'),link=False) as (src,dst):dst.actions=['Dink_Fist_Forward']
action=next(a for a in dst.actions if a);arm.animation_data.action=action;scene.frame_set(8);diagnose('OriginalDink fist frame8')
for index,(frame,matrices) in enumerate(walk_samples):
 idle_pose()
 for bone in arm.pose.bones:
  if bone.name in matrices:bone.matrix=matrices[bone.name];bpy.context.view_layer.update()
 diagnose('ActualEpic walk'+str(index)+' frame'+str(frame))
(ART/'posed_skin_occlusion_diagnosis.json').write_text(json.dumps({'scope':'Read-only actual posed protectedSkin camera-ray and signed nearest-surface tests, no anatomy changes','candidate_sha256':__import__('hashlib').sha256((ART/'SK_Dink_OutfitV3.blend').read_bytes()).hexdigest(),'poses':records},indent=2)+'\n')
