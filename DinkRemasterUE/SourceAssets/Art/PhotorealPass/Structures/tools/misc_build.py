"""Photoreal exterior families, part 2: rope-and-plank bridge kit (58), stone bridge (186), plank doors (61, 62), sign posts (186),
island huts, lattice fence and torch pole (424), two-storey and L-shaped thatched cottages and chimney stacks (63).
    DINK_PP=<PhotorealPass> blender -b -t 4 --python misc_build.py [-- name-filter ...]
Built with the Stonebrook generators (stonebrook_build.py, read-only) and kitlib; output Structures/Misc/."""
import os, sys
_T = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stonebrook_build.py')
_s = open(_T).read()
exec(_s[:_s.index('\ndef sb_modules(rows):')])
OUT = os.path.join(os.environ['DINK_PP'], 'Structures', 'Misc')
os.makedirs(OUT, exist_ok=True)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
T_ASH = 3.3


def RY(c, ang):
    """4x4: rotation by ang about the Y axis through point c"""
    return np.array(Matrix.Translation(c) @ Matrix.Rotation(ang, 4, 'Y') @ Matrix.Translation([-c[0], -c[1], -c[2]]))


# ---------------------------------------------------------------- composing whole sub-buildings
def sub_colours(sub):
    V = np.array(sub.V, float)
    if sub.floor0:
        V[:, 2] = np.maximum(V[:, 2], 0.0)
    me = bpy.data.meshes.new('tmp'); me.from_pydata([tuple(v) for v in V], [], sub.F); me.update()
    N = np.zeros(len(V) * 3, np.float32); me.vertices.foreach_get('normal', N); N = N.reshape(-1, 3).astype(float); bpy.data.meshes.remove(me)
    col = np.concatenate([np.zeros((len(V), 3)), np.ones((len(V), 1))], 1); tags = np.array(sub.VT)
    for fn in sub.paint:
        col = fn(V, tags, N, col)
    return V, col


def compose(m, sub, M):
    """append a populated (not built) module to m under the 4x4 M; it keeps the vertex colours it would have had on its own"""
    V, col = sub_colours(sub)
    base = len(m.V); M = np.array(M, float)
    tf = lambda P: (np.c_[np.asarray(P, float), np.ones(len(P))] @ M.T)[:, :3]
    m.V.extend(tf(V).tolist()); m.VT.extend(sub.VT)
    fs = list(sub.FS) + [False] * (len(sub.F) - len(sub.FS))
    for f, fm, uv, s_ in zip(sub.F, sub.FM, sub.UV, fs):
        m.F.append([base + i for i in f]); m.FM.append(fm); m.UV.append(uv); m.FS.append(s_)
    m.pre.append((base, col))
    for (lo, hi) in sub.ucx:
        m.hulls.append(tf([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]).tolist())
    for h in sub.hulls:
        m.hulls.append(tf(h).tolist())


def pre_paint(m):
    def f(P, tags, N, col):
        for base, c in m.pre:
            col[base:base + len(c)] = c
        return col
    return f


# ---------------------------------------------------------------- generic weathering for the small pieces
def misc_paint(m, kind):
    seed = int(m.rng.integers(1e6))

    def f(P, tags, N, col):
        z = P[:, 2]; zb = getattr(m, 'zbase', 0.0); zz = z - zb
        n = vnoise(P, seed, 1.3); n2 = vnoise(P, seed + 3, 6.0); n3 = vnoise(P, seed + 9, 0.55)
        R = np.zeros(len(P)); G = np.zeros(len(P)); B = np.zeros(len(P)); A = np.ones(len(P))
        up = np.clip(N[:, 2], 0, 1); north = np.clip(N[:, 1], 0, 1); under = N[:, 2] < -0.3
        st = streaks(P, seed + 5, 6.0, 0)
        stone = (tags == TAG_SHEET) | (tags == TAG_STONE)
        if kind == 'bridge_stone':
            # an old river bridge: black damp under the arches and at the water line, run-off streaks under the string course,
            # heavy moss on the deck between the wheel lines, in the kerb foot and down the north face, lichen on the merlons
            wet = np.clip((-1.2 - z) / 0.9, 0, 1)
            Rs = np.clip(0.3 + 0.3 * n + 0.25 * n3 + 0.75 * wet + 0.6 * under + 0.45 * st * np.clip((z + 1.6) / 1.4, 0, 1) * (z < -0.25) + 0.3 * (up > 0.5) * (0.4 + n2), 0, 1)
            track = np.clip(1 - np.abs(np.abs(P[:, 1]) - 0.75) / 0.45, 0, 1) * (up > 0.5) * (z < 0.1)            # worn wheel lines stay bare
            Gs = np.clip((up > 0.5) * (0.85 + 0.6 * n3 + 0.4 * n2 + 0.2 * n) * (1 - 0.75 * track) + 0.6 * north * (0.6 + n3) + 0.75 * np.clip((-0.7 - z) / 1.2, 0, 1) * (0.6 + n) + 0.5 * st * np.clip(n3 + 0.3, 0, 1) * (z < -0.25)
                         + 0.5 * np.clip(1 - np.abs(z - 0.0) / 0.12, 0, 1) * (np.abs(P[:, 1]) > getattr(m, 'kerb_y', 9) - 0.3) + 0.25 * np.clip(n3 + n2 - 0.2, 0, 1), 0, 1)
            Gs = np.where(under, Gs * 0.3, Gs)
            Bs = np.clip(0.15 + 0.25 * n + 0.6 * np.clip(n2 - 0.25, 0, 1) * (z > -0.3) + 0.35 * (z > 0.2) + 0.5 * track, 0, 1)
            R = np.where(stone, Rs, R); G = np.where(stone, Gs, G); B = np.where(stone, Bs, B)
        elif kind == 'chimney':
            top = getattr(m, 'ztop', 1.0)
            soot = np.clip((z - (top - 0.45)) / 0.4, 0, 1)
            Rs = np.clip(0.2 + 0.3 * n + 0.35 * st * np.clip((top - z) / 1.5, 0, 1) + 0.9 * soot + 0.6 * np.clip((0.25 - zz) / 0.25, 0, 1), 0, 1)
            Gs = np.clip(0.75 * north * (0.4 + n3) + 0.5 * (up > 0.5) * (0.3 + n3) * (1 - soot) + 0.3 * np.clip(n2 + n3 - 0.3, 0, 1), 0, 1)
            Bs = np.where(tags == TAG_STONE, np.clip(0.45 + 0.3 * n2, 0, 1), np.clip(0.15 + 0.2 * n, 0, 1)) * (1 - 0.8 * soot)
            R = np.where(stone, Rs, R); G = np.where(stone, Gs, G); B = np.where(stone, Bs, B)
            A = A
        elif kind == 'hut':
            # daub wall: rain splash and damp at the foot, drip streaks under the eaves, limewash chalking where the sun gets at it
            pl = tags == TAG_PLASTER
            Rp = np.clip(0.12 + 0.2 * n + 0.85 * np.clip((0.45 * (1 + 0.5 * n3) - zz) / 0.4, 0, 1) + 0.5 * st * np.clip((zz - 1.0) / 0.8, 0, 1) + 0.25 * np.clip(n2, 0, 1), 0, 1)
            Gp = np.clip(0.8 * np.clip((0.22 * (1 + n3) - zz) / 0.2, 0, 1) + 0.45 * north * np.clip(n3 + 0.2, 0, 1) * (zz < 0.9), 0, 1)
            Bp = np.clip(0.25 + 0.35 * n3 + 0.2 * n2 - 0.4 * north, 0, 1)
            R = np.where(pl, Rp, R); G = np.where(pl, Gp, G); B = np.where(pl, Bp, B)
            R = np.where(stone, np.clip(0.3 + 0.3 * n + 0.5 * np.clip((0.2 - zz) / 0.2, 0, 1), 0, 1), R); G = np.where(stone, np.clip(0.5 * (up > 0.4) * (0.3 + n3), 0, 1), G); B = np.where(stone, 0.35 + 0.25 * n2, B)
            th = (tags == TAG_THATCH) | (tags == TAG_TCREV) | (tags == TAG_THATCH + 40)
            if th.any():
                rad = np.hypot(P[:, 0], P[:, 1]); ang = np.arctan2(P[:, 1], P[:, 0])
                Q = np.stack([np.cos(ang) * 9.0, np.sin(ang) * 9.0, 0 * ang], -1)
                comb = np.clip(0.5 + 0.9 * vnoise(Q, seed + 15, 1.0), 0, 1)
                crev = (tags == TAG_TCREV).astype(float); RE = getattr(m, 'RE', 3.0)
                fringe = np.clip((rad - (RE - 0.35)) / 0.35, 0, 1)
                Rt = np.clip(0.45 + 0.35 * n3 + 0.2 * n + 0.3 * (comb - 0.5) + 0.5 * crev + 0.45 * fringe + 0.6 * (N[:, 2] < 0.1) + 0.3 * north, 0, 1)
                Gt = np.clip(1.3 * np.clip(north - 0.15, 0, 1) * np.clip(0.4 + 0.9 * n3 + 0.4 * n, 0, 1) + (0.6 * crev + 0.12) * np.clip(n3 + 0.5 * n2 + 0.1, 0, 1)
                             + 0.7 * np.clip(1 - rad / 1.1, 0, 1) * np.clip(n + n2 + 0.3, 0, 1) + 0.45 * np.clip(n3 + n - 0.55, 0, 1), 0, 1)
                Bt = np.clip(0.1 + 0.25 * np.clip(n, 0, 1) + 0.2 * (comb - 0.5) + 0.3 * np.clip(n3 - 0.3, 0, 1), 0, 1)
                R = np.where(th, Rt, R); G = np.where(th, Gt, G); B = np.where(th, Bt, B)
        if kind in ('wood', 'bamboo'):
            R = np.where(stone, np.clip(0.3 + 0.3 * n + 0.6 * np.clip((0.1 - zz) / 0.1, 0, 1), 0, 1), R); G = np.where(stone, np.clip(0.7 * up * (0.3 + n3) + 0.6 * np.clip((0.06 - zz) / 0.06, 0, 1), 0, 1), G); B = np.where(stone, np.clip(0.4 + 0.3 * n2, 0, 1), B)
        tim = (tags == TAG_TIMBER) | (tags == TAG_END)
        expo = np.clip(0.3 + 0.35 * n + 0.4 * (N[:, 2] > 0.3) - 0.5 * under, 0, 1)
        dk = np.clip(0.22 + 0.25 * n2 + 0.45 * under + 0.6 * np.clip((0.3 - zz) / 0.3, 0, 1), 0, 1)
        gm = np.clip(0.6 * (N[:, 2] > 0.6) * (0.3 + n3) + 0.7 * np.clip((0.3 - zz) / 0.3, 0, 1) * (0.5 + n), 0, 1)
        if kind == 'bamboo':                           # sun-bleached cane, green algae at the foot and in the lee of the nodes
            expo = np.clip(0.55 + 0.3 * n + 0.3 * n2, 0, 1); dk = np.clip(0.15 + 0.3 * n2 + 0.7 * np.clip((0.25 - zz) / 0.25, 0, 1) + 0.4 * (tags == TAG_END), 0, 1)
            gm = np.clip(0.8 * np.clip((0.3 - zz) / 0.3, 0, 1) * (0.5 + n) + 0.3 * np.clip(n3 + n2 - 0.4, 0, 1), 0, 1)
        if kind == 'wood':                             # tarred and oiled work: little bleaching
            expo = expo * 0.45; dk = np.clip(dk + 0.12, 0, 1)
        if kind == 'hut':                              # poles in the shade of the eaves stay dark
            dk = np.clip(dk + 0.25, 0, 1); expo = expo * 0.5
        R = np.where(tim, dk, R); B = np.where(tim, expo, B); G = np.where(tim, gm, G)
        bone = tags == TAG_BONE
        R = np.where(bone, np.clip(0.25 + 0.3 * n2 + 0.3 * n + 0.6 * np.clip((0.3 - zz) / 0.3, 0, 1) + 0.3 * under, 0, 1), R)
        G = np.where(bone, np.clip(0.7 * np.clip((0.35 - zz) / 0.35, 0, 1) * (0.5 + n) + 0.3 * north * np.clip(n3, 0, 1), 0, 1), G); B = np.where(bone, np.clip(0.4 + 0.4 * n3 + 0.3 * up, 0, 1), B)
        rope = tags == TAG_ROPE
        R = np.where(rope, np.clip(0.88 + 0.12 * n2 + 0.1 * n, 0, 1), R); G = np.where(rope, 0.0, G); B = np.where(rope, np.clip(0.5 + 0.25 * n, 0, 1), B)
        A = np.where(tags == TAG_IRON, 0.5, A); A = np.where(tags == TAG_LEAD, 0.75, A); A = np.where(tags == TAG_GLASS, 0.0, A)
        blk = tags == TAG_GLASS + 30
        A = np.where(blk, 0.5, A); R = np.where(blk, 1.0, R)
        return np.stack([R, G, B, A], -1)
    return f


