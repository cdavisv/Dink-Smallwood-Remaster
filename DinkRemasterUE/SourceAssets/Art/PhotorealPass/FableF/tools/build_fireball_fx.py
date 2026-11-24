"""Fireball and hellfire seen along their flight (502/508 and 512/518: flying south, at the camera, and north, away
from it) as flipbook atlases from a combustion simulation.

The missile cards of the east and west flights are a side view. Along the flight the same card read as a tall flame
standing on the caster. Here a ball of burning fuel sits in a head wind (Mantaflow gas domain, fire flow with an
initial velocity along +Y), so the flames wrap round the ball and trail off behind it. Cycles renders the emitting
volume twice per step with orthographic cameras raised as the play camera is: from ahead (the missile comes at the
camera: the ball in front, its short trail rising behind it) and from behind (it flies away: the trail hangs towards
the camera, below the ball). Sparks are the same analytic 3D paths projected through both cameras.

    DINK_CPU=1 blender -b --factory-startup -t 4 --python tools/build_fireball_fx.py -- <Fireball|Hellfire> [--res 112] [--cache <dir>] [--stage sim|render|atlas|preview|all]

The simulation cache and the per-frame EXRs are scratch (--cache); the atlases, strips, the .blend and the manifests
are kept. The GPU is used only when DINK_CPU is not 1 (machine rule: then run it through gpu_turn.sh).
"""
import bpy, math, os, sys, json, tempfile
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'
ELEV = math.radians(14.0)          # the play camera looks down about this much on a missile at chest height

SETS = {
    'Fireball': dict(folder='missile_fx', frame_m=1.3, grid=6, px=256, fps=24, warm=30, xfade=12, radius=0.13, core=0.085, core_strength=30.0,
                     fuel=2.0, speed=2.6, normal=0.5, burn=0.6, vort=0.4, flame_vort=0.8, beta=0.35, strength=30.0, seed=502, sparks=110, spark_len=1.8,
                     glow=2.2, hot=(0.55, 0.95, 1.0), l_alpha=0.55, l0=4.0, gamma=0.85,
                     seqs={'Front': ['502 effects/comets/sm-comt1/comt2-'], 'Back': ['508 effects/comets/sm-comt1/comt8-']},
                     dresses='the fireball spell along its flight: a ball of fire 0.35 m across, flames wrapped round it and a short trail of flame and sparks behind'),
    'Hellfire': dict(folder='missile_fx', frame_m=1.9, grid=6, px=256, fps=24, warm=30, xfade=12, radius=0.22, core=0.13, core_strength=24.0,
                     fuel=2.2, speed=2.2, normal=0.9, burn=0.5, vort=0.55, flame_vort=1.0, beta=0.5, strength=26.0, seed=512, sparks=40, spark_len=1.3,
                     glow=1.8, hot=(0.55, 0.95, 1.0), l_alpha=0.55, l0=4.0, gamma=0.85, pulse=True,
                     seqs={'Front': ['512 effects/comets/sm-comt2/fbal2-'], 'Back': ['518 effects/comets/sm-comt2/fbal8-']},
                     dresses='hellfire along its flight: a fat ball of fire 0.6 m across that sheds clumps of flame behind it (1997: a chain of fire balls)'),
}
VIEWS = ('Front', 'Back')


def args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    o = {'name': a[0] if a and not a[0].startswith('--') else 'Fireball', 'res': 112, 'cache': None, 'stage': 'all'}
    for k in ('res', 'cache', 'stage'):
        if '--' + k in a:
            o[k] = a[a.index('--' + k) + 1]
    o['res'] = int(o['res'])
    o['cache'] = o['cache'] or os.path.join(tempfile.gettempdir(), 'dink_fireball_fx', o['name'])
    return o


def use_device(scene):
    scene.render.engine = 'CYCLES'
    if os.environ.get('DINK_CPU') == '1':
        scene.cycles.device = 'CPU'
        return
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
    scene.cycles.device = 'GPU' if found else 'CPU'


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
    pw.inputs[1].default_value = 2.0
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


