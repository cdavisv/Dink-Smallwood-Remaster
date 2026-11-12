"""Deterministic Blender build of the SCR_440 kit: two-storey house + farm/yard props.

    python3 make_textures_440.py                       # host Python: tiling building PBR sets (seed 440)
    blender -b --factory-startup -t 3 -P build_440.py [-- --no-bake] [-- --only SM_X]

Writes KIT_Stonebrook440.blend, art_manifest.json and baked prop textures under Textures/.
Reads (never writes) the shared Stonebrook limewash and wrought-iron PBR sets by relative path.
No downloaded meshes or images; no generative image models.
"""
import bpy, bmesh, sys, json, math, time
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix

ART = Path(__file__).resolve().parent
UE = ART.parents[2]
REPO = UE.parent
sys.path.insert(0, str(ART)); sys.path.insert(0, str(REPO / 'tools/blender'))
from dinkasset import conventions as C, common, make_lods      # noqa: E402
import lib440 as L, mat440 as MT, house440 as HS, props440 as PR  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
NO_BAKE = '--no-bake' in argv
ONLY = argv[argv.index('--only') + 1].split(',') if '--only' in argv else None
TEX = ART / 'Textures'; SHARED = UE / 'SourceAssets/Art/Stonebrook/Textures'
SEED = 440
SOURCE = 'Original deterministic Blender geometry; build_440.py seed 440; procedural numpy/Cycles-baked textures; no third-party meshes or images'
PATH = 'Stonebrook440'

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1.0
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.use_denoising = False
L.STATE['rng'] = np.random.default_rng(SEED)
import mathutils.noise as mnoise
mnoise.seed_set(SEED)
t_start = time.time()

# ----------------------------------------------------------------------------- materials
def tex(name):
    return {s: TEX / f'T_S440_{name}_{s}.png' for s in ('BC', 'N', 'ORM')}

M = {
    'rubble': MT.image_material('MI_S440_Rubble', tex('Rubble')),
    'thatch': MT.image_material('MI_S440_Thatch', tex('Thatch')),
    'oak': MT.image_material('MI_S440_WeatheredOak', tex('WeatheredOak')),
    'glass': MT.image_material('MI_S440_LeadedGlass', tex('LeadedGlass')),
    # Shared Stonebrook sets, reused by reference so the import binds the existing MI_ assets.
    'limewash': MT.image_material('MI_Stonebrook_Limewash', {s: SHARED / f'T_Stonebrook_Limewash_{s}.png' for s in ('BC', 'N', 'ORM')}, normal_strength=.38),
    'iron': MT.image_material('MI_Stonebrook_WroughtIron', {s: SHARED / f'T_Stonebrook_WroughtIron_{s}.png' for s in ('BC', 'N', 'ORM')}, normal_strength=.38),
}
P = {
    'ash': MT.wood_material('SRC_S440_Ash', (.40, .30, .19), (.22, .145, .08), rings_per_m=260, rough=.58),
    'oak': MT.wood_material('SRC_S440_OakYard', (.20, .16, .115), (.10, .075, .05), rings_per_m=200, rough=.74, weather=.75),
    'elm': MT.wood_material('SRC_S440_Elm', (.33, .24, .16), (.17, .115, .07), rings_per_m=150, rough=.8, weather=.35,
                            bark_dark=(.055, .047, .038), bark_light=(.19, .17, .14)),
    'firewood': MT.wood_material('SRC_S440_Firewood', (.45, .34, .22), (.26, .17, .10), rings_per_m=170, rough=.8, weather=.15,
                                 bark_dark=(.06, .05, .04), bark_light=(.22, .195, .16)),
    'iron': MT.iron_material('SRC_S440_ForgedIron'),
    'straw': MT.straw_material('SRC_S440_Straw', base=(.60, .43, .15), dark=(.17, .11, .045), green=.1),
    'twine': MT.straw_material('SRC_S440_Twine', base=(.30, .22, .11), dark=(.08, .055, .03), rough=.85),
    'water': MT.water_material('SRC_S440_Water'),
}
MANIFEST_MATERIALS = {}


def record_material(mat, rel_textures, normal_strength=1.0, notes=None):
    entry = {'name': mat.name, 'textures': rel_textures, 'normal_flip_green': True, 'normal_strength': normal_strength}
    if notes:
        entry['notes'] = notes
    MANIFEST_MATERIALS[mat.name] = entry


for key, mname in (('rubble', 'Rubble'), ('thatch', 'Thatch'), ('oak', 'WeatheredOak'), ('glass', 'LeadedGlass')):
    record_material(M[key], {s: f'Textures/T_S440_{mname}_{s}.png' for s in ('BC', 'N', 'ORM')})
