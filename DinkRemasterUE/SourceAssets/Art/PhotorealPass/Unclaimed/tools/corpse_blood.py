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
WHO = (('bonca_gray', 'Bonca', 551, 0.56, 'T_Bonca_PR_Brown_BC.png'), ('slayer', 'Slayer', 645, 0.60, 'T_Slayer_PR_BC.png'),
       # the goblins of 765 / 785 / 805 lie drenched: more of the skin and the clothes soaked than the animals
       ('goblin_hammer', 'Goblin_Hammer', 765, 0.68, 'T_Goblin_Hammer_PR_BC.png'), ('goblin_horned', 'Goblin_Horned', 785, 0.68, 'T_Goblin_Horned_PR_BC.png'),
       ('goblin_soldier', 'Goblin_Soldier', 805, 0.66, 'T_Goblin_Soldier_PR_BC.png'),
       # the torn dragon of 212 / 216 is red almost all over; its tears take the raw flesh painted into the texture's corner (clips_monsters.py tear)
       ('dragon', 'Dragon', 212, 0.78, 'T_Dragon_PR_BC.png'))


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
    # colour: not one flat red. Where it stands deep (the middle, in blotches) it is dark, almost black-red; the body of the pool
    # is saturated red; along the rim runs a band that has begun to dry, browner and duller; the thrown drops are the dry tone
    inside = np.clip((rim - r) * size / 40.0, 0, 1)                 # 0 at the rim, 1 a few centimetres in
    blot = np.clip(noise(size, 96, rng) * 1.9 - 0.62, 0, 1) * inside   # standing blood in blotches all over the pool, not only under the body
    # (16 Nov, seen in the game: a pool that is bright red all over reads as spilled paint in full sun.) Blood is bright only where
    # it lies thin: a hand's width inside the rim it already stands and darkens, and it is darkest in the blotches and the middle
    stand = np.clip((rim - r) / 0.13, 0, 1) ** 0.8 * (0.80 + 0.35 * (noise(size, 40, rng) - 0.5))
    deep = np.clip(np.maximum(np.clip(1 - r / 0.36, 0, 1) ** 0.7 * 0.9, 0.62 * stand) + 0.55 * blot, 0, 1)
    edge = np.clip(1 - np.abs(rim - r) * size / 55.0, 0, 1) * (r > 0.2)
    out = np.clip((r - rim) * size / 10.0, 0, 1)                    # 1 outside the pool: drops and runs
    dry = np.clip(edge + 0.85 * out, 0, 1)
    red = 0.53 - 0.38 * deep - 0.17 * dry * (1 - deep) + 0.05 * (noise(size, 24, rng) - 0.5)
    rgb = np.stack([red, 0.012 + 0.034 * dry, 0.009 + 0.014 * dry], -1)
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
    if not os.path.exists(os.path.join(d, wears)): continue
    bc = np.asarray(Image.open(os.path.join(d, wears)).convert('RGB'), np.float32) / 255.0
    orm = np.asarray(Image.open(os.path.join(d, 'T_%s_PR_ORM.png' % name)).convert('RGB'), np.float32) / 255.0
    size = bc.shape[0]
    m, n = soak(size, cover, seq)
    wj = os.path.join(d, 'corpse_wing_uv.json')
    if os.path.exists(wj):                                          # the wing that still stands (clips_monsters.py tear): pale skin, blood from the root
        import json; from PIL import ImageDraw
        wt = Image.new('L', (size, size), 0); dr = ImageDraw.Draw(wt)
        for t, u0, v0, u1, v1, u2, v2 in json.load(open(wj))['triangles']:
            dr.polygon([(u0 * size, (1 - v0) * size), (u1 * size, (1 - v1) * size), (u2 * size, (1 - v2) * size)], fill=int(1 + 254 * min(1.0, max(0.0, t))))
        wt = np.asarray(wt, np.float32); on = wt > 0; t = np.clip((wt - 1) / 254.0, 0, 1)
        rngw = np.random.default_rng(seq + 5); streak = noise(size, 20, rngw) * 0.6 + noise(size, 6, rngw) * 0.4
        keep = np.clip((0.58 - t) / 0.34 + (streak - 0.5) * 1.0, 0, 1)       # 1 at the root, runs and spatter to about half way, none at the tips
        spat = ((noise(size, 5, rngw) > 0.80) & (noise(size, 50, rngw) > 0.5)).astype(np.float32) * 0.8
        m = np.where(on, np.clip(np.maximum(m * keep, spat * (t < 0.85)), 0, 1), m)
        print('%s: standing wing %.1f%% of the texture, %.0f%% of it bloodied' % (name, 100 * float(on.mean()), 100 * float((m[on] > 0.5).mean())))
    # fresh blood over skin: dark where it stands thick, a little brighter at thin edges; dried rims darker still
    thick = np.clip((n - np.quantile(n, 1.0 - cover * 0.6)) / 0.1, 0, 1)
    # (16 Nov, seen in the game beside the darker pools: a body at 0.54 red with a 0.16 roughness reads as a toy dipped in paint.)
    # Blood on a body is as dark as the pool it lies in, brighter only where it is thin, and it is tacky, not lacquer
    blood = np.stack([0.41 - 0.27 * thick + 0.05 * (noise(size, 24, np.random.default_rng(seq + 11)) - 0.5), 0.012 + 0.0 * thick, 0.009 + 0.0 * thick], -1)
    out = bc * (1 - 0.94 * m[..., None]) + blood * (0.94 * m[..., None])
    if name == 'Dragon':                                            # raw flesh for the tear faces: UV (0.010, 0.990) = the top-left corner
        k = size // 40; rng2 = np.random.default_rng(216); fl = rng2.random((k, k)).astype(np.float32)
        out[:k, :k] = np.stack([0.50 + 0.18 * fl, 0.030 + 0.03 * fl, 0.028 + 0.02 * fl], -1)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(d, 'T_%s_PR_Corpse_BC.png' % name))
    o2 = orm.copy(); o2[..., 1] = orm[..., 1] * (1 - m) + (0.24 + 0.20 * (1 - thick)) * m; o2[..., 2] = orm[..., 2] * (1 - m)
    Image.fromarray((np.clip(o2, 0, 1) * 255).astype(np.uint8)).save(os.path.join(d, 'T_%s_PR_Corpse_ORM.png' % name))
    pl = pool(1024, seq)
    Image.fromarray((np.clip(pl, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(d, 'T_%s_PR_BloodPool_BC.png' % name))
    print('%s: %d px, blood on %.0f%% of the skin texture; pool covers %.0f%% of its picture' % (name, size, 100 * float((m > 0.5).mean()), 100 * float((pl[..., 3] > 0.5).mean())))

gd = os.path.join(UNC, 'stone_giant', 'Stone_Giant'); gp = grit(1024, 825)
Image.fromarray((np.clip(gp, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(gd, 'T_Stone_Giant_PR_Grit_BC.png'))
print('Stone_Giant: grit covers %.0f%% of its picture (no blood: 825 has none)' % (100 * float((gp[..., 3] > 0.3).mean())))
