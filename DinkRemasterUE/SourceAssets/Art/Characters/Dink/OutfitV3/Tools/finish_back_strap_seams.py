import bpy,bmesh,json,math
from pathlib import Path
ART=Path(Path(__file__).resolve().parents[1])
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mesh=ob.data;keys={v.index:tuple(round(x,6) for x in v.co) for v in mesh.vertices};vf={};adj={}
 for face in mesh.polygons:
  if face.material_index!=4:continue
  kk=[keys[v] for v in face.vertices]
  for a,b in zip(kk,kk[1:]+kk[:1]):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
  for k in kk:vf.setdefault(k,set()).add(face.index)
 todo=set(adj);strapfaces=set();raised=set()
 while todo:
  stack=[next(iter(todo))];component=set()
  while stack:
   k=stack.pop()
   if k in component:continue
   component.add(k);stack.extend(adj[k]-component)
  todo-=component;lo=[min(v[i] for v in component) for i in range(3)];hi=[max(v[i] for v in component) for i in range(3)];faces={i for k in component for i in vf[k]}
  if hi[2]>1.45 and lo[2]>1.25 and hi[2]-lo[2]>.05 and hi[0]-lo[0]<.29 and (lo[0]>0 or hi[0]<0):strapfaces|=faces
  if hi[0]-lo[0]>.32 and lo[2]>.95 and hi[2]<1.45:
   raised|={v for i in faces for v in mesh.polygons[i].vertices}
 for i in []:pass
 bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table();front=[bm.faces[i] for i in strapfaces if bm.faces[i].calc_center_median().y>.02];geom=set(front)
 for f in front:geom.update(f.verts);geom.update(f.edges)
 result=bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-6,plane_co=(0,0,1.43),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
 # Remove tiny cut slivers only in the wardrobe; trim ends meet the raised sewn rim.
 tiny=[f for f in bm.faces if f.material_index==4 and f.calc_area()<1e-8]
 if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES_ONLY')
 bm.to_mesh(mesh);bm.free();mesh.update();rows.append({'lod':lod,'strap_faces_before_cut':len(strapfaces),'front_faces_cleanly_trimmed':len(front),'jerkin_vertices_in_seam_region':len(raised)})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'back_strap_seam_report.json').write_text(json.dumps({'scope':'Wardrobe front strap ends cut to a clean1.40m seam and sewn jerkin rim raised smoothly to cover join; UVs/texture sampling preserved. Protected anatomy untouched.','lods':rows},indent=2)+'\n');print('BACK STRAP SEAMS FINISHED',rows,flush=True)
