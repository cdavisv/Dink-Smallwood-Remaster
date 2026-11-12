"""Castle kit for sprite family 67 struct/castle/castl-: curtain wall, wall end, round tower, gatehouse.
blender -b -t 4 --python castle_build.py
Class building (the pieces are 9-12 m tall): pivot at the ground centre of the footprint, outer (field) face toward -Y."""
import bpy, os, sys, json, math
import numpy as np
from mathutils import Matrix
_T = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'TownExteriors', 'tools', 'town_build2.py')
_s = open(_T).read()
exec(_s[:_s.index('\ndef modules(rows):')])
OUT = os.path.join(os.environ['DINK_PP'], 'Structures', 'Castle')
os.makedirs(OUT, exist_ok=True)
T_ASH = 3.3                              # the 1.8 m scan laid 1.83x larger: its 0.3 m blocks become the sprite's 0.55 m courses
SA, SO = 0, 1
TAG_WALK, TAG_VOID = 40, TAG_GLASS + 30
WT_C = 1.8; WALK = 7.0


def ash(m, lo, hi, bevel=0.022, jitter=0.006, tag=TAG_STONE, rot=None):
    m.block(lo, hi, SA, T_ASH * 0.85, bevel, jitter, tag=tag, rot=rot)


def course(m, x0, x1, y0, y1, z0, z1, lmin=0.5, lmax=0.95, tag=TAG_STONE, bevel=0.022, skip=None, dy=0.008):
    """a row of individually cut blocks from x0 to x1"""
    r = m.rng; x = x0
    while x < x1 - 1e-6:
        l = min(float(r.uniform(lmin, lmax)), x1 - x)
        if x1 - (x + l) < lmin * 0.5:
            l = x1 - x
        if skip is None or not skip(x + l / 2):
            ash(m, [x + 0.005, y0 + r.normal(0, dy), z0 + 0.004], [x + l - 0.005, y1 + r.normal(0, dy * 0.3), z1 - 0.004 + r.normal(0, 0.004)], bevel, tag=tag)
        x += l


def face_relief(m, x0, x1, z0, z1, yf, n, putlog=(2.45, 4.9)):
    """break the flat wall sheet: single blocks standing 2-5 cm proud or set back, on the 0.55 m coursing, and two rows of putlog
    holes (the builders' scaffold sockets). yf is the face (looking -Y)."""
    r = m.rng; ch = 0.55
    for _ in range(n):
        k = int(r.integers(1, max(2, int((z1 - z0) / ch) - 1))); l = float(r.uniform(0.45, 0.85)); x = float(r.uniform(x0 + 0.1, x1 - l - 0.1)); pr = float(r.uniform(0.012, 0.035))
        zz = z0 + k * ch + r.normal(0, 0.01)
        ash(m, [x, yf - pr, zz + 0.012], [x + l, yf + 0.06, zz + ch * (0.5 if r.uniform() < 0.5 else 1.0) - 0.012], 0.03, 0.008, tag=TAG_STONE if r.uniform() < 0.6 else TAG_STONE + 50)
    for zp in putlog:
        if z0 < zp < z1 - 0.5:
            x = x0 + float(r.uniform(0.6, 1.4))
            while x < x1 - 0.5:
                m.block([x - 0.07, yf - 0.004, zp - 0.075], [x + 0.07, yf + 0.25, zp + 0.075], SO, T_TIMBER, 0.0, 0.0, tag=TAG_VOID)
                ash(m, [x - 0.2, yf - 0.02, zp + 0.075], [x + 0.2, yf + 0.1, zp + 0.2], 0.02, tag=TAG_STONE + 50)        # its little lintel stone
                m.streak_src.append((x, yf, zp - 0.07, 0.18, 0.45))
                x += float(r.uniform(1.9, 2.5))


def parapet(m, x0, x1, yo, z0, thick=0.45, merlons=None, breast=0.9, mh=1.1):
    """crenellated parapet along X with its outer face at yo (looking -Y): two breast courses, merlons of three courses, coping"""
    r = m.rng
    course(m, x0, x1, yo, yo + thick, z0, z0 + breast / 2); course(m, x0, x1, yo + 0.005, yo + thick, z0 + breast / 2, z0 + breast, 0.45, 0.8)
    for (a, b) in merlons:
        ch = mh / 3
        for k in range(3):
            course(m, a, b, yo - 0.004, yo + thick, z0 + breast + k * ch, z0 + breast + (k + 1) * ch, 0.4, 0.75)
        ash(m, [a - 0.03, yo - 0.04, z0 + breast + mh], [b + 0.03, yo + thick + 0.04, z0 + breast + mh + 0.11], 0.03, tag=TAG_STONE + 50)     # coping
    xs = sorted([x0] + [v for ab in merlons for v in ab] + [x1])
    for a, b in zip(xs[::2], xs[1::2]):                # embrasure sills, weathered outward
        if b - a > 0.05:
            ash(m, [a + 0.01, yo - 0.05, z0 + breast], [b - 0.01, yo + thick + 0.02, z0 + breast + 0.07], 0.02, tag=TAG_STONE + 50)
            m.streak_src.append(((a + b) / 2, yo, z0 + breast, (b - a) / 2 + 0.15, 0.9))


