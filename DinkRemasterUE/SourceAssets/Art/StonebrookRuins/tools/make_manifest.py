"""Draft runtime manifests, emitter JSON and proposed ledger rows for the ruin kit (python3 only).

Reads (never writes) Content/Dink/Data/Art/stonebrook.json and stonebrook_exterior.json so the burnt
twins reuse the exact transforms of the intact elements.  Writes only inside StonebrookRuins/.
The 'vision' and 'replaces' element fields are PROPOSED schema additions: UDinkArtSubsystem does not
read them today (dink-art/1 has no vision gating), see README.md.
"""
import csv, hashlib, json, sys, datetime, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent; UE = KIT.parents[2]
sys.path.insert(0, str(HERE))
for cand in [UE.parent / 'tools/blender', UE.parent / 'Dink-Smallwood-Remaster/tools/blender']:
    if (cand / 'dinkasset').exists():
        sys.path.insert(0, str(cand)); break
import ruin_common as R
from dinkasset import conventions as C

spec = json.loads((KIT / 'ruins_manifest.json').read_text())
socks = json.loads((KIT / 'emitter_sockets_draft.json').read_text())
A = spec['assets']


def mesh_path(name):
    p = C.content_path(A[name]['class'], name, 'StonebrookRuins')
    return f'{p}.{name}'


def asset_rows(names):
    return [{'mesh': mesh_path(n), 'expected_size_cm': [d * 100 for d in A[n]['dimensions_m']],
             'expected_lods': 3, 'bounds_tolerance_cm': 1.0, 'lod_fbx': A[n].get('lod_fbx', [])} for n in names]


# ------------------------------------------------------------------ exterior SCR_439
ext = json.loads((UE / 'Content/Dink/Data/Art/stonebrook_exterior.json').read_text())
cottage = next(e for e in ext['elements'] if e['name'] == 'DinksCottage')
cw = cottage['world_cm']
elements = []
for vision, nm in [(1, 'SM_Cottage_Stonebrook_Burning_01'), (2, 'SM_Cottage_Stonebrook_Burnt_01')]:
    elements.append({'name': f'DinksCottage_V{vision}', 'mesh': mesh_path(nm), 'world_cm': cw, 'rotation_deg': cottage['rotation_deg'],
                     'scale': cottage['scale'], 'collision': True, 'vision': vision, 'replaces': 'DinksCottage'})


def cottage_world(x, y):
    """Cottage construction metres -> world cm (asset front +Y in UE = south)."""
    piv = A['SM_Cottage_Stonebrook_Burnt_01']['pivot_offset_from_construction_m']
    return [cw[0] + (x - piv[0]) * 100, cw[1] - (y - piv[1]) * 100]


extras = [  # (name, mesh, construction x, y, yaw, scale, z_cm, vision)
    ('FallenDoor', 'SM_Door_Cottage_Fallen_01', R.DOOR_X + 1.9, -6.2, -64, 1, 0.5, 2),
    ('AshPileWest', 'SM_Debris_AshPile_Large_01', -6.0, -5.6, -17, 1, 0.3, 2),
    ('AshPileDoor', 'SM_Debris_AshPile_Small_01', 1.0, -5.3, -63, 1, 0.3, 2),
    ('AshPileEast', 'SM_Debris_AshPile_Small_01', 9.9, 1.5, -137, 1.3, 0.3, 2),
]
for name, mesh, x, y, yaw, sc, z, vis in extras:
    w = cottage_world(x, y)
    elements.append({'name': name, 'mesh': mesh_path(mesh), 'world_cm': [w[0], w[1], z], 'rotation_deg': [0, yaw, 0],
                     'scale': [sc, sc, sc], 'collision': False, 'vision': vis})