TAG_BONE = 55


# ---------------------------------------------------------------- rope-and-plank bridge (family 58)
def rope(m, pts, rad=0.02, slot=2, twist=48.0, step=0.02):
    """three-strand laid rope: lobed section twisted along its length"""
    pts = np.asarray(pts, float); out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):                      # resample at 3.5 cm so the lay shows
        k = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * (i + 1) / k for i in range(k)]
    m.tube(out, rad, slot, sides=12, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2), shape=[1.0, 0.93, 0.78, 0.93] * 3, twist=twist)


def whip(m, c, r_loop, turns=4.0, rad=0.011, slot=2, rise=0.075):
    """rope whipping round a post: close round turns"""
    n = int(turns * 10); pts = []
    for i in range(n + 1):
        a = 2 * math.pi * turns * i / n
        pts.append([c[0] + r_loop * math.cos(a), c[1] + r_loop * math.sin(a), c[2] - rise / 2 + rise * i / n + 0.004 * math.sin(a * 3)])
    m.tube(pts, rad, slot, sides=6, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))


def bridge_deck(m, L=2.5, W=1.7):
    """a length of deck: cross planks spiked to two round stringers. Walking surface at z = +0.05; stringers hang below"""
    r = m.rng; m.zbase = -0.3
    for sy in (-1, 1):
        y = sy * (W / 2 - 0.3)
        pts = [[x, y + r.normal(0, 0.006), -0.105 + r.normal(0, 0.005)] for x in np.linspace(-L / 2, L / 2, 6)]
        m.tube(pts, [0.095 * (1 + r.normal(0, 0.03)) for _ in pts], SO, sides=9, tag=TAG_TIMBER, rough=0.04, smooth=True)
    x = -L / 2; k = 0
    while x < L / 2 - 1e-6:
        pw = min(float(r.uniform(0.15, 0.24)), L / 2 - x)
        if L / 2 - (x + pw) < 0.1:
            pw = L / 2 - x
        gap = float(r.uniform(0.004, 0.013)); dz = abs(r.normal(0, 0.004)); th = float(r.uniform(0.04, 0.052))
        ya, yb = -W / 2 + r.normal(0, 0.022), W / 2 + r.normal(0, 0.022)
        if k == 4:                                             # one plank broken short, its end rotted away
            yb = W / 2 - 0.34
        n0 = len(m.V)
        timber(m, [x + gap / 2, ya, 0.0], [x + pw - gap / 2, yb, th], 0.007, 0.004, segs=6)
        m.xform_since(n0, np.array(Matrix.Translation((0, 0, dz)) @ Matrix.Rotation(float(r.normal(0, 0.006)), 4, 'Z') @ Matrix.Rotation(float(r.normal(0, 0.012)), 4, 'Y')))
        for sy in (-1, 1):                                     # forged spike heads over each stringer
            if not (k == 4 and sy > 0):
                yy = sy * (W / 2 - 0.3) + r.normal(0, 0.012)
                for dx in ((0.5,) if pw < 0.19 else (0.3, 0.72)):
                    m.tube([[x + pw * dx, yy, th + dz - 0.004], [x + pw * dx, yy, th + dz + 0.004]], [0.0075, 0.005], SO, sides=6, tag=TAG_IRON, smooth=True)
        x += pw; k += 1
    m.ucx = [([-L / 2, -W / 2, -0.2], [L / 2, W / 2, 0.05])]


def rope_post(m, x=0.0, y=0.0, L=2.5, h=1.28):
    """a rail post with its two foot struts, and the hand rope from mid-span to mid-span swagged over the post head"""
    r = m.rng
    lean = post(m, x, y, h, rad=0.058)
    m.tube([[x, y, -0.3], [x, y, 0.0]], 0.06, SO, sides=7, tag=TAG_TIMBER, smooth=False)          # it runs down past the deck to the stringer
    for sx in (-1, 1):                                         # struts spiked to the post and the deck edge
        m.tube([[x + sx * 0.3, y + r.normal(0, 0.01), 0.03], [x + sx * 0.02, y - 0.03, 0.4]], [0.034, 0.03], SO, sides=6, tag=TAG_TIMBER, smooth=False, rough=0.05)
    zt = h - 0.13; zl = 0.82
    px, py = x + lean[0] * zt, y + lean[1] * zt
    for sx in (-1, 1):
        pts = []
        for i in range(13):
            d = i / 12.0                                       # 0 at mid-span, 1 at the post
            pts.append([x + sx * (L / 2) * (1 - d) + (px - x) * d, y - 0.062 * min(1.0, d * 3) + (py - y) * d, zl + (zt - zl) * d ** 2 + 0.004 * math.sin(i * 2.1)])
        rope(m, pts, 0.021)
    whip(m, [px, py, zt], 0.066, turns=4.5, rad=0.012, rise=0.1)
    m.tube([[px, py - 0.09, zt - 0.02], [px + 0.03, py - 0.1, zt - 0.2]], [0.02, 0.012], 2, sides=5, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))     # the tail of the hitch


def bridge_rail_rope(m, L=2.5):
    rope_post(m, 0.0, 0.0, L); m.zbase = -0.3
    m.ucx = [([-L / 2, -0.08, 0], [L / 2, 0.08, 1.1])]


def bridge_rail_plank(m, L=2.5):
    """the boarded side: upright boards hung on two ledger poles outside the deck edge, the rope rail above"""
    r = m.rng; m.zbase = -0.3
    rope_post(m, 0.0, 0.0, L)
    for zz in (0.08, 0.6):
        pts = [[x_, 0.075 + r.normal(0, 0.004), zz + r.normal(0, 0.006)] for x_ in np.linspace(-L / 2, L / 2, 6)]
        m.tube(pts, 0.032, SO, sides=6, tag=TAG_TIMBER, rough=0.04, smooth=True)
    x = -L / 2
    while x < L / 2 - 1e-6:
        pw = min(float(r.uniform(0.13, 0.21)), L / 2 - x)
        if L / 2 - (x + pw) < 0.09:
            pw = L / 2 - x
        n0 = len(m.V)
        z0 = -0.2 + r.normal(0, 0.03); z1 = 0.76 + r.normal(0, 0.035)
        timber(m, [x + 0.004, 0.105, z0], [x + pw - 0.004, 0.132, z1], 0.006, 0.004, segs=5)
        m.xform_since(n0, RY([x + pw / 2, 0.12, 0.3], float(r.normal(0, 0.012))))
        for zz in (0.08, 0.6):
            m.tube([[x + pw / 2, 0.128, zz + r.normal(0, 0.008)], [x + pw / 2, 0.138, zz]], [0.007, 0.005], SO, sides=6, tag=TAG_IRON, smooth=True)
        x += pw
    m.ucx = [([-L / 2, -0.08, 0], [L / 2, 0.14, 1.1])]


