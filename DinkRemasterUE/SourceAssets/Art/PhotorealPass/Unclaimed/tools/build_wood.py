"""Joinery of the unclaimed families: bookcase (64 inside/details/inacc- frame 4), hanging healer's sign (458 inside/details/sign-),
log cabin window (59 struct/cabin/cabin- frame 3) and the wooden stairs (428 inside/stairs/stair-).

Every board is its own block: 12 triangles in the game mesh; bevelled, subdivided and warped in the dense source.

    tools/bl.sh build_wood.py <name,name|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import build_tools as T
import build_props as P
from pplib import NT, fbm

SCRIPT = 'build_wood.py'
OAK = dict(light=(0.19, 0.105, 0.045), dark=(0.065, 0.033, 0.014))


def woods(hi, **kw):
    kw = dict(OAK, **kw); return [T.wood_mat('oak_%s' % 'xyz'[a], axis=a, **kw) for a in range(3)] if hi else [None] * 3


def board(parts, name, mn, mx, c, hi, mats, axis=None, seed=0, bevel=0.004, warp=0.0015, rot=None, mat=None):
    """adds a board; grain runs along its longest side unless axis is given"""
    d = np.abs(np.array(mx, float) - np.array(mn, float)); ax = int(np.argmax(d)) if axis is None else axis
    o = L.box(name, mn, mx, c, hi, bevel=bevel, warp=warp, seed=seed, rot=rot)
    if hi:
        o.data.materials.append(mat or mats[ax])
    parts.append(o); return o


# ---------------------------------------------------------------------------------------------- bookcase
def book_mat():
    """one material for every book: binding colour from the object, gilt bands and a label on the spine, cream page edges on top"""
    t = NT('books'); rnd = t.attr('rnd'); g = [None, None, t.attr('gz')]; nrm = t.sep(t.gnormal); n = t.noise(90, 4, 0.6); n2 = t.noise(420, 3, 0.6)
    col = t.ramp(rnd, [(0.0, (0.085, 0.030, 0.014)), (0.16, (0.16, 0.022, 0.016)), (0.30, (0.030, 0.060, 0.034)), (0.44, (0.10, 0.060, 0.028)), (0.58, (0.022, 0.034, 0.075)), (0.72, (0.20, 0.13, 0.065)), (0.86, (0.040, 0.026, 0.02)), (1.0, (0.13, 0.085, 0.03))], interp='CONSTANT')
    col = t.hsv(col, v=t.maprange(n, 0.2, 0.8, 0.7, 1.25)); spine = t.maprange(nrm[1], -0.6, -0.9, 0.0, 1.0)
    band = t.math('MAXIMUM', t.math('MAXIMUM', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', g[2], 0.16)), [(0.012, 1.0), (0.018, 0.0)]), t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', g[2], 0.84)), [(0.012, 1.0), (0.018, 0.0)])),
                  t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', g[2], 0.70)), [(0.006, 1.0), (0.01, 0.0)]))
    label = t.math('MULTIPLY', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', g[2], 0.56)), [(0.07, 1.0), (0.08, 0.0)]), t.ramp(t.math('FRACT', t.math('MULTIPLY', rnd, 7.31)), [(0.45, 0.0), (0.5, 1.0)]))
    gilt = t.math('MULTIPLY', t.math('MULTIPLY', band, spine), t.ramp(n2, [(0.3, 0.3), (0.6, 1.0)])); base = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', label, spine), 0.8), col, t.hsv(col, v=0.45)); base = t.mix(gilt, base, (0.62, 0.42, 0.12))
    wear = t.math('MULTIPLY', t.ramp(t.pointiness, [(0.51, 0.0), (0.56, 1.0)]), t.ramp(n, [(0.3, 0.2), (0.7, 1.0)])); base = t.mix(t.math('MULTIPLY', wear, 0.65), base, (0.30, 0.22, 0.14))
    pages = t.math('MAXIMUM', t.maprange(nrm[2], 0.6, 0.9, 0.0, 1.0), t.maprange(nrm[1], 0.6, 0.9, 0.0, 1.0)); pg = t.math('SINE', t.math('MULTIPLY', t.sep(t.obj)[0], 9000.0))
    base = t.mix(pages, base, t.mix(t.maprange(pg, -1, 1, 0, 1), (0.36, 0.30, 0.20), (0.62, 0.55, 0.40))); dust = t.math('MULTIPLY', t.maprange(nrm[2], 0.5, 0.95, 0.0, 1.0), 0.45); base = t.mix(dust, base, (0.30, 0.28, 0.24))
    t.set(base=base, rough=t.mixf(gilt, t.mixf(n, 0.5, 0.75), 0.35), metal=t.mixf(gilt, 0.0, 0.9), normal=t.bump(t.math('ADD', t.math('MULTIPLY', n2, 0.4), t.math('ADD', t.math('MULTIPLY', t.math('MULTIPLY', band, spine), 1.2), t.math('MULTIPLY', t.math('MULTIPLY', pg, pages), 0.6))), 0.3, 0.0008))
    return t.mat


def tag(o, rng):
    """per-book values the shared material reads: a random number and the height fraction (they survive joining for the bake)"""
    import creature as C
    Pq = L.co(o); z = Pq[:, 2]; C.set_attr(o, 'rnd', np.full(len(Pq), rng.random())); C.set_attr(o, 'gz', (z - z.min()) / max(1e-6, z.max() - z.min()))


def bookcase(hi, c):
    rng2 = np.random.default_rng(99)
    W, H, D, th = 1.9, 1.78, 0.34, 0.032; m = woods(hi); parts = []; rng = np.random.default_rng(11); bm = book_mat() if hi else None
    for i, x0 in enumerate((-W / 2, W / 2 - th)):
        board(parts, 'side%d' % i, (x0, -D / 2, 0), (x0 + th, D / 2, H), c, hi, m, seed=i)
    board(parts, 'top', (-W / 2 - 0.015, -D / 2 - 0.015, H), (W / 2 + 0.015, D / 2, H + 0.036), c, hi, m, seed=3); board(parts, 'plinth', (-W / 2 + th, -D / 2 + 0.02, 0), (W / 2 - th, -D / 2 + 0.045, 0.085), c, hi, m, seed=4)
    board(parts, 'back', (-W / 2 + th, D / 2 - 0.014, 0.0), (W / 2 - th, D / 2, H), c, hi, m, axis=2, seed=5, warp=0.0008)
    zs = [0.085, 0.50, 0.92, 1.34]
    for k, z in enumerate(zs):
        board(parts, 'shelf%d' % k, (-W / 2 + th, -D / 2 + 0.006, z), (W / 2 - th, D / 2 - 0.014, z + 0.028), c, hi, m, seed=10 + k, warp=0.0025)
        clear = (zs[k + 1] if k + 1 < len(zs) else H) - z - 0.028; x = -W / 2 + th + 0.006; z0 = z + 0.028; nb = 0
        while x < W / 2 - th - 0.03:
            r = rng.random()
            if r < 0.07:                                      # a gap
                x += rng.uniform(0.04, 0.12); continue
            if r < 0.13 and x < W / 2 - th - 0.3:             # a flat stack of three or four
                bw = rng.uniform(0.2, 0.27); zz = z0
                for j in range(int(rng.integers(3, 5))):
                    t_ = rng.uniform(0.028, 0.05); dd = rng.uniform(0.15, 0.2); o = L.box('book', (x + rng.uniform(0, 0.02), -D / 2 + 0.02 + rng.uniform(0, 0.02), zz), (x + bw - rng.uniform(0, 0.03), -D / 2 + 0.02 + dd, zz + t_), c, hi, bevel=0.003, seed=nb)
                    zz += t_; nb += 1; parts.append(o)
                    if hi:
                        o.data.materials.append(bm); tag(o, rng2)
                x += bw + 0.008; continue
            t_ = rng.uniform(0.024, 0.062); hgt = min(clear - 0.012, rng.uniform(0.2, 0.33)); dd = rng.uniform(0.15, 0.23); setb = rng.uniform(0.012, 0.045)
            if x + t_ > W / 2 - th - 0.004:
                break
            lean = rng.random() < 0.08; o = L.box('book', (x, -D / 2 + setb, z0), (x + t_, -D / 2 + setb + dd, z0 + hgt), c, hi, bevel=0.0035, seed=nb,
                                                  rot=('Y', math.radians(rng.uniform(5, 11)), (x + t_, 0, z0)) if lean else None)
            parts.append(o); nb += 1; x += t_ + (0.03 if lean else rng.uniform(0.0005, 0.003))
            if hi:
                o.data.materials.append(bm); tag(o, rng2)
    return parts


# ---------------------------------------------------------------------------------------------- hanging sign
def sign(hi, c):
    """wall bracket with a brace, two iron straps and a hanging board painted with the healer's red cross"""
    m = woods(hi, light=(0.17, 0.095, 0.04)); parts = []; ir = T.iron_mat('iron', rust=0.6, seed=9.0) if hi else None
    board(parts, 'post', (-0.05, 0.0, 0.0), (0.05, 0.09, 1.0), c, hi, m, seed=1, bevel=0.006); board(parts, 'beam', (-0.045, -1.05, 0.86), (0.045, 0.0, 0.95), c, hi, m, seed=2, bevel=0.006)
    board(parts, 'brace', (-0.03, -0.03, 0.48), (0.03, 0.03, 1.04), c, hi, m, seed=3, bevel=0.005, rot=('X', math.radians(47.0), (0, 0.045, 0.48)))
    # the board, with its own painted material
    bx = L.box('board', (-0.016, -0.98, 0.2), (0.016, -0.26, 0.68), c, hi, bevel=0.005, warp=0.004, seed=4); parts.append(bx)
    for k, y in enumerate((-0.88, -0.36)):
        st = L.box('strap%d' % k, (-0.004, y - 0.012, 0.66), (0.004, y + 0.012, 0.875), c, hi, bevel=0.002, seed=20 + k); parts.append(st)
        ey = L.box('eye%d' % k, (-0.02, y - 0.016, 0.845), (0.02, y + 0.016, 0.865), c, hi, bevel=0.004, seed=30 + k); parts.append(ey)
        nl = L.box('nail%d' % k, (-0.022, y - 0.009, 0.612), (0.022, y + 0.009, 0.63), c, hi, bevel=0.004, seed=40 + k); parts.append(nl)
        if hi:
            for o in (st, ey, nl):
                o.data.materials.append(ir)
    for o in parts:                                # centre the sign on the origin (the pivot), so object-space paint coordinates survive
        Pq = L.co(o); Pq[:, 1] += 0.48; L.set_co(o, Pq)
    if hi:
        t = NT('sign'); sp = t.sep(t.obj); sc = (6.0, 60.0, 60.0); gr = t.noise(1.0, 6, 0.65, vec=t.mapping(scale=(60, 1.8, 60)), distortion=0.8); n = t.noise(22, 5, 0.65); n2 = t.noise(300, 3, 0.6)
        wood = t.ramp(gr, [(0.3, (0.075, 0.04, 0.017)), (0.5, (0.17, 0.095, 0.04)), (0.72, (0.25, 0.15, 0.07))]); plank = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', t.math('MULTIPLY', t.math('SUBTRACT', sp[2], 0.2), 6.25)), 0.5)), [(0.47, 0.0), (0.5, 1.0)])
        wood = t.mix(t.math('MULTIPLY', plank, 0.85), wood, (0.012, 0.008, 0.005))
        cy = t.math('ABSOLUTE', t.math('SUBTRACT', sp[1], -0.14)); cz = t.math('ABSOLUTE', t.math('SUBTRACT', sp[2], 0.44)); wob = t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.02)
        cross = t.math('MAXIMUM', t.math('MULTIPLY', t.maprange(t.math('ADD', cy, wob), 0.05, 0.056, 1.0, 0.0), t.maprange(cz, 0.155, 0.162, 1.0, 0.0)), t.math('MULTIPLY', t.maprange(t.math('ADD', cz, wob), 0.05, 0.056, 1.0, 0.0), t.maprange(cy, 0.155, 0.162, 1.0, 0.0)))
        flake = t.ramp(t.math('ADD', t.math('MULTIPLY', gr, 0.5), t.math('MULTIPLY', t.noise(60, 4, 0.7), 0.5)), [(0.38, 0.0), (0.5, 1.0)]); paint = t.math('MULTIPLY', cross, flake)
        base = t.mix(paint, wood, t.mix(n2, (0.30, 0.012, 0.01), (0.52, 0.035, 0.025))); t.set(base=base, rough=t.mixf(paint, t.mixf(gr, 0.55, 0.75), 0.45), normal=t.bump(t.math('ADD', t.math('MULTIPLY', gr, 0.6), t.math('ADD', t.math('MULTIPLY', plank, -2.0), t.math('MULTIPLY', paint, 0.5))), 0.35, 0.001))
        bx.data.materials.append(t.mat)
    return parts


