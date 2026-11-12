"""Source-only fresh38 cottage importer. Root owns native isolation/review/save proofs.
Never launches Unreal, mutates packages or imports assets at module load.
"""
from pathlib import Path
import copy
from house439_contract import load_contract,assert_trial_absent,require,sha,SOURCE,TRIAL
from house439_glass_material import build_graph as build_glass
from house439_opaque_material import build_graph as build_opaque
from house439_material_readback import inspect_graph as inspect_house_graph
from house439_mesh_readback import make_mesh_verifier
from native_texture_tools_v11 import _import_profile,_configure_profile
from native_mesh_tools_v11c import import_house439_base,append_lods,configure_policy
from shared_roof_native import bind_named_materials
from relative_source_metadata import inspect_relative_sources



def checked_mesh_before_save(mesh,record,configure_metadata,mesh_check,persist):
    """Configure all relative metadata before the actual mesh verifier can inspect it."""
    configure_metadata(mesh,record)
    result=mesh_check(mesh,record)
    require(isinstance(result,dict)and result.get('passed')is True,'Actual native mesh verification failed')
    require(result.get('triangles')==194192 and result.get('UCX')==6 and result.get('source_correspondence_passed')is True and result.get('raw_Color0_import_passed')is True and result.get('normal_tangent_basis')=='UV0','Incomplete whole-cottage native source proof')
    persist(mesh)
    return result


