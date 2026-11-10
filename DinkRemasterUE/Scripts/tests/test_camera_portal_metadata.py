"""Independent source/provenance checks, not a claim that uncompiled C++ or pixels pass."""
import unittest,json,hashlib,re,math
from pathlib import Path
P=Path(__file__).resolve().parents[2]
DATA=P/'Content/Dink/Data/Art/camera_exteriors.json'
SOURCE=P/'SourceAssets/Art/StonebrookExterior/CameraPortalV1/camera_exteriors.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class PortalMetadata(unittest.TestCase):
 def test_source_runtime_and_existing_geometry_authorities(self):
  self.assertEqual(DATA.read_bytes(),SOURCE.read_bytes());d=json.loads(DATA.read_text());a=d['source_provenance'];self.assertEqual(sha(P/a['generator']),a['generator_sha256']);self.assertEqual(sha(P/a['export_manifest']),a['export_manifest_sha256'])
  mesh=P/a['native_mesh_package'];raw=mesh.read_bytes();oid=re.search(rb'oid sha256:([0-9a-f]{64})',raw).group(1).decode()if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n')else sha(mesh);self.assertEqual(oid,a['native_mesh_package_sha256']);self.assertEqual(d['rules'][0]['native_mesh_package_sha256'],oid)
 def test_owner_is_explicit_actual_row_not_vista_copy(self):
  rule=json.loads(DATA.read_text())['rules'][0];manifest=json.loads((DATA.parent/rule['owner_manifest']).read_text());rows=[r for r in manifest['elements']if r['name']==rule['owner_element']];self.assertEqual(len(rows),1);self.assertEqual(manifest['screen'],439);self.assertEqual(rows[0]['mesh'],rule['expected_mesh']);self.assertTrue(rows[0]['collision']);self.assertEqual(rows[0]['scale'],[1,1,1]);self.assertEqual(rule['portal_point_cm'],[530,457+45/2,0]);self.assertEqual(rule['aperture_min_cm'],[-75,22]);self.assertEqual(rule['aperture_max_cm'],[75,250])
 def test_independent_recorded_pose_plane_projection_and_nearclip(self):
  # Recorded real free400 NOHIT case; expected plane/lift checked independently of C++ implementation.
  origin=[97131.61092968748,36920.324198125,0];pawn=[97729.63625545749,37512.61084546293,98.34999561309814];eye=[97704.23270538304,37133.03737537629,221.9567933630771];rule=json.loads(DATA.read_text())['rules'][0]
  fraction=(pawn[1]-origin[1]-rule['portal_point_cm'][1]-12)/(pawn[1]-eye[1]);limited=[pawn[i]+fraction*(eye[i]-pawn[i])for i in range(3)];self.assertAlmostEqual(limited[1]-origin[1],491.5,6);self.assertAlmostEqual(fraction*400,106.21042331,6)
  yaw,pitch=map(math.radians,[86.1711,-18]);f=[math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)];u=[-math.sin(pitch)*math.cos(yaw),-math.sin(pitch)*math.sin(yaw),math.cos(pitch)];dot=lambda a,b:sum(x*y for x,y in zip(a,b));d=[pawn[i]+(96 if i==2 else 0)-limited[i]for i in range(3)];slope=.8/(1280/720);lift=(dot(d,u)-slope*dot(d,f))/(u[2]-slope*f[2]);self.assertGreater(lift,50);self.assertLess(lift,55);d[2]-=lift;depth=dot(d,f);self.assertGreater(depth,10);self.assertAlmostEqual(dot(d,u)*(1280/720)/depth,.8,6)
 def test_hull_has_independent_structural_witness_and_portal_support(self):
  r=json.loads(DATA.read_text())['rules'][0];p=r['interior_point_cm'];self.assertTrue(all(sum(n[i]*p[i]for i in range(3))<n[3]for n in r['interior_planes']));self.assertIn([0,1,0,425],r['interior_planes']);self.assertGreater(r['portal_point_cm'][1],425);self.assertNotEqual(r['native_bounds_max_cm'][1],r['portal_point_cm'][1])
if __name__=='__main__':unittest.main()
