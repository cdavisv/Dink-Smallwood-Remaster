"""Exact source convex-input shape association; not cooked physics proof."""
import numpy as np


def compare_convex(reference,metadata,hulls,frame):
    rotation=np.asarray(frame['source_to_native_direction'],dtype=float)
    if (rotation.shape!=(3,3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation@rotation.T,np.eye(3),atol=1e-12,rtol=0)
            or frame.get('position_scale')!=100 or not frame.get('provenance')):
        raise ValueError('Explicit verified convex coordinate frame required')
    expected=metadata['hulls']
    if len(expected)!=6 or len(hulls)!=6:raise ValueError('Exactly six source/native convex inputs required')
    source=[np.asarray(reference[h['array_prefix']+'_position_m'])@rotation.T*100 for h in expected]
    used=set();matched=[]
    for hull in hulls:
        actual=np.asarray(hull['mesh_vertices'],dtype=float)
        if actual.ndim!=2 or actual.shape[1]!=3 or not np.isfinite(actual).all():
            raise ValueError('Invalid actual convex vertices')
        indices=np.asarray(hull['indices'],dtype=np.int64)
        if indices.size and (indices.size%3 or np.any(indices<0) or np.any(indices>=len(actual))):
            raise ValueError('Invalid actual convex index data')
        candidates=[]
        for i,points in enumerate(source):
            if i in used or points.shape!=actual.shape:continue
            distances=np.max(np.abs(actual[:,None,:]-points[None,:,:]),axis=2)
            links=distances<=.001 # Same accepted 1e-5m source position gate.
            if np.all(links.sum(axis=0)==1) and np.all(links.sum(axis=1)==1):
                candidates.append((i,float(distances[links].max())))
        if len(candidates)!=1:raise ValueError('Missing or ambiguous source convex shape')
        i,error=candidates[0];used.add(i)
        matched.append(dict(source_name=expected[i]['name'],vertices=len(actual),max_position_error_cm=error,
                            index_data_available=bool(indices.size)))
    return dict(pass_convex_source_vertices=True,matched=matched,cooked_physics_acceptance=False,
                scope='Actual convex source inputs/world transforms match; cooked body and real collision remain separate')


def inspect_convex(U,mesh):
    """Detach actual MeshVertices (already LocalToMesh transformed by C++)."""
    rows=[]
    for hull in U.DinkMaterialArtLibrary.inspect_static_mesh_convex_collision(mesh):
        points=hull.get_editor_property('mesh_vertices')
        rows.append(dict(mesh_vertices=[[p.x,p.y,p.z] for p in points],
                         indices=list(hull.get_editor_property('indices'))))
    return rows
