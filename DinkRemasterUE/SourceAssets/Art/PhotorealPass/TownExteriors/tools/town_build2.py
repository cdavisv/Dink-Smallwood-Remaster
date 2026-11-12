"""Town house exterior kit, round 2, for sprite family 33 struct/outinn/oinn-.
blender -b -t 4 --python town_build2.py
Bays are 2.5 m (100 px at 0.025 m/px). Pivot of wall and roof bays: left end x = 0, ground-floor wall centre line on y = 0, ground z = 0,
runs +X, street face looks down -Y; a roof bay placed at the same point as the wall bay under it fits. Every part is a closed solid."""
import bpy, os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
TOWN = os.path.dirname(HERE)
os.environ['DINK_PP'] = os.path.dirname(TOWN)
exec(open(os.path.join(os.environ['DINK_PP'], 'Structures', 'tools', 'kitlib.py')).read())
OUT = TOWN
T_RUBBLE, T_ROOF, T_DOOR = 2.5, 3.0, 2.0
WT = 0.45; GH = 2.7; JOIST = 0.16; BRESS = 0.24; UH = 1.25
TH = GH + JOIST + BRESS + UH            # 4.35 m to the top of the wall plate
JET = 0.22
YF = -WT / 2 - JET                      # street face of the jettied upper storey
PITCH = math.radians(42); RUN = 3.2; EAVE = 0.42
TP_, CP_, SP_ = math.tan(PITCH), math.cos(PITCH), math.sin(PITCH)
SLEN = (RUN + EAVE) / CP_
YE = YF - EAVE; ZE = TH - EAVE * TP_ + 0.10
RIDGE_Y = YF + RUN; RIDGE_Z = TH + 0.10 + RUN * TP_
DEPTH = 2 * RIDGE_Y                     # front wall centre line to back wall centre line
S0, S1, S2 = 0, 1, 2
CREV = 100                              # tag + CREV: the same surface, but down in a joint


def bar(m, p0, p1, w, y0, y1, slot=S1, tag=TAG_TIMBER, tile=T_TIMBER):
    """a closed prism in the XZ plane between two points, width w, from depth y0 to y1"""
    p0 = np.array(p0, float); p1 = np.array(p1, float); d = p1 - p0; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]]) * w / 2
    verts = []
    for c in (p0, p1):
        for (sn, yy) in ((-1, y0), (1, y0), (1, y1), (-1, y1)):
            verts.append([c[0] + sn * n[0] + m.rng.normal(0, 0.0015), yy, c[1] + sn * n[1] + m.rng.normal(0, 0.0015)])
    faces = [[k, (k + 1) % 4, 4 + (k + 1) % 4, 4 + k] for k in range(4)] + [[3, 2, 1, 0], [4, 5, 6, 7]]
    vv = np.array(verts); f = faces[0]
    nn = np.cross(vv[f[1]] - vv[f[0]], vv[f[2]] - vv[f[0]]); cc = vv[f].mean(0) - vv.mean(0)
    if np.dot(nn, cc) < 0:
        faces = [x[::-1] for x in faces]
    rows = m.timber_rows; v0, wv = rows[m.rng.integers(len(rows))]
    m.add(verts, faces, slot, tile, 'board', m.rng.uniform(0, 1, 2), (v0, wv), tag=tag)


def timber(m, lo, hi, bevel=0.012, warp=0.005, segs=None):
    ext = np.array(hi, float) - np.array(lo, float)
    segs = segs or max(3, int(ext.max() / 0.28))
    m.beam(lo, hi, bevel, warp, segs, 0.0035)


def peg(m, x, y, z, r=0.013, axis=1, l=0.03):
    """oak peg head standing proud of a joint"""
    p0 = [x, y, z]; p1 = [x, y, z]; p1[axis] = p1[axis] - l; p0[axis] += 0.01
    m.tube([p0, p1], [r, r * 0.8], S1, sides=6, tag=TAG_END, smooth=False)


def dressed(m, lo, hi, bevel=0.016, jitter=0.005):
    m.block(lo, hi, S0, T_RUBBLE * 0.6, bevel, jitter, tag=TAG_STONE)


def iron(m, lo, hi, bevel=0.003, rot=None):
    m.block(lo, hi, S1, T_TIMBER, bevel, 0.0006, tag=TAG_IRON, rot=rot)


def leaded(m, a, b, z0, z1, yg, sp=0.12):
    """a leaded light: diamond lead cames standing 6 mm proud of slightly uneven glass (each facet catches the sky differently)"""
    m.slab(a, b, z0, z1, yg, yg + 0.006, S1, T_TIMBER, nx=max(3, int((b - a) / 0.09)), nz=max(3, int((z1 - z0) / 0.1)), relief=0.0045, tag=TAG_GLASS)
    for sgn in (1, -1):
        c = -(z1 - z0)
        while c < (b - a):
            pa = np.array([a + c, z0] if sgn == 1 else [b - c, z0], float); pb = np.array([a + c + (z1 - z0), z1] if sgn == 1 else [b - c - (z1 - z0), z1], float)
            d = pb - pa; t0, t1 = 0.0, 1.0
            ta, tb = (a - pa[0]) / d[0], (b - pa[0]) / d[0]
            t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
            if t1 - t0 > 0.03:
                bar(m, pa + d * t0, pa + d * t1, 0.012, yg - 0.007, yg + 0.001, tag=TAG_LEAD)
            c += sp


def ground_wall(m, x0, x1, opening=None, pil=(True, False), door=False):
    y = WT / 2

    def reg(a, b, z0, z1):
        if b - a > 0.02 and z1 - z0 > 0.02:
            m.slab(a, b, z0, z1, -y, y, S0, T_RUBBLE, nx=max(1, int(round((b - a) / 0.21))), nz=max(1, int(round((z1 - z0) / 0.22))), relief=0.012)
    if opening is None:
        reg(x0, x1, 0, GH)
    else:
        ox0, ox1, oz0, oz1 = opening
        reg(x0, ox0, 0, GH); reg(ox1, x1, 0, GH); reg(ox0, ox1, 0, oz0); reg(ox0, ox1, oz1, GH)
    PW = 0.42
    for k, on in enumerate(pil):                      # pilasters of dressed blocks, alternating long and short (the sprite's pale quoin strips)
        if not on:
            continue
        xa = x0 if k == 0 else x1 - PW
        z = 0.0; i = 0
        while z < GH - 1e-6:
            h = min(float(m.rng.uniform(0.26, 0.36)), GH - z)
            if GH - (z + h) < 0.14:
                h = GH - z
            w = PW if i % 2 == 0 else PW - 0.10
            xo = xa if (k == 0) else xa + (PW - w)
            dressed(m, [xo, -y - 0.07 + m.rng.normal(0, 0.008), z + 0.006], [xo + w, -y + 0.03, z + h - 0.006])
            z += h; i += 1
    xa = x0 + (PW if pil[0] else 0); xb = x1 - (PW if pil[1] else 0)       # plinth course
    skip = (lambda x: opening[0] - 0.05 < x < opening[1] + 0.05) if (door and opening) else None
    x = xa
    while x < xb - 1e-6:
        l = float(m.rng.uniform(0.35, 0.7))
        if xb - (x + l) < 0.2:
            l = xb - x
        if skip is None or not skip(x + l / 2):
            dressed(m, [x + 0.006, -y - 0.05, 0.0], [x + l - 0.006, -y + 0.03, 0.27 + m.rng.normal(0, 0.014)], 0.018)
        x += l


