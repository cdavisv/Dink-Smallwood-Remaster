"""Bounded shared-roof source/native plan. Pure file reads; never imports Unreal."""
from pathlib import Path
import hashlib
import json

ROLES = ('OakLonggrain2m', 'OakEndgrain2m', 'LimePlaster2m')
NAMES = ('SM_IndoorRoof_EN_01', 'SM_IndoorRoof_ES_01', 'SM_IndoorRoof_Gable_EN_01',
         'SM_IndoorRoof_Gable_ES_01', 'SM_IndoorRoof_Gable_WN_01', 'SM_IndoorRoof_Gable_WS_01',
         'SM_IndoorRoof_WN_01', 'SM_IndoorRoof_WS_01')
SOURCE = Path('SourceAssets/Art/Stonebrook/Refinements/InteriorRoofSharedV1')
LIBRARY = Path('SourceAssets/Art/SharedMaterials')
TRIAL = '/Game/Dink/Refinements/InteriorRoofSharedV1/Meshes/'
SHARED = '/Game/Dink/Materials/Shared/'
PRODUCTION = '/Game/Dink/Refinements/RoofChimneyV12d/Meshes/'
CAMERA = Path('Content/Dink/Data/Art/camera_materials.json')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_file(root, package):
    require(package.startswith('/Game/Dink/') and '.' not in package and '..' not in package,
            'Invalid package path')
    return Path(root) / ('Content/' + package.removeprefix('/Game/') + '.uasset')


