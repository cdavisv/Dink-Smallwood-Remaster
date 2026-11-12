"""Bark texture sets (BC / N / ORM), 1024x2048, built from CC0 Poly Haven bark scans re-laid into three V bands:
   v 0.00-0.25 trunk base (soil stain, moss; continues seamlessly into the body band)
   v 0.25-0.75 trunk body (tiles in U and, inside the band, in V)
   v 0.75-1.00 limb / upper bark at finer scale (tiles in U and inside the band in V)
Run with python3 -I (reads third-party images)."""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from texlib import *
OUT = os.path.join(HERE, '..', 'Export', 'Textures'); TP = os.path.join(HERE, '..', '..', 'ThirdParty', 'polyhaven')

def load(aid, m, lin=True):
    im = Image.open(f'{TP}/{aid}/{aid}_{m}_2k.jpg').convert('RGB')
    a = np.asarray(im).astype(np.float64) / 255
    return a

def s2l(a): return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)

def vperiodic(a, rows=2048, ov=256):
    """crop to `rows` and cross-fade so it wraps vertically (for scans taller than wide)."""
    if a.shape[0] <= rows: return a
    top = a[:rows].copy(); ext = a[rows:rows + ov]
    t = np.linspace(1, 0, ov)[:, None, None]
    top[:ov] = top[:ov] * (1 - t) + ext * t
    return top

def rs(a, w, h):
    return np.asarray(Image.fromarray(lin8(a)).resize((w, h), Image.LANCZOS)).astype(np.float64) / 255

def build(name, aid, seed, limb_tint, limb_gain, body_tint=(1, 1, 1), moss_amt=0.8, sat=1.0, dead=False):
    m = {k: vperiodic(load(aid, k)) for k in ('diff', 'nor_gl', 'rough', 'ao', 'disp')}
    W = 1024
    body = {k: rs(v, W, 1024) for k, v in m.items()}
    limb = {k: np.hstack([rs(v, 512, 512)] * 2) for k, v in m.items()}
    bc_body = s2l(body['diff']) * np.array(body_tint)
    g = bc_body.mean(-1, keepdims=True); bc_body = np.clip(g + (bc_body - g) * sat, 0, 1)
    # macro value variation so the tile does not read as stock
    macro = 0.85 + 0.3 * fbm(1024, W, seed, 2.6)
    bc_body = bc_body * macro[..., None]
    bc_limb = s2l(limb['diff']); gl = bc_limb.mean(-1, keepdims=True)
    bc_limb = np.clip((gl + (bc_limb - gl) * 0.9) * np.array(limb_tint) * limb_gain, 0, 1)
    nb = body['nor_gl'] * 2 - 1; nl = limb['nor_gl'] * 2 - 1
    nl[..., :2] *= 0.7
    if dead:
        # limb band -> bare weathered wood; body band gets a moss stripe centred on u=0.25 (the upper side of a lying log)
        fib = fbm(512, W, seed + 30, 1.3, 1, 40); fib2 = fbm(512, W, seed + 31, 2.4, 1, 6)
        f1, f2, _, cr = worley(512, W, 26, 2, seed + 32, 0.95, ((fbm(512, W, seed + 33, 2.2) - 0.5) * 1.2, 0))
        crack = 1 - sstep(0.0, 0.05, f2 - f1)
        wc = lerp(np.array([0.07, 0.058, 0.046]), np.array([0.17, 0.15, 0.125]), fib) * (0.8 + 0.4 * fib2)[..., None]
        wc = lerp(wc, np.array([0.20, 0.12, 0.06]), sstep(0.5, 0.8, fbm(512, W, seed + 34, 2.0))[..., None] * 0.7)
        bc_limb = lerp(wc, np.array([0.03, 0.025, 0.02]), crack * 0.9)
        hmw = fib * 0.5 - crack * 1.5
        nl = normal_from_height(hmw, 5.0)
        limb['rough'] = np.repeat((0.6 + 0.3 * fib)[..., None], 3, -1); limb['ao'] = np.repeat((1 - 0.6 * crack)[..., None], 3, -1); limb['disp'] = np.repeat(fib[..., None], 3, -1)
        uu = np.linspace(0, 1, W, endpoint=False)[None, :]
        du = np.abs((uu - 0.25 + 0.5) % 1.0 - 0.5)
        mn = fbm(1024, W, seed + 40, 2.2); mf = fbm(1024, W, seed + 41, 0.5); mf2 = fbm(1024, W, seed + 42, 1.6)
        ms = sstep(0.56, 0.68, (1 - du * 2.3) * 0.74 + 0.6 * (mn - 0.5) + 0.3 * (0.5 - body['disp'][..., 0]))
        mcol = lerp(np.array([0.02, 0.035, 0.008]), np.array([0.065, 0.09, 0.02]), mf2) * (0.6 + 0.8 * mf)[..., None]
        bc_body = lerp(bc_body, mcol, ms); nb = lerp(nb, normal_from_height(blur(mf, 0.7), 5.0), ms * 0.85)
        body['rough'][..., 0] = lerp(body['rough'][..., 0], 0.96, ms)
    # base band
    bc = bc_body[:512].copy(); n = nb[:512].copy(); r = body['rough'][:512, :, 0].copy(); ao = body['ao'][:512, :, 0].copy()
    yy = np.linspace(0, 1, 512)[:, None]
    mossn = fbm(512, W, seed + 20, 2.2)
    crev = 1 - body['disp'][:512, :, 0]
    moss = sstep(0.58 - 0.3 * yy ** 2, 0.72 - 0.3 * yy ** 2, mossn * (0.3 + 0.9 * yy) + 0.35 * (crev - 0.5)) * moss_amt
    mf = fbm(512, W, seed + 21, 0.5); mf2 = fbm(512, W, seed + 22, 1.6)
    mosscol = lerp(np.array([0.03, 0.055, 0.010]), np.array([0.09, 0.13, 0.025]), mf2) * (0.6 + 0.8 * mf)[..., None]
    bc = lerp(bc, mosscol, moss)
    nm = normal_from_height(blur(mf, 0.7), 5.0)
    n = lerp(n, nm, moss * 0.85)
    r = lerp(r, 0.96, moss)
    stain = sstep(0.70, 1.0, yy + 0.25 * (fbm(512, W, seed + 23, 2.0) - 0.5))
    bc = lerp(bc, bc * np.array([0.5, 0.42, 0.34]) + np.array([0.02, 0.014, 0.009]), stain * 0.85)
    ao = ao * (1 - 0.45 * sstep(0.8, 1.0, yy))
    col = np.vstack([bc_limb, bc_body, bc])
    nn = np.vstack([nl, nb, n]); nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    rough = np.vstack([limb['rough'][..., 0], body['rough'][..., 0], r])
    aoo = np.vstack([limb['ao'][..., 0], body['ao'][..., 0], ao])
    col = np.clip(col, 0.012, 0.8)
    save_rgb(f'{OUT}/T_Veg_{name}_BC.png', srgb8(col))
    save_normal(f'{OUT}/T_Veg_{name}_N.png', nn)
    save_orm(f'{OUT}/T_Veg_{name}_ORM.png', aoo, np.clip(rough, 0.4, 1))
    hm = np.vstack([limb['disp'][..., 0], body['disp'][..., 0], body['disp'][:512, :, 0]])
    Image.fromarray(lin8(hm), 'L').save(f'{OUT}/../../work/{name}_H.png')
    s = srgb8(col).astype(float).mean(-1)
    print(name, 'luma mean/min/max', s.mean(), np.percentile(s, 1), np.percentile(s, 99))

