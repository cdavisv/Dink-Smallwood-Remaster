import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/Work/exp_sim.blend'))
bpy.data.objects['OldWardrobe'].hide_render = True
sh = bpy.data.objects['Shirt']
c = co_np(sh.data); log('shirt bbox', c.min(0), c.max(0))
mat = bpy.data.materials['clay']; sh.data.materials.clear(); sh.data.materials.append(mat)
for p in sh.data.polygons: p.material_index = 0
setup_render(samples=24, res=(900, 700))
bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = float(args()[0])
shoot(OUT / 'Dink/Review/exp_sim_front.png', (0.5, -2.2, 1.5), (0, 0, 1.25), lens=60)
