"""Per-creature manifest entries (entries/<Name>.json), facts read from the build reports, review verdicts written by hand after the last review round.
usage: python3 -I write_entries.py ; then python3 -I write_manifest.py"""
import json
from pathlib import Path
OUT = Path(__file__).resolve().parents[1]; (OUT / 'entries').mkdir(exist_ok=True)

def build(folder, name):
    p = OUT / folder / name
    return json.loads(p.read_text()) if p.exists() else {}
def files(folder, sub, pat):
    return sorted(str(p.relative_to(OUT / folder)) for p in (OUT / folder / sub).glob(pat)) if (OUT / folder / sub).exists() else []
def tex(folder, names): return [{'file': 'Textures/' + n} for n in names if (OUT / folder / 'Textures' / n).exists()]

COMMON_IMPORT = ('One FBX per LOD (Export/<Asset>_LOD0..2.fbx) plus one armature-only FBX per clip, written with the same recipe as the existing creature exporters '
                 '(metres source, temporary x100 export scene, FBX_SCALE_ALL, Armature wrapper node, no leaf bones). Import each LOD explicitly, as Scripts/import_creature_art.sh does. '
                 'Normal maps are OpenGL (green up): keep the importer green-channel flip used by the existing creature manifests. ORM = AO/roughness/metallic, linear. '
                 'SSS map (linear, single channel) is a subsurface weight mask for the creature material; without a subsurface profile the asset still reads, only flatter.')