# ---------------------------------------------------------------------------------------------- cabin window
def window(hi, c):
    """small cabin window, 0.72 x 0.84 m: squared timber frame, sill, one leaded light of diamond quarries in dark old glass"""
    m = woods(hi, light=(0.21, 0.125, 0.06), dark=(0.075, 0.04, 0.018)); parts = []; W, H, th, D = 0.72, 0.84, 0.07, 0.12
    board(parts, 'jamb_l', (-W / 2, -D / 2, 0), (-W / 2 + th, D / 2, H), c, hi, m, seed=1, bevel=0.006); board(parts, 'jamb_r', (W / 2 - th, -D / 2, 0), (W / 2, D / 2, H), c, hi, m, seed=2, bevel=0.006)
    board(parts, 'head', (-W / 2 - 0.04, -D / 2 - 0.006, H - th), (W / 2 + 0.04, D / 2, H), c, hi, m, seed=3, bevel=0.006); board(parts, 'sill', (-W / 2 - 0.06, -D / 2 - 0.045, 0), (W / 2 + 0.06, D / 2, th * 0.8), c, hi, m, seed=4, bevel=0.008)
    board(parts, 'mullion', (-0.016, -0.02, th * 0.8), (0.016, 0.02, H - th), c, hi, m, seed=5, bevel=0.004)
    g = L.box('glass', (-W / 2 + th - 0.004, -0.004, th * 0.8 - 0.004), (W / 2 - th + 0.004, 0.004, H - th + 0.004), c, hi, bevel=0.001, warp=0.0012, seed=6); parts.append(g)
    if hi:
        t = NT('leaded'); sp = t.sep(t.obj); a = t.math('MULTIPLY', t.math('ADD', sp[0], t.math('MULTIPLY', sp[2], 0.72)), 11.5); b = t.math('MULTIPLY', t.math('SUBTRACT', sp[0], t.math('MULTIPLY', sp[2], 0.72)), 11.5)
        la = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', a), 0.5)), [(0.44, 0.0), (0.47, 1.0)]); lb = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', b), 0.5)), [(0.44, 0.0), (0.47, 1.0)]); lead = t.math('MAXIMUM', la, lb)
        cid = t.voronoi(1.0, vec=t.comb(t.math('FLOOR', a), t.math('FLOOR', b), 0.0), out='Color'); cv = t.sep(cid); n = t.noise(30, 4, 0.6); n2 = t.noise(400, 3, 0.6)
        glass = t.mix(cv[0], (0.006, 0.012, 0.028), (0.02, 0.045, 0.075)); glass = t.mix(t.math('MULTIPLY', t.ramp(n, [(0.5, 0.0), (0.8, 1.0)]), 0.5), glass, (0.07, 0.075, 0.07))      # dust and bloom
        base = t.mix(lead, glass, t.mix(n2, (0.045, 0.047, 0.05), (0.12, 0.125, 0.13)))
        tilt = t.bump(t.math('ADD', t.math('MULTIPLY', cv[1], 1.0), t.math('MULTIPLY', n, 0.5)), 0.35, 0.002, normal=t.bump(lead, 0.9, 0.003))
        t.set(base=base, rough=t.mixf(lead, t.mixf(n, 0.06, 0.3), 0.55), metal=t.mixf(lead, 0.0, 0.85), normal=tilt, spec=0.7); g.data.materials.append(t.mat)
    return parts


