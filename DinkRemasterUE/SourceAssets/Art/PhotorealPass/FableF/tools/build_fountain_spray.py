"""The fountain's water (94 lands/garden/spray-): the 1997 picture is a wide blue dome of spray over the whole fountain,
80 px wide where the stone is 102. Here: water wells up at the bowl, is thrown out all round in some forty strands that
break into drops, and falls into the basin as an umbrella 2.2 m across; it splashes where it lands. A looping flipbook
made by code (numpy + PIL, no Blender). Every drop flies a ballistic arc in 3D whose cycle divides the loop, so the loop
closes; the drops are projected through a camera raised as the play camera is and drawn as streaks along their motion.

The flipbook is LIT ("blend": "lit" -> the kit importer's M_FX_Flipbook_Lit): its colour is the water's own (blue-white),
the scene's light makes it bright by day and dim in a dungeon. The unlit version before it was faint against sunlit
ground and glowed in the dark.

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
FRAME_M = 2.8                      # the frame's width and height
NOZZLE = (0.5, 0.66)               # where the water leaves the bowl, in frame units (x, y down)
BASIN_Z = -0.74                    # the basin's water below the bowl's rim (SM_Fountain_Stone_PR: rim 1.2 m, water 0.46 m)
BASIN_R = 1.16                     # inside radius of the basin
ELEV = math.radians(15.0)          # the play camera looks down about this much
G = 9.81


def build(seed=94):
    rng = np.random.default_rng(seed)
    n = GRID[0] * GRID[1]
    loop = n / FPS
    ppm = PX / FRAME_M
    drops = 13000
    strands = 44
    # each drop belongs to a strand (an azimuth the water leaves the bowl at); it strays from it as it flies
    az0 = rng.uniform(0, 2 * math.pi, strands)
    sid = rng.integers(0, strands, drops)
    az = az0[sid] + rng.normal(0, 0.05, drops)
    apex = np.clip(rng.normal(0.62, 0.13, drops), 0.25, 0.95)             # how high above the bowl the arc tops out
    reach = np.clip(rng.normal(0.90, 0.20, drops), 0.18, BASIN_R - 0.03)   # where it lands in the basin (from the middle)
    # a quarter of the water goes nearly straight up and falls back on the bowl: the dome's crown (1997's is fullest at the top)
    mid = rng.random(drops) < 0.27
    apex = np.where(mid, np.clip(rng.normal(0.84, 0.09, drops), 0.5, 1.0), apex)
    reach = np.where(mid, 0.04 + np.abs(rng.normal(0, 0.24, drops)), reach)
    vz = np.sqrt(2 * G * apex)
    flight = vz / G + np.sqrt(2 * (apex - BASIN_Z) / G)
    vr = reach / flight
    k = np.maximum(1, np.floor(loop / (flight + 0.16))).astype(int)        # cycles per loop: flight + splash fit in one cycle
    T = loop / k
    phase = rng.random(drops)
    size = rng.uniform(0.3, 1.0, drops) ** 1.6
    stray = rng.normal(0, 0.035, (drops, 2))
    ce, se = math.cos(ELEV), math.sin(ELEV)
    yy, xx = np.mgrid[0:PX, 0:PX].astype(np.float32)
    u = (xx / PX - NOZZLE[0]) * FRAME_M
    hgt = (NOZZLE[1] - yy / PX) * FRAME_M

    def splat(acc, x, y, w):
        x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
        for dx, dy, wq in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            xi, yi = x0 + dx, y0 + dy
            ok = (xi >= 0) & (xi < PX) & (yi >= 0) & (yi < PX)
            np.add.at(acc, (yi[ok], xi[ok]), (w * wq)[ok])

    def project(px3, py3, pz3):
        return NOZZLE[0] * PX + px3 * ppm, NOZZLE[1] * PX - (pz3 * ce + py3 * se) * ppm

    frames = []
    for i in range(n):
        t = ((i / n * k + phase) % 1.0) * T                    # time since launch
        acc = np.zeros((PX, PX), np.float32)                   # drops
        land = np.zeros((PX, PX), np.float32)                  # splashes
        for s in np.linspace(-1.0, 0.0, 10):                   # a streak: where the drop was during the exposure
            tt = np.clip(t + s * 0.030, 0, None)
            fly = np.minimum(tt, flight)
            r = 0.035 + vr * fly
            x3 = r * np.cos(az) + stray[:, 0] * fly
            y3 = r * np.sin(az) + stray[:, 1] * fly
            z3 = vz * fly - 0.5 * G * fly * fly
            sx, sy = project(x3, y3, z3)
            alive = (tt <= flight) * np.clip(tt / 0.03, 0, 1)
            # near the bowl the strand is still whole water (bright, continuous); further out it is drops
            whole = np.clip(1.0 - fly / 0.22, 0, 1)
            splat(acc, sx, sy, size * alive * (0.5 + 0.5 * (1 + s)) * (0.8 + 0.5 * whole))
            # the splash: a little crown thrown up where it lands, for 0.14 s
            after = tt - flight
            up = np.clip(after, 0, 0.14)
            crown = (after > 0) * (after < 0.14) * (1 - up / 0.14)
            cx, cy = project(x3 + stray[:, 0] * up * 6, y3, BASIN_Z + (1.1 * up - 0.5 * G * up * up) * 1.0)
            splat(land, cx, cy, size * crown * 0.8)
        acc = FE.blur(acc, 0.55)
        land = FE.blur(land, 1.1)
        # the water welling up at the bowl: a low boil that swells and sinks
        beat = i / n * 2 * math.pi
        boil_h = 0.26 + 0.035 * math.sin(beat * 3) + 0.02 * math.sin(beat * 7 + 1.0)
        wob = 0.02 * np.sin(hgt * 30.0 - beat * 5) + 0.012 * np.sin(hgt * 61.0 + beat * 9)
        boil = np.exp(-((u - wob) / (0.085 + 0.25 * np.clip(hgt, 0, 1))) ** 2) * np.clip(hgt / 0.02, 0, 1) * np.clip((boil_h - hgt) / 0.16, 0, 1) ** 1.2
        # fine spray: the dome itself as a haze (what the drops' own veil adds up to), and a mist over the basin
        veil = FE.blur(acc, 7.0) * 2.2 + FE.blur(acc, 2.2) * 0.9
        dome = np.exp(-((u / 1.0) ** 2 + ((hgt - 0.20) / 0.58) ** 2) ** 1.4) * (0.24 + 0.035 * math.sin(beat * 2 + 0.7))
        basin = np.exp(-((u / 1.08) ** 2) ** 2 - ((hgt - (BASIN_Z * ce + 0.06)) / 0.18) ** 2) * 0.30 + FE.blur(land, 5.0) * 1.8
        # opacity from how much water the eye looks through (never a flat white patch: the crown keeps its drops)
        # falling water is seen against bright ground by day: the curtain of drops counts for more than the rising strands
        sharp = acc * 0.60 + land * 0.7
        thick = sharp + boil * 0.75
        haze = veil * 0.16 + dome + basin
        a = np.clip(1.0 - np.exp(-(thick * 2.3 + haze * 1.7)), 0, 0.94)
        # water in daylight: sky blue where it is a veil, near white only on the drops themselves and the whole water at the bowl
        white = np.clip(1.0 - np.exp(-(sharp * 1.6 + boil * 1.2)), 0, 1)[..., None]
        rgb = np.array((0.30, 0.56, 0.93), np.float32)[None, None, :] * (1 - white) + np.array((0.80, 0.92, 1.0), np.float32)[None, None, :] * white
        edge = np.clip((yy / PX) / 0.05, 0, 1) * np.clip((1 - yy / PX) / 0.04, 0, 1) * np.clip((1 - np.abs(xx / PX - 0.5) * 2) / 0.06, 0, 1)
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
    # lit: (ground colour, light on the water) for the square's earth by day and for the dungeon
    for bg, light in (((0.30, 0.22, 0.15), 1.0), ((0.03, 0.03, 0.035), 0.16)):
        cells = []
        for i in range(0, len(frames), len(frames) // 6):
            f = frames[i]
            c = np.power(np.clip(f[..., :3], 0, 1), 2.2) * light
            cells.append(FE.srgb(c * f[..., 3:4] + np.array(bg, np.float32) * (1 - f[..., 3:4])))
        rows.append(np.concatenate(cells[:6], 1))
    Image.fromarray((np.clip(np.concatenate(rows, 0), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(folder, 'frames_strip.png'), optimize=True)
    rel = ROOT + '/fountain_spray_fx/' + NAME + '/'
    cov = float(np.mean([(f[..., 3] > 0.08).mean() for f in frames]))
    m = {'name': 'FX_' + NAME, 'class': 'effect flipbook (texture atlas; no mesh)', 'lod0_triangles': 0, 'dimensions_m': [FRAME_M, FRAME_M, 0.0],
         'textures': [{'file': rel + 'T_FX_%s_Flipbook.png' % NAME, 'size_px': [GRID[0] * PX, GRID[1] * PX],
                       'channels': 'RGB straight colour (sRGB) + alpha (opacity); %d x %d frames of %d px, row by row from the top left' % (GRID[0], GRID[1], PX)}],
         'flipbook': {'frames': GRID[0] * GRID[1], 'grid': list(GRID), 'fps': FPS, 'loop': True, 'billboard_size_m': [FRAME_M, FRAME_M], 'blend': 'lit', 'glow': 1.0,
                      'alpha_coverage': round(cov, 3), 'nozzle': list(NOZZLE), 'basin_water_below_nozzle_m': -BASIN_Z},
         'preview': rel + 'frames_strip.png',
         'source_note': 'made by code, no .blend: FableF/tools/build_fountain_spray.py (13000 drops on 3D ballistic arcs in 44 strands from the bowl into the basin, projected through a camera raised 15 degrees and drawn as streaks; a boil at the bowl, the dome\'s veil, splashes and mist on the basin).',
         'build': 'python3 -I FableF/tools/build_fountain_spray.py',
         'families': ['fountain_spray_fx', '94 lands/garden/spray-'],
         'supersedes': 'the narrow jet of 16 Nov (unlit: faint by day, glowing in the dungeon)',
         'dresses': 'the fountain\'s spray as in 1997: a dome of blue-white water 2.2 m across thrown from the bowl into the basin',
         'third_party': [], 'status': 'source delivered',
         'known_weaknesses': 'A card through the fountain\'s middle: the far half of the umbrella is not hidden by the bowl, the drops make no rings on the basin\'s water mesh and do not wet the stone. No wind.'}
    json.dump(m, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
    open(os.path.join(folder, 'manifest.json'), 'a').write('\n')
    return folder


if __name__ == '__main__':
    print('fountain spray', save(build()))
