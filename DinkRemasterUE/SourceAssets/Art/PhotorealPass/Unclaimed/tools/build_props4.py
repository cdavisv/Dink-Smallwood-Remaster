"""Paper, cloth, wood and monument props of the unclaimed families: the "Hark!" and "Wanted" notices (462 inner/poster),
the note on the floor (422), the red banner (450), the throwing axe (85), the cellar hatch (428/5), the spinning wheel
(447/4), the smashed barrel (173/6), the carved "Dink Smallwood" rock (159/4) and the stained-glass shrine (159/7).

    tools/bl.sh build_props4.py <name,name|all> [review|final]
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

SCRIPT = 'build_props4.py'
UPRIGHT = Matrix.Rotation(math.pi / 2, 4, 'X')                 # text / flat things built in XY stood up to face -Y


# ---------------------------------------------------------------------------------------------- parchment
def parchment_mat(name, lines=None, picture=None):
    """vellum from the sheet's own UV: stains, darker foxed edges, fibres; lines = (v0, v1, rows) of iron-gall script as broken strokes; picture = (u0, u1, v0, v1) an inked woodcut block"""
    t = NT(name); uv = t.sep(t.uv); u, v = uv[0], uv[1]; n = t.noise(1.0, 5, 0.65, vec=t.comb(t.math('MULTIPLY', u, 5.0), t.math('MULTIPLY', v, 7.0), 0.0)); fib = t.noise(1.0, 3, 0.6, vec=t.comb(t.math('MULTIPLY', u, 300.0), t.math('MULTIPLY', v, 60.0), 0.0))
    edge = t.math('MINIMUM', t.math('MINIMUM', u, t.math('SUBTRACT', 1.0, u)), t.math('MINIMUM', v, t.math('SUBTRACT', 1.0, v))); fox = t.maprange(t.math('ADD', edge, t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.12)), 0.0, 0.14, 1.0, 0.0, interp='SMOOTHSTEP')
    base = t.mix(n, (0.52, 0.40, 0.22), (0.74, 0.62, 0.40)); base = t.mix(t.math('MULTIPLY', fox, 0.7), base, (0.28, 0.17, 0.07)); stain = t.ramp(t.noise(1.0, 4, 0.7, vec=t.comb(t.math('MULTIPLY', u, 3.0), t.math('MULTIPLY', v, 3.0), 4.0)), [(0.6, 0.0), (0.7, 1.0)])
    base = t.mix(t.math('MULTIPLY', stain, 0.35), base, (0.36, 0.24, 0.10)); ink = t.val(0.0)
    if lines:
        v0, v1, rows = lines; fv = t.math('MULTIPLY', t.maprange(v, v0, v1, 0.0, 1.0), float(rows)); row = t.math('FRACT', fv); stroke = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', row, 0.5)), [(0.14, 1.0), (0.2, 0.0)])
        word = t.ramp(t.noise(1.0, 2, 0.5, vec=t.comb(t.math('MULTIPLY', u, 26.0), t.math('FLOOR', fv), 0.0)), [(0.42, 0.0), (0.46, 1.0)]); pen = t.ramp(t.noise(1.0, 2, 0.5, vec=t.comb(t.math('MULTIPLY', u, 170.0), t.math('MULTIPLY', v, 60.0), 0.0)), [(0.38, 0.0), (0.5, 1.0)])
        inside = t.math('MULTIPLY', t.math('MULTIPLY', t.maprange(v, v0, v0 + 0.005, 0.0, 1.0), t.maprange(v, v1 - 0.005, v1, 1.0, 0.0)), t.math('MULTIPLY', t.maprange(u, 0.1, 0.12, 0.0, 1.0), t.maprange(u, 0.88, 0.9, 1.0, 0.0)))
        ink = t.math('MULTIPLY', t.math('MULTIPLY', t.math('MULTIPLY', stroke, word), pen), inside)
    if picture:
        u0, u1, v0, v1 = picture; box = t.math('MULTIPLY', t.math('MULTIPLY', t.maprange(u, u0, u0 + 0.01, 0.0, 1.0), t.maprange(u, u1 - 0.01, u1, 1.0, 0.0)), t.math('MULTIPLY', t.maprange(v, v0, v0 + 0.01, 0.0, 1.0), t.maprange(v, v1 - 0.01, v1, 1.0, 0.0)))
        cu = t.math('SUBTRACT', u, (u0 + u1) / 2); cvv = t.math('SUBTRACT', v, v0 + (v1 - v0) * 0.56); head = t.ramp(t.vmath('LENGTH', t.comb(t.math('MULTIPLY', cu, 1.25), cvv, 0.0)), [(0.085, 1.0), (0.095, 0.0)])
        sh = t.ramp(t.vmath('LENGTH', t.comb(t.math('MULTIPLY', cu, 0.7), t.math('SUBTRACT', v, v0 - 0.02), 0.0)), [(0.12, 1.0), (0.13, 0.0)]); hatch = t.ramp(t.math('FRACT', t.math('MULTIPLY', t.math('ADD', u, v), 90.0)), [(0.45, 0.0), (0.55, 1.0)])
        fig = t.math('MAXIMUM', head, sh); pic = t.math('MULTIPLY', box, t.math('MAXIMUM', fig, t.math('MULTIPLY', t.math('SUBTRACT', 1.0, fig), t.math('ADD', t.math('MULTIPLY', hatch, 0.5), 0.12)))); ink = t.math('MAXIMUM', ink, pic)
    base = t.mix(t.math('MINIMUM', t.math('MULTIPLY', ink, 1.0), 0.94), base, (0.022, 0.016, 0.012)); t.set(base=base, rough=t.mixf(n, 0.6, 0.8), normal=t.bump(t.math('ADD', fib, t.math('MULTIPLY', n, 2.0)), 0.25, 0.0006)); return t.mat


