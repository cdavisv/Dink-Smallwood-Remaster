"""Check final baked file excludes raw donor images and preserves both source material optics."""
import bpy,json,sys,os,hashlib,traceback
from pathlib import Path
O=Path(__file__).resolve().parent
try:
 def optics(path):
  bpy.ops.wm.open_mainfile(filepath=str(path));ob=bpy.data.objects['SM_Pie_Rustic_01_LOD0'];return {m.name.replace('PhotoSource','PhotoBaked'):{k:list(bs.inputs[k].default_value)if k=='Subsurface Radius'else bs.inputs[k].default_value for k in ['IOR','Specular IOR Level','Coat Weight','Coat Roughness','Subsurface Weight','Subsurface Scale','Subsurface Radius','Alpha']}for m in ob.data.materials for bs in m.node_tree.nodes if bs.type=='BSDF_PRINCIPLED'}
 source=O/'PhotorealPieV1_Source.blend';export=O/'PhotorealPieV1_Export.blend';expected=optics(source);actual=optics(export);assert expected==actual
 images=[i for i in bpy.data.images if i.source in ['FILE','GENERATED']];assert len(images)==3;assert all(list(i.size)==[2048,2048]and i.packed_file is not None for i in images);assert all('Shortcrust'not in i.name for i in images);assert len(bpy.data.materials)==2
 r={'passed':True,'export_sha256':hashlib.sha256(export.read_bytes()).hexdigest(),'exactly_3_packed_2048_POT_images':[i.name for i in images],'raw1254reference_and_source_graphs_not_in_game_ready_export':True,'source_optics_all2slots_preserved':actual,'native_imported':False};(O/'export_contract_verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