def window(m, ox0, ox1, oz0, oz1):
    y = WT / 2
    dressed(m, [ox0 - 0.10, -y - 0.08, oz0 - 0.13], [ox1 + 0.10, -y + 0.12, oz0])                 # stone sill
    dressed(m, [ox0 - 0.16, -y - 0.03, oz1], [ox1 + 0.16, -y + 0.10, oz1 + 0.2])                   # lintel
    yf = -y + 0.11; fw = 0.07
    timber(m, [ox0, yf, oz0], [ox0 + fw, yf + 0.08, oz1], 0.008, 0.002); timber(m, [ox1 - fw, yf, oz0], [ox1, yf + 0.08, oz1], 0.008, 0.002)
    timber(m, [ox0 + fw, yf, oz0], [ox1 - fw, yf + 0.08, oz0 + fw], 0.008, 0.002); timber(m, [ox0 + fw, yf, oz1 - fw], [ox1 - fw, yf + 0.08, oz1], 0.008, 0.002)
    cx = (ox0 + ox1) / 2
    timber(m, [cx - 0.03, yf, oz0 + fw], [cx + 0.03, yf + 0.07, oz1 - fw], 0.006, 0.002)           # mullion
    for (a, b) in ((ox0 + fw, cx - 0.03), (cx + 0.03, ox1 - fw)):
        leaded(m, a, b, oz0 + fw, oz1 - fw, yf + 0.035)
        for zz in (oz0 + fw + 0.38, oz0 + fw + 0.76):                                               # iron saddle bars
            iron(m, [a, yf + 0.018, zz - 0.006], [b, yf + 0.03, zz + 0.006], 0.002)
    m.block([ox0, -y + 0.2, oz0], [ox1, y - 0.02, oz1], S1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS)      # the dark room behind
    m.streak_src.append((ox0 - 0.12, ox0 + 0.06, oz0 - 0.13, 0.9)); m.streak_src.append((ox1 - 0.06, ox1 + 0.12, oz0 - 0.13, 0.9))


def upper(m, x0, x1, studs=None, win=None, brace=None):
    """jetty: joist ends, bressummer, a close-studded storey with uneven stud spacing, optional window and brace, wall plate"""
    y = WT / 2; r = m.rng
    x = x0 + float(r.uniform(0.12, 0.25))
    while x < x1 - 0.1:
        timber(m, [x - 0.065, YF - 0.03, GH + 0.005], [x + 0.065, y - 0.02, GH + JOIST], 0.012, 0.003, 3)
        x += float(r.uniform(0.44, 0.58))
    zb = GH + JOIST
    m.block([x0, YF + 0.02, zb - 0.025], [x1, -y + 0.02, zb], S1, T_TIMBER, 0.0, 0.0, tag=TAG_TIMBER)          # soffit boards between the joists
    timber(m, [x0, YF - 0.09, zb], [x1, YF + 0.11, zb + BRESS], 0.02, 0.006, 9)                                 # bressummer
    z0 = zb + BRESS; z1 = TH - 0.14
    timber(m, [x0, YF - 0.075, z1], [x1, YF + 0.09, TH], 0.016, 0.005, 9)                                       # wall plate
    if studs is None:
        studs = []; x = x0 + 0.0
        while x < x1 - 0.2:
            studs.append(x); x += float(r.uniform(0.33, 0.52))
    L = x1 - x0
    edges = []
    for px in studs:
        w = float(r.uniform(0.085, 0.125))
        if win and win[0] - 0.02 < px + w / 2 < win[1] + 0.02:
            continue
        timber(m, [px, YF - 0.066, z0 - 0.003], [px + w, YF + 0.07, z1 + 0.003], 0.011, 0.004)
        peg(m, px + w / 2, YF - 0.066, z0 + 0.06); peg(m, px + w / 2, YF - 0.066, z1 - 0.06)
        edges.append((px, px + w))
    if win:                                              # a small two-light leaded window between two studs
        wa, wb, wz0, wz1 = win
        for (a, b) in ((wa - 0.09, wa), (wb, wb + 0.09)):
            timber(m, [a, YF - 0.07, z0 - 0.003], [b, YF + 0.07, z1 + 0.003], 0.011, 0.003)
        timber(m, [wa, YF - 0.068, wz0 - 0.09], [wb, YF + 0.07, wz0], 0.01, 0.002); timber(m, [wa, YF - 0.068, wz1], [wb, YF + 0.07, wz1 + 0.08], 0.01, 0.002)
        cx = (wa + wb) / 2
        timber(m, [cx - 0.025, YF - 0.05, wz0], [cx + 0.025, YF + 0.03, wz1], 0.006, 0.002)
        leaded(m, wa, cx - 0.025, wz0, wz1, YF - 0.012, 0.1); leaded(m, cx + 0.025, wb, wz0, wz1, YF - 0.012, 0.1)
        m.block([wa, YF + 0.0, wz0], [wb, YF + 0.2, wz1], S1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS)
        m.streak_src.append((wa - 0.1, wb + 0.1, wz0 - 0.09, 0.5))
    if brace:                                            # a raking brace let in over the studs
        (bx0, bx1) = brace
        bar(m, [bx0, z0 + 0.02], [bx1, z1 - 0.02], 0.12, YF - 0.078, YF - 0.02)
        peg(m, bx0 + 0.07, YF - 0.078, z0 + 0.1); peg(m, bx1 - 0.07, YF - 0.078, z1 - 0.1)
    # plaster infill: one closed panel behind the studs, standing 2 cm back from their faces, its surface uneven
    m.slab(x0, x1, z0 - 0.01, z1 + 0.01, YF - 0.045, YF + 0.05, S2, T_PLASTER, nx=max(2, int(L / 0.2)), nz=5, relief=0.006, tag=TAG_PLASTER, uvoff=(float(r.uniform(0, 1)), 0.0))
    m.slab(x0, x1, zb, TH, YF + 0.05, y, S2, T_PLASTER, nx=1, nz=1, relief=0.0, tag=TAG_PLASTER)                # the room behind (closed core)
    for px in (x0 + 0.3, x0 + L / 2, x1 - 0.3):
        peg(m, px, YF - 0.09, zb + 0.12, 0.015)


def tie_plate(m, x, z, y):
    """wrought iron wall tie: an X of flat bar with a square washer and bolt head"""
    for sg in (1, -1):
        bar(m, [x - 0.2, z - sg * 0.2], [x + 0.2, z + sg * 0.2], 0.036, y - 0.012, y + 0.004, tag=TAG_IRON)
    iron(m, [x - 0.05, y - 0.02, z - 0.05], [x + 0.05, y - 0.01, z + 0.05], 0.004, rot=(0, 0, math.radians(45)))
    iron(m, [x - 0.02, y - 0.036, z - 0.02], [x + 0.02, y - 0.02, z + 0.02], 0.006)


def lantern(m, x, z, y):
    """wrought iron bracket with a scroll stay and a hanging horn-paned lantern"""
    T = lambda p, r, s=6: m.tube(p, r, S1, sides=s, tag=TAG_IRON, smooth=False)
    iron(m, [x - 0.03, y - 0.012, z - 0.36], [x + 0.03, y, z + 0.06], 0.004)                 # back plate
    T([[x, y, z], [x, y - 0.55, z + 0.03], [x, y - 0.6, z + 0.0]], [0.014, 0.012, 0.008])
    stay = [[x, y - 0.01, z - 0.32]] + [[x, y - 0.06 - 0.36 * t, z - 0.32 + 0.30 * (t ** 0.6)] for t in np.linspace(0.15, 1, 6)]
    T(stay, [0.01] * 7)
    T([[x, y - 0.5, z + 0.02], [x, y - 0.5, z - 0.1]], [0.005, 0.005], 5)                     # hook and ring
    cy = y - 0.5; top = z - 0.1; w = 0.085; hgt = 0.24
    m.prism([(x - w - 0.02, top - 0.07), (x, top), (x + w + 0.02, top - 0.07)], cy - w - 0.02, cy + w + 0.02, S1, T_TIMBER, tag=TAG_IRON)   # cap
    for sx in (-1, 1):
        for sy in (-1, 1):
            iron(m, [x + sx * w - 0.007, cy + sy * w - 0.007, top - 0.07 - hgt], [x + sx * w + 0.007, cy + sy * w + 0.007, top - 0.07], 0.002)
    iron(m, [x - w - 0.01, cy - w - 0.01, top - 0.09 - hgt], [x + w + 0.01, cy + w + 0.01, top - 0.07 - hgt], 0.003)
    m.block([x - w + 0.006, cy - w + 0.006, top - 0.07 - hgt], [x + w - 0.006, cy + w - 0.006, top - 0.075], S1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS)


# ---------------------------------------------------------------- roof
def bay_pt(x0, x1, sag=0.05):
    def pt(x, s, h):
        t = min(max(s / SLEN, 0), 1)
        sg = -sag * math.sin(math.pi * t) * (0.55 + 0.45 * math.sin(math.pi * (x - x0) / max(x1 - x0, 1e-6))) - 0.018 * (1 - abs(2 * t - 1))
        hh = h + sg
        return [x, YE + s * CP_ - hh * SP_, ZE + s * SP_ + hh * CP_]
    return pt


