# Round-2 generators, store props: iron-bound chest (closed + opened variant on one bake), packing crates.
# exec'd by props_bake.py (uses MB, NT, m_wood, m_iron, m_plain, resamp, ASSETS).


def chest(b):
    """SM_Chest_Small_PR: plank carcase on two battens, coopered lid of seven staves between D-shaped ends, three iron straps over lid
    and body, corner irons, lock plate and hasp, drop handles. Lid parts are group 1 (hinge on the back top edge)."""
    r = b.rng; hi = b.hi; L = 0.86; W = 0.5; zb = 0.03; zt = 0.36; t = 0.022; hx = L / 2; hy = W / 2; rise = 0.165
    for x in (-0.3, 0.3):
        b.box([x - 0.035, -hy + 0.01, 0.0], [x + 0.035, hy - 0.01, zb], 'wood', grain=1, jit=0.002)
    ys = np.linspace(-hy + t, hy - t, 4)
    for i in range(3):
        b.box([-hx + t, ys[i] + 0.001, zb], [hx - t, ys[i + 1] - 0.001, zb + 0.018], 'wood', grain=0, jit=0.0015)
    for sy in (-1, 1):
        zs = [zb, zb + 0.17 + r.uniform(-0.012, 0.012), zt]; y0, y1 = (-hy, -hy + t) if sy < 0 else (hy - t, hy)
        for i in range(2):
            b.box([-hx, y0, zs[i] + 0.0008], [hx, y1, zs[i + 1] - 0.0008], 'wood', grain=0, jit=0.002, seg=b.d(1, 6))
    for sx in (-1, 1):
        zs = [zb, zb + 0.16 + r.uniform(-0.012, 0.012), zt]; x0, x1 = (-hx, -hx + t) if sx < 0 else (hx - t, hx)
        for i in range(2):
            b.box([x0, -hy + t + 0.0005, zs[i] + 0.0008], [x1, hy - t - 0.0005, zs[i + 1] - 0.0008], 'wood', grain=1, jit=0.002)
    xs = (-0.3, 0.0, 0.3)
    for x in xs:                                         # straps on the body, front and back, and the hinge knuckles
        for sy in (-1, 1):
            y0, y1 = sorted((sy * hy, sy * (hy + 0.0042)))
            b.box([x - 0.022, y0, zb + 0.004], [x + 0.022, y1, zt - 0.003], 'iron', grain=2, jit=0.001)
            if hi:
                for zz in (zb + 0.04, (zb + zt) / 2 + 0.01, zt - 0.045):
                    for dx in (-0.01, 0.01):
                        b.rivet([x + dx, sy * (hy + 0.0042), zz + dx * 0.4], [0, sy, 0], r=0.0055, mat='iron', n=8)
        b.tube([[x - 0.026, hy + 0.007, zt], [x + 0.026, hy + 0.007, zt]], 0.008, sides=b.d(6, 12), mat='iron')
    for sx in (-1, 1):                                   # corner irons, top and bottom
        for sy in (-1, 1):
            for (za, zc) in ((zb + 0.002, zb + 0.085), (zt - 0.085, zt - 0.003)):
                xa, xb = sorted((sx * (hx + 0.0038), sx * (hx - 0.075))); ya, yb = sorted((sy * hy, sy * (hy + 0.0038)))
                b.box([xa, ya, za], [xb, yb, zc], 'iron', grain=0, jit=0.001)
                xa, xb = sorted((sx * hx, sx * (hx + 0.0038))); ya, yb = sorted((sy * (hy + 0.0038), sy * (hy - 0.075)))
                b.box([xa, ya, za], [xb, yb, zc], 'iron', grain=1, jit=0.001)
                if hi:
                    for u in (0.02, 0.055):
                        b.rivet([sx * (hx - u), sy * (hy + 0.0038), (za + zc) / 2], [0, sy, 0], r=0.005, mat='iron', n=8)
                        b.rivet([sx * (hx + 0.0038), sy * (hy - u), (za + zc) / 2], [sx, 0, 0], r=0.005, mat='iron', n=8)
    b.box([-0.052, -hy - 0.009, zt - 0.118], [0.052, -hy - 0.004, zt - 0.012], 'iron', grain=2, jit=0.0015)       # lock plate
    if hi:
        for (u, v) in ((-0.042, -0.108), (0.042, -0.108), (-0.042, -0.022), (0.042, -0.022)):
            b.rivet([u, -hy - 0.009, zt + v], [0, -1, 0], r=0.0045, mat='iron', n=8)
        b.tube([[0, -hy - 0.0098, zt - 0.082], [0, -hy - 0.0085, zt - 0.082]], 0.0065, sides=10, mat='void')        # keyhole
        b.box([-0.0028, -hy - 0.0098, zt - 0.102], [0.0028, -hy - 0.0085, zt - 0.083], 'void', grain=2)
    for sx in (-1, 1):                                   # drop handles on two eyes
        x0 = sx * hx
        for yy in (-0.075, 0.075):
            b.rivet([x0, yy, 0.25], [sx, 0, 0], r=0.014, h=0.012, mat='iron', n=b.d(6, 10))
        ctrl = [[x0 + sx * 0.012, -0.075, 0.25], [x0 + sx * 0.028, -0.078, 0.205], [x0 + sx * 0.033, -0.05, 0.168], [x0 + sx * 0.033, 0.05, 0.168], [x0 + sx * 0.028, 0.078, 0.205], [x0 + sx * 0.012, 0.075, 0.25]]
        b.tube(resamp(ctrl, b.d(2, 6)), 0.0065, sides=b.d(6, 10), mat='iron')
    # ---- lid
    b.grp = 1
    R = (hy * hy + rise * rise) / (2 * rise); cz = zt + rise - R; pm = math.asin(hy / R)
    ph = np.linspace(-pm, pm, 8); ph[1:-1] += r.uniform(-0.03, 0.03, 6)
    for k in range(7):
        pa, pb = ph[k], ph[k + 1]; w = 2 * R * math.sin((pb - pa) / 2)
        M = Matrix.Translation((0, 0, cz)) @ Matrix.Rotation(-(pa + pb) / 2, 4, 'X') @ Matrix.Translation((0, 0, R * math.cos((pb - pa) / 2) + r.uniform(-0.0012, 0.0012)))
        b.box([-hx - 0.004, -w / 2 + 0.0008, -0.02], [hx + 0.004, w / 2 - 0.0008, 0.0], 'wood', grain=0, jit=0.0015, seg=b.d(1, 6), M=M)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (hx - 0.002), sx * (hx - 0.002 - t)))
        n0 = b.box([x0, -hy + 0.018, zt + 0.001], [x1, hy - 0.018, zt + rise - 0.02], 'wood', grain=1, seg=b.d(8, 20))

        def dee(P):
            arc = cz + np.sqrt(np.maximum((R - 0.019) ** 2 - P[:, 1] ** 2, 0.0)); f = (P[:, 2] - zt - 0.001) / (rise - 0.021)
            return np.c_[P[:, 0], P[:, 1], zt + 0.001 + f * np.maximum(arc - zt - 0.001, 0.004)]
        b.deform_since(n0, dee)
    for x in xs:
        n_ = b.d(12, 32); pp = np.linspace(-pm - 0.012, pm + 0.012, n_)
        pts = [(x, (R + 0.0024) * math.sin(p_), cz + (R + 0.0024) * math.cos(p_)) for p_ in pp]
        b.tube(pts, 1.0, mat='iron', rect=(0.044, 0.0045), ups=[(1, 0, 0)] * n_)
        if hi:
            for p_ in np.linspace(-pm + 0.12, pm - 0.12, 6):
                d_ = np.array([0, math.sin(p_), math.cos(p_)])
                for dx in (-0.011, 0.011):
                    b.rivet(np.array([x + dx, 0, cz]) + d_ * (R + 0.0046), d_, r=0.0055, mat='iron', n=8)
    b.box([-0.019, -hy - 0.0135, zt - 0.062], [0.019, -hy - 0.009, zt + 0.03], 'iron', grain=2, jit=0.001)        # hasp
    if hi:
        b.tube(resamp([[-0.008, -hy - 0.0135, zt - 0.045], [-0.006, -hy - 0.022, zt - 0.045], [0.006, -hy - 0.022, zt - 0.045], [0.008, -hy - 0.0135, zt - 0.045]], 3), 0.0028, sides=6, mat='iron')
        b.rivet([0, -hy - 0.0135, zt + 0.015], [0, -1, 0], r=0.005, mat='iron', n=8)
    b.grp = 0
    return {'hinge': [0.0, hy + 0.007, zt]}


