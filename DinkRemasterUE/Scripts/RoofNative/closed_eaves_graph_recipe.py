"""Pure active-graph recipes. No Unreal import, asset access, or saves.

The adapter interface deliberately retains Blender semantics. A native adapter
must qualify each operation, texture decode and BSDF mapping before use.
"""
import copy
import hashlib
import json


SUPPORTED = {
    'ShaderNodeVertexColor', 'ShaderNodeTexImage', 'ShaderNodeMath',
    'ShaderNodeMixRGB', 'ShaderNodeNormalMap', 'ShaderNodeBsdfPrincipled',
    'ShaderNodeSeparateXYZ', 'ShaderNodeSeparateColor', 'ShaderNodeUVMap',
    'ShaderNodeOutputMaterial',
}


def validate_raw_normal_binding(binding):
    """Require retained linear XYZ; normal-map compression reconstructs Z."""
    if (binding.get('srgb') is not False
            or binding.get('sampler') != 'linear_rgb'
            or binding.get('compression') != 'retained_rgb'
            or binding.get('source_orientation') != 'OpenGL +Y'
            or binding.get('green_flip_count') != 1
            or binding.get('retained_channels') != 'RGB'):
        raise ValueError('Raw normal XYZ and exactly one handedness conversion required')


def active_recipe(role, record, node_semantics=None):
    graph = record['graph']
    actual = hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()
    if actual != record['fingerprint']:
        raise ValueError('Source graph fingerprint mismatch')
    nodes = {n['name']: n for n in graph['nodes']}
    if len(nodes) != len(graph['nodes']):
        raise ValueError('Duplicate node identity')
    outputs = [n for n in nodes.values() if n['type'] == 'ShaderNodeOutputMaterial']
    if len(outputs) != 1:
        raise ValueError('Expected one material output')
    incoming = {}
    for a, out, b, socket in graph['links']:
        if a not in nodes or b not in nodes or (b, socket) in incoming:
            raise ValueError('Invalid or duplicate linked input')
        if (out not in dict(nodes[a]['outputs'])
                or socket not in dict(nodes[b]['inputs'])):
            raise ValueError('Unknown linked socket identifier')
        incoming[b, socket] = (a, out)
    order, visiting, visited = [], set(), set()

    def visit(name):
        if name in visiting:
            raise ValueError('Cycle in active shader')
        if name in visited:
            return
        visiting.add(name)
        for (target, _), (source, _) in incoming.items():
            if target == name:
                visit(source)
        node = nodes[name]
        if node['type'] not in SUPPORTED:
            raise ValueError('Unqualified active operation: ' + node['type'])
        visiting.remove(name)
        visited.add(name)
        order.append(copy.deepcopy(node))

    visit(outputs[0]['name'])
    if node_semantics is not None:
        if set(node_semantics) != visited:
            raise ValueError('Incomplete active node semantics')
        for node in order:
            settings = node_semantics[node['name']]
            if ('mute' not in settings
                    or any(type(v) is not bool for k, v in settings.items() if k != 'mode')
                    or ('mode' in settings and not isinstance(settings['mode'], str))):
                raise ValueError('Invalid node semantics')
            node['properties'].update(settings)
    return {
        'role': role, 'source_fingerprint': record['fingerprint'],
        'scope': 'CPU source-semantic recipe; no native equivalence claimed',
        'nodes': order,
        'links': [copy.deepcopy(e) for e in graph['links']
                  if e[0] in visited and e[2] in visited],
        'excluded_disconnected_nodes': sorted(set(nodes) - visited),
        'material_properties': copy.deepcopy(graph['material_properties']),
        'node_semantics_verified': node_semantics is not None,
    }


def build_with_adapter(recipe, adapter):
    """Preflight the WHOLE recipe before issuing construction operations.

    validate_recipe must reject unsupported BSDF/default/texture semantics and
    destinations. create_node receives all defaults, including unlinked inputs.
    This function neither imports Unreal nor saves/activates any material.
    """
    if recipe.get('node_semantics_verified') is not True:
        raise ValueError('Actual mute/clamp semantics required before construction')
    adapter.validate_recipe(copy.deepcopy(recipe))
    handles = {}
    for node in recipe['nodes']:
        handles[node['name']] = adapter.create_node(copy.deepcopy(node))
    for source, output, target, socket in recipe['links']:
        adapter.connect(handles[source], output, handles[target], socket)
    return handles
