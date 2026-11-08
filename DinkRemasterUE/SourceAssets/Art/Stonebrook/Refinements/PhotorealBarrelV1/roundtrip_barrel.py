import bpy,json,hashlib,math,sys,os
from pathlib import Path
from mathutils import Vector,kdtree
O=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealBarrelV1_Export.blend'));source=bpy.data.objects['SM_Barrel_Oak_01'];source.data.calc_loop_triangles();src=source.data.copy();baked=source.data.materials[0]
# Capture the exact triangulated pre-export UV/normal geometry before importing exported bytes.
tris=[];index={}
for p in src.polygons:
 assert len(p.vertices)==3
 row=[(src.vertices[src.loops[i].vertex_index].co.copy(),src.uv_layers.active.data[i].uv.copy(),src.corner_normals[i].vector.copy()) for i in p.loop_indices];i=len(tris);tris.append(row)
 for pos,uv,n in row:index.setdefault(tuple(round(float(v)*1e5) for v in pos),set()).add(i)
fbx=O/'Export/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.fbx';before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(fbx),use_custom_normals=True);added=set(bpy.data.objects)-before
meshes=[o for o in added if o.type=='MESH' and not o.name.startswith('UCX_')];assert len(meshes)==1;ob=meshes[0];me=ob.data;me.transform(ob.matrix_world);ob.matrix_world.identity();assert len(me.polygons)==len(src.polygons)==16648;assert len(me.materials)==1
used=set();maxpos=0;maxuv=0;mindot=1;maxnormalangle=0
for p in me.polygons:
 assert len(p.vertices)==3
 row=[(me.vertices[me.loops[i].vertex_index].co.copy(),me.uv_layers.active.data[i].uv.copy(),me.corner_normals[i].vector.copy()) for i in p.loop_indices]
 key=tuple(round(float(v)*1e5)for v in row[0][0]);candidates=set()
 for x in [-1,0,1]:
  for y in [-1,0,1]:
   for z in [-1,0,1]:candidates.update(index.get((key[0]+x,key[1]+y,key[2]+z),[]))
 match=None
 for i in candidates-used:
  for shift in range(3):
   sr=tris[i][shift:]+tris[i][:shift];pd=max((a[0]-b[0]).length for a,b in zip(row,sr));ud=max((a[1]-b[1]).length for a,b in zip(row,sr))
   if pd<1e-5 and ud<1e-5:match=(i,sr,pd,ud);break
  if match:break
 assert match is not None,('No cyclic oriented face match',p.index)
 i,sr,pd,ud=match;used.add(i);maxpos=max(maxpos,pd);maxuv=max(maxuv,ud)
 nf=(row[1][0]-row[0][0]).cross(row[2][0]-row[0][0]).normalized();sf=(sr[1][0]-sr[0][0]).cross(sr[2][0]-sr[0][0]).normalized();mindot=min(mindot,nf.dot(sf))
 for a,b in zip(row,sr):maxnormalangle=max(maxnormalangle,a[2].angle(b[2],0))
assert len(used)==len(tris);assert mindot>.999
hulls=[o for o in added if o.name.startswith('UCX_')];assert len(hulls)==1
h=hulls[0];hv=[h.matrix_world@v.co for v in h.data.vertices];hb=[[min(v[k]for v in hv)for k in range(3)],[max(v[k]for v in hv)for k in range(3)]];expected=[[-.375,-.375,0],[.375,.375,1]];assert max(abs(a-b)for x,y in zip(hb,expected)for a,b in zip(x,y))<1e-6
report={'passed':True,'source_export_sha256':sha(O/'PhotorealBarrelV1_Export.blend'),'FBX_sha256':sha(fbx),'triangles':len(me.polygons),'cyclic_oriented_bijective_face_match':True,'max_position_delta_m':maxpos,'max_UV_delta':maxuv,'minimum_geometric_front_dot':mindot,'max_stored_normal_angle_radians':maxnormalangle,'source_and_roundtrip_material_slots':1,'collision_hulls':1,'actual_roundtrip_collision_bounds_m':hb,'render_scope':'Actual FBX geometry with explicit same baked BC/N/ORM material; neutral original studio. Not native UE.'}
# Compare the exact exported geometry in the same approved source studio, with no light/exposure changes.
roundtrip=me.copy();roundtrip.materials.clear();roundtrip.materials.append(baked)
for p in roundtrip.polygons:p.material_index=0
bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealBarrelV1_Source.blend'))
# Reload actual imported FBX and export material after source studio reset.
with bpy.data.libraries.load(str(O/'PhotorealBarrelV1_Export.blend'),link=False)as (a,b):b.materials=['MI_Barrel_Oak_01_PhotoBaked']
mat=b.materials[0];s=bpy.data.scenes['BarrelStudio'];bpy.context.window.scene=s;before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(fbx),use_custom_normals=True);added=set(bpy.data.objects)-before;ob=next(o for o in added if o.type=='MESH'and not o.name.startswith('UCX_'));ob.data.transform(ob.matrix_world);ob.matrix_world.identity();ob.data.materials.clear();ob.data.materials.append(mat)
for p in ob.data.polygons:p.material_index=0
bpy.data.objects['Studio source instance'].hide_render=True
for x in added:x.hide_render=x!=ob
s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_x=s.render.resolution_y=850;s.render.resolution_percentage=100
(O/'Roundtrip').mkdir(exist_ok=True)
for name,pos,lens,target in [('front',(1.6,-2.3,1.55),58,(0,0,.49)),('game-distance',(2.3,-3.4,1.9),45,(0,0,.5)),('head',(1.0,-1.3,2.3),62,(0,0,.66))]:
 s.camera.location=pos;s.camera.rotation_euler=(Vector(target)-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.lens=lens;s.render.filepath=str(O/'Roundtrip'/(name+'.png'));bpy.ops.render.render(write_still=True,scene=s.name);print('ROUNDTRIP_RENDER',name,flush=True)
(O/'roundtrip_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print('ROUNDTRIP_PASS',flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
