"""Smouldering burn patches (155-157 struct/details/damage/fire2-..fire4-): the charred, glowing marks the fire has eaten
into the walls and the roof of the burning house. A flipbook per patch, made by code (numpy + PIL, no Blender): cracked
charcoal with a ragged edge and thin burnt runs, embers that breathe in the cracks, a few small flames from the
simulated fire (the frame cache of Fire_Wall) and a wisp of smoke.

    blender -b --factory-startup -t 4 --python FableF/tools/build_fire_fx.py -- Fire_Wall --cache <cache> --stage compact
    python3 -I FableF/tools/build_burn_patch.py <cache>/compact_256.npy [Embers_A ...]
"""
import json, math, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fire_encode as FE

KIT = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'
PX, GRID, FPS = 256, (8, 4), 14
SETS = {
    'Embers_A': dict(seq='155 struct/details/damage/fire2-', seed=155, radius=0.50, runs=7, cells=70, flames=[(-0.10, 0.34, 0.0)], size_m=0.6,
                     dresses='a burn patch 0.45 m across: charred, cracked wood with embers in the cracks and one small flame'),
    'Embers_B': dict(seq='156 struct/details/damage/fire3-', seed=156, radius=0.52, runs=8, cells=80, flames=[(0.12, 0.30, 0.3), (-0.22, 0.24, 0.6)], size_m=0.6,
                     dresses='a burn patch 0.45 m across, hotter at its middle, two small flames'),
    'Embers_C': dict(seq='157 struct/details/damage/fire4-', seed=157, radius=0.56, runs=10, cells=120, flames=[(-0.18, 0.40, 0.1), (0.20, 0.34, 0.5), (0.02, 0.26, 0.8)], size_m=1.1,
                     dresses='a burn patch 0.85 m across: a wide charred mark with a glowing bed and three small flames'),
}
CX, CY = 0.0, 0.26          # the patch's middle in frame units (-1..1, y down): low in the frame, the flames above it


def patch_static(S):
    rng = np.random.default_rng(S['seed'])
    y, x = np.mgrid[0:PX, 0:PX].astype(np.float32)
    u = x / (PX - 1) * 2 - 1 - CX
    v = y / (PX - 1) * 2 - 1 - CY
    r = np.sqrt(u * u + v * v)
    th = np.arctan2(v, u)
    # ragged outline: a few harmonics of the angle
    edge = np.ones_like(r) * S['radius']
    for k in range(2, 9):
        edge *= 1.0 + rng.uniform(0.03, 0.11) * np.sin(k * th + rng.uniform(0, 6.28))
    body = np.clip((edge - r) / 0.07, 0, 1)
    # thin burnt runs out of the patch (the legs of the 1997 mark)
    runs = np.zeros_like(r)
    for _ in range(S['runs']):
        a = rng.uniform(0, 6.28); ln = rng.uniform(1.25, 1.75) * S['radius']; w = rng.uniform(0.018, 0.04)
        bend = rng.uniform(-0.5, 0.5)
        d_ang = np.angle(np.exp(1j * (th - a - bend * (r - S['radius']))))
        across = np.abs(d_ang) * r
        along = np.clip((ln - r) / (ln - S['radius'] * 0.6), 0, 1)
        runs = np.maximum(runs, np.clip(1.0 - across / (w * (0.4 + along)), 0, 1) * (r > S['radius'] * 0.5) * (along > 0) * along ** 0.5)
    char = np.clip(np.maximum(body, runs), 0, 1)
    soot = np.clip((edge * 1.55 - r) / (edge * 0.7), 0, 1) ** 2 * 0.55
    # alligator char: Voronoi cells, cracks where two cells meet
    n = S['cells']
    pts = np.stack([rng.uniform(-1, 1, n) * S['radius'] * 1.3, rng.uniform(-1, 1, n) * S['radius'] * 1.3], -1)
    d = np.sqrt((u[..., None] - pts[:, 0]) ** 2 + (v[..., None] - pts[:, 1]) ** 2)
    idx = np.argsort(d, -1)[..., :2]
    f1 = np.take_along_axis(d, idx[..., :1], -1)[..., 0]
    f2 = np.take_along_axis(d, idx[..., 1:2], -1)[..., 0]
    crack = np.clip(1.0 - (f2 - f1) / 0.035, 0, 1)                 # 1 in a crack
    cell = idx[..., 0]
    tone = rng.uniform(0.55, 1.35, n)[cell]
    phase = rng.uniform(0, 6.28, n)[cell]
    fine = FE.periodic_fbm(1, PX, PX, rng, octaves=4, cx=24, cy=24, ct=1)[0]
    veins = FE.periodic_fbm(1, PX, PX, rng, octaves=3, cx=7, cy=7, ct=1)[0]          # which cracks are alight
    heat = np.clip(1.0 - r / (edge * 0.92), 0, 1) ** 0.8             # hot in the middle, cold at the rim
    return dict(veins=veins, u=u, v=v, r=r, char=char, soot=soot, crack=crack, tone=tone, phase=phase, fine=fine, heat=heat, body=body)


