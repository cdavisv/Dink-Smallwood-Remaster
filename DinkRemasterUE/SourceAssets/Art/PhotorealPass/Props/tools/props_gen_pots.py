# Round-2 generators: glazed earthenware (storage jar, two-handled crock, bottle vase, footed bowl).
# exec'd by props_bake.py (uses MB, NT, vnoise, resamp, ell, ASSETS).


def m_glaze(name, g0, g1, foot=0.03, clay=((0.17, 0.075, 0.035), (0.4, 0.2, 0.1)), inside=None, zin=None):
    """lead-glazed earthenware: glaze pooled dark in the throwing rings and where it ran, breaking thin and pale over edges, crazed,
    pin-holed; a wavy glaze line above a bare biscuit foot; chips through to the clay on rim and foot; grime in the foot ring.
    g0 / g1 = thick / thin glaze colour; inside = (colour, z above which the inner wall shows it) optional second glaze"""
    s = NT(name); x, y, z = s.sep(s.P)
    an = s.node('ShaderNodeMath', operation='ARCTAN2'); s.L.new(y, an.inputs[0]); s.L.new(x, an.inputs[1]); ang = an.outputs[0]

    def cyl(ka, kz, seed=0.0):
        c = s.node('ShaderNodeCombineXYZ'); s.L.new(s.math('SINE', s.mul(ang, 1.0)), c.inputs[0]); s.L.new(s.math('COSINE', ang), c.inputs[1]); s.L.new(s.mul(z, kz), c.inputs[2])
        return s.vec(c.outputs[0], scale=(ka, ka, 1.0), loc=(seed, seed * 1.7, 0.0))
    rings = s.noise(1.0, 2.0, 0.5, vec=s.vec(s.P, scale=(2.0, 2.0, 150.0)))
    big = s.noise(5.0, 4.0, 0.6); fine = s.noise(700.0, 2.0); ao = s.ao(0.03, 8)
    gl = s.step(s.add(z, s.mul(s.sub(s.noise(1.0, 3.0, 0.5, vec=cyl(2.2, 0.0)), 0.5), 0.07)), foot, foot + 0.003)             # 1 = glazed
    rn = s.noise(1.0, 3.0, 0.55, vec=cyl(7.0, 1.6, 3.0)); run = s.step(rn, 0.6, 0.72)
    thick = s.sat(s.add(s.add(s.mul(s.sub(rings, 0.5), 0.45), s.mul(s.sub(big, 0.5), 1.5)), s.add(s.mul(run, 0.9), s.add(s.mul(s.inv(ao), 0.9), 0.3))))
    col = s.mix(g1, g0, thick)
    if inside is not None:
        r_ = s.math('SQRT', s.add(s.mul(x, x), s.mul(y, y))); nz = s.sep(s.geo.outputs['Normal'])
        inw = s.step(s.add(s.mul(nz[0], s.math('DIVIDE', x, s.mx(r_, 0.001))), s.mul(nz[1], s.math('DIVIDE', y, s.mx(r_, 0.001)))), -0.2, -0.5) if zin is None else s.step(z, zin, zin + 0.004)
        col = s.mix(col, s.mix(inside, s.mix(inside, (0.5, 0.45, 0.35), 1.0, 'MULTIPLY'), thick), inw)
    brk = s.mul(s.edge(0.004, 3.0), 0.55); cl = s.ramp(s.noise(90.0, 4.0, 0.7), [(0.3, clay[0]), (0.7, clay[1])])
    col = s.mix(col, s.mix(col, cl, 0.5), brk)                                                # glaze breaks thin over the edges
    cz = s.mul(s.inv(s.step(s.voro(120.0, 'DISTANCE_TO_EDGE'), 0.0, 0.012)), s.step(s.noise(9.0, 3.0), 0.45, 0.6))
    col = s.mix(col, s.mix(col, (0.35, 0.3, 0.25), 1.0, 'MULTIPLY'), s.mul(cz, 0.7))           # crazing, stained
    pin = s.step(fine, 0.73, 0.76); col = s.mix(col, s.mix(col, (0.3, 0.25, 0.2), 1.0, 'MULTIPLY'), s.mul(pin, 0.8))
    chip = s.mx(s.wear(0.006, 3.5, 34.0, 0.45), s.step(s.noise(23.0, 2.0, 0.4), 0.74, 0.76)); bare = s.mx(s.inv(gl), chip)
    col = s.mix(col, cl, bare)
    dirt = s.sat(s.add(s.mul(s.inv(ao), 1.2), s.mul(s.inv(s.step(z, 0.0, 0.06)), 0.5)))
    col = s.mix(col, s.mix(col, (0.3, 0.25, 0.19), 1.0, 'MULTIPLY'), s.mul(dirt, s.mixf(0.45, 0.9, bare)))
    sm = s.noise(14.0, 3.0, 0.6); rough = s.ramp(s.add(sm, s.mul(pin, 0.5)), [(0.3, 0.04), (0.6, 0.12), (0.85, 0.3)]); rough = s.mixf(rough, s.ramp(fine, [(0.3, 0.78), (0.7, 0.93)]), bare)
    h = s.add(s.add(s.mul(rings, 0.55), s.mul(s.mul(run, gl), 0.5)), s.add(s.mul(chip, -1.2), s.mul(s.mul(fine, bare), 0.25)))
    return s.finish(col, rough, 0.0, height=h, bump=0.0011, bevel=0.0018)


