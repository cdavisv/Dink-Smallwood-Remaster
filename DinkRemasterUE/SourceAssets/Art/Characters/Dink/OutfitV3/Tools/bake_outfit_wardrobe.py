"""Bake only WardrobeV3 uniquely; preserve all four anatomical meshes verbatim.
UV1002 is a documented hero-range warning, NOT UDIM. Regular Texture2D REPEAT.
"""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
ART=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'))
arm=bpy.data.objects['Armature'];arm.data.pose_position='REST';arm.animation_data.action=None
originals=[bpy.data.objects[f'SK_Dink_OutfitV3_LOD{i}'] for i in range(4)];mat=originals[0].data.materials[4]
def extract(ob,protected,name):
 faces=[p for p in ob.data.polygons if (p.material_index<4)==protected];ids=sorted({i for p in faces for i in p.vertices});mapping={v:i for i,v in enumerate(ids)}
 other={i for p in ob.data.polygons if (p.material_index<4)!=protected for i in p.vertices}
 assert not set(ids)&other,'Mixed-material shared vertex needs explicit preservation strategy'
 # Keep inherited anatomical wires with their vertices as well.
 if protected:
  used_edges={tuple(sorted((a,b))) for p in faces for a,b in zip(p.vertices,list(p.vertices[1:])+[p.vertices[0]])}
  wires=[tuple(e.vertices) for e in ob.data.edges if e.is_loose]
  ids=sorted(set(ids)|{i for e in wires for i in e});mapping={v:i for i,v in enumerate(ids)}
 else:wires=[]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata([tuple(ob.data.vertices[i].co) for i in ids],[(mapping[a],mapping[b]) for a,b in wires],[tuple(mapping[i] for i in p.vertices) for p in faces]);mesh.update()
 result=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(result)
 for m in ob.data.materials:mesh.materials.append(m)
 for dst,src in zip(mesh.polygons,faces):dst.material_index=src.material_index;dst.use_smooth=src.use_smooth
 for layer in ob.data.uv_layers:
  uv=mesh.uv_layers.new(name=layer.name)
  for dst,src in zip(mesh.polygons,faces):
   for a,b in zip(dst.loop_indices,src.loop_indices):uv.data[a].uv=layer.data[b].uv
 for group in ob.vertex_groups:result.vertex_groups.new(name=group.name)
 for dst,src in enumerate(ids):
  for g in ob.data.vertices[src].groups:result.vertex_groups[g.group].add([dst],g.weight,'REPLACE')
 result['protected_original_vertex_indices']=json.dumps(ids) if protected else ''
 return result
ward=extract(originals[0],False,'WardrobeOnlyHigh');ward.data.uv_layers[0].name='WardrobeSource'
ward.data.materials.clear();ward.data.materials.append(mat)
for face in ward.data.polygons:face.material_index=0
# Collar fitting may collapse old trim slivers; remove only wardrobe zero-area faces.
import bmesh
bm=bmesh.new();bm.from_mesh(ward.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));tiny=[f for f in bm.faces if f.calc_area()<1e-8]
if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES_ONLY')
bm.to_mesh(ward.data);bm.free()
# Ensure explicit UV source, even while target atlas is active.
sourceuv=mat.node_tree.nodes.new('ShaderNodeUVMap');sourceuv.uv_map='WardrobeSource'
for node in mat.node_tree.nodes:
 if node.type=='TEX_IMAGE':mat.node_tree.links.new(sourceuv.outputs['UV'],node.inputs['Vector'])
 if node.type=='NORMAL_MAP':node.uv_map='WardrobeSource'
for ob in bpy.context.scene.objects:ob.hide_render=True;ob.select_set(False)
ward.hide_render=False;ward.select_set(True);bpy.context.view_layer.objects.active=ward
atlas=ward.data.uv_layers.new(name='WardrobeAtlas');ward.data.uv_layers.active=atlas;atlas.active_render=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.003,area_weight=.35,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
# Convert the projected chart boundaries into real seams, then relax each chart.
# Smart projection can self-overlap on folded shirt/strap surfaces.
import bmesh
bm=bmesh.new();bm.from_mesh(ward.data);layer=bm.loops.layers.uv.active
for edge in bm.edges:
 if len(edge.link_loops)!=2:edge.seam=True;continue
 a,b=edge.link_loops
 edge.seam=(a[layer].uv-b.link_loop_next[layer].uv).length>1e-6 or (a.link_loop_next[layer].uv-b[layer].uv).length>1e-6
