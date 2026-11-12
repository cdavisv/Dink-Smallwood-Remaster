"""Procedural PBR texture synthesis for the Stonebrook fire-ruin kit (python3 + numpy + Pillow).

Deterministic: every random draw comes from numpy Generators seeded from ruin_common.SEED and the
texture name.  No downloaded images and no generative models.  Output: Textures/T_Ruin_*_{BC,N,ORM[,E]}.png

Conventions (match the existing Stonebrook kits): BC sRGB (alpha = opacity mask only for the
masked decal sets), N tangent-space OpenGL (+Y green; flip green in Unreal), ORM linear
(R occlusion, G roughness, B metallic).  Arrays are built V-up ([row 0] = V 0) and flipped on save.
"""
import sys, json, hashlib, time
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ruin_common as R

OUT = HERE.parent / 'Textures'
OUT.mkdir(parents=True, exist_ok=True)
F = np.float32
ONLY = set(sys.argv[1:])


def gen(name):
    return np.random.default_rng(int(hashlib.sha256(f'{R.SEED}:{name}'.encode()).hexdigest()[:12], 16))


# ----------------------------------------------------------------------------- noise primitives
def vnoise(h, w, fy, fx, g):
    """Tileable smooth value noise with fy x fx lattice cells over the image."""
    grid = g.random((fy, fx)).astype(F)
    qy = np.linspace(0, fy, h, endpoint=False, dtype=F); qx = np.linspace(0, fx, w, endpoint=False, dtype=F)
    iy = qy.astype(np.int32); ix = qx.astype(np.int32)
    ty = qy - iy; tx = qx - ix
    ty = ty * ty * (3 - 2 * ty); tx = tx * tx * (3 - 2 * tx)
    iy1 = (iy + 1) % fy; ix1 = (ix + 1) % fx
    a = grid[iy[:, None], ix[None, :]]; b = grid[iy[:, None], ix1[None, :]]
    c = grid[iy1[:, None], ix[None, :]]; d = grid[iy1[:, None], ix1[None, :]]
    top = a + (b - a) * tx[None, :]; bot = c + (d - c) * tx[None, :]
    return top + (bot - top) * ty[:, None]


def fbm(h, w, fy, fx, g, octaves=5, gain=.5):
    acc = np.zeros((h, w), F); amp = 1.0; tot = 0.0
    for o in range(octaves):
        acc += amp * vnoise(h, w, max(1, fy << o), max(1, fx << o), g); tot += amp; amp *= gain
    return acc / tot


def voronoi(h, w, cy, cx, g, jitter=.85):
    """Tileable Worley F1/F2 (in cell units, anisotropic cells allowed) + cell random value."""
    pts = g.random((cy, cx, 2)).astype(F) * jitter + (1 - jitter) / 2
    val = g.random((cy, cx)).astype(F)
    py = (np.arange(h, dtype=F) + .5) * cy / h; px = (np.arange(w, dtype=F) + .5) * cx / w
    gy = np.floor(py).astype(np.int32); gx = np.floor(px).astype(np.int32)
    fy = py - gy; fx = px - gx
    f1 = np.full((h, w), 9, F); f2 = np.full((h, w), 9, F); cid = np.zeros((h, w), F)
    for oy in (-1, 0, 1):
        ny = (gy + oy) % cy
        for ox in (-1, 0, 1):
            nx = (gx + ox) % cx
            p = pts[ny[:, None], nx[None, :]]
            ddy = (oy + p[..., 0]) - fy[:, None]; ddx = (ox + p[..., 1]) - fx[None, :]
            d = np.sqrt(ddy * ddy + ddx * ddx)
            v = val[ny[:, None], nx[None, :]]
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d)); cid = np.where(closer, v, cid); f1 = np.where(closer, d, f1)
    return f1, f2, cid


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2 and np.ndim(a) >= 1 and np.shape(a)[-1:] == (3,):
        t = t[..., None]
    return a + (b - a) * t


def col(c):
    return np.array(c, F)


