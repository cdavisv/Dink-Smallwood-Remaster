import ast,hashlib,json
from pathlib import Path
import unreal
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
SCRIPT=ROOT/'Scripts/import_floor_surface.py'
EDIT=unreal.MaterialEditingLibrary
TEXTURES='/Game/Dink/Textures/Stonebrook/Refinements'
module=ast.parse(SCRIPT.read_text());function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='verify_material_recipe')
exec(compile(ast.Module(body=[function],type_ignores=[]),str(SCRIPT),'exec'),globals())
material=unreal.load_asset('/Game/Dink/Materials/Stonebrook/Refinements/MI_Stonebrook_FloorOakV1')
verified=json.loads(Path('/home/artist/Work/DinkQA/FloorNativePreparation/native-verify.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p:sha(ROOT/p) for p in verified['saved_package_sha256']}
assert before==verified['saved_package_sha256']
baseline=verify_material_recipe(material)
BC=EDIT.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
N=EDIT.get_material_property_input_node(material,unreal.MaterialProperty.MP_NORMAL)
ORM=EDIT.get_material_property_input_node(material,unreal.MaterialProperty.MP_ROUGHNESS)
SPEC=EDIT.get_material_property_input_node(material,unreal.MaterialProperty.MP_SPECULAR)
rows=[]
def rejection(label,mutate,restore):
 try:
  mutate()
  try:verify_material_recipe(material)
  except AssertionError as error:rows.append({'case':label,'rejected':True,'reason':str(error)})
  else:raise RuntimeError('Broken graph accepted: '+label)
 finally:restore()
 assert verify_material_recipe(material)==baseline,'Control recipe not restored: '+label
rejection('normal_disconnected',lambda:EDIT.disconnect_material_property(material,unreal.MaterialProperty.MP_NORMAL),lambda:EDIT.connect_material_property(N,'RGB',unreal.MaterialProperty.MP_NORMAL))
old=BC.get_editor_property('texture')
rejection('BC_points_to_normal_texture',lambda:BC.set_editor_property('texture',N.get_editor_property('texture')),lambda:BC.set_editor_property('texture',old))
rejection('roughness_reads_ORM_red_instead_of_green',lambda:EDIT.connect_material_property(ORM,'R',unreal.MaterialProperty.MP_ROUGHNESS),lambda:EDIT.connect_material_property(ORM,'G',unreal.MaterialProperty.MP_ROUGHNESS))
rejection('specular_wrong_value',lambda:SPEC.set_editor_property('r',.25),lambda:SPEC.set_editor_property('r',.35))
rejection('wrong_UV_channel',lambda:BC.set_editor_property('const_coordinate',1),lambda:BC.set_editor_property('const_coordinate',0))
for label,prop in [('reuse_existing_BC_as_emissive',unreal.MaterialProperty.MP_EMISSIVE_COLOR),('reuse_existing_BC_as_WPO',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)]:
 rejection(label,lambda p=prop:EDIT.connect_material_property(BC,'RGB',p),lambda p=prop:EDIT.disconnect_material_property(material,p))
extra=[]
def add_gain():
 gain=EDIT.create_material_expression(material,unreal.MaterialExpressionConstant,-200,1000);gain.set_editor_property('r',.25)
 multiply=EDIT.create_material_expression(material,unreal.MaterialExpressionMultiply,0,1000)
 extra.extend([gain,multiply]);assert EDIT.connect_material_expressions(BC,'RGB',multiply,'A');assert EDIT.connect_material_expressions(gain,'',multiply,'B');assert EDIT.connect_material_property(multiply,'',unreal.MaterialProperty.MP_BASE_COLOR)
def remove_gain():
 assert EDIT.connect_material_property(BC,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
 for node in reversed(extra):EDIT.delete_material_expression(material,node)
rejection('double_apply_point25_BC_gain',add_gain,remove_gain)
after={p:sha(ROOT/p) for p in before};assert after==before
report={'passed':len(rows)==8 and all(r['rejected'] for r in rows),'method':'Fresh saved material loaded, eight in-memory mutations through real Unreal APIs; production verifier extracted without changing its function. Every mutation restored; no save or shader compile. Native unit test separately covers hidden UV/displacement pins.','cases':rows,'importer_sha256':sha(SCRIPT),'native_verification_sha256':sha(Path('/home/artist/Work/DinkQA/FloorNativePreparation/native-verify.json')),'saved_packages_unchanged':before==after,'saved_package_sha256':after}
Path('/home/artist/Work/DinkQA/FloorNativePreparation/shader-mutations.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['passed'];print('EIGHT REAL SHADER MUTATIONS REJECTED; SAVED PACKAGES UNCHANGED',flush=True)
