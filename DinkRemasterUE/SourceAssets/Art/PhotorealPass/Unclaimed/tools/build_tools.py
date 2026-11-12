"""hand_tool_small (447 items/tools frames 5, 6, 10, 15: axe; 8, 16: hammer; 7, 14: tongs).

Each tool is a set of swept solids (forged iron, ash handles). The dense source carries hammer marks, scale,
rust and grain; the game mesh is a decimation of it.

    tools/bl.sh build_tools.py <name|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
from pplib import NT, fbm

SCRIPT = 'build_tools.py'


# ---------------------------------------------------------------------------------------------- materials
def iron_mat(name, polish=None, rust=0.5, seed=0.0):
    """forged iron: brown-black patina with fine rust bloom (scan), heavier rust in the hollows, bright worn metal on edges; polish = (axis, lo, hi) ground-bright band"""
    t = NT(name); sc = t.scan('rusty_metal_02', scale=7.0, loc=(seed, seed * 0.7, 0)); n1 = t.noise(34, 6, 0.7, vec=t.mapping(loc=(seed, 0, 0))); n2 = t.noise(210, 3, 0.6)
    n3 = t.noise(9, 3, 0.5, vec=t.mapping(loc=(0, seed, 0)))
    patina = t.mix(n2, (0.020, 0.017, 0.015), (0.050, 0.040, 0.033))
    rust_c = t.mix(0.55, t.hsv(sc['diff'], sat=1.05, v=0.32), t.mix(n2, (0.060, 0.022, 0.008), (0.150, 0.060, 0.020)))
    ao = t.ao(0.012, 12); rm = t.ramp(t.math('ADD', t.math('ADD', t.math('MULTIPLY', n1, 0.6), t.math('MULTIPLY', n3, 0.4)), t.math('MULTIPLY', t.math('SUBTRACT', 1.0, ao), 0.9)),
                                      [(0.50 - 0.15 * rust, 0.0), (0.80 - 0.15 * rust, 1.0)])
    base = t.mix(t.math('MULTIPLY', rm, 0.85), patina, rust_c)
    edge = t.math('MULTIPLY', t.ramp(t.pointiness, [(0.52, 0.0), (0.57, 1.0)]), t.ramp(t.noise(60, 3, 0.6), [(0.3, 0.2), (0.7, 0.9)]))
    if polish:
        ax, lo, hi = polish; v = t.sep(t.obj)[ax]; edge = t.math('MAXIMUM', edge, t.math('MULTIPLY', t.maprange(v, lo, hi, 0.0, 1.0, interp='SMOOTHSTEP'), t.ramp(n1, [(0.2, 0.7), (0.8, 1.0)])))
    scratch = t.noise(3.0, 2, 0.5, vec=t.mapping(scale=(300, 14, 14)))
    steel = t.mix(scratch, (0.22, 0.21, 0.20), (0.42, 0.41, 0.39)); base = t.mix(edge, base, steel)
    metal = t.mixf(edge, t.mixf(rm, 0.6, 0.0), 1.0); rough = t.mixf(edge, t.mixf(rm, t.mixf(n2, 0.45, 0.65), 0.85), t.mixf(scratch, 0.25, 0.42))
    dents = t.noise(55, 3, 0.5); h = t.math('ADD', t.math('MULTIPLY', dents, 0.6), t.math('MULTIPLY', n2, t.mixf(edge, 0.5, 0.05)))
    nrm = t.bump(h, 0.35, 0.0012, normal=t.normalmap(sc['nor_gl'], 0.5))
    t.set(base=base, rough=rough, metal=metal, normal=nrm)
    return t.mat


def wood_mat(name, axis=0, grip=None, dark_from=None, light=(0.27, 0.155, 0.065), dark=(0.10, 0.052, 0.022)):
    """old ash handle: long grain along `axis`, open pores, grime and sweat-darkening; grip = (lo, hi) hand-polished zone, dark_from = (lo, hi) oil and rust staining towards the head"""
    t = NT(name); sc = [42.0, 42.0, 42.0]; sc[axis] = 1.6; g = t.mapping(scale=tuple(sc)); gr = t.noise(1.0, 6, 0.65, vec=g, distortion=0.8)
    sc1 = [130.0, 130.0, 130.0]; sc1[axis] = 3.0; fine = t.noise(1.0, 3, 0.6, vec=t.mapping(scale=tuple(sc1)))
    sc2 = [420.0, 420.0, 420.0]; sc2[axis] = 7.0; pore = t.ramp(t.noise(1.0, 2, 0.5, vec=t.mapping(scale=tuple(sc2))), [(0.56, 0.0), (0.66, 1.0)])
    base = t.ramp(t.math('ADD', t.math('MULTIPLY', gr, 0.7), t.math('MULTIPLY', fine, 0.3)), [(0.30, dark), (0.50, light), (0.72, tuple(min(1, c * 1.45) for c in light))])
    base = t.mix(t.math('MULTIPLY', pore, 0.75), base, tuple(c * 0.35 for c in dark))
    grime = t.ramp(t.noise(6, 5, 0.65), [(0.35, 0.0), (0.7, 1.0)]); base = t.mix(t.math('MULTIPLY', grime, 0.55), base, (0.035, 0.025, 0.017))
    v = t.sep(t.obj)[axis]; rough = t.mixf(gr, 0.5, 0.72)
    if dark_from:
        d = t.maprange(t.math('ADD', v, t.math('MULTIPLY', t.math('SUBTRACT', gr, 0.5), 0.06)), dark_from[0], dark_from[1], 0.0, 1.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', d, 0.8), base, (0.035, 0.02, 0.012))
    if grip:
        gz = t.math('MULTIPLY', t.maprange(v, grip[0], grip[0] + 0.06, 0.0, 1.0, interp='SMOOTHSTEP'), t.maprange(v, grip[1] - 0.08, grip[1], 1.0, 0.0, interp='SMOOTHSTEP'))
        gz = t.math('MULTIPLY', gz, t.ramp(t.noise(11, 3, 0.6), [(0.25, 0.4), (0.7, 1.0)])); rough = t.mixf(t.math('MULTIPLY', gz, 0.85), rough, 0.27)
        base = t.mix(t.math('MULTIPLY', gz, 0.45), base, tuple(c * 0.55 for c in light))
    nick = t.ramp(t.noise(26, 2, 0.5, vec=t.mapping(loc=(4.0, 1.0, 2.0))), [(0.74, 0.0), (0.78, 1.0)]); base = t.mix(t.math('MULTIPLY', nick, 0.8), base, tuple(min(1, c * 1.9) for c in light))    # fresh dings show pale wood
    ao = t.ao(0.01, 8); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.5, 1.0), (0.9, 0.0)]), 0.6), base, (0.03, 0.02, 0.014))
    h = t.math('ADD', t.math('ADD', t.math('MULTIPLY', gr, 0.6), t.math('MULTIPLY', pore, -0.9)), t.math('MULTIPLY', nick, -1.5))
    t.set(base=base, rough=rough, normal=t.bump(h, 0.4, 0.0007))
    return t.mat


# ---------------------------------------------------------------------------------------------- tools (lying flat, handle along X)
def axe(q, c):
    """felling axe, 78 cm: bearded forged head on a curved ash helve with a fawn's-foot end; lies on its cheek"""
    zc = 0.0178
    head = L.sweep('head', [(0.300, 0.037, zc, 0.024, 0.0150, 5), (0.300, 0.020, zc, 0.027, 0.0170, 5), (0.300, 0.000, zc, 0.030, 0.0176, 4.5), (0.298, -0.030, zc, 0.027, 0.0130, 4),
                            (0.292, -0.070, zc, 0.032, 0.0090, 3.5), (0.281, -0.110, zc, 0.046, 0.0060, 3.2), (0.271, -0.150, zc, 0.061, 0.0030, 3), (0.268, -0.170, zc, 0.066, 0.0007, 3)],
                   nu=16 * q, nv=20 * q, c=c)
    helve = L.sweep('helve', [(-0.425, -0.020, 0.0138, 0.0215, 0.0135, 2.4), (-0.395, -0.016, 0.0138, 0.0205, 0.0130, 2.4), (-0.33, -0.007, 0.0135, 0.0160, 0.0115, 2.3), (-0.15, 0.004, 0.0150, 0.0155, 0.0115, 2.3),
                              (0.05, 0.004, 0.0165, 0.0160, 0.0120, 2.3), (0.22, 0.001, zc, 0.0175, 0.0125, 2.5), (0.275, 0.0, zc, 0.0185, 0.0118, 2.8), (0.337, 0.0, zc, 0.0185, 0.0112, 2.8)],
                    nu=12 * q, nv=22 * q, c=c)
    if q > 1:
        L.displace_np(head, lambda P: 0.00035 * fbm(P, 3, 60, 3) + 0.00012 * fbm(P, 5, 260, 2)); L.displace_np(helve, lambda P: 0.00015 * fbm(P * np.array([0.1, 1, 1]), 7, 180, 2))
        head.data.materials.append(iron_mat('iron', polish=(1, -0.142, -0.166), rust=0.55, seed=1.3))
        helve.data.materials.append(wood_mat('ash', axis=0, grip=(-0.40, -0.12), dark_from=(0.18, 0.27)))
    return [head, helve]


