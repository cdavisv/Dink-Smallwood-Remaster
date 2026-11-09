"""FeedSack-specific identity, metal, owned-module and safe native-getter regressions."""
import copy,json,math,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import feedsack_contract as C
import test_feedsack_publication as fixtures

class FeedSackPublicationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationTests('test_dry_run_zero_writes');self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_only_two_mesh_references_change_and_semantic_reverse_is_exact(self):
        f=self.f;new=C.rewrite_house(f.document,f.plan)
        self.assertEqual(C.rewrite_house(new,f.plan,from_new=True),f.document)
        def diff(a,b):
            if type(a)!=type(b):return 1
            if isinstance(a,dict):return sum(diff(a[k],b[k])for k in a)
            if isinstance(a,list):return sum(diff(x,y)for x,y in zip(a,b))
            return int(a!=b)
        self.assertEqual(diff(f.document,new),2)
        result=f.run_publish(True);self.assertEqual((result['changed_mesh_references'],result['asset_rows'],result['instance_rows']),(2,1,1))
    def test_feedsack_names_and_exact_reference_counts_reject_duplicates_and_replacements(self):
        f=self.f
        for kind in ['renamed','extra','replacement','mixed']:
            d=copy.deepcopy(f.document)
            if kind=='renamed':d['replacements'][0]['origin']='S001_P22'
            if kind=='extra':d['replacements'].append(copy.deepcopy(d['replacements'][0]))
            if kind=='replacement':d['replacements'].append({'mesh':f.plan['assets'][0]['old'],'origin':'S001_P22'})
            if kind=='mixed':d['assets'][0]['mesh']=C.object_path(f.plan['assets'][0]['mesh'])
            with self.subTest(kind=kind),self.assertRaises(ValueError):C.publication_state(d,f.plan)
    def test_custom_module_change_after_verification_rejects(self):
        f=self.f;p=f.root/'Plugins/DinkImport/Binaries/Linux/libUnrealEditor-DinkImport.so';p.parent.mkdir(parents=True);p.write_bytes(b'new unverified native helper')
        f.rejected_without_house_mutation()
    def test_custom_module_late_change_rejects_atomic_publish(self):
        f=self.f;p=f.root/'Binaries/Linux/libUnrealEditor-DinkRemaster.so';p.parent.mkdir(parents=True);p.write_bytes(b'initial verified module');f.receipt['module_sha256']=C.module_pins(f.root);f.write_receipt();original=C.module_pins;counter=[0]
        def racing(root):
            counter[0]+=1
            if counter[0]==3:p.write_bytes(b'changed while publication was concrete')
            return original(root)
        with patch.object(C,'module_pins',side_effect=racing):f.rejected_without_house_mutation()
        self.assertGreaterEqual(counter[0],3)
    def test_symlinked_module_is_rejected(self):
        f=self.f;p=f.root/'Binaries/Linux/libUnrealEditor-DinkRemaster.so';p.parent.mkdir(parents=True);target=Path(f.temp.name)/'foreign.so';target.write_bytes(b'foreign module');p.symlink_to(target)
        with self.assertRaises(ValueError):C.module_pins(f.root)
    def test_source_hull_dimensions_must_be_exact_original_box(self):
        f=self.f
        with patch.object(C,'source_hulls',return_value=[[[x,y,z]for x in [-44.,44.]for y in [-44.,44.]for z in [0,61.]]]):
            with self.assertRaisesRegex(ValueError,'UCX box'):C.load_plan(f.source,check_pixels=False)
    def test_mesh_manifest_bounds_and_pivot_are_original(self):
        f=self.f;manifest=f.source/'ExportIteration/Export/manifest.json';frozen=f.source/'ExportIteration/source_export_handoff.json'
        data=json.loads(manifest.read_text());data['assets'][0]['bounds_cm']['unreal_min_cm'][2]=1.;manifest.write_text(json.dumps(data));doc=json.loads(frozen.read_text());doc['files']['Export/manifest.json']=C.sha(manifest);frozen.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'pivot/bounds'):C.load_plan(f.source,check_pixels=False)

class MetallicTests(unittest.TestCase):
    def test_entirely_dielectric_and_neutral_AO(self):
        v=C.validate_orm_pixels(bytes([255,0,0,255,201,0]));self.assertEqual(v['metallic_max'],0);self.assertEqual(v['dielectric_texels'],2)
    def test_empty_metal_wrong_AO_or_shape_reject(self):
        for raw in [b'',bytes([255,100,1]),bytes([255,100,240]),bytes([254,100,0]),b'aa']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):C.validate_orm_pixels(raw)

