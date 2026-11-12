"""seashell_conch (92 lands/details/beach- frame 4): a knobbed spiral gastropod shell lying on the sand.

The shell is one helico-spiral surface (logarithmic growth) with a shouldered, knobbed section, a siphonal canal,
a flared lip and a throat that closes the aperture. The same function gives the dense source and the game mesh.

    tools/bl.sh build_shell.py Conch [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_shell.py'
TURNS = 5.4; G = 1.62; ZC = 0.068; RC = 0.0205; A = 0.039; B = 0.0265; VS = 0.9          # VS = fraction of v that is the spiral; the rest is the throat
TH_END = 2 * math.pi * TURNS


def shell(hi, c):
    nu, nv = (112, 700) if hi else (12, 62)

    def fn(U, V):
        t = np.clip(V / VS, 0, 1); back = np.clip((V - VS) / (1 - VS), 0, 1)            # back: 0 on the spiral, 0..1 down the throat
        th = TH_END * t - back * 1.25; Wg = G ** ((th - TH_END) / (2 * np.pi)); ph = 2 * np.pi * U; cp = np.cos(ph); sp = np.sin(ph)
        rho = np.ones_like(ph)
        # shoulder with knobs (upper outer quadrant), fading out on the youngest whorls of the spire
        d = np.angle(np.exp(1j * (ph - 0.95))); sh = np.exp(-(d / 0.42) ** 2); knob = np.maximum(0, np.cos(8.5 * th)) ** 1.6
        rho += sh * (0.10 + 0.20 * knob * smoothstep(0.12, 0.4, t))
        # siphonal canal: the bottom of the section drawn out and pulled to the axis
        dn = np.clip(-sp, 0, 1) ** 2.2
        ax = sp * A * (1 + 0.85 * dn); rd = cp * B * (1 - 0.55 * dn) - 0.012 * dn
        # flared outer lip on the last third of a turn
        lip = smoothstep(TH_END - 2.0, TH_END, th) * (1 - back); rho *= 1 + 0.16 * lip * np.clip(cp, 0, 1) ** 1.5
        if hi:
            rho *= 1 + 0.011 * np.cos(22 * ph) * np.clip(cp + 0.35, 0, 1) + 0.004 * np.sin(150 * th) * np.clip(cp + 0.3, 0, 1)        # spiral cords, growth lines
        k = (1 - 0.07 * smoothstep(0, 0.12, back)) * (1 - 0.72 * back ** 1.4)             # lip thickness, then the throat narrows
        r = (RC + rd * rho * k) * Wg; z = (-ZC + ax * rho * k) * Wg
        r = np.where(back >= 1, RC * Wg * 0.9, r)
        return np.stack([r * np.cos(th), r * np.sin(th), z], -1)
    ob = L.grid_surface('shell', fn, nu, nv, c, pole0=True, pole1=True); L.fix_normals(ob)
    # lay it down: aperture side towards the ground, axis nearly level
    e = TH_END; M = Matrix.Rotation(math.radians(-38), 4, 'X') @ Matrix.Rotation(math.radians(96), 4, 'Y') @ Matrix.Rotation(-e, 4, 'Z')
    ob.matrix_world = M; L.apply_xf(ob); P = L.co(ob); P[:, 2] -= P[:, 2].min(); L.set_co(ob, P)
    return ob


def shell_mat():
    """driven by the surface parameters (UV): u = round the whorl section, v = along the spiral"""
    t = NT('shell'); uv = t.sep(t.uv); u = uv[0]; v = uv[1]
    cu = t.math('COSINE', t.math('MULTIPLY', u, 6.28318)); su = t.math('SINE', t.math('MULTIPLY', u, 6.28318))
    n_lo = t.noise(1.0, 4, 0.6, vec=t.comb(t.math('MULTIPLY', v, 60.0), t.math('MULTIPLY', u, 5.0), 0.0), distortion=0.6)
    n_fl = t.noise(1.0, 5, 0.7, vec=t.comb(t.math('MULTIPLY', v, 230.0), t.math('MULTIPLY', u, 2.0), 3.0), distortion=1.5)
    n_obj = t.noise(160, 4, 0.6); n_big = t.noise(28, 4, 0.6)
    cream = t.mix(n_lo, (0.34, 0.26, 0.165), (0.52, 0.43, 0.30)); su = t.math('ADD', su, t.math('MULTIPLY', t.math('SUBTRACT', n_fl, 0.5), 0.16))
    # two chestnut spiral bands on the shoulder and above the canal, broken into axial flames
    band = t.math('MAXIMUM', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', su, 0.42)), [(0.10, 1.0), (0.22, 0.0)]), t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', su, -0.45)), [(0.08, 1.0), (0.2, 0.0)]))
    flame = t.ramp(n_fl, [(0.40, 0.0), (0.50, 1.0)]); brown = t.mix(n_obj, (0.16, 0.055, 0.018), (0.28, 0.11, 0.035))
    col = t.mix(t.math('MULTIPLY', t.math('MAXIMUM', t.math('MULTIPLY', band, t.math('ADD', 0.25, t.math('MULTIPLY', flame, 0.75))), t.math('MULTIPLY', flame, 0.28)), 0.92), cream, brown)
    white = t.ramp(t.math('ABSOLUTE', su), [(0.0, 1.0), (0.16, 0.0)]); col = t.mix(t.math('MULTIPLY', white, 0.5), col, (0.58, 0.54, 0.46))
    # bleached, chalky spire and abrasion on the knobs
    worn = t.math('MAXIMUM', t.maprange(v, 0.2, 0.5, 1.0, 0.0, interp='SMOOTHSTEP'), t.math('MULTIPLY', t.ramp(t.pointiness, [(0.53, 0.0), (0.6, 1.0)]), 0.8))
    worn = t.math('MULTIPLY', worn, t.ramp(n_big, [(0.25, 0.4), (0.7, 1.0)])); col = t.mix(t.math('MULTIPLY', worn, 0.75), col, t.mix(n_obj, (0.50, 0.48, 0.43), (0.66, 0.64, 0.58)))
    # glossy flesh-pink throat
    inside = t.maprange(v, 0.895, 0.915, 0.0, 1.0); col = t.mix(inside, col, t.mix(n_lo, (0.55, 0.26, 0.17), (0.66, 0.42, 0.30)))
    # encrusting specks and sand packed into the hollows
    enc = t.math('MULTIPLY', t.ramp(t.voronoi(260, feature='F1'), [(0.0, 1.0), (0.3, 0.0)]), t.ramp(t.noise(19, 3, 0.6, vec=t.mapping(loc=(5, 2, 1))), [(0.42, 0.0), (0.6, 1.0)]))
    col = t.mix(t.math('MULTIPLY', enc, 0.8), col, (0.62, 0.61, 0.55))
    ao = t.ao(0.008, 12); grit = t.math('MULTIPLY', t.ramp(ao, [(0.45, 1.0), (0.82, 0.0)]), t.ramp(t.noise(90, 3, 0.6), [(0.3, 0.3), (0.7, 1.0)])); grit = t.math('MULTIPLY', grit, t.math('SUBTRACT', 1.0, inside))
    col = t.mix(t.math('MULTIPLY', grit, 0.85), col, t.mix(t.noise(900, 2, 0.5), (0.36, 0.30, 0.21), (0.62, 0.55, 0.42)))
    rough = t.mixf(n_obj, 0.26, 0.42); rough = t.mixf(worn, rough, 0.72); rough = t.mixf(inside, rough, 0.12); rough = t.mixf(enc, rough, 0.85); rough = t.mixf(grit, rough, 0.9)
    h = t.math('ADD', t.math('MULTIPLY', n_obj, 0.4), t.math('ADD', t.math('MULTIPLY', enc, 1.5), t.math('MULTIPLY', grit, t.noise(900, 2, 0.5))))
    t.set(base=col, rough=rough, normal=t.bump(h, 0.25, 0.0005), spec=0.6)
    return t.mat


WEAK = ('One helico-spiral surface: the whorls pass through each other inside, the columella and inner lip are not modelled, and the aperture is a throat that narrows to a point rather than a spiral cavity. '
        'Knobs are a cosine of the spiral angle, so they are evenly spaced. The banding is procedural (two bands, axial flames); it is not a scan of a real species. '
        '1,400 triangles on a 14 cm shell: the knobs are carried by the normal map more than by the silhouette. About a quarter of the texture holds the hidden inner whorl surfaces.')


def build(mode):
    L.reset(); name = 'Conch'; asset = 'SM_Seashell_Conch_PR'; outdir = os.path.join(L.UNC, 'seashell_conch', name)
    hi = shell(True, L.coll('Source_Hi')); hi.data.materials.append(shell_mat())
    R = L.review_setup(ground='coast_sand_01', ground_scale=1.2, exposure=-5.2)

    def shots(obs, tag, d):
        for o in obs:
            o.location.z = -0.002                              # settled a little into the sand
        L.shot(R, os.path.join(d, '%s_beauty.png' % tag), obs, az=30, el=30, fill=0.5, lens=85, spp=192, fstop=8)
        L.shot(R, os.path.join(d, '%s_close.png' % tag), obs, az=-40, el=22, fill=0.9, lens=100, res=(1000, 800), spp=192, fstop=11)
        for o in obs:
            o.location.z = 0
    if mode == 'review':
        shots([hi], name + '_hi', L.REVIEW); return
    lo = shell(False, L.coll(asset)); P0 = L.co(lo); c = (P0.min(0) + P0.max(0)) / 2; c[2] = P0[:, 2].min()
    for o in (lo, hi):
        P = L.co(o); L.set_co(o, P - c)
    L.pack_uv(lo, margin=0.02, average=False)
    ids = L.origin_ids(['seashell_conch'])['seashell_conch']
    L.finish_static(asset, 'prop_small', lo, [hi], outdir, 1024, families=['seashell_conch', '92 lands/details/beach- frame 4'], origin={'seashell_conch': ids},
                    dresses='knobbed spiral sea shell (a conch or whelk), 14 cm, lying aperture-down: cream with two chestnut bands broken into flames, bleached spire, pink throat, sand in the hollows',
                    extrude=0.004, maxdist=0.009, third_party=[], script=SCRIPT + ' Conch final', ss=2, weaknesses=WEAK)
    hi.hide_render = True; shots([lo], 'render', outdir); L.save_blend()


if __name__ == '__main__':
    a = L.args(); build(a[1] if len(a) > 1 else 'review')
