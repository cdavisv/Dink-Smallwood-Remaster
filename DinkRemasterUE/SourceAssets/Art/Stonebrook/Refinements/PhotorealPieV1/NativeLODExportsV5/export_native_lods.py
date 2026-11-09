import bpy,sys,os,json,hashlib,traceback
from pathlib import Path
from types import SimpleNamespace
O=Path(__file__).resolve().parent;BASE=O.parent/'V5_OpticalLOD';sys.path.insert(0,str(BASE/'Pipeline'))
from dinkasset.export_ue import export_fbx,unhidden
try:
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=BASE/'PhotorealPieV1_Export.blend';pin=sha(source);assert pin=='2c407ff8bb6485ace844bf816316a19a8f49ae09ac70b19a80e0551fe4f7e88a'
 bpy.ops.wm.open_mainfile(filepath=str(source));rows=[]
 for i in range(3):
  ob=bpy.data.objects['SM_Pie_Rustic_01_LOD'+str(i)];path=O/(ob.name+'.fbx');assert not path.exists(),'Refuse existing perLOD file';assert all(abs(float(v))<1e-7 for v in ob.location)
  a=SimpleNamespace(renders=[ob],collision=[],armatures=[],sockets=[])
  with unhidden([ob]):export_fbx(a,str(path),'all',None)
  rows.append({'LOD':i,'file':path.name,'sha256':sha(path),'triangles':len(ob.data.polygons),'source_object':ob.name,'material_slots':[m.name for m in ob.data.materials]})
 assert sha(source)==pin
 (O/'lod_manifest.json').write_text(json.dumps({'source_export_sha256':pin,'files':rows,'units':'FBX UnitScaleFactor100; metres in Blender -> centimetres in Unreal','import_contract':'Import LOD0 alone; attach LOD1/LOD2 individually using StaticMeshEditorSubsystem.import_lod; never combine all three siblings','native_imported':False},indent=2)+'\n')
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
