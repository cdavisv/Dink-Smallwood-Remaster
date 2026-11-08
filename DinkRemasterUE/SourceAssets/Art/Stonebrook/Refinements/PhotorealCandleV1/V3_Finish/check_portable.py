"""Reopen a disposable copy with every image filename deliberately unavailable."""
import bpy,json,sys,os,hashlib,traceback
from pathlib import Path
O=Path(__file__).resolve().parent
try:
 kind=os.environ.get('DINK_CANDLE_PORTABLE_KIND','source');assert kind in ['source','export']
 source=O/('PhotorealCandleV1_Export.blend' if kind=='export' else 'PhotorealCandleV1_Source.blend');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(source)
 bpy.ops.wm.open_mainfile(filepath=str(source));images=[i for i in bpy.data.images if i.source in ['FILE','GENERATED']];assert images
 assert all(i.packed_file is not None for i in images),'Missing packed image'
 for image in images:image.filepath='/nonexistent/basket-portability/'+image.name
 p=O/'PortableTest';p.mkdir(exist_ok=True);copy=p/(kind+'_paths_absent.blend');bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(copy))
 bpy.ops.wm.open_mainfile(filepath=str(copy));images=[i for i in bpy.data.images if i.source in ['FILE','GENERATED']]
 rows=[]
 for image in images:
  assert image.packed_file is not None and len(image.pixels)>0 and image.size[0]>0
  rows.append({'image':image.name,'size':list(image.size),'packed_bytes':len(image.packed_file.data),'pixels_reopened':len(image.pixels)})
 assert sha(source)==pin
 result={'passed':True,'source_sha256':pin,'source_unchanged':True,'packed_images_reopened':rows,'test':'Disposable copy only; all image paths nonexistent before saving and reopening','native_imported':False}
 (O/('portable_export_receipt.json' if kind=='export' else 'portable_receipt.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
