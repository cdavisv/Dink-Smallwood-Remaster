"""Local candidate receipts only; shared ledger merge belongs toparent."""
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[4]
with (PROJECT/'SourceAssets/asset_ledger.csv').open(newline='') as f:fields=csv.DictReader(f).fieldnames
files=[ROOT/'SK_Dink_Hands.blend',*sorted((ROOT/'Export').glob('*.fbx')),*[ROOT/n for n in ['hand_manifest.json','hand_landmarks.json','hand_binding_report.json','scope_verification.json','hand_validation.json','hand_lod_report.json','fbx_inspection.json','hand_import_preflight.json']]]
rows=[]
for p in files:
 kind='skeletal_mesh' if p.suffix in ['.blend','.fbx'] else('manifest' if p.name=='hand_manifest.json' else 'report');derived='Content/Dink/Hero/Refinements/SK_Dink_Hands.uasset' if kind=='skeletal_mesh' else('Content/Dink/Data/Art/characters.json' if kind=='manifest' else 'source validation/provenance evidence')
 r={n:'' for n in fields};r.update(asset_path=str(p.relative_to(PROJECT)),derived_path=derived,kind=kind,replaces='player hand presentation; separately named corrective candidate',source='ExistingCC0 MakeHuman-basedDink anatomy and originalprojectwardrobe; originalisolatedper-digit handfit/weights; existingEpic rig unchanged',tool_model='Blender5.2.2LTS / originalanatomicaljoint controls, per-digit mapping, explicitisolatedweights, independentoutsidehandfingerprints',prompt='Correct anatomicalfinger fit and closedfist without altering originalhero or anyoutsidehandpositions/weights/UVs/materials/89resttransforms',parameters='89bones;4realLODs31688/15844/7921/3803tris;5reusedmaterialslots;max4weights;outsidehandSHA/UV/restboneproof;no newtextures',generation_id='dink-hand-binding-v2',generated_on='2026-11-07',credits='0',licence='ExistingCC0 MakeHuman anatomy/texture inputs plus originalprojectclothes and handcorrection; Epiccompatibilityrig retainsEpicterms. SeeREADME.',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status='candidate',notes='Independent4LODoutsidepositions/weights/UV/materials+89rest equalityPASS; crossdigitcontamination0; normalzeros0. Guide0errors/11inheritedtopologywarnings incl originalwireedges1/3/7; tinyangularthumbwebfold remains closeviewpolish. Nooriginalhero/material/runtimefiles changed; stagedUEreviewrequired.')
 rows.append(r)
with (ROOT/'asset_ledger_rows.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
assert all(hashlib.sha256((PROJECT/r['asset_path']).read_bytes()).hexdigest()==r['sha256'] for r in rows)
print('HANDV2 LOCAL LEDGER PASS',len(rows),'hashes; sharedledger untouched')
