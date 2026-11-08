"""Read the one loaded skirt source mesh and its actual world transform; no saves or mutations.
Run through the verified private session console after its owner-screen manifest loads.
"""
import json
from pathlib import Path
import unreal

qa_fg_world = next(w for w in unreal.ObjectIterator(unreal.World) if unreal.GameplayStatics.get_player_pawn(w, 0))
qa_fg_project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
qa_fg_assets = {}
qa_fg_components = []
for actor in unreal.GameplayStatics.get_all_actors_of_class(qa_fg_world, unreal.Actor):
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = component.static_mesh
        if not mesh or mesh.get_name() not in ['SM_Stonebrook_PerimeterSkirt_V1']:
            continue
        key = mesh.get_path_name()
        if key not in qa_fg_assets:
            description = mesh.get_static_mesh_description(0)
            assert description is not None
            vertices = []
            for i in range(description.get_vertex_count()):
                vid = unreal.VertexID(id_value=i)
                assert description.is_vertex_valid(vid)
                value = description.get_vertex_position(vid)
                vertices.append([float(value.x), float(value.y), float(value.z)])
            triangles = []
            for i in range(description.get_triangle_count()):
                tid = unreal.TriangleID(id_value=i)
                assert description.is_triangle_valid(tid)
                ids = []
                for index in range(3):
                    instance = description.get_triangle_vertex_instance(tid, index)
                    assert description.is_vertex_instance_valid(instance)
                    vertex = description.get_vertex_instance_vertex(instance)
                    assert description.is_vertex_valid(vertex)
                    ids.append(int(vertex.get_editor_property('id_value')))
                assert len(ids) == 3
                triangles.append(ids)
            qa_fg_assets[key] = {'vertices': vertices, 'triangles': triangles}
        transform = component.get_world_transform()
        # Export actual transformed imported vertices, not render/culling bounds.
        points = [transform.transform_location(unreal.Vector(*v)) for v in qa_fg_assets[key]['vertices']]
        qa_fg_components.append({'actor': actor.get_name(), 'component': component.get_name(), 'mesh': key,
            'actor_hidden': actor.get_editor_property('hidden'), 'visible': component.is_visible(),
            'collision': str(component.get_collision_enabled()),
            'world_vertices_cm': [[float(v.x), float(v.y), float(v.z)] for v in points]})
assert len(qa_fg_components) == 1, len(qa_fg_components)
output = qa_fg_project / 'Saved/VisualQA/Runtime/skirt_geometry.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({'assets': qa_fg_assets, 'components': qa_fg_components,
    'method': 'Actual loaded source-description vertices/triangles and component transforms. No render AABBs.'}, indent=2) + '\n')
unreal.log('QA_SKIRT_GEOMETRY_EXPORTED')
