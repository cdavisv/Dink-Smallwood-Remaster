"""Turn atlas render passes (work/<src>_{bc,n,aux,sss}.png) into Export/Textures/T_Veg_<Name>_{BC,N,ORM,SSS}.png.
usage: compose_atlas.py Name src [alpha_gain] [size]"""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from texlib import *
def compose(name, src, again=1.5, size=None, nflat=0.25, dil=14):
    W = os.path.join(HERE, '..', 'work'); OUT = os.path.join(HERE, '..', 'Export', 'Textures')
    ld = lambda m: np.asarray(Image.open(f'{W}/{src}_{m}.png').convert('RGBA')).astype(np.float64) / 255
    bc, n, aux, sss = ld('bc'), ld('n'), ld('aux'), ld('sss')
    a = bc[..., 3]; solid = (a > 0.35).astype(float)
    rgb = dilate_rgb(bc[..., :3], solid, dil)
    alpha = np.clip(a * again, 0, 1)
    nn = n[..., :3] * 2 - 1
    nn = dilate_rgb(nn, solid, dil)
    nn = nn * (1 - nflat) + np.array([0, 0, 1.0]) * nflat
    nn[..., 2] = np.abs(nn[..., 2]) + 0.05
    nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    ax = dilate_rgb(aux[..., :3], solid, dil)
    ss = dilate_rgb(sss[..., :3], solid, dil)
    def out(arr, path, mode):
        im = Image.fromarray(arr, mode)
        if size and size != im.size[0]: im = im.resize((size, size * im.size[1] // im.size[0]), Image.LANCZOS)
        im.save(path)
    out(np.dstack([lin8(rgb), lin8(alpha)]), f'{OUT}/T_Veg_{name}_BC.png', 'RGBA')
    out(lin8(nn * 0.5 + 0.5), f'{OUT}/T_Veg_{name}_N.png', 'RGB')
    out(lin8(np.stack([np.clip(ax[..., 0] * 0.8 + 0.2, 0, 1), ax[..., 1], np.zeros_like(a)], -1)), f'{OUT}/T_Veg_{name}_ORM.png', 'RGB')
    out(lin8(ss), f'{OUT}/T_Veg_{name}_SSS.png', 'RGB')
    lum = (rgb[solid > 0] * 255).mean()
    print(name, 'coverage', solid.mean(), 'mean srgb', lum)
if __name__ == '__main__':
    compose(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.5, int(sys.argv[4]) if len(sys.argv) > 4 else None)
