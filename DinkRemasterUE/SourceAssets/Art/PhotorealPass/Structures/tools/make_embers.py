"""The ember set of the burning cottage (screen 439, vision 1; picture 154 shows the room under the roof hole glowing): charred wood
broken into blocks, the cracks between them and patches of whole blocks alight. Numpy and PIL only, tileable, no scan:

    python3 -I make_embers.py        (writes ../Stonebrook/Textures/T_Stonebrook_Embers_{BC,N,ORM,E}.png)

BC sRGB (char black, grey ash on the cold blocks, dull red under the glow), N OpenGL, ORM (R occlusion in the cracks, G roughness, B 0),
E sRGB: what glows (orange in the cracks, dull red over the hot blocks). The kit importer multiplies E by the row's emissive_nits."""
import os
import numpy as np
from PIL import Image
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Stonebrook', 'Textures'); PX = 1024


def tile_noise(px, cells, rng, octaves=4, gain=0.55):
    out = np.zeros((px, px), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        n = cells * 2 ** o; g = rng.random((n, n)).astype(np.float32); g = np.pad(g, ((0, 1), (0, 1)), mode='wrap')
        y = np.arange(px) * n / px; x = y; yi = y.astype(int); xi = x.astype(int); fy = (y - yi)[:, None]; fx = (x - xi)[None, :]
        fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
        a = g[yi][:, xi]; b = g[yi][:, xi + 1]; c = g[yi + 1][:, xi]; d = g[yi + 1][:, xi + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy); tot += amp; amp *= gain
    return out / tot


def tile_voronoi(px, n, rng, jitter=0.85, stretch=1.0):
    """F1, F2 - F1 (0 on the cell borders) and the cell id of a wrapped, jittered grid of n x n points"""
    pts = (np.stack(np.meshgrid(np.arange(n), np.arange(n), indexing='ij'), -1) + 0.5 + (rng.random((n, n, 2)) - 0.5) * jitter).reshape(-1, 2) / n
    yy, xx = np.mgrid[0:px, 0:px].astype(np.float32) / px; f1 = np.full((px, px), 9.0, np.float32); f2 = f1.copy(); ident = np.zeros((px, px), np.int32)
    for k, (py, px_) in enumerate(pts):
        dy = np.abs(yy - py); dy = np.minimum(dy, 1 - dy) * stretch; dx = np.abs(xx - px_); dx = np.minimum(dx, 1 - dx); d = np.hypot(dx, dy)
        near = d < f1; f2 = np.where(near, f1, np.minimum(f2, d)); ident = np.where(near, k, ident); f1 = np.where(near, d, f1)
    return f1 * n, (f2 - f1) * n, ident


def srgb(c):
    c = np.asarray(c, np.float32) / 255.0; return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def main():
    rng = np.random.default_rng(439154); os.makedirs(OUT, exist_ok=True)
    f1, edge, ident = tile_voronoi(PX, 14, rng, stretch=0.62)              # blocks of char, longer along the grain (image x)
    _, edge2, _ = tile_voronoi(PX, 34, rng)                                # the fine checking inside a block
    big = tile_noise(PX, 3, rng, 3); mid = tile_noise(PX, 9, rng, 3); fine = tile_noise(PX, 64, rng, 3)
    heat_cell = rng.random(14 * 14)[ident]                                 # every block has its own heat
    hot = np.clip((0.50 * heat_cell + 0.85 * big - 0.60) / 0.22, 0, 1)     # which blocks are alight: in patches
    crack = np.clip(1 - edge / (0.085 + 0.07 * mid), 0, 1) ** 1.6           # the gaps between the blocks
    check = np.clip(1 - edge2 / 0.10, 0, 1) ** 2 * 0.55
    glow_crack = np.clip(crack * (0.10 + 1.2 * np.clip(big * 2.0 - 0.55, 0, 1)) + check * hot * (0.3 + 0.7 * mid), 0, 1)
    face = hot * np.clip(1 - crack, 0, 1) * np.clip(0.10 + 1.5 * (mid - 0.3), 0, 1) * (0.5 + 0.5 * fine) * (0.55 + 0.45 * np.clip(1 - edge / 0.5, 0, 1))           # a hot block glows dull red over its whole face, brightest at its edges
    e = srgb((255, 132, 26))[None, None, :] * (glow_crack ** 1.2)[..., None] + srgb((214, 38, 8))[None, None, :] * (0.55 * face)[..., None]
    e += srgb((255, 214, 120))[None, None, :] * (np.clip(glow_crack - 0.72, 0, 1) * 2.6)[..., None]          # the hottest cracks go yellow
    ash = np.clip((mid - 0.52) / 0.14, 0, 1) * (1 - hot) * np.clip(1 - crack * 1.5, 0, 1)
    bc = srgb((22, 20, 19))[None, None, :] * (0.7 + 0.6 * fine)[..., None]
    bc = bc * (1 - 0.55 * ash[..., None]) + srgb((118, 112, 104))[None, None, :] * 0.55 * ash[..., None]
    bc = bc * (1 - 0.45 * hot[..., None]) + srgb((58, 14, 8))[None, None, :] * 0.45 * hot[..., None]
    bc = bc * (1 - 0.8 * crack[..., None])
    h = 0.012 * np.clip(edge / 0.25, 0, 1) ** 0.6 - 0.004 * check + 0.0015 * fine      # metres over a tile of about a metre
    gy, gx = np.gradient(h * PX); n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    orm = np.dstack([np.clip(1 - 0.7 * crack, 0, 1), np.clip(0.86 + 0.1 * fine + 0.06 * ash, 0, 1), np.zeros_like(h)])
    u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    for role, im in (('BC', u8(to_srgb(bc))), ('N', u8(n * 0.5 + 0.5)), ('ORM', u8(orm)), ('E', u8(to_srgb(e)))):
        Image.fromarray(im, 'RGB').save(os.path.join(OUT, 'T_Stonebrook_Embers_%s.png' % role), optimize=True)
    print('embers: glowing share %.2f, mean E (linear) %s' % (float((e.max(2) > 0.05).mean()), np.round(e.mean((0, 1)), 3)))


if __name__ == '__main__':
    main()
