"""Stairs of the house interiors (428 inside/stairs/stair-), as the five pictures read in a 3D room.

  frames 1, 3   a flight going up along the wall in a corner of the ground floor: SM_Stair_Flight_L / _R
                (closed strings, risers, boarded spandrel, newel, handrail and balusters; 3.5 m storey of the kit)
  frames 2, 4   the opening in the upper floor with the flight going down: SM_Stair_Well_L / _R
                (trimmer curb, newels, rails and balusters on three sides, the first treads fading into the dark)
  frame 5       the plank door with a barred light on the cellar's north wall: SM_Door_Barred

Uses the board builder, the oak and iron materials, the bake and the review scene of the Unclaimed kit's tools
(read, not changed); sources and manifests land in this kit (PhotorealPass/FableF/stairs_wood, cellar_hatch).

    blender -b --factory-startup -t 4 --python tools/build_stairs.py -- <name,name|all> [review|final]
"""
import bpy, math, os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(KIT), 'Unclaimed', 'tools'))
import pplib as L
L.UNC = KIT
L.REVIEW = os.environ.get('DINK_REVIEW') or os.path.join(KIT, '_review')
import build_tools as T
import build_props as P
import build_wood as W
from pplib import NT

SCRIPT = 'build_stairs.py'
N = 18
RISE = 3.5 / N
GO = 0.235
WD = 1.05


def mirror(parts):
    for o in parts:
        o.scale = (-1, 1, 1)
        L.apply_xf(o)
        L.fix_normals(o)
    return parts


def dark_mat(name, col=(0.004, 0.004, 0.005)):
    t = NT(name)
    t.set(base=col, rough=0.95)
    return t.mat


def flight(hi, c, flip=False):
    """rises toward +X; the open side is the front (-Y), the wall side the back"""
    m = W.woods(hi, light=(0.165, 0.092, 0.04), dark=(0.055, 0.028, 0.012))
    parts = []
    run = GO * (N - 1)
    ang = math.atan2(RISE, GO)

    def nose(x):                                       # the pitch line through the nosings
        return RISE + x * RISE / GO
    for i, y in enumerate((0.0, WD - 0.045)):          # closed strings
        ln = math.hypot(run + 0.02, nose(run + 0.02) - nose(0)) + 0.1
        W.board(parts, 'string%d' % i, (-0.14, y, -0.16), (ln - 0.14, y + 0.045, 0.2), c, hi, m, axis=0, seed=i, bevel=0.005, rot=('Y', -ang, (0, 0, RISE * 0.55)))
    for k in range(N - 1):
        x = k * GO
        z = (k + 1) * RISE
        W.board(parts, 'tread%d' % k, (x - 0.028, 0.04, z - 0.04), (x + GO, WD - 0.04, z), c, hi, m, axis=1, seed=10 + k, bevel=0.007, warp=0.002)
        W.board(parts, 'riser%d' % k, (x, 0.045, z - RISE), (x + 0.02, WD - 0.045, z - 0.04), c, hi, m, axis=1, seed=40 + k, bevel=0.003, warp=0.001)
        zt = nose(x) - 0.36                              # boarded spandrel under the outer string
        if zt > 0.2:
            W.board(parts, 'span%d' % k, (x + 0.003, 0.008, 0.0), (x + GO - 0.003, 0.03, zt + 0.06), c, hi, m, axis=2, seed=70 + k, bevel=0.003, warp=0.0015)
        for j, dx in enumerate((0.055, 0.172)):         # two square balusters a tread
            xb = x + dx
            W.board(parts, 'bal%d_%d' % (k, j), (xb - 0.016, 0.007, nose(xb) - 0.02), (xb + 0.016, 0.039, nose(xb) + 0.84), c, hi, m, axis=2, seed=100 + k * 2 + j, bevel=0.003, warp=0.0008)
    W.board(parts, 'newel', (-0.2, -0.03, 0.0), (-0.09, 0.08, 1.2), c, hi, m, axis=2, seed=200, bevel=0.008, warp=0.001)
    W.board(parts, 'newel_cap', (-0.215, -0.045, 1.2), (-0.075, 0.095, 1.245), c, hi, m, axis=0, seed=201, bevel=0.01)
    ln = math.hypot(run + 0.12, nose(run) - nose(-0.12))
    W.board(parts, 'rail', (-0.12, -0.008, 0.0), (ln - 0.12, 0.054, 0.05), c, hi, m, axis=0, seed=202, bevel=0.012, rot=('Y', -ang, (-0.12, 0, 0)))
    parts[-1].location = (0, 0, nose(-0.12) + 0.84)
    L.apply_xf(parts[-1])
    return mirror(parts) if flip else parts


