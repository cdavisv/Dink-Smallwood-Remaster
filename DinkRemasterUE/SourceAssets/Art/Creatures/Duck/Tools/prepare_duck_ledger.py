"""Write ledger_rows_proposed.csv (same columns as SourceAssets/asset_ledger.csv) with live sha256.

    python3 Tools/prepare_duck_ledger.py

The shared ledger is NOT modified; the integrating agent merges these rows.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402

COLUMNS = ['asset_path', 'derived_path', 'kind', 'replaces', 'source', 'tool_model', 'prompt', 'parameters', 'generation_id',
           'flow_id', 'generated_on', 'credits', 'licence', 'sha256', 'duration_s', 'status', 'notes']
lod = json.loads((D.ROOT / 'duck_lod_report.json').read_text())
man = json.loads((D.ROOT / 'duck_manifest.json').read_text())
tris = '/'.join(str(l['triangles']) for l in lod['SK_Duck']['lods'])
clips = ' '.join('%s%gs' % (k, v['duration_s']) for k, v in man['animations'].items())
tris_h = '/'.join(str(l['triangles']) for l in lod['SK_Duck_Headless']['lods'])
tris_p = '/'.join(str(l['triangles']) for l in lod['SM_Duck_Head']['lods'])
params = '23bone own rig;SK_Duck 3LODs %s tris;SK_Duck_Headless 3LODs %s;SM_Duck_Head 3LODs %s+UCX;4slots;2048 BC(alpha)/N/ORM;max4weights;%s' % (tris, tris_h, tris_p, clips)
common = dict(
    replaces='seq 21-29 duck walk; 111-119 bloody headless duck; 121-129 severed duck head; 187-189 blood (brain 3 ducks, Quackers)',
    source='Original project-authored domestic Pekin-type duck anatomy, procedural numpy PBR atlas, own rig and actions',
    tool_model='Blender 5.2.2 LTS / deterministic Python (metaball anatomy, UV-space numpy texture synthesis, analytic leg IK)',
    prompt='White domestic Pekin duck matching the original sprite palette, plus the original head-off gore set (stump, severed head, blood)',
    parameters=params, generation_id='stonebrook-duck-v1', flow_id='', generated_on='2026-11-08', credits='0',
    licence='Original project-authored work; no third-party geometry, textures or generative models.', duration_s='',
    status='candidate',
    notes='Source validator %d errors/%d warnings; all-frame joint/root/loop checks pass. Not yet imported into Unreal.' % (
        lod['validation']['errors'], lod['validation']['warnings']))
REL = 'SourceAssets/Art/Creatures/Duck/'
rows = []


def add(rel, derived, kind):
    p = D.ROOT / rel
    row = dict(common, asset_path=REL + rel, derived_path=derived, kind=kind,
               sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    if kind == 'animation':
        row['duration_s'] = str(man['animations'][Path(rel).stem.split('_')[-1]]['duration_s'])
    rows.append(row)


add('SK_Duck.blend', 'Content/Dink/Creatures/Duck/SK_Duck.uasset', 'skeletal_mesh')
for i in range(3):
    add('Export/SK_Duck_LOD%d.fbx' % i, 'Content/Dink/Creatures/Duck/SK_Duck.uasset', 'skeletal_mesh')
for i in range(3):
    add('Export/SK_Duck_Headless_LOD%d.fbx' % i, 'Content/Dink/Creatures/Duck/SK_Duck_Headless.uasset', 'skeletal_mesh')
for i in range(3):
    add('Export/SM_Duck_Head_LOD%d.fbx' % i, 'Content/Dink/Creatures/Duck/SM_Duck_Head.uasset', 'static_mesh')
for k in man['animations']:
    add('Export/A_Duck_%s.fbx' % k, 'Content/Dink/Creatures/Duck/Animations/AN_Duck_%s.uasset' % k, 'animation')
for t in ('BC', 'N', 'ORM'):
    add('Textures/T_Duck_Atlas_%s.png' % t, 'Content/Dink/Textures/Creatures/T_Duck_Atlas_%s.uasset' % t, 'texture')
    for dec in ('BloodPool', 'BloodSpatter'):
        add('Textures/T_Duck_%s_%s.png' % (dec, t), 'Content/Dink/Textures/Creatures/T_Duck_%s_%s.uasset' % (dec, t), 'texture')
add('duck_manifest.json', 'Content/Dink/Data/Art/creatures.json', 'manifest')
add('duck_gore_manifest.json', 'integration draft (headless variant, head prop, decals, original behaviour)', 'manifest')
for r in ('duck_rig_report.json', 'duck_lod_report.json', 'duck_pose_validation.json', 'duck_validation.json',
          'duck_texture_report.json', 'fbx_inspection.json', 'duck_origins.json'):
    add(r, 'source validation/provenance evidence', 'report')
with open(D.ROOT / 'ledger_rows_proposed.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(rows)
print('wrote', len(rows), 'proposed ledger rows')