bm.to_mesh(ward.data);bm.free()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.unwrap(method='ANGLE_BASED',margin=.003);bpy.ops.uv.pack_islands(rotate=True,margin=.003);bpy.ops.object.mode_set(mode='OBJECT')
# Isolate any remaining folded chart faces, then repack; never weaken validator.
import sys,inspect
sys.path.insert(0,str(Path(__file__).resolve().parents[7]/'tools/blender'))
from dinkasset import validate as uvcheck
code=inspect.getsource(uvcheck.uv_stats).replace('def uv_stats(', 'def chart_audit(').replace('area > 1e-7','area > 1e-10').replace('degenerate = 0','degenerate = 0; collapsed_polys=set()').replace('degenerate += 1','degenerate += 1; collapsed_polys.add(t.polygon_index)').replace('"uv_area": total_uv_area,','"overlapping_polys": sorted({tris[i][0] for i in overlapping_tris}|collapsed_polys), "uv_area": total_uv_area,')
namespace=dict(uvcheck.__dict__);exec(code,namespace);chart_audit=namespace['chart_audit']
for iteration in range(8):
 audit=chart_audit(ward.data,1,max_pairs=10000000);print('CHART AUDIT',iteration,audit['overlap_ratio'],len(audit['overlapping_polys']),flush=True)
 if not audit['overlapping_polys']:break
 bm=bmesh.new();bm.from_mesh(ward.data);bm.faces.ensure_lookup_table()
 for index in audit['overlapping_polys']:
  for edge in bm.faces[index].edges:edge.seam=True
 bm.to_mesh(ward.data);bm.free()
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.unwrap(method='ANGLE_BASED',margin=.003);bpy.ops.uv.pack_islands(rotate=True,margin=.003);bpy.ops.object.mode_set(mode='OBJECT')
else:raise RuntimeError('Wardrobe atlas still self-overlaps after chart separation')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.bake.use_clear=True;scene.render.bake.margin=12;scene.render.bake.use_selected_to_active=False
nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');output=nodes.get('Material Output');original_surface=next(l.from_socket for l in output.inputs['Surface'].links)
emission=nodes.new('ShaderNodeEmission');targetnode=nodes.new('ShaderNodeTexImage');targetnode.extension='REPEAT'
def image_new(name,noncolor=False):
 im=bpy.data.images.new(name,width=4096,height=4096,alpha=False);im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB';return im
results={}
for label,socket,noncolor in [('BC','Base Color',False),('Roughness','Roughness',True),('Metallic','Metallic',True)]:
 im=image_new('WardrobeBaked_'+label,noncolor);targetnode.image=im;nodes.active=targetnode
 for link in list(emission.inputs['Color'].links):links.remove(link)
 if bs.inputs[socket].is_linked:links.new(bs.inputs[socket].links[0].from_socket,emission.inputs['Color'])
 else:emission.inputs['Color'].default_value=(*([bs.inputs[socket].default_value]*3),1)
 links.new(emission.outputs[0],output.inputs['Surface']);bpy.ops.object.bake(type='EMIT');results[label]=im;print('WARDROBE BAKE',label,flush=True)
links.new(original_surface,output.inputs['Surface'])
im=image_new('WardrobeBaked_N',True);targetnode.image=im;nodes.active=targetnode;bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT');results['N']=im
orm=image_new('WardrobeBaked_ORM',True);count=4096*4096;data=np.ones((count,4),np.float32)
for channel,key in [(1,'Roughness'),(2,'Metallic')]:
 values=np.empty(count*4,np.float32);results[key].pixels.foreach_get(values);data[:,channel]=values.reshape(-1,4)[:,0]
orm.pixels.foreach_set(data.ravel());results['ORM']=orm
for label in ['BC','N','ORM']:
 im=results[label];im.filepath_raw=str(ART/'Textures'/f'T_Dink_WardrobeV3_{label}.png');im.file_format='PNG';im.save();im.name=f'T_Dink_WardrobeV3_{label}_Unique'
