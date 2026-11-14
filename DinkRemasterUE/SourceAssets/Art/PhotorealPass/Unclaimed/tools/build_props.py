"""Small static props of the unclaimed families: boulders (95 lands/rocks/rock-), gold (178 bonuses/coins), hearts
(52-54 bonuses/heart), the bomb (420 items/bomb) and the arrow (25 effects/arrow).

    tools/bl.sh build_props.py <name,name|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_props.py'


# ---------------------------------------------------------------------------------------------- boulders
def rock_mat(name, scan='rock_face_03', tint=(1, 1, 1), value=1.0, sat=1.0, moss=0.4, dirt_z=0.12, scale=1.5, lichen=0.3, seed=0.0, crystals=None):
    """scanned rock (box projected, two scales blended), lichen and moss on up-facing rough parts, soil splash at the foot, dark fissures"""
    t = NT(name); a = t.scan(scan, scale=scale, loc=(seed, seed * 0.3, 0)); b = t.scan(scan, scale=scale * 0.31, rot=(0.5, 0.3, 1.0), loc=(1.7, seed, 0.4)); f = t.ramp(t.noise(1.3, 3, 0.5), [(0.35, 0.0), (0.65, 1.0)])
    base = t.mix(f, a['diff'], b['diff']); base = t.hsv(base, sat=sat, v=value); base = t.mix(1.0, base, tint, blend='MULTIPLY'); rough = t.mixf(f, a['rough'], b['rough'])
    nrm = t.normalmap(t.mix(f, a['nor_gl'], b['nor_gl']), 1.6); nz = t.sep(t.gnormal)[2]; z = t.sep(t.obj)[2]; n = t.noise(9, 5, 0.65, vec=t.mapping(loc=(seed, 2, 5))); n2 = t.noise(60, 4, 0.6)
    ao = t.ao(0.12, 12); crev = t.ramp(ao, [(0.3, 1.0), (0.75, 0.0)]); base = t.mix(t.math('MULTIPLY', crev, 0.75), base, (0.02, 0.018, 0.015))
    if lichen:
        lm = t.math('MULTIPLY', t.ramp(t.noise(14, 5, 0.7, vec=t.mapping(loc=(7, seed, 1))), [(0.6, 0.0), (0.68, 1.0)]), t.maprange(nz, -0.2, 0.5, 0.2, 1.0)); base = t.mix(t.math('MULTIPLY', lm, lichen), base, t.mix(n2, (0.36, 0.36, 0.27), (0.55, 0.52, 0.36)))
        rough = t.mixf(lm, rough, 0.9)
    if moss:
        mm = t.math('MULTIPLY', t.ramp(t.math('ADD', t.math('MULTIPLY', n, 0.6), t.math('MULTIPLY', nz, 0.45)), [(0.62, 0.0), (0.78, 1.0)]), t.ramp(n2, [(0.25, 0.4), (0.6, 1.0)])); base = t.mix(t.math('MULTIPLY', mm, moss), base, t.mix(n2, (0.025, 0.05, 0.012), (0.085, 0.13, 0.03)))
        rough = t.mixf(mm, rough, 0.95); nrm = t.bump(t.math('MULTIPLY', mm, n2), 0.6, 0.006, normal=nrm)
    soil = t.math('MULTIPLY', t.maprange(t.math('ADD', z, t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.12)), 0.0, dirt_z, 1.0, 0.0, interp='SMOOTHSTEP'), 0.8); base = t.mix(soil, base, t.mix(n2, (0.07, 0.05, 0.03), (0.16, 0.12, 0.075)))
    rough = t.mixf(soil, rough, 0.92); metal = 0.0
    if crystals:                                   # mineral faces: saturated, glassy, slightly metallic
        cm = t.attr('crystal'); cv = t.sep(t.voronoi(55, out='Color')); cc = t.ramp(cv[0], [(0.2, crystals[0]), (0.55, crystals[1]), (0.85, crystals[2])]); base = t.mix(cm, base, cc); rough = t.mixf(cm, rough, t.maprange(cv[1], 0, 1, 0.08, 0.3)); metal = t.mixf(cm, 0.0, 0.25)
    t.set(base=base, rough=rough, normal=nrm, metal=metal); return t.mat


def boulder(name, dims, seed, c, hi, rough_amp=0.16, strata=0.0, cracks=0.0, sink=0.12, sub=6, round_=1.0, crystal=False, offset=(0, 0, 0), yaw=0.0):
    ob = L.icosphere(name, 0.5, sub if hi else 5, c); P = L.co(ob); d = P / np.linalg.norm(P, axis=1)[:, None]
    r = 0.5 * (1 + rough_amp * 1.8 * fbm(d, seed, 0.8, 2))                                 # broad lumps only: the breaks below give the rock its planes
    r = r * (1 + 0.012 * fbm(d, seed + 5, 6, 3) + 0.006 * fbm(d, seed + 7, 24, 3))
    # faceting: push towards a few random planes (angular breaks)
    rng = np.random.default_rng(seed)
    for k in range(int(14 * (2 - round_))):
        n = rng.normal(size=3); n /= np.linalg.norm(n); lim = 0.5 * rng.uniform(0.70, 0.96); h = d @ n; cut = np.where(h > 1e-6, lim / np.maximum(h, 1e-6), 9.0); sm = 0.02; r = np.where(cut < r + sm, np.minimum(r, cut * (1 + 0.015 * fbm(d, seed + 20 + k, 5, 2)) + sm * np.clip((r - cut) / sm, -1, 0) ** 2 * 0.5), r)
    P = d * r[:, None] * np.array(dims)
    if strata:                                    # bedding: stepped ledges in height
        zz = P[:, 2] / dims[2]; st = (np.floor(zz * 9 + 0.6 * fbm(P, seed + 9, 1.5, 2)) % 2) * 2 - 1; P[:, :2] *= (1 + strata * st * (0.5 + 0.5 * fbm(P, seed + 11, 3, 2)))[:, None]
    if cracks and hi:
        cr = np.abs(fbm(P, seed + 13, 2.2 / max(dims), 3)); m = smoothstep(0.035, 0.0, cr); nrm = P / (np.linalg.norm(P, axis=1)[:, None] + 1e-9); P = P - nrm * (m * cracks)[:, None]
    P[:, 2] += dims[2] * (0.5 - sink); P[:, 2] = np.maximum(P[:, 2], 0.0)
    ca, sa = math.cos(yaw), math.sin(yaw); P = P @ np.array([[ca, sa, 0], [-sa, ca, 0], [0, 0, 1]]) + np.array(offset); L.set_co(ob, P)
    if crystal and hi:
        v = fbm(P, seed + 31, 9, 3); C.set_attr(ob, 'crystal', smoothstep(0.08, 0.2, v) * smoothstep(0.1, 0.25, P[:, 2] / dims[2]))
    elif crystal:
        C.set_attr(ob, 'crystal', np.zeros(len(P)))
    ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons)); return ob


# Size: the sprite's width at the art standard's 0.025 m per original pixel, the scale the hero is built at (a 103 px boulder is 2.6 m).
# The first build stood at 0.016 m per pixel: boulders half as high as the hero where the 1997 pictures show them taller than him.
ROCK = 1.7
def rk(*dims): return tuple(round(d * ROCK, 3) for d in dims)


def b_flat(hi, c):
    o = boulder('rock', rk(1.35, 1.05, 0.62), 3, c, hi, strata=0.05, rough_amp=0.13, round_=0.7, sink=0.1)
    if hi:
        o.data.materials.append(rock_mat('rock', 'rock_face_03', tint=(1.0, 0.90, 0.86), value=1.0, sat=0.7, moss=0.3, seed=1.0))
    return [o]


def b_large(hi, c):
    o = boulder('rock', rk(1.65, 1.35, 1.15), 5, c, hi, rough_amp=0.2, round_=1.0, cracks=0.03 * ROCK, sink=0.14)
    if hi:
        o.data.materials.append(rock_mat('rock', 'rock_boulder_dry', tint=(0.62, 0.63, 0.66), value=0.8, sat=0.6, moss=0.45, seed=2.0))
    return [o]


def b_red(hi, c):
    o = boulder('rock', rk(1.5, 1.1, 0.78), 8, c, hi, rough_amp=0.17, round_=0.6, cracks=0.045 * ROCK, sink=0.1)
    if hi:
        o.data.materials.append(rock_mat('rock', 'rock_boulder_dry', tint=(0.86, 0.46, 0.36), value=0.8, sat=0.9, moss=0.15, lichen=0.2, seed=3.0))
    return [o]


def b_white(hi, c):
    a = boulder('rock_a', (1.13, 1.04, 0.96), 11, c, hi, rough_amp=0.14, round_=1.0, sink=0.12, offset=(-0.48, 0.06, 0)); b = boulder('rock_b', (1.04, 0.96, 1.07), 12, c, hi, rough_amp=0.15, round_=0.9, sink=0.1, offset=(0.52, -0.04, 0), yaw=1.1)
    if hi:
        m = rock_mat('rock', 'rock_face_03', tint=(1.0, 0.99, 0.96), value=1.45, sat=0.3, moss=0.25, lichen=0.35, seed=4.0); a.data.materials.append(m); b.data.materials.append(m)
    return [a, b]


def b_tall(hi, c):
    o = boulder('rock', rk(0.88, 0.82, 1.42), 14, c, hi, rough_amp=0.18, round_=0.8, cracks=0.02 * ROCK, sink=0.2)       # sunk a fifth: at 0.08 it balanced on a point
    if hi:
        o.data.materials.append(rock_mat('rock', 'rock_face_03', tint=(0.82, 0.84, 0.88), value=0.9, sat=0.5, moss=0.35, seed=5.0))
    return [o]


def b_ore(hi, c):
    o = boulder('rock', (0.74, 0.62, 0.46), 17, c, hi, rough_amp=0.15, round_=0.55, sink=0.1, crystal=True)
    if hi:
        o.data.materials.append(rock_mat('rock', 'rock_boulder_dry', tint=(0.34, 0.36, 0.44), value=0.7, sat=0.5, moss=0.2, lichen=0.0, seed=6.0, crystals=((0.006, 0.012, 0.11), (0.010, 0.045, 0.24), (0.015, 0.13, 0.20))))
    obs = [o]
    if hi or True:                                # a few crystal prisms standing out of the top
        rng = np.random.default_rng(5); cm = None
        if hi:
            t = NT('crystal'); n = t.noise(40, 3, 0.6); t.set(base=t.mix(n, (0.004, 0.012, 0.11), (0.012, 0.06, 0.26)), rough=t.mixf(n, 0.08, 0.25), metal=0.15, coat=0.5); cm = t.mat
        for k in range(7):
            a = rng.uniform(0, 6.28); rr = rng.uniform(0.02, 0.12); x, y = rr * math.cos(a) * 1.2, rr * math.sin(a); hit = C.surface_hit(o, (x, y, 2.0), (0, 0, -1)); z0 = (hit[0][2] if hit else 0.3) - 0.02; ln = rng.uniform(0.035, 0.075)
            tip = (x + rng.uniform(-0.04, 0.04), y + rng.uniform(-0.04, 0.04), z0 + ln); p = L.sweep('prism', [(x, y, z0, 0.013, 0.013, 9), ((x + tip[0]) / 2, (y + tip[1]) / 2, z0 + ln * 0.7, 0.012, 0.012, 9), tip + (0.003, 0.003, 9)], nu=6 if not hi else 24, nv=4 if not hi else 12, c=c, up=(0, 1, 0), cap=0.3)
            if hi:
                p.data.materials.append(cm)
            obs.append(p)
    return obs


# ---------------------------------------------------------------------------------------------- gold
def gold_mat(seed=0.0):
    """struck gold coin: design in low relief (rings and a blundered device), bag wear on the high points, dirt in the recesses"""
    t = NT('gold'); sp = t.sep(t.obj); n = t.noise(240, 3, 0.6); n2 = t.noise(30, 4, 0.6, vec=t.mapping(loc=(seed, 0, 0))); ao = t.ao(0.004, 8)
    base = t.mix(n2, (0.86, 0.47, 0.085), (1.0, 0.62, 0.15)); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.85, 0.0)]), 0.7), base, (0.14, 0.07, 0.02))
    base = t.mix(t.math('MULTIPLY', t.ramp(t.noise(55, 4, 0.7), [(0.66, 0.0), (0.76, 1.0)]), 0.25), base, (0.40, 0.20, 0.05))
    t.set(base=base, rough=t.mixf(n2, 0.22, 0.42), metal=1.0, normal=t.bump(n, 0.15, 0.0003)); return t.mat


def coin(name, c, hi, r=0.013, th=0.0019, seed=0, lo_seg=24):
    """one hammered coin, lying flat on z = 0: raised rim, device relief on both faces (dense source only), slightly out of round"""
    rng = np.random.default_rng(seed); seg = 48 if hi else lo_seg
    if not hi:                                    # game mesh: a round rim (ten sides showed in game at pickup size) with a small chamfer, so no razor edge
        b = th * 0.22
        if seg < 16:                              # a coin among many on the heap: a plain disc
            return L.lathe(name, [(0, 0), (r, 0), (r, th), (0, th)], seg=seg, c=c)
        return L.lathe(name, [(0, 0), (r - b, 0), (r, b), (r, th - b), (r - b, th), (0, th)], seg=seg, c=c)
    prof = [(0, th * 0.25)] + [(r * k / 14, th * 0.25) for k in range(1, 12)] + [(r * 0.86, th * 0.05), (r * 0.93, 0.0), (r, th * 0.12), (r, th * 0.88), (r * 0.93, th), (r * 0.86, th * 0.95)] + [(r * k / 14, th * 0.75) for k in range(11, 0, -1)] + [(0, th * 0.75)]
    ob = L.lathe(name, prof, seg=seg, c=c); P = L.co(ob); rad = np.hypot(P[:, 0], P[:, 1]); ang = np.arctan2(P[:, 1], P[:, 0]); inner = smoothstep(r * 0.84, r * 0.78, rad)
    dev = (0.5 + 0.5 * np.cos(rad / r * 26)) * 0.35 + (fbm(np.stack([P[:, 0] * 260 + seed, P[:, 1] * 260, np.zeros(len(P))], 1), seed, 1.0, 3) > 0.05) * 0.65 + 0.3 * (np.cos(ang * 14) > 0.2) * smoothstep(r * 0.55, r * 0.7, rad)
    P[:, 2] += np.where(P[:, 2] > th / 2, 1, -1) * inner * dev * th * 0.16; P[:, 0] *= 1 + 0.03 * rng.normal(); L.set_co(ob, P); return ob


def heap_lobe(a):
    """outline of the coin heap: not a circle, it slumps in three lobes"""
    return 1 + 0.11 * np.sin(3 * a + 0.8) + 0.06 * np.sin(5 * a + 2.1)


def lobed(ob, k=1.0):
    P = L.co(ob); f = 1 + (heap_lobe(np.arctan2(P[:, 1], P[:, 0])) - 1) * k; P[:, 0] *= f; P[:, 1] *= f; L.set_co(ob, P); return ob


def scatter_coins(c, hi, n, spread, seed, heap=None, lo_seg=24):
    rng = np.random.default_rng(seed); obs = []
    for k in range(n):
        o = coin('coin%d' % k, c, hi, r=0.013 * rng.uniform(0.92, 1.08), seed=seed * 100 + k, lo_seg=lo_seg)
        if heap:                                  # on a mound: lie on its slope, tilted at random, a few standing on edge
            a = rng.uniform(0, 6.28); q = rng.uniform(0, 1) ** 0.55; rr = heap[0] * q * heap_lobe(a); z = heap[1] * (1 - q ** 1.7) + rng.uniform(-0.004, 0.006); slope = math.atan(heap[1] * 1.7 * q ** 0.7 / heap[0])
            tilt = slope + rng.normal(0, 0.45); M = Matrix.Translation((rr * math.cos(a), rr * math.sin(a), max(0.0, z))) @ Matrix.Rotation(a + rng.normal(0, 0.5), 4, 'Z') @ Matrix.Rotation(tilt, 4, 'Y') @ Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z')
        else:
            a = rng.uniform(0, 6.28); rr = spread * rng.uniform(0.1, 1) ** 0.7; lean = rng.random() < 0.25
            M = Matrix.Translation((rr * math.cos(a), rr * math.sin(a) * 0.7, 0.0005 if not lean else 0.004)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(0.0 if not lean else rng.uniform(0.15, 0.4), 4, 'Y')
        o.matrix_world = M; L.apply_xf(o); obs.append(o)
    return obs


def g_coin(hi, c):
    o = coin('coin', c, hi, r=0.0155, seed=3)
    if hi:
        o.data.materials.append(gold_mat())
    return [o]


def g_few(hi, c):
    obs = scatter_coins(c, hi, 11, 0.13, 7); m = gold_mat(1.0) if hi else None
    for o in obs:
        if hi:
            o.data.materials.append(m)
    return obs


def g_pile(hi, c):
    if not hi:
        # game mesh: a smooth mound just under the tops of the coins (the heap is baked onto it), the 55 coins that stand proudest of it
        # as real discs so the outline is coins and not a dome, and the stray coins. The discs are the source coins' own transforms.
        R, H = 0.172, 0.105
        env = L.lathe('heap', [(0, 0), (R + 0.006, 0), (R + 0.008, 0.006)] + [(R * q + 0.004, H * (1 - q ** 1.7) + 0.004) for q in (0.9, 0.72, 0.5, 0.26)] + [(0, H + 0.004)], seg=28, c=c); L.subsurf(env, 1); lobed(env)
        coins = scatter_coins(c, False, 520, 0, 21, heap=(R, H), lo_seg=12); rank = []
        for o in coins:
            P = L.co(o); q = np.hypot(P[:, 0], P[:, 1]) / (R * heap_lobe(np.arctan2(P[:, 1], P[:, 0])))
            rank.append((float((P[:, 2] - np.where(q < 1, H * (1 - np.minimum(q, 1) ** 1.7) + 0.004, 0.0)).max()), o))
        rank.sort(key=lambda t: -t[0]); keep = []
        for _, o in rank:
            cen = L.co(o).mean(0)
            if len(keep) < 55 and all(np.linalg.norm(cen - k) > 0.03 for _, k in keep):
                keep.append((o, cen))
        kept = [o for o, _ in keep]
        for o in coins:
            if o not in kept:
                bpy.data.objects.remove(o)
        return [env] + kept + scatter_coins(c, False, 18, 0.26, 23, lo_seg=12)
    # the body under the coins, then two layers of coins (the inner one closes the gaps of the outer: no bare mound shows), then the strays
    dome = lobed(L.lathe('dome', [(0, 0), (0.155, 0), (0.15, 0.008), (0.118, 0.04), (0.072, 0.074), (0.027, 0.089), (0, 0.092)], seg=40, c=c))
    obs = [dome] + scatter_coins(c, hi, 520, 0, 21, heap=(0.172, 0.105)) + scatter_coins(c, hi, 420, 0, 22, heap=(0.165, 0.099)) + scatter_coins(c, hi, 18, 0.26, 23)
    m = gold_mat(2.0); dm = NT('under'); dm.set(base=(0.30, 0.15, 0.03), rough=0.5, metal=1.0)
    for o in obs:
        o.data.materials.append(dm.mat if o is dome else m)
    return obs


# ---------------------------------------------------------------------------------------------- hearts, bomb, arrow
def heart(hi, c, mat):
    """the classic heart: (x^2 + 9/4 y^2 + z^2 - 1)^3 - x^2 z^3 - 9/80 y^2 z^3 = 0, solved along rays from the centre, 12 cm across"""
    o = L.icosphere('heart', 1.0, 6 if hi else 3, c); d = L.co(o); d /= np.linalg.norm(d, axis=1)[:, None]; lo_ = np.zeros(len(d)); hi_ = np.full(len(d), 2.0)

    def f(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]; return (x * x + 2.25 * y * y + z * z - 1) ** 3 - x * x * z ** 3 - 0.1125 * y * y * z ** 3
    for _ in range(40):
        mid = (lo_ + hi_) / 2; inside = f(d * mid[:, None]) < 0; lo_ = np.where(inside, mid, lo_); hi_ = np.where(inside, hi_, mid)
    P = d * ((lo_ + hi_) / 2)[:, None] * 0.05; P[:, 1] *= 1.25; P[:, 2] -= P[:, 2].min(); L.set_co(o, P); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
    if hi:
        o.data.materials.append(mat())
    return [o]


def ruby_mat():
    """the red heart: blown red glass with a fire-polished skin, a few seeds and handling scratches (it reads as a solid ruby-red cabochon)"""
    t = NT('ruby'); n = t.noise(14, 4, 0.6); scr = t.noise(3, 3, 0.6, vec=t.mapping(scale=(600, 30, 30), rot=(0.3, 0.7, 0.2))); seeds = t.ramp(t.voronoi(420, feature='F1'), [(0.0, 1.0), (0.12, 0.0)])
    base = t.mix(n, (0.26, 0.003, 0.005), (0.50, 0.010, 0.012)); base = t.mix(t.math('MULTIPLY', seeds, 0.12), base, (0.7, 0.25, 0.2))
    t.set(base=base, rough=t.math('ADD', t.mixf(n, 0.04, 0.1), t.math('MULTIPLY', t.ramp(t.noise(40, 4, 0.7), [(0.6, 0.0), (0.75, 1.0)]), 0.12)), coat=1.0, coat_rough=0.03, spec=0.8, sss=0.1, sss_radius=(1.0, 0.05, 0.05), sss_scale=0.01,
          normal=t.bump(t.noise(9, 3, 0.5), 0.05, 0.002)); return t.mat


def heart_gold_mat():
    """the golden heart: cast gold, sand-cast skin left in the hollows, burnished on the swell of the lobes"""
    t = NT('goldcast'); n = t.noise(26, 5, 0.65); pit = t.noise(520, 3, 0.6); ao = t.ao(0.01, 8); hi_ = t.ramp(t.pointiness, [(0.5, 0.0), (0.56, 1.0)])
    base = t.mix(n, (0.70, 0.43, 0.10), (0.92, 0.64, 0.20)); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.9, 0.0)]), 0.7), base, (0.12, 0.07, 0.025)); base = t.mix(t.math('MULTIPLY', t.ramp(n, [(0.62, 0.0), (0.75, 1.0)]), 0.3), base, (0.30, 0.17, 0.06))
    t.set(base=base, rough=t.mixf(hi_, t.mixf(pit, 0.32, 0.5), 0.16), metal=1.0, normal=t.bump(pit, 0.25, 0.0004)); return t.mat


def bomb(hi, c):
    body = L.icosphere('shell', 0.105, 6 if hi else 3, c); P = L.co(body); P[:, 2] += 0.105; L.set_co(body, P)
    neck = L.sweep('neck', [(0, 0, 0.198, 0.026, 0.026, 2), (0, 0, 0.212, 0.024, 0.024, 2), (0, 0, 0.224, 0.025, 0.025, 2)], nu=20 if hi else 10, nv=6 if hi else 4, c=c, up=(0, 1, 0), cap=0.85)
    fuse = L.sweep('fuse', [(0, 0, 0.218, 0.006, 0.006, 2), (0.004, -0.004, 0.25, 0.006, 0.006, 2), (0.022, -0.012, 0.285, 0.006, 0.006, 2), (0.052, -0.02, 0.305, 0.0058, 0.0058, 2), (0.08, -0.022, 0.30, 0.005, 0.005, 2)], nu=12 if hi else 6, nv=30 if hi else 8, c=c, up=(0, 1, 0), cap=0.6)
    if hi:
        L.displace_np(body, lambda Q: 0.0009 * fbm(Q, 3, 30, 3) + 0.0005 * np.abs(fbm(Q, 5, 110, 2)) - 0.0012 * smoothstep(0.004, 0.0, np.abs(Q[:, 0] + 0.0)) * 0 + 0.0016 * np.exp(-(Q[:, 1] / 0.0035) ** 2))        # casting seam round the mould line
        t = NT('castiron'); n = t.noise(36, 5, 0.65); n2 = t.noise(300, 3, 0.6); ao = t.ao(0.02, 8); sc = t.scan('rusty_metal_02', scale=6.0)
        base = t.mix(n, (0.012, 0.014, 0.022), (0.040, 0.046, 0.068)); rust = t.ramp(t.math('ADD', t.noise(11, 5, 0.7), t.math('MULTIPLY', t.math('SUBTRACT', 1.0, ao), 0.6)), [(0.62, 0.0), (0.76, 1.0)])
        base = t.mix(t.math('MULTIPLY', rust, 0.7), base, t.hsv(sc['diff'], v=0.35)); soot = t.maprange(t.sep(t.obj)[2], 0.15, 0.22, 0.0, 0.7); base = t.mix(soot, base, (0.008, 0.008, 0.008))
        t.set(base=base, rough=t.mixf(rust, t.mixf(n2, 0.42, 0.62), 0.88), metal=t.mixf(rust, 0.8, 0.05), normal=t.bump(n2, 0.5, 0.0008, normal=t.normalmap(sc['nor_gl'], 0.35))); body.data.materials.append(t.mat); neck.data.materials.append(t.mat)
        f = NT('fuse'); sp = f.sep(f.obj); tw = f.math('SINE', f.math('ADD', f.math('MULTIPLY', sp[2], 900.0), f.math('MULTIPLY', f.math('ARCTAN2', sp[1], sp[0]), 3.0))); fn = f.noise(500, 3, 0.6)
        col = f.mix(fn, (0.17, 0.13, 0.075), (0.36, 0.29, 0.17)); col = f.mix(f.maprange(sp[0], 0.06, 0.08, 0.0, 1.0), col, (0.015, 0.012, 0.01)); f.set(base=col, rough=0.9, normal=f.bump(tw, 0.8, 0.0012)); fuse.data.materials.append(f.mat)
    return [body, neck, fuse]


def arrow(hi, c):
    """war arrow lying on the ground, point towards +X: ash shaft, forged leaf head, three red goose-feather vanes bound with thread"""
    q = 4 if hi else 1; z = 0.0125
    shaft = L.sweep('shaft', [(-0.37, 0, z, 0.0042, 0.0042, 2), (-0.2, 0, z, 0.0046, 0.0046, 2), (0.2, 0, z, 0.0048, 0.0048, 2), (0.33, 0, z, 0.0045, 0.0045, 2)], nu=8 * q, nv=10 * q, c=c, up=(0, 0, 1), cap=0.8)
    head = L.sweep('head', [(0.315, 0, z, 0.0055, 0.0055, 2.2), (0.345, 0, z, 0.0052, 0.005, 2.4), (0.365, 0, z, 0.0125, 0.0028, 2.6), (0.395, 0, z, 0.0105, 0.0022, 2.6), (0.43, 0, z, 0.0012, 0.0008, 2.4)], nu=10 * q, nv=10 * q, c=c, up=(0, 0, 1), cap=0.3)
    nock = L.sweep('nock', [(-0.385, 0, z, 0.0036, 0.0036, 2), (-0.372, 0, z, 0.0048, 0.0048, 2), (-0.36, 0, z, 0.0044, 0.0044, 2)], nu=8 * q, nv=4 * q, c=c, up=(0, 0, 1), cap=0.6)
    binds = [L.sweep('bind%d' % k, [(x0, 0, z, 0.0054, 0.0054, 2), (x0 + 0.009, 0, z, 0.0056, 0.0056, 2), (x0 + 0.018, 0, z, 0.0053, 0.0053, 2)], nu=8 * q, nv=4 * q, c=c, up=(0, 0, 1), cap=0.9) for k, x0 in enumerate((-0.358, -0.218, 0.30))]
    vanes = []
    for k in range(3):
        a = math.radians(90 + 120 * k); nu, nv = (3 * q, 14 * q)
        def fn(U, V, a=a):
            x = -0.345 + 0.125 * V; hgt = 0.017 * np.sin(np.pi * np.clip(V, 0, 1) ** 0.6) ** 0.8 * (1 - 0.35 * V) + 0.0002; rr = 0.0042 + U * hgt; wob = 0.0012 * np.sin(V * 40 + k) * U
            return np.stack([x - 0.012 * U, rr * math.cos(a) - wob * math.sin(a), z + rr * math.sin(a) + wob * math.cos(a)], -1)
        v = L.grid_surface('vane%d' % k, fn, max(2, nu), nv, c, closed_u=False); L.mod(v, 'SOLIDIFY', thickness=0.0007, offset=0.0); L.apply_mods(v); L.fix_normals(v); vanes.append(v)
    if hi:
        shaft.data.materials.append(T.wood_mat('ash', axis=0, light=(0.34, 0.22, 0.10), dark=(0.15, 0.085, 0.035))); head.data.materials.append(T.iron_mat('iron', polish=(0, 0.385, 0.43), rust=0.35, seed=5.0))
        h = NT('horn'); h.set(base=(0.10, 0.075, 0.045), rough=0.4); nock.data.materials.append(h.mat)
        b = NT('thread'); sp = b.sep(b.obj); b.set(base=b.mix(b.noise(900, 2, 0.5), (0.05, 0.035, 0.02), (0.16, 0.11, 0.06)), rough=0.85, normal=b.bump(b.math('SINE', b.math('MULTIPLY', sp[0], 5200.0)), 0.9, 0.0006))
        for o in binds:
            o.data.materials.append(b.mat)
        f = NT('feather'); uv = f.sep(f.uv); barb = f.math('SINE', f.math('MULTIPLY', f.math('ADD', uv[1], f.math('MULTIPLY', uv[0], 0.12)), 520.0)); n = f.noise(1.0, 4, 0.6, vec=f.comb(f.math('MULTIPLY', uv[0], 3.0), f.math('MULTIPLY', uv[1], 30.0), 0.0))
        col = f.mix(n, (0.22, 0.012, 0.01), (0.50, 0.04, 0.025)); col = f.mix(f.ramp(uv[0], [(0.0, 1.0), (0.12, 0.0)]), col, (0.42, 0.36, 0.26)); split = f.ramp(f.noise(1.0, 2, 0.5, vec=f.comb(0.0, f.math('MULTIPLY', uv[1], 90.0), 0.0)), [(0.68, 0.0), (0.72, 1.0)])
        col = f.mix(f.math('MULTIPLY', split, 0.6), col, (0.08, 0.01, 0.008)); f.set(base=col, rough=0.6, normal=f.bump(f.math('ADD', barb, f.math('MULTIPLY', split, -3.0)), 0.5, 0.0004), sheen=0.3)
        for o in vanes:
            o.data.materials.append(f.mat)
    return [shaft, head, nock] + binds + vanes


# ---------------------------------------------------------------------------------------------- registry
W_ROCK = ('A sphere cut by random break planes and gently displaced: edges are soft, with no undercuts, overhangs or split-off slabs, and the base is a flat clip rather than a buried foot with soil piled against it. '
          'One rock scan, box projected and tinted, carries all surface detail; its features do not follow the displaced form. Moss and lichen are procedural masks.')
SPECS = {
    'Boulder_Flat': dict(fn=b_flat, fam='boulder_flat', seq='95 lands/rocks/rock- frames 4, 5', cls='prop', px=2048, tris=1600, ground='forrest_ground_01', third=['rock_face_03'], weak=W_ROCK,
                         dresses='flat-topped bedded boulder, 2.3 x 1.8 x 0.95 m, pinkish grey with stepped ledges'),
    'Boulder_Large': dict(fn=b_large, fam='boulder_large', seq='95 lands/rocks/rock- frame 10', cls='prop', px=2048, tris=1800, ground='forrest_ground_01', third=['rock_boulder_dry'], weak=W_ROCK,
                          dresses='large dark rounded boulder with fissures, 2.8 x 2.3 x 1.7 m'),
    'Boulder_Red': dict(fn=b_red, fam='boulder_red', seq='95 lands/rocks/rock- frame 3', cls='prop', px=2048, tris=1800, ground='forrest_ground_01', third=['rock_boulder_dry'],
                        weak=W_ROCK + ' Deep cracks are modelled because the scripted (bombable) red rocks must look cracked; the main crack reads a little like a seam, and an intact variant is not built.',
                        dresses='angular reddish-brown boulder, 2.55 x 1.85 x 1.2 m, visibly cracked (the bombable rock of the game)'),
    'Boulder_White_Pair': dict(fn=b_white, fam='boulder_white_pair', seq='95 lands/rocks/rock- frame 9', cls='prop', px=2048, tris=2200, ground='forrest_ground_01', third=['rock_face_03'], weak=W_ROCK,
                               dresses='two pale rounded boulders leaning together, 1.5 m across the pair, 0.7 m tall'),
    'Boulder_Grey_Tall': dict(fn=b_tall, fam='boulder_grey_tall', seq='95 lands/rocks/rock- frames 1, 2', cls='prop', px=2048, tris=1800, ground='forrest_ground_01', third=['rock_face_03'], weak=W_ROCK,
                              dresses='tall grey standing boulder, 0.9 x 0.8 x 1.25 m'),
    'Ore_Rock_Blue': dict(fn=b_ore, fam='ore_rock_blue', seq='95 lands/rocks/rock- frame 8', cls='prop', px=1024, tris=1800, ground='forrest_ground_01', third=['rock_boulder_dry'],
                          weak=W_ROCK + ' The blue mineral is a glossy colour mask on the rock plus nine plain prisms; it is not a modelled crystal druse and has no transmission or internal colour.',
                          dresses='dark angular rock, 0.75 x 0.6 x 0.45 m, crusted with blue-green mineral and a cluster of small blue crystal prisms on top'),
    'Gold_Coin': dict(fn=g_coin, fam='gold_coin', seq='178 bonuses/coins/coin- frame 1', cls='prop_small', px=256, tris=96, lo='param', ground='weathered_brown_planks', third=[], extrude=0.0006, maxdist=0.002,
                      weak='A 3.1 cm coin: at the gameplay camera it is a few pixels, so it will need a scale-up or a glint effect to read as a pickup. The device on its faces is a noise relief, not a designed coin. A 24-sided disc with a chamfered rim; the relief is in the normal map only.',
                      dresses='one hammered gold coin, 31 mm, lying flat'),
    'Gold_Coins_Few': dict(fn=g_few, fam='gold_coins_small', seq='178 bonuses/coins/coin- frame 2', cls='prop_small', px=512, tris=500, lo='param', ground='weathered_brown_planks', third=[], extrude=0.0006, maxdist=0.002,
                           weak='Eleven identical-profile coins laid by rule (three leaning); they do not overlap or stack as spilled coins would. Relief is in the normal map only.',
                           dresses='eleven gold coins spilled over 25 cm'),
    'Gold_Pile': dict(fn=g_pile, fam='gold_pile', seq='178 bonuses/coins/coin- frame 4', cls='prop_small', px=1024, tris=5000, lo='param', ground='weathered_brown_planks', third=[], extrude=0.012, maxdist=0.05,
                      weak='Coins are placed on a mound by rule, not settled by simulation, so some float a little or cut into their neighbours. The game mesh is a smooth mound with the heap baked onto it, the 55 coins that stand proudest as real twelve-sided discs (they break the outline; the first version was a clean dome) and the eighteen strays; between the discs there is no parallax at 1 m. A voxel skin over all the coins was tried and read as crumpled foil. Over the soft triangle target of a small prop for the discs. No gems, bag or chest.',
                      dresses='heap of about 950 gold coins, 36 cm across and 11 cm high, with strays round the foot'),
    'Heart_Red': dict(fn=lambda hi, c: heart(hi, c, ruby_mat), fam='heart_pickup', fams=['heart_pickup', 'small_heart'], seq='52 bonuses/heart/heart, 54 bonuses/heart/smhrt', cls='prop_small', px=512, tris=900, ground='weathered_brown_planks', third=[],
                      weak='A game pickup has no real-world object behind it: built as a ruby-red glass heart, 12 cm. The game material is opaque (no transmission or subsurface), so it reads as glazed ceramic rather than glass. The small heart is this mesh at half scale, set at placement. In game it should float and glow; neither is authored here.',
                      dresses='heart pickup as a ruby-red glass heart, 12 cm; the small heart is the same mesh at half scale'),
    'Heart_Gold': dict(fn=lambda hi, c: heart(hi, c, heart_gold_mat), fam='golden_heart', seq='53 bonuses/heart/gldhrt', cls='prop_small', px=512, tris=700, ground='weathered_brown_planks', third=[],
                       weak='Same form as the red heart in cast gold: no chasing, hallmark or suspension loop. In game it should float; not authored here.', dresses='golden heart (max life up) as a cast-gold heart, 12 cm, burnished on the lobes'),
    'Bomb': dict(fn=bomb, fam='bomb_item', seq='420 items/bomb/bomb- frame 1', cls='prop_small', px=1024, tris=900, ground='weathered_brown_planks', third=['rusty_metal_02'],
                 weak='A plain cast sphere with a mould seam and a rope fuse: no filling plug detail, lettering or carrying lugs. The fuse is a smooth rope with a twist in the normal map and a charred tip, without frayed fibres.',
                 dresses='cast-iron bomb, 21 cm, blue-black with rust bloom and soot round the fuse hole, short hemp fuse'),
    'Arrow': dict(fn=arrow, fam='arrow_prop', seq='25 effects/arrow/arrow- frames 2, 3, 4, 5, 8', cls='prop', px=1024, tris=900, ground='forrest_ground_01', third=['rusty_metal_02'], extrude=0.001, maxdist=0.004,
                  weak='Vanes are 0.7 mm solid sheets with barbs in the normal map, not alpha-carded feathers, so their edges are clean. Authored lying flat; the frames show it stuck in the ground at several angles and laid on a shop table, which is a placement rotation (bury the head 5 cm). A long thin object gets little texture area: about 2 px per mm on the shaft.',
                  dresses='war arrow, 82 cm: ash shaft, forged leaf head, horn nock, three red goose-feather vanes bound with thread'),
}


def build(name, mode):
    sp = SPECS[name]; L.reset(); asset = 'SM_%s_PR' % name; fams = sp.get('fams', [sp['fam']]); outdir = os.path.join(L.UNC, sp['fam'], name); hi = sp['fn'](True, L.coll('Source_Hi'))
    planks = 'planks' in sp['ground']; R = L.review_setup(ground=sp['ground'], ground_scale=1.6 if planks else 0.7, exposure=-5.0, hole=sp.get('ground_hole'))

    def shots(obs, tag, d):
        sh = sp.get('shot', {})
        L.shot(R, os.path.join(d, '%s_beauty.png' % tag), obs, az=sh.get('az', 30), el=sh.get('el', 24), fill=sh.get('fill', 0.6), lens=70, spp=192, fstop=8 if planks else None)
        if 'close' in sh:
            lo_, hi_ = L.bounds(obs); cc = lo_ + (hi_ - lo_) * np.array(sh['close'][:3])
            L.shot(R, os.path.join(d, '%s_close.png' % tag), center=cc, radius=float(np.linalg.norm(hi_ - lo_)) * sh['close'][3], az=-32, el=28, fill=0.9, lens=90, res=(1000, 800), spp=192, fstop=8)
        else:
            L.shot(R, os.path.join(d, '%s_close.png' % tag), obs, az=-32, el=30, fill=1.15, lens=90, res=(1000, 800), spp=192, fstop=11 if planks else None)
    if mode == 'review':
        shots(hi, name + '_hi', L.REVIEW); return
    lc = L.coll(asset)
    if sp.get('lo') == 'param':
        lo = L.join(sp['fn'](False, lc), asset); L.smart_uv(lo, angle=60, margin=0.02); L.pack_uv(lo, margin=0.02)
    elif sp.get('lo') == 'remesh':
        lo = L.remesh_lo(hi, sp['voxel'], sp['tris'], asset, lc, margin=0.006)
    else:
        lo = L.make_lo(hi, sp['tris'], asset, lc, angle=sp.get('uv_angle', 66), margin=0.008)
    size = float(np.linalg.norm(np.array(lo.dimensions))); P0 = L.co(lo); cen = (P0.min(0) + P0.max(0)) / 2; cen[2] = P0[:, 2].min() if not sp.get('keep_z', 'Boulder' in name or 'Ore' in name) else 0.0
    if sp.get('pivot_rule') == 'hinge':            # doors: hinge edge at x = 0, centred through the thickness, floor at z = 0; the leaf extends along +X
        cen = np.array([P0[:, 0].min(), (P0[:, 1].min() + P0[:, 1].max()) / 2, P0[:, 2].min()])
    for o in [lo] + hi:
        o.location = tuple(-cen); L.apply_xf(o)
    ids = L.origin_ids(fams)
    L.finish_static(asset, sp['cls'], lo, hi, outdir, sp['px'], families=fams + [sp['seq']], origin=ids, dresses=sp['dresses'], extrude=sp.get('extrude', size * 0.012), maxdist=sp.get('maxdist', size * 0.03),
                    third_party=sp['third'], script=sp.get('script', SCRIPT) + ' ' + name + ' final', ss=2 if sp['px'] <= 1024 else 1, weaknesses=sp['weak'], collision=sp.get('collision'), extra=sp.get('extra'))
    for o in hi:
        o.hide_render = True
    shots([lo], 'render', outdir); L.save_blend()


if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        build(n, mode)
