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
    def construct(self,name,engine=F.Engine):
        r=copy.deepcopy(next(r for r in self.contract['materials']if r['source_material']=='MI_Shared_'+name));r['source_graph_reviewed']=True;m=F.Material(r['package']);textures={n:F.Texture(p)for n,p in r['textures'].items()};F.Engine.textures={t.path:t for t in textures.values()};build_graph(engine,m,r,r['source_graph'],textures,lambda:None);return m,r
    def test_installed_vertex_output_rules_reject_rgb_and_preserve_texture_rgb(self):
        m=F.Material('/Game/Test/OutputRules');v=F.Editor.create_material_expression(m,F.Engine.MaterialExpressionVertexColor);t=F.Editor.create_material_expression(m,F.Engine.MaterialExpressionTextureSample);dest=F.Editor.create_material_expression(m,F.Engine.MaterialExpressionMultiply)
        self.assertFalse(InstalledOutputEditor.connect_material_expressions(v,'RGB',dest,'A'))
        self.assertTrue(InstalledOutputEditor.connect_material_expressions(v,'',dest,'A'))
        self.assertEqual(InstalledOutputEditor.get_input_node_output_name_for_material_expression(dest,v),'')
        self.assertTrue(InstalledOutputEditor.connect_material_expressions(v,'A',dest,'A'))
        self.assertEqual(InstalledOutputEditor.get_input_node_output_name_for_material_expression(dest,v),'A')
        self.assertTrue(InstalledOutputEditor.connect_material_expressions(t,'RGB',dest,'A'))
        self.assertEqual(InstalledOutputEditor.get_input_node_output_name_for_material_expression(dest,t),'RGB')
    def test_all_seven_construct_and_read_back_with_installed_vertex_output_rules(self):
        for r in self.contract['materials']:
            with self.subTest(role=r['source_material']):
                m,r=self.construct(r['source_material'].removeprefix('MI_Shared_'),InstalledOutputEngine)
                self.assertTrue(inspect_graph(InstalledOutputEngine,m,r)['passed'])
    def test_noncanonical_vertex_rgb_readback_refuses(self):
        m,r=self.construct('FiredClay2m',InstalledOutputEngine)
        for node in m.nodes:
            for pin,(parent,out)in node.inputs.items():
                if parent.KIND=='VertexColor'and out=='':
                    node.inputs[pin]=(parent,'RGB')
                    with self.assertRaises(ValueError):inspect_graph(InstalledOutputEngine,m,r)
                    return
        self.fail('Actual clay graph lacks expected VertexColor RGB edge')
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

# MaterialExpressions.cpp:10022 declares VertexColor outputs unnamed with masks
# RGB/R/G/B/A. MaterialEditingLibrary.cpp:81 resolves empty to first output and
# unnamed single channels by mask; RGB is not an accepted named output. Its
# GetExpressionOutputName at1159 returns empty for the first multi-channel mask.
VERTEX_MASKS=[(True,True,True,False),(True,False,False,False),(False,True,False,False),(False,False,True,False),(False,False,False,True)]
def vertex_output_index(name):
    if name=='':return 0
    for index,mask in enumerate(VERTEX_MASKS):
        if sum(mask)==1 and name=='RGBA'[mask.index(True)]:return index
    return None
class InstalledOutputEditor(F.Editor):
    @staticmethod
    def connect_material_expressions(a,out,b,pin):
        if a.KIND=='VertexColor' and vertex_output_index(out)is None:return False
        return F.Editor.connect_material_expressions(a,out,b,pin)
    @staticmethod
    def get_input_node_output_name_for_material_expression(parent,child):
        out=F.Editor.get_input_node_output_name_for_material_expression(parent,child)
        if child.KIND!='VertexColor':return out
        index=vertex_output_index(out)
        if index is None:return(False,'')
        mask=VERTEX_MASKS[index]
        return 'RGBA'[mask.index(True)]if sum(mask)==1 else''
class InstalledOutputEngine(F.Engine):
    MaterialEditingLibrary=InstalledOutputEditor
if __name__=='__main__':unittest.main()
