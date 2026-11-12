"""Farm-tool and yard dressing props for SCR_440 (real-world scale, closed solids, Z up, front -Y).

Original placements on the screen: pitchfork S440_P21 (tool-01), long hook/scythe S440_P22 (tool-12),
axe S440_P23 (tool-06), tongs S440_P24 (tool-16), hatchet S440_P25 (tool-14).  The hoe, shovel,
wheelbarrow, hay bale, trough, chopping block and woodpile are new believable yard dressing.
Every builder returns (collision boxes [(center, dims, rot)], bake texture size, notes)."""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix
import lib440 as L


def smooth_bump(z, c, w):
    return math.exp(-((z - c) / w) ** 2)


def bez(p0, p1, p2, p3, n):
    out = []
    for i in range(n):
        t = i / (n - 1)
        a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
        out.append(tuple(a * Vector(p0) + b * Vector(p1) + c * Vector(p2) + d * Vector(p3)))
    return out


def transform_since(start, M):
    """Apply M to every piece created since index start (mesh + grain axis attribute)."""
    R = M.to_3x3()
    for ob in L.STATE['pieces'][start:]:
        ob.data.transform(M)
        if 'gaxis' in ob.data.attributes:
            a = ob.data.attributes['gaxis']; v = np.zeros(len(a.data) * 3, np.float32); a.data.foreach_get('vector', v)
            v = (np.array(R) @ v.reshape(-1, 3).T).T
            a.data.foreach_set('vector', v.astype(np.float32).ravel())


def handle(z0, z1, r0, r1, M, grips=(), n=24, x=0.0, y=0.0, butt=True):
    zs = np.linspace(z0, z1, n)
    pts = [(x, y, z) for z in zs]
    radii = [r0 + (r1 - r0) * (z - z0) / (z1 - z0) for z in zs]
    if butt:   # rounded, slightly chamfered butt end
        radii[0] *= .62; radii[1] *= .93
        pts[1] = (x, y, z0 + .006)
    pol = [min(1.0, sum(smooth_bump(z, c, w) for c, w in grips)) for z in zs]
    return L.tube(pts, radii, M['ash'], sides=14, polish=pol)


# ----------------------------------------------------------------------------- pitchfork
def pitchfork(M):
    handle(0.0, 1.27, .0165, .0150, M, grips=((.38, .13), (1.02, .12)))
    L.lathe([(0, 1.16), (.0185, 1.16), (.0192, 1.18), (.0170, 1.30), (.0125, 1.335), (0, 1.345)], M['iron'], sides=14)
    for z in (1.20, 1.27):
        L.lathe([(0, -.004), (.0042, -.004), (.0042, .003), (.003, .0048), (0, .0052)], M['iron'], sides=8,
                center=(0, -.0185, z), axis_m=Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))))
    for sgn in (-1, 1):
        pts = bez((0, 0, 1.325), (sgn * .055, 0, 1.36), (sgn * .088, -.004, 1.47), (sgn * .092, -.055, 1.655), 16)
        radii = list(np.linspace(.0085, .0024, 16))
        edge = list(np.clip(np.linspace(-.6, 1.0, 16), 0, 1))
        L.tube(pts, radii, M['iron'], sides=7, edge=edge)
    return [((0, 0, .62), (.05, .05, 1.24), None), ((0, -.02, 1.48), (.21, .08, .36), None)], 1024


