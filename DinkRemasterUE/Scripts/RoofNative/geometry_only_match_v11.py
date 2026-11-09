"""UV-independent oriented triangle matching. Ambiguities fail rather than using UV.
Pure Python; caller supplies fixed coordinate frame and approved numeric tolerances.
"""
from collections import defaultdict
from itertools import product
import math

def require(ok,message):
    if not ok:raise ValueError(message)

def candidates(native,source,position_tolerance_cm):
    require(position_tolerance_cm>0,'Positive position tolerance required')
    def cell(p):return tuple(math.floor(v/position_tolerance_cm) for v in p)
    bins=defaultdict(list)
    for index,triangle in enumerate(source):
        require(len(triangle['corners'])==3,'Expected source triangle')
        for rotation,corner in enumerate(triangle['corners']):
            require(len(corner['position_cm'])==3 and all(math.isfinite(v) for v in corner['position_cm']),'Invalid source position')
            bins[(triangle['material'],cell(corner['position_cm']))].append((index,rotation))
    rows=[]
    for index,triangle in enumerate(native):
        require(len(triangle['corners'])==3,'Expected native triangle')
        require(all(len(c['position_cm'])==3 and all(math.isfinite(v) for v in c['position_cm']) for c in triangle['corners']),'Invalid native position')
        base=cell(triangle['corners'][0]['position_cm']);found=[]
        for offset in product((-1,0,1),repeat=3):
            key=(triangle['material'],tuple(base[i]+offset[i] for i in range(3)))
            for sid,rotation in bins.get(key,()):
                corners=source[sid]['corners'];ordered=corners[rotation:]+corners[:rotation]
                error=max(abs(a-b) for n,s in zip(triangle['corners'],ordered) for a,b in zip(n['position_cm'],s['position_cm']))
                if error<=position_tolerance_cm:found.append({'source_index':sid,'rotation':rotation,'position_error_cm':error})
        rows.append(found)
    return rows

def compare(native,source,position_tolerance_cm,UV_tolerance,normal_component_tolerance):
    require(len(native)==len(source),'Triangle count differs; native SDK triangulation may need separate review')
    require(UV_tolerance>0 and normal_component_tolerance>0,'Positive attribute tolerances required')
    matches=candidates(native,source,position_tolerance_cm)
    require(all(len(row)==1 for row in matches),'Missing/ambiguous position+material match; UV must not choose correspondence')
    require(len({row[0]['source_index'] for row in matches})==len(source),'Geometry correspondence is not bijective')
    uv_error=normal_error=position_error=0.0
    for triangle,row in zip(native,matches):
        item=row[0];ref=source[item['source_index']]['corners'];r=item['rotation'];ref=ref[r:]+ref[:r]
        for actual,expected in zip(triangle['corners'],ref):
            require(all(len(c['UV0'])==2 and len(c['normal'])==3 and all(math.isfinite(v) for key in ('UV0','normal') for v in c[key]) for c in (actual,expected)),'Invalid corner attributes')
            uv_error=max(uv_error,max(abs(a-b) for a,b in zip(actual['UV0'],expected['UV0'])))
            normal_error=max(normal_error,max(abs(a-b) for a,b in zip(actual['normal'],expected['normal'])))
        position_error=max(position_error,item['position_error_cm'])
    require(uv_error<=UV_tolerance,'Actual built UV error exceeds approved limit')
    require(normal_error<=normal_component_tolerance,'Actual built normal error exceeds approved limit')
    return {'triangles':len(native),'UV_independent_bijection':True,'cyclic_only':True,
            'max_position_error_cm':position_error,'max_UV_error':uv_error,'max_normal_component_error':normal_error}