def roof_slab(m, a0, a1, pt, S, uvfn=None, lap=0.0, slot=S0, expo=0.2, half=0.155, thick=0.085, seed_off=0, defects=True, tile=T_ROOF, tag=TAG_ROOF, ragged=0.014, st=0.03):
    """shingle roof as ONE closed solid: a grid whose rows are the butt of every course (bottom and top of the riser) and whose
    columns are the shingle joints (a 6 mm pair of columns at every half shingle, so courses break joint). Each shingle has its own
    butt position, thickness and tilt; a few are slipped, lifted or missing. pt(a, s, h) -> xyz maps along-eaves a, up-slope s, lift h."""
    r = m.rng
    nc = max(2, int(round(S / expo))); e = S / nc
    nh = max(1, int(round((a1 - a0) / half)))
    bx = np.linspace(a0, a1, nh + 1)
    bx[1:-1] += r.normal(0, half * 0.12, nh - 1)
    cols = [a0] + [v for b in bx[1:-1] for v in (b - 0.004, b + 0.004)] + [a1]
    C = len(cols); R = 2 * nc + 1
    top = np.zeros((R, C, 3)); tags = np.zeros((R, C), int); ecol = np.tile(np.array(cols), (R, 1))
    lift_prev = np.zeros(C)
    for i in range(nc):
        off = i % 2
        s_lo = np.zeros(C); hh = np.zeros(C)
        k = 0
        # shingles of this course: boundaries at bx[off::2] (plus the bay ends)
        bnd = [0] + [j for j in range(1, nh) if (j - off) % 2 == 0] + [nh]
        for a_, b_ in zip(bnd[:-1], bnd[1:]):
            ca = 0 if a_ == 0 else 2 * a_           # first column of this shingle (the +4 mm one of the pair)
            cb = C - 1 if b_ == nh else 2 * b_ - 1  # last column (the -4 mm one)
            d0 = r.normal(0, ragged); d1 = d0 + r.normal(0, ragged * 0.5); t0 = st + r.normal(0, 0.004); t1 = t0
            u = r.uniform()
            if defects and i > 1 and i < nc - 1:
                if u < 0.035:                         # slipped: slid down and skewed
                    d0 -= r.uniform(0.04, 0.09); d1 = d0 + r.normal(0, 0.03)
                elif u < 0.07:                        # lifted corner
                    t1 += r.uniform(0.02, 0.045)
                elif u < 0.09:                        # missing: the course below shows through
                    t0 = t1 = 0.002; d0 = d1 = e * 0.8
            for c in range(ca, cb + 1):
                f = 0 if cb == ca else (c - ca) / (cb - ca)
                s_lo[c] = max(0.0, i * e + (d0 + (d1 - d0) * f if i > 0 else 0.0)); hh[c] = t0 + (t1 - t0) * f
        if lap == 0:
            s_lo[0] = s_lo[C - 1] = i * e; hh[0] = hh[C - 1] = st
        if i == 0:
            hh += 0.02                                # doubled eaves course
        for c in range(C):
            # bay edges: alternate courses run 15 cm on into the next bay (4 mm proud), so the joint between two bays zigzags like any other
            xc = cols[c]; lf = 0.0
            if lap and c == 0 and i % 2 == 1:
                xc = a0 - lap; lf = 0.004
            if lap and c == C - 1 and i % 2 == 0:
                xc = a1 + lap; lf = 0.004
            ecol[2 * i, c] = ecol[2 * i + 1, c] = xc
            top[2 * i, c] = pt(xc, s_lo[c], (0.003 if i > 0 else -0.012) + lf)
            top[2 * i + 1, c] = pt(xc, s_lo[c], hh[c] + lf)
            tags[2 * i, c] = tag + CREV; tags[2 * i + 1, c] = tag
    for c in range(C):
        top[R - 1, c] = pt(cols[c], S, 0.004); tags[R - 1, c] = tag
    under = np.zeros_like(top)
    for rr_ in range(R):
        for c in range(C):
            s = min(S, e * rr_ / 2.0)
            under[rr_, c] = pt(ecol[rr_, c], s, -thick)
    n0 = len(m.V)
    m.hgrid(top, under, slot, tile, tag=tag, uvfn=uvfn, up=np.array(pt((a0 + a1) / 2, S / 2, 1.0)) - np.array(pt((a0 + a1) / 2, S / 2, 0.0)))
    m.VT[n0:n0 + R * C] = tags.reshape(-1).tolist()


def roof(m, x0, x1, dormer=False):
    r = m.rng; pt = bay_pt(x0, x1); uo = r.uniform(0, 1, 2)
    roof_slab(m, x0, x1, pt, SLEN, lap=0.155, uvfn=lambda P: np.stack([P[:, 0] / T_ROOF + uo[0], ((P[:, 1] - YE) * CP_ + (P[:, 2] - ZE) * SP_) / T_ROOF + uo[1]], -1))
    # eaves: fascia board, rafter feet standing on the plate, a tilting fillet
    ye = YE; ze = ZE
    timber(m, [x0, ye - 0.012, ze - 0.2], [x1, ye + 0.035, ze + 0.0], 0.006, 0.003, 8)
    x = x0 + 0.2
    while x < x1 - 0.05:
        a = np.array(pt(x, 0.03, -0.085)); b = np.array(pt(x, (EAVE + 0.3) / CP_, -0.085))
        w = float(r.uniform(0.04, 0.05)); V = []
        for cpt in (a, b):
            for (dxx, dh) in ((-w, 0), (w, 0), (w, -0.13), (-w, -0.13)):
                V.append([cpt[0] + dxx, cpt[1] + dh * SP_, cpt[2] + dh * CP_])
        F = [[k, (k + 1) % 4, 4 + (k + 1) % 4, 4 + k] for k in range(4)] + [[3, 2, 1, 0], [4, 5, 6, 7]]
        Va = np.array(V); f = F[0]
        if np.dot(np.cross(Va[f[1]] - Va[f[0]], Va[f[2]] - Va[f[0]]), Va[f].mean(0) - Va.mean(0)) < 0:
            F = [q[::-1] for q in F]
        m.add(V, F, S1, T_TIMBER, 'board', r.uniform(0, 1, 2), m.timber_rows[r.integers(len(m.timber_rows))], tag=TAG_TIMBER)
        x += float(r.uniform(0.38, 0.46))
    if dormer:
        dormer_on(m, (x0 + x1) / 2, pt)