def load_contract(root):
    """Validate frozen source bytes, exact role/path/count contracts and production preimages."""
    root = Path(root)
    require(root.is_absolute() and root.resolve() == root, 'Explicit resolved project root required')
    pins = {}
    for folder in (SOURCE, LIBRARY):
        sums = root / folder / 'SHA256SUMS.json'
        require(sums.is_file() and not sums.is_symlink(), 'Source checksum manifest missing/aliased')
        pins[str(sums.relative_to(root))] = sha(sums)
        for relative, expected in json.loads(sums.read_text()).items():
            file = root / folder / relative
            require(file.resolve().is_relative_to(root / folder) and file.is_file() and not file.is_symlink(),
                    'Source escaped or missing: ' + relative)
            require(sha(file) == expected, 'Frozen source bytes differ: ' + relative)
            pins[str(file.relative_to(root))] = expected
    registry = json.loads((root / LIBRARY / 'manifest.json').read_text())['materials']
    source = json.loads((root / SOURCE / 'manifest.json').read_text())
    exported = json.loads((root / SOURCE / 'export_manifest.json').read_text())
    plan = json.loads((root / SOURCE / 'production_material_update.json').read_text())
    require(set(source['assets']) == set(NAMES), 'Exact eight source roofs required')
    exports = {r['name']: r for r in exported['FBX']}
    require(set(exports) == set(NAMES) and len(exported['FBX']) == 8, 'Exact eight FBXs required')
    require(sum(r['triangles'] for r in exports.values()) == 17322 and
            sum(r['UCX'] for r in exports.values()) == 204, 'Roof geometry/UCX count differs')
    require(exported['source_sha256'] == source['source_sha256'] == sha(root / SOURCE / source['source']),
            'Saved registered source differs')
    textures, materials, packages = [], [], {}
    for role in ROLES:
        row = registry[role]
        base = 'MI_Shared_' + role
        derived = registry[role + '_CameraMasked']
        require(row['material'] == base and row['repeat_m'] == 2 and row['nominal_texels_per_m'] == 512,
                'Shared physical material contract differs')
        require(derived['derived_from'] == base and derived['same_texture_set_as'] == role and
                derived['material'] == base + '_CameraMasked' and
                derived['DinkCameraOpacity_default'] == derived['shadow_pass_opacity'] == 1 and
                derived['blend_mode'] == 'BLEND_MASKED' and derived['dither_opacity_mask'] is True and
                derived['opacity_mask_clip_value'] == .5, 'Separate camera variant contract differs')
        require(set(row['textures']) == {'BC', 'N', 'ORM'}, 'Exact BC/N/ORM roles required')
        typed = {}
        for kind in ('BC', 'N', 'ORM'):
            image = row['textures'][kind]
            suffix = 'N_GL' if kind == 'N' else kind
            filename = 'T_Shared_' + role + '_' + suffix + '.png'
            file = root / LIBRARY / image['file']
            require(file.name == filename and file.resolve().parent ==
                    root / LIBRARY / 'OakLime2mV1/Textures' and image['size'] == [1024, 1024] and
                    image['srgb'] is (kind == 'BC') and image['native_flip_green'] is (kind == 'N') and
                    sha(file) == image['sha256'], 'Shared texture filename/settings/bytes differ')
            require(kind != 'N' or image['normal_orientation'] == 'OpenGL +Y', 'Normal orientation differs')
            package = SHARED + 'Textures/' + file.stem
            texture = dict(package=package, source_file=str(file.relative_to(root)),
                           source_sha256=image['sha256'], srgb=kind == 'BC', flip_green=kind == 'N',
                           compression='TC_NORMALMAP' if kind == 'N' else 'TC_DEFAULT' if kind == 'BC' else 'TC_MASKS',
                           address='Wrap', size=1024)
            textures.append(texture)
            typed[kind] = package
            packages[package] = 'Texture2D'
        f0 = ((row['IOR'] - 1) / (row['IOR'] + 1)) ** 2 * 2 * row['specular_IOR_level']
        require(row['specular_IOR_level'] == .25 and abs(row['dielectric_F0'] - f0) < 1e-12 and
                abs(row['unreal_specular'] - f0 / .08) < 1e-12, 'Source-derived F0 differs')
        recipe = dict(source_material=base, opaque=SHARED + base, masked=SHARED + base + '_CameraMasked',
                      textures=typed, dielectric_F0=f0, unreal_specular=f0 / .08, coat=0., emission_strength=0.,
                      UV0_scale=[1, 1], UV0_offset=[0, 0], camera_opacity_default=1, shadow_opacity=1,
                      shadow_replace_named_inputs={'Default': 'DinkCameraOpacity', 'Shadow': 'constant_one'},
                      required_usage=[])
        materials.append(recipe)
        packages[recipe['opaque']] = packages[recipe['masked']] = 'Material'
    production = {r['mesh']: r for r in plan['meshes']}
    require(set(production) == set(NAMES) and len(plan['meshes']) == 8, 'Exact eight production bindings required')
    meshes = []
    for name in NAMES:
        record, data = exports[name], source['assets'][name]
        require(record['file'] == 'FBX/' + name + '.fbx' and
                sha(root / SOURCE / record['file']) == record['sha256'], 'FBX source bytes differ')
        require(data['authored_architecture'] == {'screens': [1], 'purpose': 'exposed interior roof adaptation'},
                'Declared screen identity differs')
        slots = data['material_slots']
        expected = ['MI_Shared_LimePlaster2m'] if 'Gable' in name else [
            'MI_Shared_OakLonggrain2m', 'MI_Shared_OakEndgrain2m']
        require(slots == expected, 'Actual shared FBX role names differ')
        target = TRIAL + name
        require(production[name]['existing_package'] == PRODUCTION + name and
                production[name]['trial_package'] == target and production[name]['UCX_expected'] == record['UCX'],
                'Production target identity differs')
        aliases_by_name = {'MI_InteriorRoof_GablePlaster_Baked': 'MI_Shared_LimePlaster2m'} if 'Gable' in name else {
            'MI_InteriorRoof_OakLonggrain_Baked': 'MI_Shared_OakLonggrain2m',
            'MI_InteriorRoof_RoofBoards_Baked': 'MI_Shared_OakLonggrain2m',
            'MI_InteriorRoof_OakEndgrain_Baked': 'MI_Shared_OakEndgrain2m'}
        require(production[name]['material_bindings_by_imported_slot_name'] == aliases_by_name,
                'Production semantic material alias map differs')
        existing = package_file(root, PRODUCTION + name)
        require(existing.is_file() and not existing.is_symlink() and existing.stat().st_nlink == 1 and
                existing.resolve().is_relative_to(root) and sha(existing) == production[name]['expected_existing_package_sha256'],
                'Production roof preimage missing/changed')
        meshes.append(dict(name=name, package=target, file=record['file'], sha256=record['sha256'],
                           triangles=record['triangles'], UCX=record['UCX'], material_slots=slots))
        packages[target] = 'StaticMesh'
    aliases = {}
    for role in ROLES:
        name = 'MI_Shared_' + role
        aliases[SHARED + name + '.' + name] = SHARED + name + '_CameraMasked.' + name + '_CameraMasked'
    require(plan['camera_material_aliases_at_final_activation'] == aliases, 'Exact three camera aliases differ')
    require(len(packages) == 23 and list(packages.values()).count('Texture2D') == 9 and
            list(packages.values()).count('Material') == 6 and list(packages.values()).count('StaticMesh') == 8,
            'Exact 23-package trial required')
    data_hashes = {str(p.relative_to(root)): sha(p) for p in sorted((root / 'Content/Dink/Data').rglob('*'))
                   if p.is_file()}
    require(str(CAMERA) in data_hashes, 'Existing camera material map required')
    camera_file = root / CAMERA
    require(not camera_file.is_symlink() and camera_file.resolve().is_relative_to(root) and
            camera_file.stat().st_nlink == 1, 'Camera activation file aliased/outside private root')
    camera_semantics = hashlib.sha256(json.dumps(json.loads((root / CAMERA).read_text()), sort_keys=True).encode()).hexdigest()
    result = dict(camera_semantics_sha256=camera_semantics, root=str(root), source_pins=pins, textures=textures, materials=materials, meshes=meshes,
                  trial_packages=packages, production=production, camera_aliases=aliases, data_preimages=data_hashes,
                  trial_only_meshes=[TRIAL + name for name in NAMES],
                  production_delivery_packages=[p for p, k in packages.items() if k != 'StaticMesh'] +
                                               [PRODUCTION + name for name in NAMES])
    # Additive production registration. Frozen source manifests/current-hash ledger rows remain untouched.
    delivery = SOURCE.parent / 'InteriorRoofSharedV1NativeDelivery'
    if (root / delivery).exists():
        sums = root / delivery / 'SHA256SUMS.json'
        manifest = root / delivery / 'manifest.json'
        require(sums.is_file() and not sums.is_symlink() and manifest.is_file() and not manifest.is_symlink(),
                'Explicit delivery registration files required')
        require(json.loads(sums.read_text()) == {'manifest.json': sha(manifest)}, 'Delivery registration checksums differ')
        registration = json.loads(manifest.read_text())
        require(registration.get('schema') == 'dink-shared-roof-native-delivery/1' and
                set(registration.get('assets', {})) == set(NAMES) and
                all(registration['assets'][n]['content_path'] == TRIAL + n for n in NAMES),
                'Exact eight explicit delivery paths required')
        pins[str(sums.relative_to(root))] = sha(sums)
        pins[str(manifest.relative_to(root))] = sha(manifest)
    result['digest'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def assert_trial_absent(root, contract):
    root = Path(root).resolve()
    for package in contract['trial_packages']:
        file = package_file(root, package)
        require(file.resolve().is_relative_to(root) and not file.is_symlink() and not file.exists(),
                'Existing/aliased trial destination; no overwrite/automatic resume')


def verify_package_hashes(root, hashes):
    root = Path(root).resolve()
    for relative, digest in hashes.items():
        file = root / relative
        require(file.resolve().is_relative_to(root) and file.is_file() and not file.is_symlink() and
                file.stat().st_nlink == 1 and sha(file) == digest, 'Saved package missing/changed/aliased')


if __name__ == '__main__':
    raise RuntimeError('Root-reviewed caller only; this module never launches Unreal')