def sheet(name, w, h, c, hi, curl=0.02, seed=0, thick=0.0012):
    """a sheet standing in the XZ plane facing -Y: corners lifting off the wall, a soft bow across it"""
    rng = np.random.default_rng(seed); k = rng.uniform(0.6, 1.3, 4); nu, nv = (48, 64) if hi else (7, 9)

    def fn(U, V):
        x = (U - 0.5) * w; z = V * h; cn = (k[0] * (1 - U) ** 3 * (1 - V) ** 3 + k[1] * U ** 3 * (1 - V) ** 3 + k[2] * (1 - U) ** 3 * V ** 3 + k[3] * U ** 3 * V ** 3) * 2.5
        y = -curl * cn - 0.004 * np.sin(np.pi * U) * np.sin(np.pi * V) - 0.002 * np.sin(V * 9 + seed) * np.sin(U * 4)
        return np.stack([x, y, z], -1)
    o = L.grid_surface(name, fn, nu, nv, c, closed_u=False, flip=True); L.mod(o, 'SOLIDIFY', thickness=thick, offset=0.0); L.apply_mods(o); L.fix_normals(o)
    if not hi:
        L.smart_uv(o, angle=60, margin=0.02)
    return o


def notice(hi, c, title, title_col, title_z, lines, picture=None, seed=0, size=0.085):
    w, h = 0.46, 0.64; sh = sheet('sheet', w, h, c, hi, seed=seed); parts = [sh]
    for k, (x, z) in enumerate(((-w / 2 + 0.03, h - 0.03), (w / 2 - 0.03, h - 0.03))):
        parts.append(C.ball('nail%d' % k, (x, -0.006, z), 0.008, c, seg=12 if hi else 6, squash=(1, 0.5, 1)))
    if hi:
        sh.data.materials.append(parchment_mat('vellum', lines=lines, picture=picture))
        tx = L.text_mesh('title', title, size=size, depth=0.0006, c=c); L.xform(tx, Matrix.Translation((0, -0.017, title_z)) @ UPRIGHT)
        t = NT('ink'); n = t.noise(260, 3, 0.6); t.set(base=t.mix(n, tuple(v * 0.7 for v in title_col), title_col), rough=0.6); tx.data.materials.append(t.mat); parts.append(tx)
        im = T.iron_mat('nail', rust=0.7, seed=3.0)
        for o in parts[1:3]:
            o.data.materials.append(im)
    return parts


def hark(hi, c):
    return notice(hi, c, 'Hark!', (0.42, 0.02, 0.015), 0.50, lines=(0.12, 0.70, 11), seed=2)


def wanted(hi, c):
    return notice(hi, c, 'Wanted', (0.03, 0.022, 0.016), 0.075, lines=(0.26, 0.36, 2), picture=(0.22, 0.78, 0.42, 0.9), seed=5, size=0.075)


def note(hi, c):
    """a note dropped on the floor: 34 x 24 cm of vellum, both ends rolled up, eight lines of script"""
    nu, nv = (80, 40) if hi else (12, 5); Ln, Wd, r0 = 0.44, 0.24, 0.016

    def fn(U, V):
        s = (U - 0.5) * Ln; a = np.clip((np.abs(s) - 0.14) / r0, 0, None); flat = np.minimum(np.abs(s), 0.14); rr = r0 * (1 - 0.08 * a / 3)
        x = np.sign(s) * (flat + rr * np.sin(a)); z = rr * (1 - np.cos(a)) + 0.0008 + 0.003 * np.sin(np.pi * V) * (np.abs(s) < 0.14); y = (V - 0.5) * Wd + 0.004 * np.sin(s * 30)
        return np.stack([x, y, z], -1)
    o = L.grid_surface('note', fn, nu, nv, c, closed_u=False); L.mod(o, 'SOLIDIFY', thickness=0.0012, offset=1.0); L.apply_mods(o); L.fix_normals(o)
    if hi:
        o.data.materials.append(parchment_mat('vellum', lines=None))
        t = NT('note'); uv = t.sep(t.uv); u, v = uv[0], uv[1]; n = t.noise(1.0, 5, 0.65, vec=t.comb(t.math('MULTIPLY', u, 7.0), t.math('MULTIPLY', v, 4.0), 0.0))
        row = t.math('FRACT', t.math('MULTIPLY', v, 9.0)); stroke = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', row, 0.5)), [(0.13, 1.0), (0.2, 0.0)]); word = t.ramp(t.noise(1.0, 2, 0.5, vec=t.comb(t.math('MULTIPLY', u, 40.0), t.math('FLOOR', t.math('MULTIPLY', v, 9.0)), 0.0)), [(0.42, 0.0), (0.46, 1.0)])
        pen = t.ramp(t.noise(1.0, 2, 0.5, vec=t.comb(t.math('MULTIPLY', u, 260.0), t.math('MULTIPLY', v, 40.0), 0.0)), [(0.38, 0.0), (0.5, 1.0)]); zone = t.math('MULTIPLY', t.math('MULTIPLY', t.maprange(u, 0.24, 0.26, 0.0, 1.0), t.maprange(u, 0.74, 0.76, 1.0, 0.0)), t.math('MULTIPLY', t.maprange(v, 0.1, 0.12, 0.0, 1.0), t.maprange(v, 0.88, 0.9, 1.0, 0.0)))
        ink = t.math('MULTIPLY', t.math('MULTIPLY', t.math('MULTIPLY', stroke, word), pen), zone); base = t.mix(n, (0.55, 0.43, 0.24), (0.76, 0.64, 0.42)); base = t.mix(t.math('MULTIPLY', ink, 0.9), base, (0.03, 0.022, 0.016))
        t.set(base=base, rough=t.mixf(n, 0.6, 0.8), normal=t.bump(n, 0.2, 0.0006)); L.assign(o, t.mat)
    else:
        L.smart_uv(o, angle=60, margin=0.02)
    return [o]


