import bpy,json,hashlib
from pathlib import Path
import sys
R=Path(sys.argv[sys.argv.index('--proof-dir')+1]).resolve() if '--proof-dir' in sys.argv else Path(__file__).resolve().parent;rows=[];report=json.loads((R/'PACKED_RESOURCE_CHECK.json').read_text())
for row in report['scenes']:
 P=R/row['file'];assert hashlib.sha256(P.read_bytes()).hexdigest()==row['sha256'];bpy.ops.wm.open_mainfile(filepath=str(P));m=bpy.data.materials['MI_Shared_ThinWavyGlass2m'];expected={r['name']:r['sha256']for r in row['maps']};seen=[]
 for node in m.node_tree.nodes:
  if node.type=='TEX_IMAGE':
   im=node.image;assert im.packed_file;assert len(im.pixels)==im.size[0]*im.size[1]*4 and im.has_data;assert hashlib.sha256(bytes(im.packed_file.data)).hexdigest()==expected[im.name];seen.append(im.name)
 assert len(seen)==3;p=m.node_tree.nodes.get('Principled BSDF');assert p.inputs['Transmission Weight'].default_value==1 and abs(p.inputs['IOR'].default_value-1.48)<1e-6;pane=bpy.data.objects['InsetGlassPane.009'];assert len(pane.data.polygons)==54;rows.append({'scene':row['file'],'sha256':row['sha256'],'packed_maps_exact':3,'pane_polygons':54,'source_transmission':1,'IOR':1.48})
print(json.dumps({'status':'PASS_actual_relocated_scene_reopen_without_local_texture_files','rows':rows,'scope':'SourceCPUreference only; no native validation'},indent=2))
