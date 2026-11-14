"""Photoreal pillbug: giant terrestrial isopod skinned to the existing 43-bone SK_Pillbug rig and its clips.
usage: blender -b -t 4 --python pillbug.py -- <stage>   stage: look | final | review
"""
import bpy, sys, os, math, json, random
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *

A = args(); STAGE = A[0] if A else 'look'
DST = OUT / 'Pillbug'; (DST / 'Review').mkdir(parents=True, exist_ok=True); (DST / 'Work').mkdir(exist_ok=True)
SRC = ART / 'Creatures/Pillbug/SK_Pillbug.blend'
RIG = json.loads((ART / 'Creatures/Pillbug/pillbug_rig_report.json').read_text())
random.seed(1338)
V = Vector

CX = [.39, .245, .10, -.045, -.19, -.335, -.47]
W7 = [.265, .315, .345, .35, .338, .305, .25]
KX = [-.78, -.58, -.47, -.335, -.19, -.045, .10, .245, .39, .60]
KW = [.085, .19, .25, .305, .338, .35, .345, .315, .265, .19]
KT = [.30, .375, .41, .45, .48, .495, .49, .47, .445, .415]
ZB = .32
def Wb(x): return float(np.interp(x, KX, KW))
def Tb(x): return float(np.interp(x, KX, KT))
def sstep(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def build_mesh(coll, mats):
    mb = MB()
    # ---------------- dorsal plates
    def plate(idx, cx, L, bone, sweep=.03, lobe=0.0, NV=36, US=(0, .1, .26, .45, .64, .8, .9, .955, 1.0), flare=.05, drop=.028, taper=0.0, thick=.012, chips=(), rnd=0.0, tilt=0.0):
        sv = [-1 + 2 * j / NV for j in range(NV + 1)]
        # denser sampling near the flared margins
        sv = [math.copysign(abs(s) ** .8, s) for s in sv]
        def P(u, s, inner):
            a = abs(s); x0 = cx + (.5 - u) * L
            x = x0 - sweep * a ** 3 * (.3 + .7 * u) + lobe * a ** 2.2 * (1 - u)
            w = Wb(x0); t = Tb(x0)
            d = -.011 + .023 * u - .008 * sstep(.94, 1, u) - (thick if inner else 0)
            d += .004 * math.sin(u * math.pi)                      # slight longitudinal crown
            th = s * math.pi / 2; cy = math.sin(th); cz = max(math.cos(th), 0) ** .8
            y = (w + d) * cy * (1 - taper * u ** 1.5); z = ZB + (t - ZB + d) * cz
            if a > .72:
                tt = (a - .72) / .28; y += math.copysign(flare * tt * tt, s); z -= drop * tt
            for (cs, cw, cd) in chips:                              # chipped rear margin
                if u > .8: x += cd * math.exp(-((s - cs) / cw) ** 2) * sstep(.8, 1, u)
            n = nz((x, y, z), 5.0, seed=idx * 3.1) * .005 + nz((x, y, z), 17.0, seed=idx) * .0015
            z += n * (cz + .3) + tilt * y; y += n * cy
            return V((x, y, z))
        nu = len(US); nv = NV + 1; vs = []; msk = []; loc = []
        for inner in (False, True):
            for u in US:
                for s in sv:
                    vs.append(P(u, s, inner)); a = abs(s)
                    msk.append((max(sstep(.84, 1, u), sstep(.86, 1, a) * .8), min(1.0, (1 - sstep(.28, .55, u)) * (0 if idx == 0 else 1) + .55 * sstep(.82, 1, a)) if not inner else .7, 0.0, rnd))
                    loc.append((u, (s + 1) / 2, idx / 12.0, 0.0))
        fs = []; size = nu * nv
        for k in range(2):
            for i in range(nu - 1):
                for j in range(NV):
                    a = k * size + i * nv + j; f = (a, a + nv, a + nv + 1, a + 1); fs.append(f if k == 0 else tuple(reversed(f)))
        for i in (0, nu - 1):
            for j in range(NV):
                a = i * nv + j; f = (a, a + 1, a + 1 + size, a + size); fs.append(f if i == 0 else tuple(reversed(f)))
        for j in (0, NV):
            for i in range(nu - 1):
                a = i * nv + j; f = (a, a + size, a + nv + size, a + nv); fs.append(f if j == 0 else tuple(reversed(f)))
        hid = len(mb.f); mb.add(vs, fs, bone, msk, loc)
        for q in range(hid + (nu - 1) * NV, hid + 2 * (nu - 1) * NV): mb.hid[q] = True
    chipset = {2: [(.55, .05, .022)], 4: [(-.3, .035, .014)], 5: [(.82, .06, .03)], 0: [(-.7, .04, .016)]}
    for i, cx in enumerate(CX):
        plate(i, cx, .205, 'tergite_%02d' % (i + 1), sweep=[.012, .018, .028, .04, .055, .07, .085][i], lobe=.10 if i == 0 else 0, chips=chipset.get(i, ()), rnd=random.random(), tilt=random.uniform(-.012, .012))
    for k in range(5):                                              # pleonites
        plate(7 + k, -.578 - k * .034, .058, 'tail', sweep=.03 + k * .006, NV=16, US=(0, .35, .8, 1.0), flare=.022, drop=.02, thick=.009, rnd=random.random())
    plate(12, -.745, .085, 'tail', sweep=0, NV=12, US=(0, .3, .6, .85, 1.0), flare=.0, drop=.01, taper=.92, thick=.008, rnd=random.random())   # telson
    for s in (-1, 1):                                               # uropods
        p0 = V((-.735, s * .085, .30)); p1 = V((-.80, s * .125, .275)); p2 = V((-.845, s * .14, .262))
        vs, fs, ts, an = tube([p0, p0.lerp(p1, .5) + V((0, 0, .004)), p1, p2], [.022, .026, .017, .003], 8, squash=(1.35, .55))
        mb.add(vs, fs, 'tail', [(t ** 3 * .7, .2, 0, .4) for t in ts], [(t, a, 1, 0) for t, a in zip(ts, an)])
    # ---------------- head
    HC = V((.572, 0, .333)); HR = (.128, .205, .088)
    def hfn(d, p):
        if d.z < 0: p.z *= .8
        if d.x > 0: p.x *= 1 - .18 * (1 - abs(d.y)) * max(0, -d.z + .3)     # receding lower face
        p += d * (.012 * math.exp(-((abs(d.y) - .62) / .2) ** 2) * max(d.x, 0))   # lateral lobes
        p += d * (.010 * math.exp(-(d.y / .16) ** 2) * max(d.x, 0) * max(0, d.z + .2))  # frontal shield
        p += d * (.011 * math.exp(-((d.z - .28) / .1) ** 2) * max(d.x, 0) ** .5)     # supra-antennal brow line
        p -= d * (.012 * math.exp(-((d.z + .05) / .14) ** 2) * max(d.x, 0))            # face recess under it
        p += d * (nz(p, 9, 4.0) * .004)
        return p
    vs, fs, dirs = ellipsoid(HC, HR, 28, 14, hfn)
    mb.add(vs, fs, 'head', [(.25 * max(0, d.x) ** 4, .35 * max(0, -d.x), 0, .77) for d in dirs], [(0.0, (d.y + 1) / 2, .95, 0) for d in dirs])
    for s in (-1, 1):                                               # compound eyes
        vs, fs, dirs = ellipsoid((.624, s * .148, .366), (.042, .028, .017), 12, 7)
        q = Quaternion((0, 0, 1), s * .5)
        vs = [V((.624, s * .148, .366)) + q @ (p - V((.624, s * .148, .366))) for p in vs]
        mb.add(vs, fs, 'head', (0, 0, 1, 0), (0, 0, 0, 0))
    # mouthparts: labrum, mandibles, maxillipeds
    vs, fs, dirs = ellipsoid((.672, 0, .262), (.022, .052, .02), 12, 7)
    mb.add(vs, fs, 'head', (.2, .5, .33, .3), (.05, .5, 0, 0))
    for s in (-1, 1):
        vs, fs, ts, an = tube([(.648, s * .085, .262), (.676, s * .06, .236), (.682, s * .018, .228)], [.026, .021, .005], 8, squash=(1, .7))
        mb.add(vs, fs, 'head', [(0, .5, .33, .2)] * len(vs), [(.3 + .3 * t, a, 0, .5 * sstep(.6, 1, t)) for t, a in zip(ts, an)])
        vs, fs, ts, an = tube([(.61, s * .05, .245), (.648, s * .04, .222), (.676, s * .03, .214)], [.022, .019, .004], 7, squash=(1.3, .5))
        mb.add(vs, fs, 'head', [(0, .6, .33, .6)] * len(vs), [(.55, a, 0, 0) for t, a in zip(ts, an)])
        vs, fs, ts, an = tube([(.655, s * .105, .252), (.692, s * .112, .236), (.71, s * .098, .228)], [.010, .008, .002], 6)   # palp
        mb.add(vs, fs, 'head', [(0, .3, .33, .6)] * len(vs), [(.7, a, 0, 0) for t, a in zip(ts, an)])
    # ---------------- limbs
    def article(p0, p1, r0, r1, bone, legt, n=7, bow=V((0, 0, 0)), bulge=1.12, squash=(1.28, .72), ref=(0, 0, 1), flag=0.0, rnd=0.0, tip=False):
        p0 = V(p0); p1 = V(p1)
        T = (0, .07, .3, .68, .92, 1.0) if not tip else (0, .1, .4, .75, 1.0)
        R = (r0 * .74, r0 * .95, (r0 + r1) / 2 * bulge * .96, r1 * 1.08, r1, r1 * .72) if not tip else (r0 * .7, r0, (r0 * .55 + r1), r1 * 1.6 + r0 * .12, r1)
        pts = [p0.lerp(p1, t) + bow * math.sin(math.pi * t) for t in T]
        vs, fs, ts, an = tube(pts, R, n, squash=squash, ref=ref)
        t0, t1 = legt
        mb.add(vs, fs, bone, [((abs(t - .5) * 2) ** 5, (abs(t - .5) * 2) ** 3 * .8, .33, rnd) for t in ts],
               [(t0 + (t1 - t0) * t, a, 0, flag if not tip else .5 * sstep(.15, .6, t)) for t, a in zip(ts, an)])
        return pts
    def seta(p, d, ln, bone, r=.0034):
        vs, fs, ts, an = tube([p, V(p) + V(d).normalized() * ln], [r, .0005], 3, cap=(False, True))
        mb.add(vs, fs, bone, (0, 0, .33, .5), (1, 0, 0, 1.0))
    chains = RIG['leg_chains']; bones = {b['name']: b for b in RIG['bones']}
    for ci, ch in enumerate(chains):
        up, lo = ch['upper'], ch['lower']; i = int(up[4:6]) - 1; s = 1 if up.endswith('_l') else -1
        hip = V([bones[up]['matrix_local'][r][3] for r in range(3)]); knee = V([bones[lo]['matrix_local'][r][3] for r in range(3)]); foot = V(ch['rest_foot'])
        out = V((0, s, 0)); rnd = random.random(); jit = lambda a: V((random.uniform(-a, a), random.uniform(-a, a), random.uniform(-a, a)))
        sc = 1 + random.uniform(-.06, .06)
        vs, fs, d = ellipsoid(hip + V((0, -s * .03, .012)), (.042, .05, .036), 10, 6)          # coxal membrane
        mb.add(vs, fs, up, (0, .9, .66, rnd), (0, 0, 0, 0))
        e1 = hip.lerp(knee, .6) + V((0, 0, .014)) + jit(.004)
        article(hip, e1, .023 * sc, .021 * sc, up, (.0, .2), bow=V((0, 0, .006)), rnd=rnd)          # basis
        article(e1, knee, .020 * sc, .022 * sc, up, (.2, .34), bow=V((0, 0, .004)), rnd=rnd)        # ischium
        fwd = V((1, 0, 0)) * (.012 if i < 3 else -.012)
        m1 = knee.lerp(foot, .21) + out * .018 + fwd + jit(.003); m2 = knee.lerp(foot, .46) + out * .026 + fwd * 1.5 + jit(.003); m3 = knee.lerp(foot, .87) + out * .008 + fwd + jit(.002)
        article(knee, m1, .022 * sc, .0215 * sc, lo, (.34, .5), rnd=rnd, ref=(1, 0, 0))           # merus
        article(m1, m2, .019 * sc, .0175 * sc, lo, (.5, .68), rnd=rnd, ref=(1, 0, 0))             # carpus
        article(m2, m3, .0155 * sc, .0105 * sc, lo, (.68, .9), rnd=rnd, ref=(1, 0, 0), bulge=1.0)  # propodus
        article(m3 + V((0, 0, .004)), foot + V((0, -s * .012, -.006)), .0095 * sc, .001, lo, (.9, 1.0), rnd=rnd, ref=(1, 0, 0), n=6, tip=True)   # dactylus claw
        for (a, b, r) in ((knee, m1, .02), (m1, m2, .017), (m2, m3, .012)):
            for q in (.3, .55, .8, .97):
                p = a.lerp(b, q) - out * r * .8 + V((random.uniform(-.006, .006), 0, 0))
                seta(p, -out * .8 + V((random.uniform(-.4, .4), 0, -.9)), random.uniform(.016, .034), lo)
            p = b + out * r * .7; seta(p, out + V((random.uniform(-.5, .5), 0, -1.2)), random.uniform(.012, .022), lo, .003)
    for an_ in ('l', 'r'):
        s = 1 if an_ == 'l' else -1
        b1 = bones['antenna_01_' + an_]; b2 = bones['antenna_02_' + an_]
        a = V([b1['matrix_local'][r][3] for r in range(3)]); b = V([b2['matrix_local'][r][3] for r in range(3)]); c = V((1.005, s * .355, .26))
        vs, fs, d = ellipsoid(a, (.022, .024, .02), 10, 6); mb.add(vs, fs, 'head', (0, .8, .66, .5), (0, 0, 0, 0))
        rnd = random.random(); up = V((0, 0, .012))
        q1 = a.lerp(b, .22); q2 = a.lerp(b, .5) + up
        article(a, q1, .017, .016, 'antenna_01_' + an_, (.1, .2), n=8, rnd=rnd, bulge=1.05)
        article(q1, q2, .014, .015, 'antenna_01_' + an_, (.2, .3), n=8, rnd=rnd)
        article(q2, b, .013, .0145, 'antenna_01_' + an_, (.3, .45), n=8, rnd=rnd)
        q3 = b.lerp(c, .42) + up * 1.4; q4 = b.lerp(c, .74) + up
        article(b, q3, .012, .0115, 'antenna_02_' + an_, (.3, .45), n=8, rnd=rnd, bow=V((0, 0, .006)))
        article(q3, q4, .0095, .0075, 'antenna_02_' + an_, (.45, .6), n=7, rnd=rnd)
        article(q4, c, .0068, .001, 'antenna_02_' + an_, (.6, .8), n=6, rnd=rnd, tip=True)
        for q in (.3, .6, .85):
            p = q4.lerp(c, q); seta(p, V((.3, s * .5, .6)), .012, 'antenna_02_' + an_, .002)
    # ---------------- ventral hull: sternites, membranes, pleopods
    XS = [(.50 - k * .0265) for k in range(44)]; NR = 18; vs = []; msk = []; loc = []; fs = []
    bounds = [cx - .0725 for cx in CX] + [CX[0] + .0725] + [-.58, -.615, -.65, -.685]
    for x in XS:
        d = min(abs(x - b) for b in bounds); g = math.exp(-(d / .012) ** 2)
        half = max(.02, Wb(x) - .06) * (1 - .5 * sstep(.22, .5, x) - .45 * sstep(-.55, -.72, x) if True else 1)
        depth = (.185 - .03 * g) * (1 - .62 * sstep(.18, .5, x)) * (1 - .5 * sstep(-.5, -.72, x)); zc = ZB - .02
        for j in range(NR):
            ph = math.tau * j / NR; sy = math.sin(ph); cz = math.cos(ph)
            y = half * sy * (1 - .05 * g); z = zc - (depth * abs(cz) ** .75 if cz > 0 else -.05 * abs(cz)) + nz((x, y, cz), 14, 2.0) * .004 * (cz > 0)
            mid = math.exp(-(sy / .25) ** 2) * (cz > 0)
            z += .012 * mid * (1 - g)                                # raised sternite keel plates stay shallower
            vs.append(V((x, y, z))); msk.append((mid * (1 - g) * .6, min(1, g + .25 * (cz <= 0)), .66, .5)); loc.append((.5, (sy + 1) / 2, 0, 0))
    for i in range(len(XS) - 1):
        for j in range(NR):
            a = i * NR + j; b = i * NR + (j + 1) % NR; fs.append((a, a + NR, b + NR, b))
    vs.append(V((XS[0] + .01, 0, ZB - .08))); msk.append((0, 1, .66, .5)); loc.append((.5, .5, 0, 0)); c0 = len(vs) - 1
    vs.append(V((XS[-1] - .01, 0, ZB - .06))); msk.append((0, 1, .66, .5)); loc.append((.5, .5, 0, 0)); c1 = len(vs) - 1
    o = (len(XS) - 1) * NR
    fs += [(c0, j, (j + 1) % NR) for j in range(NR)] + [(c1, o + (j + 1) % NR, o + j) for j in range(NR)]
    def vbone(p):
        if p.x < -.55: return {'tail': 1.0}
        if p.x > .47: return {'head': .5, 'pelvis': .5}
        return {'pelvis': 1.0}
    mb.add(vs, fs, [vbone(p) for p in vs], msk, loc)
    for k in range(5):                                              # pleopod plates under the pleon (wet gill covers)
        for s in (-1, 1):
            c = V((-.585 - k * .034, s * .055, .205 + k * .012))
            vs, fs, d = ellipsoid(c, (.03, .05, .012), 10, 5, lambda d_, p: p + V((0, 0, -.008 * d_.x)))
            mb.add(vs, fs, 'tail', (.3, .3, .66, .2 + .1 * k), (.5, .5, 0, 0))
    mb.v = [(x, y, max(z, .0006)) for x, y, z in mb.v]                # nothing below the ground plane (pivot rule: feet at z 0)
    ob = mb.build('SK_Pillbug_LOD0', coll, mats)
    me = ob.data; b = np.zeros(len(me.vertices) * 4, np.float32); me.color_attributes['msk'].data.foreach_get('color', b); b = b.reshape(-1, 4)[:, 2]
    for p in me.polygons:
        v = float(np.mean([b[i] for i in p.vertices])); p.material_index = 3 if v > .9 else (2 if v > .5 else (1 if v > .2 else 0))
    return ob


def chitin(mat):
    t = NT(mat); tc = t.node('ShaderNodeTexCoord'); P = tc.outputs['Object']; geo = t.node('ShaderNodeNewGeometry')
    ma = t.attr('msk'); mR, mG, mB = t.sep(ma.outputs['Color'])[:3]; mA = ma.outputs['Alpha']
    la = t.attr('loc'); lR, lG, lB = t.sep(la.outputs['Color'])[:3]; lA = la.outputs['Alpha']
    isLeg = t.math('COMPARE', mB, .33, .12); isMem = t.math('COMPARE', mB, .66, .12); isEye = t.math('GREATER_THAN', mB, .9)
    isClaw = t.math('MULTIPLY', t.math('COMPARE', lA, .5, .3), isLeg); isSeta = t.math('MULTIPLY', t.math('GREATER_THAN', lA, .85), isLeg)
    Pn = t.vmath('ADD', P, t.comb(t.math('MULTIPLY', mA, 7.0), t.math('MULTIPLY', mA, 3.0), t.math('MULTIPLY', mA, 5.0)))
    # --- dorsal cuticle colour
    big, _ = t.noise(Pn, 2.6, 2, .5)
    c = t.ramp(big, [(.3, (.016, .025, .036)), (.52, (.04, .058, .074)), (.76, (.085, .112, .126))])
    hue, _ = t.noise(Pn, 1.5, 2, .5, dist=.3)
    c = t.mix(t.math('MULTIPLY', t.smooth(hue, .48, .72), .55), c, (.04, .06, .043))
    mot, _ = t.noise(P, 42, 3, .7)
    c = t.mix(1.0, c, t.ramp(mot, [(.3, .62), (.5, 1.0), (.72, 1.32)]), 'MULTIPLY')
    spk, _ = t.voronoi(P, 120, 'F1')
    c = t.mix(t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(spk, .08, .22)), .45), c, (.02, .028, .036))   # dark pigment specks
    s2 = t.math('MULTIPLY', t.math('ABSOLUTE', t.math('SUBTRACT', lG, .5)), 2.0)
    blotn, _ = t.noise(Pn, 11, 3, .65, dist=.6)
    band = t.math('ADD', t.math('SUBTRACT', 1.0, t.smooth(t.math('ABSOLUTE', t.math('SUBTRACT', s2, .34)), .01, .075)), t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(t.math('ABSOLUTE', t.math('SUBTRACT', s2, .70)), .01, .06)), .8), clamp=True)
    uwin = t.math('MULTIPLY', t.smooth(lR, .16, .36), t.math('SUBTRACT', 1.0, t.smooth(lR, .7, .9)))
    blot = t.math('MULTIPLY', t.math('MULTIPLY', band, uwin), t.math('MULTIPLY', t.smooth(blotn, .50, .60), t.math('GREATER_THAN', mA, .22)))
    och, _ = t.noise(P, 60, 2, .5)
    c = t.mix(t.math('MULTIPLY', blot, .88), c, t.mix(och, (.16, .10, .035), (.33, .225, .08)))
    c = t.mix(t.math('MULTIPLY', t.math('POWER', mR, 1.6), .62), c, (.30, .27, .19))                       # translucent horn margin
    up = t.sepxyz(geo.outputs['Normal'])[2]
    bl, _ = t.noise(P, 5.5, 5, .72)
    bloom = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(bl, .5, .78), t.smooth(up, .15, .9)), .42)
    c = t.mix(bloom, c, (.20, .215, .20))
    wn, _ = t.noise(Pn, 16, 4, .7)
    worn = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(wn, .56, .68), t.smooth(up, .55, .95)), t.math('LESS_THAN', mB, .2))
    c = t.mix(t.math('MULTIPLY', worn, .55), c, (.15, .18, .185))
    scr = None
    for k, (rz, ry, sc_) in enumerate(((.3, .2, 130), (1.4, -.3, 170), (2.3, .5, 110), (.9, .1, 220))):
        f, _ = t.noise(t.mapping(P, (2.2, sc_, sc_), (0, ry, rz), (k * 3.3, 0, 0)), 1.0, 1, .5)
        line = t.math('SUBTRACT', 1.0, t.smooth(t.math('ABSOLUTE', t.math('SUBTRACT', f, .5)), .0, .016))
        gate, _ = t.noise(P, 3.0 + k, 2, .5); line = t.math('MULTIPLY', line, t.smooth(gate, .52, .62))
        scr = line if scr is None else t.math('MAXIMUM', scr, line)
    isDor = t.math('LESS_THAN', mB, .2)
    # review 12 Nov: more colour variation per plate and more scratches on the back plates
    pid = t.math('FRACT', t.math('MULTIPLY', t.math('SINE', t.math('MULTIPLY', mA, 91.7)), 43.37))          # per-tergite random 0..1
    pid2 = t.math('FRACT', t.math('MULTIPLY', t.math('SINE', t.math('MULTIPLY', mA, 57.3)), 17.91))
    c = t.mix(t.math('MULTIPLY', isDor, 1.0), c, t.mix(1.0, c, t.mix(pid, (.62, .70, .82), (1.12, 1.08, .98)), 'MULTIPLY'))
    pv, _ = t.noise(Pn, 4.4, 3, .6, dist=.5)
    c = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(pv, .47, .66), isDor), t.math('ADD', .25, t.math('MULTIPLY', pid2, .5))), c, (.085, .07, .045))      # brown-olive stained areas
    pv2, _ = t.noise(Pn, 7.0, 3, .6, dist=.3)
    c = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(pv2, .6, .74), isDor), t.math('ADD', .2, t.math('MULTIPLY', pid, .4))), c, (.11, .15, .19))           # paler slate-blue patches
    scr2 = None
    for k, (rz, ry, sc_, wd) in enumerate(((.15, .1, 150, .007), (1.9, .25, 190, .006), (2.7, 0, 80, .012))):
        f, _ = t.noise(t.mapping(P, (1.1 + .5 * k, sc_, sc_), (0, ry, rz), (k * 5.1 + 1.7, 0, 0)), 1.0, 1, .5)
        line = t.math('SUBTRACT', 1.0, t.smooth(t.math('ABSOLUTE', t.math('SUBTRACT', f, .5)), .0, wd))
        gate, _ = t.noise(Pn, 5.0 + 1.3 * k, 2, .5); line = t.math('MULTIPLY', line, t.smooth(gate, .6, .68))
        scr2 = line if scr2 is None else t.math('MAXIMUM', scr2, line)
    scr = t.math('MAXIMUM', scr, t.math('MULTIPLY', scr2, t.smooth(up, .0, .6)))
    scr = t.math('MULTIPLY', scr, isDor)
    c = t.mix(t.math('MULTIPLY', scr, .6), c, (.21, .24, .235))
    # --- legs and antennae
    lc = t.ramp(lR, [(0, (.028, .038, .048)), (.3, (.05, .068, .075)), (.7, (.10, .12, .12)), (1, (.23, .24, .20))])
    lc = t.mix(1.0, lc, t.ramp(mot, [(.3, .7), (.5, 1.0), (.72, 1.2)]), 'MULTIPLY')
    lc = t.mix(t.math('MULTIPLY', mR, .85), lc, (.30, .24, .15))
    lmo, _ = t.noise(P, 55, 3, .7)
    lc = t.mix(t.math('MULTIPLY', t.smooth(lmo, .44, .62), t.math('SUBTRACT', .95, t.math('MULTIPLY', lR, .4))), lc, (.025, .035, .045))
    lc = t.mix(isClaw, lc, (.03, .02, .012)); lc = t.mix(isSeta, lc, (.42, .30, .13))
    c = t.mix(isLeg, c, lc)
    # --- membranes / underside
    mn, _ = t.noise(P, 9, 4, .6)
    mc = t.mix(mn, (.19, .17, .14), (.14, .11, .09)); mc = t.mix(t.math('MULTIPLY', mR, .8), mc, (.26, .25, .22)); mc = t.mix(t.math('MULTIPLY', mG, .65), mc, (.14, .09, .055))
    c = t.mix(isMem, c, mc)
    efn, _ = t.voronoi(P, 150, 'F1')
    c = t.mix(isEye, c, t.mix(t.smooth(efn, .2, .45), (.035, .028, .02), (.008, .008, .011)))
    # --- dirt in overlaps and crevices
    ao = t.node('ShaderNodeAmbientOcclusion'); ao.samples = 8; ao.inputs['Distance'].default_value = .13
    cav = t.math('SUBTRACT', 1.0, ao.outputs['AO'])
    dn, _ = t.noise(P, 26, 4, .7); dl, _ = t.noise(P, 6, 3, .6)
    dirt = t.math('ADD', t.math('MULTIPLY', t.math('MULTIPLY', mG, isDor), .9), t.math('ADD', t.math('MULTIPLY', cav, 1.9), t.math('MULTIPLY', t.smooth(dl, .55, .8), .3)))
    dirt = t.math('MULTIPLY', t.smooth(t.math('MULTIPLY', dirt, t.math('ADD', dn, .45)), .32, .8), t.math('SUBTRACT', 1.0, isEye))
    lowz = t.math('SUBTRACT', 1.0, t.smooth(t.sepxyz(P)[2], .0, .2))                   # feet picked up soil
    dirt = t.math('MAXIMUM', dirt, t.math('MULTIPLY', lowz, t.smooth(dn, .28, .55)))
    c = t.mix(t.math('MULTIPLY', dirt, .85), c, t.mix(dn, (.085, .058, .034), (.16, .115, .07)))
    # --- roughness
    rn, _ = t.noise(P, 18, 3, .6)
    r = t.math('ADD', t.math('ADD', .2, t.math('MULTIPLY', rn, .3)), t.math('MULTIPLY', worn, .2)); r = t.math('ADD', r, t.math('MULTIPLY', bloom, .55)); r = t.math('ADD', r, t.math('MULTIPLY', scr, .25))
    r = t.mixf(isLeg, r, t.math('ADD', .34, t.math('MULTIPLY', rn, .2))); r = t.mixf(isClaw, r, .22)
    r = t.mixf(isMem, r, t.math('ADD', .14, t.math('MULTIPLY', mn, .22))); r = t.mixf(isEye, r, .07); r = t.mixf(dirt, r, .93)
    # --- height (metres)
    tub, _ = t.voronoi(P, 64, 'F1'); tubh = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(tub, .0, .42)), t.math('ADD', .35, t.math('MULTIPLY', lR, .9)))
    pit, _ = t.voronoi(P, 250, 'F1'); pith = t.smooth(pit, .0, .2)
    stn, _ = t.noise(P, 8, 2, .5); stri = t.math('MULTIPLY', t.math('SINE', t.math('ADD', t.math('MULTIPLY', lR, 70.0), t.math('MULTIPLY', stn, 40.0))), t.smooth(lR, .35, .9))
    meso, _ = t.noise(P, 30, 4, .6); micro, _ = t.noise(P, 480, 2, .5)
    h = t.math('MULTIPLY', t.math('MULTIPLY', tubh, isDor), .0008)
    h = t.math('ADD', h, t.math('MULTIPLY', pith, .0003)); h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', stri, isDor), .00016))
    h = t.math('ADD', h, t.math('MULTIPLY', meso, .0022)); h = t.math('ADD', h, t.math('MULTIPLY', micro, .00025)); h = t.math('SUBTRACT', h, t.math('MULTIPLY', scr, .0005))
    lrid = t.math('MULTIPLY', t.math('SINE', t.math('MULTIPLY', lG, 31.4)), .00022)
    h = t.math('ADD', h, t.math('MULTIPLY', lrid, isLeg))
    wr, _ = t.noise(t.mapping(P, (60, 6, 6)), 1.0, 3, .6); h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', wr, isMem), .003))
    fac, _ = t.voronoi(P, 150, 'F1'); h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(fac, 0, .5)), isEye), .002))
    h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', dirt, dn), .0012))
    n = t.bump(h, 1.0, 1.0)
    sss = t.math('ADD', t.math('MULTIPLY', isMem, .55), t.math('MULTIPLY', t.math('MULTIPLY', isLeg, lR), .25))
    b = t.finish(c, r, n, sss=sss, sss_radius=(.012, .006, .004))
    t.link(c, b.inputs['Subsurface Radius']) if False else None
    BAKE[mat.name] = t.bake
    return mat


