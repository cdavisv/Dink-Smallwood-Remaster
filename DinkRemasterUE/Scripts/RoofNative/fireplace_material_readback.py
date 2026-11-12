"""Read-only native fireplace material graph correspondence inspection.
Expected topology is recorded through the reviewed builder without creating any
Unreal object. This proves saved graph correspondence, not correctness of the
builder's rendering algorithm, shader compilation, texture pixels or appearance.
"""
import copy,math
from fireplace_material import build_graph as opaque_graph


def require(ok,message):
    if not ok:raise ValueError(message)


class _Node:
    def __init__(self,cls):self.cls=cls;self.properties={};self.inputs={}
    def set_editor_property(self,key,value):self.properties[key]=value


class _Material:
    def __init__(self,package):self.package=package;self.properties={};self.nodes=[];self.outputs={}
    def get_path_name(self):return self.package+'.'+self.package.rsplit('/',1)[-1]
    def set_editor_property(self,key,value):self.properties[key]=value


def _record_expected(U,material,recipe,textures):
    E=U.MaterialEditingLibrary;actual=list(E.get_material_expressions(material));by_class={type(n):n for n in actual};expected=_Material(recipe['package'])
    class Recorder:
        @staticmethod
        def get_material_expressions(m):return m.nodes
        @staticmethod
        def create_material_expression(m,cls):
            require(cls in by_class,'Actual graph missing required expression class')
            n=_Node(cls);m.nodes.append(n);return n
        @staticmethod
        def get_material_expression_input_names(n):return list(E.get_material_expression_input_names(by_class[n.cls]))
        @staticmethod
        def connect_material_expressions(a,out,b,pin):
            names=Recorder.get_material_expression_input_names(b)
            if pin=='':require(bool(names),'No expression input');pin=names[0]
            require(pin in names,'Expected source pin unavailable');b.inputs[pin]=(a,out);return True
        @staticmethod
        def connect_material_property(a,out,p):expected.outputs[p]=(a,out);return True
        @staticmethod
        def recompile_material(m):pass  # Synthetic record; NEVER calls Unreal recompilation.
    class EngineView:
        MaterialEditingLibrary=Recorder
        def __getattr__(self,name):return getattr(U,name)
    r=copy.deepcopy(recipe)
    require(r['profile']=='fireplace_opaque_source_graph_2m','Outside exact fireplace opaque profile')
    r['source_graph_reviewed']=True;opaque_graph(EngineView(),expected,r,r['source_graph'],textures,lambda:None)
    return expected,actual


def _same_value(a,b):
    if hasattr(a,'get_path_name')or hasattr(b,'get_path_name'):
        return hasattr(a,'get_path_name')and hasattr(b,'get_path_name')and a.get_path_name()==b.get_path_name()
    if all(hasattr(a,k)and hasattr(b,k)for k in ('r','g','b','a')):
        return all(abs(getattr(a,k)-getattr(b,k))<=1e-6 for k in ('r','g','b','a'))
    if isinstance(a,bool)or isinstance(b,bool):return type(a)is type(b)and a==b
    if isinstance(a,(int,float))and isinstance(b,(int,float)):
        return math.isfinite(a)and math.isfinite(b)and abs(a-b)<=1e-6
    return a==b


