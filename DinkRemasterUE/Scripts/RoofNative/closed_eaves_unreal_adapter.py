"""Additive Unreal expression draft. Never imports Unreal or creates/saves assets.

Caller supplies a NEW material and independently inspected texture bindings.
Native API, shader compilation, optical mapping and readback remain unverified.
"""
import math


CLASSES = {
    'constant': 'MaterialExpressionConstant', 'uv': 'MaterialExpressionTextureCoordinate',
    'vertex_color': 'MaterialExpressionVertexColor', 'texture_rgb': 'MaterialExpressionTextureSample',
    'component': 'MaterialExpressionComponentMask', 'add': 'MaterialExpressionAdd',
    'multiply': 'MaterialExpressionMultiply', 'greater_than': 'MaterialExpressionIf',
    'saturate': 'MaterialExpressionSaturate', 'lerp': 'MaterialExpressionLinearInterpolate',
    'normalize': 'MaterialExpressionNormalize',
}


def inspect_texture_storage(U, texture, image):
    """Read actual imported settings; no writes or claim of pixel equivalence."""
    try:
        settings = {name:texture.get_editor_property(name) for name in
                    ('srgb','compression_settings','flip_green_channel','address_x','address_y','filter')}
        srgb = image['colorspace'] == 'sRGB'
        allowed = ([U.TextureCompressionSettings.TC_EDITOR_ICON] if srgb else
                   [U.TextureCompressionSettings.TC_HDR,U.TextureCompressionSettings.TC_HDR_F32])
        if (settings['srgb'] != srgb or settings['flip_green_channel'] is not False
                or settings['compression_settings'] not in allowed
                or settings['address_x'] != U.TextureAddress.TA_WRAP
                or settings['address_y'] != U.TextureAddress.TA_WRAP
                or settings['filter'] != U.TextureFilter.TF_BILINEAR):
            raise ValueError('Native texture storage does not retain the required RGB/decode')
        return settings
    except (AttributeError,KeyError) as exc:
        raise ValueError('Native texture storage readback unavailable') from exc


