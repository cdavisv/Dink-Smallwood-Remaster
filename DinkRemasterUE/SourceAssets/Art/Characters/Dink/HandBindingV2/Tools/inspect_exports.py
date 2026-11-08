"""Independent binaryFBX audit of isolated skeletalhandcandidate."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[4]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import fbxparse
rows={}
for p in sorted((ROOT/'Export').glob('*.fbx')):
 r=fbxparse.inspect(p);assert abs(r['unit_scale_factor']-1)<1e-6
 assert len([m for m in r['models'].values() if m['type']=='Mesh'])==1
 assert len([m for m in r['models'].values() if m['type']=='LimbNode'])==89
 assert r['models']['root']['parent']=='Armature' and all(abs(v-1)<1e-6 for v in r['models']['root']['scaling'])
 rows[p.name]=r
assert len(rows)==4
(ROOT/'fbx_inspection.json').write_text(json.dumps(rows,indent=2)+'\n');print('HANDV2 FBX AUDIT PASS4files,89bones,header1cm,rootScale1,singlemesh eachLOD')
