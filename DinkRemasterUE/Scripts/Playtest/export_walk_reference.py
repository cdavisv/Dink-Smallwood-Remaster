"""Read installed Epic walk solely as local Blender fitting reference; no package writes."""
import unreal,json
from pathlib import Path
assert '-game' not in unreal.SystemLibrary.get_command_line().split(), 'Run only in a full editor session; never in -game'
out=Path(Path.home()/'Work/DinkQA/CharacterReference');out.mkdir(parents=True,exist_ok=True)
paths=unreal.EditorAssetLibrary.list_assets('/Game/Characters/Mannequins/Anims',recursive=True,include_folder=False)
paths=[p for p in paths if p.rsplit('/',1)[-1].split('.')[0]=='MF_Unarmed_Walk_Fwd']
assert len(paths)==1,paths
anim=unreal.load_asset(paths[0]);assert isinstance(anim,unreal.AnimSequence)
options=unreal.FbxExportOption()
for k,v in [('ascii',False),('level_of_detail',False),('collision',False),('export_morph_targets',False),('export_preview_mesh',True)]:options.set_editor_property(k,v)
options.set_editor_property('bake_material_inputs',unreal.FbxMaterialBakeMode.DISABLED)
task=unreal.AssetExportTask();task.object=anim;task.filename=str(out/'Manny_Walk_Reference.fbx');task.exporter=unreal.AnimSequenceExporterFBX();task.options=options;task.automated=True;task.prompt=False;task.replace_identical=False
assert unreal.Exporter.run_asset_export_task(task)
(out/'reference.json').write_text(json.dumps({'source':paths[0],'file':task.filename,'use':'Epic local fitting reference only; exclude from authored exports'},indent=2)+'\n')
unreal.log('QA_WALK_REFERENCE_EXPORTED '+task.filename)
