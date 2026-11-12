import bpy,json,hashlib,sys
from pathlib import Path
def meshes():
 result={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  m=o.data;payload=([tuple(v.co) for v in m.vertices],[tuple(f.vertices) for f in m.polygons],{u.name:[tuple(x.uv) for x in u.data] for u in m.uv_layers},[tuple(n.vector) for n in m.corner_normals],{a.name:[tuple(x.color) for x in a.data] for a in m.color_attributes},[list(r) for r in o.matrix_world])
  result[o.name]=hashlib.sha256(repr(payload).encode()).hexdigest()
 return result

root=Path(sys.argv[sys.argv.index('--')+1]).resolve() if '--' in sys.argv else Path(__file__).resolve().parents[1]
record=json.loads((root/'Evidence/PACKED_SOURCE.json').read_text());source=root/'Source/House439_ClosedEaves.blend'
assert hashlib.sha256(source.read_bytes()).hexdigest()==record['packed_source_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));assert meshes()==record['mesh_signatures']
rows=[]
for item in record['images']:
 im=bpy.data.images[item['image']];actual=Path(bpy.path.abspath(im.filepath)).resolve();expected=(root/item['path']).resolve()
 assert im.filepath.startswith('//') and actual==expected and root in actual.parents
 assert actual.is_file() and hashlib.sha256(actual.read_bytes()).hexdigest()==item['sha256']
 assert im.packed_file and hashlib.sha256(bytes(im.packed_file.data)).hexdigest()==item['sha256']
 assert list(im.size)==item['dimensions'] and im.colorspace_settings.name==item['colorspace']
 rows.append(item['image'])
report={'pass':True,'actual_root':str(root),'source_sha256':record['packed_source_sha256'],'exact_mesh_signatures':len(record['mesh_signatures']),'exact_external_and_packed_images':len(rows),'all_image_paths_relative_and_resolved_inside_packet':True,'native_executed':False}
(root/'Evidence/RELOCATED_SOURCE_READBACK.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
