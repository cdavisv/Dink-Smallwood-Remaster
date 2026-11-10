"""Root-reviewed native entry points only: fresh trial, readback, production bindings.
No Unreal import, launch, build, import, save or Data mutation at module load.
"""
from pathlib import Path
import json
import hashlib
from shared_roof_contract import load_contract, assert_trial_absent, package_file, require, sha, SOURCE, SHARED, CAMERA, verify_package_hashes
from native_texture_tools_v11 import import_shared_texture, configure_shared_texture
from native_material_builder_v12 import build_graph
from native_material_readback_v12 import inspect_graph
from native_mesh_tools_v11c import import_shared_roof_base, append_lods, configure_policy
from native_material_slots_v11 import inspect_slots
from relative_source_metadata import configure_relative_sources, inspect_relative_sources
from native_buffer_capture_v11d import section
from native_collision_readback_v11 import capture_collision


def preflight_native(U, root, contract, guard):
    require(callable(guard), 'Root isolation/input guard required')
    guard()
    require(str(Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()) == str(root),
            'Loaded Unreal project differs from selected isolated root')
    require(load_contract(root)['digest'] == contract['digest'], 'Source/Data/native preimages changed')
    require('-game' not in U.SystemLibrary.get_command_line().split(), 'Editor-only native preparation')
    require(U.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX') == 0,
            'Legacy FBX importer must be selected before any trial mutation')
    capability = getattr(getattr(U, 'DinkRoofSourceMetadataLibrary', None),
                         'supports_shared_roof_source_filenames', None)
    require(callable(capability) and capability() is True,
            'Shared filename scope not compiled/loaded; Root must review and build editor extension first')


def bind_named_materials(U, mesh, role_packages, expected_triangles, guard):
    slots = mesh.get_editor_property('static_materials')
    names = [str(row.get_editor_property('imported_material_slot_name')) for row in slots]
    require(len(names) == len(set(names)) and set(names) == set(role_packages), 'Imported FBX slot roles differ')
    # Slot order may change: the imported NAME is the only role selector.
    loaded = {role: U.load_asset(package) for role, package in role_packages.items()}
    require(all(isinstance(mat, U.Material) for mat in loaded.values()), 'Shared opaque role unavailable')
    for index, name in enumerate(names):
        guard()
        mesh.set_material(index, loaded[name])
    return inspect_slots(U, mesh, 0, names, role_packages,
                         expected_triangles)


def production_geometry_snapshot(U, mesh):
    """Detach actual built buffers, source filenames, authored convex and policy.
    FProc flip is retained for exact before/after equality, not claimed stored handedness.
    """
    subsystem = U.get_default_object(U.StaticMeshEditorSubsystem)
    lods = []
    for lod in range(mesh.get_num_lods()):
        settings = subsystem.get_lod_build_settings(mesh, lod)
        flags = {k: settings.get_editor_property(k) for k in
                 ('use_full_precision_u_vs', 'recompute_normals', 'recompute_tangents', 'use_mikk_t_space',
                  'remove_degenerates', 'generate_lightmap_u_vs')}
        buffers = []
        for index in range(mesh.get_num_sections(lod)):
            raw = section(U, mesh, lod, index, subsystem)
            raw.pop('material_path')  # Intended material reference is the sole allowed change.
            require(not any(raw['stats'][k] for k in
                    ('invalid_indices', 'attribute_count_mismatch', 'indices_not_triangular',
                     'used_nonfinite', 'used_missing_attributes', 'used_zero_normal',
                     'used_zero_tangentX', 'used_zero_unsigned_cross')), 'Invalid actual geometry frame')
            buffers.append(raw)
        lods.append(dict(build_flags=flags, sections=buffers))
    collision = capture_collision(U, mesh)
    filenames = json.loads(U.DinkRoofSourceMetadataLibrary.inspect_roof_source_filenames(mesh))
    require(filenames.get('valid') is True, 'Original source metadata unreadable')
    return dict(LODs=lods, convex=collision, source_filenames=filenames,
                collision_policy=str(subsystem.get_collision_complexity(mesh)),
                nanite=bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled')),
                allow_cpu_access=bool(mesh.get_editor_property('allow_cpu_access')))