def open_rig():
    bpy.ops.wm.open_mainfile(filepath=str(SRC))
    for o in list(bpy.data.objects):
        if o.type != 'ARMATURE': bpy.data.objects.remove(o)
    for c in list(bpy.data.collections):
        if c.name != 'SK_Pillbug': bpy.data.collections.remove(c)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    for i in list(bpy.data.images): bpy.data.images.remove(i)
    coll = bpy.data.collections['SK_Pillbug']; coll['dink_tex_px'] = 2048
    arm = bpy.data.objects['Armature']; arm.animation_data_create(); arm.animation_data.action = None; arm.data.pose_position = 'REST'
    return coll, arm


def shots(arm, tag, which, samples=48, scale=1.0):
    R = lambda w, h: (int(w * scale), int(h * scale)); fl = []
    D = DST / 'Review'
    if 'game' in which:
        set_action(arm, 'Pillbug_Idle', 20); f = D / (tag + '_game.png'); shoot(f, game_cam((.05, 0, .2), 6.0, -52, 45), (.05, 0, .2), 105, R(1200, 900), samples); fl.append(f)
    if 'close' in which:
        set_action(arm, 'Pillbug_Idle', 20); f = D / (tag + '_close.png'); shoot(f, (1.42, -.72, .50), (.56, 0, .30), 40, R(1200, 900), samples); fl.append(f)
    if 'back' in which:
        set_action(arm, 'Pillbug_Idle', 40); f = D / (tag + '_back.png'); shoot(f, (-1.75, .95, .30), (-.25, 0, .24), 50, R(1200, 900), samples); fl.append(f)
    if 'under' in which:
        g = bpy.data.objects['CR_Ground']; g.hide_render = True; set_action(arm, 'Pillbug_Idle', 40)
        f = D / (tag + '_under.png'); shoot(f, (.25, -.75, -1.35), (-.02, 0, .2), 45, R(1200, 900), samples, exposure=2.6); fl.append(f); g.hide_render = False
    if 'pose' in which:
        set_action(arm, 'Pillbug_Run', 5); f = D / (tag + '_run05.png'); shoot(f, game_cam((0, 0, .2), 3.2, -70, 28), (0, 0, .22), 60, R(1200, 900), samples); fl.append(f)
        set_action(arm, 'Pillbug_Walk', 9); f = D / (tag + '_walk09.png'); shoot(f, game_cam((0, 0, .2), 3.2, 115, 35), (0, 0, .22), 60, R(1200, 900), samples); fl.append(f)
    set_action(arm, None, 1); return fl


