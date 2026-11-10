"""Review-only graph construction library. Caller owns authorization/isolation/save gates.
No Unreal import, project launch, asset import, package creation or save on module load.
"""

def require(value, message):
    if not value:
        raise RuntimeError(message)

def build_graph(U, material, recipe, textures, masked, guard):
    """Build into a caller-created NEW material; guard invoked before every mutation."""
    require(callable(guard), 'An isolation/authorization guard is required')
    require(recipe['UV0_scale'] == [1, 1] and recipe['UV0_offset'] == [0, 0], 'UV identity required')
    require(recipe['coat'] == 0, 'Unsupported nonzero source coat')
    require(0 <= recipe['unreal_specular'] <= 1, 'Invalid specular')
    require(set(recipe['textures']) in ({'BC', 'N', 'ORM'}, {'BC', 'N', 'ORM', 'E'}), 'Unknown texture roles')
    require(set(textures) == set(recipe['textures']), 'Incomplete typed texture binding')
    require(all(textures[k].get_path_name().split('.')[0] == v for k, v in recipe['textures'].items()), 'Wrong source texture role')
    target = recipe['masked' if masked else 'opaque']
    require(target and material.get_path_name().split('.')[0] == target, 'Unexpected target material')
    E = U.MaterialEditingLibrary
    def call(fn, *args):
        guard()
        return fn(*args)
    def setprop(obj, key, value):
        call(obj.set_editor_property, key, value)
    def node(cls):
        result = call(E.create_material_expression, material, cls)
        require(result is not None, 'Expression creation failed')
        return result
    def link(a, output, b, input_name):
        require(call(E.connect_material_expressions, a, output, b, input_name), 'Graph input connection failed: '+input_name)
    def prop(a, output, p):
        require(call(E.connect_material_property, a, output, p), 'Material property connection failed')
    setprop(material, 'two_sided', False)
    setprop(material, 'shading_model', U.MaterialShadingModel.MSM_DEFAULT_LIT)
    setprop(material, 'blend_mode', U.BlendMode.BLEND_MASKED if masked else U.BlendMode.BLEND_OPAQUE)
    nodes = {}
    for role, texture in textures.items():
        n = node(U.MaterialExpressionTextureSample)
        setprop(n, 'texture', texture)
        setprop(n, 'const_coordinate', 0)
        sampler = {'BC': U.MaterialSamplerType.SAMPLERTYPE_COLOR,
                   'E': U.MaterialSamplerType.SAMPLERTYPE_COLOR,
                   'N': U.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                   'ORM': U.MaterialSamplerType.SAMPLERTYPE_MASKS}[role]
        setprop(n, 'sampler_type', sampler)
        nodes[role] = n
    for role, output, name in [('BC', 'RGB', 'MP_BASE_COLOR'), ('N', 'RGB', 'MP_NORMAL'),
                               ('ORM', 'R', 'MP_AMBIENT_OCCLUSION'), ('ORM', 'G', 'MP_ROUGHNESS'),
                               ('ORM', 'B', 'MP_METALLIC')]:
        prop(nodes[role], output, getattr(U.MaterialProperty, name))
    spec = node(U.MaterialExpressionConstant)
    setprop(spec, 'r', recipe['unreal_specular'])
    prop(spec, '', U.MaterialProperty.MP_SPECULAR)
    if 'E' in nodes:
        strength = node(U.MaterialExpressionConstant)
        setprop(strength, 'r', recipe['emission_strength'])
        multiply = node(U.MaterialExpressionMultiply)
        link(nodes['E'], 'RGB', multiply, 'A')
        link(strength, '', multiply, 'B')
        prop(multiply, '', U.MaterialProperty.MP_EMISSIVE_COLOR)
    else:
        require(recipe['emission_strength'] == 0, 'Nonzero emission lacks source texture')
    if masked:
        require(recipe['shadow_replace_named_inputs'] == {'Default': 'DinkCameraOpacity', 'Shadow': 'constant_one'}, 'Shadow input contract differs')
        setprop(material, 'dither_opacity_mask', True)
        setprop(material, 'opacity_mask_clip_value', .5)
        opacity = node(U.MaterialExpressionScalarParameter)
        setprop(opacity, 'parameter_name', 'DinkCameraOpacity')
        setprop(opacity, 'default_value', recipe['camera_opacity_default'])
        shadow = node(U.MaterialExpressionConstant)
        setprop(shadow, 'r', recipe['shadow_opacity'])
        switch = node(U.MaterialExpressionShadowReplace)
        link(opacity, '', switch, 'Default')
        link(shadow, '', switch, 'Shadow')
        prop(switch, '', U.MaterialProperty.MP_OPACITY_MASK)
    call(E.recompile_material, material)
    return {'package': target, 'roles': sorted(nodes), 'masked': masked,
            'scope': 'Constructed only; fresh graph readback, source pixel and shader validation required'}
