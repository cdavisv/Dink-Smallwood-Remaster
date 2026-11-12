"""Blender preview renders for the Stonebrook fire-ruin kit (not game evidence).

    blender -b --factory-startup -t 3 -P render_previews.py -- [burning|burnt|interior|compare1|compare2] [--samples N] [--pct P]

Opens KIT_StonebrookRuins.blend (never saved here) and appends context props read-only from the
existing kits (meadow, oak, fence, grass, bed, table).  Fire and smoke are preview-only volume
shaders placed on the burning cottage's SOCKET_ empties; in Unreal they are Niagara emitters.
"""
import bpy, math, sys, json, random
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
KIT = HERE.parent; UE = KIT.parents[2]
sys.path.insert(0, str(HERE))
import ruin_common as R

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SHOTS = [a for a in argv if not a.startswith('--') and not a.replace('.', '').isdigit()] or ['burning', 'burnt', 'interior', 'interior_burning']
SAMPLES = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 64
PCT = int(argv[argv.index('--pct') + 1]) if '--pct' in argv else 100
OUT = KIT / 'Previews'; OUT.mkdir(exist_ok=True)
EXT = UE / 'SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend'
INT = UE / 'SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend'


def reset():
    bpy.ops.wm.open_mainfile(filepath=str(KIT / 'KIT_StonebrookRuins.blend'))
    sc = bpy.context.scene
    for ob in bpy.data.objects:
        if '_LOD1' in ob.name or '_LOD2' in ob.name or ob.name.startswith('UCX_'):
            ob.hide_render = True; ob.hide_viewport = True
    # asset collections stay as sources; we instance them into a stage collection
    for c in list(sc.collection.children):
        sc.collection.children.unlink(c)
    stage = bpy.data.collections.new('Stage'); sc.collection.children.link(stage)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 3
    sc.cycles.volume_step_rate = 2.0; sc.cycles.volume_max_steps = 256
    sc.render.resolution_x = 1600; sc.render.resolution_y = 1000; sc.render.resolution_percentage = PCT
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.film_transparent = False
    return sc, stage


def inst(stage, coll_name, loc, rot_z=0.0, scale=1.0, name=None):
    e = bpy.data.objects.new(name or ('I_' + coll_name), None)
    e.instance_type = 'COLLECTION'; e.instance_collection = bpy.data.collections[coll_name]
    e.location = loc; e.rotation_euler = (0, 0, rot_z); e.scale = (scale, scale, scale)
    stage.objects.link(e)
    return e


def append_collections(path, names):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.collections = [n for n in src.collections if n in names]
    for c in dst.collections:
        for ob in c.objects:
            if '_LOD1' in ob.name or '_LOD2' in ob.name or ob.name.startswith('UCX_'):
                ob.hide_render = True
        # source kits keep a preview layout offset on their objects: instance about the asset origin
        main = next((o for o in c.objects if o.type == 'MESH' and not o.name.startswith('UCX_')), None)
        if main is not None:
            c.instance_offset = main.location.copy()
    return {c.name: c for c in dst.collections}


