"""Dump the rest-pose trunk profile of an assembled character for arm_clearance.py: per 1 cm slice the extents of the
vertices that belong to the trunk (not arms, not legs), and the rest heads of the spine and arm bones, in the engine's
mesh axes (Blender x, -y, z) and centimetres.
  blender -b <SK_<Name>_Photoreal.blend> --python Scripts/AnimationQA/trunk_profile.py -- <out.json>"""
import bpy, sys, json, numpy as np
out = sys.argv[sys.argv.index('--') + 1]
ob = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith('_LOD0')); arm = bpy.data.objects['Armature']
gn = {g.index: g.name for g in ob.vertex_groups}
ARM = ('upperarm', 'lowerarm', 'hand', 'index', 'middle', 'ring', 'pinky', 'thumb'); LEG = ('thigh', 'calf', 'foot', 'ball')
P = []; 
for v in ob.data.vertices:
    wa = sum(g.weight for g in v.groups if any(gn[g.group].startswith(a) for a in ARM)); wl = sum(g.weight for g in v.groups if any(gn[g.group].startswith(a) for a in LEG))
    if wa < .25 and wl < .5: P.append((v.co.x * 100, -v.co.y * 100, v.co.z * 100))
P = np.array(P); sl = []
for z in range(80, 156):
    m = (P[:, 2] >= z - .5) & (P[:, 2] < z + .5)
    if m.sum() < 6: continue
    q = P[m]; sl.append([z, float(q[:, 0].min()), float(q[:, 0].max()), float(q[:, 1].min()), float(q[:, 1].max())])
bones = {b.name: [b.head_local.x * 100, -b.head_local.y * 100, b.head_local.z * 100] for b in arm.data.bones if b.name in ('pelvis', 'spine_01', 'spine_03', 'spine_05', 'neck_01', 'head', 'clavicle_l', 'clavicle_r', 'upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r', 'hand_l', 'hand_r', 'thigh_l', 'thigh_r')}
json.dump({'slices': sl, 'bones': bones}, open(out, 'w')); print('TRUNK', len(P), len(sl), bones['upperarm_l'], bones['lowerarm_l'], bones['hand_l'])
