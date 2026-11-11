"""Read actual PNG bytes; check PBR channels, tangent unit vectors and periodic seam.
Requires Python3 Pillow and NumPy. Does not modify images or imply native acceptance.
"""
from pathlib import Path
from PIL import Image
import numpy as np,json,hashlib
P=Path(__file__).resolve().parents[1];out={};reg=json.load(open(P/'registry.json'))
for role,entry in reg.items():
 for kind,record in entry['textures'].items():
  f=P/'Textures'/Path(record['file']).name;assert hashlib.sha256(f.read_bytes()).hexdigest()==record['sha256'];im=Image.open(f);assert im.mode=='RGB';a=np.asarray(im);assert a.shape==(1024,1024,3)
  r={'shape':list(a.shape),'min':a.min(axis=(0,1)).tolist(),'max':a.max(axis=(0,1)).tolist(),'mean':a.mean(axis=(0,1)).tolist(),'sha256_matches_registry':True,'srgb':record['srgb']}
  if kind=='ORM':assert np.all(a[:,:,0]==255) and np.all(a[:,:,2]==0)
  if kind=='N':
   vectors=a.astype(float)/127.5-1;length=np.linalg.norm(vectors,axis=2);r['normal_length_range']=[float(length.min()),float(length.max())];assert length.min()>.98 and length.max()<1.02;assert record['normal_orientation']=='OpenGL +Y' and record['native_flip_green'] is True and record['srgb'] is False
  if role=='ThornBark2m':
   edge=np.concatenate([(a[:,0].astype(float)-a[:,-1]).reshape(-1),(a[0].astype(float)-a[-1]).reshape(-1)]);seam=float(np.abs(edge).mean());inside=float((np.abs(np.diff(a.astype(float),axis=0)).mean()+np.abs(np.diff(a.astype(float),axis=1)).mean())/2);r.update(seam_mean_absolute_codes=seam,interior_neighbor_mean_absolute_codes=inside);assert seam<=inside*2+1
  out[f.name]=r
(P/'TextureChecks.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS six PNGs: registry hashes, channels, unit normals and bark seam')