# ---------------------------------------------------------------------------------------------- banner
def banner(hi, c):
    """red wool wall hanging with a gold braid border, 1.2 x 0.85 m, on a wooden rod: soft vertical folds, the lower edge hanging free"""
    w, h = 1.2, 0.85; nu, nv = (120, 80) if hi else (41, 7)             # the game mesh keeps enough columns to follow the folds

    def fn(U, V):
        x = (U - 0.5) * w; z = V * h + 0.02; fold = (1 - V) ** 1.2; y = -0.012 - 0.022 * fold * np.sin(U * 2 * np.pi * 3.5 + 0.6) - 0.01 * fold * np.sin(U * 2 * np.pi * 8.1) - 0.006 * np.sin(V * 5) * np.sin(U * 9)
        return np.stack([x * (1 - 0.02 * fold * np.cos(U * 20)), y, z], -1)
    cl = L.grid_surface('cloth', fn, nu, nv, c, closed_u=False, flip=True); L.mod(cl, 'SOLIDIFY', thickness=0.004, offset=0.0); L.apply_mods(cl); L.fix_normals(cl)
    rod = L.sweep('rod', [(-0.68, -0.012, 0.885, 0.016, 0.016, 2.1), (-0.66, -0.012, 0.885, 0.022, 0.022, 2.1), (-0.63, -0.012, 0.885, 0.014, 0.014, 2.1), (0.63, -0.012, 0.885, 0.014, 0.014, 2.1), (0.66, -0.012, 0.885, 0.022, 0.022, 2.1), (0.68, -0.012, 0.885, 0.016, 0.016, 2.1)],
                  nu=12 if hi else 6, nv=30 if hi else 7, c=c, up=(0, 0, 1), cap=0.6)
    if hi:
        t = NT('wool'); uv = t.sep(t.uv); u, v = uv[0], uv[1]; n = t.noise(1.0, 5, 0.65, vec=t.comb(t.math('MULTIPLY', u, 9.0), t.math('MULTIPLY', v, 7.0), 0.0))
        weave = t.math('MULTIPLY', t.math('SINE', t.math('MULTIPLY', u, 2600.0)), t.math('SINE', t.math('MULTIPLY', v, 1900.0))); ed = t.math('MINIMUM', t.math('MINIMUM', t.math('MULTIPLY', u, w), t.math('MULTIPLY', t.math('SUBTRACT', 1.0, u), w)), t.math('MINIMUM', t.math('MULTIPLY', v, h), t.math('MULTIPLY', t.math('SUBTRACT', 1.0, v), h)))
        braid = t.math('MULTIPLY', t.maprange(ed, 0.02, 0.025, 0.0, 1.0), t.maprange(ed, 0.075, 0.08, 1.0, 0.0)); tw = t.math('SINE', t.math('MULTIPLY', t.math('ADD', t.math('MULTIPLY', u, w), t.math('MULTIPLY', v, h)), 420.0))
        red = t.mix(n, (0.20, 0.010, 0.010), (0.42, 0.030, 0.022)); fade = t.ramp(t.noise(1.0, 4, 0.7, vec=t.comb(t.math('MULTIPLY', u, 3.0), t.math('MULTIPLY', v, 2.0), 5.0)), [(0.55, 0.0), (0.75, 1.0)]); red = t.mix(t.math('MULTIPLY', fade, 0.35), red, (0.36, 0.12, 0.08))
        gold = t.mix(t.maprange(tw, -1, 1, 0, 1), (0.30, 0.19, 0.035), (0.70, 0.50, 0.14)); base = t.mix(braid, red, gold)
        t.set(base=base, rough=t.mixf(braid, 0.85, 0.5), metal=t.mixf(braid, 0.0, 0.35), normal=t.bump(t.math('ADD', t.math('MULTIPLY', weave, 0.5), t.math('MULTIPLY', t.math('MULTIPLY', braid, tw), 1.2)), 0.35, 0.0006), sheen=0.4)
        cl.data.materials.append(t.mat); rod.data.materials.append(T.wood_mat('rod', axis=0, light=(0.20, 0.11, 0.05), dark=(0.07, 0.035, 0.015)))
    else:
        L.smart_uv(cl, angle=60, margin=0.01)
    return [cl, rod]


