"""blender -b -t 4 --python review_meadow.py -- <tag> [game] [eye] [close] [single] [short] [dry]
6x6 m carpet of the tall patches instanced with random yaw / scale on the MeadowTurf set; renders into Review/Meadow_<view>_<tag>.png"""
import bpy, sys, os, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas, bl_tree as T, veg_meadow as M
argv = sys.argv[sys.argv.index('--') + 1:]; tag = argv[0]; views = argv[1:]
bl_atlas.reset(); scene = bpy.context.scene
T.setup_review(scene, samples=int(os.environ.get('VEG_SAMPLES', '40')))
scene.cycles.transparent_max_bounces = 200      # many alpha cards in a row at eye level: the default 24 runs out and renders black
R = os.path.join(HERE, '..', 'Review')
def inst(ob, loc, yaw, s=1.0):
    o = bpy.data.objects.new(ob.name + '_i', ob.data); scene.collection.objects.link(o); o.location = loc; o.rotation_euler = (0, 0, yaw); o.scale = (s, s, s); return o
rng = np.random.default_rng(11); obs = {n: M.build(n, 0) for n in M.MEADOW}
for o in obs.values(): o.location = (100, 100, 0)
kind = 'short' if 'short' in views else 'dry' if 'dry' in views else 'tall'
names = [n for n in obs if {'short': 'Short', 'dry': 'Dry', 'tall': 'Tall'}[kind] in n]
sp = 0.5; n = 12
if 'single' in views:
    for i, nm in enumerate(M.MEADOW): inst(obs[nm], ((i - 2.5) * 1.3, 0, 0), 0.3)
    for i, nm in enumerate(M.MEADOW):
        for l in (1, 2): M.build(nm, l).location = ((i - 2.5) * 1.3, 1.4 * l, 0)
    T.ref_box((4.6, 0.3, 0))
    T.camera(scene, (0, -6.5, 3.2), (0, 0, 0.15), lens=40); T.render(scene, f'{R}/Meadow_singles_{tag}.png', (1600, 620), exposure=0.5)
else:
    for ix in range(n):
        for iy in range(n):
            x = (ix - (n - 1) / 2) * sp + rng.uniform(-0.2, 0.2); y = (iy - (n - 1) / 2) * sp + rng.uniform(-0.2, 0.2)
            inst(obs[names[rng.integers(len(names))]], (x, y, 0), rng.uniform(0, 6.28), rng.uniform(0.8, 1.25))
    T.ref_box((3.6, 0.5, 0))
    if 'game' in views: T.camera(scene, (0, -8.0, 8.0), (0, 0, 0), lens=50); T.render(scene, f'{R}/Meadow_{kind}_game_{tag}.png', (1280, 720), exposure=0.5)
    if 'eye' in views: T.camera(scene, (0.5, -5.2, 1.6), (0, 0, 0.25), lens=30); T.render(scene, f'{R}/Meadow_{kind}_eye_{tag}.png', (1280, 720), exposure=0.5)
    if 'close' in views: T.camera(scene, (0.2, -3.6, 0.5), (0, -2.2, 0.25), lens=40); T.render(scene, f'{R}/Meadow_{kind}_close_{tag}.png', (1280, 720), exposure=0.5)
