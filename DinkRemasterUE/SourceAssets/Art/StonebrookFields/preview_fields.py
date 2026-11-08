"""Read-only Blender presentation renders of the new source candidate."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ART=Path(__file__).resolve().parent;ROOT=ART.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ART/'KIT_StonebrookFields.blend'))
with bpy.data.libraries.load(str(ROOT/'SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend'),link=False) as (src,dst):
 dst.collections=[n for n in src.collections if n in ['SM_Oak_Stonebrook_01','SM_Boulder_Fieldstone_01','SM_Grass_Meadow_01']]
# The old kit stores presentation offsets in object locations. Its exporter removes
# those using at_origin; normalize them for collection-instance source previews too.
for name in ['SM_Oak_Stonebrook_01','SM_Boulder_Fieldstone_01','SM_Grass_Meadow_01']:
 c=bpy.data.collections[name];ref=next(o for o in c.objects if o.name in [name,name+'_LOD0']);delta=ref.location.copy()
 for ob in c.objects:
  ob.location-=delta
for ob in bpy.data.objects:
 if '_LOD1' in ob.name or '_LOD2' in ob.name:ob.hide_render=True
def setup(name):
 scene=bpy.data.scenes.new(name);bpy.context.window.scene=scene
 scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
 scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
 scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new(name+'World');scene.world.use_nodes=True
 scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.65,.8,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
 light=bpy.data.lights.new(name+'Sun','SUN');light.energy=3.;light.angle=.14
 ob=bpy.data.objects.new(name+'Sun',light);scene.collection.objects.link(ob);ob.rotation_euler=(.4,-.4,-.6)
 cam=bpy.data.cameras.new(name+'Camera');camera=bpy.data.objects.new(name+'Camera',cam);scene.collection.objects.link(camera);scene.camera=camera;cam.type='ORTHO'
 return scene,camera
def aim(ob,point):ob.rotation_euler=(Vector(point)-ob.location).to_track_quat('-Z','Y').to_euler()
screens=json.loads((ROOT/'ImportData/screens.json').read_text())['screens']
for sid in [471,438]:
 layout=json.loads((ART/f'fields_{sid}_layout.json').read_text());screen=next(s for s in screens if s['screen']==sid)
 center=screen['center'];nw,ne,se,sw=[screen['corners'][k] for k in ['nw','ne','se','sw']]
 scene,camera=setup('Fields'+str(sid))
 for e in layout['elements']:
  c=bpy.data.collections.get(e['mesh'])
  if not c:continue
  inst=bpy.data.objects.new(e['name'],None);inst.instance_type='COLLECTION';inst.instance_collection=c;scene.collection.objects.link(inst)
  u,v=e['source_pixel'][0]/600,e['source_pixel'][1]/400
  w=[nw[i]*(1-u)*(1-v)+ne[i]*u*(1-v)+se[i]*u*v+sw[i]*(1-u)*v for i in range(2)]
  inst.location=(w[0]-center[0],-(w[1]-center[1]),e['height_cm']/100)
  inst.rotation_euler[2]=-math.radians(e['rotation_deg'][1]);inst.scale=e['scale']
 camera.location=(-25,-48,57);aim(camera,(0,0,0));camera.data.ortho_scale=74
 scene.render.filepath=str(ART/f'preview_blender_{sid}.png');bpy.ops.render.render(write_still=True)
scene,camera=setup('PinePortrait')
c=bpy.data.collections['SM_Pine_Stonebrook_01']
# Link only the finest LOD to avoid rendering all three coincident meshes.
ob=bpy.data.objects['SM_Pine_Stonebrook_01_LOD0'];scene.collection.objects.link(ob)
camera.location=(18,-22,13);aim(camera,(0,0,6.2));camera.data.ortho_scale=20
scene.render.filepath=str(ART/'preview_pine.png');bpy.ops.render.render(write_still=True)
print('SOURCE PREVIEWS:3 rendered; source blend unchanged')
