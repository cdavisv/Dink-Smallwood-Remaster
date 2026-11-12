"""Procedural tiling PBR sets for the SCR_440 two-storey house (host Python 3, numpy + Pillow).

Deterministic (seed 440). No downloaded images, no generative image models.
Writes Textures/T_S440_<Name>_{BC,N,ORM,H}.png and Textures/rubble_stones.json.

Conventions (match the existing Stonebrook kits):
  BC  sRGB base colour
  N   OpenGL (+Y up) tangent normal, linear; Unreal flips green on import
  ORM linear R=AO G=roughness B=metallic
  H   16-bit linear height (0..1 maps to 0..height_range_m) used by the Blender build
      to displace wall and thatch geometry so silhouette relief matches the texture.
Row 0 of every PNG is the top of the image (v = 1).
"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
TEX = HERE / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)
SEED = 440


def rng_for(name):
    return np.random.default_rng([SEED, sum(map(ord, name))])


# ---------------------------------------------------------------- helpers
def freq_grid(n):
    f = np.fft.fftfreq(n) * n          # cycles per tile
    return f[None, :], f[:, None]      # fx (columns / u), fy (rows / v)


def band_noise(n, rng, su, sv, power=0.0):
    """Tileable Gaussian-filtered noise. su/sv: cut-off in cycles per tile along u and v."""
    fx, fy = freq_grid(n)
    w = rng.standard_normal((n, n))
    filt = np.exp(-(fx / su) ** 2 - (fy / sv) ** 2)
    if power:
        filt *= (1 + np.hypot(fx, fy)) ** -power
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * filt))
    out -= out.mean()
    return out / (out.std() + 1e-9)


def fbm(n, rng, base, octaves=5, gain=.55, aniso=(1, 1)):
    tot = np.zeros((n, n)); amp = 1; s = 0
    for o in range(octaves):
        f = base * 2 ** o
        tot += amp * band_noise(n, rng, f * aniso[0], f * aniso[1]); s += amp; amp *= gain
    return tot / s


def blur(a, sigma_px):
    n = a.shape[0]
    fx, fy = freq_grid(n)
    k = np.exp(-2 * (math.pi * sigma_px / n) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * k))


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def normal_from_height(h_m, texel_m, strength=1.0):
    gy, gx = np.gradient(np.pad(h_m, 1, mode='wrap'))
    gx = gx[1:-1, 1:-1] / texel_m; gy = gy[1:-1, 1:-1] / texel_m
    # rows go down the image (v decreasing): dh/dv = -gy
    nx = -gx * strength; ny = gy * strength; nz = np.ones_like(h_m)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack((nx / l, ny / l, nz / l)) * .5 + .5


def cavity_ao(h_m, texel_m, radius_m, depth_m, floor=.45):
    big = blur(h_m, radius_m / texel_m)
    occ = np.clip((big - h_m) / depth_m, 0, 1)
    return np.clip(1 - occ * (1 - floor), floor, 1)


def save(name, arr, mode='RGB', bits=8):
    path = TEX / f'{name}.png'
    if bits == 16:
        Image.fromarray(np.clip(arr * 65535 + .5, 0, 65535).astype(np.uint16)).save(path)
    else:
        Image.fromarray(np.clip(arr * 255 + .5, 0, 255).astype(np.uint8), mode).save(path, optimize=True)
    return path


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= .0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - .055)


def write_set(name, bc_lin, h_m, texel_m, rough, ao, metal=None, nstrength=1.0, hrange=None):
    n = bc_lin.shape[0]
    save(f'T_S440_{name}_BC', lin_to_srgb(bc_lin))
    save(f'T_S440_{name}_N', normal_from_height(h_m, texel_m, nstrength))
    metal = np.zeros((n, n)) if metal is None else metal
    save(f'T_S440_{name}_ORM', np.dstack((ao, rough, metal)))
    info = {'size_px': n, 'tile_m': n * texel_m, 'mean_base_color_linear': [float(v) for v in bc_lin.reshape(-1, 3).mean(0)],
            'mean_roughness': float(rough.mean())}
    if hrange:
        lo, hi = hrange
        save(f'T_S440_{name}_H', (h_m - lo) / (hi - lo), mode=None, bits=16)
        info['height_range_m'] = [lo, hi]
    return info


REPORT = {}


# ---------------------------------------------------------------- 1. coursed fieldstone rubble with lime mortar
def stamp_polygon(n, tx, h, sid, attrs, sidx, cu, cv, hu, hv, rng, relief, arris, tile, shape='angular'):
    """Rasterise one fieldstone in its course cell: angular block, water-rounded cobble, flat slab
    or wedge; flat weathered face, rounded arrises.  Wraps across tile edges."""
    if shape == 'wedge':
        k = int(rng.integers(4, 6)); jit, rmin, sqw = .45, .70, .55
    elif shape == 'rounded':
        k = int(rng.integers(12, 17)); jit, rmin, sqw = .25, .80, .25
    else:
        k = int(rng.integers(6, 11)); jit, rmin, sqw = .35, .82, .65
    ang = (np.arange(k) + rng.uniform(-jit, jit, k)) * 2 * math.pi / k + rng.uniform(0, 2 * math.pi)
    rad = rng.uniform(rmin, 1.0, k)
    px = np.cos(ang) * rad; py = np.sin(ang) * rad
    # superellipse push: corners of the cell are filled more than an ellipse would
    sq = np.abs(np.cos(ang)) ** .35 * np.sign(np.cos(ang)), np.abs(np.sin(ang)) ** .35 * np.sign(np.sin(ang))
    px = (px * (1 - sqw) + sq[0] * rad * sqw) * hu; py = (py * (1 - sqw) + sq[1] * rad * sqw) * hv
    if shape == 'rounded':
        arris = max(arris, min(hu, hv) * .45)
    c0 = int((cu - hu - .01) / tx); c1 = int((cu + hu + .01) / tx) + 2
    r0 = int((cv - hv - .01) / tx); r1 = int((cv + hv + .01) / tx) + 2
    cols = np.arange(c0, c1); rows = np.arange(r0, r1)
    U = (cols * tx - cu)[None, :] * np.ones((len(rows), 1)); V = (rows * tx - cv)[:, None] * np.ones((1, len(cols)))
    d = np.full(U.shape, -1e9)
    for i in range(k):
        x0, y0, x1, y1 = px[i], py[i], px[(i + 1) % k], py[(i + 1) % k]
        ex, ey = x1 - x0, y1 - y0; L = math.hypot(ex, ey) + 1e-9
        nx, ny = ey / L, -ex / L
        if nx * (-x0) + ny * (-y0) > 0: nx, ny = -nx, -ny      # outward
        d = np.maximum(d, (U - x0) * nx + (V - y0) * ny)
    inside = d < 0
    face = smoothstep(0, arris, -d)
    tilt = rng.normal(0, .25, 2)
    dome = relief * (face * (.75 + .25 * np.sqrt(np.clip(1 - (U / hu) ** 2 - (V / hv) ** 2 * .5, 0, 1)))
                     + .004 * (tilt[0] * U / hu + tilt[1] * V / hv))
    rr = (n - 1 - (rows % n))[:, None] * np.ones((1, len(cols)), int)
    cc = (cols % n)[None, :] * np.ones((len(rows), 1), int)
    sel = inside & (dome > h[rr, cc])
    h[rr[sel], cc[sel]] = dome[sel]; sid[rr[sel], cc[sel]] = sidx
    for arr, val in attrs:
        arr[rr[sel], cc[sel]] = val
    return sel.sum()


def rubble():
    rng = rng_for('rubble'); n = 2048; tile = 2.4; tx = tile / n
    heights = []
    while sum(heights) < tile:
        heights.append(rng.uniform(.13, .30))
    heights = np.array(heights) * tile / sum(heights)
    h = np.full((n, n), -1.0); sid = np.full((n, n), -1, np.int32)
    tone = np.zeros((n, n)); hue = np.zeros((n, n)); kind = np.zeros((n, n), np.int32)
    stones = []
    v0 = 0.0
    for ci, ch in enumerate(heights):
        widths = []
        while sum(widths) < tile:
            widths.append(rng.uniform(.14, .72) * (.8 + 1.2 * ch))
        widths = np.array(widths) * tile / sum(widths)
        u0 = rng.uniform(0, tile)
        for w in widths:
            gap = rng.uniform(.006, .013)
            cu = u0 + w / 2 + rng.uniform(-.01, .01); cv = v0 + ch / 2 + rng.uniform(-.012, .012)
            hu = w / 2 - gap; hv = ch / 2 - gap * rng.uniform(.6, 1.0)
            shape = rng.choice(['angular', 'angular', 'rounded', 'slab', 'wedge'])
            cells = [(cu, cv, hu, hv)]
            if shape == 'slab':             # thin bedded slab with packing below
                cells = [(cu, cv + hv * .25, hu, hv * .62)]
            if hu > .16 and rng.random() < .22:   # two smaller stones side by side
                cells = [(cu - hu / 2, cv, hu / 2 - gap / 2, hv * rng.uniform(.8, 1)), (cu + hu / 2, cv, hu / 2 - gap / 2, hv * rng.uniform(.8, 1))]
            elif hv > .09 and rng.random() < .15:  # stacked pair in a tall course
                cells = [(cu, cv - hv / 2, hu * rng.uniform(.8, 1), hv / 2 - gap / 2), (cu, cv + hv / 2, hu * rng.uniform(.8, 1), hv / 2 - gap / 2)]
            for (a, b, c, d) in cells:
                sidx = len(stones)
                stones.append({'u': [(a - c) / tile, (a + c) / tile], 'v': [(b - d) / tile, (b + d) / tile], 'course': int(ci)})
                stamp_polygon(n, tx, h, sid, [(tone, rng.normal(0, 1)), (hue, rng.uniform(-1, 1)), (kind, int(rng.integers(0, 6)))],
                              sidx, a, b, c, d, rng, rng.uniform(.018, .055), rng.uniform(.008, .03), tile, 'angular' if shape == 'slab' else shape)
            u0 += w
        v0 += ch
    # small pinning stones (galets) packed into the remaining joints
    free = blur((h < -.5).astype(float), 10)
    for i in range(900):
        cu = rng.uniform(0, tile); cv = rng.uniform(0, tile)
        r = int(cv / tx) % n; c = int(cu / tx) % n
        if free[n - 1 - r, c] < .8: continue
        s = rng.uniform(.018, .05)
        stamp_polygon(n, tx, h, sid, [(tone, rng.normal(-.3, 1)), (hue, rng.uniform(-1, 1)), (kind, int(rng.integers(0, 6)))],
                      -2, cu, cv, s * rng.uniform(1, 1.8), s, rng, rng.uniform(.008, .02), .006, tile)
    stone = h > -.5
    pits = fbm(n, rng, 70, 4); grain = band_noise(n, rng, 600, 600)
    strata = band_noise(n, rng, 6, 90)              # sedimentary bedding lines along the course
    mortar_n = fbm(n, rng, 40, 4)
    hm = np.where(stone, h + .0018 * pits + .0005 * grain + .0012 * strata, -.012 + .003 * mortar_n + .001 * grain)
    big = fbm(n, rng, 3, 4); mid = fbm(n, rng, 20, 4)
    palette = np.array([[.27, .25, .21], [.34, .30, .23], [.22, .21, .19], [.38, .33, .25],
                        [.19, .175, .15], [.30, .28, .245]])
    base = palette[kind % len(palette)]
    face = smoothstep(.0, .015, np.clip(h, 0, None))
    col = base * (1 + .16 * tone[..., None]) * (1 + .14 * mid[..., None] + .07 * big[..., None])
    col *= (1 + .08 * pits[..., None] + .06 * strata[..., None])
    col[..., 0] *= 1.06 + .07 * hue; col[..., 2] *= .88 - .07 * hue
    col *= (.80 + .20 * face[..., None])
    # crustose lichen: small pale grey-ochre rosettes, mostly on upper faces
    lich = smoothstep(1.2, 1.9, band_noise(n, rng, 160, 160) + fbm(n, rng, 8, 3)) * face
    col = col * (1 - .35 * lich[..., None]) + np.array([.40, .39, .32]) * .35 * lich[..., None]
    mortar_col = np.array([.30, .285, .25]) * (1 + .12 * mortar_n[..., None] + .08 * grain[..., None])
    col = np.where(stone[..., None], col, mortar_col)
    col *= (.86 + .14 * smoothstep(-.7, .7, big))[..., None]    # broad weather staining
    ao = cavity_ao(hm, tx, .035, .022, .30)
    col *= (.45 + .55 * ao[..., None])
    rough = np.where(stone, .78 + .07 * mid + .05 * lich, .95 + .03 * mortar_n)
    rough = np.clip(rough - .05 * face * stone, .55, 1)
    # Height map (geometry displacement) stays the 2.4 m square tile.
    save('T_S440_Rubble_H', (hm + .02) / .08, mode=None, bits=16)
    nrm = normal_from_height(hm, tx)
    # The material is two vertically stacked copies (2.4 x 4.8 m, 2048 x 4096 px).  Walls map
    # v = height / 4.8, so the lower copy carries ground grime: damp darkening and green algae in the
    # bottom ~40 cm, moss in low joints, and rain splash-back speckle up to ~0.7 m.
    col2 = np.concatenate([col, col]); rough2 = np.concatenate([rough, rough]); ao2 = np.concatenate([ao, ao])
    nrm2 = np.concatenate([nrm, nrm]); stone2 = np.concatenate([stone, stone])
    rows = np.arange(2 * n)[:, None] * np.ones((1, n))
    z = (2 * n - 1 - rows) / (2 * n) * (2 * tile)
    edge = band_noise(n, rng, 10, 3); edge2 = np.concatenate([edge, edge])
    damp = smoothstep(.50, .02, z + .12 * edge2) + .35 * smoothstep(1.0, .3, z + .2 * edge2)
    damp = np.clip(damp, 0, 1)
    algae = damp * smoothstep(-.4, .6, np.concatenate([fbm(n, rng, 9, 4)] * 2))
    moss = smoothstep(.32, .05, z + .05 * edge2) * (~stone2) * smoothstep(-.2, .5, np.concatenate([fbm(n, rng, 30, 3)] * 2))
    sp = np.concatenate([band_noise(n, rng, 260, 260)] * 2)
    splash = smoothstep(.9, 1.7, sp + .6 * np.concatenate([band_noise(n, rng, 60, 60)] * 2)) * smoothstep(.8, .08, z)
    c = col2 * (1 - .78 * damp[..., None])
    c = c * (1 - .7 * algae[..., None]) + np.array([.030, .048, .016]) * .7 * algae[..., None]
    c = c * (1 - .8 * moss[..., None]) + np.array([.05, .085, .02]) * .8 * moss[..., None]
    c = c * (1 - .7 * splash[..., None]) + np.array([.05, .04, .03]) * .7 * splash[..., None]
    r2 = np.clip(rough2 - .12 * damp + .1 * moss, .45, 1)
    save('T_S440_Rubble_BC', lin_to_srgb(c)); save('T_S440_Rubble_N', nrm2)
    save('T_S440_Rubble_ORM', np.dstack((ao2 * (1 - .15 * moss), r2, np.zeros_like(r2))))
    REPORT['Rubble'] = {'size_px': [n, 2 * n], 'tile_m': [tile, 2 * tile], 'height_range_m': [-.02, .06],
                        'ground_grime': 'damp/algae <0.55 m, joint moss <0.32 m, splash-back <0.75 m in the lower copy (v<0.5)'}
    REPORT['Rubble']['stones'] = len(stones)
    (TEX / 'rubble_stones.json').write_text(json.dumps({'tile_m': tile, 'stones': stones}, indent=1) + '\n')


# ---------------------------------------------------------------- 2. combed long-straw thatch
def thatch():
    rng = rng_for('thatch'); n = 2048; tile = 2.0; tx = tile / n
    course = .25
    yy, xx = np.mgrid[0:n, 0:n]
    v = (n - 1 - yy) * tx          # slope distance upward from eave line (metres)
    u = xx * tx
    edge_wobble = band_noise(n, rng, 22, 1.0) * .008   # ragged course lines, constant down a column band
    vv = v + edge_wobble
    ci = np.floor(vv / course).astype(int) % int(tile / course); fv = vv / course - np.floor(vv / course)
    shift = rng.uniform(-14, 14, int(tile / course) + 2).astype(int)
    bundles = band_noise(n, rng, 45, 2.0)               # 4-5 cm hand-laid bundles
    s_fine = band_noise(n, rng, 520, 4)
    s_mid = band_noise(n, rng, 200, 2)
    lean = band_noise(n, rng, 6, 2) * 10                # slight bundle lean, in pixels
    strands = np.zeros((n, n)); bund = np.zeros((n, n))
    for k in range(int(tile / course)):
        rows = ci == k
        off = (shift[k] + (lean * fv).astype(int)) % n
        cidx = (xx + off) % n
        s = s_fine[yy, cidx] * .5 + s_mid[yy, cidx] * .5
        strands[rows] = s[rows]; bund[rows] = bundles[yy, cidx][rows]
    butt = 1 - smoothstep(.0, .09, fv)
    stalk_dots = band_noise(n, rng, 800, 800)
    lump = fbm(n, rng, 4, 4)
    h = (.009 * (1 - fv) ** 1.5 + .010 * bund + .004 * strands + .003 * butt * stalk_dots + .012 * lump)
    sharp = np.clip(strands * .35 + .5, 0, 1)
    fresh = np.array([.40, .30, .145]); old = np.array([.25, .205, .14]); dark = np.array([.05, .04, .028])
    weather = smoothstep(-.9, .9, fbm(n, rng, 4, 4)) * .7
    col = fresh * (1 - weather[..., None]) + old * weather[..., None]
    col = col * (.84 + .24 * sharp[..., None]) * (1 + .10 * bund[..., None])
    gap = smoothstep(-.2, -1.4, strands * .6 + bund * .6)
    col = col * (1 - .38 * gap[..., None]) + dark * .38 * gap[..., None]
    col = col * (1 - .10 * butt[..., None] * smoothstep(-.1, -.8, stalk_dots)[..., None])
    moss = smoothstep(.70, .95, fbm(n, rng, 6, 5)) * (.5 + .5 * butt)
    col = col * (1 - .5 * moss[..., None]) + np.array([.09, .11, .045]) * .5 * moss[..., None]
    ao = cavity_ao(h, tx, .03, .02, .35)
    col *= (.55 + .45 * ao[..., None])
    rough = np.clip(.88 + .08 * gap - .06 * sharp + .04 * moss, .6, 1)
    REPORT['Thatch'] = write_set('Thatch', col, h, tx, rough, ao, hrange=(-.04, .08))
    REPORT['Thatch']['course_m'] = course


# ---------------------------------------------------------------- 3. weathered exterior oak (grain along v)
def weathered_oak():
    rng = rng_for('oak'); n = 1024; tile = 1.0; tx = tile / n
    yy, xx = np.mgrid[0:n, 0:n]
    u = xx / n; v = (n - 1 - yy) / n
    warp = band_noise(n, rng, 3, 1.0) * .022 + band_noise(n, rng, 8, 2) * .006
    rings = (u + warp) * 46
    f = rings - np.floor(rings)
    late = smoothstep(.62, .80, f) * (1 - smoothstep(.92, 1.0, f))
    pores = (band_noise(n, rng, 420, 25) > 1.4) * (1 - late)
    fibre = band_noise(n, rng, 300, 8)
    checks = smoothstep(2.3, 3.2, band_noise(n, rng, 160, 3)) * smoothstep(.0, .5, band_noise(n, rng, 2, 2) + .4)
    weather = smoothstep(-1, 1, fbm(n, rng, 3, 4))
    silver = np.array([.27, .25, .22]); brown = np.array([.20, .135, .08]); latec = np.array([.12, .09, .065])
    col = silver * (1 - .5 * weather[..., None]) + brown * .5 * weather[..., None]
    col = col * (1 - .40 * late[..., None]) + latec * .40 * late[..., None]
    col *= (1 + .10 * fibre[..., None]) * (1 - .35 * pores[..., None])
    col = col * (1 - .8 * checks[..., None]) + np.array([.03, .025, .02]) * .8 * checks[..., None]
    h = -.0008 * late + .00025 * fibre - .003 * checks - .0004 * pores
    ao = cavity_ao(h, tx, .006, .002, .35)
    rough = np.clip(.78 + .06 * fibre * .3 + .1 * checks + .05 * late, .5, 1)
    REPORT['WeatheredOak'] = write_set('WeatheredOak', col, h, tx, rough, ao)


# ---------------------------------------------------------------- 4. leaded diamond-quarry glazing
def leaded_glass():
    rng = rng_for('glass'); n = 512; tile = .48; tx = tile / n
    yy, xx = np.mgrid[0:n, 0:n]
    u = xx * tx; v = (n - 1 - yy) * tx
    pw = .12; ph = .16                       # quarry width/height (4 x 3 per tile: tiles)
    a = u / pw + v / ph; b = u / pw - v / ph
    da = np.abs(a - np.round(a)); db = np.abs(b - np.round(b))
    dist = np.minimum(da * pw * ph / math.hypot(pw, ph) * 2, db * pw * ph / math.hypot(pw, ph) * 2)
    came = smoothstep(.0075, .0050, dist)
    qid = (np.floor(a) * 31 + np.floor(b) * 17).astype(int)
    tint = rng.uniform(-1, 1, 4096)[qid % 4096]
    # crown-glass wobble: each quarry slightly domed and rippled
    wob = band_noise(n, rng, 10, 10) * .0006 + .0004 * np.cos(np.minimum(da, db) * math.pi)
    glass = np.array([.030, .040, .036]) * (1 + .25 * tint[..., None])
    lead = np.array([.10, .10, .095])
    col = glass * (1 - came[..., None]) + lead * came[..., None]
    h = wob * (1 - came) + .0025 * came
    rough = np.clip(.06 + .03 * (tint + 1) * (1 - came) + .5 * came, 0, 1)
    metal = .65 * came
    ao = cavity_ao(h, tx, .004, .0015, .6)
    REPORT['LeadedGlass'] = write_set('LeadedGlass', col, h, tx, rough, ao, metal=metal)


if __name__ == '__main__':
    only = set(sys.argv[1:])
    for name, fn in [('rubble', rubble), ('thatch', thatch), ('oak', weathered_oak), ('glass', leaded_glass)]:
        if not only or name in only:
            fn(); print('texture', name, 'done', flush=True)
    rep = HERE / 'texture_report.json'
    old = json.loads(rep.read_text()) if rep.exists() else {}
    old.update(REPORT)
    rep.write_text(json.dumps({'seed': SEED, **{k: v for k, v in old.items() if k != 'seed'}}, indent=2) + '\n')
