"""Explicit unsaved trial entry; no Unreal import or execution on module load.

Caller owns the editor/build lease. This never saves packages, assigns game
Data, or activates replacements. Failed trials must discard their editor.
"""
import hashlib
import json
import math
from pathlib import Path

from RoofNative.closed_eaves_graph_recipe import active_recipe
from RoofNative.closed_eaves_graph_lowering import lower_recipe
from RoofNative.closed_eaves_unreal_adapter import build_new_material
from RoofNative.closed_eaves_native_graph_readback import inspect_constructed_graph
from RoofNative.house439_closed_eaves_preflight import inspect_compiled_geometry_capability
from RoofNative.closed_eaves_house_texture_encoding import PROFILE,validate_plan,configure_texture

NAMESPACE='/Game/Dink/Refinements/House439ClosedEavesV1'


def _settings_values(value):
    """Compare reflected values without relying on Unreal struct operators."""
    if value is None or type(value) in (bool,int,str):return value
    if type(value) is float:
        if not math.isfinite(value):raise ValueError('Nonfinite build setting')
        return value
    if isinstance(value,dict):return {key:_settings_values(v) for key,v in value.items()}
    if isinstance(value,(tuple,list)):return [_settings_values(v) for v in value]
    if callable(getattr(value,'to_dict',None)):return _settings_values(value.to_dict())
    if callable(getattr(value,'get_path_name',None)):return value.get_path_name()
    raise ValueError('Unsupported build-setting value type: '+type(value).__name__)


