import bpy,json,os,sys,traceback
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
try:
 bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealBasketV1_Source.blend'));s=bpy.data.scenes['BasketSource'];bpy.context.window.scene=s
 mode=os.environ.get('DINK_BASKET_RENDER_MODE','source');assert mode in ['source','baked','roundtrip']
 if mode!='source':
  bpy.data.objects['SM_Basket_Wicker_01'].hide_render=True
  with bpy.data.libraries.load(str(O/'PhotorealBasketV1_Export.blend'),link=False)as(src,dst):dst.materials=['MI_Basket_Wicker_01_PhotoBaked']
  material=dst.materials[0]
  if mode=='roundtrip':
   before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Export/Game/Dink/Props/Stonebrook/PhotorealBasketV1/SM_Basket_Wicker_01.fbx'),use_custom_normals=True);added=set(bpy.data.objects)-before
   ob=next(x for x in added if x.type=='MESH'and not x.name.startswith('UCX_'))
   for item in added:item.hide_render=item!=ob
   ob.data.transform(ob.matrix_world);ob.matrix_world.identity()
  else:
   with bpy.data.libraries.load(str(O/'PhotorealBasketV1_Export.blend'),link=False)as(src,dst):dst.objects=['SM_Basket_Wicker_01']
   ob=dst.objects[0];s.collection.objects.link(ob)
  ob.data.materials.clear();ob.data.materials.append(material)
  for polygon in ob.data.polygons:polygon.material_index=0
 s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100
 s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.36,.4,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.35
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));plane=bpy.context.object;mat=bpy.data.materials.new('Floor');mat.diffuse_color=(.14,.16,.18,1);plane.data.materials.append(mat)
 for pos,power,size in [((1.4,-2,3),300,2),((-2,-.2,1.8),150,1.5),((.2,2.2,2.8),350,1.3)]:
  data=bpy.data.lights.new('StudioArea','AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new('StudioArea',data);s.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.3))-ob.location).to_track_quat('-Z','Y').to_euler()
 data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',data);s.collection.objects.link(camera);s.camera=camera
 o=O/({'source':'DetailReview','baked':'BakedReview','roundtrip':'Roundtrip'}[mode]);o.mkdir(exist_ok=True)
 for label,pos,target,lens in [('front',(1.4,-1.8,1.3),(0,0,.32),58),('handle',(1.1,-.65,1.2),(.43,0,.55),85),('weave',(.9,-1.3,.9),(0,-.30,.33),95),('game-distance',(2.4,-3.4,2.1),(0,0,.34),45)]:
  if os.environ.get('DINK_BASKET_VIEW') and label!=os.environ['DINK_BASKET_VIEW']:continue
  camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=lens;s.render.filepath=str(o/(label+'.png'));bpy.ops.render.render(write_still=True,scene=s.name);print('CAPTURED',label,flush=True)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