# ---------------------------------------------------------------- stone bridge (family 186 frames 4-6)
def stone_bridge(m, L=8.0, W=4.4, narches=2):
    r = m.rng; hy = W / 2; zb = -2.5; zs = -1.95; rise = 1.3; wt = 0.5; m.zbase = zb; m.kerb_y = hy - 0.42
    pw = 0.6; span = (L - (narches + 1) * pw) / narches
    arches = [(-L / 2 + pw + k * (span + pw), -L / 2 + pw + k * (span + pw) + span) for k in range(narches)]

    def soffit(x):
        for (a, b) in arches:
            if a < x < b:
                c = (a + b) / 2; hw = (b - a) / 2
                return zs + rise * math.sqrt(max(0.0, 1 - ((x - c) / hw) ** 2)) ** 0.9
        return zb
    xs = [-L / 2]
    for (a, b) in arches:
        xs += list(np.linspace(xs[-1], a, max(2, int((a - xs[-1]) / 0.3) + 1)))[1:] + list(np.linspace(a + 0.002, b - 0.002, 19)) + [b]
    xs += list(np.linspace(xs[-1], L / 2, max(2, int((L / 2 - xs[-1]) / 0.3) + 1)))[1:]
    xs = np.array(xs); C = len(xs); nz = 8; ztop = -0.04
    for sy in (-1, 1):                                         # spandrel walls, their undersides following the arch
        top = np.zeros((nz + 1, C, 3)); under = np.zeros_like(top)
        for c, x in enumerate(xs):
            z0 = soffit(x)
            for j in range(nz + 1):
                z = z0 + (ztop - z0) * j / nz
                rel = 0.0 if (j in (0, nz) or c in (0, C - 1)) else 0.022 * vnoise(np.array([[x, sy * 7.0, z]]), 31, 2.2)[0] + 0.012 * vnoise(np.array([[x, sy * 7.0, z]]), 32, 6.0)[0]
                batter = 0.05 * (ztop - z) / 2.4               # the faces lean in a little toward the top
                top[j, c] = [x, sy * (hy + batter + rel), z]; under[j, c] = [x, sy * (hy - wt), z]
        m.hgrid(top, under, 0, T_ASH, tag=TAG_SHEET, up=(0, sy, 0), smooth=True, grid_under=True)
    ny = 6; top = np.zeros((ny + 1, C, 3)); under = np.zeros_like(top)      # piers, arch barrels and the fill, one solid between the walls
    for c, x in enumerate(xs):
        for j in range(ny + 1):
            y = -(hy - wt) + 2 * (hy - wt) * j / ny
            top[j, c] = [x, y, soffit(x) + (0.015 * vnoise(np.array([[x, y, 0.0]]), 33, 3.0)[0] if soffit(x) > zb else 0.0)]; under[j, c] = [x, y, ztop]
    m.hgrid(top, under, 0, T_ASH, tag=TAG_SHEET, up=(0, 0, -1), smooth=True, grid_under=True)
    for (a, b) in arches:                                      # voussoirs: a ring of cut stones round each arch, both faces
        c = (a + b) / 2; hw = (b - a) / 2; nv = 13
        for sy in (-1, 1):
            for k in range(nv):
                t = math.pi * (k + 0.5) / nv
                ex, ez = math.cos(t), math.sin(t) ** 0.9
                px, pz = c + hw * ex, zs + rise * ez
                tx, tz = -hw * math.sin(t), rise * math.cos(t); ang = -math.atan2(tz, tx)
                nx_, nz_ = -tz, tx; nl = math.hypot(nx_, nz_); nx_, nz_ = nx_ / nl, nz_ / nl
                if nz_ < 0:
                    nx_, nz_ = -nx_, -nz_
                dep = float(r.uniform(0.34, 0.46)) if k != nv // 2 else 0.55        # a deeper keystone
                seg = math.hypot(tx, tz) * math.pi / nv
                cx_, cz_ = px + nx_ * (dep / 2 - 0.02), pz + nz_ * (dep / 2 - 0.02)
                y0, y1 = (-hy - 0.05 - abs(r.normal(0, 0.012)), -hy + 0.3) if sy < 0 else (hy - 0.3, hy + 0.05 + abs(r.normal(0, 0.012)))
                m.block([cx_ - seg / 2 + 0.006, y0, cz_ - dep / 2], [cx_ + seg / 2 - 0.006, y1, cz_ + dep / 2], 3, T_BOULDER * 0.5, 0.02, 0.008, tag=TAG_STONE, rot=(0, 0, ang))
    for sy in (-1, 1):                                         # string course under the parapet, kerb course, merlons
        x = -L / 2
        while x < L / 2 - 1e-6:
            l = min(float(r.uniform(0.7, 1.05)), L / 2 - x)
            if L / 2 - (x + l) < 0.3:
                l = L / 2 - x
            ya, yb = (-hy - 0.09, -hy + 0.42) if sy < 0 else (hy - 0.42, hy + 0.09)
            m.block([x + 0.005, ya + r.normal(0, 0.008), -0.26], [x + l - 0.005, yb, -0.03 + r.normal(0, 0.004)], 3, T_BOULDER * 0.5, 0.025, 0.008, tag=TAG_STONE)
            x += l
        x = -L / 2
        while x < L / 2 - 1e-6:
            l = min(float(r.uniform(0.75, 1.0)), L / 2 - x)
            if L / 2 - (x + l) < 0.3:
                l = L / 2 - x
            ya, yb = (-hy - 0.03, -hy + 0.4) if sy < 0 else (hy - 0.4, hy + 0.03)
            m.block([x + 0.005, ya + r.normal(0, 0.008), -0.03], [x + l - 0.005, yb + r.normal(0, 0.008), 0.2 + r.normal(0, 0.006)], 3, T_BOULDER * 0.5, 0.024, 0.008, tag=TAG_STONE)
            x += l
        nm = int(round(L / 0.88)); step = L / nm
        for k in range(nm):
            if k % 2 == 1:
                continue
            xa = -L / 2 + k * step + r.normal(0, 0.012); ya, yb = (-hy - 0.02, -hy + 0.38) if sy < 0 else (hy - 0.38, hy + 0.02)
            if r.uniform() < 0.12:                                 # a merlon knocked off and lying on the deck
                m.block([xa + 0.3, -sy * 0.2 + sy * (hy - 1.3), 0.04], [xa + 0.3 + step * 0.95, -sy * 0.2 + sy * (hy - 1.3) + 0.36, 0.33], 3, T_BOULDER * 0.5, 0.03, 0.012, tag=TAG_STONE, rot=(float(r.uniform(0.3, 1.2)), 0.0, 0.0))
                continue
            m.block([xa, ya + r.normal(0, 0.008), 0.2], [xa + step * float(r.uniform(0.9, 1.0)), yb + r.normal(0, 0.008), 0.5 + r.normal(0, 0.012)], 3, T_BOULDER * 0.5, 0.03, 0.01, tag=TAG_STONE,
                    rot=(float(r.normal(0, 0.02)), 0.0, 0.0))
    yk = hy - 0.4; ncr = 6; cw_ = 2 * yk / ncr                  # deck flags, laid in courses across the road, breaking joint
    for j in range(ncr):
        x = -L / 2 - (0.0 if j % 2 == 0 else 0.45)
        while x < L / 2 - 1e-6:
            l = float(r.uniform(0.7, 1.15)); xa, xb = max(x, -L / 2), min(x + l, L / 2)
            if L / 2 - xb < 0.25:
                xb = L / 2
            if xb - xa > 0.05:
                sink = abs(r.normal(0, 0.007)) + (0.025 if r.uniform() < 0.08 else 0.0)
                m.block([xa + 0.006, -yk + j * cw_ + 0.006, -0.16], [xb - 0.006, -yk + (j + 1) * cw_ - 0.006, 0.0 - sink], 3, T_BOULDER * 0.5, 0.014, 0.004, tag=TAG_STONE,
                        rot=(0.0, float(r.normal(0, 0.006)), float(r.normal(0, 0.006))))
            x = xb if xb >= L / 2 else x + l
    m.block([-L / 2 + 0.02, -yk + 0.01, -0.3], [L / 2 - 0.02, yk - 0.01, -0.05], 3, T_BOULDER * 0.5, 0.0, 0.0, tag=TAG_SHEET)      # bedding under the flags: dark in the joints
    m.ucx = [([-L / 2, -hy, zb], [L / 2, hy, 0.0]), ([-L / 2, -hy, 0.0], [L / 2, -hy + 0.42, 0.5]), ([-L / 2, hy - 0.42, 0.0], [L / 2, hy, 0.5])]


