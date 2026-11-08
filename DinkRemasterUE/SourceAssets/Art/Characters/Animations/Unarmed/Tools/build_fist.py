"""Original hand-keyed comic fist on exact project89-bone rig; no hero edits.
Start/end sample is existing Epic MM_Idle (reference-only compatibility pose).
"""
import bpy,json,math,sys,os
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parents[1];CHARS=ROOT.parents[1]
for p in ['Export','Previews']: (ROOT/p).mkdir(parents=True,exist_ok=True)
# Cached exact current idle boundary; regeneration can use the official projectFBX.
cache=ROOT/'idle_boundary_pose.json'
if cache.exists():
 idle={n:Matrix(m) for n,m in json.loads(cache.read_text())['bones'].items()}
else:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.fbx(filepath=os.environ.get('DINK_IDLE_REFERENCE','/tmp/dink-character-reference/Manny_Idle.fbx'),automatic_bone_orientation=False,use_anim=True)
 ref=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
 idle={b.name:b.matrix.copy() for b in ref.pose.bones}
 for m in idle.values():m.translation*=.01
bpy.ops.wm.open_mainfile(filepath=os.environ.get('DINK_PREVIEW_BLEND',str(CHARS/'Dink/HandBindingV2/SK_Dink_Hands.blend')))
scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.animation_data_create();arm.animation_data.action=None;arm.data.pose_position='POSE'
# Preserve all existing texture dependencies across the new source location.
for im in bpy.data.images:
 if im.filepath:im.filepath=bpy.path.abspath(im.filepath)
for b in arm.pose.bones:
 b.rotation_mode='QUATERNION';b.matrix_basis=Matrix.Identity(4)
for b in arm.pose.bones:
 if b.name in idle:b.matrix=idle[b.name];bpy.context.view_layer.update()
base={b.name:b.matrix_basis.copy() for b in arm.pose.bones};baseworld={b.name:b.matrix.copy() for b in arm.pose.bones};rest={b.name:b.matrix_local.copy() for b in arm.data.bones}
# Existing source mesh is a clearly labeled preview reference, never an FBX output.
for ob in list(scene.objects):
 if ob.type=='MESH' and ob.name.startswith('SK_Dink') and '_LOD' in ob.name and not ob.name.endswith('_LOD0'):bpy.data.objects.remove(ob,do_unlink=True)
mesh=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('SK_Dink') and o.name.endswith('_LOD0'));mesh.hide_render=False;mesh['reference_only']='Existing SK_Dink unchanged anatomy/wardrobe; not newly authored geometry, not exported.'
scene.render.fps=40;scene.frame_start=1;scene.frame_end=17
old=bpy.data.actions.get('Dink_Fist_Forward')
if old:bpy.data.actions.remove(old)
act=bpy.data.actions.new('Dink_Fist_Forward');act.use_fake_user=True;arm.animation_data.action=act
# Pose envelopes in source seconds. Source hitframe3 entersat.175, exactframe8@40fps.
keys=[(0,0,0),(.075,-.35,1),(.125,.15,1),(.175,1,1),(.225,.78,1),(.250,.48,1),(.325,.15,.45),(.400,0,0)]
def envelope(t,column):
 for i in range(len(keys)-1):
  if keys[i][0]<=t<=keys[i+1][0]:
   u=(t-keys[i][0])/(keys[i+1][0]-keys[i][0]);u=u*u*(3-2*u);return keys[i][column]*(1-u)+keys[i+1][column]*u
 return 0

def add_world_rotation(name,axis,angle):
 # Add a local-axis rotation to the measured idle baseline, retainingresttranslation.
 b=arm.pose.bones[name];local=b.matrix.to_3x3().inverted()@Vector(axis);b.rotation_quaternion=b.rotation_quaternion@Quaternion(local.normalized(),angle)

def posed(name,h,semantic_rest_direction,new_direction):
 q=Vector(semantic_rest_direction).rotation_difference(Vector(new_direction));m=q.to_matrix().to_4x4()@rest[name];m.translation=h;return m

