"""Operational regression: relative metadata exists before verification, no early save."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'RoofNative'))
from house439_native import checked_mesh_before_save
class MetadataOrderingTests(unittest.TestCase):
    def test_metadata_then_verification_then_save(self):
        events=[];state={}
        def configure(mesh,record):state['relative']=True;events.append('metadata')
        def verify(mesh,record):
            self.assertTrue(state.get('relative'));events.append('verify');return dict(passed=True,triangles=194192,UCX=6,source_correspondence_passed=True,raw_Color0_import_passed=True,normal_tangent_basis='UV0')
        result=checked_mesh_before_save(object(),{},configure,verify,lambda m:events.append('save'));self.assertTrue(result['passed']);self.assertEqual(events,['metadata','verify','save'])
    def test_failed_metadata_never_verifies_or_saves(self):
        def failure(*args):raise ValueError('metadata failed')
        def forbidden(*args):self.fail('Verification/save must not run')
        with self.assertRaisesRegex(ValueError,'metadata failed'):checked_mesh_before_save(object(),{},failure,forbidden,forbidden)
    def test_failed_proof_never_saves(self):
        with self.assertRaises(ValueError):checked_mesh_before_save(object(),{},lambda *a:None,lambda *a:{'passed':False},lambda *a:self.fail('Unverified mesh saved'))
if __name__=='__main__':unittest.main()
