"""Read-only capture-first actual render buffers for every mesh/LOD before matching.
FProc flipY is reported API output, never proof of stored determinant/handedness.
"""
import math
from native_collision_readback_v11 import capture_collision
FLAGS=['use_full_precision_u_vs','recompute_normals','recompute_tangents','use_mikk_t_space','remove_degenerates','generate_lightmap_u_vs']

def finite(values):return all(math.isfinite(v) for v in values)
def vector(value):return [float(value.x),float(value.y),float(value.z)]
def length(v):return math.sqrt(sum(x*x for x in v))
def json_safe(value):
    if isinstance(value,float) and not math.isfinite(value):return {'nonfinite':repr(value)}
    if isinstance(value,list):return [json_safe(v) for v in value]
    if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
    return value

def section(U,mesh,lod,index,subsystem):
    out=U.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,lod,index)
    if not isinstance(out,tuple) or len(out)!=5:raise ValueError('Unexpected actual builtin section signature')
    positions,indices,normals,uvs,tangents=out
    data={'section':index,'indices':list(indices),'positions_cm':[vector(p) for p in positions],
          'normals':[vector(n) for n in normals],'UV0':[[float(u.x),float(u.y)] for u in uvs],
          'tangentX':[vector(t.get_editor_property('tangent_x')) for t in tangents],
          'reported_FProc_flipY':[bool(t.get_editor_property('flip_tangent_y')) for t in tangents],
          'tangent_sign_qualification':'Builtin derives flip from TangentX.W; stored sign lives in TangentZ.W. Reported flip is not stored handedness.'}
    slot=subsystem.get_lod_material_slot(mesh,lod,index);material=mesh.get_material(slot)
    data.update(material_slot=slot,material_path=material.get_path_name() if material else None)
    valid={i for i in data['indices'] if isinstance(i,int) and 0<=i<len(data['positions_cm'])}
    stats={'used_vertex_count':len(valid),'invalid_indices':sum(not isinstance(i,int) or i<0 or i>=len(data['positions_cm']) for i in data['indices']),
           'attribute_count_mismatch':len({len(data[k]) for k in ['positions_cm','normals','UV0','tangentX','reported_FProc_flipY']})!=1,
           'indices_not_triangular':len(data['indices'])%3!=0,'used_nonfinite':0,'used_missing_attributes':0,
           'used_zero_normal':0,'used_zero_tangentX':0,'used_zero_unsigned_cross':0,'max_abs_normalized_N_dot_T':0.}
    nl=[];tl=[];bl=[]
    for i in sorted(valid):
        if any(i>=len(data[k]) for k in ['normals','UV0','tangentX']):stats['used_missing_attributes']+=1;continue
        n,t=data['normals'][i],data['tangentX'][i]
        if not finite(data['positions_cm'][i]+data['UV0'][i]+n+t):stats['used_nonfinite']+=1;continue
        nlen,tlen=length(n),length(t);cross=[n[1]*t[2]-n[2]*t[1],n[2]*t[0]-n[0]*t[2],n[0]*t[1]-n[1]*t[0]];blen=length(cross)
        nl.append(nlen);tl.append(tlen);bl.append(blen)
        stats['used_zero_normal']+=nlen<=1e-4;stats['used_zero_tangentX']+=tlen<=1e-4;stats['used_zero_unsigned_cross']+=blen<=1e-4
        if nlen>1e-4 and tlen>1e-4:stats['max_abs_normalized_N_dot_T']=max(stats['max_abs_normalized_N_dot_T'],abs(sum(a*b for a,b in zip(n,t)))/(nlen*tlen))
    for name,values in [('normal_length',nl),('tangentX_length',tl),('unsigned_cross_length',bl)]:stats[name]={'min':min(values) if values else None,'max':max(values) if values else None}
    data['stats']=stats;return data

