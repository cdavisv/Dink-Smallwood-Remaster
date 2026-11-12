import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/Work/dink_base.blend'))
arm = bpy.data.objects['Armature']; B = arm.data.bones
sh = dup(bpy.data.objects['OldShirtTopo'], 'Shirt')
for nm in ('OldHair', 'OldEyes', 'BrowLash'): bpy.data.objects[nm].hide_render = True
subdivide(sh, 1)
co = co_np(sh.data); nr = normals_np(sh.data)
S = np.array(B['upperarm_l'].head_local); E_ = np.array(B['lowerarm_l'].head_local); H = np.array(B['hand_l'].head_local)
d = (E_ - S) / np.linalg.norm(E_ - S)
m = co.copy(); m[:, 0] = np.abs(m[:, 0])
s = (m - S) @ d  # along upper arm from shoulder
f = (m - E_) @ ((H - E_) / np.linalg.norm(H - E_))
arm_mask = sstep(-.01, .05, s)
# collider: torso out 8mm (jerkin), arms in 6mm
col = dup(sh, 'Collider'); set_co(col.data, co + nr * (.008 - .014 * arm_mask)[:, None])
pin = 1 - sstep(.0, .05, s)
pin = np.maximum(pin, sstep(.10, .13, f))
vgroup(sh, 'pin', pin)
set_co(sh.data, co + nr * (.006 * arm_mask)[:, None])
old = bpy.data.objects['OldWardrobe']
settle_cloth(sh, [col], 'pin', frames=int(args()[0]) if args() else 30, grow=.06)
smooth_shade(sh)
mat = bpy.data.materials.new('clay'); mat.use_nodes = True; mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.35, .42, .5, 1)
sh.data.materials.clear(); sh.data.materials.append(mat)
bpy.data.objects['OldShirtTopo'].hide_render = True; bpy.data.objects['OldTrousersTopo'].hide_render = True; col.hide_render = True
setup_render(samples=24, res=(900, 900))
shoot(OUT / 'Dink/Review/exp_sim_front.png', (0.9, -2.6, 1.5), (0, 0, 1.25), lens=60)
save_blend(filepath=str(OUT / 'Dink/Work/exp_sim.blend'))
