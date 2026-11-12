"""Frozen graph/pixel inspection shared by portable source checks; no writes."""
import hashlib
def graph(m):
    nodes = []
    for n in m.node_tree.nodes:
        r = dict(name=n.name, type=n.bl_idname, inputs={i.identifier: list(i.default_value) if hasattr(i.default_value, '__len__') and (not isinstance(i.default_value, str)) else i.default_value for i in n.inputs if hasattr(i, 'default_value') and isinstance(i.default_value, (int, float, str)) or (hasattr(i, 'default_value') and hasattr(i.default_value, '__len__'))})
        for k in ['uv_map', 'layer_name', 'attribute_name', 'operation', 'blend_type', 'use_clamp', 'extension', 'interpolation']:
            if hasattr(n, k):
                r[k] = getattr(n, k)
        if n.type == 'TEX_IMAGE' and n.image:
            r['image'] = dict(packed_sha256=hashlib.sha256(n.image.packed_file.data).hexdigest(), colour_space=n.image.colorspace_settings.name)
        nodes.append(r)
    return dict(nodes=nodes, links=[(l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in m.node_tree.links])
