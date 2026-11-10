import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import shaderprint_vulkan_workaround as W
class Tests(unittest.TestCase):
 def source(self):return W.ORIGINAL_CONDITION+b'\n#define SHADER_PRINT_USE_GLOBAL_RESOURCE 1\n'
 def test_exact_source_patch_and_already_fixed_bypass(self):
  base=self.source();fixed=base.replace(W.ORIGINAL_CONDITION,W.FIXED_CONDITION,1)
  with patch.object(W,'ORIGINAL_SHA',hashlib.sha256(base).hexdigest()),patch.object(W,'FIXED_SHA',hashlib.sha256(fixed).hexdigest()):
   self.assertEqual(W._classify(base),('private_overlay',fixed));self.assertEqual(W._classify(fixed),('already_fixed',None));self.assertRaises(ValueError,W._classify,base+b'extra')
 def test_only_temp_file_overlay_and_argv_preserved(self):
  e=Path('/engine');private=Path('/tmp/owned/ShaderPrint.ush');command=['/engine/Build/BatchFiles/RunUAT.sh','BuildCookRun','-project=a b.uproject']
  c=W._namespace_command(e,private,command,Path('/project'));self.assertEqual(c[c.index('--')+1:],command);self.assertEqual(c[c.index('--ro-bind')+1:c.index('--ro-bind')+3],[str(private),'/engine/Shaders/Private/ShaderPrint.ush']);self.assertEqual(c.count('--ro-bind'),1);self.assertEqual(c[c.index('--dev-bind')+1:c.index('--dev-bind')+3],['/dev','/dev']);self.assertNotIn('--unshare-net',c)
 def test_execute_overlay_normal_return_and_immutable_host(self):
  with tempfile.TemporaryDirectory()as t:
   e=Path(t);f=e/'Shaders/Private/ShaderPrint.ush';f.parent.mkdir(parents=True);base=self.source();f.write_bytes(base);(e/'Build/BatchFiles').mkdir(parents=True);(e/'Build/Build.version').write_text(json.dumps(dict(MajorVersion=5,MinorVersion=8,PatchVersion=4)));fixed=base.replace(W.ORIGINAL_CONDITION,W.FIXED_CONDITION,1);before=W._snapshot(f);fake_bwrap=e/'mock_bwrap';fake_bwrap.write_bytes(b'not executed')
   def run(command,check):
    self.assertFalse(check);private=Path(command[command.index('--ro-bind')+1]);self.assertEqual(private.read_bytes(),fixed);self.assertEqual(private.stat().st_mode&0o777,0o400);return SimpleNamespace(returncode=17)
   with patch.object(W,'BWRAP',fake_bwrap),patch.object(W,'ORIGINAL_SHA',hashlib.sha256(base).hexdigest()),patch.object(W,'FIXED_SHA',hashlib.sha256(fixed).hexdigest()),patch.object(W.subprocess,'run',side_effect=run):self.assertEqual(W.execute(e,[str(e/'Build/BatchFiles/RunUAT.sh'),'BuildCookRun']),17)
   self.assertEqual(W._snapshot(f),before)
 def test_unknown_header_and_arbitrary_command_refuse_before_launch(self):
  with tempfile.TemporaryDirectory()as t:
   e=Path(t);f=e/'Shaders/Private/ShaderPrint.ush';f.parent.mkdir(parents=True);f.write_bytes(b'unknown')
   with patch.object(W.subprocess,'run')as run:
    self.assertRaises(ValueError,W.execute,e,[str(e/'Build/BatchFiles/RunUAT.sh')]);self.assertRaises(ValueError,W.execute,e,['/bin/false']);run.assert_not_called()
 def test_changed_host_detected_even_child_success(self):
  with tempfile.TemporaryDirectory()as t:
   e=Path(t);f=e/'Shaders/Private/ShaderPrint.ush';f.parent.mkdir(parents=True);fixed=b'known fixed'
   f.write_bytes(fixed)
   def run(*args,**kwargs):f.write_bytes(b'changed');return SimpleNamespace(returncode=0)
   with patch.object(W,'FIXED_SHA',hashlib.sha256(fixed).hexdigest()),patch.object(W.subprocess,'run',side_effect=run):self.assertRaises(ValueError,W.execute,e,[str(e/'Build/BatchFiles/RunUAT.sh')])
if __name__=='__main__':unittest.main()
