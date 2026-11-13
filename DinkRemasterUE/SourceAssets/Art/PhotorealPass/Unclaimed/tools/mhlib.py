"""Loader for the CC0 MakeHuman base mesh and its bundled parts (Art/Characters/ThirdParty/MakeHuman).

The base mesh OBJ carries the body, garment helpers (skirt, tights, hair) and one small cube per joint. Everything is
converted to Blender space here: metres, Z up, the character facing -Y, feet on z = 0.
"""
import bpy, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L

MH = os.path.abspath(os.path.join(L.PP, '..', 'Characters', 'ThirdParty', 'MakeHuman'))
MH2 = os.path.abspath(os.path.join(L.PP, '..', 'Characters', 'Milder', 'ThirdParty', 'MakeHuman'))


def parse_obj(path):
    """minimal OBJ reader that keeps groups: returns V (n, 3), VT (m, 2), faces [(group, [v...], [vt...])]"""
    V = []; VT = []; F = []; g = 'default'
    for line in open(path, errors='ignore'):
        if line.startswith('v '):
            p = line.split(); V.append((float(p[1]), float(p[2]), float(p[3])))
        elif line.startswith('vt '):
            p = line.split(); VT.append((float(p[1]), float(p[2])))
        elif line.startswith('g '):
            g = line.split(None, 1)[1].strip()
        elif line.startswith('f '):
            vi = []; ti = []
            for tok in line.split()[1:]:
                a = tok.split('/'); vi.append(int(a[0]) - 1); ti.append(int(a[1]) - 1 if len(a) > 1 and a[1] else -1)
            F.append((g, vi, ti))
    return np.array(V, np.float64), np.array(VT, np.float64) if VT else np.zeros((0, 2)), F


def to_blender(V, ground=0.0):
    """MakeHuman (decimetres, Y up, facing +Z) -> Blender (metres, Z up, facing -Y)"""
    return np.stack([V[:, 0], -V[:, 2], V[:, 1] - ground], 1) * 0.1


class Base:
    """the base mesh in Blender space, with joint centres and face groups"""

    def __init__(s):
        V, VT, F = parse_obj(os.path.join(MH, 'CC0_BaseMesh.obj')); s.VT = VT; s.F = F; jv = {}
        for g, vi, ti in F:
            if g.startswith('joint-'):
                jv.setdefault(g[6:], set()).update(vi)
        gy = float(np.mean([V[i][1] for i in jv['ground']])); s.V = to_blender(V, gy); s.J = {k: s.V[sorted(v)].mean(0) for k, v in jv.items()}; s.ground_mh = gy
        s.groups = sorted({g for g, _, _ in F})

    def mesh(s, name, groups, c=None, V=None, keep=None):
        """object from the faces of the given groups (keep(face_centre) filters faces); UVs kept. Returns (object, original vertex index per new vertex)"""
        V = s.V if V is None else V; used = {}; verts = []; faces = []; uvs = []
        for g, vi, ti in s.F:
            if g not in groups:
                continue
            if keep is not None and not keep(V[vi].mean(0)):
                continue
            f = []
            for i in vi:
                if i not in used:
                    used[i] = len(verts); verts.append(V[i])
                f.append(used[i])
            faces.append(f); uvs.append([s.VT[t] if t >= 0 else (0.0, 0.0) for t in ti])
        ob = L.new_obj(name, verts, faces, c); uv = ob.data.uv_layers.new(name='UVMap')
        for poly, fu in zip(ob.data.polygons, uvs):
            for li, t in zip(poly.loop_indices, fu):
                uv.data[li].uv = t
        orig = np.zeros(len(verts), np.int64)
        for i, k in used.items():
            orig[k] = i
        return ob, orig


def part(name, relpath, ground_mh, c=None, root=None):
    """a bundled part (eyes, brows, lashes, hair) as an object in Blender space; its OBJ is already fitted to the default base mesh"""
    V, VT, F = parse_obj(os.path.join(root or MH, relpath)); Vb = to_blender(V, ground_mh); ob = L.new_obj(name, Vb, [vi for _, vi, _ in F], c); uv = ob.data.uv_layers.new(name='UVMap')
    for poly, (_, vi, ti) in zip(ob.data.polygons, F):
        for li, t in zip(poly.loop_indices, ti):
            uv.data[li].uv = VT[t] if t >= 0 else (0.0, 0.0)
    return ob
