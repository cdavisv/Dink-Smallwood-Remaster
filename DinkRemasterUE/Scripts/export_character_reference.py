"""Export installed Epic animation references for local Blender rig fitting.
Run with export_character_reference.sh. These references are Epic content,
not authored/CC0 art; retain only the fitted rig in production exports.
"""
import os
import unreal,json
from pathlib import Path
out=Path(os.environ.get('DINK_REFERENCE_DIR', '/tmp/dink-character-reference'))
out.mkdir(parents=True,exist_ok=True)
mesh=unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
if mesh is None:raise RuntimeError('Missing Manny reference')
options=unreal.FbxExportOption()
options.set_editor_property('ascii',False)
options.set_editor_property('level_of_detail',False)
options.set_editor_property('collision',False)
options.set_editor_property('export_morph_targets',False)
options.set_editor_property('bake_material_inputs',unreal.FbxMaterialBakeMode.DISABLED)
task=unreal.AssetExportTask()
task.object=mesh
task.filename=str(out/'Manny_Rest.fbx')
task.exporter=unreal.SkeletalMeshExporterFBX()
task.options=options
task.automated=True
task.prompt=False
task.replace_identical=True
if not unreal.Exporter.run_asset_export_task(task):raise RuntimeError('Reference export failed')
report={'mesh':mesh.get_path_name(),'skeleton':mesh.get_editor_property('skeleton').get_path_name(),'rest_fbx':task.filename}
assets=unreal.EditorAssetLibrary.list_assets('/Game/Characters/Mannequins/Anims',recursive=True,include_folder=False)
idle=[p for p in assets if 'Idle' in p and 'Unarmed' in p and 'Pose' not in p and 'Offset' not in p]
report['idle_candidates']=idle
for path in idle:
 anim=unreal.load_asset(path)
 if isinstance(anim,unreal.AnimSequence):
  options.set_editor_property('export_preview_mesh',True)
  animtask=unreal.AssetExportTask()
  animtask.object=anim
  animtask.filename=str(out/'Manny_Idle.fbx')
  animtask.exporter=unreal.AnimSequenceExporterFBX()
  animtask.options=options
  animtask.automated=True
  animtask.prompt=False
  animtask.replace_identical=True
  if not unreal.Exporter.run_asset_export_task(animtask):raise RuntimeError('Idle reference export failed')
  report['idle_fbx']=animtask.filename
  report['idle_asset']=path
  break
(out/'reference.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('DINK REFERENCE EXPORT OK '+json.dumps(report))
