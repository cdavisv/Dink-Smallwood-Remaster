"""Photoreal replacements for the Stonebrook exterior (first screens): thatched fieldstone cottage, split-rail fence kit and gate,
well, field boulders.   blender -b -t 4 --python stonebrook_build.py
Footprints, pivots and the door position follow SourceAssets/Art/StonebrookExterior/exterior_manifest.json so they swap in place."""
import bpy, os, sys, json, math
import numpy as np
from mathutils import Matrix
_T = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'TownExteriors', 'tools', 'town_build2.py')
_s = open(_T).read()
exec(_s[:_s.index('\ndef modules(rows):')])
OUT = os.path.join(os.environ['DINK_PP'], 'Structures', 'Stonebrook')
os.makedirs(OUT, exist_ok=True)
T_STONE, T_THATCH, T_BOULDER = 2.0, 1.08, 2.0
SF, ST, SO = 0, 2, 1                     # cottage slots: fieldstone, thatch, oak
S1 = SO                                  # town helpers (timber, bar, peg, leaded, iron) write to the oak slot


def M4(yaw=0.0, t=(0, 0, 0)):
    return np.array(Matrix.Translation(t) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'))


# ---------------------------------------------------------------- cottage
CW, CD, WH, WT_ = 18.0, 9.0, 2.9, 0.5
DOOR_X, DOOR_W, DOOR_H = 5.3, 1.5, 2.5
PITCH_T = math.radians(38.0); OVH = 0.5
ZE0 = WH + 0.28                          # top of the thatch at the eaves edge


def wall_run(m, L, openings, zt=WH, t=WT_):
    """a rubble wall along local +X from 0 to L, centre line y = 0, with rectangular openings (x0, x1, z0, z1, kind)"""
    y = t / 2
    def reg(a, b, z0, z1):
        if b - a > 0.03 and z1 - z0 > 0.03:
            m.slab(a, b, z0, z1, -y, y, SF, T_STONE, nx=max(1, int(round((b - a) / 0.2))), nz=max(1, int(round((z1 - z0) / 0.2))), relief=0.028)
    x = 0.0
    for (ox0, ox1, oz0, oz1, kind) in sorted(openings):
        reg(x, ox0, 0, zt); reg(ox0, ox1, 0, oz0); reg(ox0, ox1, oz1, zt); x = ox1
        zz = oz0 + (0.0 if kind == 'door' else 0.02); i = 0     # big squared jamb stones up both sides, alternately long and short
        while zz < oz1 - 1e-6:
            hh = min(float(m.rng.uniform(0.3, 0.44)), oz1 - zz)
            if oz1 - (zz + hh) < 0.18:
                hh = oz1 - zz
            for sx in (-1, 1):
                lw = (0.52 if (i + (sx > 0)) % 2 == 0 else 0.3) + m.rng.normal(0, 0.02)
                xa_, xb_ = (ox0 - lw, ox0) if sx < 0 else (ox1, ox1 + lw)
                m.block([xa_, -y - 0.04 + m.rng.normal(0, 0.008), zz + 0.006], [xb_, -y + 0.3, zz + hh - 0.006], SF, T_STONE * 0.5, 0.028, 0.009, tag=TAG_STONE)
            zz += hh; i += 1
        # oak lintel, built into the wall
        timber(m, [ox0 - 0.34, -y - 0.045, oz1], [ox1 + 0.34, -y + 0.3, oz1 + 0.26], 0.022, 0.006)
        if kind == 'window':
            m.block([ox0 - 0.12, -y - 0.09, oz0 - 0.12], [ox1 + 0.12, -y + 0.2, oz0], SF, T_STONE * 0.5, 0.02, 0.006, tag=TAG_STONE)   # stone sill
            yf = -y + 0.14; fw = 0.07
            timber(m, [ox0, yf, oz0], [ox0 + fw, yf + 0.08, oz1], 0.008, 0.002); timber(m, [ox1 - fw, yf, oz0], [ox1, yf + 0.08, oz1], 0.008, 0.002)
            timber(m, [ox0 + fw, yf, oz0], [ox1 - fw, yf + 0.08, oz0 + fw], 0.008, 0.002); timber(m, [ox0 + fw, yf, oz1 - fw], [ox1 - fw, yf + 0.08, oz1], 0.008, 0.002)
            cx = (ox0 + ox1) / 2
            timber(m, [cx - 0.03, yf, oz0 + fw], [cx + 0.03, yf + 0.07, oz1 - fw], 0.006, 0.002)
            for (a, b) in ((ox0 + fw, cx - 0.03), (cx + 0.03, ox1 - fw)):
                leaded(m, a, b, oz0 + fw, oz1 - fw, yf + 0.035)
            m.block([ox0, -y + 0.24, oz0], [ox1, y - 0.03, oz1], SO, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS)
            # ledged board shutters, folded back against the wall, each on two strap hinges
            for sx in (-1, 1):
                sw = (ox1 - ox0) / 2 - 0.02; xa = ox0 - 0.03 - sw if sx < 0 else ox1 + 0.03
                ys = -y - 0.065 + m.rng.normal(0, 0.006); bx = xa
                nb = 3
                for k in range(nb):
                    bw = sw / nb
                    m.block([bx + 0.003, ys + m.rng.normal(0, 0.002), oz0 - 0.02 + abs(m.rng.normal(0, 0.006))], [bx + bw - 0.003, ys + 0.028, oz1 + 0.03 - abs(m.rng.normal(0, 0.006))],
                            SO, T_TIMBER, 0.004, 0.001, mode='board', board=m.timber_rows[m.rng.integers(len(m.timber_rows))], tag=TAG_TIMBER)
                    bx += bw
                for zz in (oz0 + 0.2, oz1 - 0.2):
                    timber(m, [xa + 0.03, ys - 0.03, zz - 0.05], [xa + sw - 0.03, ys + 0.0, zz + 0.05], 0.006, 0.001)
                    hx0, hx1 = (xa + sw - 0.3, xa + sw + 0.02) if sx < 0 else (xa - 0.02, xa + 0.3)
                    iron(m, [hx0, ys - 0.04, zz - 0.018], [hx1, ys - 0.03, zz + 0.018], 0.003)
            m.streak_src.append((ox0 - 0.14, ox0 + 0.05, oz0 - 0.12, 0.8)); m.streak_src.append((ox1 - 0.05, ox1 + 0.14, oz0 - 0.12, 0.8))
        else:                                                   # doorway: oak frame, worn threshold, the dark room behind
            timber(m, [ox0, -y + 0.1, 0.0], [ox0 + 0.12, -y + 0.26, oz1], 0.012, 0.003); timber(m, [ox1 - 0.12, -y + 0.1, 0.0], [ox1, -y + 0.26, oz1], 0.012, 0.003)
            m.block([ox0 - 0.2, -y - 0.42, -0.02], [ox1 + 0.2, -y + 0.3, 0.09], SF, T_STONE * 0.5, 0.03, 0.008, tag=TAG_STONE)
            m.block([ox0, -y + 0.3, 0.0], [ox1, y + 0.05, oz1], SO, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)
    reg(x, L, 0, zt)


TAG_CHAR, TAG_EARTH, TAG_ASH, TAG_TCREV, TAG_TBLACK = 45, 46, 47, TAG_THATCH + 60, TAG_THATCH + 70


def thatch_planes(m, x0, x1, y0, y1, ze, tp, seed, clip=None, thick=0.42, expo=0.36):
    """hipped thatch built as four separate slope planes, each a closed solid whose rows are the course butts: a rounded 0.4 m
    eaves roll with an undercut, a 5 cm ledge every 0.36 m, ragged butt lines, lumps, hollows, rounded hips and ridge. Every plane
    has its own UVs with the stalks running down its slope, so the hips are honest seams between two straw directions.
    clip {plane: (t0, t1, smax)}: only part of a plane (burnt state)."""
    r = m.rng; pit = math.atan(tp); cp, sp = math.cos(pit), math.sin(pit)
    dmax = (y1 - y0) / 2; S = dmax / cp; ov = 0.07
    planes = {'front': ((x0, y0), (1, 0), (0, 1), x1 - x0), 'back': ((x1, y1), (-1, 0), (0, -1), x1 - x0),
              'left': ((x0, y1), (0, -1), (1, 0), y1 - y0), 'right': ((x1, y0), (0, 1), (-1, 0), y1 - y0)}
    hollows = getattr(m, 'hollows', [])

    def lump(x, y):
        P = np.array([[x, y, 0.0]])
        v = 0.045 * vnoise(P, seed + 1, 0.8)[0] + 0.022 * vnoise(P, seed + 2, 2.4)[0] + 0.01 * vnoise(P, seed + 3, 6.0)[0]
        for (hx_, hy_, hr_, hd_) in hollows:
            q = math.hypot(x - hx_, y - hy_) / hr_
            if q < 1:
                v -= hd_ * (1 - q * q) ** 2
        return v

    def hround(t):
        return -0.13 * max(0.0, 1 - t / 0.5) ** 2

    def pt(e, a, s, h):
        (ox, oy), (ax, ay), (ix, iy), Le = planes[e]; d = s * cp
        return [ox + a * ax + d * ix - h * sp * ix, oy + a * ay + d * iy - h * sp * iy, ze + s * sp + h * cp]
    nc = int((S - 0.2) / expo)
    for e, ((ox, oy), (ax, ay), (ix, iy), Le) in planes.items():
        if clip is not None and e not in clip:
            continue
        t0, t1, smax = clip[e] if clip is not None else (0.0, 1.0, S)
        rows = [(-0.03, -0.27, 1), (0.0, -0.11, 0), (0.08, -0.015, 0)]
        for i in range(1, nc + 1):
            if i * expo > smax:
                break
            rows += [(i * expo, 0.0, 1), (i * expo, 1.0, 0)]
        rows.append((min(S, smax), 0.3, 0))
        nA = max(4, int(Le * (t1 - t0) / 0.3)); R_ = len(rows); C_ = nA + 1
        top = np.zeros((R_, C_, 3)); under = np.zeros_like(top); tags = np.zeros((R_, C_), int)
        for ri, (sn, hb, crev) in enumerate(rows):
            d = max(sn, 0) * cp
            amin = max(d - ov, t0 * Le); amax = min(Le - d + ov, t1 * Le)
            if clip is not None:                               # ragged burnt edges
                if t0 > 0:
                    amin += 0.5 * vnoise(np.array([[sn * 2.1, seed, 1.0]]), seed + 30, 1.0)[0]
                if t1 < 1:
                    amax += 0.5 * vnoise(np.array([[sn * 2.1, seed, 5.0]]), seed + 31, 1.0)[0]
            if amax - amin < 2 * ov:
                mid = (amin + amax) / 2; amin, amax = mid - ov, mid + ov
            for c in range(C_):
                a_ = amin + (amax - amin) * c / nA
                xw = ox + a_ * ax + d * ix; yw = oy + a_ * ay + d * iy
                Pn = np.array([[xw, yw, 0.0]])
                s_ = sn
                if ri >= 3 and ri < R_ - 1:
                    s_ = sn + 0.04 * vnoise(Pn * np.array([3.0, 3.0, 1]), seed + 7 + (ri - 3) // 2, 1.0)[0]
                h = hb
                if ri >= 3 and hb == 1.0:
                    h = 0.05 + 0.018 * vnoise(Pn, seed + 11 + ri, 2.0)[0]
                elif ri == R_ - 1:
                    h = 0.015
                if smax < S and ri == R_ - 1:
                    s_ = sn + 0.3 * vnoise(Pn, seed + 40, 1.5)[0]; h = -0.02
                hip = -0.09 * max(0.0, 1 - min(a_ - d, Le - d - a_) / 0.45) ** 2 if clip is None or (t0 == 0 and t1 == 1) else 0.0
                fade = min(1.0, max(0.25, sn / 0.3))
                h += lump(xw, yw) * fade + hround(S - s_) + hip
                top[ri, c] = pt(e, a_, s_, h)
                under[ri, c] = pt(e, a_, 0.17 + 0.02 * ri if ri < 3 else max(s_, 0.25 + 0.002 * ri), -thick - (0.0 if ri < 3 else 0.004 * (ri % 2)))
                tags[ri, c] = TAG_TCREV if crev else TAG_THATCH
        uo = r.uniform(0, 1, 2)

        def uvface(Pf, ox=ox, oy=oy, ax=ax, ay=ay, ix=ix, iy=iy, uo=uo):
            return [(((q[0] - ox) * ax + (q[1] - oy) * ay) / T_THATCH + uo[0], ((q[0] - ox) * ix + (q[1] - oy) * iy) / cp / T_THATCH + uo[1]) for q in Pf]
        n0 = len(m.V)
        m.hgrid(top, under, ST, T_THATCH, tag=TAG_THATCH, up=(-ix * sp, -iy * sp, cp), uvface=uvface, smooth=True)
        m.VT[n0:n0 + R_ * C_] = tags.reshape(-1).tolist()
    m.thatch_d = (x0, x1, y0, y1, ze, tp)
    m.roof = dict(pt=pt, S=S, hround=hround, x0=x0, x1=x1)


def ridge_block(m, xa, xb):
    """block-cut ridge: a second coat of straw saddled over the ridge, 10 cm proud, with a pointed (scalloped) lower edge, held by
    hazel liggers and crossed spars"""
    r = m.rng; na = max(3, int((xb - xa) / 0.125)); nt = 8; half = 0.78
    R_ = m.roof; pt = R_['pt']; S = R_['S']

    def surf(x, t, lift=0.0):
        e = 'front' if t < 0 else 'back'
        a_ = x - R_['x0'] if t < 0 else R_['x1'] - x
        return np.array(pt(e, a_, S - abs(t), R_['hround'](abs(t)) + lift))
    A = np.linspace(xa, xb, na + 1)
    top = np.zeros((na + 1, 2 * nt + 1, 3)); under = np.zeros_like(top)
    for i, x in enumerate(A):
        ph = ((x - xa) / 0.5) % 1.0
        scal = half + 0.17 * (1 - abs(ph * 2 - 1)) + r.normal(0, 0.006)
        endf = max(0.0, min(1.0, (x - xa) / 0.4, (xb - x) / 0.4))
        for j in range(2 * nt + 1):
            t = (j - nt) / nt * scal
            top[i, j] = surf(x, t, 0.10 * (0.5 + 0.5 * endf) + 0.01 * math.sin(x * 3.1 + j)); under[i, j] = surf(x, t, -0.05)
    uo = r.uniform(0, 1, 2); cpit = 0.8
    m.hgrid(top, under, ST, T_THATCH, tag=TAG_THATCH + 40, up=(0, 0, 1), smooth=True,
            uvface=lambda Pf: [(p[0] / T_THATCH + uo[0], abs(p[1]) / cpit / T_THATCH + uo[1]) for p in Pf])
    rod = dict(sides=5, tag=TAG_TIMBER, smooth=False)
    for sg in (-1, 1):
        for tl in (0.14, 0.42, 0.7):
            pts = [surf(x, sg * tl, 0.115 + r.normal(0, 0.003)) for x in np.linspace(xa + 0.12, xb - 0.12, max(4, int((xb - xa) / 0.5)))]
            m.tube(pts, 0.012, SO, **rod)
        x = xa + 0.2; flip = False
        while x < xb - 0.45:
            for (ta, tb) in ((0.14, 0.42), (0.42, 0.7)):
                a_ = surf(x, sg * (ta if flip else tb), 0.128); b_ = surf(x + 0.3, sg * (tb if flip else ta), 0.128)
                m.tube([a_, (a_ + b_) / 2 + np.array([0, 0, 0.01]), b_], 0.008, SO, **rod)
            x += 0.3; flip = not flip


def mound(m, cx, cy, rx, ry, h, slot, tile, tag, seed):
    """a slumped heap (fallen thatch, ash): closed dome with a lumpy top"""
    n = 9; top = np.zeros((n, n, 3)); under = np.zeros_like(top)
    for i in range(n):
        for j in range(n):
            u, v = (i / (n - 1)) * 2 - 1, (j / (n - 1)) * 2 - 1
            q = min(1.0, math.hypot(u, v)); x = cx + u * rx; y = cy + v * ry
            z = h * (1 - q * q) ** 1.1 * (1 + 0.45 * vnoise(np.array([[x, y, 0.0]]), seed, 2.5)[0]) + 0.012
            top[i, j] = [x, y, max(z, 0.012)]; under[i, j] = [x, y, 0.0]
    m.hgrid(top, under, slot, tile, tag=tag, up=(0, 0, 1), smooth=True)


def apron(m, hx, hy, door_x):
    """worn bare earth round the wall foot, feathering into the turf, wider and trodden in front of the door"""
    r = m.rng; sd = int(r.integers(1e6))
    for (ox, oy, ax, ay, nx_, ny_, L) in ((-hx, -hy, 1, 0, 0, -1, 2 * hx), (hx, hy, -1, 0, 0, 1, 2 * hx), (hx, -hy, 0, 1, 1, 0, 2 * hy), (-hx, hy, 0, -1, -1, 0, 2 * hy)):
        na = int((L + 1.6) / 0.4); top = np.zeros((na + 1, 4, 3)); under = np.zeros_like(top)
        for i in range(na + 1):
            a_ = -0.8 + (L + 1.6) * i / na
            bx, by = ox + a_ * ax, oy + a_ * ay
            wd = 0.62 + 0.2 * vnoise(np.array([[bx, by, 0.0]]), sd, 0.6)[0] + 0.07 * vnoise(np.array([[bx, by, 0.0]]), sd + 1, 2.0)[0]
            if door_x is not None and ny_ == -1:
                wd += 1.9 * max(0.0, 1 - ((bx - door_x) / 2.4) ** 2) ** 1.5
            wd *= min(1.0, max(0.15, (a_ + 0.8) / 0.6), max(0.15, (L + 0.8 - a_) / 0.6))
            for j, (f, z) in enumerate(((-0.25, 0.04), (0.3, 0.035), (0.7, 0.02), (1.0, 0.004))):
                dd = wd * f if f > 0 else -0.25
                top[i, j] = [bx + nx_ * dd, by + ny_ * dd, z]; under[i, j] = [bx + nx_ * dd, by + ny_ * dd, 0.0]
        n0 = len(m.V)
        m.hgrid(top, under, 4, 4.0, tag=TAG_EARTH, up=(0, 0, 1), smooth=True, grid_under=True)
        tg = np.zeros((na + 1, 4), int); tg[:, :] = TAG_EARTH; tg[:, 3] = TAG_EARTH + 1; tg[:, 2] = TAG_EARTH + 2
        m.VT[n0:n0 + (na + 1) * 4] = tg.reshape(-1).tolist()
    if door_x is not None:                                   # a few flagstones bedded at the door
        for (dx, dy, w, d_) in ((-0.1, 0.75, 0.8, 0.6), (0.75, 1.05, 0.6, 0.55), (-0.85, 1.2, 0.7, 0.5), (0.1, 1.55, 0.75, 0.6), (-0.6, 2.05, 0.6, 0.5), (0.6, 2.2, 0.65, 0.5)):
            cxp, cyp = door_x + dx + r.normal(0, 0.03), -hy - dy
            m.block([cxp - w / 2, cyp - d_ / 2, 0.0], [cxp + w / 2, cyp + d_ / 2, 0.075 + r.normal(0, 0.006)], SF, T_STONE * 0.5, 0.02, 0.012, tag=TAG_STONE, rot=(float(r.normal(0, 0.15)), 0, 0))


def burnt_roof(m, hx, hy, tp, zr, rl):
    """what the fire left: charred rafter couples (some snapped, some gone), a broken ridge pole, a few laths, fallen timbers,
    heaps of burnt thatch and ash inside and spilled outside"""
    r = m.rng
    T = lambda pts, rad, sides=6: m.tube(pts, rad, SO, sides=sides, tag=TAG_CHAR, smooth=False, rough=0.07, shape=[1, 0.85, 1, 0.8, 1.05, 0.9][:sides])
    x = -rl + 0.6
    while x < rl + 0.4:
        for sg in (-1, 1):
            p0 = np.array([x + r.normal(0, 0.03), sg * (hy - 0.1), WH + 0.14]); p1 = np.array([x, 0.0, zr - 0.3]); u = r.uniform()
            if x < -rl + 5.5 or u < 0.3:
                T([p0, (p0 + p1) / 2 + np.array([0, 0, -0.03]), p1], [0.075, 0.07, 0.06])
            elif u < 0.75:                                    # snapped: a stub with a burnt point
                f = r.uniform(0.3, 0.7); pm = p0 + (p1 - p0) * f
                T([p0, p0 + (pm - p0) * 0.6, pm], [0.075, 0.065, 0.02])
                if r.uniform() < 0.6:                         # its top lies inside
                    q = np.array([x + r.normal(0, 0.5), sg * r.uniform(0.3, 2.5), 0.12]); T([q, q + np.array([r.normal(0, 0.8), r.uniform(1.2, 2.2) * -sg, r.uniform(0.0, 0.5)])], [0.06, 0.03])
        x += float(r.uniform(1.0, 1.25))
    T([[-rl - 0.1, 0, zr - 0.24], [-rl + 3.0, 0.02, zr - 0.26], [-rl + 6.2, 0.0, zr - 0.3]], [0.085, 0.08, 0.05])                        # ridge pole, standing part
    T([[-rl + 6.6, 0.3, zr - 1.6], [-rl + 9.5, 0.9, 1.9], [-rl + 12.0, 1.3, 0.25]], [0.05, 0.08, 0.08])                                # and the part that came down
    for sg, keep in ((-1, True), (1, False)):                                                                                       # east hip rafters
        p0 = np.array([hx - 0.1, sg * (hy - 0.1), WH + 0.14]); p1 = np.array([rl, 0.0, zr - 0.3])
        T([p0, (p0 + p1) / 2, p1] if keep else [p0, p0 + (p1 - p0) * 0.25, p0 + (p1 - p0) * 0.45], [0.08, 0.07, 0.06] if keep else [0.08, 0.07, 0.02])
    for k in range(5):                                                                                                              # laths still tied to the western rafters
        f = 0.15 + 0.17 * k
        for sg in (-1, 1):
            y_ = sg * (hy - 0.1) * (1 - f); z_ = WH + 0.2 + (zr - 0.3 - WH - 0.14) * f
            if r.uniform() < 0.35:
                continue
            xa_ = -rl + 4.4 + r.uniform(-0.3, 1.0); xb_ = min(xa_ + r.uniform(1.0, 2.6), -rl + 6.9)
            m.tube([[xa_, y_, z_], [(xa_ + xb_) / 2, y_ + 0.02, z_ - 0.03], [xb_, y_, z_ - r.uniform(0.0, 0.25)]], 0.022, SO, sides=4, tag=TAG_CHAR, smooth=False)
    for (cx, cy, rx, ry, h, kind) in ((2.5, 0.5, 2.6, 2.0, 0.75, 't'), (6.2, -1.2, 1.9, 1.6, 0.6, 't'), (5.0, 2.2, 1.6, 1.3, 0.45, 'a'), (-0.5, -1.0, 1.7, 1.4, 0.5, 't'),
                                      (7.3, -5.6, 1.3, 0.9, 0.34, 'a'), (1.4, -5.4, 1.1, 0.8, 0.28, 't'), (9.9, 1.0, 0.9, 1.3, 0.3, 'a'), (3.6, 5.5, 1.4, 0.8, 0.3, 'a')):
        mound(m, cx, cy, rx, ry, h, ST if kind == 't' else 4, T_THATCH if kind == 't' else 4.0, TAG_TBLACK if kind == 't' else TAG_ASH, int(r.integers(1e6)))
    for k in range(9):                                                                                                              # charred lengths lying about
        c = np.array([r.uniform(-1, 8.5), r.uniform(-3.5, 3.5), r.uniform(0.1, 0.6)]) if k < 6 else np.array([r.uniform(0, 9), -hy - r.uniform(0.6, 2.2), 0.08])
        d_ = np.array([math.cos(a_ := r.uniform(0, 6.28)), math.sin(a_), r.normal(0, 0.12)]) * r.uniform(0.6, 1.6)
        T([c - d_, c + d_ * 0.2, c + d_], [0.06, 0.055, 0.025])
    T([[4.6, -hy - 0.5, 0.06], [4.9, -hy + 0.1, WH * 0.55], [5.1, -hy + 0.45, WH + 0.1]], [0.07, 0.065, 0.05])                               # one rafter slid down against the front wall


def stack(m, cx, cy, w, dpt, z0, z1, slot=SF, tile=T_STONE * 0.5):
    """free-standing coursed stone stack of individually set blocks"""
    r = m.rng; z = z0
    while z < z1 - 1e-6:
        h = min(float(r.uniform(0.17, 0.26)), z1 - z)
        if z1 - (z + h) < 0.1:
            h = z1 - z
        n = 2 if w < 0.95 else 3
        cuts = sorted([-w / 2, w / 2] + [float(r.uniform(-w / 2 + 0.25, w / 2 - 0.25)) for _ in range(n - 1)])
        for a_, b_ in zip(cuts[:-1], cuts[1:]):
            if b_ - a_ < 0.05:
                continue
            m.block([cx + a_ + 0.004, cy - dpt / 2 + r.normal(0, 0.008), z + 0.004], [cx + b_ - 0.004, cy + dpt / 2 + r.normal(0, 0.008), z + h - 0.004], slot, tile, 0.022, 0.007,
                    tag=TAG_STONE if r.uniform() < 0.35 else TAG_SHEET)
        z += h


def cottage(m, W=CW, D=CD, door_x=DOOR_X, fw=(2.5, 6.5, 10.5), fw2=(16.4,), bw=(3.0, 9.0, 15.0), ew=(4.0,), patches=((-4.2, -3.2, 1.5, 1.0), (6.8, -2.2, 1.0, 1.3), (1.5, 3.0, 1.2, 0.9)), burnt=False):
    r = m.rng; hx, hy = W / 2, D / 2; m.patches = patches; m.burnt = burnt; m.open_w = []
    m.hollows = [(-hx * 0.35, -hy * 0.55, 0.9, 0.07), (hx * 0.55, hy * 0.5, 0.7, 0.06), (hx * 0.15, -hy * 0.2, 0.5, 0.05)]
    # windows: (centre, width) per wall, sill 1.05, head 2.15
    def wins(cs, w=1.0):
        return [(c - w / 2, c + w / 2, 1.05, 2.15, 'window') for c in cs]
    front = wins(list(fw)) + ([(hx + door_x - DOOR_W / 2, hx + door_x + DOOR_W / 2, 0.0, DOOR_H, 'door')] if door_x is not None else []) + wins(list(fw2), 0.9)
    for (L, ops, yaw, t) in ((W, front, 0, (-hx, -hy + WT_ / 2, 0)), (W, wins(list(bw)), 180, (hx, hy - WT_ / 2, 0)),
                             (D - 2 * WT_, wins(list(ew)), 90, (hx - WT_ / 2, -hy + WT_, 0)), (D - 2 * WT_, wins(list(ew)), -90, (-hx + WT_ / 2, hy - WT_, 0))):
        n0 = len(m.V); src0 = len(m.streak_src)
        wall_run(m, L, ops)
        m.xform_since(n0, M4(yaw, t))
        Mx = M4(yaw, t)
        for (ox0, ox1, oz0, oz1, kind_) in ops:
            c = Mx @ np.array([(ox0 + ox1) / 2, -WT_ / 2, oz1, 1.0]); m.open_w.append((c[0], c[1], oz1, (ox1 - ox0) / 2))
        for k in range(src0, len(m.streak_src)):       # streak sources into world space (centre point and half width)
            xa, xb, zt, kk = m.streak_src[k]
            c = Mx @ np.array([(xa + xb) / 2, -WT_ / 2, zt, 1.0])
            m.streak_w.append((c[0], c[1], zt, (xb - xa) / 2 + 0.1, kk))
    m.streak_src = []
    # quoins: big squared stones at the four corners, alternately long on each face
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        z = 0.0; i = 0
        while z < WH - 1e-6:
            h = min(float(r.uniform(0.34, 0.5)), WH - z)
            if WH - (z + h) < 0.2:
                h = WH - z
            la, lb = (float(r.uniform(0.85, 1.05)), 0.5) if i % 2 == 0 else (0.5, float(r.uniform(0.85, 1.05)))
            o = 0.06 + r.normal(0, 0.01)
            cxp, cyp = sx * hx, sy * hy
            lo = [min(cxp + sx * o, cxp - sx * la), min(cyp + sy * o, cyp - sy * lb), z + 0.006]; hi = [max(cxp + sx * o, cxp - sx * la), max(cyp + sy * o, cyp - sy * lb), z + h - 0.006]
            m.block(lo, hi, SF, T_STONE * 0.5, 0.03, 0.01, tag=TAG_STONE)
            z += h; i += 1
    # footing: half-buried field stones along the base of the walls
    per = [(-hx, -hy, hx, -hy), (hx, -hy, hx, hy), (hx, hy, -hx, hy), (-hx, hy, -hx, -hy)]
    for (ax, ay, bx, by) in per:
        L = math.hypot(bx - ax, by - ay); s = 0.5
        nx_, ny_ = (by - ay) / L, -(bx - ax) / L          # outward normal
        while s < L - 0.4:
            if not (ay == -hy and by == -hy and abs((ax + (bx - ax) * s / L) - (door_x if door_x is not None else 1e9)) < 1.3) and vnoise(np.array([[ax + (bx - ax) * s / L, ay + (by - ay) * s / L, 0.0]]), 77, 0.9)[0] > -0.1:
                sz = [float(r.uniform(0.28, 0.75)), float(r.uniform(0.3, 0.5)), float(r.uniform(0.16, 0.34))]
                c = [ax + (bx - ax) * s / L + nx_ * float(r.uniform(-0.06, 0.06)), ay + (by - ay) * s / L + ny_ * float(r.uniform(-0.06, 0.06)), sz[2] * float(r.uniform(0.05, 0.25))]
                if abs(nx_) > 0.5:
                    sz = [sz[1], sz[0], sz[2]]
                m.rock(c, sz, SF, T_STONE * 0.6, sub=2, tag=TAG_STONE, lump=0.3, smooth=True, facets=6, crease=0.06)
            s += float(r.uniform(0.3, 1.5))
    # wall plate and the feet of the rafter poles under the eaves (the dark dots of the sprite)
    for (a, b) in (([-hx, -hy, WH - 0.02], [hx, -hy + 0.2, WH + 0.16]), ([-hx, hy - 0.2, WH - 0.02], [hx, hy, WH + 0.16]),
                   ([-hx, -hy + 0.2, WH - 0.02], [-hx + 0.2, hy - 0.2, WH + 0.16]), ([hx - 0.2, -hy + 0.2, WH - 0.02], [hx, hy - 0.2, WH + 0.16])):
        timber(m, a, b, 0.015, 0.004)
    tp = math.tan(PITCH_T)
    def pole(px, py, dx, dy):
        p0 = np.array([px + dx * (OVH - 0.02), py + dy * (OVH - 0.02), ZE0 - 0.36 - 0.02 * tp]); p1 = np.array([px - dx * 0.5, py - dy * 0.5, ZE0 - 0.36 + (OVH + 0.5) * tp * 0.92])
        m.tube([p0, p1], [float(r.uniform(0.038, 0.05)), 0.05], SO, sides=6, tag=TAG_TIMBER, smooth=True, rough=0.04)
    x = -hx + 0.35
    while x < hx - 0.2:
        pole(x, -hy, 0, -1); pole(x + r.normal(0, 0.03), hy, 0, 1); x += float(r.uniform(0.52, 0.68))
    y = -hy + 0.5
    while y < hy - 0.3:
        pole(-hx, y, -1, 0); pole(hx, y + r.normal(0, 0.03), 1, 0); y += float(r.uniform(0.52, 0.68))
    # thatch
    x0, x1, y0, y1 = -hx - OVH, hx + OVH, -hy - OVH, hy + OVH
    dmax = (y1 - y0) / 2; zr = ZE0 + tp * dmax + 0.02; rl = (x1 - x0) / 2 - dmax
    if not burnt:
        thatch_planes(m, x0, x1, y0, y1, ZE0, tp, 439)
        ridge_block(m, -rl + 0.25, rl + 0.1)
        for (cx_, cy_, ex_) in ((x0, y0, -rl), (x0, y1, -rl), (x1, y0, rl), (x1, y1, rl)):      # hip rolls: a twisted straw roll laid over each hip joint
            pts = []
            for k in range(13):
                f = k / 12; px = cx_ + (ex_ - cx_) * f; py = cy_ * (1 - f)
                pts.append([px, py, ZE0 + tp * dmax * f - 0.13 * max(0.0, 1 - (1 - f) * dmax / 0.4) ** 2 - 0.02 + 0.02 * math.sin(k * 1.7)])
            m.tube(pts, [0.1] + [0.12] * 11 + [0.09], ST, sides=7, tag=TAG_THATCH + 40, tile=T_THATCH, smooth=True, rough=0.05, vrange=(0.5, 0.5), twist=1.2)
    else:                                                # the west end still carries its coat, burnt back in a ragged line
        S_ = dmax / math.cos(math.atan(tp)); m.xburn = x0 + 0.36 * (x1 - x0)
        thatch_planes(m, x0, x1, y0, y1, ZE0, tp, 439, clip={'left': (0.0, 1.0, S_), 'front': (0.0, 0.36, S_), 'back': (0.64, 1.0, S_)})
        burnt_roof(m, hx, hy, tp, zr, rl)
        m.slab(-hx + WT_, hx - WT_, 0.0, 0.035, -hy + WT_, hy - WT_, 4, 4.0, nx=18, nz=1, relief=0.0, tag=TAG_ASH)      # the floor: ash and cinders
    apron(m, hx, hy, door_x)
    if door_x is not None:                               # the door: ajar outward when the house stands, burnt and fallen flat when it does not
        n0 = len(m.V); f0 = len(m.F)
        door_leaf(m, 1.44, 2.46)
        for k in range(f0, len(m.F)):
            m.FM[k] = 3
        for k in range(n0, len(m.V)):
            if m.VT[k] == TAG_SHEET:
                m.VT[k] = TAG_CHAR if burnt else TAG_TIMBER
        if not burnt:
            m.xform_since(n0, M4(-62, (door_x - 0.72, -hy + 0.2, 0.09)))
        else:
            m.xform_since(n0, np.array(Matrix.Translation((door_x - 1.3, -hy - 3.3, 0.09)) @ Matrix.Rotation(math.radians(17), 4, 'Z') @ Matrix.Rotation(math.radians(86), 4, 'X')))
    # chimney at the west hip, through the ridge
    cxp = -rl + 0.05
    stack(m, cxp, 0.0, 1.05, 0.8, zr - 1.3, zr + 0.5)
    m.block([cxp - 0.6, -0.48, zr + 0.5], [cxp + 0.6, 0.48, zr + 0.58], SF, T_STONE * 0.5, 0.014, 0.005, tag=TAG_STONE)
    stack(m, cxp, 0.0, 0.95, 0.72, zr + 0.58, zr + 0.76)
    m.block([cxp - 0.56, -0.44, zr + 0.76], [cxp + 0.56, 0.44, zr + 0.84], SF, T_STONE * 0.5, 0.014, 0.005, tag=TAG_STONE)
    m.block([cxp - 0.3, -0.2, zr + 0.3], [cxp + 0.3, 0.2, zr + 0.845], SO, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)          # the black flue
    m.chim = (cxp, 0.0, zr)
    # collision: walls around the doorway, roof hull
    if burnt:
        V_ = np.array(m.V); T_ = np.array(m.VT)
        par = list(range(len(V_)))                           # connected parts: a timber chars as a whole or not at all
        def find(i):
            while par[i] != i:
                par[i] = par[par[i]]; i = par[i]
            return i
        for f in m.F:
            a_ = find(f[0])
            for v in f[1:]:
                b_ = find(v)
                if b_ != a_:
                    par[b_] = a_
        root = np.array([find(i) for i in range(len(V_))])
        cen = np.zeros((len(V_), 3)); cnt = np.zeros(len(V_))
        np.add.at(cen, root, V_); np.add.at(cnt, root, 1); C_ = cen[root] / cnt[root][:, None]
        ch = (0.55 * vnoise(C_, 91, 0.8) + 0.45 * C_[:, 2] / WH + 0.6 * (C_[:, 0] > m.xburn - 1.5) + 0.3) > 0.5
        T_ = np.where(((T_ == TAG_TIMBER) | (T_ == TAG_END)) & ch, TAG_CHAR, T_); T_ = np.where(T_ == TAG_GLASS, TAG_GLASS + 30, T_); T_ = np.where(T_ == TAG_LEAD, TAG_CHAR, T_)
        m.VT = T_.tolist()
    if door_x is not None:
        dx0, dx1 = door_x - DOOR_W / 2, door_x + DOOR_W / 2
        m.ucx = [([-hx, -hy, 0], [dx0, hy, WH]), ([dx1, -hy, 0], [hx, hy, WH]), ([dx0, -hy + 0.6, 0], [dx1, hy, WH])]
    else:
        m.ucx = [([-hx, -hy, 0], [hx, hy, WH])]
    m.hulls = ([[[x0, y0, WH - 0.1], [x1, y0, WH - 0.1], [x1, y1, WH - 0.1], [x0, y1, WH - 0.1], [-rl, 0, zr + 0.05], [rl, 0, zr + 0.05]]] if not burnt else []) + [
               [[cxp - 0.55, -0.45, zr - 0.5], [cxp + 0.55, -0.45, zr - 0.5], [cxp + 0.55, 0.45, zr - 0.5], [cxp - 0.55, 0.45, zr - 0.5],
                [cxp - 0.55, -0.45, zr + 0.84], [cxp + 0.55, -0.45, zr + 0.84], [cxp + 0.55, 0.45, zr + 0.84], [cxp - 0.55, 0.45, zr + 0.84]]]


def sb_paint(m, kind):
    seed = int(m.rng.integers(1e6))

    def f(P, tags, N, col):
        z = P[:, 2]; n = vnoise(P, seed, 1.3); n2 = vnoise(P, seed + 3, 6.0); n3 = vnoise(P, seed + 9, 0.55)
        R = np.zeros(len(P)); G = np.zeros(len(P)); B = np.zeros(len(P)); A = np.ones(len(P))
        stone = (tags == TAG_SHEET) | (tags == TAG_STONE)
        Q = P.copy(); Q[:, 2] *= 0.3
        st = np.clip(0.5 + 0.9 * vnoise(Q * np.array([6.0, 6.0, 1.0]), seed + 5, 1.0), 0, 1)
        zb = getattr(m, 'zbase', 0.0)
        if kind in ('cottage', 'well', 'boulder', 'fence'):
            north = np.clip(N[:, 1], 0, 1)                                    # +Y faces: the damp side
            splash = np.clip((0.5 * (1 + 0.5 * n) - (z - zb)) / 0.4, 0, 1)
            alg = np.clip((0.34 * (1 + 0.9 * n3 + 0.4 * n2) + 0.5 * north * (0.4 + n3) - (z - zb)) / 0.35, 0, 1)
            Rs = np.clip(0.7 * splash + 0.14 + 0.16 * n, 0, 1)
            Gs = np.clip(0.85 * alg + 0.55 * (N[:, 2] > 0.55) * (0.45 + 0.6 * n3) + 0.25 * north * np.clip(n3 + 0.2, 0, 1), 0, 1)
            if kind == 'cottage':
                eav = np.clip(1 - (WH - z) / 0.9, 0, 1) * st * 0.5 * (z < WH + 0.01)      # run-off below the eaves
                Rs = np.clip(Rs + eav, 0, 1)
                for (sx_, sy_, zt, hw, kk) in m.streak_w:
                    dd = np.hypot(P[:, 0] - sx_, P[:, 1] - sy_)
                    run = np.clip(1 - dd / hw, 0, 1) * np.clip(1 - (zt - z) / 1.1, 0, 1) * (z < zt + 0.02)
                    Rs = np.clip(Rs + kk * run * (0.5 + 0.5 * st), 0, 1); Gs = np.clip(Gs + 0.4 * kk * run * (z < zt - 0.15), 0, 1)
                if getattr(m, 'chim', None):
                    cx_, cy_, zr_ = m.chim
                    soot = np.clip((z - (zr_ + 0.25)) / 0.6, 0, 1) * (np.hypot(P[:, 0] - cx_, P[:, 1] - cy_) < 1.2)
                    Rs = np.clip(Rs + soot, 0, 1)
            if kind == 'boulder':
                Rs = np.clip(0.75 * np.clip((0.22 * (1 + 0.6 * n) - z) / 0.22, 0, 1) + 0.15 + 0.2 * n2, 0, 1)
                Gs = np.clip(2.2 * np.clip(N[:, 2] - 0.3, 0, 1) * np.clip(0.45 + 0.9 * n3 + 0.3 * n2, 0, 1) + 0.6 * north * np.clip(n3 + 0.3, 0, 1) + 0.5 * np.clip((0.15 - z) / 0.15, 0, 1), 0, 1)
            Bs = np.where(tags == TAG_STONE, np.clip(0.45 + 0.3 * n2, 0, 1), np.clip(0.12 + 0.2 * n, 0, 1))
            Bs = np.clip(Bs + 0.5 * np.clip(n2 - 0.35, 0, 1) * (N[:, 2] > 0.2), 0, 1)        # lichen spots
            R = np.where(stone, Rs, R); G = np.where(stone, Gs, G); B = np.where(stone, Bs, B)
        tim = (tags == TAG_TIMBER) | (tags == TAG_END)
        expo = np.clip(0.3 + 0.35 * n + 0.4 * (N[:, 2] > 0.3) - 0.5 * (N[:, 2] < -0.4), 0, 1)
        dk = np.clip(0.22 + 0.25 * n2 + 0.45 * (N[:, 2] < -0.4) + 0.6 * np.clip((0.3 - (z - zb)) / 0.3, 0, 1), 0, 1)
        if kind == 'cottage':
            dk = np.clip(dk + 0.45 * (z > WH - 0.4) * (z < ZE0 + 0.1), 0, 1)                   # under the eaves: dark, never bleached
            expo = np.where((z > WH - 0.4) & (z < ZE0 + 0.1), expo * 0.3, expo)
        gm = np.clip(0.6 * (N[:, 2] > 0.6) * (0.3 + n3) + 0.7 * np.clip((0.3 - (z - zb)) / 0.3, 0, 1) * (0.5 + n), 0, 1)
        R = np.where(tim, dk, R); B = np.where(tim, expo, B); G = np.where(tim, gm, G)
        th = (tags == TAG_THATCH) | (tags == TAG_THATCH + 40) | (tags == TAG_TCREV) | (tags == TAG_TBLACK)
        if th.any():
            x0, x1, y0, y1, ze, tp = m.thatch_d
            d = np.minimum.reduce([P[:, 0] - x0, x1 - P[:, 0], P[:, 1] - y0, y1 - P[:, 1]])
            dmax = (y1 - y0) / 2
            crev = (tags == TAG_TCREV).astype(float)
            along = np.where(np.abs(N[:, 1]) >= np.abs(N[:, 0]), P[:, 0], P[:, 1])             # coordinate along the eaves of this pitch
            comb = np.clip(0.5 + 0.9 * vnoise(np.stack([along * 9.0, 0 * along, 0 * along], -1), seed + 15, 1.0), 0, 1)      # combed streaks down the slope
            wide = np.clip(0.5 + 0.9 * vnoise(np.stack([along * 1.7, 0 * along, 0 * along], -1), seed + 16, 1.0), 0, 1)
            hol = np.zeros(len(P))
            for (hx_, hy_, hr_, hd_) in getattr(m, 'hollows', ()):
                hol = np.maximum(hol, np.clip(1 - np.hypot(P[:, 0] - hx_, P[:, 1] - hy_) / hr_, 0, 1))
            shade = np.clip(N[:, 1], 0, 1)                                                     # the north pitch stays damp
            Rt = np.clip(0.72 + 0.4 * n3 + 0.2 * n + 0.3 * (comb - 0.5) + 0.3 * (wide - 0.5) + 0.45 * crev + 0.3 * np.clip(1 - d / 0.5, 0, 1) + 0.6 * (N[:, 2] < 0.1) + 0.25 * shade + 0.5 * hol, 0, 1)
            ridge = np.clip(1 - (dmax - d) / 1.0, 0, 1)
            Gt = np.clip(1.6 * np.clip(shade - 0.1, 0, 1) * np.clip(0.45 + 0.9 * n3 + 0.4 * n, 0, 1) + (0.75 * crev + 0.15) * np.clip(n3 + 0.5 * n2 + 0.15, 0, 1)
                         + 0.6 * ridge * np.clip(n2 + n + 0.2, 0, 1) + 0.6 * np.clip(1 - d / 0.7, 0, 1) * np.clip(n2 + 0.5 * n, 0, 1) + 0.6 * hol, 0, 1)
            patch = np.zeros(len(P))
            for (px, py, rx, ry) in getattr(m, 'patches', ()):
                patch = np.maximum(patch, np.clip(1.3 - np.hypot((P[:, 0] - px) / rx, (P[:, 1] - py) / ry) * 1.3 + 0.5 * n2 + 0.3 * n, 0, 1))
            Bt = np.clip(0.08 + 0.2 * np.clip(n, 0, 1) + 0.2 * (comb - 0.5) + 0.5 * patch, 0, 1)
            Rt = np.clip(Rt - 0.4 * patch, 0, 1); Gt = Gt * (1 - patch)
            rb = tags == TAG_THATCH + 40
            Bt = np.where(rb, np.clip(0.32 + 0.25 * n + 0.2 * (comb - 0.5), 0, 1), Bt); Rt = np.where(rb, np.clip(0.3 + 0.3 * n3 + 0.2 * n2 + 0.6 * (N[:, 2] < 0.3), 0, 1), Rt); Gt = np.where(rb, Gt * 0.5, Gt)
            if getattr(m, 'chim', None):
                cx_, cy_, zr_ = m.chim
                near = np.clip(1 - (np.hypot(P[:, 0] - cx_, P[:, 1] - cy_) - 0.6) / 1.0, 0, 1)
                Rt = np.clip(Rt + 0.6 * near, 0, 1)
            At = np.ones(len(P))
            if getattr(m, 'burnt', False):                                                     # scorched coat, black toward the burn line
                front = P[:, 0] - (m.xburn - 1.6) + 0.9 * n + 0.4 * n2
                At = np.where((front > 0) | (tags == TAG_TBLACK), 0.5, 1.0); Rt = np.clip(Rt + 0.5, 0, 1); Gt = Gt * 0; Bt = Bt * 0.2
            R = np.where(th, Rt, R); G = np.where(th, Gt, G); B = np.where(th, Bt, B); A = np.where(th, At, A)
        ea = (tags >= TAG_EARTH) & (tags <= TAG_EARTH + 2) | (tags == TAG_ASH)
        if ea.any():
            edge = (tags == TAG_EARTH + 1).astype(float); mid = (tags == TAG_EARTH + 2).astype(float)
            Re = np.clip(0.55 - 0.35 * edge - 0.15 * mid + 0.3 * n + 0.2 * n2, 0, 1)             # damp and splashed against the wall, drier out in the yard
            Ge = np.clip(1.0 * edge + 0.45 * mid * np.clip(n + n2 + 0.3, 0, 1) + 0.2 * np.clip(n2, 0, 1), 0, 1)   # turf creeping in from the edge
            Be = np.clip(0.25 + 0.3 * n3 - 0.3 * edge, 0, 1)
            Ae = np.ones(len(P))
            if getattr(m, 'burnt', False):
                Ae = np.clip(1 - (0.55 + 0.6 * n + 0.3 * n2 + 0.3 * (P[:, 0] > 0)) * (1 - 0.7 * edge), 0, 1); Ge = Ge * edge
            ash = tags == TAG_ASH
            Re = np.where(ash, 0.2, Re); Ge = np.where(ash, 0.0, Ge); Be = np.where(ash, 0.45, Be); Ae = np.where(ash, np.clip(0.42 + 0.4 * n2 + 0.35 * n, 0, 1), Ae)
            R = np.where(ea, Re, R); G = np.where(ea, Ge, G); B = np.where(ea, Be, B); A = np.where(ea, Ae, A)
        if getattr(m, 'burnt', False) and kind == 'cottage':                                   # smoke-blackened stone: above every opening, under the lost roof, heavier where the fire was
            soot = 0.7 * np.clip((z - (WH - 1.6)) / 1.6, 0, 1) + 0.3 * (P[:, 0] > m.xburn - 2.0) + 0.3 * n + 0.2 * n2 + 0.5 * (N[:, 2] > 0.5)
            for (ox_, oy_, zt, hw) in m.open_w:
                dd = np.hypot(P[:, 0] - ox_, P[:, 1] - oy_)
                soot = soot + 1.5 * np.clip(1 - dd / (hw * 1.5 + 0.35 * np.clip(z - zt, 0, 2)), 0, 1) * np.clip((z - (zt - 0.5)) / 0.4, 0, 1) * np.clip(1 - (z - zt) / 2.0, 0.25, 1)
            A = np.where(stone, np.clip(1 - soot, 0, 1), A)
            ch = tags == TAG_CHAR
        A = np.where(tags == TAG_CHAR, 0.5, A); R = np.where(tags == TAG_CHAR, 1.0, R)
        if kind == 'door':
            sh = tags == TAG_SHEET
            R = np.where(sh, np.clip(0.25 + 0.3 * n + 0.6 * np.clip((0.4 - z) / 0.4, 0, 1), 0, 1), R); B = np.where(sh, np.clip(0.35 + 0.3 * n, 0, 1), B)
        if kind == 'well':                              # inside the shaft: wet, mossy below the rim, darker with depth; the capstone polished pale where the rope drags
            RI_, RO_, zt_, bx_, by_ = m.well
            rad = np.hypot(P[:, 0], P[:, 1]); inward = (P[:, 0] * N[:, 0] + P[:, 1] * N[:, 1]) < -0.2 * np.maximum(rad, 1e-3)
            ins = stone & (rad < RI_ + 0.12) & inward
            R = np.where(ins, np.clip(0.75 + 0.3 * n + 0.25 * np.clip(-z / 1.5, 0, 1), 0, 1), R)
            G = np.where(ins, np.clip(1.15 - 0.9 * np.clip(-z / 2.2, 0, 1) + 0.3 * n2, 0, 1), G); B = np.where(ins, 0.0, B)
            wear = np.clip(1 - np.hypot(P[:, 0] - bx_ * 0.82, P[:, 1] - by_ * 0.82) / 0.22, 0, 1) * (z > zt_ - 0.12) * stone
            B = np.clip(B + 0.9 * wear, 0, 1); G = G * (1 - wear); R = R * (1 - 0.7 * wear)
        if kind == 'fence':                             # long weathered: silver-grey with lichen, green on top, dark and damp at the foot
            ft = (tags == TAG_TIMBER) | (tags == TAG_END)
            B = np.where(ft, np.clip(0.6 + 0.3 * n + 0.5 * np.clip(n2 - 0.2, 0, 1) + 0.25 * (N[:, 2] > 0.3) - 0.7 * np.clip((0.35 - z) / 0.35, 0, 1), 0, 1), B)
            G = np.where(ft, np.clip(0.75 * (N[:, 2] > 0.5) * np.clip(0.3 + n3 + 0.5 * n2, 0, 1) + 0.8 * np.clip((0.22 - z) / 0.22, 0, 1) * np.clip(0.5 + n, 0, 1) + 0.35 * np.clip(N[:, 1], 0, 1) * np.clip(n3, 0, 1), 0, 1), G)
        rope = tags == TAG_ROPE
        R = np.where(rope, 0.55 + 0.2 * n2, R); G = np.where(rope, 0.0, G); B = np.where(rope, 0.1, B)
        A = np.where(tags == TAG_IRON, 0.5, A); A = np.where(tags == TAG_LEAD, 0.75, A); A = np.where(tags == TAG_GLASS, 0.0, A)
        blk = tags == TAG_GLASS + 30                    # unlit void (room behind the door, flue, well shaft)
        A = np.where(blk, 0.5, A); R = np.where(blk, 1.0, R)
        return np.stack([R, G, B, A], -1)
    return f


# ---------------------------------------------------------------- fence
def split_rail(m, p0, p1, rad=0.05, slot=1):
    """a cleft rail: wedge section, a little crooked, thicker at the butt"""
    r = m.rng; p0 = np.array(p0, float); p1 = np.array(p1, float); n = 7
    d = p1 - p0; L = np.linalg.norm(d); side = np.cross(d / L, [0, 0, 1.0])
    pts = []; kx = r.normal(); kz = r.normal(); kf = r.uniform(1, 2.2); kp = r.uniform(0, 3)
    for i in range(n):
        t = i / (n - 1)
        pts.append(p0 + d * t + side * (r.normal(0, 0.008) + 0.02 * math.sin(math.pi * t) * kx) + np.array([0, 0, 0.018 * math.sin(math.pi * t * kf + kp) * kz + r.normal(0, 0.005)]))
    radii = [rad * (1.12 - 0.25 * i / (n - 1)) * (1 + r.normal(0, 0.05)) for i in range(n)]
    shape = np.array([1.0, 0.72, 0.5, 0.78, 1.05, 0.9]) * (1 + r.normal(0, 0.07, 6))
    m.tube(pts, radii, slot, sides=6, tag=TAG_TIMBER, shape=shape, rough=0.05, smooth=False, twist=float(r.normal(0, 0.25)))


def post(m, x, y, h, rad=0.075, slot=1, lean=None):
    r = m.rng; lean = r.normal(0, 0.012, 2) if lean is None else lean
    zs = [-0.02, 0.12, h * 0.5, h - 0.06, h]
    pts = [[x + lean[0] * z_, y + lean[1] * z_, z_] for z_ in zs]
    radii = [rad * 1.12, rad * 1.05, rad, rad * 0.93, rad * 0.6]
    shape = np.array([1.0, 0.85, 1.0, 0.8, 1.05, 0.9, 0.95]) * (1 + r.normal(0, 0.06, 7))
    m.tube(pts, radii, slot, sides=7, tag=TAG_TIMBER, shape=shape, rough=0.04, smooth=False)
    return lean


def lashing(m, c, axis_r, turns=3.2, r_loop=0.1, slot=2):
    """rope whipped round a post and rail: a helix of thin rope"""
    r = m.rng; n = int(turns * 9); pts = []
    for i in range(n + 1):
        a = 2 * math.pi * turns * i / n
        pts.append([c[0] + r_loop * math.cos(a) * 1.15, c[1] + r_loop * math.sin(a) * 1.5, c[2] - 0.035 + 0.07 * i / n + 0.012 * math.sin(a * 2)])
    m.tube(pts, 0.009, slot, sides=4, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))


def packing(m, x, y, slot=0, k=3):
    r = m.rng
    for i in range(k):
        a = r.uniform(0, 6.28); d = r.uniform(0.09, 0.16); s = r.uniform(0.09, 0.17)
        m.rock([x + d * math.cos(a), y + d * math.sin(a), s * 0.18], [s * 1.3, s, s * 0.7], slot, T_STONE * 0.5, sub=2, tag=TAG_STONE, lump=0.18, smooth=True)


def fence_run(m, L=4.0, posts=3, broken=False):
    r = m.rng
    xs = np.linspace(-L / 2, L / 2, posts)
    hs = [1.18 + r.normal(0, 0.05) for _ in xs]; hs[1] += 0.2
    leans = [post(m, x, 0.0, h) for x, h in zip(xs, hs)]
    for zr_ in (0.48, 0.95):
        for k in range(posts - 1):
            sd = -1 if (k + (zr_ > 0.6)) % 2 == 0 else 1
            a = [xs[k] - 0.07 if k == 0 else xs[k] - 0.14, sd * 0.085, zr_ + r.normal(0, 0.025)]; b = [xs[k + 1] + (0.07 if k == posts - 2 else 0.14), sd * 0.085, zr_ + r.normal(0, 0.025)]
            if broken and zr_ > 0.6 and k == 1:              # top rail of the second bay snapped: a stub on the post, the rest fallen with one end on the ground
                split_rail(m, a, [a[0] + 0.55, a[1], a[2] - 0.03], rad=0.05)
                split_rail(m, [a[0] + 0.75, a[1] - 0.25, 0.06], [b[0], b[1], b[2] - 0.02], rad=0.048)
                continue
            if broken and zr_ < 0.6 and k == 0:              # lower rail of the first bay slipped out of its lashing at one end
                a[2] = 0.07; a[1] -= 0.12
            split_rail(m, a, b)
        for k, x in enumerate(xs):
            lashing(m, [x, 0.0, zr_], None)
    for x in xs:
        packing(m, x, 0.0)
    m.ucx = [([-L / 2 - 0.08, -0.09, 0], [L / 2 + 0.08, 0.09, 1.1])]


def gate(m, W=2.4):
    """five-bar field gate: cleft bars mortised into a hanging stile and a slimmer head stile, diagonal brace, strap hinges.
    Pivot on the hinge line."""
    r = m.rng
    timber(m, [0.0, -0.045, 0.06], [0.11, 0.045, 1.32], 0.012, 0.004); timber(m, [W - 0.08, -0.035, 0.1], [W, 0.035, 1.22], 0.01, 0.004)
    for k, zz in enumerate((0.16, 0.36, 0.58, 0.83, 1.12)):
        split_rail(m, [0.05, r.normal(0, 0.004), zz], [W - 0.03, r.normal(0, 0.004), zz + r.normal(0, 0.01)], rad=0.043)
        peg(m, 0.055, -0.045, zz, 0.01); peg(m, W - 0.04, -0.035, zz, 0.009)
    split_rail(m, [0.08, -0.05, 0.14], [W - 0.1, -0.05, 1.12], rad=0.04)
    timber(m, [W * 0.5 - 0.04, -0.075, 0.12], [W * 0.5 + 0.04, -0.035, 1.16], 0.008, 0.003)
    for zz in (0.3, 1.1):
        m.block([-0.02, -0.058, zz - 0.02], [0.5, -0.045, zz + 0.02], SO, T_TIMBER, 0.003, 0.0006, tag=TAG_IRON)
        m.tube([[0.0, -0.05, zz - 0.05], [0.0, -0.05, zz + 0.05]], 0.016, SO, sides=6, tag=TAG_IRON, smooth=False)
    m.block([W - 0.1, -0.05, 0.74], [W + 0.06, -0.038, 0.78], SO, T_TIMBER, 0.003, 0.0006, tag=TAG_IRON)            # latch bar
    V = np.array(m.V); m.V = (V + np.array([-V[:, 0].min(), -(V[:, 1].min() + V[:, 1].max()) / 2, -V[:, 2].min()])).tolist()
    m.ucx = [([0, -0.06, 0], [W, 0.06, 1.26])]


def gate_post(m):
    lean = post(m, 0.0, 0.0, 1.55, rad=0.1)
    packing(m, 0.0, 0.0, k=4)
    for zz in (0.42, 1.22):                                 # hinge pins
        m.tube([[0.06, -0.02, zz], [0.15, -0.02, zz]], 0.014, SO, sides=6, tag=TAG_IRON, smooth=False)
        m.tube([[0.14, -0.02, zz - 0.012], [0.14, -0.02, zz + 0.07]], 0.013, SO, sides=6, tag=TAG_IRON, smooth=False)
    m.ucx = [([-0.1, -0.1, 0], [0.1, 0.1, 1.5])]


# ---------------------------------------------------------------- well
def ring(m, r0, r1, z0, z1, n, slot, tile, tag=0, r0b=None, r1b=None):
    """closed annulus (hollow cylinder wall); r0b/r1b: radii at the top for a taper"""
    r0b = r0 if r0b is None else r0b; r1b = r1 if r1b is None else r1b
    V = []
    for k in range(n):
        a = 2 * math.pi * k / n; c, s = math.cos(a), math.sin(a)
        V += [[r0 * c, r0 * s, z0], [r1 * c, r1 * s, z0], [r1b * c, r1b * s, z1], [r0b * c, r0b * s, z1]]
    F = []
    for k in range(n):
        a = 4 * k; b = 4 * ((k + 1) % n)
        F += [[a + 1, b + 1, b + 2, a + 2], [a + 3, b + 3, b + 0, a + 0], [a + 2, b + 2, b + 3, a + 3], [a + 0, b + 0, b + 1, a + 1]]
    m.add(V, F, slot, tile, tag=tag, smooth=True)


def well(m):
    """stone-lined well: four courses of field stones round a 1.0 m shaft, capstones, oak posts and windlass with rope and bucket,
    a little shingled roof (sprite family 186 frames 1-3)"""
    r = m.rng; RI, RO = 0.52, 0.86
    ring(m, RI, RO - 0.07, -3.7, 0.8, 20, 0, T_STONE)                    # mortared core and the shaft lining, 3.7 m down
    m.tube([[0, 0, -3.7], [0, 0, -3.45]], RI + 0.02, SO, sides=20, tag=TAG_GLASS, smooth=False)          # still dark water: the glint at the bottom
    m.zbase = 0.0
    z = 0.0
    for c in range(4):
        n = 11 + (c % 2); h = 0.2 + r.normal(0, 0.012)
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * (c % 2) + r.normal(0, 0.05)) / n
            sz = [2 * math.pi * RO / n * float(r.uniform(0.86, 1.0)), float(r.uniform(0.3, 0.38)), h * float(r.uniform(0.95, 1.12))]
            n0 = len(m.V)
            m.rock([0, 0, 0], sz, 0, T_STONE * 0.5, sub=3, tag=TAG_STONE if r.uniform() < 0.3 else TAG_SHEET, lump=0.13)
            m.xform_since(n0, np.array(Matrix.Translation(((RO - 0.14 + r.normal(0, 0.012)) * math.cos(a), (RO - 0.14) * math.sin(a), z + h / 2 + 0.01)) @ Matrix.Rotation(a + math.pi / 2 + r.normal(0, 0.06), 4, 'Z')))
        z += h
    n = 9                                                             # flat capstones
    for k in range(n):
        a = 2 * math.pi * (k + r.normal(0, 0.04)) / n
        n0 = len(m.V)
        m.block([-2 * math.pi * 0.72 / n / 2 + 0.012, -0.21, 0.0], [2 * math.pi * 0.72 / n / 2 - 0.012, 0.21, 0.085 + r.normal(0, 0.008)], 0, T_STONE * 0.5, 0.022, 0.008, tag=TAG_STONE)
        m.xform_since(n0, np.array(Matrix.Translation((0.7 * math.cos(a), 0.7 * math.sin(a), z + 0.0)) @ Matrix.Rotation(a + math.pi / 2, 4, 'Z')))
    ztop = z + 0.085
    # frame: two posts outside the wall, braces, the roof tree
    px = RO + 0.12; ph = 2.25
    for sx in (-1, 1):
        timber(m, [sx * px - 0.075, -0.075, 0.0], [sx * px + 0.075, 0.075, ph], 0.018, 0.006)
        bar(m, [sx * (px - 0.02), ph - 0.62], [sx * (px - 0.55), ph - 0.06], 0.085, -0.035, 0.035, slot=SO)
        peg(m, sx * (px - 0.1), -0.035, ph - 0.5); packing(m, sx * px, 0.0, slot=0)
    timber(m, [-px - 0.2, -0.07, ph], [px + 0.2, 0.07, ph + 0.14], 0.016, 0.005)                        # tie
    # windlass: an oak drum on iron gudgeons, a cranked handle, rope wound on the drum
    zw = 1.5
    m.tube([[-px + 0.07, 0, zw], [px - 0.07, 0, zw]], 0.075, SO, sides=10, tag=TAG_TIMBER, smooth=True, rough=0.02)
    m.tube([[-px - 0.1, 0, zw], [-px + 0.1, 0, zw]], 0.016, SO, sides=6, tag=TAG_IRON, smooth=False)
    m.tube([[px - 0.1, 0, zw], [px + 0.16, 0, zw], [px + 0.16, 0.0, zw - 0.26], [px + 0.4, 0.0, zw - 0.26]], 0.014, SO, sides=6, tag=TAG_IRON, smooth=False)
    coil = []
    for i in range(61):
        a = 2 * math.pi * 7.5 * i / 60
        coil.append([-0.22 + 0.44 * i / 60, 0.088 * math.cos(a), zw + 0.088 * math.sin(a)])
    m.tube(coil, 0.011, 2, sides=4, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))
    bx, by = 0.3, -0.69                                               # bucket standing on the capstones, rope down to its bail
    m.tube([coil[-1], [0.24, -0.1, zw - 0.2], [0.27, -0.42, ztop + 0.55], [bx, by, ztop + 0.36]], 0.011, 2, sides=4, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))
    n0 = len(m.V)
    ring(m, 0.105, 0.125, 0.0, 0.27, 12, SO, T_TIMBER, tag=TAG_TIMBER, r0b=0.135, r1b=0.155)             # staved bucket
    m.tube([[0, 0, 0.0], [0, 0, 0.03]], 0.115, SO, sides=12, tag=TAG_TIMBER, smooth=False)
    m.tube([[0, 0, 0.16], [0, 0, 0.175]], 0.12, SO, sides=12, tag=TAG_GLASS + 30, smooth=False)          # water in it
    for zz, rr in ((0.05, 0.132), (0.21, 0.152)):
        ring(m, rr - 0.004, rr + 0.004, zz, zz + 0.022, 12, SO, T_TIMBER, tag=TAG_IRON)
    bail = [[0.15 * math.cos(a), 0, 0.26 + 0.11 * math.sin(a)] for a in np.linspace(0, math.pi, 8)]
    m.tube(bail, 0.006, SO, sides=5, tag=TAG_IRON, smooth=False)
    m.xform_since(n0, np.array(Matrix.Translation((bx, by, ztop)) @ Matrix.Rotation(0.5, 4, 'Z')))
    # roof: two slopes of cleft oak shingles on rafters and battens, ridge board
    pit = math.radians(40); S = 0.98; half = 1.3; zr_ = ph + 0.14 + 0.62
    for sg in (-1, 1):
        def wpt(a, s, h, sg=sg):
            return [a, sg * ((S - s) * math.cos(pit) + h * math.sin(pit)), zr_ - (S - s) * math.sin(pit) + h * math.cos(pit)]
        uo = r.uniform(0, 1, 2)
        roof_slab(m, -half, half, wpt, S, slot=SO, expo=0.19, half=0.12, thick=0.03, defects=True, tile=T_TIMBER, tag=TAG_TIMBER, st=0.02,
                  uvfn=lambda P, sg=sg: np.stack([(zr_ - P[:, 2]) / math.sin(pit) / T_TIMBER + uo[0], P[:, 0] / T_TIMBER * 1.0 + uo[1]], -1))
        for a in (-1.0, 0.0, 1.0):                               # rafters
            p0 = np.array(wpt(a, 0.02, -0.075)); p1 = np.array(wpt(a, S - 0.02, -0.075))
            m.tube([p0, p1], 0.04, SO, sides=4, tag=TAG_TIMBER, smooth=False, shape=[1.2, 1, 1.2, 1])
        for s in (0.15, 0.5, 0.85):                               # battens
            m.tube([wpt(-half + 0.03, s, -0.035), wpt(half - 0.03, s, -0.035)], 0.018, SO, sides=4, tag=TAG_TIMBER, smooth=False)
    timber(m, [-half - 0.02, -0.02, zr_ - 0.16], [half + 0.02, 0.02, zr_ + 0.035], 0.008, 0.003)          # ridge board standing proud
    for sx in (-1, 1):                                           # king posts on the tie
        timber(m, [sx * 1.0 - 0.04, -0.04, ph + 0.14], [sx * 1.0 + 0.04, 0.04, zr_ - 0.1], 0.008, 0.003)
    m.well = (RI, RO, ztop, bx, by)
    m.ucx = [([-RO, -RO, 0], [RO, RO, ztop]), ([-px - 0.08, -0.08, 0], [-px + 0.08, 0.08, ph]), ([px - 0.08, -0.08, 0], [px + 0.08, 0.08, ph])]
    m.hulls = [[[-half, -0.8, ph + 0.1], [half, -0.8, ph + 0.1], [half, 0.8, ph + 0.1], [-half, 0.8, ph + 0.1], [-half, 0, zr_ + 0.03], [half, 0, zr_ + 0.03]]]


