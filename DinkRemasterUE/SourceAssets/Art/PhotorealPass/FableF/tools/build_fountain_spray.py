"""The fountain's water (94 lands/garden/spray-): a jet that rises from the bowl, breaks into drops and falls back,
as a looping translucent flipbook made by code (numpy + PIL, no Blender). Every drop flies a ballistic arc whose
flight time divides the loop, so the loop closes; drops are drawn as short streaks along their motion.

    python3 -I FableF/tools/build_fountain_spray.py
"""
import json, math, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fire_encode as FE

KIT = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'
NAME = 'Fountain_Spray'
PX, GRID, FPS = 384, (8, 8), 24
FRAME_M = 2.2                      # the frame's width and height
NOZZLE = (0.5, 0.955)              # where the jet leaves the bowl, in frame units (x, y down)
G = 9.81


def build(seed=94):
    rng = np.random.default_rng(seed)
    n = GRID[0] * GRID[1]
    loop = n / FPS
    ppm = PX / FRAME_M
    drops = 1500                                              # many fine drops: 520 big ones read as white blobs in the game
    k = rng.choice([3, 3, 4, 4, 5], drops)                    # flights per loop
    T = loop / k                                              # the drop's cycle; it is back at the bowl's level at or before its end
    vy = G * T / 2 * rng.uniform(0.62, 1.0, drops)            # up speed: the fastest rise 1 m, the others fall back sooner
    reach = rng.normal(0.0, 0.40, drops)                      # an umbrella of arcs around the jet
    vx = reach / T
    phase = rng.random(drops)
    size = rng.uniform(0.35, 1.0, drops) ** 1.5
    frames = []
    yy, xx = np.mgrid[0:PX, 0:PX].astype(np.float32)
    for i in range(n):
        t = ((i / n * k + phase) % 1.0) * T                    # time since launch
        acc = np.zeros((PX, PX), np.float32)
        for s in np.linspace(-1.0, 0.0, 9):                    # a streak: where the drop was during the exposure
            tt = np.clip(t + s * 0.034, 0, None)
            x = NOZZLE[0] * PX + vx * tt * ppm
            y = NOZZLE[1] * PX - (vy * tt - 0.5 * G * tt * tt) * ppm
            back = 2 * vy / G                                    # when it is at the bowl's level again
            life = np.clip(tt / 0.05, 0, 1) * np.clip((back + 0.10 - tt) / 0.08, 0, 1)
            wgt = size * life * (0.55 + 0.45 * (1 + s))
            x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
            for dx, dy, wq in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
                xi, yi = x0 + dx, y0 + dy
                ok = (xi >= 0) & (xi < PX) & (yi >= 0) & (yi < PX)
                np.add.at(acc, (yi[ok], xi[ok]), (wgt * wq)[ok])
        acc = FE.blur(acc, 0.50) * 0.95
        # the jet itself: a column that swells and thins, strongest at the nozzle
        u = (xx / PX - NOZZLE[0]) * FRAME_M
        hgt = (NOZZLE[1] - yy / PX) * FRAME_M
        wob = 0.012 * np.sin(hgt * 21.0 - i / n * 2 * math.pi * 4) + 0.008 * np.sin(hgt * 47.0 + i / n * 2 * math.pi * 7)
        col = np.exp(-((u - wob) / (0.014 + 0.035 * np.clip(hgt, 0, 2))) ** 2) * np.clip(hgt / 0.03, 0, 1) * np.clip((1.05 - hgt) / 0.5, 0, 1) ** 1.5
        # mist where the jet breaks and a soft veil of fine spray
        mist = np.exp(-((u / 0.34) ** 2 + ((hgt - 0.78) / 0.42) ** 2)) * 0.16 * (0.8 + 0.2 * math.sin(i / n * 2 * math.pi * 3))
        a = np.clip(acc * 0.75 + col * 0.60 + mist, 0, 0.85)
        # water, not paint: grey-blue where it is thin, a cool white only where drops crowd. The card is unlit, so the
        # colour is kept below white: at full white the spray glared in the dungeon of screen 260
        white = np.clip(acc * 0.7 + col * 0.6, 0, 1)[..., None]
        rgb = np.array((0.42, 0.52, 0.62), np.float32)[None, None, :] * (1 - white) + np.array((0.78, 0.85, 0.90), np.float32)[None, None, :] * white
        edge = np.clip((yy / PX) / 0.05, 0, 1) * np.clip((1 - np.abs(xx / PX - 0.5) * 2) / 0.06, 0, 1)
        frames.append(np.concatenate([FE.srgb(rgb), (a * edge)[..., None]], -1).astype(np.float32))
    return frames