# ----------------------------------------------------------------------------- scythe
def scythe(M):
    n = 30; zs = np.linspace(0, 1.52, n)
    pts = [(.035 * math.sin(z / 1.52 * 2 * math.pi) * .8 + .02 * z, 0.0, z) for z in zs]
    radii = [.0175 - .002 * z / 1.52 for z in zs]; radii[0] *= .65
    pol = [min(1, smooth_bump(z, .48, .08) + smooth_bump(z, 1.03, .08) + .3 * smooth_bump(z, .05, .06)) for z in zs]
    L.tube(pts, radii, M['ash'], sides=14, polish=pol)
    for zc, ln in ((.48, .15), (1.03, .14)):            # the two nibs (hand grips)
        x = .035 * math.sin(zc / 1.52 * 2 * math.pi) * .8 + .02 * zc
        p = [(x, -.01, zc), (x, -.06, zc + .01), (x, -ln, zc + .03)]
        L.tube(p, [.013, .0135, .012], M['ash'], sides=10, polish=[1, 1, 1])
        L.ring_solid(.019, .04, .006, M['iron'], center=(x, 0, zc), sides=16)
    top = Vector(pts[-1])
    L.ring_solid(.021, .05, .007, M['iron'], center=top - Vector((0, 0, .03)), sides=16)
    L.box(top + Vector((.03, 0, .015)), (.07, .012, .02), M['iron'], bevel=.003)     # tang
    def blade(u, v):
        x = .05 + .70 * u; y = .11 * u * u - .02 * u
        w = .085 * (1 - u) ** .55 + .006
        return Vector((x + top.x, y + (-w * v), top.z + .02 + .015 * v * (1 - u) - .02 * u * u))
    L.plate(blade, 34, 6, lambda u, v: (.0055 - .0047 * v ** .6) * (1 - .45 * u), M['iron'],
            edge_fn=lambda u, v: max(0.0, (v - .55) / .45))
    L.tube([tuple(blade(u, 0) + Vector((0, .0025, .0015))) for u in np.linspace(0, .9, 12)], list(np.linspace(.0042, .0018, 12)), M['iron'], sides=6)
    return [((0, 0, .76), (.08, .06, 1.52), None), ((.40, .0, 1.55), (.78, .16, .08), None)], 1024


# ----------------------------------------------------------------------------- hoe
def hoe(M):
    handle(0.0, 1.36, .0165, .0150, M, grips=((.42, .14), (1.05, .13)))
    L.lathe([(0, 1.30), (.0215, 1.30), (.0225, 1.32), (.0225, 1.41), (.0205, 1.43), (0, 1.435)], M['iron'], sides=14)
    neck = bez((0, -.016, 1.40), (0, -.07, 1.43), (0, -.12, 1.42), (0, -.135, 1.37), 10)
    L.tube(neck, list(np.linspace(.0085, .0065, 10)), M['iron'], sides=8)
    def bl(u, v):
        return Vector(((u - .5) * .165 * (1 - .12 * v), -.142 - .018 * v, 1.385 - .125 * v))
    L.plate(bl, 12, 8, lambda u, v: .0042 - .0030 * v, M['iron'], edge_fn=lambda u, v: max(0.0, (v - .7) / .3))
    return [((0, 0, .68), (.05, .05, 1.36), None), ((0, -.09, 1.37), (.18, .2, .16), None)], 1024


# ----------------------------------------------------------------------------- shovel (D-handle)
def shovel(M):
    def bl(u, v):     # u across, v from shoulder (0) to tip (1); dished toward -Y
        hw = .125 * math.sqrt(max(0.0, 1 - v ** 3.2)) + .012
        x = (u - .5) * 2 * hw
        return Vector((x, -.024 * (1 - (x / max(hw, 1e-4)) ** 2) - .015 * v, .33 - .31 * v))
    L.plate(bl, 14, 14, lambda u, v: .0034 - .0016 * v ** 2, M['iron'], edge_fn=lambda u, v: max(0.0, (v - .8) / .2))
    L.tube([tuple(bl(u, 0) + Vector((0, .002, .004))) for u in np.linspace(0, 1, 14)], .0055, M['iron'], sides=8, edge=1.0)
    L.tube([(0, .004, .30), (0, .006, .40), (0, .007, .50)], [.021, .019, .0175], M['iron'], sides=14)
    L.box((0, .010, .22), (.022, .006, .17), M['iron'], bevel=.002)                       # strap rivetted to the blade back
    zs = list(np.linspace(.47, .90, 12))
    L.tube([(0, .007, z) for z in zs], [.0168 - .001 * (z - .47) for z in zs], M['ash'], sides=14,
           polish=[smooth_bump(z, .62, .1) for z in zs])
    for sgn in (-1, 1):
        arm = bez((0, .007, .89), (sgn * .02, .007, .95), (sgn * .060, .007, .99), (sgn * .062, .007, 1.06), 10)
        L.tube(arm, list(np.linspace(.015, .011, 10)), M['ash'], sides=10, polish=list(np.linspace(.1, .6, 10)))
    L.tube([(-.072, .007, 1.075), (0, .007, 1.078), (.072, .007, 1.075)], [.0155, .0165, .0155], M['ash'], sides=12, polish=[1, 1, 1])
    L.lathe([(0, .865), (.0185, .865), (.0185, .905), (0, .905)], M['iron'], sides=14, center=(0, .007, 0))
    return [((0, 0, .17), (.27, .07, .34), None), ((0, .007, .7), (.15, .05, .76), None)], 1024


