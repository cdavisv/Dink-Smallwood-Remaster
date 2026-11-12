#!/usr/bin/env python3
"""Synthesise the small support textures of the environment materials (numpy + Pillow only, deterministic):
T_Env_WaterNormal.png (tileable wind-ripple normal, OpenGL green-up), T_Env_MaskLayerA.png (pure red layer mask for
single-layer terrain instances) and T_Env_MacroDefault.png (RGB low-frequency variation for sets without a Macro map)."""
from pathlib import Path
import numpy as np
from PIL import Image
OUT = Path(__file__).resolve().parent / 'Textures'
OUT.mkdir(exist_ok=True)

def band_noise(n, lo, hi, seed, aniso=1.0, power=1.0):
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((n, n)))
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.fftfreq(n)[None, :] * n
    r = np.sqrt((fx * aniso) ** 2 + fy ** 2)
    w = np.where((r >= lo) & (r <= hi), 1.0 / np.maximum(r, 1.0) ** power, 0.0)
    h = np.real(np.fft.ifft2(f * w))
    return (h - h.mean()) / h.std()

def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.dstack([-dx, dy, np.ones_like(h)])  # OpenGL: +G = up in the image (towards row 0)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (np.clip(n * 0.5 + 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)

N = 1024
# Wind ripples: elongated crests (anisotropic band) over a broader swell and fine capillary chop.
h = 1.0 * band_noise(N, 3, 10, 11, aniso=0.55, power=1.2) + 0.55 * band_noise(N, 10, 40, 12, aniso=0.6, power=1.0) \
    + 0.22 * band_noise(N, 40, 140, 13, aniso=0.8, power=0.8)
# sharpen crests a little (trochoidal look)
h = np.sign(h) * np.abs(h) ** 0.9
Image.fromarray(normal_from_height(h, 2.2)).save(OUT / 'T_Env_WaterNormal.png')
Image.fromarray(np.dstack([np.full((8, 8), 255, np.uint8), np.zeros((8, 8), np.uint8), np.zeros((8, 8), np.uint8)])).save(OUT / 'T_Env_MaskLayerA.png')
Image.fromarray(np.zeros((8, 8, 3), np.uint8)).save(OUT / 'T_Env_Black.png')  # default of the per-layer emissive mask
M = 512
def unit(x):
    lo, hi = np.percentile(x, 1), np.percentile(x, 99)
    return np.clip((x - lo) / (hi - lo), 0, 1)
macro = np.dstack([unit(band_noise(M, 1, 4, 21, power=1.5)), unit(band_noise(M, 3, 12, 22, power=1.2)), unit(band_noise(M, 10, 40, 23, power=1.0))])
Image.fromarray((macro * 255 + 0.5).astype(np.uint8)).save(OUT / 'T_Env_MacroDefault.png')
print('wrote', sorted(p.name for p in OUT.iterdir()))