class SpecularTests(unittest.TestCase):
    def test_f0_conversion_and_float32_source_tolerance(self):
        self.assertAlmostEqual(C.source_to_ue_specular(),C.UE_SPECULAR,places=15)
        self.assertTrue(C.valid_native_specular(C.source_to_ue_specular(1.4600000381469727,.22)))
        self.assertAlmostEqual(C.source_to_ue_specular(1.5,.5),.5,places=14)
    def test_direct_source_level_or_barrel_constant_reject(self):
        for v in [.25,.35,0.,1.,float('nan'),float('inf'),True,None,'0.21853724634807323']:
            with self.subTest(value=v):self.assertFalse(C.valid_native_specular(v))
    def test_native_roundtrip_tolerance_is_explicit(self):
        self.assertTrue(C.valid_native_specular(C.UE_SPECULAR+0.99e-6))
        self.assertFalse(C.valid_native_specular(C.UE_SPECULAR+1.01e-6))
    def test_nonfinite_or_out_of_domain_source_optics_reject(self):
        for i,l in [(1.,.25),(0.,.25),(float('nan'),.25),(1.46,float('inf')),(1.46,-.1),(1.46,1.1),(True,.25),(100.,1.)]:
            with self.subTest(ior=i,level=l),self.assertRaises(ValueError):C.source_to_ue_specular(i,l)

class ID:
    def __init__(self,id_value):self.value=id_value
    def get_editor_property(self,name):assert name=='id_value';return self.value
class Desc:
    def __init__(self):self.valid_vertices={0,1,2};self.valid_triangles={0};self.valid_instances={0,1,2};self.position_calls=[];self.uv_calls=[];self.corner_vertices=[0,1,2];self.uv_bad=False
    def get_vertex_count(self):return 3
    def get_triangle_count(self):return 1
    def is_vertex_valid(self,v):return v.value in self.valid_vertices
    def is_triangle_valid(self,t):return t.value in self.valid_triangles
    def is_vertex_instance_valid(self,v):return v.value in self.valid_instances
    def get_vertex_position(self,v):assert self.is_vertex_valid(v);self.position_calls.append(v.value);return [SimpleNamespace(x=0,y=0,z=0),SimpleNamespace(x=1,y=0,z=0),SimpleNamespace(x=0,y=1,z=0)][v.value]
    def get_triangle_vertex_instances(self,t):assert self.is_triangle_valid(t);return [ID(i)for i in range(3)]
    def get_vertex_instance_vertex(self,v):assert self.is_vertex_instance_valid(v);return ID(self.corner_vertices[v.value])
    def get_vertex_instance_uv(self,v,channel):self.uv_calls.append(v.value);return SimpleNamespace(x=float('nan')if self.uv_bad else .25,y=.5)
    def get_triangle_polygon_group(self,t):return ID(0)
class NativeGetterSafetyTests(unittest.TestCase):
    def test_valid_dense_actual_getter_shape_reads(self):
        p,t,g=C.read_native_geometry(Desc(),ID,ID);self.assertEqual((len(p),len(t),g),(3,1,{0}))
    def test_sparse_vertex_rejected_before_position_getter(self):
        d=Desc();d.valid_vertices.remove(1)
        with self.assertRaisesRegex(ValueError,'sparse vertex'):C.read_native_geometry(d,ID,ID)
        self.assertEqual(d.position_calls,[0])
    def test_sparse_triangle_rejected_before_triangle_getters(self):
        d=Desc();d.valid_triangles.clear()
        with self.assertRaisesRegex(ValueError,'sparse triangle'):C.read_native_geometry(d,ID,ID)
        self.assertFalse(d.uv_calls)
    def test_invalid_corner_instance_rejected_before_index_getters(self):
        d=Desc();d.valid_instances.remove(1)
        with self.assertRaisesRegex(ValueError,'corner instances'):C.read_native_geometry(d,ID,ID)
        self.assertFalse(d.uv_calls)
    def test_out_of_bounds_corner_vertex_rejected_before_point_index_orUV(self):
        d=Desc();d.valid_vertices.add(999);d.corner_vertices[0]=999
        with self.assertRaisesRegex(ValueError,'corner vertex'):C.read_native_geometry(d,ID,ID)
        self.assertFalse(d.uv_calls)
    def test_nonfinite_native_UV_rejects(self):
        d=Desc();d.uv_bad=True
        with self.assertRaisesRegex(ValueError,'Nonfinite native UV'):C.read_native_geometry(d,ID,ID)

if __name__=='__main__':unittest.main()