def hammer(q, c):
    """smith's cross-peen hammer, 33 cm: square face one end, wedge peen the other, short ash handle"""
    zc = 0.0195
    head = L.sweep('head', [(0.105, 0.050, zc, 0.0170, 0.0170, 7), (0.105, 0.044, zc, 0.0190, 0.0190, 7), (0.105, 0.020, zc, 0.0195, 0.0195, 6), (0.105, 0.0, zc, 0.0200, 0.0195, 6),
                            (0.105, -0.022, zc, 0.0180, 0.0190, 5), (0.105, -0.045, zc, 0.0100, 0.0185, 4), (0.105, -0.060, zc, 0.0028, 0.0180, 3)], nu=16 * q, nv=18 * q, c=c)
    handle = L.sweep('handle', [(-0.205, 0.0, 0.0150, 0.0165, 0.0135, 2.4), (-0.18, 0.0, 0.0150, 0.0160, 0.0130, 2.4), (-0.08, 0.001, 0.0165, 0.0135, 0.0115, 2.3), (0.03, 0.0, 0.0185, 0.0130, 0.0110, 2.3),
                                (0.085, 0.0, zc, 0.0140, 0.0105, 2.6), (0.130, 0.0, zc, 0.0140, 0.0100, 2.6)], nu=12 * q, nv=16 * q, c=c)
    if q > 1:
        L.displace_np(head, lambda P: 0.0003 * fbm(P, 13, 70, 3) + 0.0001 * fbm(P, 15, 260, 2)); L.displace_np(handle, lambda P: 0.00015 * fbm(P * np.array([0.1, 1, 1]), 17, 180, 2))
        head.data.materials.append(iron_mat('iron', polish=(1, 0.040, 0.050), rust=0.35, seed=4.1))
        handle.data.materials.append(wood_mat('ash', axis=0, grip=(-0.2, -0.03), dark_from=(0.03, 0.09)))
    return [head, handle]


