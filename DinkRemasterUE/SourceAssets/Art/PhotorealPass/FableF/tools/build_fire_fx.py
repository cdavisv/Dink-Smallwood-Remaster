"""Fire of the burning house (427 effects/fire/fire1-) as a flipbook atlas from a combustion simulation.

Unlike build_fx.py (frames synthesised from scrolling noise) this one burns: a Mantaflow gas domain with fire flows
on a row of logs, rendered by Cycles as an emitting volume from the front, one frame per simulation step. The loop
is closed by cross-fading the tail of the run into its head. The beauty renders show the same volume (not a card)
lighting charred beams and the ground at dusk.

    blender -b --factory-startup -t 4 --python tools/build_fire_fx.py -- <Fire_Wall> [--res 128] [--cache <dir>] [--stage sim|render|atlas|beauty|compact|all]

The simulation cache and the per-frame EXRs are scratch (default: a folder beside the system temp dir, or --cache);
only the atlas, the strip, the two renders, the .blend and the manifest are kept.
"""
import bpy, math, os, sys, json, tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fire_encode

HERE = os.path.dirname(os.path.abspath(__file__))
UNC = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'
SCRIPT = 'build_fire_fx.py'

SETS = {
    # frame = the square the camera sees (m), fire stands on its bottom edge; logs = (x, y, radius) of the burning lumps
    'Fire_Wall': dict(family='fire_fx', folder='fire_fx', frame_m=2.6, grid=8, px=512, fps=20, warm=36, xfade=20,
                      domain=(3.1, 1.3, 2.9), logs=[(-0.86, 0.03, 0.08), (-0.66, -0.04, 0.10), (-0.45, 0.05, 0.115), (-0.22, -0.03, 0.12), (0.0, 0.04, 0.125),
                            (0.23, -0.05, 0.12), (0.45, 0.03, 0.115), (0.67, -0.02, 0.10), (0.87, 0.04, 0.08)],
                      fuel=1.5, time_scale=1.2, vort=0.35, flame_vort=0.75, noise=0.0, burn=0.5, strength=26.0, l0=2.6, seed=427,
                      glow=6.0, hot=(0.45, 0.85, 1.0), look={},
                      seqs=['427 effects/fire/fire1-'], dresses='the wall of flame of the burning house: 1.6 m wide and 1.6 m tall on a row of burning timbers, tongues tearing off the top'),
}


def args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    o = {'name': a[0] if a and not a[0].startswith('--') else 'Fire_Wall', 'res': 128, 'cache': None, 'stage': 'all'}
    for k in ('res', 'cache', 'stage'):
        if '--' + k in a:
            o[k] = a[a.index('--' + k) + 1]
    o['res'] = int(o['res'])
    o['cache'] = o['cache'] or os.path.join(tempfile.gettempdir(), 'dink_fire_fx', o['name'])
    return o


def use_gpu(scene):
    if os.environ.get('DINK_FIRE_CPU') == '1':      # the HIP back end faulted on this volume on one machine: CPU works
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        return False
    prefs = bpy.context.preferences.addons['cycles'].preferences
    found = False
    for backend in ('HIP', 'OPTIX', 'CUDA', 'ONEAPI'):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == backend
            found |= d.use
        if found:
            break
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU' if found else 'CPU'
    return found


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'METRIC'
    return s


def lump(name, x, y, r, rng):
    """a burning timber end: a squashed, knobbly ball half sunk in the floor"""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, r * 0.35))
    ob = bpy.context.object
    ob.name = name
    ob.scale = (1.0 + rng.uniform(0.2, 0.7), 1.0 + rng.uniform(-0.1, 0.3), 0.55 + rng.uniform(0, 0.25))
    ob.rotation_euler = (0, 0, rng.uniform(-0.5, 0.5))
    for v in ob.data.vertices:
        v.co *= 1.0 + rng.uniform(-0.12, 0.12)
    return ob


