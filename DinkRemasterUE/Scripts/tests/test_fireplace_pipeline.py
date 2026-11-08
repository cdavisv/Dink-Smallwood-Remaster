"""Stdlib tests: temporary raw assets, real production guard/entry scripts, recording Unreal fake.
Does not load Unreal, modify repository assets or assume a binary storage provider.
"""
import csv,hashlib,json,os,runpy,shutil,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
SCRIPTS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SCRIPTS))
from fireplace_source import validate_source_inputs,validate_render_policy,import_action

class AssetWriteAttempt(RuntimeError):pass
class Fixture:
 def __init__(self,root):
  self.root=root;self.source=root/'SourceAssets/Art/Stonebrook/Refinements/FireplaceV2';self.source.mkdir(parents=True)
  self.name='SM_Fireplace_Stonebrook_V2';self.paths=[]
  def put(rel,data):
   p=self.source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);self.paths.append(p);return p
  self.blend=put(self.name+'.blend',b'approved-blend')
  self.png=put('Textures/T_FireplaceV2_Atlas_BC.png',b'approved-BC')
  for kind in ['N','ORM','E']:put('Textures/T_FireplaceV2_Atlas_'+kind+'.png',('approved-'+kind).encode())
  for i in range(3):put('Export/SingleLODs/'+self.name+'_LOD'+str(i)+'.fbx',('approved-LOD'+str(i)).encode())
  self.fbx=self.source/'Export/SingleLODs'/f'{self.name}_LOD1.fbx'
  spec={'name':self.name,'textures':{k:f'Textures/T_FireplaceV2_Atlas_{k}.png' for k in ['BC','N','ORM','E']}}
  (self.source/'candidate_manifest.json').write_text(json.dumps(spec))
  blend_sha=hashlib.sha256(self.blend.read_bytes()).hexdigest()
  self.plan={'schema':'dink-fireplace-refinement/1','source_blend':str(self.blend.relative_to(root)),'source_blend_sha256':blend_sha,'source_export':str((self.source/'Export/manifest.json').relative_to(root)),'mesh':self.name,'destination':'/Game/Dink/Refinements/FireplaceV2','runtime_file':'stonebrook_refinement_fireplace_v2.json','render_policy':{'fallback_percent_triangles':1.,'fallback_relative_error':0.}}
  self.planpath=put('placement_plan.json',json.dumps(self.plan).encode())
  (self.source/'Export/manifest.json').write_text(json.dumps({'assets':[{'name':self.name,'source':{'sha256':blend_sha},'nanite':True}]}))
  with (root/'SourceAssets/asset_ledger.csv').open('w',newline='') as stream:
   w=csv.DictWriter(stream,fieldnames=['asset_path','sha256']);w.writeheader()
   for p in self.paths:w.writerow({'asset_path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  scripts=root/'Scripts';scripts.mkdir();shutil.copy2(SCRIPTS/'fireplace_source.py',scripts/'fireplace_source.py')
  for branch in ['Kits','Materials','Data/Art']:(root/'Content/Dink'/branch).mkdir(parents=True)
 def fake_unreal(self,exists=False):
  state={'asset_writes':0};u=types.ModuleType('unreal')
  def write(*args,**kwargs):state['asset_writes']+=1;raise AssetWriteAttempt('recorded create_asset call')
  u.Paths=types.SimpleNamespace(project_dir=lambda:str(self.root),convert_relative_path_to_full=lambda s:s)
  u.SystemLibrary=types.SimpleNamespace(get_command_line=lambda:'-run=pythonscript',execute_console_command=lambda *a:None,get_console_variable_int_value=lambda n:0)
  u.EditorAssetLibrary=types.SimpleNamespace(does_directory_exist=lambda d:exists,load_asset=lambda p:None)
  u.MaterialEditingLibrary=types.SimpleNamespace();u.AssetToolsHelpers=types.SimpleNamespace(get_asset_tools=lambda:types.SimpleNamespace(create_asset=write))
  u.UnrealEditorSubsystem=object;u.get_editor_subsystem=lambda t:types.SimpleNamespace(get_editor_world=lambda:None)
  u.Material=type('Material',(),{});u.MaterialFactoryNew=lambda:None
  return u,state

class FireplacePipelineTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.f=Fixture(Path(self.temp.name))
 def test_valid_materialized_sources(self):
  plan,spec,hashes=validate_source_inputs(self.f.root);self.assertEqual(len(hashes),8);self.assertEqual(plan['mesh'],self.f.name)
 def test_modified_png_fbx_and_plan_stop_entry_before_asset_write(self):
  for path in [self.f.png,self.f.fbx,self.f.planpath]:
   original=path.read_bytes();path.write_bytes(original+b'tampered');u,state=self.f.fake_unreal()
   try:
    with patch.dict(sys.modules,{'unreal':u}),patch.dict(os.environ,{'DINK_FIREPLACE_MODE':'import'}):
     with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):runpy.run_path(str(SCRIPTS/'import_fireplace_refinement.py'),run_name='__main__')
    self.assertEqual(state['asset_writes'],0);self.assertFalse((self.f.root/'Content/Dink/Refinements').exists())
   finally:path.write_bytes(original)
 def test_missing_raw_source_and_pointer_are_rejected(self):
  self.f.png.unlink()
  with self.assertRaisesRegex(ValueError,'Missing source bytes'):validate_source_inputs(self.f.root)
  self.f.png.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:'+'a'*64+'\nsize 20\n')
  with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):validate_source_inputs(self.f.root)
 def test_unpublished_resume_backs_up_only_owned_package_before_write(self):
  dest=self.f.root/'Content/Dink/Refinements/FireplaceV2';dest.mkdir(parents=True)
  partial=dest/'M_FireplaceV2_Atlas.uasset';partial.write_bytes(b'partial-material')
  foreign=dest/'ForeignReview.uasset';foreign.write_bytes(b'keep-foreign')
  u,state=self.f.fake_unreal(exists=True)
  with patch.dict(sys.modules,{'unreal':u}),patch.dict(os.environ,{'DINK_FIREPLACE_MODE':'resume'}):
   with self.assertRaises(AssetWriteAttempt):runpy.run_path(str(SCRIPTS/'import_fireplace_refinement.py'),run_name='__main__')
  copies=list((self.f.root/'Saved/Art/FireplaceResumeBackups').glob('*/M_FireplaceV2_Atlas.uasset'))
  self.assertEqual(len(copies),1);self.assertEqual(copies[0].read_bytes(),b'partial-material');self.assertEqual(foreign.read_bytes(),b'keep-foreign')
  self.assertEqual(state['asset_writes'],1);self.assertEqual(partial.read_bytes(),b'partial-material')
 def test_resume_published_candidate_rejected_before_backup_or_write(self):
  runtime=self.f.root/'Content/Dink/Data/Art'/self.f.plan['runtime_file'];runtime.write_text('{}')
  u,state=self.f.fake_unreal(exists=True)
  with patch.dict(sys.modules,{'unreal':u}),patch.dict(os.environ,{'DINK_FIREPLACE_MODE':'resume'}):
   with self.assertRaisesRegex(ValueError,'published candidate'):runpy.run_path(str(SCRIPTS/'import_fireplace_refinement.py'),run_name='__main__')
  self.assertEqual(state['asset_writes'],0);self.assertFalse((self.f.root/'Saved/Art/FireplaceResumeBackups').exists());self.assertEqual(runtime.read_text(),'{}')
 def test_mode_policy_keeps_normal_existing_import_and_check_read_only(self):
  self.assertEqual(import_action('import',True,True),'check');self.assertEqual(import_action('check',True,False),'check')
  self.assertEqual(import_action('import',False,False),'create');self.assertEqual(import_action('resume',True,False),'resume')
  with self.assertRaises(ValueError):import_action('check',False,False)
  # Run the real import entry's check branch with a recording asset factory.
  marker=self.f.root/'Saved/check_only_reached';(self.f.root/'Scripts/inspect_fireplace_refinement.py').write_text("assert mode=='check' and action=='check'\n(ROOT/'Saved').mkdir(exist_ok=True)\n(ROOT/'Saved/check_only_reached').write_text('checked')\n")
  original=self.f.root/'Content/Dink/Kits/Original.uasset';original.write_bytes(b'keep-original')
  before={str(p.relative_to(self.f.root)):p.read_bytes() for p in (self.f.root/'Content').rglob('*') if p.is_file()}
  u,state=self.f.fake_unreal(exists=True)
  with patch.dict(sys.modules,{'unreal':u}),patch.dict(os.environ,{'DINK_FIREPLACE_MODE':'check'}):runpy.run_path(str(SCRIPTS/'import_fireplace_refinement.py'),run_name='__main__')
  self.assertTrue(marker.exists());self.assertEqual(state['asset_writes'],0)
  self.assertEqual(before,{str(p.relative_to(self.f.root)):p.read_bytes() for p in (self.f.root/'Content').rglob('*') if p.is_file()})
 def test_render_policy_rejects_fraction_error_and_nonfinite(self):
  policy=self.f.plan['render_policy'];validate_render_policy(1,0,policy)
  for percent,error in [(.5,0),(1,.1),(float('nan'),0),(1,float('inf'))]:
   with self.assertRaises(ValueError):validate_render_policy(percent,error,policy)
 def test_inspector_checks_fraction_before_publication(self):
  u,state=self.f.fake_unreal(True);mesh_type=type('StaticMesh',(),{});mesh=mesh_type();u.StaticMesh=mesh_type
  pct=object();simple=object();u.NaniteFallbackTarget=types.SimpleNamespace(PERCENT_TRIANGLES=pct);u.CollisionTraceFlag=types.SimpleNamespace(CTF_USE_SIMPLE_AS_COMPLEX=simple)
  settings={'enabled':True,'fallback_target':pct,'fallback_percent_triangles':.5,'fallback_relative_error':0.}
  mesh.get_editor_property=lambda name:types.SimpleNamespace(get_editor_property=lambda key:settings[key]) if name=='nanite_settings' else types.SimpleNamespace(get_editor_property=lambda key:simple)
  mesh.get_num_triangles=lambda i:[15484,8050,4180][i];u.load_asset=lambda p:mesh
  u.StaticMeshEditorSubsystem=object;u.get_editor_subsystem=lambda t:types.SimpleNamespace(get_lod_count=lambda m:3,get_convex_collision_count=lambda m:6)
  with patch.dict(sys.modules,{'unreal':u}),patch.dict(os.environ,{'DINK_FIREPLACE_MODE':'publish'}):
   with self.assertRaisesRegex(ValueError,'fallback_percent_triangles'):runpy.run_path(str(SCRIPTS/'inspect_fireplace_refinement.py'),run_name='__main__')
  self.assertFalse((self.f.root/'Content/Dink/Data/Art'/self.f.plan['runtime_file']).exists());self.assertEqual(state['asset_writes'],0)

if __name__=='__main__':unittest.main()
