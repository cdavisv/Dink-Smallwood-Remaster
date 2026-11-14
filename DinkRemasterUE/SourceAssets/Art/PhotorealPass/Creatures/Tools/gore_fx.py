"""Shared gore pieces for the creature layer (the owner's rule: keep all of the 1997 gore, and more of it).

  Gore/Export/SM_BloodDrop.fbx          a 1 cm teardrop, +X is the direction of flight; the game instances and stretches it
  Gore/Textures/T_BloodBurst_BC.png     RGBA, seen from above: a burst with thrown streaks and drops (sprite sequence 164)
  Gore/Textures/T_BloodPuddle_BC.png    RGBA: a round pool with a few drops (under a severed head; a trail stain)
  Duck/Export/SM_Duck_HeadFlying.fbx    the severed duck head without its pool, centred, for the flight (sequences 121-129)

  Slime/Export/SM_Slime_Splat.fbx       what a killed slime leaves (sequences 661/663, 681/683, 701/703: a splatter of its gel)
  Slime/Textures/T_SlimeSplat_<Colour>_BC.png   RGBA, the splatter seen from above, one per colour

usage: blender -b -t 4 --python gore_fx.py -- [textures] [drop] [duckhead] [slime]
"""
import bpy, sys, os, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *

A = args() or ['textures', 'drop', 'duckhead']
GORE = OUT / 'Gore'; (GORE / 'Export').mkdir(parents=True, exist_ok=True); (GORE / 'Textures').mkdir(exist_ok=True)


def srgb(x): return np.where(x <= .0031308, x * 12.92, 1.055 * np.clip(x, 0, 1) ** (1 / 2.4) - .055)


def vnoise(n, cells, rng):
    g = rng.random((cells + 1, cells + 1)); t = np.linspace(0, cells, n, endpoint=False); i = t.astype(int); f = t - i; f = f * f * (3 - 2 * f)
    a = g[i][:, i]; b = g[i + 1][:, i]; c = g[i][:, i + 1]; d = g[i + 1][:, i + 1]
    return (a * (1 - f)[:, None] + b * f[:, None]) * (1 - f)[None, :] + (c * (1 - f)[:, None] + d * f[:, None]) * f[None, :]


def splat(path, seed, pool_radius, lobes, streaks, drops, n=512, fresh=(.26, .005, .005), deep=(.085, .002, .003), rim=(.15, .014, .009)):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n]; u = (x + .5) / n * 2 - 1; v = (y + .5) / n * 2 - 1
    r = np.hypot(u, v); th = np.arctan2(v, u)
    n1 = vnoise(n, 9, rng); n2 = vnoise(n, 37, rng); n3 = vnoise(n, 90, rng)
    edge = pool_radius * (1 + sum(a * np.cos(k * th + p) for k, a, p in zip(range(2, 2 + lobes), rng.uniform(.03, .12, lobes), rng.uniform(0, 6.28, lobes))))
    edge = edge * (.80 + .45 * n1) + .03 * (n2 - .5)                            # a ragged rim, not a flower
    cover = np.clip((edge - r) / .03, 0, 1)                                     # the pool
    for _ in range(streaks):                                                    # thrown streaks: tapering, broken into dashes towards the far end
        a = rng.uniform(0, 6.28); r0 = pool_radius * rng.uniform(.55, .95); ln = rng.uniform(.10, .60) * (1.15 - pool_radius); w = rng.uniform(.006, .017)
        du = u * math.cos(a) + v * math.sin(a); dv = -u * math.sin(a) + v * math.cos(a)
        t = np.clip((du - r0) / ln, 0, 1); width = w * (1 - t) ** .6 + .0025
        gaps = np.clip((np.sin(du * rng.uniform(55, 130) + rng.uniform(0, 6.28)) + 1.3 - 2.2 * t) * 3, 0, 1)
        inside = (du > r0 - .03) & (du < r0 + ln)
        cover = np.maximum(cover, np.where(inside, np.clip((width - np.abs(dv)) / .005, 0, 1) * gaps, 0))
    for _ in range(drops):                                                      # spatter: mostly tiny, drawn out along the direction of flight
        a = rng.uniform(0, 6.28); d = pool_radius * rng.uniform(.85, 1.0) + abs(rng.normal(0, .24)); rad = .003 + .016 * rng.random() ** 3; asp = rng.uniform(1.0, 2.8)
        du = (u - d * math.cos(a)) * math.cos(a) + (v - d * math.sin(a)) * math.sin(a); dv = -(u - d * math.cos(a)) * math.sin(a) + (v - d * math.sin(a)) * math.cos(a)
        cover = np.maximum(cover, np.clip((rad - np.hypot(du / asp, dv)) / .004, 0, 1))
    cover *= np.clip((1.0 - np.maximum(np.abs(u), np.abs(v))) / .03, 0, 1)      # nothing touches the border
    depth = np.clip((edge - r) / max(pool_radius, .05), 0, 1) ** .7             # 0 at the rim, 1 in the middle
    fresh = np.array(fresh); deep = np.array(deep); rim = np.array(rim)
    col = fresh[None, None, :] * (1 - depth[..., None]) + deep[None, None, :] * depth[..., None]
    thin = np.clip(1.2 - cover * 1.2, 0, 1)[..., None]
    col = col * (1 - thin * .45) + rim[None, None, :] * thin * .45
    col *= (.78 + .30 * n1 + .16 * n3)[..., None]
    alpha = cover * (.84 + .14 * n3)
    px = np.concatenate([srgb(col), alpha[..., None]], axis=2)[::-1].astype(np.float32)
    im = bpy.data.images.new(path.stem, n, n, alpha=True); im.pixels.foreach_set(px.ravel()); im.filepath_raw = str(path); im.file_format = 'PNG'; im.save()
    log('texture', path.name, 'coverage', round(float(cover.mean()), 3))


