"""Independent binary FBX bind-rest comparison against existing accepted Mother exports."""
import sys,json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parents[1];P=next(p for p in H.parents if(p/'DinkRemaster.uproject').exists());sys.path.insert(0,str(P.parent/'tools/blender'));from dinkasset import fbxparse
report={'status':'PASS','lods':[]}
for i in range(4):
 old=fbxparse.inspect(H.parents[1]/'Export'/('SK_Mother_LOD%d.fbx'%i));f=H/'Export'/('SK_Mother_ClothingV1_LOD%d.fbx'%i);new=fbxparse.inspect(f)
 assert new['unit_scale_factor']==old['unit_scale_factor'] and abs(new['unit_scale_factor']-1)<1e-6
 a={n:m for n,m in old['models'].items()if m['type']=='LimbNode'};b={n:m for n,m in new['models'].items()if m['type']=='LimbNode'}
 assert len(a)==len(b)==89 and a==b,(i,'actual exported rest/hierarchy mismatch')
 assert len([m for m in new['models'].values()if m['type']=='Mesh'])==1
 report['lods'].append({'lod':i,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size,'unit_header':new['unit_scale_factor'],'bones_exact_baseline':89,'meshes':1})
(H/'independent_fbx_readback.json').write_text(json.dumps(report,indent=2)+'\n');print('FBX READBACK PASS all4/89 exact baseline rest bones')