# Replace only the new Wardrobe graph. Old anatomical graphs are never touched.
nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Specular IOR Level'].default_value=.3;links.new(bs.outputs[0],output.inputs['Surface'])
for label in ['BC','N','ORM']:
 tex=nodes.new('ShaderNodeTexImage');tex.image=results[label];tex.extension='REPEAT';tex.label='Regular2D REPEAT; wardrobe uniqueUV tile1002'
 if label=='BC':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 elif label=='N':
  normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],bs.inputs['Normal'])
 else:
  separate=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],separate.inputs[0]);links.new(separate.outputs['Green'],bs.inputs['Roughness']);links.new(separate.outputs['Blue'],bs.inputs['Metallic'])
# A real unique set of charts; offset only separates protected anatomy's UVs.
ward.data.uv_layers.remove(ward.data.uv_layers['WardrobeSource']);ward.data.uv_layers[0].name='UVMap'
for loop in ward.data.uv_layers[0].data:loop.uv.x+=1
ward.data.uv_layers.active_index=0
# Loaded into bake script after its strict chart audit definition.
def rebuild_chart_mesh(ob,facespecs,name):
 # specs (source object, polygon index); key by object and vertex keeps all seams.
 vertices=[];faces=[];uvvalues=[];weights=[];charts=[];keys={}
 for source,pi in facespecs:
  poly=source.data.polygons[pi];face=[]
  for li in poly.loop_indices:
   loop=source.data.loops[li];co=source.data.uv_layers[0].data[li].uv;key=(source.name,loop.vertex_index,float(co.x),float(co.y))
   if key not in keys:
    keys[key]=len(vertices);v=source.data.vertices[loop.vertex_index];vertices.append(tuple(v.co));weights.append([(g.group,g.weight) for g in v.groups]);attr=source.data.attributes.get('WardrobeChart');charts.append(attr.data[v.index].value if attr else -1)
   face.append(keys[key]);uvvalues.append(tuple(co))
  faces.append(face)
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.materials.append(mat);uv=mesh.uv_layers.new(name='UVMap')
 for dst,src in zip(uv.data,uvvalues):dst.uv=src
 for face in mesh.polygons:face.use_smooth=True
 attr=mesh.attributes.new('WardrobeChart','INT','POINT')
 for dst,src in zip(attr.data,charts):dst.value=src
 result=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(result)
 for group in ob.vertex_groups:result.vertex_groups.new(name=group.name)
 for i,values in enumerate(weights):
  for group,w in values:result.vertex_groups[group].add([i],w,'REPLACE')
 return result

def prepare_chart_source(ward):
 split=rebuild_chart_mesh(ward,[(ward,p.index) for p in ward.data.polygons],'WardrobeChartSource');mesh=split.data;adj=[set() for v in mesh.vertices]
 for e in mesh.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 todo=set(range(len(mesh.vertices)));chart=0
 while todo:
  stack=[next(iter(todo))];component=set()
  while stack:
   i=stack.pop()
   if i in component:continue
   component.add(i);stack.extend(adj[i]-component)
  todo-=component
  for i in component:mesh.attributes['WardrobeChart'].data[i].value=chart
  chart+=1
 return split,chart

def restore_folded_charts(low,high):
 restored=set();removed=0
 for iteration in range(10):
  st=chart_audit(low.data,max_pairs=10000000);bad=set(st['overlapping_polys'])
  low.data.calc_loop_triangles();uv=low.data.uv_layers[0]
  for t in low.data.loop_triangles:
   a,b,c=[uv.data[i].uv for i in t.loops]
   if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<2e-10:bad.add(t.polygon_index)
  if not bad:return low,sorted(restored)
  attr=low.data.attributes['WardrobeChart'];badcharts={attr.data[low.data.polygons[i].vertices[0]].value for i in bad};restored|=badcharts
  specs=[(low,p.index) for p in low.data.polygons if attr.data[p.vertices[0]].value not in badcharts]
  highattr=high.data.attributes['WardrobeChart'];specs.extend((high,p.index) for p in high.data.polygons if highattr.data[p.vertices[0]].value in badcharts)
  fixed=rebuild_chart_mesh(low,specs,'ChartSafeWardrobe');bpy.data.objects.remove(low,do_unlink=True);low=fixed
  print('RESTORED UV CHARTS',iteration,len(badcharts),flush=True)
 raise RuntimeError('Lower wardrobe chart preservation did not converge')

