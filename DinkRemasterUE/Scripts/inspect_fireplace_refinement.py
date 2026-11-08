"""Validate the new immutable fireplace packages; optionally publish the art layer.
Run with import_fireplace_refinement.sh. No original asset package is changed.
"""
import hashlib,json,math,os,sys
from pathlib import Path
import unreal
assert '-game' not in unreal.SystemLibrary.get_command_line().split(),'Use an editor commandlet'
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
SOURCE=ROOT/'SourceAssets/Art/Stonebrook/Refinements/FireplaceV2'
sys.path.insert(0,str(ROOT/'Scripts'))
from fireplace_source import validate_source_inputs,validate_render_policy
plan,validated_spec,validated_source_hashes=validate_source_inputs(ROOT)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/plan['source_blend'])==plan['source_blend_sha256'],'Source candidate changed: review a new revision'
assert json.loads((ROOT/plan['source_export']).read_text())['assets'][0]['source']['sha256']==plan['source_blend_sha256']
DEST=plan['destination'];LIB=unreal.EditorAssetLibrary;EDIT=unreal.MaterialEditingLibrary
mode=os.environ.get('DINK_FIREPLACE_MODE','import');assert mode in ['import','check','publish','resume']
report={'validated_source_sha256':validated_source_hashes,'passed':False,'mode':mode,'source_blend_sha256':plan['source_blend_sha256'],'original_packages_changed':False,'runtime_published':False}
protected={p:sha(p) for branch in ['Kits','Materials'] for p in (ROOT/'Content/Dink'/branch).rglob('*.uasset')}
def atom(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)
def connect(mat,prop,kind):
 node=EDIT.get_material_property_input_node(mat,prop);assert isinstance(node,kind),str(prop);return node