def world(sc, color, strength, sky=None):
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    if sky:
        sk = nt.nodes.new('ShaderNodeTexSky')
        try:
            sk.sky_type = 'NISHITA' if 'NISHITA' in [i.identifier for i in sk.bl_rna.properties['sky_type'].enum_items] else sk.sky_type
        except Exception:
            pass
        for k, v in sky.items():
            try:
                setattr(sk, k, v)
            except Exception:
                pass
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = .65
        nt.links.new(sk.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = (*color, 1)
        nt.links.new(mix.outputs['Result'], bg.inputs['Color'])
    else:
        bg.inputs['Color'].default_value = (*color, 1)
    bg.inputs['Strength'].default_value = strength


def sun(stage, energy, rot, color=(1, 1, 1), angle=.05):
    L = bpy.data.lights.new('Sun', 'SUN'); L.energy = energy; L.color = color; L.angle = angle
    o = bpy.data.objects.new('Sun', L); o.rotation_euler = rot; stage.objects.link(o)


def point(stage, loc, power, color, radius=.3, name='P'):
    L = bpy.data.lights.new(name, 'POINT'); L.energy = power; L.color = color; L.shadow_soft_size = radius
    o = bpy.data.objects.new(name, L); o.location = loc; stage.objects.link(o)


def area(stage, loc, power, color, size, rot=(0, 0, 0), name='A'):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = power; L.color = color; L.size = size
    o = bpy.data.objects.new(name, L); o.location = loc; o.rotation_euler = rot; stage.objects.link(o)


def camera(sc, stage, loc, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new('Cam'); c = bpy.data.objects.new('Cam', cd); stage.objects.link(c)
    c.location = loc; c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens; cd.clip_end = 400
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    sc.camera = c


def fire_material(seed):
    m = bpy.data.materials.new(f'PreviewFire_{seed}'); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; l = nt.links
    for x in list(n):
        if x.type != 'OUTPUT_MATERIAL':
            n.remove(x)
    out = n['Material Output']
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sep.inputs[0])
    # h: 0 at base, 1 at top of the unit cube domain; r: radial distance
    h = n.new('ShaderNodeMapRange'); h.inputs['From Min'].default_value = -1; h.inputs['From Max'].default_value = 1
    l.new(sep.outputs['Z'], h.inputs['Value'])
    vlen = n.new('ShaderNodeVectorMath'); vlen.operation = 'LENGTH'
    comb = n.new('ShaderNodeCombineXYZ'); l.new(sep.outputs['X'], comb.inputs['X']); l.new(sep.outputs['Y'], comb.inputs['Y'])
    l.new(comb.outputs[0], vlen.inputs[0])
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (2.2, 2.2, .7); mp.inputs['Location'].default_value = (seed * 1.7, seed * .3, -seed * .9)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 5.5; nz.inputs['Detail'].default_value = 12
    nz.inputs['Distortion'].default_value = 3.0; nz.inputs['Roughness'].default_value = .68
    l.new(mp.outputs[0], nz.inputs['Vector'])
    # cone: allowed radius shrinks with height; flame = noise - threshold(h) - r
    rad = n.new('ShaderNodeMath'); rad.operation = 'MULTIPLY_ADD'; rad.inputs[1].default_value = -.25; rad.inputs[2].default_value = 1.0
    l.new(h.outputs[0], rad.inputs[0])
    d0 = n.new('ShaderNodeMath'); d0.operation = 'DIVIDE'; l.new(vlen.outputs['Value'], d0.inputs[0]); l.new(rad.outputs[0], d0.inputs[1])
    con = n.new('ShaderNodeMapRange'); con.inputs['From Min'].default_value = .36; con.inputs['From Max'].default_value = .64
    l.new(nz.outputs['Fac'], con.inputs['Value'])
    sh = n.new('ShaderNodeMath'); sh.operation = 'SUBTRACT'; l.new(con.outputs[0], sh.inputs[0])
    thr = n.new('ShaderNodeMath'); thr.operation = 'MULTIPLY_ADD'; thr.inputs[1].default_value = .62; thr.inputs[2].default_value = .22
    l.new(h.outputs[0], thr.inputs[0])
    sh2 = n.new('ShaderNodeMath'); sh2.operation = 'MULTIPLY_ADD'; sh2.inputs[1].default_value = .55
    l.new(d0.outputs[0], sh2.inputs[0]); l.new(thr.outputs[0], sh2.inputs[2])
    l.new(sh2.outputs[0], sh.inputs[1])
    dens = n.new('ShaderNodeMath'); dens.operation = 'MULTIPLY'; dens.use_clamp = True; dens.inputs[1].default_value = 2.2
    l.new(sh.outputs[0], dens.inputs[0])
    bb = n.new('ShaderNodeBlackbody')
    t = n.new('ShaderNodeMath'); t.operation = 'MULTIPLY_ADD'; t.inputs[1].default_value = 1000; t.inputs[2].default_value = 1150
    l.new(dens.outputs[0], t.inputs[0]); l.new(t.outputs[0], bb.inputs[0])
    em = n.new('ShaderNodeEmission'); l.new(bb.outputs[0], em.inputs['Color'])
    st = n.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; st.inputs[1].default_value = 9
    l.new(dens.outputs[0], st.inputs[0]); l.new(st.outputs[0], em.inputs['Strength'])
    ab = n.new('ShaderNodeVolumeAbsorption'); ab.inputs['Color'].default_value = (.4, .2, .1, 1)
    abd = n.new('ShaderNodeMath'); abd.operation = 'MULTIPLY'; abd.inputs[1].default_value = 0.6
    l.new(dens.outputs[0], abd.inputs[0]); l.new(abd.outputs[0], ab.inputs['Density'])
    add = n.new('ShaderNodeAddShader'); l.new(em.outputs[0], add.inputs[0]); l.new(ab.outputs[0], add.inputs[1])
    l.new(add.outputs[0], out.inputs['Volume'])
    return m


def smoke_material(density=1.0, dark=.06, seed=0):
    m = bpy.data.materials.new(f'PreviewSmoke_{seed}'); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; l = nt.links
    for x in list(n):
        if x.type != 'OUTPUT_MATERIAL':
            n.remove(x)
    out = n['Material Output']
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sep.inputs[0])
    comb = n.new('ShaderNodeCombineXYZ'); l.new(sep.outputs['X'], comb.inputs['X']); l.new(sep.outputs['Y'], comb.inputs['Y'])
    vlen = n.new('ShaderNodeVectorMath'); vlen.operation = 'LENGTH'; l.new(comb.outputs[0], vlen.inputs[0])
    h = n.new('ShaderNodeMapRange'); h.inputs['From Min'].default_value = -1; h.inputs['From Max'].default_value = 1
    l.new(sep.outputs['Z'], h.inputs['Value'])
    rad = n.new('ShaderNodeMath'); rad.operation = 'MULTIPLY_ADD'; rad.inputs[1].default_value = .55; rad.inputs[2].default_value = .35
    l.new(h.outputs[0], rad.inputs[0])
    d0 = n.new('ShaderNodeMath'); d0.operation = 'DIVIDE'; l.new(vlen.outputs['Value'], d0.inputs[0]); l.new(rad.outputs[0], d0.inputs[1])
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.4, 1.4, .8); mp.inputs['Location'].default_value = (seed, seed * .5, 0)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.0; nz.inputs['Detail'].default_value = 6; nz.inputs['Distortion'].default_value = .8
    l.new(mp.outputs[0], nz.inputs['Vector'])
    sub = n.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; l.new(nz.outputs['Fac'], sub.inputs[0]); l.new(d0.outputs[0], sub.inputs[1])
    sub2 = n.new('ShaderNodeMath'); sub2.operation = 'MULTIPLY'; sub2.use_clamp = True; sub2.inputs[1].default_value = 2.5
    l.new(sub.outputs[0], sub2.inputs[0])
    fade = n.new('ShaderNodeMath'); fade.operation = 'MULTIPLY_ADD'; fade.inputs[1].default_value = -.8; fade.inputs[2].default_value = 1.0
    l.new(h.outputs[0], fade.inputs[0])
    dd = n.new('ShaderNodeMath'); dd.operation = 'MULTIPLY'; l.new(sub2.outputs[0], dd.inputs[0]); l.new(fade.outputs[0], dd.inputs[1])
    dd2 = n.new('ShaderNodeMath'); dd2.operation = 'MULTIPLY'; dd2.inputs[1].default_value = density
    l.new(dd.outputs[0], dd2.inputs[0])
    pv = n.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (dark, dark, dark * .95, 1)
    l.new(dd2.outputs[0], pv.inputs['Density'])
    l.new(pv.outputs[0], out.inputs['Volume'])
    return m


