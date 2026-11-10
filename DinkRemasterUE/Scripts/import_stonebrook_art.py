"""Run inside UnrealEditor's Python commandlet via import_stonebrook_art.sh.

Imports the authored Blender kit with the legacy FBX factory (explicitly selected),
validates metre/centimetre scale, assigns PBR texture channels, and atomically
publishes the runtime dressing manifest only after all imports succeed.
"""
import json
import os
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
SOURCE = Path(os.environ.get('DINK_ART_SOURCE', str(ROOT / 'SourceAssets/Art/Stonebrook')))
SPEC = json.loads((SOURCE / os.environ.get('DINK_ART_MANIFEST', 'art_manifest.json')).read_text())
LAYOUT = json.loads((SOURCE / os.environ.get('DINK_ART_LAYOUT', 'room_layout.json')).read_text())
if os.environ.get('DINK_ART_USED_ASSETS_ONLY') == '1':
    required_names = {row['mesh'] for row in LAYOUT.get('replacements', []) + LAYOUT.get('elements', [])}
    SPEC['assets'] = {name:data for name,data in SPEC['assets'].items() if name in required_names}
    material_names = {name for asset in SPEC['assets'].values() for name in asset['materials']}
    SPEC['materials'] = {name:data for name,data in SPEC['materials'].items() if name in material_names}
LAYOUT_SCREEN = int(LAYOUT.get('screen', 1))
OUTPUT_NAME = os.environ.get('DINK_ART_OUTPUT_NAME', {1:'stonebrook',439:'stonebrook_exterior'}.get(LAYOUT_SCREEN, f'screen_{LAYOUT_SCREEN}'))
if not OUTPUT_NAME.replace('_','').isalnum():
    raise RuntimeError('Invalid art output name')
HOUSE_LIGHTING = None
if (LAYOUT_SCREEN == 1 and OUTPUT_NAME == 'stonebrook' and
        SOURCE.resolve() == (ROOT / 'SourceAssets/Art/Stonebrook').resolve()):
    # Validate the lighting-only authority before any native import or scene work.
    import importlib.util
    _lighting_spec = importlib.util.spec_from_file_location('dink_house_lighting', ROOT / 'Scripts/house_lighting.py')
    _lighting = importlib.util.module_from_spec(_lighting_spec)
    _lighting_spec.loader.exec_module(_lighting)
    HOUSE_LIGHTING = _lighting.load_profile(ROOT)
    _lighting.preflight_source(HOUSE_LIGHTING, LAYOUT)
ASSETS = '/Game/Dink/Kits/' + SOURCE.name
MATS = os.environ.get('DINK_ART_MATERIAL_FOLDER', '/Game/Dink/Materials/Stonebrook')
TEX = os.environ.get('DINK_ART_TEXTURE_FOLDER', '/Game/Dink/Textures/Stonebrook')
if not MATS.startswith('/Game/Dink/Materials/') or not TEX.startswith('/Game/Dink/Textures/'):
    raise RuntimeError('Art materials/textures must stay inside their Dink folders')
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
# In 5.8, Interchange intercepts FBX even with an explicit FbxFactory and
# ignores FbxImportUI on reimport. Use the documented legacy FBX path so unit
# conversion and custom collision behave identically on first/repeated imports.
unreal.SystemLibrary.execute_console_command(
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
    'Interchange.FeatureFlags.Import.FBX 0')
if unreal.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX') != 0:
    raise RuntimeError('Cannot select deterministic legacy FBX importer')


def save(asset):
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def import_file(filename, dest, name, options=None, factory=None):
    task = unreal.AssetImportTask()
    task.filename = str((SOURCE / filename).resolve())
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    if factory is not None:
        task.factory = factory
    TOOLS.import_asset_tasks([task])
    asset = LIB.load_asset(dest + '/' + name)
    if asset is None:
        raise RuntimeError('Import failed: ' + filename + ' paths=' + str(task.imported_object_paths))
    return asset


def expression(material, cls, x=0, y=0, **properties):
    node = EDIT.create_material_expression(material, cls, x, y)
    for key, value in properties.items():
        node.set_editor_property(key, value)
    return node


def scalar(material, value, prop, y):
    node = expression(material, unreal.MaterialExpressionConstant, -200, y, r=float(value))
    EDIT.connect_material_property(node, '', prop)


