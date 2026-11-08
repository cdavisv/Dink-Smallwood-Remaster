import unittest
from pathlib import Path
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publish_perimeter_skirt_surface as p

class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.points=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
        self.faces=[(0,2,1),(0,1,3),(1,2,3),(2,0,3)]

    def test_cyclic_start_and_small_float_delta_accepted(self):
        actual=[(x+1e-5,y,z) for x,y,z in self.points]
        faces=[t[1:]+t[:1] for t in self.faces]
        self.assertLess(p.match_geometry(self.points,self.faces,actual,faces),.001)

    def test_single_face_reversal_rejected(self):
        faces=list(self.faces);faces[0]=tuple(reversed(faces[0]))
        with self.assertRaises(AssertionError):p.match_geometry(self.points,self.faces,self.points,faces)

    def test_duplicate_missing_face_rejected(self):
        faces=list(self.faces);faces[0]=faces[1]
        with self.assertRaises(AssertionError):p.match_geometry(self.points,self.faces,self.points,faces)

    def test_collapsed_source_match_rejected(self):
        actual=list(self.points);actual[1]=actual[0]
        with self.assertRaises(AssertionError):p.match_geometry(self.points,self.faces,actual,self.faces)

    def test_changed_vertex_rejected(self):
        actual=list(self.points);actual[0]=(.051,0,0)
        with self.assertRaises(AssertionError):p.match_geometry(self.points,self.faces,actual,self.faces)

    def test_report_stays_in_owned_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p.report_guard(root,root/'Saved/Art/receipt.json')
            with self.assertRaises(AssertionError):p.report_guard(root,root/'SourceAssets/receipt.json')

    def test_saved_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            root=Path(tmp);(root/'Saved').symlink_to(other,target_is_directory=True)
            with self.assertRaises(AssertionError):p.report_guard(root,root/'Saved/receipt.json')

if __name__=='__main__':unittest.main()
