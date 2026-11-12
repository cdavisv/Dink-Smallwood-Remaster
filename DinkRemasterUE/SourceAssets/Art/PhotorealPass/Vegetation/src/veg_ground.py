"""Ground cover generators: grass tufts, broadleaf weeds, wildflower clumps, mushrooms. One shared atlas (T_Veg_GroundCover)."""
import numpy as np, math
from bl_tree import *

def R(x0, y0, x1, y1, pad=2):
    return ((x0 + pad) / 1024, 1 - (y1 - pad) / 1024, (x1 - pad) / 1024, 1 - (y0 + pad) / 1024)
STRIP = [R(i * 64, 0, i * 64 + 64, 1024, 3) for i in range(4)]
SEED = R(256, 0, 512, 512); DOCK = R(512, 0, 768, 512); PLANT = R(768, 0, 1024, 512); NETTLE = R(256, 512, 512, 1024)
DAISY = R(512, 512, 768, 768); BUTTER = R(768, 512, 1024, 768)
CAPA = R(512, 768, 640, 1024); CAPB = R(640, 768, 768, 1024); STEM = R(768, 768, 896, 1024); GILL = R(896, 768, 1024, 1024)
UP = np.array([0, 0, 1.0])

def blade(mb, base, yaw, lean0, curve, length, width, strip, segs, crease, twist, phase, vspan=(0.0, 1.0)):
    out = np.array([math.cos(yaw), math.sin(yaw), 0]); side0 = np.array([-math.sin(yaw), math.cos(yaw), 0])
    u0, v0, u1, v1 = strip; p = np.array(base, float); V = []; Nn = []; UVs = []; W = []; F = []
    cols = 3 if crease else 2
    for j in range(segs + 1):
        t = j / segs; ang = lean0 + curve * t ** 1.6
        d = UP * math.cos(ang) + out * math.sin(ang)
        if j > 0: p = p + d * length / segs
        tw = twist * t; nb = np.cross(side0, d); side = side0 * math.cos(tw) + nb * math.sin(tw); nb = np.cross(side, d)
        wj = width * max(0.04, (1 - t ** 2.4)) * (0.75 + 0.25 * min(1, t * 5))
        vv = v0 + (v1 - v0) * (vspan[0] + (vspan[1] - vspan[0]) * t)
        nsoft = nrm(nb * 0.5 + UP * 0.9)
        if crease:
            V += [p - side * wj / 2, p - nb * crease * wj, p + side * wj / 2]; UVs += [(u0, vv), ((u0 + u1) / 2, vv), (u1, vv)]
            Nn += [nrm(nsoft - side * 0.5), nsoft, nrm(nsoft + side * 0.5)]
        else:
            V += [p - side * wj / 2, p + side * wj / 2]; UVs += [(u0, vv), (u1, vv)]; Nn += [nrm(nsoft - side * 0.4), nrm(nsoft + side * 0.4)]
        W += [(0, phase, t * t, 0)] * cols
    for j in range(segs):
        for c in range(cols - 1):
            a = j * cols + c; F.append((a, a + 1, a + cols + 1, a + cols))
    mb.poly(V, Nn, UVs, 0, W, F)
    return p

def leaf(mb, base, yaw, elev0, curl, length, width, rect, segs=4, cols=2, fold=0.18, roll=0.0, phase=0.0, wave=0.0):
    out = np.array([math.cos(yaw), math.sin(yaw), 0]); side0 = np.array([-math.sin(yaw), math.cos(yaw), 0])
    u0, v0, u1, v1 = rect; p = np.array(base, float); V = []; Nn = []; UVs = []; W = []; F = []
    for j in range(segs + 1):
        t = j / segs; el = elev0 - curl * t ** 1.5
        d = out * math.cos(el) + UP * math.sin(el)
        if j > 0: p = p + d * length / segs
        nb = np.cross(side0, d); nb = nb if nb[2] > 0 else -nb
        side = side0 * math.cos(roll) + nb * math.sin(roll); nb2 = np.cross(d, side); nb2 = nb2 if nb2[2] > 0 else -nb2
        for c in range(cols + 1):
            x = c / cols - 0.5
            wv = wave * width * math.sin(t * 11 + c * 2.0) * abs(x) * 2
            V.append(p + side * x * width + nb2 * (fold * abs(x) * width + wv)); UVs.append((u0 + (u1 - u0) * (c / cols), v0 + (v1 - v0) * t))
            Nn.append(nrm(nb2 * 0.7 + UP * 0.5 + side * x * 0.6)); W.append((0, phase, t * (0.4 + abs(x)), 0))
    C = cols + 1
    for j in range(segs):
        for c in range(cols):
            a = j * C + c; F.append((a, a + 1, a + C + 1, a + C))
    mb.poly(V, Nn, UVs, 0, W, F)

