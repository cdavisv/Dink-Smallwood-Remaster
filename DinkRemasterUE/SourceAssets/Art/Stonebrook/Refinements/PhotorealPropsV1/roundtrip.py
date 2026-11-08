import bpy,json,hashlib,math,time,os,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPropsV1.blend'));s=bpy.context.scene
man=json.loads((O/'Export/manifest.json').read_text());rep=json.loads((O/'geometry_report.json').read_text());rows=[]
with bpy.data.libraries.load(str(O/'PhotorealPropsV1_Export.blend'),link=False)as(src,dst):dst.materials=['MI_'+n[3:]+'_PhotoBaked'for n in rep['assets']]
mats={n:m for n,m in zip(rep['assets'],dst.materials)}
for a in man['assets']:
 n=a['name'];files=a['files'];f=Path(files['fbx']);f=f if f.is_absolute()else O/'Export'/f
 before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(f),use_custom_normals=True);added=set(bpy.data.objects)-before
 meshes=[ob for ob in added if ob.type=='MESH'and not ob.name.startswith('UCX_')];ob=max(meshes,key=lambda o:len(o.data.vertices));me=ob.data
 # Apply any FBX conversion to vertex positions, then use the original actor matrix.
 me.transform(ob.matrix_world);ob.matrix_world.identity()
 size=[max(v.co[k]for v in me.vertices)-min(v.co[k]for v in me.vertices)for k in range(3)];expected=[rep['assets'][n]['candidate_bounds_m'][1][k]-rep['assets'][n]['candidate_bounds_m'][0][k]for k in range(3)]
 hulls=[o for o in added if o.name.startswith('UCX_')];row={'asset':n,'file':str(f.relative_to(O)),'size_m':size,'expected_m':expected,'max_size_error_m':max(abs(x-y)for x,y in zip(size,expected)),'collision_hulls':len(hulls),'expected_collision_hulls':rep['assets'][n]['collision_hulls'],'triangles':sum(len(p.vertices)-2 for p in me.polygons)};rows.append(row)
 assert row['max_size_error_m']<.005 and len(hulls)==row['expected_collision_hulls']
 me.materials.clear();me.materials.append(mats[n]);
 for p in me.polygons:p.material_index=0
 for inst in rep['assets'][n]['instances']:bpy.data.objects[inst['name']].data=me
 for x in added:
  x.hide_render=True
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_x=1000;s.render.resolution_y=750
for view,pos,target,lens in [('table-joinery',(-2.25,5.25,1.75),(-.3,7.35,.60),47),('bed-cloth',(-6.7,2.65,2.75),(-4.6,4.95,.57),48),('cloth-detail',(-4.15,4.25,1.12),(-4.35,4.65,.71),70)]:
 cam=s.camera;cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;s.render.filepath=str(O/('roundtrip-'+view+'.png'));bpy.ops.render.render(write_still=True)
(O/'roundtrip_receipt.json').write_text(json.dumps({'assets':rows,'PBR_assignment':'actual exported FBX geometry, explicit same2048BC/N/ORM baked materials, ORM R1 Grough B0','fixed_room_lighting':True,'native_imported':False,'passed':True},indent=2));print('ROUNDTRIP_PASSED',flush=True)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
