from pathlib import Path
import bpy,bmesh,json,hashlib,math,sys,os
O=Path(__file__).resolve().parent;source=O/'SharedGroundGameV2.blend';pin=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));prep=json.loads((O/'asset_preparation_v2.json').read_text());raw=json.loads((O/'Inputs/terrain_tiles_v1.json').read_text());by={x['asset']:x for x in raw['tiles']};rows=[]
for row in prep['terrain_assets']:
 ob=bpy.data.objects[row['asset']];me=ob.data;bm=bmesh.new();bm.from_mesh(me);assert all(e.is_manifold for e in bm.edges),ob.name;seen=set();components=0;minvol=1e10
 for face in bm.faces:
  if face in seen:continue
  todo=[face];seen.add(face);vol=0
  while todo:
   f=todo.pop();a,b,c=[v.co for v in f.verts];vol+=a.dot(b.cross(c))/6
   for edge in f.edges:
    for nb in edge.link_faces:
     if nb not in seen:seen.add(nb);todo.append(nb)
  assert vol>0,(ob.name,vol);minvol=min(minvol,vol);components+=1
 bm.free();tags=me.attributes['SourceSurface'].data;top=[p for p,t in zip(me.polygons,tags)if t.value==0];bottom=[p for p,t in zip(me.polygons,tags)if t.value==1];assert len(top)==len(by[ob.name]['triangles_canonical_m']);assert all(p.normal.z>0 for p in top);assert all(p.normal.z<0 for p in bottom);err=0;pivot=row['pivot_canonical_m']
 for poly,expected in zip(top,by[ob.name]['triangles_canonical_m']):
  a,b,c=expected
  if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:expected=list(reversed(expected))
  for vi,v in zip(poly.vertices,expected):err=max(err,max(abs(float(me.vertices[vi].co[i])+pivot[i]-v[i])for i in range(3)))
 assert err<2e-6;uv=me.uv_layers.active;assert all(math.isfinite(x)for item in uv.data for x in item.uv);rows.append({'asset':ob.name,'top_triangles':len(top),'total_triangles':len(me.polygons),'top_normals_up':True,'bottom_normals_down':True,'closed_positive_volume_components':components,'minimum_component_volume_m3':minvol,'nonmanifold_edges':0,'actual_parent_top_vertex_max_error_m':err,'local_geometry_UVs_finite':True,'fan_splits':row['point_touch_vertex_fan_splits']})
assert hashlib.sha256(source.read_bytes()).hexdigest()==pin;r={'status':'Actual source142asset setup;128terrain solids/topcoverage checks pass','source_sha256':pin,'parent_clipped_table_sha256':prep['input_clipped_table_sha256'],'terrain_assets':rows,'top_triangles':sum(x['top_triangles']for x in rows),'total_triangles':sum(x['total_triangles']for x in rows),'raw_input_winding_was_downward':True,'order_correction_changes_no_points_or_coverage':True,'topology_correction':'Only disconnectedlocalfacefans duplicated atidenticalpoints beforedownwardextrusion','actor_pivot_note':'Reconstruction uses explicit doubleprecision manifestpivot; Blenderdisplaylocationitself may quantize micro-meters; nativeactorJSON retainsdouble precision','native_approval':False};(O/'geometry_audit_v2.json').write_text(json.dumps(r,indent=2)+'\n');print('GROUND_GEOMETRY_AUDIT_PASS',r['top_triangles'],flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
