"""Review-only fresh-process asset verification. No imports/setters/saves/launches.
Needs actual import receipt hashes, separately approved tolerances and guard functions.
"""
from pathlib import Path
import hashlib,json,math
from native_texture_tools_v11 import configure_and_verify
from native_material_readback_v12 import inspect_graph
from native_material_slots_v11 import inspect_slots
from native_built_buffer_reader_v11 import FLAGS
from native_collision_readback_v11 import inspect_collision
from geometry_only_match_v11 import compare
from native_import_metadata_v11 import inspect_sources
from relative_source_metadata import inspect_relative_sources
from audit_position_tolerance_v11 import source_triangles

def require(ok,message):
    if not ok:raise ValueError(message)

def source_hull_clouds(source_reference, render_name):
    # The frozen source snapshot uses the typed kind 'UCX'. Export resets object
    # locations; these are local mesh vertices, converted metres -> UE cm/Y.
    selected = {name: record for name, record in source_reference['objects'].items()
                if name.startswith('UCX_' + render_name + '_')}
    require(bool(selected), 'No authored UCX source records for ' + render_name)
    clouds = []
    for name, record in selected.items():
        require(record.get('kind') == 'UCX', 'Unexpected collision source kind: ' + name)
        points = record['vertices']
        require(bool(points) and all(len(v) == 3 and all(math.isfinite(x) for x in v) for v in points),
                'Invalid authored UCX vertices: ' + name)
        clouds.append([[v[0]*100, -v[1]*100, v[2]*100] for v in points])
    return clouds

def verify_saved_packages(root,proposal,expected_hashes):
    paths={'Content/'+a['package'].removeprefix('/Game/')+'.uasset' for a in proposal['packages']}
    require(len(paths)==50 and set(expected_hashes)==paths,'Exact50 actual import receipt hashes required')
    for relative,expected in expected_hashes.items():
        file=Path(root)/relative
        require(file.is_file() and not file.is_symlink() and file.stat().st_nlink==1,'Missing/aliased saved package')
        require(hashlib.sha256(file.read_bytes()).hexdigest()==expected,'Saved package changed: '+relative)
    return dict(expected_hashes)