def well(hi, c, flip=False):
    """opening 2.9 x 1.2 m in the floor: entered at the -X end, the flight goes down toward +X; rails on the other three sides"""
    m = W.woods(hi, light=(0.165, 0.092, 0.04), dark=(0.055, 0.028, 0.012))
    parts = []
    x0, x1, y0, y1 = -1.45, 1.45, 0.0, 1.2
    W.board(parts, 'curb_f', (x0, y0 - 0.09, 0.0), (x1 + 0.09, y0, 0.07), c, hi, m, axis=0, seed=1, bevel=0.006)
    W.board(parts, 'curb_b', (x0, y1, 0.0), (x1 + 0.09, y1 + 0.09, 0.07), c, hi, m, axis=0, seed=2, bevel=0.006)
    W.board(parts, 'curb_e', (x1, y0, 0.0), (x1 + 0.09, y1, 0.07), c, hi, m, axis=1, seed=3, bevel=0.006)
    o = L.box('void', (x0, y0, 0.001), (x1, y1, 0.005), c, hi, bevel=0.001)
    if hi:
        o.data.materials.append(dark_mat('void'))
    parts.append(o)
    for k in range(5):                                  # the first treads, each darker: the flight sinks into the dark
        f = (1.0, 0.5, 0.24, 0.1, 0.035)[k]
        mk = T.wood_mat('tread_dark_%d' % k, axis=1, light=tuple(v * f for v in (0.165, 0.092, 0.04)), dark=tuple(v * f for v in (0.065, 0.033, 0.014))) if hi else None
        W.board(parts, 'tread%d' % k, (x0 + k * GO, y0 + 0.01, 0.005), (x0 + (k + 1) * GO - 0.012, y1 - 0.01, 0.011 if k else 0.03), c, hi, m, axis=1, seed=20 + k, bevel=0.004, mat=mk)
    for i, (x, y) in enumerate(((x0 - 0.02, y0 - 0.1), (x1 - 0.01, y0 - 0.1), (x1 - 0.01, y1 - 0.01), (x0 - 0.02, y1 - 0.01))):
        W.board(parts, 'newel%d' % i, (x, y, 0.0), (x + 0.11, y + 0.11, 1.08), c, hi, m, axis=2, seed=30 + i, bevel=0.008, warp=0.001)
        W.board(parts, 'cap%d' % i, (x - 0.015, y - 0.015, 1.08), (x + 0.125, y + 0.125, 1.125), c, hi, m, axis=0, seed=40 + i, bevel=0.01)
    W.board(parts, 'rail_f', (x0 + 0.09, y0 - 0.077, 0.93), (x1 - 0.01, y0 - 0.013, 0.98), c, hi, m, axis=0, seed=50, bevel=0.012)
    W.board(parts, 'rail_b', (x0 + 0.09, y1 + 0.013, 0.93), (x1 - 0.01, y1 + 0.077, 0.98), c, hi, m, axis=0, seed=51, bevel=0.012)
    W.board(parts, 'rail_e', (x1 + 0.013, y0 + 0.01, 0.93), (x1 + 0.077, y1 - 0.01, 0.98), c, hi, m, axis=1, seed=52, bevel=0.012)
    nb = 21
    for i in range(nb):
        x = x0 + 0.2 + (x1 - x0 - 0.3) * i / (nb - 1)
        W.board(parts, 'bal_f%d' % i, (x - 0.016, y0 - 0.061, 0.07), (x + 0.016, y0 - 0.029, 0.93), c, hi, m, axis=2, seed=60 + i, bevel=0.003, warp=0.0008)
        W.board(parts, 'bal_b%d' % i, (x - 0.016, y1 + 0.029, 0.07), (x + 0.016, y1 + 0.061, 0.93), c, hi, m, axis=2, seed=90 + i, bevel=0.003, warp=0.0008)
    for i in range(8):
        y = y0 + 0.13 + (y1 - y0 - 0.26) * i / 7
        W.board(parts, 'bal_e%d' % i, (x1 + 0.029, y - 0.016, 0.07), (x1 + 0.061, y + 0.016, 0.93), c, hi, m, axis=2, seed=120 + i, bevel=0.003, warp=0.0008)
    return mirror(parts) if flip else parts


