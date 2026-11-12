"""Extract frozen material graphs and independent reuse fixtures; no game edits."""
import bpy, hashlib, json
from pathlib import Path
from mathutils import Vector

D = Path(__file__).resolve().parents[1]
ART = D.parents[1]
SOURCE = ART / 'StonebrookExterior/Refinements/House439ClosedEavesV1/Packet/Source/House439_ClosedEaves.blend'
EXISTING = D.parent / 'ArchitecturalSurfaces2mV1/SharedArchitecturalSurfaces_Source.blend'
ROLES = ('FieldstoneSeed2m', 'LimeMortarSoot2m', 'WeatheredTimber2m', 'IronLead2m',
         'ThinWavyGlass2m', 'FieldstoneWall2m', 'LaidWeatheredPhotoCoatFrayedCut2m_SourceTrial')
import importlib.util
_spec = importlib.util.spec_from_file_location('material_fingerprint', Path(__file__).parent/'material_fingerprint.py')
_fp = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_fp)
snapshot = _fp.snapshot

source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
existing_sha = hashlib.sha256(EXISTING.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(SOURCE), link=False) as (available, loaded):
    loaded.materials = ['MI_Shared_' + role for role in ROLES]
frozen = {role: snapshot(bpy.data.materials['MI_Shared_' + role]) for role in ROLES}
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(EXISTING), link=False) as (available, loaded):
    loaded.materials = [n for n in available.materials if n.startswith('MI_Shared_')]
comparisons = {}
for role in ROLES:
    m = bpy.data.materials.get('MI_Shared_' + role)
    if m:
        current = snapshot(m)[1]
        comparisons[role] = {'current_library_fingerprint': current,
                             'frozen_source_fingerprint': frozen[role][1], 'exact': current == frozen[role][1]}
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(SOURCE), link=False) as (available, loaded):
    loaded.materials = ['MI_Shared_' + role for role in ROLES]
(D / 'Textures').mkdir(exist_ok=True)
images = []
for im in bpy.data.images:
    if im.source != 'FILE' or im.size[0] == 0:
        continue
    assert im.packed_file is not None
    payload = bytes(im.packed_file.data)
    name = Path(im.filepath).name
    target = D / 'Textures' / name
    if target.exists():
        assert target.read_bytes() == payload
    else:
        target.write_bytes(payload)
    im.filepath = '//Textures/' + name
    images.append({'image': im.name, 'file': 'Textures/' + name,
                   'sha256': hashlib.sha256(payload).hexdigest(), 'size': list(im.size),
                   'colorspace': im.colorspace_settings.name})
materials = {}
for role in ROLES:
    m = bpy.data.materials['MI_Shared_' + role]
    assert snapshot(m)[1] == frozen[role][1]
    m.use_fake_user = True
    materials[role] = m
library_mesh_count = sum(o.type == 'MESH' for o in bpy.data.objects)
library = D / 'ClosedEavesSurfaces_Source.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(library), relative_remap=False, compress=True)
# Independent 2m/4m physical repeat fixtures, including both composite selectors.
variants = {role: (0, 1) if role in ('LimeMortarSoot2m', 'WeatheredTimber2m', 'IronLead2m', ROLES[-1]) else (0,) for role in ROLES}
fixtures = []
ordinal = 0
for role in ROLES:
    for selector in variants[role]:
        for width in (2., 4.):
            x = (ordinal % 4) * 5.0
            y = (ordinal // 4) * 3.0
            m = bpy.data.meshes.new('IndependentRepeat')
            m.from_pydata([(x-width/2, y-1, 0), (x+width/2, y-1, 0),
                          (x+width/2, y+1, 0), (x-width/2, y+1, 0)], [], [(0, 1, 2, 3)])
            m.materials.append(materials[role])
            uv = m.uv_layers.new(name='UV0')
            mask = m.uv_layers.new(name='UV1_SharedData')
            color = m.color_attributes.new(name='SharedSurfaceData', type='FLOAT_COLOR', domain='CORNER')
            for i, coord in enumerate(((0, 0), (width/2, 0), (width/2, 1), (0, 1))):
                uv.data[i].uv = coord
                mask.data[i].uv = (selector, 0)
                color.data[i].color = (.44, .41, .35, 1) if role == 'LimeMortarSoot2m' and selector == 0 else (1, 1, 1, .15)
            o = bpy.data.objects.new(f'{role}_{selector}_{int(width)}m', m)
            bpy.context.scene.collection.objects.link(o)
            fixtures.append({'object': o.name, 'role': role, 'selector': selector,
                             'width_m': width, 'height_m': 2, 'UV0_extent': [width/2, 1]})
            ordinal += 1
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 16
scene.cycles.use_denoising = True; scene.render.compositor_device = 'CPU'
scene.render.resolution_x = 1500; scene.render.resolution_y = 1200; scene.render.resolution_percentage = 100
world = bpy.data.worlds.new('Neutral reuse world'); world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.45, .45, .45, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = .7; scene.world = world
light = bpy.data.lights.new('Reuse area', 'AREA'); light.energy = 6500; light.size = 12
o = bpy.data.objects.new(light.name, light); scene.collection.objects.link(o); o.location = (4, -3, 20)
o.rotation_euler = (Vector((7.5, 7.5, 0))-o.location).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.objects.new('Reuse camera', bpy.data.cameras.new('Reuse camera'))
scene.collection.objects.link(cam); cam.location = (7.5, 5, 35)
cam.rotation_euler = (Vector((7.5, 7.5, 0))-cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 25; scene.camera = cam
bpy.ops.wm.save_as_mainfile(filepath=str(D/'IndependentReuse_2m4m.blend'), relative_remap=False, compress=True)
report = {'scope': 'candidate library extraction and independent reuse, not registry/native approval',
          'frozen_cottage_source_sha256': source_sha, 'current_library_sha256_unchanged': existing_sha,
          'roles': {r: {'fingerprint': frozen[r][1], 'graph': frozen[r][0]} for r in ROLES},
          'current_opaque_library_comparison': comparisons, 'images': images, 'fixtures': fixtures,
          'no_cottage_geometry_in_library': library_mesh_count == 0}
(D/'EXTRACTION.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_sha
assert hashlib.sha256(EXISTING.read_bytes()).hexdigest() == existing_sha
scene.render.filepath = str(D/'IndependentReuse_2m4m.png')
bpy.ops.render.render(write_still=True)
print('comparisons', comparisons, 'images', len(images), 'fixtures', len(fixtures), flush=True)