def stem(mb, pts, r0, r1, rect=None, sides=3, vspan=(0.3, 0.7), phase=0.0, h=1.0):
    rect = rect or STRIP[0]; u0, v0, u1, v1 = rect; n = len(pts); V = []; Nn = []; UVs = []; W = []; F = []
    for i in range(n):
        d = nrm(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]); a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
        u = nrm(np.cross(d, a)); w = np.cross(d, u); t = i / (n - 1); r = r0 + (r1 - r0) * t
        for k in range(sides + 1):
            ang = 2 * math.pi * k / sides; o = math.cos(ang) * u + math.sin(ang) * w
            V.append(pts[i] + o * r); Nn.append(o); UVs.append((u0 + (u1 - u0) * k / sides, v0 + (v1 - v0) * (vspan[0] + (vspan[1] - vspan[0]) * t)))
            W.append((0, phase, (pts[i][2] / h) ** 2 * 0.6, 0))
    S = sides + 1
    for i in range(n - 1):
        for k in range(sides):
            a = i * S + k; F.append((a, a + 1, a + S + 1, a + S))
    mb.poly(V, Nn, UVs, 0, W, F)

def disc(mb, c, n, radius, rect, cup=0.15, sides=6, phase=0.0, spin=0.0):
    n = nrm(n); a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0]); u = nrm(np.cross(n, a)); w = np.cross(n, u)
    u0, v0, u1, v1 = rect; cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    V = [np.array(c)]; Nn = [n]; UVs = [(cu, cv)]; F = []
    for k in range(sides):
        ang = 2 * math.pi * k / sides + spin; o = math.cos(ang) * u + math.sin(ang) * w
        V.append(np.array(c) + o * radius + n * cup * radius); Nn.append(nrm(n + o * 0.5))
        UVs.append((cu + math.cos(ang - spin) * (u1 - u0) / 2, cv + math.sin(ang - spin) * (v1 - v0) / 2))
    for k in range(sides): F.append((0, 1 + k, 1 + (k + 1) % sides))
    mb.poly(V, Nn, UVs, 0, (0, phase, 0.5, 0), F)

def revolve(mb, c, axis, prof, rect, sides, wob=0.0, wph=0.0, squash=1.0):
    """prof: list of (radius, height along axis, v 0..1). u = angle."""
    axis = nrm(axis); a = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0]); u = nrm(np.cross(axis, a)); w = np.cross(axis, u)
    u0, v0, u1, v1 = rect; V = []; Nn = []; UVs = []; F = []; S = sides + 1
    for i, (r, z, v) in enumerate(prof):
        j0 = max(i - 1, 0); j1 = min(i + 1, len(prof) - 1); dr = prof[j1][0] - prof[j0][0]; dz = prof[j1][1] - prof[j0][1]
        for k in range(S):
            ang = 2 * math.pi * k / sides; o = math.cos(ang) * u * squash + math.sin(ang) * w
            rr = r * (1 + wob * math.sin(3 * ang + wph) + 0.5 * wob * math.sin(5 * ang + 2 * wph))
            V.append(np.array(c) + o * rr + axis * z); Nn.append(nrm(o * dz - axis * dr + 1e-9 * o)); UVs.append((u0 + (u1 - u0) * k / sides, v1 - (v1 - v0) * v))
    for i in range(len(prof) - 1):
        for k in range(sides):
            a_ = i * S + k; F.append((a_, a_ + 1, a_ + S + 1, a_ + S))
    mb.poly(V, Nn, UVs, 0, (0, 0, 0, 0), F)