# ---------------------------------------------------------------------------------------------- throwing axe, hatch, wheel, barrel
def axe2(hi, c):
    """double-bitted throwing axe, 80 cm, lying flat: two crescent blades on a round eye, ash haft with a leather-wrapped grip"""
    q = 4 if hi else 1; z = 0.016
    head = L.sweep('head', [(0.30, -0.155, z, 0.092, 0.0008, 3), (0.30, -0.12, z, 0.078, 0.004, 3), (0.30, -0.05, z, 0.034, 0.011, 3.5), (0.30, 0.0, z, 0.03, 0.0155, 4), (0.30, 0.05, z, 0.034, 0.011, 3.5), (0.30, 0.12, z, 0.078, 0.004, 3), (0.30, 0.155, z, 0.092, 0.0008, 3)],
                   nu=16 * q, nv=24 * q, c=c, up=(0, 0, 1), cap=0.25)
    haft = L.sweep('haft', [(-0.45, 0, 0.0135, 0.016, 0.013, 2.3), (-0.42, 0, 0.0135, 0.0185, 0.014, 2.3), (-0.2, 0, 0.014, 0.0145, 0.012, 2.3), (0.2, 0, z, 0.015, 0.012, 2.3), (0.345, 0, z, 0.0155, 0.011, 2.6)], nu=12 * q, nv=20 * q, c=c, up=(0, 0, 1), cap=0.7)
    grip = L.sweep('grip', [(-0.41, 0, 0.0135, 0.0195, 0.0152, 2.3), (-0.3, 0, 0.0137, 0.0175, 0.014, 2.3), (-0.2, 0, 0.014, 0.0165, 0.0135, 2.3)], nu=12 * q, nv=10 * q, c=c, up=(0, 0, 1), cap=0.9)
    if hi:
        L.displace_np(head, lambda Q: 0.0003 * fbm(Q, 3, 60, 3)); head.data.materials.append(T.iron_mat('iron', rust=0.35, seed=11.0)); haft.data.materials.append(T.wood_mat('ash', axis=0, dark_from=(0.2, 0.28)))
        t = NT('leather'); sp = t.sep(t.obj); wrap = t.math('SINE', t.math('ADD', t.math('MULTIPLY', sp[0], 520.0), t.math('MULTIPLY', t.math('ARCTAN2', sp[2], sp[1]), 1.0))); n = t.noise(120, 4, 0.6)
        t.set(base=t.mix(n, (0.035, 0.018, 0.009), (0.10, 0.052, 0.024)), rough=t.mixf(n, 0.4, 0.65), normal=t.bump(wrap, 0.8, 0.0012)); grip.data.materials.append(t.mat)
    return [head, haft, grip]


def hatch(hi, c):
    """cellar hatch set in the floor, 0.95 x 1.5 m: oak frame, five ledged planks, two iron strap hinges, a barred light and a ring pull"""
    wm = [T.wood_mat('oak_%s' % 'xyz'[a], axis=a, light=(0.15, 0.085, 0.036), dark=(0.05, 0.026, 0.011)) for a in range(3)] if hi else [None] * 3; im = T.iron_mat('iron', rust=0.6, seed=13.0) if hi else None; parts = []

    def bd(name, mn, mx, seed, mat=None, bev=0.005):
        d = np.abs(np.array(mx) - np.array(mn)); o = L.box(name, mn, mx, c, hi, bevel=bev, warp=0.002, seed=seed)
        if hi:
            o.data.materials.append(mat or wm[int(np.argmax(d))])
        parts.append(o)
    W, Ln = 0.95, 1.5
    bd('fr_l', (-W / 2 - 0.09, -Ln / 2 - 0.09, 0), (-W / 2, Ln / 2 + 0.09, 0.05), 1); bd('fr_r', (W / 2, -Ln / 2 - 0.09, 0), (W / 2 + 0.09, Ln / 2 + 0.09, 0.05), 2); bd('fr_b', (-W / 2, -Ln / 2 - 0.09, 0), (W / 2, -Ln / 2, 0.05), 3); bd('fr_t', (-W / 2, Ln / 2, 0), (W / 2, Ln / 2 + 0.09, 0.05), 4)
    for k in range(5):
        x0 = -W / 2 + 0.004 + k * (W - 0.008) / 5
        if k == 2:                                             # the middle plank is cut for the barred light
            bd('plank2a', (x0, -Ln / 2 + 0.004, 0.004), (x0 + (W - 0.008) / 5 - 0.004, 0.05, 0.042), 12); bd('plank2b', (x0, 0.33, 0.004), (x0 + (W - 0.008) / 5 - 0.004, Ln / 2 - 0.004, 0.042), 13)
        else:
            bd('plank%d' % k, (x0, -Ln / 2 + 0.004, 0.004), (x0 + (W - 0.008) / 5 - 0.004, Ln / 2 - 0.004, 0.042), 10 + k)
    for k, y in enumerate((-0.52, 0.55)):
        bd('strap%d' % k, (-W / 2 - 0.07, y - 0.025, 0.04), (W / 2 - 0.08, y + 0.025, 0.05), 20 + k, mat=im, bev=0.003)
    for k in range(4):
        bd('bar%d' % k, (-0.086 + k * 0.05, 0.05, 0.02), (-0.074 + k * 0.05, 0.33, 0.034), 30 + k, mat=im, bev=0.004)
    bd('void', (-0.092, 0.05, -0.02), (0.092, 0.33, 0.006), 40, mat=None)
    if hi:
        d = NT('dark'); d.set(base=(0.004, 0.004, 0.004), rough=1.0); L.assign(parts[-1], d.mat)
    rg = L.ring('pull', 0.05, 0.007, c, seg=32 if hi else 10, sides=8 if hi else 4); L.xform(rg, Matrix.Translation((0.28, -0.3, 0.05)) @ Matrix.Rotation(math.radians(12), 4, 'X'))
    if hi:
        rg.data.materials.append(im)
    parts.append(rg); return parts