def boulder(m, size, seed, sub=5, extra=()):
    r = np.random.default_rng(seed)
    m.rock([0, 0, size[2] * 0.36], size, 0, T_BOULDER, seed=seed, sub=sub, tag=TAG_SHEET, flat=0.28, lump=0.26, facets=10, crease=0.09)
    for (dx, dy, s) in extra:
        m.rock([dx, dy, s[2] * 0.3], s, 0, T_BOULDER, seed=seed + 7 + int(dx * 10), sub=4, tag=TAG_SHEET, flat=0.3, lump=0.26, facets=8, crease=0.09)
    V = np.array(m.V); V[:, 2] -= V[:, 2].min(); cxy = (V[:, :2].min(0) + V[:, :2].max(0)) / 2; V[:, :2] -= cxy
    # fine surface break-up so the silhouette is not a smooth blob
    V += 0.012 * np.stack([vnoise(V, seed + 20, 9.0), vnoise(V, seed + 21, 9.0), vnoise(V, seed + 22, 9.0)], -1) * (V[:, 2:3] > 0.02)
    m.V = V.tolist()
    m.hulls = [V[:: max(1, len(V) // 20)].tolist() + [V[V[:, k].argmin()].tolist() for k in range(3)] + [V[V[:, k].argmax()].tolist() for k in range(3)]]


def sb_modules(rows):
    out = []

    def mk(name, L, H, cls, slots, kind):
        m = Mod2(name, L, H, rows, cls, 'Structures/Stonebrook'); m.slots = list(slots); m.streak_src = []; m.streak_w = []; m.dormer_box = None
        m.floor0 = True; m.paint.append(sb_paint(m, kind)); return m

    def rec(m, fams, sup, note, **k):
        used = sorted(set(m.FM)); m.FM = [used.index(i) for i in m.FM]; m.slots = [m.slots[i] for i in used]
        out.append(dict(m=m, families=fams, supersedes=sup, dresses=note, **k))
    m = mk('SM_Cottage_Stonebrook_PR', CW, 7.9, 'building', ('fieldstone', 'oak', 'thatch', 'door', 'earth'), 'cottage'); cottage(m)
    rec(m, ['63 struct/home/home-', 'cottage_thatched_long', 'cottage_thatched_large'], 'StonebrookExterior/SM_Cottage_Stonebrook_01',
        'long fieldstone cottage under a hipped thatch (as sprite 63 frames 1 and 6): 18 x 9 m at the walls, 2.9 m walls 0.5 m thick with quoins and half-buried footing stones, oak lintels, four leaded windows with board shutters on the front, three on the back, one in each end; doorway 1.5 x 2.5 m; rafter-pole feet under 0.4 m thick eaves; block-cut ridge with hazel liggers and crossed spars; stone chimney through the west hip',
        fit={'pivot': 'ground centre of the 18 x 9 m wall rectangle (same as the superseded mesh); front faces -Y in Blender (+Y in Unreal after the usual front flip)',
             'door': 'opening centre at x = +5.30 m on the front wall (y = -4.5 m), 1.5 m wide, 2.5 m high: cottage_door_local_cm [530, 450, 0] of the old manifest still holds',
             'footprint': 'walls 18.0 x 9.0 m; thatch eaves oversail by 0.5 m (19.0 x 10.0 m); the old mesh was 18.83 x 10.55 m with a gabled roof, this one is hipped as the sprite',
             'height': 'ridge 7.3 m, chimney top about 7.9 m (old mesh 7.93 m)'})
    m = mk('SM_Cottage_Stonebrook_PR_Burnt', CW, 7.9, 'building', ('fieldstone', 'oak', 'thatch', 'door', 'earth'), 'cottage'); cottage(m, burnt=True)
    rec(m, ['screen 439 burnt state (vision 2) of 63 struct/home/home-'], 'reference only: StonebrookRuins/SM_Cottage_Stonebrook_Burnt_01 (Codex candidate, same 18 x 9 m walls and collision envelope)',
        'the Stonebrook cottage after the fire, same walls, pivot, doorway and collision as SM_Cottage_Stonebrook_PR: stone smoke-blackened above every opening and under the lost roof, window glass gone, lintels, frames and shutters charred; the west third of the thatch still hangs on, scorched and burnt back in a ragged line; beyond it charred rafter couples (some snapped), a broken ridge pole, a few laths, fallen timbers, heaps of burnt thatch and ash inside and spilled outside, the door burnt and fallen flat in front of the doorway, scorched earth at the wall foot',
        fit={'pivot': 'as SM_Cottage_Stonebrook_PR: swap in place for vision 2', 'collision': 'the same wall hulls with the doorway open; no roof hull (the roof is gone)', 'effects': 'no embers, smoke or fire here: those are emitters; Codex\'s remains and scorch decals (StonebrookRuins) are separate assets and still apply'})
    for (nm, W_, D_, kw, fam, fr) in (('Small', 7.0, 5.5, dict(fw=(1.8, 5.2), fw2=(), bw=(3.5,), ew=(2.25,), patches=((-1.5, -2.2, 1.0, 0.8),)), ['cottage_thatched_small'], 'frames 7, 8 (257x225 px)'),
                                      ('Large', 10.0, 6.5, dict(fw=(2.0, 5.0, 8.0), fw2=(), bw=(3.0, 7.0), ew=(2.75,), patches=((-2.5, -2.4, 1.2, 0.9), (3.0, 2.2, 1.0, 0.8))), ['cottage_thatched_large', 'cottage_thatched_long'], 'frames 6 (334x259 px) and 1 (332x260 px)')):
        m = mk('SM_Cottage_Thatched_%s_PR' % nm, W_, 7.0, 'building', ('fieldstone', 'oak', 'thatch', 'door', 'earth'), 'cottage'); cottage(m, W_, D_, None, **kw)
        rec(m, fam, 'none (family 63 had no final art away from screen 439)', 'fieldstone cottage under a hipped thatch, %.1f x %.1f m at the walls, built by the same generator as SM_Cottage_Stonebrook_PR (same walls, quoins, footing stones, shuttered leaded windows, rafter-pole feet, block ridge with liggers, chimney); no doorway is cut: the original places the door as its own sprite (cottage_door), so stand SM_Cottage_Door_PR against the wall where that sprite is' % (W_, D_),
            sprite_family='63 struct/home/home-', sprite_frames=fr, fit={'pivot': 'ground centre of the wall rectangle; front -Y', 'footprint': 'walls %.1f x %.1f m, eaves oversail 0.5 m' % (W_, D_), 'not_covered': 'two-storey (frames 4, 5) and L-shaped (frame 10) cottages and the separate chimney sprites (frames 11-13) are not built'})
    m = mk('SM_Cottage_Door_PR', 1.44, 2.46, 'door', ('door',), 'door'); door_leaf(m, 1.44, 2.46); m.ucx = [([0, -0.03, 0], [1.44, 0.03, 2.46])]
    rec(m, ['cottage_door', '63 struct/home/home- frames 2, 3'], 'none (the old cottage had an empty doorway)', 'ledged oak plank door for the cottage doorway, 1.44 x 2.46 m, strap hinges, studs, ring pull. Hinge pivot: hang at x = +4.58 m on the front wall, 0.2 m behind its face; the sprite shows it standing open')
    m = mk('SM_Fence_SplitRail_4m_PR', 4.0, 1.4, 'prop_large', ('fieldstone', 'oak', 'rope'), 'fence'); fence_run(m)
    rec(m, ['93 lands/fence/fence-', 'fence_rail_ew', 'fence_rail_ns', 'fence_rail_diag_nw', 'fence_rail_diag_ne'], 'StonebrookExterior/SM_Fence_SplitRail_4m_01',
        '4 m run of post-and-rail fence as sprite 93: three cleft oak posts with packing stones at the foot, two tiers of cleft wedge-section rails lapped past the posts and lashed with rope',
        fit={'pivot': 'ground centre, run along X (same as the superseded mesh, 4.18 x 0.19 x 1.44 m); yaw for the n-s and diagonal frames', 'ends': 'end posts stand at x = -2.0 and +2.0: consecutive runs share a post position, so overlap them by one post or accept a doubled post'})
    m = mk('SM_Fence_SplitRail_4m_Broken_PR', 4.0, 1.4, 'prop_large', ('fieldstone', 'oak', 'rope'), 'fence'); fence_run(m, broken=True)
    rec(m, ['93 lands/fence/fence- (variant)'], 'none (variant of SM_Fence_SplitRail_4m_PR)', 'the same 4 m run in disrepair: the top rail of one bay snapped with its long end on the ground, a lower rail slipped from its lashing. List as a variant in families.json so some runs are broken',
        fit={'pivot': 'as SM_Fence_SplitRail_4m_PR'})
    m = mk('SM_Fence_Gate_PR', 2.4, 1.3, 'door', ('fieldstone', 'oak', 'rope'), 'fence'); gate(m)
    rec(m, [], 'none (new: the 4 m gateway of exterior_layout.json had no gate)', 'five-bar cleft oak field gate, 2.4 m, diagonal brace, iron strap hinges and latch. Hinge pivot; hangs on SM_Fence_GatePost_PR')
    m = mk('SM_Fence_GatePost_PR', 0.3, 1.55, 'prop', ('fieldstone', 'oak', 'rope'), 'fence'); gate_post(m)
    rec(m, [], 'none (new)', 'heavy cleft oak gate post, 1.55 m, with two iron hinge pins and packing stones; also the latch post')
    m = mk('SM_Well_Stone_PR', 2.3, 3.0, 'prop_large', ('fieldstone', 'oak', 'rope'), 'well'); m.floor0 = False; well(m)
    rec(m, ['well_stone', '186 struct/landmark/landm- frames 1-3'], 'none in StonebrookExterior (the brief names a well, but its manifest has none); dresses class well_stone',
        'stone-lined well: 1.04 m shaft, four courses of individual field stones and nine capstones (wall 0.9 m high, 1.7 m across), oak posts with braces, windlass drum with iron crank and wound rope, staved bucket on the rim, shingled roof on rafters and battens',
        fit={'pivot': 'ground centre of the shaft (the mesh goes 3.7 m below it)', 'size': '2.6 x 1.7 x 3.0 m above ground; the sprite card (107 x 136 px) is 2.7 x 3.4 m at 0.025 m/px', 'shaft': 'REAL shaft: lining to -3.7 m with dark water at -3.45 m. The ground under the well needs a hole of 0.52 m radius (ground-chunk cut or landscape visibility mask); where that cannot be done, add SM_Well_ShaftCap_PR at the same pivot, which closes the shaft with an unlit black disc at ground level'})
    m = mk('SM_Well_ShaftCap_PR', 1.1, 0.05, 'prop', ('fieldstone', 'oak', 'rope'), 'well'); m.well = (0.52, 0.86, 0.9, 0.3, -0.69)
    m.tube([[0, 0, 0.0], [0, 0, 0.03]], 0.53, SO, sides=20, tag=TAG_GLASS + 30, smooth=False); m.ucx = [([-0.5, -0.5, 0], [0.5, 0.5, 0.03])]
    rec(m, [], 'none', 'fallback for SM_Well_Stone_PR where the ground cannot be cut: an unlit black disc, 1.06 m across, at ground level inside the well wall')
    return out


def main_sb():
    sc = new_scene()
    rows = board_rows('OakWeathered')
    oak = wmat('MI_Struct_OakWeathered', 'OakWeathered', dirt=(0.22, 0.16, 0.11), pale=(0.46, 0.45, 0.42), pale_amt=0.55, special=True, tint=(0.80, 0.62, 0.47, 1))
    mats = {'fieldstone': wmat('MI_Struct_Fieldstone', 'Fieldstone', dirt=(0.36, 0.30, 0.22), pale=(0.62, 0.60, 0.52), pale_amt=0.5, soot=True),
            'earth': wmat('MI_Struct_Earth', 'EarthPath', tint=(0.62, 0.56, 0.50, 1), dirt=(0.36, 0.30, 0.24), pale=(0.80, 0.79, 0.77), pale_amt=0.85, moss=(0.045, 0.075, 0.02), moss_rough=0.9, soot=True),
            'thatch': wmat('MI_Struct_Thatch', 'Thatch', lead=False, dirt=(0.105, 0.095, 0.08), pale=(0.80, 0.63, 0.33), pale_amt=0.6, dirt_amt=0.95, dirt_mix=True, moss=(0.05, 0.062, 0.02), special=True),
            'oak': oak,
            'door': wmat('MI_Town_DoorPlanks', 'DoorPlanks', dirt=(0.3, 0.25, 0.2), special=True),
            'rope': wmat('MI_Struct_Rope', 'Thatch', dirt=(0.5, 0.45, 0.38), pale=(0.7, 0.62, 0.45), pale_amt=0.4, tint=(0.9, 0.85, 0.8, 1)),
            'boulder': wmat('MI_Struct_FieldBoulder', 'FieldBoulder', dirt=(0.34, 0.27, 0.18), pale=(0.66, 0.66, 0.58), pale_amt=0.5, moss=(0.045, 0.06, 0.02))}
    recs = export_modules(sb_modules(rows), mats, OUT, 'Stonebrook.blend')
    json.dump(recs, open(os.path.join(OUT, 'modules.json'), 'w'), indent=1)
    print('STONEBROOK DONE', len(recs))


main_sb()
