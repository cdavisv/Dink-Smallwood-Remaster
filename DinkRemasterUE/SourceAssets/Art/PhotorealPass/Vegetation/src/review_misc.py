"""blender -b -t 4 --python review_misc.py -- patch|dead|group|single [args] ; renders into Review/"""
import bpy, sys, os, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas, bl_tree as T
argv = sys.argv[sys.argv.index('--') + 1:]; mode = argv[0]
bl_atlas.reset(); scene = bpy.context.scene
samples = int(os.environ.get('VEG_SAMPLES', '48'))
T.setup_review(scene, samples=samples)
R = os.path.join(HERE, '..', 'Review')
def inst(ob, loc, yaw, s=1.0):
    o = bpy.data.objects.new(ob.name + '_i', ob.data); scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, yaw); o.scale = (s, s, s); return o
if mode == 'patch':
    import veg_ground as G
    rng = np.random.default_rng(5); obs = {n: G.build(n, 0) for n in G.GROUND}
    for o in obs.values(): o.location = (100, 100, 0)
    grass = [n for n in obs if 'Grass_Meadow' in n]
    def scatter(names, count, ext=2.3):
        for i in range(count):
            n = names[rng.integers(len(names))]; inst(obs[n], (rng.uniform(-ext, ext), rng.uniform(-ext, ext + 2), 0), rng.uniform(0, 6.28), rng.uniform(0.8, 1.2))
    scatter(grass, 150, 2.6); scatter(['SM_Veg_Weed_Small_01', 'SM_Veg_Weed_Small_02'], 16); scatter(['SM_Veg_Weed_Sprig_01'], 9)
    scatter(['SM_Veg_Flowers_01', 'SM_Veg_Flowers_02'], 8); scatter(['SM_Veg_Mushroom_01', 'SM_Veg_Mushroom_02'], 5, 1.5)
    T.ref_box((2.6, 0.5, 0))
    T.camera(scene, (0, -6.0, 2.9), (0, 0.3, 0.3), lens=28); T.render(scene, f'{R}/GroundCover_patch_game.png', (1200, 800), exposure=0.7)
    T.camera(scene, (0.4, -2.2, 0.75), (0, 0, 0.2), lens=32); T.render(scene, f'{R}/GroundCover_patch_close.png', (1200, 800), exposure=0.7)
elif mode == 'line':    # every ground cover asset in a row, close
    import veg_ground as G
    names = list(G.GROUND)
    names = [n for n in names if 'Bed' not in n]; row = [n for n in names if 'Patch' not in n and 'Cabbage' not in n]; row2 = [n for n in names if n not in row]
    for i, n in enumerate(row): G.build(n, 0).location = ((i - (len(row) - 1) / 2) * 0.62, 0, 0)
    for i, n in enumerate(row2): G.build(n, 0).location = ((i - (len(row2) - 1) / 2) * 1.2, -1.3, 0)
    T.camera(scene, (0, -6.2, 2.1), (0, -0.5, 0.25), lens=28); T.render(scene, f'{R}/GroundCover_line.png', (2000, 760), exposure=0.5)
    T.camera(scene, (1.24, -1.1, 0.5), (1.24, 0.0, 0.2), lens=40); T.render(scene, f'{R}/GroundCover_flowers_close.png', (1200, 700), exposure=0.5)
    T.camera(scene, (2.48, -0.75, 0.3), (2.48, 0.0, 0.06), lens=45); T.render(scene, f'{R}/GroundCover_mushrooms_close.png', (1200, 700), exposure=0.5)
    for o in list(scene.objects):
        if o.name.startswith('SM_Veg'): o.hide_render = True
    b = G.build('SM_Veg_FlowerBed_Row_01', 0); T.ref_box((2.9, 0.3, 0))
    T.camera(scene, (1.0, -5.4, 2.6), (0, 0, 0.1), lens=30); T.render(scene, f'{R}/SM_Veg_FlowerBed_Row_01.png', (1200, 760), exposure=0.5)
    b.hide_render = True
    import numpy as np
    rng = np.random.default_rng(3); ps = [G.build(n, 0) for n in G.PATCH]
    for p in ps: p.location = (50, 50, 0)
    for ix in range(-3, 4):
        for iy in range(-3, 4):
            o = inst(ps[rng.integers(3)], (ix * 0.8 + rng.uniform(-0.1, 0.1), iy * 0.8 + rng.uniform(-0.1, 0.1), 0), rng.uniform(0, 6.28), rng.uniform(0.9, 1.15))
    T.camera(scene, (0, -6.0, 2.9), (0, 0.3, 0.2), lens=28); T.render(scene, f'{R}/GrassPatch_carpet_game.png', (1200, 800), exposure=0.5)
    T.camera(scene, (0.3, -3.6, 0.6), (0, 0, 0.12), lens=32); T.render(scene, f'{R}/GrassPatch_carpet_close.png', (1200, 800), exposure=0.5)
