"""CPU raw-corner/triangle comparison. Frame must be independently established.

No frame search, tolerance relaxation, art edits or asset writes. Correspondence
can diagnose importer color loss but never makes that loss an accepted result.
"""
from collections import defaultdict
from itertools import product
from RoofNative.closed_eaves_uv_profile import reference_uvs,validate_native_guard
import numpy as np


def compare_raw(reference, source_roles, geometry, frame, *, transport_profile="legacy_2uv"):
    source_uv=reference_uvs(reference,transport_profile)
    uv_channels=source_uv.shape[1]//2
    rotation=np.asarray(frame['source_to_native_direction'],dtype=float)
    if (rotation.shape!=(3,3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation@rotation.T,np.eye(3),atol=1e-12,rtol=0)
            or frame.get('position_scale')!=100 or frame.get('uv_v_flip') is not True
            or type(frame.get('reverse_winding')) is not bool
            or not frame.get('provenance')):
        raise ValueError('Explicit independently verified source/native frame required')
    if geometry.get('schema')!='dink-static-mesh-geometry/1' or geometry.get('valid') is not True:
        raise ValueError('Actual native geometry snapshot required')
    raw=geometry['raw'];rows=np.asarray(raw['instances'],dtype=float)
    triangles=np.asarray(raw['triangles'],dtype=np.int64)
    if raw['uv_channels']!=uv_channels or rows.ndim!=2 or rows.shape[1]!=15+2*uv_channels or not np.isfinite(rows).all():
        raise ValueError('Raw profile UV/corner layout differs')
    validate_native_guard(rows[:,15:],reference,transport_profile,frame)
    ids=rows[:,0].astype(np.int64)
    if len(set(ids.tolist()))!=len(ids):raise ValueError('Duplicate native instance identity')
    lookup={value:i for i,value in enumerate(ids)}
    try:native_corners=np.array([[lookup[int(v)] for v in t[:3]] for t in triangles])
    except KeyError as exc:raise ValueError('Unresolved native triangle corner') from exc
    source_tri=np.asarray(reference['triangles'])
    if len(triangles)!=len(source_tri) or len(rows)!=len(reference['position_m']):
        raise ValueError('Triangle/corner multiplicity differs')
    expected_position=np.asarray(reference['position_m'])@rotation.T*100
    expected_uv=source_uv.copy()
    expected_uv[:,1::2]=1-expected_uv[:,1::2]
    if frame['reverse_winding']:source_tri=source_tri[:,[0,2,1]]
    native_position=rows[:,1:4]
    expected_roles=[source_roles[int(i)] for i in reference['triangle_material']]
    slots={int(s['slot']):s['imported_name'] for s in geometry['slots']}
    native_roles=[slots[int(t[3])] for t in triangles]
    # Same strict world-position tolerance as the accepted export (1e-5m).
    position_tolerance_cm=.001
    cell=position_tolerance_cm*4
    centroids=expected_position[source_tri].mean(axis=1)
    buckets=defaultdict(list)
    for i,c in enumerate(centroids):buckets[tuple(np.floor(c/cell).astype(np.int64))].append(i)
    unused=set(range(len(source_tri)));correspondence={};max_position=0.;max_uv=0.
    offsets=list(product((-1,0,1),repeat=3))
    for native_index,corners in enumerate(native_corners):
        p=native_position[corners];key=np.floor(p.mean(axis=0)/cell).astype(np.int64)
        matches=[]
        for delta in offsets:
            for candidate in buckets.get(tuple(key+delta),()):
                if candidate not in unused or expected_roles[candidate]!=native_roles[native_index]:continue
                expected=source_tri[candidate]
                for roll in range(3):
                    aligned=np.roll(expected,roll)
                    pe=float(np.abs(p-expected_position[aligned]).max())
                    ue=float(np.abs(rows[corners,15:]-expected_uv[aligned]).max())
                    if pe<=position_tolerance_cm and ue<=1e-6:
                        matches.append((candidate,aligned,pe,ue));break
        if not matches:raise ValueError('No source triangle with matching position/UV/winding/material')
        # Identical duplicate triangles retain their multiplicity. Disagreement
        # in data among duplicate candidates is ambiguous and must be refused.
        first=matches[0]
        for other in matches[1:]:
            for name in ('normal','tangent','bitangent_sign','color_linear_rgba'):
                if not np.array_equal(reference[name][first[1]],reference[name][other[1]]):
                    raise ValueError('Ambiguous overlapping source triangle attributes')
        candidate,aligned,pe,ue=first;unused.remove(candidate)
        max_position=max(max_position,pe);max_uv=max(max_uv,ue)
        for native_id,source_id in zip(corners,aligned):
            if int(native_id) in correspondence and correspondence[int(native_id)]!=int(source_id):
                raise ValueError('Shared native corner maps inconsistently')
            correspondence[int(native_id)]=int(source_id)
    if unused or len(correspondence)!=len(rows):raise ValueError('Incomplete corner bijection')
    order=np.array([correspondence[i] for i in range(len(rows))])
    def angle(a,b):
        lengths=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)
        if np.any(lengths<=1e-10):return float('inf')
        return float(np.degrees(np.arccos(np.clip(np.sum(a*b,axis=1)/lengths,-1,1))).max())
    normal_error=angle(rows[:,4:7],reference['normal'][order]@rotation.T)
    tangent_error=angle(rows[:,7:10],reference['tangent'][order]@rotation.T)
    rgba_error=np.abs(rows[:,11:15]-reference['color_linear_rgba'][order]).max(axis=0)
    sign_changes=int(np.count_nonzero(rows[:,10]!=reference['bitangent_sign'][order]))
    non_color=bool(normal_error<.05 and tangent_error<.05 and sign_changes==0)
    return dict(pass_raw=bool(non_color and rgba_error.max()<=1e-6),pass_non_color=non_color,
                max_position_error_cm=max_position,max_uv_error=max_uv,
                max_normal_degrees=normal_error,max_tangent_degrees=tangent_error,
                max_linear_RGBA_error=rgba_error.tolist(),bitangent_sign_changes=sign_changes,
                source_corner_by_native_instance={int(ids[i]):int(order[i]) for i in range(len(rows))},
                scope='Raw attributes/topology only; built buffers, UCX and pixels remain separate gates')
