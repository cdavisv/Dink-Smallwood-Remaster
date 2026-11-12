"""Effect families as flipbook atlases: hearth fire (86), explosion (70), fire burst (161), falling fireball (512),
sparkle (165, 166) and fountain spray (94).

Every set is synthesised frame by frame with numpy: fire and smoke from tileable noise fields scrolled through a
shape function and mapped through a fire ramp, sparkle and spray from particles. Each is one 2048 px atlas of
8 x 8 frames (straight colour + alpha) with a manifest giving frame count, rate, loop and billboard size. The
beauty renders show the mid frame on an emissive billboard in a dusk scene (Cycles). These feed a Niagara or
flipbook material; no Unreal effect asset is authored here.

    tools/bl.sh build_fx.py <name,name|all>
"""
import bpy, math, os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import build_decals as BD
from pplib import NT, smoothstep
from PIL import Image

SCRIPT = 'build_fx.py'
GRID = 8; FPX = 256; NF = GRID * GRID; SS = 2; P = FPX * SS
RAMP_X = np.array([0.0, 0.12, 0.3, 0.52, 0.76, 1.0]); RAMP_C = np.array([(0.0, 0.0, 0.0), (0.22, 0.012, 0.0), (0.85, 0.10, 0.008), (1.0, 0.36, 0.03), (1.0, 0.72, 0.16), (1.0, 0.95, 0.70)], np.float32)
SMOKE = np.array((0.15, 0.14, 0.13), np.float32)


def ramp(h):
    h = np.clip(h, 0, 1); return np.stack([np.interp(h, RAMP_X, RAMP_C[:, k]) for k in range(3)], -1).astype(np.float32)


def fields(seed, n=4):
    """tileable noise fields (P x P, 0..1): broad, medium, fine, very fine"""
    rng = np.random.default_rng(seed); spec = [(2.6, 2, 10), (2.2, 5, 40), (1.6, 14, 120), (1.0, 40, 256)]
    out = []
    for beta, lo, hi in spec[:n]:
        f = BD.spectral(rng, px=P, beta=beta, lo=lo, hi=hi); f = (f - f.mean()) / (f.std() + 1e-6); out.append(np.clip(0.5 + f * 0.22, 0, 1))
    return out


def scroll(f, dx, dy):
    """periodic shift by (dx, dy) fractions of the field, bilinear"""
    sx = dx * P; sy = dy * P; ix = int(math.floor(sx)); iy = int(math.floor(sy)); fx = sx - ix; fy = sy - iy; a = np.roll(f, (iy, ix), (0, 1)); b = np.roll(f, (iy, ix + 1), (0, 1)); c_ = np.roll(f, (iy + 1, ix), (0, 1)); d = np.roll(f, (iy + 1, ix + 1), (0, 1))
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c_ * (1 - fx) + d * fx) * fy


def grid():
    """x in -0.5..0.5 (right positive), z in 0..1 (up positive); row 0 is the top of the frame"""
    yy, xx = np.mgrid[0:P, 0:P].astype(np.float32); return (xx + 0.5) / P - 0.5, 1.0 - (yy + 0.5) / P


def finish(heat, alpha, smoke=None):
    """heat 0..1 -> fire colour; smoke 0..1 -> grey veil behind it; returns a premultiplied RGBA frame at FPX"""
    col = ramp(heat) * (0.25 + 0.75 * np.clip(heat, 0, 1))[..., None] * 1.15; a = np.clip(alpha, 0, 1)
    if smoke is not None:
        sm = np.clip(smoke, 0, 1); col = col * a[..., None] + SMOKE * (sm * (1 - a))[..., None]; a2 = np.clip(a + sm * (1 - a), 0, 1); f = np.concatenate([col, a2[..., None]], -1)
    else:
        f = np.concatenate([col * a[..., None], a[..., None]], -1)
    return f.reshape(FPX, SS, FPX, SS, 4).mean((1, 3))