def normal_from_height(hgt, strength, wrap=True):
    if wrap:
        dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * .5
        dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * .5
    else:
        dy, dx = np.gradient(hgt)
    n = np.dstack((-dx * strength, -dy * strength, np.ones_like(hgt)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * .5 + .5


def save(name, arr, mode='RGB'):
    a = np.clip(np.flipud(arr), 0, 1)
    img = Image.fromarray((a * 255 + .5).astype(np.uint8), mode)
    img.save(OUT / f'{name}.png', optimize=False, compress_level=6)


def save_set(name, bc, nrm, orm, emissive=None, alpha=None):
    if alpha is not None:
        save(f'T_{name}_BC', np.dstack((bc, alpha)), 'RGBA')
    else:
        save(f'T_{name}_BC', bc)
    save(f'T_{name}_N', nrm); save(f'T_{name}_ORM', orm)
    if emissive is not None:
        save(f'T_{name}_E', emissive)
    print(f'  wrote T_{name}_* {bc.shape[1]}x{bc.shape[0]}', flush=True)


# ----------------------------------------------------------------------------- material layers
def alligator(h, w, g, cell_v_px, cell_u_px, crack_px=2.2):
    """Alligatored char (checking) with grain along V: wandering longitudinal checks split the
    surface into strips; each strip is broken by wider, slightly tilted transverse cracks.
    Returns crack mask, block dome (0 at crack, 1 at block centre) and a per-block random value."""
    strip_w = []
    tot = 0.0
    while tot < w:
        s_ = float(g.uniform(.55, 1.45) * cell_u_px); strip_w.append(s_); tot += s_
    edges = np.cumsum([0.0] + strip_w) * (w / tot)
    vv = np.arange(h, dtype=F)
    wob = (vnoise(h, 1, max(2, h // 90), 1, g)[:, 0] - .5) * cell_u_px * .35
    crack = np.zeros((h, w), F); dome = np.zeros((h, w), F); cid = np.zeros((h, w), F)
    lw = crack_px * .7; tw = crack_px * 1.35
    jag_u = (vnoise(h, w, max(2, h // 6), max(2, w // 40), g) - .5) * crack_px * 1.6
    jag_v = (vnoise(h, w, max(2, h // 40), max(2, w // 5), g) - .5) * crack_px * 2.2
    bend = (vnoise(h, w, max(2, h // 300), max(2, w // 60), g) - .5) * cell_v_px * .5
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]
        c0, c1 = int(np.floor(a)), int(np.ceil(b))
        cols = np.arange(c0, c1)
        if len(cols) == 0:
            continue
        uu = cols.astype(F) + .5
        # longitudinal boundary distance (boundaries wobble along V)
        ju = jag_u[:, c0:min(c1, w)]; jv = jag_v[:, c0:min(c1, w)]; bv = bend[:, c0:min(c1, w)]
        if ju.shape[1] < len(cols):
            pad = len(cols) - ju.shape[1]
            ju = np.pad(ju, ((0, 0), (0, pad)), mode='edge'); jv = np.pad(jv, ((0, 0), (0, pad)), mode='edge'); bv = np.pad(bv, ((0, 0), (0, pad)), mode='edge')
        dl = np.minimum(np.abs(uu[None, :] + ju - (a + wob[:, None])), np.abs(uu[None, :] + ju - (b + wob[:, None])))
        # transverse cracks for this strip
        pos = []; t = float(g.uniform(0, cell_v_px))
        while t < h:
            pos.append(t); t += float(g.uniform(.45, 1.7) * cell_v_px)
        pos = np.array(pos, F); tilt = g.uniform(-.25, .25, len(pos)).astype(F)
        rid = g.random(len(pos) + 1).astype(F)
        centre = (a + b) * .5
        # effective crack row per column: pos + tilt * (u - centre)
        vrow = vv[:, None] + jv + bv
        k = np.searchsorted(pos, vrow - 0 * uu[None, :]).clip(1, len(pos) - 1)
        p0 = pos[k - 1] + tilt[k - 1] * (uu[None, :] - centre); p1 = pos[k] + tilt[k] * (uu[None, :] - centre)
        dt = np.minimum(np.abs(vrow - p0), np.abs(vrow - p1))
        # wrap distance across the tile seam
        dt = np.minimum(dt, np.minimum(np.abs(vrow - pos[0] + h), np.abs(vrow - pos[-1] - h)))
        lwid = lw * (.6 + .8 * rid[k][..., None] if False else 1.0)
        merge = (rid[k] > .78).astype(F)                         # some longitudinal checks stop short
        cl = (1 - sstep(lw * .3, lw * (.6 + .8 * rid[k]), dl)) * (1 - merge)
        ct = 1 - sstep(tw * .3, tw * (.6 + .9 * rid[k]), dt)
        sl = (slice(None), slice(c0, min(c1, w)))
        nc = min(c1, w) - c0
        crack[sl] = np.maximum(cl, ct)[:, :nc]
        dd = np.minimum(np.where(merge > 0, 9, dl / ((b - a) * .5)), dt / (cell_v_px * .5))
        dome[sl] = np.sqrt(np.clip(dd, 0, 1))[:, :nc]
        cid[sl] = (rid[k] * .6 + .4 * ((i * 0.618) % 1))[:, :nc]
    return crack.astype(F), dome.astype(F), cid.astype(F)


def oak_grain(h, w, g, tile_v_m, tile_u_m, ring_mm=5.5):
    """Oak grain running along V: wavy ring lines, medullary flecks, pores."""
    yy = (np.arange(h, dtype=F)[:, None] / h); xx = (np.arange(w, dtype=F)[None, :] / w)
    warp = (fbm(h, w, 2, 2, g, 4) - .5) * .12 + (fbm(h, w, 8, 3, g, 3) - .5) * .02
    rings = tile_u_m * 1000 / ring_mm
    phase = (xx + warp) * rings
    grain = .5 + .5 * np.sin(phase * 2 * np.pi)
    grain = grain ** 2 * (.6 + .4 * fbm(h, w, 4, 12, g, 3))
    pores = (vnoise(h, w, int(h / 6), int(w / 2.2), g) > .82).astype(F) * vnoise(h, w, 32, 64, g)
    fleck = sstep(.78, .95, vnoise(h, w, int(tile_v_m * 60), int(tile_u_m * 300), g)) * .5
    return grain.astype(F), pores.astype(F), fleck.astype(F)


# ----------------------------------------------------------------------------- texture sets
def tex_timber():
    """2048^2: U [0,.5) deep alligator char, U [.5,1) scorched oak with char patches. 1 tile = 2 m along V."""
    g = gen('timber'); n = 2048; hw = 1024
    h = n
    # ---- char half
    crack, dome, cid = alligator(h, hw, g, 30, 17, 2.6)
    long = fbm(h, hw, 64, 6, g, 3)                      # long fibrous streaks along the grain
    grain, pores, fleck = oak_grain(h, hw, g, 2.0, 1.0)
    fine = vnoise(h, hw, 700, 350, g)
    fib = vnoise(h, hw, 300, 400, g)
    hgt_c = .8 * dome * (1 - crack) + .1 * long + .12 * fib + .05 * fine - 1.1 * crack
    sheen = sstep(.45, .9, fbm(h, hw, 10, 6, g, 4)) * dome * (1 - crack)
    ash = sstep(.7, .85, fbm(h, hw, 24, 12, g, 3)) * crack * .5
    ember = sstep(.7, .9, fbm(h, hw, 12, 8, g, 3)) * crack     # pyrolysed brown under cracks
    base = lerp(col((.040, .037, .035)), col((.11, .105, .10)), np.clip(cid * .8 + .2 * long, 0, 1) * (.75 + .25 * dome))
    base = base * (.85 + .3 * fib[..., None])
    bc_c = lerp(base, col((.20, .20, .205)), sheen * .55)
    bc_c = lerp(bc_c, col((.016, .014, .013)), crack * .85)
    bc_c = lerp(bc_c, col((.20, .10, .045)), ember * .6)
    bc_c = lerp(bc_c, col((.52, .51, .49)), ash * .7)
    rough_c = np.clip(.88 - .30 * sheen + .1 * crack, .45, 1)
    ao_c = np.clip(1 - .65 * crack - .1 * (1 - dome), .2, 1)
    # ---- scorched half
    g2 = gen('timber-scorch')
    grain2, pores2, fleck2 = oak_grain(h, hw, g2, 2.0, 1.0)
    broad = fbm(h, hw, 4, 3, g2, 5)
    scorch = sstep(.30, .75, fbm(h, hw, 3, 8, g2, 5))            # blackening amount (streaky along grain)
    crack2, dome2, cid2 = alligator(h, hw, g2, 34, 20, 2.4)
    patch = sstep(.585, .60, fbm(h, hw, 3, 9, g2, 5) + (cid2 - .5) * .10)   # boundaries follow the blocks
    oak = lerp(col((.20, .125, .065)), col((.38, .26, .15)), .55 * broad + .45 * grain2)
    oak = lerp(oak, col((.12, .075, .04)), pores2 * .6)
    oak = lerp(oak, col((.43, .31, .19)), fleck2 * .4)
    streak = sstep(.4, .9, fbm(h, hw, 48, 5, g2, 3))             # soot streaks following grain
    bc_s = lerp(oak, col((.075, .055, .04)), np.clip(scorch * .85 + streak * .35 * scorch, 0, 1))
    charc = lerp(col((.06, .055, .05)), col((.12, .115, .11)), cid2)
    charc = lerp(charc, col((.015, .013, .012)), crack2)
    bc_s = lerp(bc_s, charc, patch)
    hgt_s = (.12 * grain2 - .25 * pores2 + .1 * broad) * (1 - patch) + patch * (.5 * dome2 * (1 - crack2) - .8 * crack2) + .04 * fine
    rough_s = np.clip(.72 + .15 * scorch - .1 * patch * dome2 + .1 * patch * crack2, .4, 1)
    ao_s = np.clip(1 - .55 * crack2 * patch - .25 * pores2, .2, 1)
    bc = np.concatenate([bc_c, bc_s], 1); hgt = np.concatenate([hgt_c, hgt_s], 1)
    orm = np.dstack((np.concatenate([ao_c, ao_s], 1), np.concatenate([rough_c, rough_s], 1), np.zeros((n, n), F)))
    save_set('Ruin_Timber', bc, normal_from_height(hgt, 6.0), orm)


def strands(h, w, g, per_px_u, len_px_v):
    """Long straw/reed strands along V: per-strand tone and occasional breaks/ends."""
    fx = max(4, int(w / per_px_u))
    tone = vnoise(h, w, max(2, int(h / len_px_v)), fx, g)
    tone2 = vnoise(h, w, max(2, int(h / (len_px_v * .6))), int(fx * 1.7), g)
    ridge = np.abs(np.sin((np.arange(w, dtype=F)[None, :] / per_px_u + (fbm(h, w, 6, 3, g, 3) - .5) * 3) * np.pi))
    ridge = np.broadcast_to(ridge, (h, w)) * (.6 + .4 * tone2)
    ends = sstep(.86, .93, vnoise(h, w, int(h / (len_px_v * .45)), fx, g))
    return tone.astype(F), ridge.astype(F), ends.astype(F)


def tex_thatch():
    """2048^2: U [0,.5) weathered/smoke-stained thatch, U [.5,1) charred thatch. 1 tile = 1 m along V."""
    g = gen('thatch'); n = 2048; hw = 1024
    tone, ridge, ends = strands(n, hw, g, 4.6, 420)
    tone_b, ridge_b, ends_b = strands(n, hw, g, 7.5, 600)
    layer = np.maximum(ridge * (.6 + .4 * tone), ridge_b * .8)
    soot = sstep(.45, .85, fbm(n, hw, 6, 4, g, 5))
    weather = fbm(n, hw, 3, 3, g, 5)
    straw = lerp(col((.22, .17, .095)), col((.44, .36, .21)), np.clip(.75 * tone + .25 * weather, 0, 1))
    straw = lerp(straw, col((.30, .29, .26)), .35 * sstep(.4, .8, weather))      # silvered old reed
    bc_i = lerp(straw, col((.055, .045, .035)), soot * .3 + ends * .45 + .12)
    bc_i = bc_i * (.55 + .45 * layer[..., None])
    hgt_i = .6 * layer + .25 * tone - .5 * ends
    rough_i = np.clip(.86 + .08 * soot, 0, 1); ao_i = np.clip(.45 + .55 * layer, 0, 1)
    # charred half
    g2 = gen('thatch-char')
    tone2, ridge2, ends2 = strands(n, hw, g2, 4.2, 260)
    gaps = sstep(.55, .75, vnoise(n, hw, 40, 120, g2))                           # burnt-away strands
    ashc = sstep(.55, .78, fbm(n, hw, 20, 10, g2, 4)) * ridge2
    glow = sstep(.72, .9, fbm(n, hw, 10, 8, g2, 3))
    bc_c = lerp(col((.030, .027, .025)), col((.085, .078, .072)), tone2)
    bc_c = lerp(bc_c, col((.18, .09, .04)), glow * (1 - ridge2) * .5)
    bc_c = lerp(bc_c, col((.50, .49, .47)), ashc * .6)
    bc_c = bc_c * (.6 + .4 * ridge2[..., None]) * (1 - .6 * gaps[..., None])
    hgt_c = .55 * ridge2 * (1 - gaps) - .4 * ends2 + .15 * tone2
    rough_c = np.clip(.8 - .15 * ridge2 * (1 - ashc) + .1 * ashc, 0, 1); ao_c = np.clip(.35 + .65 * ridge2 * (1 - gaps), 0, 1)
    bc = np.concatenate([bc_i, bc_c], 1); hgt = np.concatenate([hgt_i, hgt_c], 1)
    orm = np.dstack((np.concatenate([ao_i, ao_c], 1), np.concatenate([rough_i, rough_c], 1), np.zeros((n, n), F)))
    save_set('Ruin_Thatch', bc, normal_from_height(hgt, 5.0), orm)


def tex_ash():
    """2048^2 tiling ash/charcoal/ember ground, 1 tile = 2 m. E = ember glow mask (burning state)."""
    g = gen('ash'); n = 2048
    f_big = fbm(n, n, 4, 4, g, 6); f_mid = fbm(n, n, 24, 24, g, 4); fine = vnoise(n, n, 600, 600, g)
    f1, f2, cid = voronoi(n, n, 70, 70, g, .95)                   # charcoal lumps ~3 cm
    clump = sstep(.35, .75, fbm(n, n, 5, 5, g, 4))
    lump = (cid > .9 - .35 * clump).astype(F) * sstep(.0, .35, f2 - f1)
    f1c, f2c, cidc2 = voronoi(n, n, 22, 22, g, .95)              # a few bigger embers/charcoal pieces ~9 cm
    lump = np.maximum(lump, (cidc2 > .86).astype(F) * sstep(0, .3, f2c - f1c) * clump)
    f1b, f2b, cidb = voronoi(n, n, 260, 260, g, .95)              # grit / flakes ~0.8 cm
    grit = (cidb > .93 - .12 * clump).astype(F) * sstep(0, .3, f2b - f1b)
    flakes = (cidb < .07).astype(F)
    crk, dome, cidc = alligator(n, n, g, 12, 9, 1.5)
    ash_tone = lerp(col((.13, .125, .12)), col((.42, .41, .40)), np.clip(.55 * f_big + .45 * f_mid, 0, 1))
    ash_tone = lerp(ash_tone, col((.36, .33, .30)), sstep(.6, .85, fbm(n, n, 8, 8, g, 4)) * .5)  # brownish wood ash
    bc = lerp(ash_tone, col((.035, .032, .03)), np.clip(lump * (1 - .5 * crk) + grit * .8, 0, 1))
    bc = lerp(bc, col((.015, .013, .012)), lump * crk)
    bc = lerp(bc, col((.70, .69, .67)), flakes * .35)
    hgt = .6 * f_big + .35 * f_mid + .5 * lump * dome - .3 * lump * crk + .25 * grit + .08 * fine
    rough = np.clip(.95 - .3 * lump * dome * (1 - crk), .5, 1)
    ao = np.clip(.55 + .45 * sstep(.2, .8, f_mid) - .3 * lump * crk, .2, 1)
    emb = sstep(.66, .82, fbm(n, n, 10, 10, g, 4)) * (lump * crk + .35 * (1 - sstep(.0, .25, f2 - f1)) * (cid > .72))
    emb = np.clip(emb, 0, 1)
    e = np.dstack((emb, emb ** 1.6 * .45, emb ** 3 * .08))
    bc = lerp(bc, col((.30, .12, .04)), emb * .5)
    save_set('Ruin_AshEmber', bc, normal_from_height(hgt, 9.0), np.dstack((ao, rough, np.zeros_like(ao))), emissive=e)


# ----------------------------------------------------------------------------- facades
def stone_field(h, w, g, rects, x_of_u, z_of_v):
    """Per-stone tint/edge masks for stones given as (cx, cz, width, height) in metres."""
    Xs = x_of_u(np.arange(w, dtype=F)); Zs = z_of_v(np.arange(h, dtype=F))
    tint = np.zeros((h, w), F); edge = np.ones((h, w), F); inside = np.zeros((h, w), F)
    pal = g.random((len(rects), 3)).astype(F)
    for i, (cx, cz, wd, ht) in enumerate(rects):
        c0, c1 = np.searchsorted(Xs, cx - wd / 2), np.searchsorted(Xs, cx + wd / 2)
        r0, r1 = np.searchsorted(Zs, cz - ht / 2), np.searchsorted(Zs, cz + ht / 2)
        if c1 <= c0 or r1 <= r0:
            continue
        dx = (wd / 2 - np.abs(Xs[c0:c1] - cx))[None, :]; dz = (ht / 2 - np.abs(Zs[r0:r1] - cz))[:, None]
        d = np.minimum(dx, dz)
        inside[r0:r1, c0:c1] = 1; tint[r0:r1, c0:c1] = pal[i, 0]
        edge[r0:r1, c0:c1] = np.clip(d / .035, 0, 1)
    return tint, edge, inside


def facade_texture(name, n, facades, gable=False, level='burnt'):
    """facades: list of dicts with u0,u1,v0,v1 (UV rect), h0,h1 (horizontal metres), z1 (top metres),
    stones, openings, active, marks.  UV: U = horizontal metres, V = height metres (0..z1).
    level 'burnt' = vision 2 (full soot, calcination, spalls); 'burning' = vision 1 (fire just broke
    through the roof: limewash still mostly clean, soot only above the openings that vent fire)."""
    burnt = level == 'burnt'
    g = gen(name)
    bc = np.zeros((n, n, 3), F); hgt = np.zeros((n, n), F); rough = np.zeros((n, n), F); ao = np.ones((n, n), F)
    big = fbm(n, n, 6, 6, g, 6); mid = fbm(n, n, 40, 40, g, 4); fine = vnoise(n, n, 900, 900, g)
    streakv = fbm(n, n, 3, 160, g, 3)                     # vertical drips (low V freq, high U freq)
    f1, f2, cid = voronoi(n, n, 160, 160, g, .9)
    hair = 1 - sstep(.0, .04, f2 - f1)                    # hairline crazing network
    for fc in facades:
        r0 = int(fc['v0'] * n); r1 = int(fc['v1'] * n); c0 = int(fc['u0'] * n); c1 = int(fc['u1'] * n)
        hh, ww = r1 - r0, c1 - c0
        hm0, hm1, z1 = fc['h0'], fc['h1'], fc['z1']
        X = (hm0 + (np.arange(ww, dtype=F) + .5) / ww * (hm1 - hm0))[None, :]
        Z = ((np.arange(hh, dtype=F) + .5) / hh * z1)[:, None]
        sl = (slice(r0, r1), slice(c0, c1))
        B, M, FI, SV, HAIR, CID = big[sl], mid[sl], fine[sl], streakv[sl], hair[sl], cid[sl]
        rects = [(c, z, w, h) for (c, z, w, h, *_r) in fc['stones']]
        tint, sedge, sin_ = stone_field(hh, ww, g, rects, lambda u: hm0 + (u + .5) / ww * (hm1 - hm0), lambda v: (v + .5) / hh * z1)
        stone_zone = np.broadcast_to(Z < fc.get('stone_top', 1.27), (hh, ww)) | (sin_ > 0)
        is_stone = (sin_ > 0)
        mortar = stone_zone & ~is_stone
        # --- fieldstone (per-stone tint, mottling, pits, darker arrises)
        warm = col((.47, .42, .35)); cool = col((.36, .36, .35)); dark = col((.27, .26, .24))
        mott = fbm(hh, ww, 30, 60, g, 5)
        pits = sstep(.8, .9, vnoise(hh, ww, hh // 6, ww // 6, g))
        st = lerp(cool, warm, tint); st = lerp(st, dark, sstep(.5, .9, B) * .5)
        st = st * (.62 + .7 * mott[..., None]) * (.85 + .2 * FI[..., None]) * (1 - .35 * pits[..., None])
        st = lerp(st, col((.52, .50, .45)), sstep(.62, .8, mott) * .35)
        st = lerp(st, col((.20, .19, .18)), (1 - sedge) * .55)
        st_h = .3 * B + .45 * mott + .15 * FI + .7 * sedge - .3 * pits
        # --- lime mortar: weathered, partly washed out (mortar loss = deep dark joints)
        loss = sstep(.55, .7, fbm(hh, ww, 8, 24, g, 4))
        mor = lerp(col((.50, .47, .41)), col((.60, .57, .50)), FI) * (.8 + .3 * M[..., None])
        mor = lerp(mor, col((.10, .09, .08)), loss * .85)
        mor_h = -.6 - .5 * loss + .1 * FI
        # --- calcined / spalled stone near the hottest openings (burnt only)
        calc = np.zeros((hh, ww), F)
        if burnt:
            for (oc, hw, ob, ot) in fc['openings']:
                calc = np.maximum(calc, np.exp(-((X - oc) / (hw + .9)) ** 2) * sstep(-0.2, .5, Z - ob + .4) * (1 - sstep(1.0, 1.4, Z)))
            calc = np.clip(calc * (.6 + .8 * B) - .25, 0, 1) * is_stone
            calc = np.clip(calc + sstep(.74, .82, fbm(hh, ww, 6, 18, g, 4)) * .8 * is_stone, 0, 1)
        stone_pick = sstep(.45, .55, tint) * (.6 + .4 * B)        # whole stones calcine, not blobs
        calc = np.clip(calc * (.4 + 1.2 * stone_pick), 0, 1)
        spall = sstep(.55, .62, fbm(hh, ww, 14, 40, g, 4)) * calc
        cst = lerp(col((.66, .63, .58)), col((.64, .54, .49)), sstep(.3, .8, tint)) * (.85 + .3 * mott[..., None])
        st = lerp(st, cst, calc * .8)
        st = lerp(st, col((.30, .28, .27)), HAIR[..., None] * calc[..., None] * .35)
        st = lerp(st, col((.76, .73, .68)), spall * .7)
        st_h = st_h - .25 * HAIR * calc + .45 * spall
        # --- limewash over daub (a burnt house's limewash is smoke-filmed throughout)
        lime = lerp(col((.70, .68, .62)), col((.83, .81, .75)), .6 * M + .4 * FI)
        lime = lerp(lime, col((.62, .58, .50)), sstep(.55, .85, B) * .35)
        if burnt:
            lime = lime * col((.70, .66, .58))
        trowel = fbm(hh, ww, 10, 30, g, 4)
        lime_h = .25 * trowel + .1 * FI - .25 * HAIR * sstep(.4, .7, B)
        spalled = sstep(.77, .80, fbm(hh, ww, 4, 10, g, 5)) * (~stone_zone) * (1.0 if burnt else 0.0)
        daub = lerp(col((.40, .36, .30)), col((.50, .45, .38)), FI)
        lime = lerp(lime, daub, spalled); lime_h = lime_h - .6 * spalled
        base = np.where(is_stone[..., None], st, np.where(mortar[..., None], mor, lime))
        h_ = np.where(is_stone, st_h, np.where(mortar, mor_h, lime_h))
        # --- soot
        if burnt:
            # general smoke deposition; holds up below 2 m, plus a grime band at the foot of the wall
            soot = (.42 * sstep(.25, 1.5, Z) + .38 * sstep(1.4, 3.0, Z)) * (.45 + .9 * B) * (.75 + .5 * M)
            soot = soot + .35 * (1 - sstep(.05, .55, Z)) * (.6 + .6 * M)
            tongue = 3.4 - (.4 + 1.1 * fbm(hh, ww, 2, 9, g, 5)) * (.6 + .6 * B)
            soot = soot + .85 * sstep(-.15, .7, Z - tongue) * (.7 + .45 * M) * (Z < 3.62)
            vents = fc['openings']
        else:
            soot = .05 * sstep(1.6, 3.4, Z) * B
            # eaves only blacken under the burning sections of the roof
            for fxp in fc.get('fires', []):
                near = np.exp(-((X - fxp) / 1.6) ** 2)
                tongue = 3.45 - (.2 + .6 * fbm(hh, ww, 2, 9, g, 5)) * near
                soot = soot + .8 * near * sstep(-.1, .5, Z - tongue) * (Z < 3.62)
            vents = fc.get('active', [])
        for (oc, hw, ob, ot) in vents:
            dz = Z - ot
            wob = (B - .5) * .5 * np.clip(dz, 0, 3) + .12 * np.sin(Z * 2.3 + oc)
            wid = hw * 1.35 + (1.0 if burnt else .6) * np.clip(dz + .3, 0, 4)
            plume = np.exp(-np.abs((X - oc - wob) / wid) ** 2.2 * 1.1) * np.exp(-np.clip(dz, 0, 9) / (4.0 if burnt else 2.0)) * sstep(-.9, -.1, dz)
            jamb = np.exp(-((np.abs(X - oc) - hw) / .12) ** 2) * sstep(ot - .6, ot, Z) * .3
            head = sstep(ot - .05, ot + .08, Z) * (np.abs(X - oc) < hw + .12)
            soot = soot + plume * ((1.25 if burnt else .95) + .35 * M) + jamb * (.6 + .6 * B) + head * .9
            if burnt:
                # rain-washed soot streaks running down from the sill onto the stone
                below = np.clip(ob - Z, 0, 2)
                streak = sstep(.55, .8, fbm(hh, ww, 2, 260, g, 3)) * (np.abs(X - oc) < hw + .25) * np.exp(-below / .7) * (Z < ob)
                soot = soot + streak * .8
        if fc.get('chimney'):
            soot = soot + sstep(6.2, 7.9, Z) * (np.abs(X + 5.4) < .75) * (.8 + .4 * B)
        if gable:
            roofline = 3.5 + 3.5 * np.clip(1 - np.abs(X - fc['hc']) / 4.5, 0, 1)
            below = roofline - Z
            soot = soot + (.95 if burnt else .35) * np.exp(-np.clip(below, 0, 9) / .9) * (Z > 3.45) * (.7 + .5 * B)
            soot = np.where((Z > 3.5) & (below < 0), 1.0, soot)
        for (mx, mz, mr) in (fc['marks'] if burnt else []):
            d = np.sqrt((X - mx) ** 2 + ((Z - mz) * 1.15) ** 2) / mr
            core = 1 - sstep(.35, .8, d + (B - .5) * .5)
            soot = soot + (1 - sstep(.6, 1.6, d + (M - .5) * .6)) + np.exp(-((X - mx) / (mr * 1.3)) ** 2) * sstep(mz, mz + .3, Z) * np.exp(-(Z - mz) / 1.8) * .8
            base = lerp(base, col((.022, .018, .016)), core * .9)
            h_ = h_ - core * .5
        soot = np.clip(soot * (.92 + .16 * SV) + .08 * (SV - .5) * sstep(2.0, 3.2, Z), 0, 1)
        soot = soot * (1 - np.clip(calc * .6, 0, 1))                 # heat burned the soot off
        tar = sstep(.08, .35, soot) * (1 - sstep(.35, .7, soot))      # brown tar fringe around plumes
        out = lerp(base, col((.33, .25, .15)), tar * .45 * (~stone_zone))
        out = lerp(out, col((.028, .025, .023)), soot ** .8 * .97)
        bc[sl] = out; hgt[sl] = h_
        rough[sl] = np.clip(np.where(stone_zone, .84, .9) + .08 * soot + .06 * calc - .05 * M - .1 * spall, 0, 1)
        ao[sl] = np.clip(np.where(is_stone, .55 + .45 * sedge, np.where(mortar, .45 - .25 * loss, 1.0)) - .25 * spalled - .2 * HAIR * calc, .15, 1)
    save_set(name, bc, normal_from_height(hgt, 7.0), np.dstack((ao, rough, np.zeros_like(ao))))


# active (fire-venting) openings in the burning state, and burning roof spots, per facade
BURNING_ACTIVE = {'front': [R.DOOR_X, 1.5, 7.5], 'back': [-3.0]}


def tex_facades():
    RL = R.rubble_layout()
    marks = {'wall_front': [], 'wall_back': [], 'wall_west': [], 'wall_east': []}
    for surf, x, y, z, r in R.wall_burns():
        marks[surf].append((x if surf in ('wall_front', 'wall_back') else y, z, r))
    fires_x = [e['cottage_m'][0] for e in R.exterior_effects() if e['vision'] == 1 and e['surface'].startswith('roof')]
    chim = [(-5.8 + c * .38, 4.55 + k * .27, .36, .25) for k in range(12) for c in range(3)]
    for level, suffix in [('burnt', ''), ('burning', '_Burning')]:
        fb = []
        for key, v0 in [('front', .5), ('back', 0.0)]:
            ops = R.openings(key)
            fb.append({'u0': 0, 'u1': 1, 'v0': v0, 'v1': v0 + .5, 'h0': -9.6, 'h1': 9.6, 'z1': 8.0,
                       'stones': list(RL[key]), 'openings': ops, 'marks': marks['wall_' + key],
                       'active': [o for o in ops if any(abs(o[0] - a) < .01 for a in BURNING_ACTIVE.get(key, []))],
                       'fires': fires_x if key == 'front' else [x for x in fires_x if abs(x) < 4]})
        fb[1]['stones'] += chim
        fb[1]['stone_top'] = 1.27; fb[1]['chimney'] = True
        facade_texture('Ruin_FacadeFrontBack' + suffix, 4096, fb, level=level)
        sides = []
        for key, u0 in [('west', 0.0), ('east', .5)]:
            sides.append({'u0': u0, 'u1': u0 + .5, 'v0': 0, 'v1': 1, 'h0': -4.8, 'h1': 4.8, 'z1': 8.0, 'hc': 0.0,
                          'stones': list(RL[key]), 'openings': [], 'marks': marks['wall_' + key], 'active': [],
                          'fires': [0.0] if (key == 'west' and min(fires_x) < -8) else []})
        facade_texture('Ruin_FacadeSides' + suffix, 4096, sides, gable=True, level=level)


# ----------------------------------------------------------------------------- interior sets
def tex_interior_plaster():
    """2048^2: U = x/2 m (tiles horizontally across modules), V = z/3.5 m (absolute height)."""
    g = gen('int-plaster'); n = 2048
    Z = ((np.arange(n, dtype=F) + .5) / n * 3.5)[:, None]
    big = fbm(n, n, 4, 4, g, 6); mid = fbm(n, n, 24, 24, g, 4); fine = vnoise(n, n, 700, 700, g)
    drip = fbm(n, n, 2, 90, g, 3)
    lime = lerp(col((.72, .69, .62)), col((.84, .82, .76)), .6 * mid + .4 * fine)
    smokey = lerp(lime, col((.62, .55, .42)), .55)             # nicotine-yellow smoke film below the layer
    tide = 1.30 + .18 * (fbm(n, n, 2, 6, g, 3) - .5) + .05 * np.sin(np.arange(n, dtype=F)[None, :] / n * 2 * np.pi * 3)
    upper = sstep(-0.12, .22, Z - tide + (fbm(n, n, 6, 12, g, 4) - .5) * .25)                         # hot smoke layer interface line
    soot = upper * np.clip(.55 + .45 * sstep(1.3, 3.3, Z) + .25 * (big - .5), 0, 1)
    soot = np.clip(soot + (1 - upper) * .12 * sstep(.2, 1.3, Z) * big + .08 * (drip - .5) * upper, 0, 1)
    spalled = sstep(.78, .81, fbm(n, n, 3, 3, g, 5)) * sstep(1.2, 2.2, Z)
    daub = lerp(col((.22, .16, .11)), col((.33, .25, .17)), fine)
    base = lerp(smokey, daub, spalled)
    bc = lerp(base, col((.03, .027, .025)), soot ** .85 * .96)
    f1, f2, cid = voronoi(n, n, 90, 90, g, .9)
    hair = 1 - sstep(0, .035, f2 - f1)
    hgt = .25 * mid + .1 * fine - .35 * hair * upper - .6 * spalled
    bc = lerp(bc, col((.02, .02, .02)), hair * upper * .5)
    rough = np.clip(.9 + .07 * soot, 0, 1); ao = np.clip(1 - .3 * spalled - .2 * hair, 0, 1)
    save_set('RuinInt_PlasterSoot', bc, normal_from_height(hgt, 6.0), np.dstack((ao, rough, np.zeros_like(ao))))


def tex_interior_floor():
    """2048^2 covers 4 m x 4 m (512 px/m): 16 boards 0.25 m wide along V, ash film, char patches."""
    g = gen('int-floor'); n = 2048
    U = (np.arange(n, dtype=F) + .5) / n * 4.0; V = (np.arange(n, dtype=F) + .5) / n * 4.0
    board = np.floor(U / .25).astype(np.int32)
    seg = np.floor((V[:, None] + (board[None, :] % 2) * 1.0) / 2.0).astype(np.int32)
    bid = (board[None, :] * 7 + seg * 13) % 97
    btone = (np.sin(bid * 12.9898) * 43758.5453) % 1.0
    grain, pores, fleck = oak_grain(n, n, g, 4.0, 4.0, 2.4)
    big = fbm(n, n, 4, 4, g, 6); mid = fbm(n, n, 30, 30, g, 4)
    oak = lerp(col((.17, .105, .055)), col((.34, .23, .13)), np.clip(.5 * btone + .3 * grain + .2 * big, 0, 1).astype(F))
    oak = lerp(oak, col((.10, .06, .03)), pores * .5)
    edgeu = np.abs(((U / .25) % 1.0) - .5) * 2
    gap = sstep(.93, .99, edgeu)[None, :] * np.ones((n, 1), F)
    scorch = sstep(.45, .8, fbm(n, n, 5, 5, g, 5))
    crk, dome, cidc = alligator(n, n, g, 22, 14, 2.0)
    charm = sstep(.64, .70, fbm(n, n, 6, 6, g, 5))
    ash = sstep(.35, .75, fbm(n, n, 7, 7, g, 5)) * .75 + gap * .5
    bc = lerp(oak, col((.06, .045, .035)), scorch * .8)
    charc = lerp(col((.05, .046, .043)), col((.11, .105, .10)), cidc); charc = lerp(charc, col((.015, .013, .012)), crk)
    bc = lerp(bc, charc, charm)
    bc = lerp(bc, lerp(col((.33, .32, .30)), col((.55, .54, .52)), mid), np.clip(ash * (.5 + .5 * mid), 0, 1) * .8)
    hgt = (.15 * grain - .25 * pores) * (1 - charm) + charm * (.5 * dome * (1 - crk) - .8 * crk) - 1.2 * gap + .2 * ash * mid
    rough = np.clip(.75 + .2 * ash + .1 * scorch - .12 * charm * dome, .4, 1)
    ao = np.clip(1 - .7 * gap - .5 * crk * charm, .15, 1)
    save_set('RuinInt_FloorAsh', bc, normal_from_height(hgt, 5.0), np.dstack((ao, rough, np.zeros_like(ao))))


def radial_decal(name, n, kind):
    """Masked decal sets (alpha = opacity mask, dithered irregular edge)."""
    g = gen(name)
    yy, xx = np.mgrid[0:n, 0:n].astype(F); yy = (yy + .5) / n; xx = (xx + .5) / n
    big = fbm(n, n, 4, 4, g, 6); mid = fbm(n, n, 20, 20, g, 5); fine = vnoise(n, n, 500, 500, g)
    if kind == 'wall':        # burn centre at lower third, soot fan rising and widening
        cx, cy = .5, .3
        dx = (xx - cx) / (.14 + .55 * np.clip(yy - cy, 0, 1)); dy = (yy - cy) / .22
        d = np.sqrt(dx * dx + np.where(dy < 0, dy * 1.8, dy * .38) ** 2)
    else:
        d = np.sqrt((xx - .5) ** 2 + (yy - .5) ** 2) / .5
    d = d + (big - .5) * .7 + (mid - .5) * .2
    core = 1 - sstep(.18, .42, d); ring = 1 - sstep(.4, .82, d)
    alpha = (ring + (fine - .5) * .35 + (mid - .5) * .3 > .35).astype(F)
    alpha *= (1 - sstep(.9, .98, np.maximum(np.abs(xx - .5), np.abs(yy - .5)) * 2))  # never reach the border
    crk, dome, cidc = alligator(n, n, g, 18 * n / 1024, 12 * n / 1024, 2.0)
    charc = lerp(col((.045, .042, .04)), col((.10, .095, .09)), cidc); charc = lerp(charc, col((.012, .011, .01)), crk)
    if kind == 'ground':
        stub_t, stub, stub_e = strands(n, n, g, 2.6, 30)
        d2 = d + (stub - .5) * .12
        core = 1 - sstep(.15, .5, d2); ring = 1 - sstep(.45, .95, d2)
        singe = lerp(col((.20, .15, .07)), col((.40, .31, .14)), stub_t)               # singed straw-coloured grass
        black = lerp(col((.035, .03, .025)), col((.08, .06, .04)), stub_t)            # blackened stubble
        bc = lerp(singe, black, sstep(.35, .8, ring + .35 * (stub - .5)))
        bc = bc * (.7 + .6 * stub[..., None])
        ashc = sstep(.42, .7, fbm(n, n, 9, 9, g, 5)) * core
        bc = lerp(bc, charc, core * .6)
        bc = lerp(bc, lerp(col((.22, .21, .20)), col((.48, .47, .45)), fine), ashc * .85)
        alpha = ((ring * .95 + (stub - .5) * .5 + (mid - .5) * .6 + (fine - .5) * .2) > .5).astype(F)
        alpha *= (1 - sstep(.9, .98, np.maximum(np.abs(xx - .5), np.abs(yy - .5)) * 2))
        hgt = .5 * stub * (1 - core) + .5 * dome * core * (1 - crk) - .4 * crk * core + .3 * ashc * mid
    elif kind == 'floor':
        bc = lerp(col((.07, .05, .035)), col((.03, .025, .02)), ring)
        bc = lerp(bc, charc, core)
        ashc = sstep(.5, .78, fbm(n, n, 12, 12, g, 4)) * ring
        bc = lerp(bc, col((.45, .44, .42)), ashc * .55)
        hgt = core * (.6 * dome * (1 - crk) - crk) + .2 * ashc + .1 * fine
    else:                     # wall: burnt-through plaster exposing charred lath, soot plume
        lath = (np.sin(yy * n / 22 * np.pi) > .1).astype(F)
        bc = lerp(col((.30, .26, .21)), col((.03, .027, .024)), np.clip(ring * 1.3, 0, 1) ** 1.5)
        bc = lerp(bc, lerp(col((.015, .013, .012)), charc, lath), core)
        alpha = ((ring * 1.1 + (mid - .5) * .5 + (fine - .5) * .3 - .25 * np.clip(yy - .3, 0, 1)) > .42).astype(F)
        alpha *= (1 - sstep(.9, .98, np.maximum(np.abs(xx - .5), np.abs(yy - .5)) * 2))
        hgt = core * (lath * .5 - .6) + .15 * fine * ring
    rough = np.clip(.88 + .1 * ring - .2 * core * dome, .4, 1).astype(F)
    ao = np.clip(1 - .5 * crk * core, .2, 1).astype(F)
    save_set(name, bc, normal_from_height(hgt, 6.0), np.dstack((ao, rough, np.zeros_like(ao))), alpha=alpha)


def ground_patch(n, g, seed, wind):
    """One feathered burn patch (masked) on meadow: charred core in patches, ash drifts streaked
    downwind, blackened stubble, singed straw-coloured grass fading into the living meadow."""
    yy, xx = np.mgrid[0:n, 0:n].astype(F); yy = (yy + .5) / n - .5; xx = (xx + .5) / n - .5
    ca, sa = np.cos(wind), np.sin(wind)
    u = xx * ca + yy * sa; v = -xx * sa + yy * ca                      # u downwind
    big = fbm(n, n, 3, 3, g, 6); mid = fbm(n, n, 14, 14, g, 5); fine = vnoise(n, n, 420, 420, g)
    d = np.sqrt((u / .5) ** 2 + (v / .42) ** 2) + (big - .5) * .7 + (mid - .5) * .3
    burn = 1 - sstep(.05, 1.1, d)                                       # 1 at the core, 0 outside
    # stubble: grass stems cut off by the fire, seen from above as short dark strokes + dots
    f1, f2, cidg = voronoi(n, n, n // 7, n // 7, g, .95)
    stem = (1 - sstep(.08, .22, f1)) * (cidg > .25)
    tone, ridge, _e = strands(n, n, g, 3.2, 26)
    char = sstep(.55, .8, burn * .85 + .9 * (mid - .5) + .3 * (fine - .5))   # partial char, not solid black
    earth = sstep(.35, .6, burn) * sstep(.55, .75, fbm(n, n, 9, 9, g, 4)) * (1 - char)
    drift_n = fbm(n, n, 3, 18, g, 5)                                    # elongated along v... rotate:
    drift = sstep(.55, .72, drift_n * .6 + .4 * fbm(n, n, 20, 6, g, 4)) * sstep(.2, .6, burn)
    meadow = lerp(col((.040, .052, .018)), col((.13, .15, .055)), np.clip(.6 * tone + .4 * fine, 0, 1))
    singed = lerp(col((.10, .085, .035)), col((.25, .20, .09)), np.clip(.7 * tone + .3 * fine, 0, 1))
    blackened = lerp(col((.030, .026, .022)), col((.09, .075, .055)), tone)
    bc = lerp(meadow, singed, sstep(.05, .35, burn))
    bc = lerp(bc, blackened, char * (.55 + .45 * ridge[..., None] if False else 1.0) * (.6 + .4 * ridge))
    bc = lerp(bc, lerp(col((.10, .07, .045)), col((.17, .12, .08)), fine), earth * .9)
    bc = lerp(bc, col((.015, .013, .012)), stem * char * .8)
    bc = lerp(bc, col((.26, .19, .09)), stem * (1 - char) * sstep(.1, .4, burn) * .6)
    ashc = lerp(col((.24, .23, .22)), col((.44, .43, .41)), fine)
    bc = lerp(bc, ashc, drift * .7)
    # feathered, irregular edge: coverage thins out stochastically through the singed fringe
    cover = sstep(.0, .6, burn) + (mid - .5) * .3 + (tone - .5) * .3
    alpha = (cover > .15 + .7 * fine).astype(F)          # stochastic coverage over a wide fringe
    edge = np.maximum(np.abs(xx), np.abs(yy)) * 2
    alpha *= (1 - sstep(.88, .97, edge))
    hgt = .45 * ridge * (1 - char) + .5 * stem * (1 - drift) + .7 * drift * mid + .2 * fine
    rough = np.clip(.92 - .22 * drift * (1 - mid) - .25 * char * sstep(.6, .9, ridge), .55, 1)   # compacted ash and char sheen
    ao = np.clip(.65 + .35 * hgt, .3, 1)
    return bc, hgt, rough, ao, alpha


def tex_ground_patches():
    """2048^2 = four 1024 px patches (quadrants), one per ground-scorch decal asset."""
    n = 1024; g = gen('ground-patches')
    BC = np.zeros((2 * n, 2 * n, 3), F); H = np.zeros((2 * n, 2 * n), F); RO = np.zeros_like(H); AO = np.zeros_like(H); A = np.zeros_like(H)
    for q, wind in enumerate([.4, 2.1, -.9, 1.3]):
        bc, h, r, a, al = ground_patch(n, g, q, wind)
        r0, c0 = (q // 2) * n, (q % 2) * n
        sl = (slice(r0, r0 + n), slice(c0, c0 + n))
        BC[sl] = bc; H[sl] = h; RO[sl] = r; AO[sl] = a; A[sl] = al
    save_set('Ruin_ScorchGround', BC, normal_from_height(H, 8.0, wrap=False), np.dstack((AO, RO, np.zeros_like(AO))), alpha=A)


def tex_blood():
    """Masked decal: the original vision-1 death sprite lies in a spread of blood droplets.
    Pool soaked into the floorboards (dark, glossy at the centre, drying matte at the rim) plus
    cast-off droplets and smears.  1024^2 over 2 m."""
    n = 1024; g = gen('blood')
    yy, xx = np.mgrid[0:n, 0:n].astype(F); yy = (yy + .5) / n - .5; xx = (xx + .5) / n - .5
    big = fbm(n, n, 3, 3, g, 6); mid = fbm(n, n, 16, 16, g, 5); fine = vnoise(n, n, 500, 500, g)
    d = np.sqrt((xx / .3) ** 2 + ((yy + .05) / .24) ** 2) + (big - .5) * .7 + (mid - .5) * .15
    pool = 1 - sstep(.75, .82, d)
    drops = np.zeros((n, n), F)
    rnd = g.random((70, 4))
    for (a, r, s, e) in rnd:
        ang = a * np.pi * 2; rr = .2 + r * .27; cx, cy = np.cos(ang) * rr, np.sin(ang) * rr * .8
        rad = .004 + s * .014
        dd = np.sqrt(((xx - cx) * (1 + e)) ** 2 + (yy - cy) ** 2)
        drops = np.maximum(drops, 1 - sstep(rad * .7, rad, dd))
    plank = (np.abs(((xx + .5) * 8.0) % 1.0 - .5) > .46).astype(F)          # seeped along board gaps
    seep = sstep(.6, .9, 1 - d) * plank * .0 + plank * sstep(.55, .85, 1 - np.abs(d - .8) * 3) * .6
    cover = np.clip(pool + drops, 0, 1)
    alpha = (cover > .5).astype(F)
    wet = sstep(.2, .7, 1 - d)
    bc = lerp(col((.16, .018, .012)), col((.075, .008, .006)), wet)
    bc = lerp(bc, col((.24, .05, .03)), drops * (1 - pool) * .5)
    bc = bc * (.85 + .3 * fine[..., None])
    hgt = .6 * pool * (1 - sstep(.5, .8, d)) + .4 * drops + .05 * fine
    rough = np.clip(.9 - .2 * wet + .08 * fine, .68, 1)          # tacky, heat-dried blood: little grazing sheen          # tacky, half-dried in the heat
    ao = np.ones((n, n), F)
    save_set('RuinInt_Blood', bc, normal_from_height(hgt, 3.0, wrap=False), np.dstack((ao, rough, np.zeros_like(ao))), alpha=alpha)


def tex_mother_remains():
    """Smoke and scorch pass over a COPY of the mother's atlas (Characters/Textures, read-only).
    UV-agnostic: broad soot film, scorched blotches and ash dusting; alpha (hair cards) kept."""
    src = HERE.parents[1] / 'Characters/Textures'
    bc = np.asarray(Image.open(src / 'T_Mother_Atlas_BC.png').convert('RGBA'), dtype=F) / 255.0
    orm = np.asarray(Image.open(src / 'T_Mother_Atlas_ORM.png').convert('RGB'), dtype=F) / 255.0
    nrm = Image.open(src / 'T_Mother_Atlas_N.png').convert('RGB')
    n = bc.shape[0]; g = gen('mother-remains')
    film = fbm(n, n, 6, 6, g, 6); blot = sstep(.6, .75, fbm(n, n, 10, 10, g, 5)); fine = vnoise(n, n, 900, 900, g)
    ash = sstep(.7, .85, fbm(n, n, 40, 40, g, 3)) * .5
    rgb = bc[..., :3] * (.55 + .25 * film[..., None])                              # smoke-darkened
    rgb = lerp(rgb, col((.03, .025, .02)), blot * .75)                                # scorched
    rgb = lerp(rgb, col((.42, .41, .40)), ash * (1 - blot))                           # ash dusting
    rgb = lerp(rgb, col((.12, .01, .008)), sstep(.78, .86, fbm(n, n, 7, 7, g, 4)) * .55)  # blood staining
    out_bc = np.dstack((rgb, bc[..., 3]))
    out_orm = orm.copy(); out_orm[..., 1] = np.clip(orm[..., 1] + .2 * blot + .15 * ash, 0, 1)
    out_orm[..., 0] = np.clip(orm[..., 0] * (.9 + .1 * fine), 0, 1)
    half = (n // 2, n // 2)                                   # 2048: a floor prop, not a hero close-up
    Image.fromarray((np.clip(out_bc, 0, 1) * 255 + .5).astype(np.uint8), 'RGBA').resize(half, Image.LANCZOS).save(OUT / 'T_RuinMother_Atlas_BC.png')
    Image.fromarray((np.clip(out_orm, 0, 1) * 255 + .5).astype(np.uint8), 'RGB').resize(half, Image.LANCZOS).save(OUT / 'T_RuinMother_Atlas_ORM.png')
    nrm.resize(half, Image.LANCZOS).save(OUT / 'T_RuinMother_Atlas_N.png')
    print('  wrote T_RuinMother_Atlas_* (derived from T_Mother_Atlas_*)', flush=True)


JOBS = {
    'timber': tex_timber, 'thatch': tex_thatch, 'ash': tex_ash, 'facades': tex_facades,
    'plaster': tex_interior_plaster, 'floor': tex_interior_floor,
    'ground': tex_ground_patches, 'blood': tex_blood, 'mother': tex_mother_remains,
    'decals': lambda: (radial_decal('RuinInt_ScorchFloor', 1024, 'floor'),
                       radial_decal('RuinInt_ScorchWall', 1024, 'wall')),
}

if __name__ == '__main__':
    t0 = time.time()
    for k, fn in JOBS.items():
        if ONLY and k not in ONLY:
            continue
        t = time.time(); print('texture set', k, flush=True); fn(); print(f'  {time.time() - t:.1f}s', flush=True)
    files = sorted(OUT.glob('T_*.png'))
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (OUT / 'texture_hashes.json').write_text(json.dumps({'seed': R.SEED, 'files': manifest}, indent=2) + '\n')
    print(f'done {len(files)} files {time.time() - t0:.1f}s')