for key, mname in (('limewash', 'Limewash'), ('iron', 'WroughtIron')):
    record_material(M[key], {s: f'../Stonebrook/Textures/T_Stonebrook_{mname}_{s}.png' for s in ('BC', 'N', 'ORM')}, .38,
                    'existing Stonebrook interior set, reused by reference (unchanged)')

ASSETS = {}
OFFSETS = {}


def place(coll, offset):
    for ob in coll.objects:
        ob.location = offset
    OFFSETS[coll.name] = list(offset)


def asset_record(name, cls, ob, ucx, extra):
    co = np.array([v.co[:] for v in ob.data.vertices])
    mn, mx = co.min(0), co.max(0)
    ASSETS[name] = dict(cls=cls, dimensions_m=[float(v) for v in mx - mn], bounds_min_m=[float(v) for v in mn],
                        bounds_max_m=[float(v) for v in mx], materials=[s.material.name for s in ob.material_slots],
                        collision_hulls=len(ucx), blend_collection=name, **extra)


# ----------------------------------------------------------------------------- house
def build_house():
    name = 'SM_House_Stonebrook_TwoStorey_01'
    coll = L.new_collection(name, 'building', PATH, SOURCE)
    stones = json.loads((TEX / 'rubble_stones.json').read_text())['stones']
    house = HS.House(M, TEX, stones)
    info = house.build()
    ob = L.join_pieces(name, smooth_angle=32)
    house.collision(coll, name)
    ucx = [o for o in coll.objects if o.name.startswith('UCX_')]
    delta, dims = L.recenter([ob] + ucx)
    info['door_local_m'] = [info['door_local_m'][i] - delta[i] for i in range(3)]
    info['pivot_shift_m'] = list(delta)
    for mat in M.values():
        if mat.name not in [s.material.name for s in ob.material_slots]:
            pass
    asset_record(name, 'building', ob, ucx, dict(role='house', origin_replaces=['S440_P03', 'S440_P11', 'S440_P04', 'S440_P08', 'S440_P09'],
                                                   house=info, tex_px=2048))
    place(coll, (0, 0, 0))


