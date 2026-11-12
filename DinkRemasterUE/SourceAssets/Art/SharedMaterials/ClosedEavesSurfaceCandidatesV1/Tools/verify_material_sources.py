"""Reopen only the candidate material/reuse sources, without a cottage dependency."""
import bpy,json,hashlib,importlib.util
from pathlib import Path
D=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('material_fingerprint',Path(__file__).parent/'material_fingerprint.py')
fp=importlib.util.module_from_spec(spec);spec.loader.exec_module(fp)
expected=json.loads((D/'EXTRACTION.json').read_text());reports=[]
for name,count in (('ClosedEavesSurfaces_Source.blend',0),('IndependentReuse_2m4m.blend',22)):
 source=D/name;before=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==count
 for role,row in expected['roles'].items():assert fp.snapshot(bpy.data.materials['MI_Shared_'+role])[1]==row['fingerprint'],role
 for image in expected['images']:
  im=bpy.data.images[image['image']];path=Path(bpy.path.abspath(im.filepath)).resolve();assert path==D/image['file'] and im.filepath.startswith('//')
  assert im.packed_file and hashlib.sha256(bytes(im.packed_file.data)).hexdigest()==image['sha256']
  assert hashlib.sha256(path.read_bytes()).hexdigest()==image['sha256']
  assert list(im.size)==image['size'] and im.colorspace_settings.name==image['colorspace']
 if count:
  for row in expected['fixtures']:
   o=bpy.data.objects[row['object']];m=o.data;assert len(m.polygons)==1 and len(m.vertices)==4
   assert o.data.materials[0].name=='MI_Shared_'+row['role']
   assert max(v.co.x for v in m.vertices)-min(v.co.x for v in m.vertices)==row['width_m']
   assert max(v.co.y for v in m.vertices)-min(v.co.y for v in m.vertices)==2
   assert max(v.uv.x for v in m.uv_layers['UV0'].data)==row['width_m']/2
   assert max(v.uv.y for v in m.uv_layers['UV0'].data)==1
   assert all(v.uv.x==row['selector'] for v in m.uv_layers['UV1_SharedData'].data)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 reports.append({'source':name,'sha256':before,'exact_material_graphs':len(expected['roles']),'exact_external_packed_images':len(expected['images']),'mesh_objects':len(meshes),'passed':True})
(D/'SOURCE_REOPEN_VERIFICATION.json').write_text(json.dumps({'passed':True,'sources':reports,'scope':'portable material sources/independent repeat fixtures only; not registry or native acceptance'},indent=2)+'\n');print(reports)
