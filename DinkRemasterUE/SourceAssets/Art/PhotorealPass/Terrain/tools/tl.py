"""Terrain set toolkit: load CC0 scans, re-tile, height-blend, grade, write game sets.
Run helper scripts that import this with `python3 -I` (scan files are untrusted data, opened only with Pillow)."""
import os, glob, json, hashlib
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN = os.path.dirname(HERE)
TP = os.path.join(os.path.dirname(TERRAIN), 'ThirdParty')
N = 2048


def srgb2lin(a):
    a = np.asarray(a, np.float32)
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).astype(np.float32)


def lin2srgb(a):
    a = np.clip(a, 0, None)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055).astype(np.float32)


def luma(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-12), 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


def gblur(a, sigma):
    """periodic gaussian blur (FFT), sigma in px"""
    if sigma <= 0:
        return a
    n0, n1 = a.shape[:2]
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.rfftfreq(n1)[None, :]
    k = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy)).astype(np.float32)
    if a.ndim == 3:
        return np.stack([gblur(a[..., i], sigma) for i in range(a.shape[2])], -1)
    return np.fft.irfft2(np.fft.rfft2(a) * k, s=a.shape).astype(np.float32)


def fbm(seed, lmax, lmin, slope=1.5, n=N, aniso=(1.0, 1.0)):
    """periodic band-passed power-law noise, zero mean unit std. lmax/lmin are wavelengths as a fraction of the tile."""
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n)).astype(np.float32)
    fy = np.fft.fftfreq(n, 1.0 / n)[:, None] * aniso[1]
    fx = np.fft.rfftfreq(n, 1.0 / n)[None, :] * aniso[0]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    amp = f ** (-slope)
    lo, hi = 1.0 / lmax, 1.0 / lmin
    amp *= (f >= lo * 0.999) * np.exp(-(f / hi) ** 4)
    amp[0, 0] = 0
    o = np.fft.irfft2(np.fft.rfft2(w) * amp, s=(n, n)).astype(np.float32)
    return (o - o.mean()) / (o.std() + 1e-9)


def cover(noise, frac, soft=0.25):
    """mask 0..1 covering about `frac` of the area, edge softness in noise std units"""
    q = np.quantile(noise[::4, ::4], 1 - frac)
    return np.clip((noise - q) / soft * 0.5 + 0.5, 0, 1).astype(np.float32)


def _open(path, mode=None):
    im = Image.open(path)
    if im.mode in ('I;16', 'I;16B', 'I'):
        a = np.asarray(im).astype(np.float32) / 65535.0
    else:
        if mode:
            im = im.convert(mode)
        a = np.asarray(im).astype(np.float32) / 255.0
    if a.shape[0] != N:
        im2 = Image.fromarray((a * 255).astype(np.uint8)) if a.ndim == 3 else Image.fromarray(a, 'F')
        a = np.asarray(im2.resize((N, N), Image.LANCZOS)).astype(np.float32) / (255.0 if a.ndim == 3 else 1.0)
    return a


