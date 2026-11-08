"""Regressions for reviewP2s: candidate TOCTOU and lost orientation."""
import copy,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feedsack_contract as C


class VerifyCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.plan={'assets':[{'mesh':C.MESH_FOLDER+'/'+n,'materials':[C.MAT_FOLDER+'/'+m for m in C.MATERIAL_NAMES],'textures':{r:C.TEX_FOLDER+'/T_'+n[3:]+'_Photo_'+r for r in C.ROLES}}for n in C.COUNTS]}
        for relative in C.packages(self.plan):
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('imported '+relative).encode())
        self.baseline=C.candidate_package_pins(self.root,self.plan);self.frozen=copy.deepcopy(self.baseline)
    def verify_with_inspection(self, inspection, final_guard=lambda:None):
        C.verify_candidate_packages(self.root,self.plan,self.baseline)  # entry
        loaded=dict(self.baseline)  # Represents inspected editor objects retaining import-time data.
        inspection()
        self.assertEqual(loaded,self.frozen)
        certified=C.verify_candidate_packages(self.root,self.plan,self.baseline)
        final_guard()
        C.verify_candidate_packages(self.root,self.plan,self.baseline)  # exit after all other guards
        return certified
    def test_unchanged_bytes_certify_exact_import_receipt(self):
        self.assertEqual(self.verify_with_inspection(lambda:None),self.frozen)
    def test_loaded_object_inspection_cannot_certify_mutated_mesh_or_texture(self):
        for suffix in ['.uasset']:
            for relative in [p for p in self.baseline if '/Props/'in p or '/Textures/'in p]:
                path=self.root/relative;original=path.read_bytes()
                with self.subTest(relative=relative):
                    with self.assertRaisesRegex(ValueError,'Candidate package set/hash drift'):self.verify_with_inspection(lambda:path.write_bytes(b'uninspected replacement'))
                    self.assertEqual(self.baseline,self.frozen)
                path.write_bytes(original)
    def test_concurrent_sidecar_addition_is_rejected(self):
        path=self.root/next(iter(self.baseline));sidecar=path.with_suffix('.ubulk')
        with self.assertRaisesRegex(ValueError,'Candidate package set/hash drift'):self.verify_with_inspection(lambda:sidecar.write_bytes(b'uninspected sidecar'))
    def test_candidate_deletion_is_rejected(self):
        path=self.root/next(iter(self.baseline))
        with self.assertRaisesRegex(ValueError,'Required candidate package missing'):self.verify_with_inspection(path.unlink)
    def test_existing_sidecar_mutation_and_deletion_are_rejected(self):
        path=(self.root/next(iter(self.baseline))).with_suffix('.uexp');path.write_bytes(b'imported sidecar');self.baseline=C.candidate_package_pins(self.root,self.plan);self.frozen=copy.deepcopy(self.baseline)
        with self.assertRaises(ValueError):self.verify_with_inspection(lambda:path.write_bytes(b'new sidecar'))
        path.write_bytes(b'imported sidecar')
        with self.assertRaises(ValueError):self.verify_with_inspection(path.unlink)
    def test_mutation_inside_late_protected_guard_is_rejected_at_exit(self):
        path=self.root/next(iter(self.baseline))
        with self.assertRaisesRegex(ValueError,'Candidate package set/hash drift'):self.verify_with_inspection(lambda:None,lambda:path.write_bytes(b'late uninspected bytes'))


class TriangleWindingTests(unittest.TestCase):
    def setUp(self):
        self.t=[([.25,1.5,2.75],[.13,.27],[0,0,0]),([4,2,3],[.6,.31],[0,0,0]),([1,5,2],[.44,.87],[0,0,0])]
        self.second=[([p[0]+7,p[1],p[2]],uv,n)for p,uv,n in self.t]
    def test_start_corner_and_triangle_list_order_are_irrelevant(self):
        self.assertEqual(C.triangle_signature([self.t,self.second]),C.triangle_signature([self.second[2:]+self.second[:2],self.t[1:]+self.t[:1]]))
    def test_single_face_reversal_is_rejected(self):
        self.assertNotEqual(C.triangle_signature([self.t,self.second]),C.triangle_signature([list(reversed(self.t)),self.second]))
    def test_all_face_reversal_is_rejected(self):
        self.assertNotEqual(C.triangle_signature([self.t,self.second]),C.triangle_signature([list(reversed(self.t)),list(reversed(self.second))]))
    def test_native_geometric_normal_evidence_accepts_cyclic_faces_and_rejects_reverse(self):
        authored=[([0,0,0],[0,1],[0,0,1]),([2,0,0],[1,1],[0,0,1]),([0,-3,0],[0,0],[0,0,1])]
        native=[(p,uv,[0,0,0])for p,uv,n in authored]
        evidence=C.verify_native_front_normals([native[1:]+native[:1]],[authored]);self.assertEqual(evidence['checked_triangles'],1);self.assertEqual(evidence['minimum_dot_source_geometric_front'],1)
        with self.assertRaises(ValueError):C.verify_native_front_normals([native[::-1]],[authored])
        bad=[(p,uv,[0,0,-1])for p,uv,n in authored]
        with self.assertRaises(ValueError):C.verify_native_front_normals([native],[bad])
    def test_UE_reflection_preserves_corner_order_and_clockwise_front_normal(self):
        # FbxUtilsImport.cpp ConvertPos/Dir: (x,y,z)->(x,-y,z).
        # FbxStaticMeshImport.cpp: CornerInstanceIDs retain PolygonVertex order.
        source=[([0,0,0],[0,0],[0,0,1]),([2,0,0],[1,0],[0,0,1]),([0,3,0],[0,1],[0,0,1])]
        expected=[([p[0],-p[1],p[2]],[uv[0],1-uv[1]],[0,0,0])for p,uv,n in source]
        a,b,c=[q[0]for q in expected];ba=[b[k]-a[k]for k in range(3)];ca=[c[k]-a[k]for k in range(3)]
        # UE clockwise face normal is cross(C-A,B-A), aligned with converted+Z normal.
        normal=[ca[1]*ba[2]-ca[2]*ba[1],ca[2]*ba[0]-ca[0]*ba[2],ca[0]*ba[1]-ca[1]*ba[0]]
        self.assertGreater(normal[2],0)
        self.assertNotEqual(C.triangle_signature([expected]),C.triangle_signature([expected[::-1]]))


if __name__=='__main__':unittest.main()
