"""Minimal binary-FBX reader (stdlib only) used to inspect exported files.

Purpose: independent evidence of what an importer such as Unreal's will see in
the file (axis header, unit header, node transforms, vertex extents), instead
of trusting Blender's own, more forgiving, FBX importer for the round trip.

Runs under plain Python 3 or inside Blender. Supports binary FBX 7.x only
(what Blender writes).
"""
import struct
import zlib

MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"


class Node:
    __slots__ = ("name", "props", "children")

    def __init__(self, name, props, children):
        self.name = name
        self.props = props
        self.children = children

    def find(self, name):
        return [c for c in self.children if c.name == name]

    def first(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None


def _read_array(data, pos, fmt, size):
    length, encoding, comp_len = struct.unpack_from("<III", data, pos)
    pos += 12
    raw = data[pos:pos + comp_len]
    pos += comp_len
    if encoding == 1:
        raw = zlib.decompress(raw)
    return list(struct.unpack("<%d%s" % (length, fmt), raw)), pos


def _read_prop(data, pos):
    t = chr(data[pos])
    pos += 1
    if t == "Y":
        return struct.unpack_from("<h", data, pos)[0], pos + 2
    if t == "C":
        return bool(data[pos]), pos + 1
    if t == "I":
        return struct.unpack_from("<i", data, pos)[0], pos + 4
    if t == "F":
        return struct.unpack_from("<f", data, pos)[0], pos + 4
    if t == "D":
        return struct.unpack_from("<d", data, pos)[0], pos + 8
    if t == "L":
        return struct.unpack_from("<q", data, pos)[0], pos + 8
    if t in "fdlib":
        fmt = {"f": "f", "d": "d", "l": "q", "i": "i", "b": "b"}[t]
        return _read_array(data, pos, fmt, 0)
    if t in "SR":
        n = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        raw = data[pos:pos + n]
        if t == "S":
            return raw.decode("utf-8", "replace"), pos + n
        return raw, pos + n
    raise ValueError("unknown FBX property type %r" % t)


def _read_node(data, pos, version):
    if version >= 7500:
        end, nprops, plen, nlen = struct.unpack_from("<QQQB", data, pos)
        pos += 25
    else:
        end, nprops, plen, nlen = struct.unpack_from("<IIIB", data, pos)
        pos += 13
    if end == 0:
        return None, pos
    name = data[pos:pos + nlen].decode("ascii")
    pos += nlen
    props = []
    for _ in range(nprops):
        v, pos = _read_prop(data, pos)
        props.append(v)
    children = []
    while pos < end:
        child, pos = _read_node(data, pos, version)
        if child is None:
            break
        children.append(child)
    return Node(name, props, children), end


def parse(path):
    """Return (version, [top-level Node])."""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(MAGIC):
        raise ValueError("not a binary FBX file: %s" % path)
    version = struct.unpack_from("<I", data, 23)[0]
    pos = 27
    nodes = []
    while pos < len(data) - 32:
        node, pos = _read_node(data, pos, version)
        if node is None:
            break
        nodes.append(node)
    return version, nodes


def _p70(node):
    """Properties70 of a node as {name: value-or-list}."""
    out = {}
    p70 = node.first("Properties70") if node else None
    if not p70:
        return out
    for p in p70.children:
        if p.name == "P" and len(p.props) >= 5:
            vals = p.props[4:]
            out[p.props[0]] = vals[0] if len(vals) == 1 else list(vals)
    return out


def inspect(path):
    """Summarise an FBX file for convention checks.

    Returns a dict:
      version, up_axis, front_axis, coord_axis (+ signs), unit_scale_factor
      (centimetres per FBX unit), models: {name: {type, translation, rotation,
      scaling, parent}}, geometries: {model_name: {min, max, size, tris}} in raw
      FBX units, and size_cm (extent * unit_scale_factor) per model.
    """
    version, top = parse(path)
    by = {n.name: n for n in top}
    gs = _p70(by["GlobalSettings"])
    unit = float(gs.get("UnitScaleFactor", 1.0))
    objects = by["Objects"]
    geoms = {}
    models = {}
    for n in objects.children:
        if n.name == "Geometry":
            gid = n.props[0]
            verts = n.first("Vertices")
            idx = n.first("PolygonVertexIndex")
            if verts is None:
                continue
            v = verts.props[0]
            pts = [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]
            tris = 0
            if idx is not None:
                cur = 0
                for i in idx.props[0]:
                    cur += 1
                    if i < 0:
                        tris += cur - 2
                        cur = 0
            geoms[gid] = (pts, tris)
        elif n.name == "Model":
            mid = n.props[0]
            name = n.props[1].split("\x00")[0]
            p = _p70(n)
            models[mid] = {
                "name": name,
                "type": n.props[2],
                "translation": list(p.get("Lcl Translation", [0, 0, 0])),
                "rotation": list(p.get("Lcl Rotation", [0, 0, 0])),
                "scaling": list(p.get("Lcl Scaling", [1, 1, 1])),
                "parent": None,
            }
    conn = by.get("Connections")
    geom_of = {}
    if conn:
        for c in conn.children:
            if c.name != "C" or len(c.props) < 3 or c.props[0] != "OO":
                continue
            child, parent = c.props[1], c.props[2]
            if child in models and parent in models:
                models[child]["parent"] = models[parent]["name"]
            if child in geoms and parent in models:
                geom_of[parent] = child
    out_models = {}
    for mid, m in models.items():
        entry = dict(m)
        g = geoms.get(geom_of.get(mid))
        if g:
            pts, tris = g
            mn = [min(p[i] for p in pts) for i in range(3)]
            mx = [max(p[i] for p in pts) for i in range(3)]
            entry["min"] = mn
            entry["max"] = mx
            entry["size"] = [mx[i] - mn[i] for i in range(3)]
            entry["size_cm"] = [(mx[i] - mn[i]) * unit for i in range(3)]
            entry["min_cm"] = [v * unit for v in mn]
            entry["max_cm"] = [v * unit for v in mx]
            entry["tris"] = tris
        out_models[m["name"]] = entry
    return {
        "version": version,
        "up_axis": [gs.get("UpAxis"), gs.get("UpAxisSign")],
        "front_axis": [gs.get("FrontAxis"), gs.get("FrontAxisSign")],
        "coord_axis": [gs.get("CoordAxis"), gs.get("CoordAxisSign")],
        "unit_scale_factor": unit,
        "original_unit_scale_factor": gs.get("OriginalUnitScaleFactor"),
        "models": out_models,
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(inspect(sys.argv[1]), indent=1))