def wall(m, L, end=None):
    r = m.rng; hx = L / 2; y = WT_C / 2
    m.slab(-hx, hx, 0.0, WALK, -y, y, SA, T_ASH, nx=max(2, int(L / 0.25)), nz=28, relief=0.02)
    for (ya, yb, sgn) in ((-y - 0.16, -y + 0.05, -1), (y - 0.05, y + 0.16, 1)):                  # two offset plinth courses each side
        course(m, -hx, hx, ya, yb, 0.0, 0.34, 0.6, 1.1, bevel=0.03)
        course(m, -hx, hx, ya + (0.08 if sgn < 0 else 0), yb - (0.08 if sgn > 0 else 0), 0.34, 0.6, 0.5, 0.9, bevel=0.035)
    # corbelled wall-walk: the parapet oversails the wall face on a table of two-stepped corbels
    x = -hx + 0.3
    while x < hx - 0.1:
        ash(m, [x - 0.14, -y - 0.13, WALK - 0.5], [x + 0.14, -y + 0.1, WALK - 0.28], 0.025, tag=TAG_STONE + 50)
        ash(m, [x - 0.14, -y - 0.27, WALK - 0.28], [x + 0.14, -y + 0.1, WALK - 0.06], 0.025, tag=TAG_STONE + 50)
        x += 0.6
    course(m, -hx, hx, -y - 0.3, -y + 0.42, WALK - 0.07, WALK + 0.03, 0.7, 1.1, tag=TAG_WALK, bevel=0.015)      # the oversailing course they carry
    mer = []; c = -hx + 1.0
    while c + 0.65 <= hx + 1e-6:
        mer.append((c - 0.65, c + 0.65)); c += 2.0
    if not mer:
        mer = [(-0.65, 0.65)]
    parapet(m, -hx, hx, -y - 0.29, WALK + 0.02, merlons=mer)
    face_relief(m, -hx, hx, 0.6, WALK - 0.6, -y, int(L * 3.5))
    n0 = len(m.V); s0 = len(m.streak_src); face_relief(m, -hx, hx, 0.6, WALK - 0.2, -y, int(L * 3), putlog=()); m.xform_since(n0, np.array(Matrix.Rotation(math.pi, 4, 'Z'))); del m.streak_src[s0:]
    course(m, -hx, hx, y - 0.34, y + 0.02, WALK - 0.06, WALK + 0.42, 0.5, 0.9)                 # inner kerb
    # wall-walk paving
    x = -hx
    while x < hx - 1e-6:
        l = min(float(r.uniform(0.7, 1.1)), hx - x)
        if hx - (x + l) < 0.35:
            l = hx - x
        cut = float(r.uniform(-0.25, 0.25))
        ash(m, [x + 0.006, -y + 0.42, WALK - 0.07], [x + l - 0.006, cut - 0.006, WALK + 0.02 + r.normal(0, 0.004)], 0.012, tag=TAG_WALK)
        ash(m, [x + 0.006, cut + 0.006, WALK - 0.07], [x + l - 0.006, y - 0.33, WALK + 0.02 + r.normal(0, 0.004)], 0.012, tag=TAG_WALK)
        x += l
    # two stone water spouts through the parapet foot
    for sx in ((-2.0, 2.0) if L >= 7.5 else (0.95,)):
        ash(m, [sx - 0.09, -y - 0.62, WALK + 0.0], [sx + 0.09, -y + 0.1, WALK + 0.13], 0.02, tag=TAG_STONE + 50)
        m.streak_src.append((sx, -y - 0.3, WALK - 0.04, 0.3, 1.0))
    if end is not None:                                                 # dressed quoins on a free end
        z = 0.6; i = 0
        while z < WALK - 0.35:
            h = float(r.uniform(0.3, 0.42)); la = 0.7 if i % 2 == 0 else 0.42
            ash(m, [end * hx - (la if end > 0 else -0.04), -y - 0.035, z], [end * hx + (0.04 if end > 0 else la), y + 0.035, z + h - 0.01], 0.028, tag=TAG_STONE + 50)
            z += h; i += 1
    m.ucx = [([-hx, -y, 0], [hx, y, WALK]), ([-hx, -y - 0.29, WALK], [hx, -y + 0.16, WALK + 0.9])]


