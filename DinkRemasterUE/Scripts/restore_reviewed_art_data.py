"""Restore reviewed art metadata from preserved import receipts without reimporting assets.
Requires an isolated project with local Data. Every reconstructed byte stream must
match the saved 121-test input hash before any runtime file is replaced.
"""
from pathlib import Path
import argparse,copy,json,hashlib,math,os,types
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);a=p.parse_args()
stage=a.project.resolve();data=stage/'Content/Dink/Data';evidence=ROOT/'Saved/StonebrookFieldsStage'
assert stage!=ROOT.resolve() and data.is_dir() and not data.is_symlink() and data.resolve().is_relative_to(stage),'Local isolated Data required'
expected=json.loads((evidence/'full_inputs_before.json').read_text())['data']
art=data/'Art';payloads={}
for screen in [471,438]:
 source=stage/'SourceAssets/Art/StonebrookFields';layout=json.loads((source/f'fields_{screen}_layout.json').read_text())
 spec=json.loads((source/'art_manifest.json').read_text());report=json.loads((evidence/f'stonebrook_fields_{screen}_import_report.json').read_text());checks=report['bounds_checks']
 meshes={row['mesh'].rsplit('/',1)[1].split('.')[0]:row['mesh'] for row in checks}
 for name in {r['mesh'] for r in layout.get('replacements',[])+layout.get('elements',[])}-set(meshes):
  path=layout.get('asset_paths',{}).get(name,'/Game/Dink/Kits/Stonebrook/'+name)
  assert (ROOT/'Content'/(path.removeprefix('/Game/').split('.')[0]+'.uasset')).is_file(),path
  meshes[name]=path if '.' in path.rsplit('/',1)[1] else path+'.'+path.rsplit('/',1)[1]
 code=(ROOT/'Scripts/import_stonebrook_art.py').read_text();code=code[code.index('# Dressing is described'):code.index("dest = ROOT / ('Content/Dink/Data/Art/")]
 ns={'ROOT':stage,'SOURCE':source,'SPEC':spec,'LAYOUT':layout,'LAYOUT_SCREEN':screen,'OUTPUT_NAME':f'stonebrook_fields_{screen}','checks':checks,'meshes':meshes,'json':json,'math':math,'os':types.SimpleNamespace(environ={})}
 exec(compile(code,'reviewed_static_metadata','exec'),ns)
 payloads[f'Art/stonebrook_fields_{screen}.json']=ns['runtime']
characters=json.loads((art/'characters.json').read_text());hand=json.loads((evidence/'character_dink_hands_import_report.json').read_text())['assets']
assert not any(v['mesh']==hand[0]['mesh'] for v in characters['assets'])
characters['assets']+=hand;characters['player']={'mesh':hand[0]['mesh']};payloads['Art/characters.json']=characters
import sys
sys.path.insert(0,str(ROOT/'Scripts'))
from creature_art_manifest import asset_origins,merge_runtime
spec=json.loads((ROOT/'SourceAssets/Art/Creatures/Pillbug/pillbug_manifest.json').read_text());row=next(iter(spec['assets'].values()));report=json.loads((evidence/'creature_pillbug_import_report.json').read_text())['assets'][0]
new={'schema':'dink-creatures/1','assets':[report],'placements':[]}
for origin in asset_origins(spec,row):
 new['placements'].append({'origin':origin,'mesh':report['mesh'],'locomotion':report['locomotion'],'feed_animation':'','offset_cm':[0,0,0],'rotation_deg':report['rotation_deg'],'scale':[1,1,1],'body_boxes':report['body_boxes'],'food_sequences':[],'food_bone':row.get('head_bone','head'),'food_radius_cm':70,'food_forward_dot':.5,'stationary_speed_cm_s':5,'nominal_walk_speed_cm_s':report['nominal_walk_speed_cm_s'],'nominal_run_speed_cm_s':report['nominal_run_speed_cm_s']})
payloads['Art/creatures.json']=merge_runtime(json.loads((art/'creatures.json').read_text()),new)
payloads['Art/hero_actions.json']={'schema':'dink-hero-actions/1','skeleton':'/Game/Characters/Mannequins/Meshes/SK_Mannequin.SK_Mannequin','actions':[{'sequences':[102,104,106,108],'animation':'/Game/Dink/Hero/Animations/AN_Dink_Fist.AN_Dink_Fist','duration_s':.4,'impact_s':.175,'loop':False}],'gameplay_authority':'Original sp_seq/pending-hit timing; animation is cosmetic only'}
recovery=stage/'Saved/Recovery';recovery.mkdir(parents=True,exist_ok=True);serialized={};bad=[]
for name,payload in payloads.items():
 text=json.dumps(payload,indent=2)+'\n';digest=hashlib.sha256(text.encode()).hexdigest();serialized[name]=text
 if digest!=expected[name]:
  bad.append({'file':name,'expected':expected[name],'reconstructed':digest});(recovery/('candidate_'+Path(name).name)).write_text(text)
assert not bad,'Reconstruction differs: '+str(bad)
for name,text in serialized.items():
 dest=data/name;temporary=dest.with_suffix('.tmp');temporary.write_text(text);os.replace(temporary,dest)
actual={str(v.relative_to(data)):hashlib.sha256(v.read_bytes()).hexdigest() for v in data.rglob('*') if v.is_file()}
assert actual==expected,'Other runtime inputs changed: '+str([k for k in expected if actual.get(k)!=expected[k]])
receipt={'restored_files':list(serialized),'runtime_files_verified':len(actual),'all_hashes_equal_to_reviewed_121_snapshot':True,'asset_reimports':0,'source':'Preserved source layouts/import reports; pure original metadata producer, strict byte hash validation'}
(recovery/'art_data_restoration.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