def dormer_on(m, cx, pt):
    """gabled dormer standing on the slope: framed front with a two-light leaded window, plastered cheeks, lead apron and soakers,
    its own shingle roof with thickness, barge boards and a lead-roll ridge"""
    r = m.rng
    w = 1.1; ds0 = 1.2
    f0 = pt(cx, ds0, 0.0); fy, fz = f0[1], f0[2] + 0.03
    hw = 1.0                                           # front wall height to the dormer eaves
    post = 0.09
    # cheeks: triangular plaster panels (closed prisms), 7 cm thick
    for sx in (-1, 1):
        xx = cx + sx * (w / 2 - 0.035)
        m.prism([(fy + 0.02, fz - 0.05), (fy + 0.02, fz + hw), (fy + (hw + 0.05) / TP_ + 0.02, fz + hw)], xx - 0.035, xx + 0.035, S1, T_TIMBER, tag=TAG_TIMBER, axis=0, mode='board')
        pa = cx - w / 2 if sx < 0 else cx + w / 2 - post
        timber(m, [pa, fy - 0.03, fz - 0.03], [pa + post, fy + 0.08, fz + hw], 0.009, 0.002)
    xa, xb = cx - w / 2 + post, cx + w / 2 - post
    timber(m, [cx - w / 2, fy - 0.04, fz - 0.05], [cx + w / 2, fy + 0.08, fz + 0.06], 0.01, 0.002)        # sill
    timber(m, [cx - w / 2 - 0.02, fy - 0.04, fz + hw - 0.1], [cx + w / 2 + 0.02, fy + 0.08, fz + hw], 0.01, 0.002)   # head
    timber(m, [cx - 0.028, fy - 0.025, fz + 0.06], [cx + 0.028, fy + 0.05, fz + hw - 0.1], 0.006, 0.002)
    leaded(m, xa, cx - 0.028, fz + 0.06, fz + hw - 0.1, fy + 0.0, 0.11); leaded(m, cx + 0.028, xb, fz + 0.06, fz + hw - 0.1, fy + 0.0, 0.11)
    m.block([xa, fy + 0.012, fz + 0.06], [xb, fy + 0.3, fz + hw - 0.1], S1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS)
    # gablet: boarded triangle above the head, with a pegged collar
    gp = 1.0                                           # 45 degree dormer roof
    ov = 0.16; gh = (w / 2 + ov) * gp; apex = fz + hw + (w / 2) * gp
    m.prism([(cx - w / 2, fz + hw), (cx + w / 2, fz + hw), (cx, apex)], fy + 0.0, fy + 0.06, S1, T_TIMBER, tag=TAG_TIMBER, axis=1, mode='board')
    # dormer roof: two closed shingle slabs from the front overhang back into the main slope
    yb = fy + (apex - f0[2]) / TP_ + 0.25
    ln = yb - (fy - 0.14)
    for sx in (-1, 1):
        def dpt(a, s, h, sx=sx):
            # a: along the dormer ridge (front to back), s: up the dormer slope from its eaves, h: lift normal to it
            c45 = math.cos(math.atan(gp)); s45 = math.sin(math.atan(gp))
            return [cx + sx * ((w / 2 + ov) - s * c45 + h * s45 * 1.0), fy - 0.14 + a, fz + hw - ov * gp + s * s45 + h * c45]
        SL = (w / 2 + ov) / math.cos(math.atan(gp))
        roof_slab(m, 0.0, ln, dpt, SL, expo=0.17, half=0.14, thick=0.05, defects=False, st=0.024)
        bar(m, [cx + sx * (w / 2 + ov + 0.01), fz + hw - ov * gp - 0.07], [cx, apex - 0.07], 0.11, fy - 0.165, fy - 0.135)    # barge board
    m.tube([[cx, fy - 0.17, apex + 0.035], [cx, yb, apex + 0.035]], [0.04, 0.04], S1, sides=6, tag=TAG_LEAD, tile=T_TIMBER, smooth=True, vrange=(0.5, 0.05))   # lead roll ridge
    for sx in (-1, 1):                                 # lead capping dressed over the roll onto the top course
        m.block([cx + sx * 0.02 - (0.16 if sx < 0 else 0), fy - 0.17, apex - 0.07], [cx + sx * 0.02 + (0.16 if sx > 0 else 0), yb, apex - 0.055], S1, T_TIMBER, 0.004, 0.002, tag=TAG_LEAD,
                rot=(0, 0, -sx * math.atan(gp)))
    # lead apron under the sill and soakers along the cheeks, lying on the main slope
    n0 = len(m.V)
    m.block([cx - w / 2 - 0.12, -0.24, -0.004], [cx + w / 2 + 0.12, 0.02, 0.008], S1, T_TIMBER, 0.003, 0.002, tag=TAG_LEAD)
    for sx in (-1, 1):
        m.block([cx + sx * (w / 2 + 0.07) - 0.07, 0.0, -0.004], [cx + sx * (w / 2 + 0.07) + 0.07, (hw + 0.1) / SP_ * 1.0, 0.008], S1, T_TIMBER, 0.003, 0.002, tag=TAG_LEAD)
    base = np.array(pt(cx, ds0, 0.045)); base[0] = 0.0
    M = np.eye(4); M[:3, :3] = np.array([[1, 0, 0], [0, CP_, -SP_], [0, SP_, CP_]]); M[:3, 3] = base
    m.xform_since(n0, M)
    m.dormer_box = (cx - w / 2 - ov, cx + w / 2 + ov, ds0, ds0 + (hw + 0.4) / SP_)


def ridge(m, L):
    """ridge: lapped stone ridge tiles (inverted V, 45 cm long, each a closed solid) bedded on a ridge board; pivot at the left end
    of the ridge line, z = 0 at the ridge"""
    r = m.rng
    x = -0.0; i = 0
    while x < L - 1e-6:
        l = min(float(r.uniform(0.40, 0.48)), L - x)
        if L - (x + l) < 0.15:
            l = L - x
        lift = 0.012 + r.normal(0, 0.003); tilt = r.normal(0, 0.01); t = 0.034; wg = 0.25 + r.normal(0, 0.008); dz = r.normal(0, 0.004)
        a = math.radians(40)
        poly = [(-wg * math.cos(a), -wg * math.sin(a)), (0.0, 0.035), (wg * math.cos(a), -wg * math.sin(a)),
                (wg * math.cos(a) - t * 0.7, -wg * math.sin(a) - t * 0.75), (0.0, 0.035 - t * 1.25), (-wg * math.cos(a) + t * 0.7, -wg * math.sin(a) - t * 0.75)]
        n0 = len(m.V)
        m.prism(poly, x + 0.0, x + l + (0.035 if x + l < L - 1e-6 else 0.0), S0, T_ROOF, tag=TAG_ROOF, axis=0)
        for k in range(n0, len(m.V)):
            fx = (m.V[k][0] - x) / l
            m.V[k][2] += lift * (1 - fx) + dz + 0.012; m.V[k][1] += tilt * (fx - 0.5)
        # mortar bed showing at the lap
        x += l; i += 1
    timber(m, [0, -0.03, -0.3], [L, 0.03, -0.045], 0.006, 0.003, 4)


def door_leaf(m, w=1.04, h=2.04):
    t = 0.055; r = m.rng; nd0 = len(m.V)
    x = 0.0; k = 0
    while x < w - 1e-6:                                 # separate planks of uneven width, each a little proud or shy
        pw = min(float(r.uniform(0.14, 0.22)), w - x)
        if w - (x + pw) < 0.08:
            pw = w - x
        dy = r.normal(0, 0.002)
        m.block([x + 0.0015, -t / 2 + dy, 0.012 + abs(r.normal(0, 0.004))], [x + pw - 0.0015, t / 2 + dy, h - abs(r.normal(0, 0.003))], S0, T_DOOR, 0.004, 0.0008, tag=TAG_SHEET)
        x += pw; k += 1
    for z in (0.32, h / 2, h - 0.32):                       # ledges on the back, strap hinges and studs on the front
        m.block([0.03, t / 2, z - 0.07], [w - 0.03, t / 2 + 0.03, z + 0.07], S0, T_DOOR, 0.005, 0.001, tag=TAG_SHEET)
        if z != h / 2:
            m.block([0.0, -t / 2 - 0.009, z - 0.022], [0.62, -t / 2, z + 0.022], S0, T_DOOR, 0.002, 0.0005, tag=TAG_IRON)
            m.block([0.62, -t / 2 - 0.009, z - 0.036], [0.70, -t / 2, z + 0.036], S0, T_DOOR, 0.003, 0.0005, tag=TAG_IRON)
    for zz in np.linspace(0.15, h - 0.14, 8):
        for xx in np.linspace(0.09, w - 0.09, 6):
            m.block([xx - 0.011, -t / 2 - 0.012, zz - 0.011], [xx + 0.011, -t / 2, zz + 0.011], S0, T_DOOR, 0.005, 0.0008, tag=TAG_IRON)
    m.block([w - 0.16, -t / 2 - 0.012, 0.98], [w - 0.07, -t / 2, 1.07], S0, T_DOOR, 0.003, 0.0, tag=TAG_IRON)
    ring = [(w - 0.115 + 0.05 * math.cos(2 * math.pi * k / 10), 0.99 + 0.05 * math.sin(2 * math.pi * k / 10)) for k in range(10)]
    for k in range(10):
        bar(m, ring[k], ring[(k + 1) % 10], 0.012, -t / 2 - 0.024, -t / 2 - 0.012, slot=S0, tag=TAG_IRON, tile=T_DOOR)
    V = np.array(m.V); W_ = V[nd0:]; dy = -(W_[:, 1].min() + W_[:, 1].max()) / 2; dz = -W_[:, 2].min(); dx = -W_[:, 0].min()
    V[nd0:] = W_ + np.array([dx, dy, dz]); m.V = V.tolist()


