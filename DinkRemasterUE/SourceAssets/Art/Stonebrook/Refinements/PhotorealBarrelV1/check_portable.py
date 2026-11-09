import bpy,json,sys,os,hashlib
from pathlib import Path
O=Path(__file__).parent;rows=[]
for filename in ['PhotorealBarrelV1_Source.blend','PhotorealBarrelV1_Export.blend','Inputs/PhotorealPropsV1_Input.blend']:
 source=O/filename;pin=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));images=[i for i in bpy.data.images if i.source=='FILE'];unpacked=[i.name for i in images if not i.packed_file]
 assert not unpacked,(filename,unpacked)
 # Force every image path to an absent directory in a disposable verification copy.
 for i in images:i.filepath='//ABSENT_OLD_WORK_FOLDERS/'+i.name+'.png'
 target=O/'PortableCheck'/Path(filename).name;target.parent.mkdir(exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(target));bpy.ops.wm.open_mainfile(filepath=str(target));images=[i for i in bpy.data.images if i.source=='FILE'];loaded=[i.name for i in images if i.packed_file and len(i.pixels[:4])==4];assert len(loaded)==len(images)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==pin
 rows.append({'file':filename,'sha256':pin,'packed_images':len(images),'buffers_reopened_with_all_paths_absent':len(loaded),'passed':True})
(O/'portable_reopen_receipt.json').write_text(json.dumps({'passed':True,'files':rows,'test':'Disposable copies set every image path to a nonexistent oldWork directory; all image data reopened from packed payloads. Original files hash unchanged.'},indent=2));print('PORTABLE_REOPEN_PASSED',flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
