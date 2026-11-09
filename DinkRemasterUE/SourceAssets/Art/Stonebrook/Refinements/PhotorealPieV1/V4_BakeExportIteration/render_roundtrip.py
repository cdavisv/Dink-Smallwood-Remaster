import bpy,json,sys,os,traceback
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
try:
 bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPieV1_Source.blend'))
 sys.path.insert(0,str(O/'Pipeline'));from dinkasset import validate
 s=bpy.data.scenes['PieSource'];bpy.context.window.scene=s
 for ob in bpy.data.collections['SM_Pie_Rustic_01'].objects:
  if ob.type=='MESH':ob.hide_render=not ob.name.endswith('_LOD'+os.environ.get('DINK_PIE_LOD','0'))
 report=validate.validate_scene(only=['SM_Pie_Rustic_01']);(O/'guide_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print('GUIDE',report['summary'],flush=True)
 for original in bpy.data.collections['SM_Pie_Rustic_01'].objects:original.hide_render=True
 with bpy.data.libraries.load(str(O/'PhotorealPieV1_Export.blend'),link=False)as(source,destination):destination.materials=['MI_Pie_BlueCeramic_PhotoBaked','MI_Pie_PastryFruit_PhotoBaked']
 materials=destination.materials;before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Export/Game/Dink/Props/Stonebrook/PhotorealPieV1/SM_Pie_Rustic_01.fbx'),use_custom_normals=True);added=set(bpy.data.objects)-before
 for ob in added:
  if ob.type!='MESH':continue
  ob.hide_render=not ob.name.split('.')[0].endswith('_LOD'+os.environ.get('DINK_PIE_LOD','0'));ids=[f.material_index for f in ob.data.polygons];ob.data.materials.clear()
  for material in materials:ob.data.materials.append(material)
  for poly,index in zip(ob.data.polygons,ids):poly.material_index=index
 for scene in [s]:
  bpy.context.window.scene=scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=2
  scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
  scene.world=bpy.data.worlds.new(scene.name+'_World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.36,.4,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
  bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));plane=bpy.context.object
  mat=bpy.data.materials.new('StudioFloor');mat.diffuse_color=(.14,.16,.18,1);plane.data.materials.append(mat)
  for pos,power,size in [((.6,-.8,1.2),80,.7),((-.8,-.2,.8),40,.5),((.2,1.,1.2),100,.5)]:
   data=bpy.data.lights.new('StudioArea','AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new('StudioArea',data);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.3))-ob.location).to_track_quat('-Z','Y').to_euler()
  data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',data);scene.collection.objects.link(camera);scene.camera=camera;data.lens=58
  (O/'Roundtrip').mkdir(exist_ok=True)
  for label,pos,target in [('front',(.65,-.95,.68),(0,0,.05)),('crust',(.25,-.35,.55),(0,0,.065)),('dish',(.35,-.5,.25),(0,0,.025)),('game-distance',(1.2,-1.9,1.1),(0,0,.05))]:
   if os.environ.get('DINK_PIE_VIEW')and label!=os.environ['DINK_PIE_VIEW']:continue
   camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens={'front':65,'crust':100,'dish':90,'game-distance':45}[label];scene.render.filepath=str(O/'Roundtrip'/(scene.name+'-'+label+('-LOD'+os.environ['DINK_PIE_LOD']if os.environ.get('DINK_PIE_LOD')else'')+'.png'));bpy.ops.render.render(write_still=True,scene=scene.name);print('CAPTURED',scene.name,label,flush=True)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
