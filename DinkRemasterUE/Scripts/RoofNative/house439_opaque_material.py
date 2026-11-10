"""Port the registered opaque shader graphs into a caller-created fresh material.
Source-only preparation. No Unreal imports, execution or saves on module import.
"""

def require(ok,message):
    if not ok:raise ValueError(message)


def validate_graph(graph):
    nodes={n['name']:n for n in graph['nodes']}
    require(len(nodes)==len(graph['nodes']),'Duplicate source node names')
    allowed={'BSDF_PRINCIPLED','OUTPUT_MATERIAL','UVMAP','TEX_IMAGE','VERTEX_COLOR','SEPXYZ','MATH','MIX_RGB','NORMAL_MAP'}
    require(all(n['type']in allowed for n in nodes.values()),'Unsupported source node')
    def default(n,index):return n['inputs'][index]['value']
    for n in nodes.values():
        t=n['type']
        if t=='UVMAP':require(n['uv_map']in ('UV0','UV1_SharedData'),'Unsupported UV layer')
        if t=='VERTEX_COLOR':require(n['layer_name']=='SharedSurfaceData','Wrong linear colour field')
        if t=='MATH':require(n['operation']in ('GREATER_THAN','MULTIPLY_ADD','ADD'),'Unsupported math operation')
        if t=='MIX_RGB':
            require(n['blend_type']in ('MIX','MULTIPLY')and not n['use_clamp'],'Unsupported colour blend')
            if n['blend_type']=='MULTIPLY':require(not n['inputs'][0]['linked']and default(n,0)==1,'Partial multiply unsupported')
        if t=='NORMAL_MAP':require(n['space']=='TANGENT'and default(n,0)==1,'Only source tangent normals at strength1 supported')
        if t=='TEX_IMAGE':require(n['extension']=='REPEAT'and n['interpolation']=='Linear','Texture sampling differs')
        if t=='BSDF_PRINCIPLED':
            byname={x['name']:x for x in n['inputs']}
            for name in ['Transmission Weight','Coat Weight','Emission Strength','Subsurface Weight','Sheen Weight']:
                require(not byname[name]['linked']and byname[name]['value']==0,'Unsupported source lobe: '+name)
            require(byname['IOR']['value']==1.5 and byname['Specular IOR Level']['value']==.5,'Source dielectric F0 differs')
            linked={x['name']for x in n['inputs']if x['linked']}
            require({'Base Color','Roughness','Normal'} <= linked <= {'Base Color','Roughness','Metallic','Normal'},'Unknown/missing Principled connections')
    edges={}
    for link in graph['links']:
        key=(link['to_node'],link['to_socket'])
        require(key not in edges and link['from_node']in nodes and link['to_node']in nodes,'Invalid/ambiguous source edge')
        edges[key]=(link['from_node'],link['from_socket'])
    roots=[n for n in nodes.values()if n['type']=='BSDF_PRINCIPLED'];require(len(roots)==1,'Exactly one source surface required')
    outputs=[n for n in nodes.values()if n['type']=='OUTPUT_MATERIAL'];require(len(outputs)==1,'Exactly one source output required')
    require(edges.get((outputs[0]['name'],0))==(roots[0]['name'],0),'Surface output differs')
    require(all(k[1]==0 for k in edges if k[0]==outputs[0]['name']),'Unexpected volume/displacement output')
    visited=set();visiting=set()
    def visit(name):
        require(name not in visiting,'Cyclic source graph')
        if name in visited:return
        visiting.add(name)
        for (target,index),source in edges.items():
            if target==name:visit(source[0])
        visiting.remove(name);visited.add(name)
    visit(outputs[0]['name']);require(visited==set(nodes),'Extra/disconnected source nodes')
    return nodes,edges,roots[0]


