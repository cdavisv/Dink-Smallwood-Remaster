"""The burn patches of the burning house (155-157 struct/details/damage/fire2..4-) as animated decal sheets.

The 1997 pictures are places where the fire has eaten through a wall or the thatch: a ragged black outline with rays,
charred laths across the gap, and the fire glowing between them (three frames of flicker). Drawn on a camera-facing
card they floated in front of the surface; here each is a flat sheet for a deferred decal (the kit importer's
M_FX_Flipbook_Decal, "blend": "decal"): soot fading out round a char-black break, brown charred laths, and behind
them a glow that flickers through a closed loop of 32 frames. Made by code (numpy + PIL), no Blender.

    python3 -I FableF/tools/build_burn_mark.py
"""
import json, math, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fire_encode as FE

KIT = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'
PX, GRID, FPS = 256, (8, 4), 12

# name: seed, 1997 picture, lobes (centre x, y, radius in frame units), lath angle (degrees), laths per frame, size the sheet covers (m)
SETS = {
    'Burn_Mark_A': dict(seed=155, seq='155 struct/details/damage/fire2-', lobes=[(0.50, 0.50, 0.25)], angle=-14.0, laths=5.5, size_m=1.0,
                        dresses='a place the fire has eaten through, 0.6 m across in a 1 m sheet: ragged black break, two charred laths, glow behind'),
    'Burn_Mark_B': dict(seed=156, seq='156 struct/details/damage/fire3-', lobes=[(0.50, 0.50, 0.27)], angle=-20.0, laths=6.5, size_m=1.0,
                        dresses='as A, rounder, three laths'),
    'Burn_Mark_C': dict(seed=157, seq='157 struct/details/damage/fire4-', lobes=[(0.40, 0.38, 0.19), (0.60, 0.62, 0.20), (0.50, 0.50, 0.15)], angle=-24.0, laths=8.0, size_m=1.85,
                        dresses='the long burn: two breaks run together along a diagonal, 1.3 m long in a 1.85 m sheet'),
}


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def fbm2(rng, n, cells, octaves=4):
    out = np.zeros((n, n), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        k = cells * 2 ** o
        lat = rng.random((k + 1, k + 1)).astype(np.float32)
        img = np.asarray(Image.fromarray(lat, 'F').resize((n, n), Image.BICUBIC), np.float32)
        out += img * amp; tot += amp; amp *= 0.55
    return out / tot


def build(name):
    S = SETS[name]
    rng = np.random.default_rng(S['seed'])
    n = GRID[0] * GRID[1]
    yy, xx = np.mgrid[0:PX, 0:PX].astype(np.float32)
    u, v = xx / PX, yy / PX
    # the break: a union of lobes whose rim is torn by noise and thrown out in rays (cracks running into the sound wood)
    rag = fbm2(rng, PX, 5) - 0.5
    fine = fbm2(rng, PX, 22, 3) - 0.5
    d = np.full((PX, PX), 9.0, np.float32)          # signed distance-like: < 0 inside
    core = np.full((PX, PX), 9.0, np.float32)       # the same without the rays: the fire shows in the break, the cracks stay black
    for (cx, cy, r) in S['lobes']:
        ang = np.arctan2(v - cy, u - cx)
        rad = np.hypot(u - cx, v - cy)
        rays = np.zeros_like(rad)
        for _ in range(int(rng.integers(9, 14))):
            a0 = rng.uniform(-math.pi, math.pi); wid = rng.uniform(0.02, 0.055); length = rng.uniform(0.25, 0.8)
            da = np.angle(np.exp(1j * (ang - a0)))
            rays = np.maximum(rays, np.exp(-(da / wid) ** 2) * length)
        d = np.minimum(d, rad / (r * (1.0 + 0.55 * rag + 0.16 * fine + rays)) - 1.0)
        core = np.minimum(core, rad / (r * (0.80 + 0.45 * rag)) - 1.0)
    hole = smooth(-d / 0.10 + 0.5)                  # 1 inside the break
    soot = np.clip(1.0 - np.clip(d, 0, None) / 0.75, 0, 1) ** 2.0 * (0.55 + 0.9 * np.clip(rag + 0.5, 0, 1))      # the scorch round it
    # charred laths across the break, eaten away towards its middle
    a = math.radians(S['angle'])
    across = (-(u - 0.5) * math.sin(a) + (v - 0.5) * math.cos(a)) * S['laths'] + rng.uniform(0, 1)
    along = ((u - 0.5) * math.cos(a) + (v - 0.5) * math.sin(a))
    row = np.floor(across)
    f = across - row
    rowrand = np.sin(row * 12.9898 + S['seed']) * 43758.5453
    rowrand = rowrand - np.floor(rowrand)
    width = 0.50 + 0.18 * (rowrand - 0.5) + 0.10 * (fbm2(rng, PX, 7) - 0.5)
    bar = smooth((width / 2 - np.abs(f - 0.5)) / 0.07)
    eaten = smooth((fbm2(rng, PX, 6) - 0.34 - 0.30 * np.clip(-d, 0, 1)) / 0.10)      # laths are burnt away in places, more towards the middle
    lath = bar * eaten
    grain = 0.75 + 0.5 * fbm2(rng, PX, 40, 2) * (0.6 + 0.4 * np.sin(along * 190.0 + rowrand * 6.28))
    lath_rgb = np.array((0.115, 0.060, 0.034), np.float32)[None, None, :] * grain[..., None]
    # embers along the laths' burnt edges
    edge = smooth((0.11 - np.abs(np.abs(f - 0.5) - width / 2)) / 0.07) * eaten
    # the fire behind: periodic rising noise through the gaps
    fire = FE.periodic_fbm(n, PX // 2, PX // 2, rng, octaves=4, cx=4, cy=4, ct=3, wraps=1)
    emb = FE.periodic_fbm(n, PX // 2, PX // 2, rng, octaves=3, cx=9, cy=9, ct=4, wraps=0)
    frames = []
    depth = smooth(-core / 0.55)                    # 0 at the rim of the break, 1 deep inside
    for i in range(n):
        fl = np.asarray(Image.fromarray(fire[i], 'F').resize((PX, PX), Image.BICUBIC), np.float32)
        em = np.asarray(Image.fromarray(emb[i], 'F').resize((PX, PX), Image.BICUBIC), np.float32)
        # mostly black: the fire shows in patches deep in the break, dull red, orange where it is hot, a little yellow
        heat = smooth((fl - 0.50) / 0.22) * depth * (1 - lath)
        glow = np.stack([np.clip(heat * 1.25, 0, 1) * 0.92, np.clip(heat * 1.45 - 0.62, 0, 1) * 0.62, np.clip(heat * 2.4 - 2.0, 0, 1) * 0.30], -1)
        ember = smooth((em - 0.56) / 0.12) * edge * depth * 0.75
        glow = np.maximum(glow, np.stack([ember, ember * 0.30, ember * 0.02], -1))
        void = np.array((0.006, 0.005, 0.005), np.float32)[None, None, :]
        inside = void * (1 - lath[..., None]) + lath_rgb * lath[..., None]
        inside = np.maximum(inside, glow)
        sootc = np.array((0.016, 0.012, 0.010), np.float32)[None, None, :]
        rgb = inside * hole[..., None] + sootc * (1 - hole[..., None])
        alpha = np.clip(hole + soot * 0.88 * (1 - hole), 0, 1)
        fade = np.clip(np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) / 0.05, 0, 1)
        frames.append(np.concatenate([FE.srgb(rgb), (alpha * fade)[..., None]], -1).astype(np.float32))
    return frames


def save(name, frames):
    S = SETS[name]
    folder = os.path.join(KIT, 'burn_mark_fx', name)
    os.makedirs(folder, exist_ok=True)
    atlas = np.zeros((GRID[1] * PX, GRID[0] * PX, 4), np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, GRID[0])
        atlas[r * PX:(r + 1) * PX, c * PX:(c + 1) * PX] = f
    Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(folder, 'T_FX_%s_Flipbook.png' % name), optimize=True)
    cells = []
    for bg in ((0.42, 0.33, 0.18), (0.50, 0.49, 0.46)):       # thatch, limewash
        for i in (0, 8, 16, 24):
            f = frames[i]
            c = np.power(np.clip(f[..., :3], 0, 1), 2.2)
            cells.append(FE.srgb(c * f[..., 3:4] + np.array(bg, np.float32) * (1 - f[..., 3:4])))
    Image.fromarray((np.clip(np.concatenate(cells, 1), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(folder, 'frames_strip.png'), optimize=True)
    rel = ROOT + '/burn_mark_fx/' + name + '/'
    m = {'name': 'FX_' + name, 'class': 'effect flipbook (texture atlas; no mesh)', 'lod0_triangles': 0, 'dimensions_m': [S['size_m'], S['size_m'], 0.0],
         'textures': [{'file': rel + 'T_FX_%s_Flipbook.png' % name, 'size_px': [GRID[0] * PX, GRID[1] * PX],
                       'channels': 'RGB straight colour (sRGB) + alpha (opacity of the soot and the break); %d x %d frames of %d px, row by row from the top left' % (GRID[0], GRID[1], PX)}],
         'flipbook': {'frames': GRID[0] * GRID[1], 'grid': list(GRID), 'fps': FPS, 'loop': True, 'billboard_size_m': [S['size_m'], S['size_m']], 'blend': 'decal', 'glow': 5.0, 'hot': [0.16, 0.5, 1.0]},
         'preview': rel + 'frames_strip.png',
         'source_note': 'made by code, no .blend: FableF/tools/build_burn_mark.py (a torn outline with rays, charred laths, a periodic rising noise as the fire behind them).',
         'build': 'python3 -I FableF/tools/build_burn_mark.py',
         'families': ['small_fire_fx', S['seq']],
         'supersedes': 'FableF/small_fire_fx/Embers_* on a camera-facing card (a glowing heap floating in front of the wall)',
         'dresses': S['dresses'], 'third_party': [], 'status': 'source delivered',
         'known_weaknesses': 'Flat: a decal has no depth, the laths do not stand in front of the fire. The wall or thatch behind the break is not cut (the roof hole itself is the burning cottage of DS-01).'}
    json.dump(m, open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)
    open(os.path.join(folder, 'manifest.json'), 'a').write('\n')
    return folder


if __name__ == '__main__':
    for name in SETS:
        print('burn mark', save(name, build(name)))
