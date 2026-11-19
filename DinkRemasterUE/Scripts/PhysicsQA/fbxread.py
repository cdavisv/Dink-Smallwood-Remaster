"""Minimal FBX binary reader (nodes, properties, arrays) for offline checks. Read-only."""
import struct, zlib, sys
import numpy as np


class Node:
    __slots__ = ('name', 'props', 'kids')

    def __init__(s, name, props, kids):
        s.name, s.props, s.kids = name, props, kids

    def find(s, name):
        for k in s.kids:
            if k.name == name:
                return k
        return None

    def all(s, name):
        return [k for k in s.kids if k.name == name]


def _prop(b, o):
    t = chr(b[o]); o += 1
    if t == 'Y': return struct.unpack_from('<h', b, o)[0], o + 2
    if t == 'C': return bool(b[o]), o + 1
    if t == 'I': return struct.unpack_from('<i', b, o)[0], o + 4
    if t == 'F': return struct.unpack_from('<f', b, o)[0], o + 4
    if t == 'D': return struct.unpack_from('<d', b, o)[0], o + 8
    if t == 'L': return struct.unpack_from('<q', b, o)[0], o + 8
    if t in 'SR':
        n = struct.unpack_from('<I', b, o)[0]; o += 4
        v = bytes(b[o:o + n]); return (v.decode('utf8', 'replace') if t == 'S' else v), o + n
    if t in 'fdlibc':
        n, enc, clen = struct.unpack_from('<III', b, o); o += 12
        raw = bytes(b[o:o + clen]); o += clen
        if enc == 1: raw = zlib.decompress(raw)
        dt = {'f': '<f4', 'd': '<f8', 'l': '<i8', 'i': '<i4', 'b': 'u1', 'c': 'u1'}[t]
        return np.frombuffer(raw, dt, n), o
    raise ValueError('prop type ' + t)


def _node(b, o, big):
    if big:
        end, nprop, plen = struct.unpack_from('<QQQ', b, o); o += 24
    else:
        end, nprop, plen = struct.unpack_from('<III', b, o); o += 12
    nl = b[o]; o += 1
    if end == 0: return None, o
    name = bytes(b[o:o + nl]).decode(); o += nl
    props = []
    for _ in range(nprop):
        v, o = _prop(b, o); props.append(v)
    kids = []
    sentinel = 25 if big else 13
    while o < end - sentinel or (o < end and b[o:o + sentinel] != b'\0' * sentinel):
        k, o = _node(b, o, big)
        if k is None: break
        kids.append(k)
    return Node(name, props, kids), end


def read(path):
    b = memoryview(open(path, 'rb').read())
    ver = struct.unpack_from('<I', b, 23)[0]; big = ver >= 7500
    o = 27; top = []
    while o < len(b) - 200:
        n, o = _node(b, o, big)
        if n is None: break
        top.append(n)
    return Node('root', [], top)
