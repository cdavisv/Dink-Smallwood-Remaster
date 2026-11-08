"""One render-only underfloor fitted to56actual native floor placements. Work-only."""
import bpy,json,hashlib,math
from pathlib import Path
O=Path(__file__).resolve().parent;p=json.loads((O/'underfloor_plan.json').read_text());bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for col in list(bpy.data.collections):bpy.data.collections.remove(col)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
name='SM_Underfloor_Stonebrook_V1';col=bpy.data.collections.new(name);s.collection.children.link(col);col['dink_class']='building';col['dink_path']='Stonebrook/Refinements/UnderfloorV1';col['dink_nanite']='yes';col['dink_render_only']=True;col['dink_source']='Original generated architecture, derived only from56actual floor transforms/native geometry bounds; no original edits';col['dink_collision_exception']='Explicit root-authorized render-only architecture, no sourceUCX/nativecollision/nav/overlap'
center=p['placement_world_cm'];ring=[((q[0]-center[0])/100,-(q[1]-center[1])/100) for q in p['actual_floor_outer_convex_contour_world_cm']];n=len(ring);v=[(x,y,z) for z in [0,.02] for x,y in ring];faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]+[(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],faces);mesh.update();obj=bpy.data.objects.new(name,mesh);col.objects.link(obj)
mat=bpy.data.materials.new(p['material']['name']);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*p['material']['base_color_linear'],1);bs.inputs['Roughness'].default_value=.96;bs.inputs['Metallic'].default_value=0;bs.inputs['Specular IOR Level'].default_value=.25;bs.inputs['Coat Weight'].default_value=0;mat.diffuse_color=(*p['material']['base_color_linear'],1);mesh.materials.append(mat)
uv=mesh.uv_layers.new(name='UVMap');width,depth=p['dimensions_m'][:2]
for poly in mesh.polygons:
 for loop in poly.loop_indices:
  q=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=((q.x/width)+.5,(q.y/depth)+.5)
# Roof/floor top is flat; sides use simple nondegenerate UVs despite constant shader.
for poly in list(mesh.polygons)[2:]:
 a,b,c,d=poly.loop_indices
 for loop,coord in zip([a,b,c,d],[(0,0),(0,1),(1,1),(1,0)]):uv.data[loop].uv=coord
assert len(mesh.vertices)==24 and sum(len(q.vertices)-2 for q in mesh.polygons)==44
# No collider objects or physics assignment: this is explicitly render-only.
obj['native_collision']='NoCollision';obj['native_navigation']=False;obj['native_overlaps']=False;obj['camera_occluder']=False
bpy.context.view_layer.objects.active=obj;obj.select_set(True);blend=O/'UnderfloorV1.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
fbx=O/'SM_Underfloor_Stonebrook_V1.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_mesh_modifiers=True,use_triangles=True,mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r={'schema':'dink-underfloor-asset/1','asset':name,'class':'building','files':{'blend':{'file':blend.name,'sha256':sha(blend)},'fbx':{'file':fbx.name,'sha256':sha(fbx)}},'source_geometry':{'vertices':24,'triangles':44,'polygons':14,'material_slots':1,'UV_layers':1,'dimensions_m':p['dimensions_m'],'native_geometry_bound_contour_corners':12,'pivot':'base_center','source_UCX_count':0,'collision_rule_exception':p['guide_exception']},'placement_world_cm':center,'rotation_deg':[0,0,0],'scale':[1,1,1],'material':p['material'],'floor_binding_signature':p['floor_transform_signature_sha256'],'geometry_positions_signature':p['native_source_vertices_sha256'],'proposed_native_package':'/Game/Dink/Kits/Stonebrook/Refinements/UnderfloorV1/'+name,'proposed_runtime_element':{'name':'StartingHouseUnderfloorV1','mesh':'/Game/Dink/Kits/Stonebrook/Refinements/UnderfloorV1/'+name+'.'+name,'world_cm':center,'rotation_deg':[0,0,0],'scale':[1,1,1],'collision':False,'camera_occluder':False},'runtime_policy':p['runtime_policy'],'native_import_requirements':{'generate_collisions':False,'has_navigation_data':False,'component_collision':'NoCollision','component_navigation':False,'component_generate_overlaps':False,'owner_screen':1},'runtime_published':False,'approved_floor_bakes_or_geometry_modified':False}
r['runtime_publication_policy']={'separate_context_manifest':'Content/Dink/Data/Art/stonebrook_underfloor_v1.json','context':{'visibility':'owner_screen_only','render_only':True},'original_floor_manifest_modified':False,'Vista359_manifest_modified':False}
r['actual_blue_pixel_ray_proof']=p['blue_gap_witness']
context={'schema':'dink-art/1','screen':1,'context':r['runtime_publication_policy']['context'],'source':'SourceAssets/Art/Stonebrook/Refinements/UnderfloorV1/asset_manifest.json','assets':[{'mesh':r['proposed_runtime_element']['mesh'],'expected_size_cm':[x*100 for x in p['dimensions_m']],'expected_lods':1,'bounds_tolerance_cm':1}],'elements':[r['proposed_runtime_element']]}
(O/'stonebrook_underfloor_v1.context.draft.json').write_text(json.dumps(context,indent=2)+'\n')
(O/'asset_manifest.json').write_text(json.dumps(r,indent=2)+'\n');print('UNDERFLOOR_SOURCE_READY',flush=True)
