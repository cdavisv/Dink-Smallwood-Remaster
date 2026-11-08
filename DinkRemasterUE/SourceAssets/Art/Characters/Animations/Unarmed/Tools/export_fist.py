"""Source animation gates and armature-only centimetre FBX export, exact shared89rig."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];CHARS=ROOT.parents[1];PROJECT=ROOT.parents[4]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Dink_Fist.blend'));scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.data.pose_position='POSE';arm.animation_data.action=bpy.data.actions['Dink_Fist_Forward']
rest={b.name:{'parent':b.parent.name if b.parent else None,'matrix':[list(r) for r in b.matrix_local]} for b in arm.data.bones}
assert len(rest)==89 and [n for n,r in rest.items() if r['parent'] is None]==['root']
assert max(abs(arm.data.bones['root'].matrix_local[r][c]-Matrix.Identity(4)[r][c]) for r in range(4) for c in range(4))<1e-6
start={};end={};foot_start={};maxfoot=maxroot=maxscale=maxjoint=0;finite=True;impact=[]
for frame in range(1,18):
 scene.frame_set(frame);bpy.context.view_layer.update()
 for b in arm.pose.bones:
  finite=finite and all(math.isfinite(x) for r in b.matrix for x in r);sc=b.matrix.to_scale();maxscale=max(maxscale,max(abs(x-1) for x in sc))
 maxroot=max(maxroot,arm.pose.bones['root'].matrix.translation.length)
 for name in ['foot_l','foot_r','ball_l','ball_r']:
  pos=arm.pose.bones[name].matrix.translation
  if frame==1:foot_start[name]=pos.copy()
  maxfoot=max(maxfoot,(pos-foot_start[name]).length)
 for upper,child in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l'),('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')]:
  expected=arm.pose.bones[upper].matrix@arm.data.bones[upper].matrix_local.inverted()@arm.data.bones[child].head_local
  maxjoint=max(maxjoint,(expected-arm.pose.bones[child].head).length)
 if frame in [1,17]:
  snap={b.name:b.matrix.copy() for b in arm.pose.bones}
  if frame==1:start=snap
  else:end=snap
 if frame==8:impact=list(arm.pose.bones['hand_r'].head)
seam=max(abs(start[n][r][c]-end[n][r][c]) for n in start for r in range(4) for c in range(4))
report={'schema':'dink-animation-validation/1','passed':finite and maxroot<.0001 and maxfoot<.0001 and maxscale<.001 and maxjoint<.001 and seam<.0001,'bone_count':len(rest),'finite_all_frames':finite,'root_motion_m':maxroot,'maximum_foot_displacement_m':maxfoot,'maximum_global_scale_error':maxscale,'maximum_arm_joint_gap_m':maxjoint,'start_end_pose_matrix_max_difference':seam,'duration_s':.4,'fps':40,'frames':[1,17],'impact_frame':8,'impact_s':.175,'impact_wrist_m':impact,'rest_bones':rest,'notes':'Feet and idle boundaries preserved; not a looped attack. Equal endpoints permit clean return to locomotion. Gameplay independently owns original impact timing/damage.'}
(ROOT/'fist_validation.json').write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']:raise RuntimeError('Fist pose gates failed '+str({k:v for k,v in report.items() if k!='rest_bones'}))
row={'schema':'dink-character-animation/1','animations':{'Fist':{'fbx':'Export/A_Dink_Fist.fbx','skeleton_from_mesh':'/Game/Dink/Hero/SK_Dink.SK_Dink','content_folder':'/Game/Dink/Hero/Animations','asset_name':'AN_Dink_Fist','action':'Dink_Fist_Forward','source_blend':'Dink_Fist.blend','loop':False,'fps':40,'frames':[1,17],'duration_s':.4,'impact_s':.175,'impact_frame':8,'source_sequences':[102,104,106,108],'root_motion':False,'mesh_reference':'../../Dink/HandBindingV2/SK_Dink_Hands.blend','forward':'Blender-Y / importedmesh+Y / existingplayerrelativeYaw-90→actor+X'}},'status':'candidate','gameplay':'Cosmetic only. No damage/notify authority; native sequence/pending-hit system remains authoritative.','source':'Original project-authored punch keyframes; exact existing Epic89bone compatibility rig and MM_Idle boundary pose, existing CC0-basedDink preview reference. SeeREADME for separate provenance.'}
(ROOT/'animation_manifest.json').write_text(json.dumps(row,indent=2)+'\n')
# Never save this temporary centimetre conversion over the editable metres source.
arm.animation_data.action=None;arm.data.pose_position='REST';bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for bone in arm.data.edit_bones:bone.head*=100;bone.tail*=100
bpy.ops.object.mode_set(mode='OBJECT');scene.unit_settings.scale_length=.01
for action in bpy.data.actions:
 for layer in action.layers:
  for strip in layer.strips:
   for slot in action.slots:
    bag=strip.channelbag(slot)
    if bag:
     for curve in bag.fcurves:
      if curve.data_path.endswith('.location'):
       for key in curve.keyframe_points:key.co.y*=100;key.handle_left.y*=100;key.handle_right.y*=100
arm.data.pose_position='POSE';arm.animation_data.action=bpy.data.actions['Dink_Fist_Forward'];scene.render.fps=40;scene.frame_start=1;scene.frame_end=17;scene.frame_set(1)
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/A_Dink_Fist.fbx'),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_space_transform=True,add_leaf_bones=False,primary_bone_axis='Y',secondary_bone_axis='X',use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='STRIP',embed_textures=False,use_custom_props=False)
print('FIST EXPORT PASS', {k:v for k,v in report.items() if k not in ['rest_bones','notes']},flush=True)
