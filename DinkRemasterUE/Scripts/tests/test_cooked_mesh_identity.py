"""Compile and exercise the actual production identity comparator, without Unreal."""
import subprocess,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[2]
class CookedMeshIdentityTests(unittest.TestCase):
 def test_exact_associations_and_separately_ordered_epochs(self):
  with tempfile.TemporaryDirectory(prefix='dink-owned-identity-') as td:
   exe=Path(td)/'identity'
   subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Wshadow','-Werror','-fno-exceptions','-fno-rtti','-I',str(P/'Plugins/DinkNarrative/Source/DinkNarrative/Public'),str(P/'Scripts/tests/native/cooked_mesh_identity.cpp'),'-o',str(exe)],check=True,capture_output=True)
   result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
   self.assertIn('PASS exact particles/indices/material/face associations',result.stdout)
