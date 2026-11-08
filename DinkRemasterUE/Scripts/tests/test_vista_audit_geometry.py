import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from vista_audit_geometry import overlap_xy,clip_triangle_open_rect,lod_intersections,coverage_source,checked_triangle_vertices

def rectangle(x0,y0,x1,y1):
    return [[[x0,y0,0],[x1,y0,0],[x1,y1,0]],[[x0,y0,0],[x1,y1,0],[x0,y1,0]]]
ROOM=[[0,0,-100],[2,2,500]]
class GeometryTests(unittest.TestCase):
    def test_notched_L_shape_aabb_is_only_potential(self):
        triangles=rectangle(-2,-2,3,0)+rectangle(-2,0,0,3)
        self.assertTrue(overlap_xy([[-2,-2,0],[3,3,0]],ROOM))
        self.assertFalse(any(clip_triangle_open_rect(t,ROOM) for t in triangles))
    def test_boundary_contact_is_not_interior(self):
        for triangle in [[[0,0,0],[0,2,0],[-1,1,3]],[[-1,-1,0],[0,0,0],[-1,1,0]]]:
            self.assertEqual(clip_triangle_open_rect(triangle,ROOM),[])
    def test_true_intrusion_and_enclosing_triangle(self):
        self.assertTrue(clip_triangle_open_rect([[-1,1,0],[1,1,0],[1,3,0]],ROOM))
        self.assertTrue(clip_triangle_open_rect([[-10,-10,0],[10,-10,0],[0,10,0]],ROOM))
    def test_vertical_surface_projection_is_not_dropped(self):
        clipped=clip_triangle_open_rect([[1,-1,0],[1,3,0],[1,1,100]],ROOM)
        self.assertTrue(clipped);self.assertTrue(any(p[2]>0 for p in clipped))
    def test_coarse_LOD_bridge_is_detected(self):
        fine=rectangle(-2,-2,3,0)+rectangle(-2,0,0,3);coarse=rectangle(-2,-2,3,3)
        result=lod_intersections([fine,coarse],ROOM)
        self.assertEqual(result[0]['triangle_hits'],0);self.assertGreater(result[1]['triangle_hits'],0)
    def test_invalid_triangle_never_reaches_editor_getter(self):
        class Description:
            calls=0
            def is_triangle_valid(self,triangle):return False
            def get_triangle_vertices(self,triangle):self.calls+=1;raise AssertionError('unsafe getter')
        description=Description()
        with self.assertRaisesRegex(ValueError,'before editor getter'):checked_triangle_vertices(description,99)
        self.assertEqual(description.calls,0)
    def test_indexed_triangle_accessor_never_reads_broken_array(self):
        class Description:
            bad_instance=False
            vertex_calls=0
            def is_triangle_valid(self,t):return t==42
            def get_triangle_vertices(self,t):raise AssertionError('never read malformed six-entry array')
            def get_triangle_vertex_instance(self,t,index):return [7,8,9][index]
            def is_vertex_instance_valid(self,i):return i in [7,8,9] and not(self.bad_instance and i==8)
            def get_vertex_instance_vertex(self,i):self.vertex_calls+=1;return {7:2,8:4,9:6}[i]
            def is_vertex_valid(self,i):return i in [2,4,6]
        description=Description();self.assertEqual(checked_triangle_vertices(description,42),[2,4,6])
        description=Description();description.bad_instance=True
        with self.assertRaisesRegex(ValueError,'vertex-instance'):checked_triangle_vertices(description,42)
        self.assertEqual(description.vertex_calls,0)
    def test_ground_OR_step_coverage(self):
        self.assertEqual(coverage_source(None,0),'step');self.assertEqual(coverage_source(0,None),'ground')
        self.assertEqual(coverage_source(-2,0),'ground+step');self.assertEqual(coverage_source(None,None),'none')
if __name__=='__main__':unittest.main()