# ---------------------------------------------------------------- plank doors (families 61, 62)
def plank_door(m, w=0.95, h=2.02, wide=False):
    """ledged-and-braced oak door: uneven boards clench-nailed to three ledges with two braces on the back, forged strap hinges
    with spear ends on pintle eyes, a ring latch on a back plate; the wide leaf has a third hinge and a lock"""
    t = 0.04; r = m.rng
    x = 0.0
    while x < w - 1e-6:
        pw = min(float(r.uniform(0.13, 0.21)), w - x)
        if w - (x + pw) < 0.09:
            pw = w - x
        dy = r.normal(0, 0.0022)
        n0 = len(m.V)
        m.block([x + 0.0018, -t / 2 + dy, 0.01 + abs(r.normal(0, 0.009))], [x + pw - 0.0018, t / 2 + dy, h - abs(r.normal(0, 0.004))], 1, T_TIMBER, 0.0045, 0.001, mode='board', board=m.timber_rows[r.integers(len(m.timber_rows))], tag=TAG_TIMBER)
        m.xform_since(n0, RY([x + pw / 2, 0, h / 2], float(r.normal(0, 0.0015))))
        x += pw
    lz = (0.26, h * 0.5, h - 0.26)
    for z in lz:                                               # ledges, chamfered, on the back
        m.block([0.04, t / 2, z - 0.075], [w - 0.04, t / 2 + 0.034, z + 0.075], 1, T_TIMBER, 0.009, 0.0012, mode='board', board=m.timber_rows[r.integers(len(m.timber_rows))], tag=TAG_TIMBER)
    for (za, zc) in ((lz[0], lz[1]), (lz[1], lz[2])):          # braces rising from the hinge side
        bar(m, (0.07, za + 0.085), (w - 0.07, zc - 0.085), 0.12, t / 2, t / 2 + 0.032, slot=1, tag=TAG_TIMBER, tile=T_TIMBER)
    hz = (0.26, h - 0.26) + ((h * 0.5,) if wide else ())
    for z in hz:                                               # strap hinges: tapering strap in three lengths, a spear end, the eye on the pintle
        sl = min(w - 0.2, 0.62 if not wide else 0.95)
        for k in range(3):
            a_, b_ = sl * k / 3, sl * (k + 1) / 3; hw_ = 0.03 - 0.006 * k
            m.block([a_, -t / 2 - 0.008, z - hw_], [b_ + 0.002, -t / 2 + 0.001, z + hw_ - 0.004], 1, T_TIMBER, 0.0025, 0.0006, tag=TAG_IRON)
        m.block([sl, -t / 2 - 0.008, z - 0.034], [sl + 0.05, -t / 2 + 0.001, z + 0.034], 1, T_TIMBER, 0.003, 0.0006, tag=TAG_IRON, rot=(0, 0, math.pi / 4))
        m.tube([[-0.012, -t / 2 - 0.012, z - 0.04], [-0.012, -t / 2 - 0.012, z + 0.04]], 0.015, 1, sides=7, tag=TAG_IRON, smooth=True)
        m.tube([[-0.012, -t / 2 - 0.012, z - 0.075], [-0.012, -t / 2 - 0.012, z - 0.04]], 0.009, 1, sides=6, tag=TAG_IRON, smooth=True)
        for xx in np.linspace(0.06, sl - 0.05, 5 if not wide else 7):                       # rose-head nails along the strap
            m.block([xx - 0.007, -t / 2 - 0.014, z - 0.01], [xx + 0.007, -t / 2 - 0.007, z + 0.004], 1, T_TIMBER, 0.003, 0.0006, tag=TAG_IRON)
    for z in lz:                                               # clenched nail heads through every board into the ledges
        if z in hz:
            continue
        xx = 0.07
        while xx < w - 0.05:
            m.block([xx - 0.006, -t / 2 - 0.005, z - 0.006 + r.normal(0, 0.006)], [xx + 0.006, -t / 2 + 0.001, z + 0.006], 1, T_TIMBER, 0.0025, 0.0006, tag=TAG_IRON)
            xx += float(r.uniform(0.07, 0.1))
    zl = 1.02; xl = w - 0.1                                    # ring latch
    m.block([xl - 0.045, -t / 2 - 0.006, zl - 0.07], [xl + 0.045, -t / 2 + 0.001, zl + 0.07], 1, T_TIMBER, 0.004, 0.0008, tag=TAG_IRON)
    m.tube([[xl, -t / 2 - 0.03, zl + 0.03], [xl, -t / 2, zl + 0.03]], 0.011, 1, sides=6, tag=TAG_IRON, smooth=True)
    ring_ = [[xl + 0.045 * math.sin(2 * math.pi * k / 12), -t / 2 - 0.026 - 0.004 * math.cos(2 * math.pi * k / 12), zl + 0.03 - 0.045 + 0.045 * math.cos(2 * math.pi * k / 12)] for k in range(13)]
    m.tube(ring_, 0.006, 1, sides=5, tag=TAG_IRON, smooth=True)
    if wide:                                                   # box lock and a draw bar on its staples
        m.block([w - 0.24, -t / 2 - 0.03, 1.2], [w - 0.02, -t / 2 + 0.001, 1.36], 1, T_TIMBER, 0.005, 0.001, tag=TAG_IRON)
        m.block([w - 0.15, -t / 2 - 0.034, 1.25], [w - 0.12, -t / 2 - 0.028, 1.3], 1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)
        for xx in (w * 0.36, w * 0.62):
            m.block([xx, -t / 2 - 0.04, 0.72], [xx + 0.022, -t / 2, 0.82], 1, T_TIMBER, 0.004, 0.001, tag=TAG_IRON)
        m.block([w * 0.3, -t / 2 - 0.036, 0.742], [w * 0.92, -t / 2 - 0.008, 0.798], 1, T_TIMBER, 0.006, 0.001, mode='board', board=m.timber_rows[0], tag=TAG_TIMBER)
    V = np.array(m.V); m.V = (V + np.array([-V[:, 0].min() - 0.0, 0.0, -V[:, 2].min()])).tolist()
    m.ucx = [([0, -0.03, 0], [w, 0.04, h])]


# ---------------------------------------------------------------- sign posts (family 186 frames 7-10)
def sign_post(m, boards):
    """hewn oak post with packing stones; each board is two or three riven planks of unequal length (the ragged ends of the sprite)
    nailed across it. boards: (z, half length left, half length right, tilt rad, point direction or 0)"""
    r = m.rng; H = 2.3
    n0 = len(m.V)
    timber(m, [-0.058, -0.058, -0.03], [0.058, 0.058, H], 0.014, 0.009, segs=9)
    V = np.array(m.V); top = V[n0:, 2] > H - 0.2                 # the head weathered to a blunt point
    V[n0:][top, 0] *= 0.55; V[n0:][top, 1] *= 0.55; V[n0:][top, 2] += 0.05; m.V = V.tolist()
    m.xform_since(n0, np.array(Matrix.Rotation(float(r.normal(0, 0.02)), 4, 'Y') @ Matrix.Rotation(float(r.normal(0, 0.02)), 4, 'X')))
    for (z, la, lb, tilt, pt_) in boards:
        np_ = 3 if (la + lb) > 0.9 else 2; ph = 0.3 / np_ if np_ == 3 else 0.115
        n1 = len(m.V)
        for k in range(np_):
            zz = z + (k - (np_ - 1) / 2) * (ph + 0.004)
            xa = -la + float(r.uniform(-0.07, 0.05)); xb = lb + float(r.uniform(-0.05, 0.07))
            if pt_ > 0 and k == np_ // 2:
                xb += 0.1
            if pt_ < 0 and k == np_ // 2:
                xa -= 0.1
            n2_ = len(m.V)
            timber(m, [xa, -0.088 + r.normal(0, 0.002), zz - ph / 2], [xb, -0.06, zz + ph / 2], 0.006, 0.005, segs=5)
            V = np.array(m.V); W_ = V[n2_:]                    # ragged ends: split off along the grain at a slant, one end worse than the other
            for xe, sg in ((xa, -1), (xb, 1)):
                e = np.abs(W_[:, 0] - xe) < 0.02
                sl = float(r.normal(0, 0.22)); k_ = float(r.uniform(0.008, 0.03))
                W_[e, 0] += sg * (-np.abs((W_[e, 2] - zz) * sl) - k_ * np.sin((W_[e, 2] - zz) / ph * 9.0 + sl * 5) ** 2) + sl * (W_[e, 2] - zz) * 0.5
            V[n2_:] = W_; m.V = V.tolist()
            m.xform_since(n2_, RY([0, -0.07, zz], float(r.normal(0, 0.012))))
            for sx in (-0.03, 0.03):
                m.tube([[sx, -0.097, zz + r.normal(0, 0.012)], [sx, -0.085, zz]], [0.008, 0.005], SO, sides=6, tag=TAG_IRON, smooth=True)
        m.xform_since(n1, RY([0, -0.07, z], tilt))
    packing(m, 0.0, 0.0, k=4)
    m.ucx = [([-0.09, -0.09, 0], [0.09, 0.09, H])]


# ---------------------------------------------------------------- chimney stacks (family 63 frames 11-13)
def chimney_stack(m, tall=False):
    r = m.rng
    if tall:                                                   # the gable-end stack: broad breast, two weathered offsets, a narrow flue
        for (w__, d__, za, zc) in ((1.3, 0.75, 0.0, 1.9), (1.05, 0.7, 1.9, 3.3), (0.82, 0.66, 3.3, 4.45)):
            stack(m, 0, 0, w__, d__, za, zc, slot=2, tile=T_BOULDER * 0.5); m.slab(-w__ / 2 + 0.035, w__ / 2 - 0.035, za, zc, -d__ / 2 + 0.035, d__ / 2 - 0.035, SF, T_STONE, relief=0.0)
        for (z, w_) in ((1.9, 1.3), (3.3, 1.05)):
            for sx in (-1, 1):
                m.block([sx * w_ / 2 - 0.16 if sx > 0 else -w_ / 2 - 0.02, -0.39, z - 0.03], [w_ / 2 + 0.02 if sx > 0 else -w_ / 2 + 0.16, 0.39, z + 0.1], 2, T_BOULDER * 0.5, 0.03, 0.008, tag=TAG_STONE, rot=(0, 0, sx * 0.5))
        zt = 4.45; w_, d_ = 0.82, 0.66
    else:
        stack(m, 0, 0, 0.95, 0.8, 0.0, 1.15, slot=2, tile=T_BOULDER * 0.5); m.slab(-0.44, 0.44, 0.0, 1.15, -0.365, 0.365, SF, T_STONE, relief=0.0); zt = 1.15; w_, d_ = 0.95, 0.8
    for sx in (-1, 1):                                         # cap course of two flags
        m.block([-w_ / 2 - 0.07 if sx < 0 else 0.01 + r.normal(0, 0.03), -d_ / 2 - 0.07, zt], [-0.01 if sx < 0 else w_ / 2 + 0.07, d_ / 2 + 0.07, zt + 0.09 + r.normal(0, 0.006)], 2, T_BOULDER * 0.5, 0.02, 0.006, tag=TAG_STONE)
    stack(m, 0, 0, w_ - 0.08, d_ - 0.08, zt + 0.09, zt + 0.28, slot=2, tile=T_BOULDER * 0.5)
    m.block([-w_ / 2 + 0.22, -d_ / 2 + 0.2, zt - 0.3], [w_ / 2 - 0.22, d_ / 2 - 0.2, zt + 0.285], SO, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)
    m.ztop = zt + 0.28
    m.ucx = [([-0.66 if tall else -w_ / 2, -0.4, 0], [0.66 if tall else w_ / 2, 0.4, zt + 0.28])]