def volume_box(stage, loc, size, mat, name):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.scale = size; me.materials.append(mat)
    stage.objects.link(o)
    return o


def sockets_world(asset, origin, rot_z=0.0):
    out = []
    for ob in bpy.data.collections[asset].objects:
        if ob.type == 'EMPTY' and ob.name.startswith('SOCKET_'):
            p = ob.location.copy(); p.rotate(__import__('mathutils').Euler((0, 0, rot_z)))
            out.append((ob.name, Vector(origin) + p))
    return out


def yard(stage, cottage_x=0.0, burnt=False):
    ext = append_collections(EXT, ['SM_Ground_Meadow_20m_01', 'SM_Oak_Stonebrook_01', 'SM_Fence_SplitRail_4m_01', 'SM_Grass_Meadow_01', 'SM_Boulder_Fieldstone_01'])
    for i in range(-1, 2):
        for j in range(-1, 2):
            inst(stage, 'SM_Ground_Meadow_20m_01', (i * 20, j * 20, -.10))
    inst(stage, 'SM_Oak_Stonebrook_01', (-17, 8, 0), .7, 1.05)
    inst(stage, 'SM_Oak_Stonebrook_01', (16, 12, 0), 2.1, .95)
    for k in range(9):
        if k == 5:
            continue
        inst(stage, 'SM_Fence_SplitRail_4m_01', (-16 + k * 4.05, -11.5, 0), 0)
    inst(stage, 'SM_Boulder_Fieldstone_01', (-12.5, -5.5, 0), .4)
    rnd = random.Random(7)
    for k in range(70):
        x, y = rnd.uniform(-22, 22), rnd.uniform(-16, 14)
        if abs(x) < 10.5 and -6.5 < y < 6.0:
            continue
        if 2 < x < 8 and -11 < y < -4:
            continue
        inst(stage, 'SM_Grass_Meadow_01', (x, y, 0), rnd.uniform(0, 6.28), rnd.uniform(.7, 1.3))


