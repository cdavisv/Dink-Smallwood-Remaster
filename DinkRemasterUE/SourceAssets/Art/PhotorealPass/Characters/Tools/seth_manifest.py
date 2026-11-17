"""Write NPC/Seth/manifest.json (schema dink-photoreal-character/1) from his export report: his own skin, eye, hair
and outfit texture sets (NPC/Seth/Textures); the gear set (belt, boots, pack, bracers) is the hero's, referenced where
it is (Characters/Dink/Textures).

    python3 -I seth_manifest.py        (after seth_build.py and export_char.py; see seth_build.py)"""
import json
from pathlib import Path

CHARS = Path(__file__).resolve().parent.parent
SETH = CHARS / 'NPC/Seth'
rep = json.loads((SETH / 'export_report.json').read_text())
hero = json.loads((CHARS / 'Dink/manifest.json').read_text())
materials = {}
OWN = {'Skin': ('BC', 'N', 'ORM', 'SSS'), 'Eyes': ('BC', 'N', 'ORM'), 'Hair': ('BC', 'N', 'ORM', 'FLOW', 'MSK'), 'Outfit': ('BC', 'N', 'ORM')}
for slot, row in hero['materials'].items():
    row = json.loads(json.dumps(row))
    part = slot.rsplit('_', 1)[1]
    if part in OWN:
        row['textures'] = {role: f'Textures/T_Seth_PR_{part}_{role}.png' for role in row['textures']}
        assert set(row['textures']) == set(OWN[part]), (slot, row['textures'])
        assert all((SETH / rel).is_file() for rel in row['textures'].values()), slot
    else:
        row['textures'] = {role: '../../Dink/' + rel for role, rel in row['textures'].items()}
    materials[slot.replace('MI_Dink_PR_', 'MI_Seth_PR_')] = row
assert list(materials) == rep['materials'], (list(materials), rep['materials'])
manifest = {
    'schema': 'dink-photoreal-character/1', 'asset': rep['asset'], 'class': 'character_hero',
    'source_blend': 'NPC/Seth/SK_Seth_Photoreal.blend',
    'build': 'the stages listed at the top of Characters/Tools/seth_build.py, then python3 -I Characters/Tools/seth_manifest.py',
    'fbx': [f'Export/{rep["asset"]}_LOD{i}.fbx' for i in range(4)],
    'dimensions_m': rep['dimensions_m'], 'bone_count': rep['bone_count'], 'root_bone': 'root',
    'skeleton': hero['skeleton'], 'lods': rep['lods'], 'lod0_triangles': rep['lods'][0]['triangles'],
    'material_slots': rep['materials'], 'materials': materials,
    # the importer takes these from the hero's content folder instead of importing them again
    'shared_textures': {'../../Dink/Textures': '/Game/Dink/Photoreal/Characters/Dink/Textures'},
    # 1997: the standing picture `pose` is 160 px against the hero's 97 (1.65 times as tall, 3.0 m beside the hero's 1.82 m)
    'placement_scale': 1.45, 'animation_set': 'NpcM', 'families': [],
    'what': 'Seth, the last enemy (s7-boss): pictures graphics/effects/magic/pose and seth1w-9w, which s7-mil loads as 580-589',
    'validation': rep['validation'], 'validator_findings': rep['findings'],
    'known_weaknesses': [
        'The face is sculpted with the kit\'s face operations (cfg/head.json), a hard older man of no particular likeness; the 1997 picture carries a photograph of a real face, which was not copied.',
        'The gloves are painted on the hand skin (cfg/skin.json `glove`): no seams, no cuff of their own; the hero\'s bracers close them at the wrist.',
        'The mail of the sleeves is a texture (colour, normal, roughness) on the hero\'s shirt, not modelled rings.',
        'No red flash of the face while he casts (second frame of the 1997 pose).',
    ],
}
(SETH / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
print('manifest', SETH / 'manifest.json')
