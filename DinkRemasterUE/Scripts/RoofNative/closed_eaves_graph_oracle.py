"""Numerical CPU oracle for lowered graphs, with caller-supplied linear samples.

This evaluates node algebra, not texture filtering, lighting or native optics.
"""
import math


def evaluate(graph, texture_samples, uv1=(0, 0, 0), vertex=(1, 1, 1, 0)):
    values = {}

    def binary(a, b, fn):
        if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
            width = len(a) if isinstance(a, (list, tuple)) else len(b)
            aa = a if isinstance(a, (list, tuple)) else [a] * width
            bb = b if isinstance(b, (list, tuple)) else [b] * width
            if len(aa) != len(bb):
                raise ValueError('Vector dimension mismatch')
            return [fn(x, y) for x, y in zip(aa, bb)]
        return fn(a, b)

    for n in graph['operations']:
        op = n['operation']
        if op == 'constant':
            result = n['value']
        elif op == 'uv':
            result = [0, 0, 0] if n['channel'] == 0 else list(uv1)
        elif op == 'vertex_color':
            result = list(vertex[:3]) if n['channels'] == 'RGB' else vertex[3]
        elif op == 'texture_rgb':
            result = list(texture_samples[n['image']['sha256']])
        elif op == 'component':
            result = values[n['source']][n['index']]
        elif op == 'add':
            result = binary(values[n['a']], values[n['b']], lambda a, b: a + b)
        elif op == 'multiply':
            result = binary(values[n['a']], values[n['b']], lambda a, b: a * b)
        elif op == 'greater_than':
            result = float(values[n['a']] > values[n['b']])
        elif op == 'saturate':
            result = binary(values[n['source']], 0, lambda a, _: min(1, max(0, a)))
        elif op == 'lerp':
            factor = values[n['factor']]
            result = binary(values[n['a']], values[n['b']], lambda a, b: a + factor * (b - a))
        elif op == 'normalize':
            v = values[n['source']]
            length = math.sqrt(sum(x*x for x in v))
            if length == 0:
                raise ValueError('Degenerate normal')
            result = [x/length for x in v]
        elif op == 'source_principled':
            result = {k: values[v] for k, v in n['inputs'].items()}
            result['Ambient Occlusion'] = values[n['ambient_occlusion']]
        else:
            raise ValueError('Unsupported oracle operation: ' + op)
        values[n['id']] = result
    return values[graph['surface']]