def build_sim(S, o, scene):
    rng = np.random.default_rng(S['seed'])
    obs = [lump('Log_%d' % i, x, y, r, rng) for i, (x, y, r) in enumerate(S['logs'])]
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    flow = bpy.context.object
    flow.name = 'Fire_Flow'
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    m = flow.modifiers.new('Fluid', 'FLUID')
    m.fluid_type = 'FLOW'
    fs = m.flow_settings
    fs.flow_type = 'FIRE'
    fs.flow_behavior = 'INFLOW'
    fs.fuel_amount = S['fuel']
    fs.surface_distance = 0.6
    fs.subframes = 1
    # the fuel comes in gusts that wander along the row: a moving cloud texture
    tex = bpy.data.textures.new('Fuel_Gusts', 'CLOUDS')
    tex.noise_scale = 0.22
    tex.noise_depth = 2
    tex.contrast = 2.2
    tex.intensity = 1.05
    fs.use_texture = True
    fs.noise_texture = tex
    fs.texture_map_type = 'AUTO'
    fs.texture_size = 1.0
    total = S['warm'] + S['grid'] ** 2 + S['xfade']
    fs.texture_offset = 0.0
    fs.keyframe_insert('texture_offset', frame=1)
    fs.texture_offset = 3.0
    fs.keyframe_insert('texture_offset', frame=total)
    flow.hide_render = True

    dx, dy, dz = S['domain']
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, dz / 2 - 0.04))
    dom = bpy.context.object
    dom.name = 'Fire_Domain'
    dom.scale = (dx, dy, dz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    m = dom.modifiers.new('Fluid', 'FLUID')
    m.fluid_type = 'DOMAIN'
    d = m.domain_settings
    d.domain_type = 'GAS'
    d.resolution_max = o['res']
    d.use_adaptive_domain = False
    d.time_scale = S['time_scale']
    d.vorticity = S['vort']
    d.alpha = 1.0
    d.beta = 2.2
    d.burning_rate = S['burn']
    d.flame_smoke = 0.0
    d.flame_vorticity = S['flame_vort']
    d.flame_ignition = 1.25
    d.flame_max_temp = 3.2
    d.use_collision_border_front = d.use_collision_border_back = False
    d.use_collision_border_left = d.use_collision_border_right = False
    d.use_collision_border_top = False
    d.use_collision_border_bottom = True
    d.use_noise = S['noise'] > 0
    if d.use_noise:
        d.noise_scale = 2
        d.noise_strength = S['noise']
        d.noise_pos_scale = 2.0
        d.noise_time_anim = 0.25
    d.cache_type = 'ALL'
    d.cache_directory = os.path.join(o['cache'], 'sim')
    d.cache_frame_start = 1
    d.cache_frame_end = total
    scene.frame_start = 1
    scene.frame_end = total
    scene.render.fps = 24
    return dom, flow, total


def fire_material(S):
    mat = bpy.data.materials.new('M_Fire_Volume')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    att = nt.nodes.new('ShaderNodeAttribute')
    att.attribute_name = 'flame'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    stops = [(0.0, (0, 0, 0, 1)), (0.05, (0.35, 0.010, 0.0, 1)), (0.2, (1.0, 0.085, 0.003, 1)), (0.45, (1.0, 0.30, 0.015, 1)), (0.72, (1.0, 0.60, 0.09, 1)), (1.0, (1.0, 0.90, 0.48, 1))]
    cr.elements[0].position, cr.elements[0].color = stops[0]
    cr.elements[1].position, cr.elements[1].color = stops[-1]
    for p, c in stops[1:-1]:
        e = cr.elements.new(p)
        e.color = c
    pw = nt.nodes.new('ShaderNodeMath')
    pw.operation = 'POWER'
    pw.inputs[1].default_value = 2.1
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = S['strength']
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(att.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(att.outputs['Fac'], pw.inputs[0])
    nt.links.new(pw.outputs[0], mul.inputs[0])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(mul.outputs[0], em.inputs['Strength'])
    nt.links.new(em.outputs['Emission'], out.inputs['Volume'])
    return mat


def front_camera(S, scene):
    cam = bpy.data.cameras.new('Cam_Front')
    cam.type = 'ORTHO'
    cam.ortho_scale = S['frame_m']
    ob = bpy.data.objects.new('Cam_Front', cam)
    scene.collection.objects.link(ob)
    ob.location = (0, -6.0, S['frame_m'] / 2 - 0.06)
    ob.rotation_euler = (math.radians(90), 0, 0)
    cam.clip_start = 0.1
    cam.clip_end = 30
    scene.camera = ob
    return ob


def load_exr(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1]


def save_png(arr, path):
    """arr: H x W x 3/4 in 0..1 display values (sRGB already), top row first"""
    from PIL import Image
    a = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(a, 'RGBA' if a.shape[2] == 4 else 'RGB').save(path, optimize=True)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def stage_sim(S, o):
    scene = clear()
    dom, flow, total = build_sim(S, o, scene)
    dom.data.materials.append(fire_material(S))
    front_camera(S, scene)
    os.makedirs(o['cache'], exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(o['cache'], 'sim.blend'))
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        r = bpy.ops.fluid.bake_all()
    print('FIRE bake', r, 'frames', total)
    bpy.ops.wm.save_mainfile()


def stage_render(S, o):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(o['cache'], 'sim.blend'))
    scene = bpy.context.scene
    use_gpu(scene)
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.cycles.volume_step_rate = 0.5
    scene.cycles.volume_max_steps = 512
    scene.cycles.max_bounces = 2
    scene.cycles.volume_bounces = 0
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = S['px']
    scene.render.resolution_percentage = 100
    scene.render.use_stamp = False
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '16'
    scene.view_settings.view_transform = 'Raw'
    scene.world = bpy.data.worlds.new('Black')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    n0 = S['warm'] + 1
    n = S['grid'] ** 2 + S['xfade']
    os.makedirs(os.path.join(o['cache'], 'frames'), exist_ok=True)
    for i in range(n):
        scene.frame_set(n0 + i)
        scene.render.filepath = os.path.join(o['cache'], 'frames', 'f_%03d.exr' % i)
        bpy.ops.render.render(write_still=True)
    print('FIRE rendered', n)


COMPACT = dict(window=(96, 416, 190, 510), px=256)      # the middle of the wall of flame as a fire of its own (burn patches, hearth)


def compact(S, frames):
    """a smaller fire from a set's frames: cut the window, let the flames die towards its sides, scale to S['px']"""
    from PIL import Image
    x0, x1, y0, y1 = S['window']
    out = []
    for f in frames:
        c = f[y0:y1, x0:x1]
        h, w = c.shape[:2]
        xx = np.linspace(-1, 1, w, dtype=np.float32)[None, :, None]
        yy = np.linspace(1, 0, h, dtype=np.float32)[:, None, None]
        bell = np.clip(1.0 - (np.abs(xx) / 0.80) ** 2.2, 0, 1) ** 1.2
        c = c * bell * np.clip(1.0 - (yy / np.maximum(0.25 + 0.75 * bell, 1e-3)) ** 3, 0, 1)
        out.append(np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(c[..., i]), 'F').resize((S['px'], S['px']), Image.BILINEAR), np.float32) for i in range(3)], -1))
    return out