# Per-asset destinations let new refinements coexist with their reviewed predecessors.
for name, data in SPEC['assets'].items():
    destination = data.get('content_folder', ASSETS)
    if not destination.startswith('/Game/Dink/') or any(not part.replace('_','').isalnum() for part in destination.split('/')[3:]):
        raise RuntimeError('Invalid Dink art destination: '+destination)

# Validate mask contracts before touching any existing material or texture package.
for name, data in SPEC['materials'].items():
    masked = bool(data.get('masked', data.get('alpha_mask', False)))
    clip = float(data.get('alpha_clip', .333333))
    if masked and (not 0. < clip < 1. or 'BC' not in data.get('textures', {})):
        raise RuntimeError('Masked foliage requires a BC alpha texture and a clip strictly between zero and one: '+name)

materials = {}
for name, data in SPEC['materials'].items():
    mat = LIB.load_asset(MATS + '/' + name) if LIB.does_asset_exist(MATS + '/' + name) else None
    if mat is None:
        mat = TOOLS.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    EDIT.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided', data.get('two_sided', False))
    masked = bool(data.get('masked', data.get('alpha_mask', False)))
    clip = float(data.get('alpha_clip', .333333))
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE)
    if masked:
        mat.set_editor_property('opacity_mask_clip_value', clip)
    channels = {}
    speed = data.get('uv_pan_speed', [0.,0.])
    panner = expression(mat, unreal.MaterialExpressionPanner, -1000, 100, speed_x=float(speed[0]), speed_y=float(speed[1])) if any(speed) else None
    for suffix, filename in data.get('textures', {}).items():
        texture = import_file(filename, TEX, Path(filename).stem)
        texture.set_editor_property('srgb', suffix == 'BC')
        if suffix == 'BC' and masked:
            # Fine needle silhouettes must survive both compression and distant mips.
            texture.set_editor_property('compression_no_alpha', False)
            coverage = bool(data.get('preserve_alpha_coverage', False))
            texture.set_editor_property('do_scale_mips_for_alpha_coverage', coverage)
            if coverage:
                texture.set_editor_property('alpha_coverage_thresholds', unreal.Vector4(0., 0., 0., clip))
        if suffix == 'N':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('flip_green_channel', data.get('normal_flip_green', True))
        elif suffix == 'ORM':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        save(texture)
        node = expression(mat, unreal.MaterialExpressionTextureSample, -600, len(channels) * 240, texture=texture)
        node.set_editor_property('sampler_type', {
            'BC': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
            'ORM': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
            'N': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        }[suffix])
        if panner is not None:
            EDIT.connect_material_expressions(panner, '', node, 'Coordinates')
        channels[suffix] = node
    if 'BC' in channels:
        EDIT.connect_material_property(channels['BC'], 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
        if masked:
            EDIT.connect_material_property(channels['BC'], 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    else:
        rgb = data.get('base_color', [0.3, 0.2, 0.12])
        node = expression(mat, unreal.MaterialExpressionConstant3Vector, -600, 0,
                          constant=unreal.LinearColor(*rgb, 1.0))
        EDIT.connect_material_property(node, '', unreal.MaterialProperty.MP_BASE_COLOR)
    if 'ORM' in channels:
        for output, prop in [('R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                             ('G', unreal.MaterialProperty.MP_ROUGHNESS),
                             ('B', unreal.MaterialProperty.MP_METALLIC)]:
            EDIT.connect_material_property(channels['ORM'], output, prop)
    else:
        scalar(mat, data.get('roughness', 0.75), unreal.MaterialProperty.MP_ROUGHNESS, 200)
        scalar(mat, data.get('metallic', 0.0), unreal.MaterialProperty.MP_METALLIC, 350)
    if 'N' in channels:
        # Match the Blender preview's restrained bump strength rather than
        # exaggerating the grain into deep carved grooves at game scale.
        strength = expression(mat, unreal.MaterialExpressionConstant3Vector, -350, 650,
                              constant=unreal.LinearColor(float(data.get('normal_strength', .35)), float(data.get('normal_strength', .35)), 1.0, 1.0))
        multiply = expression(mat, unreal.MaterialExpressionMultiply, -150, 650)
        normal = expression(mat, unreal.MaterialExpressionNormalize, 50, 650)
        EDIT.connect_material_expressions(channels['N'], 'RGB', multiply, 'A')
        EDIT.connect_material_expressions(strength, '', multiply, 'B')
        EDIT.connect_material_expressions(multiply, '', normal, 'VectorInput')
        EDIT.connect_material_property(normal, '', unreal.MaterialProperty.MP_NORMAL)
    scalar(mat, data.get('specular', 0.35), unreal.MaterialProperty.MP_SPECULAR, 500)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
    EDIT.recompile_material(mat)
    save(mat)
    materials[name] = mat


meshes = {}
checks = []
mesh_subsystem = (unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
                  or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
for name, data in SPEC['assets'].items():
    destination = data.get('content_folder', ASSETS)
    options = unreal.FbxImportUI()
    options.set_editor_property('automated_import_should_detect_type', False)
    options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property('import_mesh', True)
    options.set_editor_property('import_materials', False)
    options.set_editor_property('import_textures', False)
    options.set_editor_property('import_animations', False)
    opts = options.static_mesh_import_data
    opts.set_editor_property('combine_meshes', True)
    opts.set_editor_property('import_mesh_lods', False)
    opts.set_editor_property('remove_degenerates', True)
    if data['class'] == 'foliage':
        # Source LODs have validated per-corner normals. Preserve them: averaging
        # coincident, two-sided leaf/branch vertices can cancel normals in UE.
        opts.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    opts.set_editor_property('auto_generate_collision', False)
    opts.set_editor_property('generate_lightmap_u_vs', False)
    opts.set_editor_property('convert_scene', True)
    opts.set_editor_property('convert_scene_unit', True)
    opts.set_editor_property('import_uniform_scale', 1.0)
    # Atomic reimport consults the existing mesh's import data instead of the
    # task's new FbxImportUI. Set those conversion settings explicitly too.
    if LIB.does_asset_exist(destination + '/' + name):
        existing = LIB.load_asset(destination + '/' + name)
        stored = existing.get_editor_property('asset_import_data')
        if isinstance(stored, unreal.FbxStaticMeshImportData):
            for key in ('convert_scene', 'convert_scene_unit', 'import_uniform_scale',
                        'combine_meshes', 'auto_generate_collision', 'generate_lightmap_u_vs',
                        'import_mesh_lods', 'remove_degenerates', 'normal_import_method'):
                stored.set_editor_property(key, opts.get_editor_property(key))
            stored.scripted_add_filename(str((SOURCE / data['fbx']).resolve()), 0, '')
        else:
            opts.scripted_add_filename(str((SOURCE / data['fbx']).resolve()), 0, '')
            existing.set_editor_property('asset_import_data', opts)
    lod_files = data.get('lod_fbx', [])
    expected_lods = int(data.get('expected_lods', len(lod_files) or 1))
    if expected_lods != (len(lod_files) or 1):
        raise RuntimeError(f'{name}: explicit LOD files disagree with expected_lods={expected_lods}')
    base_file = lod_files[0] if lod_files else data['fbx']
    if data['class'] == 'foliage' and len(lod_files) != 3:
        raise RuntimeError('Foliage requires three explicit single-LOD FBX files: ' + name)
    # Reimport's stored source must follow the same LOD0 file, not the previous combined FBX.
    if LIB.does_asset_exist(destination + '/' + name):
        LIB.load_asset(destination + '/' + name).get_editor_property('asset_import_data').scripted_add_filename(str((SOURCE / base_file).resolve()), 0, '')
    mesh = import_file(base_file, destination, name, options, unreal.FbxFactory())
    for index, filename in enumerate(lod_files[1:], 1):
        if mesh_subsystem.import_lod(mesh, index, str((SOURCE / filename).resolve())) != index:
            raise RuntimeError(f'Failed to attach authored LOD{index} to {name}')
    if lod_files:
        for index in range(len(lod_files)):
            settings = mesh_subsystem.get_lod_build_settings(mesh, index)
            settings.set_editor_property('recompute_normals', False)
            settings.set_editor_property('recompute_tangents', True)
            settings.set_editor_property('remove_degenerates', True)
            mesh_subsystem.set_lod_build_settings(mesh, index, settings)
    actual_lods = mesh_subsystem.get_lod_count(mesh)
    if actual_lods != expected_lods:
        raise RuntimeError(f'{name}: imported {actual_lods} LODs, expected {expected_lods}')
    slots = list(mesh.get_editor_property('static_materials'))
    for i, slot in enumerate(slots):
        slot_name = str(slot.get_editor_property('material_slot_name'))
        imported_name = str(slot.get_editor_property('imported_material_slot_name'))
        candidate = slot_name if slot_name in materials else imported_name
        # Blender can append a numerical suffix when a library material is duplicated.
        candidate = candidate.split('.')[0]
        if candidate not in materials:
            raise RuntimeError(f'Unmapped material {slot_name}/{imported_name} on {name}')
        slot.set_editor_property('material_interface', materials[candidate])
    # Commit material slots together; per-slot setters rebuild large Nanite meshes repeatedly.
    mesh.set_editor_property('static_materials', slots)
    # Concave doorway/open furniture: retain actual geometry, never a hull spanning the opening.
    body = mesh.get_editor_property('body_setup')
    collision_mode = data.get('collision_mode', 'complex')
    if collision_mode == 'simple':
        # UE's simple count excludes UCX convex hulls; both are valid simple query bodies.
        if mesh_subsystem.get_simple_collision_count(mesh) + mesh_subsystem.get_convex_collision_count(mesh) <= 0:
            raise RuntimeError(f'{name}: simple collision requested but source hull missing')
        body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
    elif collision_mode == 'complex':
        body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    else:
        raise RuntimeError(f'{name}: unknown collision_mode {collision_mode}')
    mesh_subsystem.set_generate_lightmap_uv(mesh, False) if hasattr(mesh_subsystem, 'set_generate_lightmap_uv') else None
    bounds = mesh.get_bounds().box_extent
    actual = [bounds.x * 2, bounds.y * 2, bounds.z * 2]
    expected = [v * 100 for v in data['dimensions_m']]
    tolerance = 1.0
    if any(abs(a - b) > tolerance for a, b in zip(actual, expected)):
        raise RuntimeError(f'{name} scale/axis mismatch: expected{expected}cm imported{actual}cm')
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.set_editor_property('enabled', data['class'] not in ('foliage', 'prop_small', 'weapon'))
    nanite.set_editor_property('fallback_percent_triangles', 1.0)
    nanite.set_editor_property('fallback_relative_error', 0.0)
    mesh.set_editor_property('nanite_settings', nanite)
    save(mesh)
    meshes[name] = mesh.get_path_name()
    checks.append({'mesh': mesh.get_path_name(), 'expected_size_cm': expected,
                   'expected_lods': expected_lods, 'bounds_tolerance_cm': tolerance, 'collision_mode':collision_mode})
    unreal.log(f'DINK ART IMPORT: {name} size_cm={actual} materials={len(slots)}')

# Exterior layouts can reuse the interior's original barrel and sack assets.
# Validate those dependencies explicitly rather than duplicating their FBX files.
for name in {r['mesh'] for r in LAYOUT.get('replacements', []) + LAYOUT.get('elements', [])} - set(meshes):
    path = LAYOUT.get('asset_paths', {}).get(name, '/Game/Dink/Kits/Stonebrook/' + name)
    if not path.startswith('/Game/Dink/Kits/'):
        raise RuntimeError('Shared art must use the existing Dink kit folders: '+path)
    if not LIB.does_asset_exist(path):
        raise RuntimeError('Missing shared art ' + path + '; import the interior kit first')
    meshes[name] = LIB.load_asset(path).get_path_name()

# Dressing is described in map pixels to stay coupled to the canonical layout transform.
screens = json.loads((ROOT / 'ImportData/screens.json').read_text())['screens']
by_screen = {r['screen']: r for r in screens}
placements = json.loads((ROOT / 'ImportData/placements.json').read_text())['placements']
by_origin = {r['id']: r for r in placements}


def world_pixel(pixel, screen=None, height_m=0):
    corners = by_screen[LAYOUT_SCREEN if screen is None else screen]['corners']
    x, y = pixel[0] / 600, pixel[1] / 400
    nw, ne, se, sw = [corners[k] for k in ('nw', 'ne', 'se', 'sw')]
    out = [(nw[i]*(1-x)*(1-y) + ne[i]*x*(1-y) + se[i]*x*y + sw[i]*(1-x)*y) * 100 for i in range(2)]
    return out + [height_m * 100]


runtime = {'schema': 'dink-art/1', 'screen': LAYOUT_SCREEN, 'assets': checks,
           'source': str(SOURCE.relative_to(ROOT) / os.environ.get('DINK_ART_MANIFEST', 'art_manifest.json')),
           'replacements': [], 'elements': [], 'hide_origins': [],
           'hide_screen_visuals': LAYOUT.get('hide_screen_visuals', [LAYOUT_SCREEN]),
           'authored_collision_screens': LAYOUT.get('authored_collision_screens', [1] if LAYOUT_SCREEN == 1 else []),
           'preserve_low_collision_screens': LAYOUT.get('preserve_low_collision_screens', []), 'lights': []}
for row in LAYOUT['replacements']:
    origin = row['origin']
    source = by_origin[origin]
    if source['representation'] != 'instance':
        out = {'origin': origin, 'mesh': meshes[row['mesh']],
               'offset_cm': [a-b for a,b in zip(world_pixel(row['source_pixel'], height_m=row.get('height_cm', 0) / 100), [v*100 for v in source['world']]+[0])],
               'rotation_deg': row.get('rotation_deg', [0, row.get('yaw', 0), 0]),
               'scale': row.get('scale', [1, 1, 1])}
        runtime['replacements'].append(out)
    else:
        runtime['elements'].append({'name': origin, 'mesh': meshes[row['mesh']],
                                    'world_cm': world_pixel(row.get('source_pixel', [source['map_x'], source['map_y']])),
                                    'rotation_deg': [0, row.get('yaw', 0), 0],
                                    'scale': row.get('scale', [1, 1, 1])})
for row in LAYOUT.get('elements', []):
    location = world_pixel(row['source_pixel'], row.get('screen', LAYOUT_SCREEN), row.get('height_cm', 0) / 100)
    rotation = row.get('rotation_deg', [0, row.get('yaw', 0), 0])
    scale = row.get('scale', [1, 1, 1])
    if LAYOUT_SCREEN == 1 and SPEC['assets'][row['mesh']]['class'] in ('kit_floor', 'kit_ceiling'):
        # The documented FBX handedness conversion negates local Y. These grid
        # modules start at NW in the source layout; move their imported -Y span
        # south by one 2m grid cell (including scaling and actor yaw).
        import math
        offset = 200.0 * scale[1]
        location[0] -= math.sin(math.radians(rotation[1])) * offset
        location[1] += math.cos(math.radians(rotation[1])) * offset
    camera_occluder = row.get('camera_occluder', SPEC['assets'].get(row['mesh'], {}).get('class') in ('kit_wall', 'kit_ceiling', 'kit_piece'))
    runtime['elements'].append({'name': row['name'], 'mesh': meshes[row['mesh']],
                                'world_cm': location, 'rotation_deg': rotation, 'scale': scale, 'collision': row.get('collision', True), 'camera_occluder': camera_occluder})
for row in LAYOUT.get('lights', []):
    runtime['lights'].append({'world_cm': world_pixel(row['source_pixel'], row.get('screen', LAYOUT_SCREEN), row['height_cm'] / 100),
                              'lumens': row['lumens'], 'kelvin': row['kelvin'], 'radius_cm': row['radius_cm']})
if HOUSE_LIGHTING is not None:
    runtime = _lighting.apply_lighting(HOUSE_LIGHTING, runtime, generated_from_legacy_layout=True)
replaced_origins = {r['origin'] for r in runtime['replacements']}
runtime['hide_origins'] = [origin for origin in LAYOUT.get('hide_origins', []) if origin not in replaced_origins]
runtime['warp_overrides'] = [{'origin': 'S001_P25', 'world_cm': world_pixel([305, 398], height_m=1.5), 'extent_cm': [65, 30, 150]}] if LAYOUT_SCREEN == 1 else []
if LAYOUT_SCREEN == 439:
    runtime['warp_overrides'] = [{'origin': 'S439_P13', 'world_cm': world_pixel([339, 293], height_m=1.5),
                                  'extent_cm': [65, 35, 150]}]
if LAYOUT_SCREEN == 1:
    runtime['postprocess'] = [{'world_cm': world_pixel([300, 250], height_m=1.75),
                               'extent_cm': [770, 680, 250], 'exposure_bias': -2.0}]
dest = ROOT / ('Content/Dink/Data/Art/' + OUTPUT_NAME + '.json')
dest.parent.mkdir(parents=True, exist_ok=True)
tmp = dest.with_suffix('.tmp')
tmp.write_text(json.dumps(runtime, indent=2) + '\n')
os.replace(tmp, dest)
report = ROOT / ('Saved/Art/' + OUTPUT_NAME + '_import_report.json')
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps({'mesh_count': len(checks), 'material_count': len(materials),
                              'bounds_checks': checks, 'runtime_manifest': str(dest)}, indent=2) + '\n')
unreal.log(f'DINK ART IMPORT OK: {len(checks)} meshes, {len(materials)} PBR materials, bounds verified; {dest}')
