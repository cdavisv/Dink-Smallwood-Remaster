"""Round 2: unique bakes for the props seen most and closest. Each prop has ONE generator that is run twice (hi=True: the
high-detail source with procedural materials; hi=False: the game mesh), the source is baked onto the game mesh
(T_<Asset>_BC / _N / _ORM / _E beside the FBX) and the result is saved to Props/_build/bake/<Asset>.blend + .json.
props_merge.py then swaps the baked meshes into Props/_build/Props.blend and re-exports the FBX.

    DINK_PP=<PhotorealPass> blender -b -t 4 --python Props/tools/props_bake.py -- <asset> [...] [--nobake] [--review rN] [--views game,close,int]"""
import os, sys
_H = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(_H, 'bakelib.py')).read())
PROPS = os.path.join(PP, 'Props'); BK = os.path.join(PROPS, '_build', 'bake'); os.makedirs(BK, exist_ok=True)
ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def opt(name, default=None):
    return ARGV[ARGV.index(name) + 1] if name in ARGV else default


# ================================================================ high-detail materials
def m_iron(name, soot=None, rust=0.7, bright=0.3, hammer=1.0, heat=None, burnt=None):
    """forged wrought iron: blue-black fire scale (metal), hammer facets, rust (dielectric) in pits and crevices, worn bright
    arrises (metal); soot(s) -> 0..1 mask of fire soot, heat(s) -> faint temper tint, burnt(s) -> scaled red oxide from the fire"""
    s = NT(name)
    ham = s.voro(46.0, 'SMOOTH_F1', smooth=0.7); ham2 = s.voro(19.0, 'SMOOTH_F1', smooth=1.0)
    big = s.noise(7.0, 4.0); med = s.noise(60.0, 5.0, 0.7); fine = s.noise(900.0, 2.0)
    ao = s.ao(0.035, 6)
    rm = s.step(s.add(s.add(s.mul(s.inv(ao), 1.0), s.mul(big, 0.9)), s.mul(med, 0.55)), 1.42 - rust * 0.8, 1.62 - rust * 0.8)
    rm = s.sat(s.add(rm, s.mul(s.step(fine, 0.6, 0.68), 0.4)))                        # speckle of rust in the pits everywhere
    if burnt is not None:
        rm = s.sat(s.add(rm, s.mul(burnt(s), s.step(med, 0.3, 0.55))))
    wr = s.wear(0.005, 3.5, 110.0, bright)
    scale = s.ramp(s.noise(38.0, 4.0, 0.65), [(0.3, (0.04, 0.042, 0.05)), (0.5, (0.075, 0.075, 0.085)), (0.72, (0.125, 0.12, 0.12))])
    rustc = s.ramp(s.noise(170.0, 5.0, 0.7), [(0.28, (0.05, 0.022, 0.011)), (0.5, (0.15, 0.06, 0.023)), (0.75, (0.3, 0.135, 0.05))])
    bc = s.mix(scale, rustc, rm); bc = s.mix(bc, (0.5, 0.49, 0.47), wr)
    metal = s.mixf(1.0, 0.0, rm); metal = s.mixf(metal, 1.0, wr)
    rough = s.mixf(s.ramp(med, [(0.3, 0.42), (0.7, 0.68)]), s.ramp(fine, [(0.3, 0.82), (0.7, 0.96)]), rm); rough = s.mixf(rough, 0.3, wr)
    if heat is not None:                              # a breath of temper colour where the iron runs hot: straw to blue, never a rainbow
        h = heat(s); tc = s.ramp(s.add(h, s.mul(s.sub(med, 0.5), 0.3)), [(0.3, (0.075, 0.075, 0.085)), (0.5, (0.16, 0.12, 0.06)), (0.7, (0.1, 0.07, 0.1)), (0.85, (0.05, 0.065, 0.12))])
        bc = s.mix(bc, tc, s.mul(s.mul(s.step(h, 0.2, 0.4), s.inv(rm)), 0.22))
    if soot is not None:
        so = soot(s); so = s.step(s.add(so, s.mul(s.sub(s.noise(26.0, 5.0, 0.7), 0.5), 0.5)), 0.3, 0.7)
        bc = s.mix(bc, s.ramp(fine, [(0.3, (0.014, 0.013, 0.012)), (0.7, (0.028, 0.026, 0.024))]), so); metal = s.mixf(metal, 0.0, so); rough = s.mixf(rough, 0.96, so)
    h = s.add(s.mul(ham, 0.6 * hammer), s.mul(ham2, 0.9 * hammer)); h = s.sub(h, s.mul(rm, s.add(0.2, s.mul(fine, 0.35))))
    return s.finish(bc, rough, metal, height=h, bump=0.003, bevel=0.002)


def m_wood(name, dark=(0.045, 0.026, 0.014), mid=(0.2, 0.115, 0.058), light=(0.42, 0.28, 0.16), tile=0.45, soot=None, grease=0.3, wear=0.45, stain=None, bevel=0.003, scratch=0.0, bump=0.0022, endgrain=True):
    """riven / adzed timber from the Poly Haven rough_wood scan (grain along UV v), recoloured by value, with handling grease,
    dirt in the checks and raw pale wood on the worn arrises"""
    s = NT(name)
    uv = s.vec(s.UV, scale=(1 / tile, 1 / tile, 1))
    d = s.img('polyhaven/rough_wood/rough_wood_diff_2k.jpg', uv); lum = s.bw(d)
    col = s.ramp(lum, [(0.02, dark), (0.14, mid), (0.42, light)])
    col = s.mix(col, s.mix(col, d, 0.5, 'OVERLAY'), 0.5)
    rv = s.rand(); col = s.mix(col, s.mix(col, (0.5, 0.36, 0.25), 0.6, 'MULTIPLY'), s.step(rv, 0.3, 0.9))     # board-to-board value
    big = s.noise(5.0, 4.0); ao = s.ao(0.05, 6)
    dirt = s.sat(s.add(s.mul(s.inv(ao), 1.1), s.mul(s.sub(big, 0.5), 0.5)))
    col = s.mix(col, s.mix(col, (0.16, 0.12, 0.085), 1.0, 'MULTIPLY'), dirt)
    wr = s.wear(0.008, 3.0, 45.0, wear); col = s.mix(col, s.mix(light, (0.62, 0.48, 0.33), 0.5), s.mul(wr, 0.75))
    rg = s.img('polyhaven/rough_wood/rough_wood_rough_2k.jpg', uv, 'Non-Color')
    rough = s.ramp(rg, [(0.2, 0.55), (0.9, 0.92)])
    if grease:                                         # polished dark by hands
        g = s.step(s.add(s.noise(9.0, 3.0), s.mul(wr, 0.3)), 1.0 - grease, 1.15 - grease * 0.6)
        col = s.mix(col, s.mix(col, (0.5, 0.4, 0.3), 1.0, 'MULTIPLY'), s.mul(g, 0.6)); rough = s.mixf(rough, 0.42, s.mul(g, 0.7))
    if stain is not None:
        st = stain(s); col = s.mix(col, s.mix(col, st[1], 1.0, 'MULTIPLY'), st[0]); rough = s.mixf(rough, st[2], st[0])
    if soot is not None:
        so = soot(s); so = s.step(s.add(so, s.mul(s.sub(s.noise(30.0, 5.0, 0.7), 0.5), 0.5)), 0.35, 0.8)
        col = s.mix(col, (0.016, 0.014, 0.012), so); rough = s.mixf(rough, 0.95, so)
    hgt = s.img('polyhaven/rough_wood/rough_wood_disp_2k.jpg', uv, 'Non-Color')
    nm = s.img('polyhaven/rough_wood/rough_wood_nor_gl_2k.jpg', uv, 'Non-Color')
    if scratch:                                        # knife cuts and scores: thin straight lines in three directions, pale when fresh, dirty when old
        sc = 0.0
        for i, (rz, sc_) in enumerate(((0.3, 9.0), (1.4, 14.0), (2.5, 7.0), (0.9, 11.0))):
            n_ = s.noise(1.0, 1.0, 0.4, vec=s.vec(s.P, scale=(sc_ * 60.0, sc_, sc_ * 60.0), rot=(0.2 * i, 0.3, rz), loc=(i * 3.1, i * 1.7, 0.0)))
            l_ = s.step(n_, 0.81 - 0.04 * scratch, 0.825 - 0.04 * scratch); sc = l_ if i == 0 else s.mx(sc, l_)
        old = s.step(s.noise(6.0, 3.0), 0.4, 0.6)
        col = s.mix(col, s.mix(s.mix(light, (0.6, 0.47, 0.33), 0.5), s.mix(col, (0.3, 0.24, 0.18), 1.0, 'MULTIPLY'), old), s.mul(sc, 0.55)); rough = s.mixf(rough, 0.8, sc)
        hgt = s.sub(hgt, s.mul(sc, 0.5))
    return s.finish(col, rough, 0.0, height=hgt, bump=bump, bevel=bevel, nmap=(nm, 1.0))


