"""Mother, stage 2+3: red linen dress (bodice with short puffed sleeves, gathered floor-length skirt), black belt with
brass buckle, worn leather shoes. Game meshes + *_HI bake sources, saved to Mother/Work/mother_garments_b.blend."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *; import gearlib as G, folds
N = 'Mother'
bpy.ops.wm.open_mainfile(filepath=str(OUT / N / 'Work/mother_bodyvol.blend'))
D = bpy.data.objects; arm = D['Armature']; bv = D['BodyVol']
B = arm.data.bones
folds.setup({n: list(B[n].head_local) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')})
G.init(arm, bvh_of([bv, D['Skin']]))
S, E_, Wr, MIR = G.S, G.E_, G.Wr, G.MIR
SL = .168            # sleeve length along the upper arm
ZW, ZH = 1.050, .042  # waist seam, hem
made = []
def _mir(p):
    m = p.copy(); m[:, 0] = np.abs(m[:, 0]); return m

# ------------------------------------------------------------------ BODICE
def bodice_fold(p, fine):
    m = _mir(p); s, th, dist = poly_params(m, [S, E_, Wr], (0, 0, -1)); h = folds.arm_h(p); armw = sstep(-.004, .03, h)
    z = p[:, 2]; phi = np.arctan2(p[:, 0], -(p[:, 1] + .02)); sg = np.sign(p[:, 0])
    u = np.clip(s / SL, 0, 1)
    n1 = vnoise(p, 9, 201); n2 = vnoise(p, 17, 202)
    top = .5 - .5 * np.cos(th)                                            # 1 on top of the arm
    puff = (.012 + .026 * np.sin(np.pi * u ** .8) ** .9 * (.55 + .45 * top)) * armw * sstep(-.01, .035, s)
    cuff = sstep(.80, .93, u) * armw                                      # gathered into a narrow band
    puff = puff * (1 - cuff) + .0025 * cuff
    gath = (np.exp(-((u - .1) / .16) ** 2) + np.exp(-((u - .80) / .14) ** 2))
    g1 = .0045 * ridge(th * 13 + 5 * n1 + 2.5 * u, 1.5) * gath * armw * (1 - cuff * .7)
    sag = .008 * (1 - top) * np.sin(np.pi * u) * armw                    # the puff hangs a little
    torso = 1 - armw
    ease = .0045 + .008 * sstep(1.30, 1.10, z) + .004 * np.exp(-((z - 1.16) / .07) ** 2) * (p[:, 1] < 0)
    waist = np.exp(-((z - 1.085) / .04) ** 2)
    w1 = .0065 * ridge(phi * 17 + 5 * n1 + 14 * z, 1.5) * waist * (.35 + .65 * sstep(.3, .7, n2))      # gathered into the waistband
    bust = .0040 * ridge(2 * np.pi * (z + .25 * np.abs(p[:, 0])) / .05 + 6 * vnoise(p, 7, 203), 2.2) * np.exp(-((z - 1.22) / .06) ** 2) * (p[:, 1] < 0)
    back = .0035 * ridge(2 * np.pi * z / .045 + 7 * n1, 2.0) * np.exp(-((z - 1.16) / .06) ** 2) * (p[:, 1] > 0)
    d = puff + g1 + sag + torso * (ease + w1 + bust + back) + .002 * (fbm(p, 9, 3, 204) - .5)
    d -= .003 * np.exp(-((z - 1.052) / .016) ** 2) * torso                                            # cinched by the belt
    # centre-front opening laced shut: a shallow groove, the two turned edges, eyelets and a criss-cross cord
    lz = sstep(1.085, 1.11, z) * sstep(1.40, 1.37, z) * (p[:, 1] < 0) * torso; x_ = p[:, 0]; pit = .026
    fz = (z / pit) % 1.0; zig = (2 * np.abs(fz - .5) * 2 - 1) * .0105
    cord = np.maximum(np.exp(-((x_ - zig) / .0016) ** 2), np.exp(-((x_ + zig) / .0016) ** 2)) * (np.abs(x_) < .0125)
    eye = np.exp(-(((np.abs(x_) - .0115) / .0022) ** 2 + ((np.minimum(fz, 1 - fz) * pit) / .0022) ** 2))
    d += lz * (-.0028 * np.exp(-(x_ / .0035) ** 2) + .0016 * np.exp(-((np.abs(x_) - .013) / .004) ** 2) + .0026 * cord - .0012 * eye)
    # gathers running up from the waist seam into the bust (the bodice is cut full and drawn in)
    d += .0030 * ridge(phi * 23 + 6 * n2, 1.7) * np.exp(-((z - 1.12) / .05) ** 2) * torso * (p[:, 1] < 0) * (np.abs(x_) > .02)
    if fine:
        d += .0012 * ridge(th * 31 + 9 * n2 + 5 * u, 1.6) * gath * armw * (1 - cuff)
        d += .0020 * ridge(2 * np.pi * (z * .8 + p[:, 0] * sg * .5) / .034 + 12 * fbm(p, 13, 2, 205), 1.8) * sstep(.42, .7, vnoise(p, 11, 206)) * torso
        d += .0010 * (fbm(p, 42, 3, 207) - .5)
        d += .0018 * ridge(phi * 43 + 9 * n2 + 20 * z, 1.5) * waist * torso
    return d
bd = dup(bv, 'Bodice_Base')
implicit_cut(bd, lambda P: folds.arm_h(P) - .006)
implicit_cut(bd, lambda P: (ZW - .030) - P[:, 2])
def neck_q(P):   # open round neckline: an ellipsoid scoop (deeper in front) joined with the neck column
    return np.sqrt((P[:, 0] / .104) ** 2 + ((P[:, 1] + .030) / .112) ** 2 + ((P[:, 2] - 1.525) / .118) ** 2)
def neck_f(P):
    r = np.sqrt(P[:, 0] ** 2 + (P[:, 1] - .008) ** 2)
    return np.maximum(1 - neck_q(P), np.minimum(.080 - r, P[:, 2] - 1.44))
implicit_cut(bd, neck_f)
def bod_class(C, Nn):
    s = folds.arm_h(C)
    return np.where(Nn[:, 2] > .55, np.where(C[:, 0] > 0, 7, 8), np.where(C[:, 1] < 0, 3, 4))
bod_charts = {7: ('planar', (0, 0, 1.3), (1, 0, 0), (0, 1, 0)), 8: ('planar', (0, 0, 1.3), (1, 0, 0), (0, 1, 0)), 3: ('planar', (0, 0, 1.3), (1, 0, 0), (0, -.5, .87)), 4: ('planar', (0, 0, 1.3), (-1, 0, 0), (0, .5, .87))}
_old_charts = {1: ('cyl', [S, E_, Wr], (0, 0, 1), .075), 2: ('cyl', [S * MIR, E_ * MIR, Wr * MIR], (0, 0, 1), .075),
              3: ('planar', (0, 0, 1.3), (1, 0, 0), (0, -.5, .87)), 4: ('planar', (0, 0, 1.3), (-1, 0, 0), (0, .5, .87))}
def bod_seams(p):
    BIG = 1.0; z = p[:, 2]; x = np.abs(p[:, 0]); y = p[:, 1]; h = folds.arm_h(p)
    s, th, _ = poly_params(_mir(p), [S, E_, Wr], (0, 0, -1))
    side = np.where((z < 1.34) & (x > .08) & (h < 0), np.abs(y + .012), BIG)
    shoulder = np.where((z > 1.43) & (x > .075) & (h < 0), np.abs(y - .010), BIG)
    under = np.where(h > .02, np.abs(th) * .05, BIG)
    cfront = np.where((y < -.04) & (h < -.02), x, BIG)                    # centre-front opening, laced shut
    cuffl = np.where(h > 0, np.abs(s - (SL - .020)), BIG)
    seam = np.minimum.reduce([side, shoulder, cfront])
    nk = np.abs((neck_q(p) - 1) * .105 - .006) + (z < 1.36) * BIG                 # top-stitched neckline binding
    st = np.minimum.reduce([np.abs(seam - .0045), nk, np.abs(h + .010), np.abs(cfront - .011)])
    return seam, st
bod, bod_hi = G.finish(bd, bodice_fold, 3000, bod_class, bod_charts, 'linen_red', 'Bodice', lip=(.0028, .011), lipsel=lambda c: c.z > 1.38 and (c.x ** 2 + c.y ** 2) ** .5 < .16, seams=bod_seams, hi_levels=1)
made += [bod, bod_hi]

# ------------------------------------------------------------------ PUFFED SLEEVES (lofted; they pass through the armhole seam)
arm_bvh = bvh_of([bv])
def sleeve(sg, nu, nr, name):
    M = np.array([sg, 1, 1.0]); Sx = S * M; du = G.dU * M
    xr = np.array([0, 0, -1.0]); xr = xr - du * (xr @ du); xr /= np.linalg.norm(xr); yr = np.cross(du, xr)
    NA, NS_ = 48, 40; tha = np.linspace(0, 2 * np.pi, NA, endpoint=False); sa = np.linspace(-.04, SL, NS_)
    RA = np.zeros((NS_, NA))
    for i, s_ in enumerate(sa):
        c = Sx + du * s_
        for j, t_ in enumerate(tha):
            d = xr * math.cos(t_) + yr * math.sin(t_); hit = arm_bvh.ray_cast(Vector(c + d * .10), Vector(-d), .10)
            RA[i, j] = min(float((np.array(hit[0]) - c) @ d) if hit[0] is not None else .05, .058)
    for _ in range(3): RA = (np.roll(RA, 1, 1) + 2 * RA + np.roll(RA, -1, 1)) / 4; RA[1:-1] = (RA[:-2] + 2 * RA[1:-1] + RA[2:]) / 4
    th = np.linspace(0, 2 * np.pi, nu, endpoint=False); ss = np.linspace(-.04, SL, nr); P = np.zeros((nr, nu, 3)); SS = np.zeros((nr, nu)); TH = np.zeros((nr, nu))
    for i, s_ in enumerate(ss):
        fi = np.interp(s_, sa, np.arange(NS_)); i0 = int(min(fi, NS_ - 2)); a_ = fi - i0
        row = RA[i0] * (1 - a_) + RA[i0 + 1] * a_; ra = np.interp(th, np.concatenate([tha, [2 * np.pi]]), np.concatenate([row, row[:1]]))
        u = min(max(s_ / SL, 0), 1); top = .5 - .5 * np.cos(th)
        puff = .009 + .024 * math.sin(math.pi * u ** .85) ** .9 * (.62 + .38 * top)
        cuff = float(sstep(.84, .93, u)); r = ra + puff * (1 - cuff) + .0032 * cuff
        r = r * (.72 + .28 * float(sstep(-.04, .0, s_)))
        c = Sx + du * s_ - np.array([0, 0, .007]) * math.sin(math.pi * u) * (1 - cuff)
        P[i] = c + (np.outer(np.cos(th), xr) + np.outer(np.sin(th), yr)) * r[:, None]; SS[i] = s_; TH[i] = th
    flat = P.reshape(-1, 3); s_ = SS.ravel(); t_ = TH.ravel(); u = np.clip(s_ / SL, 0, 1); cuff = sstep(.84, .93, u)
    q = flat * M + (0 if sg > 0 else 2.7); n1 = vnoise(q, 9, 231); n2 = vnoise(q, 17, 232)
    gath = np.exp(-((u - .10) / .2) ** 2) + np.exp(-((u - .78) / .13) ** 2)
    d = .0050 * ridge(t_ * 12 + 4 * n1 + 2 * u, 1.5) * gath * (1 - cuff * .8) + .003 * (fbm(q, 8, 3, 233) - .5) * (1 - cuff)
    d += .0016 * ridge(t_ * 29 + 8 * n2 + 5 * u, 1.6) * gath * (1 - cuff) + .0009 * (fbm(q, 42, 3, 234) - .5)
    d += .0012 * np.exp(-((s_ - (SL - .003)) / .003) ** 2)                 # rolled cuff edge
    cen = np.repeat(np.array([Sx + du * v for v in ss]), nu, axis=0); rad = flat - cen; rad -= np.outer(rad @ du, du)
    flat = flat + rad / np.linalg.norm(rad, axis=1)[:, None] * d[:, None]
    o = G.grid_obj(name, flat.reshape(nr, nu, 3)); rr_ = np.linalg.norm(rad, axis=1)
    return o, s_, t_, rr_
for sg, sd in ((1, 'l'), (-1, 'r')):
    lo, _, _, _ = sleeve(sg, 26, 11, 'Sleeve_' + sd); hi, s_, t_, r_ = sleeve(sg, 208, 97, 'Sleeve_%s_HI' % sd)
    under = np.minimum(t_, 2 * np.pi - t_) * r_
    G.put(hi, 'd_seam', np.minimum(under, np.abs(s_ - (SL - .020)))); G.put(hi, 'd_stitch', np.minimum.reduce([np.abs(under - .0045), np.abs(s_ - (SL - .006)), np.abs(s_ - (SL - .016))]))
    for o in (lo, hi): G.set_chart(o, 1 if sg > 0 else 2); G.tag(o, 'linen_red', 'outfit'); smooth_shade(o)
    add_lips(lo, .0022, .010, select=lambda c: abs(c.x) > .22)
    made += [lo, hi]

# ------------------------------------------------------------------ SKIRT
bvh_body = bvh_of(bv)
NPL = 13
def skirt(nu, nr, fine, name):
    PH0 = 2.55                                                        # loft seam at the back-left, away from both views
    phi = PH0 + np.linspace(0, 2 * np.pi, nu, endpoint=False); ts = np.linspace(0, 1, nr)
    cdir = np.stack([np.sin(phi), -np.cos(phi), np.zeros(nu)], 1)
    NA = 144; pa = np.linspace(0, 2 * np.pi, NA, endpoint=False); ca = np.stack([np.sin(pa), -np.cos(pa), np.zeros(NA)], 1)
    def table(z, default):
        rb = np.array([G.ring_radius(bvh_body, np.array([0, -.02, z]), d, far=.30, default=default) for d in ca])
        for _ in range(8): rb = (np.roll(rb, 1) + 2 * rb + np.roll(rb, -1)) / 4
        return np.interp(phi % (2 * np.pi), np.concatenate([pa, [2 * np.pi]]), np.concatenate([rb, rb[:1]]))
    rw = table(ZW, .15) + .004
    front = .5 + .5 * np.cos(phi)             # 1 at the front
    ex = 2.3; rx = .335; ry = .300 + .085 * (1 - front)        # the back trails a little
    rh = 1.0 / (np.abs(np.sin(phi) / rx) ** ex + np.abs(np.cos(phi) / ry) ** ex) ** (1 / ex)
    P = np.zeros((nr, nu, 3)); T_ = np.zeros((nr, nu)); PH = np.zeros((nr, nu))
    ZT = np.linspace(ZW, .70, 12); TB = np.array([table(z, 0) for z in ZT])
    for i, t in enumerate(ts):
        z = ZW + (ZH - ZW) * t
        prof = .58 * (1 - math.exp(-4.2 * t)) / (1 - math.exp(-4.2)) + .42 * t
        r = rw + (rh - rw) * prof
        if z > .70:    # stay off the hips
            fi = (ZW - z) / (ZW - .70) * 11; i0 = int(min(fi, 10)); rb = TB[i0] * (1 - (fi - i0)) + TB[i0 + 1] * (fi - i0)
            r = np.maximum(r, rb + .010 + .02 * min(1, t * 6))
        P[i] = np.array([0, -.02, z]) + cdir * r[:, None]; T_[i] = t; PH[i] = phi
    flat = P.reshape(-1, 3); t = T_.ravel(); ph = PH.ravel()
    q = np.stack([np.sin(ph) * .3, -np.cos(ph) * .3, flat[:, 2]], 1)          # noise domain that does not stretch with the flare
    n1 = vnoise(q, 5, 211); n2 = vnoise(q, 11, 212); a1 = sstep(.25, .75, vnoise(q, 3.5, 213))
    amp = (.006 + .050 * t ** .65) * (.5 + .85 * a1)
    wob = 1.1 * (n1 - .5) * 2 * (.3 + .7 * t)
    d = amp * ridge(NPL * ph + wob, 2.6) + .6 * amp * ridge(21 * ph + 1.7 - wob * 1.3, 3.0) * sstep(.3, .7, vnoise(q, 2.7, 220))
    d += .010 * t * (fbm(q, 2.5, 2, 214) - .5) * 2                             # the cone is not round: swing and drape
    d += .0035 * ridge(34 * ph + 4 * n2, 1.6) * np.exp(-t / .10)              # gathers under the waistband
    if fine:
        d += (.0012 + .0022 * t) * ridge(47 * ph + 5 * n2 + 2 * t, 2.0) * sstep(.4, .7, vnoise(q, 8, 215))
        d += .0010 * ridge(2 * np.pi * flat[:, 2] / .06 + 9 * fbm(q, 9, 2, 216) + 2 * np.sin(NPL * ph), 3.0) * sstep(.55, .8, vnoise(q, 6, 217)) * sstep(.25, .5, t)   # creases
        d += .0010 * (fbm(q, 40, 3, 218) - .5)
        d += .0010 * ridge(67 * ph + 9 * n2, 1.5) * np.exp(-t / .07)
    rad = flat - np.array([0, -.02, 0]); rad[:, 2] = 0; rl = np.linalg.norm(rad, axis=1); flat = flat + rad / rl[:, None] * d[:, None]
    flat[:, 2] += (-.010 * np.sin(NPL * ph + wob) + .010 * (vnoise(q, 4, 219) - .5) * 2) * t ** 3   # uneven hem
    flat[:, 2] = np.maximum(flat[:, 2], .018)
    o = G.grid_obj(name, flat.reshape(nr, nu, 3))
    return o, flat, t, ph
sk_lo, _, t_lo, _ = skirt(104, 17, True, 'Skirt')
sk_hi, fl, t_hi, ph_hi = skirt(624, 281, True, 'Skirt_HI')
rr = np.sqrt(fl[:, 0] ** 2 + (fl[:, 1] + .02) ** 2)
gore = np.abs(((ph_hi + np.pi / 6) % (np.pi / 3)) - np.pi / 6) * rr          # six gores
G.put(sk_hi, 'd_seam', np.where(t_hi > .02, gore, 1.0)); G.put(sk_hi, 'd_stitch', np.minimum.reduce([np.abs(gore - .0045), np.abs(fl[:, 2] - (ZH + .028)) + (t_hi < .9) * 1.0, np.abs(t_hi - .012) * 1.0]))
for o in (sk_lo, sk_hi): G.set_chart(o, 5); G.tag(o, 'linen_red', 'outfit'); smooth_shade(o)
add_lips(sk_lo, .0022, .020, select=lambda c: c.z < .5)
G.skirt_weights(sk_lo, ZW, ZH, leg_max=.96, calf_max=.45, calf_back=.80)
made += [sk_lo, sk_hi]

# ------------------------------------------------------------------ BELT + BUCKLE
dress_bvh = bvh_of([bod, sk_lo])
(belt, belt_hi), bp, bt = G.make_belt('Belt', dress_bvh, ZW + .002, 'leather_black', h=.0185, t=.0040, drop=.012, n_lo=48)
bk, bk_hi = G.make_buckle('Buckle', bp, 'brass', W=.020, H=.020, t=bt)
belt['rigidw'] = 'pelvis:.55,spine_01:.45'; bk['rigidw'] = 'pelvis:.55,spine_01:.45'
made += [belt, belt_hi, bk, bk_hi]

# ------------------------------------------------------------------ SHOES (ankle boots under the hem)
for side in 'lr':
    for hi in (False, True):
        b = G.boot(side, 96 if hi else 14, 160 if hi else 18, hi, 'Boot_%s%s' % (side, '_HI' if hi else ''))
        s = G.sole(side, 80 if hi else 12, 'Sole_%s%s' % (side, '_HI' if hi else ''))
        G.set_chart(b, 31 if side == 'l' else 32); G.set_chart(s, 33 if side == 'l' else 34)
        G.tag(b, 'leather_shoe', 'gear'); G.tag(s, 'leather_sole', 'gear')
        if not hi: add_lips(b, .003, .012, select=lambda c: c.z > .3)
        made += [b, s]
for o in made:
    if not o.name.endswith('_HI'): G.fix_lip_charts(o)
    smooth_shade(o)
    if 'UVMetric' not in o.data.uv_layers: log('NO UV', o.name)
log('game tris', {o.name: tri_count(o) for o in made if not o.name.endswith('_HI')}, 'total', sum(tri_count(o) for o in made if not o.name.endswith('_HI')))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / N / 'Work/mother_garments_b.blend'))
if 'norender' in args(): sys.exit(0)
cols = {'linen_red': (.28, .03, .025), 'leather_black': (.03, .025, .02), 'brass': (.7, .5, .2), 'leather_shoe': (.08, .05, .03), 'leather_sole': (.04, .03, .02)}
hi_view = 'hi' in args()
for o in D:
    if o.type != 'MESH': continue
    o.hide_render = not ((o.name == 'Skin') or ('fabric' in o and (o.name.endswith('_HI') == hi_view or (hi_view and D.get(o.name + '_HI') is None))))
    if 'fabric' in o:
        mt = bpy.data.materials.new('pv'); mt.use_nodes = True; bs = mt.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value = (*cols[o['fabric']], 1); bs.inputs['Roughness'].default_value = .75
        o.data.materials.clear(); o.data.materials.append(mt)
setup_render(samples=24, res=(1500, 1000)); bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = .08
tg = 'g_hi' if hi_view else 'g_lo'
shoot(OUT / N / ('Review/%s_front.png' % tg), (0.9, -3.6, 1.3), (0, 0, .9), lens=55)
shoot(OUT / N / ('Review/%s_back.png' % tg), (-1.2, 3.4, 1.4), (0, 0, .9), lens=55)
