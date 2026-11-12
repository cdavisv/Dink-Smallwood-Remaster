"""Proposed asset-ledger rows (same columns as SourceAssets/asset_ledger.csv) for every delivered file in
this directory.  Writes ledger_rows_proposed.csv only; the shared ledger is not touched."""
import csv, hashlib, json
from pathlib import Path

ART = Path(__file__).resolve().parent
REL = 'SourceAssets/Art/Stonebrook440/'
COLS = ['asset_path', 'derived_path', 'kind', 'replaces', 'source', 'tool_model', 'prompt', 'parameters', 'generation_id', 'flow_id',
        'generated_on', 'credits', 'licence', 'sha256', 'duration_s', 'status', 'notes']
man = json.loads((ART / 'art_manifest.json').read_text())
BASE = dict(replaces='SCR_440 legacy house/door/window sprite cards (S440_P03/P04/P06/P08/P09/P11), tool sprites S440_P21-P25 and greybox blockers',
            source='Original project-authored procedural geometry, numpy texture synthesis and Cycles bakes of procedural node materials',
            tool_model='Blender 5.2.2 LTS / Python 3.14 numpy + Pillow; no generative model, no downloaded meshes or images',
            prompt='Taller two-storey Stonebrook fieldstone house with rounded thatch, farm tools and yard dressing; real-world scale',
            parameters='seed=440; metres; FBX_SCALE_ALL apply_unit_scale=True; Z-up; front=-Y; 3 LODs (1, .5, .25); BC/N/ORM',
            generation_id='stonebrook440-kit-v1', flow_id='', generated_on='2026-11-08', credits='0',
            licence='Original project asset; no third-party source material. Reused Stonebrook limewash/wrought-iron sets keep their existing ledger rows',
            duration_s='', status='candidate',
            notes='LOCAL proposed rows; not merged into asset_ledger.csv. Not imported into Unreal; no in-engine or walking verification.')


def kind_of(p):
    s = p.suffix.lower()
    if s == '.blend': return 'blender_source'
    if s == '.fbx': return 'model'
    if s == '.glb': return 'derived_export'
    if s == '.py': return 'generator'
    if s == '.md': return 'source_documentation'
    if s == '.png' and p.name.startswith('preview'): return 'preview'
    if s == '.png': return 'texture'
    if p.name.startswith('layout_440'): return 'placement_plan'
    if 'manifest' in p.name: return 'manifest'
    return 'report'


def derived(p):
    if p.suffix == '.fbx':
        name = p.stem.rsplit('_LOD', 1)[0]
        return man['assets'].get(name, {}).get('ue_path', '')
    if p.suffix == '.png' and p.name.startswith('T_S440'):
        return '/Game/Dink/Textures/Stonebrook440/' + p.stem
    return ''


rows = []
for p in sorted(ART.rglob('*')):
    if not p.is_file() or p.name.endswith('.blend1') or '__pycache__' in p.parts or 'Working' in p.parts or p.name == 'ledger_rows_proposed.csv':
        continue
    r = dict(BASE); r['asset_path'] = REL + str(p.relative_to(ART)); r['kind'] = kind_of(p); r['derived_path'] = derived(p)
    r['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    rows.append(r)
with open(ART / 'ledger_rows_proposed.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
print(len(rows), 'proposed ledger rows')
