"""Read-only authored convex-element comparison; no cooking/building/saving."""
import math

def require(ok,message):
    if not ok:raise ValueError(message)

def capture_collision(U, mesh):
    """Plain actual convex data before comparison; no building/cooking/saving."""
    require(isinstance(mesh, U.StaticMesh), 'Expected actual StaticMesh')
    reader = getattr(getattr(U, 'DinkMaterialArtLibrary', None), 'inspect_static_mesh_convex_collision', None)
    require(callable(reader), 'Read-only convex snapshot API missing')
    elements = []
    for index, snapshot in enumerate(reader(mesh)):
        elements.append({'element': index,
            'mesh_vertices_cm': [[float(p.x), float(p.y), float(p.z)] for p in snapshot.get_editor_property('mesh_vertices')],
            'indices': list(snapshot.get_editor_property('indices')),
            'local_to_mesh': str(snapshot.get_editor_property('local_to_mesh'))})
    return {'mesh': mesh.get_path_name(), 'authored_convex_elements': len(elements), 'elements': elements,
            'scope': 'Raw authored local convex data only; not cooked/world collision acceptance.'}

def inspect_collision(U,mesh,source_clouds,validators,position_tolerance_cm):
    require(isinstance(mesh,U.StaticMesh),'Expected actual StaticMesh')
    reader=getattr(getattr(U,'DinkMaterialArtLibrary',None),'inspect_static_mesh_convex_collision',None)
    require(callable(reader),'Read-only convex snapshot API missing')
    snapshots=list(reader(mesh))
    require(len(snapshots)==len(source_clouds) and bool(source_clouds),'Authored collision count differs: '+mesh.get_path_name()+' actual='+str(len(snapshots))+' expected='+str(len(source_clouds)))
    clouds=[];rows=[]
    for index,snapshot in enumerate(snapshots):
        points=[[float(p.x),float(p.y),float(p.z)] for p in snapshot.get_editor_property('mesh_vertices')]
        indices=list(snapshot.get_editor_property('indices'))
        require(points and all(math.isfinite(v) for point in points for v in point),'Nonfinite collision points')
        validators.validate_closed_indices(points,indices)
        clouds.append(points)
        rows.append({'element':index,'mesh_vertices_cm':points,'indices':indices,
                     'local_to_mesh':str(snapshot.get_editor_property('local_to_mesh'))})
    match=validators.match_convex_clouds(clouds,source_clouds,position_tolerance_cm)
    return {'mesh':mesh.get_path_name(),'elements':rows,'source_correspondence':match,
            'scope':'Authored local convex data only; complex-as-simple cooked triangles, world traces, air clearance and gameplay require separate checks'}