def shot_burning():
    sc, stage = reset()
    name = 'SM_Cottage_Stonebrook_Burning_01'
    inst(stage, name, (0, 0, 0))
    yard(stage)
    px, py = R.decal_pivot(R.DOOR_X + .2, -6.6, 2.0, 30, 1.0)
    inst(stage, 'SM_Decal_Scorch_Ground_2m_01', (px, py, .005), math.radians(30))
    world(sc, (.03, .045, .09), .55)
    sun(stage, .35, (math.radians(84), 0, math.radians(-140)), (1.0, .55, .32), .02)
    socks = sockets_world(name, (0, 0, 0))
    for i, (sn, p) in enumerate(socks):
        if sn.startswith('SOCKET_Fire'):
            big = 'Door' not in sn
            s = 1.0 if big else .7
            info = next((x for x in json.loads((KIT / 'emitter_sockets_draft.json').read_text())[name] if x['socket'] == sn), {})
            s *= max(.55, min(1.3, info.get('scale_hint', 1.0)))
            volume_box(stage, p + Vector((0, 0, 1.2 * s)), (1.3 * s, 1.1 * s, 1.5 * s), fire_material(i + 1), f'Fire_{sn}')
            point(stage, p + Vector((0, -.4, .8 * s)), 450 * s, (1.0, .5, .18), .8, f'FireLight_{sn}')
        elif sn.startswith('SOCKET_Smoke'):
            point(stage, p + Vector((0, 0, .3)), 350, (1.0, .4, .1), .5, f'Glow_{sn}')
    # one broad smoke plume leaning downwind over the roof
    volume_box(stage, Vector((0.5, 1.5, 14.5)), (12.0, 8.0, 7.5), smoke_material(3.0, .045, 3), 'SmokePlume')
    volume_box(stage, Vector((-5.4, 2.4, 10.5)), (1.6, 1.6, 2.8), smoke_material(2.0, .08, 5), 'ChimneySmoke')
    point(stage, (R.DOOR_X - .1, -2.5, 1.2), 1200, (1.0, .42, .12), .8, 'InteriorGlow')
    point(stage, (-3.5, -1.0, 1.5), 1000, (1.0, .42, .12), 1.0, 'InteriorGlow2')
    for x in R.WINDOWS_X:
        point(stage, (x, -3.6, 2.2), 260, (1.0, .45, .14), .5, 'WinGlow')
    sun(stage, .12, (math.radians(60), 0, math.radians(40)), (.55, .65, 1.0), .05)
    camera(sc, stage, (-15.5, -21.0, 6.2), (0.8, 0, 3.6), 30)
    sc.render.filepath = str(OUT / 'exterior_burning.png'); bpy.ops.render.render(write_still=True)


def shot_burnt():
    sc, stage = reset()
    inst(stage, 'SM_Cottage_Stonebrook_Burnt_01', (0, 0, 0))
    yard(stage)
    for k, (nm, size, cx, cy, yaw, s) in enumerate(R.GROUND_SCORCH):
        px, py = R.decal_pivot(cx, cy, size, yaw, s)
        inst(stage, nm, (px, py, .004 + .001 * k), math.radians(yaw), s)
    inst(stage, 'SM_Door_Cottage_Fallen_01', (R.DOOR_X + 1.9, -6.2, .0), math.radians(64))
    inst(stage, 'SM_Debris_AshPile_Large_01', (-6.0, -5.6, 0), .3)
    inst(stage, 'SM_Debris_AshPile_Small_01', (1.0, -5.3, 0), 1.1)
    inst(stage, 'SM_Debris_AshPile_Small_01', (9.9, 1.5, 0), 2.4, 1.3)
    world(sc, (.42, .47, .55), .85)
    sun(stage, 1.6, (math.radians(52), 0, math.radians(-35)), (1.0, .93, .84), .25)
    volume_box(stage, Vector((-1.5, 0.5, 9.5)), (5.0, 3.0, 3.5), smoke_material(.18, .25, 9), 'ThinSmoke')
    camera(sc, stage, (-14.5, -20.0, 5.6), (0.6, 0, 3.0), 31)
    sc.render.filepath = str(OUT / 'exterior_burnt.png'); bpy.ops.render.render(write_still=True)


