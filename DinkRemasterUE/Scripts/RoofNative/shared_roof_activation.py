"""Explicit Data-route epoch. Old trial contracts/receipts are never rewritten or waived."""
from pathlib import Path
import csv,copy,hashlib,json
from shared_roof_contract import SOURCE,LIBRARY,NAMES,TRIAL,PRODUCTION,load_contract,sha,require
DOC=Path('Docs/Verification/InteriorRoofSharedActivation')
DELIVERY=SOURCE.parent/'InteriorRoofSharedV1NativeDelivery'
HOUSE='Content/Dink/Data/Art/stonebrook.json'
CAMERA='Content/Dink/Data/Art/camera_materials.json'
HELPERS=('shared_roof_contract.py','shared_roof_native.py','shared_roof_entry_template.py','shared_roof_activation.py','test_shared_roof_activation.py')
NOTE='\n## Selected native delivery route\n\nThe eight verified InteriorRoofSharedV1 meshes are the production Data targets. This supersedes the old material-overwrite-only proposal without changing any old package or source geometry. Three opaque-to-separate-masked aliases preserve camera cutaway. Saved native23 verification passed; postactivation world/GPU/cook and final art approval remain pending. See native_delivery_mapping.json and Docs/Verification/InteriorRoofSharedActivation. Old plans/proofs remain historical and are not re-labelled as executed.\n'

def read(root,name):return json.loads((Path(root)/DOC/name).read_text())
def expected_data(before,contract):
 result=copy.deepcopy(before);changed=[]
 for index,row in enumerate(result[HOUSE]['elements']):
  for name in NAMES:
   old=PRODUCTION+name+'.'+name
   if row.get('mesh')==old:
    row['mesh']=TRIAL+name+'.'+name;changed.append(name)
 require(len(changed)==8 and set(changed)==set(NAMES),'Exact eight original roof elements required')
 variants=result[CAMERA]['material_variants']
 for opaque,masked in contract['camera_aliases'].items():
  require(opaque not in variants,'Shared camera alias already exists');variants[opaque]=masked
 return result

def delivery_mapping(contract,receipt):
 return dict(schema='dink-shared-roof-native-delivery/1',route='eight_Data_mesh_references_and_three_camera_aliases',historical_contract_digest=contract['digest'],historical_readback_phase=receipt['phase'],meshes={name:dict(previous=PRODUCTION+name,delivered=TRIAL+name)for name in NAMES},packages=dict(receipt['packages']),production_package_overwrites=0,source_geometry_changes=0,status='candidate_saved_native_verified_postactivation_world_GPU_cook_pending')

def expected_metadata(before,contract,receipt):
 original=json.loads(before['manifest.json']);assets=copy.deepcopy(original['assets'])
 for name,row in assets.items():
  require(row['content_path']==PRODUCTION+name and row['proposed_trial_path']==TRIAL+name,'Original source registration differs');row['legacy_content_path']=row['content_path'];row['content_path']=TRIAL+name;row['native_status']='SAVED_NATIVE_VERIFIED_POSTACTIVATION_WORLD_PENDING';row['source']='../InteriorRoofSharedV1/'+row['source'];row['fbx']='../InteriorRoofSharedV1/'+row['fbx']
 manifest=dict(schema='dink-shared-roof-native-delivery/1',assets=assets,delivery=delivery_mapping(contract,receipt),immutable_source_manifest=str(SOURCE/'manifest.json'),immutable_source_manifest_sha256=contract['source_pins'][str(SOURCE/'manifest.json')],supersedes='Historical trial-only delivery classification and old material-overwrite-only plan; no historical proof is re-labelled, no old file or source geometry changed.')
 encoded=json.dumps(manifest,indent=2)+'\n';return {'manifest.json':encoded,'SHA256SUMS.json':json.dumps({'manifest.json':hashlib.sha256(encoded.encode()).hexdigest()},indent=2)+'\n'}