# ---------------------------------------------------------------- gable end, corner, chimney
def gable_end(m):
    """the whole end wall of a house: box frame on a stone plinth to the plate, tie beam, then the gable triangle with king post and
    struts; verge of the roof with barge boards. Local +X runs across the house depth (0 = one long-wall centre line, DEPTH = the
    other), outer face -Y."""
    r = m.rng; D = DEPTH; yo, yi = -0.10, 0.10; ys = yo - 0.03     # timber face stands 3 cm proud of the plaster
    xa, xb = -WT / 2, D + WT / 2                       # ground storey
    ua, ub = YF - 0.02, D - YF + 0.02                  # jettied storey and gable
    zs = 0.32                                          # top of the plinth
    x = xa
    while x < xb - 1e-6:                               # plinth of dressed stone
        l = float(r.uniform(0.4, 0.75))
        if xb - (x + l) < 0.25:
            l = xb - x
        m.block([x + 0.005, yo - 0.07, 0.0], [x + l - 0.005, yi, zs + r.normal(0, 0.008)], S0, T_RUBBLE * 0.6, 0.018, 0.005, tag=TAG_STONE)
        x += l
    zst = GH + JOIST                                    # storey beam (bressummer level)
    T = lambda lo, hi, **k: timber(m, lo, hi, 0.014, 0.005, **k)
    T([xa, ys - 0.02, zs], [xb, yi, zs + 0.2])                                        # sill
    T([ua, ys - 0.03, zst - 0.02], [ub, yi, zst + BRESS])                             # storey beam
    T([ua + 0.1, ys - 0.03, TH - 0.2], [ub - 0.1, yi, TH + 0.02])                      # tie beam
    posts = [xa, xa + 1.45, D / 2 - 0.09, xb - 1.45 - 0.18, xb - 0.18]
    for px in posts:
        T([px, ys, zs + 0.2], [px + 0.18, yi, zst - 0.02])
        peg(m, px + 0.09, ys, zs + 0.3); peg(m, px + 0.09, ys, zst - 0.12)
    zr = 1.56
    for a_, b_ in zip(posts[:-1], posts[1:]):
        T([a_ + 0.18, ys + 0.008, zr], [b_, yi, zr + 0.14])                            # mid rail
    for (a_, b_) in ((posts[0], posts[1]), (posts[3], posts[4])):                     # St Andrew's cross in the end panels (as the sprite)
        bar(m, [a_ + 0.2, zs + 0.22], [b_ - 0.02, zr - 0.02], 0.11, ys + 0.012, yo + 0.03)
        bar(m, [b_ - 0.02, zs + 0.22], [a_ + 0.2, zr - 0.02], 0.11, ys + 0.004, yo + 0.022)
    # ground-floor window in the bay left of centre (sprite frame 10)
    wa, wb, wz0, wz1 = posts[1] + 0.45, posts[2] - 0.25, zr + 0.13 + 0.12, zst - 0.3
    for (a_, b_) in ((wa - 0.08, wa), (wb, wb + 0.08)):
        T([a_, ys + 0.004, zr + 0.13], [b_, yi, zst - 0.02])
    T([wa, ys + 0.006, wz0 - 0.08], [wb, yi, wz0]); T([wa, ys + 0.006, wz1], [wb, yi, wz1 + 0.08])
    cx = (wa + wb) / 2
    timber(m, [cx - 0.025, ys + 0.02, wz0], [cx + 0.025, yo + 0.06, wz1], 0.006, 0.002)
    leaded(m, wa, cx - 0.025, wz0, wz1, yo + 0.01, 0.11); leaded(m, cx + 0.025, wb, wz0, wz1, yo + 0.01, 0.11)
    m.block([wa, yo + 0.02, wz0], [wb, yi - 0.01, wz1], S1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS)
    m.streak_src.append((wa - 0.1, wb + 0.1, wz0 - 0.08, 0.5))
    # upper storey: studs, two braces down from the corner posts
    zu0 = zst + BRESS
    ust = [ua + 0.0]
    while ust[-1] < ub - 0.75:
        ust.append(ust[-1] + float(r.uniform(0.42, 0.62)))
    ust[-1] = ub - 0.16
    for k, px in enumerate(ust):
        w_ = 0.16 if k in (0, len(ust) - 1) else float(r.uniform(0.09, 0.12))
        T([px, ys, zu0], [px + w_, yi, TH - 0.2])
        peg(m, px + w_ / 2, ys, zu0 + 0.07); peg(m, px + w_ / 2, ys, TH - 0.28)
    bar(m, [ust[0] + 0.14, TH - 0.24], [ust[2] + 0.05, zu0 + 0.03], 0.12, ys - 0.012, yo + 0.02)
    bar(m, [ust[-1] + 0.02, TH - 0.24], [ust[-3] + 0.05, zu0 + 0.03], 0.12, ys - 0.012, yo + 0.02)
    # gable triangle: rafters follow the roof underside
    zt = TH + 0.02
    rz = lambda x_: ZE + ((x_ - (YE)) if x_ < D / 2 else ((D - YE) - x_)) * TP_ - 0.085 / CP_ - 0.02       # underside of the roof slab over x
    for sg in (0, 1):
        e0 = [ua + 0.05, rz(ua + 0.05) - 0.11] if sg == 0 else [ub - 0.05, rz(ub - 0.05) - 0.11]
        bar(m, e0, [D / 2, rz(D / 2) - 0.11], 0.2, ys - 0.02, yi)                       # principal rafters
    T([D / 2 - 0.09, ys, zt], [D / 2 + 0.09, yi, rz(D / 2) - 0.22])                    # king post
    zc = zt + 1.25
    hx = (rz(D / 2) - 0.36 - zc) / TP_
    T([D / 2 - hx + 0.05, ys + 0.006, zc], [D / 2 + hx - 0.05, yi, zc + 0.15])           # collar
    for sx in (-1, 1):
        qx = D / 2 + sx * 1.35
        T([qx - 0.06, ys + 0.004, zt], [qx + 0.06, yi, rz(qx) - 0.2])                  # queen struts
        qx2 = D / 2 + sx * 2.35
        T([qx2 - 0.05, ys + 0.004, zt], [qx2 + 0.05, yi, rz(qx2) - 0.2])
        bar(m, [D / 2 + sx * 0.1, zc + 0.16], [D / 2 + sx * 0.75, rz(D / 2 + sx * 0.75) - 0.24], 0.1, ys + 0.004, yo + 0.03)
    # plaster: closed panels behind the frame (ground, upper, gable)
    m.slab(xa, xb, zs, zst, yo, yi - 0.01, S2, T_PLASTER, nx=26, nz=9, relief=0.007, tag=TAG_PLASTER, uvoff=(0.3, -0.14))
    m.slab(ua, ub, zst, zt, yo, yi - 0.01, S2, T_PLASTER, nx=28, nz=7, relief=0.007, tag=TAG_PLASTER, uvoff=(0.3, -0.14))
    m.slab(ua + 0.25, ub - 0.25, zt, zt + 0.1, yo, yi - 0.01, S2, T_PLASTER, nx=28, nz=8, relief=0.006, tag=TAG_PLASTER, uvoff=(0.7, -0.14),
           ztop=lambda x_: max(zt + 0.06, rz(x_) - 0.16))
    m.streak_src.append((ua, ub, zst, 0.45)); m.streak_src.append((ua, ub, TH, 0.4))


def verge(m):
    """roof verge over a gable end: a strip of both slopes oversailing the wall, barge boards, capping fillets, finial post.
    Same local frame as the gable end."""
    D = DEPTH
    # verge: a strip of both roof slopes oversailing the wall, barge boards under its edge
    for sg in (0, 1):
        def vpt(a, s, h, sg=sg):
            t = min(max(s / SLEN, 0), 1); hh = h - 0.03 * math.sin(math.pi * t)
            xx = YE + s * CP_ - hh * SP_
            return [xx if sg == 0 else D - xx, -a, ZE + s * SP_ + hh * CP_]
        roof_slab(m, 0.0, 0.42, vpt, SLEN, slot=S0, defects=False, uvfn=lambda P: np.stack([P[:, 1] / T_ROOF + 0.3, ((np.minimum(P[:, 0], D - P[:, 0]) - YE) * CP_ + (P[:, 2] - ZE) * SP_) / T_ROOF + 0.1 * sg], -1))
        e0 = [YE + 0.02, ZE - 0.16] if sg == 0 else [D - YE - 0.02, ZE - 0.16]
        bar(m, e0, [D / 2, RIDGE_Z - 0.2], 0.24, -0.43, -0.39)                       # barge board
        bar(m, [e0[0], e0[1] + 0.12], [D / 2, RIDGE_Z - 0.08], 0.05, -0.445, -0.40)  # capping fillet
    m.block([D / 2 - 0.06, -0.455, RIDGE_Z - 0.62], [D / 2 + 0.06, -0.38, RIDGE_Z + 0.0], S1, T_TIMBER, 0.01, 0.003, tag=TAG_TIMBER)   # finial post over the barge joint