def loop_frames(S, o):
    nf = S['grid'] ** 2
    xf = S['xfade']
    raw = [load_exr(os.path.join(o['cache'], 'frames', 'f_%03d.exr' % i))[..., :3] for i in range(nf + xf)]
    out = []
    for i in range(nf):
        if i < xf:
            w = i / xf
            w = w * w * (3 - 2 * w)
            out.append(raw[i] * w + raw[i + nf] * (1 - w))
        else:
            out.append(raw[i])
    return out


def stage_atlas(S, o):
    """straight colour + opacity for the translucent flipbook master: flame body, smoke and sparks (fire_encode.py)"""
    folder = os.path.join(UNC, S['folder'], o['name'])
    os.makedirs(folder, exist_ok=True)
    frames = fire_encode.encode_loop(loop_frames(S, o), dict(fire_encode.DEFAULT, seed=S['seed'], **S.get('look', {})))
    g = S['grid']
    px = S['px']
    atlas = np.zeros((g * px, g * px, 4), np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, g)
        atlas[r * px:(r + 1) * px, c * px:(c + 1) * px] = f
    save_png(atlas, os.path.join(folder, 'T_FX_%s_Flipbook.png' % o['name']))
    # strip: eight frames across the loop as the game's material shows them (hot texels times the glow), over a dark
    # room and over a daylit wall
    pick = [int(i * len(frames) / 8) for i in range(8)]
    hot, glow = S['hot'], S['glow']
    rows = []
    for bg in ((0.02, 0.02, 0.025), (0.50, 0.46, 0.40)):
        cells = []
        for i in pick:
            f = frames[i][::2, ::2]
            c = np.power(np.clip(f[..., :3], 0, 1), 2.2)
            h = np.clip((c.max(-1) - hot[0]) / (hot[1] - hot[0]), 0, 1)
            h = h * h * (3 - 2 * h)
            lin = c * (hot[2] + (glow - hot[2]) * h)[..., None] * f[..., 3:4] + np.array(bg, np.float32) * (1 - f[..., 3:4])
            cells.append(srgb(lin / (1 + lin) * 1.15))
        rows.append(np.concatenate(cells, 1))
    save_png(np.concatenate(rows, 0), os.path.join(folder, 'frames_strip.png'))
    cov = float(np.mean([(f[..., 3] > 0.08).mean() for f in frames]))
    return folder, cov


