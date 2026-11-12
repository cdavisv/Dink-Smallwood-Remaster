"""Impact flash, dust puff, embers, ash, fireball, trail, glow, masks, noise packs."""
import numpy as np
from vfxlib import *
from vfx_fire import RAMP, flame_field, FIRE_P, colourise, curl_warp
from vfx_smoke import _grid, six_way, bake_colour


def _uv(cell, centered=True):
    ys, xs = np.mgrid[0:cell, 0:cell].astype(F32)
    return (xs + 0.5) / cell * 2 - 1, 1 - (ys + 0.5) / cell * 2   # x right, y up, both [-1,1]


def _fire_rgb(T, extra_white=None, soot=None):
    lin = RAMP.lookup_linear(np.clip(T, 0, 1))
    if extra_white is not None:
        lin = lin + extra_white[..., None] * np.array([1.0, 0.86, 0.62], F32)
    return srgb_encode(np.clip(lin, 0, 1))


def _seg_dist(x, y, ax, ay, bx, by):
    px, py = x - ax, y - ay; dx, dy = bx - ax, by - ay
    t = np.clip((px * dx + py * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
    return np.hypot(px - t * dx, py - t * dy), t


# ---------------------------------------------------------------- impact flash
def render_hit_flash(n, cell, seed):
    rng = np.random.default_rng(seed)
    noise = Noise(seed + 1)
    x, y = _uv(cell)
    r = np.hypot(x, y); th = np.arctan2(y, x)
    K = 9
    ang = rng.random(K) * 2 * np.pi
    ln = 0.55 + 0.4 * rng.random(K)
    wd = 0.05 + 0.07 * rng.random(K)
    NS = 18
    sang = rng.random(NS) * 2 * np.pi
    sspd = 0.9 + 1.6 * rng.random(NS)
    slife = 0.22 + 0.34 * rng.random(NS)
    win = window_edges(cell, cell, 0.04)
    frames = []
    for i in range(n):
        t = 0.6 * i / (n - 1)                                # clip covers the first 0.6 of the effect timeline
        endfade = 1.0 - smoothstep(0.42, 0.6, t)
        I = np.zeros((cell, cell), F32)
        # white-hot flash core: instantly bright, decays fast
        b = np.exp(-t / 0.10)
        I += 3.0 * b * np.exp(-(r / (0.09 + 0.10 * t)) ** 2) + 0.8 * b * np.exp(-(r / 0.3) ** 1.2)
        # starburst spikes, shrinking
        for k in range(K):
            dd = np.cos(th - ang[k])                       # only the forward half-plane
            perp = r * np.sqrt(np.clip(1 - dd * dd, 0, 1))
            L = ln[k] * (0.30 + 0.70 * (1 - np.exp(-t * 14))) * (1 - 0.55 * t)
            along = np.clip(1 - r / L, 0, 1) ** 1.6
            prof = np.exp(-(perp / (0.012 + 0.2 * wd[k] * r)) ** 2) * (dd > 0) * along
            I += 2.2 * np.exp(-t / 0.13) * prof
        # expanding shock ring (distorted by looping-free noise for a ragged edge)
        Rr = 0.12 + 0.74 * (1 - np.exp(-5.5 * t))
        rag = noise.fbm(np.cos(th) * 1.5 + 4, np.sin(th) * 1.5 + 4, np.full_like(r, t * 2.0), 3)
        w = 0.035 + 0.05 * t
        ring = np.exp(-((r - Rr * (1 + 0.08 * rag)) / w) ** 2) * (1 - t) ** 1.8
        I += 0.9 * ring * (0.6 + 0.6 * np.clip(rag + 0.5, 0, 1))
        # ballistic spark streaks
        for k in range(NS):
            if t > slife[k]:
                continue
            def pos(tt):
                d = sspd[k] * (1 - np.exp(-4.0 * tt))
                return np.cos(sang[k]) * d * 0.55, np.sin(sang[k]) * d * 0.55 - 0.45 * tt * tt
            x1, y1 = pos(t); x0, y0 = pos(max(t - 0.07, 0))
            dist, tt = _seg_dist(x, y, x0, y0, x1, y1)
            fade = (1 - t / slife[k]) ** 1.5
            I += 2.0 * fade * np.exp(-(dist / 0.014) ** 2) * (0.35 + 0.65 * tt)
        I *= win * endfade
        T = np.clip(I * 0.5, 0, 1.05) * (0.7 + 0.3 * np.exp(-t * 2.5))
        white = np.clip(I - 1.0, 0, 1) * 0.5
        rgb = _fire_rgb(T, white)
        a = np.clip(I * 1.0, 0, 1)
        rgb = bleed_colour(rgb, a)
        frames.append(np.dstack([rgb, a]).astype(F32))
    return frames


# ---------------------------------------------------------------- dust puff
def render_dust(n, cell, seed, W=128, D=28):
    noise = Noise(seed)
    x, y, z = _grid(W, W, D)
    fn = Noise(seed + 7)
    win = window_edges(cell, cell, 0.05)
    out = []
    for i in range(n):
        s = i / (n - 1)
        R = 0.42 + 0.50 * (1 - np.exp(-3.2 * s))
        cy = -0.35 + 0.30 * s
        # noise advected radially outward with the puff (sampling point scaled by R)
        X = x / R; Y = (y - cy) / R; Z = z / R
        n1 = noise.fbm(X * 1.5 + 3.3, Y * 1.5 - s * 0.6, Z * 1.5 + 1.1, 5)
        n01 = np.clip(0.5 + 0.9 * n1, 0, 1)
        rr = np.sqrt((x / 1.15) ** 2 + ((y - cy) / 0.72) ** 2 + (z / 1.0) ** 2) / R
        shell = 0.55 + 0.45 * smoothstep(0.15, 0.85, rr)
        env = np.clip(1 - rr ** 2.2, 0, 1) ** 0.6 * shell
        life = np.exp(-2.6 * s ** 1.4)
        field = env * 1.6 * life + (n01 - 0.5) * 1.25 - (0.30 + 0.5 * s)
        dens = smoothstep(0.0, 0.5, field) * np.clip(env, 0, 1) ** 0.3
        m = six_way(dens, k_light=5.0, k_view=3.6)
        up = {k: resize(v, (cell, cell)) for k, v in m.items()}
        al = up["alpha"]
        # fine silhouette breakup at full res
        xx, yy = _uv(cell)
        fine = fn.fbm(xx * 2.4 / R + 9, yy * 2.4 / R, np.full_like(xx, s * 1.5), 4)
        al = np.clip(al * (0.88 + 0.28 * (0.5 + fine)), 0, 1) * win
        col = srgb_encode(bake_colour(up, albedo=(0.60, 0.54, 0.45)) * 1.15)
        col = bleed_colour(col, al)
        out.append(np.dstack([col, al]).astype(F32))
    return out


# ---------------------------------------------------------------- embers / sparks
def _ember_dot(cell, rng, noise, temp=1.0, size=0.30):
    x, y = _uv(cell)
    ang = rng.random() * 6.28
    xr = x * np.cos(ang) - y * np.sin(ang); yr = x * np.sin(ang) + y * np.cos(ang)
    ar = 1.0 + 0.5 * rng.random()
    off = rng.random(2) * 40
    wob = noise.fbm(x * 2.2 + off[0], y * 2.2 + off[1], np.full_like(x, 0.5), 3)
    d = np.hypot(xr * ar, yr / ar) * (1 + 0.45 * wob)
    body = smoothstep(size, size * 0.55, d)
    crack = noise.fbm(x * 6 + off[1], y * 6 + off[0], np.full_like(x, 1.5), 3)
    Tm = np.clip((1 - (d / size) ** 1.6), 0, 1) * (0.35 + 0.95 * np.clip(0.5 + 1.2 * crack, 0, 1))
    glow = np.exp(-(d / (size * 1.6)) ** 1.3) * 0.5
    T = np.clip(Tm * temp, 0, 1.05) * body + glow * 0.45 * temp
    a = np.clip(body + glow * 0.85, 0, 1) * window_edges(cell, cell, 0.06)
    return T * (a > 0), a


def render_embers(cell, seed):
    """16 cells: 0-7 ember dots, 8-11 spark streaks (+X head), 12-15 cooling ember."""
    rng = np.random.default_rng(seed)
    noise = Noise(seed + 3)
    frames = []
    x, y = _uv(cell)
    win = window_edges(cell, cell, 0.05)
    for k in range(8):
        T, a = _ember_dot(cell, rng, noise, 0.85 + 0.2 * rng.random(), 0.22 + 0.10 * rng.random())
        rgb = bleed_colour(_fire_rgb(T), a)
        frames.append(np.dstack([rgb, a]).astype(F32))
    for k in range(4):
        L = 0.45 + 0.12 * k          # half-length
        wdt = 0.045 + 0.01 * rng.random()
        xx = x + 0.0
        along = np.clip((xx + L) / (2 * L), 0, 1)           # 0 tail .. 1 head
        prof = np.exp(-(y / (wdt * (0.35 + 0.65 * along))) ** 2) * (along ** 2.2) * smoothstep(L + 0.02, L - 0.05, np.abs(xx))
        head = np.exp(-(((xx - L * 0.92) ** 2) + y ** 2) / (0.06 ** 2))
        I = (prof * 1.1 + head * 0.9) * win
        T = np.clip(I * (0.5 + 0.5 * along), 0, 1.05)
        a = np.clip(I * 1.2, 0, 1)
        rgb = bleed_colour(_fire_rgb(T, np.clip(head - 0.6, 0, 1) * 0.4), a)
        frames.append(np.dstack([rgb, a]).astype(F32))
    rng2 = np.random.default_rng(seed + 99)
    state = rng2.bit_generator.state
    for k in range(4):
        rng2.bit_generator.state = state
        T, a = _ember_dot(cell, rng2, noise, 1.0 - 0.22 * k, 0.28)
        rgb = bleed_colour(_fire_rgb(T), a)
        frames.append(np.dstack([rgb, a]).astype(F32))
    return frames


# ---------------------------------------------------------------- ash flakes
def render_ash(cell, seed):
    rng = np.random.default_rng(seed)
    noise = Noise(seed + 5)
    x, y = _uv(cell)
    frames = []
    win = window_edges(cell, cell, 0.06)
    for k in range(16):
        ang = rng.random() * 6.28
        xr = x * np.cos(ang) - y * np.sin(ang); yr = x * np.sin(ang) + y * np.cos(ang)
        rx = 0.40 + 0.30 * rng.random(); ry = rx * (0.22 + 0.40 * rng.random())
        off = rng.random(2) * 60
        e = noise.fbm(x * 3.0 + off[0], y * 3.0 + off[1], np.full_like(x, 0.2), 4)
        e2 = noise.fbm(x * 9.0 + off[1], y * 9.0 + off[0], np.full_like(x, 0.8), 3)
        d = (xr / rx) ** 2 + (yr / ry) ** 2 + 0.85 * e + 0.30 * e2
        # chipped, torn edge: threshold a distorted ellipse
        m = smoothstep(1.0, 0.86, d)
        # curl: fake height from a bent sheet, light from above-left
        h = 0.45 * np.sin((yr / ry) * 2.2 + rng.random() * 3) + 0.35 * np.sin((xr / rx) * 3.0 + rng.random() * 3) + 0.5 * e
        gy, gx = np.gradient(h)
        shade = np.clip(0.6 + (-gx * 0.5 + gy * 0.8) * 200 / cell, 0.2, 1.25)
        fib = 0.45 * noise.fbm(xr * 9 + off[1], yr * 40 + off[0], np.full_like(x, 2.2), 3)   # burnt-paper fibres
        tone = np.clip(0.09 + 0.10 * (0.5 + fib) + 0.08 * rng.random(), 0, 1)
        # some flakes are paler grey ash, some charcoal black
        tone *= 1.0 if k % 3 else 2.2
        rimdark = smoothstep(0.55, 1.0, d)
        lin = (tone * shade * (1 - 0.4 * rimdark))[..., None] * np.array([1.0, 0.97, 0.93], F32)
        a = m * win
        rgb = bleed_colour(srgb_encode(lin), a)
        frames.append(np.dstack([rgb, a]).astype(F32))
    return frames


# ---------------------------------------------------------------- fireball core
def render_fireball_core(n, cell, seed):
    noise = Noise(seed)
    x, y = _uv(cell)
    cx, R = 0.30, 0.27
    p = dict(FIRE_P); p.update(width=0.44, taper=0.74, cool=1.6, erode1=1.15, warp_amp=0.07, base_boost=0.28,
                              fx=3.0, fy=0.85, soft=0.45)
    v = np.clip((cx - x + 0.05) / (cx + 0.95), -0.3, 1.2)      # distance behind the head 0..1
    u = y / 0.95
    win = window_edges(cell, cell, 0.06)
    col, tmp = [], []
    for i in range(n):
        s = i / n
        f = flame_field(u, v, s, noise, p)
        beh = smoothstep(-0.1, 0.12, v)
        for k in ("T", "dens", "soot", "core"):
            f[k] = f[k] * beh
        d = np.hypot(x - cx, y)
        th = np.arctan2(y, x - cx)
        sw = noise.fbm(np.cos(th) * 1.4 + 2 + 0.6 * np.cos(2 * np.pi * s), np.sin(th) * 1.4 + 2 + 0.6 * np.sin(2 * np.pi * s),
                       np.full_like(x, s * 2), 3, pz=2)
        rr = d / (R * (1 + 0.28 * sw))
        sphere = np.clip(1 - rr ** 2.6, 0, 1)
        dens = np.maximum(f["dens"], smoothstep(0, 0.5, sphere))
        inner = noise.fbm(x * 3.5 + 1.0 + 0.5 * np.cos(2 * np.pi * s), y * 3.5 + 0.5 * np.sin(2 * np.pi * s), np.full_like(x, s * 2), 4, pz=2)
        T = np.maximum(f["T"] * 0.85, np.clip((sphere ** 1.1) * (0.85 + 0.45 * inner) * 1.05, 0, 1.05) ** 1.35)
        soot = f["soot"] * (1 - sphere)
        core = np.maximum(f["core"], smoothstep(0.5, 1.0, sphere))
        dens *= win; T = T * win ** 0.5
        f2 = dict(T=T, dens=dens, soot=soot * win, core=core * win)
        rgb = bleed_colour(colourise(f2, desat=0.30), dens)
        col.append(np.dstack([rgb, dens]).astype(F32))
        tmp.append(np.dstack([T, dens, f2["soot"], f2["core"]]).astype(F32))
    return col, tmp


def render_fireball_trail(w, h, seed):
    """Tileable-in-U ribbon texture: U along the trail, V across. Static (scroll in the material)."""
    noise = Noise(seed)
    ys, xs = np.mgrid[0:h, 0:w].astype(F32)
    a = (xs + 0.5) / w              # [0,1) along flow (tiles)
    b = 1 - (ys + 0.5) / h * 2       # [-1,1] across
    PA = 4
    def psi(aa, bb):
        return noise.fbm(aa * PA, bb * 1.2 + 2.0, np.full_like(aa, 0.3), 3, px=PA)
    e = 0.004
    ca = (psi(a, b + e) - psi(a, b - e)) / (2 * e) * 0.016
    cb = -(psi(a + e, b) - psi(a - e, b)) / (2 * e) * 0.016
    a2 = a + ca; b2 = b + cb * 2.0
    # lateral profile: hot axis, flickering cooler edges
    wdt = 0.66
    core = np.clip(1 - (np.abs(b2) / wdt) ** 2, 0, 1) ** 0.7
    n = noise.fbm(a2 * 3, b2 * 5.0 + 5.0, np.full_like(a, 0.9), 4, px=3)
    n2 = noise.fbm(a2 * 12, b2 * 11.0 + 1.0, np.full_like(a, 2.1), 3, px=12)
    n01 = np.clip(0.5 + 0.9 * n + 0.2 * n2, 0, 1)
    field = core * (0.42 + 0.85 * n01) - (1 - n01) * (0.14 + 0.55 * np.abs(b2) ** 1.2)
    dens = smoothstep(0.0, 0.40, field)
    T = np.clip(field * 0.95, 0, 1.05) ** 1.3 * 0.95
    soot = np.clip((1 - T) * dens * np.abs(b2) * 0.6, 0, 1)
    f = dict(T=T, dens=dens, soot=soot, core=smoothstep(0.55, 0.9, T) * dens)
    rgb = bleed_colour(colourise(f, desat=0.18), dens)
    return np.dstack([rgb, dens]).astype(F32), np.dstack([T, dens, soot, f["core"]]).astype(F32)


# ---------------------------------------------------------------- magic glow
def render_glow_sheet(cell, seed):
    noise = Noise(seed)
    x, y = _uv(cell)
    r = np.hypot(x, y); th = np.arctan2(y, x)
    cut = smoothstep(1.0, 0.72, r)
    # 0: halo = truncated inverse-square-ish falloff (Lorentzian^1.5)
    halo = (1 / (1 + (r / 0.16) ** 2) ** 1.5) * cut
    halo = halo / halo.max()
    # 1: sparkle: four diffraction spikes (long) + four short diagonals + core
    def spike(ax, ay, wlen, wwid):
        return np.exp(-np.abs(ax) / wlen) * np.exp(-(ay / (wwid * (0.4 + 3 * np.abs(ax)))) ** 2) * smoothstep(0.0, 0.01, np.abs(ax)) if False else \
            np.exp(-np.abs(ax) / wlen) * np.exp(-(ay / (wwid * (0.25 + 1.2 * np.abs(ax)))) ** 2)
    sp = spike(x, y, 0.28, 0.035) + spike(y, x, 0.28, 0.035)
    xd = (x + y) * 0.7071; yd = (x - y) * 0.7071
    sp += 0.35 * (spike(xd, yd, 0.12, 0.03) + spike(yd, xd, 0.12, 0.03))
    spark = np.clip(sp * 0.9 + 1.2 * np.exp(-(r / 0.05) ** 2) + 0.25 * np.exp(-(r / 0.16) ** 2), 0, 1) * cut
    # 2: soft ring
    ring = (np.exp(-((r - 0.55) / 0.045) ** 2) + 0.12 * np.exp(-((r - 0.55) / 0.2) ** 2)) * cut
    ring *= 0.8 + 0.2 * np.cos(th * 5)
    # 3: swirl wisp: log-spiral arms modulated by fbm
    arm = 0.5 + 0.5 * np.cos(3 * th - 9.0 * np.log(r + 0.05))
    nn = np.clip(0.5 + 0.9 * noise.fbm(x * 2.5, y * 2.5, np.full_like(x, 0.1), 4), 0, 1)
    swirl = (arm ** 1.8) * np.exp(-r * 2.6) * (0.5 + nn) * smoothstep(0.02, 0.2, r) * cut
    swirl = np.clip(swirl * 1.4 + 0.35 * halo, 0, 1)
    return [halo, spark, ring, swirl]


# ---------------------------------------------------------------- masks & LUTs
def soft_masks(cell=256, seed=11):
    x, y = _uv(cell)
    r = np.hypot(x, y)
    A = np.dstack([
        np.clip(1 - r ** 2, 0, 1) ** 2,                                  # R smooth quadratic falloff
        np.exp(-4.5 * r ** 2) * smoothstep(1.0, 0.8, r),                 # G gaussian (windowed)
        np.clip(1 - r, 0, 1),                                            # B linear cone
        np.exp(-((r - 0.62) / 0.12) ** 2) * smoothstep(1.0, 0.85, r)])   # A soft ring
    n = Noise(seed)
    sq = np.clip(1 - (np.abs(x) ** 4 + np.abs(y) ** 4) ** 0.5 / 1.0, 0, 1)
    sq = smoothstep(0, 0.35, sq)
    streak = np.clip(1 - np.hypot(x / 1.0, y * 4.0), 0, 1) ** 1.5
    vert = smoothstep(0, 0.3, 1 - np.abs(y))
    cloud = np.clip(smoothstep(1.0, 0.1, r) * (0.45 + 0.9 * np.clip(0.5 + 0.9 * n.fbm(x * 3 + 7, y * 3, np.full_like(x, 1.), 4), 0, 1)), 0, 1)
    B = np.dstack([sq, streak, vert, cloud])
    return A.astype(F32), B.astype(F32)


def gradient_luts(w=256):
    t = np.linspace(0, 1, w, dtype=F32)
    ss = lambda a, b, x: np.clip((x - a) / (b - a), 0, 1)
    rows = {
        "linear": t, "smoothstep": t * t * (3 - 2 * t), "smootherstep": t ** 3 * (t * (6 * t - 15) + 10),
        "ease_in_quad": t ** 2, "ease_out_quad": 1 - (1 - t) ** 2, "ease_in_cubic": t ** 3, "ease_out_cubic": 1 - (1 - t) ** 3,
        "gaussian_fall": np.exp(-4.5 * t * t), "inverse_square_fall": 1 / (1 + 12 * t * t) * (1 - t ** 4),
        "exp_decay": (np.exp(-4 * t) - np.exp(-4)) / (1 - np.exp(-4)),
        "bell": np.exp(-((t - 0.5) / 0.22) ** 2),
        "triangle": 1 - np.abs(2 * t - 1),
        "attack_decay": np.clip(t * np.exp(1 - t * 6) * 6 / 6 * 1.0, 0, 1) if False else np.clip((t / 0.08) * np.exp(1 - t / 0.08) , 0, 1),
        "age_fade": ss(0, 0.12, t) * (1 - ss(0.55, 1, t)) ** 1.5,
        "flicker_hold": 0.75 + 0.25 * np.sin(2 * np.pi * 3 * t) * np.sin(2 * np.pi * 7 * t + 1.3),
        "flash_pop": np.exp(-t / 0.12),
    }
    names = list(rows)
    return names, np.stack([np.clip(rows[k], 0, 1) for k in names]).astype(F32)


def blackbody_lut(w=256, h=4):
    """RGB = sRGB tone-mapped blackbody colour; A = linear emissive multiplier / 4."""
    t = np.linspace(0, 1, w, dtype=F32)
    ldr = srgb_encode(RAMP.lookup_linear(t))
    mult = RAMP.lookup_linear(t, hdr=True).max(-1)
    a = np.clip(mult / 4.0, 0, 1)
    img = np.concatenate([ldr, a[:, None]], 1).astype(F32)
    return np.repeat(img[None], h, 0)


# ---------------------------------------------------------------- noise packs
def blue_noise(size, seed, iters=4):
    rng = np.random.default_rng(seed)
    n = rng.random((size, size)).astype(F32)
    for _ in range(iters):
        hp = n - fft_blur(n, 1.5)
        rank = np.argsort(np.argsort(hp.ravel()))
        n = (rank.reshape(size, size) / (size * size - 1)).astype(F32)
        # re-inject structure to avoid collapsing to white
        n = 0.85 * n + 0.15 * rng.random((size, size)).astype(F32)
    rank = np.argsort(np.argsort((n - fft_blur(n, 1.5)).ravel()))
    return (rank.reshape(size, size) / (size * size - 1)).astype(F32)


def noise_packs(size=512, seed=2026):
    n = Noise(seed)
    ys, xs = np.mgrid[0:size, 0:size].astype(F32) / size
    z = np.full((size, size), 0.31, F32)
    def fbmt(freq, oct, sd=0, ridge=False, gain=0.5):
        nn = Noise(seed + sd)
        return nn.fbm(xs * freq, ys * freq, z, oct, px=freq, py=freq, ridge=ridge, gain=gain)
    perlin = np.clip(0.5 + 0.6 * fbmt(4, 6), 0, 1)
    f1a, f2a = worley_tile(size, 8, seed + 1)
    f1b, f2b, cid = worley_tile(size, 6, seed + 2, want_id=True)
    w_inv = np.clip(1 - f1a, 0, 1)
    edge = np.clip((f2a - f1a) * 1.8, 0, 1)
    # Perlin-Worley (cloud base): perlin remapped against inverse worley
    pw = np.clip((perlin - (1 - w_inv) * 0.9) / (1 - (1 - w_inv) * 0.9 + 1e-3), 0, 1)
    A = np.dstack([perlin, w_inv, edge, pw])
    # B: curl-noise vector pack
    pot = fbmt(3, 4, 3, gain=0.4) * 0.5
    vx, vy = curl_from_potential(pot * size / 8.0)
    m = np.max(np.hypot(vx, vy)) + 1e-9
    mag = np.hypot(vx, vy) / m
    B = np.dstack([0.5 + 0.5 * vx / m, 0.5 + 0.5 * vy / m, mag, np.clip(0.5 + 0.9 * pot, 0, 1)])
    # C: ridged turbulence, large worley F1, small worley F1, cell id
    rid = np.clip(fbmt(5, 6, 5, ridge=True), 0, 1)
    rid = np.clip((rid - rid.min()) / (rid.max() - rid.min()), 0, 1) ** 1.6
    C = np.dstack([rid, np.clip(1 - f1b * 0.9, 0, 1), np.clip(1 - worley_tile(size, 24, seed + 3)[0], 0, 1), cid])
    return A.astype(F32), B.astype(F32), C.astype(F32)
