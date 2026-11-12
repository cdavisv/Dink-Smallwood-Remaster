"""Evaluate the ACTUAL constructed node graph for synthetic texel/native-UV inputs.
This catches a semantic FBX V-convention error, not native API/render correctness.
"""
from pathlib import Path
import json,sys,unittest,math
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Scripts/RoofNative'))
from house439_opaque_material import build_graph
GRAPH=json.loads((ROOT/'SourceAssets/Art/Stonebrook/Refinements/House439SharedExteriorV1/OPAQUE_GRAPH_SOURCE.json').read_text())['materials']['MI_Shared_LimeMortarSoot2m']
PINS={'ComponentMask':['None'],'TextureSample':['UVs'],'OneMinus':['None'],
      'AppendVector':['A','B'],'If':['A','B','A > B','A == B','A < B'],
      'LinearInterpolate':['A','B','Alpha'],'Multiply':['A','B'],'Add':['A','B'],
      'Normalize':['VectorInput'],'Clamp':['None','Min','Max']}
class Node:
    def __init__(self,kind):self.kind=kind;self.props={};self.inputs={}
    def set_editor_property(self,key,value):self.props[key]=value
class Texture:
    def __init__(self,name):self.name=name
    def get_path_name(self):return '/Game/Test/'+Path(self.name).stem+'.'+Path(self.name).stem
class Material:
    def __init__(self):self.props={};self.nodes=[];self.outputs={}
    def get_path_name(self):return '/Game/Test/Material.Material'
    def set_editor_property(self,key,value):self.props[key]=value
class Editor:
    @staticmethod
    def get_material_expressions(m):return m.nodes
    @staticmethod
    def create_material_expression(m,cls):
        n=Node(cls);n.material=m;m.nodes.append(n);return n
    @staticmethod
    def get_material_expression_input_names(n):return PINS.get(n.kind,[])
    @staticmethod
    def connect_material_expressions(a,out,b,pin):
        if pin=='':pin=PINS[b.kind][0]
        if pin not in PINS[b.kind]:return False
        b.inputs[pin]=(a,out);return True
    @staticmethod
    def connect_material_property(a,out,prop):a.material.outputs[prop]=(a,out);return True
    @staticmethod
    def recompile_material(m):pass
class Engine:
    MaterialEditingLibrary=Editor
    MaterialSamplerType=SimpleNamespace(SAMPLERTYPE_COLOR='color',SAMPLERTYPE_NORMAL='normal',SAMPLERTYPE_MASKS='masks')
    MaterialProperty=SimpleNamespace(**{k:k for k in ['MP_BASE_COLOR','MP_ROUGHNESS','MP_METALLIC','MP_NORMAL','MP_SPECULAR']})
    BlendMode=SimpleNamespace(BLEND_OPAQUE='opaque');MaterialShadingModel=SimpleNamespace(MSM_DEFAULT_LIT='lit')
    @staticmethod
    def LinearColor(r,g,b,a):return(r,g,b,a)
for kind in ['TextureCoordinate','ComponentMask','TextureSample','OneMinus','AppendVector','If','LinearInterpolate','Multiply','Add','Normalize','Clamp','Constant','Constant3Vector','VertexColor']:
    setattr(Engine,'MaterialExpression'+kind,kind)
def vector_op(a,b,fn):
    if isinstance(a,tuple)or isinstance(b,tuple):
        width=len(a)if isinstance(a,tuple)else len(b);aa=a if isinstance(a,tuple)else(a,)*width;bb=b if isinstance(b,tuple)else(b,)*width;return tuple(fn(x,y)for x,y in zip(aa,bb))
    return fn(a,b)
def evaluate(m,prop,source_u,bias):
    def run(edge):
        n,out=edge;k=n.kind;p=n.props
        def v(pin):return run(n.inputs[pin])
        if k=='TextureCoordinate':r=(source_u,1-bias)if p['coordinate_index']==1 else(.2,.3)
        elif k=='ComponentMask':
            value=v('None');r=tuple(value[i]for i,key in enumerate(['r','g','b','a'])if p.get(key));r=r[0]if len(r)==1 else r
        elif k=='Constant':r=p['r']
        elif k=='Constant3Vector':r=p['constant'][:3]
        elif k=='VertexColor':r=(.44,.41,.35)
        elif k=='TextureSample':
            name=p['texture'].name
            r=(0.,0.,1.)if '_N_GL'in name else(1.,.96 if '_Lime_'in name else .995,0.)if '_ORM'in name else(.5,.5,.5)
        elif k=='OneMinus':r=vector_op(1.,v('None'),lambda x,y:x-y)
        elif k=='AppendVector':
            a=v('A');b=v('B');r=(a if isinstance(a,tuple)else(a,))+(b if isinstance(b,tuple)else(b,))
        elif k=='If':
            a=v('A');b=v('B');r=v('A > B')if a>b else v('A < B')if a<b else v('A == B')
        elif k=='LinearInterpolate':
            a=v('A');b=v('B');f=v('Alpha');r=vector_op(a,b,lambda x,y:x*(1-f)+y*f)
        elif k=='Multiply':r=vector_op(v('A'),v('B'),lambda x,y:x*y)
        elif k=='Add':r=vector_op(v('A'),v('B'),lambda x,y:x+y)
        elif k=='Clamp':r=min(v('Max'),max(v('Min'),v('None')))
        elif k=='Normalize':
            value=v('VectorInput');length=math.sqrt(sum(x*x for x in value));r=tuple(x/length for x in value)
        else:raise AssertionError(k)
        if out=='RGB':return r[:3]
        return r
    return run(m.outputs[prop])
class OpaqueSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.material=Material();images=[n['image']['name']for n in GRAPH['nodes']if n['type']=='TEX_IMAGE'];textures={name:Texture(name)for name in images};recipe={'source_graph_reviewed':True,'uv1_semantic_decode':'U,1-V','package':'/Game/Test/Material','textures':{name:'/Game/Test/'+Path(name).stem for name in images}};build_graph(Engine,cls.material,recipe,GRAPH,textures,lambda:None)
    def test_lime_negative_bias_survives_import_V_flip(self):self.assertAlmostEqual(evaluate(self.material,'MP_ROUGHNESS',0.,-.01),.95,places=6)
    def test_lime_positive_bias_survives_import_V_flip(self):self.assertAlmostEqual(evaluate(self.material,'MP_ROUGHNESS',0.,.01),.97,places=6)
    def test_selector_threshold_and_soot_clamp(self):
        self.assertAlmostEqual(evaluate(self.material,'MP_ROUGHNESS',.5,-.01),.95,places=6)
        self.assertAlmostEqual(evaluate(self.material,'MP_ROUGHNESS',1.,-.01),.985,places=6)
        self.assertEqual(evaluate(self.material,'MP_ROUGHNESS',1.,.01),1.)
    def test_linear_vertex_tint_unchanged(self):
        for a,b in zip(evaluate(self.material,'MP_BASE_COLOR',0.,-.01),(.22,.205,.175)):self.assertAlmostEqual(a,b,places=6)
if __name__=='__main__':unittest.main()
