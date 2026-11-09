"""Two-material and nested-packet regressions beyond the 97 retained guards."""
import copy,json,unittest
import feedsack_contract as C
import test_feedsack_publication as fixtures

class TwoMaterialPublication(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationTests('test_dry_run_zero_writes');self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_six_unique_packages_with_shared_three_texture_assets(self):
        self.assertEqual(len(C.packages(self.f.plan)),6)
        self.assertEqual(len(self.f.plan['assets'][0]['materials']),2)
        self.assertEqual(len(set(self.f.plan['assets'][0]['textures'].values())),3)
    def test_cord_optics_conversion_and_independent_float32_tolerance(self):
        self.assertAlmostEqual(C.source_to_ue_specular(1.5,.22),.22)
        self.assertTrue(C.valid_native_specular(.2200000001,.22))
        self.assertFalse(C.valid_native_specular(C.UE_SPECULAR,.22))
        self.assertFalse(C.valid_native_specular(.22,C.UE_SPECULAR))
    def test_swapped_material_recipes_reject(self):
        f=self.f;f.receipt['material_recipes']['SM_FeedSack_Jute_01'].reverse();f.write_receipt();f.rejected_without_house_mutation()
    def test_missing_cord_recipe_rejects(self):
        f=self.f;f.receipt['material_recipes']['SM_FeedSack_Jute_01'].pop();f.write_receipt();f.rejected_without_house_mutation()
    def test_cord_scalar_wrong_even_when_jute_correct_rejects(self):
        f=self.f;f.receipt['material_recipes']['SM_FeedSack_Jute_01'][1]['specular']=C.UE_SPECULAR;f.write_receipt();f.rejected_without_house_mutation()
    def test_native_section_material_swap_rejects(self):
        f=self.f;f.receipt['native_assets']['SM_FeedSack_Jute_01']['section_material_slots']=[1,0];f.write_receipt();f.rejected_without_house_mutation()
    def test_material_bijection_evidence_missing_rejects(self):
        f=self.f;f.receipt['native_assets']['SM_FeedSack_Jute_01']['material_id_bijection_verified']=False;f.write_receipt();f.rejected_without_house_mutation()
    def test_missing_material_faces_rejects(self):
        f=self.f;f.receipt['native_assets']['SM_FeedSack_Jute_01']['material_triangle_counts']={'0':19644,'1':0};f.write_receipt();f.rejected_without_house_mutation()
    def test_nested_checkpoint_drift_rejects_without_house_write(self):
        f=self.f;(f.source/'SourceCheckpoint/PhotorealFeedSackV1_Source.blend').write_bytes(b'changed checkpoint');f.rejected_without_house_mutation()
    def test_nested_dependency_escape_rejects(self):
        f=self.f;p=f.source/'ExportIteration/source_export_handoff.json';d=json.loads(p.read_text());d['files']['../../outside']=next(iter(d['files'].values()));p.write_text(json.dumps(d));f.rejected_without_house_mutation()
    def test_wicker_basket_native_reference_preserved(self):
        f=self.f;d=C.rewrite_house(f.document,f.plan)
        self.assertEqual(d['elements'],f.document['elements'])
        self.assertIn('PhotorealBasketV1',d['elements'][0]['mesh'])
    def test_duplicate_shared_texture_role_rejects(self):
        f=self.f;p=f.source/'ExportIteration/Export/manifest.json';d=json.loads(p.read_text());d['assets'][0]['textures'].append(copy.deepcopy(d['assets'][0]['textures'][0]));p.write_text(json.dumps(d))
        h=f.source/'ExportIteration/source_export_handoff.json';v=json.loads(h.read_text());v['files']['Export/manifest.json']=C.sha(p);h.write_text(json.dumps(v));f.rejected_without_house_mutation()

class ActualMaterialTriangleMatching(unittest.TestCase):
    @staticmethod
    def triangle(z):return [([0,0,z],[0,0],[0,0,0]),([1,0,z],[1,0],[0,0,0]),([0,1,z],[0,1],[0,0,0])]
    def test_reordered_geometry_joins_matching_source_material_ids(self):
        a,b=self.triangle(0),self.triangle(3)
        r=C.match_oriented_triangles([b,a],[a,b],native_material_ids=[1,0],source_material_ids=[0,1])
        self.assertEqual([x['source_index']for x in r['matches']],[1,0])
    def test_same_geometry_count_and_two_slots_but_swapped_faces_reject(self):
        a,b=self.triangle(0),self.triangle(3)
        with self.assertRaises(ValueError):C.match_oriented_triangles([a,b],[a,b],native_material_ids=[1,0],source_material_ids=[0,1])
    def test_missing_per_triangle_material_coverage_rejects(self):
        a,b=self.triangle(0),self.triangle(3)
        with self.assertRaises(ValueError):C.match_oriented_triangles([a,b],[a,b],native_material_ids=[0],source_material_ids=[0,1])

class NativeMaterialBindingBridge(unittest.TestCase):
    def fixture(self):
        return {'schema':'dink-static-mesh-material-bindings/1','valid':True,
                'slots':[{'slot_index':i,'slot_name':n,'imported_slot_name':n}for i,n in enumerate(C.MATERIAL_NAMES)],
                'groups':[{'polygon_group_id':g,'slot_index':i,'imported_slot_name':n}for g,i,n in zip([7,19],[0,1],C.MATERIAL_NAMES)],
                'triangles':[{'triangle_id':0,'polygon_group_id':19,'slot_index':1},{'triangle_id':1,'polygon_group_id':7,'slot_index':0}]}
    def test_sparse_group_ids_resolve_by_names_not_as_material_indexes(self):
        self.assertEqual(C.validated_material_bindings(self.fixture(),[19,7]),[1,0])
    def test_invalid_bridge_result_rejects(self):
        d=self.fixture();d['valid']=False
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_missing_group_name_rejects(self):
        d=self.fixture();d['groups'][0]['imported_slot_name']='None'
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_ambiguous_imported_slot_names_reject(self):
        d=self.fixture();d['slots'][1]['imported_slot_name']=C.MATERIAL_NAMES[0]
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_group_slot_claim_disagrees_with_actual_name_rejects(self):
        d=self.fixture();d['groups'][0]['slot_index']=1
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_bridge_group_ids_disagree_with_mesh_description_reject(self):
        with self.assertRaises(ValueError):C.validated_material_bindings(self.fixture(),[7,19])
    def test_triangle_slot_claim_disagrees_with_group_rejects(self):
        d=self.fixture();d['triangles'][0]['slot_index']=0
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_duplicate_triangle_ids_reject(self):
        d=self.fixture();d['triangles'][1]['triangle_id']=0
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_missing_triangle_binding_rejects(self):
        d=self.fixture();d['triangles'].pop()
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_duplicate_group_ids_reject(self):
        d=self.fixture();d['groups'][1]['polygon_group_id']=7
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_duplicate_slot_indices_reject(self):
        d=self.fixture();d['slots'][1]['slot_index']=0
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])
    def test_boolean_native_ids_reject(self):
        d=self.fixture();d['slots'][0]['slot_index']=False
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7])

    def test_query_from_wrong_mesh_rejects(self):
        with self.assertRaises(ValueError):C.validated_material_bindings(self.fixture(),[19,7],'/Game/Wrong.Wrong')
    def test_query_from_wrong_lod_rejects(self):
        d=self.fixture();d['mesh']='/Game/Right.Right';d['lod']=1
        with self.assertRaises(ValueError):C.validated_material_bindings(d,[19,7],'/Game/Right.Right')
