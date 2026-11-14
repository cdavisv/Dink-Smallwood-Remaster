"""Shared gear generators for the non-hero characters. The boot / sole / tube / strap generators are taken verbatim
from dink_03_gear.py (read as source, so the Dink stage stays untouched); belts, buckles, plates and skirts are generic."""
import bpy, bmesh, math, ast
import numpy as np
from pathlib import Path
from mathutils import Vector
from prlib import *; from garlib import *

_src = (Path(__file__).parent / 'dink_03_gear.py').read_text()
_want = ('catmull', 'interp', 'put_lat', 'tag', 'set_chart', 'boot', 'sole', 'tube', 'on_surface', 'sheet', 'strap_on')
for _n in ast.parse(_src).body:
    if isinstance(_n, ast.FunctionDef) and _n.name in _want:
        exec(compile(ast.Module([_n], []), 'dink_03_gear.py', 'exec'), globals())

MIR = np.array([-1, 1, 1.0])
def init(arm, bvh):
    """Bone landmarks + the body BVH the generators ray-cast against."""
    global S, E_, Wr, T, K, A, BALL, body_bvh, LU, LF, dU, dF
    B = arm.data.bones
    def bh(n): return np.array(B[n].head_local)
    S, E_, Wr = bh('upperarm_l'), bh('lowerarm_l'), bh('hand_l')
    T, K, A, BALL = bh('thigh_l'), bh('calf_l'), bh('foot_l'), bh('ball_l')
    LU = np.linalg.norm(E_ - S); LF = np.linalg.norm(Wr - E_); dU = (E_ - S) / LU; dF = (Wr - E_) / LF
    body_bvh = bvh

def mirx(c):
    m = np.array(c, float).copy(); m[..., 0] = np.abs(m[..., 0]); return m
def s_arm(c): return (mirx(c) - S) @ dU
def f_arm(c): return (mirx(c) - E_) @ dF

def put(o, name, arr):
    a = o.data.attributes.get(name) or o.data.attributes.new(name, 'FLOAT', 'POINT'); a.data.foreach_set('value', np.asarray(arr, np.float32))

def displace(o, fn, fine):
    co = co_np(o.data); o.data.update(); nr = normals_np(o.data)
    set_co(o.data, co + nr * fn(co, fine)[:, None])

def finish(base, fn, target_tris, classify, charts, fabric, name, lipsel=None, lip=(.0025, .012), mat='outfit', seams=None, hi_levels=1, recut=()):
    """base (cut, undisplaced) -> name_HI (subdivided, all folds, seam attributes) and the game mesh (decimated, lips).
    recut: the garment's own cut functions moved a few millimetres into the cloth; the decimated mesh is cut again
    along them so that every opening has a clean rim (decimation leaves a torn one: see dink_02_garments.finish)."""
    hi = dup(base, name + '_HI'); subdivide(hi, hi_levels)
    if seams:
        sm, st = seams(co_np(hi.data)); put(hi, 'd_seam', sm); put(hi, 'd_stitch', st)
    displace(hi, fn, True); smooth_shade(hi)
    lo = dup(base, name); displace(lo, fn, True)
    t = tri_count(lo); d = lo.modifiers.new('dec', 'DECIMATE'); d.ratio = min(1, target_tris / t); apply_mods(lo)
    for f_ in recut: implicit_cut(lo, f_)
    if recut: tidy_rim(lo); log(name, 'rims re-cut after decimation, tris', tri_count(lo))
    smooth_shade(lo)
    for o in (hi, lo):
        chart_uv(o, classify, charts); o['fabric'] = fabric; o['mat'] = mat
    smooth_boundary(lo)
    if lip: add_lips(lo, lip[0], lip[1], select=lipsel)
    log(name, 'hi tris', tri_count(hi), 'game tris', tri_count(lo))
    bpy.data.objects.remove(base, do_unlink=True)
    return lo, hi

def grid_obj(name, P, closed_u=True, cap_end=False, cap_start=False):
    """P: (nr, nu, 3) array -> lofted object with metric UVs."""
    return loft(name, [list(map(tuple, r)) for r in P], closed=closed_u, cap_end=cap_end, cap_start=cap_start)

def ring_radius(bvh, c, d, far=.6, default=.15):
    hit = bvh.ray_cast(Vector(c + d * far), Vector(-d), far)
    return float((np.array(hit[0]) - c) @ d) if hit[0] is not None else default

def belt_path(n, bvh, z0, drop=.010, cy=-.02, tilt=0.0, far=.30):
    out = []
    for k in range(n):
        p = 2 * np.pi * k / n
        z = z0 - drop * np.cos(p) + tilt * np.sin(p)
        d = np.array([np.sin(p), -np.cos(p), 0]); c = np.array([0, cy, z])
        out.append((p, c, d, ring_radius(bvh, c, d, far)))
    rr = np.array([o[3] for o in out])
    for _ in range(4): rr = (np.roll(rr, 1) + 2 * rr + np.roll(rr, -1)) / 4
    return [(p, c, d, r) for (p, c, d, _), r in zip(out, rr)]