# ----------------------------------------------------------------------------- axes
def axe_parts(M, haft=.86, head_h=.17, head_len=.20, scale=1.0, edge_poll=False):
    """Axe lying on its cheek: haft along +X, bit toward -Y, cheeks face +-Z."""
    s = scale; n = 22
    xs = np.linspace(0, haft * s, n)
    pts = [(x, .012 * s * math.sin(x / (haft * s) * math.pi) - (.018 * s if x < .05 * s else 0) * (1 - x / (.05 * s)), .0) for x in xs]
    radii = [.0165 * s for _ in xs]; radii[0] *= .8
    ov = [(1.0, .72)] * n
    pol = [min(1, smooth_bump(x / s, .10, .07) + .6 * smooth_bump(x / s, .45, .12)) for x in xs]
    start = len(L.STATE['pieces'])
    L.tube(pts, radii, M['ash'], sides=12, polish=pol, ovals=ov)
    hx = haft * s - .055 * s
    def hd(u, v):   # u: poll(0) -> bit(1) along -Y, v across head height along X
        h = (.065 + (head_h - .065) * u ** 2.2) * s
        y = (.035 - head_len * u) * s
        x = hx + (v - .5) * h - .02 * s * u ** 2
        return Vector((x, y - .012 * s * (1 - ((v - .5) * 2) ** 2) * u ** 6, 0))
    L.plate(hd, 16, 8, lambda u, v: (.034 * (1 - u) ** 1.25 + .0011) * s, M['iron'],
            edge_fn=lambda u, v: max(0.0, (u - .82) / .18))
    L.box((hx, .045 * s, 0), (.072 * s, .035 * s, .035 * s), M['iron'], bevel=.004 * s)    # poll
    L.box((hx, .0, 0), (.006 * s, .012 * s, .03 * s), M['oak'], bevel=.001)            # wedge end
    return start


def felling_axe(M):
    axe_parts(M)
    return [((.43, 0, .017), (.88, .06, .035), None), ((.81, -.06, .017), (.16, .22, .035), None)], 1024


def hatchet(M):
    axe_parts(M, haft=.40, head_h=.11, head_len=.13, scale=1.0)
    return [((.2, -.03, .017), (.42, .16, .035), None)], 512


# ----------------------------------------------------------------------------- tongs
def tongs(M):
    for sgn in (-1, 1):
        path = bez((0, sgn * .028, 0), (.12, sgn * .022, 0), (.24, sgn * .012, 0), (.33, 0, sgn * .003), 12)
        path += bez((.33, 0, sgn * .003), (.37, -sgn * .01, sgn * .004), (.41, -sgn * .022, sgn * .004), (.445, -sgn * .006, sgn * .004), 8)[1:]
        r = [.0062] * 6 + [.0058] * 6 + [.0075] * 3 + [.0052] * 4
        L.tube(path, r[:len(path)], M['iron'], sides=6, ovals=[(1.0, .6)] * len(path), polish=[.8] * 5 + [0] * (len(path) - 5))
    L.lathe([(0, -.011), (.009, -.011), (.009, .011), (0, .011)], M['iron'], sides=10, center=(.33, 0, 0))
    return [((.22, 0, .01), (.46, .07, .02), None)], 512


# ----------------------------------------------------------------------------- chopping block with embedded axe
def chopping_block(M):
    rng = L.rng(); R = .29; H = .48; n = 30
    outline = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = R * (1 + .035 * math.sin(3 * a + .7) + .02 * math.sin(7 * a) + rng.uniform(-.008, .008))
        outline.append((math.cos(a) * rr, math.sin(a) * rr))
    blk = L.prism(outline, 0.0, H, M['elm'], bark_edges=set(range(n)), logr=R * .985)
    ch = np.zeros(len(blk.data.polygons), np.float32); ch[1] = 1.0   # face 1 = top cap (see lib440.prism)
    blk.data.attributes['chop'].data.foreach_set('value', ch)
    # embedded felling axe: bit sunk 4 cm into the end grain, haft rising toward +X
    start = axe_parts(M, haft=.80, head_h=.17, head_len=.20)
    ang = math.radians(-20)                              # haft rises 20 degrees away from the head
    c, sn = math.cos(ang), math.sin(ang)
    F = Matrix(((c, 0, -sn), (0, 1, 0), (sn, 0, c)))
    Rb = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))     # local -Y (bit) -> down, cheeks face +-Y
    bit = F @ Rb @ Vector((.80 - .055, -.165, 0))
    T = Matrix.Translation(Vector((.03, 0, H - .045)) - bit) @ (F @ Rb).to_4x4()
    transform_since(start, T)
    pts = [(math.cos(2 * math.pi * k / 12) * R * 1.02, math.sin(2 * math.pi * k / 12) * R * 1.02, z) for k in range(12) for z in (0, H)]
    return [('hull', pts)], 1024