def head3d(mb, c, n, radius, rng, kind='daisy', npet=13, phase=0.0):
    """flower head with real petals: cupped, in two staggered layers, round a domed centre"""
    n = nrm(n); a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0]); u = nrm(np.cross(n, a)); w = np.cross(n, u)
    rect = DAISY if kind == 'daisy' else BUTTER; u0, v0, u1, v1 = rect; cu, cv, hw, hh = (u0 + u1) / 2, (v0 + v1) / 2, (u1 - u0) / 2, (v1 - v0) / 2
    if kind == 'daisy': pu0, pu1, pv = cu + 0.29 * hw, cu + 0.86 * hw, 0.03 * hh; rin, wid, cupz, tipz = 0.2, 0.2, 0.10, -0.06; crad = 0.24
    else: pu0, pu1, pv = cu + 0.22 * hw, cu + 0.8 * hw, 0.22 * hh; rin, wid, cupz, tipz = 0.12, 0.95, 0.22, 0.42; crad = 0.2
    c = np.asarray(c, float)
    # centre: a low dome
    V = [c + n * radius * 0.1]; N = [n]; U = [(cu, cv)]; F = []
    for k in range(6):
        ang = k * math.pi / 3; o = math.cos(ang) * u + math.sin(ang) * w
        V.append(c + o * radius * crad); N.append(nrm(n * 0.6 + o)); U.append((cu + math.cos(ang) * hw * crad * 0.9, cv + math.sin(ang) * hh * crad * 0.9))
    F += [(0, 1 + k, 1 + (k + 1) % 6) for k in range(6)]
    mb.poly(V, N, U, 0, (0, phase, 0.3, 0), F)
    for k in range(npet):
        ang = 2 * math.pi * k / npet + rng.normal(0, 0.07); o = math.cos(ang) * u + math.sin(ang) * w; sd = np.cross(n, o); low = (k % 2) * 0.04
        L = radius * rng.uniform(0.85, 1.05); cz = cupz * rng.uniform(0.5, 1.4) - low; tz = tipz + rng.normal(0, 0.05) - low
        V = []; N = []; U = []
        for j, (t, wf, z) in enumerate(((0.0, 0.55, 0.0), (0.55, 1.0, cz), (1.0, 0.3, tz))):
            p = c + o * (radius * rin + (L - radius * rin) * t) + n * radius * z; hwid = radius * wid * 0.5 * wf
            V += [p - sd * hwid, p + sd * hwid]; nn = nrm(n + o * (0.5 - t)); N += [nrm(nn - sd * 0.4), nrm(nn + sd * 0.4)]
            uu = pu0 + (pu1 - pu0) * t; U += [(uu, cv - pv * wf), (uu, cv + pv * wf)]
        mb.poly(V, N, U, 0, (0, phase, 0.6, 0), [(0, 1, 3, 2), (2, 3, 5, 4)])

# ------------------------------------------------------------------ assets
GRASS = {
 'SM_Veg_Grass_Meadow_01': dict(seed=1, n=46, rad=0.10, L=(0.22, 0.52), lean=(0.05, 0.55), curve=(0.2, 1.3), w=(0.006, 0.011), dry=0.14, heads=0, thatch=8),
 'SM_Veg_Grass_Meadow_02': dict(seed=2, n=50, rad=0.12, L=(0.35, 0.85), lean=(0.03, 0.4), curve=(0.2, 1.5), w=(0.007, 0.012), dry=0.2, heads=6, thatch=8),
 'SM_Veg_Grass_Meadow_03': dict(seed=3, n=52, rad=0.16, L=(0.12, 0.34), lean=(0.15, 0.9), curve=(0.3, 1.2), w=(0.006, 0.010), dry=0.32, heads=0, thatch=12),
}
GLOD = {0: dict(keep=1.0, segs=4, crease=0.22, wmul=1.0), 1: dict(keep=0.5, segs=3, crease=0, wmul=1.5), 2: dict(keep=0.22, segs=2, crease=0, wmul=2.4)}

