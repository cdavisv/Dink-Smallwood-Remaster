"""Sample the Epic walk reference (read-only, review only) into armature-space bone matrices in metres."""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *
p = '<HOME>/Work/DinkQA/CharacterReference/Manny_Walk_Reference.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=p, automatic_bone_orientation=False, use_anim=True)
ref = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE'); act = ref.animation_data.action
s, e = act.frame_range; out = {}
def norm(m, root):
    o = m.to_quaternion().to_matrix().to_4x4(); o.translation = m.translation - root; return o
for frac in (.0, .2, .45, .7):
    f = round(s + (e - s) * frac); bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
    root = ref.matrix_world.translation.copy()
    out['walk_%02d' % int(frac * 100)] = {b.name: [list(r) for r in norm(ref.matrix_world @ b.matrix, root)] for b in ref.pose.bones}
json.dump(out, open(os.path.join(os.path.dirname(__file__), 'pose_cache', 'walk_poses.json'), 'w'))
print('[PR] walk poses', list(out), len(ref.pose.bones))
