"""Buildings of the unclaimed families: the log cabin (59 struct/cabin/cabin- frame 1).

Every log is its own swept solid, notched over its neighbours at the corners; the roof is two shingled slabs; the chimney
is fieldstone blocks. Door and window openings are left for the door and window families.

    tools/bl.sh build_buildings.py <Log_Cabin|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
import build_props as P
import build_props3 as P3
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_buildings.py'


def log_mat(axis, seed=0.0):
    """peeled, weathered pine log: silver-brown, long drying checks, knots, darker damp underside, pale end grain is left to the cap colour"""
    t = NT('log_%s' % 'xyz'[axis]); sc = [26.0, 26.0, 26.0]; sc[axis] = 0.9; gr = t.noise(1.0, 6, 0.65, vec=t.mapping(scale=tuple(sc), loc=(seed, 0, 0)), distortion=0.8)
    sc2 = [120.0, 120.0, 120.0]; sc2[axis] = 1.6; chk = t.ramp(t.noise(1.0, 3, 0.6, vec=t.mapping(scale=tuple(sc2))), [(0.60, 0.0), (0.66, 1.0)]); knot = t.ramp(t.voronoi(3.2, feature='F1', vec=t.mapping(loc=(seed, 1, 2))), [(0.0, 1.0), (0.06, 0.0)])
    base = t.ramp(gr, [(0.3, (0.075, 0.055, 0.038)), (0.5, (0.17, 0.135, 0.095)), (0.75, (0.30, 0.26, 0.20))]); base = t.mix(t.math('MULTIPLY', chk, 0.8), base, (0.02, 0.015, 0.01)); base = t.mix(t.math('MULTIPLY', knot, 0.7), base, (0.05, 0.03, 0.015))
    nz = t.sep(t.gnormal)[2]; under = t.maprange(nz, -0.9, -0.2, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', under, 0.6), base, (0.03, 0.028, 0.022)); moss = t.math('MULTIPLY', t.ramp(t.noise(5, 5, 0.7, vec=t.mapping(loc=(2, seed, 5))), [(0.58, 0.0), (0.7, 1.0)]), t.maprange(nz, 0.0, 0.7, 0.0, 1.0))
    base = t.mix(t.math('MULTIPLY', moss, 0.6), base, (0.045, 0.075, 0.02)); ao = t.ao(0.12, 10); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.3, 1.0), (0.8, 0.0)]), 0.75), base, (0.015, 0.012, 0.009))
    t.set(base=base, rough=t.mixf(gr, 0.7, 0.9), normal=t.bump(t.math('ADD', t.math('ADD', t.math('MULTIPLY', gr, 0.6), t.math('MULTIPLY', chk, -2.5)), t.math('MULTIPLY', knot, 1.0)), 0.45, 0.004)); return t.mat


def shingle_mat(pitch, ridge_z, course=0.2, width=0.16):
    """split wooden shingles laid in courses down both slopes (ridge along X): silver-grey, each shingle its own tone, curled butts, moss in the laps"""
    t = NT('shingles'); sp = t.sep(t.obj); d = t.math('DIVIDE', t.math('ABSOLUTE', sp[1]), math.cos(pitch)); fr = t.math('DIVIDE', d, course); row = t.math('FLOOR', fr); rf = t.math('FRACT', fr)
    fx = t.math('ADD', t.math('DIVIDE', sp[0], width), t.math('MULTIPLY', row, 0.47)); col = t.math('FLOOR', fx); cf = t.math('FRACT', fx); cv = t.sep(t.voronoi(1.0, vec=t.comb(col, row, 0.0), out='Color'))
    gr = t.noise(1.0, 5, 0.65, vec=t.comb(t.math('MULTIPLY', sp[0], 90.0), t.math('MULTIPLY', d, 4.0), cv[0]), distortion=0.6); base = t.ramp(gr, [(0.3, (0.07, 0.065, 0.058)), (0.5, (0.16, 0.15, 0.135)), (0.75, (0.30, 0.29, 0.26))])
    base = t.hsv(base, v=t.maprange(cv[1], 0, 1, 0.65, 1.25)); gap = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', cf, 0.5)), [(0.455, 0.0), (0.49, 1.0)]); butt = t.ramp(rf, [(0.9, 0.0), (0.98, 1.0)])
    base = t.mix(t.math('MULTIPLY', t.math('MAXIMUM', gap, butt), 0.9), base, (0.012, 0.011, 0.01)); moss = t.math('MULTIPLY', t.ramp(t.noise(1.6, 5, 0.7), [(0.5, 0.0), (0.66, 1.0)]), t.ramp(rf, [(0.3, 0.2), (0.9, 1.0)])); base = t.mix(t.math('MULTIPLY', moss, 0.7), base, t.mix(gr, (0.03, 0.06, 0.015), (0.09, 0.13, 0.03)))
    h = t.math('ADD', t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, rf), 1.2), t.math('MULTIPLY', gr, 0.3)), t.math('MULTIPLY', t.math('MAXIMUM', gap, butt), -2.0)); t.set(base=base, rough=t.mixf(gr, 0.75, 0.92), normal=t.bump(h, 0.6, 0.012)); return t.mat


def log_cabin(hi, c):
    """log cabin, 7.6 x 4.8 m: ten courses of notched logs, log gables, a shingled roof at 38 degrees, a fieldstone chimney on the west gable; door and window openings in the south wall"""
    parts = []; LX, LY, r = 7.0, 4.2, 0.14; sp_ = 2 * r * 0.9; n = 10; ov = 0.3; q = 3 if hi else 1; rng = np.random.default_rng(3); lm = [log_mat(a, seed=float(a)) for a in range(3)] if hi else [None] * 3

    def log(p0, p1, axis, rad=r, seed=0):
        p0 = np.array(p0, float); p1 = np.array(p1, float); rows = []
        for t_ in (0.0, 0.3, 0.7, 1.0):
            p = p0 * (1 - t_) + p1 * t_; rr = rad * (1.0 + 0.06 * math.sin(seed * 1.7 + t_ * 3)); rows.append((p[0], p[1], p[2] + 0.01 * math.sin(seed + t_ * 4), rr, rr * 0.97, 2.1))
        o = L.sweep('log', rows, nu=10 * q if hi else 8, nv=8 * q if hi else 5, c=c, up=(0, 0, 1), cap=0.8)
        if hi:
            L.displace_np(o, lambda Q: 0.004 * fbm(Q, 3 + seed, 4, 3) + 0.0015 * fbm(Q, 9 + seed, 30, 2)); o.data.materials.append(lm[axis])
        parts.append(o)
    door = (-1.9, -0.9, 2.0); win = (1.2, 2.2, 0.95, 1.75)            # door x0, x1, height; window x0, x1, z0, z1 (south wall, y = -LY/2)
    for k in range(n):
        z = r + k * sp_; zs = z + sp_ / 2
        for sy in (-1, 1):                                        # long walls (along X)
            y = sy * LY / 2; cuts = []
            if sy < 0:
                if z < door[2]:
                    cuts.append((door[0], door[1]))
                if win[2] < z < win[3]:
                    cuts.append((win[0], win[1]))
            xs = [-LX / 2 - ov] + [v for cseg in sorted(cuts) for v in cseg] + [LX / 2 + ov]
            for i in range(0, len(xs), 2):
                log((xs[i], y, z), (xs[i + 1], y, z), 0, seed=k * 7 + i + (sy > 0) * 3)
        if k < n - 1 or True:
            for sx in (-1, 1):                                    # end walls (along Y), half a course higher
                log((sx * LX / 2, -LY / 2 - ov, zs), (sx * LX / 2, LY / 2 + ov, zs), 1, seed=100 + k * 5 + (sx > 0))
    top = r + (n - 1) * sp_ + sp_ / 2 + r; pitch = math.radians(38); k = 0
    while True:                                                   # log gables, each course shorter, up to the ridge
        z = top + r * 0.8 + k * sp_; half = LY / 2 + 0.1 - (z - top) / math.tan(pitch)
        if half < 0.35:
            break
        for sx in (-1, 1):
            log((sx * LX / 2, -half, z), (sx * LX / 2, half, z), 1, seed=200 + k * 3 + (sx > 0))
        k += 1
    ridge_z = top + (LY / 2 + 0.1) * math.tan(pitch) + 0.12; sm = shingle_mat(pitch, ridge_z) if hi else None; eave = 0.55; run = LY / 2 + eave; sl = run / math.cos(pitch)
    for sy in (-1, 1):                                            # roof slabs: built flat, pitched about the ridge line
        o = L.box('roof', (-LX / 2 - 0.5, 0.0 if sy > 0 else -sl, -0.09), (LX / 2 + 0.5, sl if sy > 0 else 0.0, 0.0), c, hi, bevel=0.01, warp=0.006, seed=5 + sy)
        L.xform(o, Matrix.Translation((0, 0, ridge_z)) @ Matrix.Rotation(-pitch if sy > 0 else pitch, 4, 'X'))
        if hi:
            o.data.materials.append(sm)
        parts.append(o)
    rc = L.sweep('ridge', [(-LX / 2 - 0.55, 0, ridge_z + 0.02, 0.09, 0.07, 2.2), (0, 0, ridge_z + 0.03, 0.09, 0.07, 2.2), (LX / 2 + 0.55, 0, ridge_z + 0.02, 0.09, 0.07, 2.2)], nu=8 * q if hi else 6, nv=8 * q if hi else 5, c=c, up=(0, 0, 1), cap=0.8)
    if hi:
        rc.data.materials.append(lm[0])
    parts.append(rc)
    for nm, pl in (('purlin_s', -1), ('purlin_n', 1)):            # eaves purlins under the roof edge
        log((-LX / 2 - 0.45, pl * (LY / 2 + 0.02), top + 0.05), (LX / 2 + 0.45, pl * (LY / 2 + 0.02), top + 0.05), 0, rad=0.1, seed=300 + pl)
    st = [P3.stone(110 + i, tint=(0.62 + 0.05 * i, 0.58, 0.50), value=0.8, sat=0.5, moss=0.4, lichen=0.4, scan='rock_boulder_dry', scale=1.6) for i in range(3)] if hi else [None] * 3; cx = -LX / 2 - 0.62; H = ridge_z + 0.9; crs = 0.3; k = 0
    while k * crs < H:                                            # fieldstone chimney: battered stack against the west gable, three stones to a course
        z0 = k * crs; t_ = z0 / H; wy = 1.5 * (1 - 0.55 * smoothstep(0.25, 0.6, t_)); wx = 0.82 * (1 - 0.3 * smoothstep(0.25, 0.6, t_)); ys = np.linspace(-wy / 2, wy / 2, 4) if k % 2 == 0 else np.r_[-wy / 2, np.linspace(-wy / 6, wy / 6, 2), wy / 2]
        for i in range(len(ys) - 1):
            P3.blocks(parts, 'stone', (cx - wx / 2 + rng.uniform(-0.015, 0.015), ys[i] + 0.006, z0), (cx + wx / 2 + rng.uniform(-0.015, 0.015), ys[i + 1] - 0.006, z0 + crs - 0.012), c, hi, st[(k + i) % 3], seed=400 + k * 4 + i, bevel=0.03, warp=0.012)
        k += 1
    P3.blocks(parts, 'cap', (cx - 0.36, -0.42, H), (cx + 0.36, 0.42, H + 0.1), c, hi, st[0], seed=500, bevel=0.02)
    fl = L.box('floor', (-LX / 2 + 0.05, -LY / 2 + 0.05, 0.0), (LX / 2 - 0.05, LY / 2 - 0.05, 0.06), c, hi, bevel=0.01, warp=0.0, seed=600)
    dk = L.box('dark', (-LX / 2 + 0.1, -LY / 2 + 0.16, 0.06), (LX / 2 - 0.1, LY / 2 - 0.16, top - 0.05), c, hi, bevel=0.01, warp=0.0, seed=601)       # a dark core so the openings do not show the far wall or the sky
    if hi:
        d = NT('dark'); d.set(base=(0.006, 0.005, 0.005), rough=1.0); dk.data.materials.append(d.mat); fl.data.materials.append(T.wood_mat('floor', axis=0, light=(0.12, 0.07, 0.03), dark=(0.04, 0.022, 0.01)))
    parts += [fl, dk]; return parts


SPECS = {
    'Log_Cabin': dict(fn=log_cabin, fam='log_cabin', seq='59 struct/cabin/cabin- frame 1', cls='building', px=4096, tris=0, lo='param', ground='forrest_ground_01', third=['rock_boulder_dry'], extrude=0.02, maxdist=0.06, collision=True,
                      shot=dict(az=38, el=16, fill=1.0, close=(0.2, 0.0, 0.3, 0.2)),
                      weak='The corner notches are not cut: logs of one wall simply pass over those of the next with their ends proud, and the gaps between courses are closed by overlap rather than by chinking. '
                           'The roof is two flat slabs with the shingles in the textures (no shingle silhouette at the eaves, no rafters or sagging); the inside is a dark core, not a room. Chimney stones are bevelled blocks. '
                           'Door and window openings are empty: the leaf and the light are the log_cabin_door and log_cabin_window assets. One convex hull is exported.',
                      dresses='log cabin, 7.6 x 4.8 m and 5.4 m to the ridge: ten courses of weathered logs with proud ends, log gables, a mossy shingle roof at 38 degrees, a battered fieldstone chimney on the west gable, door and window openings in the south wall',
                      extra={'openings_m': {'door': {'wall': 'south (y = -2.1)', 'x': [-1.9, -0.9], 'height': 2.0}, 'window': {'wall': 'south (y = -2.1)', 'x': [1.2, 2.2], 'z': [0.95, 1.75]}}}),
}
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
