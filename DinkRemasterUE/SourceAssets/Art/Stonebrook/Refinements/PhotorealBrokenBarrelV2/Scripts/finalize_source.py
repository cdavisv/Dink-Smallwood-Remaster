"""Remove review-only intact/private data from an independent broken-source copy."""
import argparse,sys,os,traceback,json,hashlib
from pathlib import Path
import bpy

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--project-root',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 source=a.input.resolve();out=a.output.resolve();project=a.project_root.resolve()
 if not(project/'DinkRemaster.uproject').is_file()or out.exists()or out.suffix!='.blend'or out==project or out.is_relative_to(project)or project.is_relative_to(out):raise ValueError('New disposable Blend output outside project required')
 bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False);bpy.context.preferences.filepaths.save_version=0
 coll=bpy.data.collections['SM_Barrel_Broken_SourceStudy'];parts=[o for o in coll.objects if o.name!='Accepted_Intact_Comparison'];assert len(parts)==28 and all(o.type=='MESH'for o in parts)
 allowed={'MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron'};assert {m.name for o in parts for m in o.data.materials}==allowed
 review=bpy.data.objects.get('Accepted_Intact_Comparison')
 if review:bpy.data.objects.remove(review,do_unlink=True)
 for group in [bpy.data.meshes,bpy.data.materials,bpy.data.images,bpy.data.collections]:
  for item in group:item.use_fake_user=False
 bpy.data.orphans_purge(do_recursive=True)
 assert not any(m.name.startswith('MI_Barrel')for m in bpy.data.materials)
 assert all(i.packed_file for i in bpy.data.images if i.source=='FILE') and not bpy.data.libraries
 out.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(out))
 report=dict(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),target_materials=sorted(allowed),target_objects=len(parts),private_intact_comparison_removed=True,unused_private_data_purged=True,geometry_material_graph_mutations=False,native_executed=False)
 with out.with_suffix('.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
try:main();sys.stdout.flush();os._exit(0)
except BaseException:traceback.print_exc();sys.stderr.flush();os._exit(1)