def _chest_open():
    M = Matrix.Translation((0, 0.257, 0.36)) @ Matrix.Rotation(math.radians(-102), 4, 'X') @ Matrix.Translation((0, -0.257, -0.36))
    return {1: [list(r_) for r_ in M]}


def chest_mats():
    return {'wood': m_wood('H_wood', dark=(0.04, 0.012, 0.008), mid=(0.17, 0.045, 0.028), light=(0.36, 0.14, 0.085), tile=0.6, grease=0.35, wear=0.55, scratch=0.5),
            'iron': m_iron('H_iron', rust=0.8, bright=0.4, hammer=0.6), 'void': m_plain('H_void', (0.008, 0.008, 0.008), (0.012, 0.011, 0.01))}


def crate(b, X=0.966, Y=0.668, Z=0.576, nl=4):
    """slatted packing crate: corner posts inside, three slats a side with open gaps onto a real interior, bottom boards, lid boards
    under two nailed battens"""
    r = b.rng; hi = b.hi; hx = X / 2; hy = Y / 2; t = 0.016; p = 0.045; zl = Z - 0.036
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, xb = sorted((sx * (hx - t), sx * (hx - t - p))); ya, yb = sorted((sy * (hy - t), sy * (hy - t - p)))
            b.box([xa, ya, 0.0], [xb, yb, zl], 'wood', grain=2, jit=0.0015)
    ys = np.linspace(-hy + t, hy - t, 5)
    for i in range(4):
        b.box([-hx + t, ys[i] + 0.002, 0.012], [hx - t, ys[i + 1] - 0.002, 0.03], 'wood', grain=0, jit=0.002)
    n = 3; gap = 0.028; hs = (zl - 0.004 - (n - 1) * gap) / n; nails = []
    for i in range(n):
        z0 = 0.004 + i * (hs + gap)
        for sy in (-1, 1):
            dz = r.uniform(-0.004, 0.004, 2); ya, yb = sorted((sy * hy, sy * (hy - t)))
            b.box([-hx + r.uniform(0, 0.005), ya, z0 + dz[0]], [hx - r.uniform(0, 0.005), yb, z0 + hs + dz[1]], 'wood', grain=0, jit=0.0025, seg=b.d(1, 6))
            for sx in (-1, 1):
                for f in (0.28, 0.72):
                    nails.append(([sx * (hx - t - p / 2 + r.uniform(-0.008, 0.008)), sy * hy, z0 + hs * f + dz.mean()], [0, sy, 0]))
        for sx in (-1, 1):
            dz = r.uniform(-0.004, 0.004, 2); xa, xb = sorted((sx * hx, sx * (hx - t)))
            b.box([xa, -hy + t + 0.001, z0 + dz[0]], [xb, hy - t - 0.001, z0 + hs + dz[1]], 'wood', grain=1, jit=0.0025, seg=b.d(1, 6))
            for sy in (-1, 1):
                for f in (0.28, 0.72):
                    nails.append(([sx * hx, sy * (hy - t - p / 2 + r.uniform(-0.008, 0.008)), z0 + hs * f + dz.mean()], [sx, 0, 0]))
    ys = np.linspace(-hy - 0.004, hy + 0.004, nl + 1); ys[1:-1] += r.uniform(-0.012, 0.012, nl - 1)
    for i in range(nl):
        b.box([-hx - 0.004 + r.uniform(-0.005, 0.004), ys[i] + 0.0015, zl], [hx + 0.004 + r.uniform(-0.004, 0.005), ys[i + 1] - 0.0015, zl + 0.018], 'wood', grain=0, jit=0.002, seg=b.d(1, 6))
    for x in (-hx * 0.62, hx * 0.62):
        b.box([x - 0.04, -hy + 0.012, zl + 0.018], [x + 0.04, hy - 0.012, Z - 0.002], 'wood', grain=1, jit=0.002)
        for i in range(nl):
            nails.append(([x + r.uniform(-0.02, 0.02), (ys[i] + ys[i + 1]) / 2 + r.uniform(-0.02, 0.02), Z - 0.002], [0, 0, 1]))
    if hi:
        for (pt, nr) in nails:
            b.rivet(pt, nr, r=0.0048, h=0.0022, mat='iron', n=8)
    return {}


