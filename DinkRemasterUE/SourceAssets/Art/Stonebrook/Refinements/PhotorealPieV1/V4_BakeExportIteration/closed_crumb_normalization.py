import bpy
def components(me):
 parent=list(range(len(me.vertices)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for p in me.polygons:
  root=find(p.vertices[0])
  for v in p.vertices[1:]:parent[find(v)]=root
 groups={}
 for p in me.polygons:groups.setdefault(find(p.vertices[0]),[]).append(p.index)
 return list(groups.values())
def vertices(me,faces):return set(v for i in faces for v in me.polygons[i].vertices)
def small(me,faces):
 v=vertices(me,faces);return max(max(me.vertices[i].co[k]for i in v)-min(me.vertices[i].co[k]for i in v)for k in range(3))<.01

def normalize_closed_crumbs():
 prefix='SM_Pie_Rustic_01';lod0=bpy.data.objects[prefix+'_LOD0'].data;full=[g for g in components(lod0)if len(g)==8 and len(vertices(lod0,g))==6 and small(lod0,g)];assert len(full)==20;fullfaces=[i for g in full for i in g];rows=[]
 for level in [1,2]:
  ob=bpy.data.objects[prefix+'_LOD'+str(level)];old=ob.data;collapsed=[g for g in components(old)if len(g)==2 and len(vertices(old,g))==3 and small(old,g)];assert len(collapsed)==20;removed=set(i for g in collapsed for i in g);body=[i for i in range(len(old.polygons))if i not in removed];sources=[(old,i)for i in body]+[(lod0,i)for i in fullfaces];coords=[];origin_vertices=[];faces=[];normal=[];uv_layers={uv.name:[]for uv in old.uv_layers};matids=[];smooth=[];pointmap={}
  for me,fi in sources:
   p=me.polygons[fi];ids=[];assert len(p.vertices)==3
   for li in p.loop_indices:
    vi=me.loops[li].vertex_index;key=(me.name,vi)
    if key not in pointmap:pointmap[key]=len(coords);coords.append(me.vertices[vi].co.copy());origin_vertices.append((me,vi))
    ids.append(pointmap[key]);n=me.corner_normals[li].vector.copy();assert n.length>.5;normal.append(n)
    for name in uv_layers:uv_layers[name].append(me.uv_layers[name].data[li].uv.copy())
   faces.append(ids);matids.append(p.material_index);smooth.append(p.use_smooth)
  new=bpy.data.meshes.new(old.name+'_ClosedCrumbs');new.from_pydata(coords,[],faces);new.update()
  for mat in old.materials:new.materials.append(mat)
  for p,mid,sm in zip(new.polygons,matids,smooth):p.material_index=mid;p.use_smooth=sm
  for name,uvs in uv_layers.items():
   layer=new.uv_layers.new(name=name)
   for d,uv in zip(layer.data,uvs):d.uv=uv
  for label in ['Browning','FruitMask']:
   at=new.attributes.new(label,'FLOAT','POINT')
   for d,(me,vi)in zip(at.data,origin_vertices):d.value=me.attributes[label].data[vi].value
  new.normals_split_custom_set(normal);new.update();maxangle=max(a.angle(b.vector,0)for a,b in zip(normal,new.corner_normals));assert maxangle<.001 and all(n.vector.length>.5 for n in new.corner_normals)
  for newface,(me,fi)in zip(new.polygons,sources):
   original=me.polygons[fi];assert newface.material_index==original.material_index
   for a,b in zip(newface.loop_indices,original.loop_indices):
    assert (new.vertices[new.loops[a].vertex_index].co-me.vertices[me.loops[b].vertex_index].co).length==0
    assert (new.uv_layers.active.data[a].uv-me.uv_layers.active.data[b].uv).length==0
  # Closed source crumbs copied exactly; remaining body corner geometry/UV/normals retained.
  before=len(old.polygons);bounds=lambda me:[[min(v.co[k]for v in me.vertices)for k in range(3)],[max(v.co[k]for v in me.vertices)for k in range(3)]];b0=bounds(old);b1=bounds(new);oldname=old.name;old.name=oldname+'_Collapsed';new.name=oldname;ob.data=new;bpy.data.meshes.remove(old);rows.append({'LOD':level,'initial_triangles':before,'removed_collapsed_faces':len(removed),'restored_closed_source_crumb_faces':len(fullfaces),'final_triangles':len(new.polygons),'restored_components':20,'all_remaining_body_and_restored_LOD0_crumb_corner_positions_UV_materialIDs_exact':True,'max_normal_angle_radians':maxangle,'bounds_before_m':b0,'bounds_after_m':b1})
 assert [r['final_triangles']for r in rows]==[2542,1330]
 return rows
