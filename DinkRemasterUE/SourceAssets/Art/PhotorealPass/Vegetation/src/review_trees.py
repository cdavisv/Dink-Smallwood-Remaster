"""blender -b -t 4 --python review_trees.py -- <module> <asset> [shots: full,below,bark,game] [samples] [lod]"""
import bpy, sys, os, math, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas, bl_tree as T
argv = sys.argv[sys.argv.index('--') + 1:]
mod = importlib.import_module(argv[0]); name = argv[1]
shots = argv[2].split(',') if len(argv) > 2 else ['full', 'below', 'bark']
samples = int(argv[3]) if len(argv) > 3 else 48
lod = int(argv[4]) if len(argv) > 4 else 0
bl_atlas.reset(); scene = bpy.context.scene
T.setup_review(scene, samples=samples)
ob = mod.build(name, lod)
lo, hi = T.bounds(ob); H = hi[2]; Wd = max(hi[0] - lo[0], hi[1] - lo[1])
print('STATS', name, 'lod', lod, 'tris', T.tri_count(ob), 'dims', (hi - lo).round(2).tolist(), flush=True)
T.ref_box((Wd * 0.5 + 0.8, -0.5, 0) if (hi[1] - lo[1]) <= 1.5 * (hi[0] - lo[0]) else (0.5, -(Wd * 0.5 + 0.8), 0))
R = os.path.join(HERE, '..', 'Review'); tag = f'{name}_LOD{lod}' if lod else name
tag += os.environ.get('VEG_TAG', '')
if 'sky' in shots:   # whole tree against the sky from 20 m at game resolution (1280x720)
    dist = float(os.environ.get('VEG_SKYDIST', '20')); T.camera(scene, (dist * 0.2, -dist, 1.7), (0, 0, H * 0.5), lens=max(14, 0.95 * dist * 10.1 / (H * 0.56)))
    T.render(scene, f'{R}/{tag}_sky.png', (1280, 720))
if 'close' in shots:  # 2-3 m from the foliage at the crown edge
    T.camera(scene, (Wd * 0.5 + 1.6, -1.4, 1.9), (Wd * 0.3, 0.2, min(H * 0.45, 3.2)), lens=32)
    T.render(scene, f'{R}/{tag}_close.png', (1280, 720))
if 'near' in shots:   # bush: eye level from 2.2 m
    T.camera(scene, (0.6, -(Wd * 0.5 + 2.2), 1.5), (0, 0, H * 0.45), lens=32)
    T.render(scene, f'{R}/{tag}_near.png', (1280, 720))
if 'top' in shots:    # game camera: 45 degrees down from 8 m
    T.camera(scene, (0, -8.0, 8.0), (0, 0, H * 0.3), lens=50)
    T.render(scene, f'{R}/{tag}_top.png', (1280, 720))
if 'full' in shots:
    dist = max(H * 1.55, Wd * 2.0)
    side = (hi[1] - lo[1]) > 1.5 * (hi[0] - lo[0])
    T.camera(scene, (dist, dist * 0.25, 2.0 + H * 0.12) if side else (dist * 0.25, -dist, 2.0 + H * 0.12), (0, 0.4, H * 0.48) if side else (0.4, 0, H * 0.48), lens=40)
    T.render(scene, f'{R}/{tag}_full.png', (900, 1200))
if 'game' in shots:  # gameplay camera: hero 7 m in front of the tree, camera 4 m behind and 2 m above the hero
    T.camera(scene, (1.0, -11.0, 3.6), (0, 0, 2.6), lens=24)
    T.render(scene, f'{R}/{tag}_game.png', (1200, 800))
if 'below' in shots:
    T.camera(scene, (1.3, -1.9, 1.5), (0.3, 0.4, H * 0.62), lens=20)
    T.render(scene, f'{R}/{tag}_below.png', (900, 900))
if 'bark' in shots:
    tr = float(ob.get('trunk_r', 0.25)); T.camera(scene, (0.35, -(1.0 + tr), 1.25), (0, 0, 1.0), lens=35)
    T.render(scene, f'{R}/{tag}_bark.png', (900, 900))