def checked_mesh_result(result, record):
    require(isinstance(result, dict) and result.get('passed') is True and
            result.get('triangles') == record['triangles'] and result.get('UCX') == record['UCX'] and
            result.get('geometry_UV_normals_source_match') is True,
            'Reviewed actual mesh/source/UCX verifier did not establish complete correspondence')
    return result


def import_trial(U, root, contract, guard, save, pixel_check, mesh_check, emit_receipt):
    """Exact23 fresh packages. Root supplies reviewed actual pixel/geometry verifiers.
    save(asset, overwrite=False) must save ONLY the exact trial set in this contract.
    A failure preserves its partial receipt and refuses automatic retry/overwrite.
    """
    root = Path(root)
    require(all(callable(f) for f in (save, pixel_check, mesh_check, emit_receipt)),
            'Reviewed save/pixel/actual mesh/receipt callbacks required')
    preflight_native(U, root, contract, guard)
    assert_trial_absent(root, contract)
    require(all(not U.EditorAssetLibrary.does_asset_exist(p) for p in contract['trial_packages']),
            'Existing loaded trial package; no overwrite')
    report = dict(passed=False, phase='fresh23_import', contract_digest=contract['digest'], packages={},
                  textures=[], materials=[], meshes=[], production_activated=False)

    def persist(asset, files=None):
        package = asset.get_path_name().split('.')[0]
        file = package_file(root, package)
        require(package in contract['trial_packages'] and not file.exists(), 'Save outside exact fresh23 scope')
        if files:
            configure_relative_sources(U, asset, files, root / 'SourceAssets/Art', guard)
        guard()
        require(save(asset, overwrite=False) is True, 'Explicit fresh package save failed')
        require(file.is_file() and not file.is_symlink() and file.stat().st_nlink == 1, 'Saved package missing/aliased')
        report['packages'][str(file.relative_to(root))] = sha(file)

    try:
        textures = {}
        for recipe in contract['textures']:
            source = root / recipe['source_file']
            texture = import_shared_texture(U, source, recipe, guard)
            report['textures'].append(pixel_check(texture, source, recipe))
            persist(texture, [source])
            textures[recipe['package']] = texture
        tools = U.AssetToolsHelpers.get_asset_tools()
        for recipe in contract['materials']:
            typed = {kind: textures[path] for kind, path in recipe['textures'].items()}
            for masked in (False, True):
                target = recipe['masked' if masked else 'opaque']
                folder, name = target.rsplit('/', 1)
                guard()
                require(not U.EditorAssetLibrary.does_asset_exist(target), 'Late material target appeared')
                material = tools.create_asset(name, folder, U.Material, U.MaterialFactoryNew())
                require(isinstance(material, U.Material), 'Material creation failed')
                build_graph(U, material, recipe, typed, masked, guard)
                report['materials'].append(inspect_graph(U, material, recipe, masked))
                persist(material)
        role_packages = {r['source_material']: r['opaque'] for r in contract['materials']}
        subsystem = U.get_default_object(U.StaticMeshEditorSubsystem)
        for record in contract['meshes']:
            mesh = import_shared_roof_base(U, root / SOURCE, record, record['package'], guard)
            append_lods(U, mesh, root / SOURCE, [dict(index=0)], subsystem, guard)
            configure_policy(U, mesh, dict(collision='SIMPLE_AND_COMPLEX', nanite=False), guard)
            roles = {name: role_packages[name] for name in record['material_slots']}
            bind_named_materials(U, mesh, roles, record['triangles'], guard)
            # The verifier inspects raw-relative source filenames before any save.
            configure_relative_sources(U, mesh, [root / SOURCE / record['file']],
                                       root / 'SourceAssets/Art', guard)
            result = checked_mesh_result(mesh_check(mesh, record), record)
            report['meshes'].append(result)
            persist(mesh)
        require(len(report['packages']) == 23, 'Incomplete fresh23 save set')
        guard()
        require(load_contract(root)['digest'] == contract['digest'], 'Source/Data/production preimages changed')
        report['passed'] = True
        return report
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        emit_receipt(report)


