"""Refresh hashes and ledger rows for the original Stonebrook asset kit after export."""
import csv
import hashlib
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
exterior='--exterior' in sys.argv
folder='StonebrookExterior' if exterior else 'Stonebrook'
ART=ROOT/'SourceAssets/Art'/folder
LEDGER=ROOT/'SourceAssets/asset_ledger.csv'
blend='KIT_StonebrookExterior.blend' if exterior else 'KIT_Stonebrook.blend'
files=[ART/blend,*sorted((ART/'Textures').glob('*.png')),*sorted((ART/'Export').rglob('*.fbx')),*sorted((ART/'Export').rglob('*.glb'))]
with LEDGER.open(newline='') as f:
    reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
owned={str(p.relative_to(ROOT)) for p in files}
rows=[r for r in rows if r['asset_path'] not in owned]
for file in files:
    rel=str(file.relative_to(ROOT)); h=hashlib.sha256(file.read_bytes()).hexdigest()
    if file.suffix=='.blend':
        derived='Content/Dink/Kits/'+folder+'; Content/Dink/Materials/Stonebrook; Content/Dink/Textures/Stonebrook'
    elif file.suffix=='.png':derived='Content/Dink/Textures/Stonebrook/'+file.stem+'.uasset'
    else:
        asset_name=file.stem
        if file.suffix=='.fbx' and '_LOD' in asset_name and asset_name.rsplit('_LOD',1)[1].isdigit():asset_name=asset_name.rsplit('_LOD',1)[0]
        derived='Content/Dink/Kits/'+folder+'/'+asset_name+'.uasset'
    row={k:'' for k in fields}
    row.update(asset_path=rel,derived_path=derived,kind='texture' if file.suffix=='.png' else 'mesh',
               replaces=('House exterior SCR_439 legacy sprite cards and greybox blockers' if exterior else 'Starting house SCR_001 legacy sprite cards and greybox blockers'),source='Original project-authored procedural geometry and texture synthesis',
               tool_model='Blender 5.2.2 LTS / Python numpy; no generative model or external input assets',
               prompt='Rustic oak, limewashed timber, fieldstone and coarse woven linen; realistic human scale',
               parameters=('seed=439' if exterior else 'seed=1997')+'; metres; FBX_SCALE_ALL; Z-up; front=-Y; BC/N/ORM 1024px',
               generation_id=folder.lower()+'-kit-v1',generated_on='2026-11-06',credits='0',
               licence='Original project asset; no third-party source material',sha256=h,status='candidate',
               notes='Local playtest candidate. Rebuild with SourceAssets/Art/tools/'+('build_exterior.py' if exterior else 'build_stonebrook.py')+'; exported with companion dinkasset validator/exporter; human art approval pending.')
    rows.append(row)
with LEDGER.open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
backup=ART/(blend+'1')
if backup.exists():backup.unlink()
print(f'STONEBROOK LEDGER: {len(files)} original files recorded with SHA-256')
