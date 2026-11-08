"""Work-only composition revision; immutable V3 source and assets stay untouched."""
import ast, hashlib, json, math, os, random
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(os.environ.get('DINK_PROJECT_ROOT', str(Path(__file__).resolve().parents[4])))
BASE = ROOT / 'SourceAssets/Art/Stonebrook/InteriorVistaV3'
OUT = Path(__file__).resolve().parent
source = BASE / 'Stonebrook_InteriorVista_Candidate_V3.blend'
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
texture_receipt = []
for image in bpy.data.images:
    if image.source != 'FILE':
        continue
    original = image.filepath
    relative = original.rsplit('SourceAssets/Art/', 1)[-1]
    path = ROOT / 'SourceAssets/Art' / relative
    assert path.is_file(), (image.name, original, str(path))
    image.filepath = str(path)
    image.reload()
    texture_receipt.append({'image': image.name, 'project_path': str(path.relative_to(ROOT)),
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'packed': False})
(OUT / 'texture-references.json').write_text(json.dumps(texture_receipt, indent=2) + '\n')
code = ast.parse((BASE / 'build_vista.py').read_text())
height_node = next(n for n in code.body if isinstance(n, ast.FunctionDef) and n.name == 'height')
scope = {'math': math}
exec(compile(ast.Module(body=[height_node], type_ignores=[]), '<immutable V3 terrain height>', 'exec'), scope)
height = scope['height']
collection = bpy.data.collections.new('Vista_HorizonV4_Additions')
scene.collection.children.link(collection)
rng = random.Random(143904)
additions = []

def add(name, asset, x, y, scale):
    template = (bpy.data.objects.get(asset) or bpy.data.objects.get(asset + '_LOD0') or
                next((o for o in bpy.data.objects if o.type == 'MESH' and o.data.name.startswith(asset)), None))
    assert template and template.type == 'MESH', asset
    ob = bpy.data.objects.new(name, template.data)
    collection.objects.link(ob)
    ob.location = (x, y, height(x, y))
    ob.rotation_euler.z = rng.uniform(-math.pi, math.pi)
    ob.scale = scale
    prefix = ('/Game/Dink/Foliage/StonebrookFields/Refinements/' if 'Pine' in asset
              else '/Game/Dink/Kits/StonebrookExterior/')
    additions.append({'name': name, 'reused_asset': asset,
        'local_blender_m': list(ob.location), 'blender_yaw_deg': math.degrees(ob.rotation_euler.z),
        'scale': list(scale), 'collision': False, 'camera_occluder': False,
        'asset_path_proposal': prefix + asset + '.' + asset,
        'world_cm_proposal': [-183806.0975 + x * 100, 393595.98 - y * 100, ob.location.z * 100],
        'UE_yaw_deg': -math.degrees(ob.rotation_euler.z)})

# A dense, irregular meadow crest masks the finite terrain's rear edge at the
# low sight line through the door. Trees supply a deeper woodland silhouette.
for i in range(35):
    x = -13 + i * .76 + rng.uniform(-.22, .22)
    y = rng.uniform(-30.8, -28.6)
    width = rng.uniform(1.1, 1.6)
    add('VistaV4_CrestGrass_%02d' % i, 'SM_Grass_Meadow_01', x, y,
        (width, width, rng.uniform(1.6, 2.1)))
for i, x in enumerate([-12, -8.8, -5.5, -2.1, 1.5, 5, 8.5, 12]):
    scale = rng.uniform(.9, 1.15)
    add('VistaV4_Woodland_%02d' % i, 'SM_Pine_Stonebrook_V3', x,
        rng.uniform(-30.8, -29.2), (scale, scale, scale))

(OUT / 'additions.json').write_text(json.dumps({'schema': 'dink-vista-composition-additions/1',
    'base_scene_sha256': before, 'new_mesh_packages': 0, 'instances': additions,
    'status': 'Work-only trial; native visual and loaded bounds acceptance pending'}, indent=2) + '\n')
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 75
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = .8
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (.40, .55, .80, 1)
background.inputs['Strength'].default_value = .45
light = bpy.data.lights.new('HorizonTrialSun', 'SUN')
sun = bpy.data.objects.new('HorizonTrialSun', light)
scene.collection.objects.link(sun)
light.energy = 2.2
light.angle = math.radians(4)
sun.rotation_euler = (math.radians(-35), math.radians(-25), 0)
data = bpy.data.cameras.new('NativeDoorReadbackCamera')
camera = bpy.data.objects.new('NativeDoorReadbackCamera', data)
scene.collection.objects.link(camera)
camera.location = (-.45, 4.688783634, 2.2416407865)
direction = Vector((0, -math.cos(math.radians(18)), -math.sin(math.radians(18))))
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
data.lens = 25.7
data.sensor_width = 36
scene.camera = camera
scene.render.filepath = str(OUT / 'native-door-source-preview.png')
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source == 'FILE':
        image.filepath = '//' + os.path.relpath(bpy.path.abspath(image.filepath), OUT)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Stonebrook_HorizonV4.blend'))
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
print('HORIZON V4 WORK TRIAL COMPLETE', flush=True)