try:
 mesh=unreal.load_asset(DEST+'/'+plan['mesh']);assert isinstance(mesh,unreal.StaticMesh)
 sub=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
 assert sub.get_lod_count(mesh)==3
 tris=[mesh.get_num_triangles(i) for i in range(3)];assert tris==[15484,8050,4180],tris
 assert sub.get_convex_collision_count(mesh)==6
 assert mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')==unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX
 assert mesh.get_editor_property('nanite_settings').get_editor_property('enabled')
 assert mesh.get_editor_property('nanite_settings').get_editor_property('fallback_target')==unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
 settings=mesh.get_editor_property('nanite_settings')
 validate_render_policy(settings.get_editor_property('fallback_percent_triangles'),settings.get_editor_property('fallback_relative_error'),plan['render_policy'])
 assert plan['render_policy']['nanite'] is True
 assert json.loads((ROOT/plan['source_export']).read_text())['assets'][0]['nanite'] is True
 # GetBounds includes Nanite's coarse-LOD culling envelope, not just source vertices.
 b=mesh.get_bounds().box_extent;render_size=[2*b.x,2*b.y,2*b.z]
 description=mesh.get_static_mesh_description(0);assert description
 points=[]
 for i in range(description.get_vertex_count()):
  vertex=unreal.VertexID(id_value=i);assert description.is_vertex_valid(vertex)
  v=description.get_vertex_position(vertex);points.append([v.x,v.y,v.z])
 low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)];size=[b-a for a,b in zip(low,high)]
 spec=validated_spec;expected_size=[v*100 for v in spec['dimensions_m']]
 report.update(source_size_cm=size,render_culling_size_cm=render_size,source_vertices=len(points),source_triangles=description.get_triangle_count(),nanite_triangles=mesh.get_num_nanite_triangles())
 assert description.get_triangle_count()==15484 and mesh.get_num_nanite_triangles()==15484
 assert all(abs(a-b)<.05 for a,b in zip(size,expected_size)),(size,expected_size)
 mat=unreal.load_asset(DEST+'/M_FireplaceV2_Atlas');assert isinstance(mat,unreal.Material)
 assert EDIT.has_material_usage(mat,unreal.MaterialUsage.MATUSAGE_NANITE)
 slots=mesh.get_editor_property('static_materials');assert len(slots)==1 and slots[0].get_editor_property('material_interface')==mat
 textures={}
 for kind in ['BC','N','ORM','E']:
  tex=unreal.load_asset(DEST+'/T_FireplaceV2_Atlas_'+kind);assert isinstance(tex,unreal.Texture2D)
  assert bool(tex.get_editor_property('srgb'))==(kind in ['BC','E'])
  if kind=='N':
   assert tex.get_editor_property('compression_settings')==unreal.TextureCompressionSettings.TC_NORMALMAP and tex.get_editor_property('flip_green_channel')
  if kind=='ORM':assert tex.get_editor_property('compression_settings')==unreal.TextureCompressionSettings.TC_MASKS
  textures[kind]=tex
 for prop,kind,channel in [(unreal.MaterialProperty.MP_BASE_COLOR,'BC','RGB'),(unreal.MaterialProperty.MP_NORMAL,'N','RGB'),(unreal.MaterialProperty.MP_AMBIENT_OCCLUSION,'ORM','R'),(unreal.MaterialProperty.MP_ROUGHNESS,'ORM','G'),(unreal.MaterialProperty.MP_METALLIC,'ORM','B')]:
  n=connect(mat,prop,unreal.MaterialExpressionTextureSample);assert n.get_editor_property('texture')==textures[kind]
  assert EDIT.get_material_property_input_node_output_name(mat,prop)==channel
 e=connect(mat,unreal.MaterialProperty.MP_EMISSIVE_COLOR,unreal.MaterialExpressionMultiply);inputs=EDIT.get_inputs_for_material_expression(mat,e)
 assert len(inputs)==2 and isinstance(inputs[0],unreal.MaterialExpressionTextureSample) and inputs[0].get_editor_property('texture')==textures['E']
 assert isinstance(inputs[1],unreal.MaterialExpressionConstant) and abs(inputs[1].get_editor_property('r')-1.2)<1e-6
 art=ROOT/'Content/Dink/Data/Art';runtime=art/plan['runtime_file'];basepath=art/'stonebrook.json';base=json.loads(basepath.read_text())
 original=next(r for r in base['replacements'] if r['origin']==plan['placement']['origin'])
 for key in ['offset_cm','rotation_deg','scale']:assert original[key]==plan['placement'][key],('Original placement changed',key)
 lightplan=plan['local_light'];matches=[r for r in base['lights'] if math.dist(r['world_cm'][:2],lightplan['match_world_xy_cm'])<.01]
 assert len(matches)==1;light=matches[0];assert abs(light['radius_cm']-lightplan['radius_cm'])<.01
 current={'lumens':light['lumens'],'kelvin':light['kelvin'],'z_cm':light['world_cm'][2]}
 assert current in [lightplan['original'],lightplan['candidate']],('Unexpected local light edit',current)
 row={k:v for k,v in plan['placement'].items() if k!='original_script'};row['mesh']=mesh.get_path_name()
 expected={'schema':'dink-art/1','screen':1,'source':'SourceAssets/Art/Stonebrook/Refinements/FireplaceV2/placement_plan.json','replacements':[row],'elements':[],'source_blend_sha256':plan['source_blend_sha256']}
 if mode=='publish':
  if runtime.exists():assert json.loads(runtime.read_text())==expected,'Existing refinement differs; preserve it and review a new revision'
  light.update(lumens=lightplan['candidate']['lumens'],kelvin=lightplan['candidate']['kelvin']);light['world_cm'][2]=lightplan['candidate']['z_cm']
  # Publish the complete validated geometry layer before its local light adjustment.
  if not runtime.exists():atom(runtime,expected)
  if json.loads(basepath.read_text())!=base:atom(basepath,base)
 if runtime.exists():
  assert json.loads(runtime.read_text())==expected,'Published refinement mismatch'
  assert {'lumens':light['lumens'],'kelvin':light['kelvin'],'z_cm':light['world_cm'][2]}==lightplan['candidate'],'Reapply refinement after regenerating original kit lighting'
  report['runtime_published']=True
 assert all(sha(p)==h for p,h in protected.items()),'An original shared package changed'
 report.update(passed=True,mesh=mesh.get_path_name(),size_cm=size,lods=3,triangles=tris,convex_hulls=6,material_graph_verified=True,nanite_enabled=True,protected_original_packages=len(protected),texture_source_sha256={k:sha(SOURCE/f) for k,f in spec['textures'].items()})
 unreal.log('FIREPLACE REFINEMENT VERIFIED '+json.dumps({'mode':mode,'published':report['runtime_published']}))
except Exception as e:report['error']=str(e);raise
finally:atom(ROOT/'Saved/Art/fireplace_refinement_report.json',report)
