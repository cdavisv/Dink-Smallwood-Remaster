import unittest,json,copy,gzip,sys,tempfile,hashlib,ast
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True;sys.path.insert(0,str(Path(__file__).parent))
from canonical_contract import load,NAMESPACE
from relative_source_metadata import validate_snapshot
from native_import_sequence_v12 import validate_inputs
from native_asset_readback_v12 import source_hull_clouds
import native_texture_tools_v11 as T,native_mesh_tools_v11c as M
P=Path(__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.proposal,cls.recipe,cls.binding=load(P)
 def test_source100_37_50_contract(self):
  result=validate_inputs(P,self.proposal,self.recipe,self.binding,dict(enabled=True,fallback_target=1,fallback_percent_triangles=1.,fallback_relative_error=0.));self.assertEqual(result['UCX'],312)
 def test_actual_typed_UCX_312(self):
  source=json.loads(gzip.decompress(Path(self.binding['source_reference']).read_bytes()));manifest=json.loads((Path(self.binding['source_packet'])/'export_manifest.json').read_text());total=0
  for row in manifest['FBX']:
   if row['matched_UCX']:total+=len(source_hull_clouds(source,row['source_object']))
  self.assertEqual(total,312)
 def test_canonical_low_level_guards_before_first_native(self):
  class Boundary(Exception):pass
  calls=[]
  def boundary(*a):calls.append(a);raise Boundary()
  U=SimpleNamespace(EditorAssetLibrary=SimpleNamespace(does_asset_exist=boundary),SystemLibrary=SimpleNamespace(get_console_variable_int_value=boundary))
  with tempfile.TemporaryDirectory()as td:
   source=Path(td)/'source';source.write_bytes(b'guard fixture');digest=hashlib.sha256(source.read_bytes()).hexdigest()
   for a in self.proposal['packages']:
    if a['kind']=='Material':continue
    def invoke(target):
     if a['kind']=='Texture2D':return T.import_new(U,source,dict(package=target,source_sha256=digest),lambda:None)
     return M.import_base(U,td,dict(file='source',sha256=digest),target,lambda:None)
    with self.assertRaises(Boundary):invoke(a['package'])
    for prefix in ['/Game/Dink/QA/IndoorRoofV12','/Game/Dink/QA/IndoorRoofV8','/Game/Dink/Refinements/Other']:
     before=len(calls)
     with self.assertRaises(RuntimeError):invoke(a['package'].replace(NAMESPACE,prefix))
     self.assertEqual(len(calls),before)
 def test_all3_LODs_rawrelative_and_relocated_snapshots(self):
  for root in ['/tmp/clone-one/source','/tmp/different/clone-two/source']:
   files=[str(Path(root)/f'FBX/LOD{i}.fbx')for i in range(3)];row=lambda i:dict(stored=f'../../source/LOD{i}.fbx',relative=True,resolved=files[i]);data=dict(schema='dink-roof-source-filenames/1',valid=True,asset='/Owned.Mesh',files=[row(0)],LODs=[dict(LOD=i,**row(i))for i in range(3)]);validate_snapshot(data,'/Owned.Mesh',files,True)
   for lod in range(3):
    bad=copy.deepcopy(data);bad['LODs'][lod]['stored']=files[lod]
    with self.assertRaises(ValueError):validate_snapshot(bad,'/Owned.Mesh',files,True)
    bad=copy.deepcopy(data);bad['LODs'][lod]['resolved']=files[(lod+1)%3]
    with self.assertRaises(ValueError):validate_snapshot(bad,'/Owned.Mesh',files,True)
   bad=copy.deepcopy(data);bad['files'][0]['stored']=files[0]
   with self.assertRaises(ValueError):validate_snapshot(bad,'/Owned.Mesh',files,True)
 def test_texture_rawrelative_without_hidden_LODs(self):
  files=['/tmp/cold-clone/Textures/test.png'];data=dict(schema='dink-roof-source-filenames/1',valid=True,asset='/Owned.Texture',files=[dict(stored='../../Textures/test.png',relative=True,resolved=files[0])],LODs=[]);validate_snapshot(data,'/Owned.Texture',files,False)
  data['files'][0]['relative']=False
  with self.assertRaises(ValueError):validate_snapshot(data,'/Owned.Texture',files,False)
 def test_readback_requires_exact_import_receipt(self):
  with self.assertRaises(AssertionError):load(P,'readback')
 def test_metadata_fixture_never_constructs_canonical_packages(self):
  cpp=(P/'Plugins/DinkImport/Source/DinkImport/Private/Tests/DinkRoofSourceMetadataTests.cpp').read_text();header=(P/'Plugins/DinkImport/Source/DinkImport/Public/DinkRoofSourceMetadataLibrary.h').read_text();impl=(P/'Plugins/DinkImport/Source/DinkImport/Private/DinkRoofSourceMetadataLibrary.cpp').read_text()
  self.assertNotIn('/Game/Dink/Refinements/',cpp);self.assertIn('/Game/DinkQA/TransientRoofMetadata_',cpp);self.assertIn('FGuid::NewGuid()',cpp)
  self.assertIn('private:',header);self.assertLess(header.index('private:'),header.index('static bool ApplyFilenameTransaction'));self.assertIn('friend class FDinkRoofSourceMetadataTest;',header)
  self.assertIn('FPackageName::DoesPackageExist(Package)',impl);self.assertIn('public canonical setter refuses scratch scope',cpp);self.assertIn('public texture setter refuses scratch scope',cpp)
 def test_all_helpers_parse_no_native_import(self):
  for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text())
if __name__=='__main__':unittest.main()
