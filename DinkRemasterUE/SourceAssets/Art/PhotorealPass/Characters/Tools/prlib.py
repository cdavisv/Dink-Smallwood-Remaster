"""Shared helpers for the photoreal character pass (Blender 5.2 batch)."""
import bpy, bmesh, math, json, os, sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

OUT = Path(__file__).resolve().parents[1]
R = OUT.parents[4]
CHARS = OUT.parents[1] / 'Characters'

def log(*a):
    print('[PR]', *a, flush=True)

def args():
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

def use_hip_gpu(scene=None):
    """Cycles on the RX 6800 via HIP (see CYCLES_GPU.md); only that device, preferences changed in memory only.
    PR_CPU=1 in the environment forces the CPU (use it to retry after an 'Out of memory')."""
    scene = scene or bpy.context.scene; scene.render.engine = 'CYCLES'
    if os.environ.get('PR_CPU'): scene.cycles.device = 'CPU'; return False
    found = False
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'HIP'; prefs.refresh_devices()
        for d in prefs.devices:
            d.use = (d.type == 'HIP' and 'Radeon RX 6800' in d.name); found |= d.use
    except Exception as ex: log('HIP not available', ex)
    scene.cycles.device = 'GPU' if found else 'CPU'; log('Cycles device', scene.cycles.device); return found

def save_blend(filepath=None, **kw):
    """Save the .blend with relative image / library paths (the repository is public: no absolute paths inside files).
    filepath None = save in place; copy=True keeps the current file as the working file."""
    def rel():
        try: bpy.ops.file.make_paths_relative()
        except Exception as ex: log('make_paths_relative skipped:', str(ex)[:120])
    if filepath is None:
        rel(); bpy.ops.wm.save_mainfile(); return
    if kw.get('copy'):
        if bpy.data.filepath: rel()
        bpy.ops.wm.save_as_mainfile(filepath=str(filepath), **kw); return
    bpy.ops.wm.save_as_mainfile(filepath=str(filepath), **kw); rel(); bpy.ops.wm.save_mainfile()

def deselect():
    for o in list(bpy.context.view_layer.objects):
        if o is not None: o.select_set(False)

def activate(o):
    deselect(); o.select_set(True); bpy.context.view_layer.objects.active = o

def new_obj(name, verts, faces, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    o = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(o)
    return o

def co_np(me):
    a = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', a); return a.reshape(-1, 3).astype(np.float64)

def set_co(me, a):
    me.vertices.foreach_set('co', np.asarray(a, np.float32).ravel()); me.update()

def normals_np(me):
    a = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('normal', a); return a.reshape(-1, 3).astype(np.float64)

def bvh_of(objs):
    """World-space BVH of one or more mesh objects (evaluated)."""
    if not isinstance(objs, (list, tuple)): objs = [objs]
    V = []; F = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); base = len(V)
        mw = o.matrix_world
        V += [mw @ v.co for v in me.vertices]
        F += [[base + i for i in p.vertices] for p in me.polygons]
        e.to_mesh_clear()
    return BVHTree.FromPolygons(V, F)

def smooth_shade(o, on=True):
    o.data.polygons.foreach_set('use_smooth', [on] * len(o.data.polygons)); o.data.update()

def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def apply_mods(o):
    activate(o)
    for m in list(o.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as ex: log('modifier apply failed', o.name, m.name, ex); o.modifiers.remove(m)

def subdivide(o, levels=1, simple=False):
    m = o.modifiers.new('sd', 'SUBSURF'); m.levels = levels; m.render_levels = levels
    if simple: m.subdivision_type = 'SIMPLE'
    activate(o); bpy.ops.object.modifier_apply(modifier=m.name)

def join(objs, name):
    bpy.context.view_layer.update(); deselect()
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=list(objs), selected_objects=list(objs)):
        bpy.ops.object.join()
    o = objs[0]; o.name = name; o.data.name = name
    return o

def dup(o, name):
    n = o.copy(); n.data = o.data.copy(); n.name = name; n.data.name = name
    bpy.context.scene.collection.objects.link(n); return n

# ---------------------------------------------------------------- rendering
def setup_world(sun_elev=40, sun_az=215, strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('PR_Sky'); w.use_nodes = True; sc.world = w
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground')
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
        try: sky.sky_type = t; break
        except Exception: pass
    sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_az)
    try: sky.sun_intensity = 1.0; sky.sun_size = math.radians(2.5)
    except Exception: pass
    bg.inputs[1].default_value = strength
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    return w

def ground_mat():
    m = bpy.data.materials.new('PR_Ground'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 9; n.inputs['Detail'].default_value = 8
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color = (.10, .075, .05, 1); r.color_ramp.elements[1].color = (.24, .19, .13, 1)
    nt.links.new(n.outputs[0], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .95
    n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 60; n2.inputs['Detail'].default_value = 6
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .6; bp.inputs['Distance'].default_value = .02
    nt.links.new(n2.outputs[0], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def setup_render(samples=64, res=(900, 1200), engine='CYCLES'):
    sc = bpy.context.scene
    sc.render.engine = engine
    if engine == 'CYCLES':
        use_hip_gpu(sc); sc.cycles.samples = samples; sc.cycles.use_denoising = True
        sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = .03
        sc.cycles.transparent_max_bounces = 24; sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    try: sc.view_settings.view_transform = 'AgX'
    except Exception: sc.view_settings.view_transform = 'Filmic'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.render.image_settings.file_format = 'PNG'
    if not sc.world or sc.world.name != 'PR_Sky': setup_world()
    if 'PR_GroundPlane' not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); g = bpy.context.object; g.name = 'PR_GroundPlane'
        g.data.materials.append(ground_mat())
    if sc.camera is None or sc.camera.name != 'PR_Cam':
        cd = bpy.data.cameras.new('PR_Cam'); c = bpy.data.objects.new('PR_Cam', cd); sc.collection.objects.link(c); sc.camera = c
    return sc

def shoot(path, loc, target, lens=70, res=None, exposure=None):
    sc = bpy.context.scene; c = sc.camera
    c.location = loc; c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = lens
    c.data.clip_start = .02
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    if exposure is not None: sc.view_settings.exposure = exposure
    sc.render.filepath = str(path); bpy.ops.render.render(write_still=True); log('rendered', path)

# ---------------------------------------------------------------- posing
def load_idle():
    return {n: Matrix(m) for n, m in json.loads((CHARS / 'Animations/Unarmed/idle_boundary_pose.json').read_text())['bones'].items()}

def reset_pose(arm):
    if arm.animation_data: arm.animation_data.action = None
    for b in arm.pose.bones:
        b.rotation_mode = 'QUATERNION'; b.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

def apply_world_pose(arm, mats):
    """mats: bone -> armature-space matrix. Applied parent-first."""
    reset_pose(arm)
    def depth(b):
        d = 0
        while b.parent: b = b.parent; d += 1
        return d
    for b in sorted(arm.pose.bones, key=depth):
        if b.name in mats:
            b.matrix = Matrix(mats[b.name]); bpy.context.view_layer.update()

def rot_bone(arm, name, axis, deg):
    """Rotate a pose bone about an armature-space axis through its head."""
    b = arm.pose.bones[name]; bpy.context.view_layer.update()
    m = b.matrix.copy(); h = m.translation.copy()
    r = Matrix.Rotation(math.radians(deg), 4, Vector(axis))
    m2 = Matrix.Translation(h) @ r @ Matrix.Translation(-h) @ m
    b.matrix = m2; bpy.context.view_layer.update()
