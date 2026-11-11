"""Independent byte-contract oracle against the actual portable production encoder."""
import hashlib,struct,subprocess,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[2]
DOMAIN=b'DinkOrientedTrianglesF32LEMaterialU16LE/1\0'
def record(points,material=0):return struct.pack('<9fH',*(v for point in points for v in point),material)
def canonical(records):
 rows=[]
 for row in records:
  points=[row[i:i+12] for i in (0,12,24)];mat=row[36:]
  rows.append(min(b''.join(points[i:]+points[:i])+mat for i in range(3)))
 return DOMAIN+b'\x01'+struct.pack('<I',len(rows))+b''.join(sorted(rows))
class CanonicalSurfaceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='dink-surface-');cls.exe=Path(cls.tmp.name)/'surface'
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fno-exceptions','-fno-rtti','-I',str(P/'Plugins/DinkCore/Source/DinkCore/Public'),str(P/'Scripts/tests/native/canonical_surface.cpp'),'-o',str(cls.exe)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def encode(self,rows,cull=True):return subprocess.run([str(self.exe)]+([] if cull else ['no-cull']),input=b''.join(rows),check=True,capture_output=True).stdout
 def test_exact_domain_endian_count_and_cyclic_order(self):
  a=((1.,2.,3.),(4.,5.,6.),(7.,8.,9.));b=((9.,2.,1.),(4.,-5.,6.),(7.,8.,-9.))
  rows=[record(a,513),record(b,65535),record(a[1:]+a[:1],513)]
  self.assertEqual(self.encode(rows),canonical(rows));self.assertEqual(self.encode(rows),self.encode(rows[::-1]))
 def test_winding_material_duplicates_and_signed_zero_remain_identity(self):
  p=((0.,1.,2.),(3.,4.,5.),(6.,7.,8.));base=self.encode([record(p)])
  for rows in ([record((p[0],p[2],p[1]))],[record(p,1)],[record(p),record(p)],[record(((-0.,1.,2.),p[1],p[2]))]):
   self.assertNotEqual(base,self.encode(rows));self.assertEqual(self.encode(rows),canonical(rows))
 def test_cull_and_count_are_separate_policy_identity(self):
  p=((0.,1.,2.),(3.,4.,5.),(6.,7.,8.));rows=[record(p)]
  self.assertNotEqual(self.encode(rows),self.encode(rows,False))
  changed=bytearray(self.encode(rows));changed[len(DOMAIN)+1:len(DOMAIN)+5]=struct.pack('<I',2)
  self.assertNotEqual(hashlib.sha1(changed).digest(),hashlib.sha1(self.encode(rows)).digest())
 def test_empty_count_has_unambiguous_domain(self):self.assertEqual(self.encode([]),DOMAIN+b'\x01\0\0\0\0')
