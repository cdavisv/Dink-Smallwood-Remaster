"""Corrupt constructed source-derived graph doubles; no Unreal execution claim."""
from pathlib import Path
import sys,json,unittest,copy
from enum import IntEnum
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Scripts/RoofNative'))
from house439_opaque_material import build_graph as opaque
from house439_glass_material import build_graph as glass
from house439_material_readback import inspect_graph
PINS={'ComponentMask':['None'],'TextureSample':['UVs'],'OneMinus':['None'],'AppendVector':['A','B'],'If':['A','B','A > B','A == B','A < B'],'LinearInterpolate':['A','B','Alpha'],'Multiply':['A','B'],'Add':['A','B'],'Normalize':['VectorInput'],'Clamp':['None','Min','Max'],'ThinTranslucentMaterialOutput':['TransmittanceColor','SurfaceCoverage']}
class Property(IntEnum):
    MP_BASE_COLOR=0;MP_ROUGHNESS=1;MP_METALLIC=2;MP_NORMAL=3;MP_SPECULAR=4;MP_OPACITY=5;MP_EMISSIVE_COLOR=6
class Texture:
    def __init__(self,path):self.path=path
    def get_path_name(self):return self.path+'.'+self.path.rsplit('/',1)[-1]
class Material:
    mutations=0
    def __init__(self,path):self.path=path;self.props={'material_domain':'surface','dither_opacity_mask':False};self.nodes=[];self.outputs={}
    def get_path_name(self):return self.path+'.'+self.path.rsplit('/',1)[-1]
    def set_editor_property(self,key,value):Material.mutations+=1;self.props[key]=value
    def get_editor_property(self,key):return self.props[key]
class Node:
    KIND=''
    def __init__(self,material):self.material=material;self.props={'sampler_source':'from_asset','mip_value_mode':'none','u_tiling':1.,'v_tiling':1.,'un_mirror_u':False,'un_mirror_v':False};self.inputs={};self.path=material.get_path_name()+':'+str(len(material.nodes))
    def set_editor_property(self,key,value):Material.mutations+=1;self.props[key]=value
    def get_editor_property(self,key):return self.props[key]
    def get_path_name(self):return self.path
class Editor:
    @staticmethod
    def get_material_expressions(m):return m.nodes
    @staticmethod
    def create_material_expression(m,cls):Material.mutations+=1;n=cls(m);m.nodes.append(n);return n
    @staticmethod
    def get_material_expression_input_names(n):return PINS.get(n.KIND,[])
    @staticmethod
    def connect_material_expressions(a,out,b,pin):
        names=Editor.get_material_expression_input_names(b)
        if pin=='':pin=names[0]
        if pin not in names:return False
        Material.mutations+=1;b.inputs[pin]=(a,out);return True
    @staticmethod
    def connect_material_property(a,out,prop):Material.mutations+=1;a.material.outputs[prop]=(a,out);return True
    @staticmethod
    def recompile_material(m):Material.mutations+=1
    @staticmethod
    def get_material_property_input_node(m,prop):return m.outputs[prop][0]
    @staticmethod
    def get_material_property_input_node_output_name(m,prop):return m.outputs[prop][1]
    @staticmethod
    def get_inputs_for_material_expression(m,n):return[n.inputs.get(pin,(None,''))[0]for pin in Editor.get_material_expression_input_names(n)]
    @staticmethod
    def get_input_node_output_name_for_material_expression(parent,child):
        return next(out for node,out in parent.inputs.values()if node is child)
class Engine:
    MaterialEditingLibrary=Editor;Material=Material;Texture2D=Texture
    MaterialProperty=Property;MaterialDomain=SimpleNamespace(MD_SURFACE='surface')
    MaterialSamplerType=SimpleNamespace(SAMPLERTYPE_COLOR='color',SAMPLERTYPE_NORMAL='normal',SAMPLERTYPE_MASKS='masks')
    MaterialShadingModel=SimpleNamespace(MSM_DEFAULT_LIT='lit',MSM_THIN_TRANSLUCENT='thin')
    BlendMode=SimpleNamespace(BLEND_OPAQUE='opaque',BLEND_TRANSLUCENT='translucent')
    TranslucencyLightingMode=SimpleNamespace(TLM_SURFACE_PER_PIXEL_LIGHTING='forward')
    TextureMipValueMode=SimpleNamespace(TMVM_NONE='none')
    SamplerSourceMode=SimpleNamespace(SSM_FROM_TEXTURE_ASSET='from_asset')
    DinkMaterialArtLibrary=SimpleNamespace(get_connected_material_properties=lambda m:[p.value for p in m.outputs])
    textures={}
    @staticmethod
    def LinearColor(r,g,b,a):return SimpleNamespace(r=r,g=g,b=b,a=a)
    @staticmethod
    def load_asset(path):return Engine.textures.get(path)
