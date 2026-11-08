import bpy,json,sys,os
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealBarrelV1_Source.blend'))
s=bpy.data.scenes['BarrelStudio'];bpy.context.window.scene=s
s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_x=850;s.render.resolution_y=850;s.render.resolution_percentage=100
(O/'Previews').mkdir(exist_ok=True)
for name,pos,lens,target in [('front',(1.6,-2.3,1.55),58,(0,0,.49)),('back',(-1.7,2.4,1.5),58,(0,0,.49)),('game-distance',(2.3,-3.4,1.9),45,(0,0,.5)),('head',(1.0,-1.3,2.3),62,(0,0,.66))]:
 s.camera.location=pos;s.camera.rotation_euler=(Vector(target)-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.lens=lens;s.render.filepath=str(O/'Previews'/(name+'.png'));bpy.ops.render.render(write_still=True,scene=s.name)
 print('PREVIEW_COMPLETE',name,flush=True)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
