"""numpy-only PBR-ish preview renderer (GGX + lambert) for tangent-space OpenGL normals."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from sm_lib import srgb_to_lin, F32

LIGHT = np.array([-0.55, 0.50, 0.66], F32)
LIGHT /= np.linalg.norm(LIGHT)


def _tonemap(x):
    x = x * 1.05
    x = x / (1 + 0.18 * x)
    return np.clip(x, 0, 1) ** (1 / 2.2)


def shade(alb_srgb, n, rough, ao, N0=None, light=LIGHT, exposure=1.9):
    """alb_srgb (h,w,3) 0..255, n (h,w,3) shading normal, V=(0,0,1) (or N0-relative view)."""
    a = srgb_to_lin(alb_srgb)
    L = light / np.linalg.norm(light)
    ndl = np.clip((n * L).sum(-1), 0, 1)
    V = np.array([0, 0, 1], F32)
    H = (L + V) / np.linalg.norm(L + V)
    ndh = np.clip((n * H).sum(-1), 0, 1)
    ndv = np.clip(n[..., 2], 0.05, 1)
    al = np.maximum(rough, 0.2) ** 2
    d = al * al / (np.pi * ((ndh ** 2) * (al * al - 1) + 1) ** 2)
    spec = d * 0.04 * 0.25 / np.maximum(0.3 + 0.7 * ndv, 0.1)
    # soft sky ambient, occluded
    sky = 0.30 + 0.20 * n[..., 1]
    col = a * (ndl[..., None] * exposure * 0.85 + (sky * ao)[..., None] * 1.0) * (0.5 + 0.5 * ao[..., None])
    col += (spec * ndl * exposure)[..., None]
    return _tonemap(col)


def render_plane(m, tiles=1):
    alb, n, rough, ao = m["alb"], m["normal"], m["rough"], m["ao"]
    if tiles > 1:
        t = (tiles, tiles)
        alb = np.tile(alb, t + (1,))
        n = np.tile(n, t + (1,))
        rough = np.tile(rough, t)
        ao = np.tile(ao, t)
    return (shade(alb, n, rough, ao) * 255 + 0.5).astype(np.uint8)


def render_sphere(m, size=512, repeat=2.0):
    alb, nm, rough, ao = m["alb"], m["normal"], m["rough"], m["ao"]
    h, w = alb.shape[:2]
    yy, xx = np.mgrid[0:size, 0:size].astype(F32)
    x = (xx + 0.5) / size * 2 - 1
    y = -((yy + 0.5) / size * 2 - 1)
    r2 = x * x + y * y
    inside = r2 < 0.97
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    N0 = np.stack([x, y, z], -1)
    # planar-ish projection with latitude-aware u to reduce stretching
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(y, -1, 1))
    u = (lon / np.pi * 0.5 + 0.5) * repeat * 0.9
    v = (0.5 - lat / np.pi) * repeat * 0.9
    px = (u % 1.0) * w
    py = (v % 1.0) * h
    from sm_lib import sample
    A = sample(alb, px, py)
    Nt = sample(nm, px, py)
    R = sample(rough, px, py)
    AO = sample(ao, px, py)
    T = np.stack([z, np.zeros_like(z), -x], -1)
    T /= np.maximum(np.linalg.norm(T, axis=-1, keepdims=True), 1e-4)
    B = np.cross(N0, T)  # points up-ish
    n = Nt[..., 0:1] * T + Nt[..., 1:2] * B + Nt[..., 2:3] * N0
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-4)
    # light in view space (same direction as plane preview), V=(0,0,1)
    L = LIGHT
    ndl = np.clip((n * L).sum(-1), 0, 1)
    a = srgb_to_lin(A)
    Hh = (L + np.array([0, 0, 1], F32)); Hh /= np.linalg.norm(Hh)
    ndh = np.clip((n * Hh).sum(-1), 0, 1)
    al = np.maximum(R, 0.2) ** 2
    d = al * al / (np.pi * ((ndh ** 2) * (al * al - 1) + 1) ** 2)
    sky = 0.28 + 0.22 * n[..., 1]
    col = a * (ndl[..., None] * 1.7 + (sky * AO)[..., None]) * (0.5 + 0.5 * AO[..., None])
    col += (d * 0.01 * 1.7 * ndl)[..., None] * 25
    img = _tonemap(col)
    out = np.full((size, size, 3), 0.07, F32)
    out[inside] = img[inside]
    return (out * 255 + 0.5).astype(np.uint8)


def label(img, text):
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.load_default(size=20)
    except TypeError:
        f = ImageFont.load_default()
    d.rectangle([0, 0, im.width, 28], fill=(0, 0, 0))
    d.text((8, 3), text, fill=(240, 240, 240), font=f)
    return np.asarray(im)


def preview_sheet(m, title):
    """1536x1024: left lit 2x2 repeat (tiling check); right sphere, albedo crop, normal crop."""
    plane = render_plane(m, 2)  # 2x2 of the (1024) variant
    left = np.asarray(Image.fromarray(plane).resize((1024, 1024), Image.LANCZOS))
    sph = render_sphere(m, 512)
    a = m["alb"]
    s = a.shape[0]
    c = min(512, s)
    crop = np.clip(a[:c, :c] + 0.5, 0, 255).astype(np.uint8)
    nrm = ((m["normal"][:c, :c] * 0.5 + 0.5) * 255).astype(np.uint8)
    right = np.concatenate([sph, np.asarray(Image.fromarray(crop).resize((512, 256), Image.LANCZOS)),
                            np.asarray(Image.fromarray(nrm).resize((512, 256), Image.LANCZOS))], 0)
    img = np.concatenate([left, right], 1)
    return label(img, title)