# feathered ground-scorch scatter: placed by patch CENTRE.  kit_floor pivots are the min corner and FBX
# mirrors Y, so in Unreal the tile spans +X / -Y from its pivot; pivot = centre + R(yaw_ue) * (-S/2, +S/2).
scatter = list(R.GROUND_SCORCH) + [('SM_Decal_Scorch_Ground_2m_01', 2.0, R.DOOR_X + .2, -6.6, 30, 1.0, 'V1')]
for k, (mesh, size, cx, cy, yaw, sc, *tag) in enumerate(scatter):
    c = cottage_world(cx, cy); h = size * sc * 50; yaw_ue = -yaw; a = math.radians(yaw_ue)
    px = c[0] + (-h * math.cos(a) - h * math.sin(a)); py = c[1] + (-h * math.sin(a) + h * math.cos(a))
    elements.append({'name': f'ScorchGround{k:02d}', 'mesh': mesh_path(mesh), 'world_cm': [px, py, 0.5 + .05 * k],
                     'rotation_deg': [0, yaw_ue, 0], 'scale': [sc, sc, 1], 'collision': False,
                     'vision': 1 if tag else 2, 'centre_world_cm': c})

ext_emitters = []
for s in socks['SM_Cottage_Stonebrook_Burning_01']:
    lc = s['local_ue_cm']
    ext_emitters.append({**{k: s[k] for k in s if k not in ('local_m',)}, 'attach_to': 'DinksCottage_V1',
                         'world_cm': [cw[0] + lc[0], cw[1] + lc[1], lc[2]], 'vision': 1})
for s in socks['SM_Cottage_Stonebrook_Burnt_01']:
    lc = s['local_ue_cm']
    ext_emitters.append({**{k: s[k] for k in s if k not in ('local_m',)}, 'attach_to': 'DinksCottage_V2',
                         'world_cm': [cw[0] + lc[0], cw[1] + lc[1], lc[2]], 'vision': 2})
ext_lights = [{'socket': e['socket'], 'world_cm': [e['world_cm'][0], e['world_cm'][1], e['world_cm'][2] + 80],
               'lumens': 3000 if e['effect'] == 'flame_large' else 1200, 'kelvin': 1800, 'radius_cm': 900, 'vision': 1,
               'flicker': True} for e in ext_emitters if e['vision'] == 1 and e['effect'].startswith('flame')]
names_ext = ['SM_Cottage_Stonebrook_Burning_01', 'SM_Cottage_Stonebrook_Burnt_01', 'SM_Door_Cottage_Fallen_01',
             'SM_Debris_AshPile_Large_01', 'SM_Debris_AshPile_Small_01', 'SM_Decal_Scorch_Ground_3m_01',
             'SM_Decal_Scorch_Ground_2m_01', 'SM_Decal_Scorch_Ground_2m_02', 'SM_Decal_Scorch_Ground_1m5_01']
draft_ext = {'schema': 'dink-art/1', 'status': 'DRAFT - not published to Content/Dink/Data/Art; needs vision gating support',
             'screen': 439, 'assets': asset_rows(names_ext), 'source': 'SourceAssets/Art/StonebrookRuins/ruins_manifest.json',
             'vision_rules': {'1': 's1-h1-o:29 [(&story == 4)], s1-h1-o:84 [(&story == 3)]', '2': 's1-h1-o:77 [(&story > 4)]'},
             'hide_origins_by_vision': {'1': [r[0] for r in R.SCR439 if r[5] == 1], '2': [r[0] for r in R.SCR439 if r[5] == 2]},
             'elements': elements, 'emitters': ext_emitters, 'lights': ext_lights,
             'authored_collision_screens': [439],
             'notes': ['DinksCottage_V1/V2 replace element DinksCottage at the identical transform when &vision matches.',
                       'Collision of both variants is the intact cottage\'s six hulls (unchanged footprint; original v1/v2 hardness == v0).',
                       'Debris, decals and the fallen door are visual only (collision false) and keep the door walk-in corridor clear.',
                       'world_cm values derive from stonebrook_exterior.json DinksCottage and ruin_common cottage-frame positions.']}
(KIT / 'stonebrook_ruins_exterior_439.draft.json').write_text(json.dumps(draft_ext, indent=2) + '\n')

