import bpy,json,gzip,hashlib,sys
from pathlib import Path
from mathutils import Matrix
D=Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[];assert '--out'in args,'Specify --out outside frozen packet';O=Path(args[args.index('--out')+1]).resolve();O.mkdir(parents=True,exist_ok=True)
if(D/'SHA256SUMS.json').exists():assert not O.is_relative_to(D),'Frozen packet refuses in-place output'
S=D/'Source/SK_Dink_Trousers_MetricArtV32_Context.blend';pin=hashlib.sha256(S.read_bytes()).hexdigest();pants='NEW_Dink_Trousers_LOD0';frozen=json.loads((D/'Evidence/frozen_material_alias_reference.json').read_text());aliases={x['source_material']:x['fbx_alias']for x in frozen['materials']};aliases.update({x['source_material'].removeprefix('Baked252_'):x['fbx_alias']for x in frozen['materials']});rows=[]
def capture():
 arm=bpy.data.objects['Armature'];data={};bones={b.name:{'parent':b.parent.name if b.parent else None,'matrix_world_m':[list(r)for r in arm.matrix_world@b.matrix_local],'head_m':list(b.head_local),'tail_m':list(b.tail_local),'length_m':b.length,'use_deform':b.use_deform}for b in arm.data.bones}
 for ob in bpy.data.objects:
  if ob.type!='MESH':continue
  m=ob.data;m.calc_loop_triangles();data[ob.name]={'positions_m':[list(ob.matrix_world@v.co)for v in m.vertices],'weights':[{ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>0}for v in m.vertices],'materials':[aliases.get(mat.name,'QA_Trousers_MetricV32'if ob.name==pants else None)for mat in m.materials],'triangles':[{'vertices':list(t.vertices),'material':aliases.get(m.materials[t.material_index].name,'QA_Trousers_MetricV32'if ob.name==pants else None),'UV':{u.name:[list(u.data[l].uv)for l in t.loops]for u in m.uv_layers},'normals':[list(m.corner_normals[l].vector)for l in t.loops]}for t in m.loop_triangles]}
 return{'meshes':data,'bones89':bones,'unit':'metres','source_path':str(S.relative_to(D)),'source_sha256':pin}
# Snapshot uses independent original packed metre source, not exported geometry.
bpy.ops.wm.open_mainfile(filepath=str(S));ob=bpy.data.objects[pants];aliases[ob.data.materials[0].name]='QA_Trousers_MetricV32';aliases={m.name:aliases[m.name]for o in bpy.data.objects if o.type=='MESH'for m in o.data.materials};snapshot=capture();assert len(snapshot['meshes'])==8 and len(snapshot['bones89'])==89;assert all(x for m in snapshot['meshes'].values()for x in m['materials']);assert len({x for m in snapshot['meshes'].values()for x in m['materials']})==13
with gzip.open(O/'source_geometry_capture.json.gz','wt',encoding='utf8')as f:json.dump(snapshot,f,separators=(',',':'))
for label,onlypants in [('Trousers_Hi',True),('Context_Hi',False)]:
 bpy.ops.wm.open_mainfile(filepath=str(S));arm=bpy.data.objects['Armature'];arm.data.pose_position='REST';meshes=[o for o in bpy.data.objects if o.type=='MESH'and(not onlypants or o.name==pants)];cached={o.name:[tuple(n.vector)for n in o.data.corner_normals]for o in meshes};bpy.ops.object.select_all(action='DESELECT')
 for o in meshes:
  for v in o.data.vertices:v.co*=100
 arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
 for b in arm.data.edit_bones:b.head*=100;b.tail*=100
 bpy.ops.object.mode_set(mode='OBJECT');bpy.context.scene.unit_settings.scale_length=.01
 for o in meshes:o.data.update();o.data.normals_split_custom_set(cached[o.name]);o.select_set(True)
 used={m for o in meshes for m in o.data.materials}
 for mat in used:
  original=mat.name;assert original in aliases,original;mat.name=aliases[original]
  if mat.node_tree:mat.node_tree.nodes.clear()
  mat.use_nodes=False
 file=O/('SK_Dink_V33_'+label+'.fbx');kw=dict(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'},use_mesh_modifiers=False,mesh_smooth_type='FACE',use_triangles=True,use_tspace=False,use_custom_props=False,colors_type='NONE',apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_space_transform=True,add_leaf_bones=False,primary_bone_axis='Y',secondary_bone_axis='X',use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,path_mode='STRIP',embed_textures=False,batch_mode='OFF');bpy.ops.export_scene.fbx(**kw);rows.append({'role':label,'path':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size,'mesh_names':[o.name for o in meshes],'parameters':{k:sorted(v)if isinstance(v,set)else v for k,v in kw.items()}});print('FBX_EXPORT',label,file.stat().st_size,flush=True)
# Optional glTF is deliberately unshaded geometry + skin, not the procedural material.
bpy.ops.wm.open_mainfile(filepath=str(S));bpy.ops.object.select_all(action='DESELECT');bpy.data.objects['Armature'].data.pose_position='REST';bpy.data.objects['Armature'].select_set(True);bpy.data.objects[pants].select_set(True);bpy.context.view_layer.objects.active=bpy.data.objects['Armature'];file=O/'SK_Dink_V33_Trousers_GEOMETRY_ONLY.glb';glb=dict(filepath=str(file),export_format='GLB',use_selection=True,export_apply=False,export_texcoords=True,export_normals=True,export_tangents=False,export_materials='NONE',export_cameras=False,export_lights=False,export_animations=False,export_skins=True,export_yup=True,export_def_bones=False,export_all_influences=True);bpy.ops.export_scene.gltf(**glb);assert hashlib.sha256(S.read_bytes()).hexdigest()==pin
report={'scope':'SOURCE geometry/rig only; FBX graphs stripped in disposable memory, source graphs untouched. No animations baked or native assets touched. GLB omits materials intentionally; no OSL/PBR equivalence.','source_sha256':pin,'source_to_FBX_material_alias':aliases,'FBX':rows,'GLB':{'path':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size,'qualification':'Geometry-only LOD0 skin preview, no materials/texture/procedural-shading fidelity, not native path','parameters':glb},'roundtrip':'Independent actual raw FBX and Blender import verification required'};(O/'export_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
