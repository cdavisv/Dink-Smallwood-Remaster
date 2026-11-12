"""Source-only tolerance ambiguity census; no native frame/triangulation proof."""
from pathlib import Path
import json,gzip,hashlib
from geometry_only_match_v11 import candidates
ROOT=Path(__file__).resolve().parent

def source_triangles(mesh):
    triangles=[]
    for tri in mesh['triangles']:
        corners=[]
        for vertex,loop in zip(tri['vertices'],tri['loops']):
            p=mesh['vertices'][vertex];uv=mesh['UV'][loop];n=mesh['normals'][loop]
            corners.append({'position_cm':[p[0]*100,-p[1]*100,p[2]*100],
                            'UV0':[uv[0],1-uv[1]],'normal':[n[0],-n[1],n[2]]})
        triangles.append({'material':mesh['material_names'][mesh['polygon_material_indices'][tri['polygon']]],'corners':corners})
    return triangles

if __name__=='__main__':
    data=json.loads(gzip.open(ROOT/'source_reference_v11.json.gz','rt').read());rows=[]
    for name,mesh in data['objects'].items():
        if mesh['kind']!='render':continue
        triangles=source_triangles(mesh);matches=candidates(triangles,triangles,.01)
        ambiguous=[{'triangle':i,'candidates':r} for i,r in enumerate(matches) if len(r)!=1]
        rows.append({'mesh':name,'triangles':len(triangles),'ambiguous_triangles':len(ambiguous),'examples':ambiguous[:10]})
        print(name,len(triangles),'ambiguous',len(ambiguous),flush=True)
    report={'scope':'Source-to-source geometry-only 0.01cm tolerance census; actual native geometry/frame/SDK triangulation not verified','rows':rows,'total_ambiguous_triangles':sum(r['ambiguous_triangles'] for r in rows)}
    output=ROOT/'source_position_tolerance_v11.json';assert not output.exists();output.write_text(json.dumps(report,indent=2)+'\n')
