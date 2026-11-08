"""Independent stdlib audit of animation-only FBX units, hierarchy and sample span."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[4]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import fbxparse
p=ROOT/'Export/A_Dink_Fist.fbx';r=fbxparse.inspect(p);v,nodes=fbxparse.parse(p);objects=next(n for n in nodes if n.name=='Objects')
curves=[n for n in objects.children if n.name=='AnimationCurve'];times=[list(n.first('KeyTime').props[0]) for n in curves if n.first('KeyTime')]
span=(max(max(t) for t in times)-min(min(t) for t in times))/46186158000
assert abs(r['unit_scale_factor']-1)<1e-6
assert len([n for n in r['models'].values() if n['type']=='LimbNode'])==89
assert not any(n['type']=='Mesh' for n in r['models'].values())
assert r['models']['root']['parent']=='Armature'
assert all(abs(x-1)<1e-6 for x in r['models']['root']['scaling'])
assert abs(span-.4)<1e-6
r['animation']={'curve_count':len(curves),'sample_counts':sorted(set(len(t) for t in times)),'key_span_s':span,'frame_count':17,'fps':40,'impact_s':.175,'impact_frame':8}
(ROOT/'fbx_inspection.json').write_text(json.dumps(r,indent=2)+'\n');print('FIST BINARY FBX AUDIT PASS:89bones,noMesh,header1cm,.4s keys',r['animation'])
