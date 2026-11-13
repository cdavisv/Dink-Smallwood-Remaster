"""Review renders of the hero's three builds side by side (Cycles, sun + sky, idle pose).
blender -b -P render_physique.py -- <out dir rel to Characters> <tag> [views: front,threeq,back,side,game] [pose] [samples]"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *
import physique as PH
a = args(); outdir = OUT / a[0]; tag = a[1]; views = (a[2] if len(a) > 2 else 'front,threeq,back').split(',')
pose = a[3] if len(a) > 3 else 'idle'; samples = int(a[4]) if len(a) > 4 else 40
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/SK_Dink_Photoreal.blend')); outdir.mkdir(parents=True, exist_ok=True)
D = bpy.data.objects; sc = bpy.context.scene; arm = D['Armature']; arm.data.pose_position = 'POSE'
lod = int(os.environ.get('PR_LOD', '0')); mesh = D['SK_Dink_Photoreal_LOD%d' % lod]
for o in D:
    if o.type == 'MESH': o.hide_render = o is not mesh
setup_render(samples=samples, res=(560, 1000)); sc.world.node_tree.nodes['Background'].inputs[1].default_value = .085
if pose == 'idle': apply_world_pose(arm, load_idle())
elif pose == 'reach':
    apply_world_pose(arm, load_idle()); rot_bone(arm, 'upperarm_l', (0, 1, 0), -95); rot_bone(arm, 'upperarm_r', (1, 0, 0), -80); rot_bone(arm, 'lowerarm_r', (1, 0, 0), -60)
elif pose != 'rest':
    import json as _j; apply_world_pose(arm, _j.loads((Path(__file__).parent / 'pose_cache/walk_poses.json').read_text())[pose])
CAM = {'front': ((0.0, -5.4, 1.2), (0, 0, .93), 85), 'threeq': ((3.3, -4.0, 1.35), (0, 0, .93), 85), 'back': ((-0.3, 5.4, 1.25), (0, 0, .93), 85),
       'side': ((5.4, 0.0, 1.2), (0, 0, .93), 85), 'game': ((1.7, -2.6, 2.1), (0, 0, .95), 38),
       'torso': ((0.0, -2.6, 1.3), (0, 0, 1.28), 85), 'torsoq': ((1.7, -2.0, 1.4), (0, 0, 1.28), 85), 'torsob': ((-0.9, 2.5, 1.4), (0, 0, 1.28), 85),
       'legs': ((0.6, -2.7, .8), (0, 0, .62), 85), 'hip': ((2.4, -1.2, 1.0), (0, 0, .95), 85)}
keys = mesh.data.shape_keys.key_blocks
def montage(files, out):
    ims = [bpy.data.images.load(str(f)) for f in files]; w = sum(i.size[0] for i in ims); h = max(i.size[1] for i in ims)
    buf = np.zeros((h, w, 4), np.float32); x = 0
    for i in ims:
        px = np.empty(i.size[0] * i.size[1] * 4, np.float32); i.pixels.foreach_get(px); buf[:i.size[1], x:x + i.size[0]] = px.reshape(i.size[1], i.size[0], 4); x += i.size[0]
    o = bpy.data.images.new('montage', w, h); o.pixels.foreach_set(buf.ravel()); o.filepath_raw = str(out); o.file_format = 'PNG'; o.save()
    for f in files: os.remove(f)
STAGES = [('scrawny', 1, 0), ('farmhand', 0, 0), ('brawny', 0, 1)] if not os.environ.get('PR_STAGES') else \
    [(s.split(':')[0], float(s.split(':')[1]), float(s.split(':')[2])) for s in os.environ['PR_STAGES'].split(',')]
for v in views:
    loc, tgt, lens = CAM[v]; fs = []
    for name, s, b in STAGES:
        keys[PH.KEY % 'Scrawny'].value = s; keys[PH.KEY % 'Brawny'].value = b; bpy.context.view_layer.update()
        f = outdir / ('%s_%s_%s.png' % (tag, v, name)); shoot(f, loc, tgt, lens=lens, res=(700, 760) if v in ('torso', 'torsoq', 'torsob', 'legs', 'hip') else (560, 1000)); fs.append(f)
    montage(fs, outdir / ('%s_%s.png' % (tag, v)))
log('PHYSIQUE RENDERS DONE')
