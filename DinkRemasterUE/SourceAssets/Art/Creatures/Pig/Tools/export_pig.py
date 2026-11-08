"""Validate source/poses and export three skeletal LODs plus four in-place actions."""
import bpy,bmesh,json,sys,math,os
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[3]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,make_lods,validate,export_ue
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Working/Pig_Baked.blend'))
scene=bpy.context.scene;coll=bpy.data.collections['SK_Pig_Stonebrook'];coll.name='SK_Pig';coll['dink_path']='Pig';coll['dink_class']='creature_quadruped';coll['dink_tex_px']=2048
ob=bpy.data.objects['SK_Pig_Stonebrook_LOD0'];ob.name='SK_Pig_LOD0';ob.data.name=ob.name
arm=bpy.data.objects['Armature'];arm.animation_data.action=None;arm.data.pose_position='REST'
asset=common.Asset(coll);make_lods.make_lods(asset,[.5,.25],replace=True,force=True);asset.refresh()
normal_report=[]
for mesh in asset.renders:
    bm=bmesh.new();bm.from_mesh(mesh.data);bad=[f for f in bm.faces if f.calc_area()<1e-8]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
    wire=[e for e in bm.edges if not e.link_faces]
    if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(mesh.data);bm.free();mesh.data.update()
    zero={i for i,n in enumerate(mesh.data.corner_normals) if n.vector.length<1e-4};fixed=0
    for face in mesh.data.polygons:
        if any(i in zero for i in face.loop_indices):face.use_smooth=False;fixed+=1
    mesh.data.update()
    remaining=sum(n.vector.length<1e-4 for n in mesh.data.corner_normals)
    if remaining:raise RuntimeError('Zero normals remain in '+mesh.name)
    for vertex in mesh.data.vertices:
        weights=sorted([(g.group,g.weight) for g in vertex.groups if g.weight>1e-6],key=lambda p:-p[1])[:4];total=sum(w for _,w in weights)
        if total<=0:raise RuntimeError('Unweighted vertex in '+mesh.name)
        for group in mesh.vertex_groups:group.remove([vertex.index])
        for group,w in weights:mesh.vertex_groups[group].add([vertex.index],w/total,'REPLACE')
    normal_report.append({'mesh':mesh.name,'removed_zero_area_faces':len(bad),'flat_faces_for_cancelled_normals':fixed,'remaining_zero_normals':remaining})
    mesh.hide_render=mesh!=ob
# Every posed limb remains a continuous fixed-length chain; each clip has a stationary root.
action_rows=json.loads((ROOT/'pig_rig_report.json').read_text())['actions'];pose_report={}
arm.data.pose_position='POSE';pose_samples={}
for name,row in action_rows.items():
    arm.animation_data.action=bpy.data.actions[name];maximum_joint_gap=0;maximum_root_motion=0;start={};end={}
    for frame in range(row['frames'][0],row['frames'][1]+1):
        scene.frame_set(frame);bpy.context.view_layer.update()
        pose_samples[(name,frame)]={b.name:b.matrix.copy() for b in arm.pose.bones}
        for prefix in ['fore','hind']:
            for side in ['l','r']:
                upper=arm.pose.bones[prefix+'_upper_'+side];lower=arm.pose.bones[prefix+'_lower_'+side];foot=arm.pose.bones[prefix+'_foot_'+side]
                maximum_joint_gap=max(maximum_joint_gap,(upper.tail-lower.head).length,(lower.tail-foot.head).length)
        maximum_root_motion=max(maximum_root_motion,arm.pose.bones['root'].matrix.translation.length)
        if frame in [row['frames'][0],row['frames'][1]]:
            snapshot={b.name:b.matrix.copy() for b in arm.pose.bones}
            if frame==row['frames'][0]:start=snapshot
            else:end=snapshot
    seam=max(max(abs(start[n][r][c]-end[n][r][c]) for r in range(4) for c in range(4)) for n in start)
    pose_report[name]={'max_joint_gap_m':maximum_joint_gap,'root_motion_m':maximum_root_motion,'start_end_pose_matrix_max_difference':seam}
    if maximum_joint_gap>.001 or maximum_root_motion>.0001 or seam>.001:raise RuntimeError('Pose contract failed '+name+':'+str(pose_report[name]))
