"""Round 2 recipes: these replace the earlier recipes of the same name (registered last)."""
import sys, os
import numpy as np
from PIL import Image
from tl import *
bs = sys.modules.get('__main__')
R, PAL, recipe = bs.R, bs.PAL, bs.recipe
UP = np.array([0, 0, 1], np.float32)


def one(aid, size):
    s = load(aid, size)
    s['used'] = [(aid, s['source'], 1)]
    return s


def flatten(S, sigma=220, amount=0.75):
    """take out the scan's own large-scale brightness drift: at 4x4 that drift is what draws the tile grid"""
    S['bc'] = np.clip(S['bc'], 0.0, None)
    l = luma(S['bc'])
    lo = gblur(l, sigma)
    S['bc'] = S['bc'] * ((l.mean() / np.maximum(lo, 1e-4)) ** amount)[..., None]
    return S


def contour_dist(n, px_m):
    """approximate distance in metres to the zero level of a smooth field"""
    gx = (np.roll(n, -1, 1) - np.roll(n, 1, 1)) * 0.5
    gy = (np.roll(n, -1, 0) - np.roll(n, 1, 0)) * 0.5
    return np.abs(n) / (np.sqrt(gx * gx + gy * gy) + 1e-6) * px_m


def add_relief(S, dh, T):
    S['h'] = S['h'] + dh
    S['n'] = S['n'] + (normal_from_height(dh, T / N) - UP)
    S['n'] = S['n'] / (np.linalg.norm(S['n'], axis=-1, keepdims=True) + 1e-9)