def m_tar(name):
    """pitch: black, wet-glossy where thick, dusty where thin"""
    s = NT(name); n = s.noise(120.0, 4.0)
    bc = s.ramp(n, [(0.3, (0.012, 0.01, 0.008)), (0.7, (0.03, 0.022, 0.014))])
    return s.finish(bc, s.ramp(s.noise(40.0, 3.0), [(0.3, 0.1), (0.7, 0.32)]), 0.0, height=s.noise(300.0, 2.0), bump=0.0003, bevel=0.0015)


def m_plain(name, c0, c1, r0=0.8, r1=0.95, scale=200.0, bump=0.0004):
    s = NT(name); n = s.noise(scale, 4.0, 0.7)
    return s.finish(s.ramp(n, [(0.3, c0), (0.7, c1)]), s.ramp(n, [(0.3, r0), (0.7, r1)]), 0.0, height=n, bump=bump, bevel=0.0)


def _axial(s, origin, axis, z0, z1):
    dv = s.node('ShaderNodeVectorMath', operation='DOT_PRODUCT'); sb = s.node('ShaderNodeVectorMath', operation='SUBTRACT'); s.L.new(s.P, sb.inputs[0]); sb.inputs[1].default_value = origin
    s.L.new(sb.outputs[0], dv.inputs[0]); dv.inputs[1].default_value = axis
    return s.step(dv.outputs['Value'], z0, z1)


def _dist(s, p):
    d = s.node('ShaderNodeVectorMath', operation='DISTANCE'); s.L.new(s.P, d.inputs[0]); d.inputs[1].default_value = p; return d.outputs['Value']


def m_rag(name, z0, z1, axis, origin):
    """pitch-soaked rag binding: hessian weave (Poly Haven hessian_230) along the strip, wrinkles along its length, soaked black
    and tacky low down, dry charred and ash-edged toward the burning end; t = 0 at z0 .. 1 at z1 along the torch axis"""
    s = NT(name)
    t = _axial(s, origin, axis, z0, z1)
    uvw = s.vec(s.UV, scale=(1 / 0.11, 1 / 0.11, 1))
    wv = s.img('polyhaven/hessian_230/hessian_230_disp_2k.jpg', uvw, 'Non-Color'); wn = s.img('polyhaven/hessian_230/hessian_230_nor_gl_2k.jpg', uvw, 'Non-Color')
    wr = s.noise(1.0, 3.0, 0.6, vec=s.vec(s.UV, scale=(420.0, 16.0, 1.0)))                       # wrinkles running along the strip
    big = s.noise(22.0, 4.0, 0.6); ao = s.ao(0.02, 6)
    soak = s.step(s.add(s.inv(t), s.mul(s.sub(big, 0.5), 1.4)), 0.05, 0.6)                       # 1 = wet with pitch
    char = s.step(s.add(t, s.mul(s.sub(s.noise(55.0, 4.0, 0.7), 0.5), 0.8)), 0.72, 1.0)           # 1 = burnt dry
    cloth = s.ramp(wv, [(0.2, (0.022, 0.015, 0.009)), (0.8, (0.085, 0.055, 0.03))])               # tarry brown cloth
    wet = s.ramp(wv, [(0.2, (0.011, 0.009, 0.007)), (0.8, (0.035, 0.024, 0.014))])
    burnt = s.ramp(s.noise(260.0, 4.0, 0.7), [(0.3, (0.013, 0.012, 0.011)), (0.7, (0.03, 0.028, 0.026)), (0.93, (0.055, 0.052, 0.05))])   # char with a few ash flecks
    bc = s.mix(cloth, wet, soak); bc = s.mix(bc, burnt, char)
    edge = s.mul(s.wear(0.004, 4.0, 150.0, 0.4), char); bc = s.mix(bc, (0.14, 0.135, 0.125), s.mul(edge, 0.25))                              # white ash on the burnt edges
    bc = s.mix(bc, s.mix(bc, (0.25, 0.22, 0.2), 1.0, 'MULTIPLY'), s.inv(ao))
    rough = s.mixf(0.88, s.ramp(s.add(wv, s.mul(s.sub(big, 0.5), 0.8)), [(0.25, 0.3), (0.8, 0.72)]), soak); rough = s.mixf(rough, 0.96, char)
    cr = s.voro(210.0, 'DISTANCE_TO_EDGE'); em = s.mul(s.mul(s.step(t, 0.6, 0.9), s.step(s.inv(ao), 0.25, 0.7)), s.step(s.noise(70.0, 3.0), 0.45, 0.62))
    em = s.mul(em, s.inv(s.step(cr, 0.0, 0.035)))
    emis = s.mix((0, 0, 0), s.ramp(em, [(0.0, (0.5, 0.03, 0.0)), (0.6, (1.0, 0.22, 0.02)), (1.0, (1.0, 0.6, 0.15))]), em)
    h = s.add(s.add(s.mul(wv, 0.35), s.mul(wr, 0.9)), s.mul(s.noise(190.0, 3.0), s.mul(char, 0.8)))
    h = s.add(h, s.mul(s.noise(75.0, 4.0, 0.6), 0.8))
    return s.finish(bc, rough, 0.0, height=h, bump=0.003, bevel=0.0015, emis=emis, nmap=(wn, 1.0))


def m_char(name, centre, radius):
    """charcoal: black with a silky sheen along the grain, cross checks, white ash on the tops, live embers in the gaps and
    under-sides toward `centre` (emissive)"""
    s = NT(name)
    cr = s.voro(60.0, 'DISTANCE_TO_EDGE'); crack = s.inv(s.step(cr, 0.0, 0.045))
    grain = s.noise(1.0, 3.0, 0.6, vec=s.vec(s.UV, scale=(700.0, 30.0, 1.0)))
    ao = s.ao(0.035, 8); up = s.sep(s.geo.outputs['Normal'])[2]
    bc = s.ramp(s.noise(90.0, 3.0), [(0.3, (0.012, 0.012, 0.013)), (0.7, (0.036, 0.035, 0.037))])
    rough = s.ramp(grain, [(0.3, 0.32), (0.7, 0.7)])
    ash = s.mul(s.step(s.add(s.add(s.mul(up, 0.5), s.mul(s.noise(35.0, 4.0, 0.7), 1.0)), s.mul(s.edge(0.006, 3.0), 0.5)), 1.2, 1.6), 0.75)
    bc = s.mix(bc, s.ramp(s.noise(240.0, 3.0), [(0.3, (0.07, 0.068, 0.066)), (0.7, (0.2, 0.195, 0.185))]), s.mul(ash, 0.8)); rough = s.mixf(rough, 0.97, ash)
    heat = s.inv(s.step(_dist(s, centre), radius * 0.25, radius))
    em = s.add(s.add(s.mul(heat, 0.75), s.mul(s.inv(ao), 0.75)), s.add(s.mul(crack, 0.35), s.mul(s.sub(s.noise(28.0, 3.0), 0.5), 0.9)))
    em = s.mul(s.step(em, 1.0, 1.55), s.inv(s.mul(ash, 0.5)))
    emis = s.mix((0, 0, 0), s.ramp(em, [(0.0, (0.35, 0.012, 0.0)), (0.5, (1.0, 0.16, 0.012)), (1.0, (1.0, 0.55, 0.12))]), em)
    bc = s.mix(bc, (0.3, 0.07, 0.02), s.mul(em, 0.8))
    h = s.add(s.mul(grain, 0.3), s.mul(crack, -0.35))
    return s.finish(bc, rough, 0.0, height=h, bump=0.0018, bevel=0.002, emis=emis)