def wheel(hi, c):
    """spinning wheel, 1.2 m tall: a twelve-spoke wheel on two uprights, a sloping three-legged bench, the spindle head with its flyer, a treadle and footman"""
    q = 4 if hi else 1; parts = []; wm = T.wood_mat('beech', axis=0, light=(0.26, 0.15, 0.065), dark=(0.10, 0.052, 0.022)) if hi else None

    def sw(name, rows, nu=8, nv=6, up=(0, 1, 0), cap=0.6):
        o = L.sweep(name, rows, nu=nu * q, nv=nv * q, c=c, up=up, cap=cap)
        if hi:
            o.data.materials.append(wm)
        parts.append(o); return o
    cz = 0.78; cx = -0.22; R = 0.36
    rim = L.ring('rim', R, 0.024, c, seg=72 if hi else 24, sides=10 if hi else 5, squash=0.75); L.xform(rim, Matrix.Translation((cx, 0, cz)) @ Matrix.Rotation(math.pi / 2, 4, 'X')); parts.append(rim)
    if hi:
        rim.data.materials.append(wm)
    for k in range(12):
        a = k * math.pi / 6; sw('spoke%d' % k, [(cx + 0.045 * math.cos(a), 0, cz + 0.045 * math.sin(a), 0.011, 0.011, 2), (cx + 0.2 * math.cos(a), 0, cz + 0.2 * math.sin(a), 0.008, 0.008, 2), (cx + (R - 0.01) * math.cos(a), 0, cz + (R - 0.01) * math.sin(a), 0.011, 0.011, 2)], nu=6, nv=4)
    sw('hub', [(cx, -0.06, cz, 0.02, 0.02, 2), (cx, -0.035, cz, 0.05, 0.05, 2), (cx, 0.035, cz, 0.05, 0.05, 2), (cx, 0.06, cz, 0.02, 0.02, 2)], nu=10, nv=6, up=(0, 0, 1))
    sw('axle', [(cx, -0.1, cz, 0.008, 0.008, 2), (cx, 0.1, cz, 0.008, 0.008, 2), (cx, 0.13, cz - 0.03, 0.008, 0.008, 2)], nu=6, nv=5, up=(0, 0, 1))
    for sy in (-1, 1):
        sw('upright%d' % sy, [(cx + 0.02, sy * 0.085, 0.36, 0.022, 0.022, 2.2), (cx + 0.005, sy * 0.085, 0.6, 0.017, 0.017, 2.1), (cx, sy * 0.085, cz + 0.02, 0.02, 0.02, 2.1), (cx, sy * 0.085, cz + 0.06, 0.012, 0.012, 2)], nu=8, nv=8)
    sw('bench', [(-0.42, 0, 0.3, 0.095, 0.022, 6), (0.0, 0, 0.42, 0.095, 0.024, 6), (0.42, 0, 0.54, 0.085, 0.022, 6)], nu=10, nv=8, up=(0, 0, 1), cap=0.9)
    for k, (x, y, zt) in enumerate(((-0.36, 0.0, 0.3), (0.34, -0.07, 0.5), (0.34, 0.07, 0.5))):
        sw('leg%d' % k, [(x, y, zt, 0.02, 0.02, 2.1), (x + (0.0 if k else -0.1), y * 2.4, zt * 0.45, 0.024, 0.024, 2.1), (x + (0.03 if k else -0.18), y * 3.6, 0.0, 0.016, 0.016, 2.1)], nu=8, nv=6)
    for sy in (-1, 1):
        sw('maiden%d' % sy, [(0.36, sy * 0.06, 0.54, 0.017, 0.017, 2.1), (0.37, sy * 0.06, 0.7, 0.013, 0.013, 2.1), (0.37, sy * 0.06, 0.82, 0.018, 0.018, 2.1), (0.37, sy * 0.06, 0.86, 0.008, 0.008, 2)], nu=8, nv=7)
    sw('flyer', [(0.37, -0.075, 0.76, 0.006, 0.006, 2), (0.37, 0.0, 0.76, 0.022, 0.022, 2), (0.37, 0.075, 0.76, 0.006, 0.006, 2)], nu=8, nv=6, up=(0, 0, 1))
    sw('treadle', [(-0.3, 0.16, 0.06, 0.05, 0.01, 6), (0.0, 0.16, 0.09, 0.05, 0.01, 6), (0.2, 0.16, 0.12, 0.045, 0.01, 6)], nu=8, nv=5, up=(0, 0, 1), cap=0.9)
    sw('footman', [(-0.2, 0.15, 0.08, 0.006, 0.006, 2), (cx + 0.02, 0.135, 0.4, 0.006, 0.006, 2), (cx, 0.13, cz - 0.03, 0.007, 0.007, 2)], nu=6, nv=6)
    return parts


