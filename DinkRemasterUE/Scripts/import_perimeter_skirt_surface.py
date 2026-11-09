"""Guarded new-package perimeter_skirt import. UE Python: DINK_PERIMETER_SKIRT_MODE=preflight|import|verify.

No overwrite of partial packages. Preserve failure reports and back up only the
one owned unpublished mesh candidate before recovery. Never overwrite published packages.
"""
import json
import os
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_perimeter_skirt_surface import (SOURCE_REL, DEST, MAT, PACKAGES, CONTEXT,
    sha, contained, data_pins, asset_pins, source_guard, binding_guard, owned_content, tool_pins, module_pins, report_guard, source_geometry, match_geometry)

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
SOURCE = (ROOT / SOURCE_REL).resolve()
MODE = os.environ.get('DINK_PERIMETER_SKIRT_MODE', 'preflight')
REPORT = Path(os.environ.get('DINK_PERIMETER_SKIRT_REPORT', str(ROOT / ('Saved/Art/perimeter_skirt_surface_' + MODE + '.json'))))
report_guard(ROOT, REPORT)
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SUB = (unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
       or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))


def save(asset):
    assert LIB.save_loaded_asset(asset, only_if_is_dirty=False), 'Failed save: ' + asset.get_path_name()


def shader_check(material):
    assert type(material) is unreal.Material
    assert material.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_OPAQUE
    assert material.get_editor_property('two_sided') is False
    assert material.get_editor_property('use_material_attributes') is False
    assert material.get_editor_property('tangent_space_normal') is True
    assert material.get_editor_property('shading_model') == unreal.MaterialShadingModel.MSM_DEFAULT_LIT
    assert material.get_editor_property('used_with_nanite') is True
    properties = [(unreal.MaterialProperty.MP_BASE_COLOR, (.009, .005, .0025)),
                  (unreal.MaterialProperty.MP_ROUGHNESS, .96),
                  (unreal.MaterialProperty.MP_METALLIC, 0.),
                  (unreal.MaterialProperty.MP_SPECULAR, .25)]
    nodes = set()
    for prop, expected in properties:
        node = EDIT.get_material_property_input_node(material, prop)
        if isinstance(expected, tuple):
            assert type(node) is unreal.MaterialExpressionConstant3Vector
            c = node.get_editor_property('constant')
            assert all(abs(a - b) < 1e-6 for a, b in zip((c.r, c.g, c.b), expected))
            assert abs(c.a - 1.) < 1e-6
        else:
            assert type(node) is unreal.MaterialExpressionConstant
            assert abs(node.get_editor_property('r') - expected) < 1e-6
        # Native graph reader enumerates every property, including Python-hidden IDs.
        assert not any(EDIT.get_inputs_for_material_expression(material, node))
        output = EDIT.get_material_property_input_node_output_name(material, prop)
        assert output == '', 'Unexpected constant output/channel: ' + str(output)
        nodes.add(node.get_path_name())
    assert {n.get_path_name() for n in EDIT.get_material_expressions(material)} == nodes
    assert len(nodes) == 4
    connected = set(unreal.DinkMaterialArtLibrary.get_connected_material_properties(material))
    assert connected == {5, 6, 7, 8}, 'Unexpected material inputs: ' + str(connected)
    return {'connected_property_ids': sorted(connected), 'constant_nodes': 4, 'opaque_default_lit': True}