def shot_interior_burning():
    sc, stage = reset()
    append_collections(INT, ['SM_Floor_Oak_2m_01', 'SM_Ceiling_Oak_2m_01', 'SM_Wall_Limewash_2m_01', 'SM_Window_Limewash_2m_01',
                             'SM_Bed_Oak_01', 'SM_Table_Oak_01', 'SM_Chair_Oak_01'])
    for i in range(3):
        for j in range(3):
            inst(stage, 'SM_Floor_Oak_2m_01', (i * 2, j * 2, 0))
            inst(stage, 'SM_Ceiling_Oak_2m_01', (i * 2, j * 2, 3.5))
    for i, nm in enumerate(['SM_Wall_Limewash_2m_01', 'SM_Window_Limewash_2m_01', 'SM_Wall_Limewash_2m_01']):
        inst(stage, nm, (i * 2, 6.0, 0))
        inst(stage, nm, (0, i * 2, 0), math.radians(90))
    inst(stage, 'SM_Bed_Oak_01', (1.6, 1.2, 0))
    inst(stage, 'SM_Table_Oak_01', (4.8, 4.8, 0), math.radians(8))
    # S001_P34: she lies where the 1997 sprite has her, in her blood, between the fires
    bx, by = R.decal_pivot(2.45, 3.75, 2.0, -25, 1.0)
    inst(stage, 'SM_Decal_Blood_Floor_01', (bx, by, .003), math.radians(-25))
    inst(stage, 'SM_Mother_Remains_Fire_01', (2.55, 3.95, .004), math.radians(-35))
    inst(stage, 'SM_Debris_AshPile_Small_01', (.8, 5.3, 0), .4, .8)
    inst(stage, 'SM_Decal_Scorch_Floor_01', (.6, 4.4, .002), .3, 1.1)
    world(sc, (.02, .025, .04), .2)
    for k, (p, s) in enumerate([((.5, 5.4, 0), 1.0), ((3.9, 5.75, 1.6), .8), ((.25, 2.6, 1.2), .9), ((5.2, 2.2, 0), .7), ((.5, 1.0, 2.6), .6)]):
        p = Vector(p)
        volume_box(stage, p + Vector((0, 0, 1.0 * s)), (.9 * s, .9 * s, 1.2 * s), fire_material(k + 11), f'IFire{k}')
        point(stage, p + Vector((0, 0, .7 * s)), 160 * s, (1.0, .48, .16), .6, f'IFireL{k}')
    volume_box(stage, Vector((3, 3, 3.0)), (3.0, 3.0, .45), smoke_material(1.2, .05, 21), 'CeilingSmoke')
    camera(sc, stage, (4.6, 1.3, 1.7), (2.2, 4.0, .25), 22)
    sc.view_settings.exposure = -1.0
    sc.render.filepath = str(OUT / 'interior_burning.png'); bpy.ops.render.render(write_still=True)


