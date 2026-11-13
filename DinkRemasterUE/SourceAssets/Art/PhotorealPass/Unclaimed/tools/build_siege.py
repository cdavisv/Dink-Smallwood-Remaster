"""Siege engines of the unclaimed families (429 struct/cataplt/arms-): the catapult (frame 1) and the ballista (frame 4).

Timber is one bevelled block per member; iron, rope and the counterweight stone are separate parts.

    tools/bl.sh build_siege.py <Catapult|Ballista|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
import build_props as P
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_siege.py'


class Kit:
    """timber / iron / rope part builder that keeps the grain along each member"""

    def __init__(s, c, hi, light=(0.22, 0.125, 0.055), dark=(0.075, 0.04, 0.018)):
        s.c = c; s.hi = hi; s.parts = []; s.n = 0
        s.wood = [T.wood_mat('oak_%s' % 'xyz'[a], axis=a, light=light, dark=dark) for a in range(3)] if hi else [None] * 3
        s.iron = T.iron_mat('iron', rust=0.6, seed=31.0) if hi else None; s.rope = None
        if hi:
            t = NT('rope'); n = t.noise(500, 3, 0.6); tw = t.noise(1.0, 2, 0.5, vec=t.mapping(scale=(260, 260, 260))); t.set(base=t.mix(n, (0.12, 0.09, 0.05), (0.33, 0.26, 0.15)), rough=0.9, normal=t.bump(tw, 0.7, 0.002)); s.rope = t.mat

    def beam(s, mn, mx, rot=None, bevel=0.012, mat=None, axis=None):
        d = np.abs(np.array(mx, float) - np.array(mn, float)); ax = int(np.argmax(d)) if axis is None else axis; s.n += 1
        o = L.box('beam%d' % s.n, mn, mx, s.c, s.hi, bevel=bevel, warp=0.004, seed=s.n, rot=rot)
        if s.hi:
            o.data.materials.append(mat or s.wood[ax])
        s.parts.append(o); return o

    def rod(s, rows, kind='wood', nu=10, nv=8, up=(0, 0, 1), cap=0.7, axis=0):
        s.n += 1; o = L.sweep('rod%d' % s.n, rows, nu=nu * (3 if s.hi else 1), nv=nv * (3 if s.hi else 1), c=s.c, up=up, cap=cap)
        if s.hi:
            o.data.materials.append({'wood': s.wood[axis], 'iron': s.iron, 'rope': s.rope}[kind])
        s.parts.append(o); return o


def catapult(hi, c):
    """counterweight catapult, 4.6 m long: sill frame, two braced uprights carrying the axle, a throwing arm with a bowl, a stone counterweight in iron straps, a windlass with handspikes"""
    k = Kit(c, hi); PIV = (0, 0.2, 2.05)
    for sx in (-1, 1):
        k.beam((sx * 0.75 - 0.09, -1.7, 0.0), (sx * 0.75 + 0.09, 1.7, 0.18)); k.beam((sx * 0.75 - 0.08, 0.12, 0.18), (sx * 0.75 + 0.08, 0.28, 2.25))
        for sy, y0 in ((-1, -1.25), (1, 1.45)):                 # diagonal braces fore and aft of each upright
            ln = math.hypot(y0 - 0.2, 1.5); ang = math.atan2(0.2 - y0, 1.5)
            k.beam((sx * 0.75 - 0.055, y0 - 0.055, 0.2), (sx * 0.75 + 0.055, y0 + 0.055, 0.2 + ln), rot=('X', -ang, (0, y0, 0.2)), axis=2)
    for y in (-1.5, 0.2, 1.5):
        k.beam((-0.98, y - 0.08, 0.18), (0.98, y + 0.08, 0.32))
    k.rod([(-0.95, PIV[1], PIV[2], 0.06, 0.06, 2.1), (0.95, PIV[1], PIV[2], 0.06, 0.06, 2.1)], kind='iron', nu=12, nv=4, up=(0, 0, 1))
    tilt = math.radians(30); Mt = Matrix.Translation(PIV) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((-PIV[0], -PIV[1], -PIV[2]))
    arm = k.beam((-0.09, PIV[1] - 3.0, PIV[2] - 0.1), (0.09, PIV[1] + 1.25, PIV[2] + 0.1)); L.xform(arm, Mt)
    seg = 40 if hi else 14; bowl = L.lathe('bowl', [(0, -0.26), (0.16, -0.24), (0.3, -0.12), (0.36, 0.04), (0.36, 0.08), (0.31, 0.07), (0.27, -0.06), (0.14, -0.17), (0, -0.19)], seg=seg, c=c, cap0=False, cap1=False)
    if hi:
        L.subsurf(bowl, 2); bowl.data.materials.append(k.wood[0])
    L.xform(bowl, Mt @ Matrix.Translation((0, PIV[1] - 3.0, PIV[2] + 0.26))); k.parts.append(bowl)
    rock = P.boulder('weight', (0.78, 0.7, 0.72), 41, c, hi, rough_amp=0.16, round_=0.8, sink=0.02, sub=6)
    if hi:
        rock.data.materials.append(P.rock_mat('weight', 'rock_boulder_dry', tint=(0.60, 0.60, 0.62), value=0.75, sat=0.4, moss=0.15, lichen=0.3, seed=9.0))
    else:
        d = L.decimate(rock, tris=260, name='weight_lo'); bpy.data.objects.remove(rock); rock = d
    wpos = Mt @ Matrix.Translation((0, PIV[1] + 1.2, PIV[2] - 0.85)); L.xform(rock, wpos); k.parts.append(rock)
    for a in (0.0, math.pi / 2):                               # two iron straps slung round the stone, up to the arm
        st = L.ring('strap', 0.42, 0.012, c, seg=40 if hi else 14, sides=6 if hi else 4, squash=2.2); L.xform(st, wpos @ Matrix.Translation((0, 0, 0.4)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        if hi:
            st.data.materials.append(k.iron)
        k.parts.append(st)
    for sx in (-1, 1):
        k.beam((sx * 0.75 - 0.06, -1.36, 0.18), (sx * 0.75 + 0.06, -1.24, 0.72))
    k.rod([(-0.9, -1.3, 0.58, 0.07, 0.07, 2.1), (0.9, -1.3, 0.58, 0.07, 0.07, 2.1)], nu=12, nv=4, up=(0, 0, 1), axis=0)
    for sx in (-1, 1):
        for a in (0.5, 0.5 + math.pi / 2):
            k.rod([(sx * 0.88, -1.3 - 0.3 * math.cos(a), 0.58 - 0.3 * math.sin(a), 0.018, 0.018, 2), (sx * 0.88, -1.3 + 0.3 * math.cos(a), 0.58 + 0.3 * math.sin(a), 0.018, 0.018, 2)], nu=6, nv=3, up=(1, 0, 0), axis=1)
    tip = Mt @ Matrix.Translation((0, PIV[1] - 2.7, PIV[2] - 0.1)); tp = tip.translation
    k.rod([(0.0, -1.3, 0.64, 0.016, 0.016, 2), (0.0, (tp[1] - 1.3) / 2, (tp[2] + 0.6) / 2 - 0.06, 0.016, 0.016, 2), (tp[0], tp[1], tp[2], 0.016, 0.016, 2)], kind='rope', nu=6, nv=8, up=(1, 0, 0))
    return k.parts


def ballista(hi, c):
    """ballista, 2.9 m long: a braced stand, a grooved stock, two bow limbs in a head frame, a cord drawn back to the trigger, a windlass and a loaded bolt"""
    k = Kit(c, hi, light=(0.24, 0.14, 0.06)); z0 = 1.0
    for sy in (-0.55, 0.75):                                   # two trestles
        for sx in (-1, 1):
            k.beam((-0.045, sy - 0.045, 0.0), (0.045, sy + 0.045, 1.12), rot=('Y', sx * math.radians(26), (0, sy, z0)), axis=2)
        k.beam((-0.62, sy - 0.04, 0.0), (0.62, sy + 0.04, 0.09))
    k.beam((-0.05, -0.6, 0.3), (0.05, 0.8, 0.39))
    tilt = math.radians(-7); Mt = Matrix.Translation((0, 0, z0)) @ Matrix.Rotation(tilt, 4, 'X')

    def T_(o):
        return L.xform(o, Mt)
    T_(k.beam((-0.085, -1.45, -0.02), (0.085, 1.35, 0.12)))                                              # stock
    T_(k.beam((-0.03, -1.4, 0.12), (0.03, 1.0, 0.15), mat=k.iron if hi else None, bevel=0.004))            # iron-shod slide
    for sx in (-1, 1):                                          # head frame: two uprights and caps that hold the limbs
        T_(k.beam((sx * 0.36 - 0.045, -1.34, -0.2), (sx * 0.36 + 0.045, -1.24, 0.36), axis=2))
    for z in (-0.2, 0.3):
        T_(k.beam((-0.46, -1.35, z), (0.46, -1.23, z + 0.07)))
    for sx in (-1, 1):
        T_(k.rod([(sx * 0.3, -1.29, 0.08, 0.04, 0.034, 2.4), (sx * 0.62, -1.2, 0.08, 0.036, 0.03, 2.4), (sx * 1.0, -0.98, 0.08, 0.03, 0.026, 2.4), (sx * 1.28, -0.68, 0.08, 0.022, 0.02, 2.4)], nu=8, nv=10, up=(0, 0, 1), axis=0))
        T_(k.rod([(sx * 1.27, -0.69, 0.08, 0.007, 0.007, 2), (sx * 0.6, 0.05, 0.14, 0.007, 0.007, 2), (0.0, 0.62, 0.17, 0.007, 0.007, 2)], kind='rope', nu=5, nv=8, up=(0, 0, 1)))
    T_(k.beam((-0.05, 0.56, 0.12), (0.05, 0.72, 0.2), mat=k.iron if hi else None, bevel=0.006))            # trigger block
    for sx in (-1, 1):
        T_(k.beam((sx * 0.13 - 0.03, 1.08, -0.02), (sx * 0.13 + 0.03, 1.16, 0.3), axis=2))
    T_(k.rod([(-0.42, 1.12, 0.2, 0.045, 0.045, 2.1), (0.42, 1.12, 0.2, 0.045, 0.045, 2.1)], nu=10, nv=4, up=(0, 0, 1), axis=0))
    for sx in (-1, 1):
        for a in (0.3, 0.3 + math.pi / 2):
            T_(k.rod([(sx * 0.4, 1.12 - 0.22 * math.cos(a), 0.2 - 0.22 * math.sin(a), 0.014, 0.014, 2), (sx * 0.4, 1.12 + 0.22 * math.cos(a), 0.2 + 0.22 * math.sin(a), 0.014, 0.014, 2)], nu=6, nv=3, up=(1, 0, 0), axis=1))
    T_(k.rod([(0, 0.6, 0.175, 0.016, 0.016, 2.1), (0, -0.6, 0.175, 0.018, 0.018, 2.1), (0, -1.5, 0.175, 0.016, 0.016, 2.1)], nu=8, nv=8, up=(0, 0, 1), axis=1))        # the bolt
    T_(k.rod([(0, -1.48, 0.175, 0.018, 0.018, 2.4), (0, -1.58, 0.175, 0.04, 0.012, 3), (0, -1.7, 0.175, 0.03, 0.008, 3), (0, -1.86, 0.175, 0.002, 0.002, 2.4)], kind='iron', nu=8, nv=8, up=(0, 0, 1), cap=0.3))
    return k.parts


W_T = ' Timbers are bevelled blocks pushed through each other: no mortises, pegs, iron bands or bolts, and nothing turns or fires (no rig, no animation). Grain is procedural streaking along each member. One convex hull is exported for the whole engine.'
SPECS = {
    'Catapult': dict(fn=catapult, fam='catapult', seq='429 struct/cataplt/arms- frame 1', cls='prop_large', px=2048, tris=0, lo='param', ground='forrest_ground_01', third=['rock_boulder_dry', 'rusty_metal_02'], extrude=0.008, maxdist=0.025, shot=dict(az=40, el=14, fill=1.0, close=(0.5, 0.75, 0.6, 0.22)),
                     weak='Built as a counterweight engine from one 260-pixel frame: the sling, release hook and trough of a real trebuchet are replaced by a fixed bowl, as the sprite shows.' + W_T,
                     dresses='catapult, 4.6 m long and 3.4 m to the counterweight: oak sill frame, two braced uprights with an iron axle, a throwing arm with a bowl, a strapped stone counterweight, a windlass with handspikes and a hauling rope'),
    'Ballista': dict(fn=ballista, fam='ballista', seq='429 struct/cataplt/arms- frame 4', cls='prop', px=2048, tris=0, lo='param', ground='forrest_ground_01', third=['rusty_metal_02'], extrude=0.006, maxdist=0.02, shot=dict(az=40, el=14, fill=1.0, close=(0.5, 0.2, 0.75, 0.25)),
                     weak='The limbs are plain tapered staves set in a simple frame: no torsion skeins, washers or ratchet. The cord is a 14 mm rope sweep without servings.' + W_T,
                     dresses='ballista, 2.9 m long with a 2.6 m bow: two trestles, a tilted stock with an iron-shod slide, bow limbs in a head frame, the cord drawn to the trigger, a windlass and a loaded iron-headed bolt'),
}
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