E = {}
b = build('Pillbug', 'pillbug_build.json'); c = build('Pillbug', 'pillbug_corpse_build.json')
E['Pillbug'] = {
    'asset': 'SK_Pillbug', 'folder': 'Pillbug', 'class': 'creature', 'supersedes': 'SourceAssets/Art/Creatures/Pillbug (SK_Pillbug, stylised)', 'source_blend': 'Pillbug/SK_Pillbug.blend', 'build_script': 'Tools/pillbug.py',
    'dimensions_m': b.get('dimensions_m'), 'lods': b.get('lods'), 'uv': b.get('uv'),
    'families': ['pillbug', '131 foes/pill/f1-w1-', '133 foes/pill/f1-w3-', '137/139 (same actor facings)'],
    'slots': ['MI_Pillbug_Carapace', 'MI_Pillbug_Ochre', 'MI_Pillbug_Joints', 'MI_Pillbug_Eyes'],
    'slot_note': 'Same four slot names and the same atlas file names (T_Pillbug_Atlas_BC/N/ORM) as the asset it replaces, so the existing material instances rebind. All four slots read one atlas; MI_Pillbug_Eyes only needs lower roughness headroom. New: T_Pillbug_Atlas_SSS (membranes and leg translucency).',
    'textures': tex('Pillbug', ['T_Pillbug_Atlas_BC.png', 'T_Pillbug_Atlas_N.png', 'T_Pillbug_Atlas_ORM.png', 'T_Pillbug_Atlas_SSS.png']),
    'exports': files('Pillbug', 'Export', '*.fbx'),
    'rig_compatibility': 'Existing 43-bone armature and its three actions (Pillbug_Idle, Pillbug_Walk, Pillbug_Run, 40 fps) are carried over untouched from Creatures/Pillbug/SK_Pillbug.blend; rest matrices identical, so the imported skeleton, blendspace and clips stay valid. Rigid one-bone weights per cuticle part (the earlier convention); the ventral hull follows pelvis/head/tail. Verified by rendering Idle, Walk f9 and Run f5.',
    'importer_notes': COMMON_IMPORT + ' Bounds grew slightly (antennae and uropods): re-measure expected_size_cm and body_boxes on import.',
    'third_party': [], 'review_only_third_party': ['polyhaven/dirt (ground plane of the review renders, not shipped)'],
    'gore': {'asset': 'SM_Pillbug_Corpse', 'class': 'prop_large', 'families': ['pillbug_corpse', '141 foes/pill/f1-x1-', '143 foes/pill/f1-x3-'], 'source_blend': 'Pillbug/SM_Pillbug_Corpse.blend', 'lods': c.get('lods'), 'dimensions_m': c.get('dimensions_m'),
             'slots': ['MI_Pillbug_Carapace', 'MI_Pillbug_Ochre', 'MI_Pillbug_Joints', 'MI_Pillbug_Eyes', 'MI_Pillbug_Gore'], 'textures': tex('Pillbug', ['T_Pillbug_Gore_BC.png', 'T_Pillbug_Gore_N.png', 'T_Pillbug_Gore_ORM.png', 'T_Pillbug_Gore_SSS.png']),
             'note': 'Burst carcass for the death frames: the same mesh posed through the rig (collapsed, two tergites torn off and flipped, legs folded), frozen to a static mesh, in a blood pool with clots and spilled viscera. Red blood kept as in the sprite. No UCX collision authored (decal-like prop). The live death today hides the actor at once; spawning this prop on death is a runtime change for the coordinator.'},
}
b = build('Pig', 'pig_build.json')
E['Pig'] = {
    'asset': 'SK_Pig', 'folder': 'Pig', 'class': 'creature_quadruped', 'supersedes': 'SourceAssets/Art/Creatures/Pig (SK_Pig, stylised)', 'source_blend': 'Pig/SK_Pig.blend (contains the high-poly bake source PigHigh, hidden)', 'build_script': 'Tools/pig.py, Tools/gen_bristle_atlas.py',
    'dimensions_m': b.get('dimensions_m'), 'lods': b.get('lods'), 'uv': b.get('uv'), 'high_triangles': b.get('high_triangles'),
    'families': ['pig', '41 animals/pig/pg-w1-', '43 animals/pig/pg-w3-', '47 animals/pig/pg-w7-', '49 animals/pig/pg-w9-'],
    'slots': ['MI_Pig_Skin', 'MI_Pig_Muzzle', 'MI_Pig_HornBristle', 'MI_Pig_Eye'],
    'slot_note': 'Same four slot names as the asset it replaces. MI_Pig_Skin, MI_Pig_Muzzle and MI_Pig_Eye read T_Pig_Atlas_* (hooves and dewclaws now sit in MI_Pig_Skin). MI_Pig_HornBristle now carries ONLY the bristle cards and reads T_Pig_BristleCards_BC (alpha) / _N / _ORM: make it a masked or dithered two-sided material that casts NO dynamic shadow (the review renders switch card shadows off; with shadows on, every card prints a dark tick on the skin). The cards carry custom vertex normals copied from the skin: import normals, do not recompute them.',
    'textures': tex('Pig', ['T_Pig_Atlas_BC.png', 'T_Pig_Atlas_N.png', 'T_Pig_Atlas_ORM.png', 'T_Pig_Atlas_SSS.png', 'T_Pig_BristleCards_BC.png', 'T_Pig_BristleCards_N.png', 'T_Pig_BristleCards_ORM.png']),
    'exports': files('Pig', 'Export', '*.fbx'),
    'rig_compatibility': 'Existing 26-bone armature and its four actions (Pig_Idle, Pig_Walk, Pig_Run, Pig_Feed, 30 fps) carried over untouched; rest matrices identical; no bone added or renamed. Mesh rebuilt on 12 Nov 2026 (v2: deep barrel, sagging belly, stout legs, wedge head) and skinned with bone heat (max 4 influences); hooves, eyes rigid; ears and tail weighted to their own bones; bristle cards take the weights of the skin under them. Verified by rendering Walk f6, Run f4 and Feed f7.',
    'importer_notes': COMMON_IMPORT + ' Body is about 0.77 m wide, 1.79 m long, 1.0 m to the ear tips: re-measure body_boxes on import, they feed the fitted trunk/head boxes. Validator: UV_OVERLAP is reported because the bristle cards (own texture, own slot) share UV0 space with the atlas; the atlas islands themselves do not overlap (0.03 %).',
    'third_party': ['polyhaven/brown_mud_02 (diffuse: wet mud layer, box-projected and tinted inside the baked atlas)', 'polyhaven/mud_cracked_dry_riverbed_002 (diffuse: dry caked mud layer, same use)'], 'review_only_third_party': ['polyhaven/dirt (review ground)'],
}
b = build('Duck', 'duck_build.json')
E['Duck'] = {
    'asset': 'SK_Duck', 'folder': 'Duck', 'class': 'creature', 'supersedes': 'SourceAssets/Art/Creatures/Duck (untracked stylised candidate: SK_Duck, SK_Duck_Headless, SM_Duck_Head)', 'source_blend': 'Duck/SK_Duck.blend (three collections plus the hidden high-poly DuckHigh)', 'build_script': 'Tools/duck.py, Tools/gen_feather_atlas2.py',
    'dimensions_m': b.get('dimensions_m'), 'lods': b.get('lods'), 'uv': b.get('uv'), 'high_triangles': b.get('high_triangles'),
    'families': ['duck', '21/23/24/26/27/29 animals/duck/dkNw-', 'duck_head', 'duck_corpse', '121/127 animals/duck/death/dkhNx-'],
    'species_note': 'All-white domestic (Pekin type) duck with orange bill and feet, as every frame of the sprite shows. The black patches on the earlier contact sheet were a shading defect (inverted normals baked from back-facing feather vanes, plus vertices left behind by dropped skin weights), not a colour choice; both causes are fixed in duck.py.',
    'slots': ['MI_Duck_Feather', 'MI_Duck_Bill', 'MI_Duck_Feet', 'MI_Duck_Eye', 'MI_Duck_FeatherCards'],
    'slot_note': 'First four keep the candidate names and share T_Duck_Atlas_*. MI_Duck_FeatherCards (masked or dithered, two-sided, NO dynamic shadow; multiply base colour by the mesh vertex colour, which carries a per-feather tint: cream staining, belly soil, slight value jitter) uses T_Duck_FeatherCards_BC (alpha) / _N / _ORM, an 8-cell feather atlas, for about 2,150 cards: contour and down feathers over body and neck, wing coverts, scapulars, secondaries, primaries, tail coverts and rectrices. Cards carry custom vertex normals blended toward the skin normal: import normals, do not recompute. Gore variants: SK_Duck_Headless and SM_Duck_Head swap MI_Duck_Feather for MI_Duck_Feather_Bloody (T_Duck_Atlas_Bloody_BC/ORM, same N), use MI_Duck_FeatherCards_Bloody (T_Duck_FeatherCards_Bloody_*) on the cards round the wound, and add MI_Duck_Gore (T_Duck_Gore_*, two-sided: wound section, torn skin collar, vertebra stub, trachea, oesophagus, vessels).',
    'textures': tex('Duck', ['T_Duck_Atlas_BC.png', 'T_Duck_Atlas_N.png', 'T_Duck_Atlas_ORM.png', 'T_Duck_Atlas_SSS.png', 'T_Duck_Atlas_Bloody_BC.png', 'T_Duck_Atlas_Bloody_ORM.png', 'T_Duck_FeatherCards_BC.png', 'T_Duck_FeatherCards_N.png', 'T_Duck_FeatherCards_ORM.png',
                             'T_Duck_FeatherCards_Bloody_BC.png', 'T_Duck_FeatherCards_Bloody_N.png', 'T_Duck_FeatherCards_Bloody_ORM.png', 'T_Duck_Gore_BC.png', 'T_Duck_Gore_N.png', 'T_Duck_Gore_ORM.png']),
    'exports': files('Duck', 'Export', '*.fbx'),
    'rig_compatibility': 'Existing 23-bone armature and all nine actions (Idle, Walk, Run, Peck, Quack, Hit, Death, HeadlessRun, HeadlessDeath, 30 fps) carried over untouched; no bone added or renamed. Mesh rebuilt on 12 Nov 2026 (v2). Body skinned with bone heat; the wing, shin, foot and jaw influences on the plumage are handed to spine_01, pelvis and head; bill, legs, feet, eyes rigid; wing shells and wing cards blend wing -> wingtip; tail cards on tail_01/02; stump parts on neck_02. SK_Duck_Headless shares the armature (import against the SK_Duck skeleton). Verified by rendering Walk f4, Peck f18, Quack f8 and HeadlessRun f4.',
    'importer_notes': COMMON_IMPORT + ' SM_Duck_Head is a static prop (three LOD FBXs, no UCX hull authored; a simple sphere collision is enough). The earlier candidate was never imported, so this is a first import. Validator reports UV_OVERLAP because the feather cards (own atlas, own slot) share UV0 space with the body atlas; the body islands do not overlap.',
    'third_party': [], 'review_only_third_party': ['polyhaven/leafy_grass (review ground)'],
    'gore': {'assets': ['SK_Duck_Headless', 'SM_Duck_Head'], 'note': 'Decapitation kept. The neck is bisected and capped with the cross-section texture; on top of the cap sits modelled stump anatomy: a ragged collar of torn skin flaps, the cervical vertebra stub with transverse processes, a ringed open trachea pulled forward, the collapsed oesophagus and hanging clotted vessels (body side). Plumage round the cut is blood-soaked in the baked atlas (texture-space composite from the position map, runs down the breast) and the feather cards near the wound switch to a blood-matted card atlas. The severed head carries the matching short stump.'},
}
b = build('Slime', 'slime_build.json')
E['Slime'] = {
    'asset': 'SK_Slime', 'folder': 'Slime', 'class': 'creature', 'supersedes': None, 'source_blend': 'Slime/SK_Slime.blend (with the hidden high-poly SlimeHigh; collection SM_Slime_Trail holds the trail decal mesh)', 'build_script': 'Tools/slime.py',
    'dimensions_m': b.get('dimensions_m'), 'lods': b.get('lods'), 'uv': b.get('uv'),
    'families': ['slime_blue', 'slime_green', 'slime_red', '651/653 foes/puddle/blue/walk', '671/673 foes/puddle/green/walk', '691/693 foes/puddle/red/walk'],
    'slots': ['MI_Slime', 'MI_Slime_Core', 'MI_Slime_Wet'],
    'slot_note': 'Three slots on SK_Slime: MI_Slime (gel shell), MI_Slime_Core (interior), MI_Slime_Wet (meniscus film). Colour variants Blue / Green / Red are material instances that swap T_Slime_<Var>_BC, T_Slime_Core_<Var>_BC and T_Slime_Trail_<Var>_BC; N / ORM / SSS are shared (T_Slime_Blue_*, T_Slime_Core_Blue_*). See engine_material for the integrator.',
    'engine_material': {
        'status': 'NOT built or tested in Unreal by this stream (the brief forbids starting the editor). What follows is the intended setup; the Cycles review renders use a refracting stand-in, so the engine look will differ.',
        'MI_Slime (shell)': ['Blend mode Translucent, lighting mode Surface Translucency Volume (or Surface ForwardShading if the per-pixel cost is acceptable: it gives the sharp wet highlight). Thin Translucent shading model is the alternative when the project uses it: base colour as transmittance tint.',
                             'Refraction OFF (no refraction input, no pixel-offset refraction): the interior is real geometry and refraction would smear it and cost a scene-colour copy.',
                             'Opacity = alpha of T_Slime_<Var>_BC (clear gel 0.04-0.4, pigment spots, grit and foot soil near 1). Multiply by a scalar (default 1) so the integrator can tune it; add a fresnel term (about +0.35 at grazing angles) so the rim reads thicker than the centre.',
                             'Base colour = BC rgb. Subsurface / transmittance tint per variant (linear): Blue (0.17, 0.28, 0.72), Green (0.55, 0.54, 0.10), Red (0.62, 0.22, 0.15) - slime.py TINT. T_Slime_Blue_SSS is the subsurface weight mask.',
                             'Roughness from ORM G (0.10-0.35 on gel, about 0.85 on grit). Specular 0.5-0.8. Wet coat: with Substrate use a thin clear coat slab of roughness 0.05; otherwise clamp roughness low, the highlight is the coat.',
                             'Normal T_Slime_Blue_N (OpenGL: flip green on import). Two-sided off. Cast shadow ON with a masked shadow proxy or as an opaque caster: a translucent mesh casts none by default (bCastVolumetricTranslucentShadow, or simply let MI_Slime_Core cast the shadow).'],
        'MI_Slime_Core (interior)': ['Opaque default-lit, T_Slime_Core_<Var>_BC + T_Slime_Core_Blue_N / _ORM (1024). It is a separate element inside the same skeletal mesh (murky core, bubbles, grit, ribs, bird skull), skinned to the same bones. Casts the body shadow.'],
        'MI_Slime_Wet (meniscus)': ['Translucent, unlit-cheap or Surface Translucency Volume, opacity = alpha of T_Slime_Wet_BC, roughness about 0.05, dark base colour. No shadow. Alternative: masked + DBuffer-style darkening is not possible on a skeletal mesh, so keep it translucent.'],
        'MI_Slime_Trail (SM_Slime_Trail)': ['Either a translucent mesh decal (blend Translucent, decal response off, depth bias) or copy T_Slime_Trail_<Var>_BC / _N / _ORM into a deferred decal material (DBuffer colour + normal + roughness) projected down 10 cm. Spawn behind the moving slime every about 1.2 m, fade opacity to 0 over 20-30 s.'],
        'sort_order': 'Opaque core renders first (opaque pass). Translucent sort priority: meniscus -1, trail -2 (both below the shell), shell 0. All three shell-family elements are in one skeletal mesh, so set the priority on the component only if the shell is split out; otherwise rely on the element order in the FBX (shell element 0, core 1, meniscus 2) and on the core being opaque. If the shell sorts wrongly against the meniscus, enable Render After DOF off / translucency sort by distance on the component.',
        'fallback': 'If translucency is not acceptable: make MI_Slime opaque subsurface with the same maps (ignore BC alpha). The slime then looks as in the earlier delivery (wet, spotted, solid) and the core is hidden.'},
    'textures': tex('Slime', ['T_Slime_Blue_BC.png', 'T_Slime_Green_BC.png', 'T_Slime_Red_BC.png', 'T_Slime_Blue_N.png', 'T_Slime_Blue_ORM.png', 'T_Slime_Blue_SSS.png', 'T_Slime_Core_Blue_BC.png', 'T_Slime_Core_Green_BC.png', 'T_Slime_Core_Red_BC.png', 'T_Slime_Core_Blue_N.png', 'T_Slime_Core_Blue_ORM.png',
                              'T_Slime_Wet_BC.png', 'T_Slime_Wet_N.png', 'T_Slime_Wet_ORM.png', 'T_Slime_Trail_Blue_BC.png', 'T_Slime_Trail_Blue_N.png', 'T_Slime_Trail_Blue_ORM.png', 'T_Slime_Trail_Green_BC.png', 'T_Slime_Trail_Green_N.png', 'T_Slime_Trail_Green_ORM.png', 'T_Slime_Trail_Red_BC.png', 'T_Slime_Trail_Red_N.png', 'T_Slime_Trail_Red_ORM.png']),
    'exports': files('Slime', 'Export', '*.fbx'),
    'rig_compatibility': 'NEW rig (made in this pass, no earlier asset existed): 10 bones (root, pelvis, body_01..04, head, hump_02..04), identity root, all bones world-aligned; unchanged from the first delivery of this pass, so its four clips still apply. Interior and meniscus are skinned to the same bones by position. Clips are translation/rotation only (no bone scale): ' + json.dumps({k: {'frames': v['frames'], 'loop': v['loop']} for k, v in b.get('actions', {}).items()}) + ' at 30 fps, in place, nominal walk speed 30 cm/s (a guess: fit playback to the en-slim* brain speed).',
    'importer_notes': COMMON_IMPORT + ' New skeleton and new creatures.json asset row needed; no locomotion blendspace exists yet. Death sprites 661/663/681/683/701/703 (splatter) are not covered by a separate prop: the Death clip flattens the body into a puddle and holds. The meniscus film is part of the skeletal mesh: it is the lowest 3 cm band of the shell pushed outward 2-3 cm and laid 0.6 mm above z=0, so it follows every bay of the foot; on uneven ground it will still float or clip.',
    'third_party': [], 'review_only_third_party': ['polyhaven/forrest_ground_03 (review ground)'],
}
V = json.loads((OUT / 'Tools/verdicts.json').read_text()) if (OUT / 'Tools/verdicts.json').exists() else {}
for k, e in E.items():
    e.update(V.get(k, {'status': 'not reviewed', 'known_weaknesses': ['no verdict recorded']}))
    if not (OUT / e['folder']).exists(): continue
    (OUT / 'entries' / (k + '.json')).write_text(json.dumps(e, indent=1) + '\n')
# the validator reports write absolute paths; the repo is public, so they are rewritten relative to the repo root
REPO = OUT.parents[4]
for q in OUT.glob('*/*_validation.json'):
    t = q.read_text(); t2 = t.replace(str(REPO) + '/', '').replace(str(REPO), '.')
    if t2 != t: q.write_text(t2)
print('entries:', [k for k in E if (OUT / 'entries' / (k + '.json')).exists()])