def shot_interior():
    sc, stage = reset()
    append_collections(INT, ['SM_Bed_Oak_01', 'SM_Table_Oak_01', 'SM_Chair_Oak_01'])
    # 3 x 3 modules: room x 0..6 (east), y 0..6 (north); north wall at y=6, west wall at x=0
    v = 1
    for i in range(3):
        for j in range(3):
            inst(stage, f'SM_Floor_Oak_Burnt_2m_0{v}', (i * 2, j * 2, 0)); v = v % 4 + 1
            inst(stage, 'SM_Ceiling_Oak_BurntHole_2m_01' if (i, j) == (1, 1) else 'SM_Ceiling_Oak_Burnt_2m_01', (i * 2, j * 2, 3.5))
    for i, nm in enumerate(['SM_Wall_Limewash_Burnt_2m_01', 'SM_Window_Limewash_Burnt_2m_01', 'SM_Wall_Limewash_Burnt_2m_01']):
        inst(stage, nm, (i * 2, 6.0, 0))
    for j, nm in enumerate(['SM_Wall_Limewash_Burnt_2m_01', 'SM_Window_Limewash_Burnt_2m_01', 'SM_Wall_Limewash_Burnt_2m_01']):
        inst(stage, nm, (0, j * 2, 0), math.radians(90))
    inst(stage, 'SM_Bed_Oak_01', (1.6, 1.2, 0), math.radians(0))
    inst(stage, 'SM_Table_Oak_01', (4.6, 4.7, 0), math.radians(8))
    inst(stage, 'SM_Chair_Oak_01', (4.5, 3.7, 0), math.radians(170))
    inst(stage, 'SM_Decal_Scorch_Floor_01', (1.9, 3.4, .003), .4, 1.3)
    inst(stage, 'SM_Decal_Scorch_Floor_01', (4.4, .4, .003), 1.9, 1.0)
    inst(stage, 'SM_Decal_Scorch_Wall_01', (2.6, 5.80, .25), 0, 1.0)
    inst(stage, 'SM_Decal_Scorch_Wall_01', (0.2, 3.9, .15), math.radians(90), .9)
    inst(stage, 'SM_Debris_AshPile_Small_01', (2.9, 3.05, 0), .7, 1.4)
    inst(stage, 'SM_Debris_AshPile_Small_01', (0.6, 5.2, 0), 2.0, .9)
    world(sc, (.62, .70, .80), .25)
    sun(stage, 3.0, (math.radians(50), 0, math.radians(200)), (1.0, .92, .8), .02)
    area(stage, (3.0, 3.0, 3.8), 300, (.75, .82, 1.0), 1.6, (0, 0, 0), 'HoleSky')
    area(stage, (2.8, 7.2, 1.9), 500, (.8, .87, 1.0), 1.4, (math.radians(90), 0, 0), 'WindowNorth')
    area(stage, (-1.2, 3.0, 1.9), 400, (.8, .87, 1.0), 1.4, (math.radians(90), 0, math.radians(-90)), 'WindowWest')
    area(stage, (5.0, -.5, 2.0), 140, (1.0, .95, .9), 3.0, (math.radians(-80), 0, 0), 'Fill')
    camera(sc, stage, (5.0, .3, 1.75), (1.0, 4.6, .8), 17)
    sc.render.filepath = str(OUT / 'interior_burnt.png'); bpy.ops.render.render(write_still=True)


def compare(state):
    """Orthographic view along the original sprite's viewing direction (see ruin_common)."""
    sc, stage = reset()
    asset = 'SM_Cottage_Stonebrook_Burning_01' if state == 1 else 'SM_Cottage_Stonebrook_Burnt_01'
    piv = Vector(json.loads((KIT / 'ruins_manifest.json').read_text())['assets'][asset]['pivot_offset_from_construction_m'])
    inst(stage, asset, -piv)   # place in construction frame
    append_collections(EXT, ['SM_Ground_Meadow_20m_01'])
    for i in range(-1, 2):
        for j in range(-1, 2):
            inst(stage, 'SM_Ground_Meadow_20m_01', (i * 20, j * 20, -.10))
    dx, dy = R._solve2(R.SPR_EX, R.SPR_EY, (-R.SPR_EZ[0], -R.SPR_EZ[1]))
    d = Vector((dx, dy, 1.0)).normalized()
    world(sc, (.6, .65, .7), 1.0)
    sun(stage, 2.5, (math.radians(45), 0, math.radians(-30)), (1, .95, .88), .1)
    target = Vector((0, 0, 3.0))
    camera(sc, stage, target + d * 60, target, ortho=26)
    if state == 1:
        for i, (sn, p) in enumerate(sockets_world(asset, -piv)):
            if sn.startswith('SOCKET_Fire') and 'Door' not in sn:
                volume_box(stage, p + Vector((0, 0, 1.0)), (.8, .8, 1.2), fire_material(i + 1), f'Fire_{sn}')
                point(stage, p + Vector((0, 0, .8)), 1500, (1.0, .45, .12), .5)
    sc.render.resolution_x = 900; sc.render.resolution_y = 600
    sc.render.filepath = str(OUT / f'_compare_v{state}_render.png'); bpy.ops.render.render(write_still=True)


for s in SHOTS:
    {'burning': shot_burning, 'burnt': shot_burnt, 'interior': shot_interior,
     'compare1': lambda: compare(1), 'compare2': lambda: compare(2), 'interior_burning': shot_interior_burning}[s]()
    print('RENDERED', s, flush=True)
