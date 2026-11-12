"""food_fruit (421 items/food frames 18-22, 25) and tree_fruit (frame 23).

The original frames are three bell peppers (red, green, yellow), a pumpkin, a tomato, an aubergine and, for the
fruit hanging in the tree, an acorn-shaped nut. Each is a parametric surface: the same function gives the dense
source (displaced, procedural skin) and the game mesh.

    tools/bl.sh build_fruit.py <name|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_fruit.py'


def cr_spline(pts, n=240):
    P = np.array(pts, float); Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    k = len(P) - 1; per = max(2, n // k)
    for i in range(k):
        p0, p1, p2, p3 = Q[i], Q[i + 1], Q[i + 2], Q[i + 3]; t = np.linspace(0, 1, per, endpoint=(i == k - 1))[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.vstack(out)


def profile_fn(pts):
    D = cr_spline(pts); s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(D, axis=0), axis=1))]; s /= s[-1]
    return lambda v: np.stack([np.interp(v, s, D[:, k]) for k in range(D.shape[1])], -1)


# ---------------------------------------------------------------------------------------------- shapes
def lobed(name, hi, prof, n, crease, zlift, warp=(0.25, 0.1), seed=0, p=2.2, lean=(0.0, 0.0), wobble=0.04, res=(28, 20), c=None, uneven=0.0, twist=0.0):
    """lobed body of revolution: prof = (r, z) control points bottom pole -> top pole; crease/zlift = [(v, value)] tables"""
    pf = profile_fn(prof); rng = np.random.default_rng(seed); ph = rng.uniform(0, 6.28, 4); cv, ca = zip(*crease); zv, za = zip(*zlift)
    nu, nv = (res[0] * 6, res[1] * 6) if hi else res

    def fn(U, V):
        th = 2 * np.pi * U; th2 = th + warp[0] * np.sin(th + ph[0]) + warp[1] * np.sin(2 * th + ph[1]) + twist * V
        cc = ((1 - np.cos(n * th2)) / 2) ** p; rz = pf(V); r = rz[:, 0]; z = rz[:, 1]
        a = np.interp(V, cv, ca); r = r * (1 - a * cc) * (1 + uneven * np.cos(th2 + ph[2]) + 0.5 * uneven * np.cos(2 * th2 + ph[3]))
        d = np.stack([np.cos(th), np.sin(th), z * 14], -1); r = r * (1 + wobble * fbm(d, seed, 0.9, 3))
        z = z + np.interp(V, zv, za) * cc
        x = r * np.cos(th) + lean[0] * z; y = r * np.sin(th) + lean[1] * z
        return np.stack([x, y, z], -1)
    return L.grid_surface(name, fn, nu, nv, c, pole0=True, pole1=True)


def stem(name, hi, base, prof, bend=(0.0, 0.0), lobes=0, lobe_amp=0.0, lobe_r=(0.008, 0.015), res=(12, 10), seed=0, c=None, ridges=0, ridge_amp=0.0, twist=0.0, lobe_p=1.0,
         bend_from=0.0, lift=0.0, under=None):
    """stalk with an optional lobed calyx collar at its base; prof (r, z) in local coords from the collar rim to the cut end (pole); closed underneath"""
    prof = (list(under) if under else [(0.0, prof[0][1])]) + list(prof)
    pf = profile_fn(prof); nu, nv = (res[0] * 4, res[1] * 5) if hi else res; H = max(p_[1] for p_ in prof); rng = np.random.default_rng(seed); ph = rng.uniform(0, 6.28)

    def fn(U, V):
        th = 2 * np.pi * U; rz = pf(V); r = rz[:, 0]; z = rz[:, 1]
        if lobes:
            k = ((1 + np.cos(lobes * th + ph)) / 2) ** lobe_p; w = smoothstep(lobe_r[0], lobe_r[1], r)
            r = r * (1 - lobe_amp * (1 - k) * w); z = z + lift * w * k * k
        if ridges:
            r = r * (1 + ridge_amp * np.cos(ridges * (th + twist * z / H)) * smoothstep(0.05, 0.3, V))
        t = np.clip((z - bend_from) / (H - bend_from), 0, 1); x = r * np.cos(th) + bend[0] * t * t * H; y = r * np.sin(th) + bend[1] * t * t * H
        return np.stack([x + base[0], y + base[1], z + base[2]], -1)
    return L.grid_surface(name, fn, nu, nv, c, pole0=True, pole1=True)


def leaf(name, hi, root, length, width, yaw, droop=0.5, curl=0.25, res=(6, 10), c=None, thick=0.0005, seed=0, pitch=0.2):
    """ovate leaf with a short petiole; u across, v along; solidified to a thin closed shell"""
    nu, nv = (res[0] * 5, res[1] * 5) if hi else res; rng = np.random.default_rng(seed); ph = rng.uniform(0, 6.28, 3)

    def fn(U, V):
        w = width * np.sin(np.pi * np.clip(V, 0, 1) ** 0.72) ** 0.9 * (1 - 0.25 * V) + 0.0009    # petiole end narrow, widest at 35 %, pointed tip
        s = (U - 0.5) * 2; x = s * w / 2; y = V * length
        z = -droop * length * V * V + curl * w * (s * s) - 0.08 * width * np.cos(np.pi * s) * 0 + pitch * y
        z = z + 0.012 * length * np.sin(7 * V + ph[0]) * s + 0.006 * length * np.sin(11 * V * (1 + 0.3 * s) + ph[1])     # undulating margin
        return np.stack([x, y, z], -1)
    ob = L.grid_surface(name, fn, nu, nv, c, closed_u=False)
    L.mod(ob, 'SOLIDIFY', thickness=thick, offset=0.0); L.apply_mods(ob)
    ob.rotation_euler = (0, 0, yaw); ob.location = root; L.apply_xf(ob); return ob


# ---------------------------------------------------------------------------------------------- materials (dense source)
def skin_mat(name, cols, speck=(0.9, 0.8, 0.6), speck_amt=0.25, rough=(0.2, 0.42), green=None, top_z=0.08, russet=0.0, pore_scale=900.0, pore_bump=0.12,
             wrinkle=0.0, streak=0.0, bloom=0.0, scale=1.0, dirt=0.0, dirt_dist=0.02):
    """fruit skin: three-colour mottling, pale lenticel specks, scuffed roughness, pore bump, optional green shoulder, russet scars and streaks"""
    t = NT(name); n1 = t.noise(9 * scale, 5, 0.6); n2 = t.noise(31 * scale, 4, 0.55, distortion=0.3); n3 = t.noise(3.1 * scale, 3, 0.5)
    base = t.ramp(n1, [(0.28, cols[0]), (0.52, cols[1]), (0.78, cols[2])])
    base = t.hsv(base, v=t.maprange(n2, 0.25, 0.75, 0.86, 1.12), sat=t.maprange(n3, 0.3, 0.7, 0.92, 1.06))
    if streak:
        sp = t.sep(t.obj); ang = t.math('ARCTAN2', sp[1], sp[0]); st = t.noise(4.0, 3, 0.6, vec=t.comb(t.math('MULTIPLY', ang, 6.0), t.math('MULTIPLY', sp[2], 2.0 * scale), 0.0))
        base = t.mix(t.math('MULTIPLY', t.ramp(st, [(0.45, 0.0), (0.7, 1.0)]), streak), base, cols[3] if len(cols) > 3 else cols[0])
    if green is not None:
        z = t.sep(t.obj)[2]; g = t.maprange(t.math('ADD', z, t.math('MULTIPLY', t.math('SUBTRACT', n1, 0.5), 0.03)), top_z - 0.022, top_z + 0.004, 0.0, 1.0, interp='SMOOTHSTEP')
        base = t.mix(t.math('MULTIPLY', g, green[1]), base, green[0])
    sv = t.voronoi(pore_scale * scale, feature='F1'); dots = t.ramp(sv, [(0.0, 1.0), (0.16, 0.0)]); dots = t.math('MULTIPLY', dots, t.ramp(t.noise(60 * scale, 2, 0.5), [(0.35, 0.0), (0.6, 1.0)]))
    base = t.mix(t.math('MULTIPLY', dots, speck_amt), base, speck)
    scar = t.val(0.0)
    if russet:
        w = t.noise(5.5 * scale, 5, 0.7, distortion=1.2); line = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', w, 0.5)), [(0.0, 1.0), (0.012, 0.0)])
        patch = t.ramp(t.noise(2.3 * scale, 2, 0.5, vec=t.mapping(loc=(3.1, 1.7, 0.4))), [(0.60, 0.0), (0.68, 1.0)])
        blot = t.ramp(t.noise(14 * scale, 4, 0.7, vec=t.mapping(loc=(7.7, 0.3, 2.9))), [(0.70, 0.0), (0.76, 1.0)])
        scar = t.math('MULTIPLY', t.math('MAXIMUM', t.math('MULTIPLY', line, patch), t.math('MULTIPLY', blot, patch)), russet)
        base = t.mix(scar, base, t.mix(t.noise(200 * scale, 2, 0.5), (0.30, 0.19, 0.10), (0.46, 0.33, 0.20)))
    dm = t.val(0.0)
    if dirt:
        dm = t.math('MULTIPLY', t.math('MULTIPLY', t.ramp(t.ao(dirt_dist, 12), [(0.55, 1.0), (0.85, 0.0)]), t.ramp(t.noise(30 * scale, 4, 0.7), [(0.3, 0.2), (0.7, 1.0)])), dirt)
        base = t.mix(dm, base, t.mix(t.noise(300 * scale, 2, 0.5), (0.10, 0.07, 0.045), (0.2, 0.15, 0.1)))
    scuff = t.ramp(t.noise(17 * scale, 5, 0.65, vec=t.mapping(loc=(1.3, 5.1, 2.2))), [(0.42, 0.0), (0.74, 1.0)])
    r = t.mixf(scuff, rough[0], rough[1]); r = t.math('ADD', r, t.math('MULTIPLY', dots, 0.12)); r = t.mixf(scar, r, 0.78); r = t.mixf(dm, r, 0.9)
    if bloom:
        bl = t.ramp(t.noise(6 * scale, 4, 0.6, vec=t.mapping(loc=(9.1, 2.2, 4.4))), [(0.35, 0.0), (0.75, 1.0)]); r = t.math('ADD', r, t.math('MULTIPLY', bl, 0.25 * bloom))
        base = t.mix(t.math('MULTIPLY', bl, 0.22 * bloom), base, (0.62, 0.62, 0.66))
    h = t.math('ADD', t.math('MULTIPLY', t.noise(pore_scale * 0.6 * scale, 3, 0.6), 0.5), t.math('MULTIPLY', dots, -0.6))
    h = t.math('ADD', h, t.math('MULTIPLY', scar, 0.9))
    nrm = t.bump(h, pore_bump, 0.0004)
    if wrinkle:
        nrm = t.bump(t.noise(70 * scale, 4, 0.6, distortion=0.6), wrinkle, 0.001, normal=nrm)
    t.set(base=base, rough=r, normal=nrm, sss=0.05, sss_radius=(0.9, 0.3, 0.15), sss_scale=0.002, spec=0.5)
    return t.mat


def stem_mat(name, green=(0.075, 0.13, 0.028), dry=(0.24, 0.17, 0.09), cut_z=None, scale=1.0, woody=0.0):
    """stalk: fibrous striations along the axis, drying brown towards the cut end, corky tip"""
    t = NT(name); sp = t.sep(t.obj); ang = t.math('ARCTAN2', sp[1], sp[0])
    fib = t.noise(3.0, 4, 0.7, vec=t.comb(t.math('MULTIPLY', ang, 9.0), t.math('MULTIPLY', sp[2], 25.0 * scale), 0.0))
    g = t.mix(fib, tuple(c * 0.62 for c in green), tuple(min(1, c * 1.35) for c in green))
    d = t.mix(t.noise(140 * scale, 3, 0.6), tuple(c * 0.7 for c in dry), tuple(min(1, c * 1.25) for c in dry))
    k = t.val(woody)
    if cut_z is not None:
        k = t.math('MAXIMUM', k, t.maprange(t.math('ADD', sp[2], t.math('MULTIPLY', t.math('SUBTRACT', fib, 0.5), 0.004 / scale)), cut_z - 0.004 / scale, cut_z, 0.0, 1.0, interp='SMOOTHSTEP'))
    base = t.mix(k, g, d)
    h = t.math('ADD', t.math('MULTIPLY', fib, 1.0), t.math('MULTIPLY', t.noise(260 * scale, 2, 0.5), 0.35))
    t.set(base=base, rough=t.mixf(k, t.mixf(fib, 0.38, 0.55), 0.82), normal=t.bump(h, 0.35, 0.0008), sss=0.05, sss_scale=0.002)
    return t.mat


def leaf_mat(name, col=(0.035, 0.075, 0.02), vein=(0.16, 0.24, 0.08)):
    """leaf from its own UV: midrib, lateral and tertiary veins as pale raised lines, blade mottling, drier brown margin spots"""
    t = NT(name); uv = t.sep(t.uv); a = t.math('ABSOLUTE', t.math('SUBTRACT', uv[0], 0.5))
    mid = t.ramp(a, [(0.0, 1.0), (0.035, 0.0)])
    lat = t.math('FRACT', t.math('ADD', t.math('MULTIPLY', uv[1], 7.0), t.math('MULTIPLY', a, -5.0)))
    latl = t.math('MULTIPLY', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', lat, 0.5)), [(0.0, 1.0), (0.05, 0.0)]), t.ramp(a, [(0.0, 1.0), (0.5, 0.25)]))
    cell = t.voronoi(55.0, vec=t.comb(uv[0], t.math('MULTIPLY', uv[1], 2.2), 0.0), feature='DISTANCE_TO_EDGE'); ter = t.ramp(cell, [(0.0, 1.0), (0.05, 0.0)])
    v = t.math('MAXIMUM', t.math('MAXIMUM', mid, latl), t.math('MULTIPLY', ter, 0.35))
    blade = t.mix(t.noise(40, 4, 0.6, vec=t.comb(uv[0], uv[1], 0.0)), tuple(c * 0.7 for c in col), tuple(c * 1.5 for c in col))
    spot = t.ramp(t.noise(23, 4, 0.7, vec=t.comb(uv[0], uv[1], 3.0)), [(0.68, 0.0), (0.74, 1.0)])
    base = t.mix(t.math('MULTIPLY', v, 0.75), blade, vein); base = t.mix(t.math('MULTIPLY', spot, 0.7), base, (0.33, 0.24, 0.09))
    h = t.math('ADD', t.math('MULTIPLY', v, 1.0), t.math('MULTIPLY', t.noise(300, 2, 0.5, vec=t.comb(uv[0], uv[1], 0.0)), 0.15))
    t.set(base=base, rough=t.mixf(v, 0.42, 0.55), normal=t.bump(h, 0.5, 0.0006), sss=0.1, sss_scale=0.002, sss_radius=(0.3, 0.9, 0.2))
    return t.mat


# ---------------------------------------------------------------------------------------------- the seven
def pepper(hi, cols, seed, green=None, lobes=3, c=None):
    prof = [(0, 0.016), (0.011, 0.006), (0.023, 0.0), (0.033, 0.010), (0.039, 0.034), (0.0425, 0.060), (0.0435, 0.079), (0.039, 0.092), (0.029, 0.0965), (0.017, 0.091), (0.007, 0.083), (0, 0.081)]
    body = lobed('body', hi, prof, lobes, crease=[(0, 0.0), (0.05, 0.42), (0.18, 0.36), (0.5, 0.2), (0.78, 0.26), (0.9, 0.34), (1, 0.0)],
                 zlift=[(0, 0.0), (0.08, 0.012), (0.25, 0.004), (0.6, 0.0), (0.8, -0.004), (0.92, -0.007), (1, 0.0)], seed=seed, lean=(0.06, -0.03), wobble=0.055, c=c, warp=(0.3, 0.12), uneven=0.07, twist=0.35, p=2.6)
    st = stem('stem', hi, (0.081 * 0.06, -0.081 * 0.03, 0.0795), [(0.0165, 0.0015), (0.0158, 0.004), (0.0095, 0.0068), (0.0068, 0.012), (0.0058, 0.022), (0.006, 0.031), (0.0064, 0.0368), (0.0058, 0.0382), (0, 0.0384)],
              bend=(0.25, 0.12), lobes=5, lobe_amp=0.16, lobe_r=(0.008, 0.015), seed=seed, c=c, ridges=5, ridge_amp=0.1, bend_from=0.008)
    lf = leaf('leaf', hi, (0.081 * 0.06 + 0.0075, -0.081 * 0.03 + 0.003, 0.0795 + 0.030), 0.082, 0.043, yaw=math.radians(-58 + seed * 37), droop=0.75, curl=0.16, c=c, seed=seed, pitch=0.42)
    if hi:
        L.displace_np(body, lambda P: 0.0003 * fbm(P, seed + 3, 45, 3) + 0.00015 * fbm(P, seed + 9, 140, 2))
        body.data.materials.append(skin_mat('skin', cols, green=green, top_z=0.088, russet=0.6, rough=(0.16, 0.4), wrinkle=0.04, speck_amt=0.12))
        st.data.materials.append(stem_mat('stem', cut_z=0.0795 + 0.0372)); lf.data.materials.append(leaf_mat('leaf'))
    return [body, st, lf]


def tomato(hi, seed=5, c=None):
    prof = [(0, 0.0035), (0.012, 0.001), (0.026, 0.004), (0.035, 0.016), (0.0375, 0.031), (0.034, 0.045), (0.024, 0.0535), (0.012, 0.0535), (0.005, 0.050), (0, 0.049)]
    body = lobed('body', hi, prof, 5, crease=[(0, 0), (0.3, 0.012), (0.6, 0.03), (0.8, 0.09), (0.93, 0.16), (1, 0)], zlift=[(0, 0), (0.7, 0.0), (0.9, -0.003), (1, 0)], seed=seed, wobble=0.05, c=c, p=1.6, warp=(0.2, 0.1))
    st = stem('stem', True, (0, 0, 0.0512), [(0.026, 0.0052), (0.019, 0.0028), (0.009, 0.0024), (0.0042, 0.004), (0.0026, 0.009), (0.0024, 0.017), (0.0030, 0.021), (0.0034, 0.0225), (0, 0.0228)],
              bend=(0.35, -0.2), lobes=5, lobe_amp=0.86, lobe_r=(0.0045, 0.013), seed=seed, c=c, res=(30, 12), lobe_p=1.5, bend_from=0.004, lift=0.0035,
              under=[(0, 0.0010), (0.009, 0.0010), (0.019, 0.0015), (0.0255, 0.0040)])
    if not hi:                                  # the sepal star is too spiky for a coarse parametric grid: decimate the source instead, so the bake rays find it
        d = L.decimate(st, tris=560, name='stem_lo'); bpy.data.objects.remove(st); st = d; L.smart_uv(st, angle=70, margin=0.02)
    if hi:
        L.displace_np(body, lambda P: 0.0004 * fbm(P, seed + 3, 60, 3))
        body.data.materials.append(skin_mat('skin', [(0.30, 0.010, 0.005), (0.42, 0.018, 0.007), (0.52, 0.045, 0.012)], green=((0.30, 0.17, 0.02), 0.45), top_z=0.058, russet=0.35,
                                            rough=(0.14, 0.34), speck_amt=0.12, pore_bump=0.06))
        st.data.materials.append(stem_mat('stem', green=(0.085, 0.16, 0.035), cut_z=0.0512 + 0.0215))
    return [body, st]


def pumpkin(hi, seed=11, c=None):
    prof = [(0, 0.012), (0.03, 0.004), (0.062, 0.0), (0.088, 0.018), (0.098, 0.05), (0.096, 0.085), (0.08, 0.115), (0.055, 0.13), (0.03, 0.128), (0.012, 0.118), (0, 0.115)]
    body = lobed('body', hi, prof, 11, crease=[(0, 0), (0.06, 0.12), (0.3, 0.1), (0.6, 0.1), (0.85, 0.16), (0.96, 0.22), (1, 0)], zlift=[(0, 0), (0.08, 0.006), (0.3, 0), (0.85, -0.004), (1, 0)],
                 seed=seed, wobble=0.07, c=c, p=1.7, warp=(0.12, 0.2), lean=(0.04, 0.02), res=(44, 18))
    st = stem('stem', hi, (0.115 * 0.04, 0.115 * 0.02, 0.113), [(0.03, 0.002), (0.022, 0.006), (0.0135, 0.014), (0.0105, 0.03), (0.0095, 0.05), (0.0105, 0.062), (0.0112, 0.066), (0.010, 0.0685), (0, 0.069)],
              bend=(0.55, 0.25), lobes=5, lobe_amp=0.25, lobe_r=(0.012, 0.027), seed=seed, c=c, ridges=5, ridge_amp=0.13, twist=1.4, res=(15, 12), bend_from=0.012)
    if hi:
        L.displace_np(body, lambda P: 0.0016 * fbm(P, seed + 3, 22, 3) + 0.0006 * fbm(P, seed + 9, 90, 2))
        body.data.materials.append(skin_mat('skin', [(0.36, 0.085, 0.008), (0.48, 0.14, 0.012), (0.58, 0.21, 0.03), (0.30, 0.10, 0.015)], green=((0.30, 0.2, 0.04), 0.3), top_z=0.125, russet=0.9,
                                            rough=(0.3, 0.55), speck=(0.85, 0.6, 0.3), speck_amt=0.3, pore_scale=420, pore_bump=0.2, wrinkle=0.12, streak=0.55, scale=0.5, dirt=0.8, dirt_dist=0.02))
        st.data.materials.append(stem_mat('stem', green=(0.11, 0.13, 0.04), dry=(0.22, 0.17, 0.09), cut_z=0.113 + 0.064, scale=0.6, woody=0.6))
    return [body, st]


def aubergine(hi, seed=17, c=None):
    """lies on its side: built along +Z then laid down along +X"""
    prof = [(0, 0.0), (0.014, 0.002), (0.03, 0.012), (0.041, 0.035), (0.044, 0.065), (0.040, 0.10), (0.031, 0.135), (0.023, 0.165), (0.0185, 0.185), (0.012, 0.193), (0, 0.195)]
    body = lobed('body', hi, prof, 2, crease=[(0, 0), (0.5, 0.025), (1, 0)], zlift=[(0, 0), (1, 0)], seed=seed, wobble=0.035, c=c, lean=(0.16, 0.0), res=(24, 22))
    P = L.co(body); P[:, 0] += 0.9 * P[:, 2] ** 2; L.set_co(body, P)                              # the neck bends
    tip = np.array([0.195 * 0.16 + 0.9 * 0.195 ** 2, 0, 0.195])
    st = stem('stem', hi, (0, 0, 0), [(0.030, -0.034), (0.0275, -0.02), (0.0225, -0.008), (0.014, 0.0), (0.008, 0.004), (0.0065, 0.014), (0.006, 0.028), (0.0068, 0.036), (0.0072, 0.039), (0, 0.0395)],
              bend=(0.5, 0.1), lobes=5, lobe_amp=0.42, lobe_r=(0.012, 0.027), seed=seed, c=c, res=(20, 14), ridges=5, ridge_amp=0.07, lobe_p=1.6, bend_from=0.004)
    st.rotation_euler = (0, math.atan(0.16 + 1.8 * 0.195), 0); st.location = tip; L.apply_xf(st)
    obs = [body, st]
    for o in obs:                                                                                # lay it down
        o.rotation_euler = (0, math.radians(78), 0); L.apply_xf(o)
    zmin = min(L.co(o)[:, 2].min() for o in obs)
    for o in obs:
        P = L.co(o); P[:, 2] -= zmin; L.set_co(o, P)
    if hi:
        L.displace_np(body, lambda P: 0.0005 * fbm(P, seed + 3, 40, 3))
        body.data.materials.append(skin_mat('skin', [(0.010, 0.003, 0.016), (0.02, 0.005, 0.03), (0.035, 0.009, 0.05)], rough=(0.1, 0.3), speck_amt=0.05, speck=(0.3, 0.2, 0.35), russet=0.45,
                                            pore_bump=0.04, bloom=0.22, scale=0.7))
        st.data.materials.append(stem_mat('stem', green=(0.06, 0.10, 0.025), cut_z=None, woody=0.12))
    return obs


def acorn(hi, seed=23, c=None):
    """hangs from its stalk: the origin is the top of the stalk (the twig end), the nut points down"""
    nut = lobed('nut', hi, [(0, 0.0), (0.0015, 0.0007), (0.004, 0.0035), (0.0115, 0.012), (0.0158, 0.026), (0.0165, 0.038), (0.015, 0.047), (0.008, 0.052), (0, 0.053)], 2,
                crease=[(0, 0), (1, 0)], zlift=[(0, 0), (1, 0)], seed=seed, wobble=0.02, c=c, res=(18, 12))
    cap = stem('cap', hi, (0, 0, 0.0), [(0.0163, 0.031), (0.0196, 0.0325), (0.0208, 0.038), (0.0195, 0.047), (0.014, 0.0545), (0.0062, 0.058), (0.0036, 0.0605), (0.0029, 0.064), (0.0028, 0.068), (0.0033, 0.0705), (0, 0.071)],
               bend=(0.25, 0.1), seed=seed, c=c, res=(20, 14), bend_from=0.061)
    if hi:
        # overlapping cup scales: Voronoi-like bumps pushed out along the normal, only on the cup
        def cup(P):
            z = P[:, 2]; m = smoothstep(0.0305, 0.034, z) * (1 - smoothstep(0.056, 0.060, z)); th = np.arctan2(P[:, 1], P[:, 0]); row = (z - 0.031) / 0.0042
            cell = np.abs(((th * 7 / np.pi + (np.floor(row) % 2) * 0.5) % 1.0) - 0.5) * 2; sc = (1 - cell ** 2.2) * (1 - (row % 1.0)) ** 0.7
            return m * (0.0019 * sc + 0.0002 * fbm(P, seed, 600, 2))
        L.displace_np(cap, cup)
        t = NT('nut'); sp = list(t.sep(t.obj)); sp[2] = t.math('ADD', sp[2], 0.071); ang = t.math('ARCTAN2', sp[1], sp[0])
        stripe = t.noise(2.0, 4, 0.7, vec=t.comb(t.math('MULTIPLY', ang, 14.0), t.math('MULTIPLY', sp[2], 6.0), 0.0))
        col = t.ramp(stripe, [(0.3, (0.24, 0.115, 0.025)), (0.55, (0.40, 0.22, 0.05)), (0.8, (0.52, 0.33, 0.09))])
        col = t.mix(t.maprange(sp[2], 0.0, 0.012, 1.0, 0.0), col, (0.30, 0.2, 0.1)); col = t.mix(t.ramp(t.noise(260, 3, 0.6), [(0.62, 0.0), (0.7, 0.6)]), col, (0.2, 0.11, 0.04))
        t.set(base=col, rough=t.mixf(t.noise(40, 4, 0.6), 0.2, 0.42), normal=t.bump(t.math('ADD', stripe, t.math('MULTIPLY', t.noise(700, 2, 0.5), 0.2)), 0.12, 0.0003), sss=0.05, sss_scale=0.002)
        nut.data.materials.append(t.mat)
        t = NT('cup'); n = t.noise(420, 4, 0.7); z = t.math('ADD', t.sep(t.obj)[2], 0.071)
        col = t.mix(n, (0.055, 0.028, 0.012), (0.17, 0.09, 0.04)); col = t.mix(t.ramp(t.noise(38, 3, 0.6), [(0.6, 0.0), (0.75, 0.3)]), col, (0.2, 0.2, 0.14))        # grey-green lichen dust
        col = t.mix(t.maprange(z, 0.058, 0.064, 0.0, 1.0), col, t.mix(n, (0.08, 0.05, 0.025), (0.17, 0.11, 0.06)))
        t.set(base=col, rough=t.mixf(n, 0.7, 0.92), normal=t.bump(n, 0.6, 0.0004))
        cap.data.materials.append(t.mat)
    obs = [nut, cap]
    for o in obs:                                              # hang: top of the stalk at the origin
        P = L.co(o); P[:, 2] -= 0.071; L.set_co(o, P)
    return obs


SPECS = {
    'Pepper_Red': dict(fn=lambda hi, c: pepper(hi, [(0.30, 0.006, 0.005), (0.43, 0.010, 0.007), (0.55, 0.028, 0.012)], 1, green=((0.16, 0.07, 0.015), 0.3), c=c), fam='food_fruit', frame='421/18', px=1024,
                       dresses='red bell pepper, three lobes, about 9.5 cm tall with a 4 cm cut stalk, calyx collar and one leaf left on the stalk', ground='weathered_brown_planks'),
    'Pepper_Green': dict(fn=lambda hi, c: pepper(hi, [(0.09, 0.17, 0.02), (0.15, 0.27, 0.035), (0.24, 0.36, 0.06)], 2, lobes=4, c=c), fam='food_fruit', frame='421/19', px=1024,
                         dresses='green bell pepper, four lobes, about 9.5 cm tall with stalk, calyx and one leaf', ground='weathered_brown_planks'),
    'Pepper_Yellow': dict(fn=lambda hi, c: pepper(hi, [(0.48, 0.24, 0.008), (0.58, 0.34, 0.012), (0.66, 0.43, 0.03)], 3, green=((0.27, 0.30, 0.03), 0.5), c=c), fam='food_fruit', frame='421/20', px=1024,
                          dresses='yellow-orange bell pepper ripening from green at the shoulder, three lobes, stalk, calyx and one leaf', ground='weathered_brown_planks'),
    'Pumpkin': dict(fn=lambda hi, c: pumpkin(hi, c=c), fam='food_fruit', frame='421/21', px=1024, dresses='small pie pumpkin, eleven ribs, about 20 cm across and 13 cm tall, with a twisted woody stalk',
                    ground='weathered_brown_planks'),
    'Tomato': dict(fn=lambda hi, c: tomato(hi, c=c), fam='food_fruit', frame='421/22', px=1024, dresses='ripe tomato, about 7.5 cm across, faintly ribbed at the shoulder, green star calyx and stalk stub',
                   ground='weathered_brown_planks'),
    'Aubergine': dict(fn=lambda hi, c: aubergine(hi, c=c), fam='food_fruit', frame='421/25', px=1024, dresses='aubergine lying on its side, about 21 cm long, dark purple with a waxy bloom, green five-pointed calyx and stalk',
                      ground='weathered_brown_planks'),
    'Acorn_Hanging': dict(fn=lambda hi, c: acorn(hi, c=c), fam='tree_fruit', frame='421/23', px=512, hang=True,
                          dresses='the fruit hanging in the fruit tree: a large acorn-shaped nut, 5.3 cm, tan striped shell in a scaled brown cup on a 1 cm stalk; origin at the top of the stalk so it hangs from a twig',
                          ground='forrest_ground_01'),
}


WEAK = {
    'Pepper_Red': 'Game material has no subsurface term, so the flesh reads a little harder than a real pepper in back light. The leaf is a 0.5 mm closed shell, not a translucent card. The body is one smooth parametric surface: no bruises, dents or asymmetry beyond the lobe warp. About 70 % of the UV square is used.',
    'Pepper_Green': 'Same generator as the red pepper with four lobes: the two read as siblings rather than as two individual fruit. No subsurface in the game material; leaf is a thin closed shell.',
    'Pepper_Yellow': 'Same generator as the red pepper: sibling shape. The green-to-yellow ripening band follows height only, not the sun side. No subsurface in the game material.',
    'Pumpkin': 'Ribs are evenly spaced (eleven, mildly warped); a real pumpkin has a flat pale ground spot and bigger irregularities. Stalk is a ribbed tube without the corky cracking of a dried stem. Crease dirt is baked from ambient occlusion of the source and is uniform around the fruit.',
    'Tomato': 'Sepals are thick (about 1 mm solid) and lie flat rather than curling; their game mesh is a decimation of the source, so its triangles are irregular. Skin is very clean: no cracks at the shoulder, no stem scar ring. No subsurface in the game material, which a tomato needs in back light.',
    'Aubergine': 'Calyx lobes are smooth, without the prickles and veining of a real one. The waxy bloom is a procedural noise, not wiped where it would be handled. Shape is a clean teardrop.',
    'Acorn_Hanging': 'Identity is a guess from a 7x12 px frame (brown cap over a yellow body, pointed below): built as a large acorn, 5.3 cm, which is big for an oak; scale it at placement if it must read from the gameplay camera. Cup scales are a soft displaced pattern, not individual scales: at 1 m the cup reads as a rough brown cap rather than as imbricate scales. No twig or leaves: the tree it hangs in belongs to the vegetation pass.',
}


def build(name, mode):
    sp = SPECS[name]; L.reset(); asset = 'SM_%s_PR' % name; outdir = os.path.join(L.UNC, sp['fam'], name)
    hc = L.coll('Source_Hi'); hi = sp['fn'](True, hc); hang = sp.get('hang')
    R = L.review_setup(ground=sp['ground'], ground_scale=1.6 if 'planks' in sp['ground'] else 0.8, exposure=-5.0)

    def shots(obs, tag, d):
        if hang:                                    # hangs in the tree in game; shown lying on the ground
            for o in obs:
                o.rotation_euler = (math.radians(96), 0, math.radians(25))
            bpy.context.view_layer.update(); z0 = L.bounds(obs)[0][2]
            for o in obs:
                o.location.z -= z0
        L.shot(R, os.path.join(d, '%s_beauty.png' % tag), obs, az=32, el=24, fill=0.5, lens=85, spp=192, fstop=8)
        L.shot(R, os.path.join(d, '%s_close.png' % tag), obs, az=-28, el=38, fill=0.95, lens=100, res=(1000, 800), spp=192, fstop=11)
        for o in obs:
            o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0)
    if mode == 'review':
        shots(hi, name + '_hi', L.REVIEW); return
    lo = L.join(sp['fn'](False, L.coll(asset)), asset); L.pack_uv(lo, margin=0.02)
    for o in hi:
        o.hide_render = True
    ids = L.origin_ids([sp['fam']])[sp['fam']]
    size = float(np.linalg.norm(np.array(lo.dimensions)))
    man = L.finish_static(asset, 'prop_small', lo, hi, outdir, sp['px'], families=[sp['fam'], '421 items/food/food- frame %s' % sp['frame'].split('/')[1]], origin={sp['fam']: ids},
                          dresses=sp['dresses'], extrude=size * 0.025, maxdist=size * 0.06, third_party=[], script=SCRIPT + ' ' + name + ' final', ss=2,
                          weaknesses=WEAK[name],
                          extra={'origin_ids_note': 'the family shares its origin IDs between all of its frames; this asset dresses the placements that show frame %s' % sp['frame'],
                                 **({'pivot': 'top of the stalk at the origin (hangs from a twig); the nut points down -Z'} if hang else {})})
    shots([lo], 'render', outdir)
    bpy.context.scene.render.filepath = '//render'; bpy.ops.wm.save_mainfile(compress=True)


if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        build(n, mode)