# ------------------------------------------------------------------ interior SCR_001
room = json.loads((UE / 'Content/Dink/Data/Art/stonebrook.json').read_text())
twins = {'SM_Wall_Limewash_2m_01': 'SM_Wall_Limewash_Burnt_2m_01', 'SM_Window_Limewash_2m_01': 'SM_Window_Limewash_Burnt_2m_01',
         'SM_Doorway_Limewash_4m_01': 'SM_Doorway_Limewash_Burnt_4m_01', 'SM_Ceiling_Oak_2m_01': 'SM_Ceiling_Oak_Burnt_2m_01',
         'SM_Floor_Oak_2m_01': 'SM_Floor_Oak_Burnt_2m_01'}
int_elements = []
holes_at = {(3, 2), (5, 4)}     # ceiling modules burnt through (under the two big roof openings' interior side)
for e in room['elements']:
    base = e['mesh'].rsplit('/', 1)[-1].split('.')[0]
    if base not in twins:
        continue
    nm = twins[base]
    if base == 'SM_Floor_Oak_2m_01':
        i, j = (int(t) for t in e['name'].split('_')[1:3])
        nm = f'SM_Floor_Oak_Burnt_2m_0{(i * 3 + j * 7) % 4 + 1}'
    if base == 'SM_Ceiling_Oak_2m_01':
        i, j = (int(t) for t in e['name'].split('_')[1:3])
        if (i, j) in holes_at:
            nm = 'SM_Ceiling_Oak_BurntHole_2m_01'
    int_elements.append({**e, 'name': e['name'] + '_Burnt', 'mesh': mesh_path(nm), 'vision': 2, 'replaces': e['name']})
int_emitters = []
for fx in R.interior_effects():
    px, py = fx['placement_pixel']
    w = R.world_cm(1, px, py)
    rec = {'origin': fx['id'], 'source_pixel': fx['source_pixel'], 'placement_pixel': fx['placement_pixel'],
           'surface': fx['surface'], 'world_cm': [w[0], w[1], fx['height_cm']], 'height_cm': fx['height_cm'],
           'vision': fx['vision'], 'original_sequence': fx['seq'], 'original_frame': fx['frame'],
           'original_sequence_path': R.SEQ_NAMES[fx['seq']]}
    if fx['vision'] == 1:
        if fx['seq'] == 355:
            rec.update({'effect': None, 'note': "mother's death sprite: reproduced as the SM_Mother_Remains_Fire_01 prop + blood decal (elements MotherBody/MotherBlood), not an emitter"})
        else:
            rec['effect'] = R.EFFECT_KIND[fx['seq']]
            rec['scale_hint'] = round(R.FRAMES[(fx['seq'], fx['frame'])][0] / 80.0, 2)
        int_emitters.append(rec)
    else:
        # vision-2 burn holes become decals
        floor = fx['surface'] == 'floor'
        s = {23: .7, 42: 1.0}[R.FRAMES[(fx['seq'], fx['frame'])][0]]
        if floor:
            pos = [w[0] - 75 * s, w[1] + 75 * s, .3]; yaw = 0; mesh = 'SM_Decal_Scorch_Floor_01'
        else:
            yaw = {'wall_north': 0, 'wall_south': 180, 'wall_west': -90}[fx['surface']]
            off = {'wall_north': (-75 * s, 0), 'wall_south': (75 * s, 0), 'wall_west': (0, -75 * s)}[fx['surface']]
            pos = [w[0] + off[0], w[1] + off[1], max(0, fx['height_cm'] - 64 * s)]
            mesh = 'SM_Decal_Scorch_Wall_01'
        int_elements.append({'name': f"Scorch_{fx['id']}", 'mesh': mesh_path(mesh), 'world_cm': pos, 'rotation_deg': [0, yaw, 0],
                             'scale': [s, s, s if not floor else 1], 'collision': False, 'vision': 2, 'origin': fx['id'],
                             'note': 'replaces the original seq-158 burn-hole sprite; wall decals sit 3 mm in front of the inner wall face (verify offset against the wall thickness in editor)'})
