"""Review-only exact50 asset sequence. No module-load Unreal calls or auto-launch.
Caller must provide reviewed project/mount/module/input guards, exact save callback,
source-pixel diagnostic callback and receipt writer. Fresh readback is a separate run.
"""
from pathlib import Path
import hashlib,json,re
from native_texture_tools_v11 import import_new as import_texture
from native_material_builder_v12 import build_graph
from native_material_readback_v12 import inspect_graph
from native_mesh_tools_v11c import import_base,append_lods,configure_policy
from native_material_slots_v11 import inspect_slots
from relative_source_metadata import configure_relative_sources

def require(ok,message):
    if not ok:raise ValueError(message)

def validate_inputs(root,proposal,recipe,binding,approved_fireplace_nanite):
    root=Path(root);packet=Path(binding['source_packet']).resolve()
    require(root.is_absolute() and root.resolve()==root and Path(binding['project'])==root,'Unexpected selected project')
    assets=proposal['packages'];packages={a['package']:a for a in assets}
    require(len(packages)==len(assets)==50,'Exact50 unique packages required')
    require({k:sum(a['kind']==k for a in assets) for k in ['Texture2D','Material','StaticMesh']}=={'Texture2D':25,'Material':15,'StaticMesh':10},'Exact asset classes/counts required')
    folders={'Texture2D':'Textures','Material':'Materials','StaticMesh':'Meshes'}
    require(all(re.fullmatch(r'/Game/Dink/Refinements/RoofChimneyV12d/'+folders[a['kind']]+r'/[A-Za-z0-9_]+',a['package']) for a in assets),'Package type/path mismatch')
    require(approved_fireplace_nanite and approved_fireplace_nanite.get('enabled') is True and {'fallback_target','fallback_percent_triangles','fallback_relative_error'}<=approved_fireplace_nanite.keys(),'Exact original FP baseline required before native API calls')
    require(len(recipe['textures'])==25 and len(recipe['materials'])==8 and len(binding['meshes'])==10,'Recipe inventory differs')
    require(hashlib.sha256((packet/'export_manifest.json').read_bytes()).hexdigest()==proposal['manifest_sha256'],'Pinned new source manifest differs')
    require(hashlib.sha256(Path(binding['source_reference']).read_bytes()).hexdigest()==binding['source_reference_sha256'],'Pinned actual FBX source reference differs')
    manifest=json.loads((packet/'export_manifest.json').read_text())
    records=manifest['FBX']+manifest['textures'];require(len(manifest['FBX'])==12 and len(manifest['textures'])==25,'Exact37 payload files required')
    require(len({r['file'] for r in records})==37 and sum(r['matched_UCX'] for r in manifest['FBX'])==312,'Source inventory differs')
    for record in records:
        file=(packet/record['file']).resolve();require(file.is_relative_to(packet),'Payload escaped packet')
        require(file.is_file() and file.stat().st_size==record['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==record['sha256'],'Source payload differs')
    fbxs={r['file']:r for r in manifest['FBX']};lods=[]
    for mesh in binding['meshes']:
        require([r['index'] for r in mesh['LODs']]==list(range(len(mesh['LODs']))),'LOD sequence incomplete')
        for lod in mesh['LODs']:
            require(lod['file'] in fbxs and lod['sha256']==fbxs[lod['file']]['sha256'] and lod['full_precision_uv'] is True,'LOD source/precision contract differs');lods.append(lod)
    require(len(lods)==12 and len({r['file'] for r in lods})==12 and sum(r['expected_source_triangles'] for r in lods)==48090,'Exact12LOD/48090source triangle contract differs')
    require({r['source_sha256'] for r in recipe['textures']}=={r['sha256'] for r in manifest['textures']},'Texture recipe/source hashes differ')
    require(hashlib.sha256(Path(binding['source_inventory']).read_bytes()).hexdigest()==binding['source_inventory_sha256'],'Explicit source inventory changed')
    inventory=json.loads(Path(binding['source_inventory']).read_text())['objects']
    source_objects={r['source_object']:r for r in manifest['FBX']}
    require(len(inventory)==12 and {r['name'] for r in inventory}==set(source_objects),'Exact12 source inventory objects required')
    for record in inventory:
        require(record['triangles']==source_objects[record['name']]['render_triangles'],'Inventory/actual FBX triangle count differs')
        slots=record['material_slots'];counts=record['triangle_material_counts']
        require(slots and len(slots)==len(set(slots)) and set(counts)<=set(slots) and sum(counts.values())==record['triangles'],'Source material-slot inventory incomplete')
    texture_by_file={r['file']:r for r in manifest['textures']}
    require(len({r['source_file'] for r in recipe['textures']})==25,'Exact25 intended texture filenames required')
    for row in recipe['textures']:
        filename=row['source_file'];require(filename in texture_by_file and texture_by_file[filename]['sha256']==row['source_sha256'],'Explicit texture file/SHA differs')
        logical=Path(filename).name
        while logical.endswith('.png'):logical=logical[:-4]
        require(logical==row['package'].rsplit('/',1)[-1] and Path(filename).stem==row['source_image'],'Texture filename/logical role differs; SHA aliases cannot select sources')
    proposed_textures={a['package']:a for a in assets if a['kind']=='Texture2D'}
    for row in recipe['textures']:
        settings=proposed_textures[row['package']]['settings']
        require(row['srgb']==settings['native_sRGB'],'Recipe/proposal texture sRGB differs')
        if row['package'].endswith('_N'):
            require(row['compression']=='TC_NORMALMAP' and row['flip_green']==settings['native_flip_green'],'Explicit normal compression/green policy differs')
    by_object={r['name']:r for r in inventory}
    nanite_roles=set()
    for asset in assets:
        if asset['kind']=='StaticMesh' and asset['collision_policy']['nanite'] is not False:
            for lod in asset['LODs']:nanite_roles.update(by_object[fbxs[lod['file']]['source_object']]['material_slots'])
    require(nanite_roles<={r['source_material'] for r in recipe['materials']},'Nanite material role unresolved')
    for row in recipe['materials']:
        expected=['MATUSAGE_NANITE'] if row['source_material'] in nanite_roles else []
        require(row['required_usage']==expected,'Role-required Nanite usage differs')
    return {'payload_files':37,'packages':50,'LODs':12,'source_triangles':48090,'UCX':312,'scope':'Source inputs/structure only; native policy approval and runtime proof remain separate'}

def import_assets(U,root,proposal,recipe,binding,approved_fireplace_nanite,guard,save,pixel_check,emit_receipt):
    root=Path(root);packet=Path(binding['source_packet'])
    validate_inputs(root,proposal,recipe,binding,approved_fireplace_nanite)
    require(root.resolve()==root and Path(binding['project'])==root,'Unexpected selected project')
    require(all(callable(f) for f in [guard,save,pixel_check,emit_receipt]),'Reviewed guard/save/readback/receipt functions required')
    packages={a['package']:a for a in proposal['packages']}
    require(len(packages)==len(proposal['packages'])==50,'Exact50 unique packages required')
    require(all(p.startswith('/Game/Dink/Refinements/RoofChimneyV12d/') and '.' not in p for p in packages),'Invalid/private package scope')
    require(approved_fireplace_nanite and approved_fireplace_nanite.get('enabled') is True and {'fallback_target','fallback_percent_triangles','fallback_relative_error'}<=approved_fireplace_nanite.keys(),'Approved exact original FP fallback baseline required BEFORE mutations')
    require({a['package'] for a in recipe['textures']}=={p for p,a in packages.items() if a['kind']=='Texture2D'},'Texture whitelist differs')
    require({r[k] for r in recipe['materials'] for k in ['opaque','masked'] if r[k]}=={p for p,a in packages.items() if a['kind']=='Material'},'Material whitelist differs')
    require({m['package'] for m in binding['meshes']}=={p for p,a in packages.items() if a['kind']=='StaticMesh'},'Mesh whitelist differs')
    manifest=json.loads((packet/'export_manifest.json').read_text())
    files={r['file']:r for r in manifest['FBX']}
    sources={r['file']:r for r in manifest['textures']}
    inventory={r['name']:r for r in json.loads(Path(binding['source_inventory']).read_text())['objects']}
    material_rows={r['source_material']:r for r in recipe['materials']}
    opaque={role:r['opaque'] for role,r in material_rows.items()}
    report={'passed':False,'phase':'candidate_asset_import_only','packages':{},'texture_checks':[], 'material_checks':[],'slot_checks':[],'runtime_published':False,'fresh_reopen_required':True}
    require(callable(getattr(U.MaterialEditingLibrary,'set_base_material_usage',None)) and callable(getattr(U.MaterialEditingLibrary,'has_material_usage',None)) and getattr(U.MaterialUsage,'MATUSAGE_NANITE',None) is not None,'Required material usage API/enum unavailable before imports')
    require(callable(getattr(getattr(U,'DinkRoofSourceMetadataLibrary',None),'set_roof_source_filenames_relative',None))and callable(getattr(getattr(U,'DinkRoofSourceMetadataLibrary',None),'inspect_roof_source_filenames',None)),'Reviewed raw-relative metadata API unavailable before imports')
    L=U.EditorAssetLibrary;T=U.AssetToolsHelpers.get_asset_tools()
    def persist(asset):
        package=asset.get_path_name().split('.')[0]
        require(package in packages,'Save outside exact50 whitelist')
        relative='Content/'+package.removeprefix('/Game/')+'.uasset';file=root/relative
        require(not file.exists() and relative not in report['packages'],'Refusing package overwrite')
        if packages[package]['kind']!='Material':
            files=([packet/r['source_file']for r in recipe['textures']if r['package']==package]if packages[package]['kind']=='Texture2D'else[packet/r['file']for m in binding['meshes']if m['package']==package for r in m['LODs']])
            configure_relative_sources(U,asset,files,packet,guard)
        guard();require(save(asset) is True,'Explicit package save failed')
        require(file.is_file() and not file.is_symlink() and file.stat().st_nlink==1,'Invalid saved package')
        report['packages'][relative]=hashlib.sha256(file.read_bytes()).hexdigest()
    try:
        guard()
        require(all(not L.does_asset_exist(p) for p in packages),'Existing target detected; no automatic resume/replacement')
        textures={}
        for row in recipe['textures']:
            source=packet/sources[row['source_file']]['file']
            texture=import_texture(U,source,row,guard)
            report['texture_checks'].append(pixel_check(texture,source,row))
            persist(texture);textures[row['package']]=texture
        for row in recipe['materials']:
            typed={role:textures[path] for role,path in row['textures'].items()}
            for masked in [False,True]:
                target=row['masked' if masked else 'opaque']
                if target is None:continue
                folder,name=target.rsplit('/',1);guard();require(not L.does_asset_exist(target),'Late material target exists')
                material=T.create_asset(name,folder,U.Material,U.MaterialFactoryNew())
                require(isinstance(material,U.Material),'Material creation failed')
                build_graph(U,material,row,typed,masked,guard)
                report['material_checks'].append(inspect_graph(U,material,row,masked));persist(material)
        S=U.get_default_object(U.StaticMeshEditorSubsystem)
        for mesh_row in binding['meshes']:
            target=mesh_row['package'];records=mesh_row['LODs'];require(records[0]['index']==0,'Missing explicit base LOD')
            base=files[records[0]['file']];mesh=import_base(U,packet,base,target,guard)
            append_lods(U,mesh,packet,records,S,guard)
            policy=packages[target]['collision_policy'];configure_policy(U,mesh,policy,guard,approved_fireplace_nanite)
            source_slots=inventory[base['source_object']]['material_slots']
            actual=mesh.get_editor_property('static_materials')
            require(len(actual)==len(source_slots),'Actual slot count differs')
            imported=[str(row.get_editor_property('imported_material_slot_name')) for row in actual]
            require(set(imported)==set(source_slots) and len(imported)==len(set(imported)),'Imported slot semantic roles differ')
            for index,role in enumerate(imported):
                material=U.load_asset(opaque[role]);require(isinstance(material,U.Material),'Missing opaque source role')
                guard();mesh.set_material(index,material)
            for record in records:
                info=inventory[files[record['file']]['source_object']]
                report['slot_checks'].append(inspect_slots(U,mesh,record['index'],info['material_slots'],opaque,info['triangles']))
            persist(mesh)
        guard();require(len(report['packages'])==50,'Incomplete exact50 save set')
        report['passed']=True
        return report
    except BaseException as error:
        report['error']=repr(error)
        raise
    finally:
        emit_receipt(report)  # Preserve partial-save evidence; never silently rerun.