def save(frames):
    folder = os.path.join(KIT, 'fountain_spray_fx', NAME)
    os.makedirs(folder, exist_ok=True)
    atlas = np.zeros((GRID[1] * PX, GRID[0] * PX, 4), np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, GRID[0])
        atlas[r * PX:(r + 1) * PX, c * PX:(c + 1) * PX] = f
    Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(folder, 'T_FX_%s_Flipbook.png' % NAME), optimize=True)
    rows = []
    for bg in ((0.30, 0.22, 0.15), (0.03, 0.03, 0.035)):          # the square's earth by day, the dungeon
        cells = []
        for i in range(0, len(frames), len(frames) // 8):
            f = frames[i]
            c = np.power(np.clip(f[..., :3], 0, 1), 2.2)
            cells.append(FE.srgb(c * f[..., 3:4] + np.array(bg, np.float32) * (1 - f[..., 3:4])))
        rows.append(np.concatenate(cells[:8], 1))
    Image.fromarray((np.clip(np.concatenate(rows, 0), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(folder, 'frames_strip.png'), optimize=True)
    rel = ROOT + '/fountain_spray_fx/' + NAME + '/'
    cov = float(np.mean([(f[..., 3] > 0.08).mean() for f in frames]))
    m = {'name': 'FX_' + NAME, 'class': 'effect flipbook (texture atlas; no mesh)', 'lod0_triangles': 0, 'dimensions_m': [FRAME_M, FRAME_M, 0.0],
         'textures': [{'file': rel + 'T_FX_%s_Flipbook.png' % NAME, 'size_px': [GRID[0] * PX, GRID[1] * PX],
                       'channels': 'RGB straight colour (sRGB) + alpha (opacity); %d x %d frames of %d px, row by row from the top left' % (GRID[0], GRID[1], PX)}],
         'flipbook': {'frames': GRID[0] * GRID[1], 'grid': list(GRID), 'fps': FPS, 'loop': True, 'billboard_size_m': [FRAME_M, FRAME_M], 'blend': 'translucent', 'glow': 1.0, 'hot': [0.98, 1.0, 1.0],
                      'alpha_coverage': round(cov, 3), 'stands_on_bottom_edge': True, 'nozzle': list(NOZZLE)},
         'preview': rel + 'frames_strip.png',
         'source_note': 'made by code, no .blend: FableF/tools/build_fountain_spray.py (1500 fine drops on ballistic arcs whose flight times divide the loop, drawn as streaks; a jet column, mist where it breaks).',
         'build': 'python3 -I FableF/tools/build_fountain_spray.py',
         'families': ['fountain_spray_fx', '94 lands/garden/spray-'],
         'supersedes': 'Unclaimed/fountain_spray_fx/Fountain_Spray (128 px frames, additive: its drops were blocks at the play camera and it vanished on a bright ground)',
         'dresses': 'the fountain\'s spray: a jet 1 m high from the bowl, breaking into drops that fall back around it',
         'third_party': [], 'status': 'source delivered',
         'known_weaknesses': 'A card: the drops do not land on the water, make no rings and do not wet the bowl. Unlit: the water keeps its own brightness at night. Arcs only: no wind.'}
    json.dump(m, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
    open(os.path.join(folder, 'manifest.json'), 'a').write('\n')
    return folder


if __name__ == '__main__':
    print('fountain spray', save(build()))
