"""Build/check immutable camera-fade material variants from the existing Blender kit.
DINK_CAMERA_CHECK=1 performs a read-only check. DINK_CAMERA_REVISION selects a new
asset revision; existing material packages are validated and never overwritten.
DINK_CAMERA_MATERIALS_ONLY=1 adds/checks variants without touching floor framing or room art.
"""
import hashlib,json,math,os,re
from pathlib import Path
import unreal
assert '-game' not in unreal.SystemLibrary.get_command_line().split(), 'Camera material authoring requires an editor commandlet'
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
LIB=unreal.EditorAssetLibrary; EDIT=unreal.MaterialEditingLibrary
CHECK=os.environ.get('DINK_CAMERA_CHECK')=='1'
MATERIALS_ONLY=os.environ.get('DINK_CAMERA_MATERIALS_ONLY')=='1'
REVISION=os.environ.get('DINK_CAMERA_REVISION','v1')
assert re.fullmatch(r'[A-Za-z0-9_]+',REVISION),'Invalid revision'
REPORT=ROOT/'Saved/Art/camera_materials_report.json'
report={'passed':False,'check_only':CHECK,'revision':REVISION,'materials':[],'original_packages_changed':False}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atom(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)
def require(c,msg):
 if not c:raise RuntimeError(msg)
def graph(mat):
 require(mat.get_editor_property('blend_mode')==unreal.BlendMode.BLEND_MASKED,'Material must be masked')
 require(mat.get_editor_property('dither_opacity_mask'),'Material needs temporal opacity dithering')
 require(abs(mat.get_editor_property('opacity_mask_clip_value')-.5)<1e-6,'Dithered opacity needs clip .5 for exact0/1 coverage')
 node=EDIT.get_material_property_input_node(mat,unreal.MaterialProperty.MP_OPACITY_MASK)
 require(isinstance(node,unreal.MaterialExpressionShadowReplace),'ShadowPassSwitch is required')
 inputs=EDIT.get_inputs_for_material_expression(mat,node)
 require(len(inputs)==2 and isinstance(inputs[0],unreal.MaterialExpressionScalarParameter) and isinstance(inputs[1],unreal.MaterialExpressionConstant),'Unexpected shadow-pass graph')
 require(str(inputs[0].get_editor_property('parameter_name'))=='DinkCameraOpacity','Wrong fade parameter')
 require(abs(inputs[0].get_editor_property('default_value')-1)<1e-6,'Default surface must be opaque')
 require(abs(inputs[1].get_editor_property('r')-1)<1e-6,'Shadow pass must stay opaque')