def build_grass(name, lod):
    P = GRASS[name]; C = GLOD[lod]; rng = np.random.default_rng(P['seed']); mb = MeshB()
    for i in range(P['n']):
        key = rng.random(); a = rng.uniform(0, 6.28); rr = P['rad'] * math.sqrt(rng.random())
        base = np.array([math.cos(a) * rr, math.sin(a) * rr, 0]); yaw = a + rng.normal(0, 0.9)
        L = rng.uniform(*P['L']) * (1.15 - 0.5 * rr / P['rad']); lean = rng.uniform(*P['lean']) * (0.4 + 0.6 * rr / P['rad'] + 0.2 * rng.random())
        dry = rng.random() < P['dry']; strip = STRIP[3 if (dry and rng.random() < 0.6) else (2 if dry else rng.integers(0, 2))]
        args = (base, yaw, lean, rng.uniform(*P['curve']) * (1.25 if dry else 1), L, rng.uniform(*P['w']) * C['wmul'] * (0.8 + 0.5 * L / P['L'][1]), strip, C['segs'], C['crease'], rng.normal(0, 0.7), rng.random())
        if key < C['keep']: blade(mb, *args)
    for i in range(P['thatch']):   # dead blades lying at the base hide the contact with the ground
        key = rng.random(); a = rng.uniform(0, 6.28); base = np.array([math.cos(a) * 0.03, math.sin(a) * 0.03, 0.004])
        args = (base, a + rng.normal(0, 0.8), rng.uniform(0.95, 1.45), rng.uniform(-0.25, 0.45), rng.uniform(0.07, 0.24), 0.008 * C['wmul'], STRIP[3 if rng.random() < 0.7 else 2], 3 if lod == 0 else 2, 0, rng.normal(0, 0.8), 0.0)
        if key < max(C['keep'], 0.4): blade(mb, *args)
    for i in range(P['heads']):
        key = rng.random(); a = rng.uniform(0, 6.28); rr = P['rad'] * 0.6 * rng.random(); base = np.array([math.cos(a) * rr, math.sin(a) * rr, 0])
        L = rng.uniform(0.6, 0.92); yaw = a + rng.normal(0, 0.5); lean = rng.uniform(0.03, 0.2); cv = rng.uniform(0.1, 0.45); ph = rng.random()
        tg = mb if key < max(C['keep'], 0.5) else MeshB()
        tip = blade(tg, base, yaw, lean, cv, L, 0.0035 * C['wmul'], STRIP[2], max(2, C['segs'] - 1), 0, 0, ph, vspan=(0.25, 0.6))
        hl = rng.uniform(0.2, 0.3); el = math.pi / 2 - (lean + cv) - 0.1
        leaf(tg, tip - UP * hl * 0.25, yaw, el, 0.5, hl, hl * 0.5, SEED, 2, 1, 0.0, rng.uniform(0, 3.1), ph)
    mb.v = [p for p in mb.v]; _fix_ground(mb)
    return mb.build(f'{name}_LOD{lod}', [gc_mat()])

def _fix_ground(mb):
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.0); mb.v = list(V); recenter(mb)

def gc_mat(): return game_mat('MI_Veg_GroundCover', 'T_Veg_GroundCover', alpha=True, translucency=0.3)

