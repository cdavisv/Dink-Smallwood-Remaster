"""Pure metadata checks and a read-only inspector probe. No import/save entry point."""
import json
import math
from pathlib import Path

SOURCE = Path('SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1')
MESH = '/Game/Dink/Refinements/House439ClosedEavesV1/Meshes/SM_Cottage_Stonebrook_01'
ROLES = frozenset((
    'MI_Shared_FieldstoneSeed2m', 'MI_Shared_LimeMortarSoot2m',
    'MI_Shared_WeatheredTimber2m', 'MI_Shared_IronLead2m',
    'MI_Shared_ThinWavyGlass2m', 'MI_Shared_FieldstoneWall2m',
    'MI_Shared_LaidWeatheredPhotoCoatFrayedCut2m_SourceTrial',
))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_export(report):
    require(report.get('pass') is True, 'Export readback did not pass')
    require(report['triangles_before_after'] == [182626, 182626], 'Triangle count differs')
    require(report['max_position_error_m'] == report['linear_RGBA_import_error'] == 0,
            'Source position/linear color differs')
    require(report['UV_errors'] == {'UV0': 0.0, 'UV1_SharedData': 0.0}, 'UV contract differs')
    require(report['zeroT_counts'] == [0, 0] and report['bitangent_sign_changes'] == 0,
            'Signed tangent frame differs')
    for key in ('normal_difference_degrees', 'Mikk_difference_degrees'):
        values = report[key]
        require(len(values) == 3 and all(math.isfinite(x) for x in values) and
                0 <= values[-1] < .05, 'Normal/Mikk export tolerance exceeded')
    slots = report['actual_material_slots']
    require(len(slots) == 7 and len(set(slots)) == 7 and set(slots) == ROLES and
            report['material_roles_exact'] is True, 'Imported material names differ')
    colors = report['rawColor0']
    require(len(colors) == 1 and colors[0]['layer0'] == 'SharedSurfaceData' and
            colors[0]['corners'] == 547878 and colors[0]['RGBA_error'] == 0,
            'Serialized Color0 contract differs')
    hulls = report['collision_hulls']
    expected = {'UCX_SM_Cottage_Stonebrook_01_' + str(i).zfill(2) for i in range(1, 7)}
    require(len(hulls) == 6 and {x['name'] for x in hulls} == expected and
            all(x['positions_shape_exact'] is True and x['max_position_error_m'] == 0 and
                x['max_TRS_error'] == 0 for x in hulls), 'Six source hulls/frames differ')


def validate_candidate_row(row, frame):
    require(row['mesh'] == MESH + '.SM_Cottage_Stonebrook_01', 'Fresh candidate identity differs')
    require(row['expected_lods'] == 1 and row['bounds_tolerance_cm'] == 1.0,
            'LOD or existing bounds tolerance differs')
    bounds = frame['assembled_render_bounds_m']
    expected = [100 * (bounds[1][i] - bounds[0][i]) for i in range(3)]
    require(len(row['expected_size_cm']) == 3 and all(
        math.isfinite(x) and abs(x - y) < 1.e-6
        for x, y in zip(row['expected_size_cm'], expected)),
        'Candidate expectation must use fresh source bounds; no old asset row reuse')


def inspect_compiled_geometry_capability(U, project_root, guard):
    """Caller first proves its own modules/lease; this probe never loads an asset."""
    require(callable(guard), 'Own-build/module/isolation guard required')
    guard()
    loaded_root = Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()
    require(loaded_root == Path(project_root).resolve(), 'Loaded editor project differs')
    method = getattr(getattr(U, 'DinkMaterialArtLibrary', None),
                     'inspect_static_mesh_geometry', None)
    require(callable(method), 'Geometry inspector not compiled/loaded')
    reply = json.loads(method(None))
    require(reply.get('schema') == 'dink-static-mesh-geometry/1' and
            reply.get('valid') is False and reply.get('error') == 'null_mesh',
            'Geometry inspector null capability contract differs')
    return reply