def m_ash(name):
    s = NT(name); n = s.noise(50.0, 5.0, 0.7); f = s.step(s.noise(400.0, 2.0), 0.62, 0.7)
    bc = s.mix(s.ramp(n, [(0.3, (0.24, 0.235, 0.225)), (0.7, (0.5, 0.49, 0.46))]), (0.02, 0.02, 0.02), f)
    return s.finish(bc, 0.96, 0.0, height=s.add(n, s.mul(f, 0.5)), bump=0.003, bevel=0.0)


def m_wax(name, soot_z=None, col0=(0.6, 0.47, 0.27), col1=(0.8, 0.7, 0.5)):
    """tallow: yellowed cream, satin, grubby in the folds, sooty round the wick"""
    s = NT(name); n = s.noise(9.0, 3.0); ao = s.ao(0.012, 6)
    bc = s.ramp(n, [(0.3, col0), (0.7, col1)])
    bc = s.mix(bc, s.mix(bc, (0.45, 0.33, 0.2), 1.0, 'MULTIPLY'), s.inv(ao))
    sp = s.step(s.noise(500.0, 2.0), 0.66, 0.72); bc = s.mix(bc, (0.12, 0.09, 0.06), s.mul(sp, 0.6))          # flies and grit caught in it
    rough = s.ramp(s.noise(70.0, 3.0), [(0.3, 0.3), (0.7, 0.55)])
    if soot_z is not None:
        so = s.step(s.add(s.step(s.sep(s.P)[2], soot_z[0], soot_z[1]), s.mul(s.sub(s.noise(120.0, 4.0), 0.5), 0.8)), 0.6, 1.1)
        bc = s.mix(bc, (0.03, 0.026, 0.022), s.mul(so, 0.85)); rough = s.mixf(rough, 0.8, so)
    h = s.add(s.noise(1.0, 3.0, vec=s.vec(s.P, scale=(140.0, 140.0, 16.0))), s.mul(s.noise(40.0, 3.0), 0.6))
    return s.finish(bc, rough, 0.0, height=h, bump=0.0008, bevel=0.0015)


def m_horn(name, socket, glow_r=0.16, top_z=None):
    """scraped horn pane: streaky amber, cloudy, scratched, grime in the corners, smoked toward the top; E = the glow it shows
    when the candle behind it is lit"""
    s = NT(name)
    st = s.noise(1.0, 4.0, 0.6, vec=s.vec(s.P, scale=(45.0, 45.0, 14.0))); cl = s.noise(16.0, 3.0)
    v = s.add(s.mul(s.sub(st, 0.5), 0.8), s.add(0.5, s.mul(s.sub(cl, 0.5), 0.9))); ao = s.ao(0.015, 6)
    bc = s.ramp(v, [(0.2, (0.1, 0.045, 0.014)), (0.45, (0.3, 0.17, 0.055)), (0.75, (0.5, 0.36, 0.16))])
    grime = s.sat(s.add(s.mul(s.inv(ao), 1.3), s.mul(s.sub(s.noise(40.0, 4.0), 0.55), 0.6)))
    bc = s.mix(bc, (0.07, 0.05, 0.03), s.mul(grime, 0.85))
    sm = s.step(s.add(s.step(s.sep(s.P)[2], top_z - 0.12, top_z + 0.02), s.mul(s.sub(s.noise(30.0, 4.0), 0.5), 0.7)), 0.55, 1.15) if top_z is not None else 0.0
    bc = s.mix(bc, (0.035, 0.028, 0.02), s.mul(sm, 0.8))
    scr = s.noise(1.0, 2.0, vec=s.vec(s.P, scale=(900.0, 900.0, 40.0), rot=(0.3, 0.2, 0.0)))
    rough = s.mixf(s.ramp(scr, [(0.35, 0.22), (0.7, 0.5)]), 0.85, grime)
    g = s.math('POWER', s.inv(s.step(_dist(s, socket), 0.0, glow_r)), 1.6)
    g = s.mul(s.mul(g, s.add(0.55, s.mul(v, 0.7))), s.inv(s.mul(s.mx(grime, sm), 0.8)))
    emis = s.mix((0, 0, 0), s.ramp(g, [(0.0, (0.5, 0.14, 0.02)), (0.6, (1.0, 0.5, 0.12)), (1.0, (1.0, 0.8, 0.4))]), g)
    return s.finish(bc, rough, 0.0, height=s.add(scr, st), bump=0.0004, bevel=0.001, emis=emis)


# ================================================================ props
def ell(a, b, sides):
    return [a * b / math.sqrt((b * math.cos(2 * math.pi * k / sides)) ** 2 + (a * math.sin(2 * math.pi * k / sides)) ** 2) for k in range(sides)]


def resamp(ctrl, n, smooth=True):
    """n segments per control span, Catmull-Rom through the control points"""
    C = [np.array(c, float) for c in ctrl]; out = []
    for i in range(len(C) - 1):
        p0 = C[max(i - 1, 0)]; p1 = C[i]; p2 = C[i + 1]; p3 = C[min(i + 2, len(C) - 1)]
        for t in np.linspace(0, 1, n + 1)[:-1]:
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3) if smooth else p1 + (p2 - p1) * t)
    out.append(C[-1]); return out


