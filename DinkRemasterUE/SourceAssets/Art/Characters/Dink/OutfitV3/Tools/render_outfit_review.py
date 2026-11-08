"""Read-only source front/back/idle/fist/walk-like deformation review. Noexports."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ART=Path(__file__).resolve().parents[1];CHARS=ART.parents[1]
# Read the existingEpic walk reference into temporary memory only, never into
# the saved candidate or any authored/exported animation asset.
walk_samples=[];walk_rest={};walk_path=Path('/home/artist/Work/DinkQA/CharacterReference/Manny_Walk_Reference.fbx')
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
# Preview the new Wardrobe material with Unreal's one-sided surface behavior.
# This graph wrapper exists in render memory only; the source is never saved.
wardmat=bpy.data.materials['MI_Dink_WardrobeV3'];nodes=wardmat.node_tree.nodes;links=wardmat.node_tree.links;surface=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');original=surface.inputs['Surface'].links[0].from_socket;geo=nodes.new('ShaderNodeNewGeometry');transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links.new(geo.outputs['Backfacing'],mix.inputs[0]);links.new(original,mix.inputs[1]);links.new(transparent.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],surface.inputs['Surface'])
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
render('outfit_idle_front',(0,-4.5,1.55));render('outfit_idle_threequarter',(2.6,-4.1,1.9));render('outfit_idle_back',(0,4.4,1.55));render('outfit_torso_detail',(0,-2.4,1.55),(0,-.015,1.28),75);render('outfit_backpack_detail',(1.25,2.1,1.65),(0,.12,1.28),75)
with bpy.data.libraries.load(str(CHARS/'Animations/Unarmed/Dink_Fist.blend'),link=False) as (src,dst):dst.actions=['Dink_Fist_Forward']
action=next(a for a in dst.actions if a);arm.animation_data.action=action;scene.render.fps=40;scene.frame_set(8);bpy.context.view_layer.update();pose='Existing originalDink_Fist_Forward frame8/175ms, noanimationchanges'
render('outfit_fist_impact',(2.6,-4.1,1.9));render('outfit_fist_side',(3.5,-.8,1.8));render('outfit_fist_back',(1.9,3.7,1.8))
walk_mismatch=0.
if walk_samples:
 walk_mismatch=max(max(abs(walk_rest[b.name][r][c]-b.matrix_local[r][c]) for r in range(4) for c in range(4)) for b in arm.data.bones if b.name in walk_rest)
 for index,(frame,matrices) in enumerate(walk_samples):
  idle_pose();pose='ExistingEpic MF_Unarmed_Walk_Fwd reference frame'+str(frame)+'; roottranslation removedforframing, noanimationexport'
  for bone in arm.pose.bones:
   if bone.name in matrices:bone.matrix=matrices[bone.name];bpy.context.view_layer.update()
  render('outfit_walk_reference_'+str(index)+'_front',(2.6,-4.1,1.9));render('outfit_walk_reference_'+str(index)+'_back',(1.9,3.7,1.8))
else:
 idle_pose();pose='SOURCE WALK-LIKE JOINTDEFORMATION FIXTURE only; noactualwalkreference available'
 def rotate_world(name,axis,angle):
  b=arm.pose.bones[name];at=b.head.copy();m=Quaternion(Vector(axis),math.radians(angle)).to_matrix().to_4x4()@b.matrix;m.translation=at;b.matrix=m;bpy.context.view_layer.update()
 for name,axis,angle in [('thigh_l',(1,0,0),-25),('calf_l',(1,0,0),32),('thigh_r',(1,0,0),20),('calf_r',(1,0,0),10),('upperarm_l',(1,0,0),18),('upperarm_r',(1,0,0),-15),('spine_03',(0,0,1),-4)]:rotate_world(name,axis,angle)
 render('outfit_walk_fixture_front',(2.6,-4.1,1.9));render('outfit_walk_fixture_back',(1.9,3.7,1.8))
(ART/'preview_review_report.json').write_text(json.dumps({'stage':'SOURCE VISUAL REVIEW ONLY; nofinalexports/imports/manifests/ledger','source_blend':'SK_Dink_OutfitV3.blend','existing_idle_and_fist_reference':True,'walk_reference_existing_Epic_only':bool(walk_samples),'walk_reference_rest_matrix_max_error':walk_mismatch,'walk_reference_root_translation_removed_for_framing':bool(walk_samples),'walk_animation_exported':False,'images':records},indent=2)+'\n');print('OUTFIT SOURCE PREVIEWS COMPLETE',len(records),flush=True)
