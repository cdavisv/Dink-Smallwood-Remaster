# Round-2 generators, furniture: long and round oak tables, plank bench, three-legged stool, joined chair.
# exec'd by props_bake.py (uses MB, NT, m_wood, resamp, ASSETS).


def _pegs(b, pts):
    if b.hi:
        for (p, n) in pts:
            b.rivet(p, n, r=0.009, h=0.003, mat='wood', n=8)


def table_long(b):
    """SM_Table_Oak_Long_PR 2.65 x 1.5 x 0.905 m: six-board top with uneven ends, square tapered legs, pegged rails, foot rails, stretcher"""
    r = b.rng; zt = 0.905; th = 0.046; lx, ly = 1.15, 0.58
    ys = np.linspace(-0.75, 0.75, 7); ys[1:-1] += r.uniform(-0.025, 0.025, 5)
    for i in range(6):
        dz = r.uniform(-0.002, 0.002)
        b.box([-1.325 + r.uniform(-0.01, 0.02), ys[i] + 0.0012, zt - th + dz], [1.325 + r.uniform(-0.02, 0.01), ys[i + 1] - 0.0012, zt + dz], 'wood', grain=0, jit=0.003, seg=b.d(2, 10))
    pg = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box([sx * lx - 0.042, sy * ly - 0.042, 0.0], [sx * lx + 0.042, sy * ly + 0.042, zt - th], 'wood', grain=2, jit=0.002, taper=1.32, seg=b.d(1, 4))
            for zz in (0.78, 0.83):
                pg += [([sx * (lx + 0.056), sy * ly, zz], [sx, 0, 0]), ([sx * lx, sy * (ly + 0.056), zz], [0, sy, 0])]
            pg.append(([sx * (lx + 0.05), sy * ly, 0.155], [sx, 0, 0]))
    for sy in (-1, 1):
        b.box([-lx + 0.04, sy * ly - 0.016, 0.745], [lx - 0.04, sy * ly + 0.016, zt - th], 'wood', grain=0, jit=0.002, seg=b.d(1, 6))
    for sx in (-1, 1):
        b.box([sx * lx - 0.016, -ly + 0.04, 0.745], [sx * lx + 0.016, ly - 0.04, zt - th], 'wood', grain=1, jit=0.002)
        b.box([sx * lx - 0.022, -ly + 0.03, 0.12], [sx * lx + 0.022, ly - 0.03, 0.19], 'wood', grain=1, jit=0.002)
    b.box([-lx + 0.02, -0.03, 0.128], [lx - 0.02, 0.03, 0.178], 'wood', grain=0, jit=0.002, seg=b.d(1, 6))
    _pegs(b, pg)
    return {}


def table_round(b):
    """SM_Table_Oak_Round_PR 1.6 m across, 0.8 m: seven boards cut to the round on two battens, four tapered legs, crossed stretchers"""
    r = b.rng; zt = 0.803; th = 0.042; R = 0.795
    ys = np.linspace(-R, R, 8); ys[1:-1] += r.uniform(-0.02, 0.02, 6)
    for i in range(7):
        ym = min(abs(ys[i]), abs(ys[i + 1])); xl = math.sqrt(max(R * R - ym * ym, 0)) + 0.01; dz = r.uniform(-0.002, 0.002)
        n0 = b.box([-xl, ys[i] + 0.0012, zt - th + dz], [xl, ys[i + 1] - 0.0012, zt + dz], 'wood', grain=0, jit=0.002, seg=b.d(10, 28))

        def clip(P, k=r.uniform(0.992, 1.0)):
            q = np.hypot(P[:, 0], P[:, 1]); f = np.minimum(1.0, R * k / np.maximum(q, 1e-6)); return np.c_[P[:, 0] * f, P[:, 1] * f, P[:, 2]]
        b.deform_since(n0, clip)
    for x in (-0.36, 0.36):
        b.box([x - 0.05, -0.62, zt - th - 0.04], [x + 0.05, 0.62, zt - th], 'wood', grain=1, jit=0.002)
    q = 0.4; pg = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box([sx * q - 0.04, sy * q - 0.04, 0.0], [sx * q + 0.04, sy * q + 0.04, zt - th - 0.04], 'wood', grain=2, jit=0.002, taper=1.3, seg=b.d(1, 4))
            pg.append(([sx * q + sx * 0.035, sy * q + sy * 0.035, 0.225], [sx, sy, 0]))
    for k, a in enumerate((45, -45)):
        M = Matrix.Rotation(math.radians(a), 4, 'Z')
        b.box([-q * 1.414 + 0.02, -0.024, 0.19 + 0.02 * k], [q * 1.414 - 0.02, 0.024, 0.245 + 0.02 * k], 'wood', grain=0, jit=0.002, M=M, seg=b.d(1, 4))
    _pegs(b, pg)
    return {}