def verify_trial_readback(U, root, contract, imported, guard, pixel_check, mesh_check, emit_receipt):
    """Separate fresh-process saved readback. No imports, setters or saves."""
    root = Path(root)
    preflight_native(U, root, contract, guard)
    expected = {str(package_file(root, p).relative_to(root)) for p in contract['trial_packages']}
    require(imported.get('passed') is True and imported.get('phase') == 'fresh23_import' and
            imported.get('contract_digest') == contract['digest'] and set(imported['packages']) == expected,
            'Complete exact23 import receipt required')
    report = dict(passed=False, phase='fresh23_saved_readback', contract_digest=contract['digest'],
                  packages=dict(imported['packages']), textures=[], materials=[], meshes=[], imports=0, saves=0)
    try:
        verify_package_hashes(root, report['packages'])
        for recipe in contract['textures']:
            guard()
            texture = U.load_asset(recipe['package'])
            configure_shared_texture(U, texture, recipe, guard)
            inspect_relative_sources(U, texture, [root / recipe['source_file']], root / 'SourceAssets/Art')
            report['textures'].append(pixel_check(texture, root / recipe['source_file'], recipe))
        for recipe in contract['materials']:
            for masked in (False, True):
                guard()
                report['materials'].append(inspect_graph(U, U.load_asset(recipe['masked' if masked else 'opaque']),
                                                        recipe, masked))
        roles = {r['source_material']: r['opaque'] for r in contract['materials']}
        for record in contract['meshes']:
            guard()
            mesh = U.load_asset(record['package'])
            inspect_relative_sources(U, mesh, [root / SOURCE / record['file']], root / 'SourceAssets/Art')
            inspect_slots(U, mesh, 0, record['material_slots'], roles, record['triangles'])
            report['meshes'].append(checked_mesh_result(mesh_check(mesh, record), record))
        guard()
        require(all(sha(root / p) == h for p, h in report['packages'].items()), 'Readback changed saved packages')
        report['passed'] = True
        return report
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        emit_receipt(report)


def assert_data_unchanged(root, expected, allow_camera=False):
    root = Path(root)
    actual = {str(p.relative_to(root)) for p in (root / 'Content/Dink/Data').rglob('*') if p.is_file()}
    require(actual == set(expected), 'Gameplay Data file set changed')
    require(all((allow_camera and name == str(CAMERA)) or sha(root / name) == digest
                for name, digest in expected.items()), 'Unrelated gameplay Data bytes changed')


def camera_map_with_aliases(original, aliases):
    from shared_roof_contract import ROLES
    expected = {}
    for role in ROLES:
        name = 'MI_Shared_' + role
        expected[SHARED + name + '.' + name] = SHARED + name + '_CameraMasked.' + name + '_CameraMasked'
    require(aliases == expected, 'Exact three registered shared camera aliases required')
    camera = json.loads(original)
    require(camera.get('schema') == 'dink-camera/1' and isinstance(camera.get('material_variants'), dict),
            'Existing camera map schema differs')
    require(not (set(camera['material_variants']) & set(aliases)), 'Alias overwrite/resume refused')
    camera['material_variants'].update(aliases)
    encoded = (json.dumps(camera, indent=2) + '\n').encode()
    after = json.loads(encoded)
    for key, value in aliases.items():
        require(after['material_variants'].pop(key) == value, 'Shared camera alias differs')
    require(after == json.loads(original), 'Unrelated camera values changed')
    return encoded


