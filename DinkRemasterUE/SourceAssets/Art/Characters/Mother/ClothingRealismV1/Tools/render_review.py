"""Actual CPU Cycles review renders from packed source; same neutral studio all views."""
import bpy,math,sys
from pathlib import Path
from mathutils import Vector
H=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str((H.parents[1]/'SK_Mother.blend')if'--baseline'in sys.argv else(H/'SK_Mother_ClothingRealismV1.blend')));s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=1
s.render.resolution_x=850;s.render.resolution_y=1100;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
s.world.color=(.18,.18,.18)
for o in bpy.data.objects:
 if o.type=='MESH':o.hide_render=o.name!='SK_Mother_LOD0'
for o in list(bpy.data.objects):
 if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
def light(name,pos,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
light('Large softbox',(2.2,-3,3),450,2.3);light('Soft fill',(-2,-1.2,2.2),200,2);light('Rim',(0,2,2.6),400,1.6)
cam=s.camera;cam.data.lens=65
views={'front':((1.1,-3.7,1.55),(0,0,.9),65),'back':((-1.1,3.7,1.55),(0,0,.9),65),'fabric-detail':((.15,-1.35,1.36),(0,-.12,1.23),80)}
views['linen-detail']=((.1,-1.5,.80),(0,-.23,.64),80)
if '--baseline'in sys.argv:views={'baseline-front':views['front']}
if '--detail'in sys.argv:views={'fabric-detail':views['fabric-detail']}
if '--full'in sys.argv:views={k:v for k,v in views.items()if k!='fabric-detail'}
for name,(pos,target,lens)in views.items():
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens
 s.render.resolution_x=900 if name in ['fabric-detail','linen-detail']else 850;s.render.resolution_y=750 if name in ['fabric-detail','linen-detail']else 1100
 s.render.filepath=str(H/'Renders'/('mother-'+name+'.png'));bpy.ops.render.render(write_still=True);print('RENDERED',name,flush=True)
