"""Source-only scope, refusal and save-order checks; no Unreal module required."""
from pathlib import Path
import copy,gc,re,sys,tempfile,types,unittest
from unittest.mock import patch
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'Scripts/RoofNative'))
import fireplace_contract as C
import fireplace_native as N
from fireplace_mesh_readback import decode_source,candidates

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
  self.assertEqual(c['source_blockers'],[])
  self.assertTrue(any('/FireplaceFiredClayV3/' in n for n in c['source_pins']))
  self.assertTrue(all(p.startswith('/Game/Dink/Refinements/FireplaceFiredClayV4/')for p in c['trial_packages']))
 def test_unused_source_slot_preserved(self):
  chimney=self.contract['meshes'][0]
  self.assertEqual(set(chimney['FBX_metadata']['unused_materials']),{'MI_Shared_FieldstoneSeed2m','MI_Shared_LimeMortar2m','MI_Shared_OakLonggrain2m'})
  self.assertEqual(len(chimney['material_slots']),6)
  self.assertEqual([len(r['material_slots'])for r in self.contract['meshes'][1:]],[5]*3)
 def test_four_actual_sources_have_representable_color_and_unique_geometry(self):
  for record in self.contract['meshes']:
   source,hulls=decode_source(P,record)
   self.assertEqual((len(source),len(hulls)),(record['triangles'],record['UCX']))
   self.assertTrue(all(corner['UV0']==corner['UVMap']and all(0<=v<=1 for v in corner['color'])for triangle in source for corner in triangle['corners']))
   matches=candidates(source,source,.0001)
   self.assertTrue(all(len(row)==1 for row in matches))
   self.assertEqual(len({row[0]['source_index']for row in matches}),len(source))
   del source,hulls,matches;gc.collect()
 def test_actual_role_f0_and_uv_semantics(self):
  for r in self.contract['materials']:
   expected=.35 if 'FiredClay' in r['source_material'] else .25 if 'Oak' in r['source_material'] else .5
   self.assertEqual(r['native_unreal_specular'],expected)
   self.assertEqual(r['uv1_semantic_decode'],'U,1-V')
   self.assertEqual(r['implicit_image_vector'],'UV0')
 def test_cpp_exact_filename_allowlist(self):
  source=(P/'Plugins/DinkImport/Source/DinkImport/Private/DinkRoofSourceMetadataLibrary.cpp').read_text().split('bool UDinkRoofSourceMetadataLibrary::SetFireplaceFiredClayV4SourceFilenamesRelative',1)[1]
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
 def test_recipe_mutation_with_unchanged_digest_refuses(self):
  c=copy.deepcopy(self.contract);c['materials'][0]['native_unreal_specular']=.5
  U=types.SimpleNamespace(Paths=types.SimpleNamespace(convert_relative_path_to_full=lambda x:x,project_dir=lambda:str(P)))
  with patch.object(N,'load_contract',return_value=self.contract):
   with self.assertRaisesRegex(ValueError,'recipe changed'):N.preflight(U,P,c,lambda:None)
 def test_symlinked_parent_refuses_fresh_target(self):
  with tempfile.TemporaryDirectory()as td:
   root=Path(td).resolve();foreign=root/'foreign';foreign.mkdir()
   content=root/'Content';content.symlink_to(foreign,target_is_directory=True)
   with self.assertRaisesRegex(ValueError,'Symlinked trial'):
    C.assert_trial_absent(root,dict(trial_packages={C.TRIAL+'Meshes/SM_Test':'StaticMesh'}))
   self.assertEqual(list(foreign.iterdir()),[])
 def test_dangling_target_symlink_refuses(self):
  with tempfile.TemporaryDirectory()as td:
   root=Path(td).resolve();package=C.TRIAL+'Meshes/SM_Test';target=C.trial_package_file(root,package)
   target.parent.mkdir(parents=True);target.symlink_to(root/'missing')
   with self.assertRaisesRegex(ValueError,'Symlinked trial'):C.trial_package_file(root,package)
 def test_normal_fresh_target_has_exact_bounded_path(self):
  with tempfile.TemporaryDirectory()as td:
   root=Path(td).resolve();package=C.TRIAL+'Meshes/SM_Test'
   self.assertEqual(C.trial_package_file(root,package),root/'Content/Dink/Refinements/FireplaceFiredClayV4/Meshes/SM_Test.uasset')
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
