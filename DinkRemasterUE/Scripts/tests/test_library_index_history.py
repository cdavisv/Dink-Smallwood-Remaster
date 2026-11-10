import hashlib,importlib.util,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'library_index_history.py';spec=importlib.util.spec_from_file_location('index_history',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class IndexHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.name='SourceAssets/Art/SharedMaterials/manifest.json';self.old=b'{"old":true}\n';self.new=b'{"new":true}\n';self.oldsha=hashlib.sha256(self.old).hexdigest();self.newsha=hashlib.sha256(self.new).hexdigest();self.path=self.root/self.name;self.path.parent.mkdir(parents=True);self.path.write_bytes(self.new);self.archive=self.path.parent/'History'/self.oldsha/self.path.name;self.archive.parent.mkdir(parents=True);self.archive.write_bytes(self.old);self.row={'asset_path':self.name,'sha256':self.oldsha};self.rows=[self.row,{'asset_path':self.name,'sha256':self.newsha}]
    def test_exact_history_and_latest_pass(self):self.assertTrue(m.historical_index_matches(self.root,self.rows,self.row))
    def test_prior_ledger_row_unchanged(self):
        before=[dict(r)for r in self.rows];m.historical_index_matches(self.root,self.rows,self.row);self.assertEqual(before,self.rows)
    def test_missing_archive_rejected(self):
        self.archive.unlink();self.assertFalse(m.historical_index_matches(self.root,self.rows,self.row))
    def test_corrupt_archive_rejected(self):
        self.archive.write_bytes(b'changed');self.assertFalse(m.historical_index_matches(self.root,self.rows,self.row))
    def test_current_index_must_match_latest(self):
        self.path.write_bytes(b'changed');self.assertFalse(m.historical_index_matches(self.root,self.rows,self.row))
    def test_no_new_current_row_rejected(self):self.assertFalse(m.historical_index_matches(self.root,[self.row],self.row))
    def test_current_row_not_historical(self):self.assertFalse(m.historical_index_matches(self.root,self.rows,self.rows[-1]))
    def test_audio_and_ordinary_assets_strict(self):
        for name in ['SourceAssets/Audio/selection_manifest.json','SourceAssets/Art/SomeMesh/manifest.json']:
            r={'asset_path':name,'sha256':self.oldsha};self.assertFalse(m.historical_index_matches(self.root,[r,{'asset_path':name,'sha256':self.newsha}],r))
    def test_symlink_archive_rejected(self):
        self.archive.unlink();target=self.root/'old';target.write_bytes(self.old);self.archive.symlink_to(target);self.assertFalse(m.historical_index_matches(self.root,self.rows,self.row))
    def test_symlink_current_rejected(self):
        self.path.unlink();target=self.root/'current';target.write_bytes(self.new);self.path.symlink_to(target);self.assertFalse(m.historical_index_matches(self.root,self.rows,self.row))
    def test_unrecorded_old_digest_rejected(self):
        r={'asset_path':self.name,'sha256':'a'*64};self.assertFalse(m.historical_index_matches(self.root,self.rows,r))
if __name__=='__main__':unittest.main()