def core_material(S):
    """the white-hot heart of the ball: an emitting sphere whose rim falls off to orange, so no hard disc shows"""
    mat = bpy.data.materials.new('M_Fire_Core')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (1.0, 0.93, 0.62, 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (1.0, 0.50, 0.06, 1)
    e = cr.elements.new(0.45)
    e.color = (1.0, 0.80, 0.30, 1)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = S['core_strength']
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    pw = nt.nodes.new('ShaderNodeMath')
    pw.operation = 'POWER'
    pw.inputs[1].default_value = 1.3
    nt.links.new(lw.outputs['Facing'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(lw.outputs['Facing'], pw.inputs[0])
    nt.links.new(pw.outputs[0], mix.inputs['Fac'])
    nt.links.new(em.outputs['Emission'], mix.inputs[1])
    nt.links.new(tr.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return mat


def build_sim(S, o, scene):
    rng = np.random.default_rng(S['seed'])
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=S['radius'], location=(0, 0, 0))
    flow = bpy.context.object
    flow.name = 'Fire_Flow'
    for v in flow.data.vertices:
        v.co *= 1.0 + rng.uniform(-0.10, 0.10)
    m = flow.modifiers.new('Fluid', 'FLUID')
    m.fluid_type = 'FLOW'
    fs = m.flow_settings
    fs.flow_type = 'FIRE'
    fs.flow_behavior = 'INFLOW'
    fs.fuel_amount = S['fuel']
    fs.surface_distance = 0.8
    fs.subframes = 2
    fs.use_initial_velocity = True
    fs.velocity_coord = (0.0, S['speed'], 0.0)
    fs.velocity_normal = S['normal']
    fs.velocity_random = 0.35
    total = S['warm'] + S['grid'] ** 2 + S['xfade']
    tex = bpy.data.textures.new('Fuel_Gusts', 'CLOUDS')
    tex.noise_scale = 0.12
    tex.noise_depth = 2
    tex.contrast = 2.0
    tex.intensity = 1.1
    fs.use_texture = True
    fs.noise_texture = tex
    fs.texture_map_type = 'AUTO'
    fs.texture_size = 1.0
    fs.texture_offset = 0.0
    fs.keyframe_insert('texture_offset', frame=1)
    fs.texture_offset = 4.0
    fs.keyframe_insert('texture_offset', frame=total)
    if S.get('pulse'):      # hellfire sheds clumps: the fuel comes in beats
        for f in range(1, total + 1, 3):
            fs.fuel_amount = S['fuel'] * (1.0 if (f // 3) % 2 == 0 else 0.25)
            fs.keyframe_insert('fuel_amount', frame=f)
    flow.hide_render = True

    # x across, y along the flight (the flames leave towards +y), z up
    lo = Vector((-0.75, -0.55, -0.7)) * (S['frame_m'] / 1.3)
    hi = Vector((0.75, 2.45, 0.95)) * (S['frame_m'] / 1.3)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(lo + hi) / 2)
    dom = bpy.context.object
    dom.name = 'Fire_Domain'
    dom.scale = hi - lo
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    m = dom.modifiers.new('Fluid', 'FLUID')
    m.fluid_type = 'DOMAIN'
    d = m.domain_settings
    d.domain_type = 'GAS'
    d.resolution_max = o['res']
    d.use_adaptive_domain = False
    d.time_scale = 1.0
    d.vorticity = S['vort']
    d.alpha = 0.0
    d.beta = S['beta']
    d.burning_rate = S['burn']
    d.flame_smoke = 0.0
    d.flame_vorticity = S['flame_vort']
    d.flame_ignition = 1.25
    d.flame_max_temp = 3.0
    for side in ('front', 'back', 'left', 'right', 'top', 'bottom'):
        setattr(d, 'use_collision_border_' + side, False)
    d.use_noise = False
    d.cache_type = 'ALL'
    d.cache_directory = os.path.join(o['cache'], 'sim')
    d.cache_frame_start = 1
    d.cache_frame_end = total
    scene.frame_start = 1
    scene.frame_end = total
    scene.render.fps = 24
    dom.data.materials.append(fire_material(S))

    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=S['core'], location=(0, 0, 0))
    core = bpy.context.object
    core.name = 'Fire_Core'
    bpy.ops.object.shade_smooth()
    core.data.materials.append(core_material(S))
    core.visible_shadow = False
    return dom, flow, total


def view_basis(view):
    """(camera position direction from the ball, right, up) of the two orthographic cameras"""
    if view == 'Front':      # ahead of the ball, looking back along the flight (+y), raised
        d = Vector((0.0, -math.cos(ELEV), math.sin(ELEV)))
        right = Vector((1.0, 0.0, 0.0))
    else:                    # behind the ball, looking along the flight (-y), raised
        d = Vector((0.0, math.cos(ELEV), math.sin(ELEV)))
        right = Vector((-1.0, 0.0, 0.0))
    up = d.cross(right).normalized()
    if up.z < 0:
        up = -up
    return d, right, up


def view_centre(S, view):
    """the point the frame's middle shows: the ball sits low in the frame from ahead (its trail rises behind it) and high from behind"""
    d, right, up = view_basis(view)
    return up * (S['frame_m'] * (0.17 if view == 'Front' else -0.17))


def cameras(S, scene):
    cams = {}
    for view in VIEWS:
        cam = bpy.data.cameras.new('Cam_' + view)
        cam.type = 'ORTHO'
        cam.ortho_scale = S['frame_m']
        cam.clip_start = 0.1
        cam.clip_end = 40
        ob = bpy.data.objects.new('Cam_' + view, cam)
        scene.collection.objects.link(ob)
        d, right, up = view_basis(view)
        c = view_centre(S, view)
        ob.location = c + d * 8.0
        ob.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        cams[view] = ob
    return cams


def load_exr(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1]


def save_png(arr, path):
    from PIL import Image
    a = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(a, 'RGBA' if a.shape[2] == 4 else 'RGB').save(path, optimize=True)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def stage_sim(S, o):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    dom, flow, total = build_sim(S, o, scene)
    cameras(S, scene)
    os.makedirs(o['cache'], exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(o['cache'], 'sim.blend'))
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        r = bpy.ops.fluid.bake_all()
    print('FIREBALL bake', r, 'frames', total)
    bpy.ops.wm.save_mainfile()


def render_setup(S, scene, px, samples):
    use_device(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.volume_step_rate = 0.5
    scene.cycles.volume_max_steps = 512
    scene.cycles.max_bounces = 2
    scene.cycles.volume_bounces = 0
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.resolution_percentage = 100
    scene.render.use_stamp = False
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '16'
    scene.view_settings.view_transform = 'Raw'
    scene.world = bpy.data.worlds.new('Black')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0


def stage_render(S, o, preview=False):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(o['cache'], 'sim.blend'))
    scene = bpy.context.scene
    render_setup(S, scene, 128 if preview else S['px'], 16 if preview else 40)
    n0 = S['warm'] + 1
    n = S['grid'] ** 2 + S['xfade']
    sub = 'preview' if preview else 'frames'
    os.makedirs(os.path.join(o['cache'], sub), exist_ok=True)
    frames = range(0, n, 6) if preview else range(n)
    for view in VIEWS:
        scene.camera = bpy.data.objects['Cam_' + view]
        for i in frames:
            scene.frame_set(n0 + i)
            scene.render.filepath = os.path.join(o['cache'], sub, '%s_%03d.exr' % (view, i))
            bpy.ops.render.render(write_still=True)
    print('FIREBALL rendered', len(frames), 'x', len(VIEWS))
    if preview:
        rows = []
        for view in VIEWS:
            fr = [encode_frame(S, load_exr(os.path.join(o['cache'], sub, '%s_%03d.exr' % (view, i)))[..., :3]) for i in frames]
            rows.append(np.concatenate([over(f, (0.17, 0.33, 0.12)) for f in fr], 1))
        save_png(np.concatenate(rows, 0), os.path.join(o['cache'], 'preview.png'))


def over(f, bg):
    return f[..., :3] * f[..., 3:4] + np.array(bg, np.float32)[None, None, :] * (1 - f[..., 3:4])


def encode_frame(S, hdr):
    """HDR flame -> straight sRGB colour + opacity: an opaque glowing body where the fire is thick, wisps at its edges"""
    # the simulation's voxel columns show as fine vertical streaks when the missile fills the screen: a 1 px blur takes them out
    k = np.array((0.25, 0.5, 0.25), np.float32)
    for _ in range(max(1, int(round(2 * hdr.shape[0] / 256.0)))):
        p = np.pad(hdr, ((1, 1), (0, 0), (0, 0)), mode='edge'); hdr = p[:-2] * k[0] + p[1:-1] * k[1] + p[2:] * k[2]
        p = np.pad(hdr, ((0, 0), (1, 1), (0, 0)), mode='edge'); hdr = p[:, :-2] * k[0] + p[:, 1:-1] * k[1] + p[:, 2:] * k[2]
    l = hdr.max(-1)
    hue = np.where(l[..., None] > 1e-5, hdr / np.maximum(l, 1e-6)[..., None], 0.0)
    # the colour stays a flame's (never a dark brown rim): the fall-off towards the edge is carried by the opacity
    tone = 0.58 + 0.42 * np.power(1.0 - np.exp(-l / S['l0']), S['gamma'])
    a = 1.0 - np.exp(-l / S['l_alpha'])
    return np.concatenate([srgb(hue * tone[..., None]), a[..., None]], -1).astype(np.float32)


def spark_layers(S, n, px):
    """sparks shed by the ball: each leaves the ball's rim, falls behind along +y, wavers and dims, once per loop. The same
    3D paths are projected through both cameras. Returns {view: [n arrays px x px x 4, straight colour + alpha]}"""
    rng = np.random.default_rng(S['seed'] + 7)
    out = {v: [np.zeros((px, px, 4), np.float32) for _ in range(n)] for v in VIEWS}
    scale = px / S['frame_m']
    for _ in range(S['sparks']):
        ang = rng.uniform(0, 2 * math.pi)
        r0 = S['radius'] * rng.uniform(0.6, 1.25)
        p0 = np.array([math.cos(ang) * r0, rng.uniform(-0.05, 0.1), math.sin(ang) * r0])
        life = int(rng.uniform(0.3, 0.7) * n)
        start = rng.integers(0, n)
        vy = S['speed'] * rng.uniform(0.45, 0.9) * S['spark_len'] / 2.6
        spread = rng.uniform(0.15, 0.6)
        wob = rng.uniform(0.02, 0.07); freq = rng.uniform(1.0, 3.0); ph = rng.uniform(0, 6.28)
        size = rng.uniform(0.8, 1.6) * px / 256.0
        for i in range(life):
            u = i / life
            t = i / S['fps']
            p = p0 + np.array([math.cos(ang) * spread * t + wob * math.sin(ph + freq * 6.28 * u), vy * t, math.sin(ang) * spread * t + wob * math.cos(ph * 1.7 + freq * 6.28 * u) + 0.25 * t * t])
            bright = (1.0 - u) ** 1.4 * min(1.0, i / 1.5)
            if bright < 0.04:
                continue
            for view in VIEWS:
                d, right, up = view_basis(view)
                c = view_centre(S, view)
                q = Vector(p) - c
                x = px / 2 + q.dot(right) * scale
                y = px / 2 - q.dot(up) * scale
                if not (3 < x < px - 4 and 3 < y < px - 4):
                    continue
                f = out[view][(start + i) % n]
                ix, iy = int(x), int(y)
                for dy in range(-3, 4):
                    for dx in range(-3, 4):
                        d2 = (ix + dx + 0.5 - x) ** 2 + (iy + dy + 0.5 - y) ** 2
                        g = math.exp(-d2 / (2 * (0.75 * size) ** 2)) * bright
                        if g < 0.02:
                            continue
                        pxl = f[iy + dy, ix + dx]
                        col = np.array((1.0, 0.50 + 0.45 * bright, 0.10 + 0.55 * bright), np.float32)
                        pxl[:3] = pxl[:3] * (1 - g) + col * g
                        pxl[3] = max(pxl[3], min(1.0, g * 1.5))
    return out


def loop_frames(S, o, view):
    nf = S['grid'] ** 2
    xf = S['xfade']
    raw = [load_exr(os.path.join(o['cache'], 'frames', '%s_%03d.exr' % (view, i)))[..., :3] for i in range(nf + xf)]
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
    g, px = S['grid'], S['px']
    sp = spark_layers(S, g * g, px)
    for view in VIEWS:
        name = '%s_%s' % (o['name'], view)
        folder = os.path.join(KIT, S['folder'], name)
        os.makedirs(folder, exist_ok=True)
        frames = []
        for t, hdr in enumerate(loop_frames(S, o, view)):
            f = encode_frame(S, hdr)
            s = sp[view][t]
            pr = np.maximum(f[..., :3] * f[..., 3:4], f[..., :3] * f[..., 3:4] * (1 - s[..., 3:4]) + s[..., :3] * s[..., 3:4])      # sparks are light: never darker than the flame under them
            a = f[..., 3] + s[..., 3] * (1 - f[..., 3])
            frames.append(np.concatenate([pr / np.maximum(a, 1e-4)[..., None], a[..., None]], -1))
        # nothing may touch the frame's edge (a card edge would show)
        yy, xx = np.mgrid[0:px, 0:px].astype(np.float32)
        edge = np.clip(np.minimum(np.minimum(xx, px - 1 - xx), np.minimum(yy, px - 1 - yy)) / (px * 0.06), 0, 1)
        atlas = np.zeros((g * px, g * px, 4), np.float32)
        for i, f in enumerate(frames):
            f[..., 3] *= edge
            r, c = divmod(i, g)
            atlas[r * px:(r + 1) * px, c * px:(c + 1) * px] = f
        save_png(atlas, os.path.join(folder, 'T_FX_%s_Flipbook.png' % name))
        strip = np.concatenate([over(frames[i], (0.17, 0.33, 0.12)) for i in range(0, g * g, max(1, g * g // 8))][:8], 1)
        save_png(strip, os.path.join(folder, 'frames_strip.png'))
        cover = float(np.mean([f[..., 3].mean() for f in frames]))
        manifest = {
            'name': 'FX_' + name,
            'class': 'effect flipbook (texture atlas; no mesh)',
            'lod0_triangles': 0,
            'dimensions_m': [S['frame_m'], S['frame_m'], 0.0],
            'textures': [{'file': '%s/%s/%s/T_FX_%s_Flipbook.png' % (ROOT, S['folder'], name, name), 'size_px': [g * px, g * px],
                          'channels': 'RGB straight colour (sRGB) + alpha = opacity; %d x %d frames of %d px, row by row from the top left' % (g, g, px)}],
            'flipbook': {'frames': g * g, 'grid': [g, g], 'fps': S['fps'], 'loop': True, 'billboard_size_m': [S['frame_m'], S['frame_m']], 'blend': 'translucent',
                         'glow': S['glow'], 'hot': list(S['hot']), 'alpha_coverage': round(cover, 3),
                         'ball_centre_uv': [0.5, 0.5 + (0.17 if view == 'Front' else -0.17)]},
            'preview': '%s/%s/%s/frames_strip.png' % (ROOT, S['folder'], name),
            'source_blend': '%s/%s/%s_Front/FX_%s.blend' % (ROOT, S['folder'], o['name'], o['name']),
            'source_note': 'a Mantaflow gas simulation (a ball of burning fuel in a head wind, resolution %d) rendered by Cycles as an emitting volume with an orthographic camera raised %d degrees, %s; one frame per step, the loop closed by a %d-frame cross-fade; sparks are analytic 3D paths projected through the same camera' % (
                o['res'], round(math.degrees(ELEV)), 'from ahead of the ball (it flies at the camera)' if view == 'Front' else 'from behind the ball (it flies away)', S['xfade']),
            'build': 'DINK_CPU=1 blender -b --factory-startup -t 4 --python FableF/tools/build_fireball_fx.py -- ' + o['name'],
            'families': ['missile_fx'] + S['seqs'][view],
            'supersedes': 'the upright side-view fireball card on the south and north flights',
            'dresses': S['dresses'],
        }
        json.dump(manifest, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
        print('FIREBALL atlas', name, 'coverage', round(cover, 3))
    # the source scene without its cache path
    src = os.path.join(o['cache'], 'sim.blend')
    if os.path.isfile(src):
        bpy.ops.wm.open_mainfile(filepath=src)
        dom = bpy.data.objects['Fire_Domain']
        dom.modifiers['Fluid'].domain_settings.cache_directory = '//cache_fireball'
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(KIT, S['folder'], o['name'] + '_Front', 'FX_%s.blend' % o['name']), compress=True, relative_remap=False)


def main():
    o = args()
    S = SETS[o['name']]
    if o['stage'] in ('sim', 'all', 'preview'):
        stage_sim(S, o)
    if o['stage'] == 'preview':
        stage_render(S, o, preview=True)
    if o['stage'] in ('render', 'all'):
        stage_render(S, o)
    if o['stage'] in ('atlas', 'all'):
        stage_atlas(S, o)


if __name__ == '__main__':
    main()
