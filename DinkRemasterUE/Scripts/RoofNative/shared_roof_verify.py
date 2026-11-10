"""Actual FBX -> actual native buffer/convex verification; no module-load native calls."""
from pathlib import Path
import importlib.util
import math
from shared_roof_contract import SOURCE, require
from native_built_buffer_reader_v11 import read_mesh
from native_buffer_capture_v11d import section
from native_collision_readback_v11 import inspect_collision
from native_import_metadata_v11 import inspect_sources
from geometry_only_match_v11 import compare
import vista_geometry


def decode_source(root, record):
    """Use the pinned stdlib binary decoder; material identities come from actual FBX names."""
    root = Path(root)
    spec = importlib.util.spec_from_file_location('shared_roof_binary_decoder', root / SOURCE / 'fbxparse.py')
    F = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(F)
    _, nodes = F.parse(root / SOURCE / record['file'])
    top = {n.name: n for n in nodes}
    objects = {n.props[0]: n for n in top['Objects'].children}
    connections = top['Connections'].children

    def linked(model, kind):
        return [objects[c.props[1]] for c in connections if len(c.props) > 2 and c.props[0] == 'OO'
                and c.props[2] == model.props[0] and c.props[1] in objects
                and objects[c.props[1]].name == kind]

    def layer(g, name, field, index, width, count):
        n = g.first(name)
        values = n.first(field).props[0]
        rows = [values[i:i+width] for i in range(0, len(values), width)]
        mode = n.first('ReferenceInformationType').props[0]
        if mode == 'IndexToDirect':
            rows = [rows[i] for i in n.first(index).props[0]]
        else:
            require(mode == 'Direct', 'Unsupported serialized corner indexing')
        mapping = n.first('MappingInformationType').props[0]
        if mapping == 'AllSame':
            rows = rows[:1] * count
        else:
            require(mapping == 'ByPolygonVertex', 'Unsupported corner mapping')
        require(len(rows) == count, 'Incomplete serialized corner values')
        return rows

    triangles, hulls = [], []
    for model in [n for n in objects.values() if n.name == 'Model']:
        name = model.props[1].split('\0')[0]
        g, = linked(model, 'Geometry')
        raw = g.first('Vertices').props[0]
        points = [raw[i:i+3] for i in range(0, len(raw), 3)]
        if name.startswith('UCX_' + record['name'] + '_'):
            hulls.append([[p[0]*100, -p[1]*100, p[2]*100] for p in points])
            continue
        require(name == record['name'], 'Unexpected FBX render model')
        polygons, current = [], []
        for i in g.first('PolygonVertexIndex').props[0]:
            current.append(i if i >= 0 else -i-1)
            if i < 0:
                polygons.append(current)
                current = []
        require(not current and all(len(p) == 3 for p in polygons), 'Explicit source triangles required')
        count = 3 * len(polygons)
        uv = layer(g, 'LayerElementUV', 'UV', 'UVIndex', 2, count)
        normals = layer(g, 'LayerElementNormal', 'Normals', 'NormalsIndex', 3, count)
        names = [n.props[1].split('\0')[0] for n in linked(model, 'Material')]
        require(set(names) == set(record['material_slots']), 'Actual FBX material roles differ')
        m = g.first('LayerElementMaterial')
        ids = m.first('Materials').props[0]
        if m.first('MappingInformationType').props[0] == 'AllSame':
            ids = ids * len(polygons)
        require(len(ids) == len(polygons), 'Incomplete actual FBX role coverage')
        for index, polygon in enumerate(polygons):
            corners = []
            for k, vi in enumerate(polygon):
                p, n, t = points[vi], normals[3*index+k], uv[3*index+k]
                corners.append(dict(position_cm=[p[0]*100, -p[1]*100, p[2]*100],
                                    normal=[n[0], -n[1], n[2]], UV0=[t[0], 1-t[1]]))
            triangles.append(dict(material=names[ids[index]], corners=corners))
    require(len(triangles) == record['triangles'] and len(hulls) == record['UCX'], 'Actual FBX inventory differs')
    return triangles, hulls


def make_mesh_verifier(U, root, contract, tolerances):
    """Concrete callback for shared_roof_native import/readback. Caller approves tolerances.
    Uses reviewed legacy geometry-independent correspondence and typed authored convex reader.
    Does not invent stored tangent-Y handedness or claim world/cooked collision acceptance.
    """
    require(set(tolerances) == {'position_cm', 'UV0', 'normal_component'} and
            all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in tolerances.values()),
            'Explicit Root-approved geometry/UV/normal tolerances required')
    sources = {r['name']: decode_source(root, r) for r in contract['meshes']}
    roles = {r['opaque']: r['source_material'] for r in contract['materials']}
    subsystem = U.get_default_object(U.StaticMeshEditorSubsystem)

    def verify(mesh, record):
        source, hulls = sources[record['name']]
        captured = read_mesh(U, mesh, subsystem, 1)
        actual = []
        for sec in captured['LODs'][0]['sections']:
            package = sec['material_path'].split('.')[0]
            require(package in roles, 'Unrecognized actual section material')
            for i in range(0, len(sec['indices']), 3):
                actual.append(dict(material=roles[package],
                                   corners=[sec['vertices'][j] for j in sec['indices'][i:i+3]]))
        geometry = compare(actual, source, tolerances['position_cm'], tolerances['UV0'],
                           tolerances['normal_component'])
        for index in range(mesh.get_num_sections(0)):
            stats = section(U, mesh, 0, index, subsystem)['stats']
            require(not any(stats[k] for k in ('invalid_indices', 'attribute_count_mismatch',
                    'indices_not_triangular', 'used_nonfinite', 'used_missing_attributes',
                    'used_zero_normal', 'used_zero_tangentX', 'used_zero_unsigned_cross')),
                    'Actual used native frame invalid')
        collision = inspect_collision(U, mesh, hulls, vista_geometry, tolerances['position_cm'])
        metadata = inspect_sources(U, mesh, [dict(index=0, file=record['file'], sha256=record['sha256'])],
                                   Path(root) / SOURCE)
        require(subsystem.get_collision_complexity(mesh) == U.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX and
                mesh.get_editor_property('nanite_settings').get_editor_property('enabled') is False,
                'Saved roof policy differs')
        return dict(passed=True, triangles=len(actual), UCX=len(hulls), geometry_UV_normals_source_match=True,
                    geometry=geometry, authored_convex=collision, source_metadata=metadata,
                    stored_TangentY_handedness='NOT_PROVEN', cooked_world_gameplay_collision='NOT_CHECKED')
    return verify


def make_pixel_verifier(U, diagnostic_root, guard):
    """Concrete Texture.Source PNG/RGB callback; Root owns an empty diagnostic directory."""
    from native_texture_tools_v11 import verify_shared_pixels
    from png_source_v11 import png_rgb
    directory = Path(diagnostic_root)
    require(directory.is_absolute() and directory.resolve() == directory and directory.is_dir() and
            not any(directory.iterdir()) and callable(guard), 'Explicit empty Root-owned diagnostic directory required')

    def verify(texture, source_path, recipe):
        filename = recipe['package'].rsplit('/', 1)[-1] + '_TextureSource.png'
        return verify_shared_pixels(U, texture, source_path, recipe, directory / filename,
                                    directory, png_rgb, guard)
    return verify