def corner(m, A=4.0):
    """outer corner of two curtain walls (frame 8): two arms with the field faces toward -Y and -X, dressed quoins at the angle"""
    y = WT_C / 2
    n0 = len(m.V); s0 = len(m.streak_src); wall(m, A + y)
    Mx = np.array(Matrix.Translation(((A - y) / 2, 0, 0))); m.xform_since(n0, Mx)
    m.streak_src[s0:] = [(a + (A - y) / 2, b, c, d, e) for (a, b, c, d, e) in m.streak_src[s0:]]
    n0 = len(m.V); s1 = len(m.streak_src); wall(m, A - y)
    Mx = np.array(Matrix.Translation((0, y + (A - y) / 2, 0)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z')); m.xform_since(n0, Mx)
    m.streak_src[s1:] = [(-b, y + (A - y) / 2 - a, c, d, e) for (a, b, c, d, e) in m.streak_src[s1:]]
    r = m.rng; z = 0.6; i = 0
    while z < WALK - 0.55:
        h = float(r.uniform(0.4, 0.55)); la, lb = (1.0, 0.6) if i % 2 == 0 else (0.6, 1.0)
        ash(m, [-y - 0.045, -y - 0.045, z], [-y + la, -y + 0.3, z + h - 0.012], 0.03, tag=TAG_STONE + 50); ash(m, [-y - 0.045, -y + 0.3, z], [-y + 0.3, -y + lb, z + h - 0.012], 0.03, tag=TAG_STONE + 50)
        z += h; i += 1
    sh = np.array([-(A - y) / 2 + y / 2, -(A - y) / 2 + y / 2, 0.0])       # pivot to the centre of the footprint
    sh = -np.array([(A - y) / 2 - 0.15, (A - y) / 2 - 0.15, 0.0])
    m.V = (np.array(m.V) + sh).tolist(); m.streak_src = [(a + sh[0], b + sh[1], c, d, e) for (a, b, c, d, e) in m.streak_src]
    m.corner_shift = sh
    m.ucx = [([-y + sh[0], -y + sh[1], 0], [A + sh[0], y + sh[1], WALK]), ([-y + sh[0], y + sh[1], 0], [y + sh[0], A + sh[1], WALK])]


def drum(m, R, z0, z1, n=40, nz=None, relief=0.02, Rtop=None, tag=0, cx=0.0, cy=0.0):
    """closed stone cylinder (or cone frustum) with cylindrical UVs and an uneven face"""
    Rtop = R if Rtop is None else Rtop; nz = nz or max(1, int((z1 - z0) / 0.3)); r = m.rng; sd = int(r.integers(1e6))
    V = []; uo = r.uniform(0, 1, 2)
    for i in range(n):
        a = 2 * math.pi * i / n
        for j in range(nz + 1):
            t = j / nz; rr = R + (Rtop - R) * t; z = z0 + (z1 - z0) * t
            p = np.array([rr * math.cos(a), rr * math.sin(a), z])
            d = (vnoise(p[None, :], sd, 2.4)[0] + 0.5 * vnoise(p[None, :], sd + 3, 7.0)[0]) * relief if 0 < j < nz else 0.0
            V.append([cx + (rr + d) * math.cos(a), cy + (rr + d) * math.sin(a), z])
    V.append([cx, cy, z0]); V.append([cx, cy, z1]); c0, c1 = len(V) - 2, len(V) - 1
    F = []; UV = []
    cir = 2 * math.pi * R
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(nz):
            a_, b_, c_, d_ = i * (nz + 1) + j, i2 * (nz + 1) + j, i2 * (nz + 1) + j + 1, i * (nz + 1) + j + 1
            F.append([a_, b_, c_, d_])
            u0, u1 = i / n * cir / T_ASH + uo[0], (i + 1) / n * cir / T_ASH + uo[0]
            v0, v1 = (z0 + (z1 - z0) * j / nz) / T_ASH + uo[1], (z0 + (z1 - z0) * (j + 1) / nz) / T_ASH + uo[1]
            UV.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        F.append([c0, i2 * (nz + 1), i * (nz + 1)]); F.append([c1, i * (nz + 1) + nz, i2 * (nz + 1) + nz])
        for k in range(2):
            a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n
            UV.append([(0.5 + uo[0], 0.5), (0.5 + uo[0] + R * math.cos(a1 if k == 0 else a0) / T_ASH, 0.5 + R * math.sin(a1 if k == 0 else a0) / T_ASH), (0.5 + uo[0] + R * math.cos(a0 if k == 0 else a1) / T_ASH, 0.5 + R * math.sin(a0 if k == 0 else a1) / T_ASH)])
    m.add_uv(V, F, UV, SA, tag, True)


def radial(m, n0, ang, R, cx=0.0, cy=0.0, z=0.0):
    """move parts built at the origin (outer face toward -Y, i.e. local y = -depth) out to radius R at angle ang"""
    M = Matrix.Translation((cx + R * math.cos(ang), cy + R * math.sin(ang), z)) @ Matrix.Rotation(ang + math.pi / 2, 4, 'Z')
    m.xform_since(n0, np.array(M))


def round_top(m, R, zw, cx=0.0, cy=0.0, nm=10, corbels=True):
    """corbel table, breast wall of chord blocks, merlons with copings, paved floor"""
    r = m.rng; Ro = R + (0.32 if corbels else 0.06)
    if corbels:
        nc = int(2 * math.pi * R / 0.62)
        for k in range(nc):
            a = 2 * math.pi * k / nc
            for (zz, pr, hh) in ((zw - 0.62, 0.14, 0.2), (zw - 0.42, 0.26, 0.2), (zw - 0.22, 0.36, 0.2)):
                n0 = len(m.V)
                ash(m, [-0.15, -pr, 0], [0.15, 0.1, hh - 0.01], 0.02, tag=TAG_STONE + 50)
                radial(m, n0, a, R, cx, cy, zz)
        n0 = len(m.V)
    nb = int(2 * math.pi * Ro / 0.8)
    for c in range(2):
        for k in range(nb):
            a = 2 * math.pi * (k + 0.5 * c) / nb; ch = 2 * Ro * math.sin(math.pi / nb)
            n0 = len(m.V)
            ash(m, [-ch / 2 + 0.004, -0.0, 0], [ch / 2 - 0.004, 0.42, 0.44], 0.022)
            radial(m, n0, a, Ro, cx, cy, zw - 0.02 + c * 0.45)
    for k in range(nm):
        a = 2 * math.pi * (k + 0.5) / nm; wdt = 2 * math.pi * Ro / nm * 0.56
        for c in range(3):
            n0 = len(m.V)
            if c == 1:
                ash(m, [-wdt / 2, -0.004, 0], [-0.01, 0.42, 0.36], 0.022); ash(m, [0.01, -0.004, 0], [wdt / 2, 0.42, 0.36], 0.022)
            else:
                ash(m, [-wdt / 2, -0.004, 0], [wdt / 2, 0.42, 0.36], 0.022)
            radial(m, n0, a, Ro, cx, cy, zw + 0.88 + c * 0.365)
        n0 = len(m.V)
        ash(m, [-wdt / 2 - 0.03, -0.04, 0], [wdt / 2 + 0.03, 0.46, 0.11], 0.03, tag=TAG_STONE + 50)
        radial(m, n0, a, Ro, cx, cy, zw + 0.88 + 3 * 0.365)
        m.streak_src.append((cx + Ro * math.cos(a + math.pi / nm), cy + Ro * math.sin(a + math.pi / nm), zw + 0.86, 0.5, 0.8))
    m.tube([[cx, cy, zw - 0.2], [cx, cy, zw + 0.0]], Ro - 0.05, SA, sides=28, tag=TAG_WALK, smooth=False, tile=T_ASH, vrange=(0.5, 0.3))


def loop(m, ang, R, z, cx=0.0, cy=0.0, h=1.2):
    """arrow loop: a dark slit with dressed jambs, sill and lintel standing a little proud of the wall"""
    n0 = len(m.V)
    m.block([-0.2, 0.05, 0.0], [0.2, 0.3, h], SO, T_TIMBER, 0.0, 0.0, tag=TAG_VOID)
    for sx in (-1, 1):
        zz = 0.0
        while zz < h - 1e-6:
            hh = min(0.3, h - zz)
            ash(m, [sx * 0.06 if sx > 0 else -0.34, -0.03, zz], [0.34 if sx > 0 else -0.06, 0.2, zz + hh - 0.006], 0.018, tag=TAG_STONE + 50, rot=(-sx * 0.42, 0, 0)); zz += hh      # jambs cut on the splay
    ash(m, [-0.36, -0.05, -0.2], [0.36, 0.2, 0.0], 0.02, tag=TAG_STONE + 50); ash(m, [-0.36, -0.04, h], [0.36, 0.2, h + 0.22], 0.02, tag=TAG_STONE + 50)
    radial(m, n0, ang, R, cx, cy, z)
    m.streak_src.append((cx + R * math.cos(ang), cy + R * math.sin(ang), z - 0.2, 0.4, 0.6))


def tower(m, R=2.6, H=10.0):
    drum(m, R, 0.0, H, n=48, relief=0.022)
    drum(m, R + 0.4, 0.0, 1.7, n=48, relief=0.015, Rtop=R + 0.01)                 # battered base
    nb = int(2 * math.pi * (R + 0.42) / 0.8)
    for k in range(nb):
        n0 = len(m.V); a = 2 * math.pi * k / nb; ch = 2 * (R + 0.42) * math.sin(math.pi / nb)
        ash(m, [-ch / 2 + 0.004, -0.06, 0], [ch / 2 - 0.004, 0.3, 0.3], 0.03); radial(m, n0, a, R + 0.42, 0, 0, 0.0)
    for k in range(3):
        loop(m, -math.pi / 2 + 2 * math.pi * k / 3 + 0.3, R, 3.6); loop(m, -math.pi / 2 + 2 * math.pi * (k + 0.5) / 3 + 0.3, R, 6.6)
    r = m.rng
    for _ in range(70):                                  # proud and shy blocks on the drum
        n0 = len(m.V); l = float(r.uniform(0.45, 0.8)); k = int(r.integers(4, 16)); pr = float(r.uniform(0.012, 0.035))
        ash(m, [-l / 2, -pr, 0.012], [l / 2, 0.08, 0.55 * (0.5 if r.uniform() < 0.5 else 1.0) - 0.012], 0.03, 0.008, tag=TAG_STONE if r.uniform() < 0.6 else TAG_STONE + 50)
        radial(m, n0, float(r.uniform(0, 6.283)), R, 0, 0, k * 0.55)
    for zp in (2.6, 5.2, 7.8):
        for k in range(5):
            n0 = len(m.V); a_ = 2 * math.pi * (k + 0.3 * (zp > 5)) / 5 + 0.7
            m.block([-0.07, -0.004, -0.075], [0.07, 0.25, 0.075], SO, T_TIMBER, 0.0, 0.0, tag=TAG_VOID); radial(m, n0, a_, R, 0, 0, zp)
            m.streak_src.append((R * math.cos(a_), R * math.sin(a_), zp - 0.07, 0.2, 0.45))
    round_top(m, R, H)
    m.hulls = [[[(R + 0.4) * math.cos(a), (R + 0.4) * math.sin(a), z] for a in np.linspace(0, 2 * math.pi, 13)[:-1] for z in (0.0, H + 2.0)]]
    m.ztop = H


def gatehouse(m, W=8.0, D=5.0, H=8.5):
    r = m.rng; hx, hy = W / 2, D / 2; pw = 1.6; zs = 2.8; za = zs + pw
    m.slab(-hx, -pw, 0.0, H, -hy, hy, SA, T_ASH, nx=10, nz=34, relief=0.02); m.slab(pw, hx, 0.0, H, -hy, hy, SA, T_ASH, nx=10, nz=34, relief=0.02)
    m.slab(-pw, pw, za, H, -hy, hy, SA, T_ASH, nx=13, nz=16, relief=0.02)
    for sx in (-1, 1):                                                   # barrel vault: spandrels through the full depth
        arc = [(sx * pw * math.cos(t), zs + pw * math.sin(t)) for t in np.linspace(0, math.pi / 2, 9)]
        m.prism([(sx * pw, za)] + arc, -hy, hy, SA, T_ASH, tag=TAG_SHEET, axis=1)
    for fy, sg in ((-hy, -1), (hy, 1)):                                  # voussoirs and jamb stones on both faces
        nv = 13
        for k in range(nv):
            t = math.pi * (k + 0.5) / nv
            n0 = len(m.V)
            ash(m, [-0.19, -0.2, 0.0], [0.19, 0.2, 0.5 + (0.12 if k == nv // 2 else 0)], 0.022, tag=TAG_STONE + 50)
            Mx = Matrix.Translation((pw * math.cos(t), fy + sg * 0.06 - sg * 0.2, zs + pw * math.sin(t))) @ Matrix.Rotation(-(t - math.pi / 2), 4, 'Y')
            m.xform_since(n0, np.array(Mx))
        for sx in (-1, 1):
            z = 0.0; i = 0
            while z < zs - 1e-6:
                h = min(0.4, zs - z); la = 0.62 if i % 2 == 0 else 0.4
                ash(m, [min(sx * pw, sx * (pw + la)), min(fy - sg * 0.3, fy + sg * 0.05), z + 0.005], [max(sx * pw, sx * (pw + la)), max(fy - sg * 0.3, fy + sg * 0.05), z + h - 0.005], 0.024, tag=TAG_STONE + 50)
                z += h; i += 1
    for sgn in (-1, 1):                                                  # plinth
        ya, yb = (-hy - 0.16, -hy + 0.05) if sgn < 0 else (hy - 0.05, hy + 0.16)
        for (a, b) in ((-hx, -pw - 0.7), (pw + 0.7, hx)):
            course(m, a, b, ya, yb, 0.0, 0.34, 0.6, 1.1, bevel=0.03)
    course(m, -hx, hx, -hy - 0.1, -hy + 0.05, H - 0.3, H - 0.06, 0.55, 1.0, tag=TAG_STONE + 50, bevel=0.03)
    face_relief(m, -hx, -pw - 0.7, 0.6, H - 0.6, -hy, 12); face_relief(m, pw + 0.7, hx, 0.6, H - 0.6, -hy, 12); face_relief(m, -pw, pw, za + 2.2, H - 0.6, -hy, 6, putlog=())
    # carved panel over the arch and two loops lighting the chamber above the gate
    ash(m, [-0.55, -hy - 0.07, za + 0.75], [0.55, -hy + 0.1, za + 2.0], 0.03, tag=TAG_STONE + 50)
    ash(m, [-0.38, -hy - 0.1, za + 0.9], [0.38, -hy + 0.1, za + 1.85], 0.05, tag=TAG_STONE)
    for sx in (-1.9, 1.9):
        n0 = len(m.V); loop(m, -math.pi / 2, 0.0, 0.0, h=1.1)
        m.xform_since(n0, np.array(Matrix.Translation((sx, -hy, za + 1.2)))); m.streak_src[-1] = (sx, -hy, za + 1.0, 0.4, 0.6)
    # portcullis, raised: oak grille shod and banded with iron, hanging in its slot 0.6 m inside the outer face
    yp = -hy + 0.6
    for k in range(8):
        x = -pw + 0.2 + k * (2 * pw - 0.4) / 7
        timber(m, [x - 0.05, yp - 0.05, 2.25], [x + 0.05, yp + 0.05, za + 0.3], 0.008, 0.002, 4)
        m.prism([(x - 0.05, 2.25), (x + 0.05, 2.25), (x, 2.02)], yp - 0.05, yp + 0.05, SO, T_TIMBER, tag=TAG_IRON, axis=1)
    for zz in (2.5, 3.1, 3.7, 4.3):
        timber(m, [-pw + 0.05, yp - 0.07, zz - 0.045], [pw - 0.05, yp - 0.045, zz + 0.045], 0.006, 0.002)
        m.block([-pw + 0.05, yp - 0.078, zz - 0.02], [pw - 0.05, yp - 0.07, zz + 0.02], SO, T_TIMBER, 0.002, 0.0005, tag=TAG_IRON)
    # roof: parapets all round, paving
    mer = [(c - 0.65, c + 0.65) for c in (-3.0, -1.0, 1.0, 3.0)]
    parapet(m, -hx, hx, -hy - 0.02, H - 0.06, merlons=mer)
    n0 = len(m.V); src0 = len(m.streak_src); parapet(m, -hx, hx, -hy - 0.02, H - 0.06, merlons=mer); m.xform_since(n0, np.array(Matrix.Rotation(math.pi, 4, 'Z'))); del m.streak_src[src0:]
    for sgn in (-1, 1):
        n0 = len(m.V); src0 = len(m.streak_src)
        parapet(m, -hy + 0.43, hy - 0.43, -hx - 0.02, H - 0.06, merlons=[(-1.55, -0.45), (0.45, 1.55)])
        m.xform_since(n0, np.array(Matrix.Rotation(sgn * math.pi / 2, 4, 'Z'))); del m.streak_src[src0:]
    x = -hx + 0.43
    while x < hx - 0.44:
        l = min(float(r.uniform(0.8, 1.2)), hx - 0.43 - x)
        for (a, b) in ((-hy + 0.43, -0.8), (-0.8, 0.9), (0.9, hy - 0.43)):
            ash(m, [x + 0.006, a + 0.006, H - 0.07], [x + l - 0.006, b - 0.006, H + 0.02 + r.normal(0, 0.004)], 0.012, tag=TAG_WALK)
        x += l
    # two round flanking turrets at the outer corners, rising above the gate roof
    for sx in (-1, 1):
        cx, cy = sx * (hx - 0.2), -hy + 0.1; Rt = 1.45
        drum(m, Rt, 0.0, H + 1.5, n=30, relief=0.018, cx=cx, cy=cy)
        drum(m, Rt + 0.3, 0.0, 1.5, n=30, relief=0.012, Rtop=Rt + 0.01, cx=cx, cy=cy)
        round_top(m, Rt, H + 1.5, cx, cy, nm=6)
        loop(m, -math.pi / 2 - sx * 0.5, Rt, 3.4, cx, cy); loop(m, -math.pi / 2 - sx * 0.1, Rt, 6.6, cx, cy)
    m.ucx = [([-hx, -hy, 0], [-pw, hy, H]), ([pw, -hy, 0], [hx, hy, H]), ([-pw, -hy, za], [pw, hy, H])]
    for sx in (-1, 1):
        cx, cy = sx * (hx - 0.2), -hy + 0.1
        m.hulls.append([[cx + 1.6 * math.cos(a), cy + 1.6 * math.sin(a), z] for a in np.linspace(0, 2 * math.pi, 11)[:-1] for z in (0.0, H + 3.4)])
    m.ztop = H


def castle_paint(m):
    seed = int(m.rng.integers(1e6))

    def f(P, tags, N, col):
        z = P[:, 2]; n = vnoise(P, seed, 1.1); n2 = vnoise(P, seed + 3, 6.0); n3 = vnoise(P, seed + 9, 0.45)
        R = np.zeros(len(P)); G = np.zeros(len(P)); B = np.zeros(len(P)); A = np.ones(len(P))
        Q = P.copy(); Q[:, 2] *= 0.25
        st = np.clip(0.5 + 0.9 * vnoise(Q * np.array([5.0, 5.0, 1.0]), seed + 5, 1.0), 0, 1)
        stone = (tags == TAG_SHEET) | (tags == TAG_STONE) | (tags == TAG_STONE + 50) | (tags == TAG_WALK)
        north = np.clip(N[:, 1], 0, 1)
        splash = np.clip((0.7 * (1 + 0.5 * n) - z) / 0.6, 0, 1)
        alg = np.clip((0.9 * (1 + 0.9 * n3 + 0.4 * n2) + 0.9 * north * (0.4 + n3) - z) / 0.7, 0, 1)
        ztop = getattr(m, 'ztop', WALK)
        head = np.clip(1 - (ztop - z) / 3.0, 0, 1) * (z < ztop) * st * 0.8             # run-off below the wall head
        Rs = np.clip(0.7 * splash + 0.22 + 0.3 * n + 0.3 * n3 + head, 0, 1)
        Gs = np.clip(0.9 * alg + 0.7 * (N[:, 2] > 0.6) * np.clip(0.5 + 0.8 * n3, 0, 1) + 0.3 * north * np.clip(n3 + 0.2, 0, 1), 0, 1)
        for (sx_, sy_, zt, hw, kk) in m.streak_src:
            dd = np.hypot(P[:, 0] - sx_, P[:, 1] - sy_)
            run = np.clip(1 - dd / (hw + 0.1 * (zt - z)), 0, 1) * np.clip(1 - (zt - z) / 4.5, 0, 1) * (z < zt + 0.02)
            Rs = np.clip(Rs + 1.3 * kk * run * (0.45 + 0.55 * st), 0, 1); Gs = np.clip(Gs + 0.5 * kk * run * (z < zt - 0.3) * np.clip(n3 + 0.5, 0, 1), 0, 1)
        Bs = np.where(tags == TAG_STONE + 50, np.clip(0.55 + 0.3 * n2, 0, 1), np.clip(0.15 + 0.25 * n + 0.2 * (tags == TAG_STONE), 0, 1))
        Bs = np.clip(Bs + 0.6 * np.clip(n2 - 0.3, 0, 1) * (N[:, 2] > -0.2), 0, 1)
        walk = tags == TAG_WALK
        Rs = np.where(walk, np.clip(0.45 + 0.3 * n, 0, 1), Rs); Gs = np.where(walk, np.clip(0.5 + 0.8 * n3 + 0.4 * n2, 0, 1) * 0.8, Gs)
        R = np.where(stone, Rs, R); G = np.where(stone, Gs, G); B = np.where(stone, Bs, B)
        tim = (tags == TAG_TIMBER) | (tags == TAG_END)
        R = np.where(tim, np.clip(0.5 + 0.3 * n2, 0, 1), R); B = np.where(tim, np.clip(0.2 + 0.3 * n, 0, 1), B)
        A = np.where(tags == TAG_IRON, 0.5, A); A = np.where(tags == TAG_VOID, 0.5, A); R = np.where(tags == TAG_VOID, 1.0, R)
        return np.stack([R, G, B, A], -1)
    return f


def castle_modules(rows):
    out = []

    def mk(name, L, H):
        m = Mod2(name, L, H, rows, 'building', 'Structures/Castle'); m.slots = ['ashlar', 'oak']; m.streak_src = []; m.floor0 = True
        m.paint.append(castle_paint(m)); return m

    def rec(m, fams, frames, note, **k):
        used = sorted(set(m.FM)); m.FM = [used.index(i) for i in m.FM]; m.slots = [m.slots[i] for i in used]
        out.append(dict(m=m, families=fams, sprite_family='67 struct/castle/castl-', sprite_frames=frames, supersedes='none (family 67 had no final art)', dresses=note, **k))
    m = mk('SM_Castle_Wall_8m', 8.0, 9.0); wall(m, 8.0)
    rec(m, ['castle_wall_diag', 'castle_wall_corner'], 'frames 6, 7, 9 (350 px wall runs) and 8', 'curtain wall, 8.0 m long, 1.8 m thick, courses about 0.55 m; wall-walk at 7.0 m oversailing the field face by 0.3 m on a corbel table, crenellated parapet to 9.2 m (four merlons, period 2.0 m, so runs tile), inner kerb, paved walk, offset plinth courses, proud and shy blocks and two rows of putlog holes on the faces, two stone water spouts',
        fit={'pivot': 'ground centre; field face toward -Y', 'frames': 'the 350 px frames are oblique views of a wall run: yaw 45 degrees for the diagonal frames (6, 7, 9); one module per sprite, 8.75 m of card for 8.0 m of wall, so allow a 0.75 m overlap into the towers or scale X by 1.09'})
    m = mk('SM_Castle_Wall_Corner', 4.9, 9.0); corner(m)
    rec(m, ['castle_wall_corner'], 'frame 8 (350x505 px)', 'outer corner of the curtain wall: two arms 4.0 m long measured from the angle, field faces toward -X and -Y, the same corbelled parapet, plinth and putlog holes as the wall, dressed quoins up the angle',
        fit={'pivot': 'ground centre of the L footprint; the outer angle of the two field faces is at (%.2f, %.2f) from the pivot; arms run toward +X and +Y and end square, so SM_Castle_Wall_8m butts against them' % (-0.9 - 1.4, -0.9 - 1.4)})
    m = mk('SM_Castle_Wall_End', 2.5, 9.0); wall(m, 2.5, end=1)
    rec(m, ['castle_wall_end'], 'frame 12 (100x340 px)', '2.5 m wall end with dressed quoins on its free (+X) end, one merlon', fit={'pivot': 'ground centre; the quoined free end is at +X: yaw 180 for the other hand'})
    m = mk('SM_Castle_Tower_Round', 5.2, 12.1); tower(m)
    rec(m, ['castle_tower_round'], 'frames 1-4 (193 px wide)', 'round tower, 5.2 m across (6.0 m at the battered foot), 10 m to the paved top, corbel table of three oversailing courses, ten merlons with copings to 12.1 m, six arrow loops in two tiers',
        fit={'pivot': 'ground centre', 'frames': 'frames 1-4 differ only in which wall stubs are drawn against the tower: one mesh serves all four; the 193 px card is 4.8 m'})
    m = mk('SM_Castle_Gatehouse', 8.0, 12.4); gatehouse(m)
    rec(m, ['castle_gatehouse'], 'frame 5 (335x389 px)', 'gatehouse 8.0 x 5.0 m, 8.5 m to its paved roof: 3.2 m round-arched passage with a barrel vault, voussoirs and jamb stones on both faces, raised iron-shod oak portcullis, carved panel and two loops over the arch, crenellated parapet all round, two round flanking turrets to 12.4 m',
        fit={'pivot': 'ground centre; field face -Y; the passage runs along Y at x = 0, 3.2 m wide, 4.4 m to the crown, portcullis foot at 2.0 m', 'note': 'the sprite shows a closed block with two half-round turrets and no visible gate (seen from inside the walls); this module has the arch on both faces'})
    return out


def main_castle():
    sc = new_scene()
    rows = board_rows('OakWeathered')
    mats = {'ashlar': wmat('MI_Struct_CastleAshlar', 'CastleAshlar', dirt=(0.30, 0.22, 0.12), pale=(0.60, 0.60, 0.52), pale_amt=0.5, dirt_amt=0.92, moss=(0.04, 0.055, 0.02)),
            'oak': wmat('MI_Struct_OakWeathered', 'OakWeathered', dirt=(0.22, 0.16, 0.11), pale=(0.46, 0.45, 0.42), pale_amt=0.55, special=True, tint=(0.80, 0.62, 0.47, 1))}
    recs = export_modules(castle_modules(rows), mats, OUT, 'Castle.blend')
    json.dump(recs, open(os.path.join(OUT, 'modules.json'), 'w'), indent=1)
    print('CASTLE DONE', len(recs))


main_castle()