arm.animation_data.action=None;arm.data.pose_position='REST';scene.frame_set(1)
sys.path.insert(0,str(Path(__file__).parent))
from pig_standard_rig import standardize_rig
aliases=standardize_rig(arm,asset.renders)
arm.data.pose_position='POSE';normalization_difference=0
for (name,frame),sample in pose_samples.items():
    arm.animation_data.action=bpy.data.actions[name];scene.frame_set(frame);bpy.context.view_layer.update()
    for old,matrix in sample.items():
        actual=arm.pose.bones[aliases.get(old,old)].matrix
        normalization_difference=max(normalization_difference,max(abs(matrix[r][c]-actual[r][c]) for r in range(4) for c in range(4)))
if normalization_difference>.0001:raise RuntimeError('Rig normalization changed global poses:'+str(normalization_difference))
pose_report['standardization']={'existing_bone_global_pose_max_difference':normalization_difference,'bone_count':len(arm.data.bones),'aliases':aliases}
rig_report=json.loads((ROOT/'pig_rig_report.json').read_text());rig_report['bone_count']=len(arm.data.bones);rig_report['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'matrix_local':[list(row) for row in b.matrix_local]} for b in arm.data.bones];rig_report['standardized_quadruped_names']=aliases
(ROOT/'pig_rig_report.json').write_text(json.dumps(rig_report,indent=2)+'\n')
arm.animation_data.action=None;arm.data.pose_position='REST';scene.frame_set(1)
for image in bpy.data.images:
    if image.filepath and Path(bpy.path.abspath(image.filepath)).parent==ROOT/'Textures':image.filepath='//Textures/'+Path(image.filepath).name
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SK_Pig.blend'),relative_remap=False)
verdict=validate.validate_scene(only=['SK_Pig']);(ROOT/'pig_validation.json').write_text(json.dumps(verdict,indent=2)+'\n')
if verdict['summary']['errors']:
    for entry in verdict['assets']:
        for finding in entry['findings']:
            if finding['severity']=='error':print('PIG VALIDATION ERROR',finding['code'],finding['message'],flush=True)
    raise RuntimeError('Pig source validation must pass')
bounds=[common.world_bounds(o) for o in asset.renders];mn=Vector(tuple(min(b[0][i] for b in bounds) for i in range(3)));mx=Vector(tuple(max(b[1][i] for b in bounds) for i in range(3)));base_min,base_max=common.world_bounds(ob)
materials=json.loads((ROOT/'pig_materials.json').read_text());animations={}
for key in ['Idle','Walk','Run','Feed']:
    row=action_rows['Pig_'+key];animations[key]={'fbx':'Export/A_Pig_'+key+'.fbx','loop':row['loop'],'fps':row['fps'],'duration_s':row['duration_s'],'frames':row['frames'],'root_motion':False}
    if key in ['Walk','Run']:animations[key]['nominal_speed_cm_s']=row['nominal_speed_cm_s']
def fitted_box(points):
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center=(lo+hi)*50;center.y*=-1
    return {'offset_cm':list(center),'extent_cm':list((hi-lo)*50+Vector((1,1,1)))}
body_boxes=[fitted_box([v.co for v in ob.data.vertices if -.68<v.co.x<.38 and v.co.z>.30]),
            fitted_box([v.co for v in ob.data.vertices if v.co.x>=.35 and .44<v.co.z<.82])]
row={'fbx':'Export/SK_Pig_LOD0.fbx','lod_fbx':['Export/SK_Pig_LOD%d.fbx'%i for i in range(3)],'dimensions_m':list(base_max-base_min),'lod_union_dimensions_m':list(mx-mn),'bounds_min_m':list(base_min),'bounds_max_m':list(base_max),
     'materials':[slot.material.name for slot in ob.material_slots],'root_bone':'root','bones':[b.name for b in arm.data.bones],'head_bone':'head','pelvis_bone':'pelvis','class':'creature_quadruped','rotation_deg':[0,0,0],
     'forward':'+X','source_blend':'SK_Pig.blend','body_boxes':body_boxes,'body_boxes_note':'Measured rest-surface AABBs of major trunk and head, excluding decorative tail/ears;1cm padding, actor-forward UEcm.'}
manifest={'schema':'dink-creature-art/1','assets':{'SK_Pig':row},'materials':materials,'animations':animations,'source':'Original project-authored pig anatomy, procedural materials, quadruped rig and actions; no third-party geometry/textures.',
          'export_units':'Source metres; temporary mesh/edit-bone/action-location coordinates100x, scene.01 and FBXheader1 centimetres; identityroot, noleafbones.',
          'food_mesh':'/Game/Dink/Kits/PigPen/SM_FeedScatter_Wheat_01.SM_FeedScatter_Wheat_01','food_mesh_offset_cm':[0,0,-59.4],
          'appearance_revision':materials.get('MI_Pig_Skin',{}).get('appearance_revision','original-v1'),
          'origins':['S407_P02','S407_P05','S407_P06','S407_P07','S407_P11'],'status':'candidate'}
(ROOT/'pig_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(ROOT/'pig_pose_validation.json').write_text(json.dumps(pose_report,indent=2)+'\n')
(ROOT/'pig_lod_report.json').write_text(json.dumps({'validation':verdict['summary'],'normals':normal_report,'lods':[{'name':m.name,'triangles':common.tri_count(m),'vertices':len(m.data.vertices)} for m in asset.renders]},indent=2)+'\n')
if os.environ.get('PIG_VALIDATE_ONLY'):
    print('PIG SOURCE VALIDATION OK:',verdict['summary'],'POSES',pose_report,flush=True);sys.exit(0)
# Save source in metres above; mutate only the process's export copy below.
for mesh in asset.renders:
    for vertex in mesh.data.vertices:vertex.co*=100
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
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
for material in bpy.data.materials:
    if material.node_tree:material.node_tree.nodes.clear()
    material.use_nodes=False
DEST=ROOT/'Export';DEST.mkdir(exist_ok=True)
for lod in range(3):
    mesh=bpy.data.objects['SK_Pig_LOD%d'%lod];proxy=type('ExportAsset',(),{'renders':[mesh],'collision':[],'armatures':[arm],'sockets':[]})()
    with export_ue.unhidden([mesh,arm]):export_ue.export_fbx(proxy,str(DEST/('SK_Pig_LOD%d.fbx'%lod)),'all','Armature')
arm.data.pose_position='POSE';pose_samples={}
for name,row in animations.items():
    arm.animation_data.action=bpy.data.actions['Pig_'+name];scene.frame_start=row['frames'][0];scene.frame_end=row['frames'][1];scene.frame_set(scene.frame_start)
    bpy.ops.object.select_all(action='DESELECT');arm.hide_set(False);arm.hide_viewport=False;arm.select_set(True);bpy.context.view_layer.objects.active=arm
    bpy.ops.export_scene.fbx(filepath=str(ROOT/row['fbx']),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',
        axis_forward='Y',axis_up='Z',bake_space_transform=False,use_space_transform=True,add_leaf_bones=False,primary_bone_axis='Y',secondary_bone_axis='X',use_armature_deform_only=False,
        armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,
        bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='STRIP',embed_textures=False,use_custom_props=False)
print('PIG EXPORT OK:3LODs,4actions,26bones;SOURCEVALIDATION',verdict['summary'],flush=True)