MATN = ['MI_Pillbug_Carapace', 'MI_Pillbug_Ochre', 'MI_Pillbug_Joints', 'MI_Pillbug_Eyes']
if STAGE in ('look', 'final'):
    coll, arm = open_rig()
    mats = [chitin(bpy.data.materials.new(n)) for n in MATN]
    ob = build_mesh(coll, mats)
    ob.parent = arm; md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = arm
    clean_mesh(ob); log('LOD0 triangles', tri_count(ob), 'dims', tuple(round(x, 3) for x in ob.dimensions))
    if STAGE == 'look':
        setup_review(samples=32)
        fl = shots(arm, 'look', A[1].split(',') if len(A) > 1 else ('game', 'close'), 32, .75)
    else:
        res = int(A[1]) if len(A) > 1 else 2048
        uv = uv_unwrap(ob)
        bpy.ops.wm.save_as_mainfile(filepath=str(DST / 'Work/Pillbug_Procedural.blend'))
        tex = bake_set(ob, DST / 'Textures', 'T_Pillbug_Atlas', res=res, extra=('sss',))
        for i, n in enumerate(MATN):
            old = ob.material_slots[i].material; old.name = n + '_Procedural'; old.use_fake_user = True
            ob.material_slots[i].material = game_material(n, tex, sss=True)
        from dinkasset import common, make_lods
        asset = common.Asset(coll); make_lods.make_lods(asset, [.5, .25], replace=True, force=True); asset.refresh()
        for m in asset.renders: clean_mesh(m); limit_weights(m); m.hide_render = m.name != ob.name
        (DST / 'pillbug_build.json').write_text(json.dumps({'uv': uv, 'texture_px': res, 'lods': [{'name': m.name, 'triangles': tri_count(m)} for m in asset.renders], 'dimensions_m': list(ob.dimensions)}, indent=1, default=str))
        for im in bpy.data.images:
            if im.filepath and str(DST / 'Textures') in bpy.path.abspath(im.filepath): im.filepath = '//Textures/' + Path(im.filepath).name
        bpy.ops.wm.save_as_mainfile(filepath=str(DST / 'SK_Pillbug.blend'), relative_remap=False)
        log('FINAL SAVED')
