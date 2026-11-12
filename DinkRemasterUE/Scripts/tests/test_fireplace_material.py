"""Actual frozen source DAG -> constructed native-graph semantics; no Unreal imports."""
from pathlib import Path
import sys,json,unittest,copy,importlib.util
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'Scripts/RoofNative'))
from fireplace_material import build_graph,validate_graph,ROLE_SPEC
spec=importlib.util.spec_from_file_location('fireplace_graph_stub',P/'Scripts/tests/test_house439_opaque_semantics.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
GRAPHS=json.loads((P/'Docs/Verification/FireplaceNativePreparation/ACTUAL_SOURCE_GRAPHS.json').read_text())['materials']
class Texture(F.Texture):
    def get_path_name(self):
        name=self.name.split('.png')[0];return '/Game/Test/'+name+'.'+name

def constructed(role):
    m=F.Material();g=GRAPHS[role];images=[n['image']['name']for n in g['nodes']if n['type']=='TEX_IMAGE'];textures={name:Texture(name)for name in images};recipe=dict(package='/Game/Test/Material',source_material=role,textures={name:'/Game/Test/'+name.split('.png')[0] for name in images},source_graph_reviewed=True,uv1_semantic_decode='U,1-V',implicit_image_vector='UV0');build_graph(F.Engine,m,recipe,g,textures,lambda:None);return m

def evaluate(m,prop,rgba=(.8,.6,.5,.4),selector=0.,return_uv=False):
    def vec(a,b,fn):return F.vector_op(a,b,fn)
    def run(edge):
        n,out=edge;k=n.kind;p=n.props
        def v(pin):return run(n.inputs[pin])
        if k=='TextureCoordinate':r=(selector,1.)if p['coordinate_index']==1 else(.2,.3)
        elif k=='ComponentMask':
            a=v('None');r=tuple(a[i]for i,key in enumerate(['r','g','b','a'])if p.get(key));r=r[0]if len(r)==1 else r
        elif k=='Constant':r=p['r']
        elif k=='Constant3Vector':r=p['constant'][:3]
        elif k=='VertexColor':r=rgba[3]if out=='A'else rgba[:3]
        elif k=='TextureSample':
            uv=v('UVs')
            if return_uv:return uv
            name=p['texture'].name;soot='Soot2m'in name
            r=(-.1,.05,.99)if soot and'_N_GL'in name else(.2,.1,.97)if'_N_GL'in name else(1.,.97 if soot else .83,0.)if'_ORM'in name else(.018,.015,.012)if soot else(.4,.25,.12)
        elif k=='OneMinus':r=vec(1.,v('None'),lambda a,b:a-b)
        elif k=='AppendVector':
            a,b=v('A'),v('B');r=(a if isinstance(a,tuple)else(a,))+(b if isinstance(b,tuple)else(b,))
        elif k=='If':r=v('A > B')if v('A')>v('B')else v('A < B')if v('A')<v('B')else v('A == B')
        elif k=='LinearInterpolate':r=vec(v('A'),v('B'),lambda a,b:a*(1-v('Alpha'))+b*v('Alpha'))
        elif k=='Multiply':r=vec(v('A'),v('B'),lambda a,b:a*b)
        elif k=='Add':r=vec(v('A'),v('B'),lambda a,b:a+b)
        elif k=='Normalize':
            a=v('VectorInput');length=sum(x*x for x in a)**.5;r=tuple(x/length for x in a)
        else:raise AssertionError(k)
        return r[:3]if out=='RGB'else r
    return run(m.outputs[prop])
class FiredClayMaterialTests(unittest.TestCase):
    def test_all_seven_actual_source_graphs_construct(self):
        for name in GRAPHS:
            with self.subTest(role=name):self.assertTrue(constructed(name).nodes)
    def test_exact_per_role_specular(self):
        for role,value in ROLE_SPEC.items():self.assertAlmostEqual(evaluate(constructed(role),'MP_SPECULAR'),value,places=7)
    def test_clay_not_house_point_five(self):
        g=copy.deepcopy(GRAPHS['MI_Shared_FiredClay2m']);n=next(n for n in g['nodes']if n['type']=='BSDF_PRINCIPLED');next(i for i in n['inputs']if i['name']=='Specular IOR Level')['value']=.5
        with self.assertRaises(ValueError):validate_graph(g,'MI_Shared_FiredClay2m')
    def test_alpha_soot_mix_and_roughness(self):
        for name in ['MI_Shared_FiredClay2m','MI_Shared_FiredClayMasonry2m']:
            m=constructed(name);actual=evaluate(m,'MP_BASE_COLOR');expected=[(.4*.8)*.6+.018*.4,(.25*.6)*.6+.015*.4,(.12*.5)*.6+.012*.4]
            for a,b in zip(actual,expected):self.assertAlmostEqual(a,b)
            rough=evaluate(m,'MP_ROUGHNESS');self.assertAlmostEqual(rough,.83*.6+.97*.4)
    def test_alpha_does_not_drive_opacity(self):
        m=constructed('MI_Shared_FiredClay2m');self.assertEqual(m.props['blend_mode'],'opaque');self.assertNotIn('MP_OPACITY',m.outputs);self.assertEqual(evaluate(m,'MP_METALLIC'),0.)
    def test_unlinked_texture_vector_is_active_uv_not_zero_constant(self):
        for name in ['MI_Shared_OakLonggrain2m','MI_Shared_LimeMortar2m','MI_Shared_Soot2m']:
            m=constructed(name)
            for node in m.nodes:
                if node.kind=='TextureSample':self.assertEqual(node.inputs['UVs'][0].kind,'TextureCoordinate');self.assertEqual(node.inputs['UVs'][0].props['coordinate_index'],0)
    def test_unknown_lobe_and_private_attribute_refuse(self):
        for prop in ['Transmission Weight','Coat Weight']:
            g=copy.deepcopy(GRAPHS['MI_Shared_FiredClay2m']);n=next(n for n in g['nodes']if n['type']=='BSDF_PRINCIPLED');next(i for i in n['inputs']if i['name']==prop)['value']=1
            with self.assertRaises(ValueError):validate_graph(g,'MI_Shared_FiredClay2m')
        g=copy.deepcopy(GRAPHS['MI_Shared_FiredClay2m']);next(n for n in g['nodes']if n['type']=='VERTEX_COLOR')['layer_name']='PrivateFireplace'
        with self.assertRaises(ValueError):validate_graph(g,'MI_Shared_FiredClay2m')
    def test_opacity_connection_refused(self):
        g=copy.deepcopy(GRAPHS['MI_Shared_FiredClay2m']);n=next(n for n in g['nodes']if n['type']=='BSDF_PRINCIPLED');next(i for i in n['inputs']if i['name']=='Alpha')['linked']=True
        with self.assertRaises(ValueError):validate_graph(g,'MI_Shared_FiredClay2m')
if __name__=='__main__':unittest.main()