# ---------------------------------------------------------------------------------------------- stairs
def stairs(hi, c):
    """straight open flight for the 3.5 m storey: eighteen risers of 194 mm, 250 mm goings, two cut strings, 1.0 m wide"""
    m = woods(hi, light=(0.20, 0.115, 0.05)); parts = []; n = 18; rise = 3.5 / n; go = 0.25; Wd = 1.0; run = go * (n - 1)
    ang = math.atan2(3.5 - rise, run)
    for i, x in enumerate((-Wd / 2, Wd / 2 - 0.045)):                 # strings: long boards laid along the pitch (built flat, then pitched about the foot)
        ln = math.hypot(run + 0.2, 3.5 - rise) + 0.18
        board(parts, 'string%d' % i, (x, -0.05, -0.02), (x + 0.045, ln - 0.05, 0.24), c, hi, m, seed=i, bevel=0.005, rot=('X', ang, (0, 0, 0)))
    for k in range(n - 1):
        y = k * go; z = (k + 1) * rise
        board(parts, 'tread%d' % k, (-Wd / 2 - 0.012, y - 0.02, z - 0.04), (Wd / 2 + 0.012, y + go + 0.012, z), c, hi, m, seed=10 + k, bevel=0.006, warp=0.002)
    return parts


W_J = ' Boards are bevelled blocks butted together: no joints, pegs, nails or tool marks are modelled, and the grain is procedural streaking, not a scan. Every board is 12 triangles in the game mesh, so edge rounding is in the normal map only.'
SPECS = {
    'Bookcase': dict(fn=bookcase, fam='bookcase', seq='64 inside/details/inacc- frame 4', cls='prop', px=2048, tris=0, lo='param', ground='weathered_brown_planks', third=[], extrude=0.004, maxdist=0.012, shot=dict(az=28, el=12, fill=1.0, close=(0.3, 0.2, 0.62, 0.22)),
                     weak='About a hundred books as bevelled blocks sharing one material (colour picked per book): no titles, raised bands, headbands or individual wear, and all stand square.' + W_J + ' Game mesh spends 12 triangles on every book, including hidden faces; UVs are several hundred small islands.',
                     dresses='oak bookcase, 1.9 m wide, 1.8 m tall, four shelves packed with about a hundred leather-bound books, a few leaning or stacked flat'),
    'Sign_Healer': dict(fn=sign, fam='shop_sign', seq='458 inside/details/sign- frames 1-5', cls='prop', px=1024, tris=0, lo='param', ground='weathered_brown_planks', third=['rusty_metal_02'], extrude=0.003, maxdist=0.01,
                        shot=dict(az=62, el=10, fill=1.1, close=(0.5, 0.42, 0.45, 0.3)),
                        weak='The bracket stands on its own post so the sign can be placed free or against a wall; the original hangs from a wall bracket only. Straps are flat bars, not chain. The cross is one painted shape with procedural flaking; the back of the board carries the same cross.' + W_J,
                        dresses="healer's hanging sign: timber post and bracket with a brace, a 72 x 48 cm board on two iron straps, painted with a worn red cross"),
    'Cabin_Window': dict(fn=window, fam='log_cabin_window', seq='59 struct/cabin/cabin- frame 3', cls='prop', px=1024, tris=0, lo='param', ground='weathered_brown_planks', third=[], extrude=0.003, maxdist=0.01,
                         shot=dict(az=18, el=8, fill=1.1, close=(0.5, 0.0, 0.5, 0.3)),
                         weak='The glass is an opaque dark panel with the lead lattice painted and bumped on it: no transmission, so nothing shows through and it cannot glow at night without an emissive map. Quarry tilt is a normal-map effect.' + W_J + ' It is a loose window for a log wall; the wall belongs to the log cabin family.',
                         dresses='small cabin window, 72 x 84 cm: squared timber frame, sill and mullion, leaded diamond quarries of dark blue-grey glass'),
    'Stairs_Wood': dict(fn=stairs, fam='stairs_wood', seq='428 inside/stairs/stair- frames 1, 2', cls='prop_large', px=2048, tris=0, lo='param', ground='weathered_brown_planks', third=[], extrude=0.004, maxdist=0.012,
                        shot=dict(az=40, el=14, fill=1.1, close=(0.5, 0.25, 0.3, 0.2)),
                        weak='An open flight without handrail, newels or risers, sized to the 3.5 m storey of the kit; the original frames show a short cellar-style flight and a floor opening with its trimmer frame, which is not built. No UCX collision is exported: a stair needs stepped hulls or a ramp, which is a level decision.' + W_J,
                        dresses='straight open oak stair for the 3.5 m storey: eighteen risers, 1.0 m wide, two strings and seventeen treads'),
}
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
