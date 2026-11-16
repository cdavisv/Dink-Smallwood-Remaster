#!/usr/bin/env python3
"""Blood-soaked textures for the corpses that clips_bonca.py / clips_monsters.py freeze from the death pose.

The 1997 pictures of the dead bonca (551-559) and the dead slayer (645) show the body dark with blood, in a pool. The
corpse mesh keeps the living animal's UVs, so the soak is laid in UV space: large wet patches (about two thirds of the
skin), runs and spatter between them, the base colour showing through at the edges. Roughness drops where it is wet.

The pool is its own picture, T_<Name>_PR_BloodPool_BC.png (RGBA, seen from straight above, +X of the picture = the
animal's forward): a lobed pool that reaches past the body on every side, runs and fingers at its rim, and a ring of
dozens of thrown drops and streaks out to a body-width beyond it, in the saturated red of the 1997 pictures. The game
projects it on the ground and the grass as the class row's corpse decal.

    python3 -I corpse_blood.py            writes T_<Name>_PR_Corpse_BC.png, T_<Name>_PR_Corpse_ORM.png and T_<Name>_PR_BloodPool_BC.png
"""
import os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); UNC = os.path.dirname(HERE)
# family, name, 1997 picture (seed), share of the skin soaked, base colour the corpse wears (all three boncas leave the brown body of 551-559)
WHO = (('bonca_gray', 'Bonca', 551, 0.56, 'T_Bonca_PR_Brown_BC.png'), ('slayer', 'Slayer', 645, 0.60, 'T_Slayer_PR_BC.png'))


def noise(size, cell, rng):
    small = rng.random((size // cell + 2, size // cell + 2)).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((size + 2 * cell, size + 2 * cell), Image.BICUBIC)
    return np.asarray(im, np.float32)[:size, :size] / 255.0


def soak(size, cover, seed):
    rng = np.random.default_rng(seed)
    n = 0.5 * noise(size, 256, rng) + 0.3 * noise(size, 96, rng) + 0.15 * noise(size, 32, rng) + 0.05 * noise(size, 8, rng)
    cut = np.quantile(n, 1.0 - cover)
    wet = np.clip((n - cut) / 0.035 + 0.5, 0, 1)                       # patches with a short soft edge
    spat = (noise(size, 6, rng) > 0.78).astype(np.float32) * (noise(size, 64, rng) > 0.45)   # thrown drops between them
    spat = np.asarray(Image.fromarray((spat * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255.0
    return np.clip(np.maximum(wet, spat * 0.9), 0, 1), n


def pool(size, seed, aspect=1.28):
    """RGBA float picture of the pool: alpha 1 in the pool and on every drop."""
    rng = np.random.default_rng(seed * 7 + 1)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32); cx = cy = size / 2.0
    dx = (xx - cx) / (size * 0.5); dy = (yy - cy) / (size * 0.5) * aspect; r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    # the rim: a few big lobes, fingers between them, fine wobble
    rim = np.full_like(r, 0.50)
    for k, amp in ((2, 0.050), (3, 0.060), (5, 0.050), (8, 0.030), (13, 0.022), (21, 0.012)):
        rim += amp * np.sin(k * th + rng.uniform(0, 6.283))
    rim += 0.045 * (noise(size, 48, rng) - 0.5) + 0.02 * (noise(size, 12, rng) - 0.5)
    a = np.clip((rim - r) * size / 6.0 + 0.5, 0, 1)
    img = Image.fromarray((a * 255).astype(np.uint8)); from PIL import ImageDraw; dr = ImageDraw.Draw(img)
    for _ in range(26):                                             # runs: fingers that leave the rim and thin out
        t = rng.uniform(0, 6.283); r0 = 0.47; ln = rng.uniform(0.06, 0.20); w = rng.uniform(5, 13) * size / 1024
        for q in np.linspace(0, 1, 14):
            rr = r0 + ln * q; px = cx + np.cos(t) * rr * size * 0.5; py = cy + np.sin(t) * rr * size * 0.5 / aspect; ww = w * (1 - 0.75 * q)
            dr.ellipse((px - ww, py - ww, px + ww, py + ww), fill=255)
        ww = w * 0.7; dr.ellipse((px - ww, py - ww, px + ww, py + ww), fill=255)                      # the bead at the end of the run
    for _ in range(150):                                            # thrown drops: many small near the rim, fewer and farther out
        t = rng.uniform(0, 6.283); rr = 0.56 + abs(rng.normal(0, 0.16)); rad = max(2.0, rng.gamma(2.0, 2.6)) * size / 1024
        if rr > 0.97: continue
        px = cx + np.cos(t) * rr * size * 0.5; py = cy + np.sin(t) * rr * size * 0.5 / aspect; el = rng.uniform(1.0, 2.2)      # drawn out along its flight
        d = Image.new('L', (int(rad * el * 2 + 4), int(rad * 2 + 4)), 0); ImageDraw.Draw(d).ellipse((1, 1, d.width - 2, d.height - 2), fill=255)
        d = d.rotate(-np.degrees(np.arctan2(np.sin(t) / aspect, np.cos(t))), expand=True, resample=Image.BICUBIC); img.paste(255, (int(px - d.width / 2), int(py - d.height / 2)), d)
    a = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8 * size / 1024)), np.float32) / 255.0
    a = np.clip((a - 0.35) / 0.3, 0, 1)
    # colour: saturated red, darker where it stands deep (middle) and at a thin dried line along the rim
    deep = np.clip(1 - r / 0.42, 0, 1) * (0.6 + 0.4 * noise(size, 96, rng)); edge = np.clip(1 - np.abs(rim - r) * size / 14.0, 0, 1) * (r > 0.2)
    red = 0.60 - 0.20 * deep - 0.12 * edge + 0.05 * (noise(size, 24, rng) - 0.5)
    rgb = np.stack([red, 0.016 + 0.0 * red, 0.012 + 0.0 * red], -1)
    return np.dstack([rgb, a])


def grit(size, seed):
    """The dead stone giant (825) bleeds nothing: around the heap lies dark grit, a dusting of crushed stone thick under
    the blocks and thinning outwards, with chips thrown clear. RGBA float picture, seen from above."""
    from PIL import ImageDraw
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32); r = np.hypot((xx - size / 2) / (size * 0.5), (yy - size / 2) / (size * 0.5) * 1.25)
    n = 0.6 * noise(size, 96, rng) + 0.4 * noise(size, 20, rng); dust = np.clip((0.74 + 0.25 * (n - 0.5) - r) / 0.30, 0, 1) ** 1.2 * (0.55 + 0.45 * noise(size, 6, rng))
    img = Image.new('L', (size, size), 0); dr = ImageDraw.Draw(img)
    for _ in range(900):
        t = rng.uniform(0, 6.283); rr = abs(rng.normal(0.48, 0.24)); rad = max(1.5, rng.gamma(1.8, 2.4)) * size / 1024
        if rr > 0.96: continue
        px = size / 2 + np.cos(t) * rr * size * 0.5; py = size / 2 + np.sin(t) * rr * size * 0.5 / 1.25; k = rng.uniform(0.6, 1.0)
        dr.polygon([(px + rad * np.cos(a + t) * rng.uniform(0.6, 1.2), py + rad * k * np.sin(a + t) * rng.uniform(0.6, 1.2)) for a in np.linspace(0, 6.283, 6)[:-1]], fill=255)
    chips = np.asarray(img.filter(ImageFilter.GaussianBlur(0.6 * size / 1024)), np.float32) / 255.0
    a = np.clip(np.maximum(dust * 0.85, chips * 0.97), 0, 1)
    tone = 0.075 + 0.04 * noise(size, 10, rng); rgb = np.stack([tone * 1.05, tone * 0.82, tone * 0.60], -1) * (1 - 0.35 * chips[..., None])
    return np.dstack([rgb, a])


