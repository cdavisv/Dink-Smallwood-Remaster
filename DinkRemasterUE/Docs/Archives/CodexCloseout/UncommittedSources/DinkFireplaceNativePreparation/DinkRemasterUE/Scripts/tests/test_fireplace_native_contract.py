"""Source-only scope, refusal and save-order checks; no Unreal module required."""
from pathlib import Path
import copy,re,sys,types,unittest
from unittest.mock import patch
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'Scripts/RoofNative'))
import fireplace_contract as C
import fireplace_native as N

class FireplaceContractTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.contract=C.load_contract(P)
 def test_actual_closed_scope(self):
  c=self.contract
  self.assertEqual((len(c['meshes']),len(c['materials']),len(c['textures']),len(c['trial_packages'])),(4,7,24,35))
  self.assertEqual([r['triangles']for r in c['meshes']],[1486,57296,37908,19998])
  self.assertEqual([r['UCX']for r in c['meshes']],[92,16,0,0])
  self.assertFalse(c['production_activated']);self.assertTrue(c['native_review_required'])
  self.assertIn('SourceAssets/asset_ledger.csv',c['source_pins'])
 def test_unused_source_slot_preserved(self):
  chimney=self.contract['meshes'][0]
  self.assertEqual(set(chimney['FBX_metadata']['unused_materials']),{'MI_Shared_FieldstoneSeed2m','MI_Shared_LimeMortar2m','MI_Shared_OakLonggrain2m'})
  self.assertEqual(len(chimney['material_slots']),6)
  self.assertEqual([len(r['material_slots'])for r in self.contract['meshes'][1:]],[5]*3)
 def test_actual_role_f0_and_uv_semantics(self):
  for r in self.contract['materials']:
   expected=.35 if 'FiredClay' in r['source_material'] else .25 if 'Oak' in r['source_material'] else .5
   self.assertEqual(r['native_unreal_specular'],expected)
   self.assertEqual(r['uv1_semantic_decode'],'U,1-V')
   self.assertEqual(r['implicit_image_vector'],'UV0')
 def test_cpp_exact_filename_allowlist(self):
  source=(P/'Plugins/DinkImport/Source/DinkImport/Private/DinkRoofSourceMetadataLibrary.cpp').read_text().split('bool UDinkRoofSourceMetadataLibrary::SetFireplaceFiredClaySourceFilenamesRelative',1)[1]
  entries=dict(re.findall(r'\{TEXT\("([^"\n]+)"\),TEXT\("([^"\n]+)"\)\}',source))
  expected={r['name']:str(C.SOURCE/r['file'])for r in self.contract['meshes']}
  expected.update({Path(r['source_file']).stem:r['source_file']for r in self.contract['textures']})
  self.assertEqual(entries,expected)
  self.assertIn('TEXT("'+C.TRIAL+'")',source)
 def test_hdr_source_refuses_before_any_engine_access(self):
  c=copy.deepcopy(self.contract);c['source_blockers']=[{'reason':'synthetic HDR'}]
  with self.assertRaisesRegex(ValueError,'Source Color0 clipping'):N.preflight(object(),P,c,lambda:self.fail('guard reached'))
 def test_old_dll_refuses_before_import(self):
  c=copy.deepcopy(self.contract);c['source_blockers']=[]
  U=types.SimpleNamespace(Paths=types.SimpleNamespace(convert_relative_path_to_full=lambda x:x,project_dir=lambda:str(P)),SystemLibrary=types.SimpleNamespace(get_command_line=lambda:'',get_console_variable_int_value=lambda key:0))
  with patch.object(N,'load_contract',return_value=c):
   with self.assertRaisesRegex(ValueError,'not compiled'):N.preflight(U,P,c,lambda:None)
 def test_metadata_before_verify_before_save(self):
  events=[];record=dict(triangles=4,UCX=0)
  def metadata(*a):events.append('metadata')
  def verify(*a):
   events.append('verify');return dict(passed=True,triangles=4,UCX=0,source_correspondence_passed=True,raw_Color0_import_passed=True,normal_tangent_basis='UV0')
  N.checked_mesh_before_save(object(),record,metadata,verify,lambda m:events.append('save'))
  self.assertEqual(events,['metadata','verify','save'])
 def test_failed_geometry_never_saves(self):
  with self.assertRaises(ValueError):N.checked_mesh_before_save(object(),{},lambda *a:None,lambda *a:dict(passed=False),lambda m:self.fail('saved failed geometry'))
 def test_missing_root_approval_never_calls_engine(self):
  with self.assertRaisesRegex(ValueError,'Root source/F0/pivot'):
   N.import_trial(object(),P,self.contract,{},*[lambda *a:None]*6)

if __name__=='__main__':unittest.main()
