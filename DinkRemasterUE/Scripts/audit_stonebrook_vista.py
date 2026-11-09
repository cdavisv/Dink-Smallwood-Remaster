"""READ-ONLY editor audit fixture. No context actor spawn, package save or Data publication.
Root reviews before executing. Reads actual loaded screen volumes and mesh source vertices.
"""
import unreal,json,math,hashlib,os,sys
from pathlib import Path
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
assert '-game' not in unreal.SystemLibrary.get_command_line().lower().split()
FILE=Path(os.environ['DINK_VISTA_AUDIT_MANIFEST']).resolve()
assert not FILE.is_relative_to(ROOT/'Content/Dink/Data'),'Use the Work-only review manifest'
M=json.loads(FILE.read_text());assert M['context']=={'visibility':'owner_screen_only','render_only':True}
sys.path.insert(0,str(Path(__file__).resolve().parent))
from vista_audit_geometry import overlap_xy,clip_triangle_open_rect,lod_intersections,coverage_source,checked_triangle_vertices
OUT=ROOT/'Saved/VistaContext/LoadedAudit';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file()};protected[str(ROOT/'SourceAssets/asset_ledger.csv')]=sha(ROOT/'SourceAssets/asset_ledger.csv')
report={'passed':False,'runtime_layer_published':False,'context_spawned':False,'manifest_sha256':sha(FILE),'protected_file_count':len(protected),'limits':['Editor-loaded actual screen-volume bounds; no live-context rendering acceptance','GeometryAABB is conservative, not exact triangle overlap','Culling envelope is recorded separately and never used as physical mesh dimensions']}
cache={};triangles={};faces_by_lod={};TRIANGLE_TOLERANCE_CM=.01
def vector(v):return [float(v.x),float(v.y),float(v.z)]
def corners(low,high):return [[x,y,z] for x in [low[0],high[0]] for y in [low[1],high[1]] for z in [low[2],high[2]]]
def transform(p,row):
 pitch,yaw,roll=row['rotation_deg'];assert pitch==0 and roll==0
 c,s=math.cos(math.radians(yaw)),math.sin(math.radians(yaw));x,y,z=[a*b for a,b in zip(p,row['scale'])];t=row['world_cm']
 return [t[0]+c*x-s*y,t[1]+s*x+c*y,t[2]+z]
def bounds(points):return [min(p[k] for p in points) for k in range(3)],[max(p[k] for p in points) for k in range(3)]
def overlap(a,b):return overlap_xy(a,b)
def height(x,y,t):
 a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
 if abs(den)<1.e-10:return None
 u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;w=1-u-v
 return u*a[2]+v*b[2]+w*c[2] if min(u,v,w)>=-1.e-7 else None
def mesh_lod_faces(path,lod):
 key=(path,lod)
 if key not in faces_by_lod:
  mesh=unreal.load_asset(path);assert isinstance(mesh,unreal.StaticMesh),path
  desc=mesh.get_static_mesh_description(lod);assert desc
  points={}
  for i in range(desc.get_vertex_count()):
   vertex=unreal.VertexID(id_value=i);assert desc.is_vertex_valid(vertex),('Sparse vertex IDs',path,lod,i)
   points[i]=vector(desc.get_vertex_position(vertex))
  faces=[]
  for i in range(desc.get_triangle_count()):
   triangle=unreal.TriangleID(id_value=i)
   ids=checked_triangle_vertices(desc,triangle,context=(path,lod,i))
   indices=[int(v.get_editor_property('id_value')) for v in ids]
   assert all(index in points for index in indices),('Invalid triangle vertex',path,lod,i)
   faces.append([points[index] for index in indices])
  faces_by_lod[key]=faces
 return faces_by_lod[key]
def instance_hits(source_row,rectangle):
 path=source_row['mesh'];lods=[mesh_lod_faces(path,lod) for lod in range(len(cache[path]['lods']))]
 return lod_intersections(lods,rectangle,transform=lambda p:transform(p,source_row),tolerance=TRIANGLE_TOLERANCE_CM)