for fam, name, seq, cover, wears in WHO:
    d = os.path.join(UNC, fam, name)
    bc = np.asarray(Image.open(os.path.join(d, wears)).convert('RGB'), np.float32) / 255.0
    orm = np.asarray(Image.open(os.path.join(d, 'T_%s_PR_ORM.png' % name)).convert('RGB'), np.float32) / 255.0
    size = bc.shape[0]
    m, n = soak(size, cover, seq)
    # fresh blood over skin: dark where it stands thick, a little brighter at thin edges; dried rims darker still
    thick = np.clip((n - np.quantile(n, 1.0 - cover * 0.6)) / 0.1, 0, 1)
    blood = np.stack([0.56 - 0.24 * thick, 0.014 + 0.0 * thick, 0.010 + 0.0 * thick], -1)
    out = bc * (1 - 0.94 * m[..., None]) + blood * (0.94 * m[..., None])
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(d, 'T_%s_PR_Corpse_BC.png' % name))
    o2 = orm.copy(); o2[..., 1] = orm[..., 1] * (1 - m) + (0.16 + 0.12 * (1 - thick)) * m; o2[..., 2] = orm[..., 2] * (1 - m)
    Image.fromarray((np.clip(o2, 0, 1) * 255).astype(np.uint8)).save(os.path.join(d, 'T_%s_PR_Corpse_ORM.png' % name))
    pl = pool(1024, seq)
    Image.fromarray((np.clip(pl, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(d, 'T_%s_PR_BloodPool_BC.png' % name))
    print('%s: %d px, blood on %.0f%% of the skin texture; pool covers %.0f%% of its picture' % (name, size, 100 * float((m > 0.5).mean()), 100 * float((pl[..., 3] > 0.5).mean())))

gd = os.path.join(UNC, 'stone_giant', 'Stone_Giant'); gp = grit(1024, 825)
Image.fromarray((np.clip(gp, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(gd, 'T_Stone_Giant_PR_Grit_BC.png'))
print('Stone_Giant: grit covers %.0f%% of its picture (no blood: 825 has none)' % (100 * float((gp[..., 3] > 0.3).mean())))
