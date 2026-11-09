"""Private editor-only VistaV3 importer/checker. Never publishes Data or ledger rows.
Modes: import, check(default), resume(explicit unpublished-only, with backups).
DINK_VISTA_SOURCE points to the immutable reviewed139-file source bundle.
"""
import json,os,sys,shutil,time
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
sys.path.insert(0,str(ROOT/'Scripts'))
from vista_import_support import DEST,DEST_ROOTS,package_file,sha,validate_bundle,validate_material_usage,render_policy,is_published,action,material_reference,asset_file

def main():
    if '-game' in unreal.SystemLibrary.get_command_line().lower().split():raise ValueError('Use an editor commandlet')
    source=Path(os.environ.get('DINK_VISTA_SOURCE',str(ROOT/'SourceAssets/Art/Stonebrook/InteriorVistaV3'))).resolve()
    mode=os.environ.get('DINK_VISTA_MODE','check')
    report={'passed':False,'mode':mode,'destination_roots':DEST_ROOTS,'runtime_manifest_written':False,'ledger_written':False,'assets':[]}
    protected={}
    try:
        # The pinned manifest AND every139 payload must match before any editor write.
        spec,proposal,bundle_sha=validate_bundle(source)
        report['source_bundle_sha256']=bundle_sha
        lib=unreal.EditorAssetLibrary;edit=unreal.MaterialEditingLibrary
        tools=unreal.AssetToolsHelpers.get_asset_tools()
        sub=(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
        if sub is None:raise ValueError('StaticMeshEditorSubsystem unavailable in editor commandlet')
        operation=action(mode,any(lib.does_directory_exist(prefix) for prefix in DEST_ROOTS),is_published(ROOT/'Content/Dink/Data/Art'))
        report['operation']=operation
        owned_packages={package_file(ROOT,a) for a in spec['assets']}
        for p in (ROOT/'Content').rglob('*'):
            if p.is_file() and p.suffix in ['.uasset','.umap'] and p not in owned_packages:protected[str(p)]=sha(p)
        protected.update({str(p):sha(p) for p in (ROOT/'Content/Dink/Data').rglob('*') if p.is_file()})
        ledger=ROOT/'SourceAssets/asset_ledger.csv';protected[str(ledger)]=sha(ledger)
        new_paths={a['content_path']+'.'+a['name'] for a in spec['assets']}
        for path in set(r['asset_path_proposal'] for r in proposal['instances'])-new_paths:
            if not asset_file(ROOT,path).is_file():raise ValueError('Missing shared mesh package file: '+path)
            if not isinstance(lib.load_asset(path),unreal.StaticMesh):raise ValueError('Missing shared mesh: '+path)
        material_paths={row['name']:material_reference(row['existing_UE_material']) for row in proposal['new_meshes']}
        report['material_reference_corrections']={row['existing_UE_material']:material_reference(row['existing_UE_material']) for row in proposal['new_meshes'] if row['existing_UE_material']!=material_reference(row['existing_UE_material'])}
        materials={};chains={}
        # Required for BOTH import and check; resolve MIC parents read-only to UMaterial.
        for path in sorted(set(material_paths.values())):
            if not asset_file(ROOT,path).is_file():raise ValueError('Missing shared material package file: '+path)
            material=lib.load_asset(path)
            if material is None:raise ValueError('Missing shared material: '+path)
            _,chain=validate_material_usage(material,unreal.Material,edit.has_material_usage,unreal.MaterialUsage.MATUSAGE_NANITE)
            materials[path]=material;chains[path]=chain
        report['shared_material_chains']=chains
        if operation=='resume':
            backup=ROOT/'Saved/Art/VistaResumeBackups'/str(time.time_ns());backup.mkdir(parents=True)
            copied={}
            # Only the55 reviewed private packages/sidecars; never remove unrelated files.
            for asset in spec['assets']:
                for suffix in ['.uasset','.uexp','.ubulk']:
                    path=package_file(ROOT,asset).with_suffix(suffix)
                    if path.exists():
                        if path.is_symlink() or not path.is_file():raise ValueError('Nonregular candidate package: '+str(path))
                        digest=sha(path);shutil.copy2(path,backup/path.name)
                        if sha(backup/path.name)!=digest or sha(path)!=digest:raise ValueError('Candidate changed while backing up: '+str(path))
                        copied[path.name]=digest
            (backup/'backup_manifest.json').write_text(json.dumps(copied,indent=2)+'\n')
            report['resume_backup']=str(backup);report['backup_hashes']=copied
        if operation in ['create','resume']:
            world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
            if unreal.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')!=0:raise ValueError('Legacy FBX importer unavailable')
            for asset in spec['assets']:
                options=unreal.FbxImportUI()
                options.set_editor_property('automated_import_should_detect_type',False)
                options.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
                for key,value in [('import_mesh',True),('import_materials',False),('import_textures',False),('import_animations',False)]:options.set_editor_property(key,value)
                opts=options.static_mesh_import_data
                for key,value in [('combine_meshes',True),('auto_generate_collision',False),('import_mesh_lods',False),('generate_lightmap_u_vs',False),('convert_scene',True),('convert_scene_unit',True),('force_front_x_axis',False),('import_uniform_scale',1.),('one_convex_hull_per_ucx',True)]:opts.set_editor_property(key,value)
                opts.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
                task=unreal.AssetImportTask();task.filename=str(source/'Export'/asset['files']['fbx']);task.destination_path=asset['content_path'].rsplit('/',1)[0];task.destination_name=asset['name'];task.automated=True
                task.replace_existing=operation=='resume';task.replace_existing_settings=operation=='resume';task.save=False;task.options=options;task.factory=unreal.FbxFactory()
                tools.import_asset_tasks([task]);mesh=lib.load_asset(asset['content_path'])
                if not isinstance(mesh,unreal.StaticMesh):raise ValueError('Missing imported mesh: '+asset['name'])
                slots=list(mesh.get_editor_property('static_materials'))
                if len(slots)!=1:raise ValueError('Expected one material slot: '+asset['name'])
                slots[0].set_editor_property('material_interface',materials[material_paths[asset['name']]])
                mesh.set_editor_property('static_materials',slots)
                settings=mesh.get_editor_property('nanite_settings')
                for key,value in [('enabled',True),('fallback_target',unreal.NaniteFallbackTarget.PERCENT_TRIANGLES),('fallback_percent_triangles',1.),('fallback_relative_error',0.)]:settings.set_editor_property(key,value)
                mesh.set_editor_property('nanite_settings',settings)
                build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True);sub.set_lod_build_settings(mesh,0,build)
                if not lib.save_loaded_asset(mesh,only_if_is_dirty=False):raise ValueError('Failed saving unique Vista mesh')
        for asset in spec['assets']:
            mesh=lib.load_asset(asset['content_path'])
            if not isinstance(mesh,unreal.StaticMesh):raise ValueError('Missing Vista mesh: '+asset['name'])
            expected_triangles=asset['tris']['LOD0']
            if sub.get_lod_count(mesh)!=1 or mesh.get_num_triangles(0)!=expected_triangles:raise ValueError('Vista fallback LOD count/triangles mismatch')
            render_policy(mesh.get_editor_property('nanite_settings'),unreal.NaniteFallbackTarget.PERCENT_TRIANGLES,expected_triangles,mesh.get_num_nanite_triangles())
            description=mesh.get_static_mesh_description(0)
            if description is None or description.get_triangle_count()!=expected_triangles:raise ValueError('Vista source geometry triangles mismatch')
            points=[]
            for i in range(description.get_vertex_count()):
                vertex=unreal.VertexID(id_value=i)
                if not description.is_vertex_valid(vertex):raise ValueError('Unexpected sparse vertex IDs')
                q=description.get_vertex_position(vertex);points.append([q.x,q.y,q.z])
            low=[min(q[k] for q in points) for k in range(3)];high=[max(q[k] for q in points) for k in range(3)]
            expected=asset['bounds_cm']
            if not all(abs(low[k]-expected['unreal_min_cm'][k])<.05 and abs(high[k]-expected['unreal_max_cm'][k])<.05 for k in range(3)):raise ValueError('Imported vertex bounds mismatch: '+asset['name'])
            if mesh.get_material(0)!=materials[material_paths[asset['name']]]:raise ValueError('Unexpected shared material binding')
            report['assets'].append({'name':asset['name'],'source_content_path':asset['content_path'],'imported_object':mesh.get_path_name(),'triangles':expected_triangles,'actual_nanite_triangles':mesh.get_num_nanite_triangles(),'vertex_min_cm':low,'vertex_max_cm':high,'source_ucx_hulls':sub.get_convex_collision_count(mesh),'runtime_policy':'NoCollision actor/components; source UCX never activated','fallback_percent':1.,'fallback_relative_error':0.})
        if sum(a['triangles'] for a in report['assets'])!=17604:raise ValueError('Vista triangle inventory mismatch')
        report['passed']=True
    except Exception as error:
        report['error']=str(error);raise
    finally:
        changed=[path for path,digest in protected.items() if not Path(path).is_file() or sha(path)!=digest]
        if changed:report['passed']=False;report['protected_changes']=changed
        out=ROOT/'Saved/Art/interior_vista_import_check.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
        if changed:raise ValueError('Shared asset/Data/ledger changed: '+str(changed))
    print('INTERIOR VISTA55 IMPORT/CHECK PASS; Data and ledger unchanged')

if __name__=='__main__':main()