# ------------------------------------------------------------------ meadow plants
def stamp_plants(S, T, seed, counts, tint=0.5, h_scale=0.3):
    z = np.load(os.path.join(TERRAIN, 'Plants', 'plant_sheet.npz'), allow_pickle=False)
    alb = z['albedo'].astype(np.float32); al = z['alpha'].astype(np.float32); nr = z['normal'].astype(np.float32)
    hh = z['height'].astype(np.float32); ao = z['ao'].astype(np.float32); kinds = [str(k) for k in z['kinds']]
    cells = int(round(len(kinds) ** 0.5)); cp = alb.shape[0] // cells
    ppm = float(z['px_per_m'])
    r = np.random.default_rng(seed)
    scale0 = (N / T) / ppm
    mean_set = S['bc'].reshape(-1, 3).mean(0)
    by = {}
    for i, k in enumerate(kinds):
        by.setdefault('daisy' if k == 'daisy_flower' else k, []).append(i)
    jobs = []
    for kind, (n, clusters) in counts.items():
        if clusters:
            cc = r.uniform(0, 1, (clusters, 2))
            for _ in range(n):
                c = cc[r.integers(clusters)] + r.normal(0, 0.035 * 2.8 / T, 2)
                jobs.append((kind, c[0] % 1, c[1] % 1))
        else:
            for _ in range(n):
                jobs.append((kind, r.uniform(), r.uniform()))
    order = r.permutation(len(jobs))
    bc, nn, hgt, aoo, rough = S['bc'], S['n'], S['h'], S['ao'], S['rough']
    base0 = hgt.copy()
    for j in order:
        kind, u, v = jobs[j]
        ci = by[kind][r.integers(len(by[kind]))]
        y0 = (cells - 1 - ci // cells) * cp; x0 = (ci % cells) * cp          # image row 0 is the top (+Y)
        ang = r.uniform(0, 360); sc = scale0 * r.uniform(0.8, 1.25)
        m = max(8, int(round(cp * sc)))

        def tf(a, resample=Image.BILINEAR):
            im = Image.fromarray(np.ascontiguousarray(a[y0:y0 + cp, x0:x0 + cp]), 'F').rotate(ang, resample=resample).resize((m, m), Image.BILINEAR)
            return np.asarray(im)
        A = np.clip(tf(al), 0, 1)
        if A.max() < 0.05:
            continue
        C = np.stack([tf(alb[..., k]) for k in range(3)], -1)
        Nx = tf(nr[..., 0]); Ny = tf(nr[..., 1]); Nz = tf(nr[..., 2])
        a = np.radians(ang); ca, sa = np.cos(a), np.sin(a)
        Nx, Ny = Nx * ca - Ny * sa, Nx * sa + Ny * ca      # PIL rotates counter-clockwise on screen = counter-clockwise in +Y-up space
        Hd = tf(hh); Ad = tf(ao)
        if kind in ('clover', 'plantain', 'daisy', 'dandelion'):
            g = C[A > 0.6]
            if len(g):
                green = (C[..., 1] > C[..., 0] * 1.05)[..., None]
                f = (mean_set / (np.median(g, 0) + 1e-4)) ** tint
                C = np.where(green, C * f * r.uniform(0.9, 1.2), C)
        iy = (int((1 - v) * N) + np.arange(m) - m // 2) % N
        ix = (int(u * N) + np.arange(m) - m // 2) % N
        I = np.ix_(iy, ix)
        A3 = A[..., None]
        bc[I] = bc[I] * (1 - A3) + C * A3
        nd = np.stack([Nx, Ny, np.maximum(Nz, 0.2)], -1)
        nn[I] = nn[I] * (1 - A3) + nd * A3
        hgt[I] = np.maximum(hgt[I], (base0[I] + Hd * h_scale) * A + hgt[I] * (1 - A))
        aoo[I] = aoo[I] * (1 - A) + np.clip(Ad, 0, 1) ** 0.7 * A
        # soft contact shade under the plant, in AO only
        rough[I] = rough[I] * (1 - A) + (0.62 if kind != 'litter' else 0.85) * A
    S['n'] = nn / (np.linalg.norm(nn, axis=-1, keepdims=True) + 1e-9)
    return S


@recipe
def MeadowTurf():
    T = 2.8
    a = rep(load('Grass004', 1.4), 2)
    b = match_colour(rep(load('Grass001', 1.4), 2, (0.17, 0.39)), a, 0.8)
    c = match_colour(fit(load('leafy_grass', 2.0), T, (0.31, 0.13)), a, 0.55)
    for x in (a, b):
        x['h'] = x['h'] * 2.5
    s = hblend(a, b, cover(fbm(11, 0.5, 0.05, 1.3), 0.42, 0.6), 0.5)
    s = hblend(s, c, cover(fbm(12, 0.30, 0.025, 1.1), 0.22, 0.30), 1.0, 0.3)
    drift = fbm(13, 1.0, 0.2, 1.6)
    s['bc'] = s['bc'] * (1 + 0.09 * drift[..., None] * np.array([1.0, 0.6, 0.9], np.float32))
    grade(s, PAL['grass'], hue=0.55, mean_luma=96, sat=0.92, contrast=1.05)
    s['rough'] = np.clip(s['rough'] + 0.2, 0, 1)
    stamp_plants(s, T, 101, {'clover': (520, 30), 'plantain': (30, 0), 'daisy': (26, 0), 'dandelion': (12, 0), 'litter': (90, 0)})
    return write_set('MeadowTurf', s, T, ['grass'], seed=1,
                     note='ambientCG Grass004 (2x2) height-blended with Grass001 (2x2, shifted) and Poly Haven leafy_grass (true scale, worn patches), plus plants modelled here in Blender and baked top-down as decals (clover patches, plantain, daisy and dandelion rosettes, a few daisy flowers, dry leaves and straw blades); graded toward the original grass palette',
                     weaknesses='plants are stamped decals in albedo, normal and AO with only a few millimetres of height: they do not stand up at grazing view; the 1.4 m lawn period can still be found in a flat-lit 4x4 view')


@recipe
def WildGrass():
    T = 4.0
    a = rep(load('sparse_grass', 2.0), 2)
    b = match_colour(fit(load('Grass001', 1.4), T, (0.23, 0.41)), a, 0.93)
    c = match_colour(fit(load('leafy_grass', 2.0), T, (0.11, 0.37)), a, 0.85)
    b['h'] = b['h'] * 2.5
    s = hblend(a, b, cover(fbm(21, 0.30, 0.03, 1.1), 0.36, 0.5), 1.2, 0.5)
    s = hblend(s, c, cover(fbm(22, 0.25, 0.03, 1.1), 0.14, 0.4), 1.2, 0.4)
    drift = fbm(23, 1.0, 0.2, 1.6)
    s['bc'] = s['bc'] * (1 + 0.10 * drift[..., None] * np.array([1.0, 0.7, 0.8], np.float32))
    # clump structure: tussocks stand a little proud, the gaps between them are shaded and strawy
    tus = fbm(24, 0.06, 0.02, 1.0)
    add_relief(s, tus * 0.004, T)
    s['ao'] = np.clip(s['ao'] * (1 - 0.22 * smooth(0.2, -1.2, tus)), 0, 1)
    s['bc'] = s['bc'] * (1 + 0.10 * np.clip(tus, -1.5, 1.5)[..., None] * np.array([0.8, 1.0, 0.7], np.float32))
    grade(s, PAL['grass_rocky'], hue=0.8, mean_luma=82, sat=0.95, contrast=1.08)
    stamp_plants(s, T, 202, {'clover': (420, 26), 'plantain': (110, 0), 'dandelion': (90, 0), 'daisy': (24, 0), 'litter': (520, 0)}, tint=0.6)
    return write_set('WildGrass', s, T, ['grass', 'grass_rocky', 'forest_canopy'], seed=2, status='interim',
                     note='Poly Haven sparse_grass (2x2, long dry-strawed grass) with patches of ambientCG Grass001 and Poly Haven leafy_grass at true scale, plus modelled-and-baked plant decals (plantain, dandelion, clover, dry leaves and straw); darker and rougher than MeadowTurf',
                     weaknesses='reads as rough pasture rather than knee-high grass: length must come from 3D tufts; 1.95 mm per pixel, soft under 1 m; decals are flat')


# ------------------------------------------------------------------ grid fixes
@recipe
def CliffRock():
    T = 2.7
    a = flatten(one('rock_face_03', 2.7))
    # find the scan's straight through-going joints (they draw a cross at 4x4) and make sure the second rock covers them
    def band(profile):
        p = profile - np.convolve(np.tile(profile, 3), np.ones(301) / 301, 'same')[N:2 * N]
        i0 = int(np.argmin(p))
        t = (np.arange(N) - i0 + N // 2) % N - N // 2
        return np.exp(-(t / (0.035 * N)) ** 2).astype(np.float32)
    bx = band(gblur(a['h'], 3).mean(0)); by = band(gblur(a['h'], 3).mean(1))
    b = match_colour(flatten(fit(load('rock_face', 2.38), T, (0.31, 0.17))), a, 0.9)
    b['h'] = b['h'] * (a['h'].std() / (b['h'].std() + 1e-9)) * 0.9
    c = match_colour(fit(rot90(load('rock_face_03', 2.7)), T * 1.31, (0.55, 0.4)), a, 1.0)
    c['size_m'] = T
    wob = fbm(91, 0.3, 0.03, 1.2)
    m1 = np.clip(cover(fbm(92, 0.5, 0.05, 1.3), 0.34, 0.35) + np.clip((bx[None, :] + by[:, None]) * 1.6 + 0.35 * wob - 0.25, 0, 1), 0, 1)
    s = hblend(a, c, m1, 0.9, 0.35)
    s = hblend(s, b, cover(fbm(93, 0.45, 0.05, 1.3), 0.28, 0.35), 0.9, 0.35)
    grade(s, (98, 82, 64), hue=0.75, mean_luma=92, sat=0.8, contrast=1.1)
    return write_set('CliffRock', s, T, ['cliff_face', 'rock_mass'], seed=9,
                     note='Poly Haven rock_face_03 with its two straight through-going joints located and covered by a turned, enlarged copy of itself, plus patches of Poly Haven rock_face at a non-commensurate scale; large-scale brightness drift removed; graded to the dark grey-brown of the original cliffs',
                     weaknesses='no bedding direction, so it does not read as layered strata; relief of 8 cm needs parallax or tessellation to show on a flat cliff mesh')


@recipe
def ForestFloor():
    T = 3.0
    a = flatten(selfblend(load('forest_leaves_04', 1.5), 2, 54, 1, (0.29, 0.43)))
    b = flatten(fit(load('forrest_ground_03', 2.0), T, (0.19, 0.33)))
    c0 = load('forest_leaves_02', 3.0)
    c = flatten(fit(c0, T * 0.83, (0.41, 0.07)), 160, 0.9)
    c['size_m'] = T
    c['h'] = c['h'] * 0.45
    c['n'] = c['n'] * np.array([0.6, 0.6, 1.0], np.float32)
    b = match_colour(b, a, 0.75)
    c = match_colour(c, a, 0.3)
    g = c['bc']
    green = smooth(0.0, 0.06, g[..., 1] - 0.5 * (g[..., 0] + g[..., 2]) * 1.05)
    c['bc'] = g * (1 - green[..., None]) + g * np.array([0.62, 0.95, 0.55], np.float32) * green[..., None]
    s = hblend(a, c, cover(fbm(52, 0.5, 0.05, 1.3), 0.40, 0.35), 0.8)
    s = hblend(s, b, cover(fbm(51, 0.35, 0.03, 1.2), 0.20, 0.25), 1.6, 0.5)
    s['bc'] = s['bc'] * (1 + 0.06 * fbm(53, 0.4, 0.1, 1.4)[..., None])
    grade(s, (92, 78, 48), hue=0.6, mean_luma=74, sat=0.8, contrast=1.05)
    return write_set('ForestFloor', s, T, ['forest_canopy', 'grass'], seed=5,
                     note='Poly Haven forest_leaves_04 (2x2, self-blended with a quarter-turned copy) with forest_leaves_02 (moss, sticks, leaves; non-commensurate scale, relief halved) and patches of forrest_ground_03 (pine needle mat); every layer has its large-scale brightness drift removed so no band survives at 4x4; desaturated and darkened for shade',
                     weaknesses='no cones; moss is sparse and olive rather than deep green')


@recipe
def ScorchedSoil():
    T = 4.0
    a = flatten(selfblend(load('mud_cracked_dry_riverbed_002', 2.0), 2, 194, 1, (0.33, 0.19), hk=0.3))
    b0 = load('burned_ground_01', 1.0)
    b = match_colour(flatten(fit(b0, T / 1.37, (0.21, 0.37)), 120, 0.9), a, 0.72)     # 1.37 x enlarged: 2.92 periods across the tile
    b['size_m'] = T
    s = hblend(a, b, cover(fbm(191, 0.22, 0.02, 1.1), 0.36, 0.5), 0.9, 0.45)
    grade(s, (78, 74, 70), hue=0.85, mean_luma=64, sat=0.55, contrast=1.1)
    ash = cover(fbm(192, 0.2, 0.012, 1.2), 0.3, 0.6) * smooth(0.0, 1.0, (s['h'] - s['h'].mean()) / (s['h'].std() + 1e-9) * -1 + 0.3)
    s['bc'] = s['bc'] * (1 - 0.5 * ash[..., None]) + np.float32(0.16) * 0.5 * ash[..., None]
    s['rough'] = s['rough'] + 0.05 * ash
    return write_set('ScorchedSoil', s, T, ['wasteland'], seed=19,
                     note='Poly Haven mud_cracked_dry_riverbed_002 (2x2, self-blended with a quarter-turned copy) height-blended with burned_ground_01 (charred turf, dead straw; non-commensurate scale), desaturated to char with pale ash settled in the hollows',
                     weaknesses='1.95 mm per pixel: cracks soften under 1 m; the burnt-straw layer is 1.37 times life size; the original wasteland tiles are grey-green rock, this is the darker scorched reading the brief asks for')


@recipe
def SnowTrampled():
    T = 4.0
    src = load('snow_01', 2.0)
    src['h'] = src['h'] - gblur(src['h'], 200) * 0.8          # level the scan first so the two copies meet at one height
    flatten(src, 200, 0.8)
    s = selfblend(src, 2, 181, 0, (0.29, 0.37), frac=0.5, soft=0.9, hk=0.25)     # not turned: trodden snow is directional and a turned copy shades differently under a low sun
    s['bc'] = s['bc'] * (1 + 0.03 * fbm(182, 1.0, 0.2, 1.6)[..., None])
    grade(s, PAL['snow'], hue=0.8, mean_luma=212, sat=0.8, contrast=0.9)
    return write_set('SnowTrampled', s, T, ['snow', 'path'], seed=18,
                     note='Poly Haven snow_01 (boot-trodden snow), 2x2, levelled, then height-blended with a shifted copy of itself under a 4 m mask so the 2 m period is broken; prints still run along V and the 2 m period is broken',
                     weaknesses='modern boot treads are visible under 1 m; 1.95 mm per pixel')


# ------------------------------------------------------------------ dungeon
@recipe
def DungeonFlagstone():
    T = 2.0
    a = flatten(one('stone_tiles_02', 2.0), 200, 0.6)
    hn = (a['h'] - a['h'].mean()) / (a['h'].std() + 1e-9)
    worn = cover(fbm(131, 0.8, 0.15, 1.6), 0.45, 1.2) * smooth(-0.2, 0.8, hn)          # foot-polished slab tops along walked lines
    a['rough'] = a['rough'] * (1 - 0.28 * worn)
    a['bc'] = a['bc'] * (1 + 0.10 * worn[..., None])
    grit = smooth(-0.6, -1.6, hn) * cover(fbm(132, 0.3, 0.02, 1.1), 0.6, 0.8)             # dirt packed into the joints
    a['bc'] = a['bc'] * (1 - grit[..., None]) + np.array([0.035, 0.030, 0.024], np.float32) * grit[..., None]
    a['rough'] = a['rough'] + 0.1 * grit
    grade(a, (84, 86, 82), hue=0.8, mean_luma=74, sat=0.5, contrast=1.08)
    return write_set('DungeonFlagstone', a, T, ['stone_floor'], seed=13, rough_gain=0.95,
                     note='Poly Haven stone_tiles_02 (large irregular split slabs with mortared joints), darkened to the original dungeon floor grey, with foot-polished slab tops along walked lines and dark grit packed in the joints. Floor only: irregular slabs, no courses',
                     weaknesses='single scan at 2 m; slabs are 25-45 cm, smaller than a great-hall flag')


def _masonry():
    a = flatten(one('stone_brick_wall_001', 2.5), 220, 0.6)
    return a


MASON = (128, 108, 70)


@recipe
def DungeonMasonry():
    T = 2.5
    a = _masonry()
    print('   masonry scan rough mean/std', float(a['rough'].mean()), float(a['rough'].std()), 'ao', float(a['ao'].mean()))
    grade(a, MASON, hue=0.75, mean_luma=96, sat=0.85, contrast=1.05)
    return write_set('DungeonMasonry', a, T, ['structure_facade', 'cave_wall'], seed=14,
                     note='Poly Haven stone_brick_wall_001 (coursed rough-faced ashlar, mixed block sizes, deeply recessed mortar), graded to the golden olive-brown of the original dungeon wall sprites. Walls only: horizontal courses along U',
                     weaknesses='single scan at 2.5 m, the same as one wall module, so the block layout repeats per module unless the mesh UVs are offset (the wall kit does this); courses are 15-35 cm',
                     extra={'wall_grime_mask': 'PlasterWall/T_Terrain_PlasterWall_WallGrime.png works for this set too (R damp at the base: blend toward DungeonMasonryDamp)'})


@recipe
def DungeonMasonryDamp():
    T = 2.5
    a = _masonry()
    hn = (a['h'] - a['h'].mean()) / (a['h'].std() + 1e-9)
    m = flatten(fit(load('mossy_rock', 3.0), T, (0.2, 0.6)), 150, 0.8)
    g = m['bc']
    green = smooth(0.0, 0.05, g[..., 1] - 0.5 * (g[..., 0] + g[..., 2]) * 1.02)        # keep only the moss and lichen of that scan
    streak = fbm(141, 0.5, 0.01, 1.0, aniso=(1.0, 0.07))                                  # vertical run-off streaks
    wet = np.clip(0.55 + 0.35 * streak, 0, 1)
    grade(a, MASON, hue=0.75, mean_luma=96, sat=0.85, contrast=1.05)
    a['bc'] = a['bc'] * (1 - 0.42 * wet[..., None]) * np.array([0.95, 1.0, 0.93], np.float32)
    a['rough'] = np.clip(a['rough'] - 0.30 * wet, 0.15, 1)
    mm = np.clip(cover(fbm(142, 0.35, 0.03, 1.2), 0.5, 0.5) * (0.35 + 0.65 * smooth(0.3, -0.9, hn)) * (0.3 + green * 1.2), 0, 1)
    mossc = g * np.array([0.55, 0.85, 0.45], np.float32) * (0.10 / max(float(luma(g).mean()), 1e-3))
    a['bc'] = a['bc'] * (1 - mm[..., None]) + mossc * mm[..., None]
    a['rough'] = a['rough'] * (1 - mm) + 0.9 * mm
    a['h'] = a['h'] + 0.003 * mm
    a['used'] = a['used'] + [('mossy_rock', 'polyhaven', 0.83)]
    return write_set('DungeonMasonryDamp', a, T, ['structure_facade', 'cave_wall'], seed=24,
                     note='the DungeonMasonry wall with the same block layout (so the two blend by mask without ghosting): darker and glossier with vertical run-off streaks, and moss and lichen (from Poly Haven mossy_rock) grown in the joints and on the lower block faces. Meant for the lowest metre of a wall, blended in with the WallGrime R channel or vertex colour',
                     weaknesses='moss is a colour and roughness layer with 3 mm of height, not tufts')


# ------------------------------------------------------------------ plaster
def _trowel(seed, T, n=1024, strokes=170):
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    h = np.zeros((n, n), np.float32)
    for _ in range(strokes):
        cx, cy = r.uniform(0, 1, 2); Rr = r.uniform(0.18, 0.5) / T * 1.0; w = r.uniform(0.05, 0.09) / T
        a0 = r.uniform(0, 6.283); span = r.uniform(0.5, 1.4)
        dx = (x - cx + 0.5) % 1 - 0.5; dy = (y - cy + 0.5) % 1 - 0.5
        rr = np.sqrt(dx * dx + dy * dy)
        aa = (np.arctan2(dy, dx) - a0 + np.pi) % (2 * np.pi) - np.pi
        p = (rr - Rr) / w
        mask = np.clip(1 - np.abs(aa) / span, 0, 1) ** 0.6 * (np.abs(p) < 0.5)
        prof = 0.5 * p + 0.5 * np.exp(-((p - 0.36) / 0.16) ** 2) - 0.3 * np.exp(-((p + 0.36) / 0.18) ** 2)
        h = h * (1 - 0.7 * mask) + prof * mask * r.uniform(0.6, 1.2)
    im = Image.fromarray(np.ascontiguousarray(h, dtype=np.float32), 'F').resize((N, N), Image.BICUBIC)
    return np.asarray(im).astype(np.float32)


def _plaster_base(T):
    a = flatten(fit(load('painted_plaster_wall', 2.0), T, (0.1, 0.2)), 200, 0.8)
    b = match_colour(flatten(fit(load('plastered_wall_04', 3.2), T, (0.4, 0.3)), 200, 0.8), a, 0.9)
    s = hblend(a, b, cover(fbm(151, 0.5, 0.04, 1.3), 0.45, 0.9), 0.4, 0.8)
    # trowel sweeps: overlapping arcs with a raised lip, about half a millimetre
    tr = _trowel(155, T)
    add_relief(s, gblur(tr, 2.0) * 0.0007, T)
    s['bc'] = s['bc'] * (1 + 0.035 * np.clip(tr, -1, 1)[..., None])
    s['rough'] = np.clip(s['rough'] - 0.05 * np.clip(tr, 0, 1), 0, 1)       # the trowel lip is burnished
    # limewash: coat thickness and tone vary, brushed in vertical-ish strokes
    wash = fbm(152, 0.6, 0.015, 1.0, aniso=(1.0, 0.16)) * 0.5 + fbm(156, 0.9, 0.2, 1.6) * 0.8
    thin = cover(fbm(157, 0.45, 0.04, 1.3), 0.22, 0.8)
    s['bc'] = s['bc'] * (1 + 0.045 * wash[..., None] * np.array([1.0, 0.95, 0.8], np.float32)) * (1 - 0.10 * thin[..., None])
    s['rough'] = np.clip(s['rough'] + 0.03 * wash + 0.05 * thin, 0, 1)
    # hairline cracks: a main meandering set and short branches off it
    c1 = contour_dist(fbm(158, 0.7, 0.12, 1.7), T / N)
    c2 = contour_dist(fbm(159, 0.25, 0.05, 1.5), T / N)
    g1 = cover(fbm(160, 0.6, 0.1, 1.4), 0.38, 0.4)
    crack = np.exp(-(c1 / 0.0009) ** 2) * g1 + np.exp(-(c2 / 0.0006) ** 2) * g1 * np.exp(-(c1 / 0.10) ** 2) * 0.8
    crack = np.clip(crack, 0, 1)
    add_relief(s, -crack * 0.0007, T)
    s['bc'] = s['bc'] * (1 - 0.5 * crack[..., None])
    s['ao'] = s['ao'] * (1 - 0.5 * crack)
    s['used'] = [('painted_plaster_wall', 'polyhaven', round(T / 2.0, 2)), ('plastered_wall_04', 'polyhaven', round(T / 3.2, 2))]
    return s


PLASTER = (176, 172, 152)       # limewash over grey lime plaster: the original interior wall sprites are a grey-olive, not white


def _wall_grime():
    n = 512
    v = (1 - (np.arange(n) + 0.5) / n)[:, None]
    wick = fbm(153, 0.5, 0.03, 1.2, n)[0:1, :] * 0.06 + fbm(154, 0.2, 0.02, 1.0, n) * 0.035
    damp = smooth(0.34, 0.02, v + wick) * (0.75 + 0.25 * np.clip(fbm(155, 0.3, 0.03, 1.2, n) * 0.5 + 0.5, 0, 1))
    soot = smooth(0.62, 1.0, v + fbm(156, 0.4, 0.05, 1.3, n) * 0.07) ** 1.5
    drip = np.clip(fbm(157, 0.6, 0.01, 0.8, n, aniso=(1.0, 0.04)) * 0.5, 0, 1) * smooth(0.2, 0.9, v)
    g = np.stack([damp, soot, drip], -1)
    Image.fromarray(np.clip(g * 255 + 0.5, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(TERRAIN, 'PlasterWall', 'T_Terrain_PlasterWall_WallGrime.png'))


GRIME_NOTE = 'non-tiling in V (0 floor, 1 ceiling), tiles in U; R damp at the base (darken x0.7, tint green-brown, roughness -0.15, or blend to the Damp/Broken variant), G soot under the ceiling (multiply toward 0.25 grey), B drip streaks'


@recipe
def PlasterWall():
    T = 2.5
    s = _plaster_base(T)
    grade(s, PLASTER, hue=0.85, mean_luma=168, sat=0.9, contrast=1.0)
    info = write_set('PlasterWall', s, T, ['structure_facade'], seed=15,
                     note='lime plaster built from Poly Haven painted_plaster_wall and plastered_wall_04 (both at non-commensurate scales) with trowel sweeps (overlapping arcs with a burnished lip, in height, normal and roughness), limewash coat variation in brushed strokes, and a hairline crack network with branches; graded to the grey-olive limewash of the original interior wall sprites',
                     weaknesses='trowel sweeps and cracks are synthesised, not scanned; one tile is one 2.5 m wall module, so offset UVs between modules (the wall kit does)')
    _wall_grime()
    info['files']['WallGrime'] = 'PlasterWall/T_Terrain_PlasterWall_WallGrime.png'
    info['wall_grime_mask'] = GRIME_NOTE
    json.dump(info, open(os.path.join(TERRAIN, 'PlasterWall', 'set.json'), 'w'), indent=1)
    return info


@recipe
def PlasterWallBroken():
    T = 2.5
    s = _plaster_base(T)
    grade(s, PLASTER, hue=0.85, mean_luma=168, sat=0.9, contrast=1.0)
    # layer 1: flaking, patched and stained old plaster from the scan
    c = match_colour(flatten(fit(load('rough_plaster_broken', 1.5), T, (0.3, 0.1)), 160, 0.7), s, 0.72)
    s2 = hblend(s, c, cover(fbm(161, 0.45, 0.04, 1.3), 0.34, 0.3), 0.6, 0.3)
    # layer 2: plaster fallen away to the rubble stone behind, with a broken 12 mm edge
    st = _masonry()
    grade(st, (150, 132, 100), hue=0.7, mean_luma=118, sat=0.7)                 # lime-stained rubble, not far below the plaster in value
    edge = fbm(162, 0.08, 0.012, 1.1)
    f = fbm(163, 0.7, 0.12, 1.7) + 0.10 * edge
    q = np.quantile(f[::4, ::4], 0.935)
    hole = smooth(q - 0.03, q + 0.03, f)
    rim = smooth(q - 0.30, q - 0.02, f) * (1 - hole)                         # stained, crumbling margin
    out = dict(s2)
    H3 = hole[..., None]
    out['bc'] = s2['bc'] * (1 - 0.22 * rim[..., None]) * (1 - H3) + st['bc'] * 0.9 * H3
    out['rough'] = s2['rough'] * (1 - hole) + st['rough'] * hole
    out['ao'] = s2['ao'] * (1 - hole) + np.clip(st['ao'] * 1.1, 0, 1) * hole
    out['h'] = (s2['h'] + 0.012) * (1 - hole) + (st['h'] * 0.6) * hole - 0.002 * rim
    out['n'] = normal_from_height(gblur(out['h'], 0.7), T / N) * 0.7 + (s2['n'] * (1 - H3) + st['n'] * H3) * 0.3
    out['n'] = out['n'] / (np.linalg.norm(out['n'], axis=-1, keepdims=True) + 1e-9)
    out['used'] = s['used'] + [('rough_plaster_broken', 'polyhaven', round(T / 1.5, 2)), ('stone_brick_wall_001', 'polyhaven', 1)]
    return write_set('PlasterWallBroken', out, T, ['structure_facade'], seed=25, status='interim',
                     note='PlasterWall with the same trowel and crack layout, plus flaking and patched plaster from Poly Haven rough_plaster_broken and areas where the plaster has fallen off the rubble stone behind (stone_brick_wall_001), with a broken 12 mm edge and stained margin. A dressing variant to blend into PlasterWall by vertex colour or mask on a few modules, not for whole rooms',
                     weaknesses='the exposed backing is stone, not lath; the fallen patches are landmarks, so use it on single modules',
                     extra={'wall_grime_mask': GRIME_NOTE})


# ------------------------------------------------------------------ snow, lava
@recipe
def Snow():
    T = 3.0
    s = fit(load('Snow008A', 2.0), T, (0.2, 0.1))
    fine_n = s['n'].copy()
    f = fbm(171, 0.55, 0.02, 1.75, aniso=(0.28, 1.0))                # wind along U: long ridges
    f = f + 0.35 * fbm(172, 0.12, 0.012, 1.3, aniso=(0.4, 1.0))
    t = f * 1.6
    k = np.floor(t); fr = t - k
    ter = k + smooth(0.0, 0.22, fr)                                     # wind-cut terraces with sharp undercut risers
    sas = (0.62 * ter + 0.38 * t) * 0.0045
    dune = fbm(173, 1.0, 0.25, 2.0) * 0.005
    crust = fbm(174, 0.02, 0.003, 0.8) * 0.0006                         # sintered surface grain
    h = sas + dune + crust
    s['h'] = h
    s['n'] = normal_from_height(h, T / N) + (fine_n - UP) * 0.5
    s['n'] = s['n'] / (np.linalg.norm(s['n'], axis=-1, keepdims=True) + 1e-9)
    cav = gblur(h, 14) - h
    s['ao'] = np.clip(1 - np.clip(cav / 0.003, 0, 1) * 0.5, 0, 1)
    riser = smooth(0.0, 0.22, fr) * (1 - smooth(0.22, 0.5, fr))         # the freshly cut faces
    packed = smooth(-0.3, 0.8, f)                                       # windward crests are wind-packed and glazed
    l = luma(s['bc'])
    s['bc'] = (s['bc'] / l.mean()) * 0 + np.float32(0.72) * (1 + 0.03 * fbm(175, 0.3, 0.01, 1.2)[..., None] - 0.035 * riser[..., None] + 0.02 * packed[..., None]) * np.array([0.975, 0.995, 1.02], np.float32)
    rough = 0.80 - 0.32 * packed + 0.08 * riser
    r = np.random.default_rng(176)
    sp = gblur((r.uniform(size=(N, N)) > 0.988).astype(np.float32), 0.55) * 4.0      # sparse sun-facing crystal faces
    s['rough'] = np.clip(rough - np.clip(sp, 0, 1) * 0.45, 0.12, 1)
    s['used'] = [('Snow008A', 'ambientcg', round(T / 2.0, 2))]
    grade(s, PAL['snow'], hue=0.8, mean_luma=226, sat=0.8, contrast=1.0)
    return write_set('Snow', s, T, ['snow', 'ice'], seed=17,
                     note='wind-sculpted fresh snow built here: sastrugi as wind-aligned terraced ridges with undercut risers over low drift swells (synthesised height, 3 m period), fine crust normal from ambientCG Snow008A, glazed wind-packed crests and sparse crystal glints in roughness. No tracks. Wind runs along U',
                     weaknesses='sastrugi are synthesised, not scanned; direction is fixed along U; albedo is capped at 240 so subsurface and sparkle bloom must come from the Unreal material')


@recipe
def LavaCrust():
    T = 3.0
    px = T / N
    n1 = fbm(201, 0.60, 0.16, 1.9)
    n2 = fbm(202, 0.50, 0.14, 1.9)
    n3 = fbm(203, 0.20, 0.06, 1.7)
    g3 = cover(fbm(204, 0.7, 0.2, 1.6), 0.45, 0.25)                       # only part of the field is broken small
    d1 = contour_dist(n1, px); d2 = contour_dist(n2, px); d3 = contour_dist(n3, px) + (1 - g3) * 1.0
    wv = 0.6 + 0.5 * np.clip(fbm(205, 0.3, 0.05, 1.3) * 0.5 + 0.5, 0, 1)   # crack width varies along its length
    dmain = np.minimum(d1 / (0.010 * wv), d2 / (0.007 * wv))
    dall = np.minimum(dmain, d3 / 0.0035)
    crack = np.exp(-dall ** 2)                                            # 1 in the crack floor
    dm = np.minimum(np.minimum(d1, d2), d3)
    # each plate sits at its own level and tilt (signs of the three fields give a per-plate id without labelling)
    s1 = np.tanh(n1 / 0.06); s2 = np.tanh(n2 / 0.06); s3 = np.tanh(n3 / 0.08) * g3
    level = 0.010 * s1 + 0.007 * s2 * (1 + 0.5 * s1) + 0.004 * s3
    tilt = 0.012 * fbm(206, 0.5, 0.2, 1.8) * s1 * s2
    dome = 0.014 * (1 - np.exp(-dm / 0.035))
    # ropy pahoehoe folds on some plates, slabby aa clinker on the others
    wx = fbm(207, 0.5, 0.12, 1.8) * 0.10; wy = fbm(208, 0.5, 0.12, 1.8) * 0.10
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    ropy = cover(fbm(209, 0.6, 0.2, 1.7) + 0.6 * s1, 0.5, 0.5)
    ph = (x * 3 + y * 2) * 7 + (wx + wy) * 9 + 1.5 * s1 + 0.8 * s2          # integer wave vector keeps the ropes periodic; each plate has its own phase
    ph = ph + 2.5 * (dm / 0.05) * 0                                         # (folds bow with the flow via the warp)
    ropes = (np.abs(np.sin(np.pi * ph)) ** 0.6) * 0.004 * ropy * (1 - np.exp(-dm / 0.02)) * cover(fbm(214, 0.3, 0.05, 1.4), 0.6, 0.8)
    clink = (fbm(210, 0.05, 0.006, 1.2) * 0.0035 + np.abs(fbm(211, 0.02, 0.004, 1.0)) * 0.002) * (1 - ropy)
    det = fit(load('rock_face_04', 2.0), T, (0.1, 0.6))
    h = (level + tilt + dome) * 0.55 + ropes + clink + det['h'] * 0.25 * (1 - 0.6 * ropy) - 0.022 * crack
    S = {}
    S['h'] = h.astype(np.float32)
    S['n'] = normal_from_height(gblur(S['h'], 0.5), px) + (det['n'] - UP) * 0.35
    S['n'] = S['n'] / (np.linalg.norm(S['n'], axis=-1, keepdims=True) + 1e-9)
    ld = np.clip(luma(det['bc']), 1e-4, None); ld = (ld / ld.mean()) ** 0.7
    var = fbm(212, 0.5, 0.04, 1.4)
    base = np.array([0.034, 0.032, 0.034], np.float32) * (1 + 0.22 * var[..., None]) * ld[..., None]
    base = base * (1 + ropy[..., None] * np.array([-0.12, -0.08, 0.06], np.float32))          # glassy blue-black pahoehoe skin
    ox = np.exp(-dall / 2.2) * (1 - crack)                                                      # oxidised rims
    base = base * (1 + ox[..., None] * np.array([1.6, 0.35, 0.0], np.float32))
    # glow: only the floor of the main cracks, only in the hot part of the field, falling off up the crack walls
    hot = cover(fbm(213, 0.9, 0.3, 1.8), 0.40, 0.6)
    core = np.exp(-(dmain / 0.36) ** 2) * cover(fbm(215, 0.18, 0.03, 1.2), 0.42, 0.35)      # broken into lengths, not one ribbon
    glow = np.clip(core * hot, 0, 1)
    halo = np.clip(np.exp(-dmain / 1.1) * hot * 0.10, 0, 1) * (1 - core)
    S['emis'] = np.clip(glow + halo, 0, 1).astype(np.float32)
    base = base * (1 - 0.7 * crack[..., None])
    S['bc'] = base.astype(np.float32)
    S['rough'] = np.clip(0.78 - 0.42 * ropy * (0.6 + 0.4 * np.abs(np.sin(np.pi * ph))) + 0.1 * var + 0.15 * crack, 0.18, 1).astype(np.float32)
    cav = gblur(S['h'], 10) - S['h']
    S['ao'] = np.clip(1 - np.clip(cav / 0.008, 0, 1) * 0.75, 0.1, 1).astype(np.float32)
    S['used'] = [('rock_face_04', 'polyhaven', round(T / 2.0, 2))]
    return write_set('LavaCrust', S, T, ['lava', 'wasteland'], seed=20, status='interim',
                     note='built here (no CC0 lava scan is usable): plates of varied size from three overlaid crack fields, each plate at its own level and tilt, ropy pahoehoe folds with a glassy skin on some plates and rough aa clinker on the others, oxidised rims, Poly Haven rock_face_04 for surface grain. The E mask is the floor of the main cracks only, in the hot 40 percent of the field, with a faint halo up the crack walls',
                     weaknesses='synthesised: plate outlines are smooth-noise contours, more rounded than real fracture; ropes all run one way',
                     extra={'emissive': 'E mask 0..1; suggested colour ramp (1.0,0.12,0.0) to (1.0,0.75,0.25), strength 20-60 nits scaled by E'})


# ------------------------------------------------------------------ building materials (round 3)
@recipe
def TownRubble():
    a = flatten(one('castle_wall_slates', 2.5), 220, 0.6)
    grade(a, (96, 88, 74), hue=0.6, mean_luma=84, sat=0.75, contrast=1.05)
    return write_set('TownRubble', a, 2.5, ['structure_facade'], seed=31,
                     note='Poly Haven castle_wall_slates (coursed rubble of thin slabs in lime mortar), darkened to the grey-brown ground-floor stone of the original town house sprites', weaknesses='single scan; one pale block is a landmark every 2.5 m')


@recipe
def RoofShingle():
    a = flatten(one('roof_slates_02', 3.0), 220, 0.5)
    moss = cover(fbm(321, 0.5, 0.05, 1.4), 0.12, 0.5) * smooth(0.3, -0.8, (a['h'] - a['h'].mean()) / (a['h'].std() + 1e-9))
    grade(a, (118, 112, 96), hue=0.6, mean_luma=104, sat=0.8, contrast=1.08)
    a['bc'] = a['bc'] * (1 - moss[..., None]) + np.array([0.05, 0.075, 0.025], np.float32) * moss[..., None]
    a['rough'] = np.clip(a['rough'] + 0.08 * moss, 0, 1)
    return write_set('RoofShingle', a, 3.0, ['structure_facade'], seed=32,
                     note='Poly Haven roof_slates_02 (weathered split shingles in courses), graded to the pale grey-olive of the original roof sprites, with moss in the laps. Courses run along U, eaves toward -V',
                     weaknesses='single scan; shingles are small (about 8 cm) against the broad courses of the sprite')


@recipe
def DoorPlanks():
    a = one('medieval_wood', 2.0)
    grade(a, (96, 62, 38), hue=0.7, mean_luma=70, sat=0.9, contrast=1.05)
    return write_set('DoorPlanks', a, 2.0, ['structure_facade'], seed=33,
                     note='Poly Haven medieval_wood (vertical riven planks with rows of iron stud nails), warmed to the dark brown of the original doors. Planks run along V', weaknesses='single scan; studs are part of the texture, not geometry')


@recipe
def TimberBeam():
    a = flatten(one('weathered_brown_planks', 1.8), 200, 0.5)
    grade(a, (150, 92, 48), hue=0.7, mean_luma=96, sat=0.95, contrast=1.05)
    return write_set('TimberBeam', a, 1.8, ['structure_facade', 'wood_floor'], seed=34,
                     note='Poly Haven weathered_brown_planks (broad sawn boards, grain along U), graded to the orange-brown of the original exterior timbers; beams map inside single boards', weaknesses='sawn, not hewn: adze marks come only from the beam geometry')
