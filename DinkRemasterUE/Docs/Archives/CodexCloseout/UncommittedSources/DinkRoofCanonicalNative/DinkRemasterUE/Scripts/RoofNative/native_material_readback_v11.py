"""Read-only inspection of actual saved PBR graphs; no module-load Unreal calls."""

def require(ok,message):
    if not ok:raise ValueError(message)

def inspect_graph(U,material,recipe,masked):
    E=U.MaterialEditingLibrary;P=U.MaterialProperty
    require(material.get_path_name().split('.')[0]==recipe['masked' if masked else 'opaque'],'Material target differs')
    require(material.get_editor_property('shading_model')==U.MaterialShadingModel.MSM_DEFAULT_LIT,'Shading model differs')
    require(material.get_editor_property('blend_mode')==(U.BlendMode.BLEND_MASKED if masked else U.BlendMode.BLEND_OPAQUE),'Blend mode differs')
    require(not material.get_editor_property('two_sided') and not material.get_editor_property('use_material_attributes') and material.get_editor_property('tangent_space_normal'),'Material mode differs')
    nodes=set();properties=set();samples={}
    def remember(node):
        require(node is not None,'Missing graph expression');nodes.add(node.get_path_name());return node
    def master(prop,channel,cls):
        n=remember(E.get_material_property_input_node(material,prop));require(type(n) is cls,'Unexpected property expression type')
        require(E.get_material_property_input_node_output_name(material,prop)==channel,'Wrong master output channel')
        properties.add(prop.value);return n
    def inputs(node):
        names=list(E.get_material_expression_input_names(node));values=list(E.get_inputs_for_material_expression(material,node))
        require(len(names)==len(values) and len(set(names))==len(names),'Ambiguous named inputs')
        return dict(zip(names,values))
    def edge_output(node,parent):
        value=E.get_input_node_output_name_for_material_expression(parent,node)
        if isinstance(value,str):return value
        if isinstance(value,tuple) and len(value)==2:
            boolean=[v for v in value if isinstance(v,bool)];strings=[v for v in value if isinstance(v,str)]
            require(boolean==[True] and len(strings)==1,'Input-output readback failed');return strings[0]
        raise ValueError('Unsupported actual input-output API signature')
    def sample(node,role):
        remember(node);require(type(node) is U.MaterialExpressionTextureSample,'Expected typed texture sample')
        tex=node.get_editor_property('texture');require(tex is not None and tex.get_path_name().split('.')[0]==recipe['textures'][role],'Wrong texture role')
        sampler={'BC':U.MaterialSamplerType.SAMPLERTYPE_COLOR,'E':U.MaterialSamplerType.SAMPLERTYPE_COLOR,'N':U.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':U.MaterialSamplerType.SAMPLERTYPE_MASKS}[role]
        require(node.get_editor_property('sampler_type')==sampler and node.get_editor_property('const_coordinate')==0,'Sampler/UV0 differs')
        require(not any(E.get_inputs_for_material_expression(material,node)),'Hidden UV/mip/texture inputs')
        if role in samples:require(samples[role]==node.get_path_name(),'Duplicated role sampler nodes')
        samples[role]=node.get_path_name()
    def constant(node,value):
        remember(node);require(type(node) is U.MaterialExpressionConstant and abs(node.get_editor_property('r')-value)<=1e-6,'Constant differs')
        require(not any(E.get_inputs_for_material_expression(material,node)),'Unexpected constant input')
    for role,channel,prop in [('BC','RGB',P.MP_BASE_COLOR),('N','RGB',P.MP_NORMAL),('ORM','R',P.MP_AMBIENT_OCCLUSION),('ORM','G',P.MP_ROUGHNESS),('ORM','B',P.MP_METALLIC)]:
        sample(master(prop,channel,U.MaterialExpressionTextureSample),role)
    constant(master(P.MP_SPECULAR,'',U.MaterialExpressionConstant),recipe['unreal_specular'])
    if 'E' in recipe['textures']:
        multiply=master(P.MP_EMISSIVE_COLOR,'',U.MaterialExpressionMultiply);links=inputs(multiply)
        require(set(links)=={'A','B'},'Unexpected emissive multiply pins');sample(links['A'],'E');constant(links['B'],recipe['emission_strength'])
        require(edge_output(links['A'],multiply)=='RGB' and edge_output(links['B'],multiply)=='','Emission output channels differ')
    else:require(recipe['emission_strength']==0,'Unexpected emission contract')
    if masked:
        require(material.get_editor_property('dither_opacity_mask') and abs(material.get_editor_property('opacity_mask_clip_value')-.5)<=1e-6,'Dither mask differs')
        switch=master(P.MP_OPACITY_MASK,'',U.MaterialExpressionShadowReplace);links=inputs(switch)
        require(set(links)=={'Default','Shadow'},'ShadowReplace named pins differ')
        opacity=remember(links['Default']);require(type(opacity) is U.MaterialExpressionScalarParameter,'Opacity source type differs')
        require(str(opacity.get_editor_property('parameter_name'))=='DinkCameraOpacity' and opacity.get_editor_property('default_value')==1,'Opacity default differs')
        require(not any(E.get_inputs_for_material_expression(material,opacity)),'Unexpected opacity inputs')
        constant(links['Shadow'],1)
        require(edge_output(opacity,switch)==edge_output(links['Shadow'],switch)=='','Shadow output channels differ')
    require({n.get_path_name() for n in E.get_material_expressions(material)}==nodes,'Extra/hidden graph nodes')
    require(set(U.DinkMaterialArtLibrary.get_connected_material_properties(material))==properties,'Extra/hidden connected shader properties')
    return {'package':material.get_path_name(),'masked':masked,'nodes':len(nodes),'connected_properties':sorted(properties),
            'scope':'Actual graph topology/roles readback only; source pixels/compressed mip appearance/shader rendering verified separately'}
