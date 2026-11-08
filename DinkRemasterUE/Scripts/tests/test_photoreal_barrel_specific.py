"""Barrel-specific identity, metal, owned-module and safe native-getter regressions."""
import copy,json,math,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import barrel_contract as C
import test_photoreal_barrel_publication as fixtures

class BarrelPublicationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationTests('test_dry_run_zero_writes');self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_only_three_mesh_references_change_and_semantic_reverse_is_exact(self):
        f=self.f;new=C.rewrite_house(f.document,f.plan)
        self.assertEqual(C.rewrite_house(new,f.plan,from_new=True),f.document)
        def diff(a,b):
            if type(a)!=type(b):return 1
            if isinstance(a,dict):return sum(diff(a[k],b[k])for k in a)
            if isinstance(a,list):return sum(diff(x,y)for x,y in zip(a,b))
            return int(a!=b)
        self.assertEqual(diff(f.document,new),3)
        result=f.run_publish(True);self.assertEqual((result['changed_mesh_references'],result['asset_rows'],result['instance_rows']),(3,1,2))
    def test_barrel_names_and_exact_reference_counts_reject_duplicates_and_replacements(self):
        f=self.f
        for kind in ['renamed','extra','replacement','mixed']:
            d=copy.deepcopy(f.document)
            if kind=='renamed':d['elements'][0]['name']='WrongBarrel'
            if kind=='extra':d['elements'].append(copy.deepcopy(d['elements'][0]))
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
        with patch.object(C,'source_hulls',return_value=[[[x,y,z]for x in [-37.5,37.5]for y in [-37.5,37.5]for z in [0,101.]]]):
            with self.assertRaisesRegex(ValueError,'UCX75'):C.load_plan(f.source,check_pixels=False)
    def test_mesh_manifest_bounds_and_pivot_are_original(self):
        f=self.f;manifest=f.source/'Export/manifest.json';frozen=f.source/'final_handoff.json'
        data=json.loads(manifest.read_text());data['assets'][0]['bounds_cm']['unreal_min_cm'][2]=1.;manifest.write_text(json.dumps(data));doc=json.loads(frozen.read_text());doc['frozen_files']['Export/manifest.json']=C.sha(manifest);frozen.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'ground-center'):C.load_plan(f.source,check_pixels=False)

class MetallicTests(unittest.TestCase):
    def test_real_metal_range_retained_with_wood_zero(self):
        p=bytes([255,130,0,255,120,240,255,180,73]);v=C.validate_orm_pixels(p);self.assertEqual(v['metallic_max'],240);self.assertEqual(v['wood_zero_metal_texels'],1)
    def test_all_dielectric_all_metal_wrong_AO_or_range_reject(self):
        for raw in [b'',bytes([255,100,0]*2),bytes([255,100,240]*2),bytes([254,100,0,255,100,240]),bytes([255,100,0,255,100,255]),b'aa']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):C.validate_orm_pixels(raw)

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
