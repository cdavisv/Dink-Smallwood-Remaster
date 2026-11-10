"""Review-only texture import/readback helpers; no native calls at module load.
Caller supplies authorization/isolation guard and approved diagnostic directory.
"""
from pathlib import Path
import hashlib


def require(value, message):
    if not value:
        raise RuntimeError(message)


def _configure_profile(U, texture, recipe, guard, configure, size):
    require(callable(guard), 'Isolation guard required')
    require(isinstance(texture, U.Texture2D), 'Expected Texture2D')
    require(texture.get_path_name().split('.')[0] == recipe['package'], 'Unexpected texture package')
    expected = {'srgb': recipe['srgb'], 'flip_green_channel': recipe['flip_green'],
                'compression_settings': getattr(U.TextureCompressionSettings, recipe['compression']),
                'address_x': U.TextureAddress.TA_WRAP, 'address_y': U.TextureAddress.TA_WRAP}
    require(recipe['address'] == 'Wrap', 'Unexpected addressing contract')
    for key, value in expected.items():
        if configure:
            guard()
            texture.set_editor_property(key, value)
        require(texture.get_editor_property(key) == value, 'Texture setting mismatch: '+key)
    require(texture.blueprint_get_size_x() == texture.blueprint_get_size_y() == size, 'Texture dimensions differ')
    return expected


def _import_profile(U, source_path, recipe, guard, prefix, configure_texture):
    source = Path(source_path)
    require(hashlib.sha256(source.read_bytes()).hexdigest() == recipe['source_sha256'], 'Source PNG hash mismatch')
    target = recipe['package']
    require(target.startswith(prefix), 'Target outside private scope')
    require('.' not in target, 'Invalid package name')
    guard()
    require(not U.EditorAssetLibrary.does_asset_exist(target), 'Refusing texture replacement')
    folder, name = target.rsplit('/', 1)
    task = U.AssetImportTask()
    task.filename = str(source.resolve())
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    guard()
    U.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    require(list(task.imported_object_paths) == [target+'.'+name], 'Unexpected imported objects')
    texture = U.load_asset(target)
    configure_texture(U, texture, recipe, guard, configure=True)
    return texture  # Caller verifies and saves only through its exact-package gate.


def _verify_pixels_profile(U, texture, source_path, recipe, diagnostic_file, diagnostic_root, read_pixels, guard, configure_texture):
    """Export Texture.Source PNG and compare decoded RGB exactly; never edits source."""
    configure_texture(U, texture, recipe, guard)
    source = Path(source_path)
    require(hashlib.sha256(source.read_bytes()).hexdigest() == recipe['source_sha256'], 'Source PNG changed')
    output = Path(diagnostic_file)
    root = Path(diagnostic_root).resolve()
    require(output.resolve().is_relative_to(root), 'Diagnostic outside approved root')
    require(output.suffix == '.png' and not output.exists() and not output.is_symlink(), 'Refusing diagnostic overwrite')
    require(output.parent.is_dir(), 'Caller must prepare approved diagnostic directory')
    guard()
    task = U.AssetExportTask()
    task.object = texture
    task.filename = str(output.resolve())
    task.exporter = U.TextureExporterPNG()
    task.automated = True
    task.prompt = False
    task.replace_identical = False
    require(U.Exporter.run_asset_export_task(task), 'Texture.Source PNG export failed')
    original, actual = read_pixels(source), read_pixels(output)
    require(original == actual, 'Texture.Source pixels differ from approved PNG')
    require(hashlib.sha256(source.read_bytes()).hexdigest() == recipe['source_sha256'], 'Source mutated during readback')
    return {'package': recipe['package'], 'source_sha256': recipe['source_sha256'],
            'decoded_RGB_sha256': hashlib.sha256(actual[2]).hexdigest(),
            'scope': 'Exact Texture.Source RGB only; compressed GPU mip appearance requires separate visual verification'}


def configure_and_verify(U, texture, recipe, guard, configure=False):
    return _configure_profile(U, texture, recipe, guard, configure, 2048)


def import_new(U, source_path, recipe, guard):
    return _import_profile(U, source_path, recipe, guard,
                           '/Game/Dink/Refinements/RoofChimneyV12d/Textures/', configure_and_verify)


def verify_source_pixels(U, texture, source_path, recipe, diagnostic_file, diagnostic_root, read_pixels, guard):
    return _verify_pixels_profile(U, texture, source_path, recipe, diagnostic_file, diagnostic_root,
                                  read_pixels, guard, configure_and_verify)


def _shared_texture_name(recipe):
    from shared_roof_contract import ROLES, SHARED
    allowed = {SHARED + 'Textures/T_Shared_' + role + '_' + suffix
               for role in ROLES for suffix in ('BC', 'N_GL', 'ORM')}
    require(recipe['package'] in allowed and recipe['size'] == 1024, 'Outside exact nine shared 1024 textures')


def configure_shared_texture(U, texture, recipe, guard, configure=False):
    _shared_texture_name(recipe)
    return _configure_profile(U, texture, recipe, guard, configure, 1024)


def import_shared_texture(U, source_path, recipe, guard):
    from shared_roof_contract import SHARED
    _shared_texture_name(recipe)
    require(Path(source_path).stem == recipe['package'].rsplit('/', 1)[-1], 'Shared texture source name differs')
    return _import_profile(U, source_path, recipe, guard, SHARED + 'Textures/', configure_shared_texture)


def verify_shared_pixels(U, texture, source_path, recipe, diagnostic_file, diagnostic_root, read_pixels, guard):
    return _verify_pixels_profile(U, texture, source_path, recipe, diagnostic_file, diagnostic_root,
                                  read_pixels, guard, configure_shared_texture)