def validate_epoch(root):
 root=Path(root).resolve();baseline=read(root,'baseline.json');epoch=read(root,'epoch.json')
 require(set(epoch['helper_source_deltas'])=={'Scripts/RoofNative/'+n for n in HELPERS},'Wrong exact helper delta set')
 require(sha(root/DOC/'before-helper-sources.json')==baseline['before_helper_sources_sha256'],'Helper preimages changed')
 prior=read(root,'before-helper-sources.json')
 for name,delta in epoch['helper_source_deltas'].items():
  require(delta['before_sha256']==prior[name] and sha(root/name)==delta['after_sha256'],'Reviewed helper source delta changed: '+name)
 for file,key in [('before-contract.json','before_contract_sha256'),('accepted-trial-readback.json','original_readback_sha256'),('before-data.json','before_data_sha256'),('before-source-metadata.json','before_metadata_sha256')]:require(sha(root/DOC/file)==baseline[key],'Historical evidence changed: '+file)
 require(sha(root/DOC/'accepted-native-report.json')==baseline['accepted_native_report_sha256'],'Raw actual native report changed')
 native=read(root,'accepted-native-report.json');summary=json.loads((root/'Docs/Verification/InteriorRoofSharedNativeTrial/results.json').read_text())['runs']['readback'];require(summary['NATIVE_REPORT.json_sha256']==baseline['accepted_native_report_sha256']and summary['passed']is True and summary['exit_code']==0 and summary['imports']==summary['saves']==0,'Committed actual readback authority differs')
 before=read(root,'before-contract.json');receipt=read(root,'accepted-trial-readback.json');require(native.get('passed')is True and native.get('protected_Content_unchanged')is True and native.get('receipt')==receipt and summary['packages']==receipt['packages'],'Actual native report/receipt bytes disagree');require(receipt.get('passed')is True and receipt.get('phase')=='fresh23_saved_readback'and receipt.get('contract_digest')==before['digest']and receipt.get('imports')==receipt.get('saves')==0,'Original actual saved readback required')
 canonical=dict(before);canonical.pop('digest');require(hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()==before['digest'],'Original contract digest invalid')
 require(epoch['historical_contract_digest']==before['digest']and epoch['historical_readback_sha256']==baseline['original_readback_sha256'],'Wrong explicit transition authority')
 require(len(receipt.get('textures',[]))==9 and len(receipt.get('materials',[]))==6 and len(receipt.get('meshes',[]))==8,'Actual saved23 verifier inventory incomplete')
 expected=expected_data(read(root,'before-data.json'),before)
 require(set(before['data_preimages'])=={str(p.relative_to(root))for p in(root/'Content/Dink/Data').rglob('*')if p.is_file()},'Data membership changed')
 for name,digest in before['data_preimages'].items():
  if name in expected:require(json.loads((root/name).read_text())==expected[name],'Unexpected Data semantic delta: '+name)
  else:require(sha(root/name)==digest,'Other Data changed: '+name)
 require({n:sha(root/n)for n in expected}==epoch['post_Data_sha256'],'Activated Data bytes changed')
 metadata=expected_metadata(read(root,'before-source-metadata.json'),before,receipt);added={str(DELIVERY/n)for n in metadata}
 require({str(p.relative_to(root))for p in(root/DELIVERY).rglob('*')if p.is_file()}==added,'Unexpected delivery mapping addition')
 require(epoch['approved_additions']=={str(DELIVERY/n):hashlib.sha256(text.encode()).hexdigest()for n,text in metadata.items()},'Wrong exact additive mapping hashes')
 for name,text in metadata.items():require((root/DELIVERY/name).read_bytes()==text.encode(),'Unexpected additive source mapping delta: '+name)
 require({str(p.relative_to(root))for folder in [SOURCE,LIBRARY]for p in(root/folder).rglob('*')if p.is_file()}==set(before['source_pins']),'Frozen source membership changed')
 for name,digest in before['source_pins'].items():require(sha(root/name)==digest,'Frozen source changed: '+name)
 after=load_contract(root)
 require(set(after['source_pins'])==set(before['source_pins'])|added,'Source membership changed outside mapping')
 require(after['source_pins']==epoch['post_source_pins'],'Post-mapping source epoch differs')
 for field in ['textures','materials','meshes','trial_packages','production','camera_aliases']:
  require(after[field]==before[field],'Native geometry/material/policy declaration changed: '+field)
 old=baseline['before_content'];now={str(p.relative_to(root)):sha(p)for p in(root/'Content').rglob('*')if p.is_file()};require(set(now)==set(old)|set(receipt['packages']),'Unexpected Content added/removed')
 for name,digest in old.items():
  if name not in expected:require(now[name]==digest,'Existing nonData Content changed: '+name)
 require(set(receipt['packages'])=={'Content/'+p.removeprefix('/Game/')+'.uasset'for p in before['trial_packages']}and len(receipt['packages'])==23,'Exact actual23 package set required')
 require(all(now[n]==h for n,h in receipt['packages'].items()),'Saved accepted package bytes changed')
 ledger=(root/'SourceAssets/asset_ledger.csv').read_bytes();prefix=baseline['ledger_prefix_bytes'];require(hashlib.sha256(ledger[:prefix]).hexdigest()==baseline['ledger_prefix_sha256'],'Existing ledger raw prefix changed');require(hashlib.sha256(ledger[prefix:]).hexdigest()==epoch['ledger_suffix_sha256'],'Unapproved ledger suffix bytes');rows=list(csv.DictReader(ledger.decode().splitlines()));require(len(rows)==baseline['ledger_prefix_rows']+23,'Ledger has extra/missing rows');added=rows[-23:];require(len(added)==23 and {r['asset_path']:r['sha256']for r in added}==receipt['packages'],'Exact23 current-hash candidate rows required');require(all(r['status']=='candidate'for r in added),'Premature asset approval');require(all(sha(root/r['asset_path'])==r['sha256']for r in rows),'Ledger current-hash mismatch')
 require(after['digest']!=before['digest'],'Data activation must be a new explicit epoch')
 return after,receipt

def verify_activated_readback(U,root,contract,guard,pixel_check,mesh_check,emit_receipt):
 """Fresh process, all Content RO; existing verifier core, no import/save or fake import receipt."""
 from shared_roof_native import preflight_native,verify_saved23_assets
 root=Path(root);guard();actual,receipt=validate_epoch(root);require(actual==contract,'Wrong postactivation contract');preflight_native(U,root,contract,guard)
 report=dict(passed=False,phase='activated23_saved_readback',contract_digest=contract['digest'],historical_contract_digest=receipt['contract_digest'],historical_readback_sha256=sha(root/DOC/'accepted-trial-readback.json'),packages=dict(receipt['packages']),textures=[],materials=[],meshes=[],imports=0,saves=0,production_package_overwrites=0,world_GPU_cook_validation='PENDING')
 try:
  verify_saved23_assets(U,root,contract,report,guard,pixel_check,mesh_check);validate_epoch(root);report['passed']=True;return report
 except BaseException as error:report['error']=repr(error);raise
 finally:emit_receipt(report)
if __name__=='__main__':raise RuntimeError('Root-reviewed postactivation readback only; never automatically mutates or launches')