def apply_production_bindings(U, root, contract, saved_readback, guard, save, emit_receipt):
    """After Root-reviewed trial/readback: exact8 existing mesh material edits +3 aliases.
    Shared15 packages must already be present at their final paths in this isolated root.
    No mesh reimport/build/collision setter or scene transform/Data-row replacement is called.
    Root save callback must whitelist these exact8 existing mesh package overwrites.
    """
    root = Path(root)
    require(all(callable(f) for f in (guard, save, emit_receipt)), 'Root activation callbacks required')
    preflight_native(U, root, contract, guard)
    require(saved_readback.get('passed') is True and saved_readback.get('phase') == 'fresh23_saved_readback' and
            saved_readback.get('contract_digest') == contract['digest'] and
            len(saved_readback.get('meshes', [])) == 8 and len(saved_readback.get('textures', [])) == 9 and
            len(saved_readback.get('materials', [])) == 6, 'Saved fresh23 readback required before production edits')
    expected = {str(package_file(root, p).relative_to(root)) for p in contract['trial_packages']}
    require(set(saved_readback['packages']) == expected, 'Readback package identity differs')
    verify_package_hashes(root, saved_readback['packages'])
    camera_file = root / CAMERA
    original_camera = camera_file.read_bytes()
    updated_camera = camera_map_with_aliases(original_camera, contract['camera_aliases'])
    report = dict(passed=False, phase='production8_bindings_and3_aliases', contract_digest=contract['digest'],
                  packages={}, meshes=[], camera_aliases_added={}, geometry_or_collision_setters=0,
                  runtime_GPU_validation_required=True, published=False)
    try:
        prepared = []
        # Validate every actual role/geometry/policy before the first production mutation.
        for name, record in contract['production'].items():
            guard()
            mesh = U.load_asset(record['existing_package'])
            require(isinstance(mesh, U.StaticMesh), 'Missing production roof')
            snapshot = production_geometry_snapshot(U, mesh)
            require(snapshot['convex']['authored_convex_elements'] == record['UCX_expected'] and
                    not snapshot['nanite'] and
                    U.get_default_object(U.StaticMeshEditorSubsystem).get_collision_complexity(mesh) ==
                    U.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX, 'Original production roof policy differs')
            slots = [str(s.get_editor_property('imported_material_slot_name'))
                     for s in mesh.get_editor_property('static_materials')]
            require(set(slots) == set(record['material_bindings_by_imported_slot_name']) and
                    len(slots) == len(set(slots)), 'Production imported FBX role identity differs')
            prepared.append((mesh, record, snapshot))
        for mesh, record, before in prepared:
            roles = {old: SHARED + shared for old, shared in record['material_bindings_by_imported_slot_name'].items()}
            bind_named_materials(U, mesh, roles, next(r['triangles'] for r in contract['meshes'] if r['name'] == record['mesh']), guard)
            require(production_geometry_snapshot(U, mesh) == before, 'Material edit changed actual geometry/UCX/policy')
            guard()
            require(save(mesh, overwrite=True) is True, 'Explicit production mesh save failed')
            require(production_geometry_snapshot(U, mesh) == before, 'Saved production geometry/UCX/policy changed')
            file = package_file(root, record['existing_package'])
            require(file.is_file() and not file.is_symlink() and file.stat().st_nlink == 1, 'Production file aliased')
            report['packages'][str(file.relative_to(root))] = sha(file)
            report['meshes'].append(dict(package=record['existing_package'], geometry_UV_normals_UCX_policy_exact=True,
                                         source_filename_preserved=True, named_material_bindings=roles,
                                         geometry_snapshot_sha256=hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()))
        assert_data_unchanged(root, contract['data_preimages'])
        guard()
        require(camera_file.read_bytes() == original_camera, 'Camera map preimage changed')
        camera_file.write_bytes(updated_camera)
        require(camera_file.read_bytes() == updated_camera, 'Saved camera aliases differ')
        assert_data_unchanged(root, contract['data_preimages'], allow_camera=True)
        require(all(sha(root / p) == h for p, h in saved_readback['packages'].items()), 'Shared/trial packages changed during activation')
        report.update(passed=True, camera_aliases_added=contract['camera_aliases'], camera_file_sha256=sha(camera_file))
        guard()
        return report
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        emit_receipt(report)


