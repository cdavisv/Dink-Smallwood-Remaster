"""Fold / drape displacement fields for Dink's garments. fine=False gives the game-mesh macro shape, fine=True adds
the bake-source wrinkles. All functions return a per-vertex offset along the base normal, in metres."""
import numpy as np
from garlib import vnoise, fbm, ridge, poly_params, sstep

def setup(bones):
    global S, E_, Wr, T, K, A, LU, LT, LF
    S, E_, Wr, T, K, A = [np.array(bones[n]) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')]
    LU = np.linalg.norm(E_ - S); LF = np.linalg.norm(Wr - E_); LT = np.linalg.norm(K - T)

def _mir(p):
    m = p.copy(); m[:, 0] = np.abs(m[:, 0]); return m

def arm_h(p):
    """Signed 'arm side' measure in metres (>0: sleeve, <0: torso). Armhole surface between spine and arm axes."""
    m = _mir(p); s, th, d_arm = poly_params(m, [S, E_, Wr], (0, 0, -1))
    d_sp = np.sqrt(m[:, 0] ** 2 + (m[:, 1] + .02) ** 2)
    dU = (E_ - S) / LU; s0 = (m - S) @ dU
    return np.minimum((d_sp / .16 - d_arm / .058) * .05, s0 + .03)

def shirt(p, fine):
    m = _mir(p); s, th, dist = poly_params(m, [S, E_, Wr], (0, 0, -1))
    h = arm_h(p); armw = sstep(-.004, .03, h)
    e = s - LU; f = e
    tuck = 1 - sstep(.085, .118, f)
    off = -.003 + .011 * sstep(.0, .05, h) * sstep(.02, .10, s)
    off = off * tuck - .001 * (1 - tuck)
    off += .008 * np.exp(-((f - .055) / .035) ** 2) * tuck * armw
    sag = .006 * np.maximum(np.cos(th), 0) * sstep(.04, .16, s) * tuck * armw
    n1 = vnoise(p, 7, 1); n2 = vnoise(p, 13, 2); a1 = sstep(.25, .7, vnoise(p, 5, 3)); a2 = sstep(.2, .65, vnoise(p, 6, 4))
    free = sstep(.03, .09, s) * tuck * armw
    w1 = fbm(p, 9, 2, 101); w2 = fbm(p, 12, 2, 102)
    a1 = sstep(.38, .62, vnoise(p, 11, 3)); a2 = sstep(.36, .6, vnoise(p, 13, 4))
    sg = np.sign(p[:, 0])
    F1 = .0036 * ridge(2 * np.pi * s / .062 + 1.6 * th * sg + 9 * w1) * free * (1 - sstep(LU - .06, LU, s)) * (.35 + .65 * a1)
    F2 = .0026 * ridge(2 * np.pi * e / .026 + 8 * w2 + .7 * th, 1.6) * np.exp(-(e / .055) ** 2) * (.45 + .55 * a2) * free
    F3 = .0028 * ridge(2 * np.pi * f / .028 + 8 * w1 + 1.2 * th * sg, 1.8) * sstep(.0, .05, f) * (1 - sstep(.088, .118, f)) * (.4 + .6 * a1) * armw
    d = off + sag + F1 + F2 + F3
    if fine:
        n3 = vnoise(p, 22, 5)
        d += .0011 * ridge(2 * np.pi * s / .024 + 3.2 * th * sg + 15 * fbm(p, 14, 2, 103), 1.8) * free * sstep(.4, .65, vnoise(p, 12, 6))
        d += .0008 * ridge(2 * np.pi * s / .019 - 2.4 * th * sg + 15 * fbm(p, 17, 2, 104), 1.8) * free * sstep(.45, .7, vnoise(p, 15, 10))
        d += .0010 * (fbm(p, 45, 3, 7) - .5) * (.3 + .7 * free)
        d += (1 - armw) * .0010 * ridge(p[:, 0] * 2 * np.pi / .018 + 5 * vnoise(p, 12, 8), 1.4) * sstep(.4, .7, vnoise(p, 8, 9))
    return d

def jerkin(p, fine):
    z = p[:, 2]; phi = np.arctan2(p[:, 0], -(p[:, 1] + .02))
    d = np.full(len(p), .004)
    n1 = vnoise(p, 6, 11); n2 = vnoise(p, 11, 12)
    waist = np.exp(-((z - 1.045) / .04) ** 2)
    d += .0035 * ridge(2 * np.pi * z / .03 + 5 * n1 + .8 * np.sin(2 * phi), 1.6) * waist * (.3 + .7 * sstep(.3, .7, n2))
    d -= .004 * np.exp(-((z - 1.005) / .022) ** 2)   # cinched by the belt
    skirt = 1 - sstep(.93, .99, z)
    d += skirt * (.004 + .006 * ridge(7 * phi + 4 * n1, 1.3) * (1 - sstep(.86, .98, z) * .6))
    d += .003 * (fbm(p, 9, 3, 13) - .5)
    if fine:
        d += .0010 * ridge(2 * np.pi * z / .012 + 7 * n2 + 2 * phi, 1.4) * waist * sstep(.35, .7, vnoise(p, 14, 14))
        d += .0015 * (fbm(p, 30, 4, 15) - .5)
        # long stress creases
        d += .0012 * ridge(2 * np.pi * (p[:, 0] * .6 + z) / .045 + 6 * vnoise(p, 5, 16), 3.0) * sstep(.45, .75, vnoise(p, 4, 17))
    return d

def trousers(p, fine):
    m = _mir(p); s, th, dist = poly_params(m, [T, K, A], (0, -1, 0)); z = p[:, 2]
    e = s - LT; sg = np.sign(p[:, 0])
    leg = 1 - sstep(.86, .93, z)
    inboot = 1 - sstep(.350, .40, z)
    off = (.004 + .006 * sstep(0, .15, s) * leg) * (1 - inboot) - .001 * inboot
    off += .008 * np.exp(-((z - .43) / .035) ** 2)
    n1 = vnoise(p, 6, 21); n2 = vnoise(p, 11, 22); a1 = sstep(.25, .7, vnoise(p, 5, 23)); a2 = sstep(.2, .65, vnoise(p, 7, 24))
    w1 = fbm(p, 8, 2, 121); w2 = fbm(p, 11, 2, 122)
    a1 = sstep(.38, .62, vnoise(p, 9, 23)); a2 = sstep(.36, .6, vnoise(p, 12, 24))
    K1 = .0024 * ridge(2 * np.pi * e / .03 + 9 * w1 + .8 * th, 1.6) * np.exp(-(e / .06) ** 2) * (.25 + .75 * np.maximum(-np.cos(th), 0)) * (.4 + .6 * a1)
    K2 = .004 * np.exp(-((e + .01) / .06) ** 2) * np.maximum(np.cos(th), 0)
    T1 = .0038 * ridge(2 * np.pi * s / .08 + 2.2 * th * sg + 10 * w2, 2.0) * sstep(.05, .15, s) * (1 - sstep(LT - .09, LT, s)) * leg * (.3 + .7 * a2)
    C1 = .0036 * ridge(2 * np.pi * e / .065 - 2.0 * th * sg + 10 * w1, 2.0) * sstep(.05, .1, e) * (1 - sstep(.5, .6, z)) * (.3 + .7 * a1)
    B1 = .0028 * ridge(2 * np.pi * z / .032 + 9 * w2 + 1.3 * th * sg, 1.7) * np.exp(-((z - .445) / .05) ** 2) * (.45 + .55 * a2)
    d = off + (K1 + K2 + T1 + C1 + B1) * (1 - inboot)
    if fine:
        d += .0012 * ridge(2 * np.pi * s / .03 + 3.0 * th * sg + 15 * fbm(p, 12, 2, 125), 1.8) * sstep(.4, .65, vnoise(p, 10, 26)) * (1 - inboot)
        d += .0009 * ridge(2 * np.pi * s / .022 - 2.2 * th * sg + 15 * fbm(p, 15, 2, 126), 1.8) * sstep(.45, .7, vnoise(p, 13, 28)) * (1 - inboot)
        d += .0012 * (fbm(p, 40, 3, 27) - .5)
        crotch = np.exp(-((z - .87) / .05) ** 2) * (np.abs(p[:, 0]) < .12)
        d += .002 * ridge(2 * np.pi * (np.abs(p[:, 0]) * .8 + z) / .03 + 4 * n1, 1.6) * crotch
    return d
