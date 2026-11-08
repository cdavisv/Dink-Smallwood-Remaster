"""Record CC0 inputs separately from original output and Epic reference rig data."""
import csv,json,hashlib,argparse
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--name',default='Mother');args=P.parse_args()
ART=Path(__file__).resolve().parents[1];ROOT=ART.parents[2];name=args.name
folder=ART if name=='Mother' else ART/name
ledger=ROOT/'SourceAssets/asset_ledger.csv'
with ledger.open(newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
inputs=list((ART/'ThirdParty/MakeHuman').rglob('*'))
outputs=[folder/('SK_'+name+'.blend'),*list((folder/'Export').glob('*.fbx')),*list((folder/'Textures').glob('*.png'))]
reports=[folder/(name.lower()+suffix) for suffix in ['_rig_report.json','_lod_report.json','_validation.json']]
files=[p for p in inputs+outputs+reports if p.is_file()]
keys={str(p.relative_to(ROOT)) for p in files};rows=[r for r in rows if r['asset_path'] not in keys]
for p in files:
    raw='ThirdParty' in p.parts;atlas='Atlas_' in p.name
    target='Content/Dink/NPC/Mother/SK_Mother.uasset' if name=='Mother' else 'Content/Dink/Hero/SK_Dink.uasset'
    if raw:derived=str((folder/'Textures'/('T_'+name+'_Atlas_BC.png')).relative_to(ROOT))
    elif p.suffix=='.png':derived=('Content/Dink/Textures/Characters/'+p.stem+'.uasset') if atlas else str((folder/'Textures'/('T_'+name+'_Atlas_BC.png')).relative_to(ROOT))
    elif p.suffix=='.json':derived='validation/provenance evidence; not a runtime asset'
    else:derived=target
    row={k:'' for k in fields}
    row.update(asset_path=str(p.relative_to(ROOT)),derived_path=derived,kind='source' if raw else ('texture' if p.suffix=='.png' else ('report' if p.suffix=='.json' else 'skeletal_mesh')),
        replaces='S001_P26 mother sprite' if name=='Mother' else 'Player mannequin / Dink',
        source='Official MakeHuman system assets' if raw else 'CC0 MakeHuman anatomical base plus original project-authored wardrobe and atlas bake',
        tool_model='MPFB2 commit6ff1eb358f6c1959ced77e79e6dd2406d9a71f49 / Blender5.2.2LTS',
        prompt='Grounded rural middle-aged mother in rust dress and linen apron' if name=='Mother' else 'Grounded young Dink in rustic tunic, tan trousers and leather boots',
        parameters='89bone shared Manny rest skeleton; source metres / temporary cmFBX;4LODs;5materialslots;max4weights',
        generation_id='character-'+name.lower()+('-v2' if name=='Dink' else '-v1'),generated_on='2026-11-07',credits='0',
        licence='CC0 1.0 original MakeHuman asset; explicit2020release notices preserved' if raw else 'CC0 MakeHuman body/texture derivatives + original project wardrobe; Epic-compatible reference bone transforms are separate UE-licensed data, not CC0 geometry',
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status='candidate',
        notes='Raw shared character authoring input only; see Characters/Provenance/makehuman_sources.json' if raw else ('No Epic robot geometry delivered. Runtime atlas/mesh candidate; bind pose checked separately against all89original bones. Fine cloth/bust polish remains candidate review.' if name=='Mother' else 'No Epic robot geometry delivered. Rustic split-neck shirt, sewn binding, conforming cuffs, iron buckle and boot welts. Five slots, four LODs, exact89bone reference; live deformation candidate review required.'))
    rows.append(row)
with ledger.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('CHARACTER LEDGER:',name,len(files),'files')
