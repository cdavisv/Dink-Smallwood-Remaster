"""Explicit pre-release candidate render configuration; original kit is untouched."""
import unreal,json,hashlib,shutil,sys
from pathlib import Path
assert '-game' not in unreal.SystemLibrary.get_command_line().split()
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve();source=ROOT/'SourceAssets/Art/Stonebrook/Refinements/FireplaceV2'
sys.path.insert(0,str(ROOT/'Scripts'))
from fireplace_source import validate_source_inputs
plan,_,_=validate_source_inputs(ROOT)
assert plan['destination']=='/Game/Dink/Refinements/FireplaceV2'
assert hashlib.sha256((ROOT/plan['source_blend']).read_bytes()).hexdigest()==plan['source_blend_sha256']
export=json.loads((ROOT/plan['source_export']).read_text())['assets'][0];assert export['nanite'] is True and plan['render_policy']['nanite'] is True
LIB=unreal.EditorAssetLibrary;EDIT=unreal.MaterialEditingLibrary
mesh=unreal.load_asset(plan['destination']+'/'+plan['mesh']);mat=unreal.load_asset(plan['destination']+'/M_FireplaceV2_Atlas');assert mesh and mat
out=ROOT/'Saved/FireplaceV2Integration/BeforeProductionRender';out.mkdir(parents=True,exist_ok=True)
for name in [plan['mesh'],'M_FireplaceV2_Atlas']:
 p=ROOT/'Content/Dink/Refinements/FireplaceV2'/(name+'.uasset');backup=out/p.name
 if not backup.exists():shutil.copy2(p,backup)
EDIT.set_base_material_usage(mat,unreal.MaterialUsage.MATUSAGE_NANITE,True);assert EDIT.has_material_usage(mat,unreal.MaterialUsage.MATUSAGE_NANITE);EDIT.recompile_material(mat);assert LIB.save_loaded_asset(mat,only_if_is_dirty=False)
settings=mesh.get_editor_property('nanite_settings')
for key,value in [('enabled',True),('fallback_target',unreal.NaniteFallbackTarget.PERCENT_TRIANGLES),('fallback_percent_triangles',1.),('fallback_relative_error',0.)]:settings.set_editor_property(key,value)
mesh.set_editor_property('nanite_settings',settings);assert LIB.save_loaded_asset(mesh,only_if_is_dirty=False)
exec((ROOT/'Scripts/inspect_fireplace_refinement.py').read_text())
