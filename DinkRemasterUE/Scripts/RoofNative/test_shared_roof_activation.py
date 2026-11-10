import copy,json,sys,unittest
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
sys.dont_write_bytecode=True;sys.path.insert(0,str(Path(__file__).parent))
import shared_roof_activation as A,shared_roof_native as N
from shared_roof_contract import require
P=Path(__file__).resolve().parents[2]
@contextmanager
def changed(path,value):
 old=path.read_bytes()
 try:path.write_bytes(value);yield
 finally:path.write_bytes(old)
class ActivationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=A.read(P,'before-contract.json');cls.data=A.read(P,'before-data.json')
 def test_actual_current_epoch_and_original_digest_distinct(self):
  after,receipt=A.validate_epoch(P);self.assertNotEqual(after['digest'],self.before['digest']);self.assertEqual(receipt['contract_digest'],self.before['digest']);self.assertEqual(receipt['phase'],'fresh23_saved_readback')
 def test_exact_eight_meshes_and_three_aliases_only(self):
  after=A.expected_data(self.data,self.before);rest=copy.deepcopy(after)
  for a,b in zip(self.data[A.HOUSE]['elements'],rest[A.HOUSE]['elements']):
   if a.get('mesh')!=b.get('mesh'):self.assertIn(a['mesh'].split('.')[-1],A.NAMES);b['mesh']=a['mesh']
  for key in self.before['camera_aliases']:del rest[A.CAMERA]['material_variants'][key]
  self.assertEqual(rest,self.data);self.assertEqual(after[A.CAMERA]['floor_framing'],self.data[A.CAMERA]['floor_framing'])
 def test_transform_or_collision_delta_refused(self):
  p=P/A.HOUSE;d=json.loads(p.read_text());d['elements'][-1]['collision']=not d['elements'][-1]['collision']
  with changed(p,json.dumps(d).encode()):self.assertRaisesRegex(ValueError,'Unexpected Data semantic delta',A.validate_epoch,P)
 def test_other_data_membership_refused(self):
  p=P/'Content/Dink/Data/unauthorized_activation_test.json';self.assertFalse(p.exists())
  try:p.write_text('{}');self.assertRaisesRegex(ValueError,'Data membership',A.validate_epoch,P)
  finally:p.unlink()
 def test_frozen_manifest_readme_checksums_untouched(self):
  before=A.read(P,'before-source-metadata.json')
  for name,text in before.items():self.assertEqual((P/A.SOURCE/name).read_bytes(),text.encode())
 def test_any_extra_mapping_file_refused(self):
  p=P/A.DELIVERY/'unauthorized.json';self.assertFalse(p.exists())
  try:p.write_text('{}');self.assertRaisesRegex(ValueError,'Unexpected delivery mapping addition',A.validate_epoch,P)
  finally:p.unlink()
 def test_old_source_geometry_hash_fault_refused(self):
  original=A.sha;target=str(A.SOURCE/'FBX/SM_IndoorRoof_EN_01.fbx')
  with patch.object(A,'sha',side_effect=lambda p:'BAD'if str(p).endswith(target)else original(p)):self.assertRaisesRegex(ValueError,'Frozen source changed',A.validate_epoch,P)
 def test_existing_ledger_prefix_change_refused(self):
  p=P/'SourceAssets/asset_ledger.csv';data=p.read_bytes()
  with changed(p,data.replace(b'candidate',b'candidatX',1)):self.assertRaisesRegex(ValueError,'ledger raw prefix',A.validate_epoch,P)
 def test_extra_row_before_last23_refused(self):
  p=P/'SourceAssets/asset_ledger.csv';raw=p.read_bytes();prefix=A.read(P,'baseline.json')['ledger_prefix_bytes'];suffix=raw[prefix:];extra=suffix.splitlines(keepends=True)[0]
  with changed(p,raw[:prefix]+extra+suffix):self.assertRaisesRegex(ValueError,'ledger suffix|extra/missing rows',A.validate_epoch,P)
 def test_reviewed_helper_delta_fault_refused(self):
  original=A.sha
  with patch.object(A,'sha',side_effect=lambda p:'BAD'if str(p).endswith('shared_roof_entry_template.py')else original(p)):self.assertRaisesRegex(ValueError,'helper source delta',A.validate_epoch,P)
 def test_old_trial_contract_still_refuses_new_epoch(self):
  from types import SimpleNamespace
  u=SimpleNamespace(Paths=SimpleNamespace(project_dir=lambda:str(P),convert_relative_path_to_full=lambda p:p))
  self.assertRaisesRegex(ValueError,'Source/Data/native preimages changed',N.preflight_native,u,P,self.before,lambda:None)
 def test_new_readback_reuses_saved23_core_without_faking_import(self):
  after,receipt=A.validate_epoch(P);emitted=[];events=[]
  def core(u,root,contract,report,guard,pixels,mesh):
   self.assertEqual(report['phase'],'activated23_saved_readback');self.assertEqual(report['packages'],receipt['packages']);self.assertEqual(report['imports'],0);self.assertEqual(report['saves'],0);events.append('actual-core-boundary')
  with patch.object(N,'preflight_native'),patch.object(N,'verify_saved23_assets',side_effect=core):result=A.verify_activated_readback(None,P,after,lambda:None,None,None,emitted.append)
  self.assertTrue(result['passed']);self.assertEqual(events,['actual-core-boundary']);self.assertEqual(emitted[-1]['historical_contract_digest'],receipt['contract_digest']);self.assertEqual(receipt['phase'],'fresh23_saved_readback')
if __name__=='__main__':unittest.main()