def build_weed(name, lod):
    rng = np.random.default_rng({'SM_Veg_Weed_Small_01': 5, 'SM_Veg_Weed_Small_02': 6, 'SM_Veg_Weed_Sprig_01': 7}[name]); mb = MeshB()
    segs = (4, 3, 2)[lod]; cols = (2, 1, 1)[lod]; keep = (1.0, 0.75, 0.5)[lod]; sc = (1.0, 1.1, 1.3)[lod]
    if name == 'SM_Veg_Weed_Small_01':     # plantain / dandelion-type rosette with two seed spikes
        n = 11
        for i in range(n):
            a = i * 2.4 + rng.normal(0, 0.2); L = rng.uniform(0.13, 0.24) * sc; inner = i > n * 0.6
            leaf(mb if rng.random() < keep else MeshB(), (math.cos(a) * 0.012, math.sin(a) * 0.012, 0.004), a, rng.uniform(0.9, 1.2) if inner else rng.uniform(0.3, 0.75), rng.uniform(0.5, 1.1), L, L * 0.42, PLANT, segs, cols, 0.2, rng.normal(0, 0.2), rng.random(), 0.05)
        for i in range(2):
            tg = mb if (lod < 2 or i == 0) else MeshB()
            a = rng.uniform(0, 6.28); h = rng.uniform(0.2, 0.3); pts = path((0, 0, 0), (math.cos(a) * 0.25, math.sin(a) * 0.25, 1), h, 3, rng, 0.15)
            stem(tg, pts, 0.0022, 0.0016, STRIP[1], 3, (0.3, 0.6), 0.3, h)
            stem(tg, np.array([pts[-1], pts[-1] + nrm(pts[-1] - pts[-2]) * 0.05]), 0.005, 0.003, STRIP[3], 4 if lod == 0 else 3, (0.5, 0.7), 0.3, h)
    elif name == 'SM_Veg_Weed_Small_02':   # broad-leaved dock seedling: few large upright leaves
        n = 6
        for i in range(n):
            a = i * 2.4 + rng.normal(0, 0.25); L = rng.uniform(0.2, 0.36) * sc * (0.7 if i > 3 else 1)
            pet = rng.uniform(0.04, 0.09); el = rng.uniform(0.75, 1.25) if i > 2 else rng.uniform(0.35, 0.8)
            b = np.array([math.cos(a) * 0.01, math.sin(a) * 0.01, 0.0]); o = np.array([math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)])
            tg = mb if (rng.random() < keep or i < 3) else MeshB()
            if True:
                stem(tg, np.array([b, b + o * pet]), 0.003, 0.0025, STRIP[1], 3, (0.3, 0.5), 0.2, 0.3)
                leaf(tg, b + o * pet * 0.9, a, el, rng.uniform(0.6, 1.3), L, L * 0.5, DOCK, segs, cols, 0.22, rng.normal(0, 0.25), rng.random(), 0.07)
    else:                                   # nettle-type sprig: upright stems with opposite toothed leaves
        for s in range(3):
            tg0 = mb if (lod < 2 or s < 2) else MeshB()
            a0 = rng.uniform(0, 6.28); h = rng.uniform(0.28, 0.46) * (0.7 if s == 2 else 1)
            b = np.array([math.cos(a0) * 0.03 * s, math.sin(a0) * 0.03 * s, 0])
            pts = path(b, (math.cos(a0) * 0.18, math.sin(a0) * 0.18, 1), h, 4, rng, 0.12); ph = rng.random()
            stem(tg0, pts, 0.0035, 0.0018, STRIP[1], 4 if lod == 0 else 3, (0.25, 0.6), ph, h)
            npair = int(h / 0.055); az = rng.uniform(0, 3.14)
            for k in range(npair):
                t = (k + 0.6) / npair; i = min(int(t * 4), 3); p = pts[i] + (pts[i + 1] - pts[i]) * (t * 4 - i)
                L = (0.085 - 0.045 * t + 0.02 * math.sin(t * 3.1)) * sc * rng.uniform(0.85, 1.15); az += math.pi / 2
                for sd in (0, math.pi):
                    leaf(tg0 if not (lod == 2 and k % 2) else MeshB(), p, az + sd + rng.normal(0, 0.2), rng.uniform(0.0, 0.5) * (1 - t) + 0.25 * t, rng.uniform(0.5, 1.0), L, L * 0.62, NETTLE, max(2, segs - 1), 1 if lod else 2, 0.25, rng.normal(0, 0.2), ph, 0.0)
    _fix_ground(mb)
    return mb.build(f'{name}_LOD{lod}', [gc_mat()])

