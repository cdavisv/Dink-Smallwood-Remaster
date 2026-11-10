"""Read-only per-LOD material semantics from actual imported slot-name bindings."""
import json

def require(ok,message):
    if not ok:raise ValueError(message)

def inspect_slots(U,mesh,lod,source_slots,role_packages,expected_triangles):
    require(len(source_slots)==len(set(source_slots)),'Source slots ambiguous')
    reader=getattr(getattr(U,'DinkMaterialArtLibrary',None),'inspect_static_mesh_material_bindings',None)
    require(callable(reader),'Read-only binding bridge missing')
    data=json.loads(reader(mesh,lod))
    require(data.get('schema')=='dink-static-mesh-material-bindings/1' and data.get('valid') is True,'Native binding snapshot invalid')
    require(data.get('mesh')==mesh.get_path_name() and data.get('lod')==lod,'Snapshot mesh/LOD mismatch')
    slots=data['slots'];groups=data['groups'];triangles=data['triangles']
    by_slot={row['slot_index']:row for row in slots}
    require(len(by_slot)==len(slots)==len(source_slots),'Native material slot count differs')
    require(set(by_slot)==set(range(len(slots))),'Invalid native material slot indices')
    require({row['imported_slot_name'] for row in slots}==set(source_slots),'Imported slot roles differ')
    require(len(mesh.get_editor_property('static_materials'))==len(slots),'Actual static material count differs')
    semantic={}
    for index,row in by_slot.items():
        role=row['imported_slot_name'];require(role in role_packages,'Unknown source semantic role')
        mat=mesh.get_material(index)
        require(mat is not None and mat.get_path_name().split('.')[0]==role_packages[role],'Actual slot uses wrong material package')
        semantic[index]=role
    by_group={row['polygon_group_id']:row for row in groups}
    require(len(by_group)==len(groups) and bool(groups),'Duplicate/empty polygon groups')
    for row in groups:
        require(row['slot_index'] in by_slot and row['imported_slot_name']==semantic[row['slot_index']],'Group-to-slot role mismatch')
    require(len(triangles)==expected_triangles and len({row['triangle_id'] for row in triangles})==expected_triangles,'Native triangle binding coverage differs')
    result=[]
    for row in triangles:
        group=by_group.get(row['polygon_group_id']);require(group is not None,'Unresolved triangle group')
        require(row['slot_index']==group['slot_index'],'Triangle-to-group slot mismatch')
        result.append({'triangle_id':row['triangle_id'],'semantic':semantic[row['slot_index']],'slot_index':row['slot_index']})
    return {'mesh':mesh.get_path_name(),'lod':lod,'slots':slots,'triangle_roles':result,
            'scope':'Actual MeshDescription slot-name binding and material objects; source geometry correspondence and built section roles remain separate checks'}
