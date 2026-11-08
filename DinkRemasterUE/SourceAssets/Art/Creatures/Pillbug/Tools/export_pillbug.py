"""Validated three-LOD bespoke skeletal export. Source metres, UE centimetre recipe."""
import bpy,bmesh,json,sys,math,os
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[3]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,make_lods,validate,export_ue
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Working/Pillbug_Baked.blend'))
scene=bpy.context.scene;coll=bpy.data.collections['SK_Pillbug'];ob=bpy.data.objects['SK_Pillbug_LOD0'];arm=bpy.data.objects['Armature'];arm.animation_data.action=None;arm.data.pose_position='REST'
asset=common.Asset(coll);make_lods.make_lods(asset,[.5,.25],replace=True,force=True);asset.refresh();normals=[]
for mesh in asset.renders:
 bm=bmesh.new();bm.from_mesh(mesh.data);bad=[f for f in bm.faces if f.calc_area()<1e-8]
 if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
 wire=[e for e in bm.edges if not e.link_faces]
 if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
 loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh.data);bm.free();mesh.data.update()
 zero={i for i,n in enumerate(mesh.data.corner_normals) if n.vector.length<1e-4};flat=0
 for f in mesh.data.polygons:
  if any(i in zero for i in f.loop_indices):f.use_smooth=False;flat+=1
 mesh.data.update();remaining=sum(n.vector.length<1e-4 for n in mesh.data.corner_normals)
 if remaining:raise RuntimeError('Zero normals '+mesh.name)
 for v in mesh.data.vertices:
  weights=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-6],key=lambda x:-x[1])[:4];total=sum(w for _,w in weights)
  if total<=0:raise RuntimeError('Unweighted '+mesh.name)
  for g in mesh.vertex_groups:g.remove([v.index])
  for g,w in weights:mesh.vertex_groups[g].add([v.index],w/total,'REPLACE')
 normals.append({'mesh':mesh.name,'removed_degenerate_faces':len(bad),'removed_wire_edges':len(wire),'removed_loose_vertices':len(loose),'flat_faces_for_cancelled_normals':flat,'remaining_zero_normals':remaining});mesh.hide_render=mesh!=ob
report=json.loads((ROOT/'pillbug_rig_report.json').read_text());actions=report['actions'];poses={};arm.data.pose_position='POSE'
for name,row in actions.items():
 arm.animation_data.action=bpy.data.actions[name];joint=0;root=0;scale=0;finite=True;start={};end={};reach=0
 for frame in range(row['frames'][0],row['frames'][1]+1):
  scene.frame_set(frame);bpy.context.view_layer.update()
  for chain in report['leg_chains']:
   upper=arm.pose.bones[chain['upper']];lower=arm.pose.bones[chain['lower']];joint=max(joint,(upper.tail-lower.head).length)
  for b in arm.pose.bones:
   loc,rot,s=b.matrix.decompose();scale=max(scale,max(abs(x-1) for x in s));finite=finite and all(math.isfinite(x) for r in b.matrix for x in r)
  root=max(root,arm.pose.bones['root'].matrix.translation.length)
  if frame in [row['frames'][0],row['frames'][1]]:
   snapshot={b.name:b.matrix.copy() for b in arm.pose.bones}
   if frame==row['frames'][0]:start=snapshot
   else:end=snapshot
 seam=max(abs(start[n][r][c]-end[n][r][c]) for n in start for r in range(4) for c in range(4))
 poses[name]={'max_joint_gap_m':joint,'root_motion_m':root,'maximum_global_scale_error':scale,'finite':finite,'loop_pose_matrix_max_difference':seam}
 if joint>.001 or root>.0001 or scale>.001 or seam>.001 or not finite:raise RuntimeError('Pose gate failed '+name+str(poses[name]))
arm.animation_data.action=None;arm.data.pose_position='REST';scene.frame_set(1)
for image in bpy.data.images:
 if image.filepath and Path(bpy.path.abspath(image.filepath)).parent==ROOT/'Textures':image.filepath='//Textures/'+Path(image.filepath).name
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SK_Pillbug.blend'),relative_remap=False)
verdict=validate.validate_scene(only=['SK_Pillbug']);(ROOT/'pillbug_validation.json').write_text(json.dumps(verdict,indent=2)+'\n')
if verdict['summary']['errors']:
 for entry in verdict['assets']:
  for f in entry['findings']:
   if f['severity']=='error':print('PILLBUG VALIDATION ERROR',f['code'],f['message'],flush=True)
 raise RuntimeError('Source guide validation failed')