if STAGE == 'retex':
    # texture-only rebake on the saved, already unwrapped mesh: UVs, names, rig and pivot stay exactly as exported
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'Work/Pillbug_Procedural.blend')); ob = bpy.data.objects['SK_Pillbug_LOD0']
    for i, n in enumerate(MATN):
        old = ob.material_slots[i].material; old.name = n + '_old'; ob.material_slots[i].material = chitin(bpy.data.materials.new(n))
    bake_set(ob, DST / 'Textures', 'T_Pillbug_Atlas', res=2048, extra=('sss',)); log('RETEX DONE')
if STAGE == 'review':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Pillbug.blend')); arm = bpy.data.objects['Armature']
    setup_review(samples=int(A[3]) if len(A) > 3 else 64)
    shots(arm, A[1], A[2].split(','), int(A[3]) if len(A) > 3 else 64)
if STAGE == 'export':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Pillbug.blend')); arm = bpy.data.objects['Armature']
    export_skeletal('SK_Pillbug', arm, DST / 'Export', {'Idle': 'Pillbug_Idle', 'Walk': 'Pillbug_Walk', 'Run': 'Pillbug_Run'}, 'A_Pillbug', 40, DST / 'pillbug_validation.json')


def gore_mat(mat):
    """Blood pool, clots and spilled viscera for the death state (sprite sequences 141/143)."""
    t = NT(mat); tc = t.node('ShaderNodeTexCoord'); P = tc.outputs['Object']; ma = t.attr('msk'); mR, mG, mB = t.sep(ma.outputs['Color'])[:3]
    n1, _ = t.noise(P, 7, 4, .65, dist=.6); n2, _ = t.noise(P, 40, 3, .6); n3, _ = t.noise(P, 180, 2, .5)
    blood = t.mix(n1, (.20, .004, .004), (.075, .001, .002)); blood = t.mix(t.math('MULTIPLY', t.smooth(n2, .5, .72), .8), blood, (.03, .0, .001))        # fresh pool (the sprite's bright red), clots
    blood = t.mix(t.math('MULTIPLY', mG, .45), blood, (.13, .02, .012))                                                                                     # thin drying edge soaking into soil
    gut = t.mix(n2, (.50, .23, .18), (.62, .40, .30)); vd, _ = t.voronoi(P, 90, 'F1'); gut = t.mix(t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(vd, .1, .3)), .5), gut, (.30, .04, .05))
    gut = t.mix(t.math('MULTIPLY', t.smooth(n1, .32, .6), .85), gut, (.24, .005, .005))                                                                     # blood running over the viscera
    c = t.mix(mR, blood, gut)
    r = t.math('ADD', .03, t.math('MULTIPLY', n2, .08)); r = t.mixf(t.math('MULTIPLY', mG, t.smooth(n2, .3, .6)), r, .7); r = t.mixf(mR, r, t.math('ADD', .16, t.math('MULTIPLY', n2, .2)))
    h = t.math('ADD', t.math('MULTIPLY', t.smooth(n2, .55, .75), .0025), t.math('ADD', t.math('MULTIPLY', n1, .003), t.math('MULTIPLY', n3, .0003)))
    h = t.math('ADD', h, t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(vd, 0, .5), mR), .003))
    t.finish(c, r, t.bump(h, 1.0, 1.0), sss=t.math('MULTIPLY', mR, .4), sss_radius=(.01, .003, .002))
    BAKE[mat.name] = t.bake; return mat


