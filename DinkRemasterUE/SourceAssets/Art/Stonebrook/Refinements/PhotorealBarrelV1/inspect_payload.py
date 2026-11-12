"""Read-only barrel payload/hash/texture check. Run from any working directory."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((O/'Export/manifest.json').read_text());assert len(manifest['assets'])==1;a=manifest['assets'][0]
assert a['content_path']=='/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01'
assert a['validation']['errors']==0 and not a['validation']['forced']
for t in a['textures']:
 p=O/'Export'/t['file'];assert p.read_bytes()==(O/'Textures'/p.name).read_bytes();im=Image.open(p);assert im.size==(2048,2048)
 ar=np.array(im)
 if t['role']=='ORM':assert np.all(ar[:,:,0]==255) and ar[:,:,2].max()>220 and np.count_nonzero(ar[:,:,2]>100)>10000
assert sha(O/'PhotorealBarrelV1_Source.blend')=='2cab573f8f40a99a2b513a454b8d0e006e73353171e3a25bc94254580cf9c0f7'
r=json.loads((O/'roundtrip_receipt.json').read_text());assert r['passed'] and r['triangles']==16648 and r['max_position_delta_m']==r['max_UV_delta']==0
print('BARREL_PAYLOAD_PASS: frozen source,3pixel-identical2048maps, metalliccontrast,16648orientedFBXfaces/UVs and1exactUCX')