def flame_frames(seed, width=0.2, height=0.82, sway=0.16, base=0.03, rise=(1, 2, 3, 5), tail=0.0, head=None):
    """a flame standing on the bottom edge: a swaying, tapering column eaten by turbulence that scrolls upward; whole numbers of scroll per loop, so it loops exactly"""
    X, Z = grid(); N0, N1, N2, N3 = fields(seed); out = []
    for i in range(NF):
        u = i / NF; zn = np.clip((Z - base) / height, 0, 1.2); w0 = scroll(N0, 0.0, u * rise[0]); xs = X + (w0 - 0.5) * sway * (0.25 + 1.6 * zn)
        wd = width * np.maximum(1 - zn, 0.0) ** 0.62 * (1.0 + 0.25 * np.sin(2 * np.pi * (u + Z * 1.5)) * zn)
        if head is not None:                                # a ball at the bottom with the flame streaming up from it
            hd = 1 - np.hypot(X, (Z - head[0]) * 1.0) / head[1]; env = np.maximum(hd * 1.15, 1 - np.abs(xs) / np.maximum(wd, 1e-3) - tail * zn) * (Z > head[0] - head[1] * 1.2)
        else:
            env = 1 - np.abs(xs) / np.maximum(wd, 1e-3)
        t1 = scroll(N1, 0.13, u * rise[1]); t2 = scroll(N2, 0.37, u * rise[2]); t3 = scroll(N3, 0.71, u * rise[3])
        f = env * 1.0 + (t1 - 0.5) * (0.5 + 2.0 * zn) + (t2 - 0.5) * (0.25 + 0.9 * zn) + (t3 - 0.5) * 0.18 + 0.1 - 0.5 * zn ** 2
        f = BD.blur(f.astype(np.float32), 1.5) * smoothstep(0.0, 0.035, Z - base + 0.02); heat = smoothstep(-0.05, 1.0, f) * (1.08 - 0.5 * zn); alpha = smoothstep(0.0, 0.55, f)
        out.append(finish(np.clip(heat, 0, 1), alpha))
    return out


def blast_frames(seed, mushroom=False):
    """one shot: a ball of fire that swells, breaks up and cools to rising smoke (mushroom: a column carrying a rolling cap upward)"""
    X, Z = grid(); N0, N1, N2, N3 = fields(seed); out = []
    for i in range(NF):
        u = i / (NF - 1); g = 1 - math.exp(-4.2 * u)
        if mushroom:
            zc = 0.12 + 0.62 * g; R = 0.07 + 0.2 * g; cap = 1 - np.hypot(X / R, (Z - zc) / (R * 0.62)); roll = 1 - np.hypot((np.abs(X) - R * 0.62) / (R * 0.5), (Z - zc + R * 0.18) / (R * 0.42))
            stem = np.where(Z < zc, 1 - np.abs(X) / (R * 0.3 + 0.07 * np.maximum(0, 0.14 - Z) / 0.14), -4.0); env = np.maximum(np.maximum(cap, roll * 0.9), stem * 0.9); rr = np.hypot(X, Z - zc) / (R + 1e-3)
        else:
            cz = 0.36 + 0.2 * u; R = 0.04 + 0.34 * g + 0.06 * u; rr = np.hypot(X, Z - cz) / R; env = 1 - rr
        zoom = 0.35 + 0.65 * g; t1 = scroll(N1, 0.1 + 0.25 * g, 0.2 + 0.5 * g); t2 = scroll(N2, 0.3 - 0.4 * g, 0.4 + 0.9 * g); t3 = scroll(N3, 0.6, u * 1.5); t0 = scroll(N0, 0.0, 0.3 * g)
        brk = 0.35 + 1.5 * u                                  # the ball breaks up as it cools
        f = env * 1.0 + (t0 - 0.5) * 0.7 * brk + (t1 - 0.5) * 0.9 * brk + (t2 - 0.5) * 0.4 + (t3 - 0.5) * 0.15 + 0.15 - 0.35 * u; f = BD.blur(f.astype(np.float32), 1.5)
        hot = max(0.0, 1.3 * math.exp(-(3.4 if not mushroom else 2.6) * u) - 0.03); heat = smoothstep(-0.05, 0.9, f) * hot * (1.1 - 0.35 * np.clip(rr, 0, 1)); fade = max(0.0, 1 - u) ** 0.8
        alpha = smoothstep(0.0, 0.5, f) * min(1.0, hot * 1.4); smoke = smoothstep(-0.05, 0.55, f + 0.1) * min(1.0, 3.0 * u) * fade * 0.9
        out.append(finish(np.clip(heat, 0, 1), alpha, smoke))
    return out