def export_static(ob, path):
    from dinkasset import export_ue
    sc = bpy.context.scene
    for v in ob.data.vertices: v.co *= 100
    sc.unit_settings.scale_length = .01
    for material in bpy.data.materials:
        if material.node_tree: material.node_tree.nodes.clear()
    proxy = type('ExportAsset', (), {'renders': [ob], 'collision': [], 'armatures': [], 'sockets': []})()
    with export_ue.unhidden([ob]): export_ue.export_fbx(proxy, str(path), 'all', 'Armature')
    log('exported', path.name, tri_count(ob), 'tris')


if 'textures' in A:
    splat(GORE / 'Textures/T_BloodBurst_BC.png', 164, .30, 6, 60, 420)
    splat(GORE / 'Textures/T_BloodPuddle_BC.png', 121, .50, 5, 9, 70)
if 'drop' in A:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    segs, rings = 10, 7; vs = []; fs = []
    for j in range(rings + 1):
        t = j / rings; xx = -.5 + t                                             # tail at -X, round head at +X
        rad = .30 * math.sin(math.pi * t ** .62) ** 1.0 * (1 if t > 0 else 0)
        for i in range(segs):
            a = 2 * math.pi * i / segs; vs.append((xx * .01, rad * math.cos(a) * .01, rad * math.sin(a) * .01))
    for j in range(rings):
        for i in range(segs):
            a = j * segs + i; b = j * segs + (i + 1) % segs; fs.append((a, b, b + segs, a + segs))
    ob = mesh_obj('SM_BloodDrop', vs, fs); bpy.context.scene.collection.objects.link(ob) if ob.name not in bpy.context.scene.collection.objects else None
    activate(ob); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-6)
    bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT')
    for p in ob.data.polygons: p.use_smooth = True
    m = bpy.data.materials.new('MI_BloodDrop'); ob.data.materials.append(m)
    export_static(ob, GORE / 'Export/SM_BloodDrop.fbx')
if 'duckhead' in A:
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Duck/SK_Duck.blend'))
    src = bpy.data.objects['SM_Duck_Head_LOD1']; ob = src.copy(); ob.data = src.data.copy(); ob.name = 'SM_Duck_HeadFlying'
    bpy.context.scene.collection.objects.link(ob)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data)
    gore = [i for i, s in enumerate(ob.material_slots) if s.material and s.material.name == 'MI_Duck_Gore']
    flat = [f for f in bm.faces if f.material_index in gore and max(v.co.z for v in f.verts) < .006]     # the pool lying on the ground
    bmesh.ops.delete(bm, geom=flat, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
    for v in bm.verts: v.co -= c
    bm.to_mesh(ob.data); bm.free()
    log('flying head: removed', len(flat), 'pool faces; centre was', [round(x, 3) for x in c])
    export_static(ob, OUT / 'Duck/Export/SM_Duck_HeadFlying.fbx')
if 'slime' in A:
    SL = OUT / 'Slime'
    # the gel colours of the three slimes (slime.py TINT), darker where it lies thick
    for name, c in (('Blue', (.17, .28, .72)), ('Green', (.55, .54, .10)), ('Red', (.62, .22, .15))):
        c = np.array(c)
        splat(SL / ('Textures/T_SlimeSplat_%s_BC.png' % name), 661 + len(name), .26, 6, 34, 330, fresh=tuple(c * .75), deep=tuple(c * .32), rim=tuple(c * .5 + .04))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(661); parts = []
    for i in range(14):                                                         # blobs of gel thrown out from the middle, flattened where they landed
        a = rng.uniform(0, 6.28); d = abs(rng.normal(0, .22)) if i else 0.0; rad = (.13 if i == 0 else rng.uniform(.025, .075)); h = rad * rng.uniform(.28, .45)
        vs, fs, _ = ellipsoid((d * math.cos(a), d * math.sin(a), h * .55), (rad * rng.uniform(.9, 1.5), rad, h), n=14, rings=7)
        parts.append(mesh_obj('b', vs, fs))
    ob = join(parts, 'SM_Slime_Splat')
    activate(ob); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT')
    for p in ob.data.polygons: p.use_smooth = True
    ob.data.materials.clear(); ob.data.materials.append(bpy.data.materials.new('MI_Slime'))
    export_static(ob, SL / 'Export/SM_Slime_Splat.fbx')