def corner_quoin(m):
    """corner of two stone bay rows: alternating long and short dressed quoins on both faces, the jetty's corner post on a bracket.
    Pivot at the meeting point of the two wall centre lines; faces look down -Y and -X."""
    y = WT / 2; z = 0.0; i = 0; r = m.rng
    while z < GH - 1e-6:
        h = min(float(r.uniform(0.27, 0.36)), GH - z)
        if GH - (z + h) < 0.15:
            h = GH - z
        la, lb = (0.62, 0.36) if i % 2 == 0 else (0.36, 0.62)
        o = 0.075
        m.block([-y - o + r.normal(0, 0.006), -y - o + r.normal(0, 0.006), z + 0.006], [-y + la, -y + lb * 0 + 0.3, z + h - 0.006], S0, T_RUBBLE * 0.6, 0.018, 0.005, tag=TAG_STONE)
        m.block([-y - o + r.normal(0, 0.004), -y + 0.3, z + 0.006], [-y + 0.3, -y + lb, z + h - 0.006], S0, T_RUBBLE * 0.6, 0.018, 0.005, tag=TAG_STONE)
        z += h; i += 1
    zb = GH + JOIST
    timber(m, [YF - 0.1, YF - 0.1, zb + BRESS], [YF + 0.12, YF + 0.12, TH], 0.016, 0.004)                      # corner post
    timber(m, [YF - 0.1, YF - 0.1, zb], [YF + 0.3, YF + 0.12, zb + BRESS], 0.016, 0.004); timber(m, [YF - 0.1, YF + 0.12, zb], [YF + 0.12, YF + 0.3, zb + BRESS], 0.016, 0.004)
    # dragon bracket: a curved knee from the quoin up to the jetty corner
    pts = [[-y - 0.06 - 0.16 * t, -y - 0.06 - 0.16 * t, GH - 0.55 + 0.72 * (t ** 0.55)] for t in np.linspace(0, 1, 6)]
    m.tube(pts, [0.07, 0.075, 0.08, 0.085, 0.09, 0.09], S1, sides=6, tag=TAG_TIMBER, smooth=False, shape=[1, 0.8, 1, 0.8, 1, 0.8])
    m.slab(YF + 0.02, y, zb, TH, YF + 0.02, y, S2, T_PLASTER, nx=1, nz=1, relief=0, tag=TAG_PLASTER)
    m.slab(-y, y, 0, GH, -y, y, S0, T_RUBBLE, nx=2, nz=10, relief=0.0)


def chimney(m, H=7.62):
    """external stone stack: battered base, two weathered offsets, a flue with a drip course, slate-and-stone cap, two clay pots.
    Pivot: centre of the face that stands against the wall (y = 0), ground z = 0; the stack projects toward -Y."""
    r = m.rng

    def courses(xw0, xw1, d0, d1, z0, z1, hmin=0.2, hmax=0.3):
        z = z0
        while z < z1 - 1e-6:
            h = min(float(r.uniform(hmin, hmax)), z1 - z)
            if z1 - (z + h) < 0.12:
                h = z1 - z
            t = (z - z0) / max(z1 - z0, 1e-6); w = xw0 + (xw1 - xw0) * t; d = d0 + (d1 - d0) * t
            # each course: 2-3 stones across the face, returns at the sides
            n = 2 if w < 0.9 else 3; cuts = sorted([-w / 2, w / 2] + [float(r.uniform(-w / 2 + 0.22, w / 2 - 0.22)) for _ in range(n - 1)])
            cuts = [c for k, c in enumerate(cuts) if k == 0 or c - cuts[k - 1] > 0.16]
            cuts[-1] = w / 2
            for a_, b_ in zip(cuts[:-1], cuts[1:]):
                m.block([a_ + 0.004, -d + r.normal(0, 0.006), z + 0.004], [b_ - 0.004, 0.0, z + h - 0.004], S0, T_RUBBLE * 0.6, 0.02, 0.006, tag=TAG_STONE if r.uniform() < 0.3 else TAG_SHEET)
            z += h
    courses(1.15, 1.1, 0.75, 0.72, 0.0, 2.6)
    for k in range(3):                                   # first offset (weathered shoulders)
        courses(1.1 - 0.07 * (k + 1), 1.1 - 0.07 * (k + 1), 0.72 - 0.035 * (k + 1), 0.72 - 0.035 * (k + 1), 2.6 + 0.2 * k, 2.6 + 0.2 * (k + 1), 0.2, 0.2)
    courses(0.88, 0.86, 0.61, 0.6, 3.2, 5.2)
    for k in range(2):
        courses(0.86 - 0.06 * (k + 1), 0.86 - 0.06 * (k + 1), 0.6 - 0.02 * (k + 1), 0.6 - 0.02 * (k + 1), 5.2 + 0.18 * k, 5.2 + 0.18 * (k + 1), 0.18, 0.18)
    courses(0.75, 0.74, 0.56, 0.56, 5.56, H - 0.5)
    m.block([-0.44, -0.62, H - 0.5], [0.44, 0.06, H - 0.41], S0, T_RUBBLE * 0.6, 0.012, 0.004, tag=TAG_STONE)       # drip course
    courses(0.76, 0.76, 0.56, 0.56, H - 0.41, H - 0.12, 0.14, 0.16)
    m.block([-0.47, -0.65, H - 0.12], [0.47, 0.09, H - 0.05], S0, T_RUBBLE * 0.6, 0.014, 0.005, tag=TAG_STONE)      # cap slab
    for cx in (-0.17, 0.17):                              # clay pots, sooted
        pts = [[cx, -0.28, H - 0.06], [cx, -0.28, H + 0.05], [cx, -0.28, H + 0.3], [cx, -0.28, H + 0.34]]
        m.tube(pts, [0.13, 0.115, 0.095, 0.105], S0, sides=10, tag=TAG_LEAD + 20, tile=T_RUBBLE, smooth=True, vrange=(0.3, 0.2))


