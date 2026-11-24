"""Write NPC/<Name>/manifest.json (schema dink-photoreal-character/1) for a townsman of townsfolk.py from his export
report: his own skin, eye, hair and gear texture sets and outfit colour map (NPC/<Name>/Textures); the outfit's normal
and roughness maps are the hero's, referenced where they are (Characters/Dink/Textures).

    python3 -I townsfolk_manifest.py <Name>        (after export_char.py; the stages are listed in run_townsfolk.sh)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from townsfolk import TOWNSFOLK

CHARS = Path(__file__).resolve().parent.parent
NAME = sys.argv[1]; ROW = TOWNSFOLK[NAME]; HERE = CHARS / 'NPC' / NAME
rep = json.loads((HERE / 'export_report.json').read_text())
hero = json.loads((CHARS / 'Dink/manifest.json').read_text())
OWN = {'Skin': ('BC', 'N', 'ORM', 'SSS'), 'Eyes': ('BC', 'N', 'ORM'), 'Hair': ('BC', 'N', 'ORM', 'FLOW', 'MSK'), 'Outfit': ('BC',), 'Gear': ('BC', 'N', 'ORM')}
PORT = ROW.get('body') == 'port'      # the clothes are the Unclaimed source's: Outfit and Gear both show its outfit maps, where they are
if PORT: OWN.update(Outfit=(), Gear=())
materials = {}
for slot, row in hero['materials'].items():
    row = json.loads(json.dumps(row))
    part = slot.rsplit('_', 1)[1]
    textures = {}
    for role, rel in row['textures'].items():
        if role in OWN[part]:
            textures[role] = f'Textures/T_{NAME}_PR_{part}_{role}.png'
            assert (HERE / textures[role]).is_file(), textures[role]
        elif PORT and part in ('Outfit', 'Gear'):
            textures[role] = f'../../../Unclaimed/{ROW["src"][0]}/T_{ROW["src"][1]}_Outfit_{role}.png'
            assert (HERE / textures[role]).is_file(), textures[role]
        else:
            textures[role] = '../../Dink/' + rel
    row['textures'] = textures
    materials[slot.replace('MI_Dink_PR_', f'MI_{NAME}_PR_')] = row
assert list(materials) == rep['materials'], (list(materials), rep['materials'])
manifest = {
    'schema': 'dink-photoreal-character/1', 'asset': rep['asset'], 'class': 'character_hero',
    'source_blend': f'NPC/{NAME}/SK_{NAME}_Photoreal.blend',
    'build': f'Characters/Tools/run_townsfolk.sh {NAME} (the stages are listed in that file)',
    'fbx': [f'Export/{rep["asset"]}_LOD{i}.fbx' for i in range(4)],
    'dimensions_m': rep['dimensions_m'], 'bone_count': rep['bone_count'], 'root_bone': 'root',
    'skeleton': hero['skeleton'], 'lods': rep['lods'], 'lod0_triangles': rep['lods'][0]['triangles'],
    'material_slots': rep['materials'], 'materials': materials,
    # the importer takes these from the hero's content folder instead of importing them again
    **({} if PORT else {'shared_textures': {'../../Dink/Textures': '/Game/Dink/Photoreal/Characters/Dink/Textures'}}),
    'placement_scale': ROW['placement_scale'], 'animation_set': ROW['animation_set'], 'families': ROW['families'],
    'what': ROW['what'],
    'validation': rep['validation'], 'validator_findings': rep['findings'],
    'known_weaknesses': ROW['weak'],
}
(HERE / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
print('manifest', HERE / 'manifest.json', 'LOD0 triangles', manifest['lod0_triangles'])