def bench(b):
    """SM_Bench_Oak_PR 2.3 x 0.3 x 0.45 m: one thick board on two slab ends with boot notches, through tenons, a stretcher"""
    r = b.rng; zt = 0.457; th = 0.05
    b.box([-1.15, -0.15, zt - th], [1.15, 0.15, zt], 'wood', grain=0, jit=0.003, seg=b.d(3, 12))
    for sx in (-1, 1):
        x = sx * 0.93
        b.box([x - 0.023, -0.14, 0.13], [x + 0.023, 0.14, zt - th], 'wood', grain=2, jit=0.002)
        for sy in (-1, 1):
            ya, yb = sorted((sy * 0.14, sy * 0.045))
            n0 = b.box([x - 0.023, ya, 0.0], [x + 0.023, yb, 0.13], 'wood', grain=2, jit=0.0015)
            b.deform_since(n0, lambda P, sy=sy: np.c_[P[:, 0], P[:, 1] + sy * 0.03 * (1 - P[:, 2] / 0.13) * (np.abs(P[:, 1]) < 0.09), P[:, 2]])   # the boot notch is a splayed V
            b.box([x - 0.016, sy * 0.07 - 0.022, zt - 0.01], [x + 0.016, sy * 0.07 + 0.022, zt + 0.0035], 'wood', grain=2, jit=0.001)        # through tenon, proud of the seat
    b.box([-0.93, -0.018, 0.2], [0.93, 0.018, 0.275], 'wood', grain=0, jit=0.002, seg=b.d(1, 6))
    _pegs(b, [([sx * 0.955, 0, 0.24], [sx, 0, 0]) for sx in (-1, 1)])
    return {}


def stool(b):
    """SM_Stool_Oak_PR: three-legged stool, 0.36 m dished seat, 0.45 m, legs wedged through the seat"""
    r = b.rng; zt = 0.45
    sd = lambda P: np.c_[P[:, 0] * (1 + 0.02 * vnoise(P, 4, 6.0)) + 0.008, P[:, 1] * (1 + 0.02 * vnoise(P, 5, 6.0)) - 0.012, P[:, 2]]
    for pr in ([(0, zt - 0.042), (0.15, zt - 0.042), (0.176, zt - 0.03), (0.18, zt - 0.012)], [(0.18, zt - 0.012), (0.172, zt), (0.12, zt - 0.006), (0, zt - 0.009)]):
        b.lathe(pr, n=b.d(18, 56), mat='wood', sub=b.d(1, 3), planar=True, cap=False, deform=sd)       # the seat is a slice of plank: straight grain, two charts
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5; d = np.array([math.cos(a), math.sin(a), 0.0]); o = np.array([0.008, -0.012, 0])
        pts = [o + d * (0.165 - 0.065 * t) + [0, 0, 0.0 + (zt - 0.006) * t] for t in np.linspace(0, 1, b.d(5, 14))]
        rad = np.interp(np.linspace(0, 1, len(pts)), [0, 0.15, 0.5, 0.8, 1.0], [0.015, 0.02, 0.023, 0.02, 0.016])
        b.tube(pts, rad, sides=b.d(8, 16), mat='wood', shape=[1, 0.94, 1.03, 0.92, 1, 0.95, 1.02, 0.93] * b.d(1, 2))
    return {}


def chair(b):
    """SM_Chair_Oak_PR 0.52 x 0.56 x 1.0 m: raked back legs with a kicked foot, three-board seat, seat rails and stretchers, crest rail
    and slat, pegged. Front is -Y."""
    r = b.rng; zs = 0.45; lx = 0.215; pg = []
    for sx in (-1, 1):
        x = sx * lx
        ctrl = [[x, 0.262, 0.02], [x, 0.215, 0.2], [x, 0.205, 0.44], [x, 0.24, 0.72], [x, 0.288, 0.985]]
        b.tube(resamp(ctrl, b.d(2, 6)), 1.0, mat='wood', rect=(0.04, 0.038), up=[1, 0, 0], ups=[(1, 0, 0)] * (4 * b.d(2, 6) + 1))
        b.box([x - 0.02, -0.225, 0.0], [x + 0.02, -0.185, zs - 0.022], 'wood', grain=2, jit=0.0015, taper=1.15)
        b.box([x - 0.012, -0.19, 0.37], [x + 0.012, 0.19, zs - 0.022], 'wood', grain=1, jit=0.0015)             # side seat rail
        b.box([x - 0.011, -0.19, 0.15 + 0.03 * (sx > 0)], [x + 0.011, 0.2, 0.185 + 0.03 * (sx > 0)], 'wood', grain=1, jit=0.0015)
        pg += [([x + sx * 0.02, -0.205, 0.41], [sx, 0, 0]), ([x + sx * 0.02, 0.205, 0.41], [sx, 0, 0]), ([x + sx * 0.02, 0.283, 0.94], [sx, 0, 0])]
    b.box([-lx + 0.018, -0.217, 0.37], [lx - 0.018, -0.193, zs - 0.022], 'wood', grain=0, jit=0.0015)             # front and back seat rails
    b.box([-lx + 0.018, 0.193, 0.37], [lx - 0.018, 0.217, zs - 0.022], 'wood', grain=0, jit=0.0015)
    b.box([-lx + 0.018, -0.216, 0.2], [lx - 0.018, -0.194, 0.235], 'wood', grain=0, jit=0.0015)                   # front stretcher
    xs = np.linspace(-0.258, 0.258, 4); xs[1:-1] += r.uniform(-0.012, 0.012, 2)
    for i in range(3):
        dz = r.uniform(-0.0015, 0.0015)
        b.box([xs[i] + 0.001, -0.242 + r.uniform(0, 0.006), zs - 0.022 + dz], [xs[i + 1] - 0.001, 0.228, zs + dz], 'wood', grain=1, jit=0.002, seg=b.d(1, 5))
    M = Matrix.Translation((0, 0.277, 0.93)) @ Matrix.Rotation(math.radians(-10), 4, 'X')
    n0 = b.box([-lx + 0.012, -0.011, -0.055], [lx - 0.012, 0.011, 0.062], 'wood', grain=0, jit=0.002, seg=b.d(4, 10), M=M)                 # crest rail, shaped top
    b.deform_since(n0, lambda P: np.c_[P[:, 0], P[:, 1], P[:, 2] - 0.02 * (P[:, 0] / lx) ** 2 * (P[:, 2] > 0.95)])
    M = Matrix.Translation((0, 0.228, 0.655)) @ Matrix.Rotation(math.radians(-7), 4, 'X')
    b.box([-lx + 0.015, -0.009, -0.04], [lx - 0.015, 0.009, 0.04], 'wood', grain=0, jit=0.002, M=M)
    _pegs(b, pg)
    return {}


