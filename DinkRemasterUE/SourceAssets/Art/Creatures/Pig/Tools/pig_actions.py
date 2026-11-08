"""Deterministic in-place pig actions; world-axis rotations and synchronized analytic IK."""
import bpy,math
from mathutils import Vector,Matrix,Quaternion

def create_pig_actions(arm,scene):
    arm.data.pose_position='POSE'
    arm.animation_data_create();arm.animation_data.action=None
    for action_name in ['Pig_Idle','Pig_Walk','Pig_Run','Pig_Feed']:
        old=bpy.data.actions.get(action_name)
        if old:bpy.data.actions.remove(old)
    # Explicit actions with in-place, loop-seam-equal root and planted foot targets.
    rest={b.name:b.matrix_local.copy() for b in arm.data.bones}
    def posed_matrix(name,head,tail):
        b=arm.data.bones[name];q=(b.tail_local-b.head_local).rotation_difference(Vector(tail)-Vector(head))
        mat=q.to_matrix().to_4x4()@b.matrix_local;mat.translation=head;return mat
    
    def set_leg(prefix,side,stride=0,lift=0):
        bpy.context.view_layer.update()
        upper=prefix+'_upper_'+side;lower=prefix+'_lower_'+side;foot=prefix+'_foot_'+side
        ub=arm.data.bones[upper];lb=arm.data.bones[lower];fb=arm.data.bones[foot]
        parent=arm.pose.bones[ub.parent.name]
        h=(parent.matrix@ub.parent.matrix_local.inverted()@ub.matrix_local).translation
        target=fb.head_local+Vector((stride,0,lift))
        l1=ub.length;l2=lb.length;delta=target-h;d=min(delta.length,l1+l2-.00001);direction=delta.normalized()
        restbend=lb.head_local-ub.head_local;perp=restbend-direction*restbend.dot(direction)
        if perp.length<.0001:perp=Vector((-1,0,0))
        perp.normalize();a=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-a*a));joint=h+direction*a+perp*height
        target=h+direction*d
        arm.pose.bones[upper].matrix=posed_matrix(upper,h,joint)
        bpy.context.view_layer.update()
        arm.pose.bones[lower].matrix=posed_matrix(lower,joint,target)
        bpy.context.view_layer.update()
        mat=fb.matrix_local.copy();mat.translation=target;arm.pose.bones[foot].matrix=mat
        bpy.context.view_layer.update()
    
    def rotate_world(name,axis,angle):
        local=arm.data.bones[name].matrix_local.to_3x3().inverted()@Vector(axis)
        arm.pose.bones[name].rotation_quaternion=Quaternion(local.normalized(),angle)
    
    actions={}
    for action_name,frames in [('Pig_Idle',61),('Pig_Walk',19),('Pig_Run',13),('Pig_Feed',13)]:
        arm.animation_data_create();action=bpy.data.actions.new(action_name);arm.animation_data.action=action;action.use_fake_user=True
        for frame in range(1,frames+1):
            scene.frame_set(frame);t=(frame-1)/(frames-1);phase=t*math.tau
            for b in arm.pose.bones:b.matrix_basis=Matrix.Identity(4)
            pelvis=arm.pose.bones['pelvis'];pelvis.location.z=.003*math.sin(phase)
            rotate_world('spine',(1,0,0),.008*math.sin(phase))
            rotate_world('neck',(0,1,0),.025*math.sin(phase))
            for side,offset in [('l',0),('r',1.7)]:rotate_world('ear_'+side,(1,0,0),.04*math.sin(phase+offset))
            for i in range(3):rotate_world('tail_%02d'%i,(0,0,1),.10*math.sin(phase+i*.6))
            if action_name=='Pig_Feed':
                ramp=min(1,t/.375,(1-t)/.375);ramp=max(0,ramp);envelope=ramp*ramp*(3-2*ramp)
                pelvis.location.z=envelope*(-.018+.003*math.sin(phase*2))
                rotate_world('neck',(0,1,0),envelope*(.28+.025*math.sin(phase*2)))
                rotate_world('head',(0,1,0),envelope*(.12+.02*math.sin(phase*2)))
                rotate_world('jaw',(0,1,0),-envelope*.018*(.5+.5*math.sin(phase*6)))
            if action_name=='Pig_Walk':pelvis.location.z=.008*math.cos(phase*2)
            if action_name=='Pig_Run':
                pelvis.location.z=-.065+.050*max(0,math.sin(phase*2))
                rotate_world('spine',(0,1,0),.045*math.sin(phase))
                rotate_world('neck',(0,1,0),-.045+.035*math.sin(phase))
            bpy.context.view_layer.update()
            for prefix,side,offset in [('fore','l',0),('hind','l',math.pi/2),('fore','r',math.pi),('hind','r',3*math.pi/2)]:
                stride=lift=0
                if action_name=='Pig_Walk':
                    q=phase+offset;stride=.24*math.cos(q);lift=.085*max(0,-math.sin(q))
                if action_name=='Pig_Run':
                    offset_run=(0 if prefix=='fore' else .5)+(0 if side=='l' else .06)
                    run_phase=(t+offset_run)%1
                    if run_phase<.4:
                        stride=.32-.64*(run_phase/.4);lift=0
                    else:
                        u=(run_phase-.4)/.6;stride=-.32+.64*(.5-.5*math.cos(math.pi*u));lift=.22*math.sin(math.pi*u)
                set_leg(prefix,side,stride,lift)
            for b in arm.pose.bones:
                b.keyframe_insert('location',frame=frame,group=b.name);b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name);b.keyframe_insert('scale',frame=frame,group=b.name)
        actions[action_name]={'frames':[1,frames],'fps':30,'duration_s':(frames-1)/30,'loop':action_name!='Pig_Feed','root_motion':False,'nominal_speed_cm_s':80 if action_name=='Pig_Walk' else (400 if action_name=='Pig_Run' else 0)}
    arm.animation_data.action=bpy.data.actions['Pig_Idle'];scene.frame_start=1;scene.frame_end=61;scene.frame_set(1)
    return actions