# ----------------------------------------------------------------------------- wheelbarrow
def wheelbarrow(M):
    rng = L.rng()
    wr = .2225; wy = -.60
    # wheel
    ax = Matrix(((0, 0, 1), (0, 1, 0), (-1, 0, 0)))     # local Z -> world X
    L.lathe([(0, -.075), (.040, -.075), (.050, -.05), (.050, .05), (.040, .075), (0, .075)], M['oak'], sides=16, center=(0, wy, wr), axis_m=ax)
    L.ring_solid(.185, .055, .052, M['oak'], center=(0, wy, wr), axis_m=ax, sides=40)
    L.ring_solid(.2155, .058, .0105, M['iron'], center=(0, wy, wr), axis_m=ax, sides=48, bevel_frac=.3)
    for k in range(8):
        a = 2 * math.pi * k / 8 + .2
        d = Vector((0, math.cos(a), math.sin(a)))
        L.tube([tuple(Vector((0, wy, wr)) + d * .045), tuple(Vector((0, wy, wr)) + d * .16)], [.0125, .0105], M['oak'], sides=8)
    L.tube([(-.20, wy, wr), (.20, wy, wr)], .011, M['iron'], sides=10)
    for sx in (-1, 1):
        L.lathe([(0, -.012), (.022, -.012), (.022, .012), (0, .012)], M['iron'], sides=10, center=(sx * .085, wy, wr), axis_m=ax)
    # shafts (side rails) from the axle to the handle grips
    hz = .56; hy = .80
    for sx in (-1, 1):
        a = Vector((sx * .135, wy - .06, wr)); b = Vector((sx * .30, hy, hz))
        L.beam(a, b, .048, .068, M['oak'], bevel=.008)
        g = b + (b - a).normalized() * .0; gdir = (b - a).normalized()
        L.tube([tuple(b - gdir * .17), tuple(b - gdir * .02), tuple(b + gdir * .07)], [.022, .021, .019], M['oak'], sides=12, polish=[.6, 1, 1])
        # legs
        top = a + (b - a) * .70
        L.beam(top + Vector((0, 0, -.02)), Vector((sx * .27, top.y + .02, 0)), .045, .045, M['oak'], bevel=.006)
        L.box((sx * .155, wy - .01, wr + .0), (.05, .16, .05), M['oak'], bevel=.006, grain_axis=1)   # axle block
    leg_z = .25
    L.beam((-.27, .42, .24), (.27, .42, .24), .035, .035, M['oak'], bevel=.005)         # leg stretcher
    # tray: built level then tilted to sit on the rails
    start = len(L.STATE['pieces'])
    tlen = .78; tw = .44
    for k in range(3):
        L.box(((k - 1) * tw / 3, 0, .0125), (tw / 3 - .006, tlen, .025), M['oak'], bevel=.004, grain_axis=1)
    for sx in (-1, 1):   # flared side boards
        ang = math.radians(24) * sx
        Rr = Matrix.Rotation(ang, 3, 'Y')
        L.box((sx * (tw / 2 + .05), .02, .13), (.022, tlen + .10, .23), M['oak'], bevel=.004, rot=Rr, grain_axis=1)
        L.box((sx * (tw / 2 + .095), .02, .255), (.012, tlen + .14, .025), M['iron'], bevel=.003, rot=Rr)   # top edge strap
    Rf = Matrix.Rotation(math.radians(38), 3, 'X')
    L.box((0, -tlen / 2 - .05, .13), (tw + .16, .022, .25), M['oak'], bevel=.004, rot=Rf, grain_axis=0)
    L.box((0, tlen / 2 + .005, .085), (tw + .08, .022, .16), M['oak'], bevel=.004, grain_axis=0)
    for sx in (-1, 1):
        for yy in (-tlen / 2 + .03, tlen / 2 - .02):
            L.box((sx * (tw / 2 + .02), yy, .09), (.012, .04, .16), M['iron'], bevel=.002)
    slope = math.atan2(hz - wr, hy - wy + .06)
    T = Matrix.Translation((0, -.05, wr + .045 + (hz - wr) * ((-.05 - wy) / (hy - wy)))) @ Matrix.Rotation(slope, 4, 'X')
    transform_since(start, T)
    return [((0, -.05, .42), (.80, 1.0, .46), None), ((0, wy, wr), (.14, .45, .45), None),
            ((0, .70, .40), (.66, .28, .36), None)], 1024


