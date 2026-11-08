"""Write candidate rows locally; parent coordinates shared asset-ledger merge."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[3]
with (PROJECT/'SourceAssets/asset_ledger.csv').open(newline='') as f:fields=csv.DictReader(f).fieldnames
files=[ROOT/'SK_Pillbug.blend',*sorted((ROOT/'Export').glob('*.fbx')),*sorted((ROOT/'Textures').glob('*.png')),*[ROOT/n for n in ['pillbug_manifest.json','pillbug_rig_report.json','pillbug_lod_report.json','pillbug_pose_validation.json','pillbug_validation.json','fbx_inspection.json']]]
manifest=json.loads((ROOT/'pillbug_manifest.json').read_text());rows=[]
for path in files:
 if path.suffix=='.png':derived='Content/Dink/Textures/Creatures/'+path.stem+'.uasset';kind='texture'
 elif path.name.startswith('A_Pillbug_'):derived='Content/Dink/Creatures/Pillbug/Animations/AN_'+path.stem.removeprefix('A_')+'.uasset';kind='animation'
 elif path.suffix in ['.fbx','.blend']:derived='Content/Dink/Creatures/Pillbug/SK_Pillbug.uasset';kind='skeletal_mesh'
 elif path.name=='pillbug_manifest.json':derived='Content/Dink/Data/Art/creatures.json';kind='manifest'
 else:derived='source validation/provenance evidence';kind='report'
 row={n:'' for n in fields};row.update(asset_path=str(path.relative_to(PROJECT)),derived_path=derived,kind=kind,replaces=';'.join(manifest['origins']),
 source='Original project-authored pillbug segmented anatomy, procedural PBR cuticle, bespoke rig and metachronal actions',tool_model='Blender5.2.2LTS / deterministic Python modeled plates and cuticle, rigid weights, analytic legIK, conformal UV atlas bake',
 prompt='Grounded blue-green armored pillbug with ochre rims, seven overlapping thoracic plates, fourteen articulated legs, inset compound eyes, jointed antennae and realistic cuticle surface',
 parameters='creature;43bones;3LODs24000/12000/6000tris;4opaque slots;2048BC/N/ORM;max4weights;Idle2s Walk.375s80cm/s Run.375s400cm/s;40fps;rootmotion0',
 generation_id='stonebrook-pillbug-v1',generated_on='2026-11-07',credits='0',licence='Original project-authored work; no third-party geometry/textures. Biology and original sprite references used for observation only; see README.',
 sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status='candidate',notes='Source validator0errors/1nonexportedstudio warning; uniqueUV overlap0; all-frame finite/unit-scale/joint/root/loop checks pass; independentFBX6filesheader1cm/rootScale1. Lowerlegdetail remains simplified at project gameplay viewing distance. Engine import/PhysicsAsset/pose/gameplay QA belongs to staged integration. Existing scripts, stats, vision, speed and immediate death unchanged.')
 if kind=='animation':row['duration_s']=str(manifest['animations'][path.stem.removeprefix('A_Pillbug_')]['duration_s'])
 rows.append(row)
with (ROOT/'asset_ledger_rows.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
assert all(hashlib.sha256((PROJECT/r['asset_path']).read_bytes()).hexdigest()==r['sha256'] for r in rows)
print('PILLBUG LOCAL LEDGER PASS',len(rows),'hashes; shared ledger untouched')