def _wob(sd, amp=0.012):
    def f(P):
        a = np.arctan2(P[:, 1], P[:, 0]); k = 1 + amp * np.sin(a * 2 + sd) * np.clip(P[:, 2] * 3, 0, 1) + 0.006 * vnoise(P, int(sd * 10), 9.0)
        return np.c_[P[:, 0] * k + amp * 0.4 * P[:, 2], P[:, 1] * k, P[:, 2] + 0.004 * np.sin(a + sd) * np.clip(P[:, 2] * 3, 0, 1)]
    return f


def pot(b, prof, sd, n=(28, 96), handles=None):
    b.lathe(prof, n=b.d(*n), mat='glaze', sub=b.d(1, 5), deform=_wob(sd))
    for (sgn, top, out, bot) in (handles or []):                # pulled strap handles, thumbed on at both ends
        ctrl = [[sgn * (top[0] - 0.012), 0, top[1]], [sgn * (top[0] + 0.02), 0, top[1] + 0.012], [sgn * out[0], 0, out[1]], [sgn * (bot[0] + 0.02), 0, bot[1] + 0.03], [sgn * (bot[0] - 0.012), 0, bot[1]]]
        pts = resamp(ctrl, b.d(3, 8)); n_ = len(pts); rw = np.interp(np.linspace(0, 1, n_), [0, 0.12, 0.5, 0.88, 1], [1.5, 1.0, 0.9, 1.05, 1.6])
        n0 = b.tube(pts, rw, sides=b.d(8, 16), mat='glaze', shape=ell(0.021, 0.0095, b.d(8, 16)), up=[0, 1, 0], ups=[(0, 1, 0)] * n_)
        b.deform_since(n0, _wob(sd))
    return {}


_JAR = [(0, 0), (0.105, 0), (0.122, 0.006), (0.125, 0.02), (0.118, 0.032), (0.15, 0.09), (0.205, 0.22), (0.247, 0.4), (0.24, 0.52), (0.2, 0.62), (0.16, 0.672), (0.148, 0.695), (0.158, 0.715), (0.171, 0.727), (0.172, 0.735),
        (0.163, 0.738), (0.15, 0.73), (0.136, 0.7), (0.146, 0.66), (0.188, 0.6), (0.225, 0.5), (0.232, 0.4), (0.19, 0.22), (0.13, 0.08), (0.08, 0.035), (0, 0.03)]