# ---------------------------------------------------------------------------------------------- particle sprites
def _disc(img, x, y, r, col, a):
    """soft additive dot into an RGBA float frame (premultiplied)"""
    n = img.shape[0]; x0 = max(0, int(x - 3 * r)); x1 = min(n, int(x + 3 * r) + 1); y0 = max(0, int(y - 3 * r)); y1 = min(n, int(y + 3 * r) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]; g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * r * r)) * a; img[y0:y1, x0:x1, :3] += g[..., None] * np.array(col, np.float32); img[y0:y1, x0:x1, 3] += g


def sparkle_frames():
    rng = np.random.default_rng(5); PP = 4 * FPX; stars = [(rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8), rng.uniform(0, 1), rng.uniform(0.5, 1.0), rng.integers(1, 4)) for _ in range(16)]; out = []
    for i in range(NF):
        u = i / NF; img = np.zeros((PP, PP, 4), np.float32)
        for (sx, sy, ph, sz, k) in stars:
            b = max(0.0, math.sin(2 * math.pi * (u * k + ph))) ** 3
            if b < 0.02:
                continue
            cx, cy = sx * PP, sy * PP; L_ = sz * PP * 0.11 * (0.4 + 0.6 * b); col = (1.0, 0.92, 0.55)
            for ang in (0, math.pi / 2, math.pi / 4, 3 * math.pi / 4):
                ln = L_ * (1.0 if ang in (0, math.pi / 2) else 0.45)
                for s_ in np.linspace(-1, 1, 41):
                    w = (1 - abs(s_)) ** 2; _disc(img, cx + math.cos(ang) * ln * s_, cy + math.sin(ang) * ln * s_, 1.0 + 2.2 * w * sz, col, 0.16 * b * w)
            _disc(img, cx, cy, 5.0 * sz, (1.0, 1.0, 0.9), 0.9 * b); _disc(img, cx, cy, 16.0 * sz, (1.0, 0.75, 0.3), 0.18 * b)
        out.append(img.reshape(FPX, 4, FPX, 4, 4).mean((1, 3)))
    return out


def spray_frames():
    """fountain jet: drops thrown up 1.2 m in a narrow cone, falling back as a veil; a steady state sampled over one loop"""
    rng = np.random.default_rng(9); PP = 4 * FPX; NP = 1500; T = NF / 24.0; t0 = rng.uniform(0, T, NP); ang = rng.normal(0, 0.17, NP); spd = rng.normal(4.6, 0.45, NP); sz = rng.uniform(0.6, 1.5, NP); life = 2 * spd * np.cos(ang) / 9.81; out = []
    for i in range(NF):
        tt = i / 24.0; img = np.zeros((PP, PP, 4), np.float32)
        for k in range(NP):
            age = (tt - t0[k]) % T
            if age > life[k]:
                continue
            for sub in range(4):                              # a short streak: four samples back along the path
                a = max(0.0, age - sub * 0.008); x = spd[k] * math.sin(ang[k]) * a; z = spd[k] * math.cos(ang[k]) * a - 0.5 * 9.81 * a * a; px = (0.5 + x / 2.0) * PP; py = (1 - (z + 0.05) / 2.0) * PP
                _disc(img, px, py, 1.9 * sz[k], (0.82, 0.92, 1.0), 0.55 * (1 - sub * 0.2))
        mist = np.zeros((PP, PP, 4), np.float32); _disc(mist, PP * 0.5, PP * 0.94, PP * 0.07, (0.8, 0.9, 1.0), 0.25); out.append((img + mist).reshape(FPX, 4, FPX, 4, 4).mean((1, 3)))
    return out


