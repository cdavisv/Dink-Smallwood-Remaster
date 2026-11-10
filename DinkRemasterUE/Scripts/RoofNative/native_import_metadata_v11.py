"""Read-only saved FBX settings and per-LOD original source-filename proof."""
from pathlib import Path
import hashlib,json
from relative_source_metadata import inspect_relative_sources

def require(ok,message):
    if not ok:raise ValueError(message)

def inspect_sources(U,mesh,records,packet):
    packet=Path(packet).resolve();metadata=mesh.get_editor_property('asset_import_data')
    require(isinstance(metadata,U.FbxStaticMeshImportData),'Saved legacy FBX metadata missing')
    expected={'normal_import_method':U.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
              'normal_generation_method':U.FBXNormalGenerationMethod.MIKK_T_SPACE,
              'auto_generate_collision':False,'one_convex_hull_per_ucx':True,
              'convert_scene':True,'convert_scene_unit':True,'force_front_x_axis':False,
              'import_uniform_scale':1.0,'transform_vertex_to_absolute':True,'bake_pivot_in_vertex':False,
              'combine_meshes':False,'import_mesh_lo_ds':False,'remove_degenerates':False,'generate_lightmap_u_vs':False}
    for key,value in expected.items():require(metadata.get_editor_property(key)==value,'Saved FBX setting differs: '+key)
    translation=metadata.get_editor_property('import_translation');rotation=metadata.get_editor_property('import_rotation')
    require([translation.x,translation.y,translation.z]==[0,0,0] and [rotation.pitch,rotation.yaw,rotation.roll]==[0,0,0],'Saved FBX transform differs')
    bridge=getattr(getattr(U,'DinkMaterialArtLibrary',None),'inspect_static_mesh_source_lods',None)
    require(callable(bridge),'Per-LOD filename snapshot API missing')
    data=json.loads(bridge(mesh))
    require(data.get('schema')=='dink-static-mesh-source-lods/1' and data.get('valid') is True and data.get('mesh')==mesh.get_path_name(),'Invalid LOD source snapshot')
    require(len(data['lods'])==len(records),'LOD source count differs')
    base=list(metadata.extract_filenames());require(len(base)==1,'Ambiguous LOD0 import filenames')
    rows=[]
    for record,actual in zip(records,data['lods']):
        require(actual['lod']==record['index'],'LOD source order differs')
        expected_file=(packet/record['file']).resolve();require(expected_file.is_relative_to(packet),'Source outside packet')
        require(expected_file.is_file() and hashlib.sha256(expected_file.read_bytes()).hexdigest()==record['sha256'],'Source filename payload changed')
        if record['index']==0:
            resolved=Path(base[0]).resolve();require(resolved==expected_file,'LOD0 references wrong original filename')
            require(not actual['resolved_source'] or Path(actual['resolved_source']).resolve()==expected_file,'Conflicting LOD0 source model filename')
        else:
            require(bool(actual['resolved_source']) and Path(actual['resolved_source']).resolve()==expected_file,'Explicit LOD references wrong original filename')
        rows.append({'LOD':record['index'],'source_file':str(expected_file),'sha256':record['sha256']})
    raw=inspect_relative_sources(U,mesh,[packet/r['file']for r in records],packet)
    return {'raw_relative':raw,'LODs':rows,'settings':{key:str(value) for key,value in expected.items()},'scope':'Saved original import metadata only; built geometry/UV/normal verification remains separate'}