def build_graph(U,material,recipe,graph,textures,guard):
    """Translate actual source DAG. Caller supplies source-pinned recipe and typed textures.
    Normal textures are native normal samplers; encoded source normal mixes become
    decoded-vector mixes followed by normalization. Actual compression/API/GPU proof
    is required separately. Source ORM.R is unused, so native AO stays at default1.
    """
    nodes,edges,root=validate_graph(graph)
    require(callable(guard),'Root isolation guard required')
    require(recipe.get('source_graph_reviewed')is True,'Reviewed source graph recipe required')
    require(material.get_path_name().split('.')[0]==recipe['package'],'Unexpected material target')
    images={n['image']['name']for n in nodes.values()if n['type']=='TEX_IMAGE'}
    require(set(textures)==images and set(recipe['textures'])==images,'Actual source image set differs')
    require(all(textures[k].get_path_name().split('.')[0]==v for k,v in recipe['textures'].items()),'Wrong actual source texture binding')
    E=U.MaterialEditingLibrary
    require(not E.get_material_expressions(material),'Only fresh empty material allowed')
    def call(fn,*args):guard();return fn(*args)
    def setp(o,k,v):call(o.set_editor_property,k,v)
    def new(name):
        o=call(E.create_material_expression,material,getattr(U,'MaterialExpression'+name));require(o is not None,'Expression unavailable: '+name);return o
    def connect(value,to,pin):
        # MaterialEditingLibrary uses shortened editor pin names, not C++ fields.
        aliases={'AGreaterThanB':'A > B','AEqualsB':'A == B','ALessThanB':'A < B'}
        actual=list(E.get_material_expression_input_names(to));name=aliases.get(pin,pin)
        if pin=='Input':name=''  # Empty requests first input; editor shortens Input to None.
        require(name=='' or name in actual,'Unsupported actual expression pin: '+pin)
        require(call(E.connect_material_expressions,value[0],value[1],to,name),'Failed expression edge: '+pin)
    def constant(value):
        if isinstance(value,list):
            o=new('Constant3Vector');setp(o,'constant',U.LinearColor(*value[:3],1.))
        else:o=new('Constant');setp(o,'r',value)
        return(o,'')
    def op(kind,values):
        o=new(kind)
        for pin,value in values.items():connect(value,o,pin)
        return(o,'')
    cache={};active=set()
    def input_value(name,index):
        edge=edges.get((name,index));return expression(*edge)if edge else constant(nodes[name]['inputs'][index]['value'])
    def expression(name,index):
        key=(name,index)
        if key in cache:return cache[key]
        require(key not in active,'Cyclic source graph');active.add(key);n=nodes[name];t=n['type']
        if t=='UVMAP':
            o=new('TextureCoordinate');setp(o,'coordinate_index',0 if n['uv_map']=='UV0' else 1);v=(o,'')
        elif t=='VERTEX_COLOR':v=(new('VertexColor'),'RGB'if index==0 else'A')
        elif t=='TEX_IMAGE':
            o=new('TextureSample');image=n['image']['name'];setp(o,'texture',textures[image]);setp(o,'const_coordinate',0);kind='N'if '_N_GL'in image else'ORM'if '_ORM'in image else'BC';setp(o,'sampler_type',{'BC':U.MaterialSamplerType.SAMPLERTYPE_COLOR,'N':U.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':U.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]);connect(input_value(name,0),o,'UVs');v=(o,'RGB'if index==0 else'A')
        elif t=='SEPXYZ':
            o=new('ComponentMask');setp(o,'r',index==0);setp(o,'g',index==1);setp(o,'b',index==2);setp(o,'a',False);connect(input_value(name,0),o,'Input');v=(o,'')
        elif t=='MATH':
            operation=n['operation']
            if operation=='GREATER_THAN':
                o=new('If');setp(o,'equals_threshold',0.);connect(input_value(name,0),o,'A');connect(input_value(name,1),o,'B');connect(constant(1.),o,'AGreaterThanB');connect(constant(0.),o,'AEqualsB');connect(constant(0.),o,'ALessThanB');v=(o,'')
            elif operation=='ADD':v=op('Add',{'A':input_value(name,0),'B':input_value(name,1)})
            else:v=op('Add',{'A':op('Multiply',{'A':input_value(name,0),'B':input_value(name,1)}),'B':input_value(name,2)})
            if n.get('use_clamp'):v=op('Clamp',{'Input':v,'Min':constant(0.),'Max':constant(1.)})
        elif t=='MIX_RGB':
            v=op('Multiply',{'A':input_value(name,1),'B':input_value(name,2)})if n['blend_type']=='MULTIPLY'else op('LinearInterpolate',{'A':input_value(name,1),'B':input_value(name,2),'Alpha':input_value(name,0)})
        elif t=='NORMAL_MAP':v=op('Normalize',{'VectorInput':input_value(name,1)})
        else:raise ValueError('Unsupported requested source output: '+t)
        cache[key]=v;active.remove(key);return v
    setp(material,'two_sided',False);setp(material,'use_material_attributes',False);setp(material,'tangent_space_normal',True);setp(material,'blend_mode',U.BlendMode.BLEND_OPAQUE);setp(material,'shading_model',U.MaterialShadingModel.MSM_DEFAULT_LIT)
    for name,native in [('Base Color','MP_BASE_COLOR'),('Roughness','MP_ROUGHNESS'),('Metallic','MP_METALLIC'),('Normal','MP_NORMAL')]:
        socket=next(x['index']for x in root['inputs']if x['name']==name);v=input_value(root['name'],socket);require(call(E.connect_material_property,v[0],v[1],getattr(U.MaterialProperty,native)),'Failed master surface connection')
    spec=constant(.5);require(call(E.connect_material_property,spec[0],spec[1],U.MaterialProperty.MP_SPECULAR),'Failed F0 connection');call(E.recompile_material,material)
    return {'package':recipe['package'],'source_nodes':len(nodes),'translated_outputs':len(cache),'scope':'Constructed only; actual saved graph/API/texture/mesh/GPU verification pending'}