def build_flowers(name, lod):
    two = name.endswith('02'); rng = np.random.default_rng(31 if two else 30); mb = MeshB()
    segs = (3, 2, 2)[lod]; nfl = (9, 7, 5)[lod] if not two else (8, 6, 4)[lod]; mbreal = mb
    # basal leaves
    for i in range(9):
        mb = mbreal if i < (9, 6, 4)[lod] else MeshB()
        a = rng.uniform(0, 6.28); L = rng.uniform(0.07, 0.14); rr = rng.uniform(0, 0.08)
        leaf(mb, (math.cos(a) * rr, math.sin(a) * rr, 0.003), a + rng.normal(0, 0.5), rng.uniform(0.25, 0.9), rng.uniform(0.4, 1.0), L, L * 0.4, PLANT, segs, 1, 0.2, rng.normal(0, 0.3), rng.random())
    for i in range(9):
        mb = mbreal if i < nfl else MeshB()
        a = rng.uniform(0, 6.28); rr = 0.12 * math.sqrt(rng.random()); b = np.array([math.cos(a) * rr, math.sin(a) * rr, 0])
        butter = two and i % 2 == 0
        h = rng.uniform(0.16, 0.34) if not two else rng.uniform(0.22, 0.48); ph = rng.random()
        pts = path(b, (math.cos(a) * 0.3, math.sin(a) * 0.3, 1), h, 3, rng, 0.2)
        stem(mb, pts, 0.0022, 0.0015, STRIP[0], 3, (0.3, 0.6), ph, h)
        n = nrm(nrm(pts[-1] - pts[-2]) + np.array([0.35, -0.45, 0.5]) + rng.normal(0, 0.2, 3))    # heads turn toward the sun
        hr = np.random.default_rng(1000 + i + (50 if two else 0)); r_b = rng.uniform(0.011, 0.015); r_d = rng.uniform(0.02, 0.028) * (1.25 if two else 1); cup = rng.uniform(-0.05, 0.25); spin = rng.uniform(0, 6)
        if lod == 2: disc(mb, pts[-1], n, r_b if butter else r_d, BUTTER if butter else DAISY, 0.45 if butter else cup, 4, ph, spin)
        elif butter: head3d(mb, pts[-1], n, r_b, hr, 'butter', 5, ph)
        else: head3d(mb, pts[-1], n, r_d, hr, 'daisy', 13 if lod == 0 else 8, ph)
        if True:
            j = 1; leaf(mb if (rng.random() < 0.6 and lod == 0) else MeshB(), pts[j], a + rng.uniform(0, 6), 0.6, 0.6, 0.05, 0.02, PLANT, 2, 1, 0.2, 0, ph)
    for i in range(14 if two else 8):      # a few grass blades through the clump
        mb = mbreal if i < ((14, 8, 4)[lod] if two else (8, 5, 3)[lod]) else MeshB()
        a = rng.uniform(0, 6.28); rr = 0.13 * math.sqrt(rng.random())
        blade(mb, (math.cos(a) * rr, math.sin(a) * rr, 0), a + rng.normal(0, 1), rng.uniform(0.05, 0.4), rng.uniform(0.3, 1.2), rng.uniform(0.15, 0.4), 0.007 * (1, 1.4, 2)[lod], STRIP[rng.integers(0, 3)], (3, 2, 2)[lod], 0.2 if lod == 0 else 0, rng.normal(0, 0.5), rng.random())
    mb = mbreal; _fix_ground(mb)
    return mb.build(f'{name}_LOD{lod}', [gc_mat()])