def room_mats(kw=None):
    def rings(s):                                        # mug rings and spills, only on faces that look up
        up = s.sep(s.geo.outputs['Normal'])[2]; d = s.voro(3.3, 'F1')
        ring = s.mul(s.mul(s.step(d, 0.105, 0.115), s.inv(s.step(d, 0.122, 0.135))), s.step(s.noise(1.7, 2.0), 0.52, 0.56))
        blot = s.step(s.noise(2.6, 4.0, 0.6), 0.63, 0.72)
        return (s.mul(s.sat(s.add(s.mul(ring, 0.75), s.mul(blot, 0.55))), s.step(up, 0.8, 0.95)), (0.4, 0.28, 0.19), 0.4)
    k = dict(dark=(0.04, 0.022, 0.011), mid=(0.16, 0.09, 0.045), light=(0.36, 0.23, 0.13), tile=0.7, grease=0.6, wear=0.4, scratch=0.6, stain=rings, bevel=0.004); k.update(kw or {})
    return {'wood': m_wood('H_wood', **k)}


_RM = dict(cls='prop', px=2048, mats=room_mats, extrude=0.006, maxdist=0.02, third_party=['rough_wood'], sharp=35.0, int_watts=40.0)
ASSETS['SM_Table_Oak_Long_PR'] = dict(_RM, fn=table_long, slots=[('MI_Table_Oak_Long', 'opaque', None)], seed=21, int_light=(1.2, -1.0, 1.6),
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.5), 55), 'close': ((2.1, -1.9, 1.75), (0.75, -0.3, 0.7), 30), 'int': ((1.9, -2.6, 1.9), (0, 0, 0.5), 30)})
ASSETS['SM_Table_Oak_Round_PR'] = dict(_RM, fn=table_round, slots=[('MI_Table_Oak_Round', 'opaque', None)], seed=22, int_light=(1.0, -0.9, 1.5),
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.45), 75), 'close': ((0.9, -1.4, 1.5), (0.15, -0.2, 0.7), 30), 'int': ((1.5, -2.1, 1.6), (0, 0, 0.45), 30)})
ASSETS['SM_Bench_Oak_PR'] = dict(_RM, fn=bench, slots=[('MI_Bench_Oak', 'opaque', None)], seed=23, int_light=(1.0, -0.8, 1.0),
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.25), 60), 'close': ((1.5, -1.2, 1.0), (0.7, 0, 0.3), 30), 'int': ((1.9, -2.0, 1.2), (0, 0, 0.25), 30)})
ASSETS['SM_Stool_Oak_PR'] = dict(_RM, cls='prop_small', px=1024, fn=stool, slots=[('MI_Stool_Oak', 'opaque', None)], seed=24, int_light=(0.6, -0.5, 0.9), int_watts=15.0,
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.25), 180), 'close': ((0.6, -0.9, 0.9), (0, 0, 0.25), 35), 'int': ((0.6, -0.9, 0.9), (0, 0, 0.25), 35)})
ASSETS['SM_Chair_Oak_PR'] = dict(_RM, fn=chair, slots=[('MI_Chair_Oak', 'opaque', None)], seed=25, int_light=(0.8, -0.8, 1.3), int_watts=25.0,
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.5), 120), 'close': ((0.8, -1.3, 1.35), (0, 0, 0.5), 35), 'int': ((0.8, -1.3, 1.35), (0, 0, 0.5), 35)})