def import_trial(U,root,contract,approval,guard,save,pixel_check,graph_check,mesh_check,emit_receipt):
    """Exact fresh set only. No production binding, Data changes or automatic retries.
    Callback checks must inspect actual native content, never substitute offline proof.
    Caller must fresh-process readback and verify optics after this phase.
    """
    root=Path(root)
    require(all(callable(x)for x in (guard,save,pixel_check,graph_check,mesh_check,emit_receipt)),'Root guarded native callbacks required')
    require(approval.get('approved')is True and approval.get('contract_digest')==contract['digest']and approval.get('source_graphs_reviewed')is True and approval.get('physical_uv_channel')==0 and approval.get('closed_pane_thin_sheet_trial')is True,'Explicit matching Root native review required')
    guard();require(load_contract(root)['digest']==contract['digest'],'Frozen source contract changed')
    require(Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()==root,'Loaded native project differs')
    require('-game'not in U.SystemLibrary.get_command_line().split(),'Editor-only import')
    require(U.SystemLibrary.get_console_variable_int_value('r.Substrate')==0,'Legacy thin-translucent profile refuses Substrate')
    require(U.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')==0,'Legacy FBX importer required')
    capability=getattr(getattr(U,'DinkRoofSourceMetadataLibrary',None),'supports_house439_shared_source_filenames',None)
    require(callable(capability)and capability()is True,'House439 metadata scope not compiled/loaded; refuse before imports')
    require(callable(getattr(getattr(U,'DinkMaterialArtLibrary',None),'inspect_static_mesh_geometry',None)),'RAW/all-UV/Color0 bridge not compiled; refuse before imports')
    concrete_mesh_check=make_mesh_verifier(U,root,contract,approval.get('geometry_tolerances'))
    assert_trial_absent(root,contract)
    require(all(not U.EditorAssetLibrary.does_asset_exist(p)for p in contract['trial_packages']),'Loaded trial target already exists')
    report=dict(passed=False,phase='fresh38_house439_import',contract_digest=contract['digest'],geometry_tolerances=dict(approval['geometry_tolerances']),packages={},textures=[],materials=[],meshes=[],production_activated=False)
    def checked(result,label):
        require(isinstance(result,dict)and result.get('passed')is True,'Actual native '+label+' verification failed');return result
    def metadata(asset,files):
        expected=[str(Path(p).resolve())for p in files];guard();require(U.DinkRoofSourceMetadataLibrary.set_house439_source_filenames_relative(asset,expected)is True,'House439 relative metadata setter refused')
        inspect_relative_sources(U,asset,files,root/'SourceAssets/Art')
    def persist(asset,files=None):
        package=asset.get_path_name().split('.')[0];require(package in contract['trial_packages'],'Unexpected package save');file=root/('Content/'+package.removeprefix('/Game/')+'.uasset');require(not file.exists()and not file.is_symlink(),'Refusing package overwrite')
        if files:
            metadata(asset,files)
        guard();require(save(asset,overwrite=False)is True,'Fresh package save failed');require(file.is_file()and not file.is_symlink()and file.stat().st_nlink==1,'Saved package missing/aliased');report['packages'][file.relative_to(root).as_posix()]=sha(file)
    def combined_mesh_check(mesh,record):
        actual=concrete_mesh_check(mesh,record);actual['additional_review']=checked(mesh_check(mesh,record),'additional mesh/frame');return actual
    try:
        imported={}
        for recipe in contract['textures']:
            def configure(U,texture,actual_recipe,guard,configure=False):
                require(actual_recipe==recipe,'Texture recipe escaped frozen set');return _configure_profile(U,texture,actual_recipe,guard,configure,1024)
            source=root/recipe['source_file'];texture=_import_profile(U,source,recipe,guard,TRIAL+'Textures/',configure);report['textures'].append(checked(pixel_check(texture,source,recipe),'source pixel'));persist(texture,[source]);imported[recipe['package']]=texture
        tools=U.AssetToolsHelpers.get_asset_tools()
        for pending in contract['materials']:
            recipe=copy.deepcopy(pending);target=recipe['package'];folder,name=target.rsplit('/',1);guard();require(not U.EditorAssetLibrary.does_asset_exist(target),'Late material target appeared');material=tools.create_asset(name,folder,U.Material,U.MaterialFactoryNew());require(isinstance(material,U.Material),'Material creation failed')
            typed={name:imported[path]for name,path in recipe['textures'].items()}
            if recipe['profile']=='thin_transmissive_surface_2m':
                recipe.update(native_policy_reviewed=True,physical_uv_reviewed=True);build_glass(U,material,recipe,typed,guard)
            else:
                recipe['source_graph_reviewed']=True;build_opaque(U,material,recipe,recipe['source_graph'],typed,guard)
            actual_graph=inspect_house_graph(U,material,recipe);actual_graph['additional_review']=checked(graph_check(material,recipe),'additional graph/shader');report['materials'].append(actual_graph);persist(material)
        role_packages={r['source_material']:r['package']for r in contract['materials']};subsystem=U.get_default_object(U.StaticMeshEditorSubsystem)
        for record in contract['meshes']:
            native_record=dict(record,sha256=record['source_sha256']);mesh=import_house439_base(U,root/SOURCE,native_record,record['package'],guard);append_lods(U,mesh,root/SOURCE,[dict(index=0)],subsystem,guard);configure_policy(U,mesh,record,guard);bind_named_materials(U,mesh,role_packages,194192,guard);result=checked_mesh_before_save(mesh,record,lambda asset,r:metadata(asset,[root/SOURCE/r['file']]),combined_mesh_check,persist);report['meshes'].append(result)
        require(len(report['packages'])==38,'Incomplete fresh38 save set');guard();require(load_contract(root)['digest']==contract['digest'],'Source changed during trial');report['passed']=True;return report
    except BaseException as error:
        report['error']=repr(error);raise
    finally:emit_receipt(report)


def verify_trial_readback(U,root,contract,imported,guard,pixel_check,graph_check,mesh_check,emit_receipt):
    """Separate fresh-process saved readback. No import, setter or save is called.
    Root supplies reviewed read-only source-pixel/actual-graph/mesh inspectors.
    """
    from native_texture_tools_v11 import _configure_profile
    from native_material_slots_v11 import inspect_slots
    require(all(callable(x)for x in (guard,pixel_check,graph_check,mesh_check,emit_receipt)),'Reviewed read-only native callbacks required')
    root=Path(root);require(imported.get('passed')is True and imported.get('contract_digest')==contract['digest']and imported.get('phase')=='fresh38_house439_import','Successful matching native import receipt required')
    require(imported.get('production_activated')is False,'Production activation outside trial scope')
    concrete_mesh_check=make_mesh_verifier(U,root,contract,imported.get('geometry_tolerances'))
    expected={'Content/'+p.removeprefix('/Game/')+'.uasset'for p in contract['trial_packages']};require(set(imported['packages'])==expected,'Saved package coverage differs')
    report=dict(passed=False,phase='saved38_house439_readback',contract_digest=contract['digest'],textures=[],materials=[],meshes=[],production_activated=False)
    def hashes():
        for relative,digest in imported['packages'].items():
            p=root/relative;require(p.is_file()and not p.is_symlink()and p.stat().st_nlink==1 and sha(p)==digest,'Saved trial bytes changed/missing: '+relative)
    def checked(result,label):require(isinstance(result,dict)and result.get('passed')is True,'Actual saved '+label+' check failed');return result
    try:
        guard();require(Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()==root,'Saved readback loaded project differs');require(load_contract(root)['digest']==contract['digest'],'Source contract changed');hashes()
        for recipe in contract['textures']:
            guard();texture=U.load_asset(recipe['package']);_configure_profile(U,texture,recipe,guard,False,1024);source=root/recipe['source_file'];inspect_relative_sources(U,texture,[source],root/'SourceAssets/Art');report['textures'].append(checked(pixel_check(texture,source,recipe),'source pixel'))
        for recipe in contract['materials']:
            guard();material=U.load_asset(recipe['package']);require(isinstance(material,U.Material),'Saved material missing');actual_graph=inspect_house_graph(U,material,recipe);actual_graph['additional_review']=checked(graph_check(material,recipe),'additional saved graph/shader');report['materials'].append(actual_graph)
        roles={r['source_material']:r['package']for r in contract['materials']}
        for record in contract['meshes']:
            guard();mesh=U.load_asset(record['package']);require(isinstance(mesh,U.StaticMesh),'Saved whole cottage missing');inspect_relative_sources(U,mesh,[root/SOURCE/record['file']],root/'SourceAssets/Art');names=[str(s.get_editor_property('imported_material_slot_name'))for s in mesh.get_editor_property('static_materials')];require(len(names)==7 and set(names)==set(roles),'Saved semantic slot set differs');inspect_slots(U,mesh,0,names,roles,194192);result=concrete_mesh_check(mesh,record);result['additional_review']=checked(mesh_check(mesh,record),'additional saved mesh/frame');require(result.get('triangles')==194192 and result.get('UCX')==6 and result.get('source_correspondence_passed')is True and result.get('raw_Color0_import_passed')is True and result.get('normal_tangent_basis')=='UV0','Incomplete saved whole-cottage proof');report['meshes'].append(result)
        guard();hashes();require(load_contract(root)['digest']==contract['digest'],'Source changed during saved readback');report['passed']=True;return report
    except BaseException as error:report['error']=repr(error);raise
    finally:emit_receipt(report)