def apply_mesh_precision(subsystem,mesh,precision,guard):
    """Change only the two storage-precision fields on a detached settings copy."""
    expected={'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True}
    if precision!=expected:raise ValueError('Exact source-preserving precision plan required')
    def call(fn,*args):
        guard();return fn(*args)
    before=call(subsystem.get_lod_build_settings,mesh,0)
    target=call(before.copy)
    for key,value in precision.items():call(target.set_editor_property,key,value)
    expected_values=call(_settings_values,target)
    expected_text=call(target.export_text)
    call(subsystem.set_lod_build_settings,mesh,0,target)
    actual=call(subsystem.get_lod_build_settings,mesh,0)
    if call(_settings_values,actual)!=expected_values or call(actual.export_text)!=expected_text:
        raise RuntimeError('Actual LOD build settings differ; unrelated settings must remain exact')
    flags={key:actual.get_editor_property(key) for key in precision}
    if flags!=expected:raise RuntimeError('Actual mesh storage precision not retained')
    return dict(flags=flags,other_build_settings_preserved=True,actual_settings=expected_values,
                native_settings_text=expected_text)


def prepare_trial(project_root, *, transport_profile="legacy_2uv"):
    """All source payload hashes checked without an editor or asset access."""
    root=Path(project_root).resolve()
    folder=root/'Docs/Verification/House439ClosedEavesNative/MaterialProfile'
    library=root/'SourceAssets/Art/SharedMaterials/ClosedEavesSurfaceCandidatesV1'
    source=json.loads((library/'EXTRACTION.json').read_text())
    supplement=json.loads((folder/'NODE_SEMANTICS_SUPPLEMENT.json').read_text())
    packed=library/'ClosedEavesSurfaces_Source.blend'
    if hashlib.sha256(packed.read_bytes()).hexdigest()!=supplement['source_sha256']:
        raise ValueError('Material source differs from actual node readback')
    recipes={role:active_recipe(role,record,supplement['roles'][role])
             for role,record in source['roles'].items()}
    graphs={role:lower_recipe(recipe) for role,recipe in recipes.items()}
    payloads={hashlib.sha256(p.read_bytes()).hexdigest():p
              for p in (library/'Textures').iterdir() if p.is_file()}
    textures={}
    for graph in graphs.values():
        for n in graph['operations']:
            if n['operation']!='texture_rgb':continue
            image=n['image'];sha=image['sha256']
            if sha not in payloads:raise ValueError('Missing exact source texture '+sha)
            if sha in textures and textures[sha]['image']!=image:
                raise ValueError('Conflicting texture decode roles')
            textures[sha]=dict(image=image,file=str(payloads[sha]),
                               target=NAMESPACE+'/Textures/T_Source_'+sha)
    if transport_profile=="legacy_2uv":
        export=root/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/ExplicitTangentsV1'
        proof_file=export/'Evidence/SERIALIZED_TBN_READBACK.json'
        if hashlib.sha256(proof_file.read_bytes()).hexdigest()!='13aac0f6bb19979a0cc1df015f57b2bbcbe1fdae796e80ed8412e8a13f411eec':
            raise ValueError('Reviewed explicit-tangent core-equivalence proof differs')
        proof=json.loads(proof_file.read_text())
        mesh=export/'FBX/SM_Cottage_Stonebrook_01.fbx'
        mesh_sha=hashlib.sha256(mesh.read_bytes()).hexdigest()
        if (mesh_sha!='4d8c8f1eda4e37beed0dc1586bc3a72e1937660d990330d4473f8ec389c854e3'
                or proof['successor_fbx_sha256']!=mesh_sha
                or proof['old_fbx_sha256']!='aa4e091a48f3337f7b9bda4b1f044786c46149c163df511978bebb86bc210f27'
                or proof['frozen_geometry_sha256']!='20e969bcd0f4fae11f47d6d224e8063eb802e615263a8304ecd0c16c020d0c3d'
                or proof['pass_serialized_tbn'] is not True):
            raise ValueError('Explicit-tangent FBX does not match reviewed source admission')
        reference_metadata=export/'Reference/REFERENCE.json'
        reference_metadata_sha=hashlib.sha256(reference_metadata.read_bytes()).hexdigest()
        if reference_metadata_sha!='a268c2f32b64d4ccb0c7d62169dbc1b773728a58e0976de085f25b698583b842':
            raise ValueError('Explicit-tangent reference metadata companion differs')
        metadata=json.loads(reference_metadata.read_text())
        if metadata['fbx_sha256']!=mesh_sha or metadata['geometry_npz_sha256']!=proof['frozen_geometry_sha256']:
            raise ValueError('Explicit-tangent FBX/reference epoch differs')
    elif transport_profile=="house439_uv2_weld_seam_guard_v1":
        from RoofNative.closed_eaves_guarded_epoch import load_guarded_epoch
        epoch=load_guarded_epoch(root)
        mesh=epoch['mesh'];mesh_sha=epoch['mesh_sha256']
        reference_metadata=epoch['metadata'];reference_metadata_sha=epoch['metadata_sha256']
        proof_file=epoch['proof']
    else:
        raise ValueError('Unknown source transport profile')
    return dict(project=str(root),source_encoding_profile=PROFILE,graphs=graphs,textures=textures,mesh_file=str(mesh),
                mesh_sha256=mesh_sha,transport_profile=transport_profile,
                expected_uv_channels=3 if transport_profile=="house439_uv2_weld_seam_guard_v1" else 2,
                geometry_reference_metadata_file=str(reference_metadata),
                geometry_reference_metadata_sha256=reference_metadata_sha,
                explicit_tangent_admission_sha256=hashlib.sha256(proof_file.read_bytes()).hexdigest(),
                mesh_target=NAMESPACE+'/Meshes/SM_Cottage_Stonebrook_01',
                materials={role:NAMESPACE+'/Materials/MI_Shared_'+role for role in graphs},
                vertex_color_encoding='raw_linear_built_srgb_rgb_linear_alpha',
                nanite_enabled=False,
                mesh_precision={'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True},
                fbx_frame_options=dict(import_translation_cm=[0,0,0],import_rotation_degrees=[0,0,0],
                    force_front_x_axis=False,coordinate_system_policy='MATCH_UP_AXIS',
                    convert_scene=True,convert_scene_unit=True,import_uniform_scale=1.0),
                scope='Unsaved isolated trial only; own build/lease and full native evidence required')


def run_unsaved_trial(U, plan, guard, inspect_results):
    """Construct trial objects; require caller's actual native readback callback.

    inspect_results receives actual mesh/material/texture objects and must
    independently validate their serialized/native graphs, geometry and pixels.
    Its return is evidence, never implicit permission to save or activate.
    """
    if not callable(guard) or not callable(inspect_results):
        raise ValueError('Own lease guard and actual native readback required')
    guard()
    if plan!=prepare_trial(plan['project'],transport_profile=plan.get('transport_profile','legacy_2uv')):
        raise ValueError('Trial plan differs from current frozen source')
    inspect_compiled_geometry_capability(U,plan['project'],guard)
    guard()
    inputs_probe=json.loads(U.DinkMaterialArtLibrary.inspect_material_expression_inputs(None))
    if inputs_probe.get('schema')!='dink-expression-inputs/1' or inputs_probe.get('valid') is not False:
        raise ValueError('Exact expression input inspector not compiled/loaded')
    guard()
    pixels_probe=json.loads(U.DinkMaterialArtLibrary.inspect_texture_source_pixels(None))
    if pixels_probe.get('schema')!='dink-texture-source-pixels/1' or pixels_probe.get('valid') is not False:
        raise ValueError('Texture source pixel inspector not compiled/loaded')
    lib=U.EditorAssetLibrary
    targets=list(plan['materials'].values())+[v['target'] for v in plan['textures'].values()]+[plan['mesh_target']]
    if len(targets)!=len(set(targets)) or any(lib.does_asset_exist(p) for p in targets):
        raise ValueError('Trial target exists; no overwrite or reimport permitted')
    if U.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')!=0:
        raise ValueError('Caller must select and verify legacy FBX importer first')
    tools=U.AssetToolsHelpers.get_asset_tools()

    def call(fn,*args):
        guard();return fn(*args)
    def setprop(obj,key,value):call(obj.set_editor_property,key,value)
    def import_one(filename,target,options=None,factory=None):
        task=call(U.AssetImportTask)
        for key,value in dict(filename=filename,destination_path=target.rsplit('/',1)[0],
                              destination_name=target.rsplit('/',1)[1],automated=True,
                              replace_existing=False,save=False).items():setprop(task,key,value)
        if options is not None:setprop(task,'options',options)
        if factory is not None:setprop(task,'factory',factory)
        call(tools.import_asset_tasks,[task])
        paths=task.get_editor_property('imported_object_paths')
        if len(paths)!=1 or paths[0].split('.')[0]!=target:
            raise RuntimeError('Unexpected imported object inventory')
        result=lib.load_asset(paths[0])
        if result is None:raise RuntimeError('Imported object unavailable')
        return result

    validate_plan(plan) # Exact32 source payloads/profile/namespace before any texture import.
    bindings={}
    for sha,row in plan['textures'].items():
        texture=import_one(row['file'],row['target'],factory=call(U.TextureFactory))
        srgb=row['image']['colorspace']=='sRGB'
        for key,value in dict(srgb=srgb,flip_green_channel=False,
            compression_settings=U.TextureCompressionSettings.TC_EDITOR_ICON if srgb else U.TextureCompressionSettings.TC_HDR,
            address_x=U.TextureAddress.TA_WRAP,address_y=U.TextureAddress.TA_WRAP,
            filter=U.TextureFilter.TF_BILINEAR).items():setprop(texture,key,value)
        encoding=configure_texture(U,texture,sha,row,guard)
        bindings[sha]=dict(texture=texture,source_sha256=sha,srgb=srgb,
                           compression='retained_rgb',retained_channels='RGB',green_flip_count=0,source_encoding=encoding)
    call(U.SystemLibrary.execute_console_command,None,'Editor.AsyncTextureCompilationFinishAll',None)
    materials={};actual_graphs={}
    for role,graph in plan['graphs'].items():
        target=plan['materials'][role]
        material=call(tools.create_asset,target.rsplit('/',1)[1],target.rsplit('/',1)[0],
                      U.Material,call(U.MaterialFactoryNew))
        if material is None:raise RuntimeError('New material creation failed')
        contract=dict(target=target,new_empty_material=True,
            vertex_color_encoding=plan['vertex_color_encoding'],
            normal_basis_conversion='source_OpenGL_to_imported_UE_single_Y_flip',
            optics='thin_translucent_closed_pane_trial' if role=='ThinWavyGlass2m' else 'opaque_dielectric_metal_trial')
        receipt=build_new_material(U,material,graph,bindings,contract,guard)
        guard()
        actual_graphs[role]=inspect_constructed_graph(U,material,receipt)
        materials[role]=material
    options=call(U.FbxImportUI)
    for key,value in dict(automated_import_should_detect_type=False,
        mesh_type_to_import=U.FBXImportType.FBXIT_STATIC_MESH,import_mesh=True,
        import_materials=False,import_textures=False,import_animations=False).items():setprop(options,key,value)
    for key,value in dict(combine_meshes=True,import_mesh_lods=False,remove_degenerates=False,
        build_nanite=plan['nanite_enabled'],
        auto_generate_collision=False,generate_lightmap_u_vs=False,convert_scene=True,
        convert_scene_unit=True,import_uniform_scale=1.0,
        normal_import_method=U.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS,
        vertex_color_import_option=U.VertexColorImportOption.REPLACE).items():setprop(options.static_mesh_import_data,key,value)
    frame=plan['fbx_frame_options']
    frame_values=dict(import_translation=U.Vector(*frame['import_translation_cm']),
        import_rotation=U.Rotator(*frame['import_rotation_degrees']),
        force_front_x_axis=frame['force_front_x_axis'],
        coordinate_system_policy=getattr(U.CoordinateSystemPolicy,frame['coordinate_system_policy']),
        convert_scene=frame['convert_scene'],convert_scene_unit=frame['convert_scene_unit'],
        import_uniform_scale=frame['import_uniform_scale'])
    for key,value in frame_values.items():setprop(options.static_mesh_import_data,key,value)
    def assert_frame(data):
        if any(data.get_editor_property(key)!=value for key,value in frame_values.items()):
            raise RuntimeError('Effective FBX frame options differ')
    assert_frame(options.static_mesh_import_data)
    mesh=import_one(plan['mesh_file'],plan['mesh_target'],options=options,factory=call(U.FbxFactory))
    assert_frame(mesh.get_editor_property('asset_import_data'))
    actual_nanite=mesh.get_editor_property('nanite_settings').get_editor_property('enabled')
    if actual_nanite is not plan['nanite_enabled']:
        raise RuntimeError('Actual candidate Nanite path differs from explicit trial plan')
    subsystem=U.get_editor_subsystem(U.StaticMeshEditorSubsystem)
    if subsystem is None:raise RuntimeError('Static mesh editor subsystem unavailable')
    precision_readback=apply_mesh_precision(subsystem,mesh,plan['mesh_precision'],guard)
    call(subsystem.set_allow_cpu_access,mesh,True)
    # Resolve real imported slot names, never assume list order from source.
    slots=mesh.get_editor_property('static_materials')
    names=[str(slot.get_editor_property('imported_material_slot_name')) for slot in slots]
    expected={'MI_Shared_'+role for role in materials}
    if len(names)!=7 or set(names)!=expected:raise RuntimeError('Imported seven material roles differ')
    for index,name in enumerate(names):call(mesh.set_material,index,materials[name.removeprefix('MI_Shared_')])
    guard()
    geometry=json.loads(U.DinkMaterialArtLibrary.inspect_static_mesh_geometry(mesh,0))
    if (geometry.get('schema')!='dink-static-mesh-geometry/1' or geometry.get('valid') is not True
            or len(geometry['raw']['triangles'])!=182626
            or len(geometry['built']['indices'])!=182626*3
            or geometry['raw']['uv_channels']!=plan['expected_uv_channels'] or geometry['built']['uv_channels']!=plan['expected_uv_channels']
            or geometry['built']['full_precision_uvs'] is not True
            or geometry['built']['high_precision_tangent_basis'] is not True):
        raise RuntimeError('Actual geometry readback differs from source admission')
    evidence=inspect_results(mesh,materials,bindings,plan)
    guard()
    final_geometry=json.loads(U.DinkMaterialArtLibrary.inspect_static_mesh_geometry(mesh,0))
    if final_geometry.get('valid') is not True:
        raise RuntimeError('Post-callback mesh geometry unavailable')
    return dict(mesh=mesh,materials=materials,bindings=bindings,evidence=evidence,
                initial_geometry=geometry,actual_geometry=final_geometry,actual_graphs=actual_graphs,
                actual_import_frame_options=frame,
                actual_nanite_enabled=actual_nanite,
                actual_mesh_precision=precision_readback,
                saved=False,activated=False,scope='Unsaved trial; discard editor on any failure')
