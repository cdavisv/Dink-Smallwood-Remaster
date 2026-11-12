"""CPU-only lowering to explicit material operations; no native BSDF mapping.

Texture samples retain source hashes/colorspaces and RGB channels. A native
backend must qualify texture storage, TBN conversion and Principled mapping.
"""
import copy


def lower_recipe(recipe):
    if recipe.get('node_semantics_verified') is not True:
        raise ValueError('Actual node semantics required')
    operations, outputs = [], {}
    links = {(b, socket): (a, out) for a, out, b, socket in recipe['links']}

    def emit(operation, **kwargs):
        ref = 'e' + str(len(operations))
        operations.append(dict(id=ref, operation=operation, **kwargs))
        return ref

    def constant(value):
        if isinstance(value, list) and len(value) == 4:
            value = value[:3]  # Color outputs carry RGB; alpha is a separate socket.
        return emit('constant', value=copy.deepcopy(value))

    def input_value(node, socket):
        target = links.get((node['name'], socket))
        if target is not None:
            return outputs[target]
        return constant(dict(node['inputs'])[socket])

    surface = None
    for node in recipe['nodes']:
        kind, props = node['type'], node['properties']
        if props.get('mute') is not False:
            raise ValueError('Muted or unverified nodes require explicit bypass mapping')
        get = lambda socket: input_value(node, socket)
        result = {}
        if kind == 'ShaderNodeUVMap':
            if props['uv_map'] not in ('UV0', 'UV1_SharedData'):
                raise ValueError('Unknown source UV role')
            result['UV'] = emit('uv', channel=0 if props['uv_map'] == 'UV0' else 1)
        elif kind == 'ShaderNodeVertexColor':
            if props['layer_name'] != 'SharedSurfaceData':
                raise ValueError('Unknown vertex layer')
            result['Color'] = emit('vertex_color', channels='RGB')
            result['Alpha'] = emit('vertex_color', channels='A')
        elif kind == 'ShaderNodeTexImage':
            image = copy.deepcopy(node['image'])
            if (props['interpolation'] != 'Linear' or props['extension'] != 'REPEAT'
                    or props.get('projection') != 'FLAT'):
                raise ValueError('Unqualified texture sampling')
            uv = get('Vector') if (node['name'], 'Vector') in links else emit('uv', channel=0)
            result['Color'] = emit('texture_rgb', image=image, uv=uv,
                                   filter='linear', address='repeat', retained_channels='RGB')
            result['Alpha'] = constant(1.0)
        elif kind in ('ShaderNodeSeparateXYZ', 'ShaderNodeSeparateColor'):
            if kind == 'ShaderNodeSeparateColor' and props.get('mode') != 'RGB':
                raise ValueError('Only actual RGB separation is qualified')
            source = get('Vector' if kind == 'ShaderNodeSeparateXYZ' else 'Color')
            names = ('X', 'Y', 'Z') if kind == 'ShaderNodeSeparateXYZ' else ('Red', 'Green', 'Blue')
            result = {name: emit('component', source=source, index=i) for i, name in enumerate(names)}
        elif kind == 'ShaderNodeMath':
            a, b = get('Value'), get('Value_001')
            operation = props['operation']
            if operation == 'MULTIPLY_ADD':
                value = emit('add', a=emit('multiply', a=a, b=b), b=get('Value_002'))
            elif operation in ('ADD', 'GREATER_THAN'):
                value = emit('add' if operation == 'ADD' else 'greater_than', a=a, b=b)
            else:
                raise ValueError('Unsupported math operation')
            if props.get('use_clamp'):
                value = emit('saturate', source=value)
            result['Value'] = value
        elif kind == 'ShaderNodeMixRGB':
            a, b = get('Color1'), get('Color2')
            if props['blend_type'] == 'MULTIPLY':
                b = emit('multiply', a=a, b=b)
            elif props['blend_type'] != 'MIX':
                raise ValueError('Unsupported color blend')
            value = emit('lerp', a=a, b=b, factor=emit('saturate', source=get('Fac')))
            if props.get('use_clamp'):
                value = emit('saturate', source=value)
            result['Color'] = value
        elif kind == 'ShaderNodeNormalMap':
            if props['space'] != 'TANGENT' or props['uv_map'] != 'UV0':
                raise ValueError('Unqualified normal frame')
            decoded = emit('add', a=emit('multiply', a=get('Color'), b=constant(2)), b=constant(-1))
            blended = emit('lerp', a=constant([0, 0, 1]), b=decoded, factor=get('Strength'))
            result['Normal'] = emit('normalize', source=blended, frame='source_tangent_OpenGL')
        elif kind == 'ShaderNodeBsdfPrincipled':
            # Preserve ALL source inputs. Backend must explicitly map optical
            # parameters; this is not a claim that UE DefaultLit equals Blender.
            result['BSDF'] = emit('source_principled', inputs={name: get(name) for name, _ in node['inputs']},
                                  properties=copy.deepcopy(props), ambient_occlusion=constant(1))
        elif kind == 'ShaderNodeOutputMaterial':
            surface = get('Surface')
        else:
            raise ValueError('Unsupported node type: ' + kind)
        outputs.update({(node['name'], name): ref for name, ref in result.items()})
    if surface is None:
        raise ValueError('Missing source surface')
    return dict(role=recipe['role'], operations=operations, surface=surface,
                scope='Explicit CPU graph; native texture/TBN/BSDF mapping unqualified')