def make_belt(name, bvh, z0, fabric, h=.0175, t=.0042, n_lo=72, n_hi=256, chart=51, mat='gear', **kw):
    objs = []
    for hi in (False, True):
        rings = []
        for p, c, d, r in belt_path(n_hi if hi else n_lo, bvh, z0, **kw):
            r0 = r + .0012; up = np.array([0, 0, 1.0])
            sec = [(0, -h), (t * .75, -h - .0006), (t, -h + .003), (t * 1.08, 0), (t, h - .003), (t * .75, h + .0006), (0, h)]
            rings.append([tuple(c + d * (r0 + a) + up * b) for a, b in sec] + [tuple(c + d * (r0 - .001) + up * 0)])
        rings.append(rings[0])
        o = loft(name + ('_HI' if hi else ''), rings)
        put_lat(o, [-h, -h - .0006, -h + .003, 0, h - .003, h + .0006, h, 0] * len(rings), h - .004)
        activate(o); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
        set_chart(o, chart); tag(o, fabric, mat); smooth_shade(o); objs.append(o)
    return objs, belt_path(256, bvh, z0, **kw), t

def belt_pt(bp, p, out=0.0, dz=0.0, t=.0042):
    k = int(round((p % (2 * np.pi)) / (2 * np.pi) * 256)) % 256; _, c, d, r = bp[k]
    return c + d * (r + .0012 + t + out) + np.array([0, 0, dz]), d

def make_buckle(name, bp, fabric='brass', W=.023, H=.022, chart=52, t=.0042, at=0.0, mat='gear', wire=.0030):
    zax = np.array([0, 0, 1.0]); r = bp[0][3]
    def on_belt(xo, zo, out=0.0):
        q, d = belt_pt(bp, at + xo / r, .0026 + out, t=t); return q + zax * zo
    frame = []
    for k in range(24):
        a = 2 * np.pi * k / 24; cx, cz = math.cos(a), math.sin(a); ex = 4.0
        rr = 1.0 / (abs(cx / W) ** ex + abs(cz / H) ** ex) ** (1 / ex)
        frame.append(on_belt(rr * cx - .004, rr * cz, .0008))
    buck = tube(name, frame, wire, 6, closed=True)
    bar = tube(name + 'Bar', [on_belt(-.004 - W * .55, z_, .0004) for z_ in np.linspace(-H, H, 3)], wire * .73, 5)
    tongue = tube(name + 'Tongue', [on_belt(-.004 - W * .55, 0, .0030), on_belt(-.004, 0, .0034), on_belt(-.004 + W * .85, 0, .0036), on_belt(-.004 + W * 1.02, 0, .0030)], lambda u: wire * .8 - wire * .3 * u, 5)
    bk = join([buck, bar, tongue], name); set_chart(bk, chart); tag(bk, fabric, mat, scale=1.5); smooth_shade(bk)
    bkh = dup(bk, name + '_HI'); subdivide(bkh, 2); smooth_shade(bkh)
    return bk, bkh

def skirt_weights(o, zw, zh, knee_z=.50, leg_max=.92, calf_max=.35, top=.04, full=.38, xw=.09, extra=None, calf_back=None):
    """Authored skirt skinning: pelvis at the waistband, blending to the thigh of each side (smooth lateral blend so
    the cloth spans between the legs), with a calf share below the knee. Marks the object so stage 6 keeps it."""
    co = co_np(o.data); t = np.clip((zw - co[:, 2]) / (zw - zh), 0, 1)
    L = sstep(top, full, t) * leg_max; wl = sstep(-xw, xw, co[:, 0]); kb = sstep(knee_z + .10, knee_z - .14, co[:, 2]) * (calf_max if calf_back is None else calf_max + (calf_back - calf_max) * sstep(-.06, .10, co[:, 1]))
    W = {'pelvis': 1 - L, 'thigh_l': L * wl * (1 - kb), 'thigh_r': L * (1 - wl) * (1 - kb), 'calf_l': L * wl * kb, 'calf_r': L * (1 - wl) * kb}
    if extra: W = extra(co, W)
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    for nme, w in W.items():
        g = o.vertex_groups.new(name=nme)
        for i in np.nonzero(w > 1e-4)[0]: g.add([int(i)], float(w[i]), 'REPLACE')
    o['weights'] = 'keep'

def fix_lip_charts(o):
    """add_lips makes faces with chart id 0; give them the chart of the face they hang from so they pack with it."""
    bm = bmesh.new(); bm.from_mesh(o.data); lay = bm.faces.layers.int.get('chart')
    if lay is None: bm.free(); return
    for _ in range(3):
        for f in bm.faces:
            if f[lay] == 0:
                for e in f.edges:
                    nb = [g for g in e.link_faces if g is not f and g[lay] != 0]
                    if nb: f[lay] = nb[0][lay]; break
    bm.to_mesh(o.data); bm.free()