def stage_beauty(S, o):
    """the simulated volume itself at dusk: it lights charred beams, a plank floor and the wall behind it"""
    folder = os.path.join(UNC, S['folder'], o['name'])
    bpy.ops.wm.open_mainfile(filepath=os.path.join(o['cache'], 'sim.blend'))
    scene = bpy.context.scene
    use_gpu(scene)
    rng = np.random.default_rng(7)

    def mat(name, col, rough):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1)
        b.inputs['Roughness'].default_value = rough
        nt = m.node_tree
        noise = nt.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 14
        noise.inputs['Detail'].default_value = 8
        bump = nt.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.5
        nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
        return m
    floor = mat('Floor', (0.11, 0.075, 0.05), 0.75)
    char = mat('Char', (0.015, 0.013, 0.012), 0.9)
    wall = mat('Wall', (0.30, 0.27, 0.22), 0.9)
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    bpy.context.object.data.materials.append(floor)
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 1.6, 2.0), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(wall)
    for i in range(6):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(rng.uniform(-0.6, 0.6), rng.uniform(-0.12, 0.12), 0.06 + 0.03 * i * 0.3))
        b = bpy.context.object
        b.scale = (rng.uniform(0.5, 1.1), 0.11, 0.09)
        b.rotation_euler = (rng.uniform(-0.1, 0.1), rng.uniform(-0.08, 0.08), rng.uniform(-0.7, 0.7))
        bev = b.modifiers.new('Bevel', 'BEVEL')
        bev.width = 0.012
        bev.segments = 3
        b.data.materials.append(char)
    w = bpy.data.worlds.new('Dusk')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.07, 0.12, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
    scene.world = w
    scene.cycles.samples = 192
    scene.cycles.use_denoising = True
    scene.cycles.volume_step_rate = 0.5
    scene.cycles.volume_bounces = 0
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -1.6
    scene.frame_set(S['warm'] + 30)
    for name, loc, rot, lens, res in (('render_beauty', (0.0, -5.2, 3.4), (math.radians(62), 0, 0), 50, (1200, 1000)),
                                      ('render_close', (0.9, -1.9, 0.95), (math.radians(84), 0, math.radians(24)), 40, (1200, 1000))):
        cam = bpy.data.cameras.new(name)
        cam.lens = lens
        ob = bpy.data.objects.new(name, cam)
        scene.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = rot
        scene.camera = ob
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = os.path.join(folder, name + '.png')
        bpy.ops.render.render(write_still=True)
    # the kept .blend: the review scene with the emitter and an empty domain setup (no cache: rebuild with this script)
    dom = bpy.data.objects['Fire_Domain']
    dom.modifiers['Fluid'].domain_settings.cache_directory = '//cache_not_kept'
    bpy.ops.file.make_paths_relative() if bpy.data.filepath else None
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(folder, 'FX_%s.blend' % o['name']), compress=True)


