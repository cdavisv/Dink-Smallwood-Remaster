"""Prepare local candidate rows only; parent owns the shared ledger merge."""
import csv,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[3]
with (PROJECT/'SourceAssets/asset_ledger.csv').open(newline='') as handle:fields=csv.DictReader(handle).fieldnames
files=[ROOT/'SK_Milder.blend',*sorted((ROOT/'Export').glob('*.fbx')),*sorted((ROOT/'Textures').glob('*.png')),
       *[ROOT/name for name in ['milder_manifest.json','milder_rig_report.json','milder_lod_report.json','milder_validation.json','fbx_inspection.json']],
       *sorted(p for p in (ROOT/'ThirdParty').rglob('*') if p.is_file())]
rows=[]
for path in files:
    raw='ThirdParty' in path.parts;atlas='Atlas_' in path.name
    if raw:derived='SourceAssets/Art/Characters/Milder/SK_Milder.blend';kind='source'
    elif path.suffix=='.png':
        derived=('Content/Dink/Textures/Characters/'+path.stem+'.uasset') if atlas else 'SourceAssets/Art/Characters/Milder/Textures/T_Milder_Atlas_BC.png';kind='texture'
    elif path.suffix in ['.fbx','.blend']:derived='Content/Dink/NPC/Milder/SK_Milder.uasset';kind='skeletal_mesh'
    elif path.name=='milder_manifest.json':derived='Content/Dink/Data/Art/characters.json (local runtime merge)';kind='manifest'
    else:derived='source validation/provenance evidence';kind='report'
    row={name:'' for name in fields};row.update(asset_path=str(path.relative_to(PROJECT)),derived_path=derived,kind=kind,replaces='dynamic s1-bul Milder (initialseq341,base_walk400;reference401/01)',
        source='Official MakeHuman system assets CC0 archive' if raw else 'CC0 anatomical human/skin/eyes/hair plus original project-authored soldier armor and wardrobe',
        tool_model='MPFB2 commit6ff1eb358f6c1959ced77e79e6dd2406d9a71f49 / Blender5.2.2LTS',
        prompt='Grounded mature Milder soldier, brown hair, forged steel plates, leather equipment, blue gambeson/waistcloth,nohelmet',
        parameters='89bone exactManny rest rig;4LODs32674/16337/8168/3921tris;5slots;4096uniqueUV BC/N/ORM;max4weights;rigidarmor masks',
        generation_id='character-milder-v1',generated_on='2026-11-07',credits='0',
        licence='CC0 1.0 MakeHuman system asset; explicit2020release notices preserved' if raw else 'CC0 MakeHuman derivatives + original project wardrobe; Epic reference skeleton transforms remain separate UE project data, not CC0 geometry',
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status='candidate',
        notes='Raw selected authoring input; shared provenance under Characters/Provenance' if raw else 'No Epic robot geometry delivered. Source validator0errors;wire artifacts stripped fromallLODs. Two3-face waist-clothing edge junctions remain documented; stagedin-game deformation/lighting review required.')
    rows.append(row)
with (ROOT/'asset_ledger_rows.csv').open('w',newline='') as handle:
    writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
print('MILDER LOCAL LEDGER ROWS:',len(rows),'shared ledger untouched')
