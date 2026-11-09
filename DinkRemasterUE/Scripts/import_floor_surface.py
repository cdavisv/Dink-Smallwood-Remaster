"""Import the approved oak surface into new packages; never reimport kit geometry.

Run with Unreal's Python commandlet. DINK_FLOOR_SOURCE selects the reviewed
source bundle. DINK_FLOOR_MODE is preflight (default), import (five new
packages), or verify (read-only saved-package checks). Runtime placement
publication is a separate review step.
"""
import hashlib
import json
import os
from pathlib import Path
import struct

import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
SOURCE = Path(os.environ.get('DINK_FLOOR_SOURCE', str(ROOT / 'SourceAssets/Art/Stonebrook/Refinements/FloorOakV1'))).resolve()
REPORT = Path(os.environ.get('DINK_FLOOR_REPORT', str(ROOT / 'Saved/Art/floor_surface_import.json')))
ORIGINAL = '/Game/Dink/Kits/Stonebrook/SM_Floor_Oak_2m_01'
DEST = '/Game/Dink/Kits/Stonebrook/Refinements/FloorOakV1/SM_Floor_Oak_2m_01'
MAT = '/Game/Dink/Materials/Stonebrook/Refinements/MI_Stonebrook_FloorOakV1'
TEXTURES = '/Game/Dink/Textures/Stonebrook/Refinements'
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sid(value):
    return int(value.get_editor_property('id_value'))


def snapshot(mesh):
    """Compare actual source-description topology/UVs and physical build settings."""
    desc = mesh.get_static_mesh_description(0)
    vertices = []
    for i in range(desc.get_vertex_count()):
        v = desc.get_vertex_position(unreal.VertexID(i))
        vertices.append([float(v.x), float(v.y), float(v.z)])
    instances = []
    for i in range(desc.get_vertex_instance_count()):
        instance = unreal.VertexInstanceID(i)
        uv = desc.get_vertex_instance_uv(instance, 0)
        instances.append([sid(desc.get_vertex_instance_vertex(instance)), float(uv.x), float(uv.y)])
    triangles = []
    for i in range(desc.get_triangle_count()):
        triangle = unreal.TriangleID(i)
        triangles.append([sid(desc.get_triangle_polygon_group(triangle)),
                          [sid(v) for v in desc.get_triangle_vertex_instances(triangle)]])
    body = mesh.get_editor_property('body_setup')
    subsystem = unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
    return {'vertices': vertices, 'instances': instances, 'triangles': triangles,
            'collision': body.get_editor_property('agg_geom').export_text(),
            'collision_trace_flag': str(body.get_editor_property('collision_trace_flag')),
            'nanite': mesh.get_editor_property('nanite_settings').export_text(),
            'lods': subsystem.get_lod_count(mesh),
            'slot_names': [str(s.get_editor_property('material_slot_name'))
                           for s in mesh.get_editor_property('static_materials')],
            'imported_slot_names': [str(s.get_editor_property('imported_material_slot_name'))
                                    for s in mesh.get_editor_property('static_materials')],
            'nails_slot_metadata': mesh.get_editor_property('static_materials')[1].export_text(),
            'nails': mesh.get_material(1).get_path_name()}


def save(asset):
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())