def hull(points):
 pts=sorted(set(points))
 def cross(a,b,c):
  length=math.hypot(b[0]-a[0],b[1]-a[1])
  return ((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/max(length,1e-12)
 lo=[]
 for p in pts:
  while len(lo)>1 and cross(lo[-2],lo[-1],p)<=.02:lo.pop()
  lo.append(p)
 hi=[]
 for p in reversed(pts):
  while len(hi)>1 and cross(hi[-2],hi[-1],p)<=.02:hi.pop()
  hi.append(p)
 return lo[:-1]+hi[:-1]
try:
 runtime_path=ROOT/'Content/Dink/Data/Art/stonebrook.json'
 runtime=json.loads(runtime_path.read_text());require(runtime.get('schema')=='dink-art/1' and runtime.get('screen')==1,'Expected authored starting house')
 source_spec=None if MATERIALS_ONLY else json.loads((ROOT/runtime['source']).read_text())
 variants={};originals={}
 for kind in ['Oak','Limewash','Fieldstone','WroughtIron','Thatch']:
  source='/Game/Dink/Materials/Stonebrook/MI_Stonebrook_'+kind
  package=ROOT/'Content/Dink/Materials/Stonebrook'/('MI_Stonebrook_'+kind+'.uasset')
  originals[package]=sha(package)
  target='/Game/Dink/Camera/Stonebrook/M_CameraFade_'+kind+'_'+REVISION
  existing=LIB.does_asset_exist(target)
  require(existing or not CHECK,'Missing camera variant '+target)
  if existing:mat=unreal.load_asset(target)
  else:
   mat=LIB.duplicate_asset(source,target);require(isinstance(mat,unreal.Material),'Could not duplicate source material')
   mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED);mat.set_editor_property('dither_opacity_mask',True);mat.set_editor_property('opacity_mask_clip_value',.5)
   alpha=EDIT.create_material_expression(mat,unreal.MaterialExpressionScalarParameter,100,1000)
   alpha.set_editor_property('parameter_name','DinkCameraOpacity');alpha.set_editor_property('default_value',1.)
   opaque=EDIT.create_material_expression(mat,unreal.MaterialExpressionConstant,100,1150);opaque.set_editor_property('r',1.)
   switch=EDIT.create_material_expression(mat,unreal.MaterialExpressionShadowReplace,320,1000)
   require(EDIT.connect_material_expressions(alpha,'',switch,'Default'),'Cannot connect fade')
   require(EDIT.connect_material_expressions(opaque,'',switch,'Shadow'),'Cannot preserve shadows')
   require(EDIT.connect_material_property(switch,'',unreal.MaterialProperty.MP_OPACITY_MASK),'Cannot connect mask')
   EDIT.recompile_material(mat);graph(mat);require(LIB.save_loaded_asset(mat,only_if_is_dirty=False),'Cannot save new material')
  graph(mat);variants[source+'.MI_Stonebrook_'+kind]=mat.get_path_name()
  report['materials'].append({'original':source,'original_package_sha256':originals[package],'variant':mat.get_path_name(),'existing_package_kept':existing,'default_opacity':1,'shadow_opacity':1,'clip':.5})
 floor_count=0;occluders=0;polygon=None;floor_z=None
 if not MATERIALS_ONLY:
  points=[];heights=[];floor_count=0;occluders=0
  for row in runtime['elements']:
   name=row['mesh'].split('.')[-1];category=source_spec['assets'].get(name,{}).get('class')
   occlude=row.get('camera_occluder',category in ('kit_wall','kit_ceiling','kit_piece'))
   if occlude:
    occluders+=1
    if not CHECK:row['camera_occluder']=True
    else:require(row.get('camera_occluder') is True,'Missing authored occluder tag '+row['name'])
   if category!='kit_floor':continue
   mesh=unreal.load_asset(row['mesh']);require(isinstance(mesh,unreal.StaticMesh),'Missing floor mesh')
   bound=mesh.get_bounds();o,e=bound.origin,bound.box_extent
   rotation=row.get('rotation_deg',[0,0,0]);location=row['world_cm'];scale=row.get('scale',[1,1,1])
   transform=unreal.Transform(location=unreal.Vector(*location),rotation=unreal.Rotator(pitch=rotation[0],yaw=rotation[1],roll=rotation[2]),scale=unreal.Vector(*scale))
   for x in [o.x-e.x,o.x+e.x]:
    for y in [o.y-e.y,o.y+e.y]:
     p=unreal.MathLibrary.transform_location(transform,unreal.Vector(x,y,o.z+e.z));points.append((float(p.x),float(p.y)));heights.append(float(p.z))
   floor_count+=1
  require(floor_count>0,'No actual floor meshes')
  points=[(round(x,5),round(y,5)) for x,y in points];polygon=hull(points);report['observed_hull']=polygon;require(len(polygon)==4,'Current camera framing requires an authored convex quadrilateral room')
  require(max(heights)-min(heights)<.5,'Floor is not horizontal; author a separate framing policy')
  floor_z=sum(heights)/len(heights)
 config_path=ROOT/'Content/Dink/Data/Art/camera_materials.json'
 config=json.loads(config_path.read_text()) if config_path.exists() else {'schema':'dink-camera/1'}
 expected={'polygon_cm':polygon,'floor_z_cm':floor_z}
 current=config.get('floor_framing',{}).get('1',{})
 def same_polygon(a,b):
  return len(a)==len(b) and all(min(math.dist(x,y) for y in b)<.02 for x in a)
 require(config.get('schema')=='dink-camera/1','Unsupported camera schema')
 if CHECK:
  require(config.get('material_variants')==variants,'Runtime fade mapping differs from approved variants')
  if not MATERIALS_ONLY:require(same_polygon(current.get('polygon_cm',[]),polygon) and abs(current.get('floor_z_cm',1e9)-floor_z)<.02,'Framing footprint differs from actual floor meshes')
 else:
  config['material_variants']=variants
  if not MATERIALS_ONLY and (not same_polygon(current.get('polygon_cm',[]),polygon) or abs(current.get('floor_z_cm',1e9)-floor_z)>=.02):
   config.setdefault('floor_framing',{})['1']=expected
  # Leave byte-identical files alone on repeat runs.
  old=json.loads(config_path.read_text()) if config_path.exists() else None
  if old!=config:atom(config_path,config)
  if json.loads(runtime_path.read_text())!=runtime:atom(runtime_path,runtime)
 require(all(sha(p)==h for p,h in originals.items()),'An original material package changed')
 report.update(passed=True,materials_only=MATERIALS_ONLY,floor_policy_unchanged=MATERIALS_ONLY,floor_mesh_count=floor_count,floor_polygon_cm=polygon,floor_z_cm=floor_z,occluder_count=occluders,existing_variants_overwritten=0)
 atom(REPORT,report);unreal.log('DINK CAMERA MATERIALS CHECK PASS' if CHECK else 'DINK CAMERA MATERIALS READY')
except Exception as error:
 report['error']=str(error);atom(REPORT,report);raise
