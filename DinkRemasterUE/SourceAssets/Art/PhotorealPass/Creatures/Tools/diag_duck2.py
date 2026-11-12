import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Duck/SK_Duck.blend')); arm = bpy.data.objects['Armature']
mode = args()[0]
o = bpy.data.objects['SK_Duck_LOD0']
for ob in bpy.data.objects:
    if ob.type == 'MESH': ob.hide_render = ob.name != 'SK_Duck_LOD0'
if mode == 'nonrm':
    for s in o.material_slots:
        nt = s.material.node_tree
        for n in nt.nodes:
            if n.type == 'NORMAL_MAP':
                for l in list(n.outputs[0].links): nt.links.remove(l)
if mode == 'nocustom':
    o.data.attributes.remove(o.data.attributes['custom_normal']) if 'custom_normal' in o.data.attributes else log('no custom_normal attr', [a.name for a in o.data.attributes])
if mode == 'nosss':
    for s in o.material_slots:
        for n in s.material.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED': 
                for l in list(n.inputs['Subsurface Weight'].links): s.material.node_tree.links.remove(l)
                n.inputs['Subsurface Weight'].default_value = 0
setup_review(samples=32, ground='leafy_grass', ground_scale=1.2)
set_action(arm, 'Duck_Idle', 10)
shoot('/tmp/crk/diag_%s.png' % mode, (.50, -.40, .50), (.12, 0, .40), 85, (600, 450), 32, exposure=-.7)