def tongs(q, c):
    """blacksmith's flat-jaw tongs, 52 cm: two forged bars on a domed rivet, lying slightly open"""
    obs = []
    for s, z in ((1, 0.0052), (-1, 0.0128)):
        rows = [(-0.375, -0.058 * s, 0.0055, 0.0046, 0.0046, 2.0), (-0.36, -0.057 * s, 0.0055, 0.0050, 0.0050, 2.0), (-0.22, -0.046 * s, 0.0058, 0.0056, 0.0056, 2.2), (-0.08, -0.028 * s, 0.0062, 0.0062, 0.0058, 2.6),
                (-0.02, -0.012 * s, (0.0062 + z) / 2, 0.0090, 0.0048, 4.0), (0.02, -0.002 * s, z, 0.0118, 0.0042, 4.5), (0.045, 0.004 * s, z, 0.0120, 0.0042, 4.5), (0.075, 0.016 * s, (z + 0.0085) / 2, 0.0090, 0.0052, 4.0),
                (0.105, 0.019 * s, 0.0085, 0.0075, 0.0058, 4.0), (0.135, 0.0105 * s, 0.0085, 0.0070, 0.0056, 4.5), (0.165, 0.0062 * s, 0.0085, 0.0052, 0.0054, 5.0), (0.182, 0.0058 * s, 0.0085, 0.0048, 0.0052, 5.0)]
        obs.append(L.sweep('bar%d' % (1 if s > 0 else 2), rows, nu=10 * q, nv=30 * q, c=c))
    obs.append(L.sweep('rivet', [(0.032, 0.001, -0.0002, 0.0052, 0.0052, 2), (0.032, 0.001, 0.0012, 0.0072, 0.0072, 2), (0.032, 0.001, 0.0030, 0.0050, 0.0050, 2), (0.032, 0.001, 0.0150, 0.0050, 0.0050, 2),
                                 (0.032, 0.001, 0.0168, 0.0072, 0.0072, 2), (0.032, 0.001, 0.0186, 0.0050, 0.0050, 2)], nu=10 * q, nv=10 * q, c=c, up=(1, 0, 0)))
    if q > 1:
        m = iron_mat('iron', rust=0.7, seed=7.7)
        for i, o in enumerate(obs):
            L.displace_np(o, lambda P, i=i: 0.00028 * fbm(P, 23 + i, 80, 3) + 0.0001 * fbm(P, 29 + i, 300, 2)); o.data.materials.append(m)
    return obs


