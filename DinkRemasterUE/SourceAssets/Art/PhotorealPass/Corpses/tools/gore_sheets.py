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


def blood_sheet(px, size, seed, pools=(), foot=None, grow=0.10, n_drops=140, reach=0.55, drop_r=(0.004, 0.028), casts=5, mist=500,
                edge_noise=0.2, thin=(60, 5, 4), mid=(40, 2, 2), deep=(17, 1, 1), dried=(44, 12, 8), smear=(54, 10, 7), damp=(40, 27, 21), soak_m=0.06,
                centre=(0.0, 0.0), wet=0.05):
    """pools = [(cx, cy, a, b, rot, runs)] in metres; foot = (n, 2) points the pool also spreads around (a body's outline), by `grow` metres.
    Drops are thrown out to `reach` metres beyond the pool. Returns dict BC (h, w, 4 uint8), N, ORM (h, w, 3 uint8) and `cover` (float mask)."""
    rng = np.random.default_rng(seed); cv = Canvas(px, size); k = cv.k
    for cx, cy, a, b, rot, runs in pools:
        cv.poly(lobed((cx, cy), a, b, rot, rng, runs=runs))
    if foot is not None:
        for p in foot:
            cv.disc(p, grow * rng.uniform(0.7, 1.25))
    base = blur(cv.arr(), 0.018 * k)
    nz = noise2(px, size / 0.16, rng, 4, 0.55)
    pool = sstep(-0.012, 0.012, base - 0.5 - edge_noise * (nz - 0.5))
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
    # the soaked fringe: damp earth, darker than the dry ground, ragged, reddish next to the pool
    fz = noise2(px, size / 0.035, rng, 4, 0.6); soak = blur(pool, soak_m * 0.5 * k)
    fringe = sstep(0.06, 0.22, soak + 0.16 * (fz - 0.5)) * (1 - cover)
    near = sstep(0.25, 0.5, soak)
    fcol = _srgb(damp)[None, None, :] * (1 - 0.6 * near[..., None]) + _srgb(dried)[None, None, :] * 0.6 * near[..., None]
    fcol = fcol * (0.8 + 0.4 * fz)[..., None]
    col = col * (1 - fringe[..., None]) + fcol * fringe[..., None]
    rough = rough * (1 - fringe) + (0.50 + 0.25 * (1 - near)) * fringe
    # height in metres: a meniscus at every edge, a swell over the deep parts, clot skin; the open surface is smooth so it mirrors the sky
    h = 0.0012 * np.sqrt(np.clip((e1 - 0.5) * 2, 0, 1)) + 0.0016 * sstep(0.5, 1.0, e2) + 0.0010 * deepf + 0.0005 * clot + 0.00005 * fine
    gy, gx = np.gradient(h * k)                       # slope per metre along rows (down) and columns (right)
    n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    alpha = np.maximum(sstep(0.30, 0.60, cover), sstep(0.35, 0.65, fringe))
    bc = np.dstack([_to_srgb(col), alpha])
    hole = alpha < 0.02                              # colour under the cut-out: damp earth, so mip levels do not fringe red
    bc[hole, :3] = np.asarray(damp, np.float32) / 255.0
    orm = np.dstack([np.ones_like(h), np.clip(rough, 0.04, 1), np.zeros_like(h)])
    u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    return {'BC': u8(bc), 'N': u8(n * 0.5 + 0.5), 'ORM': u8(orm), 'cover': cover}


def scorch_sheet(px, size, seed, r=0.35, spikes=22, spike_len=(0.5, 1.5), aspect=1.0, rot=0.0):
    """a burnt hole: a charred, cracked centre whose edge runs out into thin burn tongues, ash-grey flecks and scorched brown inside"""
    rng = np.random.default_rng(seed); cv = Canvas(px, size); k = cv.k
    cv.poly(lobed((0, 0), r * aspect, r, rot, rng, lobes=0.30))
    for _ in range(spikes):                          # burn tongues: thin, jagged, sometimes forked
        a = rng.uniform(0, 2 * math.pi); L = r * rng.uniform(*spike_len); w = r * rng.uniform(0.05, 0.13); p = np.array([math.cos(a), math.sin(a)]) * r * 0.55; pts_l = []; pts_r = []; n = 7
        for i in range(n + 1):
            t = i / n; a += rng.normal(0, 0.16); p = p + np.array([math.cos(a), math.sin(a)]) * L / n; ww = w * (1 - t) ** 0.8 + 0.002; nx, ny = -math.sin(a), math.cos(a)
            pts_l.append((p[0] + nx * ww, p[1] + ny * ww)); pts_r.append((p[0] - nx * ww, p[1] - ny * ww))
            if i == n // 2 and rng.random() < 0.5:
                b = a + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9); q = p.copy()
                for j in range(4):
                    q2 = q + np.array([math.cos(b), math.sin(b)]) * L * 0.12; cv.d.line([cv.xy(q), cv.xy(q2)], fill=255, width=max(2, int(ww * k * (1.2 - 0.25 * j)))); q = q2
        cv.poly(pts_l + pts_r[::-1])
    for _ in range(60):                              # cinders thrown out
        a = rng.uniform(0, 2 * math.pi); d = r * rng.uniform(1.0, 2.2); cv.disc((math.cos(a) * d, math.sin(a) * d), rng.uniform(0.004, 0.014))
    base = blur(cv.arr(), 0.004 * k); nz = noise2(px, size / 0.05, rng, 4, 0.6)
    cover = sstep(-0.05, 0.05, base - 0.5 - 0.35 * (nz - 0.5))
    core = sstep(0.5, 0.95, blur(cover, 0.05 * k)); soot = blur(cover, 0.035 * k)            # soot halo round the char
    fine = noise2(px, size / 0.008, rng, 3, 0.6); crack = noise2(px, size / 0.03, rng, 2, 0.5); crack = 1 - sstep(0.0, 0.035, np.abs(crack - 0.5))
    ash = sstep(0.62, 0.72, noise2(px, size / 0.04, rng, 4, 0.6)) * core; ember = sstep(0.66, 0.74, noise2(px, size / 0.06, rng, 3, 0.6)) * core
    col = np.broadcast_to(_srgb((14, 12, 11)), (px, px, 3)).copy() * (0.6 + 0.8 * fine[..., None])
    col = col * (1 - 0.8 * ash[..., None]) + _srgb((96, 92, 86))[None, None, :] * 0.8 * ash[..., None]
    col = col * (1 - 0.75 * ember[..., None]) + _srgb((92, 44, 18))[None, None, :] * 0.75 * ember[..., None]
    col *= (1 - 0.7 * crack * core)[..., None]
    alpha = np.maximum(sstep(0.3, 0.6, cover), 0.0)
    halo = sstep(0.12, 0.5, soot) * (0.45 + 0.55 * fine)                                    # dithered soot round the hole (alpha-tested: the noise makes it break up)
    alpha = np.maximum(alpha, sstep(0.42, 0.58, halo))
    h = -0.004 * core + 0.0015 * ash - 0.002 * crack * core + 0.0006 * fine
    gy, gx = np.gradient(h * k); n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    bc = np.dstack([_to_srgb(col), alpha]); bc[alpha < 0.02, :3] = np.asarray((14, 12, 11), np.float32) / 255.0
    orm = np.dstack([1 - 0.5 * core * crack, 0.82 + 0.15 * fine, np.zeros_like(h)])
    u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    return {'BC': u8(bc), 'N': u8(n * 0.5 + 0.5), 'ORM': u8(orm), 'cover': cover}


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