def ramp(h):
    """ember colour by heat 0..1: dull red, orange, yellow"""
    h = np.clip(h, 0, 1)[..., None]
    c0, c1, c2 = np.array((0.30, 0.012, 0.0)), np.array((1.0, 0.24, 0.02)), np.array((1.0, 0.72, 0.22))
    return np.where(h < 0.5, c0 + (c1 - c0) * (h * 2), c1 + (c2 - c1) * (h * 2 - 1)).astype(np.float32)


def build(name, fire_hdr):
    S = SETS[name]
    T = patch_static(S)
    n = GRID[0] * GRID[1]
    rng = np.random.default_rng(S['seed'] + 1000)
    breath = FE.periodic_fbm(n, PX // 4, PX // 4, rng, octaves=3, cx=5, cy=5, ct=3, wraps=0)
    # the small flames: the compact fire, every second frame, scaled down and set on the patch
    step = len(fire_hdr) // n
    small = []
    for i in range(n):
        acc = np.zeros((PX, PX, 3), np.float32)
        for (fx, size, shift) in S['flames']:
            f = fire_hdr[(i * step + int(shift * len(fire_hdr))) % len(fire_hdr)]
            w = int(PX * size)
            im = np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(f[..., c]), 'F').resize((w, w), Image.BILINEAR), np.float32) for c in range(3)], -1)
            # no straight foot: the flame grows out of the char, strongest a little above its base, and is narrow
            up = np.linspace(1.0, 0.0, w, dtype=np.float32)[:, None, None]           # 1 at the top row
            across = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :, None]
            im = im * np.clip((1.0 - up) / 0.30, 0, 1) ** 0.0 * np.clip(up / 0.16, 0, 1) ** 1.4 * np.clip(1.0 - (np.abs(across) / 0.62) ** 2, 0, 1)
            x0 = int((fx + CX + 1) / 2 * PX - w / 2); y1 = int((CY + 1) / 2 * PX + 0.10 * PX); y0 = y1 - w
            xs0, ys0 = max(0, -x0), max(0, -y0)
            xe, ye = min(PX, x0 + w), min(PX, y1)
            if xe > x0 + xs0 and ye > y0 + ys0:
                acc[y0 + ys0:ye, x0 + xs0:xe] += im[ys0:ye - y0, xs0:xe - x0] * 0.55
        small.append(acc)
    look = dict(FE.DEFAULT, smoke_max=0.30, smoke_density=2.6, rise_px=110.0, sigma0=2.0, sigma1=9.0, sway_px=8.0, wind_px=5.0, sparks=3, seed=S['seed'])
    flames = FE.encode_loop(small, look)
    out = []
    lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    for i in range(n):
        b = np.asarray(Image.fromarray(breath[i], 'F').resize((PX, PX), Image.BICUBIC), np.float32)
        pulse = 0.55 + 0.45 * np.sin(2 * math.pi * i / n + T['phase'])          # each cell breathes at its own phase
        alight = np.clip((T['veins'] - 0.40 + 0.25 * T['heat']) * 4.0, 0, 1)
        glow_crack = T['crack'] ** 1.5 * T['heat'] ** 0.7 * (0.35 + 0.9 * np.clip((b - 0.3) * 2.2, 0, 1)) * T['body'] * alight
        coal = np.clip((T['heat'] - 0.45) * 2.4, 0, 1) * np.clip((T['tone'] - 0.95) * 4, 0, 1) * (0.25 + 0.75 * pulse) * (1 - T['crack']) * 0.8
        hot = np.clip(glow_crack * 1.25 + coal, 0, 1)
        charcol = (np.array((0.022, 0.019, 0.017), np.float32)[None, None, :] * (T['tone'] * (0.75 + 0.6 * T['fine']))[..., None]
                   + np.array((0.10, 0.09, 0.085), np.float32)[None, None, :] * (np.clip((T['fine'] - 0.62) * 5, 0, 1) * (1 - T['heat']) * 0.6)[..., None])     # ash on the cold rim
        charcol = charcol * (1.0 - 0.75 * T['crack'][..., None] ** 2)
        rgb = charcol * (1 - hot[..., None]) + ramp(hot * (0.55 + 0.45 * T['heat'])) * hot[..., None]
        a = np.clip(T['char'] * 0.97 + T['soot'] * (1 - T['char']), 0, 1)
        rgb = np.where(T['char'][..., None] > 0.02, rgb, np.array((0.012, 0.010, 0.009), np.float32))
        # flames and smoke over the patch
        f = flames[i]
        fa = f[..., 3:4]
        pr = lin(f[..., :3]) * fa + rgb * a[..., None] * (1 - fa)
        aa = fa[..., 0] + a * (1 - fa[..., 0])
        out.append(np.concatenate([FE.srgb(pr / np.maximum(aa, 1e-4)[..., None]), aa[..., None]], -1).astype(np.float32))
    return out


