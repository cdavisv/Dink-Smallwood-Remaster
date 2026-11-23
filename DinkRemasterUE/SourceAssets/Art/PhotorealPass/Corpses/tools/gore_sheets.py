"""Ground sheets for the corpse kit, made with numpy and PIL only (no Blender needed):

  blood_sheet()   a pool of blood with its thrown drops, streaks and mist as a BC (+ alpha) / N / ORM set
  scorch_sheet()  a burnt hole: charred centre, radial burn tongues, ash and ember flecks

A sheet is drawn on a square of `size` metres and is used on a flat card a few millimetres above the ground
(alpha-tested), so the outline, the drops and the wet highlights are in the texture and not in the mesh.
Conventions: BC sRGB with alpha, N tangent space OpenGL (green up), ORM = occlusion, roughness, metallic.

    python3 -I gore_sheets.py preview <out.png>      # contact sheet of test sheets on a grass-green ground
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _srgb(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def noise2(px, cells, rng, octaves=4, gain=0.5):
    """value noise 0..1 on a px x px grid; `cells` = cells across the sheet for the first octave"""
    out = np.zeros((px, px), np.float32); amp = 1.0; tot = 0.0
    for _ in range(octaves):
        n = max(2, int(round(cells)))
        a = (rng.random((n, n)) * 255).astype(np.uint8)
        out += amp * np.asarray(Image.fromarray(a, 'L').resize((px, px), Image.BICUBIC), np.float32) / 255.0
        tot += amp; amp *= gain; cells *= 2.0
    return out / tot


def blur(a, sigma_px):
    """gaussian blur of a float array (FFT; the sheet edges are empty, so the wrap-around does not show)"""
    if sigma_px <= 0.05:
        return a
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2.0 * (math.pi * sigma_px) ** 2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(a.astype(np.float32)) * g, s=a.shape).astype(np.float32)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


class Canvas:
    """a mask in metres: origin at the sheet centre, +x right, +y up"""

    def __init__(self, px, size):
        self.px = px; self.size = size; self.k = px / size
        self.im = Image.new('L', (px, px), 0); self.d = ImageDraw.Draw(self.im)

    def xy(self, p):
        return (self.px / 2 + p[0] * self.k, self.px / 2 - p[1] * self.k)

    def disc(self, c, r, v=255):
        x, y = self.xy(c); r *= self.k
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=v)

    def poly(self, pts, v=255):
        self.d.polygon([self.xy(p) for p in pts], fill=v)

    def ellipse(self, c, a, b, rot, v=255, n=40):
        cs, sn = math.cos(rot), math.sin(rot)
        self.poly([(c[0] + cs * a * math.cos(t) - sn * b * math.sin(t), c[1] + sn * a * math.cos(t) + cs * b * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)], v)

    def arr(self):
        return np.asarray(self.im, np.float32) / 255.0


def lobed(c, a, b, rot, rng, lobes=0.22, n=180, runs=()):
    """outline of an ellipse broken into lobes; runs = [(angle, half width rad, extra length m)] tongues that run further out"""
    th = np.linspace(0, 2 * math.pi, n, endpoint=False); r = np.ones(n)
    for k in range(2, 9):
        r += lobes / (k - 1) ** 0.8 * rng.uniform(0.4, 1.0) * np.sin(k * th + rng.uniform(0, 6.3))
    R = a * b / np.sqrt((b * np.cos(th)) ** 2 + (a * np.sin(th)) ** 2) * r
    for ang, w, e in runs:
        d = np.angle(np.exp(1j * (th + rot - ang))); R = R + e * np.exp(-(d / w) ** 2)
    cs, sn = math.cos(rot), math.sin(rot)
    return [(c[0] + R[i] * (cs * math.cos(th[i]) - sn * math.sin(th[i])), c[1] + R[i] * (sn * math.cos(th[i]) + cs * math.sin(th[i]))) for i in range(n)]


def drop(cv, p, r, ang, stretch, rng, tail=True):
    """one thrown drop: a body drawn out along its flight direction, a thin tail and a satellite or two beyond it"""
    dx, dy = math.cos(ang), math.sin(ang)
    cv.ellipse(p, r * stretch, r, ang, n=14)
    if tail and stretch > 1.25:
        L = r * stretch * rng.uniform(1.2, 2.6); w = r * rng.uniform(0.25, 0.5)
        cv.poly([(p[0] - dy * w, p[1] + dx * w), (p[0] + dy * w, p[1] - dx * w), (p[0] + dx * L, p[1] + dy * L)])
        for _ in range(int(rng.integers(0, 3))):
            q = L * rng.uniform(1.1, 1.9); cv.disc((p[0] + dx * q + rng.normal(0, r * 0.3), p[1] + dy * q + rng.normal(0, r * 0.3)), r * rng.uniform(0.18, 0.4))


def sprite_red(path, width_m, height_m, depth=1.3, fill=0):
    """the blood of a 1997 picture as a ground stamp: (mask image, width m, depth m, centre xy m relative to the card centre, red area m2).
    The extracted picture is stretched to a power-of-two canvas, so the scale comes from the card (width_m x height_m of placements.json),
    not from the pixel count. Red = clearly red pixels; the picture looks down at an angle, so its height is stretched by `depth` on the ground."""
    im = Image.open(path).convert('RGBA'); a = np.asarray(im).astype(np.int32); op = a[..., 3] > 0
    red = op & (a[..., 0] > 105) & (a[..., 1] < 85) & (a[..., 2] < 85) & (a[..., 0] > a[..., 1] * 2)
    ys, xs = np.nonzero(op); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1; red = red[y0:y1, x0:x1]; h, w = red.shape
    mx = width_m / w; my = height_m / h
    mask = Image.fromarray((red * 255).astype(np.uint8), 'L').filter(ImageFilter.MaxFilter(3))
    pad = 0
    if fill:                                         # close the gaps between the picture's red pixels (a body lay over them): one pool, not islands
        pad = 4 * int(fill) + 6                      # room round the picture, or its frame cuts the grown pool off in a straight line
        wide = Image.new('L', (mask.width + 2 * pad, mask.height + 2 * pad), 0); wide.paste(mask, (pad, pad)); mask = wide
        mask = mask.filter(ImageFilter.MaxFilter(2 * int(fill) + 1)).filter(ImageFilter.MinFilter(2 * max(int(fill) - 1, 0) + 1))
        # round the pixel stairs off: no blocky outline. The square dilation above leaves corners `fill` picture pixels wide, so the blur
        # must be wider than that (9 px at x10 was under one picture pixel and the pool of 436 kept its stairs, seen in the 16 Nov render);
        # the cut below the middle grey keeps the pool at least as large as the picture's red
        r = 18 * (int(fill) + 1.5); big = mask.resize((mask.width * 10, mask.height * 10), Image.BICUBIC).filter(ImageFilter.GaussianBlur(r)); f = np.asarray(big, np.float32) / 255.0
        # ... and a pool is not a polygon: the picture's red is a straight-sided patch of pixels, so the soft field is bent by two
        # scales of noise before the cut (lobes about 30 cm and 10 cm across); the cut stays below the middle so no blood is lost
        rng = np.random.default_rng(int(red.sum()) + 7)
        def _n(cell):
            small = rng.random((f.shape[0] // cell + 3, f.shape[1] // cell + 3)).astype(np.float32)
            return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((f.shape[1] + 2 * cell, f.shape[0] + 2 * cell), Image.BICUBIC), np.float32)[:f.shape[0], :f.shape[1]] / 255.0
        c1 = max(8, int(0.30 / mx * 10)); c2 = max(4, int(0.10 / mx * 10))
        f = f + np.clip(f / 0.12, 0, 1) * (0.80 * (_n(c1) - 0.5) + 0.34 * (_n(c2) - 0.5))      # only where the pool's own edge is: no islands out of the noise alone
        mask = Image.fromarray(((f > 0.36) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(4))
    ys2, xs2 = np.nonzero(red); cen = ((xs2.mean() / w - 0.5) * width_m, (0.5 - ys2.mean() / h) * height_m * depth) if len(xs2) else (0.0, 0.0)
    sprite_red.centroid = cen                        # where the red lies relative to the card's middle (m, x east, y north)
    return mask, width_m * (w + 2 * pad) / w, height_m * depth * (h + 2 * pad) / h, (0.0, 0.0), float(red.sum()) * mx * my


# The one blood look of the remains and the placed splats (23 Nov 2026): the bright red of the 1997 pictures where the blood is thin,
# deep crimson where it is thick. Pass with look='fresh'. The numbers are set by the running game, not by a render: in the sun of
# an outdoor screen the bodies of a pool at sRGB 162, 132 and 100 were all drawn as one clipped poster red (three rounds, seen), while
# the hit-blood sheets of Props/tools/decals.py (thin 148 at the rim only, body 90 mixed with a crust of 74) read as blood. So the
# body sits at 80, the 1997 red is kept for the thin film at every edge, and the thick middle goes to 38.
FRESH_1997 = dict(thin=(128, 10, 7), mid=(80, 5, 4), deep=(38, 2, 2), dried=(66, 10, 7), smear=(92, 8, 6))


def blood_sheet(px, size, seed, pools=(), foot=None, grow=0.10, n_drops=140, reach=0.55, drop_r=(0.004, 0.028), casts=5, mist=500,
                edge_noise=0.2, thin=(60, 5, 4), mid=(40, 2, 2), deep=(17, 1, 1), dried=(44, 12, 8), smear=(54, 10, 7), damp=(40, 27, 21), soak_m=0.06,
                centre=(0.0, 0.0), wet=0.05, stamp=None, keep_fringe=False, meniscus=0.25, look=None, deep_m=0.05):
    """pools = [(cx, cy, a, b, rot, runs)] in metres; foot = (n, 2) points the pool also spreads around (a body's outline), by `grow` metres.
    Drops are thrown out to `reach` metres beyond the pool. Returns dict BC (h, w, 4 uint8), N, ORM (h, w, 3 uint8) and `cover` (float mask)."""
    rng = np.random.default_rng(seed); cv = Canvas(px, size); k = cv.k
    for cx, cy, a, b, rot, runs in pools:
        cv.poly(lobed((cx, cy), a, b, rot, rng, runs=runs))
    if foot is not None:
        for p in foot:
            cv.disc(p, grow * rng.uniform(0.7, 1.25))
    if stamp is not None:                            # the red of the 1997 picture, laid on the ground at its size: (mask image 'L', width m, depth m, centre xy)
        sim, sw, sd, sc = stamp; w_ = max(1, int(round(sw * k))); h_ = max(1, int(round(sd * k))); big = sim.resize((w_, h_), Image.BICUBIC)
        x0 = int(round(px / 2 + sc[0] * k - w_ / 2)); y0 = int(round(px / 2 - sc[1] * k - h_ / 2)); layer = Image.new('L', (px, px), 0); layer.paste(big, (x0, y0))
        from PIL import ImageChops
        cv.im = ImageChops.lighter(cv.im, layer); cv.d = ImageDraw.Draw(cv.im)
    base = blur(cv.arr(), 0.018 * k)
    nz = noise2(px, size / 0.16, rng, 4, 0.55)
    fray = 0.0
    if look == 'fresh':
        # the outline is bent by a few centimetres (no straight side or square corner of a 1997 pixel survives) and wicks into the ground in small tongues
        amp = 0.028 * k; wy = (noise2(px, size / 0.08, rng, 3, 0.6) - 0.5) * 2 * amp; wx = (noise2(px, size / 0.08, rng, 3, 0.6) - 0.5) * 2 * amp
        yy, xx = np.mgrid[0:px, 0:px]
        base = base[np.clip((yy + wy).round().astype(int), 0, px - 1), np.clip((xx + wx).round().astype(int), 0, px - 1)]
        base = blur(base, 0.004 * k)
        fray = 0.16 * (noise2(px, size / 0.022, rng, 3, 0.6) - 0.5)
    pool = sstep(-0.012, 0.012, base - 0.5 - edge_noise * (nz - 0.5) - fray)
    # the mask without the fine noise gives each direction's pool radius for throwing drops
    ys, xs = np.nonzero(base > 0.5)
    if len(xs):
        P = np.stack([(xs - px / 2) / k - centre[0], (px / 2 - ys) / k - centre[1]], 1); ang = np.arctan2(P[:, 1], P[:, 0]); rad = np.hypot(P[:, 0], P[:, 1])
        bins = ((ang + math.pi) / (2 * math.pi) * 90).astype(int) % 90; edge = np.zeros(90)
        np.maximum.at(edge, bins, rad)
        edge = np.maximum(edge, 0.05)
    else:
        edge = np.full(90, 0.02)

    def edge_at(a):
        return float(edge[int((a + math.pi) / (2 * math.pi) * 90) % 90])
    dv = Canvas(px, size)
    for _ in range(n_drops):
        a = rng.uniform(-math.pi, math.pi); u = rng.random() ** 1.7; d = edge_at(a) + 0.01 + reach * u
        r = (drop_r[1] - (drop_r[1] - drop_r[0]) * u ** 0.4) * rng.uniform(0.45, 1.15)
        p = (centre[0] + math.cos(a) * d, centre[1] + math.sin(a) * d)
        drop(dv, p, r, a + rng.normal(0, 0.25), 1.0 + rng.uniform(0.0, 2.4) * u ** 0.5, rng)
    for _ in range(casts):                           # cast-off: a line of drops flung in one direction, shrinking as they go
        a = rng.uniform(-math.pi, math.pi); d0 = edge_at(a) * rng.uniform(0.85, 1.0); n = int(rng.integers(7, 15)); bend = rng.normal(0, 0.25); r = drop_r[1] * rng.uniform(0.5, 0.9)
        for i in range(n):
            t = i / n; d = d0 + reach * 1.25 * t ** 1.3; aa = a + bend * t
            p = (centre[0] + math.cos(aa) * d + rng.normal(0, 0.006), centre[1] + math.sin(aa) * d + rng.normal(0, 0.006))
            drop(dv, p, r * (1 - 0.75 * t) * rng.uniform(0.7, 1.2), aa, 1.3 + 1.8 * t, rng, tail=i % 2 == 0)
    for _ in range(mist):                            # fine mist round the pool
        a = rng.uniform(-math.pi, math.pi); d = edge_at(a) + reach * 0.8 * rng.random() ** 1.3
        dv.disc((centre[0] + math.cos(a) * d, centre[1] + math.sin(a) * d), rng.uniform(0.0012, 0.0035))
    drops = blur(dv.arr(), 0.7)
    cover = np.maximum(pool, sstep(0.35, 0.65, drops))
    e1 = blur(cover, 0.003 * k); e2 = blur(cover, 0.012 * k); dp = blur(pool, 0.05 * k)
    deepf = sstep(0.55, 0.97, dp) * pool
    fine = noise2(px, size / 0.012, rng, 3, 0.6); clotn = noise2(px, size / 0.05, rng, 4, 0.6)
    clot = sstep(0.64, 0.72, clotn) * sstep(0.2, 0.7, deepf)                     # half-dried skin floating on the deep parts
    rim = cover * (1 - sstep(0.55, 0.80, e2))                                     # the thin edge dries first
    # Look, judged in the game (review of PR #103): the middle nearly black, no bright line at the rim (the edge dries
    # brown-red), thrown drops and smears brown-red, and round the pool a fringe of earth the blood has soaked into.
    shallow = pool * (1 - deepf)
    col = _srgb(mid)[None, None, :] * (1 - deepf[..., None]) + _srgb(deep)[None, None, :] * deepf[..., None]
    edgef = shallow * (1 - sstep(0.35, 0.9, e2)); col = col * (1 - 0.5 * edgef[..., None]) + _srgb(thin)[None, None, :] * 0.5 * edgef[..., None]
    col = col * (1 - 0.75 * rim[..., None]) + _srgb(dried)[None, None, :] * 0.75 * rim[..., None]
    col = col * (1 - 0.7 * clot[..., None]) + _srgb((14, 1, 1))[None, None, :] * 0.7 * clot[..., None]
    thrown = cover * (1 - pool)                                                   # drops, cast-off lines, mist: thin, drying
    col = col * (1 - thrown[..., None]) + _srgb(smear)[None, None, :] * thrown[..., None]
    col *= (0.88 + 0.24 * fine)[..., None]
    rough = wet + 0.03 * fine + 0.32 * rim + 0.22 * clot + 0.30 * thrown + 0.06 * (1 - sstep(0.2, 0.8, e2))
    rough = rough + 0.55 * cover * (1 - sstep(0.5, 0.92, e1))      # the very edge is matt: a mirror-smooth meniscus caught the sky as a silver outline
    if look == 'fresh':
        # 23 Nov 2026, judged in the game (PRs #216, #224): one flat bright red read as spilled paint. Blood has depth: a thin film at
        # every edge is the bright red of the 1997 pictures, the body of a pool or a large drop is darker the thicker it lies, the
        # thickest parts are deep crimson with clots; the surface is wet (a domed, smooth core that catches the sun), only the very
        # rim has begun to dry. `thick` 0..1 drives colour, roughness and height together.
        body = sstep(0.70, 0.99, blur(pool, deep_m * k)) * pool
        core = sstep(0.50, 0.95, e1) * cover
        mott = np.clip(0.55 + 0.9 * clotn, 0.0, 1.5)
        thick = np.clip(np.maximum(pool * core * (0.16 + 0.24 * sstep(0.6, 1.0, e2) + 0.60 * body), thrown * 0.55 * sstep(0.70, 1.0, e1)) * mott, 0.0, 1.0)
        lo_ = sstep(0.0, 0.30, thick)[..., None]; hi_ = sstep(0.40, 1.0, thick)[..., None]
        col = _srgb(thin)[None, None, :] * (1 - lo_) + _srgb(mid)[None, None, :] * lo_
        col = col * (1 - hi_) + _srgb(deep)[None, None, :] * hi_
        clot = sstep(0.66, 0.74, clotn) * sstep(0.55, 0.9, thick)
        col = col * (1 - 0.6 * clot[..., None]) + _srgb((16, 1, 1))[None, None, :] * 0.6 * clot[..., None]
        dry = rim * (1 - sstep(0.15, 0.5, thick))
        col = col * (1 - 0.45 * dry[..., None]) + _srgb(dried)[None, None, :] * 0.45 * dry[..., None]
        speck = thrown * (1 - sstep(0.25, 0.7, e1))                                # mist and the finest drops: a stain, not a bead
        col = col * (1 - 0.7 * speck[..., None]) + _srgb(smear)[None, None, :] * 0.7 * speck[..., None]
        col *= (0.86 + 0.28 * fine)[..., None]
        # wet, but not a mirror: at 0.05 a splat seen at a low angle was a pale pink film of sky (game, 23 Nov)
        rough = wet + 0.05 + 0.10 * fine + 0.22 * dry + 0.20 * clot + 0.30 * speck + 0.30 * cover * (1 - sstep(0.5, 0.92, e1))
        deepf = np.maximum(deepf, sstep(0.5, 1.0, thick) * cover)                  # the swell of the height map follows the thickness
        dome = 0.0010 * core * thrown
    else:
        dome = 0.0
    # the soaked fringe: damp earth, darker than the dry ground, ragged, reddish next to the pool
    fz = noise2(px, size / 0.035, rng, 4, 0.6); soak = blur(pool, soak_m * 0.5 * k)
    fringe = sstep(0.06, 0.22, soak + 0.16 * (fz - 0.5)) * (1 - cover)
    if not keep_fringe:                                   # 16 Nov 2026 review: the damp fringe drew a pale grey rim round every pool on planks and dry earth ("a sticker")
        fringe = fringe * 0.0
    near = sstep(0.25, 0.5, soak)
    fcol = _srgb(damp)[None, None, :] * (1 - 0.6 * near[..., None]) + _srgb(dried)[None, None, :] * 0.6 * near[..., None]
    fcol = fcol * (0.8 + 0.4 * fz)[..., None]
    col = col * (1 - fringe[..., None]) + fcol * fringe[..., None]
    rough = rough * (1 - fringe) + (0.50 + 0.25 * (1 - near)) * fringe
    # height in metres: a meniscus at every edge, a swell over the deep parts, clot skin; the open surface is smooth so it mirrors the sky
    h = meniscus * (0.0012 * np.sqrt(np.clip((e1 - 0.5) * 2, 0, 1)) + 0.0016 * sstep(0.5, 1.0, e2)) + 0.0010 * deepf + 0.0005 * clot + 0.00005 * fine + dome
    gy, gx = np.gradient(h * k)                       # slope per metre along rows (down) and columns (right)
    n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    alpha = np.maximum(sstep(0.30, 0.60, cover), sstep(0.35, 0.65, fringe))
    bc = np.dstack([_to_srgb(col), alpha])
    hole = alpha < 0.02                              # colour under the cut-out: damp earth, so mip levels do not fringe red
    bc[hole, :3] = np.asarray(damp, np.float32) / 255.0
    orm = np.dstack([np.ones_like(h), np.clip(rough, 0.04, 1), np.zeros_like(h)])
    u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    return {'BC': u8(bc), 'N': u8(n * 0.5 + 0.5), 'ORM': u8(orm), 'cover': cover}


def scorch_sheet(px, size, seed, r=0.35, spikes=22, spike_len=(0.5, 1.5), aspect=1.0, rot=0.0, centres=None, ash_k=0.18, stamp=None, soft=False, through=False):
    """a burnt hole: a charred, cracked centre whose edge runs out into thin burn tongues, ash-grey flecks and scorched brown inside"""
    rng = np.random.default_rng(seed); cv = Canvas(px, size); k = cv.k
    centres = centres or [(0.0, 0.0, 1.0)]                # picture 158 frame 3 is two holes run together: (x, y, radius factor) each
    if stamp is not None:                            # the 1997 picture's own outline: (mask image 'L', width m, height m, centre xy); no drawn hole, no drawn tongues
        sim, sw, sd, sc = stamp; w_ = max(1, int(round(sw * k))); h_ = max(1, int(round(sd * k))); big = sim.resize((w_, h_), Image.BICUBIC)
        cv.im.paste(big, (int(round(px / 2 + sc[0] * k - w_ / 2)), int(round(px / 2 - sc[1] * k - h_ / 2)))); cv.d = ImageDraw.Draw(cv.im); centres = []; spikes = 0
    for cx_, cy_, rk in centres:
        cv.poly(lobed((cx_, cy_), r * rk * aspect, r * rk, rot, rng, lobes=0.30))
    for i_ in range(spikes * len(centres)):          # burn tongues: thin, jagged, sometimes forked
        cx_, cy_, rk = centres[i_ % len(centres)]; r_ = r * rk
        a = rng.uniform(0, 2 * math.pi); L = r_ * rng.uniform(*spike_len); w = r_ * rng.uniform(0.05, 0.13); p = np.array([cx_, cy_]) + np.array([math.cos(a), math.sin(a)]) * r_ * 0.55; pts_l = []; pts_r = []; n = 7
        for i in range(n + 1):
            t = i / n; a += rng.normal(0, 0.16); p = p + np.array([math.cos(a), math.sin(a)]) * L / n; ww = w * (1 - t) ** 0.8 + 0.002; nx, ny = -math.sin(a), math.cos(a)
            pts_l.append((p[0] + nx * ww, p[1] + ny * ww)); pts_r.append((p[0] - nx * ww, p[1] - ny * ww))
            if i == n // 2 and rng.random() < 0.5:
                b = a + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9); q = p.copy()
                for j in range(4):
                    q2 = q + np.array([math.cos(b), math.sin(b)]) * L * 0.12; cv.d.line([cv.xy(q), cv.xy(q2)], fill=255, width=max(2, int(ww * k * (1.2 - 0.25 * j)))); q = q2
        cv.poly(pts_l + pts_r[::-1])
    for _ in range(60 if centres else 0):            # cinders thrown out
        a = rng.uniform(0, 2 * math.pi); d = r * rng.uniform(1.0, 2.2); cx_, cy_, rk = centres[rng.integers(len(centres))]; cv.disc((cx_ + math.cos(a) * d * rk, cy_ + math.sin(a) * d * rk), rng.uniform(0.004, 0.014))
    base = blur(cv.arr(), 0.004 * k); nz = noise2(px, size / 0.05, rng, 4, 0.6)
    cover = sstep(-0.05, 0.05, base - 0.5 - 0.35 * (nz - 0.5))
    core = sstep(0.5, 0.95, blur(cover, 0.05 * k)); soot = blur(cover, 0.035 * k)            # soot halo round the char
    fine = noise2(px, size / 0.008, rng, 3, 0.6); crack = noise2(px, size / 0.03, rng, 2, 0.5); crack = 1 - sstep(0.0, 0.035, np.abs(crack - 0.5))
    heart = sstep(0.55, 1.0, blur(cover, 0.10 * k))                                         # the middle of each hole: where the picture glows brown-red
    ash = sstep(0.66, 0.74, noise2(px, size / 0.025, rng, 4, 0.6)) * core * ash_k / 0.8; ember = sstep(0.50, 0.66, noise2(px, size / 0.035, rng, 3, 0.6)) * heart
    col = np.broadcast_to(_srgb((14, 12, 11)), (px, px, 3)).copy() * (0.6 + 0.8 * fine[..., None])
    col = col * (1 - 0.8 * ash[..., None]) + _srgb((96, 92, 86))[None, None, :] * 0.8 * ash[..., None]
    col = col * (1 - 0.75 * ember[..., None]) + _srgb((74, 30, 14))[None, None, :] * 0.75 * ember[..., None]
    col *= (1 - 0.7 * crack * core)[..., None]
    alpha = np.maximum(sstep(0.3, 0.6, cover), 0.0)
    halo = sstep(0.12, 0.5, soot) * (0.45 + 0.55 * fine)                                    # dithered soot round the hole (alpha-tested: the noise makes it break up)
    alpha = np.maximum(alpha, sstep(0.42, 0.58, halo))
    if through:                                      # burnt THROUGH (15 Nov 2026): a black void with the charred far wall of the planks showing, as the black of picture 158
        hole = sstep(0.45, 0.62, blur(cover, 0.006 * k)); d_w = int(round(0.055 * k)); d_l = int(round(0.012 * k))
        north = np.roll(hole, d_w, axis=0); north[:d_w] = 0            # the hole moved towards the camera (south, down in the image)
        wall = hole * (1 - sstep(0.3, 0.7, north))                      # inside the hole, within a plank thickness of its far (north) rim: the cut face of the floor
        lipn = np.roll(hole, d_l, axis=0); lipn[:d_l] = 0; lip = hole * (1 - sstep(0.3, 0.7, lipn))       # the top arris of that face catches the light
        grain = noise2(px, size / 0.006, rng, 2, 0.5); grain = blur(np.repeat(grain[:1], px, 0) * 0.6 + grain * 0.4, 0.6)   # split wood: streaks running down the face
        depth = sstep(0.0, 1.0, blur(hole, 0.07 * k)) * hole           # 0 at the rim, 1 in the middle
        void = np.broadcast_to(_srgb((3, 3, 3)), (px, px, 3)).copy()
        void = void + _srgb((30, 9, 5))[None, None, :] * (0.12 * heart * sstep(0.55, 0.7, noise2(px, size / 0.05, rng, 3, 0.6)))[..., None]   # barely a trace of the picture's brown-red heart (16 Nov review: jet black, as 158)
        wcol = _srgb((24, 15, 9))[None, None, :] * (0.45 + 0.9 * grain)[..., None]; wcol = wcol * (1 - 0.6 * sstep(0.2, 0.9, np.roll(depth, -d_w // 2, axis=0)))[..., None]
        wcol = wcol * (1 - lip[..., None]) + _srgb((58, 38, 24))[None, None, :] * lip[..., None] * (0.6 + 0.6 * grain)[..., None]
        inside = void * (1 - wall[..., None]) + wcol * wall[..., None]
        rimc = (1 - hole) * sstep(0.3, 0.6, cover)                      # what is left of the cover outside the void: charred plank tops, cracked, a little ash
        col = col * 0.32                                 # the rim: charred plank, nearly black
        col = col * (1 - hole[..., None]) + inside * hole[..., None]
        h = -0.0015 * crack * rimc + 0.0004 * fine        # no bevel into the void: the bevelled edge caught the light and read as a glossy patch
        gy, gx = np.gradient(h * k); n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
        n = n * (1 - (hole * (1 - wall))[..., None]) + np.array([0, 0, 1.0])[None, None, :] * (hole * (1 - wall))[..., None]
        bc = None; rough_t = np.clip(0.9 + 0.1 * fine + hole, 0, 1)
    if soft:                                         # a deferred decal blends: the soot fades out instead of breaking up into dots
        alpha = np.clip(np.maximum(sstep(0.3, 0.6, cover), 0.8 * sstep(0.03, 0.55, soot) * (0.6 + 0.4 * fine)), 0, 1)
    if not through:
        h = -0.004 * core + 0.0015 * ash - 0.002 * crack * core + 0.0006 * fine
        gy, gx = np.gradient(h * k); n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    bc = np.dstack([_to_srgb(col), alpha]); bc[alpha < 0.02, :3] = np.asarray((14, 12, 11), np.float32) / 255.0
    orm = np.dstack([1 - 0.5 * core * crack, rough_t if through else 0.82 + 0.15 * fine, np.zeros_like(h)])
    u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    return {'BC': u8(bc), 'N': u8(n * 0.5 + 0.5), 'ORM': u8(orm), 'cover': cover}


def _voronoi(px, ny, nx, rng, jitter=0.9):
    """a jittered-grid Voronoi over the sheet: (f1, f2 - f1, random value per cell, cell row, cell column), ny x nx cells"""
    pts = np.stack(np.meshgrid(np.arange(ny), np.arange(nx), indexing='ij'), -1) + 0.5 + (rng.random((ny, nx, 2)) - 0.5) * jitter; val = rng.random((ny, nx)).astype(np.float32)
    y, x = np.mgrid[0:px, 0:px].astype(np.float32); y *= ny / px; x *= nx / px; ci = np.floor(y).astype(int); cj = np.floor(x).astype(int)
    f1 = np.full((px, px), 9.0, np.float32); f2 = f1.copy(); bi = ci.copy(); bj = cj.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ii = np.clip(ci + di, 0, ny - 1); jj = np.clip(cj + dj, 0, nx - 1); p = pts[ii, jj]; d = np.hypot(p[..., 0] - y, p[..., 1] - x).astype(np.float32); closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d)); bi = np.where(closer, ii, bi); bj = np.where(closer, jj, bj); f1 = np.where(closer, d, f1)
    return f1, f2 - f1, val[bi, bj], bi, bj, pts


def pit_sheet(px, size, seed, r=0.27, spikes=20, spike_len=(0.5, 1.5), aspect=1.0, rot=0.0, centres=None, wall=False, plume=0.0):
    """A hole burnt THROUGH planks (picture 158), for the `pit` material of the kit importer (16 Nov 2026 rebuild).

    The flat sheet carries what a hole in a floor is made of, and the importer's pit shader gives it its depth:
      BC rgb   outside the void: charred wood broken into blocks (alligator char), pale ash in the cracks and round the rim,
               brown scorch fading into the floor; inside the void: what lies below the floor (black, a few dull embers)
      BC a     cover, 0..1: 1 on the char, falling off through the scorch (the shader dithers it, so the scorch fades out)
      ORM r/g  occlusion (cracks, the rim) and roughness; ORM b is NOT metallic here: it is the void mask the shader reads
               (1 = burnt through). The shader draws the far wall of the hole (the cut face of the planks) by parallax,
               shades the void without any specular (a lit black sheet is grey: that was the 'tar' of the first version)
    `wall` = burnt through a plastered wall: the same hole with a soot plume of `plume` metres rising above it (image up)."""
    rng = np.random.default_rng(seed); cv = Canvas(px, size); k = cv.k; vc = Canvas(px, size)
    centres = centres or [(0.0, 0.0, 1.0)]
    for cx_, cy_, rk in centres:                      # the void: lobed, as the body of the 1997 blotch
        pts_ = lobed((cx_, cy_), r * rk * aspect, r * rk, rot, rng, lobes=0.30); cv.poly(pts_); vc.poly(pts_)
    for i_ in range(spikes * len(centres)):           # burn tongues: charred grooves running out, the spikes of the 1997 picture
        cx_, cy_, rk = centres[i_ % len(centres)]; r_ = r * rk
        a = rng.uniform(0, 2 * math.pi); Ln = r_ * rng.uniform(*spike_len); w = r_ * rng.uniform(0.07, 0.16); p = np.array([cx_, cy_]) + np.array([math.cos(a), math.sin(a)]) * r_ * 0.55; pl = []; pr = []; n = 7
        for i in range(n + 1):
            t = i / n; a += rng.normal(0, 0.16); p = p + np.array([math.cos(a), math.sin(a)]) * Ln / n; ww = w * (1 - t) ** 0.8 + 0.003; nx_, ny_ = -math.sin(a), math.cos(a)
            pl.append((p[0] + nx_ * ww, p[1] + ny_ * ww)); pr.append((p[0] - nx_ * ww, p[1] - ny_ * ww))
        cv.poly(pl + pr[::-1])
    for _ in range(70):                               # cinders thrown out
        a = rng.uniform(0, 2 * math.pi); d = r * rng.uniform(1.0, 2.3); cx_, cy_, rk = centres[rng.integers(len(centres))]; cv.disc((cx_ + math.cos(a) * d * rk, cy_ + math.sin(a) * d * rk), rng.uniform(0.004, 0.012))
    nz = noise2(px, size / 0.05, rng, 4, 0.6); fine = noise2(px, size / 0.008, rng, 3, 0.6); med = noise2(px, size / 0.02, rng, 3, 0.6)
    cover = sstep(-0.05, 0.05, blur(cv.arr(), 0.004 * k) - 0.5 - 0.35 * (nz - 0.5))            # all that is char: void, rim and tongues
    # ---- alligator char: blocks longer along the grain (image up/down), broken by deep cracks
    ny = max(4, int(round(size / 0.021))); nx = max(4, int(round(size / 0.013))); f1, edge, cval, bi, bj, pts = _voronoi(px, ny, nx, rng)
    crack = 1 - sstep(0.02, 0.16, edge)                                                       # 1 in the crack between two blocks
    # ---- the void: whole blocks have fallen in, so its outline runs along the cracks; a block goes when its middle lies well inside the lobes
    vsoft = blur(vc.arr(), 0.014 * k) - 0.20 * (noise2(px, size / 0.07, rng, 3, 0.6) - 0.5) - 0.25 * (noise2(px, size / 0.018, rng, 2, 0.5) - 0.5)
    cy_px = np.clip((pts[..., 0] * px / ny).astype(int), 0, px - 1); cx_px = np.clip((pts[..., 1] * px / nx).astype(int), 0, px - 1); gone = vsoft[cy_px, cx_px] > 0.62
    void = blur(gone[bi, bj].astype(np.float32), 0.0012 * k); void = sstep(0.42, 0.58, void)
    near = sstep(0.0, 1.0, blur(void, 0.022 * k) * 2.2) * (1 - void)                           # the rim: within a few centimetres of the void
    char = cover * (1 - void)
    # ---- colours
    blockc = (0.007 + 0.016 * cval ** 2 + 0.005 * fine)[..., None] * np.array([1.0, 0.92, 0.84], np.float32)[None, None, :]        # charcoal: nearly black, a little brown
    blockc = blockc * (1 - 0.92 * crack[..., None])
    ashn = noise2(px, size / 0.035, rng, 4, 0.6); ash = sstep(0.60, 0.74, ashn + 0.20 * near - 0.06) * char * (0.28 + 0.4 * fine)            # pale ash lying on the char, most round the rim
    ash = np.maximum(ash, 0.45 * crack * char * sstep(0.56, 0.7, noise2(px, size / 0.06, rng, 3, 0.6)))                                  # and blown into some of the cracks
    ashc = _srgb((104, 100, 94))[None, None, :] * (0.40 + 0.6 * med)[..., None]
    col = blockc * (1 - ash[..., None]) + ashc * ash[..., None]
    soot_d = blur(cover, 0.06 * k); soot = sstep(0.03, 0.50, soot_d) * (0.55 + 0.45 * med) * (0.75 + 0.25 * fine)                              # scorch: brown-black, fading into the boards
    if wall and plume > 0:                            # soot climbs a wall: the scorch is drawn out upwards (image up = up the wall), widening and thinning
        up = np.zeros_like(cover); n_ = 28; step = plume * k / n_
        for i in range(1, n_ + 1):
            sh = np.roll(blur(cover, (0.03 + 0.10 * i / n_) * k), -int(round(i * step)), axis=0); sh[-int(round(i * step)) - 1:] = 0; up = np.maximum(up, sh * (1 - i / (n_ + 1)) ** 1.3)
        soot = np.maximum(soot, sstep(0.03, 0.6, up) * (0.45 + 0.55 * noise2(px, size / 0.09, rng, 4, 0.6)) * (0.8 + 0.2 * fine))
    scorch_c = _srgb((30, 17, 9))[None, None, :] * (0.5 + 0.7 * med)[..., None]
    col = col * char[..., None] + scorch_c * (1 - char[..., None])
    # ---- below the floor: black, with a few dull embers and fallen ash in the middle (the brown-red heart of the 1997 picture)
    heart = sstep(0.5, 1.0, blur(void, 0.07 * k)); emb = sstep(0.66, 0.80, noise2(px, size / 0.03, rng, 3, 0.6)) * heart
    below = np.broadcast_to(_srgb((2, 2, 2)), (px, px, 3)).copy() * (0.5 + fine)[..., None]
    below = below * (1 - emb[..., None]) + (_srgb((40, 13, 5))[None, None, :] * (0.15 + 0.6 * med)[..., None]) * emb[..., None]
    below = below + _srgb((40, 37, 33))[None, None, :] * (0.25 * heart * sstep(0.74, 0.86, noise2(px, size / 0.012, rng, 2, 0.5)))[..., None]
    col = col * (1 - void[..., None]) + below * void[..., None]
    alpha = np.clip(np.maximum(np.maximum(sstep(0.3, 0.6, cover), void), 0.92 * soot), 0, 1)
    # ---- relief: blocks stand proud of their cracks, the rim is burnt thin and dips to the void, ash lies in low drifts
    h = 0.0022 * sstep(0.02, 0.30, edge) * char * (0.7 + 0.6 * cval) - 0.0030 * near * char + 0.0009 * ash + 0.0003 * fine * (1 - void)
    gy, gx = np.gradient(blur(h, 0.6) * k); n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    n = n * (1 - void[..., None]) + np.array([0, 0, 1.0], np.float32)[None, None, :] * void[..., None]
    occ = np.clip(1 - 0.75 * crack * char - 0.35 * near - void, 0, 1)
    rough = np.clip(0.88 + 0.10 * cval + 0.25 * ash + 0.3 * crack + (1 - char) * 0.2 + void, 0, 1)        # matt: glossy char read as grey scales in the sun
    bc = np.dstack([_to_srgb(col), alpha]); bc[alpha < 0.004, :3] = np.asarray((30, 17, 9), np.float32) / 255.0
    orm = np.dstack([occ, rough, void]); u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    return {'BC': u8(bc), 'N': u8(n * 0.5 + 0.5), 'ORM': u8(orm), 'cover': cover, 'void': void, 'char': char, 'near': near, 'ash': ash}


def save(sheet, stem):
    """write <stem>_BC.png (RGBA), _N.png, _ORM.png; returns {role: path}"""
    out = {}
    for role, mode in (('BC', 'RGBA'), ('N', 'RGB'), ('ORM', 'RGB')):
        p = '%s_%s.png' % (stem, role); Image.fromarray(sheet[role], mode).save(p, optimize=True); out[role] = p
    return out


def preview(sheets, path, cell=700, ground=(92, 118, 60)):
    """quick look: each sheet lit from the upper left over a flat ground colour"""
    ims = []
    for s in sheets:
        bc = s['BC'].astype(np.float32) / 255.0; n = s['N'].astype(np.float32) / 255.0 * 2 - 1; r = s['ORM'][..., 1].astype(np.float32) / 255.0
        Ld = np.array([-0.45, 0.45, 0.77]); Ld /= np.linalg.norm(Ld); Hh = Ld + np.array([0, -0.5, 0.86]); Hh /= np.linalg.norm(Hh)
        dif = np.clip(n @ Ld, 0, 1)[..., None]; spec = (np.clip(n @ Hh, 0, 1) ** (2.0 / np.maximum(r, 0.03) ** 2))[..., None] * 0.9
        lit = bc[..., :3] * (0.35 + 0.8 * dif) + spec; g = np.asarray(ground, np.float32) / 255.0
        a = (bc[..., 3:] > 0.33).astype(np.float32); out = lit * a + g[None, None, :] * (1 - a)
        ims.append(Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).resize((cell, cell), Image.LANCZOS))
    sh = Image.new('RGB', (cell * len(ims), cell))
    for i, im in enumerate(ims):
        sh.paste(im, (i * cell, 0))
    sh.save(path)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'preview':
        a = blood_sheet(1024, 2.6, 275, pools=[(0, 0, 0.95, 0.55, 0.3, [(0.4, 0.3, 0.3), (3.4, 0.2, 0.25)])])
        b = blood_sheet(1024, 1.2, 188, pools=[(0, 0, 0.16, 0.10, 0.5, [])], n_drops=160, reach=0.42, casts=6, mist=300)
        c = scorch_sheet(1024, 1.6, 158)
        preview([a, b, c], sys.argv[2])