def write_manifest(S, o, folder, cov):
    rel = ROOT + '/' + S['folder'] + '/' + o['name'] + '/'
    g = S['grid']
    m = {
        'name': 'FX_' + o['name'],
        'class': 'effect flipbook (texture atlas; no mesh)',
        'lod0_triangles': 0,
        'dimensions_m': [S['frame_m'], S['frame_m'], 0.0],
        'textures': [{'file': rel + 'T_FX_%s_Flipbook.png' % o['name'], 'size_px': [g * S['px'], g * S['px']],
                      'channels': 'RGB straight colour (sRGB) + alpha = opacity (flames nearly opaque where the fire is thick, smoke up to 0.55); %d x %d frames of %d px, row by row from the top left' % (g, g, S['px'])}],
        'flipbook': {'frames': g * g, 'grid': [g, g], 'fps': S['fps'], 'loop': True, 'billboard_size_m': [S['frame_m'], S['frame_m']],
                     'blend': 'translucent', 'glow': S['glow'], 'hot': list(S['hot']), 'alpha_coverage': round(cov, 3), 'stands_on_bottom_edge': True},
        'preview': rel + 'frames_strip.png',
        'source_blend': rel + 'FX_%s.blend' % o['name'],
        'source_note': 'a Mantaflow gas simulation (fire flows on a row of timbers, resolution %d) rendered by Cycles as an emitting volume, front view, one frame per step; the loop is closed by a %d-frame cross-fade. tools/fire_encode.py turns the HDR flame frames into colour and opacity and adds what the flame render does not hold: smoke built from the flames\' own earlier frames (risen, spread, broken into billows by rising noise, lit from below) and sparks. The .blend holds the emitter, the domain settings and the review scene; the simulation cache is not kept (rebuild with the script).' % (o['res'], S['xfade']),
        'build': 'blender -b --factory-startup -t 4 --python FableF/tools/build_fire_fx.py -- ' + o['name'],
        'families': [S['family']] + S['seqs'],
        'supersedes': 'none (placeholder greybox cards)',
        'dresses': S['dresses'],
        'third_party': [],
        'status': 'source delivered',
        'known_weaknesses': 'A flipbook on a camera-facing card, not a volume in the game: it has no depth against the scene and from straight above it is still a side view. The smoke is made from the flame frames, not simulated, and ends at the top of the frame (1 m above the flames): it does not gather under a ceiling or trail off downwind. The material is unlit: the smoke keeps its own brightness in a dark room. One loop of 3.2 s.',
    }
    json.dump(m, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
    open(os.path.join(folder, 'manifest.json'), 'a').write('\n')


def main():
    o = args()
    S = SETS[o['name']]
    st = o['stage']
    if st in ('sim', 'all'):
        stage_sim(S, o)
    if st in ('render', 'all'):
        stage_render(S, o)
    if st in ('atlas', 'all'):
        folder, cov = stage_atlas(S, o)
        write_manifest(S, o, folder, cov)
    if st == 'compact':      # linear HDR frames of the compact fire for tools/build_burn_patch.py
        path = os.path.join(o['cache'], 'compact_%d.npy' % COMPACT['px'])
        np.save(path, np.stack(compact(COMPACT, loop_frames(S, o))).astype(np.float16))
        print('FIRE compact frames', path)
    if st in ('beauty', 'all'):
        stage_beauty(S, o)
    print('FIRE DONE', o['name'], st)


if __name__ == '__main__':
    main()
