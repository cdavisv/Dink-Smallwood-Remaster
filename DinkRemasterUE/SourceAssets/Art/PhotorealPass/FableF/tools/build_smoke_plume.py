"""The smoke of the burning house: a column that rolls up from a fire, as a looping translucent flipbook made by code
(numpy + PIL, no Blender). Billows are rising periodic noise warped by slower noise; the column widens and thins with
height, leans a little downwind, is lit orange from below and ends before the frame does.

    python3 -I FableF/tools/build_smoke_plume.py [Smoke_Plume]
"""
import json, math, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fire_encode as FE

KIT = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'
W, H, GRID, FPS = 256, 512, (8, 8), 16          # 64 frames, 4 s; a 2048 x 4096 atlas
SETS = {'Smoke_Plume': dict(seed=439, size_m=(3.5, 7.0), dresses='the smoke column over a burning roof: 3 m wide where it leaves the fire, rolling up 7 m and thinning')}


def build(name):
    S = SETS[name]
    rng = np.random.default_rng(S['seed'])
    n = GRID[0] * GRID[1]
    big = FE.periodic_fbm(n, H // 2, W // 2, rng, octaves=4, cx=3, cy=5, ct=2, wraps=1)
    mid = FE.periodic_fbm(n, H // 2, W // 2, rng, octaves=3, cx=7, cy=11, ct=3, wraps=2)
    warp = FE.periodic_fbm(n, H // 2, W // 2, rng, octaves=2, cx=2, cy=3, ct=2, wraps=1)
    fine = FE.periodic_fbm(n, H, W, rng, octaves=3, cx=13, cy=23, ct=4, wraps=3)           # full size: the ragged edge of each billow
    yy = np.linspace(0.0, 1.0, H // 2, dtype=np.float32)[:, None]            # 0 at the top row, 1 at the bottom
    xx = np.linspace(-1.0, 1.0, W // 2, dtype=np.float32)[None, :]
    up = 1.0 - yy                                                             # height above the fire, 0..1
    upf = np.linspace(1.0, 0.0, H, dtype=np.float32)[:, None]
    def full(a):
        return np.asarray(Image.fromarray(a.astype(np.float32), 'F').resize((W, H), Image.BICUBIC), np.float32)
    out = []
    for i in range(n):
        lean = 0.16 * up ** 1.5 + (warp[i] - 0.5) * 0.55 * (0.25 + up)           # downwind drift and a slow wander
        half = 0.26 + 0.46 * up ** 0.8                                         # the column widens
        core = np.clip(1.0 - ((xx - lean) / half) ** 2, 0, 1)
        puff = np.clip((big[i] - 0.30) / 0.42, 0, 1)
        dens = core ** 1.3 * (0.25 + 1.25 * puff * puff * (3 - 2 * puff)) * (0.6 + 0.8 * mid[i])
        dens *= np.clip(up / 0.10, 0, 1) ** 1.5 * np.clip((1.0 - up) / 0.30, 0, 1) ** 1.3 * (1.0 - 0.60 * up)       # born in the flames, thin before the top
        d = np.clip(full(dens), 0, None) * (0.55 + 0.9 * fine[i])               # billows with ragged edges, not blurred blobs
        a = np.clip(1.0 - np.exp(-2.3 * d), 0, 0.74)
        # grey-brown wood smoke: its lumps catch the sky on top and are dark underneath; the fire reddens only its foot,
        # which stands inside the flames
        lump = full(np.clip(mid[i] - 0.35, 0, 1))
        shade = 0.60 + 1.0 * lump + 0.35 * np.clip(fine[i] - 0.45, 0, 1)
        base = np.array((0.078, 0.070, 0.064), np.float32)[None, None, :] * (0.75 + 1.5 * upf[..., None]) * shade[..., None]
        fire = np.array((0.34, 0.11, 0.02), np.float32)[None, None, :] * (np.clip(1.0 - upf / 0.13, 0, 1) ** 2)[..., None]
        rgb = base + fire
        out.append(np.concatenate([FE.srgb(rgb), a[..., None]], -1).astype(np.float32))
    return out


def save(name, frames):
    S = SETS[name]
    folder = os.path.join(KIT, 'smoke_fx', name)
    os.makedirs(folder, exist_ok=True)
    atlas = np.zeros((GRID[1] * H, GRID[0] * W, 4), np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, GRID[0])
        atlas[r * H:(r + 1) * H, c * W:(c + 1) * W] = f
    Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(folder, 'T_FX_%s_Flipbook.png' % name), optimize=True)
    rows = []
    for bg in ((0.45, 0.55, 0.70), (0.05, 0.05, 0.06)):                         # day sky, night
        cells = []
        for i in range(0, len(frames), len(frames) // 8):
            f = frames[i][::2, ::2]
            c = np.power(np.clip(f[..., :3], 0, 1), 2.2)
            cells.append(FE.srgb(c * f[..., 3:4] + np.array(bg, np.float32) * (1 - f[..., 3:4])))
        rows.append(np.concatenate(cells[:8], 1))
    Image.fromarray((np.clip(np.concatenate(rows, 0), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(folder, 'frames_strip.png'), optimize=True)
    rel = ROOT + '/smoke_fx/' + name + '/'
    cov = float(np.mean([(f[..., 3] > 0.08).mean() for f in frames]))
    m = {'name': 'FX_' + name, 'class': 'effect flipbook (texture atlas; no mesh)', 'lod0_triangles': 0, 'dimensions_m': [S['size_m'][0], S['size_m'][1], 0.0],
         'textures': [{'file': rel + 'T_FX_%s_Flipbook.png' % name, 'size_px': [GRID[0] * W, GRID[1] * H],
                       'channels': 'RGB straight colour (sRGB) + alpha (opacity); %d x %d frames of %d x %d px, row by row from the top left' % (GRID[0], GRID[1], W, H)}],
         'flipbook': {'frames': GRID[0] * GRID[1], 'grid': list(GRID), 'fps': FPS, 'loop': True, 'billboard_size_m': list(S['size_m']), 'blend': 'translucent', 'glow': 1.0, 'hot': [0.9, 1.0, 1.0],
                      'alpha_coverage': round(cov, 3), 'stands_on_bottom_edge': True},
         'preview': rel + 'frames_strip.png',
         'source_note': 'made by code, no .blend: FableF/tools/build_smoke_plume.py (rising periodic noise in a widening, leaning column; orange underlight at its foot).',
         'build': 'python3 -I FableF/tools/build_smoke_plume.py ' + name,
         'families': ['fire_fx plume'], 'supersedes': 'none', 'dresses': S['dresses'], 'third_party': [], 'status': 'source delivered',
         'known_weaknesses': 'Noise, not a simulation: the billows roll but do not curl into vortices. Unlit: the smoke keeps its own brightness at night. A card: it does not bend with a wind and ends 7 m up.'}
    json.dump(m, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
    open(os.path.join(folder, 'manifest.json'), 'a').write('\n')
    return folder


if __name__ == '__main__':
    for nm in (sys.argv[1:] or list(SETS)):
        print('smoke plume', nm, save(nm, build(nm)))
