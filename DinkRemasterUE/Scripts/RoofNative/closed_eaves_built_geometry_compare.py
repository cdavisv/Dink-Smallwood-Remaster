"""Read-only built-corner proof, with exact native ToFColor(true) byte oracle.

Decoded quantization errors are measurements, not pixel/appearance acceptance.
"""
import numpy as np
from RoofNative.closed_eaves_geometry_compare import compare_raw
from RoofNative.closed_eaves_uv_profile import reference_uvs


def compare_built(reference,roles,geometry,frame, *, transport_profile="legacy_2uv"):
    uv_channels=reference_uvs(reference,transport_profile).shape[1]//2
    raw=compare_raw(reference,roles,geometry,frame,transport_profile=transport_profile)
    if not raw['pass_raw']:raise ValueError('Raw source preservation must pass first')
    built=geometry['built'];vertices=np.asarray(built['vertices'],dtype=float)
    indices=np.asarray(built['indices'],dtype=np.int64)
    if (vertices.ndim!=2 or vertices.shape[1]!=17+2*uv_channels or not np.isfinite(vertices).all()
            or built['uv_channels']!=uv_channels or built.get('color0_present') is not True
            or len(indices)!=len(reference['triangles'])*3 or np.any(indices<0)
            or np.any(indices>=len(vertices))):
        raise ValueError('Built color/UV/index layout differs')
    if np.any(vertices[:,13:17]!=np.floor(vertices[:,13:17])) or np.any((vertices[:,13:17]<0)|(vertices[:,13:17]>255)):
        raise ValueError('Invalid built RGBA bytes')
    slots=np.full(len(indices)//3,-1,dtype=np.int64)
    for section in built['sections']:
        first,count=int(section['first_index']),int(section['triangles'])
        if first%3 or count<0 or first<0 or first+count*3>len(indices):
            raise ValueError('Invalid built section range')
        target=slice(first//3,first//3+count)
        if np.any(slots[target]!=-1):raise ValueError('Overlapping built sections')
        slots[target]=section['slot']
    if np.any(slots<0):raise ValueError('Uncovered built triangles')
    corners=vertices[indices];rgba=corners[:,13:17]/255
    decoded=rgba.copy()
    decoded[:,:3]=np.where(rgba[:,:3]<=.04045,rgba[:,:3]/12.92,((rgba[:,:3]+.055)/1.055)**2.4)
    # Expand welded vertices into per-triangle corners for the same topology,
    # cyclic winding, UV, material and source N/T checks as the raw snapshot.
    ids=np.arange(len(indices))
    rows=np.column_stack((ids,corners[:,:9],corners[:,12],decoded,corners[:,17:]))
    triangles=np.column_stack((ids.reshape(-1,3),slots))
    proxy=dict(schema='dink-static-mesh-geometry/1',valid=True,slots=geometry['slots'],
               raw=dict(uv_channels=uv_channels,instances=rows.tolist(),triangles=triangles.tolist()))
    report=compare_raw(reference,roles,proxy,frame,transport_profile=transport_profile)
    if not report['pass_non_color']:raise ValueError('Built non-color source attributes differ')
    by_source={source:native for native,source in raw['source_corner_by_native_instance'].items()}
    native_bytes={int(row[0]):np.asarray(row[1:],dtype=float)
                  for row in geometry['raw']['expected_built_color_rgba8']}
    expected=np.array([native_bytes[by_source[report['source_corner_by_native_instance'][i]]]
                       for i in range(len(indices))])
    if not np.array_equal(corners[:,13:17],expected):
        raise ValueError('Built color bytes differ from exact native linear-to-sRGB encoding')
    expected_y=np.cross(corners[:,3:6],corners[:,6:9])*corners[:,12,None]
    actual_y=corners[:,9:12]
    lengths=np.linalg.norm(expected_y,axis=1)*np.linalg.norm(actual_y,axis=1)
    if np.any(lengths<=1e-10):raise ValueError('Zero built bitangent')
    error=np.degrees(np.arccos(np.clip(np.sum(expected_y*actual_y,axis=1)/lengths,-1,1)))
    if error.max()>=.05:raise ValueError('Built signed bitangent reconstruction differs')
    return dict(pass_built_structure_and_encoding=True,
                max_position_error_cm=report['max_position_error_cm'],max_uv_error=report['max_uv_error'],
                max_normal_degrees=report['max_normal_degrees'],max_tangent_degrees=report['max_tangent_degrees'],
                max_bitangent_reconstruction_degrees=float(error.max()),
                decoded_quantization_RGBA_error=report['max_linear_RGBA_error'],
                exact_native_encoded_bytes=True,pixel_or_appearance_acceptance=False,
                scope='Actual built topology/N-T-UV-role/sign and native packing proof; GPU/render proof pending')