# ---------------------------------------------------------------- vertex colour
def town_paint(m, kind):
    seed = int(m.rng.integers(1e6))

    def f(P, tags, N, col):
        z = P[:, 2]; n = vnoise(P, seed, 1.6); n2 = vnoise(P, seed + 3, 7.0); n3 = vnoise(P, seed + 9, 0.7)
        base = tags % CREV; crev = tags >= CREV
        R = np.zeros(len(P)); G = np.zeros(len(P)); B = np.zeros(len(P)); A = np.ones(len(P))
        stone = (base == TAG_SHEET) | (base == TAG_STONE)
        st = streaks(P, seed + 5, 7.0, 0 if kind != 'gable' else 0)
        if kind in ('wall', 'gable', 'corner', 'chimney'):
            # stone: splash-back dirt, green algae at the base, run-off streaks below the jetty and the sills, moss on ledges
            splash = np.clip((0.55 * (1 + 0.5 * n) - z) / 0.45, 0, 1)
            alg = np.clip((0.30 * (1 + 0.9 * n3 + 0.4 * n2) - z) / 0.3, 0, 1)
            jet = np.clip(1 - (GH - z) / 1.1, 0, 1) * st * 0.55 if kind != 'chimney' else 0.25 * st
            Rs = np.clip(0.75 * splash + jet + 0.12 + 0.12 * n + 0.9 * np.clip(n2 - 0.45, 0, 1) * (base == TAG_SHEET) * np.clip(1.4 - z / 1.6, 0.25, 1), 0, 1)      # dark open joints where the mortar has gone
            Gs = np.clip(0.8 * alg + 0.45 * (N[:, 2] > 0.6) * (base == TAG_STONE) * (z > 0.5) * (0.5 + 0.5 * n3), 0, 1)
            for (xa, xb, zt, k) in m.streak_src:
                inx = np.clip(1 - np.maximum(xa - P[:, 0], P[:, 0] - xb) / 0.12, 0, 1) * (P[:, 0] > xa - 0.12) * (P[:, 0] < xb + 0.12)
                run = np.clip(1 - (zt - z) / 1.3, 0, 1) * (z < zt + 0.02)
                Rs = np.clip(Rs + k * inx * run * (0.5 + 0.5 * st), 0, 1); Gs = np.clip(Gs + 0.35 * k * inx * run * (z < zt - 0.2), 0, 1)
            Bs = np.where(base == TAG_STONE, np.clip(0.8 + 0.2 * n2, 0, 1), np.clip(0.1 + 0.15 * n, 0, 1))
            if kind == 'chimney':
                Rs = np.clip(Rs + np.clip((z - 6.3) / 1.2, 0, 1) * 0.8, 0, 1)        # soot toward the top
                Gs = np.clip(Gs + 0.5 * (N[:, 2] > 0.5) + 0.25 * np.clip(n3, 0, 1), 0, 1)
            R = np.where(stone, Rs, R); G = np.where(stone, Gs, G); B = np.where(stone, Bs, B)
        tim = (base == TAG_TIMBER) | (base == TAG_END)
        # oak: silvered where the weather reaches it (outward and upward faces), dark under the jetty and in the joints, damp at the foot
        expo = np.clip(0.22 + 0.3 * n + 0.4 * (N[:, 2] > 0.3) + 0.12 * (N[:, 1] < -0.5) - 0.5 * (N[:, 2] < -0.4), 0, 1)
        dk = np.clip(0.22 + 0.25 * n2 + 0.45 * (N[:, 2] < -0.4) + 0.5 * np.clip((0.3 - z) / 0.3, 0, 1) + 0.25 * st * (N[:, 1] < -0.5), 0, 1)
        R = np.where(tim, dk, R); B = np.where(tim, expo, B); G = np.where(tim, np.clip(0.5 * (N[:, 2] > 0.7) * (0.4 + n3) + 0.5 * np.clip((0.25 - z) / 0.25, 0, 1), 0, 1), G)
        R = np.where(base == TAG_END, 0.8, R)
        pl = base == TAG_PLASTER
        zt = P[:, 2].max()
        Rp = np.clip(0.38 + 0.4 * n + 0.35 * n2 + 0.25 * n3 + 0.7 * st * np.clip(1 - (TH - z) / 0.6, 0, 1) * (z < TH + 0.05) + 0.5 * np.clip(1 - (z - (GH + JOIST + BRESS)) / 0.25, 0, 1) * (z < TH), 0, 1)
        if kind == 'gable':
            Rp = np.clip(Rp + 0.35 * np.clip((0.9 - z) / 0.6, 0, 1), 0, 1)
            for (xa, xb, zs, k) in m.streak_src:
                inx = (P[:, 0] > xa) & (P[:, 0] < xb)
                Rp = np.clip(Rp + k * inx * np.clip(1 - (zs - z) / 0.7, 0, 1) * (z < zs) * st, 0, 1)
        R = np.where(pl, Rp, R); G = np.where(pl, np.clip(0.5 * np.clip((0.75 - z) / 0.4, 0, 1) * (0.5 + n3), 0, 1) * (kind == 'gable'), G)
        B = np.where(pl, np.clip(0.15 + 0.2 * n3, 0, 1), B)
        if kind == 'door':
            sh = base == TAG_SHEET
            R = np.where(sh, np.clip(0.2 + 0.3 * n + 0.6 * np.clip((0.35 - z) / 0.35, 0, 1), 0, 1), R); B = np.where(sh, np.clip(0.3 + 0.3 * n, 0, 1), B)
        rf = base == TAG_ROOF
        if rf.any():
            # moss along the course butts and in the lee of the dormer; lichen spots on the faces; damp dark runs
            mm = np.clip(0.9 * n3 + 0.5 * n - 0.15, 0, 1)
            lee = np.zeros(len(P))
            if getattr(m, 'dormer_box', None):
                xa, xb, s0, s1 = m.dormer_box
                s = ((P[:, 1] - YE) * CP_ + (z - ZE) * SP_)
                dx = np.maximum(np.maximum(xa - P[:, 0], P[:, 0] - xb), 0)
                lee = np.clip(1 - dx / 0.4, 0, 1) * np.clip(1 - np.maximum(s0 - 0.5 - s, 0) / 0.5, 0, 1) * (s < s1 + 0.3)
            Gr = np.clip(np.where(crev, 1.3 * mm, 0.5 * np.clip(mm - 0.55, 0, 1)) + lee * np.where(crev, 0.9, 0.4), 0, 1)
            Rr = np.clip(0.25 + 0.3 * n + 0.45 * crev + 0.3 * st * (n3 < 0), 0, 1)
            Br = np.clip((n2 - 0.25) * 2.2, 0, 1) * (~crev) * 0.8
            R = np.where(rf, Rr, R); G = np.where(rf, Gr, G); B = np.where(rf, Br, B)
        pot = base == TAG_LEAD + 20                   # clay pots: sooty
        R = np.where(pot, 0.9, R); G = np.where(pot, 0.0, G); B = np.where(pot, 0.0, B)
        special = (base == TAG_IRON) | (base == TAG_LEAD) & (N[:, 0] * 0 == 0) & False
        A = np.where(base == TAG_IRON, 0.5, A); A = np.where(base == TAG_GLASS, 0.0, A)
        A = np.where(base == TAG_LEAD, 0.75, A)
        return np.stack([R, G, B, A], -1)
    return f