# ----------------------------------------------------------------------------- hay bale
def hay_bale(M):
    """One continuous compressed bale: rounded, slightly bulging faces, faint flake creases, two
    sisal bands pressed into grooves, and loose protruding stalks (face attribute 'stalk')."""
    rng = L.rng(); Lx, Wy, Hz = .92, .46, .36; band_y = (-.12, .12); r = .045; nfl = 10
    xs = sorted(set([-Lx / 2, -Lx / 2 + r * .35, -Lx / 2 + r * .75, -Lx / 2 + r, Lx / 2 - r, Lx / 2 - r * .75, Lx / 2 - r * .35, Lx / 2] +
                    [-Lx / 2 + k * Lx / nfl + o for k in range(1, nfl) for o in (-.006, 0, .006)] +
                    list(np.linspace(-Lx / 2 + r, Lx / 2 - r, 23))))
    ys = sorted(set([-Wy / 2, -Wy / 2 + r * .35, -Wy / 2 + r * .75, -Wy / 2 + r, Wy / 2 - r, Wy / 2 - r * .75, Wy / 2 - r * .35, Wy / 2] +
                    [b + o for b in band_y for o in (-.014, -.007, 0, .007, .014)] + list(np.linspace(-Wy / 2 + r, Wy / 2 - r, 9))))
    zs = sorted(set([0, r * .35, r * .75, r, Hz - r, Hz - r * .75, Hz - r * .35, Hz] + list(np.linspace(r, Hz - r, 8))))
    flake_x = [-Lx / 2 + k * Lx / nfl for k in range(1, nfl)]
    import mathutils.noise as mn
    def disp(p, n):
        d = 0.0
        # faces bulge where the baler compression relaxes (max ~1.4 cm mid-face)
        fx = 1 - (2 * p.x / Lx) ** 2; fy = 1 - (2 * p.y / Wy) ** 2; fz = 1 - ((2 * p.z - Hz) / Hz) ** 2
        if abs(n.x) > .7: d += .012 * fy * fz
        if abs(n.y) > .7: d += .014 * fx * fz
        if abs(n.z) > .7: d += .010 * fx * fy
        # sisal bands press grooves around the bale (not on the +-Y faces)
        if abs(n.y) < .7:
            for b in band_y:
                t = abs(p.y - b) / .014
                if t < 1: d -= .009 * (1 - t * t)
        # faint flake creases on the long faces and the top/bottom
        if abs(n.x) < .7:
            for fxp in flake_x:
                t = abs(p.x - fxp) / .006
                if t < 1: d -= .0015 * (1 - t)
        return d + .004 * mn.noise(p * 9.0)
    L.rounded_box(xs, ys, zs, r, M['straw'], disp=disp, grain_axis=0)
    for y in band_y:     # sisal twine loops seated in their grooves
        pts = []
        for sx, sz in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
            cx = sx * (Lx / 2 - r); cz = Hz / 2 + sz * (Hz / 2 - r)
            for a in np.linspace(0, math.pi / 2, 6):
                ca = math.atan2(sz, sx) - math.pi / 4 + a
                pts.append((cx + math.cos(ca) * (r - .001), y, cz + math.sin(ca) * (r - .001)))
        pts.append(tuple(Vector(pts[0]) + Vector((-.006, 0, 0))))
        L.tube(pts, .0045, M['twine'], sides=6)
    start = len(L.STATE['pieces'])
    for i in range(110):      # loose stalks poking out (thicker than real so they survive at distance)
        face = rng.integers(0, 4)
        if face == 0:
            p = Vector((rng.uniform(-Lx / 2 + .03, Lx / 2 - .03), rng.uniform(-Wy / 2 + .03, Wy / 2 - .03), Hz + .004))
            d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(.05, .45)))
        elif face < 3:
            sgn = 1 if face == 1 else -1
            p = Vector((rng.uniform(-Lx / 2 + .03, Lx / 2 - .03), sgn * (Wy / 2 + .006), rng.uniform(.04, Hz - .03)))
            d = Vector((rng.uniform(-.6, .6), sgn * rng.uniform(.4, 1), rng.uniform(-.5, .3)))
        else:
            sgn = rng.choice([-1, 1])
            p = Vector((sgn * (Lx / 2 + .004), rng.uniform(-Wy / 2 + .03, Wy / 2 - .03), rng.uniform(.04, Hz - .03)))
            d = Vector((sgn * rng.uniform(.4, 1), rng.uniform(-.6, .6), rng.uniform(-.4, .3)))
        d.normalize(); ln = rng.uniform(.04, .12); bend = Vector((0, 0, -rng.uniform(.0, .025)))
        pts = [tuple(p - d * .03), tuple(p + d * ln * .45), tuple(p + d * ln * .8 + bend * .5), tuple(p + d * ln + bend)]
        L.tube(pts, [.0024, .0021, .0017, .0010], M['straw'], sides=4)
    for ob in L.STATE['pieces'][start:]:
        a = ob.data.attributes['stalk']; a.data.foreach_set('value', np.ones(len(ob.data.polygons), np.float32))
    return [((0, 0, Hz / 2), (Lx + .02, Wy + .03, Hz + .01), None)], 2048