def load(aid, size_m):
    """returns dict with linear bc, unit normal n (GL, +Y up), ao, rough, h in metres, plus source info"""
    d = glob.glob(os.path.join(TP, '*', aid))[0]
    src = os.path.basename(os.path.dirname(d))
    fs = {os.path.basename(f): f for f in glob.glob(d + '/*')}

    def pick(*keys):
        for k in keys:
            for b, f in fs.items():
                if k in b:
                    return f
        return None
    S = {'id': aid, 'source': src, 'size_m': size_m}
    S['bc'] = srgb2lin(_open(pick('_diff', '_Color'), 'RGB'))
    n = _open(pick('_nor_gl', '_NormalGL'), 'RGB') * 2 - 1
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    S['n'] = n
    arm = pick('_arm_')
    if arm:
        a = _open(arm, 'RGB')
        S['ao'], S['rough'] = a[..., 0], a[..., 1]
    else:
        ao = pick('_AmbientOcclusion')
        S['ao'] = _open(ao, 'L') if ao else np.ones((N, N), np.float32)
        S['rough'] = _open(pick('_Roughness'), 'L')
    h = _open(pick('_disp', '_Displacement'))
    if h.ndim == 3:
        h = h[..., 0]
    em = pick('_Emission')
    if em:
        S['emis'] = luma(srgb2lin(_open(em, 'RGB')))
    # metric height: fit the height gradient to the normal map slopes
    p = size_m / N
    if float(h.max() - h.min()) < 1e-4:
        # broken displacement file: integrate the normal map instead (periodic Poisson solve)
        sx0 = -n[..., 0] / np.maximum(n[..., 2], 0.2); sy0 = -n[..., 1] / np.maximum(n[..., 2], 0.2)
        ky = np.fft.fftfreq(N)[:, None] * 2 * np.pi; kx = np.fft.fftfreq(N)[None, :] * 2 * np.pi
        k2 = kx * kx + ky * ky; k2[0, 0] = 1
        # +Y is image up, so d/dy = -d/drow
        Hf = (-1j * kx * np.fft.fft2(sx0) + 1j * ky * np.fft.fft2(sy0)) / k2
        Hf[0, 0] = 0
        hm = np.real(np.fft.ifft2(Hf)).astype(np.float32) * p
        S['fit'] = {'height': 'integrated from the normal map (source displacement file is blank)'}
        S['h'] = hm - hm.mean()
        print('   height integrated from normals for', aid, 'span', float(hm.max() - hm.min()))
        return S
    hb = gblur(h, 2.0)
    nb = gblur(n, 2.0)
    sx = -nb[..., 0] / np.maximum(nb[..., 2], 0.2)
    sy = -nb[..., 1] / np.maximum(nb[..., 2], 0.2)
    gx = (np.roll(hb, -1, 1) - np.roll(hb, 1, 1)) / (2 * p)
    gy = (np.roll(hb, 1, 0) - np.roll(hb, -1, 0)) / (2 * p)   # +Y is image up
    cx = float((gx * sx).sum() / np.sqrt((gx * gx).sum() * (sx * sx).sum() + 1e-12))
    cy = float((gy * sy).sum() / np.sqrt((gy * gy).sum() * (sy * sy).sum() + 1e-12))
    k = float(((gx * sx).sum() + (gy * sy).sum()) / ((gx * gx).sum() + (gy * gy).sum() + 1e-12))
    S['fit'] = {'corr_x': round(cx, 3), 'corr_y_gl': round(cy, 3), 'height_span_m': round(k, 4)}
    if cy < 0.05 or cx < 0.05 or k <= 0:
        print('   WARNING normal/height disagreement for', aid, S['fit'])
        k = abs(k) if abs(k) > 1e-4 else 0.02
    S['h'] = (h - h.mean()) * k
    return S


def rep(S, k, shift=(0.0, 0.0)):
    """k x k repeats of the scan inside the tile (box-filtered), optional shift as a tile fraction"""
    def f(a):
        if k > 1:
            t = np.tile(a, (k, k) + (1,) * (a.ndim - 2))
            sh = t.shape
            t = t.reshape(N, k, N, k, *sh[2:]).mean(axis=(1, 3))
        else:
            t = a
        if shift != (0.0, 0.0):
            t = np.roll(t, (int(shift[1] * N), int(shift[0] * N)), (0, 1))
        return t.astype(np.float32)
    O = dict(S)
    for key in ('bc', 'n', 'ao', 'rough', 'h', 'emis'):
        if key in S:
            O[key] = f(S[key])
    O['n'] = O['n'] / (np.linalg.norm(O['n'], axis=-1, keepdims=True) + 1e-9)
    O['size_m'] = S['size_m'] * k
    O['used'] = [(S['id'], S['source'], k)]
    return O