def torch(b):
    """SM_Prop_Torch_Wall_01. Wall plane y = 0, the torch stands out to -Y. Same pivot, bounds and flame socket as round 1."""
    r = b.rng; rx = b.rx; hi = b.hi
    b.box([-0.045, -0.008, 0.0], [0.045, 0.0, 0.3], 'iron', grain=2, jit=0.0025, seg=b.d(1, 4))          # back plate, two forged spikes with square heads
    for zz in (0.035, 0.265):
        b.rivet([0.004 * (zz > 0.1), -0.008, zz], [0, -1, 0], r=0.013, h=0.008, mat='iron', n=4)
    n0 = b.box([-0.075, -0.0035, 0.42], [0.075, 0.0, 0.95], 'plate', grain=2, jit=0.003, seg=b.d(7, 28))  # smoke plate: thin sheet curled out at the top
    b.deform_since(n0, lambda P: np.c_[P[:, 0], P[:, 1] - 0.03 * np.clip((P[:, 2] - 0.8) / 0.15, 0, 1) ** 2 - 0.003 * np.sin((P[:, 2] - 0.42) * 14) * (P[:, 1] < -0.001), P[:, 2]])
    b.deform_since(0, lambda P: np.c_[P[:, 0], np.where(P[:, 1] > -0.0018, np.minimum(P[:, 1], 0.0), np.minimum(P[:, 1], -0.0028)), P[:, 2]])
    for (x, z) in ((-0.058, 0.45), (0.058, 0.452), (0.002, 0.775)):
        b.rivet([x, -0.0035, z], [0, -1, 0], r=0.0075, mat='plate', n=b.d(6, 10))
    ax = np.array([0.0, -math.sin(0.33), math.cos(0.33)]); c0 = np.array([0.0, -0.135, 0.2]); side = np.array([1.0, 0, 0]); fw = np.cross(ax, side)
    Mh = np.eye(4); Mh[:3, 0] = side; Mh[:3, 1] = fw; Mh[:3, 2] = ax; Mh[:3, 3] = c0
    p_end = c0 + np.array([0, 0.018, -0.028])
    b.tube(resamp([[0, -0.006, 0.06], [0, -0.03, 0.062], [0, -0.062, 0.078], [0, -0.092, 0.11], [0, -0.108, 0.15], p_end], b.d(4, 10)), 1.0, mat='iron', twist=26.0, up=[1, 0, 0], rect=(0.019, 0.019))
    q0 = c0 + ax * 0.08 + fw * 0.03
    b.tube(resamp([[0, -0.006, 0.272], [0, -0.06, 0.262], q0 + [0, 0.004, 0]], b.d(2, 6)), 1.0, mat='iron', up=[1, 0, 0], rect=(0.015, 0.012))
    b.rivet([0, -0.008, 0.272], [0, -1, 0.0], r=0.012, h=0.006, mat='iron', n=b.d(6, 10))
    for zc in (0.0, 0.08):                              # two flat bands gripping the stave
        cc = c0 + ax * zc; rr = 0.0275 if zc else 0.0265
        ring_ = [cc + rr * (math.cos(t) * side + math.sin(t) * fw) for t in np.linspace(0, 2 * math.pi, b.d(14, 40) + 1)[:-1]]
        b.tube(ring_, 1.0, mat='iron', closed=True, up=ax, rect=(0.017, 0.0055))
        b.rivet(cc + rr * fw + fw * 0.002, fw, r=0.006, mat='iron', n=b.d(5, 8))
    ns = b.d(7, 30); zs = np.linspace(-0.16, 0.4, ns); sh = [1, 0.9, 1.02, 0.86, 1, 0.93, 1.03, 0.88]   # the stave: cleft ash, drawknifed, out of true
    rad = np.interp(zs, [-0.16, -0.14, 0.14, 0.4], [0.013, 0.02, 0.0235, 0.022])
    sp = [(0.002 * math.sin(z * 9), 0.0015 * math.sin(z * 13 + 1), z) for z in zs]
    n0 = b.tube(sp, rad, sides=b.d(8, 16), mat='wood', shape=sh if not hi else [sh[k // 2] * (1.0 if k % 2 == 0 else 0.965) for k in range(16)])
    b.xform_since(n0, Mh)
    core = [(0.02, 0.0), (0.036, 0.012), (0.044, 0.05), (0.047, 0.11), (0.043, 0.16), (0.034, 0.192), (0.022, 0.212), (0.0, 0.222)]
    cz = [p[1] for p in core]; cr = [p[0] for p in core]; sd = 4711; Hz = 0.36

    def lump(P, amp=0.1):
        ang = np.arctan2(P[:, 1], P[:, 0]); k = 1 + amp * vnoise(P, sd, 30.0) + 0.05 * np.sin(ang * 3 + P[:, 2] * 40) + 0.05 * np.clip((P[:, 2] - 0.17) / 0.05, 0, 1) * vnoise(P, sd + 1, 60.0)
        Q = P.copy(); Q[:, 0] *= k; Q[:, 1] *= k; Q[:, 2] += 0.004 * np.clip((P[:, 2] - 0.17) / 0.05, 0, 1) * np.sin(ang * 4 + 1); return Q
    n0 = b.lathe(core, n=b.d(14, 40), mat='rag', sub=b.d(2, 6), deform=lump)
    specs = ((3.2, 0.0, 0.012, 0.12, 0.017), (3.0, 2.4, 0.06, 0.185, 0.016), (1.6, 4.4, 0.0, 0.05, 0.014), (1.3, 1.0, 0.15, 0.2, 0.012))
    for (turns, ph, zA, zB, wid) in (specs if hi else specs[:2]):
        m_ = int(turns * b.d(14, 44)); pts = []; rw = []
        for i in range(m_ + 1):
            t = i / m_; a = 2 * math.pi * turns * t + ph; z = zA + (zB - zA) * t + 0.004 * math.sin(a * 1.7 + ph)
            q = float(np.interp(z, cz, cr)) + 0.0035 + 0.0015 * math.sin(a * 2.3 + ph * 3) + 0.001 * math.sin(t * 40 + ph)
            pts.append((q * math.cos(a), q * math.sin(a), z)); rw.append(1.0 + 0.16 * math.sin(t * 31 + ph) + 0.1 * math.sin(t * 97))
        b.tube(pts, rw, sides=b.d(6, 10), mat='rag', shape=ell(wid, 0.003, b.d(6, 10)), up=[0, 0, 1], caps=True, ups=[(0.25 * p_[0] / 0.05, 0.25 * p_[1] / 0.05, 1.0) for p_ in pts])
    for k in range(5):                                  # torn tails standing off the wrap
        a = r.uniform(0, 6.28); z = r.uniform(0.03, 0.17); q = float(np.interp(z, cz, cr)) + 0.006; L = r.uniform(0.03, 0.055)
        d0 = np.array([math.cos(a), math.sin(a), 0.0]); tg = np.array([-math.sin(a), math.cos(a), 0.0]); nt_ = b.d(4, 8)
        pts = [d0 * q + [0, 0, z] + tg * L * t + d0 * 0.014 * t ** 2 - np.array([0, 0, 0.022]) * t ** 2 for t in np.linspace(0, 1, nt_)]
        b.tube(pts, np.linspace(1.0, 0.5, nt_), sides=b.d(4, 8), mat='rag', shape=ell(0.011, 0.002, b.d(4, 8)), up=[0, 0, 1])
    if hi:
        for k in range(160):                            # frayed threads, most of them at the burnt end
            a = rx.uniform(0, 6.28); z = min(0.215, abs(rx.normal(0.19, 0.045))) if k < 100 else rx.uniform(0.0, 0.2)
            q = float(np.interp(z, cz, cr)) + 0.005; d0 = np.array([math.cos(a), math.sin(a), 0.0]); L = rx.uniform(0.004, 0.012)
            dirn = d0 * rx.uniform(0.1, 0.5) + np.array([0, 0, rx.uniform(-0.3, 1.0)]) + np.array([-math.sin(a), math.cos(a), 0]) * rx.uniform(-0.8, 0.8); dirn /= np.linalg.norm(dirn)
            p0 = d0 * q + [0, 0, z]
            b.tube([p0, p0 + dirn * L * 0.5 + d0 * 0.001, p0 + dirn * L + np.array([0, 0, -0.002])], [0.0007, 0.0006, 0.0003], sides=3, mat='fibre', caps=False)
        for k in range(3):                              # iron wire binding the foot of the head
            z = 0.014 + 0.007 * k
            b.tube([(float(np.interp(z, cz, cr)) + 0.0095) * np.array([math.cos(t), math.sin(t), 0]) + [0, 0, z + 0.003 * math.sin(t + k)] for t in np.linspace(0, 2 * math.pi, 40)[:-1]], 0.0011, sides=5, mat='iron', closed=True, up=[0, 0, 1])
    b.xform_since(n0, Mh @ np.array(Matrix.Translation((0, 0, Hz))))
    if hi:
        n0 = len(b.V)
        for k in range(7):                              # runs of pitch down the stave, each ending in a bead
            a = rx.uniform(0, 6.28) if k else -1.57; L = rx.uniform(0.03, 0.13) if k else 0.15; w = rx.uniform(0.0025, 0.0042); pts = []; m_ = 12
            for i in range(m_ + 1):
                t = i / m_; z = Hz + 0.012 - L * t; aa = a + 0.25 * math.sin(t * 5 + k) * t
                q = float(np.interp(z, [-0.16, 0.14, 0.4], [0.02, 0.0235, 0.022])) + 0.0012
                pts.append((q * math.cos(aa), q * math.sin(aa), z))
            rw = [w * (1.0 - 0.35 * t) for t in np.linspace(0, 1, m_ + 1)]; rw[-2] = w * 1.25; rw[-1] = w * 1.45
            b.tube(pts, rw, sides=8, mat='tar'); b.blob(pts[-1], (w * 1.5, w * 1.5, w * 2.0), sub=2, mat='tar', lump=0.0)
        b.xform_since(n0, Mh)
    return {'socket': [0.0, -0.329, 0.768]}


def torch_mats():
    ax = (0.0, -math.sin(0.33), math.cos(0.33)); c0 = (0.0, -0.135, 0.2)
    hb = tuple(c0[i] + ax[i] * 0.36 for i in range(3))

    def soot_plate(s):                                  # the smoke plate: clean at the foot, black above the flame
        z = s.sep(s.P)[2]; x = s.sep(s.P)[0]
        return s.mul(s.step(z, 0.5, 0.8), s.inv(s.mul(s.step(s.math('ABSOLUTE', x), 0.035, 0.1), s.inv(s.step(z, 0.75, 0.95)))))

    return {'iron': m_iron('H_iron', soot=lambda s: s.mul(s.step(s.sep(s.P)[2], 0.2, 0.45), 0.8), rust=0.7, bright=0.3),
            'plate': m_iron('H_plate', soot=soot_plate, heat=lambda s: s.step(s.sep(s.P)[2], 0.4, 0.62), rust=0.6, bright=0.2, hammer=0.7),
            'wood': m_wood('H_wood', dark=(0.035, 0.024, 0.016), mid=(0.13, 0.09, 0.058), light=(0.3, 0.23, 0.16), soot=lambda s: s.inv(s.step(_dist(s, hb), 0.0, 0.26)), grease=0.55), 'rag': m_rag('H_rag', 0.0, 0.2, ax, hb), 'tar': m_tar('H_tar'),
            'fibre': m_plain('H_fibre', (0.02, 0.016, 0.012), (0.07, 0.055, 0.04))}


def brazier(b):
    """SM_Prop_Brazier_Standing_01: three forged legs splayed from a collar, a riveted basket of ten straps and three hoops, an ash
    pan under it, a bed of charcoal with live embers"""
    r = b.rng; rx = b.rx; hi = b.hi; H = 0.95; Rb = 0.24
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3; d = np.array([math.cos(a), math.sin(a), 0.0]); tg = np.array([-math.sin(a), math.cos(a), 0.0])
        ctrl = [d * 0.36, d * 0.33 + [0, 0, 0.03], d * 0.16 + [0, 0, 0.4], d * 0.07 + [0, 0, 0.62], d * 0.12 + [0, 0, 0.74], d * 0.2 + [0, 0, H - 0.2]]
        pts = resamp(ctrl, b.d(4, 12)); rr = np.interp(np.linspace(0, 1, len(pts)), np.linspace(0, 1, 6), [1.4, 1.1, 1.0, 1.0, 1.0, 0.9])
        b.tube(pts, rr, mat='iron', twist=7.0, up=tg, rect=(0.02, 0.02))
        b.box([-0.034, -0.03, 0.0], [0.034, 0.03, 0.011], 'iron', grain=0, jit=0.004, M=Matrix.Translation(d * 0.372) @ Matrix.Rotation(a, 4, 'Z'))       # the foot, beaten flat
    for (zz, q, wd) in ((0.62, 0.079, 0.022), (0.4, 0.168, 0.016)):                               # collar and stretcher ring
        b.tube([[q * math.cos(t), q * math.sin(t), zz + 0.003 * math.sin(2 * t)] for t in np.linspace(0, 2 * math.pi, b.d(18, 48) + 1)[:-1]], 1.0, mat='iron', closed=True, up=[0, 0, 1], rect=(wd, 0.006))
    b.lathe([(0, H - 0.262), (0.2, H - 0.26), (0.216, H - 0.25), (0.222, H - 0.233), (0.2, H - 0.238), (0.1, H - 0.25), (0, H - 0.252)], n=b.d(18, 64), mat='iron',
            deform=lambda P: P + np.c_[0 * P[:, 0], 0 * P[:, 0], 0.004 * vnoise(P, 5, 9.0)])
    b.lathe([(0.19, H - 0.246), (0.11, H - 0.236), (0, H - 0.23)], n=b.d(12, 40), mat='ash', sub=b.d(1, 4), deform=lambda P: P + np.c_[0 * P[:, 0], 0 * P[:, 0], 0.006 * vnoise(P, 8, 25.0)])
    b.deform_since(0, lambda P: np.c_[P[:, 0], P[:, 1], np.maximum(P[:, 2], 0.0)])                # nothing below the floor
    hoops = ((H - 0.2, 0.162), (H - 0.1, 0.218), (H, Rb + 0.004))
    for k in range(10):                                                                           # basket straps, flaring up
        a = 2 * math.pi * k / 10 + 0.05 * math.sin(k * 2.1); d = np.array([math.cos(a), math.sin(a), 0.0]); tg = np.array([-math.sin(a), math.cos(a), 0.0])
        ctrl = [d * q + [0, 0, zz] for (q, zz) in ((0.1, H - 0.237), (0.16, H - 0.2), (0.215, H - 0.1), (Rb, H - 0.01), (Rb + 0.014, H + 0.014))]
        b.tube(resamp(ctrl, b.d(2, 8)), 1.0, mat='hot', up=tg, rect=(0.019, 0.0055))
        if hi:
            for (zz, q) in hoops:
                b.rivet(d * (q + 0.0085) + [0, 0, zz], d, r=0.0058, mat='hot', n=8)
    for (zz, q) in hoops:
        b.tube([[(q + 0.0052) * math.cos(t) * (1 + 0.012 * math.sin(3 * t)), (q + 0.0052) * math.sin(t), zz + 0.004 * math.sin(2 * t)] for t in np.linspace(0, 2 * math.pi, b.d(24, 72) + 1)[:-1]], 1.0, mat='hot', closed=True, up=[0, 0, 1], rect=(0.016, 0.005))
    dome = [(0.146, H - 0.2), (0.2, H - 0.1), (0.19, H - 0.05), (0.12, H - 0.006), (0.0, H + 0.012)]
    b.lathe(dome, n=b.d(16, 48), mat='char', sub=b.d(2, 6), deform=lambda P: P * (1 + 0.05 * vnoise(P, 3, 22.0))[:, None] * np.array([1, 1, 1.0]) + np.c_[0 * P[:, 0], 0 * P[:, 0], 0.012 * vnoise(P, 4, 30.0)])
    dq = [p[0] for p in dome][::-1]; dzz = [p[1] for p in dome][::-1]
    for k in range(b.d(18, 80)):                                                                  # charcoal: the big lumps are geometry in the game mesh too
        rr_ = r if k < 18 else rx
        a = rr_.uniform(0, 6.28); q = 0.19 * math.sqrt(rr_.uniform(0, 1)); zz = float(np.interp(q, dq, dzz)) + rr_.uniform(0.0, 0.02)
        big = k < 18; sz = [rr_.uniform(0.032, 0.058) if big else rr_.uniform(0.014, 0.03), rr_.uniform(0.022, 0.034) if big else rr_.uniform(0.01, 0.02), rr_.uniform(0.018, 0.028) if big else rr_.uniform(0.008, 0.016)]
        M = Matrix.Rotation(float(rr_.uniform(0, 3)), 4, 'Z') @ Matrix.Rotation(float(rr_.uniform(-0.7, 0.7)), 4, 'X'); sd = int(rr_.integers(1e6))
        b.blob((q * math.cos(a), q * math.sin(a), zz), sz, sub=b.d(1, 3), mat='char', lump=0.2, freq=1.1, seed=sd, M=M, flat=0.22)
    return {'socket': [0.0, 0.0, 0.97]}


def brazier_mats():
    H = 0.95
    return {'iron': m_iron('H_iron', rust=0.75, bright=0.3, soot=lambda s: s.mul(s.step(s.sep(s.P)[2], 0.55, 0.75), 0.75)),
            'hot': m_iron('H_hot', rust=0.6, bright=0.1, burnt=lambda s: s.step(s.sep(s.P)[2], H - 0.22, H - 0.05), soot=lambda s: s.mul(s.step(s.sep(s.P)[2], H - 0.12, H + 0.02), 0.7)),
            'char': m_char('H_char', (0.0, 0.0, H - 0.1), 0.24), 'ash': m_ash('H_ash')}


def candle(b):
    """SM_Prop_Candle_Holder_01 (and SM_Candle_Iron_PR): tallow candle guttered on a forged pricket stick"""
    r = b.rng; rx = b.rx; hi = b.hi; H = 0.45; zt = H - 0.012
    hp = [(0, 0.0), (0.085, 0.0), (0.097, 0.004), (0.1, 0.012), (0.09, 0.018), (0.05, 0.024), (0.02, 0.034), (0.012, 0.05), (0.011, 0.1), (0.022, 0.112), (0.024, 0.122), (0.012, 0.134), (0.011, 0.2),
          (0.03, 0.212), (0.06, 0.218), (0.066, 0.232), (0.062, 0.236), (0.05, 0.226), (0.02, 0.224), (0, 0.224)]
    b.lathe(hp, n=b.d(26, 72), mat='iron', deform=lambda P: P * np.c_[1 + 0.02 * vnoise(P, 2, 14.0), 1 + 0.02 * vnoise(P, 3, 14.0), np.ones(len(P))])
    prof = [(0, 0.222), (0.021, 0.222), (0.0235, 0.23), (0.023, 0.3), (0.0225, 0.38), (0.022, zt - 0.02), (0.0235, zt - 0.006), (0.022, zt), (0.016, zt - 0.004), (0.008, zt - 0.012), (0, zt - 0.014)]

    def gut(P):
        P = P.copy(); top = np.clip((P[:, 2] - (zt - 0.03)) / 0.03, 0, 1); ang = np.arctan2(P[:, 1], P[:, 0])
        P[:, 2] -= 0.012 * top * (0.5 + 0.5 * np.cos(ang - 0.8)); k = 1 + 0.03 * vnoise(P, 6, 35.0) * (1 + 2 * top); P[:, 0] *= k; P[:, 1] *= k
        P[:, 0] += 0.004 * np.clip((P[:, 2] - 0.23) / 0.2, 0, 1) ** 2                                # a slight lean
        return P
    b.lathe(prof, n=b.d(14, 56), mat='wax', sub=b.d(1, 5), deform=gut)
    runs = [(0.8, 0.14, 0.006), (1.5, 0.07, 0.005), (3.9, 0.19, 0.0065), (5.2, 0.05, 0.0045)] + ([(2.6, 0.03, 0.004), (4.5, 0.1, 0.004), (0.2, 0.045, 0.0035), (3.2, 0.06, 0.003)] if hi else [])
    for (a, l, rr) in runs:                              # runs of wax, each ending in a bead
        q = 0.0235; x, y = q * math.cos(a), q * math.sin(a)
        ctrl = [[x * 0.9, y * 0.9, zt - 0.012], [x * 1.05, y * 1.05, zt - 0.03], [x * 1.08, y * 1.08, zt - l * 0.6], [x * 1.12, y * 1.12, zt - l], [x * 1.0, y * 1.0, zt - l - rr]]
        pts = resamp(ctrl, b.d(1, 4)); rw = np.interp(np.linspace(0, 1, len(pts)), np.linspace(0, 1, 5), [rr * 0.6, rr, rr * 0.85, rr * 1.35, rr * 0.4])
        pts = [p + [0.004 * np.clip((p[2] - 0.23) / 0.2, 0, 1) ** 2, 0, 0] for p in pts]
        b.tube(pts, rw, sides=b.d(6, 12), mat='wax')
    b.lathe([(0, 0.224), (0.036, 0.224), (0.04, 0.229), (0.03, 0.234), (0, 0.236)], n=b.d(12, 40), mat='wax', c=(0.012, 0.008, 0.0), sub=b.d(1, 3),
            deform=lambda P: P * np.c_[1 + 0.12 * vnoise(P, 9, 40.0), 1 + 0.12 * vnoise(P, 10, 40.0), np.ones(len(P))])        # the puddle in the pan
    b.tube(resamp([[0.004, 0, zt - 0.016], [0.005, 0.0, zt + 0.004], [0.008, 0.001, zt + 0.011], [0.011, 0.001, zt + 0.01]], b.d(1, 4)), [0.0018] * (b.d(1, 4) * 3) + [0.0011], sides=b.d(4, 8), mat='wick')
    return {'socket': [0.003, 0.0, 0.452]}


def candle_mats():
    return {'iron': m_iron('H_iron', rust=0.7, bright=0.4, hammer=0.5), 'wax': m_wax('H_wax', soot_z=(0.41, 0.445)), 'wick': m_plain('H_wick', (0.014, 0.013, 0.012), (0.05, 0.045, 0.04))}


def lantern(b):
    """SM_Prop_Lantern_Hanging_01: riveted sheet-iron frame, four horn panes, pierced cap, chain to a ceiling hook. Origin at the hook"""
    r = b.rng; rx = b.rx; hi = b.hi; w = 0.085; zb = -0.78; zt = -0.5
    rot45 = lambda P: np.c_[(P[:, 0] - P[:, 1]) * 0.7071, (P[:, 0] + P[:, 1]) * 0.7071, P[:, 2]]
    b.lathe([(0, zb), (w * 1.45, zb), (w * 1.5, zb + 0.008), (w * 1.45, zb + 0.016), (0, zb + 0.016)], n=4, mat='iron', deform=rot45)
    b.lathe([(0, zt - 0.006), (w * 1.5, zt - 0.006), (w * 1.55, zt), (w * 1.1, zt + 0.045), (w * 0.5, zt + 0.1), (w * 0.3, zt + 0.108), (0, zt + 0.11)], n=4, mat='cap', deform=rot45)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; x, y = w * 1.42 * math.cos(a), w * 1.42 * math.sin(a)
        b.tube([[x, y, zb + 0.01], [x * (1 + 0.01 * (k == 1)), y, (zb + zt) / 2], [x, y, zt]], 1.0, mat='iron', up=[math.cos(a), math.sin(a), 0], rect=(0.015, 0.015))            # corner bars
        a2 = k * math.pi / 2; n_ = np.array([math.cos(a2), math.sin(a2), 0.0]); t_ = np.array([-math.sin(a2), math.cos(a2), 0.0]); d = w * 0.98
        M = np.eye(4); M[:3, 0] = -t_; M[:3, 1] = n_; M[:3, 2] = [0, 0, 1]
        b.box([-w * 0.96, d - 0.0025, zb + 0.018], [w * 0.96, d, zt - 0.008], 'horn', grain=2, M=M)                                         # horn pane
        b.tube([n_ * (d + 0.002) + [0, 0, zb + 0.018], n_ * (d + 0.002) + [0, 0, zt - 0.008]], 1.0, mat='iron', up=t_, rect=(0.008, 0.004))   # glazing bar
        if hi:
            for (u, zz) in ((-0.9, zb + 0.008), (0.9, zb + 0.008), (0.0, zb + 0.008), (-0.8, zt - 0.003), (0.8, zt - 0.003)):                 # rivets along tray and eave
                b.rivet(n_ * (w * 1.03) + t_ * u * w + [0, 0, zz], n_, r=0.0035, mat='iron', n=6)
            nv = (n_ * 0.52 + np.array([0, 0, 0.855])); nv /= np.linalg.norm(nv)
            for u in (-0.03, 0.0, 0.03):                                                                                                  # smoke vents punched in the cap
                p = n_ * 0.07 + t_ * u + [0, 0, zt + 0.03]
                b.tube([p - nv * 0.004, p + nv * 0.0015], 0.0045, sides=8, mat='void')
    if hi:                                              # door furniture on the front pane: two hinge knuckles and a hasp
        for zz in (zb + 0.07, zt - 0.06):
            b.tube([[-w * 1.0, -w * 1.02, zz - 0.012], [-w * 1.0, -w * 1.02, zz + 0.012]], 0.0045, sides=8, mat='iron')
        b.box([w * 0.8, -w * 1.06, (zb + zt) / 2 - 0.006], [w * 1.04, -w * 1.02, (zb + zt) / 2 + 0.006], 'iron', grain=0)
        b.rivet([w * 0.92, -w * 1.06, (zb + zt) / 2], [0, -1, 0], r=0.003, mat='iron', n=6)
    b.lathe([(0, zb + 0.016), (0.014, zb + 0.016), (0.0145, zb + 0.08), (0.011, zb + 0.09), (0.005, zb + 0.086), (0, zb + 0.084)], n=b.d(8, 24), mat='wax', sub=b.d(1, 3))
    b.lathe([(0, zb + 0.016), (0.028, zb + 0.016), (0.03, zb + 0.019), (0.02, zb + 0.022), (0.0, zb + 0.023)], n=b.d(8, 24), mat='wax')
    b.tube([[0, 0, zb + 0.084], [0.001, 0, zb + 0.1]], 0.0012, sides=4, mat='void')
    zz = zt + 0.11
    for k in range(7):                                                                           # ring and chain
        tw = (k % 2) * math.pi / 2; c_ = zz + 0.028 + k * 0.05; lh = 0.034
        pts = [[0.012 * math.cos(t) * math.cos(tw), 0.012 * math.cos(t) * math.sin(tw), c_ + lh * math.sin(t)] for t in np.linspace(0, 2 * math.pi, b.d(10, 24) + 1)[:-1]]
        b.tube(pts, 0.004, sides=b.d(5, 8), mat='iron', closed=True, up=[math.sin(tw), -math.cos(tw), 0])
    b.tube(resamp([[0, 0, -0.07], [0, 0, -0.03], [0.02, 0, -0.012], [0.03, 0, -0.03], [0.02, 0, -0.05]], b.d(1, 5)), 0.005, sides=b.d(5, 8), mat='iron')
    b.box([-0.03, -0.03, -0.006], [0.03, 0.03, 0.0], 'iron', grain=0, jit=0.002)
    return {'socket': [0.0, 0.0, round(zb + 0.115, 3)]}


def lantern_mats():
    sock = (0.0, 0.0, -0.665)
    return {'iron': m_iron('H_iron', rust=0.75, bright=0.3, hammer=0.4), 'cap': m_iron('H_cap', rust=0.6, bright=0.2, hammer=0.4, soot=lambda s: s.step(s.sep(s.P)[2], -0.5, -0.42)),
            'horn': m_horn('H_horn', sock, 0.17, top_z=-0.508), 'wax': m_wax('H_wax'), 'void': m_plain('H_void', (0.012, 0.012, 0.012), (0.014, 0.013, 0.012))}


def barrel(b):
    """SM_Barrel_Oak_PR: twenty separate oak staves of uneven width with gaps, heads of five boards set in the croze, four driven
    hoops with riveted laps, a bung. 0.84 m at the bilge, 1.0 m tall, base centre"""
    r = b.rng; rx = b.rx; hi = b.hi; H = 1.0; re = 0.335; rm = 0.42; ns = 20
    prof = lambda z: re + (rm - re) * (1 - (2 * z / H - 1) ** 2)
    wd = r.uniform(0.8, 1.25, ns); wd = wd / wd.sum() * 2 * math.pi; th0 = np.concatenate([[0], np.cumsum(wd)[:-1]])
    for k in range(ns):
        dr = r.uniform(-0.002, 0.002); dz = r.uniform(-0.004, 0.003); gap = r.uniform(0.0008, 0.0022); tw = r.uniform(-0.004, 0.004)
        wr_ = wd[k] * rm; n0 = b.box([0.0, -0.024, 0.0], [wr_, 0.0, 1.0], 'wood', grain=2, seg=b.d(8, 20))

        def bend(P, k=k, dr=dr, dz=dz, gap=gap, tw=tw, wr_=wr_):
            z = P[:, 2] * (H + dz) ; rr = prof(np.clip(z, 0, H)) + P[:, 1] + dr + tw * (P[:, 2] - 0.5)
            ga = gap / rr; th = th0[k] + ga + (1.0 - P[:, 0] / wr_) * (wd[k] - 2 * ga)      # mirrored so the faces stay outward
            return np.c_[rr * np.cos(th), rr * np.sin(th), z]
        b.deform_since(n0, bend)
    for (zh, top) in ((0.035, False), (H - 0.035, True)):                                  # heads
        R = prof(zh) - 0.02; xs = np.linspace(-R, R, 6) + np.array([0, 0.012, -0.01, 0.008, -0.012, 0])
        for i in range(5):
            xa, xb = xs[i] + 0.0012, xs[i + 1] - 0.0012; xm = min(abs(xa), abs(xb)); yl = math.sqrt(max(R * R - xm * xm, 0.0)) + 0.012
            n0 = b.box([xa, -yl, zh - 0.011 + 0.002 * math.sin(i * 2.2)], [xb, yl, zh + 0.011 + 0.002 * math.sin(i * 2.2)], 'head', grain=1, jit=0.0012, seg=b.d(6, 16))

            def clip(P, R=R):                               # the boards are sawn round and sit in the croze
                q = np.hypot(P[:, 0], P[:, 1]); k = np.minimum(1.0, (R + 0.006) / np.maximum(q, 1e-6)); return np.c_[P[:, 0] * k, P[:, 1] * k, P[:, 2]]
            b.deform_since(n0, clip)
    for zh in (0.07, 0.25, H - 0.25, H - 0.07):                                            # hoops, driven on: each a touch out of level, lapped and riveted
        tilt = r.uniform(-0.006, 0.006); ph = r.uniform(0, 6.28); R = prof(zh) + 0.0058; n_ = b.d(40, 96)
        pts = [[R * math.cos(t), R * math.sin(t), zh + tilt * math.sin(t + ph)] for t in np.linspace(0, 2 * math.pi, n_ + 1)[:-1]]
        slope = (prof(zh + 0.02) - prof(zh - 0.02)) / 0.04
        b.tube(pts, 1.0, mat='iron', closed=True, rect=(0.042, 0.0035), ups=[(slope * p_[0] / R, slope * p_[1] / R, 1.0) for p_ in pts])
        if hi:
            lap = [[(R + 0.0032) * math.cos(t), (R + 0.0032) * math.sin(t), zh + tilt * math.sin(t + ph)] for t in np.linspace(ph, ph + 0.3, 8)]
            b.tube(lap, 1.0, mat='iron', rect=(0.04, 0.003), ups=[(0, 0, 1.0)] * 8)
            for t in (ph + 0.06, ph + 0.22):
                d = np.array([math.cos(t), math.sin(t), 0.0]); b.rivet(d * (R + 0.0048) + [0, 0, zh + tilt * math.sin(t + ph)], d, r=0.0065, mat='iron', n=10)
    a = th0[3] + wd[3] / 2; d = np.array([math.cos(a), math.sin(a), 0.0])                   # the bung
    M = Matrix.Translation(d * (rm - 0.006) + np.array([0, 0, H / 2])) @ Vector((0, 0, 1)).rotation_difference(Vector(d)).to_matrix().to_4x4()
    n0 = b.lathe([(0.0, 0.0), (0.024, 0.0), (0.022, 0.014), (0.018, 0.017), (0.0, 0.018)], n=b.d(8, 20), mat='head'); b.xform_since(n0, M)
    return {}


def barrel_mats():
    def runs(s):                                        # rust and wet running down from under each hoop, and a dark tide mark at the foot
        z = s.sep(s.P)[2]; m = 0.0
        ang = s.node('ShaderNodeMath', operation='ARCTAN2'); s.L.new(s.sep(s.P)[1], ang.inputs[0]); s.L.new(s.sep(s.P)[0], ang.inputs[1])
        cx = s.node('ShaderNodeCombineXYZ'); s.L.new(s.mul(ang.outputs[0], 9.0), cx.inputs[0]); s.L.new(s.mul(z, 1.3), cx.inputs[2]); st = s.noise(1.0, 4.0, 0.65, vec=cx.outputs[0])
        for zh in (0.07, 0.25, 0.75, 0.93):
            band = s.mul(s.step(z, zh - 0.16, zh - 0.02), s.inv(s.step(z, zh - 0.02, zh + 0.0)))
            m = s.mx(m, band) if not isinstance(m, float) else band
        m = s.mul(m, s.step(st, 0.42, 0.7)); foot = s.mul(s.inv(s.step(z, 0.0, 0.1)), 0.8)
        return (s.sat(s.add(s.mul(m, 0.8), foot)), (0.36, 0.2, 0.12), 0.8)
    kw = dict(dark=(0.04, 0.023, 0.012), mid=(0.17, 0.095, 0.045), light=(0.36, 0.23, 0.125), tile=0.55, grease=0.25, wear=0.4)
    return {'wood': m_wood('H_wood', stain=runs, **kw), 'head': m_wood('H_head', **kw), 'iron': m_iron('H_iron', rust=0.85, bright=0.3, hammer=0.45)}


ASSETS = {
    'SM_Prop_Torch_Wall_01': dict(fn=torch, mats=torch_mats, px=2048, cls='prop', slots=[('MI_Prop_Torch_Wall_01', 'opaque', None)], emissive=True, emis_nits=40.0,
                                  extrude=0.008, maxdist=0.03, at=(0, 0, 1.3), wall='PlasterWall', third_party=['rough_wood', 'hessian_230'],
                                  views={'game': ((1.6, -4.3, 6.0), (0, -0.15, 1.75), 150), 'close': ((0.5, -1.0, 1.95), (0, -0.14, 1.72), 42), 'head': ((0.3, -0.62, 2.1), (0, -0.28, 1.97), 60),
                                         'int': ((0.6, -1.1, 1.9), (0, -0.17, 1.8), 50)}, int_light=(0.35, -0.75, 2.45)),
    'SM_Prop_Brazier_Standing_01': dict(fn=brazier, mats=brazier_mats, px=2048, cls='prop', slots=[('MI_Prop_Brazier_Standing_01', 'opaque', None)], emissive=True, emis_nits=120.0,
                                        extrude=0.007, maxdist=0.025,
                                        views={'game': ((1.5, -4.1, 6.0), (0, 0, 0.5), 120), 'close': ((0.75, -0.95, 1.45), (0, 0, 0.78), 35), 'int': ((0.7, -1.0, 1.4), (0, 0, 0.75), 35)}, int_light=(0.25, -0.5, 1.6), int_watts=22.0),
    'SM_Prop_Candle_Holder_01': dict(fn=candle, mats=candle_mats, px=1024, cls='prop_small', slots=[('MI_Prop_Candle_Holder_01', 'opaque', None), ('MI_Prop_Candle_Holder_01_Wax', 'subsurface', ['wax'])],
                                     extrude=0.004, maxdist=0.015, params={'sss_radius': (0.012, 0.007, 0.004)},
                                     views={'game': ((1.4, -4.2, 6.0), (0, 0, 0.2), 260), 'close': ((0.45, -0.85, 0.62), (0, 0, 0.24), 45), 'int': ((0.45, -0.85, 0.62), (0, 0, 0.24), 45)}, int_light=(0.003, 0.0, 0.5), int_watts=4.0),
    'SM_Barrel_Oak_PR': dict(fn=barrel, mats=barrel_mats, px=2048, cls='prop', slots=[('MI_Barrel_Oak', 'opaque', None)], extrude=0.006, maxdist=0.02, third_party=['rough_wood'], sharp=35.0,
                             views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.45), 110), 'close': ((0.7, -1.15, 1.25), (0, 0, 0.55), 35), 'int': ((0.7, -1.15, 1.25), (0, 0, 0.55), 35)}, int_light=(0.9, -0.6, 1.2), int_watts=30.0),
    'SM_Prop_Lantern_Hanging_01': dict(fn=lantern, mats=lantern_mats, px=1024, cls='prop', slots=[('MI_Prop_Lantern_Hanging_01', 'opaque', None), ('MI_Prop_Lantern_Hanging_01_Horn', 'translucent', ['horn'])],
                                       emissive=True, emis_nits=60.0, extrude=0.004, maxdist=0.012, at=(0, 0, 2.0), params={'transmission': 0.6, 'ior': 1.5, 'thin': True},
                                       views={'game': ((1.5, -4.1, 6.0), (0, 0, 1.4), 150), 'close': ((0.5, -0.9, 1.55), (0, 0, 1.38), 42), 'int': ((0.5, -0.9, 1.55), (0, 0, 1.38), 42)}, int_light=(0.0, 0.0, 1.335), int_watts=3.0),
}