oldward=ward;ward,chart_count=prepare_chart_source(oldward);bpy.data.objects.remove(oldward,do_unlink=True)
reports=[]
for lod,old in enumerate(originals):
 body=extract(old,True,f'ProtectedAnatomy_LOD{lod}')
 garment=ward.copy();garment.data=ward.data.copy();bpy.context.scene.collection.objects.link(garment);garment.name=f'UniqueWardrobe_LOD{lod}'
 for ob in bpy.context.selected_objects:ob.select_set(False)
 garment.hide_render=False;garment.select_set(True);bpy.context.view_layer.objects.active=garment
 if lod:
  modifier=garment.modifiers.new('WardrobeOnlyReduction','DECIMATE');modifier.ratio=[1,.5,.25,.12][lod];modifier.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=modifier.name)
 garment,restored_charts=restore_folded_charts(garment,ward)
 # Wardrobe-only interpolation can add influences; prune to existing top4.
 for v in garment.data.vertices:
  values=sorted(((g.group,g.weight) for g in v.groups if g.weight>1e-7),key=lambda x:-x[1])[:4];total=sum(w for _,w in values)
  for group in garment.vertex_groups:group.remove([v.index])
  for group,w in values:garment.vertex_groups[group].add([v.index],w/total,'REPLACE')
 # Manual merge preserves protected float coordinates, weights, UVs and polygons.
 for face in garment.data.polygons:face.material_index=4
 parts=[body,garment];verts=[];faces=[];edgepairs=[];polymats=[];smooth=[];uvs=[];weights=[]
 for part in parts:
  offset=len(verts);verts.extend([tuple(v.co) for v in part.data.vertices]);faces.extend([tuple(i+offset for i in p.vertices) for p in part.data.polygons]);edgepairs.extend([tuple(i+offset for i in e.vertices) for e in part.data.edges if e.is_loose]);polymats.extend([p.material_index for p in part.data.polygons]);smooth.extend([p.use_smooth for p in part.data.polygons]);uvs.extend([tuple(v.uv) for v in part.data.uv_layers[0].data]);weights.extend([[(g.group,g.weight) for g in v.groups] for v in part.data.vertices])
 mesh=bpy.data.meshes.new(f'SK_Dink_OutfitV3_LOD{lod}_Unique');mesh.from_pydata(verts,edgepairs,faces);mesh.update()
 for m in old.data.materials:mesh.materials.append(m)
 for p,material,sm in zip(mesh.polygons,polymats,smooth):p.material_index=material;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for loop,value in zip(uv.data,uvs):loop.uv=value
 old.data=mesh
 old.vertex_groups.clear()
 for group in body.vertex_groups:old.vertex_groups.new(name=group.name)
 for i,values in enumerate(weights):
  for group,w in values:old.vertex_groups[group].add([i],w,'REPLACE')
 old['protected_original_vertex_indices']=body['protected_original_vertex_indices'];old.hide_render=lod!=0
 reports.append({'lod':lod,'triangles':sum(len(p.vertices)-2 for p in mesh.polygons),'restored_uv_charts':restored_charts,'wardrobe_triangles':sum(len(p.vertices)-2 for p in garment.data.polygons),'protected_original_vertex_indices':json.loads(body['protected_original_vertex_indices'])})
 bpy.data.objects.remove(body,do_unlink=True);bpy.data.objects.remove(garment,do_unlink=True)
bpy.data.objects.remove(ward,do_unlink=True)
report={'stage':'SOURCE REVIEW ONLY; no export/import/ledger','texture_size':4096,'uv_contract':'Anatomy1001 bitexact, wardrobe unique charts1002, Texture2D REPEAT, noUDIM; UV_RANGEwarning retained','lods':reports}
(ART/'wardrobe_bake_report.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False);print('UNIQUE WARDROBE COMPLETE',[(r['lod'],r['triangles']) for r in reports],flush=True)
