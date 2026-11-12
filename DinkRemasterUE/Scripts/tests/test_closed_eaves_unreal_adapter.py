"""CPU construction tests; fake API is not native compilation/readback proof."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import math
from itertools import product

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Scripts'))
from RoofNative.closed_eaves_unreal_adapter import build_new_material, CLASSES
from RoofNative.closed_eaves_graph_oracle import evaluate
from RoofNative.closed_eaves_native_graph_readback import inspect_constructed_graph


class Object:
    def __init__(self,path='',kind='material'):
        self.path,self.kind,self.properties=path,kind,{}
    def get_path_name(self):return self.path
    def set_editor_property(self,k,v):self.properties[k]=v
    def get_editor_property(self,k):return self.properties[k]
    def get_class(self):return SimpleNamespace(get_name=lambda:self.kind)


class API:
    def __init__(self):self.nodes=[];self.links=[];self.outputs={};self.compiles=0
    def get_num_material_expressions(self,material):return len(self.nodes)
    def create_material_expression(self,material,cls):
        obj=Object(path='/Node_'+str(len(self.nodes)),kind=cls);self.nodes.append(obj);return obj
    def get_material_expressions(self,material):return list(self.nodes)
    def get_material_expression_input_names(self,node):
        return ['None' if s=='' else s for a,o,b,s in self.links if b is node]
    def get_inputs_for_material_expression(self,material,node):return [a for a,o,b,s in self.links if b is node]
    def get_input_node_output_name_for_material_expression(self,node,source):
        return next(o for a,o,b,s in self.links if b is node and a is source)
    def get_material_property_input_node(self,material,prop):return self.outputs[prop][0]
    def get_material_property_input_node_output_name(self,material,prop):return self.outputs[prop][1]
    def get_material_expression_output_names(self,node):
        return {'MaterialExpressionVertexColor':['','R','G','B','A'],
                'MaterialExpressionTextureSample':['RGB','R','G','B','A','RGBA']}.get(node.kind,[''])
    def inspect_exact_inputs(self,node):
        rows=[]
        for a,o,b,s in self.links:
            if b is not node:continue
            names=self.get_material_expression_output_names(a)
            rows.append(dict(input_index=len(rows),input_name=s,source=a.get_path_name(),
                             output_index=0 if o=='' else names.index(o) if o in names else 999))
        return json.dumps(dict(schema='dink-expression-inputs/1',valid=True,expression=node.get_path_name(),inputs=rows))
    def connect_material_expressions(self,a,out,b,socket):
        outputs={'MaterialExpressionVertexColor':{'','R','G','B','A'},
                 'MaterialExpressionTextureSample':{'','RGB','R','G','B','A','RGBA'}}
        if out not in outputs.get(a.kind,{''}):return False
        sockets={
            'MaterialExpressionTextureSample':{'UVs'},
            'MaterialExpressionComponentMask':{''},
            'MaterialExpressionSaturate':{''},
            'MaterialExpressionNormalize':{'VectorInput'},
            'MaterialExpressionAdd':{'A','B'},
            'MaterialExpressionMultiply':{'A','B'},
            'MaterialExpressionLinearInterpolate':{'A','B','Alpha'},
            'MaterialExpressionIf':{'A','B','A > B','A == B','A < B'},
            'MaterialExpressionThinTranslucentMaterialOutput':{'TransmittanceColor','SurfaceCoverage'},
            'MaterialExpressionPower':{'Base','Exp'},
            'MaterialExpressionAppendVector':{'A','B'},
            'MaterialExpressionVertexInterpolator':{'VS'},
        }
        if socket not in sockets.get(b.kind,set()):return False
        self.links.append((a,out,b,socket));return True
    def connect_material_property(self,a,out,p):self.outputs[p]=(a,out);return True
    def recompile_material(self,material):self.compiles+=1


def fixture(graph):
    api=API();u=SimpleNamespace(MaterialEditingLibrary=api,LinearColor=lambda *x:x)
    u.DinkMaterialArtLibrary=SimpleNamespace(get_connected_material_properties=lambda material:list(api.outputs),
                                           inspect_material_expression_inputs=api.inspect_exact_inputs)
    for name in set(CLASSES.values())|{'MaterialExpressionConstant3Vector','MaterialExpressionThinTranslucentMaterialOutput','MaterialExpressionPower','MaterialExpressionAppendVector','MaterialExpressionVertexInterpolator'}:
        setattr(u,name,name)
    for group,names in {
        'BlendMode':['BLEND_TRANSLUCENT','BLEND_OPAQUE'],
        'MaterialShadingModel':['MSM_THIN_TRANSLUCENT','MSM_DEFAULT_LIT'],
        'TranslucencyLightingMode':['TLM_SURFACE_PER_PIXEL_LIGHTING'],
        'MaterialSamplerType':['SAMPLERTYPE_COLOR','SAMPLERTYPE_LINEAR_COLOR'],
        'TextureCompressionSettings':['TC_EDITOR_ICON','TC_HDR','TC_HDR_F32'],
        'TextureAddress':['TA_WRAP'],
        'TextureFilter':['TF_BILINEAR'],
        'MaterialProperty':['MP_BASE_COLOR','MP_ROUGHNESS','MP_METALLIC','MP_NORMAL','MP_SPECULAR','MP_AMBIENT_OCCLUSION','MP_OPACITY'],
    }.items():setattr(u,group,SimpleNamespace(**{n:n for n in names}))
    target='/Game/Dink/Refinements/House439ClosedEavesV1/Materials/Test'
    material=Object(target+'.Test')
    contract=dict(target=target,new_empty_material=True,
                  vertex_color_encoding='raw_linear_built_srgb_rgb_linear_alpha',
                  normal_basis_conversion='source_OpenGL_to_imported_UE_single_Y_flip',
                  optics='thin_translucent_closed_pane_trial' if graph['role']=='ThinWavyGlass2m' else 'opaque_dielectric_metal_trial')
    bindings={n['image']['sha256']:dict(texture=Object(n['image']['sha256']),source_sha256=n['image']['sha256'],
              srgb=n['image']['colorspace']=='sRGB',retained_channels='RGB',compression='retained_rgb',green_flip_count=0)
              for n in graph['operations'] if n['operation']=='texture_rgb'}
    for binding in bindings.values():
        binding['texture'].properties.update(srgb=binding['srgb'],flip_green_channel=False,
            compression_settings='TC_EDITOR_ICON' if binding['srgb'] else 'TC_HDR',
            address_x='TA_WRAP',address_y='TA_WRAP',filter='TF_BILINEAR')
    return u,api,material,bindings,contract


class AdapterTests(unittest.TestCase):
    def test_rgb_is_decoded_per_vertex_before_barycentric_interpolation(self):
        graph=self.graphs['LaidWeatheredPhotoCoatFrayedCut2m_SourceTrial']
        u,api,material,bindings,contract=fixture(graph)
        build_new_material(u,material,graph,bindings,contract,lambda:None)
        carriers=[n for n in api.nodes if n.kind=='MaterialExpressionVertexInterpolator']
        self.assertEqual(len(carriers),1)
        encoded=[(0,.04,.6,.1),(1,.8,.2,.9),(.5,1,0,.5)]
        weights=(.5,.5,0)
        def decode(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
        def run(obj,out='',vertex=None):
            kind=obj.kind.removeprefix('MaterialExpression');p=obj.properties
            def read(socket,vi=vertex):
                a,o=next((a,o) for a,o,b,s in api.links if b is obj and s==socket)
                return run(a,o,vi)
            if kind=='Constant':return p['r']
            if kind=='VertexColor':
                value=list(encoded[vertex]) if vertex is not None else [sum(w*v[c] for w,v in zip(weights,encoded)) for c in range(4)]
                return value[:3] if out=='' else value[3]
            if kind=='ComponentMask':return read('')[next(i for i,k in enumerate(('r','g','b','a')) if p[k])]
            if kind=='Add':return read('A')+read('B')
            if kind=='Multiply':return read('A')*read('B')
            if kind=='Power':return read('Base')**read('Exp')
            if kind=='If':
                a,b=read('A'),read('B');return read('A > B' if a>b else 'A == B' if a==b else 'A < B')
            if kind=='AppendVector':
                a,b=read('A'),read('B');return (a if isinstance(a,list) else [a])+(b if isinstance(b,list) else [b])
            if kind=='VertexInterpolator':
                values=[read('VS',i) for i in range(3)]
                return [sum(w*v[c] for w,v in zip(weights,values)) for c in range(3)]
            raise AssertionError(kind)
        actual=run(carriers[0]);expected=[sum(w*decode(v[c]) for w,v in zip(weights,encoded)) for c in range(3)]
        for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=12)
        self.assertAlmostEqual(actual[0],.5)
        self.assertGreater(abs(actual[0]-decode(.5)),.28)
        # A bypass would decode after interpolation and reproduce the defect.
        source,out=next((a,o) for a,o,b,s in api.links if b is carriers[0] and s=='VS')
        wrong=run(source,out)
        self.assertAlmostEqual(wrong[0],decode(.5),places=12)

    def test_vertex_encoding_contract_required_before_mutation(self):
        graph=self.graphs['ThinWavyGlass2m']
        for encoding in (None,'legacy_direct_color_bytes'):
            u,api,material,bindings,contract=fixture(graph);calls=[]
            contract['vertex_color_encoding']=encoding
            with self.assertRaisesRegex(ValueError,'vertex color encoding'):
                build_new_material(u,material,graph,bindings,contract,lambda:calls.append(1))
            self.assertEqual(calls,[]);self.assertEqual(api.nodes,[])

    def test_exact_input_indices_detect_second_edge_corruption_with_shared_source(self):
        u,api,material,_,contract=fixture(self.graphs['ThinWavyGlass2m'])
        source=api.create_material_expression(material,'MaterialExpressionVertexColor')
        target=api.create_material_expression(material,'MaterialExpressionAdd')
        api.connect_material_expressions(source,'',target,'A')
        api.connect_material_expressions(source,'A',target,'B')
        api.outputs['MP_BASE_COLOR']=(target,'')
        intent=dict(material_properties={},nodes=[dict(object=source,type=source.kind,properties={}),
                    dict(object=target,type=target.kind,properties={})],
                    edges=[(source,'',target,'A'),(source,'A',target,'B')],outputs={'MP_BASE_COLOR':(target,'')})
        receipt=dict(target=contract['target'],construction_intent=intent)
        inspect_constructed_graph(u,material,receipt)
        api.links[1]=(source,'',target,'B')
        with self.assertRaisesRegex(ValueError,'Wrong connected output channel'):
            inspect_constructed_graph(u,material,receipt)

    def test_actual_graph_readback_all_seven_and_corruption_detection(self):
        for role,graph in self.graphs.items():
            u,api,material,bindings,contract=fixture(graph)
            receipt=build_new_material(u,material,graph,bindings,contract,lambda:None)
            result=inspect_constructed_graph(u,material,receipt)
            self.assertEqual(result['node_count'],len(api.nodes))
            original=material.properties['tangent_space_normal']
            material.properties['tangent_space_normal']=False
            with self.assertRaisesRegex(ValueError,'Material setting'):
                inspect_constructed_graph(u,material,receipt)
            material.properties['tangent_space_normal']=original
            constant=next(n for n in api.nodes if n.kind=='MaterialExpressionConstant')
            value=constant.properties['r'];constant.properties['r']=value+.125
            with self.assertRaisesRegex(ValueError,'Expression setting'):
                inspect_constructed_graph(u,material,receipt)
            constant.properties['r']=value
            api.nodes.append(Object('/Extra','MaterialExpressionConstant'))
            with self.assertRaisesRegex(ValueError,'Missing/extra'):
                inspect_constructed_graph(u,material,receipt)
            api.nodes.pop()
            a,o,b,s=api.links[0];api.links[0]=(a,'WRONG_CHANNEL',b,s)
            with self.assertRaisesRegex(ValueError,'output channel'):
                inspect_constructed_graph(u,material,receipt)

    def test_actual_native_storage_disagreement_rejects_even_when_metadata_claims_valid(self):
        graph=self.graphs['ThinWavyGlass2m']
        for field,value in [('compression_settings','TC_NORMALMAP'),('flip_green_channel',True),
                            ('address_x','TA_CLAMP'),('srgb',True),('filter','TF_NEAREST')]:
            u,api,material,bindings,contract=fixture(graph)
            binding=next(b for b in bindings.values() if not b['srgb'])
            binding['texture'].properties[field]=value;calls=[]
            with self.subTest(field=field),self.assertRaises(ValueError):
                build_new_material(u,material,graph,bindings,contract,lambda:calls.append(1))
            self.assertEqual(calls,[]);self.assertEqual(api.nodes,[])

    def test_fake_api_rejects_original_native_socket_mismatches(self):
        api=API();a=Object(kind='MaterialExpressionConstant')
        for kind,socket in [('MaterialExpressionTextureSample','Coordinates'),
                            ('MaterialExpressionComponentMask','Input'),
                            ('MaterialExpressionSaturate','Input')]:
            self.assertFalse(api.connect_material_expressions(a,'',Object(kind=kind),socket))
        self.assertEqual(api.links,[])
        self.assertFalse(api.connect_material_expressions(Object(kind='MaterialExpressionVertexColor'),'RGB',Object(kind='MaterialExpressionMultiply'),'A'))
    @classmethod
    def setUpClass(cls):
        cls.graphs=json.loads((ROOT/'Docs/Verification/House439ClosedEavesNative/MaterialProfile/LOWERED_MATERIAL_OPERATIONS.json').read_text())['roles']

    def test_all_seven_construct_no_save_with_raw_linear_samples_and_single_final_flip(self):
        for role,graph in self.graphs.items():
            with self.subTest(role=role):
                u,api,material,bindings,contract=fixture(graph);calls=[]
                receipt=build_new_material(u,material,graph,bindings,contract,lambda:calls.append(1))
                self.assertFalse(receipt['saved']);self.assertEqual(api.compiles,1)
                normal=api.outputs['MP_NORMAL'][0]
                self.assertEqual(normal.kind,'MaterialExpressionMultiply')
                flip=next(a for a,_,b,s in api.links if b is normal and s=='B')
                self.assertEqual(flip.properties['constant'],(1,-1,1,1))
                samples=[n for n in api.nodes if n.kind=='MaterialExpressionTextureSample']
                self.assertTrue(all(n.properties['sampler_type'] in ('SAMPLERTYPE_COLOR','SAMPLERTYPE_LINEAR_COLOR') for n in samples))
                if role=='ThinWavyGlass2m':
                    self.assertTrue(any(n.kind=='MaterialExpressionThinTranslucentMaterialOutput' for n in api.nodes))
                for node in api.nodes:
                    if node.kind=='MaterialExpressionIf':self.assertEqual(node.properties['equals_threshold'],0)

    def test_bad_texture_format_flip_and_destination_refuse_before_mutation(self):
        graph=self.graphs['ThinWavyGlass2m']
        for defect in ('compression','flip','srgb','destination','reference','existing'):
            u,api,material,bindings,contract=fixture(graph);g=copy.deepcopy(graph)
            binding=next(iter(bindings.values()))
            if defect=='compression':binding['compression']='TC_NORMALMAP'
            elif defect=='flip':binding['green_flip_count']=1
            elif defect=='srgb':binding['srgb']=not binding['srgb']
            elif defect=='destination':contract['target']='/Game/Dink/Existing'
            elif defect=='reference':next(n for n in g['operations'] if n['operation']=='texture_rgb')['uv']='missing'
            else:api.nodes.append(Object())
            before=len(api.nodes);calls=[]
            with self.subTest(defect=defect),self.assertRaises(ValueError):
                build_new_material(u,material,g,bindings,contract,lambda:calls.append(1))
            self.assertEqual(calls,[]);self.assertEqual(len(api.nodes),before)

    def test_every_optical_default_rejected_when_changed_before_mutation(self):
        graph=self.graphs['ThinWavyGlass2m'];by_id={n['id']:n for n in graph['operations']}
        surface=by_id[graph['surface']]
        for field,ref in surface['inputs'].items():
            if field in ('Base Color','Roughness','Metallic','Normal'):continue
            g=copy.deepcopy(graph);ops={n['id']:n for n in g['operations']}
            value=ops[ref]['value']
            ops[ref]['value']=[.123,.234,.345] if isinstance(value,list) else 0.123
            u,api,material,bindings,contract=fixture(g);calls=[]
            with self.subTest(field=field),self.assertRaises(ValueError):
                build_new_material(u,material,g,bindings,contract,lambda:calls.append(1))
            self.assertEqual(calls,[]);self.assertEqual(api.nodes,[])

    def test_linked_ior_refuses_before_any_guard_or_mutation(self):
        graph=copy.deepcopy(self.graphs['ThinWavyGlass2m'])
        ops={n['id']:n for n in graph['operations']};bsdf=ops[graph['surface']]
        bsdf['inputs']['IOR']=bsdf['inputs']['Roughness']
        u,api,material,bindings,contract=fixture(graph);calls=[]
        with self.assertRaisesRegex(ValueError,'Unsupported linked optical'):
            build_new_material(u,material,graph,bindings,contract,lambda:calls.append(1))
        self.assertEqual(calls,[]);self.assertEqual(api.nodes,[])

    def test_constructed_expression_algebra_matches_source_oracle(self):
        for role,graph in self.graphs.items():
            u,api,material,bindings,contract=fixture(graph)
            build_new_material(u,material,graph,bindings,contract,lambda:None)
            samples={sha:[.2+i*.013,.3+i*.011,.8-i*.009] for i,sha in enumerate(bindings)}
            encoded_cases=[tuple([12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055 for v in (.25,.17,.9)]+[.37])]
            encoded_cases.extend((v,v,v,.37) for v in (0,.04045,.0404500001,.5,1))
            for selector,encoded_vertex in product((.49,.5,.51),encoded_cases):
                vertex=tuple([v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in encoded_vertex[:3]]+[encoded_vertex[3]])
                expected=evaluate(graph,samples,uv1=(selector,.17,0),vertex=vertex)
                memo={}
                def binary(a,b,fn):
                    if isinstance(a,(tuple,list)) or isinstance(b,(tuple,list)):
                        count=len(a) if isinstance(a,(tuple,list)) else len(b)
                        aa=a if isinstance(a,(tuple,list)) else [a]*count
                        bb=b if isinstance(b,(tuple,list)) else [b]*count
                        return [fn(x,y) for x,y in zip(aa,bb)]
                    return fn(a,b)
                def run(obj,out=''):
                    key=(id(obj),out)
                    if key in memo:return memo[key]
                    props=obj.properties;kind=obj.kind.removeprefix('MaterialExpression')
                    def read(socket):
                        a,o=next((a,o) for a,o,b,s in api.links if b is obj and s==socket)
                        return run(a,o)
                    if kind=='Constant':value=props['r']
                    elif kind=='Constant3Vector':value=list(props['constant'][:3])
                    elif kind=='TextureCoordinate':value=[0,0,0] if props['coordinate_index']==0 else [selector,.17,0]
                    elif kind=='VertexColor':
                        value=list(encoded_vertex[:3]) if out=='' else encoded_vertex[3]
                    elif kind=='TextureSample':value=samples[props['texture'].path]
                    elif kind=='ComponentMask':value=read('')[next(i for i,k in enumerate(('r','g','b','a')) if props[k])]
                    elif kind=='Add':value=binary(read('A'),read('B'),lambda a,b:a+b)
                    elif kind=='Multiply':value=binary(read('A'),read('B'),lambda a,b:a*b)
                    elif kind=='Power':value=binary(read('Base'),read('Exp'),lambda a,b:a**b)
                    elif kind=='AppendVector':
                        a,b=read('A'),read('B');value=(a if isinstance(a,list) else [a])+(b if isinstance(b,list) else [b])
                    elif kind=='VertexInterpolator':value=read('VS')
                    elif kind=='LinearInterpolate':value=binary(read('A'),read('B'),lambda a,b:a+read('Alpha')*(b-a))
                    elif kind=='Saturate':value=binary(read(''),0,lambda a,_:min(1,max(0,a)))
                    elif kind=='Normalize':
                        v=read('VectorInput');length=math.sqrt(sum(x*x for x in v));value=[x/length for x in v]
                    elif kind=='If':
                        a,b=read('A'),read('B');value=read('A > B' if a>b else 'A == B' if a==b else 'A < B')
                    else:raise AssertionError(kind)
                    memo[key]=value;return value
                for source,dest in [('Base Color','MP_BASE_COLOR'),('Roughness','MP_ROUGHNESS'),('Metallic','MP_METALLIC'),('Normal','MP_NORMAL')]:
                    actual=run(*api.outputs[dest]);target=expected[source]
                    if source=='Normal':target=[target[0],-target[1],target[2]]
                    with self.subTest(role=role,selector=selector,field=source):
                        if isinstance(target,list):
                            for a,b in zip(actual,target):self.assertAlmostEqual(a,b,places=12)
                        else:self.assertAlmostEqual(actual,target,places=12)


if __name__=='__main__':unittest.main()