def door(hi, c):
    """ledged plank door, 0.95 x 2.0 m, in a plain oak frame, with a barred light at head height; stands against a wall, front on -Y"""
    m = W.woods(hi, light=(0.062, 0.036, 0.018), dark=(0.02, 0.011, 0.006))
    parts = []
    w, h = 0.95, 2.0
    for i in range(5):
        xa = -w / 2 + i * w / 5
        W.board(parts, 'plank%d' % i, (xa + 0.002, 0.0, 0.01), (xa + w / 5 - 0.002, 0.035, h), c, hi, m, axis=2, seed=i, bevel=0.004, warp=0.0015)
    for i, z in enumerate((0.28, 1.02, 1.78)):
        W.board(parts, 'ledge%d' % i, (-w / 2 + 0.03, -0.028, z), (w / 2 - 0.03, 0.0, z + 0.13), c, hi, m, axis=0, seed=10 + i, bevel=0.005)
    for i, x in enumerate((-w / 2 - 0.11, w / 2)):
        W.board(parts, 'jamb%d' % i, (x, -0.03, 0.0), (x + 0.11, 0.09, h + 0.02), c, hi, m, axis=2, seed=20 + i, bevel=0.007, warp=0.001)
    W.board(parts, 'head', (-w / 2 - 0.13, -0.035, h + 0.02), (w / 2 + 0.13, 0.095, h + 0.15), c, hi, m, axis=0, seed=22, bevel=0.007)
    # the light: a dark opening behind a framed iron grille
    o = L.box('light', (-0.17, -0.004, 1.34), (0.17, 0.0, 1.66), c, hi, bevel=0.001)
    if hi:
        o.data.materials.append(dark_mat('light_dark', (0.012, 0.018, 0.03)))
    parts.append(o)
    iron = T.iron_mat('iron', rust=0.55) if hi else None
    for i in range(4):
        x = -0.12 + i * 0.08
        W.board(parts, 'bar%d' % i, (x - 0.008, -0.022, 1.33), (x + 0.008, -0.006, 1.67), c, hi, m, axis=2, seed=30 + i, bevel=0.004, mat=iron)
    for i, z in enumerate((1.42, 1.58)):
        W.board(parts, 'cross%d' % i, (-0.175, -0.026, z - 0.007), (0.175, -0.012, z + 0.007), c, hi, m, axis=0, seed=36 + i, bevel=0.003, mat=iron)
    for i, (a, b) in enumerate(((-0.2, -0.17), (0.17, 0.2))):
        W.board(parts, 'lf%d' % i, (a, -0.03, 1.31), (b, 0.0, 1.69), c, hi, m, axis=2, seed=40 + i, bevel=0.004)
    for i, (a, b) in enumerate(((1.31, 1.34), (1.66, 1.69))):
        W.board(parts, 'lh%d' % i, (-0.2, -0.03, a), (0.2, 0.0, b), c, hi, m, axis=0, seed=44 + i, bevel=0.004)
    for i, z in enumerate((0.33, 1.83)):               # strap hinges and a ring pull
        W.board(parts, 'strap%d' % i, (-w / 2 + 0.01, -0.036, z), (w / 2 - 0.3, -0.028, z + 0.045), c, hi, m, axis=0, seed=50 + i, bevel=0.003, mat=iron)
    W.board(parts, 'pull', (w / 2 - 0.13, -0.05, 1.0), (w / 2 - 0.09, -0.028, 1.14), c, hi, m, axis=2, seed=55, bevel=0.006, mat=iron)
    return parts