def end_tex():
    A = os.path.join(HERE, '..', '..', 'ThirdParty', 'ambientcg', 'TreeEnd003')
    ld = lambda m: np.asarray(Image.open(f'{A}/TreeEnd003_2K-JPG_{m}.jpg').convert('RGB').resize((1024, 1024), Image.LANCZOS)).astype(np.float64) / 255
    col = s2l(ld('Color')); op = ld('Opacity')[..., 0]; solid = (op > 0.5).astype(float)
    col = dilate_rgb(col, solid, 40) * np.array([0.8, 0.74, 0.66])     # weathered: slightly greyer and darker than fresh-cut
    gy = col.mean(-1, keepdims=True); col = lerp(col, gy * np.array([0.62, 0.61, 0.59]), 0.6)        # silver-grey weathering; rings and checks stay from the scan
    yy_, xx_ = np.mgrid[0:1024, 0:1024]; rad_ = np.hypot(xx_ - 512, yy_ - 512) / 512; ang_ = np.arctan2(yy_ - 512, xx_ - 512)
    chk = sstep(0.93, 1.0, np.cos(ang_ * 9 + 3 * fbm(1024, 1024, 81, 2.2))) * sstep(0.15, 0.5, rad_) * sstep(0.2, 0.6, fbm(1024, 1024, 82, 1.5))
    col = lerp(col, np.array([0.03, 0.026, 0.022]), chk[..., None] * 0.85)       # extra radial drying checks
    g = fbm(1024, 1024, 77, 2.2); col = col * (0.75 + 0.4 * g)[..., None]
    col = lerp(col, np.array([0.10, 0.12, 0.05]), sstep(0.62, 0.78, fbm(1024, 1024, 78, 2.0))[..., None] * 0.5)   # algae staining
    n = dilate_rgb(ld('NormalGL') * 2 - 1, solid, 40); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    save_rgb(f'{OUT}/T_Veg_DeadwoodEnd_BC.png', srgb8(np.clip(col, 0.012, 0.8))); save_normal(f'{OUT}/T_Veg_DeadwoodEnd_N.png', n)
    save_orm(f'{OUT}/T_Veg_DeadwoodEnd_ORM.png', dilate_rgb(ld('AmbientOcclusion'), solid, 40)[..., 0], np.clip(dilate_rgb(ld('Roughness'), solid, 40)[..., 0], 0.5, 1))
    print('end ok')

