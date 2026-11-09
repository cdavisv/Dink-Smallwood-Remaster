import json,math,re
from pathlib import Path
import numpy as np
from PIL import Image
OUT=Path('/home/davisc/Work/DinkQA/SurfaceNative/Before')
s=json.loads(Path('/home/davisc/Work/DinkQA/FloorNativePreparation/native_snapshot.json').read_text())
p=np.array(s['vertices']);v=np.array([p[x[0]] for x in s['instances']]);tris=v[np.array([x[1] for x in s['triangles']])]
layout=json.loads(Path('/home/davisc/Work/DinkSurfaceDelivery/DinkRemasterUE/Content/Dink/Data/Art/stonebrook.json').read_text())
world=[]
for row in layout['elements']:
 if row['mesh'].endswith('.SM_Floor_Oak_2m_01'):
  assert row['rotation_deg']==[0,0,0]
  world.append(tris*np.array(row['scale'])+np.array(row['world_cm']))
tri=np.concatenate(world);e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
c=json.loads((OUT/'door-room-camera.json').read_text());o=np.array(c['camera_cm'])
rot=c['camera_rotation'];pitch,yaw=[math.radians(float(re.search(k+r': ([-\d.]+)',rot)[1])) for k in ['pitch','yaw']]
f=np.array([math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)])
r=np.array([-math.sin(yaw),math.cos(yaw),0]);u=np.cross(f,r)
tan=math.tan(math.radians(c['field_of_view'])/2)
im=Image.open(OUT/'door-room.png')
rows=[]
for x in range(648,663):
 y=600;d=f+r*((2*(x+.5)/1280-1)*tan)+u*((1-2*(y+.5)/720)*tan/(1280/720));d/=np.linalg.norm(d)
 h=np.cross(np.broadcast_to(d,e2.shape),e2);a=np.einsum('ij,ij->i',e1,h);good=np.abs(a)>1e-10
 inv=np.zeros_like(a);inv[good]=1/a[good];sv=o-tri[:,0];bu=inv*np.einsum('ij,ij->i',sv,h);q=np.cross(sv,e1);bv=inv*np.einsum('j,ij->i',d,q);t=inv*np.einsum('ij,ij->i',e2,q)
 hit=good&(bu>=0)&(bv>=0)&(bu+bv<=1)&(t>.0001)
 t0=float(t[hit].min()) if hit.any() else None
 plane=o+d*(-o[2]/d[2]);rows.append({'pixel':[x,y],'RGB':im.getpixel((x,y)),'floor_mesh_hit_cm':t0,'plane_z0_world_cm':plane.tolist()})
receipt={'method':'Read-only camera projection and exact imported mesh triangles across all56transforms; tests floor intersection only, not other objects. Half-pixel centers, horizontalFOV70.','rays':rows}
(OUT/'gap-ray-diagnostic.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(rows,indent=1))