def crate_mats():
    def nail_runs(s):                                    # grey weathering and damp at the foot
        z = s.sep(s.P)[2]; return (s.mul(s.inv(s.step(z, 0.0, 0.14)), 0.7), (0.4, 0.33, 0.26), 0.85)
    return {'wood': m_wood('H_wood', dark=(0.045, 0.032, 0.02), mid=(0.2, 0.145, 0.095), light=(0.44, 0.35, 0.25), tile=0.5, grease=0.15, wear=0.5, scratch=0.35, stain=nail_runs),
            'iron': m_iron('H_iron', rust=1.0, bright=0.15, hammer=0.3)}


_ST = dict(cls='prop', px=2048, extrude=0.006, maxdist=0.02, third_party=['rough_wood'], sharp=35.0)
ASSETS['SM_Chest_Small_PR'] = dict(_ST, fn=chest, mats=chest_mats, slots=[('MI_Chest_Small', 'opaque', None)], bake_pose=_chest_open(),
    variants={'SM_Chest_Small_Open_PR': {'class': 'prop', 'families': ['chest_small (opened state)', 'chest_medium / chest_large opened (scale)'], 'supersedes': 'none (new: the opened state of SM_Chest_Small_PR)',
                                         'dresses': 'the iron-bound chest with its lid thrown back 102 degrees on the back hinges: same mesh and the same texture set as SM_Chest_Small_PR (T_Chest_Small_PR_*), empty plank interior',
                                         'fit': {'pivot': 'base centre, identical to SM_Chest_Small_PR: swap the mesh in place to open the chest', 'hinge': 'hinge axis along X through (y 0.257, z 0.36) m; lid angle 102 degrees; put loot or a glow inside the body cavity (floor at z 0.048)'}}},
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.25), 110), 'close': ((0.8, -1.25, 1.1), (0, 0, 0.28), 35), 'int': ((0.8, -1.25, 1.1), (0, 0, 0.28), 35), 'open': ((0.75, -1.35, 1.35), (0, 0.1, 0.42), 32)},
    int_light=(0.9, -0.7, 1.1), int_watts=30.0)
ASSETS['SM_Crate_Large_PR'] = dict(_ST, fn=crate, mats=crate_mats, slots=[('MI_Crate_Large', 'opaque', None)], seed=5,
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.3), 110), 'close': ((0.85, -1.3, 1.15), (0, 0, 0.3), 35), 'int': ((0.85, -1.3, 1.15), (0, 0, 0.3), 35)}, int_light=(0.9, -0.7, 1.1), int_watts=30.0)
ASSETS['SM_Crate_Small_PR'] = dict(_ST, fn=lambda b: crate(b, 0.743, 0.548, 0.466, 3), mats=crate_mats, slots=[('MI_Crate_Small', 'opaque', None)], seed=11,
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.25), 130), 'close': ((0.75, -1.15, 1.0), (0, 0, 0.24), 35), 'int': ((0.75, -1.15, 1.0), (0, 0, 0.24), 35)}, int_light=(0.9, -0.7, 1.1), int_watts=30.0)