for kind in ['TextureCoordinate','ComponentMask','TextureSample','OneMinus','AppendVector','If','LinearInterpolate','Multiply','Add','Normalize','Clamp','Constant','Constant3Vector','VertexColor','ThinTranslucentMaterialOutput']:
    setattr(Engine,'MaterialExpression'+kind,type(kind,(Node,),{'KIND':kind}))
SOURCE=json.loads((ROOT/'Docs/Verification/House439SharedExteriorSource/native-trial-contract.json').read_text())
def construct(role):
    recipe=copy.deepcopy(next(r for r in SOURCE['materials']if r['source_material']=='MI_Shared_'+role));m=Material(recipe['package']);textures={name:Texture(path)for name,path in recipe['textures'].items()};Engine.textures={t.path:t for t in textures.values()}
    if role=='ThinWavyGlass2m':recipe.update(native_policy_reviewed=True,physical_uv_reviewed=True);glass(Engine,m,recipe,textures,lambda:None)
    else:recipe['source_graph_reviewed']=True;opaque(Engine,m,recipe,recipe['source_graph'],textures,lambda:None)
    return m,recipe
class MaterialReadbackTests(unittest.TestCase):
    def test_all_seven_constructed_source_graphs(self):
        for r in SOURCE['materials']:
            with self.subTest(role=r['source_material']):
                m,recipe=construct(r['source_material'].removeprefix('MI_Shared_'));self.assertTrue(inspect_graph(Engine,m,recipe)['passed'])
    def test_readback_has_no_graph_mutations(self):
        m,r=construct('LimeMortarSoot2m');before=Material.mutations;inspect_graph(Engine,m,r);self.assertEqual(Material.mutations,before)
    def test_roughness_bias_decode_bypass_rejected(self):
        m,r=construct('LimeMortarSoot2m');append=next(n for n in m.nodes if n.KIND=='AppendVector');minus=append.inputs['B'][0];append.inputs['B']=minus.inputs['None']
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_wrong_specular_rejected(self):
        m,r=construct('FieldstoneSeed2m');m.outputs[Property.MP_SPECULAR][0].props['r']=.25
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_hidden_extra_node_rejected(self):
        m,r=construct('DressedReed2m');Editor.create_material_expression(m,Engine.MaterialExpressionConstant)
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_wrong_normal_sampler_rejected(self):
        m,r=construct('WeatheredTimber2m');n=next(n for n in m.nodes if n.KIND=='TextureSample'and n.props['sampler_type']=='normal');n.props['sampler_type']='color'
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_shared_clamp_sampler_override_rejected(self):
        m,r=construct('DressedReed2m');n=next(n for n in m.nodes if n.KIND=='TextureSample');n.props['sampler_source']='shared_clamp'
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_glass_opaque_top_layer_rejected(self):
        m,r=construct('ThinWavyGlass2m');m.outputs[Property.MP_OPACITY][0].props['r']=1.
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_glass_coverage_zero_rejected(self):
        m,r=construct('ThinWavyGlass2m');n=next(n for n in m.nodes if n.KIND=='ThinTranslucentMaterialOutput');n.inputs['SurfaceCoverage'][0].props['r']=0.
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_extra_master_property_rejected(self):
        m,r=construct('ThinWavyGlass2m');m.outputs[Property.MP_EMISSIVE_COLOR]=m.outputs[Property.MP_OPACITY]
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
    def test_wrong_output_channel_rejected(self):
        m,r=construct('FieldstoneWall2m');n,_=m.outputs[Property.MP_BASE_COLOR];m.outputs[Property.MP_BASE_COLOR]=(n,'R')
        with self.assertRaises(ValueError):inspect_graph(Engine,m,r)
if __name__=='__main__':unittest.main()