def save(name, frames):
    S = SETS[name]
    folder = os.path.join(KIT, 'small_fire_fx', name)
    os.makedirs(folder, exist_ok=True)
    atlas = np.zeros((GRID[1] * PX, GRID[0] * PX, 4), np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, GRID[0])
        atlas[r * PX:(r + 1) * PX, c * PX:(c + 1) * PX] = f
    Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(folder, 'T_FX_%s_Flipbook.png' % name), optimize=True)
    glow, hot = 2.6, (0.35, 0.8, 1.0)
    rows = []
    for bg in ((0.30, 0.27, 0.22), (0.05, 0.04, 0.035)):          # a limewashed wall in firelight, thatch at night
        cells = []
        for i in range(0, len(frames), max(1, len(frames) // 8)):
            f = frames[i]
            c = np.power(np.clip(f[..., :3], 0, 1), 2.2)
            h = np.clip((c.max(-1) - hot[0]) / (hot[1] - hot[0]), 0, 1); h = h * h * (3 - 2 * h)
            px = c * (hot[2] + (glow - hot[2]) * h)[..., None] * f[..., 3:4] + np.array(bg, np.float32) * (1 - f[..., 3:4])
            cells.append(FE.srgb(px / (1 + px) * 1.15))
        rows.append(np.concatenate(cells[:8], 1))
    Image.fromarray((np.clip(np.concatenate(rows, 0), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(folder, 'frames_strip.png'), optimize=True)
    rel = ROOT + '/small_fire_fx/' + name + '/'
    cov = float(np.mean([(f[..., 3] > 0.08).mean() for f in frames]))
    m = {'name': 'FX_' + name, 'class': 'effect flipbook (texture atlas; no mesh)', 'lod0_triangles': 0, 'dimensions_m': [S['size_m'], S['size_m'], 0.0],
         'textures': [{'file': rel + 'T_FX_%s_Flipbook.png' % name, 'size_px': [GRID[0] * PX, GRID[1] * PX],
                       'channels': 'RGB straight colour (sRGB) + alpha (opacity); %d x %d frames of %d px, row by row from the top left' % (GRID[0], GRID[1], PX)}],
         'flipbook': {'frames': GRID[0] * GRID[1], 'grid': list(GRID), 'fps': FPS, 'loop': True, 'billboard_size_m': [S['size_m'], S['size_m']], 'blend': 'translucent', 'glow': glow, 'hot': list(hot),
                      'alpha_coverage': round(cov, 3), 'content_box': [round(0.5 + (CX - S['radius']) / 2, 3), round(0.5 + (CY - S['radius']) / 2, 3), round(0.5 + (CX + S['radius']) / 2, 3), round(0.5 + (CY + S['radius']) / 2, 3)]},
         'preview': rel + 'frames_strip.png',
         'source_note': 'made by code, no .blend: FableF/tools/build_burn_patch.py draws the charred patch (ragged outline, burnt runs, Voronoi cracks, embers that breathe by cell and by a slow noise) and sets small flames from the frames of the simulated fire (the Fire_Wall cache, cut as for Hearth) and their smoke on it with tools/fire_encode.py.',
         'build': 'python3 -I FableF/tools/build_burn_patch.py <Fire_Wall cache>/compact_256.npy ' + name + '   (the .npy: build_fire_fx.py -- Fire_Wall --cache <cache> --stage compact)',
         'families': ['small_fire_fx', S['seq']], 'supersedes': 'the charred timber heaps of 15 Nov 2026 (a heap is a thing on a floor; all six placements are marks on a wall or on the roof)',
         'dresses': S['dresses'], 'third_party': [], 'status': 'source delivered',
         'known_weaknesses': 'A flat picture on a camera-facing card, not a decal on the surface: on the roof slope it stands a little off the thatch, and it does not follow a wall seen at an angle. Unlit: the char keeps its own darkness whatever the room light. The same flame motion as the wall of flame, smaller.'}
    json.dump(m, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
    open(os.path.join(folder, 'manifest.json'), 'a').write('\n')
    return folder


if __name__ == '__main__':
    hdr = [f.astype(np.float32) for f in np.load(sys.argv[1])]
    for nm in (sys.argv[2:] or list(SETS)):
        print('burn patch', nm, save(nm, build(nm, hdr)))