def inspect_graph(U,material,recipe):
    """Inspect graph roots, named edges, typed textures, defaults and full node set.
    There are no setters, imports, package creations, recompiles or saves here.
    U.load_asset reads the expected already-imported texture assets only.
    """
    require(isinstance(material,U.Material),'Saved native material type differs')
    require(material.get_path_name().split('.')[0]==recipe['package'],'Saved material package differs')
    E=U.MaterialEditingLibrary;textures={name:U.load_asset(path)for name,path in recipe['textures'].items()};require(all(isinstance(x,U.Texture2D)for x in textures.values()),'Expected saved texture missing/wrong class')
    expected,actual_nodes=_record_expected(U,material,recipe,textures)
    for key,value in expected.properties.items():require(_same_value(material.get_editor_property(key),value),'Saved material property differs: '+key)
    require(material.get_editor_property('material_domain')==U.MaterialDomain.MD_SURFACE,'Non-surface material domain')
    require(not material.get_editor_property('dither_opacity_mask'),'Unexpected camera dithering')
    required_props={p.value for p in expected.outputs};actual_props=set(U.DinkMaterialArtLibrary.get_connected_material_properties(material));require(actual_props==required_props,'Extra/missing master properties')
    matched={};reverse={}
    def identity(n):return n.get_path_name()
    def edge_output(parent,child):
        value=E.get_input_node_output_name_for_material_expression(parent,child)
        if isinstance(value,str):return value
        if isinstance(value,tuple)and len(value)==2:
            flags=[x for x in value if isinstance(x,bool)];names=[x for x in value if isinstance(x,str)];require(flags==[True]and len(names)==1,'Native edge channel readback failed');return names[0]
        raise ValueError('Unsupported edge output API')
    def compare(want,got):
        require(got is not None and type(got)is want.cls,'Saved expression class differs')
        key=id(want);path=identity(got)
        if key in matched:require(matched[key]==path,'Saved graph duplicated a shared source expression');return
        require(path not in reverse,'Saved graph aliases distinct source expressions');matched[key]=path;reverse[path]=key
        for prop,value in want.properties.items():require(_same_value(got.get_editor_property(prop),value),'Saved expression value differs: '+prop)
        if isinstance(got,U.MaterialExpressionTextureSample):
            require(got.get_editor_property('mip_value_mode')==U.TextureMipValueMode.TMVM_NONE,'Unexpected explicit texture mip mode')
            require(got.get_editor_property('sampler_source')==U.SamplerSourceMode.SSM_FROM_TEXTURE_ASSET,'Texture wrapping overridden by shared sampler')
        if isinstance(got,U.MaterialExpressionTextureCoordinate):
            for prop,value in [('u_tiling',1.),('v_tiling',1.),('un_mirror_u',False),('un_mirror_v',False)]:require(_same_value(got.get_editor_property(prop),value),'Unexpected UV coordinate modifier')
        names=list(E.get_material_expression_input_names(got));values=list(E.get_inputs_for_material_expression(material,got));require(len(names)==len(values)and len(names)==len(set(names)),'Ambiguous native expression inputs');inputs=dict(zip(names,values));require(set(want.inputs)<=set(inputs),'Expected native edge absent')
        for pin,parent in inputs.items():
            if pin not in want.inputs:require(parent is None,'Hidden native graph input: '+pin);continue
            upstream,output=want.inputs[pin];require(parent is not None,'Disconnected native graph input: '+pin);require(edge_output(got,parent)==output,'Native edge output channel differs: '+pin);compare(upstream,parent)
    for prop,(node,output)in expected.outputs.items():
        actual=E.get_material_property_input_node(material,prop);require(E.get_material_property_input_node_output_name(material,prop)==output,'Master output channel differs');compare(node,actual)
    thin=getattr(U,'MaterialExpressionThinTranslucentMaterialOutput',None)
    expected_custom=[n for n in expected.nodes if n.cls is thin]if thin else[];actual_custom=[n for n in actual_nodes if type(n)is thin]if thin else[];require(len(expected_custom)==len(actual_custom)<=1,'Custom thin-transmission output coverage differs')
    if expected_custom:compare(expected_custom[0],actual_custom[0])
    require(set(reverse)=={identity(n)for n in actual_nodes}and len(matched)==len(expected.nodes),'Extra/disconnected native graph nodes')
    return {'passed':True,'package':recipe['package'],'nodes':len(actual_nodes),'connected_properties':sorted(actual_props),'profile':recipe['profile'],'scope':'Actual native graph correspondence only; generated expected topology shares builder. Independent source semantics/texture pixels/shader compile/GPU appearance checks remain required.'}
