import copy,hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hero_source_history as H

class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  old,new=b'actual archived preimage',b'accepted replacement';self.old=hashlib.sha256(old).hexdigest();self.new=hashlib.sha256(new).hexdigest()
  self.e=dict(asset_path='SourceAssets/Hero.fbx',old_sha256=self.old,new_sha256=self.new,archive_path='SourceAssets/History/'+self.old+'/Hero.fbx',accepted_commit='200ea3d60ec48c4a59dd7c5ac9d36219fd95b840')
  self.rows=[dict(asset_path=self.e['asset_path'],sha256=self.old),dict(asset_path=self.e['asset_path'],sha256=self.new)]
  for path,data in [(self.e['asset_path'],new),(self.e['archive_path'],old)]:
   p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  self.manifest=dict(schema='dink-accepted-hero-source-history/1',accepted_commit=H.ACCEPTED_COMMIT,entries=[self.e],scope=H.SCOPE);self.patch=patch.object(H,'AUTHORITY',[self.e]);self.patch.start();self.addCleanup(self.patch.stop)
 def check(self):return H.validate_history(self.root,self.rows,self.manifest)
 def test_actual_bytes_and_later_row(self):self.assertEqual(self.check()['indices'],{0})
 def test_corrupt_archive(self):
  (self.root/self.e['archive_path']).write_bytes(b'corrupt')
  with self.assertRaises(ValueError):self.check()
 def test_missing_archive(self):
  (self.root/self.e['archive_path']).unlink()
  with self.assertRaises(ValueError):self.check()
 def test_wrong_current_bytes(self):
  (self.root/self.e['asset_path']).write_bytes(b'wrong')
  with self.assertRaises(ValueError):self.check()
 def test_wrong_newhash_manifest(self):
  self.manifest=copy.deepcopy(self.manifest);self.manifest['entries'][0]['new_sha256']='0'*64
  with self.assertRaises(ValueError):self.check()
 def test_no_later_row(self):
  self.rows.pop()
  with self.assertRaises(ValueError):self.check()
 def test_reversed_rows(self):
  self.rows.reverse()
  with self.assertRaises(ValueError):self.check()
 def test_extra_revision(self):
  self.rows.append(dict(asset_path=self.e['asset_path'],sha256='f'*64))
  with self.assertRaises(ValueError):self.check()
 def test_no_generic_row_waiver(self):
  self.rows.append(dict(asset_path='Other',sha256='0'*64));self.assertEqual(self.check()['indices'],{0})
 def test_symlink_archive(self):
  p=self.root/self.e['archive_path'];data=p.read_bytes();p.unlink();target=self.root/'alias';target.write_bytes(data);p.symlink_to(target)
  with self.assertRaises(ValueError):self.check()
class PointerTests(HistoryTests):
 def pointers(self):
  self.inventory={}
  for path,sha,size in [(self.e['asset_path'],self.new,123),(self.e['archive_path'],self.old,456)]:
   (self.root/path).write_text('version https://git-lfs.github.com/spec/v1\noid sha256:'+sha+'\nsize '+str(size)+'\n')
   self.inventory[path]={'sha256':sha,'size':size}
 def meta(self):return H.validate_history(self.root,self.rows,self.manifest,metadata_only=True,inventory=self.inventory)
 def test_correct_pointers(self):
  self.pointers();r=self.meta();self.assertEqual(r,{'indices':{0},'historical_rows_binary_verified':0,'historical_rows_metadata_only':1})
 def test_wrong_oid(self):
  self.pointers();p=self.root/self.e['archive_path'];p.write_text(p.read_text().replace(self.old,'0'*64))
  with self.assertRaises(ValueError):self.meta()
 def test_wrong_size(self):
  self.pointers();self.inventory[self.e['archive_path']]['size']+=1
  with self.assertRaises(ValueError):self.meta()
 def test_missing_inventory(self):
  self.pointers();self.inventory.pop(self.e['archive_path'])
  with self.assertRaises(ValueError):self.meta()
 def test_full_refuses_pointer(self):
  self.pointers()
  with self.assertRaises(ValueError):self.check()
 def test_inventory_cannot_authorize_wrong_approved_oid(self):
  self.pointers();p=self.root/self.e['asset_path'];p.write_text(p.read_text().replace(self.new,'0'*64));self.inventory[self.e['asset_path']]['sha256']='0'*64
  with self.assertRaises(ValueError):self.meta()
 def test_metadata_with_real_bytes_is_binary(self):
  self.inventory={};self.assertEqual(self.meta()['historical_rows_binary_verified'],1)
if __name__=='__main__':unittest.main()