# ----------------------------------------------------------------------------- props
def build_prop(i, name, cls, builder, origin, desc):
    coll = L.new_collection(name, cls, PATH, SOURCE + '; ' + desc)
    out = builder(P)
    cols, px = out[0], out[1]
    ob = L.join_pieces(name, smooth_angle=38)
    for k, c in enumerate(cols, 1):
        if c[0] == 'hull':
            L.collision_hull(coll, name, k, c[1])
        else:
            L.collision_box(coll, name, k, c[0], c[1], c[2])
    ucx = [o for o in coll.objects if o.name.startswith('UCX_')]
    L.recenter([ob] + ucx)
    coll['dink_tex_px'] = px
    L.smart_uv(ob)
    stats = {}
    if not NO_BAKE:
        short = name[3:]
        t0 = time.time()
        mat, stats = MT.bake_asset(ob, short, px, TEX)
        stats['bake_s'] = round(time.time() - t0, 1)
        record_material(mat, {s: f'Textures/T_S440_{short}_{s}.png' for s in ('BC', 'N', 'ORM')}, 1.0,
                        'unique baked set from procedural Cycles source material(s); normals baked at physical strength')
    bmh = bmesh.new(); bmh.from_mesh(ob.data)
    hull = bmesh.ops.convex_hull(bmh, input=bmh.verts[:])
    hv = sorted({tuple(round(c, 4) for c in v.co) for v in hull['geom'] if isinstance(v, bmesh.types.BMVert)})
    bmh.free()
    extra = dict(role='prop', original_origin=origin, description=desc, tex_px=px, bake=stats, hull_points_m=hv)
    if len(out) > 2:
        extra['pieces'] = out[2]
    asset_record(name, cls, ob, ucx, extra)
    place(coll, (6 + (i % 6) * 2.6, -12 - (i // 6) * 3.2, 0))
    print('built', name, 'tris', sum(len(p.vertices) - 2 for p in ob.data.polygons), flush=True)


if not ONLY or 'SM_House_Stonebrook_TwoStorey_01' in ONLY:
    build_house(); print('house built', round(time.time() - t_start, 1), 's', flush=True)
for i, (name, cls, builder, origin, desc) in enumerate(PR.ASSETS):
    if ONLY and name not in ONLY:
        continue
    build_prop(i, name, cls, builder, origin, desc)

# ----------------------------------------------------------------------------- LODs (3 levels) for every asset
def keep_stalk_lods(asset):
    """LOD1/2 = decimated bale body + loose stalks copied from LOD0 (all in LOD1, every second in LOD2),
    so the silhouette keeps its stalks instead of decimation folding them flat."""
    log = []; lod0 = make_lods._rename_lod0(asset, log); log = []
    def split(keep_stalk, every=1):
        me = lod0.data.copy(); bm = bmesh.new(); bm.from_mesh(me)
        lay = bm.faces.layers.float.get('stalk')
        bad = [f for f in bm.faces if (f[lay] > .5) != keep_stalk]
        bmesh.ops.delete(bm, geom=bad, context='FACES')
        if keep_stalk and every > 1:
            seen = set(); comps = []
            for f in bm.faces:
                if f.index in seen: continue
                stack = [f]; comp = []
                while stack:
                    x = stack.pop()
                    if x.index in seen: continue
                    seen.add(x.index); comp.append(x)
                    stack.extend(e2 for e in x.edges for e2 in e.link_faces)
                comps.append(comp)
            drop = [f for k, c in enumerate(comps) if k % every for f in c]
            bmesh.ops.delete(bm, geom=drop, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(me); bm.free(); return me
    base = common.tri_count(lod0)
    for i, (ratio, every) in enumerate(((.5, 1), (.25, 2)), 1):
        name = '%s_LOD%d' % (asset.name, i)
        if name in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        body = bpy.data.objects.new(name, split(False)); asset.coll.objects.link(body); body.location = lod0.location
        stalks_me = split(True, every); body_tris = common.tri_count(body)
        make_lods.decimate_object(body, max(24, int(body_tris * ratio)))
        st = bpy.data.objects.new(name + '_stalks', stalks_me); asset.coll.objects.link(st); st.location = lod0.location
        with bpy.context.temp_override(active_object=body, selected_editable_objects=[body, st], selected_objects=[body, st]):
            bpy.ops.object.join()
        body.name = name; body.data.name = name
        log.append({'name': name, 'tris': common.tri_count(body), 'ratio_achieved': round(common.tri_count(body) / base, 4)})
    asset.refresh(); return log


lod_log = {}
for asset in common.find_assets():
    log = keep_stalk_lods(asset) if asset.name == 'SM_HayBale_01' else make_lods.make_lods(asset, [.5, .25], force=True)
    asset.refresh()
    lod_log[asset.name] = [{k: v for k, v in e.items() if k in ('name', 'tris', 'ratio_achieved')} for e in log if e.get('action', 'lod') == 'lod']
    ASSETS[asset.name]['triangles_per_lod'] = {o.name: common.tri_count(o) for o in asset.renders}
    ASSETS[asset.name]['expected_lods'] = len(asset.renders)
    ASSETS[asset.name]['fbx'] = 'Export/' + C.content_path(asset.cls_name, asset.name, PATH).lstrip('/') + '.fbx'
    ASSETS[asset.name]['lod_fbx'] = ['Export/LODs/%s_LOD%d.fbx' % (asset.name, k) for k in range(len(asset.renders))]
    ASSETS[asset.name]['ue_path'] = '/Game/Dink/Kits/Stonebrook440/' + asset.name
    for o in asset.renders:      # LODs share the asset location
        o.location = asset.renders[0].location

for img in bpy.data.images:
    if img.filepath:
        img.filepath = bpy.path.relpath(str(Path(bpy.path.abspath(img.filepath)).resolve()), start=str(ART))
blend = ART / 'KIT_Stonebrook440.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend), relative_remap=True, compress=True)

manifest_path = ART / 'art_manifest.json'
old = json.loads(manifest_path.read_text()) if (ONLY and manifest_path.exists()) else {'assets': {}, 'materials': {}}
old['assets'].update(ASSETS); old['materials'].update(MANIFEST_MATERIALS)
manifest = {'schema': 'dink-stonebrook-art/1', 'source': 'KIT_Stonebrook440.blend', 'seed': SEED,
            'units': 'metres; FBX UnitScaleFactor100 converts to Unreal cm',
            'screen': 440, 'assets': old['assets'], 'materials': old['materials'], 'lod_log': lod_log,
            'baked': not NO_BAKE,
            'notes': ['House front (door) faces Blender -Y = Unreal +Y (south), like SM_Cottage_Stonebrook_01.',
                      'Prop textures are unique Cycles bakes of procedural attribute-driven materials (SRC_S440_* kept with fake users for re-baking).',
                      'Building materials tile in world metres (Rubble 2.4 m, Thatch 2.0 m, WeatheredOak 1.0 m, LeadedGlass 0.48 m).',
                      'Unreal should import S440 normals at full strength (1.0); the shared Stonebrook sets keep their 0.35-0.38 bridge strength.']}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
import runpy; runpy.run_path(str(ART / 'cleanup_440.py'))
print('STONEBROOK440 BUILD OK', len(ASSETS), 'assets in', round(time.time() - t_start, 1), 's', flush=True)