def build(name, A):
    hm = A['mats'](); order = list(hm.keys())
    bh = MB(seed=A.get('seed', 3), hi=True, mi={k: i for i, k in enumerate(order)}); info = A['fn'](bh); bh.pose(A.get('bake_pose'))
    hi = bh.obj(name + '_HI', [hm[k] for k in order], sharp=35.0, merge=0.0)
    slotof = {}
    for i, (mn, kind, keys) in enumerate(A['slots']):
        for k in (keys or []):
            slotof[k] = i
    for k in order:
        slotof.setdefault(k, 0)
    bl = MB(seed=A.get('seed', 3), hi=False, mi=slotof); A['fn'](bl); bl.pose(A.get('bake_pose'))
    gm = [game_material(mn, name, kind) for (mn, kind, keys) in A['slots']]
    lo = bl.obj(name + '_LOD0', gm, sharp=A.get('sharp', 42.0))
    return hi, lo, gm, info or {}


def main():
    names = [a for a in ARGV if a in ASSETS]
    rdir = opt('--review'); views = (opt('--views') or 'game,close,int,open').split(',')
    for name in names:
        A = ASSETS[name]
        bpy.ops.wm.read_factory_settings(use_empty=True); CH.clear()
        sc = bpy.context.scene; sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
        short = name[3:-3] if name.endswith('_PR') else name[3:]
        outdir = os.path.join(PROPS, short)
        hi, lo, gm, info = build(name, A)
        lods = finish_lo(lo)
        print('BUILT', name, 'hi tris', tris(hi), 'lo tris', [tris(o) for o in lods]); sys.stdout.flush()
        tname = 'T_' + name[3:]
        if '--nobake' in ARGV:
            files = {k: os.path.join(outdir, '%s_%s.png' % (tname, k)) for k in ('BC', 'N', 'ORM', 'E') if os.path.exists(os.path.join(outdir, '%s_%s.png' % (tname, k)))}; stats = {}
        else:
            files, stats = bake(name, [hi], lo, int(os.environ.get('PX', A['px'])), outdir, extrude=A.get('extrude', 0.006), maxdist=A.get('maxdist', 0.02), emissive=A.get('emissive', False), spp=A.get('spp'))
        for m, (mn, kind, keys) in zip(gm, A['slots']):
            wire_game_material(m, files, A.get('emis_nits', 0.0) * 0.02 if A.get('emissive') else 0.0, A.get('params'))
        hi.hide_render = True; hi.hide_viewport = True
        outs = {name: lods}
        for vname in A.get('variants', {}):                 # extra assets on the same texture set: the bake pose, kept
            vl = []
            for i, o in enumerate(lods):
                c = o.copy(); c.data = o.data.copy(); c.name = '%s_LOD%d' % (vname, i); c.data.name = c.name; bpy.context.scene.collection.objects.link(c); c.hide_render = True; vl.append(c)
            outs[vname] = vl
        if A.get('bake_pose'):                              # the named asset itself goes back to its rest pose
            inv = {g: np.linalg.inv(np.array(M)) for g, M in A['bake_pose'].items()}
            for o in lods:
                pose_object(o, inv)

        def bnd(o):
            V = np.array([v.co[:] for v in o.data.vertices]); a, b_ = V.min(0), V.max(0)
            return {'bounds_min_m': [round(float(x), 3) for x in a], 'bounds_max_m': [round(float(x), 3) for x in b_], 'dimensions_m': [round(float(x), 3) for x in (b_ - a)]}
        V = np.array([v.co[:] for v in lo.data.vertices]); mn_, mx_ = V.min(0), V.max(0)
        rec = {'name': name, 'class': A['cls'], 'px': A['px'], 'slots': [{'material': mn, 'kind': kind} for (mn, kind, keys) in A['slots']],
               'textures': {k: os.path.basename(v) for k, v in files.items()}, 'lod_triangles': [tris(o) for o in lods], 'hi_triangles': tris(hi),
               'bounds_min_m': [round(float(x), 3) for x in mn_], 'bounds_max_m': [round(float(x), 3) for x in mx_], 'dimensions_m': [round(float(x), 3) for x in (mx_ - mn_)],
               'emissive_nits': A.get('emis_nits') if A.get('emissive') else None, 'params': A.get('params'), 'stats': stats, 'info': info, 'third_party': A.get('third_party', []),
               'variants': {vn: dict(bnd(vl[0]), meta=A['variants'][vn]) for vn, vl in outs.items() if vn != name}, 'meta': A.get('meta'), 'extra': A.get('extra')}
        if stats:
            json.dump(rec, open(os.path.join(BK, name + '.json'), 'w'), indent=1)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BK, name + '.blend'), compress=True)
        if rdir:
            R = review_setup(floor=A.get('floor', 'PlankFloor'), wall=A.get('wall'))
            lo.location = A.get('at', (0, 0, 0))
            for vn in views:
                if vn not in A['views']:
                    continue
                loc, tgt, lens = A['views'][vn]
                for on, ol in outs.items():                 # views named open* show the variant, the others the asset itself
                    ol[0].hide_render = (on == name) == vn.startswith('open'); ol[0].location = A.get('at', (0, 0, 0))
                review_shot(R, os.path.join(PROPS, 'review', rdir, '%s_%s.png' % (short, vn)), loc, tgt, lens, res=(900, 680) if vn != 'game' else (760, 570), spp=96,
                            interior=A.get('int_light') if vn == 'int' else None, watts=A.get('int_watts', 25.0))
            for ol in outs.values():
                ol[0].location = (0, 0, 0); ol[0].hide_render = False
    print('BAKE DONE', names)


for _f in sorted(os.listdir(_H)):                       # more generators: tools/props_gen_*.py, each adds to ASSETS
    if _f.startswith('props_gen_') and _f.endswith('.py'):
        exec(open(os.path.join(_H, _f)).read())
main()
