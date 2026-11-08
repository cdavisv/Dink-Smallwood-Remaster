"""Metachronal14-leg walking, source-cadence loops and fixed-length analyticIK."""
import bpy,math
from mathutils import Vector,Matrix,Quaternion

def create_actions(arm,scene,legs):
 arm.data.pose_position='POSE';arm.animation_data_create();arm.animation_data.action=None
 def rotate(name,axis,angle):
  local=arm.data.bones[name].matrix_local.to_3x3().inverted()@Vector(axis);arm.pose.bones[name].rotation_quaternion=Quaternion(local.normalized(),angle)
 def posed(name,h,t):
  b=arm.data.bones[name];q=(b.tail_local-b.head_local).rotation_difference(Vector(t)-Vector(h));m=q.to_matrix().to_4x4()@b.matrix_local;m.translation=h;return m
 def solve(upper,lower,foot,stride,lift):
  bpy.context.view_layer.update();ub=arm.data.bones[upper];lb=arm.data.bones[lower];parent=arm.pose.bones[ub.parent.name]
  hip=(parent.matrix@ub.parent.matrix_local.inverted()@ub.matrix_local).translation
  target=foot+Vector((stride,0,lift));delta=target-hip;distance=min(delta.length,ub.length+lb.length-.00001);direction=delta.normalized()
  bend=lb.head_local-ub.head_local;perp=bend-direction*bend.dot(direction)
  if perp.length<.0001:perp=Vector((0,0,1))
  perp.normalize();a=(ub.length**2-lb.length**2+distance**2)/(2*distance);height=math.sqrt(max(0,ub.length**2-a*a));knee=hip+direction*a+perp*height;target=hip+direction*distance
  arm.pose.bones[upper].matrix=posed(upper,hip,knee);bpy.context.view_layer.update();arm.pose.bones[lower].matrix=posed(lower,knee,target);bpy.context.view_layer.update()
 actions={}
 for key,frames in [('Idle',81),('Walk',16),('Run',16)]:
  action=bpy.data.actions.new('Pillbug_'+key);action.use_fake_user=True;arm.animation_data.action=action
  for frame in range(1,frames+1):
   scene.frame_set(frame);t=(frame-1)/(frames-1);phase=t*math.tau
   for b in arm.pose.bones:b.matrix_basis=Matrix.Identity(4)
   arm.pose.bones['pelvis'].location.z=(.0015 if key=='Idle' else .004)*math.sin(phase*2)
   rotate('head',(0,0,1),.013*math.sin(phase))
   for i in range(7):rotate('tergite_%02d'%(i+1),(0,1,0),(.003 if key=='Idle' else .008)*math.sin(phase+i*.5))
   for side,shift in [('l',0),('r',2.2)]:
    rotate('antenna_01_'+side,(0,0,1),.055*math.sin(phase+shift));rotate('antenna_02_'+side,(0,1,0),.08*math.sin(phase+shift+.8))
   bpy.context.view_layer.update()
   for upper,lower,seg,h,k,f,i,label in legs:
    stride=lift=0
    if key!='Idle':
     p=(t+i/7+(.5 if label=='r' else 0))%1;stance=.6 if key=='Walk' else 1/3;sweep=.18 if key=='Walk' else .50
     if p<stance:stride=sweep*.5-sweep*p/stance
     else:
      u=(p-stance)/(1-stance);stride=-sweep*.5+sweep*(.5-.5*math.cos(math.pi*u));lift=(.035 if key=='Walk' else .07)*math.sin(math.pi*u)
    solve(upper,lower,f,stride,lift)
   for b in arm.pose.bones:
    b.keyframe_insert('location',frame=frame,group=b.name);b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name);b.keyframe_insert('scale',frame=frame,group=b.name)
  actions['Pillbug_'+key]={'frames':[1,frames],'fps':40,'duration_s':(frames-1)/40,'loop':True,'root_motion':False,'nominal_speed_cm_s':80 if key=='Walk' else(400 if key=='Run' else 0),'gait':'seven-pair left/right offset metachronal wave; in-place fixed-length analyticIK'}
 arm.animation_data.action=None;scene.frame_start=1;scene.frame_end=81;scene.frame_set(1);return actions