def verify_assets(U,root,proposal,recipe,binding,source_reference,expected_hashes,approved_FP_nanite,tolerances,validators,guard,pixel_check,emit_receipt,captured_buffers,capture_summary,basis_failures):
    root=Path(root);packet=Path(binding['source_packet'])
    require(root.resolve()==root and root==Path(binding['project']),'Wrong project')
    require(all(callable(f) for f in [guard,pixel_check,emit_receipt]),'Reviewed callbacks required')
    require(set(tolerances)=={'position_cm','UV0','normal_component'} and all(math.isfinite(v) and v>0 for v in tolerances.values()),'Exact approved numeric tolerances required')
    require(approved_FP_nanite and approved_FP_nanite.get('enabled') is True and {'fallback_target','fallback_percent_triangles','fallback_relative_error'}<=approved_FP_nanite.keys(),'Complete original saved FP baseline required')
    before=verify_saved_packages(root,proposal,expected_hashes)
    report={'passed':False,'phase':'fresh_saved_asset_readback','packages':before,'textures':[],'materials':[],'meshes':[],'capture_summary':capture_summary,'basis_failures':basis_failures,'imports':0,'saves':0,'runtime_published':False}
    try:
        guard();manifest=json.loads((packet/'export_manifest.json').read_text())
        require(source_reference['source_sha256']==manifest['source']['sha256'],'Source reference differs')
        fbxs={r['file']:r for r in manifest['FBX']};texture_files={Path(r['file']).stem:r['file'] for r in manifest['textures']}
        packages={a['package']:a for a in proposal['packages']}
        roles={row['source_material']:row['opaque'] for row in recipe['materials']};reverse_roles={package:role for role,package in roles.items()}
        require(len(reverse_roles)==8,'Material package semantics ambiguous')
        for row in recipe['textures']:
            guard();asset=U.load_asset(row['package']);configure_and_verify(U,asset,row,guard)
            raw_relative=inspect_relative_sources(U,asset,[packet/row['source_file']],packet)
            pixels=pixel_check(asset,packet/texture_files[row['source_image']],row);pixels['raw_relative']=raw_relative;report['textures'].append(pixels)
        for row in recipe['materials']:
            for masked in [False,True]:
                target=row['masked' if masked else 'opaque']
                if target is None:continue
                guard();report['materials'].append(inspect_graph(U,U.load_asset(target),row,masked))
        S=U.get_default_object(U.StaticMeshEditorSubsystem);total_lods=total_hulls=total_triangles=0
        for row in binding['meshes']:
            guard();mesh=U.load_asset(row['package']);require(isinstance(mesh,U.StaticMesh),'Missing saved mesh')
            metadata_proof=inspect_sources(U,mesh,row['LODs'],packet)
            raw=captured_buffers[row['package']]
            require(len(raw)==len(row['LODs']),'Captured actual LOD count differs')
            lods=[]
            for capture in raw:
                require(not capture.get('capture_error') and capture.get('build_flags')==FLAGS,'Captured build flags/error differ')
                sections=[]
                for section in capture['sections']:
                    require(not section.get('capture_error'),'Actual section capture failed')
                    require(len(section['positions_cm'])==len(section['UV0'])==len(section['normals']),'Captured attribute counts differ')
                    vertices=[{'position_cm':p,'UV0':u,'normal':n} for p,u,n in zip(section['positions_cm'],section['UV0'],section['normals'])]
                    sections.append({'material_path':section['material_path'],'vertices':vertices,'indices':section['indices']})
                lods.append({'lod':capture['LOD'],'sections':sections})
            native={'LODs':lods};details=[]
            for record,actual in zip(row['LODs'],native['LODs']):
                source=source_reference['objects'][fbxs[record['file']]['source_object']]
                slot_proof=inspect_slots(U,mesh,record['index'],source['material_names'],roles,len(source['triangles']))
                triangles=[]
                for section in actual['sections']:
                    package=section['material_path'].split('.')[0];require(package in reverse_roles,'Unknown built section material')
                    for start in range(0,len(section['indices']),3):
                        corners=[section['vertices'][i] for i in section['indices'][start:start+3]]
                        triangles.append({'material':reverse_roles[package],'corners':corners})
                geometry=compare(triangles,source_triangles(source),tolerances['position_cm'],tolerances['UV0'],tolerances['normal_component'])
                details.append({'LOD':record['index'],'source_role_binding':slot_proof,'actual_built_geometry_UV_normals':geometry})
                total_lods+=1;total_triangles+=len(triangles)
            name=fbxs[row['LODs'][0]['file']]['source_object'];clouds=source_hull_clouds(source_reference,name)
            collision=inspect_collision(U,mesh,clouds,validators,tolerances['position_cm']);total_hulls+=len(clouds)
            policy=packages[row['package']]['collision_policy']
            flag={'SIMPLE_AND_COMPLEX':U.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX,'COMPLEX_AS_SIMPLE':U.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,'SIMPLE_AS_COMPLEX':U.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX}[policy['collision']]
            require(S.get_collision_complexity(mesh)==flag,'Saved collision policy differs')
            nanite=mesh.get_editor_property('nanite_settings')
            if policy['nanite'] is False:require(nanite.get_editor_property('enabled') is False,'Unexpected saved Nanite')
            else:
                for key,value in approved_FP_nanite.items():require(nanite.get_editor_property(key)==value,'Original FP Nanite policy differs: '+key)
            report['meshes'].append({'package':row['package'],'LODs':details,'collision':collision,'source_metadata':metadata_proof})
        require(total_lods==12 and total_hulls==312 and total_triangles==48090,'Whole asset set coverage incomplete')
        guard();verify_saved_packages(root,proposal,before)
        require(not basis_failures,'Actual used zero/nonfinite TBN frames: raw evidence retained, no appearance acceptance')
        report.update(passed=True,total_LODs=total_lods,total_hulls=total_hulls,total_triangles=total_triangles)
        return report
    except BaseException as error:
        report['error']=repr(error);raise
    finally:
        try:
            report['saved_packages_unchanged']=verify_saved_packages(root,proposal,before)==before
        except Exception as integrity_error:
            report['saved_packages_unchanged']=False
            report['integrity_error']=repr(integrity_error)
            report['passed']=False
        emit_receipt(report)
        require(report['saved_packages_unchanged'],'Saved package integrity failure during readback')