def variants():
    """round 2 texture variants derived from the sets above: dry grey pine bark, charred bark, dry needle atlas, dark thorn / dead-tree bark, frosted bark."""
    ld = lambda n, t: np.asarray(Image.open(f'{OUT}/T_Veg_{n}_{t}.png').convert('RGBA' if t == 'BC' and 'Needles' in n else 'RGB')).astype(np.float64) / 255
    def cp(src, dst, t): Image.open(f'{OUT}/T_Veg_{src}_{t}.png').save(f'{OUT}/T_Veg_{dst}_{t}.png')
    H = np.asarray(Image.open(f'{OUT}/../../work/PineBark_H.png')).astype(np.float64) / 255
    h, w = H.shape
    # charred: alligator char = deep black glossy plates, grey ash on the ridges, a little unburnt brown low on the base band
    bc = s2l(ld('PineBark', 'BC')); g = bc.mean(-1)
    n1 = fbm(h, w, 5, 2.2); n2 = fbm(h, w, 6, 0.8)
    char = np.stack([0.007 + 0.016 * g, 0.006 + 0.014 * g, 0.006 + 0.013 * g], -1)
    ash = sstep(0.62, 0.85, H + 0.25 * (n1 - 0.5)) * sstep(0.45, 0.7, n2)
    char = lerp(char, np.array([0.16, 0.155, 0.15]) * (0.7 + 0.6 * n2)[..., None], ash * 0.4)
    yy = np.linspace(0, 1, h)[:, None]
    unb = sstep(0.93, 1.0, yy + 0.1 * (n1 - 0.5)) * 0.6
    char = lerp(char, bc * 0.5, unb)
    save_rgb(f'{OUT}/T_Veg_CharredBark_BC.png', srgb8(np.clip(char, 0.006, 0.8)))
    orm = ld('PineBark', 'ORM'); orm[..., 1] = np.clip(0.42 + 0.35 * ash + 0.25 * (1 - H) + 0.1 * n2, 0.3, 1)
    save_rgb(f'{OUT}/T_Veg_CharredBark_ORM.png', lin8(orm)); cp('PineBark', 'CharredBark', 'N')
    # dry needles: brown-orange, thinned
    a = ld('PineNeedles', 'BC'); lum = s2l(a[..., :3]).mean(-1); hh, ww = lum.shape
    t = fbm(hh, ww, 9, 1.8)[..., None]
    col = (lum[..., None] * 4.2) ** 0.8 * lerp(np.array([0.36, 0.17, 0.05]), np.array([0.50, 0.30, 0.11]), t)
    woodm = (a[..., 0] > a[..., 1] * 1.05)[..., None]
    col = np.where(woodm, s2l(a[..., :3]) * np.array([0.8, 0.8, 0.85]), col)
    drop = sstep(0.42, 0.56, fbm(hh, ww, 10, 1.3) * 0.6 + fbm(hh, ww, 11, 0.4) * 0.4)
    alpha = np.where(woodm[..., 0], a[..., 3], a[..., 3] * drop)
    save_rgb(f'{OUT}/T_Veg_PineNeedlesDry_BC.png', srgb8(np.clip(col, 0.01, 0.85)), lin8(alpha))
    save_rgb(f'{OUT}/T_Veg_PineNeedlesDry_SSS.png', srgb8(np.clip(col * 0.5, 0, 1)))
    cp('PineNeedles', 'PineNeedlesDry', 'N')
    o2 = ld('PineNeedles', 'ORM'); o2[..., 1] = np.clip(o2[..., 1] + 0.2, 0, 1); save_rgb(f'{OUT}/T_Veg_PineNeedlesDry_ORM.png', lin8(o2))
    print('variants ok')

if __name__ == '__main__':
    if 'r2' in sys.argv:
        build('PineBarkDry', 'pine_bark', 1200, (0.75, 0.74, 0.72), 0.6, body_tint=(0.80, 0.78, 0.76), moss_amt=0.15, sat=0.22)
        build('DarkBark', 'bark_willow', 1300, (0.55, 0.52, 0.5), 0.75, body_tint=(0.5, 0.47, 0.46), moss_amt=0.25, sat=0.45)
        build('FrostBark', 'jolcham_oak_bark_01', 1400, (1.5, 1.55, 1.65), 1.2, body_tint=(1.25, 1.3, 1.4), moss_amt=0.0, sat=0.2)
        variants(); sys.exit()
    if 'dead' in sys.argv:
        build('Deadwood', 'pine_bark', 1111, (1, 1, 1), 1.0, body_tint=(0.44, 0.43, 0.42), moss_amt=0.6, sat=0.5, dead=True); end_tex(); sys.exit()
    build('PineBark', 'pine_bark', 1000, (0.9, 0.84, 0.76), 0.5, moss_amt=0.5)
    build('OakBark', 'jolcham_oak_bark_01', 1037, (1.0, 1.0, 1.0), 1.0, moss_amt=1.0)
    build('WillowBark', 'bark_willow', 1074, (1.15, 1.15, 1.0), 1.3, body_tint=(1.3, 1.27, 1.15), moss_amt=0.9, sat=0.75)