_JUG = [(0, 0), (0.125, 0), (0.146, 0.006), (0.15, 0.02), (0.146, 0.03), (0.185, 0.12), (0.222, 0.27), (0.217, 0.4), (0.18, 0.49), (0.152, 0.525), (0.15, 0.545), (0.162, 0.566), (0.166, 0.576), (0.158, 0.58),
        (0.145, 0.572), (0.136, 0.545), (0.14, 0.52), (0.168, 0.48), (0.203, 0.4), (0.208, 0.27), (0.17, 0.12), (0.11, 0.04), (0, 0.032)]
_VASE = [(0, 0), (0.055, 0), (0.068, 0.005), (0.07, 0.016), (0.066, 0.026), (0.095, 0.11), (0.121, 0.25), (0.108, 0.39), (0.06, 0.5), (0.04, 0.58), (0.042, 0.63), (0.054, 0.668), (0.058, 0.68), (0.052, 0.684),
         (0.043, 0.676), (0.032, 0.63), (0.03, 0.58), (0.048, 0.5), (0.094, 0.39), (0.107, 0.25), (0.082, 0.11), (0.04, 0.03), (0, 0.026)]
_BOWL = [(0, 0.004), (0.06, 0.004), (0.066, 0.0), (0.08, 0.0), (0.084, 0.008), (0.078, 0.03), (0.105, 0.052), (0.17, 0.1), (0.203, 0.148), (0.21, 0.16), (0.207, 0.166), (0.198, 0.162), (0.19, 0.148), (0.158, 0.104), (0.095, 0.064),
         (0, 0.054)]
_PV = lambda h, rr, lens: {'game': ((1.6, -4.4, 6.0), (0, 0, h * 0.5), lens), 'close': ((0.55 + rr, -0.85 - rr, 0.6 + h), (0, 0, h * 0.5), 38), 'int': ((0.55 + rr, -0.85 - rr, 0.6 + h), (0, 0, h * 0.5), 38)}
_PT = dict(cls='prop', px=1024, extrude=0.004, maxdist=0.015, sharp=50.0, int_watts=18.0)
ASSETS['SM_Jar_Storage_PR'] = dict(_PT, fn=lambda b: pot(b, _JAR, 1.0), mats=lambda: {'glaze': m_glaze('H_glaze', (0.06, 0.028, 0.012), (0.24, 0.12, 0.05), foot=0.07)},
                                   slots=[('MI_Jar_Storage', 'opaque', None)], views=_PV(0.74, 0.25, 150), int_light=(0.7, -0.6, 1.0))
ASSETS['SM_Jar_Jug_PR'] = dict(_PT, fn=lambda b: pot(b, _JUG, 2.3, handles=[(1, (0.158, 0.535), (0.25, 0.47), (0.222, 0.3)), (-1, (0.158, 0.535), (0.25, 0.47), (0.222, 0.3))]),
                               mats=lambda: {'glaze': m_glaze('H_glaze', (0.05, 0.065, 0.08), (0.24, 0.29, 0.32), foot=0.06)},
                               slots=[('MI_Jar_Jug', 'opaque', None)], views=_PV(0.58, 0.25, 150), int_light=(0.7, -0.6, 0.9))
ASSETS['SM_Jar_Vase_PR'] = dict(_PT, fn=lambda b: pot(b, _VASE, 4.1, n=(22, 80)), mats=lambda: {'glaze': m_glaze('H_glaze', (0.07, 0.01, 0.008), (0.25, 0.045, 0.028), foot=0.045)},
                                slots=[('MI_Jar_Vase', 'opaque', None)], views=_PV(0.68, 0.12, 200), int_light=(0.5, -0.5, 0.9))
ASSETS['SM_Jar_Bowl_PR'] = dict(_PT, cls='prop_small', fn=lambda b: pot(b, _BOWL, 5.2, n=(26, 90)),
                                mats=lambda: {'glaze': m_glaze('H_glaze', (0.1, 0.06, 0.025), (0.3, 0.2, 0.09), foot=0.035, inside=(0.52, 0.42, 0.24), zin=None)},
                                slots=[('MI_Jar_Bowl', 'opaque', None)], views=_PV(0.17, 0.2, 230), int_light=(0.45, -0.4, 0.5), int_watts=10.0)