try:
 world=unreal.EditorLoadingAndSavingUtils.load_map(str(ROOT/'Content/Dink/_Generated/Maps/L_Greybox_World.umap'));assert world
 sub=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
 volumes=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.DinkScreenVolume)
 room_boxes={}
 for actor in volumes:
  number=int(actor.get_editor_property('screen_number'));origin,extent,radius=unreal.SystemLibrary.get_component_bounds(actor.get_editor_property('bounds'));o,e=vector(origin),vector(extent)
  assert number not in room_boxes
  room_boxes[number]={'name':actor.get_name(),'min_cm':[o[k]-e[k] for k in range(3)],'max_cm':[o[k]+e[k] for k in range(3)],'area':actor.get_editor_property('area_name')}
 assert 1 in room_boxes and len(room_boxes)==644,('Unexpected loaded screen coverage',len(room_boxes))
 report['loaded_screens']=len(room_boxes);report['loaded_room_bounds_cm']=room_boxes
 rows=[];ground=[];steps=[]
 for row in M['elements']:
  assert row['collision'] is False and row['camera_occluder'] is False
  path=row['mesh']
  if path not in cache:
   mesh=unreal.load_asset(path);assert isinstance(mesh,unreal.StaticMesh),path
   all_points=[];lods=[]
   for lod in range(sub.get_lod_count(mesh)):
    desc=mesh.get_static_mesh_description(lod);assert desc;points={}
    for i in range(desc.get_vertex_count()):
     vertex=unreal.VertexID(id_value=i);assert desc.is_vertex_valid(vertex);points[i]=vector(desc.get_vertex_position(vertex))
    all_points+=list(points.values());lods.append({'lod':lod,'vertices':len(points),'triangles':desc.get_triangle_count(),'bounds_cm':bounds(list(points.values()))})
    if lod==0 and ('SM_VistaGround_' in path or 'SM_Doorstep_StonebrookVista_' in path):
     triangles[path]=mesh_lod_faces(path,0)
   low,high=bounds(all_points);cull=mesh.get_bounds();origin,extent=vector(cull.origin),vector(cull.box_extent)
   cache[path]={'geometry':corners(low,high),'culling':corners([origin[k]-extent[k] for k in range(3)],[origin[k]+extent[k] for k in range(3)]),'lods':lods}
  geometry=bounds([transform(p,row) for p in cache[path]['geometry']]);culling=bounds([transform(p,row) for p in cache[path]['culling']])
  rows.append({'name':row['name'],'mesh':path,'geometry_allLOD_AABB_cm':geometry,'render_culling_AABB_cm':culling})
  if path in triangles:
   faces=[[transform(p,row) for p in triangle] for triangle in triangles[path]]
   (ground if 'SM_VistaGround_' in path else steps).extend(faces)
 geometry=bounds([p for row in rows for p in row['geometry_allLOD_AABB_cm']]);culling=bounds([p for row in rows for p in row['render_culling_AABB_cm']])
 neighbors=[]
 for number,room in room_boxes.items():
  if number==1:continue
  box=[room['min_cm'],room['max_cm']];gap=math.hypot(max(0,box[0][0]-geometry[1][0],geometry[0][0]-box[1][0]),max(0,box[0][1]-geometry[1][1],geometry[0][1]-box[1][1]))
  potential=overlap(geometry,box);confirmed=[]
  if potential:
   for source_row,instance in zip(M['elements'],rows):
    if not overlap(instance['geometry_allLOD_AABB_cm'],box):continue
    details=instance_hits(source_row,box)
    if any(lod['triangle_hits'] for lod in details):confirmed.append({'name':instance['name'],'lod_checks':details})
  neighbors.append({'screen':number,'name':room['area'],'geometry_AABB_potential_overlap':potential,'geometry_overlap':bool(confirmed),'triangle_intersections':confirmed,'culling_overlap':overlap(culling,box),'geometry_gap_cm':gap})
 neighbors.sort(key=lambda x:x['geometry_gap_cm']);anchor=[-183806.0975,393595.98,0]
 # Authored floor elements are not spawned in editor worlds. Read the actual
 # imported floor vertices and the same validated Data transforms without spawning.
 house=json.loads((ROOT/'Content/Dink/Data/Art/stonebrook.json').read_text())
 floor_rows=[row for row in house['elements'] if 'SM_Floor_Oak_2m_01.' in row['mesh']]
 assert len(floor_rows)==56
 floor_points=[]
 for row in floor_rows:
  mesh=unreal.load_asset(row['mesh']);desc=mesh.get_static_mesh_description(0);assert desc
  for i in range(desc.get_vertex_count()):
   vertex=unreal.VertexID(id_value=i);assert desc.is_vertex_valid(vertex)
   floor_points.append(transform(vector(desc.get_vertex_position(vertex)),row))
 floor_low,floor_high=bounds(floor_points)
 assert abs(floor_high[2])<.01,('Actual imported floor top differs from source0',floor_high)
 room=[[floor_low[0],floor_low[1],-100],[floor_high[0],floor_high[1],500]]
 nominal=[[-184565.16,392283.48],[-183077.66,393595.98]]
 report['actual_authored_floor_geometry_bounds_cm']=[floor_low,floor_high]
 report['source_room_clear_reference_cm']=nominal
 report['floor_reference_note']='56actual imported floor meshes transformed from immutable house Data; editor world does not instantiate authored dressing'
 potentials=[];intrusions=[]
 for source_row,instance in zip(M['elements'],rows):
  if not overlap(instance['geometry_allLOD_AABB_cm'],room):continue
  details=instance_hits(source_row,room)
  confirmed=any(lod['triangle_hits'] for lod in details)
  potentials.append({'name':instance['name'],'geometry_allLOD_AABB_cm':instance['geometry_allLOD_AABB_cm'],'actual_triangle_intrusion':confirmed,'lod_checks':details})
  if confirmed:intrusions.append(instance['name'])
 samples=[]
 for dx in [-75,0,75]:
  for dy in [5,25,75,125,200]:
   x,y=anchor[0]+dx,anchor[1]+dy
   gh=[h for t in ground if (h:=height(x,y,t)) is not None];sh=[h for t in steps if (h:=height(x,y,t)) is not None]
   samples.append({'offset_cm':[dx,dy],'ground_highest_z_cm':max(gh) if gh else None,'step_highest_z_cm':max(sh) if sh else None,'authored_floor_reference_z_cm':floor_high[2],'coverage_source':coverage_source(max(gh) if gh else None,max(sh) if sh else None)})
 report.update(loaded_screens=len(room_boxes),other_screens_audited=len(neighbors),instances=len(rows),unique_meshes=len(cache),geometry_allLOD_union_cm=geometry,render_culling_union_cm=culling,neighbor_overlaps=[r for r in neighbors if r['geometry_overlap']],culling_only_overlaps=[r for r in neighbors if r['culling_overlap'] and not r['geometry_overlap']],closest_neighbors=neighbors[:12],room_clear_rectangle_cm=room,room_geometry_AABB_potential_overlaps=potentials,room_geometry_triangle_intrusions=intrusions,triangle_open_rect_tolerance_cm=TRIANGLE_TOLERANCE_CM,neighbor_AABB_potential_overlaps=[r for r in neighbors if r['geometry_AABB_potential_overlap']],protected_file_count=len(protected),near_door_source_triangle_heights=samples,instances_AABB=rows,actual_mesh_LODs={p:r['lods'] for p,r in cache.items()})
 assert not report['neighbor_overlaps'],report['neighbor_overlaps']
 assert not intrusions,intrusions
 assert all(s['coverage_source']!='none' for s in samples),'Missing ground OR step coverage outside threshold'
 report['passed']=True
except Exception as error:report['error']=str(error);raise
finally:
 changed=[p for p,h in protected.items() if not Path(p).is_file() or sha(Path(p))!=h];report['protected_changes']=changed
 (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
 if changed:raise ValueError('Read-only audit changed original inputs')
print('VISTA LOADED GEOMETRY/NEIGHBOR AUDIT PASS')