def sprite_set(outdir, name, frames, size, spec):
    atlas = np.zeros((GRID * FPX, GRID * FPX, 4), np.float32)
    for i, f in enumerate(frames):
        a = np.clip(f[..., 3:4], 0, 1); rgb = np.where(a > 1e-4, f[..., :3] / np.maximum(f[..., 3:4], 1e-4), 0.0); r, c = divmod(i, GRID); atlas[r * FPX:(r + 1) * FPX, c * FPX:(c + 1) * FPX] = np.concatenate([np.clip(rgb, 0, 1), a], -1)
    p = os.path.join(outdir, 'T_FX_%s_Flipbook.png' % name); Image.fromarray((atlas * 255 + 0.5).astype(np.uint8), 'RGBA').save(p, optimize=True)
    st = [atlas[(k // GRID) * FPX:(k // GRID + 1) * FPX, (k % GRID) * FPX:(k % GRID + 1) * FPX] for k in spec.get('strip', (4, 20, 36, 52))]; s = np.concatenate(st, 1); comp = s[..., :3] * s[..., 3:4] + 0.07 * (1 - s[..., 3:4])
    Image.fromarray((np.clip(comp, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(outdir, 'frames_strip.png'), optimize=True)
    # beauty: the mid frame on a billboard in the dusk scene
    L.reset(); R = L.review_setup(ground='park_dirt', ground_scale=0.6, exposure=-1.2, sun_elev=3.0, sun_rot=-60.0); k = spec.get('mid', 20); fr = atlas[(k // GRID) * FPX:(k // GRID + 1) * FPX, (k % GRID) * FPX:(k % GRID + 1) * FPX]
    tmp = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'dink_unclaimed_fx'); os.makedirs(tmp, exist_ok=True); fp = os.path.join(tmp, name + '_mid.png'); Image.fromarray((fr * 255 + 0.5).astype(np.uint8), 'RGBA').save(fp)
    bb = L.new_obj('billboard', [(-size / 2, 0, 0), (size / 2, 0, 0), (size / 2, 0, size), (-size / 2, 0, size)], [(0, 1, 2, 3)], smooth=False); uv = bb.data.uv_layers.new(name='UVMap')
    for li, c in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[li].uv = c
    t = NT('fx_billboard'); im = t.image(fp, 'sRGB', t.uv, ext='CLIP'); em = t.node('ShaderNodeEmission'); t.L.new(im.outputs[0], em.inputs[0]); em.inputs[1].default_value = spec.get('gain', 6.0); tr = t.node('ShaderNodeBsdfTransparent'); mx = t.node('ShaderNodeMixShader')
    t.L.new(im.outputs[1], mx.inputs[0]); t.L.new(tr.outputs[0], mx.inputs[1]); t.L.new(em.outputs[0], mx.inputs[2]); t.L.new(mx.outputs[0], t.out.inputs['Surface']); L.assign(bb, t.mat)
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), center=(0, 0, size * 0.45), radius=size * 0.62, az=0, el=6, fill=0.85, lens=60, spp=96); L.shot(R, os.path.join(outdir, 'render_close.png'), center=(0, 0, size * 0.4), radius=size * 0.3, az=0, el=4, fill=0.9, lens=85, res=(1000, 800), spp=96)
    return p, float((atlas[..., 3] > 0.05).mean())


SPECS = {
    'Hearth_Fire': dict(fam='hearth_fire', seq='86 inside/details/fire- frame 1', frames=lambda: flame_frames(3), size=1.0, loop=True, fps=24, gain=7.0, blend='additive (or alpha with emissive)',
                        dresses='hearth fire: a 0.8 m flame with swaying, breaking tongues, looping exactly over 64 frames; sits on the fireplace logs',
                        weak='Synthesised from scrolling noise through a tapering column, not a combustion simulation: tongues rise and break plausibly but there are no detached flamelets curling over, no embers or sparks, and no logs (the fireplace prop has those).'),
    'Fireball': dict(fam='fireball_fx', seq='512 effects/comets/sm-comt2/fbal2- frame 1', frames=lambda: flame_frames(7, width=0.13, height=0.8, sway=0.1, base=0.2, tail=0.25, head=(0.2, 0.13)), size=2.4, loop=True, fps=24, gain=7.0,
                     blend='additive (or alpha with emissive)', dresses='falling fireball: a 0.6 m burning head with a 1.9 m flame trail streaming up behind it, looping; move the billboard down to make it fall',
                     weak='A head-and-trail shape from scrolling noise; the fall itself, the impact and the scorch are not part of it.'),
    'Explosion': dict(fam='explosion_fx', seq='70 effects/splode/explo- frame 1', frames=lambda: blast_frames(11), size=3.0, loop=False, fps=30, gain=6.0, mid=8, strip=(2, 8, 20, 40), blend='alpha with emissive (fire first, smoke after)',
                      dresses='explosion, one shot of 64 frames: a fireball swelling to about 2 m, breaking up as it cools, then a rising, thinning ball of smoke',
                      weak='A noise-eaten disc that swells, cools and thins by rule: no shock ring, debris, sparks or ground flash, and the smoke does not billow as a simulation would.'),
    'Fire_Burst': dict(fam='fire_burst_fx', seq='161 effects/atomic/atomc- frames 4, 14', frames=lambda: blast_frames(17, mushroom=True), size=6.0, loop=False, fps=30, gain=6.0, mid=14, strip=(3, 12, 26, 46), blend='alpha with emissive',
                       dresses='fire burst (the "atomic" frames), one shot of 64 frames: a column of fire carrying a rolling cap up to about 4.5 m, cooling to smoke',
                       weak='The mushroom is a cap, two side rolls and a stem drawn in profile with noise on them: it does not turn over like a real vortex ring, and the base has no ground fire or dust skirt.'),
    'Sparkle': dict(fam='sparkle_fx', seq='165 effects/shiny/shiny-, 166 effects/sparks/spark-', frames=sparkle_frames, size=1.0, loop=True, fps=24, gain=30.0, mid=20, blend='additive',
                    dresses='sparkle: sixteen warm four-point glints twinkling in a 1 m square, looping',
                    weak='Sixteen four-point glints twinkling at fixed places, drawn in 2D: no relation to a light or a surface. One set stands for both original sequences (the shimmer and the spark burst).'),
    'Fountain_Spray': dict(fam='fountain_spray_fx', seq='94 lands/garden/spray- frame 1', frames=spray_frames, size=2.0, loop=True, fps=24, gain=3.0, mid=20, blend='alpha (or additive at low intensity)',
                           dresses='fountain spray: a jet of drops thrown 1.1 m up and falling back as a veil, looping',
                           weak='Fifteen hundred ballistic drops drawn as soft streaks in a side view, with a touch of mist at the foot: no refraction, no sheet or column of water, no splash rings in the basin.'),
}
W_FX = (' A flipbook, not an effect: 64 frames of 256 px on one 2048 px atlas for a camera-facing billboard. It is drawn in 2D, so it casts no light, has no depth against the scene (soft-particle fade is engine work), and seen from above it is still a side view. '
        'The beauty render is the mid frame on an emissive card at dusk, not a volume. No Niagara system, material or light is authored here.')


def build(name):
    sp = SPECS[name]; outdir = os.path.join(L.UNC, sp['fam'], name); os.makedirs(outdir, exist_ok=True); frames = sp['frames'](); size = sp['size']
    p, cov = sprite_set(outdir, name, frames, size, sp); L.save_blend(os.path.join(outdir, 'FX_%s.blend' % name))
    man = {'name': 'FX_' + name, 'class': 'effect flipbook (texture atlas; no mesh)', 'lod0_triangles': 0, 'dimensions_m': [size, size, 0.0],
           'textures': [{'file': L.rel(p), 'size_px': [GRID * FPX, GRID * FPX], 'channels': 'RGB straight colour (sRGB) + alpha; %d x %d frames of %d px, row by row from the top left' % (GRID, GRID, FPX)}],
           'flipbook': {'frames': NF, 'grid': [GRID, GRID], 'fps': sp['fps'], 'loop': sp['loop'], 'billboard_size_m': [size, size], 'blend': sp['blend'], 'alpha_coverage': round(cov, 3)},
           'preview': L.rel(os.path.join(outdir, 'frames_strip.png')), 'source_blend': L.rel(os.path.join(outdir, 'FX_%s.blend' % name)), 'source_note': 'the frames are generated by the build script (seeded, deterministic); the .blend holds the dusk review scene with the mid frame on a card',
           'build': 'Unclaimed/tools/bl.sh %s %s' % (SCRIPT, name), 'families': [sp['fam'], sp['seq']], 'origin_ids': L.origin_ids([sp['fam']]), 'supersedes': 'none (placeholder greybox cards)', 'dresses': sp['dresses'],
           'third_party': ['park_dirt (render ground)'], 'status': 'source delivered; not imported into Unreal, no effect asset built', 'known_weaknesses': 'PARTIAL. ' + sp['weak'] + W_FX}
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', outdir)


if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(',')
    for n in names:
        build(n)
