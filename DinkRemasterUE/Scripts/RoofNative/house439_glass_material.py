"""Source-only thin-glass graph preparation. No Unreal actions on import.
Root must review/compile/run in its guarded native lane; no opaque fallback.
"""
from math import isfinite


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_recipe(recipe):
    require(recipe.get('profile') == 'thin_transmissive_surface_2m', 'Explicit thin-glass profile required')
    require(recipe.get('front_back_policy') == 'closed_panes_front_faces_only', 'Reviewed closed-pane policy required')
    require(recipe.get('native_policy_reviewed') is True, 'Root native glass policy review required')
    require(recipe.get('physical_uv_reviewed') is True, 'Physical glass coordinates must be reviewed')
    require(type(recipe.get('uv_channel')) is int and 0 <= recipe['uv_channel'] < 8, 'Explicit physical UV channel required')
    require(recipe.get('transmission') == 1 and recipe.get('surface_coverage') == 1 and
            recipe.get('top_material_coverage') == 0, 'Clear glass coverage contract differs')
    ior = recipe.get('IOR')
    require(isinstance(ior, (int, float)) and isfinite(ior) and abs(ior - 1.48) < 1e-9, 'Registered glass IOR differs')
    f0 = ((ior - 1) / (ior + 1)) ** 2
    require(abs(recipe.get('unreal_specular', -1) - f0 / .08) < 1e-9, 'Glass Fresnel specular differs')
    require(set(recipe.get('textures', {})) == {'BC', 'N', 'ORM'}, 'Exact glass texture roles required')
    require(recipe.get('two_sided') is False, 'Closed panes must cull back faces')
    require(recipe.get('substrate_enabled') is False, 'This explicit legacy thin-translucent profile does not support Substrate')
    return f0


def build_graph(U, material, recipe, textures, guard):
    """Build only a caller-created NEW material. Caller owns isolation, save and receipts.

    Unreal ThinTranslucentCommon.ush treats root Opacity as TOP material coverage.
    It must be zero for clear glass; custom SurfaceCoverage remains one. Setting
    root Opacity to one would remove background transmission even in ThinTranslucent.
    """
    f0 = validate_recipe(recipe)
    require(callable(guard), 'Root isolation guard required')
    require(set(textures) == {'BC', 'N', 'ORM'}, 'Incomplete actual texture set')
    require(all(textures[k].get_path_name().split('.')[0] == path
                for k, path in recipe['textures'].items()), 'Actual glass texture binding differs')
    require(material.get_path_name().split('.')[0] == recipe.get('package'), 'Unexpected fresh glass target')
    # Resolve every required class/enum before any graph mutation.
    thin_class = getattr(U, 'MaterialExpressionThinTranslucentMaterialOutput', None)
    shading = getattr(U.MaterialShadingModel, 'MSM_THIN_TRANSLUCENT', None)
    lighting = getattr(getattr(U, 'TranslucencyLightingMode', None), 'TLM_SURFACE_PER_PIXEL_LIGHTING', None)
    require(thin_class is not None and shading is not None and lighting is not None,
            'Physical thin-translucent API unavailable; refusing fallback')
    E = U.MaterialEditingLibrary
    require(len(E.get_material_expressions(material)) == 0, 'Only a fresh empty material is allowed')

    def call(fn, *args):
        guard()
        return fn(*args)

    def setprop(obj, key, value):
        call(obj.set_editor_property, key, value)

    def node(cls):
        result = call(E.create_material_expression, material, cls)
        require(result is not None, 'Glass expression creation failed')
        return result

    def link(a, output, b, input_name):
        require(call(E.connect_material_expressions, a, output, b, input_name), 'Glass expression connection failed: ' + input_name)

    def prop(a, output, name):
        require(call(E.connect_material_property, a, output, getattr(U.MaterialProperty, name)), 'Glass property connection failed: ' + name)

    setprop(material, 'two_sided', False)
    setprop(material, 'tangent_space_normal', True)
    setprop(material, 'use_material_attributes', False)
    setprop(material, 'blend_mode', U.BlendMode.BLEND_TRANSLUCENT)
    setprop(material, 'shading_model', shading)
    setprop(material, 'translucency_lighting_mode', lighting)
    samples = {}
    for kind in ('BC', 'N', 'ORM'):
        n = node(U.MaterialExpressionTextureSample)
        setprop(n, 'texture', textures[kind])
        setprop(n, 'const_coordinate', recipe['uv_channel'])
        setprop(n, 'sampler_type', {'BC': U.MaterialSamplerType.SAMPLERTYPE_COLOR,
                                  'N': U.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                                  'ORM': U.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind])
        samples[kind] = n
    custom = node(thin_class)
    names = list(E.get_material_expression_input_names(custom))
    require(set(names) == {'TransmittanceColor', 'SurfaceCoverage'}, 'Thin output pins differ; refusing guessed wiring')
    link(samples['BC'], 'RGB', custom, 'TransmittanceColor')
    coverage = node(U.MaterialExpressionConstant)
    setprop(coverage, 'r', 1.)
    link(coverage, '', custom, 'SurfaceCoverage')
    zero = node(U.MaterialExpressionConstant)
    setprop(zero, 'r', 0.)
    prop(zero, '', 'MP_OPACITY')
    prop(zero, '', 'MP_BASE_COLOR')
    prop(zero, '', 'MP_METALLIC')
    prop(samples['N'], 'RGB', 'MP_NORMAL')
    prop(samples['ORM'], 'G', 'MP_ROUGHNESS')
    specular = node(U.MaterialExpressionConstant)
    setprop(specular, 'r', f0 / .08)
    prop(specular, '', 'MP_SPECULAR')
    call(E.recompile_material, material)
    return {'package': recipe['package'], 'dielectric_F0': f0, 'top_material_coverage': 0,
            'surface_coverage': 1, 'scope': 'Graph constructed only. Actual saved graph, shader compilation, source pixels, native pane response and GPU verification remain required.'}