# ---------------------------------------------------------------- two-storey and L-shaped cottages (family 63 frames 4, 5, 10)
def _sub(parent, name):
    s = Mod2(name, 1, 1, parent.timber_rows, 'building', 'Structures/Misc'); s.slots = list(parent.slots); s.streak_src = []; s.streak_w = []; s.dormer_box = None
    s.floor0 = True; s.paint.append(sb_paint(s, 'cottage')); return s


def two_storey(m, W=6.6, D=6.0, inset=0.85, M=None):
    """lower storey with a thatched pentice all round, a smaller upper storey rising through it under its own hipped thatch"""
    global thatch_planes, ridge_block
    _tp, _rb = thatch_planes, ridge_block
    M = np.eye(4) if M is None else M
    lower = _sub(m, m.name + '_lower')

    def tp_clip(m_, x0, x1, y0, y1, ze, tp, seed, clip=None, **k):
        S_ = (inset + OVH + 0.4) / math.cos(math.atan(tp))
        return _tp(m_, x0, x1, y0, y1, ze, tp, seed, clip={e: (0.0, 1.0, S_) for e in ('front', 'back', 'left', 'right')}, **k)
    thatch_planes = tp_clip; ridge_block = lambda *a, **k: None
    try:
        cottage(lower, W, D, None, fw=(W * 0.28,), fw2=(), bw=(W * 0.5,), ew=(), patches=((-W * 0.3, -D * 0.52, 0.8, 0.5),))
    finally:
        thatch_planes, ridge_block = _tp, _rb
    lower.hulls = []                                           # its roof hull would be the full pyramid; the upper storey's box replaces it
    compose(m, lower, M)
    U0 = 3.1
    upper = _sub(m, m.name + '_upper')
    cottage(upper, W - 2 * inset, D - 2 * inset, None, fw=(), fw2=(), bw=(), ew=(), patches=((0.8, -1.2, 0.8, 0.6),))
    compose(m, upper, M @ np.array(Matrix.Translation((0, 0, U0))))
    hx, hy = W / 2 + OVH, D / 2 + OVH
    m.hulls.append((np.c_[np.array([[sx * hx, sy * hy, WH - 0.1] for sx in (-1, 1) for sy in (-1, 1)] + [[sx * (hx - 1.5), sy * (hy - 1.5), WH + 1.2] for sx in (-1, 1) for sy in (-1, 1)]), np.ones(8)] @ M.T)[:, :3].tolist())


