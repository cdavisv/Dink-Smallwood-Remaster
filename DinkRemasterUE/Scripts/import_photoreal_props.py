"""Staged UE commandlet only. DINK_PROPS_MODE=preflight|import|verify (defaultpreflight).
Source bundle is immutable. No runtime publication. Verify never saves assets.
"""
import hashlib,json,math,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import props_contract as C


def main():
    import unreal as U
    C.require('-game' not in U.SystemLibrary.get_command_line().split(), 'Editor commandlet required')
    root=Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()
    source=Path(os.environ.get('DINK_PROPS_SOURCE',str(root/'SourceAssets/Art/Stonebrook/Refinements/PhotorealPropsV1'))).resolve()
    mode=os.environ.get('DINK_PROPS_MODE','preflight');C.require(mode in {'preflight','import','verify'},'Mode')
    output=Path(os.environ.get('DINK_PROPS_REPORT',str(root/'Saved/Art'/('photoreal_props_'+mode+'.json')))).resolve()
    C.require(output.is_relative_to(root/'Saved'),'Receipt must stay in owned project Saved')
    C.require_owned_content(root)
    plan=C.load_plan(source); tools=C.tool_pins(Path(__file__).parent)
    L=U.EditorAssetLibrary;E=U.MaterialEditingLibrary;T=U.AssetToolsHelpers.get_asset_tools()
    S=U.get_default_object(U.StaticMeshEditorSubsystem)
    required=C.packages(plan);expected=C.candidate_files(plan); all_before=C.pins(root,'Content'); data_before=C.pins(root,'Content/Dink/Data')
    existing=[a for a in expected if (root/a).exists()]
    if mode=='verify':C.require(required.issubset(existing),'Candidate package set incomplete')
    else:C.require(not existing and all(not L.does_asset_exist(p)for a in plan['assets']for p in [a['mesh'],a['material']]+list(a['textures'].values())),'Refusing existing candidate packages')
    house=json.loads((root/C.HOUSE).read_text())
    priorpath=Path(os.environ.get('DINK_PROPS_IMPORT_RECEIPT',str(root/'Saved/Art/photoreal_props_import.json')))
    context=C.verification_context(root,plan,house,all_before,data_before,mode,priorpath)
    baseline_packages={}; baseline_native={}
    for a in plan['assets']:
        package=a['old'].split('.')[0];mesh=U.load_asset(package);C.require(isinstance(mesh,U.StaticMesh),'Old baseline missing')
        C.require(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')==U.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,'Baseline collision policy changed')
        C.require(len(mesh.get_editor_property('static_materials'))==(2 if 'Chair'not in a['name']else 1),'Old material-slot baseline changed')
        relative=C.package_file(package);baseline_packages[relative]=C.sha(root/relative)
        desc=mesh.get_static_mesh_description(0);C.require(desc is not None,'Old geometry unavailable')
        C.require(desc.get_triangle_count()=={'SM_Table_Oak_01':2264,'SM_Bed_Oak_01':7744,'SM_Chair_Oak_01':1728}[a['name']],'Original baseline triangle count')
        expected_old={'SM_Table_Oak_01':[265,149.8,90.6],'SM_Bed_Oak_01':[251,137,112],'SM_Chair_Oak_01':[65,53.75,100.5]}[a['name']]
        actual_old=[mesh.get_bounds().box_extent.x*2,mesh.get_bounds().box_extent.y*2,mesh.get_bounds().box_extent.z*2]
        C.require(all(abs(x-y)<.05 for x,y in zip(expected_old,actual_old)),'Original baseline dimensions')
        expected_materials=['MI_Stonebrook_Oak']+(['MI_Stonebrook_WroughtIron']if 'Table'in a['name']else ['MI_Stonebrook_Linen']if 'Bed'in a['name']else [])
        C.require([mesh.get_material(i).get_path_name().rsplit('/',1)[1].split('.')[0]for i in range(len(expected_materials))]==expected_materials,'Original baseline material identity')
        baseline_native[a['name']]={'triangles':desc.get_triangle_count(),'body':mesh.get_editor_property('body_setup').get_editor_property('agg_geom').export_text(),'bounds':[mesh.get_bounds().box_extent.x*2,mesh.get_bounds().box_extent.y*2,mesh.get_bounds().box_extent.z*2]}
    report={'schema':C.SCHEMA,'passed':False,'mode':mode,'project':str(root),'source':str(source),
        'plan':plan,'plan_sha256':C.canonical_hash(plan),'tool_sha256':tools,'runtime_data_sha256':data_before,
        'baseline_package_sha256':baseline_packages,'baseline_native':baseline_native,'verified_old_baseline':True,'house_baseline_semantic_sha256':C.canonical_hash(house),
        'runtime_manifest_published':False,'publication_state':context['publication_state'],'verification_basis':context['verification_basis'],'scene_data_approval':False,'verification_scope':'saved_props_assets_with_current_pinned_Data_context','writer_scope':'none' if context['publication_state']=='published' else 'eight_mesh_paths_after_separate_publication_guard','normal_contract':'preserve FBX normals; generate MikkTSpace tangents (FBX has no exported tangents)',
        'collision_policy':'existing complex-as-simple; authored UCX retained and verified, not active query source'}
    prior=context['prior']
    candidate_baseline=context['entry_package_sha256']
    if prior is not None:
        priorpath=priorpath.resolve()
        for key in ['plan_sha256','tool_sha256','runtime_data_sha256','baseline_package_sha256','baseline_native','house_baseline_semantic_sha256']:
            C.require(prior[key]==report[key],'Import-to-verify drift: '+key)
        C.require(C.pins(root,'Content')==dict(prior['protected_content_sha256'],**prior['saved_package_sha256']),'Saved Content set/hash drift since import')
        report['import_receipt_sha256']=C.sha(priorpath)
    if mode=='verify':C.verify_candidate_packages(root,plan,candidate_baseline)
    protected={p:h for p,h in all_before.items()if p not in expected}
    report['protected_content_sha256']=protected
    def guards():
        C.require(C.load_plan(source,check_pixels=False)==plan,'Source changed during commandlet')
        C.require(C.tool_pins(Path(__file__).parent)==tools,'Tool changed during commandlet')
        C.require(C.pins(root,'Content/Dink/Data')==data_before,'Runtime Data changed')
        actual=C.pins(root,'Content');C.require({p:h for p,h in actual.items()if p not in expected}==protected,'Protected Content set/hash changed')
        if prior is not None:
            C.require(C.sha(priorpath)==report['import_receipt_sha256'],'Import receipt changed during verification')
        if mode=='verify':C.verify_candidate_packages(root,plan,candidate_baseline)
    def save(asset):
        package=asset.get_path_name().split('.')[0];C.require(C.package_file(package)in expected,'Save outside candidate scope')
        guards();C.require(L.save_loaded_asset(asset,only_if_is_dirty=False),'Save failed')
    def imp(file,package,options=None):
        guards();C.require(C.package_file(package)in expected and not L.does_asset_exist(package),'Import destination exists/outside scope')
        task=U.AssetImportTask();task.filename=str(C.inside(source,file));task.destination_path,task.destination_name=package.rsplit('/',1)
        task.automated=True;task.replace_existing=False;task.save=False
        if options is not None:task.options=options;task.factory=U.FbxFactory()
        T.import_asset_tasks([task]);C.require(set(task.imported_object_paths)=={C.object_path(package)},'Unexpected import objects')
        result=U.load_asset(package);C.require(result is not None,'Import missing');return result
    def recipe(material,a):
        C.require(material.get_editor_property('blend_mode')==U.BlendMode.BLEND_OPAQUE and not material.get_editor_property('two_sided'),'Material surface')
        C.require(not material.get_editor_property('use_material_attributes') and material.get_editor_property('tangent_space_normal'),'Material model')
        C.require(material.get_editor_property('shading_model')==U.MaterialShadingModel.MSM_DEFAULT_LIT and material.get_editor_property('used_with_nanite'),'Material shading/Nanite')
        expected_inputs=[('BC','RGB',U.MaterialProperty.MP_BASE_COLOR),('N','RGB',U.MaterialProperty.MP_NORMAL),('ORM','R',U.MaterialProperty.MP_AMBIENT_OCCLUSION),('ORM','G',U.MaterialProperty.MP_ROUGHNESS),('ORM','B',U.MaterialProperty.MP_METALLIC)]
        nodes=set();approved=set()
        for channel,channelout,prop in expected_inputs:
            node=E.get_material_property_input_node(material,prop);C.require(type(node)is U.MaterialExpressionTextureSample,'Non-direct material input')
            C.require(node.get_editor_property('texture').get_path_name()==C.object_path(a['textures'][channel]),'Texture reference')
            sampler={'BC':U.MaterialSamplerType.SAMPLERTYPE_COLOR,'N':U.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':U.MaterialSamplerType.SAMPLERTYPE_MASKS}[channel]
            C.require(node.get_editor_property('sampler_type')==sampler and node.get_editor_property('const_coordinate')==0,'Sampler/UV')
            C.require(not any(E.get_inputs_for_material_expression(material,node)),'Hidden UV/mip input')
            C.require(E.get_material_property_input_node_output_name(material,prop)==channelout,'Wrong material output channel')
            nodes.add(node.get_path_name());approved.add(prop.value)
        constant=E.get_material_property_input_node(material,U.MaterialProperty.MP_SPECULAR)
        C.require(type(constant)is U.MaterialExpressionConstant and abs(constant.get_editor_property('r')-.35)<1e-6,'Specular must be direct.35')
        C.require(E.get_material_property_input_node_output_name(material,U.MaterialProperty.MP_SPECULAR)=='','Specular output')
        nodes.add(constant.get_path_name());approved.add(U.MaterialProperty.MP_SPECULAR.value)
        C.require({n.get_path_name()for n in E.get_material_expressions(material)}==nodes,'Extra material expression')
        C.require(set(U.DinkMaterialArtLibrary.get_connected_material_properties(material))==approved,'Hidden material property input')
        return {'direct_BC_N_ORM':True,'specular':.35,'all_native_material_property_ids_checked':sorted(approved)}
    def create_material(a,textures):
        folder,name=a['material'].rsplit('/',1);mat=T.create_asset(name,folder,U.Material,U.MaterialFactoryNew());C.require(isinstance(mat,U.Material),'Material creation')
        mat.set_editor_property('two_sided',False);mat.set_editor_property('blend_mode',U.BlendMode.BLEND_OPAQUE)
        nodes={}
        for role in C.ROLES:
            node=E.create_material_expression(mat,U.MaterialExpressionTextureSample);node.set_editor_property('texture',textures[role]);node.set_editor_property('const_coordinate',0)
            node.set_editor_property('sampler_type',{'BC':U.MaterialSamplerType.SAMPLERTYPE_COLOR,'N':U.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':U.MaterialSamplerType.SAMPLERTYPE_MASKS}[role]);nodes[role]=node
        for role,out,prop in [('BC','RGB',U.MaterialProperty.MP_BASE_COLOR),('N','RGB',U.MaterialProperty.MP_NORMAL),('ORM','R',U.MaterialProperty.MP_AMBIENT_OCCLUSION),('ORM','G',U.MaterialProperty.MP_ROUGHNESS),('ORM','B',U.MaterialProperty.MP_METALLIC)]:C.require(E.connect_material_property(nodes[role],out,prop),'Material link')
        scalar=E.create_material_expression(mat,U.MaterialExpressionConstant);scalar.set_editor_property('r',.35);C.require(E.connect_material_property(scalar,'',U.MaterialProperty.MP_SPECULAR),'Specular link')
        E.set_base_material_usage(mat,U.MaterialUsage.MATUSAGE_NANITE,True);E.recompile_material(mat);recipe(mat,a);save(mat);return mat
    def source_filename(asset,relative):
        imported=asset.get_editor_property('asset_import_data')
        C.require(isinstance(imported,U.AssetImportData),'Native import metadata missing')
        return C.validate_native_source_filename(source,relative,imported.extract_filenames(),plan['source_sha256'][relative])
    def read_mesh(mesh,a):
        desc=mesh.get_static_mesh_description(0);C.require(desc is not None,'Mesh description unavailable')
        points=[]
        for i in range(desc.get_vertex_count()):
            v=desc.get_vertex_position(U.VertexID(id_value=i));points.append([float(v.x),float(v.y),float(v.z)])
        low=[min(p[k]for p in points)for k in range(3)];high=[max(p[k]for p in points)for k in range(3)]
        for actual,expected_bound in [(low,a['bounds_cm']['unreal_min_cm']),(high,a['bounds_cm']['unreal_max_cm'])]:C.require(all(abs(x-y)<.05 for x,y in zip(actual,expected_bound)),'Bounds/pivot mismatch')
        triangles=[];groups=set()
        for i in range(desc.get_triangle_count()):
            tid=U.TriangleID(id_value=i);groups.add(int(desc.get_triangle_polygon_group(tid).get_editor_property('id_value')));corners=[]
            for vi in desc.get_triangle_vertex_instances(tid):
                vertex=desc.get_vertex_instance_vertex(vi);uv=desc.get_vertex_instance_uv(vi,0);corners.append((points[int(vertex.get_editor_property('id_value'))],[float(uv.x),float(uv.y)],[0,0,0]))
            triangles.append(corners)
        C.require(len(triangles)==a['triangles'] and groups=={0},'Triangle/material-group mismatch')
        raw_source=C.source_triangles(source,a,include_authored_normals=True)
        try:matching=C.match_oriented_triangles(triangles,raw_source)
        except ValueError:
            diagnostics=output.parent/'SignatureDiagnostics';diagnostics.mkdir(parents=True,exist_ok=True)
            (diagnostics/(a['name']+'.json')).write_text(json.dumps({'native_triangles':triangles,'expected_authored_source_triangles':raw_source},indent=2)+'\n')
            raise
        native_signature=C.triangle_signature([[(p,uv,[0,0,0])for p,uv,n in t]for t in raw_source])
        front_normals=C.verify_native_front_normals(triangles,raw_source,matching)
        slots=list(mesh.get_editor_property('static_materials'));C.require(len(slots)==1 and mesh.get_material(0).get_path_name()==C.object_path(a['material']),'One baked material slot required')
        build=S.get_lod_build_settings(mesh,0);C.require(not build.get_editor_property('recompute_normals') and build.get_editor_property('recompute_tangents') and build.get_editor_property('use_mikk_t_space'),'Normals/tangents flags')
        imported=mesh.get_editor_property('asset_import_data');C.require(isinstance(imported,U.FbxStaticMeshImportData),'Legacy FBX import data')
        C.require(imported.get_editor_property('normal_import_method')==U.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,'Source normals import method')
        C.require(not imported.get_editor_property('force_front_x_axis') and not imported.get_editor_property('auto_generate_collision') and imported.get_editor_property('one_convex_hull_per_ucx'),'Saved custom collision/axes options')
        C.require(imported.get_editor_property('convert_scene') and imported.get_editor_property('convert_scene_unit') and abs(imported.get_editor_property('import_uniform_scale')-1)<1e-7,'Saved FBX unit settings')
        nanite=mesh.get_editor_property('nanite_settings');C.require(nanite.get_editor_property('enabled') and abs(nanite.get_editor_property('fallback_percent_triangles')-1)<1e-7 and nanite.get_editor_property('fallback_relative_error')==0,'Nanite fallback')
        C.require(nanite.get_editor_property('fallback_target')==U.NaniteFallbackTarget.PERCENT_TRIANGLES and S.get_lod_count(mesh)==1,'Nanite/LOD policy')
        body=mesh.get_editor_property('body_setup');C.require(body.get_editor_property('collision_trace_flag')==U.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,'Collision policy changed')
        agg=body.get_editor_property('agg_geom');hulls=list(agg.get_editor_property('convex_elems'));C.require(len(hulls)==a['hulls'] and S.get_convex_collision_count(mesh)==a['hulls'],'UCX count')
        for prop in ['sphere_elems','box_elems','sphyl_elems','tapered_capsule_elems']:C.require(not agg.get_editor_property(prop),'Unexpected analytic collider')
        snapshots=list(U.DinkMaterialArtLibrary.inspect_static_mesh_convex_collision(mesh))
        C.require(len(snapshots)==len(hulls),'Native convex bridge count')
        clouds=[];bridge=[]
        for snapshot in snapshots:
            vertices=[[float(v.x),float(v.y),float(v.z)]for v in snapshot.get_editor_property('mesh_vertices')]
            indices=list(snapshot.get_editor_property('indices'))
            C.validate_convex_points(vertices);C.validate_closed_indices(vertices,indices)
            clouds.append(sorted(tuple(round(x/.01)for x in p)for p in vertices))
            bridge.append({'transform':snapshot.get_editor_property('local_to_mesh').export_text(),'mesh_vertices':vertices,'indices':indices})
        raw_clouds=[row['mesh_vertices']for row in bridge];source_clouds=C.source_hulls(source,a,include_points=True)
        cloud_diagnostic=output.parent/'UCXDiagnostics';cloud_diagnostic.mkdir(parents=True,exist_ok=True)
        try:cloud_match=C.match_convex_clouds(raw_clouds,source_clouds)
        except ValueError as error:
            (cloud_diagnostic/(a['name']+'.json')).write_text(json.dumps({'actual_bridge':bridge,'source_clouds':source_clouds,'error':repr(error)},indent=2)+'\n')
            raise
        (cloud_diagnostic/(a['name']+'.json')).write_text(json.dumps({'actual_bridge':bridge,'source_clouds':source_clouds,'match':cloud_match},indent=2)+'\n')
        return {'bounds_min_cm':low,'bounds_max_cm':high,'triangles':len(triangles),'material_polygon_groups':sorted(groups),'geometry_uv0_sha256':C.canonical_hash(native_signature),'native_geometry_uv0_exact_sha256':C.canonical_hash(triangles),'oriented_source_match':matching['summary'],'UCX_hulls':len(hulls),'UCX_vertex_cloud_sha256':C.canonical_hash(C.source_hulls(source,a)),'native_UCX_vertex_cloud_exact_sha256':C.canonical_hash(raw_clouds),'convex_source_match':cloud_match,'native_convex_bridge':bridge,'native_source_filename':source_filename(mesh,a['fbx']),'aggregate_geometry_export':agg.export_text(),'native_front_normal_evidence':front_normals,'source_normals_imported_and_Mikk_tangents_generated':True,'collision_policy':'complex-as-simple'}
    try:
        if mode=='import':
            world=U.get_editor_subsystem(U.UnrealEditorSubsystem).get_editor_world();U.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
            C.require(U.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')==0,'Cannot select legacy FBX')
            for a in plan['assets']:
                textures={}
                for role in C.ROLES:
                    tex=imp(a['texture_files'][role],a['textures'][role]);C.require(isinstance(tex,U.Texture2D),'Texture type')
                    tex.set_editor_property('srgb',role=='BC');tex.set_editor_property('flip_green_channel',role=='N')
                    tex.set_editor_property('compression_settings',{'BC':U.TextureCompressionSettings.TC_DEFAULT,'N':U.TextureCompressionSettings.TC_NORMALMAP,'ORM':U.TextureCompressionSettings.TC_MASKS}[role]);save(tex);textures[role]=tex
                mat=create_material(a,textures)
                ui=U.FbxImportUI()
                for key,value in {'automated_import_should_detect_type':False,'mesh_type_to_import':U.FBXImportType.FBXIT_STATIC_MESH,'import_mesh':True,'import_materials':False,'import_textures':False,'import_animations':False}.items():ui.set_editor_property(key,value)
                opts=ui.static_mesh_import_data
                for key,value in {'combine_meshes':True,'import_mesh_lods':False,'remove_degenerates':False,'normal_import_method':U.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,'auto_generate_collision':False,'one_convex_hull_per_ucx':True,'generate_lightmap_u_vs':False,'convert_scene':True,'convert_scene_unit':True,'force_front_x_axis':False,'import_uniform_scale':1.0}.items():opts.set_editor_property(key,value)
                mesh=imp(a['fbx'],a['mesh'],ui);C.require(isinstance(mesh,U.StaticMesh),'Mesh type')
                build=S.get_lod_build_settings(mesh,0)
                for key,value in {'recompute_normals':False,'recompute_tangents':True,'use_mikk_t_space':True,'remove_degenerates':False,'generate_lightmap_u_vs':False}.items():build.set_editor_property(key,value)
                S.set_lod_build_settings(mesh,0,build);mesh.set_material(0,mat)
                mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',U.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                nanite=mesh.get_editor_property('nanite_settings')
                for key,value in {'enabled':True,'fallback_target':U.NaniteFallbackTarget.PERCENT_TRIANGLES,'fallback_percent_triangles':1.0,'fallback_relative_error':0.0}.items():nanite.set_editor_property(key,value)
                mesh.set_editor_property('nanite_settings',nanite);read_mesh(mesh,a);save(mesh)
        if mode in {'import','verify'}:
            report['native_assets']={};report['material_recipes']={};report['native_texture_source_pixels']={};report['native_source_filenames']={}
            for a in plan['assets']:
                report['native_assets'][a['name']]=read_mesh(U.load_asset(a['mesh']),a);report['material_recipes'][a['name']]=recipe(U.load_asset(a['material']),a)
                report['native_source_filenames'][a['name']+'/FBX']=source_filename(U.load_asset(a['mesh']),a['fbx'])
                for role in C.ROLES:
                    tex=U.load_asset(a['textures'][role]);C.require(isinstance(tex,U.Texture2D),'Saved texture type')
                    report['native_source_filenames'][a['name']+'/'+role]=source_filename(tex,a['texture_files'][role])
                    C.require(tex.blueprint_get_size_x()==2048 and tex.blueprint_get_size_y()==2048,'Saved texture resolution')
                    C.require(tex.get_editor_property('srgb')==(role=='BC') and tex.get_editor_property('flip_green_channel')==(role=='N'),'Saved texture color/normal flags')
                    C.require(tex.get_editor_property('compression_settings')=={'BC':U.TextureCompressionSettings.TC_DEFAULT,'N':U.TextureCompressionSettings.TC_NORMALMAP,'ORM':U.TextureCompressionSettings.TC_MASKS}[role],'Saved texture compression')
                    diagnostic=root/'Saved/Art/PhotorealPropsTextureSource'/mode/(tex.get_name()+'.png');diagnostic.parent.mkdir(parents=True,exist_ok=True)
                    task=U.AssetExportTask();task.object=tex;task.filename=str(diagnostic);task.exporter=U.TextureExporterPNG();task.automated=True;task.prompt=False;task.replace_identical=True
                    C.require(U.Exporter.run_asset_export_task(task),'Read-only texture source export failed')
                    decoded=C.png_rgb(diagnostic);original=C.png_rgb(C.inside(source,a['texture_files'][role]));C.require(decoded==original,'Saved Texture.Source pixels differ from frozen source')
                    report['native_texture_source_pixels'][a['name']+'/'+role]=hashlib.sha256(decoded[2]).hexdigest()

            if prior:C.require(report['native_assets']==prior['native_assets'] and report['material_recipes']==prior['material_recipes'] and report['native_texture_source_pixels']==prior['native_texture_source_pixels'] and report['native_source_filenames']==prior['native_source_filenames'],'Saved native data changed since import')
            report['saved_package_sha256']=(C.verify_candidate_packages(root,plan,candidate_baseline) if mode=='verify' else C.candidate_package_pins(root,plan))
        guards();report['protected_changes']=[];report['runtime_data_changes']=[];report['passed']=True
    except Exception as error:
        report['error']=repr(error);raise
    finally:
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print('PHOTOREAL PROPS '+mode.upper()+' PASS; runtime publication not performed')


if __name__=='__main__':main()
