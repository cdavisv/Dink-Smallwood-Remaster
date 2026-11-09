from pathlib import Path
import bpy,json,sys,os,hashlib,shutil,math
O=Path(__file__).resolve().parent;source=O/'SharedGroundGameV2.blend';pin=hashlib.sha256(source.read_bytes()).hexdigest();probe=O/'PortableProbe_NoTextures';probe.mkdir(exist_ok=True);clone=probe/source.name;shutil.copyfile(source,clone);assert not(probe/'Textures').exists();bpy.ops.wm.open_mainfile(filepath=str(clone));expected={}
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 expected[ob.name]={'tris':len(ob.data.polygons),'min':[min(v.co[i]for v in ob.data.vertices)for i in range(3)],'max':[max(v.co[i]for v in ob.data.vertices)for i in range(3)]}
images=[]
for im in bpy.data.images:
 if im.source=='FILE'and im.name.startswith(('T_Shared_Ground_','T_Shared_Willow_Leaf_')):
  assert im.packed_file and len(im.pixels)>0;missing=not Path(bpy.path.abspath(im.filepath)).exists();assert missing;images.append({'image':im.name,'packed':True,'missing_external_file':True,'size':list(im.size),'pixels_read':len(im.pixels)})
assert len(images)==12;manifest=json.loads((O/'ExportV2/manifest.json').read_text());prep=json.loads((O/'asset_preparation_v2.json').read_text());reednames={r['asset']for r in prep['reed_clusters']};tasks=[]
for entry in manifest['assets']:
 names=[entry['name']+'_LOD'+str(i)for i in range(3)]if entry['name']in reednames else[entry['name']];tasks.append((O/'ExportV2'/entry['files']['fbx'],names))
for root in reednames:
 for i in range(3):name=root+'_LOD'+str(i);tasks.append((O/'ReedLOD'/(name+'.fbx'),[name]))
rows=[]
for index,(path,names)in enumerate(tasks):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=True,use_image_search=False);meshes={ob.name:ob for ob in bpy.context.scene.objects if ob.type=='MESH'};assert set(meshes)==set(names),(path,set(meshes),names);models=[]
 for name,ob in meshes.items():
  ex=expected[name];coords=[ob.matrix_world@v.co for v in ob.data.vertices];mn=[min(v[i]for v in coords)for i in range(3)];mx=[max(v[i]for v in coords)for i in range(3)];err=max([abs(mn[i]-ex['min'][i])for i in range(3)]+[abs(mx[i]-ex['max'][i])for i in range(3)]);tris=sum(len(f.vertices)-2 for f in ob.data.polygons);assert tris==ex['tris']and err<1e-5,(path,name,tris,ex['tris'],err);assert all(math.isfinite(x)for v in coords for x in v);models.append({'model':name,'actual_import_triangles':tris,'source_bounds_error_m':err,'UV_layers':len(ob.data.uv_layers)})
 rows.append({'file':str(path.relative_to(O)),'actual_models':models})
 if index%25==0:print('GROUND_ACTUAL_REIMPORT',index,len(tasks),flush=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==pin;r={'status':'Actualpacked independent-folder reopen and everyFBXimport passed','source_sha256':pin,'packed_images':images,'actual_FBX_files_imported':len(rows),'roundtrips':rows,'source_unchanged':True,'native_approval':False};(O/'packed_roundtrip_v2.json').write_text(json.dumps(r,indent=2)+'\n');print('SHAREDGROUND_PACKED_ALL_ROUNDTRIPS_PASS',len(rows),flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
