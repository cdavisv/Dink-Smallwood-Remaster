"""Write candidate ledger rows locally; parent coordinates the shared ledger merge."""
import csv,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[3]
with (PROJECT/'SourceAssets/asset_ledger.csv').open(newline='') as handle:fields=csv.DictReader(handle).fieldnames
files=[ROOT/'SK_Pig.blend',*sorted((ROOT/'Export').glob('*.fbx')),*sorted((ROOT/'Textures').glob('*.png')),*[ROOT/name for name in ['pig_manifest.json','pig_rig_report.json','pig_lod_report.json','pig_pose_validation.json','pig_validation.json','fbx_inspection.json']]]
rows=[]
for path in files:
    if path.suffix=='.png':derived='Content/Dink/Textures/Creatures/'+path.stem+'.uasset';kind='texture'
    elif path.name.startswith('A_Pig_'):derived='Content/Dink/Creatures/Pig/Animations/AN_'+path.stem.removeprefix('A_')+'.uasset';kind='animation'
    elif path.suffix in ['.fbx','.blend']:derived='Content/Dink/Creatures/Pig/SK_Pig.uasset';kind='skeletal_mesh'
    elif path.name=='pig_manifest.json':derived='Content/Dink/Data/Art/creatures.json';kind='manifest'
    else:derived='source validation/provenance evidence';kind='report'
    row={name:'' for name in fields};row.update(asset_path=str(path.relative_to(PROJECT)),derived_path=derived,kind=kind,
        replaces='S407_P02;S407_P05;S407_P06;S407_P07;S407_P11',source='Original project-authored pig anatomy, procedural PBR materials, quadruped rig and actions',
        tool_model='Blender5.2.2LTS / deterministic Python model,bone heat,torso mask,atlas bake',prompt='Grounded domestic pig with organic skin, recessed nostrils, inset eyes, cloven horn toes, curled tail and sparse stubble',
        parameters='26bone ownquadruped;3LODs19266/9633/4815tris;4slots;2048BC/N/ORM;max4weights;Idle2s Walk.6s80cm/s Run.4s400cm/s Feed.4s',
        generation_id='stonebrook-pig-v2-albedo',generated_on='2026-11-07',credits='0',licence='Original project-authored work; no third-party geometry/textures. Anatomy reference publication used for observation only, see README.',
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status='candidate',notes='Source validator0errors; all-frame joint/root/loop checks pass. Accepted first-import candidate: small compressed underbelly/hip crease remains in gallop quarter04. Skin/Muzzle linear albedo0.5 revision; geometry/rig/UVs/normal/roughness/eye/horn colors unchanged. Original gameplay behavior unchanged.')
    rows.append(row)
with (ROOT/'asset_ledger_rows.csv').open('w',newline='') as handle:
    writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
print('PIG LOCAL LEDGER ROWS:',len(rows),'shared ledger untouched')
