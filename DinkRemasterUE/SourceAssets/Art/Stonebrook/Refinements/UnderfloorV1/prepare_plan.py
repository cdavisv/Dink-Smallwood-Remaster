import json,math,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;S=Path(Path.home()/'Work/DinkSurfaceDelivery/DinkRemasterUE');P=Path(Path.home()/'Work/DinkQA/FloorNativePreparation/native_snapshot.json');snapshot=json.loads(P.read_text());doc=json.loads((S/'Content/Dink/Data/Art/stonebrook.json').read_text());rows=[r for r in doc['elements'] if r['mesh'].split('.')[-1]=='SM_Floor_Oak_2m_01'];assert len(rows)==56
bind=[{k:r[k] for k in ['name','world_cm','rotation_deg','scale']} for r in rows];bind.sort(key=lambda r:r['name']);blob=lambda o:json.dumps(o,sort_keys=True,separators=(',',':')).encode();points=[];heights=[]
for row in rows:
 p,y,r=row['rotation_deg'];assert p==r==0;c,s=math.cos(math.radians(y)),math.sin(math.radians(y));t=row['world_cm'];scale=row['scale']
 for v in snapshot['vertices']:
  x,y,z=[v[k]*scale[k] for k in range(3)];points.append((t[0]+c*x-s*y,t[1]+s*x+c*y));heights.append(t[2]+z)
# Work in centimetres; round only sub-micrometre noise before hull construction.
pts=sorted(set((round(x,6),round(y,6)) for x,y in points))
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
lo=[]
for p in pts:
 while len(lo)>1 and cross(lo[-2],lo[-1],p)<=1e-5:lo.pop()
 lo.append(p)
hi=[]
for p in reversed(pts):
 while len(hi)>1 and cross(hi[-2],hi[-1],p)<=1e-5:hi.pop()
 hi.append(p)
hull=lo[:-1]+hi[:-1];low=[min(p[k] for p in points) for k in range(2)];high=[max(p[k] for p in points) for k in range(2)];center=[(low[k]+high[k])/2 for k in range(2)]
camera_path=Path(Path.home()/'Work/DinkQA/SurfaceNative/Before/door-room-camera.json');cam=json.loads(camera_path.read_text())['camera_cm'];diag=json.loads(Path(Path.home()/'Work/DinkQA/SurfaceNative/Before/gap-ray-diagnostic.json').read_text());witness=next(r for r in diag['rays'] if r['pixel']==[660,600]);assert witness['floor_mesh_hit_cm'] is None;q=witness['plane_z0_world_cm'];factor=(cam[2]+16)/cam[2];hit=[cam[k]+factor*(q[k]-cam[k]) for k in range(3)];inside=all(cross(a,hull[(i+1)%len(hull)],hit)>=-1e-5 for i,a in enumerate(hull));assert inside and abs(hit[2]+16)<1e-6
report={'schema':'dink-underfloor-source/1','source_floor_count':56,'floor_bindings':bind,'floor_transform_signature_sha256':hashlib.sha256(blob(bind)).hexdigest(),'binding_excludes_mesh_paths_and_unrelated_house_fields':True,'native_source_vertices_sha256':hashlib.sha256(blob(snapshot['vertices'])).hexdigest(),'native_mesh_vertex_count':len(snapshot['vertices']),'native_actual_geometry_z_cm':[min(heights),max(heights)],'actual_floor_outer_convex_contour_world_cm':hull,'contour_kind':'Convex outer contour from ALL56 transformed actual imported vertex sets; board/module internal gaps intentionally covered','world_bounds_xy_cm':[low,high],'dimensions_m':[(high[k]-low[k])/100 for k in range(2)]+[.02],'placement_world_cm':center+[-18.],'top_world_z_cm':-16.,'bottom_world_z_cm':-18.,'below_actual_geometry_clearance_cm':min(heights)+16.,'conservative_reported_culling_or_nail_envelope_cm':-14.,'below_conservative_envelope_clearance_cm':2.,'blue_gap_witness':{'matching_camera_file':str(camera_path),'matching_camera_sha256':hashlib.sha256(camera_path.read_bytes()).hexdigest(),'camera_world_cm':cam,'pixel':[660,600],'before_RGB':witness['RGB'],'before_floor_triangle_hit':None,'underfloor_plane_hit_world_cm':hit,'hit_inside_derived_contour':inside},'runtime_policy':{'collision':False,'camera_occluder':False,'navigation':False,'overlap_events':False,'visibility':'owner_screen1_only','shared_geometry_or_material_edits':False},'material':{'name':'M_Stonebrook_Underfloor_DarkOak_V1','base_color_linear':[.009,.005,.0025],'roughness':.96,'metallic':0,'specular':.25,'opaque':True},'source_class':'building','guide_exception':'Requiredcollision rule waived by explicit render-only task; no sourceUCX and nativeNoCollision/noNav/overlap. All other geometry/size/pivot/UV/material rules remain.'}
(O/'underfloor_plan.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['dimensions_m','placement_world_cm','native_actual_geometry_z_cm','below_actual_geometry_clearance_cm','blue_gap_witness']},indent=2));print('hull vertices',len(hull))