mp = next(f for f in R.interior_effects() if f['id'] == 'S001_P34')
mw = R.world_cm(1, *mp['visual_pixel'])
int_elements.append({'name': 'MotherBody', 'mesh': mesh_path('SM_Mother_Remains_Fire_01'), 'world_cm': [mw[0], mw[1], 0.4],
                     'rotation_deg': [0, 35, 0], 'scale': [1, 1, 1], 'collision': False, 'vision': 1, 'origin': 'S001_P34',
                     'note': "Replaces the 1997 death sprite (seq 355 people/mom/death-): the mother lies dead face-down in "
                             "the burning room. Static prop; the live mother actor S001_P26 is already deactivated by s1-h1-m when &story > 2."})
bh = 100.0; ba = math.radians(35)
int_elements.append({'name': 'MotherBlood', 'mesh': mesh_path('SM_Decal_Blood_Floor_01'),
                     'world_cm': [mw[0] - bh * math.cos(ba) - bh * math.sin(ba), mw[1] - bh * math.sin(ba) + bh * math.cos(ba), 0.3],
                     'rotation_deg': [0, 35, 0], 'scale': [1, 1, 1], 'collision': False, 'vision': 1, 'origin': 'S001_P34'})
int_lights = [{'origin': r['origin'], 'world_cm': [r['world_cm'][0], r['world_cm'][1], r['height_cm'] + 90], 'lumens': 1500,
               'kelvin': 1800, 'radius_cm': 650, 'vision': 1, 'flicker': True}
              for r in int_emitters if r.get('effect') in ('flame_large', 'fire_column')]
names_int = sorted({e['mesh'].split('.')[-1] for e in int_elements} | {'SM_Debris_AshPile_Small_01'})
A['SM_Mother_Remains_Fire_01'].setdefault('lod_fbx', [])
draft_int = {'schema': 'dink-art/1', 'status': 'DRAFT - not published to Content/Dink/Data/Art; needs vision gating support',
             'screen': 1, 'assets': asset_rows(names_int), 'source': 'SourceAssets/Art/StonebrookRuins/ruins_manifest.json',
             'vision_rules': {'1': 's1-h1-s:6 [(&story == 3)]', '2': 's1-h1-s:30/41 [(&story > 3) && (&letter == 1)] ...'},
             'elements': int_elements, 'emitters': int_emitters, 'lights': int_lights,
             'notes': ['Vision 2 swaps every kit module for its burnt twin at the identical transform (same pivots and hulls).',
                       'Vision 1 keeps the intact modules and adds the emitters (fire still spreading) plus the mother\'s body in her blood (S001_P34), reproduced faithfully per owner decision; furniture/props are owned by the interior props work and are not replaced here.',
                       'Interior positions use room source pixels (0.04375 m/px) and ImportData/screens.json corners.']}
(KIT / 'stonebrook_ruins_interior_001.draft.json').write_text(json.dumps(draft_int, indent=2) + '\n')

# ------------------------------------------------------------------ emitter socket JSON (single deliverable)
(KIT / 'fire_emitters.json').write_text(json.dumps({
    'schema': 'dink-fire-emitters/1', 'units': 'local_ue_cm: centimetres in the static mesh\'s Unreal asset space (+Y = cottage front); world_cm: level space',
    'effect_kinds': {'flame_large': 'tall licking flame sheet, ~2 m', 'flame_medium': 'flame ~1.2 m', 'flame_small': 'flame ~0.7 m',
                     'smoulder_damage': 'charring patch: embers + dense smoke', 'smoke_vent': 'smoke column out of a roof opening',
                     'smoke_column': 'chimney smoke', 'fire_column': 'tall burst/column of flame (interior)',
                     'burst_oneshot': 'one-shot flare-up', 'smoulder_wisp': 'faint smoke wisps (optional, off by default)'},
    'exterior_439': {'mesh_sockets': socks, 'emitters': ext_emitters},
    'interior_001': {'emitters': int_emitters},
    'mapping': 'Exterior: original sprite visual points mapped onto the 3D roof/walls by ruin_common.sprite_to_cottage_roofaware '
               '(inverse-bilinear on the sprite roof quad; oblique fit for walls). Interior: room source pixels; wall-painted fires lifted to the wall face.',
}, indent=2) + '\n')