def verify_material_recipe(material):
    """Read the loaded graph, including saved node links rather than just flags."""
    assert material.get_editor_property('use_material_attributes') is False
    assert material.get_editor_property('tangent_space_normal') is True
    assert material.get_editor_property('shading_model') == unreal.MaterialShadingModel.MSM_DEFAULT_LIT
    expected = [('BC', 'RGB', unreal.MaterialProperty.MP_BASE_COLOR),
                ('N', 'RGB', unreal.MaterialProperty.MP_NORMAL),
                ('ORM', 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                ('ORM', 'G', unreal.MaterialProperty.MP_ROUGHNESS),
                ('ORM', 'B', unreal.MaterialProperty.MP_METALLIC)]
    sampler = {'BC': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
               'N': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               'ORM': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}
    inputs = []
    nodes = set()
    for channel, output, prop in expected:
        node = EDIT.get_material_property_input_node(material, prop)
        assert type(node) is unreal.MaterialExpressionTextureSample, 'Non-direct texture input: ' + str(prop)
        texture = node.get_editor_property('texture')
        assert texture.get_path_name() == TEXTURES + '/T_Stonebrook_FloorOakV1_' + channel + '.T_Stonebrook_FloorOakV1_' + channel
        assert node.get_editor_property('sampler_type') == sampler[channel]
        assert EDIT.get_material_property_input_node_output_name(material, prop) == output
        assert node.get_editor_property('const_coordinate') == 0
        assert not any(EDIT.get_inputs_for_material_expression(material, node)), 'Unexpected UV/texture/mip input'
        nodes.add(node.get_path_name())
        inputs.append({'property': str(prop), 'texture': texture.get_path_name(), 'output': output, 'UV_channel': 0})
    constant = EDIT.get_material_property_input_node(material, unreal.MaterialProperty.MP_SPECULAR)
    assert type(constant) is unreal.MaterialExpressionConstant
    assert abs(constant.get_editor_property('r') - .35) < 1.e-6
    assert EDIT.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_SPECULAR) == ''
    nodes.add(constant.get_path_name())
    assert {node.get_path_name() for node in EDIT.get_material_expressions(material)} == nodes, 'Unexpected material nodes'
    approved = {prop.value for _, _, prop in expected} | {unreal.MaterialProperty.MP_SPECULAR.value}
    # The native reader safely covers every input, including hidden enum values
    # unavailable to Python and deprecated IDs for which the library getter is unsafe.
    connected = set(unreal.DinkMaterialArtLibrary.get_connected_material_properties(material))
    assert connected == approved, 'Unexpected material property inputs: ' + str(sorted(connected - approved))
    return {'inputs': inputs, 'specular': float(constant.get_editor_property('r')), 'direct_baked_inputs': True,
            'all_material_property_inputs_checked_natively': True, 'connected_property_ids': sorted(connected)}


spec = json.loads((SOURCE / 'material_manifest.json').read_text())
assert spec['schema'] == 'dink-floor-material-refinement/1'
assert set(spec['textures']) == {'BC', 'N', 'ORM'}
assert spec['resolution'] == 2048
assert spec['native_base_color_gain'] == 1
assert spec['roundtrip_visual_gate'] == 'approved', 'Baked Blender comparison still needs review'
for row in list(spec['source_files'].values()) + [spec['source_image']]:
    path = (SOURCE / row['file']).resolve()
    assert path.is_relative_to(SOURCE), 'Source bundle dependency escapes its directory: ' + str(path)
    assert sha(path) == row['sha256'], 'Stale source dependency: ' + str(path)
texture_paths = {}
for channel, row in spec['textures'].items():
    path = (SOURCE / row['file']).resolve()
    assert path.is_relative_to(SOURCE), path
    assert sha(path) == row['sha256'], path
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', data[16:24]) == (2048, 2048)
    assert data[24:26] == bytes([8, 2]), 'Expected 8-bit RGB PNG: ' + str(path)
    assert path.stem == 'T_Stonebrook_FloorOakV1_' + channel
    texture_paths[channel] = path
assert spec['normal_flip_green'] is True
assert spec['normal_strength'] == 1
assert spec['specular'] == .35
packages = [DEST, MAT] + [TEXTURES + '/' + p.stem for p in texture_paths.values()]
existing = [p for p in packages if LIB.does_asset_exist(p)]
mode = os.environ.get('DINK_FLOOR_MODE', 'preflight')
assert mode in {'preflight', 'import', 'verify'}, mode
if mode == 'verify':
    assert len(existing) == len(packages), 'Refinement packages missing'
else:
    assert not existing, 'Refusing to overwrite existing refinement packages: ' + str(existing)
original = unreal.load_asset(ORIGINAL)
assert isinstance(original, unreal.StaticMesh)
baseline = snapshot(original)
assert (len(baseline['vertices']), len(baseline['instances']), len(baseline['triangles']), baseline['lods']) == (1408, 7872, 2624, 1)
assert len(baseline['slot_names']) == 2
assert baseline['nails'].endswith('/MI_Stonebrook_WroughtIron.MI_Stonebrook_WroughtIron')
protected = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'Content').rglob('*.uasset')}
data_pins = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'Content/Dink/Data').rglob('*') if p.is_file()}
report = {'mode': mode,
          'source_manifest_sha256': sha(SOURCE / 'material_manifest.json'), 'packages': packages,
          'original_mesh': ORIGINAL, 'protected_existing_packages': len(protected),
          'project': str(ROOT), 'importer_sha256': sha(Path(__file__).resolve()),
          'protected_runtime_data_files': len(data_pins),
          'runtime_data_sha256': data_pins,
          'native_geometry_uv_collision_sha256': hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()}
