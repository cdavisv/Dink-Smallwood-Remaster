"""Oriented matching regressions from actual float32 native import boundary errors."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import basket_contract as C


class TolerantOrientedMatchingTests(unittest.TestCase):
    def face(self,x=0,uv=.2,size=2):
        return [([x,0,0],[uv,.2],[0,0,-1]),([x+size,0,0],[uv+.2,.2],[0,0,-1]),([x,size+1,0],[uv,.6],[0,0,-1])]
    def test_opposite_round_half_bins_accept_tiny_actual_position_and_UV_deltas(self):
        source=self.face(.0049999999,.00004999999);native=self.face(.0050000001,.00005000001)
        self.assertNotEqual(C.triangle_signature([source]),C.triangle_signature([native]))
        m=C.match_oriented_triangles([native],[source]);self.assertLess(m['summary']['max_position_delta_cm'],1e-8);self.assertLess(m['summary']['max_UV_delta'],1e-9);self.assertTrue(m['summary']['bijective_source_coverage'])
    def test_neighbour_floor_bins_accept_negative_and_positive_boundary_deltas(self):
        for x in [.0099999999,-.0100000001]:
            source=self.face(x);native=self.face(x+2e-10);self.assertEqual(C.match_oriented_triangles([native],[source])['summary']['checked_triangles'],1)
    def test_actual_position_and_UV_limits_are_not_increased(self):
        source=self.face()
        for native in [self.face(.010001),self.face(0,.20010001)]:
            with self.assertRaises(ValueError):C.match_oriented_triangles([native],[source])
    def test_cyclic_rotation_and_triangle_reorder_accept(self):
        a=self.face();b=self.face(10);m=C.match_oriented_triangles([b[1:]+b[:1],a[2:]+a[:2]],[a,b]);self.assertEqual({x['source_index']for x in m['matches']},{0,1})
    def test_single_and_all_reversals_reject(self):
        a=self.face();b=self.face(10)
        for native in [[a[::-1],b],[a[::-1],b[::-1]]]:
            with self.assertRaises(ValueError):C.match_oriented_triangles(native,[a,b])
    def test_subtolerance_triangle_reversal_still_rejects_by_geometric_front(self):
        tiny=[([0,0,0],[0,0],[0,0,-1]),([.001,0,0],[.00001,0],[0,0,-1]),([0,.001,0],[0,.00001],[0,0,-1])]
        with self.assertRaises(ValueError):C.match_oriented_triangles([tiny[::-1]],[tiny])
    def test_missing_face_and_duplicate_native_face_cannot_replace_source_coverage(self):
        a=self.face();b=self.face(10)
        for native in [[a],[a,a]]:
            with self.assertRaises(ValueError):C.match_oriented_triangles(native,[a,b])


class ConvexCloudMatchingTests(unittest.TestCase):
    def cloud(self,x=0):return [[x+a,b,c]for a in [0,2]for b in [-1,1]for c in [-3,3]]
    def test_half_bin_errors_are_checked_by_actual_delta(self):
        source=self.cloud(.0049999999);native=self.cloud(.0050000001);self.assertNotEqual([[round(x/.01)for x in p]for p in source],[[round(x/.01)for x in p]for p in native]);r=C.match_convex_clouds([native[::-1]],[source]);self.assertTrue(r['bijective_hulls_and_vertices']);self.assertLess(r['max_vertex_delta_cm'],1e-8)
    def test_real_out_of_limit_vertex_is_rejected(self):
        with self.assertRaises(ValueError):C.match_convex_clouds([self.cloud(.010001)],[self.cloud()])
    def test_missing_vertex_or_duplicate_hull_cannot_replace_source(self):
        for native,source in [([self.cloud()[:-1]],[self.cloud()]),([self.cloud(),self.cloud()],[self.cloud(),self.cloud(10)])]:
            with self.assertRaises(ValueError):C.match_convex_clouds(native,source)


if __name__=='__main__':unittest.main()