def build_new_material(U, material, graph, bindings, contract, guard):
    """Draft only: guard precedes each mutation; validate full graph first."""
    if not callable(guard):
        raise ValueError('Mutation guard required')
    target = material.get_path_name().split('.')[0]
    if (not target.startswith('/Game/Dink/Refinements/House439ClosedEavesV1/Materials/')
            or target != contract.get('target') or contract.get('new_empty_material') is not True):
        raise ValueError('Only an isolated NEW empty material is allowed')
    if contract.get('normal_basis_conversion') != 'source_OpenGL_to_imported_UE_single_Y_flip':
        raise ValueError('Explicit normal basis contract required')
    if contract.get('vertex_color_encoding') != 'raw_linear_built_srgb_rgb_linear_alpha':
        raise ValueError('Explicit raw/built vertex color encoding contract required')
    ops = {n['id']: n for n in graph['operations']}
    if len(ops) != len(graph['operations']):
        raise ValueError('Duplicate operation identity')
    bsdf = ops[graph['surface']]
    if bsdf['operation'] != 'source_principled':
        raise ValueError('Source Principled surface required')

    def scalar(name):
        n = ops[bsdf['inputs'][name]]
        if n['operation'] != 'constant':
            raise ValueError('Unsupported linked optical parameter: ' + name)
        return n['value']

    glass = graph['role'] == 'ThinWavyGlass2m'
    expected_defaults = {
        'IOR': 1.4800000190734863 if glass else 1.5,
        'Alpha': 1.0, 'Thin Wall': glass, 'Weight': 0.0,
        'Diffuse Roughness': 0.0, 'Subsurface Weight': 0.0,
        'Subsurface Radius': [1.0,0.20000000298023224,0.10000000149011612],
        'Subsurface Scale': 0.004999999888241291,
        'Subsurface IOR': 1.399999976158142, 'Subsurface Anisotropy': 0.0,
        'Specular IOR Level': .5, 'Specular Tint': [1.0,1.0,1.0],
        'Anisotropic': 0.0, 'Anisotropic Rotation': 0.0, 'Tangent': [0.0,0.0,0.0],
        'Transmission Weight': float(glass), 'Coat Weight': 0.0,
        'Coat Roughness': 0.029999999329447746, 'Coat IOR': 1.5,
        'Coat Tint': [1.0,1.0,1.0], 'Coat Normal': [0.0,0.0,0.0],
        'Sheen Weight': 0.0, 'Sheen Roughness': .5, 'Sheen Tint': [1.0,1.0,1.0],
        'Emission Color': [1.0,1.0,1.0], 'Emission Strength': 0.0,
        'Thin Film Thickness': 0.0, 'Thin Film IOR': 1.3300000429153442,
    }
    if set(bsdf['inputs']) != set(expected_defaults) | {'Base Color','Roughness','Metallic','Normal'}:
        raise ValueError('Unknown or missing source Principled input')
    for name,expected in expected_defaults.items():
        if scalar(name) != expected:
            raise ValueError('Unqualified Principled default: '+name)
    if (bsdf.get('properties') != {'distribution':'MULTI_GGX','mute':False}
            or ops[bsdf['ambient_occlusion']].get('value') != 1):
        raise ValueError('Unqualified source BSDF properties or ambient occlusion')
    if (scalar('Transmission Weight') != int(glass) or scalar('Thin Wall') != glass
            or scalar('Coat Weight') != 0 or scalar('Emission Strength') != 0
            or scalar('Alpha') != 1 or scalar('Specular IOR Level') != .5):
        raise ValueError('Unqualified source optics')
    if contract.get('optics') != ('thin_translucent_closed_pane_trial' if glass else 'opaque_dielectric_metal_trial'):
        raise ValueError('Explicit source optical trial required')
    # Every texture must retain XYZ. Normal sampler/BC5 would reconstruct Z.
    for n in graph['operations']:
        if n['operation'] not in CLASSES and n['operation'] != 'source_principled':
            raise ValueError('Unknown material operation')
        if n['operation'] == 'texture_rgb':
            binding = bindings[n['image']['sha256']]
            if (binding.get('source_sha256') != n['image']['sha256']
                    or binding.get('srgb') != (n['image']['colorspace'] == 'sRGB')
                    or binding.get('retained_channels') != 'RGB'
                    or binding.get('compression') != 'retained_rgb'
                    or binding.get('green_flip_count') != 0
                    or binding.get('texture') is None
                    or n.get('retained_channels') != 'RGB'):
                raise ValueError('Texture storage/decode contract mismatch')
            if n.get('filter') != 'linear' or n.get('address') != 'repeat':
                raise ValueError('Unsupported texture filtering/addressing')
            inspect_texture_storage(U,binding['texture'],n['image'])
        elif n['operation'] == 'component' and n.get('index') not in (0,1,2):
            raise ValueError('Unsupported component index')
        elif n['operation'] == 'uv' and n.get('channel') not in (0,1):
            raise ValueError('Unsupported UV channel')
        elif n['operation'] == 'vertex_color' and n.get('channels') not in ('RGB','A'):
            raise ValueError('Unsupported vertex color channel')
        elif n['operation'] == 'normalize' and n.get('frame') != 'source_tangent_OpenGL':
            raise ValueError('Unsupported normal frame')
        elif n['operation'] == 'constant':
            value=n['value']; elements=value if isinstance(value,list) else [value]
            if ((isinstance(value,list) and len(value)!=3)
                    or any(not isinstance(v,(int,float,bool)) or not math.isfinite(v) for v in elements)):
                raise ValueError('Unsupported or nonfinite constant')
    needed = set(CLASSES.values()) | {'MaterialExpressionConstant3Vector',
                                     'MaterialExpressionPower','MaterialExpressionAppendVector',
                                     'MaterialExpressionVertexInterpolator'}
    if glass:
        needed.add('MaterialExpressionThinTranslucentMaterialOutput')
    for name in needed:
        if not hasattr(U, name):
            raise ValueError('Missing native expression capability: ' + name)
    E = U.MaterialEditingLibrary
    for name in ('get_num_material_expressions','create_material_expression',
                 'connect_material_expressions','connect_material_property','recompile_material'):
        if not callable(getattr(E,name,None)):
            raise ValueError('Missing native editing capability: ' + name)
    enums = {
        'BlendMode': ['BLEND_TRANSLUCENT' if glass else 'BLEND_OPAQUE'],
        'MaterialShadingModel': ['MSM_THIN_TRANSLUCENT' if glass else 'MSM_DEFAULT_LIT'],
        'MaterialSamplerType': ['SAMPLERTYPE_COLOR','SAMPLERTYPE_LINEAR_COLOR'],
        'MaterialProperty': ['MP_BASE_COLOR','MP_ROUGHNESS','MP_METALLIC','MP_NORMAL','MP_SPECULAR','MP_AMBIENT_OCCLUSION'],
    }
    if glass:
        enums['TranslucencyLightingMode']=['TLM_SURFACE_PER_PIXEL_LIGHTING']
        enums['MaterialProperty'].append('MP_OPACITY')
    for group,names in enums.items():
        if any(not hasattr(getattr(U,group,None),name) for name in names):
            raise ValueError('Missing native enum capability: '+group)
    if E.get_num_material_expressions(material) != 0:
        raise ValueError('Existing material graph cannot be overwritten')
    seen = set()
    for n in graph['operations']:
        keys = {'add': ('a','b'), 'multiply': ('a','b'), 'greater_than': ('a','b'),
                'lerp': ('a','b','factor'), 'saturate': ('source',),
                'normalize': ('source',), 'component': ('source',),
                'texture_rgb': ('uv',)}.get(n['operation'], ())
        refs = [n[k] for k in keys]
        if n['operation'] == 'source_principled':
            refs += list(n['inputs'].values()) + [n['ambient_occlusion']]
        if any(ref not in seen for ref in refs):
            raise ValueError('Missing or out-of-order operation reference')
        seen.add(n['id'])

    def call(fn, *args):
        guard()
        return fn(*args)

    intent=dict(nodes=[],material_properties={},edges=[],outputs={})
    def prop(obj, name, value):
        call(obj.set_editor_property, name, value)
        if obj is material:intent['material_properties'][name]=value
        else:next(row for row in intent['nodes'] if row['object'] is obj)['properties'][name]=value

    def node(cls):
        obj = call(E.create_material_expression, material, getattr(U, cls))
        if obj is None:
            raise RuntimeError('Expression creation failed')
        intent['nodes'].append(dict(object=obj,type=cls,properties={}))
        return obj

    def link(a, b, socket):
        if not call(E.connect_material_expressions, a[0], a[1], b, socket):
            raise RuntimeError('Expression connection failed: ' + socket)
        intent['edges'].append((a[0],a[1],b,socket))

    def connect_property(a, name):
        if not call(E.connect_material_property, a[0], a[1], getattr(U.MaterialProperty, name)):
            raise RuntimeError('Material property connection failed')
        intent['outputs'][name]=a

    def constant(value):
        if isinstance(value, (list, tuple)):
            obj = node('MaterialExpressionConstant3Vector')
            prop(obj, 'constant', U.LinearColor(*value[:3], 1))
        else:
            obj = node('MaterialExpressionConstant'); prop(obj, 'r', float(value))
        return obj, ''

    def binary(cls,a,b,a_pin='A',b_pin='B'):
        obj=node(cls);link(a,obj,a_pin);link(b,obj,b_pin);return obj,''

    def decode_vertex_rgb(encoded):
        # StaticMeshBuilder uses ToFColor(true), while LocalVF fetches bytes
        # without decoding. Restore source data with the exact sRGB EOTF;
        # deliberately avoid working-color-space transforms on data channels.
        decoded=[]
        for channel in range(3):
            mask=node('MaterialExpressionComponentMask')
            for i,key in enumerate(('r','g','b','a')):prop(mask,key,i==channel)
            link(encoded,mask,'');x=(mask,'')
            linear=binary('MaterialExpressionMultiply',x,constant(1/12.92))
            shifted=binary('MaterialExpressionAdd',x,constant(.055))
            base=binary('MaterialExpressionMultiply',shifted,constant(1/1.055))
            nonlinear=binary('MaterialExpressionPower',base,constant(2.4),'Base','Exp')
            choose=node('MaterialExpressionIf');prop(choose,'equals_threshold',0.0)
            link(x,choose,'A');link(constant(.04045),choose,'B')
            link(nonlinear,choose,'A > B');link(linear,choose,'A == B');link(linear,choose,'A < B')
            decoded.append((choose,''))
        rg=binary('MaterialExpressionAppendVector',decoded[0],decoded[1])
        rgb=binary('MaterialExpressionAppendVector',rg,decoded[2])
        carrier=node('MaterialExpressionVertexInterpolator')
        link(rgb,carrier,'VS')
        return carrier,''

    prop(material, 'blend_mode', U.BlendMode.BLEND_TRANSLUCENT if glass else U.BlendMode.BLEND_OPAQUE)
    prop(material, 'shading_model', U.MaterialShadingModel.MSM_THIN_TRANSLUCENT if glass else U.MaterialShadingModel.MSM_DEFAULT_LIT)
    prop(material, 'two_sided', False)
    prop(material, 'tangent_space_normal', True)
    prop(material, 'use_material_attributes', False)
    if glass:
        prop(material, 'translucency_lighting_mode', U.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    refs = {}
    # Source Principled includes unused input defaults; emit only ancestors of
    # connected UE fields, retaining the full source record in the recipe.
    def emit(ref):
        if ref in refs:
            return refs[ref]
        n = ops[ref]; op = n['operation']
        if op == 'constant':
            result = constant(n['value'])
        else:
            obj = node(CLASSES[op]); output = ''
            if op == 'uv':
                prop(obj, 'coordinate_index', n['channel'])
            elif op == 'vertex_color':
                output = '' if n['channels'] == 'RGB' else 'A'
            elif op == 'texture_rgb':
                binding = bindings[n['image']['sha256']]
                prop(obj, 'texture', binding['texture'])
                sampler = 'SAMPLERTYPE_COLOR' if binding['srgb'] else 'SAMPLERTYPE_LINEAR_COLOR'
                prop(obj, 'sampler_type', getattr(U.MaterialSamplerType, sampler))
                link(emit(n['uv']), obj, 'UVs'); output = 'RGB'
            elif op == 'component':
                for i, name in enumerate(('r','g','b','a')):
                    prop(obj, name, i == n['index'])
                link(emit(n['source']), obj, '')
            elif op in ('add','multiply','lerp','greater_than'):
                link(emit(n['a']), obj, 'A'); link(emit(n['b']), obj, 'B')
                if op == 'lerp':
                    link(emit(n['factor']), obj, 'Alpha')
                elif op == 'greater_than':
                    prop(obj, 'equals_threshold', 0.0)
                    link(constant(1), obj, 'A > B')
                    link(constant(0), obj, 'A == B')
                    link(constant(0), obj, 'A < B')
            elif op in ('saturate','normalize'):
                link(emit(n['source']), obj, 'VectorInput' if op == 'normalize' else '')
            result = obj, output
            if op=='vertex_color' and n['channels']=='RGB':result=decode_vertex_rgb(result)
        refs[ref] = result
        return result

    for source, dest in [('Base Color','MP_BASE_COLOR'),('Roughness','MP_ROUGHNESS'),('Metallic','MP_METALLIC')]:
        connect_property(emit(bsdf['inputs'][source]), dest)
    normal = emit(bsdf['inputs']['Normal'])
    flip = node('MaterialExpressionMultiply')
    link(normal, flip, 'A'); link(constant([1,-1,1]), flip, 'B')
    connect_property((flip,''), 'MP_NORMAL')
    ior = scalar('IOR'); f0 = ((ior-1)/(ior+1))**2
    connect_property(constant(f0/.08), 'MP_SPECULAR')
    connect_property(constant(1), 'MP_AMBIENT_OCCLUSION')
    if glass:
        output = node('MaterialExpressionThinTranslucentMaterialOutput')
        link(emit(bsdf['inputs']['Base Color']), output, 'TransmittanceColor')
        connect_property(constant(0), 'MP_OPACITY')
    call(E.recompile_material, material)
    return dict(target=target, source_role=graph['role'], saved=False,
                construction_intent=intent,
                qualification='Draft graph built; native readback/optics/render acceptance required')
