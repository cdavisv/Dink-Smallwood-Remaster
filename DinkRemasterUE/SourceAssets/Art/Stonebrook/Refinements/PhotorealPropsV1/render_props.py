import bpy,json,time,hashlib,os
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPropsV1.blend'));s=bpy.context.scene;s.cycles.samples=32;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_x=1000;s.render.resolution_y=750
r=json.loads((O/'geometry_report.json').read_text());after_only=os.environ.get('PROPS_AFTER_ONLY')=='1';rows=[x for x in json.loads((O/'render_receipt.json').read_text())if x['variant']=='before']if after_only else []
for view,pos,target,lens in [('table-joinery',(-2.25,5.25,1.75),(-.3,7.35,.60),47),('bed-cloth',(-6.7,2.65,2.75),(-4.6,4.95,.57),48),('gameplay-distance',(1.0,-1.0,6.6),(-.2,5.9,.45),28),('cloth-detail',(-4.15,4.25,1.12),(-4.35,4.65,.71),70)]:
 cam=s.camera;cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens
 for variant in (['after']if after_only else ['before','after']):
  for n,rec in r['assets'].items():
   mesh=bpy.data.meshes[n+'_Mesh']if variant=='before'else bpy.data.objects[n].data
   for inst in rec['instances']:bpy.data.objects[inst['name']].data=mesh
  s.render.filepath=str(O/f'{view}-{variant}.png');start=time.time();bpy.ops.render.render(write_still=True)
  rows.append({'view':view,'variant':variant,'file':Path(s.render.filepath).name,'seconds':time.time()-start,'camera_matrix':[list(v)for v in cam.matrix_world],'lens':lens,'lights':{o.name:{'matrix':[list(v)for v in o.matrix_world],'power':o.data.energy,'color':list(o.data.color)}for o in s.objects if o.type=='LIGHT'},'exposure':s.view_settings.exposure,'view_transform':s.view_settings.view_transform})
  (O/'render_receipt.json').write_text(json.dumps(rows,indent=2));print('RENDERED',s.render.filepath,flush=True)

# Blender audio teardown hangs in this sandbox; all durable writes above are complete.
import os,sys
sys.stdout.flush();sys.stderr.flush();os._exit(0)
