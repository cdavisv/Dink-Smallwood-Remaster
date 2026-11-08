"""Remove reversed duplicate faces created by branch LOD decimation.

No vertex is moved. One valid triangle survives each opposite pair so its normal
cannot cancel. Every changed mesh must keep its original bounds exactly.
"""
import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector

def local_bounds(me):
    return [[min(v.co[i] for v in me.vertices) for i in range(3)],
            [max(v.co[i] for v in me.vertices) for i in range(3)]]

def repair_collapsed_components(ob):
    me=ob.data
    zero_corners={i for i,n in enumerate(me.corner_normals) if n.vector.length<1e-4}
    if not zero_corners:return {'mesh':ob.name,'removed_faces':0,'zero_corners_after':0}
    before=local_bounds(me)
    affected={p.index for p in me.polygons if any(i in zero_corners for i in p.loop_indices)}
    # A collapsed closed branch has only two opposite triangles sharing all3 vertices.
    groups={}
    for p in me.polygons:
        if p.index in affected:groups.setdefault(tuple(sorted(p.vertices)),[]).append(p.index)
    remove=set();processed=set()
    for indices in groups.values():
        if len(indices)!=2:raise RuntimeError(f'Unexpected bad-normal component in {ob.name}: {indices}')
        a,b=[me.polygons[i] for i in indices]
        if len(a.vertices)!=3 or a.normal.dot(b.normal)>-.9999:
            raise RuntimeError(f'Bad normal is not an opposite triangle pair: {ob.name}')
        # Keep one valid triangle, remove its reversed duplicate. This retains every
        # vertex and exact bounds, while the remaining triangle has a useful normal.
        remove.add(indices[1]);processed.update(indices)
    if processed!=affected:raise RuntimeError('Normal cleanup would affect a non-collapsed component')
    # Rebuild explicitly: bmesh imports can reorder coincident reversed faces.
    # Keep the vertex array byte-for-byte equivalent and copy only retained loops.
    keep=[p for p in me.polygons if p.index not in remove]
    old_name=me.name
    fresh=bpy.data.meshes.new(old_name+'_Repair')
    fresh.from_pydata([tuple(v.co) for v in me.vertices],[],[list(p.vertices) for p in keep])
    for mat in me.materials:fresh.materials.append(mat)
    for new_poly,old_poly in zip(fresh.polygons,keep):
        new_poly.use_smooth=old_poly.use_smooth;new_poly.material_index=old_poly.material_index
    for old_uv in me.uv_layers:
        new_uv=fresh.uv_layers.new(name=old_uv.name)
        for new_poly,old_poly in zip(fresh.polygons,keep):
            for new_loop,old_loop in zip(new_poly.loop_indices,old_poly.loop_indices):
                new_uv.data[new_loop].uv=old_uv.data[old_loop].uv
    ob.data=fresh
    if me.users==0:bpy.data.meshes.remove(me)
    fresh.name=old_name;me=fresh;me.update()
    after=local_bounds(me)
    error=max(abs(a-b) for side1,side2 in zip(before,after) for a,b in zip(side1,side2))
    if error>1e-6:raise RuntimeError(f'Cleanup changes {ob.name} bounds by {error}m')
    remaining=sum(n.vector.length<1e-4 for n in me.corner_normals)
    if remaining:raise RuntimeError(f'{ob.name} still has {remaining} cancelling corner normals')
    return {'mesh':ob.name,'removed_faces':len(remove),'repaired_duplicate_pairs':len(remove),
            'bounds_max_change_m':error,'zero_corners_before':len(zero_corners),'zero_corners_after':remaining}

if __name__=='__main__':
    root=Path(__file__).resolve().parents[3];art=root/'SourceAssets/Art/StonebrookExterior'
    bpy.ops.wm.open_mainfile(filepath=str(art/'KIT_StonebrookExterior.blend'))
    report=[]
    for name in ['SM_Oak_Stonebrook_01_LOD0','SM_Oak_Stonebrook_01_LOD1','SM_Oak_Stonebrook_01_LOD2']:
        report.append(repair_collapsed_components(bpy.data.objects[name]))
    bpy.ops.wm.save_as_mainfile(filepath=str(art/'KIT_StonebrookExterior.blend'))
    (art/'foliage_normal_repair.json').write_text(json.dumps({'passed':True,'meshes':report},indent=2)+'\n')
    print(json.dumps(report))