def build_mushroom(name, lod):
    agaric = name.endswith('02'); rng = np.random.default_rng(44 if agaric else 43); mb = MeshB()
    sides0 = (12, 8, 5)[lod]; spec = [(0, 0, 1.0), (0.085, 0.04, 0.72), (-0.05, 0.075, 0.5), (0.03, -0.075, 0.42), (-0.085, -0.03, 0.3)] if not agaric else [(0, 0, 1.0), (0.1, -0.05, 0.62), (-0.07, 0.06, 0.45), (0.03, 0.1, 0.28)]
    for (x, y, s) in spec:
        H = (0.145 if agaric else 0.13) * s * rng.uniform(0.9, 1.1); cr = (0.062 if agaric else 0.06) * s * rng.uniform(0.9, 1.1); sr = cr * (0.2 if agaric else 0.3)
        tilt = nrm(np.array([rng.normal(0, 0.13), rng.normal(0, 0.13), 1])); base = np.array([x, y, 0.0]); sides = sides0 if s > 0.6 else max(5, sides0 - 4)
        if lod == 2 and s < 0.45: continue
        young = s < 0.55
        # stem (bulbous base)
        prof = [(sr * 1.7, 0.0, 1.0), (sr * 1.5, H * 0.08, 0.85), (sr * 1.05, H * 0.25, 0.6), (sr * 0.9, H * 0.6, 0.3), (sr * 0.85, H * 0.86, 0.0)]
        if lod == 2: prof = [prof[0], prof[2], prof[4]]
        revolve(mb, base, tilt, prof, STEM, max(5, sides // 2))
        if agaric and lod < 2 and not young:   # ring (skirt)
            revolve(mb, base, tilt, [(sr * 0.95, H * 0.72, 0.0), (sr * 1.9, H * 0.63, 0.2)], STEM, max(5, sides // 2), 0.08)
        # cap: convex top, rim, gilled underside
        ch = cr * (0.95 if young else (0.55 if agaric else 0.7)); top = H + ch * 0.55
        capprof = [(0.004, top, 0.0)]
        for t in ((0.25, 0.5, 0.75, 0.93, 1.0) if lod == 0 else (0.5, 0.9, 1.0)):
            rr = cr * (math.sin(t * math.pi / 2) ** (0.8 if not young else 0.55)) * (0.7 if young else 1); zz = top - ch * (1 - math.cos(t * math.pi / 2) ** 0.9)
            capprof.append((rr, zz, t * 0.97))
        revolve(mb, base, tilt, capprof, CAPB if agaric else CAPA, sides, 0.05, rng.uniform(0, 6))
        rimr, rimz, _ = capprof[-1]
        revolve(mb, base, tilt, [(rimr, rimz, 0.0), (rimr * 0.93, rimz - ch * 0.06, 0.1), (sr * 0.9, H * 0.84, 1.0)], GILL, sides, 0.05)
    recenter(mb)
    return mb.build(f'{name}_LOD{lod}', [gc_mat()])

from veg_broadleaf import GRASS_T
PATCH = {'SM_Veg_GrassPatch_Dense_01': dict(seed=71, n=30, tiles=(0, 2), h=(0.5, 0.75), size=0.9),
         'SM_Veg_GrassPatch_Dense_02': dict(seed=72, n=28, tiles=(1, 3, 0), h=(0.45, 0.7), size=0.9),
         'SM_Veg_GrassPatch_Dense_03': dict(seed=73, n=24, tiles=(0, 1, 2, 3), h=(0.38, 0.58), size=0.8)}
def build_patch(name, lod):
    """dense meadow patch for instancing: grass-clump cards (understory atlas) standing in a jittered grid, bent back, normals up"""
    P = PATCH[name]; rng = np.random.default_rng(P['seed']); mb = MeshB(); keep = (1.0, 0.45, 0.17)[lod]; sc = (1.0, 1.35, 1.9)[lod]; g = int(math.ceil(math.sqrt(P['n'])))
    for k in range(P['n']):
        key = rng.random(); gx, gy = k % g, k // g
        x = ((gx + rng.uniform(0.15, 0.85)) / g - 0.5) * P['size']; y = ((gy + rng.uniform(0.15, 0.85)) / g - 0.5) * P['size']
        yaw = rng.uniform(0, 6.28); w = np.array([math.cos(yaw), math.sin(yaw), 0]); back = np.cross(UP, w)
        t = GRASS_T[P['tiles'][rng.integers(len(P['tiles']))]]; hs = rng.uniform(*P['h']); wd = 0.5 * rng.uniform(0.75, 1.0)
        d = nrm(UP + back * rng.uniform(-0.25, 0.25)); o = np.array([x, y, -0.01])
        if key < keep:
            mb.card(o, d, w, 0.4 * hs * sc ** 0.5, wd * sc, (t[0], t[3], t[2], t[1]), 2 if lod == 0 else 1, 1, 0.0, 0, o - UP * 4.0, 0.85, (0, rng.random(), 0, 0), 0, rng.random() < 0.5,
                    lift=rng.uniform(-0.5, 0.5), uvaxis='v')
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.0); mb.v = list(V); recenter(mb)
    return mb.build(f'{name}_LOD{lod}', [game_mat('MI_Veg_Understory', 'T_Veg_Understory', alpha=True, translucency=0.25)])

def build_cabbage(name, lod):
    rng = np.random.default_rng(88); mb = MeshB(); segs = (4, 3, 2)[lod]; cols = (2, 2, 1)[lod]
    for i in range(15):
        a = i * 2.4 + rng.normal(0, 0.2); inner = i >= 6; L = rng.uniform(0.2, 0.27) if not inner else rng.uniform(0.13, 0.19) * (1 - 0.02 * i)
        el = rng.uniform(0.25, 0.6) if not inner else rng.uniform(0.95, 1.3); curl = rng.uniform(-0.2, 0.5) if not inner else rng.uniform(-1.3, -0.7)
        tg = mb if (lod == 0 or i % (lod + 1) == 0 or i < 6) else MeshB()
        leaf(tg, (math.cos(a) * 0.02, math.sin(a) * 0.02, 0.005), a, el, curl, L, L * 0.85, DOCK, segs, cols, 0.35, rng.normal(0, 0.15), rng.random(), 0.1)
    _fix_ground(mb)
    return mb.build(f'{name}_LOD{lod}', [gc_mat()])

def build_bed(name, lod):
    """planted bed (sprite 66/01): a low tilled soil mound with three ridges, two planted rows. Soil = terrain set TransitionDirt (world-scale UVs, wraps)."""
    import os
    rng = np.random.default_rng(99); mb = MeshB(); Lx, Wy, hmax = 4.6, 1.15, 0.13; nx, ny = (24, 12, 6)[lod], (12, 7, 4)[lod]
    def hgt(x, y):
        ex = min(1.0, (Lx / 2 - abs(x)) / 0.25); ey = min(1.0, (Wy / 2 - abs(y)) / 0.2); e = max(0.0, min(ex, ey)); e = e * e * (3 - 2 * e)
        return e * (hmax * (0.62 + 0.38 * math.cos(y / Wy * 3 * 2 * math.pi)) + 0.012 * math.sin(x * 7.3 + y * 3.1) + 0.008 * math.sin(x * 17.0 - y * 9.0)) - 0.02 * (1 - e)
    V = []; N = []; U = []; F = []
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = (i / nx - 0.5) * Lx; y = (j / ny - 0.5) * Wy; z = hgt(x, y); e = 0.02
            V.append((x, y, z)); N.append(nrm([-(hgt(x + e, y) - hgt(x - e, y)) / (2 * e), -(hgt(x, y + e) - hgt(x, y - e)) / (2 * e), 1.0])); U.append((x / 2.0 + 2.0, y / 2.0 + 1.0))
    for i in range(nx):
        for j in range(ny):
            a = i * (ny + 1) + j; F.append((a, a + ny + 1, a + ny + 2, a + 1))
    mb.poly(V, N, U, 1, (0, 0, 0, 0), F)
    k = 0
    for row in (-1, 1):
        x = -Lx / 2 + 0.3 + rng.uniform(0, 0.1)
        while x < Lx / 2 - 0.25:
            y = row * Wy / 3 + rng.normal(0, 0.03); z = hgt(x, y); k += 1; kind = rng.random(); tg = mb if (lod == 0 or (lod == 1 and k % 2 == 0) or (lod == 2 and k % 4 == 0)) else MeshB()
            nl = int(rng.integers(5, 8))
            for q in range(nl):
                a = q * 2.4 + rng.normal(0, 0.3); L = rng.uniform(0.1, 0.19)
                leaf(tg, (x + math.cos(a) * 0.01, y + math.sin(a) * 0.01, z), a, rng.uniform(0.4, 1.1), rng.uniform(0.3, 1.0), L, L * (0.5 if kind < 0.6 else 0.42), DOCK if kind < 0.6 else PLANT, (3, 2, 2)[lod], 1, 0.22, rng.normal(0, 0.2), rng.random())
            x += rng.uniform(0.3, 0.42)
    V2 = np.asarray(mb.v); lo = V2[:, 2].min(); mb.v = [p - np.array([0, 0, lo]) for p in mb.v]; recenter(mb)
    soil = os.path.abspath(os.path.join(HERE, '..', '..', 'Terrain', 'TransitionDirt', 'T_Terrain_TransitionDirt'))
    return mb.build(f'{name}_LOD{lod}', [gc_mat(), game_mat('MI_Terrain_TransitionDirt_Tilled', soil, tint=(0.5, 0.44, 0.4))])

GROUND = {**{k: build_grass for k in GRASS}, 'SM_Veg_Weed_Small_01': build_weed, 'SM_Veg_Weed_Small_02': build_weed, 'SM_Veg_Weed_Sprig_01': build_weed,
          'SM_Veg_Flowers_01': build_flowers, 'SM_Veg_Flowers_02': build_flowers, 'SM_Veg_Mushroom_01': build_mushroom, 'SM_Veg_Mushroom_02': build_mushroom,
          **{k: build_patch for k in PATCH}, 'SM_Veg_Cabbage_01': build_cabbage, 'SM_Veg_FlowerBed_Row_01': build_bed}
def build(name, lod): return GROUND[name](name, lod)
