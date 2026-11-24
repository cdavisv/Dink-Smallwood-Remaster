"""Write NPC/Maiden/manifest.json (schema dink-photoreal-character/1) from her export report.

The maiden is the Mother's body and dress with a head of her own stage (a younger face shape, the young skin set of
NPC/Maiden/cfg/skin.json) and long loose hair (hair_styles.py 'Maiden', groom kind 'long'). Her eye, outfit and gear
texture sets are the Mother's, referenced where they are. The three colour twins (MaidenBlue / Brown / Red,
npc_variants.py) are copies of her.

    blender -b -t 4 --python dink_04_head.py -- <abs>/NPC/Maiden/cfg/head.json
    blender -b -t 4 --python dink_05b_skin.py -- <abs>/NPC/Maiden/cfg/skin.json
    blender -b -t 4 --python hair_groom.py -- Maiden atlas,save m1
    blender -b -t 4 --python dink_06_assemble.py -- <abs>/NPC/Maiden/cfg/assemble.json
    blender -b -t 4 --python char_07_build.py -- NPC/Maiden Matron 0                    no build: combs the neckline skin (cfg skin_relax)
    blender -b -t 4 <Characters>/NPC/Maiden/SK_Maiden_Photoreal.blend --python export_char.py -- <abs>/NPC/Maiden/Export <abs>/NPC/Maiden/export_report.json character_humanoid
    python3 -I maiden_manifest.py
    blender -b -t 4 --python maiden_trim.py ; python3 -I npc_variants.py              the twins' dress maps with the white trim"""
import json
from pathlib import Path

CHARS = Path(__file__).resolve().parent.parent
HERE = CHARS / 'NPC/Maiden'
rep = json.loads((HERE / 'export_report.json').read_text())
mother = json.loads((CHARS / 'Mother/manifest.json').read_text())
OWN = ('Skin', 'Hair')
materials = {}
for slot, row in mother['materials'].items():
    row = json.loads(json.dumps(row))
    part = slot.rsplit('_', 1)[1]
    if part in OWN:
        row['textures'] = {role: f'Textures/T_Maiden_PR_{part}_{role}.png' for role in row['textures']}
        assert all((HERE / rel).is_file() for rel in row['textures'].values()), slot
    else:
        row['textures'] = {role: '../../Mother/' + rel for role, rel in row['textures'].items()}
    materials[slot.replace('MI_Mother_PR_', 'MI_Maiden_PR_')] = row
assert list(materials) == rep['materials'], (list(materials), rep['materials'])
manifest = {
    'schema': 'dink-photoreal-character/1', 'asset': rep['asset'], 'class': 'character_humanoid',
    'source_blend': 'NPC/Maiden/SK_Maiden_Photoreal.blend',
    'build': 'the stages listed at the top of Characters/Tools/maiden_manifest.py',
    'fbx': [f'Export/{rep["asset"]}_LOD{i}.fbx' for i in range(4)],
    'dimensions_m': rep['dimensions_m'], 'bone_count': rep['bone_count'], 'root_bone': 'root',
    'skeleton': mother['skeleton'], 'lods': rep['lods'], 'lod0_triangles': rep['lods'][0]['triangles'],
    'material_slots': rep['materials'], 'materials': materials,
    'shared_textures': {'../../Mother/Textures': '/Game/Dink/Photoreal/Characters/Mother/Textures'},
    'placement_scale': 0.9, 'animation_set': 'NpcF', 'families': [],
    'what': 'the young woman of the 1997 pictures 221-259 (people/maiden): base of the colour twins MaidenBlue, MaidenBrown and MaidenRed',
    'validation': rep['validation'], 'validator_findings': rep['findings'],
    'known_weaknesses': [
        'The body and the dress are the Mother\'s (without her stout build); the white sleeve bands, the pale neckline edge and the skirt stripes of the 1997 maiden are painted on the twins\' dress maps (maiden_trim.py), not sewn; the 1997 skirt is fuller.',
        'The long hair is cards skinned to the head, the neck and the back by surface transfer: it does not swing, and a deep bow or a raised arm passes through it.',
        'The face is sculpted with the kit\'s face operations on the Mother\'s base head (cfg/head.json): a young woman of no particular likeness.',
    ],
}
(HERE / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
print('manifest', HERE / 'manifest.json')
