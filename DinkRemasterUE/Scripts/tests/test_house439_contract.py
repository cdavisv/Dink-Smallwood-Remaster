"""Exercise actual registered cottage/library bytes in isolated copied source trees."""
from pathlib import Path
import importlib.util,sys,unittest,tempfile,shutil,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Scripts/RoofNative'))
import house439_contract as c
class CottageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='dink-house439-contract-');cls.root=Path(cls.temp.name).resolve()
        for folder in (c.SOURCE,c.LIBRARY):shutil.copytree(ROOT/folder,cls.root/folder)
        for relative in c.IMPORTER_FILES:
            p=cls.root/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,p)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_real_source_fresh38_and_unapproved(self):
        r=c.load_contract(self.root);c.assert_trial_absent(self.root,r)
        self.assertEqual((len(r['textures']),len(r['materials']),len(r['meshes']),len(r['trial_packages'])),(30,7,1,38))
        self.assertFalse(r['production_activated'])
        for recipe in r['materials']:
            self.assertFalse(recipe.get('source_graph_reviewed',recipe.get('native_policy_reviewed')))
    def test_importer_change_invalidates_review_digest(self):
        before=c.load_contract(self.root)['digest'];p=self.root/'Scripts/RoofNative/house439_native.py';data=p.read_bytes()
        try:
            p.write_bytes(data+b'\n# changed after review\n');self.assertNotEqual(before,c.load_contract(self.root)['digest'])
        finally:p.write_bytes(data)
    def test_tampered_actual_fbx_rejected(self):
        p=self.root/c.SOURCE/'FBX/SM_Cottage_Stonebrook_01.fbx';data=p.read_bytes()
        try:
            p.write_bytes(data+b'changed')
            with self.assertRaisesRegex(ValueError,'Frozen source mismatch'):c.load_contract(self.root)
        finally:p.write_bytes(data)
    def test_tampered_texture_rejected(self):
        p=next((self.root/c.LIBRARY/'ThinWavyGlass2mV1/Textures').glob('*.png'));data=p.read_bytes()
        try:
            p.write_bytes(data[:-1]+bytes([data[-1]^1]))
            with self.assertRaisesRegex(ValueError,'Frozen source mismatch'):c.load_contract(self.root)
        finally:p.write_bytes(data)
    def test_existing_trial_package_rejected(self):
        r=c.load_contract(self.root);package=r['meshes'][0]['package'];p=self.root/('Content/'+package.removeprefix('/Game/')+'.uasset');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'existing')
        try:
            with self.assertRaisesRegex(ValueError,'Refusing existing'):c.assert_trial_absent(self.root,r)
        finally:p.unlink()
    def test_broken_symlink_trial_package_rejected(self):
        r=c.load_contract(self.root);package=r['meshes'][0]['package'];p=self.root/('Content/'+package.removeprefix('/Game/')+'.uasset');p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(self.root/'absent')
        try:
            with self.assertRaisesRegex(ValueError,'Refusing existing'):c.assert_trial_absent(self.root,r)
        finally:p.unlink()
    def test_unapproved_native_refuses_before_engine(self):
        import house439_native as native
        class ForbiddenEngine:
            def __getattr__(self,key):raise AssertionError('Unapproved native access: '+key)
        def forbidden(*args,**kwargs):raise AssertionError('Unapproved callback')
        with self.assertRaisesRegex(ValueError,'Explicit matching Root'):
            native.import_trial(ForbiddenEngine(),self.root,{'digest':'unreviewed'},
                {'approved':False},forbidden,forbidden,forbidden,forbidden,forbidden,forbidden)
    def test_escape_package_rejected(self):
        with self.assertRaisesRegex(ValueError,'escaped'):c.assert_trial_absent(self.root,{'trial_packages':{'/Game/Other/Unrelated':'StaticMesh'}})
if __name__=='__main__':unittest.main()
