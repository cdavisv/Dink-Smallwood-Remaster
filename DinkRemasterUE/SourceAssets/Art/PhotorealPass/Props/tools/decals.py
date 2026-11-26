"""Decal texture sets for the photoreal pass: blood splats (glossy wet blood: gore stays) and burn marks (a black scorch on the ground).
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
    """One scorch mark as a signed field (> 0 inside the black heart, in units of its radius): a ragged star, as the 1997
    pictures 158 draw a burn (a black blot with spikes of soot thrown out of it), not a round pit."""
    y, x = np.mgrid[0:C, 0:C].astype(np.float32); cx, cy = C / 2 + rng.uniform(-12, 12), C / 2 + rng.uniform(-12, 12)
    r = np.hypot(x - cx, y - cy); th = np.arctan2(y - cy, x - cx)
    lob = sum(rng.uniform(0.05, 0.16) * np.cos(k * th + rng.uniform(0, 6.28)) for k in (2, 3, 5)); R0 = rng.uniform(80, 100)
    spikes = np.zeros_like(r)
    for _ in range(int(rng.integers(9, 15))):                                   # soot thrown out along rays: narrow, tapering
        a0 = rng.uniform(0, 6.28); w = rng.uniform(0.05, 0.14); ln = rng.uniform(0.22, 0.72)
        d = np.abs(np.angle(np.exp(1j * (th - a0)))); spikes = np.maximum(spikes, ln * np.clip(1 - (d / w) ** 1.6, 0, 1))
    edge = R0 * (1 + lob + spikes) + 22 * (fbm(rng, C, 7) - 0.5) + 9 * (fbm(rng, C, 28) - 0.5)
    return (edge - r) / R0


def burn_set(rng):
    """Four scorch marks on the ground. Black char in the heart, soot spikes, a brown singed rim that breaks up into the
    ground; ash only as sparse fine flecks; hardly any relief and no gloss. The first version (a round pit of crazed
    plates with wide ash patches) read in the game as a pale grey cracked slab lying on the grass."""
    n = 2 * C; D = np.zeros((n, n), np.float32)
    for j in range(2):
        for i in range(2):
            D[j * C:(j + 1) * C, i * C:(i + 1) * C] = burn(rng)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); f1 = fbm(rng, n, 20); f2 = fbm(rng, n, 80); f3 = fbm(rng, n, 220, oct=2)
    heart = ss(D + 0.25 * (f1 - 0.5), 0.0, 0.22)                                 # solid black
    soot = ss(D + 0.5 * (f2 - 0.5), -0.34, 0.02)                                 # the singed rim, torn by fine noise
    char = np.array([0.006, 0.0055, 0.005]); singe = np.array([0.020, 0.011, 0.005]); ash = np.array([0.055, 0.052, 0.048])
    col = singe[None, None] * (0.7 + 0.6 * f1)[..., None]
    col = col + (char - col) * heart[..., None]
    col = col * (0.8 + 0.4 * f3)[..., None]                                      # granular char, no plates
    fleck = ss(f3 + 0.35 * f2, 1.02, 1.12) * heart * 0.55                        # sparse fine ash
    col = col + (ash - col) * np.clip(fleck, 0, 1)[..., None]
    edge = ss(np.minimum(np.minimum(xx % C, C - 1 - xx % C), np.minimum(yy % C, C - 1 - yy % C)), 2, 30)
    alpha = np.clip(np.maximum(heart, soot * (0.55 + 0.6 * f2)), 0, 1) * edge
    h = -0.25 * ss(D, -0.05, 0.5) + 0.10 * f3 * heart                             # a shallow hollow, fine grain
    rough = np.ones_like(D)
    ao = 1 - 0.2 * heart
    return col, alpha, normal(h, 4.0), np.stack([np.clip(ao, 0, 1), rough, np.zeros_like(rough)], -1)


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
    {'name': 'BurnHole', 'class': 'burn_hole_decal (26 placements)', 'files': sets['BurnHole'], 'resolution_px': 1024, 'specular': 0.0, 'atlas': '2 x 2 variants, 512 px cells',
     'size_m': 'one cell covers about 1.2 x 1.2 m (the charred pit is 0.5-0.6 m across)', 'material': 'deferred decal, translucent blend: base colour = BC.rgb, opacity = BC.a (scorch halo fades out), normal = N (a shallow hollow), specular 0 (manifest row "specular": a lit black decal with the default specular is grey in the sun), roughness = ORM.G, AO = ORM.R, metallic 0; optional faint ember emissive is not authored',
     'known_weaknesses': 'procedural: a flat scorch (black heart, soot spikes, singed rim), no burnt debris and no depth; four variants only'}]}
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