# ----------------------------------------------------------------------------- water trough
def water_trough(M):
    rng = L.rng(); Lx, Wy, Hz, t = 1.50, .54, .50, .045; z0 = .085
    for x in (-.52, .52):     # bearers
        L.box((x, 0, z0 / 2), (.09, Wy + .12, z0), M['oak'], bevel=.01, grain_axis=1)
    for k in range(3):
        L.box((0, (k - 1) * (Wy - 2 * t) / 3, z0 + t / 2), (Lx - .01, (Wy - 2 * t) / 3 - .004, t), M['oak'], bevel=.005, grain_axis=0)
    ph = (Hz - z0) / 3
    for sy in (-1, 1):
        for k in range(3):
            L.box((0, sy * (Wy / 2 - t / 2), z0 + ph * (k + .5)), (Lx, t, ph - .004), M['oak'], bevel=.006, grain_axis=0)
    for sx in (-1, 1):
        for k in range(3):
            L.box((sx * (Lx / 2 - t / 2 - .01), 0, z0 + ph * (k + .5)), (t, Wy - 2 * t - .004, ph - .004), M['oak'], bevel=.006, grain_axis=1)
    for x in (-.46, .46):     # wrought iron bands with corner rivets
        for sy in (-1, 1):
            L.box((x, sy * (Wy / 2 + .004), z0 + (Hz - z0) / 2), (.045, .007, Hz - z0 + .01), M['iron'], bevel=.002)
        L.box((x, 0, z0 - .004), (.045, Wy + .015, .007), M['iron'], bevel=.002)
        for sy in (-1, 1):
            for z in (z0 + .06, Hz - .05):
                L.lathe([(0, 0), (.007, 0), (.007, .003), (0, .006)], M['iron'], sides=8, center=(x, sy * (Wy / 2 + .007), z),
                        axis_m=Matrix(((1, 0, 0), (0, 0, sy), (0, -sy, 0))))
    wb = L.box((0, 0, z0 + t + (.405 - z0 - t) / 2), (Lx - 2 * t - .024, Wy - 2 * t - .004, .405 - z0 - t), M['water'], bevel=0)
    return [((0, 0, Hz / 2), (Lx + .02, Wy + .14, Hz), None)], 1024


