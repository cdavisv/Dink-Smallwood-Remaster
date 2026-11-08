"""Reapply the anatomical torso mask without altering topology/UV/texture atlases."""
import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(Path(__file__).parent))
from pig_skin import refine_torso_weights
from pig_actions import create_pig_actions
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Working/Pig_Baked.blend'))
ob=bpy.data.objects['SK_Pig_Stonebrook_LOD0'];arm=bpy.data.objects['Armature']
actions=create_pig_actions(arm,bpy.context.scene)
report=refine_torso_weights(ob,arm);row=json.loads((ROOT/'pig_rig_report.json').read_text());row['torso_mask']=report;row['actions']=actions;(ROOT/'pig_rig_report.json').write_text(json.dumps(row,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Working/Pig_Baked.blend'))
arm.data.pose_position='POSE'
for action,frames in [('Pig_Run',[1,4,7,10]),('Pig_Feed',[7])]:
    arm.animation_data.action=bpy.data.actions[action]
    for frame in frames:
        bpy.context.scene.frame_set(frame);bpy.context.scene.render.filepath=str(ROOT/('review_'+action.lower()+'_%02d.png'%frame));bpy.ops.render.render(write_still=True)
print('TORSO MASK REVIEW READY',report,flush=True)
