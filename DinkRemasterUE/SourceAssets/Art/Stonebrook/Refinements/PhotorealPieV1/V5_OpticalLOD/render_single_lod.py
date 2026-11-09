import bpy,json,sys,os,traceback
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
try:
 level=int(os.environ['DINK_PIE_LOD']);assert level in [1,2];BASE=O.parent/'V5_OpticalLOD';BRIDGE=O.parent/'NativeLODExportsV5'
 bpy.ops.wm.open_mainfile(filepath=str(BASE/'PhotorealPieV1_Export.blend'));s=bpy.data.scenes['PieSource'];bpy.context.window.scene=s;materials=list(bpy.data.objects['SM_Pie_Rustic_01_LOD0'].data.materials)
 for old in list(s.objects):old.hide_render=True
 before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(BRIDGE/('SM_Pie_Rustic_01_LOD'+str(level)+'.fbx')),use_custom_normals=True);added=set(bpy.data.objects)-before;meshes=[x for x in added if x.type=='MESH'];assert len(meshes)==1;ob=meshes[0];assert len(ob.data.polygons)==[3046,2048][level-1];ob.hide_render=False
 ids=[f.material_index for f in ob.data.polygons];ob.data.materials.clear()
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
   if label not in ['front','game-distance']:continue
   camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens={'front':65,'crust':100,'dish':90,'game-distance':45}[label];scene.render.filepath=str(O/'Roundtrip'/(scene.name+'-'+label+('-LOD'+os.environ['DINK_PIE_LOD']if os.environ.get('DINK_PIE_LOD')else'')+'.png'));bpy.ops.render.render(write_still=True,scene=scene.name);print('CAPTURED',scene.name,label,flush=True)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
