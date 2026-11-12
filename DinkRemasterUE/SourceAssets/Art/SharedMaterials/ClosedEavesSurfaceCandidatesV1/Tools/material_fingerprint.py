import hashlib, json

PROPS = ('operation', 'uv_map', 'layer_name', 'attribute_name', 'blend_type', 'data_type',
         'interpolation', 'projection', 'extension', 'distribution', 'space', 'vector_type',
         'noise_dimensions', 'voronoi_dimensions', 'distance', 'feature', 'normalize')

def value(socket):
    v = getattr(socket, 'default_value', None)
    if v is None:
        return None
    if isinstance(v, (str, bool, int, float)):
        return v
    return list(v)

def snapshot(material):
    rows = []
    for n in sorted(material.node_tree.nodes, key=lambda x: x.name):
        row = {'name': n.name, 'type': n.bl_idname,
               'properties': {k: getattr(n, k) for k in PROPS if hasattr(n, k)},
               'inputs': [(s.identifier, value(s)) for s in n.inputs],
               'outputs': [(s.identifier, value(s)) for s in n.outputs]}
        if n.type == 'TEX_IMAGE' and n.image:
            assert n.image.packed_file is not None
            row['image'] = {'sha256': hashlib.sha256(bytes(n.image.packed_file.data)).hexdigest(),
                            'colorspace': n.image.colorspace_settings.name, 'size': list(n.image.size)}
        if hasattr(n, 'color_ramp'):
            ramp = n.color_ramp
            row['ramp'] = {'interpolation': ramp.interpolation, 'color_mode': ramp.color_mode,
                           'elements': [(e.position, list(e.color)) for e in ramp.elements]}
        rows.append(row)
    links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                   for l in material.node_tree.links)
    props = {k: getattr(material, k) for k in ('surface_render_method', 'use_backface_culling',
             'use_transparent_shadow', 'use_transparency_overlap') if hasattr(material, k)}
    result = {'nodes': rows, 'links': links, 'material_properties': props}
    return result, hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()