POOL_DECAL_M = 4.4   # side of the square the blood decal covers, metres (creatures.json corpses[].decal.size_cm)


def pool_decal(gore, bc_path, out_path):
    """T_Pillbug_BloodPool_BC (RGBA): the gore seen straight from above, unlit. The game projects it onto the ground and the
    grass under the carcass (a flat pool is hidden by the grass carpet). Image right = +X (the head end), image up = +Y."""
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; use_hip_gpu(sc)
    tm = bpy.data.materials.new('PR_PoolDecal'); tm.use_nodes = True; nt = tm.node_tree; nt.nodes.clear()
    img = nt.nodes.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(str(bc_path), check_existing=True); em = nt.nodes.new('ShaderNodeEmission'); o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(img.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], o.inputs[0])
    keep = gore.material_slots[0].material; gore.material_slots[0].material = tm
    hidden = {x.name: x.hide_render for x in sc.objects}
    for x in sc.objects: x.hide_render = x is not gore
    cd = bpy.data.cameras.new('PR_PoolCam'); cd.type = 'ORTHO'; cd.ortho_scale = POOL_DECAL_M; cam = bpy.data.objects.new('PR_PoolCam', cd); sc.collection.objects.link(cam)
    cam.location = (0, 0, 5); cam.rotation_euler = (0, 0, 0); old = (sc.camera, sc.render.film_transparent, sc.view_settings.view_transform, sc.view_settings.look, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples, sc.render.image_settings.color_mode)
    sc.camera = cam; sc.render.film_transparent = True; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0
    sc.render.resolution_x = sc.render.resolution_y = 1024; sc.render.resolution_percentage = 100; sc.cycles.samples = 16; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = str(out_path); bpy.ops.render.render(write_still=True)
    sc.camera, sc.render.film_transparent, sc.view_settings.view_transform, sc.view_settings.look, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples, sc.render.image_settings.color_mode = old
    gore.material_slots[0].material = keep; bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd); bpy.data.materials.remove(tm)
    for x in sc.objects: x.hide_render = hidden.get(x.name, x.hide_render)
    # colour bled into the transparent margin, so a filtered edge is red, not black
    im = bpy.data.images.load(str(out_path), check_existing=False); a = np.empty(1024 * 1024 * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(1024, 1024, 4)
    cover = float((a[..., 3] > .5).mean()); mean = a[a[..., 3] > .5][:, :3].mean(0)
    a[..., :3] = np.where(a[..., 3:4] > .02, a[..., :3], mean); im.pixels.foreach_set(a.ravel()); im.save(); bpy.data.images.remove(im)
    log('pool decal %s: %.0f %% of the %.1f m square covered' % (out_path.name, 100 * cover, POOL_DECAL_M)); return out_path


def bloody_atlas(ob):
    """T_Pillbug_Corpse_BC/_ORM: the body atlas with blood composited in texture space from the posed corpse's world positions.
    Heavy round the burst middle, runs down the plates across the body, soaked where the shell lies in the pool, spatter everywhere."""
    import crlib
    res = 2048; sc = bpy.context.scene; sc.render.engine = 'CYCLES'; use_hip_gpu(sc); sc.cycles.samples = 1; sc.cycles.use_denoising = False
    tm = bpy.data.materials.new('PR_PosBake'); tm.use_nodes = True; nt = tm.node_tree; nt.nodes.clear()
    geo = nt.nodes.new('ShaderNodeNewGeometry'); em = nt.nodes.new('ShaderNodeEmission'); out = nt.nodes.new('ShaderNodeOutputMaterial'); img = nt.nodes.new('ShaderNodeTexImage')
    nt.links.new(em.outputs[0], out.inputs[0]); nt.nodes.active = img; img.select = True
    keep = [s.material for s in ob.material_slots]
    for s_ in ob.material_slots: s_.material = tm
    hidden = {o.name: o.hide_render for o in sc.objects}
    for o in sc.objects: o.hide_render = o is not ob
    activate(ob); maps = {}
    for key, sock in (('pos', 'Position'), ('nrm', 'True Normal')):
        im = crlib._img('pr_' + key, res, True, True); img.image = im
        for l in list(em.inputs[0].links): nt.links.remove(l)
        nt.links.new(geo.outputs[sock], em.inputs[0])
        bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True); maps[key] = crlib._px(im)[..., :3].copy(); bpy.data.images.remove(im)
    for s_, m in zip(ob.material_slots, keep): s_.material = m
    for o in sc.objects: o.hide_render = hidden.get(o.name, o.hide_render)
    bpy.data.materials.remove(tm)
    P_ = maps['pos'].astype(np.float64); N_ = maps['nrm']; x, y, z = P_[..., 0], P_[..., 1], P_[..., 2]
    def vnoise(q, seed):
        """Value noise on the unit lattice, trilinear with smooth weights; q (...,3)."""
        i = np.floor(q).astype(np.int64); f = q - i; f = f * f * (3 - 2 * f)
        def h(a, b, c):
            n = (a * 374761393 + b * 668265263 + c * 2147483647 + seed * 974711) & 0xFFFFFFFF; n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF; return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
        r_ = 0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                    r_ = r_ + w * h(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz)
        return r_
    def fbm(q, seed, octaves=4):
        a, tot, r_ = 1.0, 0.0, 0
        for o_ in range(octaves): r_ = r_ + a * vnoise(q * 2 ** o_, seed + o_); tot += a; a *= .5
        return r_ / tot
    def ss(a, b, v): t_ = np.clip((v - a) / (b - a), 0, 1); return t_ * t_ * (3 - 2 * t_)
    blotch = fbm(P_ * 4.0, 11); broad = fbm(P_ * 1.8, 23); fine = fbm(P_ * 26.0, 37, 3)
    burst = ss(.58, .12, np.sqrt((x - .02) ** 2 * .45 + y ** 2)) * ss(.36, .58, blotch)                         # thrown out of the opened middle
    warp = (fbm(P_ * 3.0, 51) - .5) * .9
    runs = ss(.53, .63, fbm(np.stack([x * 21 + warp, np.zeros_like(x) + .37, (y * .35 + z * .35) * 6], -1), 61, 3)) * ss(.30, .55, broad)   # runs across the body, down each plate
    soak = ss(.085, .02, z + (fine - .5) * .03)                                                                 # the rim that lies in the pool
    spat = ss(.70, .78, vnoise(P_ * 55.0, 71)) * ss(.35, .6, fbm(P_ * 5.0, 83))                                # spatter
    m = np.clip(np.maximum.reduce([burst * .95, runs * .9, soak, spat * .9]), 0, 1); m = np.clip(m * (.8 + .5 * fine), 0, 1)
    valid = np.abs(N_).sum(-1) > .01
    log('blood coverage of the carapace atlas: %.0f %% of baked texels (%.0f %% of the up-facing ones)' % (100 * m[valid].mean(), 100 * m[valid & (N_[..., 2] > .3)].mean()))
    def load(path, linear):
        im = bpy.data.images.load(str(path), check_existing=False); im.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'; a = crlib._px(im).copy()
        if im.size[0] != res: raise RuntimeError('atlas is not %d px: %s' % (res, path))
        bpy.data.images.remove(im); return a
    def save(arr, name, linear):
        im = bpy.data.images.new(name + '_o', res, res, alpha=False); im.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'
        im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); p_ = DST / 'Textures' / (name + '.png'); im.filepath_raw = str(p_); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im); return p_
    to_lin = lambda c: np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    to_srgb = lambda c: np.where(c <= .0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - .055)
    bc = load(DST / 'Textures/T_Pillbug_Atlas_BC.png', False); orm = load(DST / 'Textures/T_Pillbug_Atlas_ORM.png', True)
    lin = to_lin(bc[..., :3].astype(np.float64)); age = fbm(P_ * 9.0, 91)[..., None]
    red = (1 - age) * np.array((.21, .004, .004)) + age * np.array((.07, .001, .002))                           # fresh to clotting
    thin = np.clip(m * 2, 0, 1)[..., None]; thick = np.clip(m * 2 - 1, 0, 1)[..., None]
    lin = lin * (1 - thin * (1 - np.array((.55, .10, .09)))); lin = lin * (1 - thick) + red * thick             # a thin film stains, a thick coat covers
    bc[..., :3] = np.clip(to_srgb(lin), 0, 1); bc[..., 3] = 1
    orm[..., 1] = orm[..., 1] * (1 - m) + (.07 + .10 * fine) * m; orm[..., 3] = 1                              # wet
    return {'BC': save(bc, 'T_Pillbug_Corpse_BC', False), 'ORM': save(orm, 'T_Pillbug_Corpse_ORM', True),
            'N': DST / 'Textures/T_Pillbug_Atlas_N.png', 'SSS': DST / 'Textures/T_Pillbug_Atlas_SSS.png'}


