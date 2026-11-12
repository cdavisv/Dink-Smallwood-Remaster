"""Source-derived actual graph doubles: F0, soot alpha, hidden inputs, read-only proof."""
from pathlib import Path
import sys,unittest,copy,importlib.util
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'Scripts/RoofNative'))
from fireplace_contract import load_contract
from fireplace_material import build_graph
from fireplace_material_readback import inspect_graph
spec=importlib.util.spec_from_file_location('fireplace_native_graph_stub',P/'Scripts/tests/test_house439_material_readback.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
class FireplaceGraphReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.contract=load_contract(P)
    def construct(self,name):
        r=copy.deepcopy(next(r for r in self.contract['materials']if r['source_material']=='MI_Shared_'+name));r['source_graph_reviewed']=True;m=F.Material(r['package']);textures={n:F.Texture(p)for n,p in r['textures'].items()};F.Engine.textures={t.path:t for t in textures.values()};build_graph(F.Engine,m,r,r['source_graph'],textures,lambda:None);return m,r
    def test_all_seven_saved_graph_doubles_match(self):
        for r in self.contract['materials']:
            with self.subTest(role=r['source_material']):m,r=self.construct(r['source_material'].removeprefix('MI_Shared_'));self.assertTrue(inspect_graph(F.Engine,m,r)['passed'])
    def test_reader_has_no_native_mutations(self):
        m,r=self.construct('FiredClay2m');before=F.Material.mutations;inspect_graph(F.Engine,m,r);self.assertEqual(before,F.Material.mutations)
    def test_wrong_clay_point_five_refused(self):
        m,r=self.construct('FiredClay2m');m.outputs[F.Property.MP_SPECULAR][0].props['r']=.5
        with self.assertRaises(ValueError):inspect_graph(F.Engine,m,r)
    def test_wrong_oak_specular_refused(self):
        m,r=self.construct('OakLonggrain2m');m.outputs[F.Property.MP_SPECULAR][0].props['r']=.5
        with self.assertRaises(ValueError):inspect_graph(F.Engine,m,r)
    def test_alpha_mask_connected_to_opacity_refused(self):
        m,r=self.construct('FiredClay2m');v=next(n for n in m.nodes if n.KIND=='VertexColor');m.outputs[F.Property.MP_OPACITY]=(v,'A')
        with self.assertRaises(ValueError):inspect_graph(F.Engine,m,r)
    def test_rgb_replacing_soot_alpha_refused(self):
        m,r=self.construct('FiredClay2m');n=next(n for n in m.nodes if n.KIND=='LinearInterpolate');v,_=n.inputs['Alpha'];n.inputs['Alpha']=(v,'RGB')
        with self.assertRaises(ValueError):inspect_graph(F.Engine,m,r)
    def test_uv1_native_v_decode_bypass_refused(self):
        m,r=self.construct('IronLead2m');a=next(n for n in m.nodes if n.KIND=='AppendVector');minus=a.inputs['B'][0];a.inputs['B']=minus.inputs['None']
        with self.assertRaises(ValueError):inspect_graph(F.Engine,m,r)
    def test_wrong_normal_sampler_refused(self):
        m,r=self.construct('FiredClayMasonry2m');n=next(n for n in m.nodes if n.KIND=='TextureSample'and n.props['sampler_type']=='normal');n.props['sampler_type']='color'
        with self.assertRaises(ValueError):inspect_graph(F.Engine,m,r)
if __name__=='__main__':unittest.main()