def capture_all(U,bindings,subsystem,guard,write_json):
    """write_json(relative_name, plain_data) must persist each file before returning."""
    result={'phase':'capture_all_actual_buffers_before_comparison','meshes':[],'actual_LOD_count':0,'strict_source_matchers_called':0,
            'scope':'Actual section buffers/used tangentX and unsigned cross magnitudes only; stored determinant and full TBN handedness unproven'}
    for mesh_index,binding in enumerate(bindings):
        guard();row={'package':binding['package'],'expected_LODs':len(binding['LODs']),'LODs':[]}
        try:
            mesh=U.load_asset(binding['package'])
            if not isinstance(mesh,U.StaticMesh):raise ValueError('Saved mesh missing or wrong class')
            collision_file=f'collision_{mesh_index:02}.json'
            try:collision_raw=capture_collision(U,mesh)
            except Exception as error:collision_raw={'package':binding['package'],'capture_error':repr(error)}
            write_json(collision_file,json_safe(collision_raw));row['raw_collision_file']=collision_file
            row['actual_LODs']=mesh.get_num_lods();row['allow_cpu_access']=bool(mesh.get_editor_property('allow_cpu_access'))
            for lod in range(row['actual_LODs']):
                capture={'package':binding['package'],'LOD':lod,'sections':[]}
                try:
                    try:
                        settings=subsystem.get_lod_build_settings(mesh,lod);capture['build_flags']={key:settings.get_editor_property(key) for key in FLAGS}
                    except Exception as error:capture['build_flags_error']=repr(error)
                    for index in range(mesh.get_num_sections(lod)):
                        try:capture['sections'].append(section(U,mesh,lod,index,subsystem))
                        except Exception as error:capture['sections'].append({'section':index,'capture_error':repr(error)})
                except Exception as error:capture['capture_error']=repr(error)
                filename=f'mesh_{mesh_index:02}_LOD{lod}.json';write_json(filename,json_safe(capture))
                summary={'LOD':lod,'raw_file':filename,'section_count':len(capture['sections']),'build_flags':capture.get('build_flags'),'build_flags_error':capture.get('build_flags_error'),
                         'section_stats':[s.get('stats',{'capture_error':s.get('capture_error')}) for s in capture['sections']]}
                if 'capture_error' in capture:summary['capture_error']=capture['capture_error']
                row['LODs'].append(summary);result['actual_LOD_count']+=1
        except Exception as error:row['capture_error']=repr(error)
        result['meshes'].append(row);write_json('capture_progress.json',json_safe(result))
    result['all_expected_meshes_visited']=len(result['meshes'])==len(bindings)
    write_json('capture_complete.json',json_safe(result))
    return result

def capture_failures(summary):
    """Call only AFTER all raw captures have been persisted."""
    failures=[]
    for mesh in summary['meshes']:
        if 'capture_error' in mesh:failures.append({'package':mesh['package'],'error':mesh['capture_error']});continue
        if mesh['actual_LODs']!=mesh['expected_LODs'] or not mesh['allow_cpu_access']:failures.append({'package':mesh['package'],'error':'LOD count/CPU access differs'})
        for lod in mesh['LODs']:
            for key in ['capture_error','build_flags_error']:
                if lod.get(key):failures.append({'package':mesh['package'],'LOD':lod['LOD'],'error':lod[key]})
            if not lod['section_count'] or not lod['section_stats']:failures.append({'package':mesh['package'],'LOD':lod['LOD'],'error':'Missing or empty sections'})
            for stats in lod['section_stats']:
                if 'used_vertex_count' in stats and not stats['used_vertex_count']:failures.append({'package':mesh['package'],'LOD':lod['LOD'],'error':'Empty used section'})
                bad={k:v for k,v in stats.items() if k in ['capture_error','invalid_indices','attribute_count_mismatch','indices_not_triangular','used_nonfinite','used_missing_attributes','used_zero_normal','used_zero_tangentX','used_zero_unsigned_cross'] and v}
                if bad:failures.append({'package':mesh['package'],'LOD':lod['LOD'],'evidence':bad})
    return failures