def barrel_broken(hi, c):
    """a smashed barrel: fourteen oak staves splayed where it burst, two halves of a head, a sprung iron hoop in two pieces"""
    rng = np.random.default_rng(8); parts = []; q = 4 if hi else 1; wm = T.wood_mat('oak', axis=0, light=(0.22, 0.125, 0.055), dark=(0.075, 0.04, 0.018)) if hi else None; im = T.iron_mat('hoop', rust=0.75, seed=17.0) if hi else None
    for k in range(14):
        a = k * 2 * math.pi / 14 + rng.normal(0, 0.16); ln = rng.uniform(0.62, 0.8); d0 = rng.uniform(0.02, 0.16); wd = rng.uniform(0.04, 0.055); lift = rng.uniform(0.0, 0.05); bow = rng.uniform(0.02, 0.05)
        rows = [(d0, 0, 0.012 + lift, wd * 0.8, 0.009, 5), (d0 + ln * 0.5, 0, 0.012 + bow + lift * 0.5, wd, 0.0095, 5), (d0 + ln, 0, 0.011, wd * 0.8, 0.009, 5)]
        o = L.sweep('stave%d' % k, rows, nu=8 * q if hi else 6, nv=10 * q if hi else 10, c=c, up=(0, 0, 1), cap=0.85); L.xform(o, Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(rng.normal(0, 0.12), 4, 'X'))
        Pq = L.co(o); Pq[:, 2] -= min(0.0, Pq[:, 2].min()); L.set_co(o, Pq)
        if hi:
            o.data.materials.append(wm)
        parts.append(o)
    for k, (x, y, a) in enumerate(((0.06, 0.02, 0.4), (-0.1, -0.12, 2.6))):                          # the head, split across
        o = L.sweep('head%d' % k, [(-0.2, 0, 0.03, 0.02, 0.009, 5), (-0.1, 0.0, 0.03, 0.14, 0.009, 5), (0.1, 0.0, 0.03, 0.14, 0.009, 5), (0.2, 0, 0.03, 0.02, 0.009, 5)], nu=8 * q if hi else 6, nv=8 * q if hi else 10, c=c, up=(0, 0, 1), cap=0.8)
        L.xform(o, Matrix.Translation((x, y, 0.012 + 0.02 * k)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(0.12 * (1 - 2 * k), 4, 'Y'))
        if hi:
            o.data.materials.append(wm)
        parts.append(o)
    for k, (a0, a1, R_, x, y) in enumerate(((0.3, 3.6, 0.3, 0.1, 0.05), (3.9, 5.6, 0.34, -0.12, 0.1))):
        rows = [(x + R_ * math.cos(a), y + R_ * math.sin(a) * 0.8, 0.03 + 0.03 * math.sin(a * 2 + k), 0.016, 0.0016, 5) for a in np.linspace(a0, a1, 9)]
        o = L.sweep('hoop%d' % k, rows, nu=8 if hi else 4, nv=60 if hi else 20, c=c, up=(0, 0, 1), cap=0.9)
        if hi:
            o.data.materials.append(im)
        parts.append(o)
    return parts


# ---------------------------------------------------------------------------------------------- carved rock, shrine
def monument(hi, c):
    """the "Dink Smallwood" rock: a 2.5 m boulder with the name cut into its face in two lines"""
    rock = P.boulder('rock', (2.5, 1.5, 2.1), 23, c, hi, rough_amp=0.14, round_=0.75, sink=0.08, sub=7 if hi else 5)
    if hi:
        cut = []
        for k, (txt, size, z) in enumerate((('Dink', 0.5, 1.22), ('Smallwood', 0.27, 0.78))):
            hit = C.surface_hit(rock, (0.0, -5.0, z + size * 0.3), (0, 1, 0)); y0 = (hit[0][1] if hit else -0.6)
            tx = L.text_mesh('cut%d' % k, txt, size=size, depth=0.5, c=c, spacing=1.05); L.xform(tx, Matrix.Translation((0.0, y0 + 0.08, z)) @ UPRIGHT); cut.append(tx)
        cutter = L.join(cut, 'cutter'); m = rock.modifiers.new('carve', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter; m.solver = 'EXACT'; L.apply_mods(rock); bpy.data.objects.remove(cutter)
        rock.data.polygons.foreach_set('use_smooth', [True] * len(rock.data.polygons))
        try:
            rock.data.set_sharp_from_angle(angle=math.radians(50))
        except Exception:
            pass
        L.assign(rock, P.rock_mat('rock', 'rock_boulder_dry', tint=(0.66, 0.62, 0.56), value=0.75, sat=0.6, moss=0.45, lichen=0.4, seed=7.0))
    return [rock]


def shrine(hi, c):
    """wayside shrine, 2.4 m: a three-sided alcove of sandstone blocks on a plinth under a cornice, a stained-glass light in the back wall"""
    m = [P3.stone(80 + k, tint=(0.80, 0.76 + 0.03 * k, 0.60), value=0.9, sat=0.55, moss=0.35) for k in range(3)] if hi else [None] * 3; parts = []; Wb, D, H, crs = 1.5, 0.3, 0.34, 6

    def wall(tag, x0, x1, M, seed):
        n = 3 if x1 - x0 > 1.0 else 2
        for k in range(crs):
            xs = np.linspace(x0, x1, n + 1) if k % 2 == 0 else np.r_[x0, np.linspace(x0 + (x1 - x0) / n / 2, x1 - (x1 - x0) / n / 2, n), x1]
            for i in range(len(xs) - 1):
                if tag == 'back' and 1 <= k <= 3 and xs[i] < 0.26 and xs[i + 1] > -0.26:             # leave the window opening
                    for (a, b) in ((xs[i], min(xs[i + 1], -0.26)), (max(xs[i], 0.26), xs[i + 1])):
                        if b - a > 0.03:
                            o = P3.blocks(parts, tag, (a + 0.003, -D / 2, 0.2 + k * H), (b - 0.003, D / 2, 0.2 + (k + 1) * H - 0.006), c, hi, m[(k + i) % 3], seed=seed + k * 5 + i); L.xform(o, M)
                    continue
                o = P3.blocks(parts, tag, (xs[i] + 0.003, -D / 2, 0.2 + k * H), (xs[i + 1] - 0.003, D / 2, 0.2 + (k + 1) * H - 0.006), c, hi, m[(k + i) % 3], seed=seed + k * 5 + i); L.xform(o, M)
    wall('back', -Wb / 2, Wb / 2, Matrix.Translation((0, 0.35, 0)), 100)
    for s in (-1, 1):
        M = Matrix.Translation((s * Wb / 2, 0.35, 0)) @ Matrix.Rotation(s * math.radians(-52), 4, 'Z') @ Matrix.Translation((s * 0.42, 0, 0)); wall('wing', -0.42, 0.42, M, 200 + 50 * s)
    P3.blocks(parts, 'plinth', (-Wb / 2 - 0.62, -0.42, 0), (Wb / 2 + 0.62, 0.56, 0.2), c, hi, m[0], seed=300, bevel=0.02); P3.blocks(parts, 'cornice', (-Wb / 2 - 0.1, 0.16, 0.2 + crs * H), (Wb / 2 + 0.1, 0.56, 0.2 + crs * H + 0.16), c, hi, m[1], seed=301, bevel=0.02)
    for s in (-1, 1):
        o = P3.blocks(parts, 'cornice_w', (-0.5, -0.2, 0.2 + crs * H), (0.5, 0.2, 0.2 + crs * H + 0.16), c, hi, m[2], seed=302 + s, bevel=0.02); L.xform(o, Matrix.Translation((s * Wb / 2, 0.35, 0)) @ Matrix.Rotation(s * math.radians(-52), 4, 'Z') @ Matrix.Translation((s * 0.42, 0, 0)))
    g = L.box('glass', (-0.262, 0.33, 0.2 + H - 0.004), (0.262, 0.37, 0.2 + 4 * H), c, hi, bevel=0.002, warp=0.001, seed=400); parts.append(g)
    if hi:
        t = NT('stained'); sp = t.sep(t.obj); a = t.math('MULTIPLY', t.math('ADD', sp[0], t.math('MULTIPLY', sp[2], 0.8)), 9.0); b = t.math('MULTIPLY', t.math('SUBTRACT', sp[0], t.math('MULTIPLY', sp[2], 0.8)), 9.0)
        la = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', a), 0.5)), [(0.43, 0.0), (0.47, 1.0)]); lb = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', b), 0.5)), [(0.43, 0.0), (0.47, 1.0)]); lead = t.math('MAXIMUM', la, lb)
        cid = t.sep(t.voronoi(1.0, vec=t.comb(t.math('FLOOR', a), t.math('FLOOR', b), 0.0), out='Color')); n = t.noise(40, 4, 0.6)
        col = t.ramp(cid[0], [(0.0, (0.30, 0.012, 0.010)), (0.3, (0.012, 0.035, 0.22)), (0.55, (0.36, 0.22, 0.02)), (0.78, (0.02, 0.14, 0.05)), (1.0, (0.30, 0.012, 0.010))], interp='CONSTANT'); col = t.hsv(col, v=t.maprange(n, 0.2, 0.8, 0.7, 1.3))
        base = t.mix(lead, col, t.mix(n, (0.04, 0.042, 0.045), (0.11, 0.115, 0.12))); t.set(base=base, rough=t.mixf(lead, t.mixf(n, 0.05, 0.25), 0.55), metal=t.mixf(lead, 0.0, 0.85), normal=t.bump(t.math('ADD', lead, t.math('MULTIPLY', cid[1], 0.5)), 0.6, 0.003), spec=0.7)
        g.data.materials.append(t.mat)
    return parts


