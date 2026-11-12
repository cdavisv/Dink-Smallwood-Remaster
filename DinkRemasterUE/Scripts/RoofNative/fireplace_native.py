"""Fresh35 import/readback adapter only. Root owns guarded editor/build/activation.
No launcher, Unreal import, asset mutation or source writes on module import.
"""
from pathlib import Path
import copy
from fireplace_contract import load_contract,assert_trial_absent,trial_package_file,require,sha,SOURCE,TRIAL
from fireplace_material import build_graph
from fireplace_material_readback import inspect_graph
from fireplace_mesh_readback import make_mesh_verifier,source_used_role_packages,decode_source
from native_texture_tools_v11 import _import_profile,_configure_profile
from native_mesh_tools_v11c import import_fireplace_base,append_lods,configure_policy
from shared_roof_native import bind_named_materials
from relative_source_metadata import inspect_relative_sources

def preflight(U,root,contract,guard):
    require(not contract.get('source_blockers'),'Source Color0 clipping blocks native trial before imports; no tolerance/reference waiver')
    require(callable(guard),'Root source/Content/module guard required');guard()
    require(Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()==root,'Loaded editor project differs')
    require(load_contract(root)==contract,'Pinned source/code contract or recipe changed')
    for package in contract['trial_packages']:trial_package_file(root,package)
    require('-game'not in U.SystemLibrary.get_command_line().split(),'Editor only')
    require(U.SystemLibrary.get_console_variable_int_value('r.Substrate')==0,'Reviewed legacy opaque source port refuses Substrate')
    require(U.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')==0,'Legacy FBX required')
    capability=getattr(getattr(U,'DinkRoofSourceMetadataLibrary',None),'supports_fireplace_fired_clay_v4_source_filenames',None)
    require(callable(capability)and capability()is True,'New exact fireplace filename scope not compiled; refuse before imports')
    require(callable(getattr(getattr(U,'DinkMaterialArtLibrary',None),'inspect_static_mesh_geometry',None)),'Reviewed RAW/built guarded inspector unavailable')
def approved(result,label):
    require(isinstance(result,dict)and result.get('passed')is True,'Actual '+label+' verification failed');return result
def checked_mesh_before_save(mesh,record,configure_metadata,mesh_check,persist):
    configure_metadata(mesh,record);result=approved(mesh_check(mesh,record),'mesh')
    require(result.get('triangles')==record['triangles']and result.get('UCX')==record['UCX']and result.get('source_correspondence_passed')is True and result.get('raw_Color0_import_passed')is True and result.get('normal_tangent_basis')=='UV0','Incomplete actual mesh/UCX/UV/Color0 proof')
    persist(mesh);return result

def import_trial(U,root,contract,approval,guard,save,pixel_check,graph_check,mesh_check,emit_receipt):
    root=Path(root);require(all(callable(x)for x in(guard,save,pixel_check,graph_check,mesh_check,emit_receipt)),'Reviewed Root callbacks required')
    require(approval.get('approved')is True and approval.get('contract_digest')==contract['digest']and approval.get('source_graphs_reviewed')is True and approval.get('pivot_compensation_reviewed')is True,'Matching explicit Root source/F0/pivot review required')
    preflight(U,root,contract,guard);concrete=make_mesh_verifier(U,root,contract,approval.get('geometry_tolerances'));assert_trial_absent(root,contract)
    require(all(not U.EditorAssetLibrary.does_asset_exist(p)for p in contract['trial_packages']),'Loaded fresh target exists')
    report=dict(passed=False,phase='fresh35_fireplace_import',contract_digest=contract['digest'],geometry_tolerances=dict(approval['geometry_tolerances']),packages={},textures=[],materials=[],meshes=[],production_activated=False)
    def metadata(asset,files):
        guard();require(U.DinkRoofSourceMetadataLibrary.set_fireplace_fired_clay_v4_source_filenames_relative(asset,[str(Path(p).resolve())for p in files])is True,'Exact fireplace filename transaction refused');inspect_relative_sources(U,asset,files,root/'SourceAssets/Art')
    def persist(asset,files=None):
        package=asset.get_path_name().split('.')[0];require(package in contract['trial_packages'],'Unexpected save');file=trial_package_file(root,package);require(not file.exists(),'Overwrite save')
        if files:metadata(asset,files)
        guard();require(save(asset,overwrite=False)is True,'Fresh save failed');require(file.is_file()and not file.is_symlink()and file.stat().st_nlink==1,'Saved file missing/aliased');report['packages'][str(file.relative_to(root))]=sha(file)
    def combined(mesh,record):
        result=concrete(mesh,record);result['additional_review']=approved(mesh_check(mesh,record),'additional mesh/frame');return result
    try:
        imported={}
        for recipe in contract['textures']:
            def configure(U,texture,r,guard,configure=False):
                require(r==recipe,'Texture recipe escaped set');return _configure_profile(U,texture,r,guard,configure,1024)
            source=root/recipe['source_file'];texture=_import_profile(U,source,recipe,guard,TRIAL+'Textures/',configure);report['textures'].append(approved(pixel_check(texture,source,recipe),'source pixel'));persist(texture,[source]);imported[recipe['package']]=texture
        tools=U.AssetToolsHelpers.get_asset_tools()
        for pending in contract['materials']:
            recipe=copy.deepcopy(pending);folder,name=recipe['package'].rsplit('/',1);guard();require(not U.EditorAssetLibrary.does_asset_exist(recipe['package']),'Late material target appeared');m=tools.create_asset(name,folder,U.Material,U.MaterialFactoryNew());require(isinstance(m,U.Material),'Material creation failed');recipe['source_graph_reviewed']=True;build_graph(U,m,recipe,recipe['source_graph'],{n:imported[p]for n,p in recipe['textures'].items()},guard)
            result=inspect_graph(U,m,recipe);result['additional_review']=approved(graph_check(m,recipe),'additional shader/F0');report['materials'].append(result);persist(m)
        all_roles={r['source_material']:r['package']for r in contract['materials']};subsystem=U.get_default_object(U.StaticMeshEditorSubsystem)
        for record in contract['meshes']:
            source,_=decode_source(root,record);roles=source_used_role_packages(record,all_roles,source)
            native_record=dict(record,sha256=record['source_sha256']);mesh=import_fireplace_base(U,root/SOURCE,native_record,record['package'],guard);append_lods(U,mesh,root/SOURCE,[dict(index=0)],subsystem,guard);configure_policy(U,mesh,record,guard);bind_named_materials(U,mesh,roles,record['triangles'],guard)
            report['meshes'].append(checked_mesh_before_save(mesh,record,lambda m,r:metadata(m,[root/SOURCE/r['file']]),combined,persist))
        require(len(report['packages'])==35,'Incomplete fresh35 save set');guard();require(load_contract(root)==contract,'Source/code/recipe changed during import');report['passed']=True;return report
    except BaseException as error:report['error']=repr(error);raise
    finally:emit_receipt(report)

def verify_trial_readback(U,root,contract,imported,guard,pixel_check,graph_check,mesh_check,emit_receipt):
    root=Path(root);require(all(callable(x)for x in(guard,pixel_check,graph_check,mesh_check,emit_receipt)),'Read-only Root callbacks required');preflight(U,root,contract,guard)
    require(imported.get('passed')is True and imported.get('phase')=='fresh35_fireplace_import'and imported.get('contract_digest')==contract['digest']and imported.get('production_activated')is False,'Complete matching trial receipt required')
    expected={'Content/'+p.removeprefix('/Game/')+'.uasset'for p in contract['trial_packages']};require(set(imported['packages'])==expected,'Saved package set differs');concrete=make_mesh_verifier(U,root,contract,imported.get('geometry_tolerances'));report=dict(passed=False,phase='saved35_fireplace_readback',contract_digest=contract['digest'],packages=dict(imported['packages']),textures=[],materials=[],meshes=[],imports=0,saves=0,production_activated=False)
    def hashes():
        for package in contract['trial_packages']:trial_package_file(root,package)
        for name,digest in imported['packages'].items():
            p=root/name;require(p.is_file()and not p.is_symlink()and p.stat().st_nlink==1 and sha(p)==digest,'Saved trial bytes differ')
    try:
        guard();hashes()
        for recipe in contract['textures']:
            guard();texture=U.load_asset(recipe['package']);_configure_profile(U,texture,recipe,guard,False,1024);source=root/recipe['source_file'];inspect_relative_sources(U,texture,[source],root/'SourceAssets/Art');report['textures'].append(approved(pixel_check(texture,source,recipe),'saved source pixel'))
        for recipe in contract['materials']:
            guard();m=U.load_asset(recipe['package']);result=inspect_graph(U,m,recipe);result['additional_review']=approved(graph_check(m,recipe),'saved shader/F0');report['materials'].append(result)
        for record in contract['meshes']:
            guard();m=U.load_asset(record['package']);require(isinstance(m,U.StaticMesh),'Saved mesh missing');result=concrete(m,record);result['additional_review']=approved(mesh_check(m,record),'saved mesh/frame');require(result['triangles']==record['triangles']and result['UCX']==record['UCX'],'Incomplete saved inventory');report['meshes'].append(result)
        guard();hashes();require(load_contract(root)==contract,'Contract changed in readback');report['passed']=True;return report
    except BaseException as error:report['error']=repr(error);raise
    finally:emit_receipt(report)