if mode == 'import':
    textures = {}
    for channel, path in texture_paths.items():
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = TEXTURES
        task.destination_name = path.stem
        task.automated = True
        task.replace_existing = False
        task.save = False
        TOOLS.import_asset_tasks([task])
        texture = unreal.load_asset(TEXTURES + '/' + path.stem)
        assert isinstance(texture, unreal.Texture2D), path
        texture.set_editor_property('srgb', channel == 'BC')
        if channel == 'N':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('flip_green_channel', True)
        elif channel == 'ORM':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        save(texture)
        textures[channel] = texture
    folder, name = MAT.rsplit('/', 1)
    material = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('two_sided', False)
    nodes = {}
    for index, channel in enumerate(('BC', 'N', 'ORM')):
        node = EDIT.create_material_expression(material, unreal.MaterialExpressionTextureSample, -500, index * 220)
        node.set_editor_property('texture', textures[channel])
        node.set_editor_property('sampler_type', {'BC': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
            'N': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 'ORM': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}[channel])
        nodes[channel] = node
    for channel, output, prop in [('BC', 'RGB', unreal.MaterialProperty.MP_BASE_COLOR),
            ('N', 'RGB', unreal.MaterialProperty.MP_NORMAL), ('ORM', 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
            ('ORM', 'G', unreal.MaterialProperty.MP_ROUGHNESS), ('ORM', 'B', unreal.MaterialProperty.MP_METALLIC)]:
        assert EDIT.connect_material_property(nodes[channel], output, prop)
    constant = EDIT.create_material_expression(material, unreal.MaterialExpressionConstant, -200, 700)
    constant.set_editor_property('r', .35)
    assert EDIT.connect_material_property(constant, '', unreal.MaterialProperty.MP_SPECULAR)
    EDIT.set_base_material_usage(material, unreal.MaterialUsage.MATUSAGE_NANITE, True)
    EDIT.recompile_material(material)
    report['material_recipe'] = verify_material_recipe(material)
    save(material)
    duplicate = LIB.duplicate_asset(ORIGINAL, DEST)
    assert isinstance(duplicate, unreal.StaticMesh)
    duplicate.set_material(0, material)
    assert snapshot(duplicate) == baseline, 'Geometry/UV/nails/collision/Nanite changed'
    assert duplicate.get_material(0) == material
    save(duplicate)
    report['native_geometry_uv_nails_collision_nanite_unchanged'] = True
if mode == 'verify':
    duplicate = unreal.load_asset(DEST)
    material = unreal.load_asset(MAT)
    assert isinstance(duplicate, unreal.StaticMesh)
    assert isinstance(material, unreal.Material)
    assert snapshot(duplicate) == baseline, 'Saved geometry/UV/nails/collision/Nanite changed'
    assert duplicate.get_material(0) == material
    assert material.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_OPAQUE
    assert material.get_editor_property('two_sided') is False
    assert material.get_editor_property('used_with_nanite') is True
    report['material_recipe'] = verify_material_recipe(material)
    for channel, path in texture_paths.items():
        texture = unreal.load_asset(TEXTURES + '/' + path.stem)
        assert isinstance(texture, unreal.Texture2D)
        assert texture.get_editor_property('srgb') == (channel == 'BC')
        if channel == 'N':
            assert texture.get_editor_property('compression_settings') == unreal.TextureCompressionSettings.TC_NORMALMAP
            assert texture.get_editor_property('flip_green_channel') is True
        elif channel == 'ORM':
            assert texture.get_editor_property('compression_settings') == unreal.TextureCompressionSettings.TC_MASKS
    report['native_geometry_uv_nails_collision_nanite_unchanged'] = True
changed = [p for p, digest in protected.items() if sha(ROOT / p) != digest]
assert not changed, changed
data_changes = [p for p, digest in data_pins.items() if sha(ROOT / p) != digest]
assert not data_changes, data_changes
report['protected_changes'] = changed
report['runtime_data_changes'] = data_changes
if mode in {'import', 'verify'}:
    report['saved_package_sha256'] = {}
    for package in packages:
        relative = Path('Content') / (package.removeprefix('/Game/') + '.uasset')
        report['saved_package_sha256'][str(relative)] = sha(ROOT / relative)
report['runtime_manifest_published'] = False
report['passed'] = True
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2) + '\n')
print('FLOOR SURFACE ' + report['mode'].upper() + ' PASS: no runtime manifest publication')
