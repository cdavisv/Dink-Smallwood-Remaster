"""Offline bounded floor proof; input archive only, no Unreal or desktop access."""
from pathlib import Path
import json,re
import numpy as np
from PIL import Image
import argparse
parser=argparse.ArgumentParser(description='Check archived exact-camera floor pixels and loaded native CW-front geometry, offline.')
parser.add_argument('--qa-root', type=Path, required=True, help='Saved/VisualQA or portable Evidence folder')
parser.add_argument('--out', type=Path, required=True)
args=parser.parse_args()
P=args.qa_root.resolve()
assert not args.out.exists(), 'Preserve prior evidence'
b=json.load(open(P/'Runtime/north-floor-right.json'));a=json.load(open(P/'Runtime/skirt-north-exact.json'));contract={}
for k in ['pawn_cm','camera_cm','FOV','arm_cm','target_offset','socket_offset','floor_framing_shift']:
 assert np.allclose(b[k],a[k],rtol=0,atol=1e-6),k;contract[k]=a[k]
def rotation(s):return [float(re.search(n+r': ([-\d.]+)',s)[1]) for n in ['pitch','yaw','roll']]
assert rotation(b['camera_rotation'])==rotation(a['camera_rotation']);contract['rotation']=rotation(a['camera_rotation'])
g=json.load(open(P/'Runtime/skirt_geometry.json'));assert len(g['components'])==1
c=g['components'][0];assert c['actor_hidden'] is False and c['visible'] is True
v=np.array(c['world_vertices_cm']);ids=np.array(g['assets'][c['mesh']]['triangles']);assert v.shape==(48,3) and ids.shape==(96,3)
t=v[ids];e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];o=np.array(b['camera_cm']);normal=-np.cross(e1,e2);normal/=np.linalg.norm(normal,axis=1)[:,None]
old=json.load(open(P/'north_floor_right_ray_diagnosis.json'));rays=[r for r in old['rays'] if r['blue_mask'] and all(x is None for x in r['hit_distance_cm'].values())];assert len(rays)==7;results=[]
for r in rays:
 d=np.array(r['direction']);h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-10;inv=np.zeros_like(det);inv[valid]=1/det[valid];s=o-t[:,0];u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);vv=inv*np.einsum('j,ij->i',d,q);distance=inv*np.einsum('ij,ij->i',e2,q);hit=np.where(valid&(u>=-1e-8)&(vv>=-1e-8)&(u+vv<=1+1e-8)&(distance>1e-5))[0];assert len(hit)>0,r['pixel'];near=hit[np.argmin(distance[hit])];dot=float(normal[near]@d);assert dot<0
 results.append({'pixel':r['pixel'],'native_skirt_distance_cm':float(distance[near]),'native_triangle':int(near),'UE_CW_front_geometric_normal_dot_ray':dot})
checks=[]
for rel in ['Baseline/north-floor-right.png','ExposureRender/Route/fresh-house.png','SkirtRender/Route/fresh-house.png','SkirtRender/NorthFixtures/north-exact.png','SkirtRender/NorthFixtures/skirt-north-pitch-10.png','SkirtRender/NorthFixtures/skirt-north-pitch-25.png','SkirtRender/NorthFixtures/skirt-north-pitch-35.png']:
 im=np.array(Image.open(P/rel).convert('RGB')).astype(np.int16);mask=(im[:,:,2]>im[:,:,0]+20)&(im[:,:,2]>im[:,:,1]+5)&(im[:,:,0]>50)&(im[:,:,2]>100);mask[:420]=False;mask[:,1100:]=False
 count=int(mask.sum());checks.append({'image':rel,'blue_pixels_in_bounded_roi':count});
 if rel.startswith('SkirtRender/'):assert count==0,rel
out={'normal_convention':'UE left-handed/CW front uses negative right-handed cross(edge1,edge2). The importer proves exact oriented FBX triangle identity; FBX normals are imported without recomputation. Installed Python wrapper has no stored-normal getter, so this is geometric front orientation, not a stored shading-normal assertion. Initial RH-cross assertion failure is preserved as a convention error.','matched_camera_contract':contract,'exact_match_tolerance_cm':1e-6,'original7_escape_rays_hit_actual_native_skirt_front_faces':results,'pixel_checks':checks,'limits':['Bounded floor ROI plus normal pitch−10/−18/−25/−35 at one measured north position; not universal all-world/all-angle coverage.','Source triangle hits alone do not establish Nanite pixels; exact matched native screenshots independently confirm the formerly blue pixels are closed.','Accepted−2EV and all material/light/camera parameters are unchanged.']}
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(out,indent=2)+'\n');print('EXACT_CAMERA_PASS;7/7actual_native_frontface_hits;0bluein5afterviews')
