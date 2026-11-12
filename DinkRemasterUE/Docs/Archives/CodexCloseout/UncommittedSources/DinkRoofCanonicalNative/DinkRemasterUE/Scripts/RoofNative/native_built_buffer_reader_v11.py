"""Read-only library for separately reviewed Unreal execution; no import/save/launch."""
import math

FLAGS = {
    'use_full_precision_u_vs': True,
    'recompute_normals': False,
    'recompute_tangents': True,
    'use_mikk_t_space': True,
    'remove_degenerates': False,
    'generate_lightmap_u_vs': False,
}

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def read_mesh(U, mesh, subsystem, expected_lods):
    """Return actual indexed render corners for every LOD; makes no acceptance claim."""
    reader = getattr(getattr(U, 'ProceduralMeshLibrary', None), 'get_section_from_static_mesh', None)
    require(callable(reader), 'Actual built-buffer reader unavailable')
    require(mesh.get_editor_property('allow_cpu_access') is True, 'CPU buffer access is required')
    require(mesh.get_num_lods() == expected_lods, 'Unexpected LOD count')
    result = []
    for lod in range(expected_lods):
        build = subsystem.get_lod_build_settings(mesh, lod)
        flags = {key: build.get_editor_property(key) for key in FLAGS}
        require(flags == FLAGS, 'Required build settings differ at LOD %d: %r' % (lod, flags))
        sections = []
        for section in range(mesh.get_num_sections(lod)):
            output = reader(mesh, lod, section)
            require(isinstance(output, tuple) and len(output) == 5, 'Unexpected actual reader signature')
            vertices, indices, normals, uvs, tangents = output
            require(len(vertices) == len(normals) == len(uvs) == len(tangents), 'Incomplete built vertex attributes')
            require(len(indices) > 0 and len(indices) % 3 == 0, 'Incomplete built triangles')
            require(all(isinstance(i, int) and 0 <= i < len(vertices) for i in indices), 'Invalid built indices')
            slot = subsystem.get_lod_material_slot(mesh, lod, section)
            material = mesh.get_material(slot)
            require(material is not None, 'Missing actual section material')
            rows = []
            for v, n, uv in zip(vertices, normals, uvs):
                row = {'position_cm': [float(v.x), float(v.y), float(v.z)],
                       'normal': [float(n.x), float(n.y), float(n.z)],
                       'UV0': [float(uv.x), float(uv.y)]}
                require(all(math.isfinite(x) for values in row.values() for x in values), 'Nonfinite built corner')
                rows.append(row)
            sections.append({'section': section, 'material_slot': slot,
                             'material_path': material.get_path_name(),
                             'vertices': rows, 'indices': list(indices)})
        require(bool(sections), 'No actual render sections')
        result.append({'lod': lod, 'build_settings': flags, 'sections': sections})
    return {'scope': 'Actual LODResources only; source correspondence and Nanite stream not asserted', 'LODs': result}