def solve_arm(side,wrist,strength):
 upper='upperarm_'+side;lower='lowerarm_'+side;hand='hand_'+side;ub=arm.data.bones[upper];lb=arm.data.bones[lower];hb=arm.data.bones[hand]
 bpy.context.view_layer.update();h=arm.pose.bones[upper].head.copy();l1=(lb.head_local-ub.head_local).length;l2=(hb.head_local-lb.head_local).length;target=Vector(wrist)
 delta=target-h;distance=min(delta.length,l1+l2-.003);direction=delta.normalized();bend=Vector((-1 if side=='r' else 1,.15,-.65));perp=bend-direction*bend.dot(direction);perp.normalize();a=(l1*l1-l2*l2+distance*distance)/(2*distance);knee=h+direction*a+perp*math.sqrt(max(0,l1*l1-a*a));target=h+direction*distance
 updir=lb.head_local-ub.head_local;lowdir=hb.head_local-lb.head_local
 arm.pose.bones[upper].matrix=posed(upper,h,updir,knee-h);bpy.context.view_layer.update();arm.pose.bones[lower].matrix=posed(lower,knee,lowdir,target-knee);bpy.context.view_layer.update()
 q=lowdir.rotation_difference(target-knee);punchrot=(q.to_matrix()@rest[hand].to_3x3()).to_quaternion()
 if side=='r':
  mid=arm.data.bones['middle_01_r'].head_local-hb.head_local;lateral=arm.data.bones['index_01_r'].head_local-arm.data.bones['pinky_01_r'].head_local;pn=mid.cross(lateral).normalized()
  if pn.x<0:pn*=-1
  current=punchrot@(rest[hand].to_3x3().inverted()@pn);axis=(target-knee).normalized();a=current-axis*current.dot(axis);desired=Vector((0,0,-1));b=desired-axis*desired.dot(axis)
  if a.length>.001 and b.length>.001:
   a.normalize();b.normalize();angle=math.atan2(axis.dot(a.cross(b)),a.dot(b));punchrot=Quaternion(axis,angle)@punchrot
 idlerot=baseworld[hand].to_quaternion();rotation=idlerot.slerp(punchrot,strength)
 m=rotation.to_matrix().to_4x4();m.translation=target;arm.pose.bones[hand].matrix=m;bpy.context.view_layer.update()

def curl_fingers(side,strength):
 # Curl toward anatomicalpalmnormal, independentlyof world handorientation.
 h=arm.data.bones['hand_'+side];mid=arm.data.bones['middle_01_'+side].head_local-h.head_local
 lateral=arm.data.bones['index_01_'+side].head_local-arm.data.bones['pinky_01_'+side].head_local
 normal=mid.cross(lateral).normalized();medial=Vector((1 if side=='r' else -1,0,0))
 if normal.dot(medial)<0:normal*=-1
 for finger in ['index','middle','ring','pinky']:
  for joint,angle in [(1,1.35),(2,1.50),(3,.90)]:
   n='%s_%02d_%s'%(finger,joint,side)
   if n not in arm.data.bones:continue
   b=arm.data.bones[n];nextname='%s_%02d_%s'%(finger,joint+1,side);prevname='%s_%02d_%s'%(finger,joint-1,side)
   d=((arm.data.bones[nextname].head_local-b.head_local) if nextname in arm.data.bones else (b.head_local-arm.data.bones[prevname].head_local)).normalized();axis=d.cross(normal)
   if axis.length<.001:axis=lateral.copy()
   local=b.matrix_local.to_3x3().inverted()@axis.normalized();pb=arm.pose.bones[n];pb.rotation_quaternion=base[n].to_quaternion().slerp(Quaternion(local.normalized(),angle),strength)
 # Anatomical index adduction closes the lateral gap instead of overcurling DIP.
 n='index_01_'+side;local=arm.data.bones[n].matrix_local.to_3x3().inverted()@normal;pb=arm.pose.bones[n];pb.rotation_quaternion=Quaternion(local,(-.10 if side=='r' else .10)*strength)@pb.rotation_quaternion
 for j,angle in [(1,.95),(2,.95),(3,.80)]:
  n='thumb_%02d_%s'%(j,side)
  if n in arm.pose.bones:
   bone=arm.data.bones[n];nextname='thumb_%02d_%s'%(j+1,side);prevname='thumb_%02d_%s'%(j-1,side)
   d=((arm.data.bones[nextname].head_local-bone.head_local) if nextname in arm.data.bones else (bone.head_local-arm.data.bones[prevname].head_local)).normalized()
   target=(arm.data.bones['index_01_'+side].head_local-bone.head_local).normalized() if j==1 else normal
   axis=d.cross(target)
   if axis.length<.001:axis=lateral
   local=bone.matrix_local.to_3x3().inverted()@axis.normalized();arm.pose.bones[n].rotation_quaternion=base[n].to_quaternion().slerp(Quaternion(local.normalized(),angle),strength)

 # Lay the distal thumb across the outside of the index/middle knuckles.
 # Imported FBXtails aredisplayaxes, so use actual previous-joint direction.
 bpy.context.view_layer.update()
 n='thumb_03_'+side;pb=arm.pose.bones[n];bone=arm.data.bones[n];head=pb.head.copy();target=arm.pose.bones['middle_03_'+side].head.copy();d=bone.head_local-arm.data.bones['thumb_02_'+side].head_local
 q=d.rotation_difference(target-head);wanted=(q.to_matrix()@bone.matrix_local.to_3x3()).to_quaternion();rotation=pb.matrix.to_quaternion().slerp(wanted,strength);m=rotation.to_matrix().to_4x4();m.translation=head;pb.matrix=m;bpy.context.view_layer.update()


