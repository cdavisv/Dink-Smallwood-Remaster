"""Check authored meadow coverage and the south gateway in world coordinates."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'SourceAssets/Art/StonebrookExterior'
corners=next(s for s in json.loads((ROOT/'ImportData/screens.json').read_text())['screens'] if s['screen']==439)['corners']
nw,ne,sw,se=[corners[k] for k in ['nw','ne','sw','se']]
def world_point(pixel):
    u,v=pixel[0]/600,pixel[1]/400
    return [nw[i]*(1-u)*(1-v)+ne[i]*u*(1-v)+sw[i]*(1-u)*v+se[i]*u*v for i in range(2)]
layout=json.loads((ART/'exterior_layout.json').read_text())
tiles=[]
for e in layout['elements']:
    if e['mesh']!='SM_Ground_Meadow_20m_01':continue
    center=world_point(e['source_pixel']);half=[10*e['scale'][i] for i in range(2)]
    tiles.append({'name':e['name'],'min':[center[i]-half[i] for i in range(2)],'max':[center[i]+half[i] for i in range(2)],'physical':e.get('collision',True)})
uncovered=[]
for y in range(0,401,10):
    for x in range(0,601,10):
        p=world_point([x,y])
        if not any(t['physical'] and all(t['min'][i]-1e-5<=p[i]<=t['max'][i]+1e-5 for i in range(2)) for t in tiles):uncovered.append([x,y])
gate=world_point([339,366]);gate_clear=True
for e in layout['elements']:
    if not e['name'].startswith('FenceSouth'):continue
    p=world_point(e['source_pixel'])
    if abs(gate[0]-p[0])<2.15+.28 and abs(gate[1]-p[1])<.12+.28:gate_clear=False
report={'tool':'authored exterior floor and gateway layout check','screen':439,'passed':not uncovered and gate_clear,
        'sample_count':2501,'uncovered_source_pixels':uncovered,'south_gateway_clear_for_56cm_capsule':gate_clear,
        'ground_tiles':tiles,'notes':['Floor tiles share a rectangular world grid covering all skewed screen corners with a2cm outer margin.',
                                   'Exact triangle/capsule behavior is verified separately by the Unreal walking tests.']}
(ART/'layout_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print('EXTERIOR FLOOR:',2501-len(uncovered),'/2501 samples covered; GATE:',gate_clear)
if not report['passed']:raise SystemExit(1)
