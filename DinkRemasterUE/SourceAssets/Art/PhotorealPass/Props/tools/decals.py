"""Decal texture sets for the photoreal pass: blood splats (glossy wet blood: gore stays) and burn holes (charred pit).
Each set is a 2 x 2 atlas of four variants, 1024 px: T_Decal_<Name>_BC (sRGB + alpha), _N (linear, OpenGL +Y), _ORM (linear;
R ambient occlusion, G roughness, B metallic 0). Writes Props/Decals/decals.json and a preview.   python3 -I decals.py"""
import json, os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'Decals'); os.makedirs(OUT, exist_ok=True)
C = 512                                                    # one variant cell


def noise(rng, n, cells):
    a = rng.random((cells + 3, cells + 3)).astype(np.float32)
    im = Image.fromarray(a, 'F').resize((n * (cells + 3) // cells, n * (cells + 3) // cells), Image.BICUBIC)
    return np.asarray(im)[:n, :n]


def fbm(rng, n, cells, oct=4):
    s = np.zeros((n, n), np.float32); a = 0.5
    for o in range(oct):
        s += a * noise(rng, n, cells * 2 ** o); a *= 0.5
    return s / (1 - 0.5 ** oct)


def ss(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def normal(h, k):
    gy, gx = np.gradient(h); n = np.stack([-gx * k, gy * k, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=2)[..., None]; return n * 0.5 + 0.5


def srgb(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def blood(rng):
    """one splat: a pooled centre with a scalloped edge, radial streaks and thrown droplets; h = film thickness 0..1"""
    y, x = np.mgrid[0:C, 0:C].astype(np.float32); cx, cy = C / 2 + rng.uniform(-30, 30), C / 2 + rng.uniform(-30, 30)
    dx, dy = x - cx, y - cy; r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    lob = sum(rng.uniform(0.05, 0.22) * np.cos(k * th + rng.uniform(0, 6.28)) for k in (2, 3, 5, 7, 11)); R0 = rng.uniform(70, 105)
    h = ss(R0 * (1 + lob) + 22 * (fbm(rng, C, 6) - 0.5) - r, -4, 14)
    for i in range(int(rng.integers(7, 13))):                # streaks thrown outward, tapering
        a = rng.uniform(0, 6.28); L = rng.uniform(60, 150); w = rng.uniform(3, 9)
        u = dx * np.cos(a) + dy * np.sin(a); v = -dx * np.sin(a) + dy * np.cos(a); t = np.clip((u - R0 * 0.6) / L, 0, 1)
        h = np.maximum(h, ss(w * (1 - t) ** 0.7 - np.abs(v + 6 * np.sin(u * 0.05 + i)), -1.5, 2.5) * (u > R0 * 0.5) * (u < R0 * 0.6 + L))
    for i in range(int(rng.integers(50, 90))):               # droplets: many small, a few large, further out the smaller
        a = rng.uniform(0, 6.28); d = R0 * rng.uniform(1.05, 2.4); s_ = min(9.0, max(1.2, rng.pareto(2.2) * 3.0 * (2.6 - d / R0))); e = rng.uniform(1.0, 2.2)
        px, py = cx + d * np.cos(a), cy + d * np.sin(a)
        if not (8 < px < C - 8 and 8 < py < C - 8):
            continue
        u = (x - px) * np.cos(a) + (y - py) * np.sin(a); v = -(x - px) * np.sin(a) + (y - py) * np.cos(a)
        h = np.maximum(h, ss(1.0 - np.hypot(u / (s_ * e), v / s_), 0.0, 0.5))
    edge = ss(np.minimum(np.minimum(x, C - 1 - x), np.minimum(y, C - 1 - y)), 2, 14)
    return h * edge


def blood_set(rng):
    H = np.zeros((2 * C, 2 * C), np.float32)
    for j in range(2):
        for i in range(2):
            H[j * C:(j + 1) * C, i * C:(i + 1) * C] = blood(rng)
    n = 2 * C; thick = np.clip(H * (0.55 + 0.9 * fbm(rng, n, 10)), 0, 1)        # meniscus: thicker in from the edge, uneven
    dry = ss(fbm(rng, n, 5), 0.5, 0.75) * 0.7 + (1 - ss(thick, 0.1, 0.5)) * 0.5      # dried: thin rims and patches
    wet = np.array([0.105, 0.004, 0.004]); thin = np.array([0.3, 0.012, 0.008]); crust = np.array([0.07, 0.016, 0.01])
    col = thin + (wet - thin) * ss(thick, 0.15, 0.7)[..., None]; col = col + (crust - col) * np.clip(dry, 0, 1)[..., None] * 0.75
    col *= (0.85 + 0.3 * fbm(rng, n, 40))[..., None]
    alpha = ss(H, 0.04, 0.3) * (0.82 + 0.18 * ss(thick, 0.1, 0.5))
    rough = 0.07 + 0.1 * fbm(rng, n, 30) + 0.5 * np.clip(dry, 0, 1) ** 1.5
    hh = ss(H, 0.0, 0.6) * (0.7 + 0.3 * thick)
    return col, alpha, normal(hh, 14.0), np.stack([np.ones_like(rough), np.clip(rough, 0.04, 1), np.zeros_like(rough)], -1)


def burn(rng):
    y, x = np.mgrid[0:C, 0:C].astype(np.float32); cx, cy = C / 2 + rng.uniform(-15, 15), C / 2 + rng.uniform(-15, 15)
    r = np.hypot(x - cx, y - cy); th = np.arctan2(y - cy, x - cx)
    lob = sum(rng.uniform(0.04, 0.14) * np.cos(k * th + rng.uniform(0, 6.28)) for k in (2, 3, 4, 6, 9)); R0 = rng.uniform(95, 125)
    return (R0 * (1 + lob) + 30 * (fbm(rng, C, 5) - 0.5) - r) / R0                 # signed: > 0 inside the pit, scaled by its radius


def burn_set(rng):
    n = 2 * C; D = np.zeros((n, n), np.float32)
    for j in range(2):
        for i in range(2):
            D[j * C:(j + 1) * C, i * C:(i + 1) * C] = burn(rng)
    pts = rng.random((900, 2)) * n; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)        # crazed char: distance to the two nearest of scattered cells
    d1 = np.full((n, n), 1e9, np.float32); d2 = np.full((n, n), 1e9, np.float32)
    for (px, py) in pts:
        x0, x1, y0, y1 = int(max(px - 70, 0)), int(min(px + 70, n)), int(max(py - 70, 0)), int(min(py + 70, n))
        d = np.hypot(xx[y0:y1, x0:x1] - px, yy[y0:y1, x0:x1] - py); a = d1[y0:y1, x0:x1]; b_ = d2[y0:y1, x0:x1]
        nb = np.where(d < a, a, np.minimum(b_, d)); na = np.minimum(a, d); d1[y0:y1, x0:x1] = na; d2[y0:y1, x0:x1] = nb
    crack = 1 - ss(d2 - d1, 0.0, 5.0)
    pit = ss(D, 0.0, 0.35); halo = ss(D, -0.75, 0.05); f1 = fbm(rng, n, 24); f2 = fbm(rng, n, 90)
    char = np.array([0.012, 0.011, 0.011]); ash = np.array([0.13, 0.125, 0.115]); scorch = np.array([0.02, 0.013, 0.008])
    col = scorch[None, None] * (0.6 + 0.8 * f1)[..., None]
    col = col + (char - col) * pit[..., None]
    ashm = ss(f1 + 0.5 * f2, 0.95, 1.1) * pit * 0.7 + ss(f2, 0.68, 0.74) * ss(D, -0.2, 0.2) * 0.2
    col = col + (ash - col) * np.clip(ashm, 0, 1)[..., None]
    col = col * (1 - 0.6 * (crack * pit))[..., None]
    edge = ss(np.minimum(np.minimum(xx % C, C - 1 - xx % C), np.minimum(yy % C, C - 1 - yy % C)), 2, 30)
    alpha = np.clip(halo ** 1.2 * (0.8 + 0.6 * f1) + pit, 0, 1) * edge
    h = -0.9 * ss(D, -0.05, 0.6) + 0.25 * ss(D, -0.12, 0.0) * (1 - ss(D, 0.0, 0.12)) - 0.25 * crack * pit + 0.12 * f2 * pit      # sunk pit, raised lip, cracks
    rough = 0.93 - 0.35 * ss(f2, 0.6, 0.75) * pit * (1 - ashm)                    # glints of glassy char
    ao = 1 - 0.5 * crack * pit - 0.25 * pit
    return col, alpha, normal(h, 9.0), np.stack([np.clip(ao, 0, 1), np.clip(rough, 0.3, 1), np.zeros_like(rough)], -1)


def save(name, col, alpha, nrm, orm):
    f = {}
    for key, arr, mode in (('BC', np.concatenate([srgb(col), alpha[..., None]], -1), 'RGBA'), ('N', nrm, 'RGB'), ('ORM', orm, 'RGB')):
        p = 'T_Decal_%s_%s.png' % (name, key); Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), mode).save(os.path.join(OUT, p), optimize=True); f[key] = p
    return f


rng = np.random.default_rng(1997)
sets = {}
bc = blood_set(rng); sets['BloodSplat'] = save('BloodSplat', *bc)
bu = burn_set(rng); sets['BurnHole'] = save('BurnHole', *bu)
man = {'schema': 'dink-decals/1', 'folder': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Props/Decals', 'sets': [
    {'name': 'BloodSplat', 'class': 'blood_splat (46 placements)', 'files': sets['BloodSplat'], 'resolution_px': 1024, 'atlas': '2 x 2 variants, 512 px cells; pick one cell per placement, random yaw',
     'size_m': 'one cell covers about 0.9 x 0.9 m (the pool is 0.3-0.4 m across)', 'material': 'deferred decal, translucent blend: base colour = BC.rgb, opacity = BC.a, normal = N (OpenGL: flip green), roughness = ORM.G (0.07 wet centre to 0.6 dried rim), metallic 0, specular 0.5; no emissive',
     'known_weaknesses': 'procedural: streaks are straight tapered lines, droplets are ellipses, there is no soak-in tint on porous ground and no directional cast-off pattern; four variants only'},
    {'name': 'BurnHole', 'class': 'burn_hole_decal (26 placements)', 'files': sets['BurnHole'], 'resolution_px': 1024, 'atlas': '2 x 2 variants, 512 px cells',
     'size_m': 'one cell covers about 1.2 x 1.2 m (the charred pit is 0.5-0.6 m across)', 'material': 'deferred decal, translucent blend: base colour = BC.rgb, opacity = BC.a (scorch halo fades out), normal = N (sunk pit with a raised lip and crazed char), roughness = ORM.G, AO = ORM.R, metallic 0; optional faint ember emissive is not authored',
     'known_weaknesses': 'procedural: the crazing is an even cell pattern, ash is flecks of flat grey, no burnt debris or soot streak downwind; a decal cannot really sink the ground (normal only)'}]}
json.dump(man, open(os.path.join(OUT, 'decals.json'), 'w'), indent=1)
# preview on a dirt-brown ground, lit from the upper left, with a crude specular so the wet gloss shows
prev = []
for (col, alpha, nrm, orm) in (bc, bu):
    g = np.array([0.2, 0.15, 0.1]) * (0.8 + 0.4 * fbm(rng, 2 * C, 60))[..., None]; n = nrm * 2 - 1
    L = np.array([-0.5, 0.5, 0.7]); L /= np.linalg.norm(L); Hv = L + np.array([0, 0, 1.0]); Hv /= np.linalg.norm(Hv)
    dif = np.clip(n @ L, 0, 1)[..., None]; sp = (np.clip(n @ Hv, 0, 1) ** (2 / np.clip(orm[..., 1], 0.05, 1) ** 2))[..., None] * (1 - orm[..., 1:2]) * 0.6
    lit = col * (0.35 + 0.9 * dif) + sp; out = g * (0.35 + 0.9 * L[2]) * (1 - alpha[..., None]) + lit * alpha[..., None]
    prev.append((srgb(out) * 255).astype(np.uint8))
Image.fromarray(np.concatenate(prev, 1)).save(os.path.join(OUT, 'preview.png'))
print('decals written', list(sets))
