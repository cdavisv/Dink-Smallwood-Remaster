"""Report whether probe points lie inside any UCX_ hull of an asset.

    blender -b --factory-startup -P tests/probe_collision.py -- --blend F --asset NAME --points "x,y,z;x,y,z"
Points are in asset space (metres, relative to the asset origin).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from dinkasset import common  # noqa: E402


def inside(ob, p):
    me = ob.data
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        a, b, c = (me.vertices[i].co for i in t.vertices)
        n = (b - a).cross(c - a)
        if n.length < 1e-12:
            continue
        n.normalize()
        if n.dot(p - a) > 1e-6:
            return False
    return True


def main():
    argv = common.script_argv()
    get = lambda k: argv[argv.index(k) + 1]  # noqa: E731
    common.open_blend(get("--blend"))
    asset = [a for a in common.find_assets(only=[get("--asset")])][0]
    res = []
    for ptxt in get("--points").split(";"):
        p = Vector([float(v) for v in ptxt.split(",")])
        hits = [c.name for c in asset.collision if inside(c, p)]  # hulls share the asset origin
        res.append({"point": list(p), "hulls": hits})
    common.emit({"tool": "probe_collision", "asset": asset.name, "hulls": [c.name for c in asset.collision], "points": res})


if __name__ == "__main__":
    main()
