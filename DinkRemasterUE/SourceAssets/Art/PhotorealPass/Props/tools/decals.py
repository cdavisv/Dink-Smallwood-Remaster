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


def splat(F, px, py, s, amp=1.0, e=1.0, ang=0.0):
    """add one soft blob (radius s px, stretched e along ang) to the metaball field F"""
    R = int(s * e * 3) + 2; x0, x1, y0, y1 = int(max(px - R, 0)), int(min(px + R + 1, C)), int(max(py - R, 0)), int(min(py + R + 1, C))
    if x1 <= x0 or y1 <= y0:
        return
    y, x = np.mgrid[y0:y1, x0:x1].astype(np.float32); u = (x - px) * np.cos(ang) + (y - py) * np.sin(ang); v = -(x - px) * np.sin(ang) + (y - py) * np.cos(ang)
    F[y0:y1, x0:x1] += amp * np.exp(-((u / (s * e)) ** 2 + (v / s) ** 2))


def blood(rng, kind):
    """one cell after the 1997 pictures (sequences 187-189): not one pool but a SPRAY of separate drops over the whole
    picture. kind 'spurt' = spurt-01/02, a dense wide patch whose drops run together in the middle; kind 'spray' =
    sprtl/sprtr-04, some forty separate drops thrown over a tall patch. A cell is 1.7 m: a drop of the picture (2-4 px
    at the hero's scale of 3 cm a pixel) is 6-12 cm. Returns the film thickness 0..1 and a soak stain 0..1."""
    F = np.zeros((C, C), np.float32); S = np.zeros((C, C), np.float32); cx = cy = C / 2
    if kind == 'spurt':
        n, ax, ay, core = int(rng.integers(64, 80)), 185.0, 100.0, True
    else:
        n, ax, ay, core = int(rng.integers(40, 50)), 150.0, 205.0, False
    pts = []
    for i in range(n * 30):
        if len(pts) >= n:
            break
        if core:                                           # gaussian: thick in the middle, loose at the rim
            px, py = cx + rng.normal(0, ax * 0.42), cy + rng.normal(0, ay * 0.42)
        else:                                              # even over the ellipse, as the sprays are
            a, r = rng.uniform(0, 6.28), np.sqrt(rng.uniform(0, 1)); px, py = cx + ax * r * np.cos(a), cy + ay * r * np.sin(a)
        if not (26 < px < C - 26 and 26 < py < C - 26) or ((px - cx) / (ax * 1.25)) ** 2 + ((py - cy) / (ay * 1.25)) ** 2 > 1:
            continue
        if not core and any(np.hypot(px - qx, py - qy) < 26 for qx, qy in pts):      # the sprays' drops do not touch
            continue
        pts.append((px, py))
    for (px, py) in pts:
        d = np.hypot((px - cx) / ax, (py - cy) / ay); out = np.arctan2(py - cy, px - cx) + rng.normal(0, 0.5)
        s = rng.uniform(7.0, 13.0) * (1.25 - 0.35 * d if core else 1.0)                # 5-9 cm across
        for j in range(int(rng.integers(2, 5))):                                       # a drop is two to four lobes run together
            splat(F, px + rng.normal(0, s * 0.55), py + rng.normal(0, s * 0.55), s * rng.uniform(0.55, 1.0), 1.0, rng.uniform(1.0, 1.5), rng.uniform(0, 3.14))
        if rng.random() < 0.45:                                                         # a tail thrown outward, thinning
            L = rng.uniform(1.5, 3.5) * s
            for t in np.linspace(0.3, 1.0, 7):
                splat(F, px + np.cos(out) * L * t, py + np.sin(out) * L * t, s * 0.42 * (1.1 - t), 0.9, 1.8, out)
        for j in range(int(rng.integers(1, 5))):                                       # satellites
            a, r = rng.uniform(0, 6.28), s * rng.uniform(1.6, 3.2); splat(F, px + r * np.cos(a), py + r * np.sin(a), rng.uniform(1.6, 3.4), 1.0)
        splat(S, px, py, s * 2.3, 0.8)
    for i in range(int(rng.integers(120, 180))):                                       # fine mist between the drops
        a, r = rng.uniform(0, 6.28), np.sqrt(rng.uniform(0, 1)) * 1.2; splat(F, cx + ax * r * np.cos(a), cy + ay * r * np.sin(a), rng.uniform(0.9, 2.0), 1.0)
    if core:
        splat(S, cx, cy, ay * 0.8, 0.5, ax / ay, 0.0)
    wob = 0.25 * (fbm(rng, C, 40) - 0.5)                                                # ragged outlines
    y, x = np.mgrid[0:C, 0:C].astype(np.float32); edge = ss(np.minimum(np.minimum(x, C - 1 - x), np.minimum(y, C - 1 - y)), 3, 20)
    return ss(F + wob, 0.42, 0.95) * edge, np.clip(S, 0, 1) * edge