def verify_production_readback(U, root, contract, activation, trial_readback, guard, pixel_check, emit_receipt):
    """Fresh-process final23 package verification after eight material-only saves.
    Trial-only mesh packages are intentionally not production delivery requirements.
    No import, setter, save or camera Data write occurs here.
    """
    root = Path(root)
    require(all(callable(f) for f in (guard, pixel_check, emit_receipt)), 'Reviewed readback callbacks required')
    guard()
    require(str(Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()) == str(root),
            'Wrong selected production readback project')
    require(activation.get('passed') is True and activation.get('phase') == 'production8_bindings_and3_aliases' and
            activation.get('contract_digest') == trial_readback.get('contract_digest') == contract['digest'] and
            trial_readback.get('passed') is True and trial_readback.get('phase') == 'fresh23_saved_readback',
            'Actual activation and saved trial readback receipts required')
    for relative, digest in contract['source_pins'].items():
        require(sha(root / relative) == digest, 'Frozen source changed after activation')
    expected8 = {str(package_file(root, r['existing_package']).relative_to(root))
                 for r in contract['production'].values()}
    require(set(activation['packages']) == expected8 and len(activation.get('meshes', [])) == 8,
            'Exact eight production save receipts required')
    shared15 = {str(package_file(root, p).relative_to(root)) for p, kind in contract['trial_packages'].items()
                if kind != 'StaticMesh'}
    hashes = dict(activation['packages'])
    require(shared15 <= set(trial_readback['packages']), 'Shared15 package receipt incomplete')
    hashes.update({p: trial_readback['packages'][p] for p in shared15})
    require(len(hashes) == 23, 'Final production23 package set differs')
    verify_package_hashes(root, hashes)
    assert_data_unchanged(root, contract['data_preimages'], allow_camera=True)
    require(sha(root / CAMERA) == activation['camera_file_sha256'], 'Activated camera alias bytes changed')
    camera = json.loads((root / CAMERA).read_text())
    for key, value in contract['camera_aliases'].items():
        require(camera['material_variants'].pop(key, None) == value, 'Final camera alias differs')
    require(hashlib.sha256(json.dumps(camera, sort_keys=True).encode()).hexdigest() ==
            contract['camera_semantics_sha256'], 'Unrelated camera semantics changed')
    report = dict(passed=False, phase='fresh_production23_readback', contract_digest=contract['digest'],
                  packages=hashes, textures=[], materials=[], meshes=[], imports=0, saves=0,
                  GPU_gameplay_validation_required=True, stored_TangentY_handedness='NOT_PROVEN', published=False)
    try:
        for recipe in contract['textures']:
            guard()
            texture = U.load_asset(recipe['package'])
            configure_shared_texture(U, texture, recipe, guard)
            inspect_relative_sources(U, texture, [root / recipe['source_file']], root / 'SourceAssets/Art')
            report['textures'].append(pixel_check(texture, root / recipe['source_file'], recipe))
        for recipe in contract['materials']:
            for masked in (False, True):
                guard()
                report['materials'].append(inspect_graph(U, U.load_asset(recipe['masked' if masked else 'opaque']),
                                                        recipe, masked))
        before = {r['package']: r for r in activation['meshes']}
        expected_triangles = {r['name']: r['triangles'] for r in contract['meshes']}
        for name, record in contract['production'].items():
            guard()
            mesh = U.load_asset(record['existing_package'])
            roles = {old: SHARED + shared for old, shared in record['material_bindings_by_imported_slot_name'].items()}
            inspect_slots(U, mesh, 0, list(roles), roles, expected_triangles[name])
            snapshot = production_geometry_snapshot(U, mesh)
            digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
            require(digest == before[record['existing_package']]['geometry_snapshot_sha256'],
                    'Fresh production geometry/UV/normals/UCX/source-filenames/policy differs from original')
            report['meshes'].append(dict(package=record['existing_package'], geometry_snapshot_sha256=digest,
                                         geometry_UV_normals_UCX_policy_exact=True))
        guard()
        require(all(sha(root / p) == digest for p, digest in hashes.items()), 'Readback changed production files')
        report['passed'] = True
        return report
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        emit_receipt(report)


if __name__ == '__main__':
    raise RuntimeError('Preparation only. Root must review caller/isolation/save/actual verifiers before native execution.')