def mesh_check(mesh, material, spec, plan):
    from collections import Counter
    import math
    assert isinstance(mesh, unreal.StaticMesh)
    assert SUB.get_lod_count(mesh) == 1 and mesh.get_editor_property('has_navigation_data') is False
    geom = mesh.get_editor_property('body_setup').get_editor_property('agg_geom')
    for name in ('sphere_elems','box_elems','sphyl_elems','convex_elems','tapered_capsule_elems',
                 'level_set_elems','skinned_level_set_elems','ml_level_set_elems','skinned_triangle_mesh_elems'):
        assert len(geom.get_editor_property(name)) == 0, 'Unexpected collision: ' + name
    assert SUB.get_convex_collision_count(mesh) == SUB.get_simple_collision_count(mesh) == 0
    assert mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag') == unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX
    assert len(mesh.get_editor_property('static_materials')) == 1 and mesh.get_material(0) == material
    stored = mesh.get_editor_property('asset_import_data')
    assert stored.get_editor_property('normal_import_method') == unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    settings = SUB.get_lod_build_settings(mesh,0)
    assert settings.get_editor_property('recompute_normals') is False
    assert settings.get_editor_property('recompute_tangents') is True
    assert settings.get_editor_property('use_mikk_t_space') is True
    desc = mesh.get_static_mesh_description(0)
    assert desc and desc.get_vertex_count() == 48 and desc.get_triangle_count() == 96
    expected, faces = source_geometry(SOURCE, spec)
    points = []
    for i in range(48):
        vertex = unreal.VertexID(id_value=i)
        assert desc.is_vertex_valid(vertex), 'Unexpected sparse vertex IDs'
        v = desc.get_vertex_position(vertex)
        points.append((float(v.x),float(v.y),float(v.z)))
    actual_faces = []
    for i in range(96):
        t = unreal.TriangleID(id_value=i)
        assert desc.is_triangle_valid(t), 'Unexpected sparse triangle IDs'
        assert desc.get_triangle_polygon_group(t).get_editor_property('id_value') == 0
        instances = list(desc.get_triangle_vertex_instances(t))
        assert len(instances) == 3 and all(desc.is_vertex_instance_valid(v) for v in instances)
        vertices = [desc.get_vertex_instance_vertex(v) for v in instances]
        assert all(desc.is_vertex_valid(v) for v in vertices)
        actual_faces.append(tuple(v.get_editor_property('id_value') for v in vertices))
    maximum = match_geometry(expected,faces,points,actual_faces)
    for i in range(desc.get_vertex_instance_count()):
        instance = unreal.VertexInstanceID(id_value=i)
        assert desc.is_vertex_instance_valid(instance), 'Unexpected sparse vertex-instance IDs'
        uv = desc.get_vertex_instance_uv(instance,0)
        assert math.isfinite(uv.x) and math.isfinite(uv.y)
    low = [min(p[k] for p in points) for k in range(3)]
    high = [max(p[k] for p in points) for k in range(3)]
    assert abs(low[2]) < .05 and abs(high[2]-17.8) < .05
    assert all(abs(high[k]-low[k]-spec['dimensions_m'][k]*100) < .05 for k in range(3))
    nanite = mesh.get_editor_property('nanite_settings')
    assert nanite.get_editor_property('enabled') is True
    assert nanite.get_editor_property('fallback_target') == unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
    assert abs(nanite.get_editor_property('fallback_percent_triangles')-1) < 1e-6
    assert nanite.get_editor_property('fallback_relative_error') == 0
    assert mesh.get_num_triangles(0) == mesh.get_num_nanite_triangles() == 96
    filename = mesh.get_editor_property('asset_import_data').get_first_filename()
    assert Path(filename).resolve() == contained(SOURCE,spec['files']['fbx']['file'])
    return {'vertices':48,'triangles':96,'nanite_triangles':96,'lods':1,
        'dimensions_cm':[high[k]-low[k] for k in range(3)],'source_oriented_triangles_match':True,
        'source_vertex_matching_bijective':True,'collision':False,'navigation':False,
        'max_source_vertex_delta_cm':maximum,
        'material_reused_without_save':material.get_path_name()}


