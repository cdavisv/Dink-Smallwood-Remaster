"""Transfer reference skin weights without delivering the mannequin's geometry."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE');ART=ROOT/'SourceAssets/Art/Characters'
bpy.ops.wm.open_mainfile(filepath=str(ART/'Mother_Working.blend'))
coll=bpy.data.collections['SK_Mother'];arm=next(o for o in coll.objects if o.type=='ARMATURE');arm.name='Armature'
ref=bpy.data.objects['Reference_Manny'];ref.hide_set(False);ref.hide_render=True
bones=set(arm.data.bones.keys());source=[o for o in coll.objects if o.type=='MESH']
for ob in source:
    for old_uv in list(ob.data.uv_layers)[1:]:ob.data.uv_layers.remove(old_uv)
    if ob.data.uv_layers:ob.data.uv_layers[0].name='UVSource'
    if 'skirt' in ob.name.lower():
        group=ob.vertex_groups.new(name='__MotherSkirt');group.add(list(range(len(ob.data.vertices))),1,'REPLACE')
    for v in ob.data.vertices:v.co.z=max(0,v.co.z)
bpy.ops.object.select_all(action='DESELECT')
for ob in source:ob.select_set(True)
ob=bpy.data.objects['Mother_AnatomicalBody'];bpy.context.view_layer.objects.active=ob
bpy.ops.object.join();ob.name='SK_Mother_LOD0';ob.data.name='SK_Mother_LOD0_Mesh'
for g in list(ob.vertex_groups):
    if g.name not in bones and g.name!='__MotherSkirt':ob.vertex_groups.remove(g)
for g in ref.vertex_groups:
    if g.name in bones and g.name not in ob.vertex_groups:ob.vertex_groups.new(name=g.name)
print('REFERENCE WEIGHT GROUPS',[g.name for g in ref.vertex_groups],flush=True)
print('BONES',sorted(bones),flush=True)
for name in bones:
    if name not in ob.vertex_groups:ob.vertex_groups.new(name=name)
mod=ob.modifiers.new('Reference surface weight projection','DATA_TRANSFER');mod.object=ref;mod.use_vert_data=True
mod.data_types_verts={'VGROUP_WEIGHTS'};mod.vert_mapping='POLYINTERP_NEAREST';mod.layers_vgroup_select_src='ALL';mod.layers_vgroup_select_dst='NAME'
bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
mask=ob.vertex_groups.get('__MotherSkirt');skirt_ids=[]
if mask:
    skirt_ids=[v.index for v in ob.data.vertices if any(g.group==mask.index and g.weight>.5 for g in v.groups)]
for index in skirt_ids:
    v=ob.data.vertices[index];t=max(0,min(1,(v.co.z-.13)/.91));pelvis=.25+.75*t
    left=.5+.5*math.tanh(v.co.x/.15)
    values={'pelvis':pelvis,'thigh_l':(1-pelvis)*.7*left,'thigh_r':(1-pelvis)*.7*(1-left),
            'calf_l':(1-pelvis)*.3*left,'calf_r':(1-pelvis)*.3*(1-left)}
    for g in ob.vertex_groups:
        if g.name in bones:g.remove([index])
    for name,weight in values.items():ob.vertex_groups[name].add([index],weight,'REPLACE')
if mask:ob.vertex_groups.remove(mask)
# Normalize and cap influences so both the validator and engine see the same skin.
unweighted=0;maximum=0
for v in ob.data.vertices:
    values=sorted([(g.group,g.weight) for g in v.groups if ob.vertex_groups[g.group].name in bones and g.weight>1e-6],key=lambda p:-p[1])[:4]
    if not values:
        name='head' if v.co.z>1.5 else 'pelvis';values=[(ob.vertex_groups[name].index,1)];unweighted+=1
    total=sum(w for _,w in values)
    for g in ob.vertex_groups:g.remove([v.index])
    for group,weight in values:ob.vertex_groups[group].add([v.index],weight/total,'REPLACE')
    maximum=max(maximum,len(values))
modifier=ob.modifiers.new('Manny compatible skin','ARMATURE');modifier.object=arm;modifier.use_deform_preserve_volume=False
# Strip reference geometry from the source deliverable as well as the export selection.
mesh=ref.data;bpy.data.objects.remove(ref,do_unlink=True)
if mesh.users==0:bpy.data.meshes.remove(mesh)
ob.data.calc_loop_triangles()
report={'bone_count':len(arm.data.bones),'root_bones':[b.name for b in arm.data.bones if b.parent is None],
        'triangles':len(ob.data.loop_triangles),'material_slots':[s.material.name for s in ob.material_slots],
        'max_influences':maximum,'unweighted_before_fallback':unweighted,'vertices':len(ob.data.vertices),'skirt_vertices':len(skirt_ids),
        'reference_geometry_present':any('Manny' in o.name and o.type=='MESH' for o in bpy.context.scene.objects)}
(ART/'mother_rig_report.json').write_text(json.dumps(report,indent=2)+'\n')
ART.joinpath('Working').mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Working/Mother_Rigged_PreBake.blend'))
# A temporary probe lets Unreal check this skin's actual bind pose while atlas baking proceeds.
for v in ob.data.vertices:v.co*=100
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones:b.head*=100;b.tail*=100
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.scene.unit_settings.scale_length=.01
ob.select_set(True)
bpy.ops.export_scene.fbx(filepath='/tmp/dink-character-reference/Mother_Probe.fbx',use_selection=True,object_types={'MESH','ARMATURE'},
    use_mesh_modifiers=True,mesh_smooth_type='FACE',use_triangles=True,use_tspace=False,use_custom_props=False,colors_type='NONE',
    apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,
    use_space_transform=True,add_leaf_bones=False,primary_bone_axis='Y',secondary_bone_axis='X',use_armature_deform_only=False,
    armature_nodetype='NULL',bake_anim=False,path_mode='STRIP',embed_textures=False)
print('MOTHER RIG:',json.dumps(report))