def fit(S, tile_m, shift=(0.0, 0.0)):
    """resample the scan at its true scale into a tile of tile_m metres (any, non-commensurate, number of periods)
    and make the result periodic by handing over to a half-shifted copy near the tile border."""
    k = tile_m / S['size_m']
    kk = int(np.ceil(k))
    m = int(round(N * k))
    def f(a):
        if a.ndim == 3:
            return np.stack([f(a[..., i]) for i in range(a.shape[2])], -1)
        t = np.roll(a, (int(shift[1] * N), int(shift[0] * N)), (0, 1))
        t = np.tile(t, (kk, kk))[:m, :m]
        return np.asarray(Image.fromarray(t.astype(np.float32), 'F').resize((N, N), Image.LANCZOS if k > 1 else Image.BICUBIC))
    O = dict(S)
    for key in ('bc', 'n', 'ao', 'rough', 'h', 'emis'):
        if key in S:
            O[key] = f(S[key])
            if key in ('bc', 'ao', 'rough', 'emis'):
                O[key] = np.clip(O[key], 0.0, None)        # resampling filters overshoot below zero
    # make it periodic: near the tile border show a half-tile-shifted copy instead (its own seam sits at the centre, hidden);
    # the hand-over is height-aware so it stays crisp instead of ghosting
    t = (np.arange(N) + 0.5) / N
    e = np.minimum(t, 1 - t)
    d = np.minimum(e[:, None], e[None, :])
    wob = fbm((sum(map(ord, S['id'])) % 9973) + int(shift[0] * 100), 0.25, 0.03, 1.2) * 0.02
    hn = (O['h'] - O['h'].mean()) / (O['h'].std() + 1e-9)
    R = {kk_: np.roll(O[kk_], (N // 2, N // 2), (0, 1)) for kk_ in ('bc', 'n', 'ao', 'rough', 'h', 'emis') if kk_ in O}
    hr = np.roll(hn, (N // 2, N // 2), (0, 1))
    w = smooth(-0.35, 0.35, (d + wob - 0.07) / 0.05 + 0.25 * (hn - hr))
    w = np.where(d < 0.004, 0.0, w).astype(np.float32)
    for kk_ in R:
        ww = w[..., None] if O[kk_].ndim == 3 else w
        O[kk_] = O[kk_] * ww + R[kk_] * (1 - ww)
    O['n'] = O['n'] / (np.linalg.norm(O['n'], axis=-1, keepdims=True) + 1e-9)
    O['size_m'] = tile_m
    O['used'] = [(S['id'], S['source'], round(k, 2))]
    return O


def window(margin=0.04):
    """kept for older recipes: fit() layers are periodic now, so no border window is needed"""
    return np.float32(1.0)


def selfblend(S, k, seed, quarter_turns=1, shift=(0.37, 0.21), frac=0.5, soft=0.7, hk=0.5):
    """k x k repeats of the scan blended with a turned, shifted copy of itself under a tile-period mask:
    breaks the scan's own period and halves how often any landmark shows"""
    a = rep(S, k)
    r = S
    for _ in range(quarter_turns):
        r = rot90(r)
    b = rep(r, k, shift)
    o = hblend(a, b, cover(fbm(seed, 0.6, 0.06, 1.4), frac, soft), hk, 0.5)
    o['used'] = [(S['id'], S['source'], k)]
    return o


def rot90(S):
    """the scan turned a quarter turn counter-clockwise (still periodic): a cheap second, different-looking layer"""
    O = dict(S)
    for key in ('bc', 'ao', 'rough', 'h', 'emis'):
        if key in S:
            O[key] = np.ascontiguousarray(np.rot90(S[key]))
    n = np.rot90(S['n'])
    O['n'] = np.stack([-n[..., 1], n[..., 0], n[..., 2]], -1).astype(np.float32)
    return O


def match_colour(S, ref, amount=1.0):
    """move S's mean colour (linear) toward ref's"""
    g = (ref['bc'].reshape(-1, 3).mean(0) / S['bc'].reshape(-1, 3).mean(0)) ** amount
    S['bc'] = S['bc'] * g
    return S


def hblend(A, B, m, k=0.6, soft=0.35):
    """height-aware blend: B over A where mask m (0..1) says so; high parts of B come through first"""
    ha = (A['h'] - A['h'].mean()) / (A['h'].std() + 1e-9)
    hb = (B['h'] - B['h'].mean()) / (B['h'].std() + 1e-9)
    t = (m * 2 - 1) + k * 0.5 * (hb - ha)
    w = smooth(-soft, soft, t)
    O = dict(A)
    for key in ('bc', 'n', 'ao', 'rough', 'h'):
        a, b = A[key], B[key]
        ww = w[..., None] if a.ndim == 3 else w
        O[key] = a * (1 - ww) + b * ww
    O['n'] = O['n'] / (np.linalg.norm(O['n'], axis=-1, keepdims=True) + 1e-9)
    O['used'] = A.get('used', []) + B.get('used', [])
    O['w'] = w
    return O


def grade(S, target=None, hue=0.7, mean_luma=None, sat=1.0, contrast=1.0):
    """target: sRGB 0-255 colour whose chromaticity the mean moves toward (hue 0..1);
    mean_luma: sRGB 0-255 value the mean luminance is set to; sat/contrast around the pixel luma / mean"""
    bc = S['bc']
    mean = bc.reshape(-1, 3).mean(0)
    if target is not None:
        t = srgb2lin(np.array(target, np.float32) / 255.0)
        g = ((t / luma(t)) / (mean / luma(mean))) ** hue
        bc = bc * g
    if mean_luma is not None:
        L = float(srgb2lin(np.float32(mean_luma / 255.0)))
        bc = bc * (L / luma(bc).mean())
    if sat != 1.0:
        l = luma(bc)[..., None]
        bc = l + (bc - l) * sat
    if contrast != 1.0:
        m = luma(bc).mean()
        l = np.maximum(luma(bc), 1e-5)[..., None]
        bc = bc * ((l / m) ** (contrast - 1.0))
    S['bc'] = np.clip(bc, 0, None).astype(np.float32)
    return S


def soft_limit(s, lo=30.0, hi=240.0, knee=12.0):
    """soft clip of sRGB 0-255 values into the plausible albedo range"""
    s = np.where(s < lo + knee, lo + knee * np.exp((s - lo - knee) / knee), s)
    s = np.where(s > hi - knee, hi - knee * np.exp(-(s - hi + knee) / knee), s)
    return s


def normal_from_height(h, px, gain=1.0):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px) * gain
    gy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) / (2 * px) * gain
    n = np.stack([-gx, -gy, np.ones_like(h)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def macro_mask(seed):
    r = fbm(seed, 1.0, 0.25, 1.6, 512)
    g = fbm(seed + 1, 0.34, 0.08, 1.3, 512)
    b = fbm(seed + 2, 0.12, 0.02, 1.0, 512)
    o = np.stack([np.clip(c * 0.22 + 0.5, 0, 1) for c in (r, g, b)], -1)
    return (o * 255 + 0.5).astype(np.uint8)


def write_set(name, S, tile_m, classes, note='', status='finished', weaknesses='', seed=1, extra=None, rough_gain=1.0, rough_bias=0.0, ao_gamma=1.0):
    d = os.path.join(TERRAIN, name)
    os.makedirs(d, exist_ok=True)
    pre = os.path.join(d, 'T_Terrain_%s_' % name)
    s = soft_limit(lin2srgb(S['bc']) * 255.0)
    bc8 = np.clip(s + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(bc8, 'RGB').save(pre + 'BC.png')
    n = S['n'] / (np.linalg.norm(S['n'], axis=-1, keepdims=True) + 1e-9)
    Image.fromarray(np.clip((n * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8), 'RGB').save(pre + 'N.png')
    rough = np.clip(S['rough'] * rough_gain + rough_bias, 0.04, 1.0)
    ao = np.clip(S['ao'], 0, 1) ** ao_gamma
    orm = np.stack([ao, rough, np.zeros_like(ao)], -1)
    Image.fromarray(np.clip(orm * 255 + 0.5, 0, 255).astype(np.uint8), 'RGB').save(pre + 'ORM.png')
    h = S['h']
    lo, hi = float(h.min()), float(h.max())
    h16 = np.clip((h - lo) / (hi - lo + 1e-12) * 65535 + 0.5, 0, 65535).astype(np.uint16)
    Image.fromarray(h16).save(pre + 'H.png')
    Image.fromarray(macro_mask(seed * 7 + 11), 'RGB').save(pre + 'Macro.png')
    files = {'BC': 'BC.png', 'N': 'N.png', 'ORM': 'ORM.png', 'H': 'H.png', 'Macro': 'Macro.png'}
    if 'emis' in S:
        Image.fromarray(np.clip(S['emis'] * 255 + 0.5, 0, 255).astype(np.uint8), 'L').save(pre + 'E.png')
        files['E'] = 'E.png'
    l = luma(bc8.astype(np.float32))
    used = []
    for u in S.get('used', []):
        if u[:2] not in [x[:2] for x in used]:
            used.append(u)
    info = {
        'name': name,
        'files': {k: '%s/T_Terrain_%s_%s' % (name, name, v) for k, v in files.items()},
        'resolution_px': N, 'macro_px': 512,
        'tile_size_m': round(tile_m, 3),
        'texel_mm_per_px': round(tile_m / N * 1000, 3),
        'height_range_m': round(hi - lo, 4),
        'height_note': 'H 0..65535 spans height_range_m; mid level about %.3f' % ((0 - lo) / (hi - lo + 1e-12)),
        'colour_spaces': {'BC': 'sRGB', 'N': 'linear, OpenGL (+Y up); flip green on Unreal import', 'ORM': 'linear; R AO, G roughness, B metallic 0', 'H': 'linear 16-bit', 'Macro': 'linear; R large, G medium, B small low-frequency variation, sample at 1/6 to 1/10 of the tile UV scale', 'E': 'linear emissive mask'},
        'tile_classes': classes,
        'status': status,
        'method': note,
        'third_party': [{'source': u[1], 'asset_id': u[0], 'licence': 'CC0-1.0', 'repeats_in_tile': u[2]} for u in used],
        'albedo_luma_srgb': {'min': round(float(l.min()), 1), 'mean': round(float(l.mean()), 1), 'max': round(float(l.max()), 1)},
        'mean_srgb': [int(x) for x in bc8.reshape(-1, 3).mean(0).round()],
        'roughness_mean': round(float(rough.mean()), 3),
        'known_weaknesses': weaknesses,
    }
    if extra:
        info.update(extra)
    json.dump(info, open(os.path.join(d, 'set.json'), 'w'), indent=1)
    print('wrote', name, 'tile', tile_m, 'h', round(hi - lo, 4), 'mean', info['mean_srgb'], 'rough', info['roughness_mean'])
    return info


def write_manifest():
    sets = []
    for f in sorted(glob.glob(os.path.join(TERRAIN, '*', 'set.json'))):
        sets.append(json.load(open(f)))
    order = json.load(open(os.path.join(HERE, 'order.json'))) if os.path.exists(os.path.join(HERE, 'order.json')) else []
    sets.sort(key=lambda s: order.index(s['name']) if s['name'] in order else 999)
    man = {
        'schema': 'dink-terrain-sets/1',
        'root': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Terrain',
        'conventions': 'BC sRGB RGB; N OpenGL green-up; ORM R=AO G=roughness B=metallic; H 16-bit, spans height_range_m; world tile = tile_size_m x 100 cm; Macro = companion low-frequency RGB mask (512 px) to break repetition',
        'sets': sets,
    }
    sm = []
    notes = json.load(open(os.path.join(HERE, 'scatter_notes.json'))) if os.path.exists(os.path.join(HERE, 'scatter_notes.json')) else {}
    for fam in ('BeachPebbles', 'Pebbles', 'Clam', 'Starfish'):
        sc = os.path.join(TERRAIN, 'Scatter', 'scatter_%s.json' % fam)
        if os.path.exists(sc):
            for r in json.load(open(sc)):
                r.update(notes.get(fam, {}))
                r.update(notes.get(r['name'], {}))
                sm.append(r)
    if sm:
        man['scatter_meshes'] = sm
    json.dump(man, open(os.path.join(TERRAIN, 'manifest.json'), 'w'), indent=1)
    print('manifest:', len(sets), 'sets')
