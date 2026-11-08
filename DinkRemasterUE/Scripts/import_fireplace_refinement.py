"""Private new-package import. Does not publish runtime placement or touch originals."""
import json,hashlib,os
from pathlib import Path
import unreal
assert '-game' not in unreal.SystemLibrary.get_command_line().split()
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
SOURCE=ROOT/'SourceAssets/Art/Stonebrook/Refinements/FireplaceV2'
DEST='/Game/Dink/Refinements/FireplaceV2'
LIB=unreal.EditorAssetLibrary;EDIT=unreal.MaterialEditingLibrary;TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
SPEC=json.loads((SOURCE/'candidate_manifest.json').read_text())
report={'passed':False,'source_blend_sha256':hashlib.sha256((SOURCE/'SM_Fireplace_Stonebrook_V2.blend').read_bytes()).hexdigest(),'destination':DEST,'runtime_manifest_changed':False}
assert report['source_blend_sha256']=='49b3464b88fc749bc212f45a2be7d686cb6a909f028429de50b35c16ec6d1d02'
mode=os.environ.get('DINK_FIREPLACE_MODE','import');assert mode in ['import','check','publish']
if not LIB.does_directory_exist(DEST):
 assert mode=='import','Import the candidate packages before checking or publishing'
 # Protect every shared kit/material package, not just one assumed filename.
 protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for branch in ['Kits','Materials'] for p in (ROOT/'Content/Dink'/branch).rglob('*.uasset')}
 data={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Content/Dink/Data').rglob('*') if p.is_file()}
 def save(a):assert LIB.save_loaded_asset(a,only_if_is_dirty=False),a.get_path_name()
 def imp(file,name,options=None,factory=None):
  task=unreal.AssetImportTask();task.filename=str(file.resolve());task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=True
  if options is not None:task.options=options
  if factory is not None:task.factory=factory
  TOOLS.import_asset_tasks([task]);a=LIB.load_asset(DEST+'/'+name);assert a is not None,str(file);return a
 def node(mat,cls,x,y,**kwargs):
  n=EDIT.create_material_expression(mat,cls,x,y)
  for k,v in kwargs.items():n.set_editor_property(k,v)
  return n
 def link(n,channel,prop):assert EDIT.connect_material_property(n,channel,prop)
 try:
  world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
  unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
  assert unreal.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')==0
  mat=TOOLS.create_asset('M_FireplaceV2_Atlas',DEST,unreal.Material,unreal.MaterialFactoryNew());assert mat
  tex={};texture_checks=[]
  for i,(kind,file) in enumerate(SPEC['textures'].items()):
   a=imp(SOURCE/file,Path(file).stem);a.set_editor_property('srgb',kind in ['BC','E'])
   sampler=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
   if kind=='N':
    a.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP);a.set_editor_property('flip_green_channel',True);sampler=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
   if kind=='ORM':a.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS);sampler=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
   save(a);tex[kind]=node(mat,unreal.MaterialExpressionTextureSample,-700,i*240,texture=a,sampler_type=sampler)
   texture_checks.append({'kind':kind,'source_sha256':hashlib.sha256((SOURCE/file).read_bytes()).hexdigest(),'srgb':bool(a.get_editor_property('srgb')),'sampler':str(sampler)})
  link(tex['BC'],'RGB',unreal.MaterialProperty.MP_BASE_COLOR);link(tex['N'],'RGB',unreal.MaterialProperty.MP_NORMAL)
  for ch,prop in [('R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',unreal.MaterialProperty.MP_ROUGHNESS),('B',unreal.MaterialProperty.MP_METALLIC)]:link(tex['ORM'],ch,prop)
  strength=node(mat,unreal.MaterialExpressionConstant,-400,1000,r=float(SPEC['emission_strength']));mul=node(mat,unreal.MaterialExpressionMultiply,-150,1000)
  assert EDIT.connect_material_expressions(tex['E'],'RGB',mul,'A');assert EDIT.connect_material_expressions(strength,'',mul,'B');link(mul,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
  specular=node(mat,unreal.MaterialExpressionConstant,-150,1250,r=.35);link(specular,'',unreal.MaterialProperty.MP_SPECULAR)
  EDIT.set_base_material_usage(mat,unreal.MaterialUsage.MATUSAGE_NANITE,True);EDIT.recompile_material(mat);save(mat)
  options=unreal.FbxImportUI();options.set_editor_property('automated_import_should_detect_type',False);options.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
  for key,val in [('import_mesh',True),('import_materials',False),('import_textures',False),('import_animations',False)]:options.set_editor_property(key,val)
  opts=options.static_mesh_import_data
  for key,val in [('combine_meshes',True),('import_mesh_lods',False),('auto_generate_collision',False),('generate_lightmap_u_vs',False),('convert_scene',True),('convert_scene_unit',True),('import_uniform_scale',1.),('one_convex_hull_per_ucx',True)]:opts.set_editor_property(key,val)
  opts.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
  name=SPEC['name'];files=[SOURCE/'Export/SingleLODs'/(name+'_LOD'+str(i)+'.fbx') for i in range(3)]
  mesh=imp(files[0],name,options,unreal.FbxFactory());sub=(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
  for i,file in enumerate(files[1:],1):assert sub.import_lod(mesh,i,str(file.resolve()))==i
  for i in range(3):
   build=sub.get_lod_build_settings(mesh,i);build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True);sub.set_lod_build_settings(mesh,i,build)
  assert sub.get_lod_count(mesh)==3
  hulls=sub.get_convex_collision_count(mesh);assert hulls==6,('Expected six fitted UCX hulls',hulls)
  body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
  slots=list(mesh.get_editor_property('static_materials'));assert len(slots)==1,len(slots);slots[0].set_editor_property('material_interface',mat);mesh.set_editor_property('static_materials',slots)
  nanite=mesh.get_editor_property('nanite_settings');nanite.set_editor_property('enabled',True);nanite.set_editor_property('fallback_target',unreal.NaniteFallbackTarget.PERCENT_TRIANGLES);nanite.set_editor_property('fallback_percent_triangles',1.);nanite.set_editor_property('fallback_relative_error',0.);mesh.set_editor_property('nanite_settings',nanite)
  description=mesh.get_static_mesh_description(0);assert description
  points=[]
  for i in range(description.get_vertex_count()):
   vertex=unreal.VertexID(id_value=i);assert description.is_vertex_valid(vertex);v=description.get_vertex_position(vertex);points.append([v.x,v.y,v.z])
  actual=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)];expected=[v*100 for v in SPEC['dimensions_m']]
  assert all(abs(a-b)<.05 for a,b in zip(actual,expected)),(actual,expected)
  triangles=[mesh.get_num_triangles(i) for i in range(3)];assert triangles==[15484,8050,4180],triangles
  save(mesh)
  assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items()),'Shared package changed'
  assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in data.items()),'Runtime Data changed'
  report.update(passed=True,mesh=mesh.get_path_name(),dimensions_cm=actual,lods=3,triangles=triangles,convex_hulls=hulls,collision_mode=str(body.get_editor_property('collision_trace_flag')),textures=texture_checks,protected_shared_packages=len(protected),protected_data_files=len(data),limitations=['No actual capsule sweeps yet','No live runtime placement or lighting acceptance','Nanite follows source policy;3authored fallback LODs retained'])
  print('FIREPLACE V2 STAGE IMPORT PASS',flush=True)
 except Exception as e:
  report['error']=str(e);raise
 finally:
  out=ROOT/'Saved/Art/fireplace_refinement_import.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')

exec((ROOT/'Scripts/inspect_fireplace_refinement.py').read_text())
