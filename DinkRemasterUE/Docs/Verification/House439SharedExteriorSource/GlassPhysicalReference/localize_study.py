import bpy,json,hashlib
from pathlib import Path
import sys
D=Path(sys.argv[sys.argv.index('--out')+1]).resolve() if '--out' in sys.argv else Path(__file__).resolve().parent;L=Path(__file__).resolve().parents[4]/'SourceAssets/Art/SharedMaterials'
assert not (D/'PACKED_RESOURCE_CHECK.json').exists(),'Use fresh study folder; preserve frozen proof';entry=json.loads((L/'manifest.json').read_text())['materials']['ThinWavyGlass2m'];allowed={Path(r['file']).name:(L/r['file'],r['sha256'])for r in entry['textures'].values()};rows=[]
for filename in ['ActualCottagePane_OpticalReference.blend','ActualCottagePane_ReflectionControl.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(D/filename));m=bpy.data.materials['MI_Shared_ThinWavyGlass2m'];maps=[]
 for node in m.node_tree.nodes:
  if node.type!='TEX_IMAGE':continue
  im=node.image;p,sha=allowed[im.name];assert im.packed_file and hashlib.sha256(bytes(im.packed_file.data)).hexdigest()==sha;im.filepath=bpy.path.relpath(str(p),start=str(D));maps.append({'name':im.name,'sha256':sha,'packed':True,'relative_path':im.filepath})
 assert len(maps)==3;bpy.ops.wm.save_as_mainfile(filepath=str(D/filename),compress=True);rows.append({'file':filename,'sha256':hashlib.sha256((D/filename).read_bytes()).hexdigest(),'maps':maps})
(D/'PACKED_RESOURCE_CHECK.json').write_text(json.dumps({'status':'PASS_registered_map_bytes_exact_packed_relative_paths','scenes':rows,'scope':'Study scenes only; cottage/library source bytes unchanged'},indent=2)+'\n')
