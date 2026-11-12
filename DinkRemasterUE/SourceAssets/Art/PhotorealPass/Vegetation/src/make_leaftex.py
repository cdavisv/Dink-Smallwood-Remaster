"""Procedural single-leaf textures (numpy) used as sources for modelled sprays: willow leaf, grass blade strip etc."""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from texlib import *
W = os.path.join(HERE, '..', 'work')

def lanceolate(name, w=128, h=768, seed=5, widest=0.38, col0=(0.07, 0.15, 0.03), col1=(0.12, 0.22, 0.045), rib=(0.28, 0.36, 0.14), serr=0.0, nveins=22, tipy=None):
    y, x = np.mgrid[0:h, 0:w].astype(float); t = 1 - y / (h - 1); s = (x / (w - 1) - 0.5) * 2
    prof = np.where(t < widest, np.sin(0.5 * np.pi * (t / widest)) ** 0.75, np.cos(0.5 * np.pi * ((t - widest) / (1 - widest))) ** 1.25)
    prof = prof * 0.92 * (1 + serr * np.sin(t * 150))
    d = prof - np.abs(s)
    alpha = sstep(-0.02, 0.03, d)
    n1 = fbm(h, w, seed, 2.0); n2 = fbm(h, w, seed + 1, 1.0)
    col = lerp(np.array(col0), np.array(col1), n1)
    col = col * (0.85 + 0.3 * n2)[..., None]
    # veins: midrib + pinnate laterals
    mid = np.exp(-(s / 0.07) ** 2)
    lat = 0.5 + 0.5 * np.cos((t - np.abs(s) * 0.55) * nveins * 2 * np.pi)
    lat = sstep(0.93, 1.0, lat) * (1 - sstep(0.0, 1.0, np.abs(s) / (prof + 1e-3)) ** 2)
    vein = np.clip(mid + 0.45 * lat, 0, 1)
    col = lerp(col, np.array(rib), vein * 0.8)
    edge = 1 - sstep(0.0, 0.12, d)
    col = lerp(col, col * np.array([1.15, 1.0, 0.6]), edge * 0.5)
    hm = -np.abs(s) * 0.5 - 0.6 * mid + 0.25 * lat + 0.15 * n2
    nrmm = normal_from_height(blur(hm, 1.2), 14.0, wrap=False)
    rgb = dilate_rgb(col, alpha, 12)
    save_rgb(f'{W}/{name}_c.png', srgb8(rgb), lin8(alpha)); save_normal(f'{W}/{name}_n.png', nrmm)
    Image.fromarray(lin8(alpha), 'L').save(f'{W}/{name}_a.png')

if __name__ == '__main__':
    lanceolate('willow_leaf', seed=5)
    lanceolate('willow_leaf_y', seed=9, col0=(0.20, 0.24, 0.035), col1=(0.34, 0.33, 0.05), rib=(0.45, 0.42, 0.16))
    lanceolate('nettle_leaf', w=256, h=512, seed=12, widest=0.3, col0=(0.035, 0.10, 0.02), col1=(0.07, 0.16, 0.03), rib=(0.16, 0.26, 0.09), serr=0.08, nveins=9)
    print('ok')
