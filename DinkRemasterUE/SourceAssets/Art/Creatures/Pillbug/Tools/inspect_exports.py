"""Independent binary-FBX units/model/geometry audit (stdlib; no Blender required)."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[3]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import fbxparse
reports={p.name:fbxparse.inspect(p) for p in sorted((ROOT/'Export').glob('*.fbx'))}
for name,row in reports.items():
 assert abs(row['unit_scale_factor']-1)<.001,(name,'units')
 assert 'root' in row['models'] and row['models']['root']['parent']=='Armature',(name,'root')
 assert all(abs(v-1)<.0001 for v in row['models']['root']['scaling']),(name,'rootscale')
 mesh=[v for v in row['models'].values() if v['type']=='Mesh']
 if name.startswith('SK_'):assert len(mesh)==1,(name,'meshcount')
 else:assert len(mesh)==0,(name,'armatureonly')
(ROOT/'fbx_inspection.json').write_text(json.dumps(reports,indent=2)+'\n')
print('PILLBUG INDEPENDENT FBX AUDIT PASS',len(reports),'files,header1cm,rootScale1,singleLODmesh/armature-onlyclips')