W_PAPER = ' The body text is a generated pattern of broken pen strokes, not writing: it reads as script at the gameplay camera and as scribble at 1 m. The title is set in Blender\'s built-in sans face, not a period hand. A flat sheet of 100 triangles with curl at the corners.'
SPECS = {
    'Notice_Hark': dict(fn=hark, fam='poster_hark', seq='462 inner/poster frame 3', cls='prop', px=1024, tris=0, lo='param', ground='weathered_brown_planks', third=['rusty_metal_02'], extrude=0.024, maxdist=0.034, shot=dict(az=8, el=6, fill=1.05, close=(0.5, 0.0, 0.75, 0.22)),
                        weak='Authored standing free for the render; in game it hangs on a wall (the back face is plain vellum).' + W_PAPER, dresses='the "Hark!" notice: a vellum sheet, 46 x 64 cm, red title, eleven lines of script, two nails'),
    'Notice_Wanted': dict(fn=wanted, fam='poster_wanted', seq='462 inner/poster frame 2', cls='prop', px=1024, tris=0, lo='param', ground='weathered_brown_planks', third=['rusty_metal_02'], extrude=0.024, maxdist=0.034, shot=dict(az=8, el=6, fill=1.05, close=(0.5, 0.0, 0.5, 0.25)),
                          weak='The portrait is a hatched block with a head-and-shoulders silhouette, not a drawn face.' + W_PAPER, dresses='the "Wanted" poster: a vellum sheet, 46 x 64 cm, a woodcut portrait block, two lines of script and the title below'),
    'Note_Floor': dict(fn=note, fam='scroll_note', seq='422 items/paper/paper- frame 1', cls='prop_small', px=512, tris=0, lo='param', ground='weathered_brown_planks', third=[], extrude=0.002, maxdist=0.006,
                       weak='Rolled ends are a 1.5-turn curl of the same sheet; the script is a generated stroke pattern. No seal, ribbon or creases.', dresses='a note on the floor: a vellum sheet 34 x 24 cm with both ends rolled, nine lines of script'),
    'Banner_Red': dict(fn=banner, fam='wall_stripe_red', seq='450 inter/health/hm-br- frames 1, 2', cls='prop', px=1024, tris=0, lo='param', ground='weathered_brown_planks', third=[], extrude=0.008, maxdist=0.02, shot=dict(az=10, el=6, fill=1.1, close=(0.3, 0.0, 0.3, 0.2)),
                       weak='The original is a flat red bar with a gold edge taken from the health-bar art; it is interpreted here as a red wall hanging with a gold braid border on a rod. Folds are a fixed sine pattern, not simulated cloth, and the back is the same cloth. No fringe or device.',
                       dresses='red wool wall hanging, 1.2 x 0.85 m, gold braid border, hung from a turned wooden rod, soft folds'),
    'Axe_Throwing': dict(fn=axe2, fam='axe_item', seq='85 effects/axe/wpn02- frame 9', cls='prop', px=1024, tris=1500, ground='forrest_ground_01', third=['rusty_metal_02'], extrude=0.0015, maxdist=0.005, shot=dict(az=22, el=34, fill=0.95, close=(0.85, 0.5, 0.5, 0.22)),
                         weak='Head and haft are swept solids pushed together, with no eye or wedge. The blades are symmetric crescents with a plain rust-and-patina surface: no ground bevel line. The thrown-weapon version in flight is an effect, not this prop.',
                         dresses='double-bitted throwing axe, 80 cm, lying flat: two crescent blades, ash haft, leather-wrapped grip'),
    'Cellar_Hatch': dict(fn=hatch, fam='cellar_hatch', seq='428 inside/stairs/stair- frame 5', cls='prop', px=1024, tris=0, lo='param', ground='weathered_brown_planks', third=['rusty_metal_02'], extrude=0.003, maxdist=0.01, shot=dict(az=24, el=44, fill=0.95, close=(0.5, 0.6, 0.5, 0.2)),
                         weak='A closed hatch only: it does not open, and there is no ladder or shaft below (the original frame hints at one through the barred light, which here is a black recess). Boards are bevelled blocks without nails; strap hinges have no knuckles.',
                         dresses='cellar hatch in the floor, 1.1 x 1.7 m over the frame: oak frame, five planks, two iron straps, a barred light, a ring pull'),
    'Spinning_Wheel': dict(fn=wheel, fam='spinning_wheel', seq='447 items/tools/tool- frame 4', cls='prop', px=1024, tris=4500, ground='weathered_brown_planks', third=[], shot=dict(az=35, el=14, fill=1.1, close=(0.3, 0.5, 0.65, 0.25)),
                           weak='Turned parts are smooth sweeps without beads or coves; joints are parts pushed through each other. No drive band, bobbin, distaff or wool. One wood material with grain along world X for every part.',
                           dresses='spinning wheel, 1.15 m tall: twelve-spoke wheel on two uprights, sloping three-legged bench, maidens and flyer, treadle and footman'),
    'Barrel_Smashed': dict(fn=barrel_broken, fam='barrel_broken', seq='173 bonuses/barrels/barel- frame 6', cls='prop', px=1024, tris=0, lo='param', ground='forrest_ground_01', third=['rusty_metal_02'], extrude=0.006, maxdist=0.016, shot=dict(az=25, el=34, fill=0.9),
                           weak='Staves are clean bowed boards laid out by rule: no splintered ends, no croze groove, and they do not rest on each other physically. This is the end state only; the break itself is an animation in the original. One wood material with grain along world X.',
                           dresses='a smashed barrel: fourteen oak staves splayed in a 1.7 m star, the split head, two pieces of a sprung iron hoop'),
    'Monument_Dink': dict(fn=monument, fam='dink_monument_rock', seq='159 struct/stone/mdink/monum- frame 4', cls='prop', px=2048, tris=4000, ground='forrest_ground_01', third=['rock_boulder_dry'], shot=dict(az=12, el=10, fill=1.05, close=(0.5, 0.0, 0.5, 0.3)),
                          weak='The name is cut with Blender\'s built-in sans face as a straight boolean cut, so the letters have vertical walls and no chisel V or weathered edges; the original lettering is a heavy gothic. The rock is a displaced sphere with break planes.' + P3.W_STONE,
                          dresses='the "Dink Smallwood" rock: a grey boulder 2.3 m wide and 1.9 m tall with DINK and SMALLWOOD cut into its face in two lines'),
    'Shrine_Glass': dict(fn=shrine, fam='teleport_shrine', seq='159 struct/stone/mdink/monum- frame 7', cls='prop_large', px=2048, tris=0, lo='param', ground='forrest_ground_01', third=['rock_face_03'], extrude=0.008, maxdist=0.025, shot=dict(az=18, el=12, fill=1.05, close=(0.5, 0.3, 0.5, 0.22)),
                         weak='Blocks are bevelled boxes of 12 triangles with open joints; the stained glass is an opaque coloured lattice (no transmission, no emissive glow, and the original glows when it teleports). The cornice is three plain slabs. One convex hull covers the alcove.' + P3.W_STONE,
                         dresses='stained-glass shrine (teleporter): a three-sided sandstone alcove 2.9 m wide and 2.4 m tall on a plinth, six courses under a cornice, a leaded light of red, blue, amber and green quarries in the back wall'),
}
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
