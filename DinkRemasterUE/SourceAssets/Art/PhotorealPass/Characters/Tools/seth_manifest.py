"""Write NPC/Seth/manifest.json (schema dink-photoreal-character/1) from his export report: the hero's own texture
sets (Characters/Dink/Textures, referenced where they are) except the recoloured outfit colour map.

    python3 -I seth_manifest.py        (after seth_build.py and export_char.py; see seth_build.py)"""
import json
from pathlib import Path

CHARS = Path(__file__).resolve().parent.parent
SETH = CHARS / 'NPC/Seth'
rep = json.loads((SETH / 'export_report.json').read_text())
hero = json.loads((CHARS / 'Dink/manifest.json').read_text())
materials = {}
for slot, row in hero['materials'].items():
    row = json.loads(json.dumps(row))
    row['textures'] = {role: '../../Dink/' + rel for role, rel in row['textures'].items()}
    materials[slot.replace('MI_Dink_PR_', 'MI_Seth_PR_')] = row
materials['MI_Seth_PR_Outfit']['textures']['BC'] = 'Textures/T_Seth_PR_Outfit_BC.png'
assert list(materials) == rep['materials'], (list(materials), rep['materials'])
manifest = {
    'schema': 'dink-photoreal-character/1', 'asset': rep['asset'], 'class': 'character_hero',
    'source_blend': 'NPC/Seth/SK_Seth_Photoreal.blend',
    'build': 'python3 -I Characters/Tools/npc_variants.py; blender -b -t 4 Characters/Dink/SK_Dink_Photoreal.blend --python Characters/Tools/seth_build.py; '
             'blender -b -t 4 Characters/NPC/Seth/SK_Seth_Photoreal.blend --python Characters/Tools/export_char.py -- <abs>/NPC/Seth/Export <abs>/NPC/Seth/export_report.json character_hero; '
             'python3 -I Characters/Tools/seth_manifest.py',
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
        'The face is the hero kit\'s sculpted face grown with the head, a young man\'s; the 1997 picture carries a photograph of a grown man\'s face. No likeness of a real person was modelled.',
        'The hair is the hero\'s groom with its cards turned up and back over a high forehead (seth_build.py sweep_hair), not a groom of its own: the forelock is a loose tuft from the side and the sides lack the 1997 picture\'s wave.',
        'No crossed-arms pose (picture 580) and no red flash of the face (its second frame): he stands and walks with the mannequin clips.',
        'Bare hands; the picture has brown gloves.',
    ],
}
(SETH / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
print('manifest', SETH / 'manifest.json')
