"""Open-hand gesture review of isolated binding; never saves original or candidate model."""
import bpy,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SK_Dink_Hands.blend'));s=bpy.context.scene;a=bpy.data.objects['Armature'];a.data.pose_position='POSE';s.frame_set(1);a.animation_data.action=None;bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in a.data.bones}
# Fixedlength armIK raises a palm for clear per-digit separation review.
u='upperarm_r';l='lowerarm_r';hand='hand_r';h=a.pose.bones[u].head.copy();target=Vector((-.27,-.13,1.53));l1=(a.data.bones[l].head_local-a.data.bones[u].head_local).length;l2=(a.data.bones[hand].head_local-a.data.bones[l].head_local).length;v=target-h;d=v.length;axis=v.normalized();bend=Vector((-.9,.1,-.4));perp=(bend-axis*bend.dot(axis)).normalized();along=(l1*l1-l2*l2+d*d)/(2*d);k=h+axis*along+perp*math.sqrt(max(0,l1*l1-along*along))
for n,head,old,new in [(u,h,a.data.bones[l].head_local-a.data.bones[u].head_local,k-h),(l,k,a.data.bones[hand].head_local-a.data.bones[l].head_local,target-k)]:
 q=old.rotation_difference(new);m=q.to_matrix().to_4x4()@rest[n];m.translation=head;a.pose.bones[n].matrix=m;bpy.context.view_layer.update()
long=(a.data.bones['middle_01_r'].head_local-a.data.bones[hand].head_local).normalized();lateral=a.data.bones['index_01_r'].head_local-a.data.bones['pinky_01_r'].head_local;normal=long.cross(lateral).normalized()
if normal.x<0:normal*=-1
normal=(normal-long*normal.dot(long)).normalized();source=Matrix((long,normal,long.cross(normal))).transposed();dlong=Vector((0,0,1));dn=Vector((0,-1,0));dest=Matrix((dlong,dn,dlong.cross(dn))).transposed();m=(dest@source.inverted()).to_4x4()@rest[hand];m.translation=target;a.pose.bones[hand].matrix=m
for b in a.pose.bones:
 if b.name.endswith('_r') and b.name.startswith(('thumb_','index_','middle_','ring_','pinky_')):b.rotation_quaternion=(1,0,0,0)
bpy.context.view_layer.update();s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1200;s.render.resolution_y=1000;s.render.resolution_percentage=100;cam=s.camera;cam.location=(2.4,-4.4,2.1);cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=66;s.render.filepath=str(ROOT/'Previews/hands_open_gesture.png');bpy.ops.render.render(write_still=True)
cam.location=(.4,-1.6,1.65);cam.rotation_euler=(Vector((-.27,-.13,1.58))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=80;s.render.filepath=str(ROOT/'Previews/hands_open_close.png');bpy.ops.render.render(write_still=True)
print('HANDV2 OPEN GESTURE REVIEW READY',flush=True)