if STAGE == 'corpse':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Pillbug.blend')); arm = bpy.data.objects['Armature']; sc = bpy.context.scene
    src = bpy.data.objects['SK_Pillbug_LOD0']; arm.data.pose_position = 'POSE'; set_action(arm, None, 1)
    R = random.Random(141); PB = arm.pose.bones
    def world(name, loc=(0, 0, 0), axis=(1, 0, 0), ang=0.0):
        """Apply a world-space rotation about the bone head, then a world translation."""
        b = arm.data.bones[name]; pb = PB[name]; bpy.context.view_layer.update()
        M = pb.matrix.copy(); piv = M.translation.copy()
        Rm = Matrix.Rotation(math.radians(ang), 4, V(axis)); T = Matrix.Translation(V(loc))
        pb.matrix = T @ Matrix.Translation(piv) @ Rm @ Matrix.Translation(-piv) @ M; bpy.context.view_layer.update()
    world('pelvis', (0, 0, -.115))
    world('head', (.05, .04, -.05), (0, 1, 0), 28); world('tail', (-.04, 0, -.06), (0, 1, 0), -14)
    plan = {1: ((.03, -.02, -.04), (1, 0, 0), 9), 2: ((.0, .05, -.05), (1, 0, 0), -14), 3: ((.06, .46, -.215), (1, .15, 0), 168), 4: ((-.03, -.50, -.20), (.9, 0, .3), 72),
            5: ((.0, .0, -.07), (1, 0, 0), 6), 6: ((-.07, .08, -.06), (0, 0, 1), 13), 7: ((-.13, -.07, -.08), (0, 1, .3), -20)}
    for i in range(1, 8): world('tergite_%02d' % i, *plan[i])
    for i in range(1, 8):
        for sd, s in (('l', 1), ('r', -1)):
            world('leg_%02d_upper_%s' % (i, sd), (0, 0, 0), (1, 0, 0), s * R.uniform(-30, 25)); world('leg_%02d_upper_%s' % (i, sd), (0, 0, 0), (0, 0, 1), R.uniform(-30, 30))
            world('leg_%02d_lower_%s' % (i, sd), (0, 0, 0), (1, 0, 0), s * R.uniform(35, 95))
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = src.evaluated_get(dg); me = bpy.data.meshes.new_from_object(ev)
    coll = bpy.data.collections.new('SM_Pillbug_Corpse'); sc.collection.children.link(coll); coll['dink_class'] = 'prop_large'; coll['dink_path'] = 'Pillbug'; coll['dink_tex_px'] = 2048
    ob = bpy.data.objects.new('SM_Pillbug_Corpse_LOD0', me); coll.objects.link(ob)
    co = co_np(me); co[:, 2] = np.maximum(co[:, 2], .002 + .01 * (np.sin(co[:, 0] * 37) * np.sin(co[:, 1] * 41) * .5 + .5)); set_co(me, co)       # nothing below the ground
    ob.vertex_groups.clear(); set_action(arm, None, 1)
    decimate_to(ob, 15000); clean_mesh(ob)
    # blood across the carapace, as sprites 141/143 show it: the corpse body gets its own colour and roughness maps
    bloody = bloody_atlas(ob)
    for slot in ob.material_slots:
        slot.material = game_material(slot.material.name.split('.')[0] + '_Bloody', bloody, sss=True)
    # gore: pool, clots, spilled viscera
    gm = gore_mat(bpy.data.materials.new('MI_Pillbug_Gore')); mbg = MB()
    NR, NA_ = 16, 192; vs = [V((0, 0, .014))]; msk = [(0, 0, 0, 0)]
    arms = [(R.uniform(0, math.tau), R.uniform(.10, .27), R.uniform(.09, .19)) for _ in range(11)]                    # rounded lobes: the sprite's ragged rim
    for i in range(1, NR + 1):
        for j in range(NA_):
            th = math.tau * j / NA_; rr = (.86 + .15 * math.sin(3 * th + .7) + .10 * math.sin(5 * th + 2.1) + .06 * math.sin(8 * th + 1.0) + .04 * math.sin(13 * th) + .02 * math.sin(29 * th + .4)) * (1.0 + .22 * math.cos(th) ** 2)
            rr += sum(a_ * math.exp(-(math.remainder(th - t0, math.tau) / w_) ** 2) for t0, a_, w_ in arms)
            a = i / NR; x = math.cos(th) * rr * a * 1.15; y = math.sin(th) * rr * a
            vs.append(V((x - .05, y, .008 * (1 - a ** 4) + .0008))); msk.append((0, a ** 5, 0, 0))
    fs = [(0, 1 + j, 1 + (j + 1) % NA_) for j in range(NA_)]
    for i in range(NR - 1):
        for j in range(NA_):
            a = 1 + i * NA_ + j; b = 1 + i * NA_ + (j + 1) % NA_; fs.append((a, a + NA_, b + NA_, b))
    mbg.add(vs, fs, 'x', msk)
    for k in range(84):                                                                                   # satellite drops and splashes
        th = R.uniform(0, math.tau); d = R.uniform(.95, 1.25) + R.random() ** 3 * .85; rr = R.uniform(.008, .04)
        vs, fs, dd = ellipsoid((math.cos(th) * d * 1.1, math.sin(th) * d, .001), (rr * R.uniform(1, 3.0), rr, .0025), 10, 4); q = Quaternion((0, 0, 1), th); vs = [q @ (p - V((math.cos(th) * d * 1.1, math.sin(th) * d, 0))) + V((math.cos(th) * d * 1.1, math.sin(th) * d, 0)) for p in vs]
        mbg.add(vs, fs, 'x', (0, .5, 0, 0))
    for k in range(18):                                                                                   # thrown streaks beyond the rim, each tapering into drops
        th = R.uniform(0, math.tau); d0 = R.uniform(.92, 1.12); ln = R.uniform(.22, .75); wd = R.uniform(.022, .055); bend = R.uniform(-.25, .25)
        for q in range(4):
            f_ = q / 3.0; d = d0 + ln * f_; a2 = th + bend * f_ * f_; c = (math.cos(a2) * d * 1.1, math.sin(a2) * d, .001)
            vs, fs, dd = ellipsoid(c, (ln * .22 * (1 - .45 * f_), wd * (1 - .6 * f_), .003), 12, 4); qr = Quaternion((0, 0, 1), a2); vs = [qr @ (p - V(c)) + V(c) for p in vs]
            mbg.add(vs, fs, 'x', (0, .35 + .3 * f_, 0, 0))
    for k in range(9):                                                                                    # viscera coils and lumps
        sy = R.choice((-1, 1)); c = V((R.uniform(-.14, .16), R.uniform(-.08, .08), .215)); pts = [c]
        for q in range(8): pts.append(pts[-1] + V((R.uniform(-.07, .07), sy * R.uniform(.02, .09), 0)))
        pts = [V((p.x, p.y, max(.025, .225 - 1.0 * max(0.0, abs(p.y) - .16)) + R.uniform(-.01, .01))) for p in pts]
        vs, fs, ts, an = tube(pts, [R.uniform(.022, .036) * (1 + .25 * math.sin(i * 2.1)) for i in range(len(pts))], 8); mbg.add(vs, fs, 'x', (1, 0, 0, 0))
    for k in range(7):
        c = (R.uniform(-.2, .2), R.uniform(-.2, .2), R.uniform(.17, .225)); vs, fs, dd = ellipsoid(c, (R.uniform(.05, .11), R.uniform(.04, .09), R.uniform(.025, .05)), 12, 7, lambda d_, p: p * (1 + .2 * nz(p, 22, k)))
        mbg.add(vs, fs, 'x', (R.choice((0, 1, 1)), 0, 0, 0))
    gore = mbg.build('gore', coll, [gm]); gore.vertex_groups.clear()
    uv_unwrap(gore, angle=66, hidden_scale=1.0)
    gt = bake_set(gore, DST / 'Textures', 'T_Pillbug_Gore', res=1024, extra=('sss',))
    gore.material_slots[0].material = game_material('MI_Pillbug_Gore', gt, sss=True); gm.name = 'MI_Pillbug_Gore_Procedural'
    pool_decal(gore, gt['BC'], DST / 'Textures/T_Pillbug_BloodPool_BC.png')
    ob = join([ob, gore], 'SM_Pillbug_Corpse_LOD0')
    for a in list(ob.data.color_attributes): ob.data.color_attributes.remove(a)
    from dinkasset import common, make_lods
    asset = common.Asset(coll); make_lods.make_lods(asset, [.5, .25], replace=True, force=True); asset.refresh()
    for m in asset.renders: clean_mesh(m); m.hide_render = m.name != ob.name
    for o in bpy.data.objects:
        if o.name.startswith('SK_Pillbug'): o.hide_render = True
    info = {'lods': [{'name': m.name, 'triangles': tri_count(m)} for m in asset.renders], 'dimensions_m': list(ob.dimensions), 'pool_decal_m': POOL_DECAL_M}
    (DST / 'pillbug_corpse_build.json').write_text(json.dumps(info, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(DST / 'SM_Pillbug_Corpse.blend'), relative_remap=False)
    setup_review(samples=64)
    shoot(DST / 'Review/corpse_game.png', game_cam((0, 0, .1), 6.0, -52, 45), (0, 0, .1), 68, (1200, 900), 64)
    shoot(DST / 'Review/corpse_close.png', (1.5, -1.0, .7), (.0, 0, .1), 40, (1200, 900), 64)
    # export (static, cm)
    (DST / 'Export').mkdir(exist_ok=True)
    from dinkasset import export_ue
    for o in asset.renders:
        for v in o.data.vertices: v.co *= 100
    sc.unit_settings.scale_length = .01
    for material in bpy.data.materials:
        if material.node_tree: material.node_tree.nodes.clear()
    for o in asset.renders:
        proxy = type('ExportAsset', (), {'renders': [o], 'collision': [], 'armatures': [], 'sockets': []})()
        with export_ue.unhidden([o]): export_ue.export_fbx(proxy, str(DST / 'Export' / (o.name + '.fbx')), 'all', 'Armature')
    log('corpse exported', info)
