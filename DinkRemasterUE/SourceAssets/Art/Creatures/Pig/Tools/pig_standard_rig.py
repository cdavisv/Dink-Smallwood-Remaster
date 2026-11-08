"""Normalize project quadruped names/spans without changing existing bone global poses."""
import bpy

def curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag=strip.channelbag(slot)
                if bag:
                    yield from bag.fcurves

def standardize_rig(arm,meshes):
    aliases={'spine':'spine_01','chest':'spine_02','neck':'neck_01','tail_00':'tail_01','tail_01':'tail_02','tail_02':'tail_03'}
    for side in ['l','r']:
        aliases.update({a+'_'+side:b+'_'+side for a,b in [('fore_upper','upperarm'),('fore_lower','lowerarm'),('fore_foot','hand'),('hind_upper','thigh'),('hind_lower','calf'),('hind_foot','foot')]})
    paths=[(curve,curve.data_path) for action in bpy.data.actions for curve in curves(action)]
    groups=[(group,group.name) for mesh in meshes for group in mesh.vertex_groups if group.name in aliases]
    for group,old in groups:group.name='__standard_'+old
    for old in aliases:arm.data.bones[old].name='__standard_'+old
    for old,new in aliases.items():arm.data.bones['__standard_'+old].name=new
    for group,old in groups:group.name=aliases[old]
    for curve,path in paths:
        for old,new in aliases.items():
            token='pose.bones["'+old+'"]'
            if token in path:path=path.replace(token,'pose.bones["'+new+'"]');break
        curve.data_path=path
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
    bones=arm.data.edit_bones
    for old_name,new_name,child_name,ratio in [('spine_02','spine_03','neck_01',.66),('neck_01','neck_02','head',.5)]:
        old=bones[old_name];tail=old.tail.copy();mid=old.head.lerp(tail,ratio);roll=old.roll
        child=bones[child_name];child_matrix=child.matrix.copy();old.tail=mid
        new=bones.new(new_name);new.head=mid;new.tail=tail;new.roll=roll;new.parent=old;new.use_deform=True
        child.parent=new;child.matrix=child_matrix
    bpy.ops.object.mode_set(mode='OBJECT')
    for mesh in meshes:
        for name in ['spine_03','neck_02']:
            if name not in mesh.vertex_groups:mesh.vertex_groups.new(name=name)
    return aliases
