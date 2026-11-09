"""Stand-alone source/material/recovery gates; no editor launches or repository assets."""
import hashlib,json,os,runpy,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
SCRIPTS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SCRIPTS))
import vista_import_support as support

class ReachedNextStage(RuntimeError):pass
class Material:
    def __init__(self,path):self.path=path
    def get_path_name(self):return self.path
class Instance:
    def __init__(self,path,parent):self.path=path;self.parent=parent
    def get_path_name(self):return self.path
    def get_editor_property(self,key):assert key=='parent';return self.parent
class Settings:
    def __init__(self,**overrides):self.values={'enabled':True,'fallback_target':'percent','fallback_percent_triangles':1.,'fallback_relative_error':0.,**overrides}
    def get_editor_property(self,key):return self.values[key]

class Fixture:
    def __init__(self,root):
        self.root=root;self.bundle=root/'Bundle';self.bundle.mkdir();files={};assets=[];new=[]
        def put(rel,data):
            path=self.bundle/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);files[rel]=support.sha(path)
        for i in range(55):
            name=f'SM_Vista_Test{i:02d}';fbx=f'Game/Test/{name}.fbx';glb=f'Game/Test/{name}.glb'
            put('Export/'+fbx,('fbx'+str(i)).encode());put('Export/'+glb,('glb'+str(i)).encode())
            assets.append({'name':name,'lod_count':1,'nanite':True,'content_path':(support.DEST_ROOTS[1] if i==54 else support.DEST)+'/'+name,'files':{'fbx':fbx,'glb':glb},'tris':{'LOD0':324 if i==54 else 320}})
            new.append({'name':name,'existing_UE_material':'/Game/Dink/Materials/Test/MI_Fieldstone' if i==54 else '/Game/Dink/Materials/Test/MI_Meadow'})
        put('Export/manifest.json',json.dumps({'assets':assets}).encode())
        proposal={'new_meshes':new,'instances':[{'asset_path_proposal':'/Game/Dink/Shared/Shared.Shared'} for _ in range(316)]}
        put('placement_proposal.json',json.dumps(proposal).encode())
        for i in range(139-len(files)):put(f'other/file{i}',('source'+str(i)).encode())
        (self.bundle/'bundle_manifest.json').write_text(json.dumps({'files':files}));self.anchor=support.sha(self.bundle/'bundle_manifest.json');self.assets=assets
        self.project=root/'Project';self.project.mkdir();(self.project/'SourceAssets').mkdir();(self.project/'SourceAssets/asset_ledger.csv').write_bytes(b'unchanged-ledger')
        for branch in ['Kits','Materials','Foliage','Data/Art']:(self.project/'Content/Dink'/branch).mkdir(parents=True)
        for reference in ['/Game/Dink/Shared/Shared.Shared','/Game/Dink/Materials/Test/MI_Fieldstone','/Game/Dink/Materials/Test/MI_Meadow']:
            path=support.asset_file(self.project,reference);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'shared-read-only-fixture')
        self.dest=self.project/'Content/Dink/Kits/Stonebrook/InteriorVista'
    def fake(self,exists=False,usage=True):
        state={'usage':[],'writes':0};u=types.ModuleType('unreal');base=Material('/Game/Materials/M_Surface')
        mats={name:Instance(name,Instance(name+'_Parent',base)) for name in ['/Game/Dink/Materials/Test/MI_Fieldstone','/Game/Dink/Materials/Test/MI_Meadow']}
        class Mesh:pass
        def load(path):
            if path in mats:return mats[path]
            if any(path.startswith(prefix+'/') for prefix in support.DEST_ROOTS):raise ReachedNextStage('check mesh validation reached')
            return Mesh()
        def has(mat,flag):
            if not isinstance(mat,Material):raise TypeError('base Material required')
            state['usage'].append(mat.get_path_name());return usage
        def mutate(*a,**k):state['writes']+=1;raise AssertionError('unexpected package write')
        u.Paths=types.SimpleNamespace(project_dir=lambda:str(self.project),convert_relative_path_to_full=lambda s:s)
        u.SystemLibrary=types.SimpleNamespace(get_command_line=lambda:'-run=pythonscript',execute_console_command=lambda *a:(_ for _ in ()).throw(ReachedNextStage('import reached after preflight')))
        u.Material=Material;u.StaticMesh=Mesh;u.MaterialUsage=types.SimpleNamespace(MATUSAGE_NANITE='nanite')
        u.EditorAssetLibrary=types.SimpleNamespace(does_directory_exist=lambda p:exists,load_asset=load,save_loaded_asset=mutate)
        u.MaterialEditingLibrary=types.SimpleNamespace(has_material_usage=has)
        u.AssetToolsHelpers=types.SimpleNamespace(get_asset_tools=lambda:types.SimpleNamespace(import_asset_tasks=mutate))
        u.StaticMeshEditorSubsystem=object();u.UnrealEditorSubsystem=object();u.get_editor_subsystem=lambda t:types.SimpleNamespace(get_editor_world=lambda:None)
        return u,state

class VistaImportTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.f=Fixture(Path(self.temp.name))
    def run_entry(self,mode,unreal):
        original=support.validate_bundle
        with patch.dict(sys.modules,{'unreal':unreal}),patch.dict(os.environ,{'DINK_VISTA_SOURCE':str(self.f.bundle),'DINK_VISTA_MODE':mode}),patch.object(support,'validate_bundle',lambda p:original(p,self.f.anchor)):
            runpy.run_path(str(SCRIPTS/'import_stonebrook_vista.py'),run_name='__main__')
    def test_valid_139_file_source(self):
        spec,p,h=support.validate_bundle(self.f.bundle,self.f.anchor);self.assertEqual((len(spec['assets']),len(p['instances'])),(55,316))
    def test_changed_payload_and_manifest_stop_before_editor_writes(self):
        for path in [self.f.bundle/'Export/Game/Test/SM_Vista_Test00.fbx',self.f.bundle/'other/file0',self.f.bundle/'bundle_manifest.json']:
            original=path.read_bytes();path.write_bytes(original+b'tampered');u,state=self.f.fake()
            try:
                with self.assertRaises(ValueError):self.run_entry('import',u)
                self.assertEqual(state['writes'],0);self.assertEqual(state['usage'],[]);self.assertFalse(self.f.dest.exists())
            finally:path.write_bytes(original)
    def test_instance_chain_resolves_read_only_to_base(self):
        base=Material('base');instance=Instance('child',Instance('parent',base));actual,chain=support.resolve_base_material(instance,Material)
        self.assertIs(actual,base);self.assertEqual(chain,['child','parent','base'])
    def test_new_step_props_path_is_not_misclassified_as_shared(self):
        p=self.f.bundle/'placement_proposal.json';data=json.loads(p.read_text());asset=self.f.assets[-1]
        data['instances'][0]['asset_path_proposal']=asset['content_path']+'.'+asset['name'];p.write_text(json.dumps(data))
        manifest_path=self.f.bundle/'bundle_manifest.json';manifest=json.loads(manifest_path.read_text());manifest['files']['placement_proposal.json']=support.sha(p);manifest_path.write_text(json.dumps(manifest));self.f.anchor=support.sha(manifest_path)
        u,state=self.f.fake();original_load=u.EditorAssetLibrary.load_asset
        def guarded(path):
            if path==asset['content_path']+'.'+asset['name']:raise AssertionError('new doorstep must not be loaded as shared before import')
            return original_load(path)
        u.EditorAssetLibrary.load_asset=guarded
        with self.assertRaises(ReachedNextStage):self.run_entry('import',u)
        self.assertEqual(state['writes'],0)
        self.assertEqual(support.package_file(self.f.project,asset),self.f.project/'Content/Dink/Props/Stonebrook/InteriorVista'/f'{asset["name"]}.uasset')
    def test_missing_parent_and_cycle_rejected(self):
        for instance in [Instance('missing',None),Instance('cycle',None)]:
            if instance.path=='cycle':instance.parent=instance
            with self.assertRaises(ValueError):support.resolve_base_material(instance,Material)
    def test_import_and_check_require_base_usage_before_next_stage(self):
        for mode in ['import','check']:
            u,state=self.f.fake(exists=mode=='check')
            with self.assertRaises(ReachedNextStage):self.run_entry(mode,u)
            self.assertEqual(state['usage'],['/Game/Materials/M_Surface']*2);self.assertEqual(state['writes'],0)
    def test_import_and_check_missing_usage_stop_read_only(self):
        for mode in ['import','check']:
            u,state=self.f.fake(exists=mode=='check',usage=False)
            with self.assertRaisesRegex(ValueError,'lacks required Nanite usage'):self.run_entry(mode,u)
            self.assertEqual(state['writes'],0)
    def test_commandlet_static_mesh_subsystem_uses_default_object(self):
        u,state=self.f.fake();fallback=types.SimpleNamespace();seen=[];prior=u.get_editor_subsystem
        u.get_editor_subsystem=lambda cls:None if cls is u.StaticMeshEditorSubsystem else prior(cls)
        u.get_default_object=lambda cls:(seen.append(cls) or fallback)
        with self.assertRaises(ReachedNextStage):self.run_entry('import',u)
        self.assertEqual(seen,[u.StaticMeshEditorSubsystem]);self.assertEqual(state['writes'],0)
    def test_numeric_policy_and_actual_nanite_geometry(self):
        support.render_policy(Settings(),'percent',320,320)
        for settings,count in [(Settings(fallback_percent_triangles=.5),320),(Settings(fallback_relative_error=.2),320),(Settings(fallback_relative_error=float('nan')),320),(Settings(enabled=False),320),(Settings(fallback_target='auto'),320),(Settings(),100)]:
            with self.assertRaises(ValueError):support.render_policy(settings,'percent',320,count)
    def test_resume_published_context_rejected_before_backup(self):
        (self.f.project/'Content/Dink/Data/Art/vista.json').write_text(json.dumps({'mesh':support.DEST.upper()+'/SM_Vista_Test00'}));u,state=self.f.fake(exists=True)
        with self.assertRaisesRegex(ValueError,'published Vista'):self.run_entry('resume',u)
        self.assertEqual(state['writes'],0);self.assertFalse((self.f.project/'Saved/Art/VistaResumeBackups').exists())
    def test_partial_resume_backs_up_known_only_preserves_foreign(self):
        self.f.dest.mkdir(parents=True);owned=self.f.dest/'SM_Vista_Test00.uasset';owned.write_bytes(b'partial');foreign=self.f.dest/'Foreign.uasset';foreign.write_bytes(b'foreign')
        u,state=self.f.fake(exists=True)
        with self.assertRaises(ReachedNextStage):self.run_entry('resume',u)
        backups=list((self.f.project/'Saved/Art/VistaResumeBackups').glob('*/SM_Vista_Test00.uasset'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),b'partial')
        self.assertEqual(owned.read_bytes(),b'partial');self.assertEqual(foreign.read_bytes(),b'foreign');self.assertFalse((backups[0].parent/'Foreign.uasset').exists());self.assertEqual(state['writes'],0)
    def test_known_meadow_reference_uses_original_shared_folder(self):
        proposed='/Game/Dink/Materials/StonebrookExterior/MI_Stonebrook_Meadow.MI_Stonebrook_Meadow'
        actual=support.material_reference(proposed)
        self.assertEqual(actual,'/Game/Dink/Materials/Stonebrook/MI_Stonebrook_Meadow.MI_Stonebrook_Meadow')
        self.assertEqual(support.asset_file(self.f.project,actual),self.f.project/'Content/Dink/Materials/Stonebrook/MI_Stonebrook_Meadow.uasset')
        fieldstone='/Game/Dink/Materials/Stonebrook/MI_Stonebrook_Fieldstone.MI_Stonebrook_Fieldstone'
        self.assertEqual(support.material_reference(fieldstone),fieldstone)
    def test_check_and_existing_import_policy(self):
        self.assertEqual(support.action('check',True,True),'check')
        with self.assertRaises(ValueError):support.action('import',True,False)
        with self.assertRaises(ValueError):support.action('check',False,False)

if __name__=='__main__':unittest.main()