# ------------------------------------------------------------------ proposed ledger rows
header = 'asset_path,derived_path,kind,replaces,source,tool_model,prompt,parameters,generation_id,flow_id,generated_on,credits,licence,sha256,duration_s,status,notes'.split(',')
today = datetime.date.today().isoformat()
rows = []
common = {'source': 'Original project-authored procedural geometry and texture synthesis',
          'tool_model': 'Blender 5.2.2 LTS / Python numpy+Pillow; no generative model or external input assets',
          'prompt': 'Fire-damaged Stonebrook cottage: alligatored char, calcined fieldstone, sooted limewash, ash and ember debris; realistic human scale',
          'parameters': f'seed={R.SEED}; metres; FBX_SCALE_ALL; apply_unit_scale; Z-up; front=-Y; BC/N/ORM(+E/alpha); 3 LODs',
          'generation_id': 'stonebrookruins-kit-v1', 'flow_id': '', 'generated_on': today, 'credits': '0',
          'licence': 'Original project asset; no third-party source material', 'duration_s': '', 'status': 'candidate'}
rep = {'SCR_439': 'House exterior SCR_439 vision 1/2 sprites (seq 427/154-158 fire and damage cards)',
       'SCR_001': 'House interior SCR_001 vision 1/2 sprites (seq 427/70/155-158/161 fire, burst and hole cards)'}
files = [KIT / 'KIT_StonebrookRuins.blend', KIT / 'Working/MotherRemains_posed.blend'] + sorted((KIT / 'Textures').glob('T_*.png')) + sorted(KIT.glob('tools/*.py'))
for f in files:
    rel = str(f.relative_to(UE))
    kind = 'mesh' if f.suffix == '.blend' else ('texture' if f.suffix == '.png' else 'source_script')
    derived = 'Content/Dink/Kits/StonebrookRuins; Content/Dink/Textures/StonebrookRuins' if f.suffix == '.blend' else \
        (f'Content/Dink/Textures/StonebrookRuins/{f.stem}.uasset' if f.suffix == '.png' else '')
    extra = {}
    if 'Mother' in f.name:
        extra = {'source': 'Derived from SourceAssets/Art/Characters/SK_Mother.blend and T_Mother_Atlas_* (CC0 MakeHuman anatomy/skin/hair + original project wardrobe)',
                 'licence': 'CC0 MakeHuman base (see Characters/Provenance/MakeHuman_CC0.txt) + original project wardrobe and procedural smoke/blood pass',
                 'replaces': "SCR_001 vision 1 S001_P34 (seq 355 people/mom/death-): the mother's body in the burning house"}
    rows.append({**common, 'asset_path': rel, 'derived_path': derived, 'kind': kind,
                 'replaces': extra.get('replaces') or (rep['SCR_001'] if ('RuinInt' in f.name) else rep['SCR_439'] + '; ' + rep['SCR_001']),
                 'sha256': hashlib.sha256(f.read_bytes()).hexdigest(),
                 **({k: v for k, v in extra.items() if k != 'replaces'}),
                 'notes': 'Proposed row (not merged). Rebuild: StonebrookRuins/tools/run_all.sh; human art approval pending; vision gating not yet supported at runtime.'})
with open(KIT / 'ledger_rows_proposed.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=header); w.writeheader(); w.writerows(rows)
print('manifests written;', len(int_elements), 'interior elements,', len(elements), 'exterior elements,',
      len(ext_emitters) + len(int_emitters), 'emitters,', len(rows), 'ledger rows')
