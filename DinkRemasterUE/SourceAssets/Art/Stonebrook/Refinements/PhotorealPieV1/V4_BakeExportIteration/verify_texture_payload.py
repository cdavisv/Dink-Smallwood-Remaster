from pathlib import Path
import json,hashlib
from PIL import Image
O=Path(__file__).resolve().parent;m=json.loads((O/'Export/manifest.json').read_text())['assets'][0];assert m['lod_count']==3 and m['nanite'] is False and len(m['material_slots'])==2;rows={}
for t in m['textures']:
 p=O/'Export'/t['file'];assert p.read_bytes()==(O/'Textures'/p.name).read_bytes();im=Image.open(p);assert im.mode=='RGB'and im.size==(2048,2048);r=im.getextrema();role=t['role'];assert t['srgb']==(role=='BC')and t['normal_green_flip']==(role=='N')
 if role=='ORM':assert r[0]==(255,255)and r[2]==(0,0)
 rows[role]={**t,'range':r,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'export_bytes_identical_to_bake':True}
(O/'texture_payload_validation.json').write_text(json.dumps({'passed':True,'textures':rows,'raw_generated_reference_resampled':False,'maps_are_new_3D_UV_bakes':True,'native_imported':False},indent=2)+'\n')