# ----------------------------------------------------------------------------- woodpile
def log_outline(kind, R, segs, rng):
    pts = []
    if kind == 'round':
        for k in range(segs):
            a = 2 * math.pi * k / segs; rr = R * (1 + rng.uniform(-.03, .03))
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
        return pts, set(range(segs))
    span = math.pi if kind == 'half' else math.pi / 2
    a0 = rng.uniform(0, 2 * math.pi)
    pts.append((0.0, 0.0))
    m = max(4, int(segs * span / (2 * math.pi)) + 2)
    for k in range(m + 1):
        a = a0 + span * k / m; rr = R * (1 + rng.uniform(-.03, .03))
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    bark = set(range(1, m + 1))
    if kind == 'half':   # a half's flat face passes through the pith: drop the explicit centre point
        pts = pts[1:]; bark = set(range(0, m))
    return pts, bark


def woodpile(M):
    rng = L.rng(); length = 2.0; depth_c = 0.0
    for y in (-.13, .13):   # bearer poles keep the wood off the ground
        L.prism([(math.cos(a) * .045, math.sin(a) * .045) for a in np.linspace(0, 2 * math.pi, 11)[:-1]], -length / 2 - .1, length / 2 + .1,
                M['firewood'], M=Matrix.Translation((0, y, .045)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'), bark_edges=set(range(10)), logr=.045)
    for x in (-length / 2 - .06, length / 2 + .06):   # end stakes driven into the ground
        L.prism([(math.cos(a) * .042, math.sin(a) * .042) for a in np.linspace(0, 2 * math.pi, 11)[:-1]], 0, 1.12, M['firewood'],
                M=Matrix.Translation((x, 0, 0)), bark_edges=set(range(10)), logr=.042)
    z = .085; pieces = 0
    for row in range(7):
        x = -length / 2 + .02; heights = []
        while x < length / 2 - .06:
            kind = rng.choice(['round', 'half', 'quarter', 'quarter'], p=[.25, .35, .25, .15])
            R = {'round': rng.uniform(.045, .075), 'half': rng.uniform(.07, .105), 'quarter': rng.uniform(.10, .14)}[kind]
            outline, bark = log_outline(kind, R, 16, rng)
            pts = np.array(outline); mn = pts.min(0); mx = pts.max(0)
            w = mx[0] - mn[0]
            if x + w > length / 2:
                break
            ln = rng.uniform(.38, .44); yoff = rng.uniform(-.025, .025)
            ox = x - mn[0]; oz = z - mn[1] + rng.uniform(-.012, .0)
            Mx = Matrix.Translation((ox, yoff + ln / 2, oz)) @ Matrix.Rotation(math.pi / 2, 4, 'X')
            L.prism(outline, 0, ln, M['firewood'], M=Mx, bark_edges=bark, logr=R)
            heights.append(mx[1] - mn[1]); x += w * .93 + .004; pieces += 1
        z += float(np.median(heights)) * .86 if heights else .1
    top = z
    return [((0, 0, top / 2), (length + .2, .48, top), None)], 2048, pieces


ASSETS = [
    # name, class, builder, original origin, description
    ('SM_Pitchfork_Ash_01', 'prop', pitchfork, 'S440_P21', 'two-tine hay fork, forged iron, polished ash shaft'),
    ('SM_Scythe_Ash_01', 'prop', scythe, 'S440_P22', 'scythe: curved ash snath, two nibs, forged blade'),
    ('SM_Hoe_Ash_01', 'prop', hoe, None, 'swan-neck draw hoe'),
    ('SM_Shovel_Ash_01', 'prop', shovel, None, 'D-handle shovel with rolled tread'),
    ('SM_Axe_Felling_01', 'prop', felling_axe, 'S440_P23', 'felling axe lying on its cheek'),
    ('SM_Hatchet_01', 'prop_small', hatchet, 'S440_P25', 'hatchet lying on its cheek'),
    ('SM_Tongs_Iron_01', 'prop_small', tongs, 'S440_P24', 'riveted hearth/smithing tongs'),
    ('SM_ChoppingBlock_Axe_01', 'prop', chopping_block, None, 'elm chopping round with an axe bitten into it'),
    ('SM_Wheelbarrow_Oak_01', 'prop', wheelbarrow, None, 'wooden wheelbarrow, iron-tyred spoked wheel'),
    ('SM_HayBale_01', 'prop', hay_bale, None, 'twine-tied small square straw bale'),
    ('SM_WaterTrough_Oak_01', 'prop', water_trough, None, 'iron-banded oak plank trough with water'),
    ('SM_Woodpile_Split_01', 'prop', woodpile, None, 'stacked split firewood on bearers between stakes'),
]