def l_shape(m):
    two_storey(m, 6.6, 6.0, M=np.array(Matrix.Translation((-1.2, 1.4, 0))))
    wing = _sub(m, m.name + '_wing')
    cottage(wing, 5.6, 4.4, None, fw=(), fw2=(), bw=(), ew=(2.2 - WT_,), patches=((1.0, -1.5, 0.7, 0.6),))
    compose(m, wing, np.array(Matrix.Translation((2.3, -2.6, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z')))


# ---------------------------------------------------------------- island hut, lattice fence, torch pole (family 424)
def cane(m, p0, p1, rad, slot=1, sides=8, bow=0.0):
    """a bamboo cane: straight culm with a swollen ring at every node"""
    r = m.rng; p0 = np.array(p0, float); p1 = np.array(p1, float); L = np.linalg.norm(p1 - p0)
    side = np.cross((p1 - p0) / L, [0.3, 0.2, 1.0]); side /= np.linalg.norm(side)
    ts = [0.0]; rs = [1.0]; s = float(r.uniform(0.1, 0.3))
    while s < L - 0.05:
        ts += [s - 0.012, s, s + 0.012]; rs += [1.0, 1.16, 1.0]; s += float(r.uniform(0.26, 0.4))
    ts.append(L); rs.append(1.0)
    pts = [p0 + (p1 - p0) * (t / L) + side * bow * math.sin(math.pi * t / L) for t in ts]
    radii = [rad * q * (1.05 - 0.15 * t / L) for q, t in zip(rs, ts)]
    m.tube(pts, radii, slot, sides=sides, tag=TAG_TIMBER, smooth=True, rough=0.0)


def island_fence(m, L=4.4):
    r = m.rng; xs = np.linspace(-L / 2, L / 2, 3)
    for x in xs:
        lean = r.normal(0, 0.02, 2)
        cane(m, [x, 0, -0.03], [x + lean[0], lean[1], 1.72 + r.normal(0, 0.05)], 0.036)
    for zz, sy in ((0.42, -1), (1.36, 1)):
        cane(m, [-L / 2 - 0.16, sy * 0.045, zz + r.normal(0, 0.02)], [L / 2 + 0.16, sy * 0.045, zz + r.normal(0, 0.02)], 0.028, bow=0.015)
    for k in range(2):
        xa, xb = xs[k], xs[k + 1]
        cane(m, [xa + 0.05, -0.1, 0.3], [xb - 0.02, -0.1, 1.5], 0.024, bow=0.01)
        cane(m, [xa + 0.03, 0.1, 1.48], [xb - 0.06, 0.1, 0.28], 0.024, bow=-0.01)
        whip(m, [(xa + xb) / 2, 0.0, 0.9], 0.07, turns=3.0, rad=0.007, rise=0.04)
        n0 = len(m.V); whip(m, [(xa + xb) / 2, 0.0, 0.9], 0.07, turns=3.0, rad=0.007, rise=0.04); m.xform_since(n0, np.array(Matrix.Translation(((xa + xb) / 2, 0, 0.9)) @ Matrix.Rotation(1.57, 4, 'Y') @ Matrix.Translation((-(xa + xb) / 2, 0, -0.9))))
    for x in xs:
        for zz in (0.42, 1.36):
            whip(m, [x, 0.0, zz], 0.058, turns=4.0, rad=0.007, rise=0.05)
            n0 = len(m.V); whip(m, [x, 0.0, zz], 0.058, turns=3.0, rad=0.007, rise=0.045); m.xform_since(n0, np.array(Matrix.Translation((x, 0, zz)) @ Matrix.Rotation(1.57, 4, 'X') @ Matrix.Translation((-x, 0, -zz))))
        packing(m, x, 0.0, k=2)
    m.ucx = [([-L / 2 - 0.05, -0.1, 0], [L / 2 + 0.05, 0.1, 1.5])]


def island_torch(m):
    """the three-pronged pole of frame 18: a thick cane split into three tines above a red cloth binding, each tine charred at the tip"""
    r = m.rng; H = 2.6
    cane(m, [0, 0, -0.03], [0.02, 0.01, H - 0.75], 0.046, sides=9)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        base = np.array([0.02, 0.01, H - 0.8]); mid = base + np.array([0.11 * math.cos(a), 0.11 * math.sin(a), 0.3]); tip = base + np.array([0.13 * math.cos(a), 0.13 * math.sin(a), 0.78])
        m.tube([base, base + (mid - base) * 0.5 + np.array([0, 0, 0.02]), mid, tip], [0.024, 0.023, 0.021, 0.016], 1, sides=7, tag=TAG_TIMBER, smooth=True)
        m.tube([tip - np.array([0, 0, 0.05]), tip + np.array([0, 0, 0.012])], 0.0175, 1, sides=7, tag=TAG_GLASS + 30, smooth=True)     # charred tip
    pts = []
    for i in range(46):                                         # the binding: cloth strip wound in nine turns
        a = 2 * math.pi * 9 * i / 45
        pts.append([0.02 + 0.05 * math.cos(a), 0.01 + 0.05 * math.sin(a), H - 0.98 + 0.2 * i / 45])
    m.tube(pts, 0.014, 3, sides=5, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.3))
    packing(m, 0.0, 0.0, k=3)
    m.ucx = [([-0.08, -0.08, 0], [0.08, 0.08, H])]


def hut_storey(m, R=2.6, HW=1.9, door=True, z0=0.0, seed=7, band_seed=3):
    """one round storey: daub wall painted in three colours with a stepped border, whale-rib buttresses, conical thatch"""
    r = m.rng; T_PL = 2.5; nth = 96; nz = 10; wt = 0.24
    dh = math.asin(0.62 / R) if door else 0.0
    th0 = -math.pi / 2 + dh; th1 = 1.5 * math.pi - dh
    ths = np.linspace(th0, th1, nth + 1)
    rb = np.random.default_rng(band_seed); step = []
    while len(step) < nth:
        step += [int(rb.integers(2, 6))] * int(rb.integers(2, 5))
    red = [(int(rb.integers(8, 30)), int(rb.integers(7, 12))), (int(rb.integers(55, 80)), int(rb.integers(6, 11)))]
    hc = nth // 2
    for half in (0, 1):                                        # two half drums, so each has an unambiguous outward side
        cs = list(range(half * hc, half * hc + hc + 1)); C = len(cs)
        top = np.zeros((nz + 1, C, 3)); under = np.zeros_like(top)
        for ci, c in enumerate(cs):
            th = ths[c]
            for j in range(nz + 1):
                z = HW * j / nz; Pn = np.array([[math.cos(th) * R, math.sin(th) * R, z]])
                bulge = 0.05 * math.sin(math.pi * min(1.0, z / HW)) + 0.022 * vnoise(Pn, seed, 1.6)[0] + 0.01 * vnoise(Pn, seed + 1, 5.0)[0]
                ro = R + bulge + 0.22 * (1 - z / HW) ** 1.6
                top[j, ci] = [ro * math.cos(th), ro * math.sin(th), z0 + z]; under[j, ci] = [(R - wt) * math.cos(th), (R - wt) * math.sin(th), z0 + z]
        f0 = len(m.F); tha = ths[cs]

        def uvw(P, tha=tha, C=C):
            idx = np.arange(len(P)); c_ = idx % C; j_ = (idx // C) % (nz + 1)
            return np.stack([tha[c_] * R / T_PL, HW * j_ / nz / T_PL], -1)
        am = ths[cs[C // 2]]
        m.hgrid(top, under, 3, T_PL, tag=TAG_PLASTER, up=(math.cos(am), math.sin(am), 0), uvfn=uvw, smooth=True, grid_under=True)
        for j in range(nz):                                    # paint, per face: blue dado with a stepped top, olive above, ox-blood panels
            for ci in range(C - 1):
                c = cs[ci]; s_ = 0 if j < step[c] else 3
                if s_ == 3 and any(a_ <= c < a_ + w_ for a_, w_ in red) and j < nz - 1:
                    s_ = 4
                m.FM[f0 + j * (C - 1) + ci] = s_
    # wall plate ring of lashed poles, and rib buttresses (weathered whale ribs) bowed out from the foot to the eaves
    ringp = [[(R + 0.05) * math.cos(a), (R + 0.05) * math.sin(a), z0 + HW + 0.03] for a in np.linspace(th0, th1, 40)]
    m.tube(ringp, 0.05, 1, sides=6, tag=TAG_TIMBER, smooth=True, rough=0.03)
    nr = 9
    for k in range(nr):
        a = th0 + (th1 - th0) * (k + 0.5) / nr + r.normal(0, 0.03)
        pts = []; rr = []
        for i in range(8):
            t = i / 7.0
            ro = R + 0.1 + 0.42 * (1 - t) ** 1.5 + 0.12 * math.sin(math.pi * t) ** 1.2
            pts.append([ro * math.cos(a), ro * math.sin(a), z0 - 0.05 + (HW + 0.02) * t]); rr.append(0.062 - 0.03 * t)
        m.tube(pts, rr, 5, sides=7, tag=TAG_BONE, smooth=True, shape=[1.0, 0.82, 0.7, 0.82, 1.0, 0.85, 0.75], tile=1.5, vrange=(0.5, 0.25))
    if door:
        yj = -R * math.cos(dh)
        for sx in (-1, 1):                                     # jamb posts painted ox-blood, with inlaid shell lozenges
            m.block([sx * 0.62 - 0.1, yj - 0.3, z0], [sx * 0.62 + 0.1, yj + 0.2, z0 + 1.7], 4, T_PL, 0.02, 0.006, tag=TAG_PLASTER)
            for k in range(5):
                zz = z0 + 0.28 + k * 0.28
                m.block([sx * 0.62 - 0.045, yj - 0.315, zz - 0.045], [sx * 0.62 + 0.045, yj - 0.295, zz + 0.045], 5, 1.5, 0.006, 0.002, tag=TAG_BONE, rot=(0, 0, math.pi / 4))
        timber(m, [-0.8, yj - 0.24, z0 + 1.7], [0.8, yj + 0.2, z0 + 1.84], 0.02, 0.006)
        m.block([-0.54, yj + 0.0, z0], [0.54, yj + 0.5, z0 + 1.72], 1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)                       # the dark inside
        m.block([-0.75, yj - 0.62, z0 - 0.03], [0.75, yj + 0.2, z0 + 0.07], 1, T_TIMBER, 0.02, 0.006, mode='board', board=m.timber_rows[0], tag=TAG_TIMBER)             # oak sill
        for sx in (-1, 1):                                     # the crossed tusks of the porch
            pts = []; rr = []
            for i in range(10):
                t = i / 9.0
                pts.append([sx * (1.12 - 1.5 * t ** 1.5), -(R + 0.45 + 0.3) + 0.85 * t ** 1.3 - sx * 0.06 * t, z0 - 0.05 + 2.72 * t ** 0.8]); rr.append(0.11 - 0.09 * t ** 1.2)
            m.tube(pts, rr, 5, sides=8, tag=TAG_BONE, smooth=True, tile=1.5, vrange=(0.5, 0.25))
    # thatch: twelve sectors of a domed cone, shaggy eaves, cane ties over the joints, rope rings, a finial
    RE = R + 0.45; zE = z0 + HW - 0.06; zA = z0 + HW + 2.15; nsec = 12; m.RE = RE
    prof = lambda q: zA - (zA - zE) * (q / RE) ** 1.55
    rows = [(RE + 0.02, -0.3, 1), (RE + 0.05, -0.12, 0), (RE - 0.03, 0.0, 0)]
    q = RE - 0.42; i = 0
    while q > 0.5:
        rows += [(q, 0.0, 1), (q, 0.06, 0)]; q -= 0.42 - 0.012 * i; i += 1
    rows.append((0.12, 0.04, 0))
    for s in range(nsec):
        a0, a1 = 2 * math.pi * s / nsec, 2 * math.pi * (s + 1) / nsec; nA = 7
        topg = np.zeros((len(rows), nA + 1, 3)); und = np.zeros_like(topg); tg = np.zeros((len(rows), nA + 1), int)
        for ri, (q, hb, crev) in enumerate(rows):
            for c in range(nA + 1):
                a = a0 + (a1 - a0) * c / nA; Pn = np.array([[q * math.cos(a), q * math.sin(a), 0.0]])
                qq = q; h = hb
                if ri < 3:                                     # ragged fringe: every bundle ends where it likes
                    qq += 0.09 * vnoise(Pn * 4.0, seed + 20, 1.0)[0] + 0.04 * vnoise(Pn * 11.0, seed + 21, 1.0)[0]
                    h += 0.06 * vnoise(Pn * 6.0, seed + 22, 1.0)[0]
                elif ri < len(rows) - 1:
                    qq += 0.05 * vnoise(Pn * 3.0, seed + 23 + ri // 2, 1.0)[0]
                    if hb > 0:
                        h = 0.055 + 0.02 * vnoise(Pn * 2.0, seed + 30 + ri, 1.0)[0]
                h += 0.05 * vnoise(Pn, seed + 2, 0.9)[0] + 0.022 * vnoise(Pn, seed + 3, 2.6)[0]
                topg[ri, c] = [qq * math.cos(a), qq * math.sin(a), prof(min(qq, RE)) + h]
                qu = min(qq, RE - 0.2 - 0.02 * ri) if ri < 3 else qq
                und[ri, c] = [qu * math.cos(a), qu * math.sin(a), prof(min(qu, RE)) - 0.3]
                tg[ri, c] = TAG_TCREV if crev else TAG_THATCH
        am = (a0 + a1) / 2; uo = r.uniform(0, 1, 2)

        def uvface(Pf, am=am, uo=uo):
            out = []
            for q_ in Pf:
                rad = math.hypot(q_[0], q_[1]); a = math.atan2(q_[1], q_[0]) - am
                a = (a + math.pi) % (2 * math.pi) - math.pi
                out.append((a * max(rad, 0.5) / T_THATCH + uo[0], -rad * 1.2 / T_THATCH + uo[1]))
            return out
        nv0 = len(m.V)
        m.hgrid(topg, und, 2, T_THATCH, tag=TAG_THATCH, up=(math.cos(am) * 0.5, math.sin(am) * 0.5, 0.85), uvface=uvface, smooth=True)
        m.VT[nv0:nv0 + topg.shape[0] * topg.shape[1]] = tg.reshape(-1).tolist()
        pts = [[q * math.cos(a0), q * math.sin(a0), prof(q) + 0.065 + 0.012 * math.sin(q * 5 + s)] for q in np.linspace(RE - 0.12, 0.25, 12)]
        m.tube(pts, [0.03] * 11 + [0.022], 1, sides=6, tag=TAG_TIMBER, smooth=True, rough=0.04)
    for q in (RE - 0.55, RE * 0.52, 0.85):                     # rope rings holding the ties down
        pts = [[q * math.cos(a) * (1 + 0.01 * math.sin(a * 7)), q * math.sin(a), prof(q) + 0.105 + 0.01 * math.sin(a * 5)] for a in np.linspace(0, 2 * math.pi, 49)]
        m.tube(pts, 0.02, 1, sides=6, tag=TAG_TIMBER, smooth=True, rough=0.03)
    m.tube([[0, 0, zA - 0.3], [0.01, 0, zA + 0.2], [0.02, 0.01, zA + 0.55]], [0.085, 0.07, 0.05], 1, sides=8, tag=TAG_TIMBER, smooth=True, rough=0.04)
    pts = [[0.012 + 0.1 * math.cos(a), 0.1 * math.sin(a), zA + 0.08 + 0.1 * a / 25.0] for a in np.linspace(0, 25.0, 60)]
    m.tube(pts, 0.016, 1, sides=5, tag=TAG_TIMBER, smooth=True)
    return zA


def island_hut(m, two=False):
    r = m.rng
    if two:
        hut_storey(m, 3.0, 1.9, True, 0.0, seed=11, band_seed=5)
        # the upper drum stands inside the lower roof, which is cut by it: the lower cone above 3.1 m is hidden inside the drum
        hut_storey(m, 2.2, 1.6, False, 2.55, seed=12, band_seed=6)
        m.ucx = [([-2.2, -2.2, 0], [2.2, 2.2, 5.9])]
        m.hulls = [[[3.0 * math.cos(a), 3.0 * math.sin(a), z] for a in np.linspace(0, 2 * math.pi, 13)[:-1] for z in (0.0, 1.9)]]
    else:
        hut_storey(m, 2.6, 1.9, True, 0.0)
        m.hulls = [[[2.65 * math.cos(a), 2.65 * math.sin(a), z] for a in np.linspace(0, 2 * math.pi, 13)[:-1] for z in (0.0, 1.9)],
                   [[3.2 * math.cos(a), 3.2 * math.sin(a), 1.75] for a in np.linspace(0, 2 * math.pi, 13)[:-1]] + [[0, 0, 4.1]]]
    # trodden earth ring at the foot
    Rr = 3.0 if two else 2.6
    n = 40; top = np.zeros((n + 1, 4, 3)); und = np.zeros_like(top)
    for i in range(n + 1):
        a = 2 * math.pi * i / n; wd = 0.55 + 0.18 * math.sin(a * 3 + 1) + (1.3 * max(0.0, -math.sin(a)) ** 6)
        for j, (f, z) in enumerate(((-0.3, 0.04), (0.3, 0.035), (0.7, 0.02), (1.0, 0.004))):
            q = Rr + (wd * f if f > 0 else -0.3)
            top[i, j] = [q * math.cos(a), q * math.sin(a), z]; und[i, j] = [q * math.cos(a), q * math.sin(a), 0.0]
    n0 = len(m.V)
    m.hgrid(top, und, 8, 4.0, tag=TAG_EARTH, up=(0, 0, 1), smooth=True, grid_under=True)
    tg = np.zeros((n + 1, 4), int); tg[:, :] = TAG_EARTH; tg[:, 3] = TAG_EARTH + 1; tg[:, 2] = TAG_EARTH + 2
    m.VT[n0:n0 + (n + 1) * 4] = tg.reshape(-1).tolist()


def earth_paint(m):
    seed = 77

    def f(P, tags, N, col):
        ea = (tags >= TAG_EARTH) & (tags <= TAG_EARTH + 2)
        if ea.any():
            n = vnoise(P, seed, 1.3); n2 = vnoise(P, seed + 3, 6.0); n3 = vnoise(P, seed + 9, 0.55)
            edge = (tags == TAG_EARTH + 1).astype(float); mid = (tags == TAG_EARTH + 2).astype(float)
            col[:, 0] = np.where(ea, np.clip(0.55 - 0.35 * edge - 0.15 * mid + 0.3 * n + 0.2 * n2, 0, 1), col[:, 0])
            col[:, 1] = np.where(ea, np.clip(0.55 * edge * np.clip(0.5 + n + n2, 0, 1) + 0.3 * mid * np.clip(n + n2 + 0.3, 0, 1) + 0.2 * np.clip(n2, 0, 1), 0, 1), col[:, 1])
            col[:, 2] = np.where(ea, np.clip(0.25 + 0.3 * n3 - 0.3 * edge, 0, 1), col[:, 2])
        return col
    return f


# ---------------------------------------------------------------- modules
def misc_modules(rows):
    out = []

    def want(name):
        return not ARGS or any(a in name for a in ARGS)

    def mk(name, L, H, cls, slots, kind, sb=False):
        m = Mod2(name, L, H, rows, cls, 'Structures/Misc'); m.slots = list(slots); m.streak_src = []; m.streak_w = []; m.dormer_box = None; m.pre = []
        m.floor0 = False; m.paint.append(sb_paint(m, kind) if sb else misc_paint(m, kind)); return m

    def rec(m, fams, sup, note, **k):
        used = sorted(set(m.FM)); m.FM = [used.index(i) for i in m.FM]; m.slots = [m.slots[i] for i in used]
        out.append(dict(m=m, families=fams, supersedes=sup, dresses=note, **k))
    FEN = ('fieldstone', 'oakdark', 'rope')
    if want('Bridge_Wood'):
        m = mk('SM_Bridge_Wood_Deck_PR', 2.5, 0.3, 'kit_piece', FEN, 'wood'); bridge_deck(m)
        rec(m, ['58 struct/bridge/brdge- frames 1-3, 5', 'bridge_wood_deck'], 'none (family 58 was placeholder)',
            '2.5 m length of plank bridge deck, 1.7 m wide: thirteen riven cross planks of uneven width and thickness, one broken short, spiked with forged nails to two round stringers',
            fit={'pivot': 'centre of the deck at walking level: plank tops are at z = +0.04 to +0.06 m, the stringers hang to z = -0.2 m (over water or a ditch they show; on a bank they are buried)', 'run': 'along X; butt modules end to end every 2.5 m; yaw for the n-s and diagonal frames',
                 'sprite_scale': 'frames 1-3 are 65 px (1.6 m) wide'})
        m = mk('SM_Bridge_Wood_Rail_Rope_PR', 2.5, 1.3, 'prop', FEN, 'wood'); bridge_rail_rope(m)
        rec(m, ['58 struct/bridge/brdge- frames 4, 7, 9, 11', 'bridge_wood_rail_rope'], 'none',
            '2.5 m of rope hand rail: one cleft post 1.28 m with two foot struts, a three-strand rope swagged over its head and hitched, hanging to 0.82 m at both module ends',
            fit={'pivot': 'foot of the post at deck level; the rope ends at x = -1.25 and +1.25 at z = 0.82 with a level tangent, so consecutive modules join in mid-span', 'place': 'stand it on the deck edge, y = +-0.8 m from the deck centre line'})
        m = mk('SM_Bridge_Wood_Rail_Plank_PR', 2.5, 1.3, 'prop', FEN, 'wood'); bridge_rail_plank(m)
        rec(m, ['58 struct/bridge/brdge- frames 6, 8, 10', 'bridge_wood_rail_plank'], 'none',
            'the boarded side of the bridge: fourteen upright boards hung on two ledger poles from below deck level to 0.76 m, with the same post and rope rail above',
            fit={'pivot': 'as SM_Bridge_Wood_Rail_Rope_PR; the boards hang on the +Y side of the post line (outside the deck)'})
    if want('Bridge_Stone'):
        m = mk('SM_Bridge_Stone_PR', 8.0, 3.0, 'prop_large', ('ashlar', 'oak', 'rope', 'boulder'), 'bridge_stone'); stone_bridge(m)
        rec(m, ['186 struct/landmark/landm- frames 4-6', 'bridge_stone'], 'none (bridge_stone was placeholder)',
            'two-arch stone river bridge, 8.0 x 4.4 m: battered spandrel walls, rings of thirteen cut voussoirs with a deeper keystone, a projecting string course, kerb stones carrying square merlons (the toothed edge of the sprite; one fallen onto the deck), a roadway of some fifty individually laid flags, mossed between the wheel lines',
            fit={'pivot': 'centre of the roadway at walking level (flag tops at z = 0 to -0.03); the structure goes down to z = -2.5 m: set it across a river bed about 2 m below the banks, or sink the lower part in water', 'run': 'along X; roadway 3.6 m between kerbs',
                 'frames': 'frame 4 (437 px) is the long three-arch view, frames 5-6 the short one; this is one mesh of two arches; build stone_bridge(L=12, narches=3) for a three-arch variant'})
    if want('Door_Wood'):
        m = mk('SM_Door_Wood_Single_PR', 0.95, 2.02, 'door', FEN, 'wood'); plank_door(m)
        rec(m, ['61 struct/details/door/odor1-', 'door_wood_single'], 'none (family 61 was placeholder)',
            'ledged-and-braced plank door, 0.95 x 2.02 m: six boards of uneven width, three chamfered ledges and two braces on the back, two forged strap hinges with spear ends and rose-head nails, clenched nail rows, ring latch on a back plate',
            fit={'pivot': 'hinge: board edge on x = 0, centred through the 4 cm thickness, floor level; closed leaf along +X, face to -Y; the sprite frames 1-6 are the leaf swinging, so animate yaw', 'sprite_scale': 'the sprite leaf is 64 px (1.6 m) tall: the 3D door is life size, as the town and cottage doors'})
        m = mk('SM_Door_Wood_Wide_PR', 1.5, 2.1, 'door', FEN, 'wood'); plank_door(m, 1.5, 2.1, wide=True)
        rec(m, ['62 struct/details/door/odor2-', 'door_wood_wide'], 'none (family 62 was placeholder)',
            'wide ledged-and-braced door, 1.5 x 2.1 m: the same construction with three long strap hinges, a box lock and a draw bar in two staples',
            fit={'pivot': 'hinge, as SM_Door_Wood_Single_PR'})
    if want('SignPost'):
        for nm, bs, fr in (('Single', [(2.0, 0.5, 0.52, 0.03, 0)], 'frame 7'), ('Double', [(2.02, 0.5, 0.5, -0.02, 0), (1.55, 0.46, 0.5, 0.05, 0)], 'frame 8'),
                           ('Triple', [(2.02, 0.48, 0.5, 0.02, 0), (1.62, 0.1, 0.62, -0.06, 1), (1.36, 0.6, 0.1, 0.07, -1)], 'frames 9, 10')):
            m = mk('SM_SignPost_%s_PR' % nm, 1.1, 2.3, 'prop', FEN, 'wood'); m.floor0 = True; sign_post(m, bs)
            rec(m, ['186 struct/landmark/landm- ' + fr, 'sign_post'], 'none (sign_post was placeholder)',
                'road sign: hewn oak post 2.3 m with a lead cap and packing stones, %d board(s) each of riven planks of unequal length nailed across it' % len(bs),
                fit={'pivot': 'foot of the post, boards face -Y', 'text': 'the boards carry no lettering (the game shows the sign text in a dialogue box)'})
    if want('Chimney'):
        m = mk('SM_Chimney_Stone_Short_PR', 1.0, 1.5, 'prop', ('fieldstone', 'oak', 'boulder'), 'chimney'); chimney_stack(m)
        rec(m, ['63 struct<HOME> frames 11, 12', 'chimney_stone'], 'none', 'fieldstone chimney top to stand on a thatched roof: 0.95 x 0.8 m stack of individually set blocks, 1.43 m, oversailing cap course, sooted flue',
            fit={'pivot': 'centre of the base: sink it 0.3-0.5 m into the thatch at the ridge'})
        m = mk('SM_Chimney_Stone_Tall_PR', 1.3, 4.8, 'prop_large', ('fieldstone', 'oak', 'boulder'), 'chimney'); m.floor0 = True; chimney_stack(m, tall=True)
        rec(m, ['63 struct<HOME> frame 13', 'chimney_stone'], 'none', 'gable-end chimney from the ground: 1.3 m breast, two weathered offsets, 0.82 m flue, 4.73 m (sprite 187 px = 4.7 m)',
            fit={'pivot': 'centre of the base at ground level; stand it against an end wall'})
    COT = ('fieldstone', 'oak', 'thatch', 'door', 'earth')
    if want('Cottage'):
        m = mk('SM_Cottage_Thatched_TwoStorey_PR', 7.6, 9.2, 'building', COT, 'cottage', sb=True); m.paint = [pre_paint(m)]; two_storey(m)
        rec(m, ['63 struct<HOME> frames 4, 5', 'cottage_thatched_two_storey'], 'none (not built in round 1)',
            'two-storey fieldstone cottage as sprite 63 frames 4-5: 6.6 x 6.0 m lower storey with quoins, footing stones and two shuttered windows under a thatched pentice roof on all four sides; a 4.9 x 4.3 m upper storey rises through it under its own hipped thatch with block ridge and chimney',
            fit={'pivot': 'ground centre of the lower wall rectangle; front -Y', 'footprint': 'lower walls 6.6 x 6.0 m, eaves 7.6 x 7.0 m; ridge 8.3 m, chimney top 9.2 m', 'door': 'no doorway is cut: stand SM_Cottage_Door_PR where the door sprite is, as for the other family-63 cottages'})
        m = mk('SM_Cottage_Thatched_LShape_PR', 9.5, 9.2, 'building', COT, 'cottage', sb=True); m.paint = [pre_paint(m)]; l_shape(m)
        rec(m, ['63 struct<HOME> frame 10', 'cottage_thatched_l_shape'], 'none (not built in round 1)',
            'L-shaped cottage as sprite 63 frame 10: the two-storey block with a single-storey hipped wing (4.4 x 5.6 m) thrown forward from its right half',
            fit={'pivot': 'ground; the two-storey block is centred at (-1.2, +1.4), the wing at (+2.3, -2.6), front -Y', 'footprint': 'about 9.3 x 11.2 m over the eaves'})
    HUT = ('daub_blue', 'oak', 'palm', 'daub_olive', 'daub_red', 'bone', 'fieldstone', 'rope', 'earth')
    if want('Island'):
        for two in (False, True):
            m = mk('SM_Island_Hut_%s_PR' % ('TwoStorey' if two else 'Round'), 6.5, 6.5 if two else 4.7, 'building', HUT, 'hut'); m.paint.append(earth_paint(m)); island_hut(m, two)
            rec(m, ['424 struct/island/isle- ' + ('frames 4-6' if two else 'frames 1-3'), 'island_hut_two_storey' if two else 'island_hut_round'], 'none (family 424 was placeholder)',
                ('two-storey round hut: a 6.0 m drum under a thatch skirt with a 4.4 m drum and cone rising through it' if two else 'round island hut, 5.2 m across the wall, 6.4 m across the eaves, 4.6 m to the finial') +
                ': bulging daub wall limewashed blue below a stepped border, olive above, with ox-blood panels (separate material slots, so the colours are paint, not tint); nine weathered whale-rib buttresses; doorway with ox-blood jambs inlaid with shell lozenges under two crossed tusks; domed conical thatch in twelve sectors with a ragged fringe, cane ties, three cane hoops and a whipped finial',
                fit={'pivot': 'ground centre; doorway faces -Y (frames 1-3 are the same hut turned: yaw it)', 'door': 'opening 1.08 m wide, 1.7 m high at y = -%.2f; a dark closed box stands behind it' % (2.9 if two else 2.5)})
        m = mk('SM_Island_Fence_Lattice_PR', 4.4, 1.8, 'prop_large', ('fieldstone', 'bamboo', 'rope'), 'bamboo'); m.floor0 = True; island_fence(m)
        rec(m, ['424 struct/island/isle- frames 7-12', 'island_fence_lattice'], 'none', '4.4 m run of cane lattice fence: three posts, two rails, crossed diagonals in each bay, all bamboo with node rings, rope lashings at every crossing',
            fit={'pivot': 'ground centre, run along X; end posts at x = +-2.2 (share a post between runs as with the split-rail fence)'})
        m = mk('SM_Island_TorchPole_PR', 0.4, 2.6, 'prop', ('fieldstone', 'bamboo', 'rope', 'red_cloth'), 'bamboo'); m.floor0 = True; island_torch(m)
        rec(m, ['424 struct/island/isle- frame 18', 'island_totem_pole'], 'none', 'three-tined cane pole, 2.6 m, bound with red cloth below the tines, tips charred (class island_totem_pole; frame 18)',
            fit={'pivot': 'foot of the pole', 'light': 'unlit; if the game lights it, put flames on the three tips at z = 2.58 m'})
    return out


def main_misc():
    sc = new_scene()
    rows = board_rows('OakWeathered')
    oakp = dict(dirt=(0.22, 0.16, 0.11), pale=(0.46, 0.45, 0.42), pale_amt=0.55, special=True)
    daub = dict(dirt=(0.30, 0.24, 0.16), pale=(0.8, 0.78, 0.72), pale_amt=0.35, dirt_amt=0.95)
    mats = {'fieldstone': wmat('MI_Struct_Fieldstone', 'Fieldstone', dirt=(0.36, 0.30, 0.22), pale=(0.62, 0.60, 0.52), pale_amt=0.5, soot=True),
            'earth': wmat('MI_Struct_Earth', 'EarthPath', tint=(0.62, 0.56, 0.50, 1), dirt=(0.36, 0.30, 0.24), pale=(0.80, 0.79, 0.77), pale_amt=0.85, moss=(0.045, 0.075, 0.02), moss_rough=0.9, soot=True),
            'thatch': wmat('MI_Struct_Thatch', 'Thatch', lead=False, dirt=(0.105, 0.095, 0.08), pale=(0.80, 0.63, 0.33), pale_amt=0.6, dirt_amt=0.95, dirt_mix=True, moss=(0.05, 0.062, 0.02), special=True),
            'oak': wmat('MI_Struct_OakWeathered', 'OakWeathered', tint=(0.80, 0.62, 0.47, 1), **oakp),
            'door': wmat('MI_Town_DoorPlanks', 'DoorPlanks', dirt=(0.3, 0.25, 0.2), special=True),
            'oakdark': wmat('MI_Struct_OakDark', 'OakWeathered', tint=(0.6, 0.36, 0.23, 1), dirt=(0.2, 0.14, 0.1), pale=(0.5, 0.47, 0.42), pale_amt=0.5, special=True),
            'rope': wmat('MI_Struct_Rope', 'Thatch', dirt=(0.5, 0.45, 0.38), pale=(0.7, 0.62, 0.45), pale_amt=0.4, tint=(0.9, 0.85, 0.8, 1)),
            'boulder': wmat('MI_Struct_FieldBoulder', 'FieldBoulder', dirt=(0.34, 0.27, 0.18), pale=(0.66, 0.66, 0.58), pale_amt=0.5, moss=(0.045, 0.06, 0.02)),
            'ashlar': wmat('MI_Struct_CastleAshlar', 'CastleAshlar', dirt=(0.30, 0.22, 0.12), pale=(0.60, 0.60, 0.52), pale_amt=0.5, dirt_amt=0.92, moss=(0.04, 0.055, 0.02)),
            'bamboo': wmat('MI_Island_Bamboo', 'OakWeathered', tint=(1.0, 0.92, 0.6, 1), dirt=(0.3, 0.26, 0.14), pale=(0.74, 0.70, 0.5), pale_amt=0.7, special=True, macro=0.3),
            'palm': wmat('MI_Island_PalmThatch', 'Thatch', lead=False, tint=(1.0, 0.78, 0.6, 1), dirt=(0.12, 0.085, 0.06), pale=(0.85, 0.6, 0.3), pale_amt=0.5, dirt_amt=0.9, dirt_mix=True, moss=(0.06, 0.075, 0.02), special=True),
            'daub_blue': wmat('MI_Island_DaubBlue', 'PlasterWall', tint=(0.2, 0.33, 0.85, 1), **daub),
            'daub_olive': wmat('MI_Island_DaubOlive', 'PlasterWall', tint=(0.3, 0.33, 0.13, 1), **daub),
            'daub_red': wmat('MI_Island_DaubOxblood', 'PlasterWall', tint=(0.42, 0.12, 0.06, 1), **daub),
            'bone': wmat('MI_Island_Bone', 'PlasterWall', tint=(0.86, 0.9, 1.0, 1), dirt=(0.36, 0.33, 0.26), pale=(0.9, 0.9, 0.86), pale_amt=0.5, dirt_amt=0.9, moss=(0.05, 0.07, 0.03)),
            'red_cloth': wmat('MI_Island_RedCloth', 'Thatch', tint=(0.85, 0.12, 0.08, 1), dirt=(0.3, 0.2, 0.16), pale=(0.8, 0.4, 0.3), pale_amt=0.4)}
    mods = misc_modules(rows)
    blend = 'Misc.blend' if not ARGS else 'Misc_part_%s.blend' % '_'.join(ARGS)
    recs = export_modules(mods, mats, OUT, blend)
    mj = os.path.join(OUT, 'modules.json'); old = json.load(open(mj)) if os.path.exists(mj) else []
    names = [r_['name'] for r_ in recs]
    allr = [o for o in old if o['name'] not in names] + recs
    json.dump(allr, open(mj, 'w'), indent=1)
    mp = os.path.join(OUT, 'materials_all.json'); allm = json.load(open(mp)) if os.path.exists(mp) else {}
    allm.update(MATREG); json.dump(allm, open(mp, 'w'), indent=1)
    used = {s for r_ in allr for s in r_['materials']}
    json.dump({k: v for k, v in allm.items() if k in used}, open(os.path.join(OUT, 'materials.json'), 'w'), indent=1)
    print('MISC DONE', len(recs), 'of', len(allr))


main_misc()
