"""Bounded import-conversion repair; never saves or activates a mesh."""
import json
import numpy as np
from RoofNative.closed_eaves_geometry_compare import compare_raw


def prepare_color_rows(reference, roles, geometry, frame, *, transport_profile="legacy_2uv"):
    report=compare_raw(reference,roles,geometry,frame,transport_profile=transport_profile)
    if not report['pass_non_color']:
        raise ValueError('Non-color source attributes differ; color-only repair refused')
    mapping=report['source_corner_by_native_instance']
    ids=sorted(mapping)
    if len(set(mapping.values()))!=len(ids):
        raise ValueError('Color correction requires a complete corner bijection')
    colors=np.asarray(reference['color_linear_rgba'])[[mapping[i] for i in ids]]
    if colors.shape!=(len(ids),4) or not np.isfinite(colors).all() or np.any((colors<0)|(colors>1)):
        raise ValueError('Invalid source linear colors')
    return ids,colors.tolist(),report


def restore_imported_colors(U,mesh,reference,roles,frame,guard, *, transport_profile="legacy_2uv"):
    if not callable(guard):raise ValueError('Own editor/build lease guard required')
    guard()
    before_json=U.DinkMaterialArtLibrary.inspect_static_mesh_geometry(mesh,0)
    before=json.loads(before_json)
    ids,colors,report=prepare_color_rows(reference,roles,before,frame,transport_profile=transport_profile)
    if report['pass_raw']:
        return dict(changed=False,saved=False,before=before,after=before,comparison=report)
    values=[U.LinearColor(*color) for color in colors]
    guard()
    result=U.DinkMaterialArtLibrary.restore_candidate_static_mesh_linear_colors(mesh,before_json,ids,values)
    after=json.loads(result)
    if after.get('valid') is not True:
        raise RuntimeError('Color correction failed; discard trial editor: '+str(after.get('error')))
    actual=compare_raw(reference,roles,after,frame,transport_profile=transport_profile)
    if not actual['pass_raw']:
        raise RuntimeError('Color correction postflight differs; discard trial editor')
    return dict(changed=True,saved=False,before=before,after=after,comparison=actual,
                scope='Raw linear color correction only; built quantization/rendering still pending')