def modules(rows):
    out = []

    def mk(name, length=SEG, height=TH, cls='kit_piece', slots=('rubble', 'timber', 'plaster'), kind='wall'):
        m = Mod2('SM_Town_' + name, length, height, rows, cls, 'TownExteriors'); m.slots = list(slots); m.streak_src = []; m.dormer_box = None; m.floor0 = kind in ('wall', 'gable', 'corner', 'chimney')
        m.paint.append(town_paint(m, kind)); return m
    wall_ucx = lambda L: [([0, -WT / 2, 0], [L, WT / 2, GH]), ([0, YF - 0.1, GH], [L, WT / 2, TH])]

    def rec(m, fams, frames, note, **k):
        out.append(dict(m=m, families=fams, sprite_family='33 struct/outinn/oinn-', sprite_frames=frames, dresses=note, module_length_m=round(m.length, 3), **k))
    m = mk('Wall_Plain'); ground_wall(m, 0, SEG, None, (True, True)); upper(m, 0, SEG, win=(0.95, 1.6, GH + JOIST + BRESS + 0.3, TH - 0.36)); m.ucx = wall_ucx(SEG)
    tie_plate(m, 1.25, 1.75, -WT / 2 - 0.012)
    rec(m, ['town_wall_stone_window'], 'frames 17, 46 (blank bays between two quoin strips)', 'ground-floor rubble wall with dressed-stone pilasters at both ends, plinth course and an iron tie plate; jettied close-studded upper storey with a small two-light leaded window. NOTE: the class id says window, but these frames are blank bays: bind by sequence frame')
    for side in ('L', 'R'):
        m = mk('Wall_Window_' + side)
        o = (0.95, 2.05, 1.0, 2.25) if side == 'L' else (0.45, 1.55, 1.0, 2.25)
        ground_wall(m, 0, SEG, o, (side == 'L', side == 'R')); window(m, *o)
        upper(m, 0, SEG, brace=(0.12, 0.95) if side == 'L' else (2.4, 1.55)); m.ucx = wall_ucx(SEG)
        rec(m, ['town_wall_stone_window'], 'frames 1, 14-16, 35-37, 40-45 (100 px bays with a lattice window)', 'bay with a 1.1 x 1.25 m diamond-leaded two-light window (stone sill and lintel, oak frame, iron saddle bars) and one pilaster at its %s end; jettied upper storey with a raking brace. Choose L or R by the side the sprite frame has its quoin strip' % ('left' if side == 'L' else 'right'))
    m = mk('Wall_Door'); o = (0.7, 1.8, 0.0, 2.1)
    ground_wall(m, 0, SEG, o, (True, True), door=True)
    timber(m, [o[0] - 0.2, -WT / 2 - 0.03, 2.1], [o[1] + 0.2, -WT / 2 + 0.18, 2.32], 0.018, 0.004)                     # oak lintel
    timber(m, [o[0], -WT / 2 + 0.08, 0.0], [o[0] + 0.08, -WT / 2 + 0.2, 2.1], 0.01, 0.002); timber(m, [o[1] - 0.08, -WT / 2 + 0.08, 0.0], [o[1], -WT / 2 + 0.2, 2.1], 0.01, 0.002)
    dressed(m, [o[0] - 0.15, -WT / 2 - 0.55, 0.0], [o[1] + 0.15, -WT / 2 + 0.05, 0.15], 0.025, 0.007)                  # worn stone step
    lantern(m, 2.02, 2.42, -WT / 2 - 0.07)
    upper(m, 0, SEG)
    m.ucx = [([0, -WT / 2, 0], [o[0], WT / 2, GH]), ([o[1], -WT / 2, 0], [SEG, WT / 2, GH]), ([0, YF - 0.1, 2.1], [SEG, WT / 2, TH])]
    rec(m, ['town_wall_stone_door'], 'frames 3, 5, 6, 21, 23, 33, 34, 38, 39', 'bay with a 1.1 x 2.1 m door opening between two pilasters, oak lintel and jambs, worn stone step 0.55 m out from the wall, a wrought-iron lantern bracket right of the door; jettied upper storey. The leaf is the separate SM_Town_Door_Studded, hinge at x = 0.73 on the back of the jamb')
    NW = 64 * M_PER_PX
    m = mk('Wall_Narrow', NW); ground_wall(m, 0, NW, None, (True, False)); upper(m, 0, NW); m.ucx = wall_ucx(NW)
    rec(m, ['town_wall_stone_window'], 'frames 2, 11, 18, 19 (64 px corner pieces)', '1.6 m bay with one pilaster, for corners and short returns; yaw 90 degrees for the return wall')
    roof_ucx = [([0, YE, TH - 0.3], [SEG, YF + RUN * 0.5, TH + 0.1 + RUN * 0.5 * TP_]), ([0, YF + RUN * 0.5, TH], [SEG, RIDGE_Y, RIDGE_Z])]
    m = mk('Roof_Slope', slots=('shingle', 'timber'), kind='roof'); roof(m, 0, SEG); m.ucx = roof_ucx
    rec(m, ['town_roof_flat', 'town_roof_slope'], 'frames 12, 29, 30 (100x200 px) and 9, 26, 27 (100x150 px)', 'one bay of stone-slate roof slope at 42 degrees, one closed solid 8.5 cm thick: eaves 0.42 m in front of the jetty at %.2f m, ridge %.2f m behind the wall line at %.2f m; doubled eaves course, fascia, rafter feet; slipped, lifted and missing slates. Shares the wall pivot' % (ZE, RIDGE_Y, RIDGE_Z))
    m = mk('Roof_Slope_B', slots=('shingle', 'timber'), kind='roof'); roof(m, 0, SEG); m.ucx = roof_ucx
    rec(m, ['town_roof_flat', 'town_roof_slope'], 'variant of SM_Town_Roof_Slope for the same frames', 'second roof bay with different slates, defects and moss, so a run of bays does not repeat: list it as a variant of SM_Town_Roof_Slope in families.json')
    m = mk('Roof_Dormer', slots=('shingle', 'timber'), kind='roof'); roof(m, 0, SEG, dormer=True); m.ucx = roof_ucx
    rec(m, ['town_roof_dormer'], 'frames 13, 31, 32', 'the roof bay with a gabled dormer standing on it: oak front with a two-light leaded window, boarded cheeks, lead apron and soakers, its own slate roof with barge boards and a lead ridge')
    RL = 60 * M_PER_PX
    m = mk('Roof_RidgeCap', RL, 0.3, slots=('shingle', 'timber'), kind='roof'); ridge(m, RL); m.ucx = [([0, -0.25, -0.3], [RL, 0.25, 0.06])]
    rec(m, ['town_roof_ridge_cap'], 'frames 8, 25 (60x45 px)', '1.5 m of ridge: lapped stone ridge tiles on a ridge board. Pivot on the ridge line at its left end; sits at z = %.2f, %.2f m behind the front wall line' % (RIDGE_Z, RIDGE_Y))
    m = mk('Wall_GableEnd', DEPTH, RIDGE_Z, kind='gable'); gable_end(m)
    m.ucx = [([-WT / 2, -0.12, 0], [DEPTH + WT / 2, 0.1, TH])]
    m.hulls = [[[YF, -0.12, TH], [DEPTH - YF, -0.12, TH], [DEPTH / 2, -0.12, RIDGE_Z - 0.3], [YF, 0.1, TH], [DEPTH - YF, 0.1, TH], [DEPTH / 2, 0.1, RIDGE_Z - 0.3]]]
    rec(m, ['town_wall_gable_end'], 'frames 7, 10, 24 (92x200 px)', 'the whole end wall of a house, %.2f m between the long-wall centre lines: stone plinth, pegged box frame with St Andrew\'s crosses and a leaded window, jettied upper frame, tie beam, gable triangle with king post, collar and struts (the roof verge over it is SM_Town_Roof_Verge, placed at the same point). Bind ONE per house end (the sprite is a 92 px slice of the same wall): left end of a row at (0, %.2f, 0) yaw -90, right end at (row length, 0, 0) yaw +90' % (DEPTH, DEPTH))
    m = mk('Roof_Verge', DEPTH, RIDGE_Z, slots=('shingle', 'timber'), kind='roof'); verge(m)
    m.hulls = [[[YE, -0.44, ZE - 0.2], [DEPTH - YE, -0.44, ZE - 0.2], [DEPTH / 2, -0.44, RIDGE_Z], [YE, 0.0, ZE - 0.2], [DEPTH - YE, 0.0, ZE - 0.2], [DEPTH / 2, 0.0, RIDGE_Z]]]
    rec(m, [], 'the shingled verge drawn at the top of frames 7, 10, 24', 'roof verge for a gable end: 0.56 m strips of both slopes oversailing the wall by 0.3 m, barge boards with capping fillets and a finial post. Place at the same point and yaw as SM_Town_Wall_GableEnd')
    m = mk('Corner_Quoin', 0.8, TH, kind='corner'); corner_quoin(m); m.ucx = [([-WT / 2 - 0.08, -WT / 2 - 0.08, 0], [0.4, 0.4, GH])]
    rec(m, [], 'the pale quoin strip at the outer corner of frames 2, 11, 18, 19', 'outer corner of two stone bay rows: alternating long and short dressed quoins, jetty corner post on a dragon bracket. Not family-bound: place where two rows meet at a right angle (pivot on the meeting point of the wall centre lines, faces toward -X and -Y)')
    m = mk('Chimney_Stack', 1.15, 7.96, slots=('rubble',), kind='chimney'); chimney(m); m.ucx = [([-0.58, -0.76, 0], [0.58, 0, 3.2]), ([-0.45, -0.62, 3.2], [0.45, 0, 7.6])]
    rec(m, [], 'no sprite frame in family 33 (the town roofs show no stack); family 63 chimney_stone frame 13 (61x187 px) is the same object', 'external stone chimney stack, 7.6 m to the cap plus pots: battered base, two weathered offsets, drip course, cap slab, two sooted clay pots. Stands against a gable end or long wall (pivot at the centre of its back face on the ground)')
    m = mk('Door_Studded', 1.04, 2.04, cls='door', slots=('door',), kind='door'); door_leaf(m); m.ucx = [([0, -0.03, 0], [1.04, 0.03, 2.04])]
    rec(m, [], 'the door drawn inside the town_wall_stone_door frames', 'studded door leaf of seven separate oak planks, 1.04 x 2.04 m, ledges, strap hinges, 48 iron studs and a ring pull. Pivot on the hinge edge. Not family-bound: place in each Wall_Door opening')
    return out


def main_town():
    sc = new_scene()
    rows = board_rows('OakWeathered')
    mats = {'rubble': wmat('MI_Town_Rubble', 'TownRubble', dirt=(0.34, 0.29, 0.22), pale=(0.50, 0.47, 0.40), pale_amt=0.55),
            'timber': wmat('MI_Town_Oak', 'OakWeathered', dirt=(0.22, 0.16, 0.11), pale=(0.46, 0.45, 0.42), pale_amt=0.55, special=True, tint=(0.80, 0.62, 0.47, 1)),
            'plaster': wmat('MI_Town_Plaster', 'PlasterWall', dirt=(0.30, 0.24, 0.16), pale=(0.8, 0.78, 0.72), pale_amt=0.0, dirt_amt=0.95, tint=(0.86, 0.83, 0.76, 1)),
            'shingle': wmat('MI_Town_RoofShingle', 'RoofShingle', dirt=(0.36, 0.33, 0.28), moss=(0.04, 0.052, 0.02), pale=(0.62, 0.62, 0.50), pale_amt=0.6),
            'door': wmat('MI_Town_DoorPlanks', 'DoorPlanks', dirt=(0.3, 0.25, 0.2), special=True)}
    recs = export_modules(modules(rows), mats, OUT, 'TownExteriors.blend')
    json.dump(recs, open(os.path.join(OUT, 'modules.json'), 'w'), indent=1)
    print('TOWN DONE', len(recs))


main_town()
