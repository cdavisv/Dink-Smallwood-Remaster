import bpy,math
from pathlib import Path
from mathutils import Vector
p=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(p/'KIT_StonebrookFields.blend'));scene=bpy.data.scenes.new('PineLODComparison');bpy.context.window.scene=scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('LODworld');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.65,.8,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
for lod,x in [(0,-8),(1,0),(2,8)]:
 source=bpy.data.objects['SM_Pine_Stonebrook_01_LOD'+str(lod)];ob=source.copy();ob.data=source.data;ob.location.x=x;ob.hide_render=False;scene.collection.objects.link(ob)
light=bpy.data.lights.new('LODsun','SUN');light.energy=3;ob=bpy.data.objects.new('LODsun',light);scene.collection.objects.link(ob);ob.rotation_euler=(.4,-.5,-.8)
cam=bpy.data.cameras.new('LODcamera');ob=bpy.data.objects.new('LODcamera',cam);scene.collection.objects.link(ob);ob.location=(18,-35,14);ob.rotation_euler=(Vector((0,0,6))-ob.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=32;scene.camera=ob;scene.render.filepath=str(p/'preview_pine_lods.png');bpy.ops.render.render(write_still=True)
