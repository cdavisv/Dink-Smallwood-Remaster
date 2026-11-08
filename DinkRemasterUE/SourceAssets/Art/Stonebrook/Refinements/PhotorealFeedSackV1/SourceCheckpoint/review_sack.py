import bpy,json,sys,os,traceback
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
try:
 bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealFeedSackV1_Source.blend'))
 sys.path.insert(0,str(O/'Pipeline'));from dinkasset import validate
 s=bpy.data.scenes['SackSource'];bpy.context.window.scene=s
 report=validate.validate_scene(only=['SM_FeedSack_Jute_01']);(O/'guide_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print('GUIDE',report['summary'],flush=True)
 for scene in [bpy.data.scenes['SackReference'],s]:
  bpy.context.window.scene=scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=2
  scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
  scene.world=bpy.data.worlds.new(scene.name+'_World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.36,.4,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
  bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));plane=bpy.context.object
  mat=bpy.data.materials.new('StudioFloor');mat.diffuse_color=(.14,.16,.18,1);plane.data.materials.append(mat)
  for pos,power,size in [((1.4,-2,3),300,2),((-2,-.2,1.8),150,1.5),((.2,2.2,2.8),350,1.3)]:
   data=bpy.data.lights.new('StudioArea','AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new('StudioArea',data);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.3))-ob.location).to_track_quat('-Z','Y').to_euler()
  data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',data);scene.collection.objects.link(camera);scene.camera=camera;data.lens=58
  (O/'Previews').mkdir(exist_ok=True)
  for label,pos,target in [('front',(1.4,-1.8,1.3),(0,0,.32)),('inside',(.9,-1.15,1.85),(0,0,.28))]:
   camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/'Previews'/(scene.name+'-'+label+'.png'));bpy.ops.render.render(write_still=True,scene=scene.name);print('CAPTURED',scene.name,label,flush=True)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