def blood_set(rng):
    H = np.zeros((2 * C, 2 * C), np.float32); St = np.zeros((2 * C, 2 * C), np.float32)
    for k, kind in enumerate(('spurt', 'spray', 'spray', 'spurt')):
        j, i = k // 2, k % 2
        H[j * C:(j + 1) * C, i * C:(i + 1) * C], St[j * C:(j + 1) * C, i * C:(i + 1) * C] = blood(rng, kind)
    n = 2 * C; thick = np.clip(H * (0.6 + 0.8 * fbm(rng, n, 24)), 0, 1)
    dry = np.clip(ss(fbm(rng, n, 12), 0.5, 0.75) * 0.6 + (1 - ss(thick, 0.15, 0.6)) * 0.6, 0, 1)   # thin rims and small drops dry first
    wet = np.array([0.20, 0.006, 0.005]); thin = np.array([0.36, 0.016, 0.010]); crust = np.array([0.075, 0.012, 0.008]); soak = np.array([0.05, 0.012, 0.008])
    col = thin + (wet - thin) * ss(thick, 0.2, 0.75)[..., None]; col = col + (crust - col) * dry[..., None] * 0.7
    col *= (0.85 + 0.3 * fbm(rng, n, 60))[..., None]
    film = ss(H, 0.05, 0.35); stain = 0.34 * ss(St, 0.15, 0.8) * (0.6 + 0.8 * fbm(rng, n, 30))     # the ground darkens where blood soaked in
    alpha = np.clip(film * 0.95 + (1 - film) * stain, 0, 1)
    col = soak[None, None] * (1 - film[..., None]) + col * film[..., None]
    rough = np.where(film > 0.5, 0.16 + 0.12 * fbm(rng, n, 50) + 0.45 * dry ** 1.5, 0.85)
    hh = ss(H, 0.0, 0.7) * (0.6 + 0.4 * thick)
    return col, alpha, normal(hh, 5.0), np.stack([np.ones_like(rough), np.clip(rough, 0.06, 1), np.zeros_like(rough)], -1)


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
    char = np.array([0.012, 0.011, 0.011]); ash = np.array([0.075, 0.072, 0.066]); scorch = np.array([0.02, 0.013, 0.008])
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
bu = burn_set(np.random.default_rng(1998)); sets['BurnHole'] = save('BurnHole', *bu)
man = {'schema': 'dink-decals/1', 'folder': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Props/Decals', 'sets': [
    {'name': 'BloodSplat', 'class': 'blood_splat (46 placements)', 'files': sets['BloodSplat'], 'resolution_px': 1024, 'atlas': '2 x 2 variants, 512 px cells (0 and 3: the dense spurt, 1 and 2: the spray of separate drops); one cell per placement, random yaw',
     'size_m': 'one cell covers 1.7 x 1.7 m: the spray of drops is the size of the 1997 picture at the hero\'s scale (1.0-1.3 m by 0.6-1.4 m)', 'tint': [0.42, 0.30, 0.30], 'material': 'deferred decal, translucent blend: base colour = BC.rgb, opacity = BC.a, normal = N (OpenGL: flip green), roughness = ORM.G (0.16 wet drop to 0.6 dried rim; 0.85 on the soak stain), metallic 0, specular 0.5; no emissive',
     'known_weaknesses': 'procedural: drops are soft lobes run together, tails are straight; the cell does not follow the 1997 frame of its placement (picked by a hash of the origin), so a spurt can lie where the picture was a spray; four variants only'},
    {'name': 'BurnHole', 'class': 'burn_hole_decal (26 placements)', 'files': sets['BurnHole'], 'resolution_px': 1024, 'atlas': '2 x 2 variants, 512 px cells',
     'size_m': 'one cell covers about 1.2 x 1.2 m (the charred pit is 0.5-0.6 m across)', 'tint': [0.6, 0.6, 0.6], 'material': 'deferred decal, translucent blend: base colour = BC.rgb, opacity = BC.a (scorch halo fades out), normal = N (sunk pit with a raised lip and crazed char), roughness = ORM.G, AO = ORM.R, metallic 0; optional faint ember emissive is not authored',
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