SPECS = {
    'Axe_Felling': dict(fn=axe, cls='prop', px=1024, tris=1500, frames='5, 6, 10, 15', dresses='felling axe, 78 cm: bearded forged-iron head with a ground edge, on a curved ash helve; authored lying on its cheek (frames 5 and 15); frames 6 and 10 show the same axe leaning, a placement rotation',
                        weak='Head and helve are separate swept solids that pass through each other: there is no eye, no wedge and no lip where the wood meets the iron. The helve grain is procedural streaking, not a scan, and does not follow the curve. Authored lying flat; the leaning frames need a tilt at placement and a wall or block to lean on.'),
    'Hammer_Smith': dict(fn=hammer, cls='prop_small', px=1024, tris=1100, frames='8, 16', dresses="smith's cross-peen hammer, 33 cm: square struck face, wedge peen, short ash handle",
                         weak='No eye or wedge where the handle passes the head (two solids intersect). The struck face has no mushrooming or dings beyond a noise dent pattern. Handle grain is procedural.'),
    'Tongs_Smith': dict(fn=tongs, cls='prop_small', px=1024, tris=1300, frames='7, 14', dresses="blacksmith's flat-jaw tongs, 55 cm: two forged bars on a domed rivet, lying slightly open",
                        weak='Bars are smooth sweeps: no hammer facets or drawn-out taper marks beyond noise, and the boss is not visibly flattened by forging. Rust is one scan layered by a noise mask; it does not concentrate where water would sit. Thin reins give the bake little texel area (about 1 px per 0.5 mm).'),
}


def build(name, mode):
    sp = SPECS[name]; L.reset(); asset = 'SM_%s_PR' % name; outdir = os.path.join(L.UNC, 'hand_tool_small', name)
    hc = L.coll('Source_Hi'); hi = sp['fn'](4, hc); R = L.review_setup(ground='forrest_ground_01', ground_scale=0.8, exposure=-5.0)

    def shots(obs, tag, d):
        L.shot(R, os.path.join(d, '%s_beauty.png' % tag), obs, az=25, el=38, fill=0.62, lens=70, spp=192)
        lo_, hi_ = L.bounds(obs); c = (lo_ + hi_) / 2; c[0] = hi_[0] - (hi_[0] - lo_[0]) * 0.22
        L.shot(R, os.path.join(d, '%s_close.png' % tag), center=c, radius=float(np.linalg.norm(hi_ - lo_)) * 0.2, az=-35, el=32, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
    if mode == 'review':
        shots(hi, name + '_hi', L.REVIEW); return
    lo = L.make_lo(hi, sp['tris'], asset, L.coll(asset), angle=60, margin=0.01); L.pivot_base_center(lo)
    ids = L.origin_ids(['hand_tool_small'])['hand_tool_small']; size = float(np.linalg.norm(np.array(lo.dimensions)))
    # the source was built resting on z = 0 around the tool's own centre: move it with the pivot
    P0 = np.array(L.bounds(hi)[0]); P1 = np.array(L.bounds(hi)[1]); off = np.array([(P0[0] + P1[0]) / 2, (P0[1] + P1[1]) / 2, P0[2]])
    for o in hi:
        o.location = tuple(-off); L.apply_xf(o)
    L.finish_static(asset, sp['cls'], lo, hi, outdir, sp['px'], families=['hand_tool_small', '447 items/tools/tool- frames %s' % sp['frames']], origin={'hand_tool_small': ids}, dresses=sp['dresses'],
                    extrude=0.0015, maxdist=0.006, third_party=['rusty_metal_02'], script=SCRIPT + ' ' + name + ' final', ss=2, weaknesses=sp['weak'], collision=False,
                    extra={'origin_ids_note': 'the family shares its origin IDs between all of its frames; this asset dresses the placements that show frames %s' % sp['frames'],
                           'contact_crop': 0.8})
    for o in hi:
        o.hide_render = True
    shots([lo], 'render', outdir)
    L.save_blend()


if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        build(n, mode)