elif mode == 'under':
    import veg_under as U_, veg_broadleaf as B_
    lay = [(U_, 'SM_Veg_ThornBush_01', (-4.2, 0)), (U_, 'SM_Veg_ThornBush_02', (-1.9, 0)), (U_, 'SM_Veg_ThornBranch_01', (-0.5, -0.9)), (U_, 'SM_Veg_Fern_01', (0.3, 0.2)), (U_, 'SM_Veg_Fern_02', (1.5, -0.6)),
           (U_, 'SM_Veg_HangingVines_01', (2.7, 0.4)), (U_, 'SM_Veg_HangingVines_02', (4.2, 0.4)),
           (B_, 'SM_Veg_Bush_Small_01', (-4.0, 3.2)), (B_, 'SM_Veg_Bush_Round_Medium_01', (-2.0, 3.2)), (B_, 'SM_Veg_Bush_Round_Large_01', (0.4, 3.4)), (B_, 'SM_Veg_Bush_Wide_01', (3.6, 3.4))]
    for m, n, (x, y) in lay: m.build(n, 0).location = (x, y, 0)
    T.ref_box((5.6, 1.5, 0))
    T.camera(scene, (0.5, -9.5, 3.6), (0.3, 1.2, 0.5), lens=30); T.render(scene, f'{R}/Understory_group.png', (1500, 800), exposure=0.3)
    T.camera(scene, (-3.2, -3.2, 1.3), (-3.0, 0, 0.4), lens=30); T.render(scene, f'{R}/SM_Veg_ThornBush_close.png', (1100, 750), exposure=0.3)
    T.camera(scene, (1.0, -2.6, 1.0), (0.8, -0.1, 0.25), lens=30); T.render(scene, f'{R}/SM_Veg_Fern_close.png', (1100, 750), exposure=0.3)
    T.camera(scene, (-0.5, 0.0, 1.2), (0.6, 3.4, 0.5), lens=30); T.render(scene, f'{R}/SM_Veg_Bush_close.png', (1100, 750), exposure=0.3)
    T.camera(scene, (3.4, -3.0, 1.7), (3.4, 0.4, 1.5), lens=30); T.render(scene, f'{R}/SM_Veg_HangingVines_close.png', (800, 900), exposure=0.3)
elif mode == 'dead':
    import veg_deadwood as D
    pos = {'SM_Veg_Stump_01': (-2.2, 0.6), 'SM_Veg_Stump_02': (-0.7, 1.2), 'SM_Veg_FallenLog_01': (1.4, 1.2), 'SM_Veg_FallenBranch_Forked_01': (0.6, -0.9), 'SM_Veg_TwigCluster_01': (-1.4, -1.0)}
    for n, (x, y) in pos.items(): D.build(n, 0).location = (x, y, 0)
    T.ref_box((3.4, 1.0, 0))
    T.camera(scene, (0.2, -5.6, 2.6), (0.2, 0.3, 0.2), lens=30); T.render(scene, f'{R}/Deadwood_group.png', (1200, 800), exposure=0.5)
    if len(argv) > 1:
        T.camera(scene, (-2.2 + 0.5, 0.6 - 1.2, 0.85), (-2.2, 0.6, 0.3), lens=30); T.render(scene, f'{R}/SM_Veg_Stump_01_close.png', (900, 900), exposure=0.5)
        T.camera(scene, (1.4 - 1.4, 1.2 - 1.5, 0.8), (1.4 - 0.6, 1.2, 0.15), lens=30); T.render(scene, f'{R}/SM_Veg_FallenLog_01_close.png', (900, 900), exposure=0.5)
        T.camera(scene, (0.4, -2.6, 0.9), (0.2, -0.9, 0.1), lens=30); T.render(scene, f'{R}/SM_Veg_FallenBranch_close.png', (900, 900), exposure=0.5)
elif mode == 'group':
    import veg_pine, veg_broadleaf
    lay = [(veg_pine, 'SM_Veg_Pine_Large_01', (-24, 6)), (veg_pine, 'SM_Veg_Pine_Medium_01', (-15, -2)), (veg_pine, 'SM_Veg_Pine_Storm_01', (-7, 7)),
           (veg_broadleaf, 'SM_Veg_Willow_01', (3, -4)), (veg_broadleaf, 'SM_Veg_Oak_Large_01', (12, 8)), (veg_broadleaf, 'SM_Veg_Oak_Large_02', (23, 0)), (veg_broadleaf, 'SM_Veg_Willow_Large_01', (36, 8)),
           (veg_pine, 'SM_Veg_Pine_Dry_01', (-34, 0)), (veg_pine, 'SM_Veg_Pine_Burnt_01', (-42, 6)),
           (veg_broadleaf, 'SM_Veg_DeadTree_Dark_01', (49, 2)), (veg_broadleaf, 'SM_Veg_DeadTree_DarkTall_01', (60, 8)), (veg_broadleaf, 'SM_Veg_DeadTree_Frosted_01', (68, 0))]
    for m, n, (x, y) in lay: m.build(n, 0).location = (x, y, 0)
    T.ref_box((-3, -8, 0))
    T.camera(scene, (13, -105, 6.0), (13, 0, 7.0), lens=30); T.render(scene, f'{R}/Trees_group.png', (2600, 760))