bounds=[common.world_bounds(m) for m in asset.renders];mn=Vector(tuple(min(b[0][i] for b in bounds) for i in range(3)));mx=Vector(tuple(max(b[1][i] for b in bounds) for i in range(3)));lo,hi=common.world_bounds(ob)
def box(names):
 points=[v.co for v in ob.data.vertices if any(ob.vertex_groups[g.group].name in names and g.weight>.5 for g in v.groups)]
 a=Vector(tuple(min(p[i] for p in points) for i in range(3)));b=Vector(tuple(max(p[i] for p in points) for i in range(3)));c=(a+b)*50;c.y*=-1
 return {'offset_cm':list(c),'extent_cm':list((b-a)*50+Vector((.5,.5,.5)))}
body=[box({'pelvis','tail'}|{'tergite_%02d'%i for i in range(1,8)}),box({'head'})]
animations={}
for key in ['Idle','Walk','Run']:
 r=actions['Pillbug_'+key];animations[key]={'fbx':'Export/A_Pillbug_'+key+'.fbx','loop':True,'fps':40,'duration_s':r['duration_s'],'frames':r['frames'],'root_motion':False}
 if key!='Idle':animations[key]['nominal_speed_cm_s']=r['nominal_speed_cm_s']
row={'fbx':'Export/SK_Pillbug_LOD0.fbx','lod_fbx':['Export/SK_Pillbug_LOD%d.fbx'%i for i in range(3)],'dimensions_m':list(hi-lo),'lod_union_dimensions_m':list(mx-mn),'bounds_min_m':list(lo),'bounds_max_m':list(hi),'materials':[s.material.name for s in ob.material_slots],
 'root_bone':'root','bones':[b.name for b in arm.data.bones],'head_bone':'head','pelvis_bone':'pelvis','class':'creature','content_folder':'/Game/Dink/Creatures/Pillbug','rotation_deg':[0,0,0],'forward':'+X','source_blend':'SK_Pillbug.blend','body_boxes':body,'body_boxes_note':'Rest-cuticle surfaces grouped by rigid body/tergite/head bones; excludes leg and antenna reach; .5cm padding in actor-forward Unrealcm.'}
manifest={'schema':'dink-creature-art/1','assets':{'SK_Pillbug':row},'materials':json.loads((ROOT/'pillbug_materials.json').read_text()),'animations':animations,'source':'Original project-authored segmented terrestrial-isopod anatomy, rig, procedural materials and metachronal actions; no third-party mesh or texture assets.',
 'export_units':'Editable sources metres; temporary geometry, edit-bone and animated location coordinates100x; scene.01/FBXheader1cm; identityroot along+Y; noleafbones.','origins':['S438_P02','S438_P03','S438_P04','S438_P05','S438_P06','S438_P07'],'status':'candidate',
 'behavior_contract':'Existing actors/scripts/vision/HP/contact damage/saves unchanged. No attack/feed/hit/death presentation cue invented; original native death hides immediately. Fast original speed preserved; Run400cm/s drives runtimeplayrate~2.1 for835cm/s.'}
(ROOT/'pillbug_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(ROOT/'pillbug_pose_validation.json').write_text(json.dumps(poses,indent=2)+'\n')
(ROOT/'pillbug_lod_report.json').write_text(json.dumps({'validation':verdict['summary'],'normals':normals,'lods':[{'name':m.name,'triangles':common.tri_count(m),'vertices':len(m.data.vertices)} for m in asset.renders]},indent=2)+'\n')
# Source saved in metres; this process alone becomes temporary cm exportscene.
for mesh in asset.renders:
 for v in mesh.data.vertices:v.co*=100
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones:b.head*=100;b.tail*=100
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
for lod in range(3):
 m=bpy.data.objects['SK_Pillbug_LOD%d'%lod];proxy=type('ExportAsset',(),{'renders':[m],'collision':[],'armatures':[arm],'sockets':[]})()
 with export_ue.unhidden([m,arm]):export_ue.export_fbx(proxy,str(ROOT/'Export'/('SK_Pillbug_LOD%d.fbx'%lod)),'all','Armature')
arm.data.pose_position='POSE'
for name,row in animations.items():
 arm.animation_data.action=bpy.data.actions['Pillbug_'+name];scene.frame_start=row['frames'][0];scene.frame_end=row['frames'][1];scene.render.fps=row['fps'];scene.frame_set(scene.frame_start)
 bpy.ops.object.select_all(action='DESELECT');arm.hide_set(False);arm.hide_viewport=False;arm.select_set(True);bpy.context.view_layer.objects.active=arm
 bpy.ops.export_scene.fbx(filepath=str(ROOT/row['fbx']),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_space_transform=True,add_leaf_bones=False,primary_bone_axis='Y',secondary_bone_axis='X',use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='STRIP',embed_textures=False,use_custom_props=False)
print('PILLBUG EXPORT OK:3LODs,3actions,43bones',verdict['summary'],flush=True)