report={'schema':'dink-animation-source/1','name':'Dink_Fist_Forward','fps':40,'frames':[1,17],'duration_s':.4,'impact_s':.175,'impact_frame':8,'source_sequences':[102,104,106,108],'source_frame_delays_ms':[75,100,75,75,75],'source_special_frame':3,'idle_reference':'/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle, exportedfirstframe','root_motion':False,'bones':89,'frames_measured':[]}
for frame in range(1,18):
 scene.frame_set(frame);t=(frame-1)/40;drive=envelope(t,1);fist=envelope(t,2)
 for b in arm.pose.bones:b.matrix_basis=base[b.name].copy()
 bpy.context.view_layer.update()
 for n,weight in [('spine_02',.15),('spine_03',.25),('spine_04',.30),('spine_05',.30)]:
  add_world_rotation(n,(0,0,1),.38*drive*weight);add_world_rotation(n,(1,0,0),.14*max(0,drive)*weight);bpy.context.view_layer.update()
 add_world_rotation('neck_01',(0,0,1),-.11*drive);bpy.context.view_layer.update()
 if abs(drive)>.000001 or fist>.000001:
  baseline_r=baseworld['hand_r'].translation;baseline_l=baseworld['hand_l'].translation
  # Guard closesatwindup, cross sweepsforwardatimpact, other arm counterbalances.
  guard_r=Vector((-.27,-.24,1.17));impact_r=Vector((-.10,-.59,1.34));wind_r=Vector((-.30,.06,1.20))
  guard_l=Vector((.25,-.22,1.20));impact_l=Vector((.32,.17,1.20));wind_l=Vector((.30,-.29,1.24))
  if drive>=0:r=guard_r.lerp(impact_r,drive);l=guard_l.lerp(impact_l,drive)
  else:r=guard_r.lerp(wind_r,-drive/.35);l=guard_l.lerp(wind_l,-drive/.35)
  blend=min(1,max(fist,abs(drive)));r=baseline_r.lerp(r,blend);l=baseline_l.lerp(l,blend)
  solve_arm('r',r,max(0,drive));solve_arm('l',l,fist);curl_fingers('r',fist);curl_fingers('l',.85*fist)
 bpy.context.view_layer.update()
 for b in arm.pose.bones:
  b.keyframe_insert('location',frame=frame,group=b.name);b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name);b.keyframe_insert('scale',frame=frame,group=b.name)
 report['frames_measured'].append({'frame':frame,'time_s':t,'drive':drive,'fist':fist,'right_wrist_m':list(arm.pose.bones['hand_r'].head),'left_wrist_m':list(arm.pose.bones['hand_l'].head)})
scene.frame_set(1)
for im in bpy.data.images:
 if im.filepath:im.filepath=bpy.path.relpath(im.filepath,start=str(ROOT))
(ROOT/'fist_source_report.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Dink_Fist.blend'),relative_remap=False)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
# ExistingDink studioframes fullbody; centerupperbodyandhandsfor actionreview.
cam=scene.camera;cam.location=(2.4,-4.4,2.1);cam.rotation_euler=(Vector((0,-.10,1.0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=66
for key,frame in [('impact',8),('windup',4),('idle',1),('recoil',11),('end',17)]:
 scene.frame_set(frame);scene.render.filepath=str(ROOT/'Previews'/('fist_'+key+'.png'));bpy.ops.render.render(write_still=True)
scene.frame_set(8);cam.location=(3.7,-.6,1.8);cam.rotation_euler=(Vector((0,-.15,1.05))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews/fist_impact_side.png');bpy.ops.render.render(write_still=True)
cam.location=(.6,-1.6,1.6);cam.rotation_euler=(Vector((-.08,-.63,1.32))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=90;scene.render.filepath=str(ROOT/'Previews/fist_hand_close.png');bpy.ops.render.render(write_still=True)
print('FIST HANDKEYED REVIEW READY',flush=True)
