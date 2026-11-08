import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SK_Pillbug.blend'))
scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.data.pose_position='POSE';scene.cycles.samples=24
for key,frame in [('Idle',1),('Run',5),('Run',9)]:
 arm.animation_data.action=bpy.data.actions['Pillbug_'+key];scene.frame_set(frame);scene.render.filepath=str(ROOT/'Previews'/('pillbug_baked_'+key.lower()+'_%02d.png'%frame));bpy.ops.render.render(write_still=True)
