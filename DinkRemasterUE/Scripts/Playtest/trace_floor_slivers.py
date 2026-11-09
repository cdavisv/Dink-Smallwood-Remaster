#!/usr/bin/env python3
"""Offline rays through saved framebuffer pixels against actual imported floor triangles."""
import argparse
import json
import math
from pathlib import Path
import re
import numpy as np
from PIL import Image

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--image',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
c=json.loads(a.runtime.read_text());g=json.loads(a.geometry.read_text());im=Image.open(a.image).convert('RGB');pixels=np.array(im).astype(np.int16);mask=(pixels[:,:,2]>pixels[:,:,0]+20)&(pixels[:,:,2]>pixels[:,:,1]+5)&(pixels[:,:,0]>50)&(pixels[:,:,2]>100);mask[:420]=False;mask[:,1100:]=False
ys,xs=np.where(mask);probes={(int(x),int(y)) for x,y in zip(xs,ys)}
for x,y in list(probes):probes.update((xx,y) for xx in [x-1,x+1] if 0<=xx<im.width)
triangles={}
for component in g['components']:
 key='underfloor' if 'SM_Underfloor_' in component['mesh'] else 'floor';v=np.array(component['world_vertices_cm'],dtype=np.float64);ids=np.array(g['assets'][component['mesh']]['triangles'],dtype=np.int64);triangles.setdefault(key,[]).append(v[ids])
triangles={k:np.concatenate(v) for k,v in triangles.items()}
o=np.array(c['camera_cm'],dtype=np.float64);rot=c['camera_rotation'];pitch,yaw=[math.radians(float(re.search(k+r': ([-\d.]+)',rot)[1])) for k in ['pitch','yaw']];f=np.array([math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)]);right=np.array([-math.sin(yaw),math.cos(yaw),0]);up=np.cross(f,right);tan=math.tan(math.radians(c['FOV'])/2)
def intersect(t,d):
 e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-10;inv=np.zeros_like(det);inv[valid]=1/det[valid];s=o-t[:,0];u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inv*np.einsum('j,ij->i',d,q);distance=inv*np.einsum('ij,ij->i',e2,q);hits=valid&(u>=0)&(v>=0)&(u+v<=1)&(distance>1e-5)
 return float(distance[hits].min()) if hits.any() else None
rows=[]
for x,y in sorted(probes):
 d=f+right*((2*(x+.5)/im.width-1)*tan)+up*((1-2*(y+.5)/im.height)*tan/(im.width/im.height));d/=np.linalg.norm(d)
 hits={key:intersect(t,d) for key,t in triangles.items()};planes={str(z):(o+d*((z-o[2])/d[2])).tolist() for z in [0,-11,-16]}
 rows.append({'pixel':[x,y],'RGB':im.getpixel((x,y)),'blue_mask':bool(mask[y,x]),'direction':d.tolist(),'hit_distance_cm':hits,'plane_world_cm':planes})
under=np.concatenate([np.array(c['world_vertices_cm']) for c in g['components'] if 'SM_Underfloor_' in c['mesh']]);out={'camera':c['camera_cm'],'camera_rotation':rot,'FOV':c['FOV'],'resolution':list(im.size),'projection':'HorizontalFOV; actualviewport; half-pixel centers; no camera roll','geometry':'Actualloaded source-description triangles and component transforms','underfloor_bounds_cm':[under.min(axis=0).tolist(),under.max(axis=0).tolist()],'blue_pixels':len(xs),'rays':rows,'limitations':['Tests floor and underfloor triangles only; does not exclude wall or prop surfaces. Need geometry/scene confirmation before interpreting sky misses.']};a.out.write_text(json.dumps(out,indent=2)+'\n');print('Bluepixels',len(xs),'miss_both',sum(r['blue_mask'] and all(v is None for v in r['hit_distance_cm'].values()) for r in rows));print(json.dumps([r for r in rows if r['blue_mask']][:3],indent=2))
