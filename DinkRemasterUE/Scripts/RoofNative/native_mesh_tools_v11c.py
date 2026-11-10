"""Review-only mesh import helpers. No native execution at module load or saves.
Private setup must select legacy FBX importer before invoking these helpers.
"""
from pathlib import Path
import hashlib
from native_built_buffer_reader_v11 import FLAGS, require


def source_file(packet, record):
    path = (Path(packet) / record['file']).resolve()
    require(path.is_relative_to(Path(packet).resolve()), 'Source outside packet')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256'], 'FBX hash mismatch')
    return path


def apply_lod_builds(mesh, subsystem, expected_lods, guard):
    require(mesh.get_num_lods() == expected_lods, 'Unexpected imported LOD count')
    for lod in range(expected_lods):
        options = subsystem.get_lod_build_settings(mesh, lod)
        for key, value in FLAGS.items():
            options.set_editor_property(key, value)
        guard()
        subsystem.set_lod_build_settings(mesh, lod, options)
        actual = subsystem.get_lod_build_settings(mesh, lod)
        require(all(actual.get_editor_property(k) == v for k, v in FLAGS.items()), 'LOD build settings failed')
    guard()
    mesh.set_editor_property('allow_cpu_access', True)


def _import_base_profile(U, packet, record, package, guard, prefix):
    path = source_file(packet, record)
    require(package.startswith(prefix) and '.' not in package, 'Unexpected mesh package')
    require(U.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX') == 0, 'Legacy FBX importer required')
    guard()
    require(not U.EditorAssetLibrary.does_asset_exist(package), 'Refusing mesh overwrite')
    ui = U.FbxImportUI()
    for key, value in {'automated_import_should_detect_type': False, 'mesh_type_to_import': U.FBXImportType.FBXIT_STATIC_MESH,
                       'import_mesh': True, 'import_materials': False, 'import_textures': False, 'import_animations': False}.items():
        ui.set_editor_property(key, value)
    for key, value in {'combine_meshes': False, 'import_mesh_lo_ds': False, 'remove_degenerates': False,
                       'normal_import_method': U.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                       'normal_generation_method': U.FBXNormalGenerationMethod.MIKK_T_SPACE,
                       'auto_generate_collision': False, 'one_convex_hull_per_ucx': True,
                       'generate_lightmap_u_vs': False, 'convert_scene': True, 'convert_scene_unit': True,
                       'force_front_x_axis': False, 'import_uniform_scale': 1.0,
                       'import_translation': U.Vector(0, 0, 0), 'import_rotation': U.Rotator(0, 0, 0),
                       'transform_vertex_to_absolute': True, 'bake_pivot_in_vertex': False}.items():
        ui.static_mesh_import_data.set_editor_property(key, value)
    folder, name = package.rsplit('/', 1)
    task = U.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = str(path), folder, name
    task.automated, task.replace_existing, task.save = True, False, False
    task.options, task.factory = ui, U.FbxFactory()
    guard()
    U.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    require(list(task.imported_object_paths) == [package+'.'+name], 'Unexpected imported mesh objects')
    mesh = U.load_asset(package)
    require(isinstance(mesh, U.StaticMesh), 'Expected StaticMesh')
    return mesh


def import_base(U, packet, record, package, guard):
    return _import_base_profile(U, packet, record, package, guard,
                                '/Game/Dink/Refinements/RoofChimneyV12d/Meshes/')


def import_shared_roof_base(U, packet, record, package, guard):
    from shared_roof_contract import NAMES, TRIAL
    require(package in {TRIAL + name for name in NAMES}, 'Outside exact eight shared roof trial targets')
    require(record['file'] == 'FBX/' + package.rsplit('/', 1)[-1] + '.fbx', 'Shared FBX name differs')
    return _import_base_profile(U, packet, record, package, guard, TRIAL)


def append_lods(U, mesh, packet, records, subsystem, guard):
    """Records include base index0; caller binds materials and collision separately."""
    require([r['index'] for r in records] == list(range(len(records))), 'LOD order must be explicit contiguous')
    for record in records[1:]:
        path = source_file(packet, record)
        guard()
        require(subsystem.import_lod(mesh, record['index'], str(path)) == record['index'], 'Explicit LOD import failed')
        apply_lod_builds(mesh, subsystem, record['index']+1, guard)
    apply_lod_builds(mesh, subsystem, len(records), guard)


def configure_policy(U, mesh, collision_policy, guard, approved_fireplace_nanite=None):
    """Explicit policy values only. New imports cannot inherit unknown FP settings."""
    policy = collision_policy['collision']
    flags = {'SIMPLE_AND_COMPLEX': U.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX,
             'COMPLEX_AS_SIMPLE': U.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
             'SIMPLE_AS_COMPLEX': U.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX}
    require(policy in flags, 'Unsupported collision policy')
    nanite = mesh.get_editor_property('nanite_settings')
    if collision_policy['nanite'] is False:
        nanite.set_editor_property('enabled', False)
    else:
        require(collision_policy['nanite'] == 'PRESERVE_ENABLED_FULL_FALLBACK', 'Unknown Nanite policy')
        require(approved_fireplace_nanite and approved_fireplace_nanite.get('enabled') is True, 'Exact approved FP native baseline required')
        require({'fallback_target', 'fallback_percent_triangles', 'fallback_relative_error'} <= approved_fireplace_nanite.keys(), 'Incomplete FP fallback baseline')
        for key, value in approved_fireplace_nanite.items():
            nanite.set_editor_property(key, value)
    guard()
    mesh.set_editor_property('nanite_settings', nanite)
    guard()
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag', flags[policy])
    # Navigation/overlap are component/scene gates, never silently set here.