report = {'passed': False, 'mode': MODE, 'project': str(ROOT)}
protected = data = None
try:
    assert MODE in {'preflight', 'import', 'verify'}
    owned_content(ROOT)
    assert LIB.does_asset_exist(MAT), 'Missing published material dependency'
    report['tool_sha256'] = tool_pins(ROOT)
    report['module_sha256'] = module_pins(ROOT)
    loaded = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if '.so' in line and ('libUnrealEditor-Dink' in line or 'libUnrealEditor-Ink' in line)})
    assert loaded and all(Path(p).resolve().is_relative_to(ROOT) for p in loaded), 'Foreign project modules loaded'
    report['loaded_project_modules'] = loaded
    spec, plan, context = source_guard(SOURCE)
    source_geometry(SOURCE, spec)
    signature = binding_guard(ROOT, plan)
    published = (ROOT / CONTEXT).exists()
    if published:
        assert MODE == 'verify', 'Candidate context already published'
        expected_context = (json.dumps(context, indent=2) + '\n').encode()
        assert (ROOT / CONTEXT).read_bytes() == expected_context, 'Published context differs from pinned source'
    report['runtime_context_already_published'] = published
    # Also demand the helper APIs before any package creation.
    assert callable(unreal.DinkMaterialArtLibrary.get_connected_material_properties)
    assert callable(EDIT.get_material_property_input_node_output_name)
    assert SUB is not None
    exists = [p for p in (DEST,) if LIB.does_asset_exist(p)]
    on_disk = [p for p in PACKAGES if (ROOT / p).exists()]
    if MODE == 'verify':
        assert len(exists) == len(on_disk) == 1, 'Missing saved candidate'
    else:
        assert not exists and not on_disk, 'Refusing overwrite/partial import: ' + str(exists + on_disk)
    protected = asset_pins(ROOT)
    data = data_pins(ROOT)
    report.update(source_handoff_sha256=sha(SOURCE / 'source_handoff.json'),
                  source_manifest_sha256=sha(SOURCE / 'asset_manifest.json'),
                  importer_sha256=sha(Path(__file__).resolve()),
                  publisher_sha256=sha(Path(__file__).with_name('publish_perimeter_skirt_surface.py')),
                  floor_transform_signature_sha256=signature, runtime_data_sha256=data)
    if MODE == 'import':
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
        assert unreal.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX') == 0
        options = unreal.FbxImportUI()
        for key, value in [('automated_import_should_detect_type', False), ('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH),
                           ('import_mesh', True), ('import_materials', False), ('import_textures', False), ('import_animations', False)]:
            options.set_editor_property(key, value)
        opts = options.static_mesh_import_data
        for key, value in [('combine_meshes', True), ('import_mesh_lods', False), ('auto_generate_collision', False),
                           ('generate_lightmap_u_vs', False), ('convert_scene', True), ('convert_scene_unit', True),
                           ('import_uniform_scale', 1.), ('one_convex_hull_per_ucx', True),
                           ('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)]:
            opts.set_editor_property(key, value)
        task = unreal.AssetImportTask()
        task.filename = str(contained(SOURCE, spec['files']['fbx']['file']))
        task.destination_path, task.destination_name = DEST.rsplit('/', 1)
        task.automated = True
        task.replace_existing = False
        task.save = False
        task.factory = unreal.FbxFactory()
        task.options = options
        TOOLS.import_asset_tasks([task])
        assert set(task.imported_object_paths) == {DEST + '.' + task.destination_name}
        mesh = unreal.load_asset(DEST)
        assert isinstance(mesh, unreal.StaticMesh)
        material = unreal.load_asset(MAT)
        shader_check(material)
        mesh.set_material(0, material)
        settings = SUB.get_lod_build_settings(mesh,0)
        for name,value in [('recompute_normals',False),('recompute_tangents',True),('use_mikk_t_space',True)]:
            settings.set_editor_property(name,value)
        SUB.set_lod_build_settings(mesh,0,settings)
        mesh.set_editor_property('has_navigation_data', False)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        nanite = mesh.get_editor_property('nanite_settings')
        for key, value in [('enabled', True), ('fallback_target', unreal.NaniteFallbackTarget.PERCENT_TRIANGLES),
                           ('fallback_percent_triangles', 1.), ('fallback_relative_error', 0.)]:
            nanite.set_editor_property(key, value)
        mesh.set_editor_property('nanite_settings', nanite)
        report['material'] = shader_check(material)
        report['mesh'] = mesh_check(mesh, material, spec, plan)
        save(mesh)
    elif MODE == 'verify':
        material = unreal.load_asset(MAT)
        report['material'] = shader_check(material)
        report['mesh'] = mesh_check(unreal.load_asset(DEST), material, spec, plan)
    # Re-pin source/bindings and exact Content/Data sets, not just preexisting paths.
    source_guard(SOURCE)
    assert tool_pins(ROOT) == report['tool_sha256'], 'Tool drift during native validation'
    assert module_pins(ROOT) == report['module_sha256'], 'Modules changed during native validation'
    binding_guard(ROOT, plan)
    after = asset_pins(ROOT)
    expected_set = set(protected) | (PACKAGES if MODE == 'import' else set())
    assert set(after) == expected_set, 'Unexpected Content package files created/deleted'
    changes = [p for p, digest in protected.items() if after.get(p) != digest]
    assert not changes, 'Existing package modified: ' + str(changes)
    assert data_pins(ROOT) == data, 'Runtime Data modified'
    report.update(protected_changes=[], runtime_data_changes=[], all_asset_sha256=after,
                  runtime_manifest_published=published, passed=True)
    if MODE in {'import', 'verify'}:
        report['saved_package_sha256'] = {p: after[p] for p in sorted(PACKAGES)}
except Exception as error:
    report['error'] = str(error)
    if protected is not None:
        actual = asset_pins(ROOT)
        report['protected_changes'] = [p for p, digest in protected.items() if actual.get(p) != digest]
        report['new_packages'] = sorted(set(actual) - set(protected))
    if data is not None:
        actual = data_pins(ROOT)
        report['runtime_data_changes'] = sorted(p for p in set(actual) | set(data) if actual.get(p) != data.get(p))
    raise
finally:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + '\n')
print('PERIMETER_SKIRT ' + MODE.upper() + ' PASS; runtime publication remains separate')