W_J = ' Boards are bevelled blocks butted together: no joints, pegs or nails are modelled, and the grain is procedural streaking, not a scan. Every board is 12 triangles in the game mesh, so edge rounding is in the normal map only.'
SPECS = {
    'Stair_Flight_L': dict(fn=lambda hi, c: flight(hi, c, True), fam='stairs_wood', seq='428 inside/stairs/stair- frame 1', dresses='oak stair going up to the left along a wall: closed strings, risers, boarded spandrel, newel, handrail and balusters; eighteen risers for the 3.5 m storey'),
    'Stair_Flight_R': dict(fn=lambda hi, c: flight(hi, c, False), fam='stairs_wood', seq='428 inside/stairs/stair- frame 3', dresses='as Stair_Flight_L, going up to the right'),
    'Stair_Well_L': dict(fn=lambda hi, c: well(hi, c, False), fam='stairs_wood', seq='428 inside/stairs/stair- frame 2', dresses='stair opening in an upper floor, 2.9 x 1.2 m: trimmer curb, four newels, rails and balusters on three sides, the first treads sinking into the dark; entered from the left'),
    'Stair_Well_R': dict(fn=lambda hi, c: well(hi, c, True), fam='stairs_wood', seq='428 inside/stairs/stair- frame 4', dresses='as Stair_Well_L, entered from the right'),
    'Door_Barred': dict(fn=door, fam='cellar_hatch', seq='428 inside/stairs/stair- frame 5', px=1024, cls='door', dresses='dark ledged plank door in an oak frame with a barred light at head height, 0.95 x 2.0 m, standing against the wall'),
}
WEAK = {
    'Stair_Flight': 'The flight ends at 3.5 m without a landing or a trimmed ceiling opening: in the room it runs into the ceiling. One convex hull would close the space under it, so no collision is exported.' + W_J,
    'Stair_Well': 'There is no hole: the floor of the room cannot be cut, so the opening is a black board 5 mm above the floor with five treads painted darker and darker. From the play camera the rails hide most of it; from straight above it is flat.' + W_J,
    'Door_Barred': 'The light is a dark panel behind the bars, not an opening, and the door does not open. The 1997 picture shows blue glints in the grille that are not reproduced.' + W_J,
}
for k_, v_ in SPECS.items():
    v_.setdefault('cls', 'prop_large')
    v_.setdefault('px', 2048)
    v_.update(tris=0, lo='param', ground='weathered_brown_planks', third=['rusty_metal_02'] if k_ == 'Door_Barred' else [], extrude=0.004, maxdist=0.012, collision=False,
              shot=dict(az=-24 if k_.endswith('_L') else 24, el=14, fill=1.0), weak=WEAK[k_.rsplit('_', 1)[0] if k_[-2:] in ('_L', '_R') else k_], script=SCRIPT)
P.SPECS.update(SPECS)


def fix_manifest(name):
    """the shared finisher writes the Unclaimed kit's wording: put this kit's build line and status"""
    sp = SPECS[name]
    path = os.path.join(KIT, sp['fam'], name, 'manifest.json')
    m = json.load(open(path))
    m['build'] = 'blender -b --factory-startup -t 4 --python FableF/tools/build_stairs.py -- %s final' % name
    m['status'] = 'source delivered'
    m['source_note'] = 'the .blend holds the game mesh with its baked set; the dense boards it was baked from are rebuilt by the script (they were removed after the bake to keep the file small)'
    m['material_exception'] = 'unique BC/N/ORM bake private to this asset: the joinery needs its own ambient occlusion and wear'
    json.dump(m, open(path, 'w'), indent=1)
    open(path, 'a').write('\n')
    c = bpy.data.collections.get('Source_Hi')
    for o in (list(c.objects) if c else []):
        bpy.data.objects.remove(o)
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(KIT, sp['fam'], name, 'SM_%s_PR.blend' % name), compress=True)


if __name__ == '__main__':
    a = L.args()
    names = list(SPECS) if a[0] == 'all' else a[0].split(',')
    mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
        if mode != 'review':
            fix_manifest(n)
