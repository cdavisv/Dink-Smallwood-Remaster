"""Oak, weeping willow, dead leafless trees and bushes: space-colonisation skeleton, pipe-model radii, leaf-cluster / hanging-withe / twig cards."""
import numpy as np, math
from bl_tree import *

E = 3.0 / 2048
OAK_TILES = [(c * 0.5 + E, 1 - (r + 1) * 0.5 + E, (c + 1) * 0.5 - E, 1 - r * 0.5 - E) for r in range(2) for c in range(2)]
WIL_TILES = [(c * 0.25 + E, E, (c + 1) * 0.25 - E, 1 - E) for c in range(4)]
OAK_N = [OAK_TILES[0], OAK_TILES[3]]; OAK_LIGHT = OAK_TILES[1]; OAK_DARK = OAK_TILES[2]       # atlas tiles are graded: sunlit / neutral / interior
def U(x0, y0, x1, y1): return (x0 / 2 + E, y0 / 2 + E, x1 / 2 - E, y1 / 2 - E)                # understory atlas rect from metres (2 m sheet)
BUSH_T = [U(i * 0.5, 1.5, i * 0.5 + 0.5, 2.0) for i in range(3)]; TWIG_S = U(1.5, 1.5, 2.0, 2.0); TWIG_L = U(1.0, 0.0, 2.0, 0.6)
FERN_T = [U(0, 1.0, 1.0, 1.5), U(1.0, 1.0, 2.0, 1.5)]; GRASS_T = [U(i * 0.5, 0.6, i * 0.5 + 0.5, 1.0) for i in range(4)]; VINE_T = [U(0, 0.3, 1.0, 0.6), U(0, 0.0, 1.0, 0.3)]
BLOD = {0: dict(tr_sides=6, k=1, min_r=0.011, keep=1.0, scale=1.0, segs=1, sides=lambda r: 5 if r > 0.03 else (4 if r > 0.018 else 3), ds=lambda r: 0.18),
        1: dict(tr_sides=4, k=1, min_r=0.02, keep=0.5, scale=1.4, segs=1, sides=lambda r: 3, ds=lambda r: 0.3),
        2: dict(tr_sides=3, k=1, min_r=0.5, keep=0.2, scale=2.1, segs=1, sides=lambda r: 3, ds=lambda r: 0.5)}

OAK_TIP = 10; OAK_MID = 6; OAK_INNER = 3; OAK_PROTRUDE = 0.75        # v3 oak crown density
LOD = {0: dict(tr_sides=14, k=4, min_r=0.021, keep=1.0, scale=1.0, segs=2, sides=lambda r: 8 if r > 0.12 else (6 if r > 0.06 else (5 if r > 0.035 else 4)), ds=lambda r: max(0.3, min(0.9, r * 9))),
       1: dict(tr_sides=8, k=2, min_r=0.04, keep=0.5, scale=1.38, segs=1, sides=lambda r: 6 if r > 0.12 else 4, ds=lambda r: max(0.6, min(1.4, r * 14))),
       2: dict(tr_sides=6, k=1, min_r=0.085, keep=0.17, scale=2.2, segs=1, sides=lambda r: 4 if r > 0.12 else 3, ds=lambda r: 1.6)}

DLOD = {0: dict(tr_sides=12, k=4, min_r=0.0115, keep=1.0, scale=1.0, segs=1, sides=lambda r: 8 if r > 0.12 else (6 if r > 0.06 else (4 if r > 0.025 else 3)), ds=lambda r: max(0.3, min(0.9, r * 9))),
        1: dict(tr_sides=8, k=2, min_r=0.03, keep=0.55, scale=1.3, segs=1, sides=lambda r: 5 if r > 0.12 else 3, ds=lambda r: max(0.6, min(1.4, r * 14))),
        2: dict(tr_sides=6, k=1, min_r=0.07, keep=0.25, scale=1.9, segs=1, sides=lambda r: 4 if r > 0.12 else 3, ds=lambda r: 1.6)}
TREES = {
 'SM_Veg_Oak_Large_01': dict(kind='oak', seed=11, H=13.5, fork=2.6, r0=0.46, c=(0.0, 0.0, 7.5), rad=(4.7, 4.5, 4.7), n_attr=1000, lean=(0.03, 0.02), gaps=6, D=0.5),
 'SM_Veg_Oak_Large_02': dict(kind='oak', seed=29, H=10.6, fork=1.9, r0=0.5, c=(0.4, -0.3, 5.6), rad=(6.0, 5.2, 3.5), n_attr=950, lean=(0.06, -0.03), gaps=7, D=0.5, flat=True),
 'SM_Veg_Willow_01': dict(kind='willow', seed=41, H=9.4, fork=2.2, r0=0.36, c=(0.0, 0.0, 4.4), rad=(3.1, 3.1, 4.1), n_attr=520, bend=0.22, lean=(0.08, 0.03), gaps=2, D=0.45, hang=(1.8, 3.6), ground_clear=0.9),
 'SM_Veg_Willow_Large_01': dict(kind='willow', seed=57, H=11.6, fork=2.7, r0=0.46, c=(0.2, 0.0, 6.6), rad=(5.0, 4.7, 4.3), n_attr=640, bend=0.25, lean=(-0.08, 0.05), gaps=7, D=0.5, hang=(2.2, 6.0), ground_clear=0.5, clear_var=2.6),
 'SM_Veg_DeadTree_Dark_01': dict(kind='dead', bark='DarkBark', seed=71, H=10.0, fork=2.2, r0=0.34, c=(0.0, 0.0, 5.8), rad=(5.0, 4.6, 3.8), n_attr=640, lean=(0.05, 0.02), gaps=6, D=0.5, flat=True),
 'SM_Veg_DeadTree_DarkTall_01': dict(kind='dead', bark='DarkBark', seed=83, H=13.0, fork=3.0, r0=0.36, c=(0.0, 0.0, 8.0), rad=(3.6, 3.4, 5.0), n_attr=620, lean=(-0.03, 0.03), gaps=5, D=0.5),
 'SM_Veg_DeadTree_Frosted_01': dict(kind='dead', bark='FrostBark', frost=True, seed=97, H=8.0, fork=1.7, r0=0.2, c=(0.0, 0.0, 4.9), rad=(2.9, 2.7, 3.1), n_attr=330, lean=(0.04, -0.05), gaps=4, D=0.42, roots=1.5),
 'SM_Veg_Bush_Small_01': dict(kind='bush', seed=111, H=1.0, fork=0.14, r0=0.03, c=(0.0, 0.0, 0.42), rad=(0.62, 0.58, 0.5), n_attr=170, lean=(0, 0), gaps=1, D=0.15),
 'SM_Veg_Bush_Round_Medium_01': dict(kind='bush', seed=123, H=0.95, fork=0.14, r0=0.03, c=(0.0, 0.0, 0.4), rad=(0.68, 0.66, 0.48), n_attr=190, lean=(0, 0), gaps=0, D=0.15),
 'SM_Veg_Bush_Round_Large_01': dict(kind='bush', seed=137, H=1.3, fork=0.16, r0=0.04, c=(0.0, 0.0, 0.52), rad=(0.98, 0.9, 0.68), n_attr=300, lean=(0, 0), gaps=1, D=0.17),
 'SM_Veg_Bush_Wide_01': dict(kind='bush', seed=149, H=1.35, fork=0.16, r0=0.045, c=(0.0, 0.0, 0.5), rad=(1.35, 0.95, 0.72), n_attr=400, lean=(0, 0), gaps=2, D=0.17),
}

def envelope_points(P, rng):
    c = np.array(P['c']); rad = np.array(P['rad']); n = P['n_attr']
    ph = rng.uniform(0, 6.28, 6)
    def bump(d):
        az = np.arctan2(d[:, 1], d[:, 0]); el = np.arcsin(np.clip(d[:, 2], -1, 1))
        return 1 + 0.16 * np.sin(3 * az + ph[0]) * np.cos(el) + 0.12 * np.sin(5 * az + ph[1] + 2 * el) + 0.10 * np.sin(4 * el + ph[2] + az)
    d = rng.normal(0, 1, (n * 6, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    u = rng.random(n * 6)
    if P['kind'] == 'bush':
        rr = 0.55 + 0.45 * rng.random(n * 6); pts = c + d * rad * (rr * bump(d))[:, None]
        pts = pts[(pts[:, 2] > 0.14)]
        for _ in range(P['gaps']):
            g = pts[rng.integers(len(pts))]; pts = pts[np.linalg.norm(pts - g, axis=1) > 0.22]
        return pts[:n]
    if P['kind'] in ('oak', 'dead'):
        # lumpy crown: a union of offset sub-crowns (one per main limb) instead of a single ball
        rr = np.where(u < 0.72, 0.72 + 0.28 * rng.random(n * 6), rng.random(n * 6) ** 0.5 * 0.72)
        K = 6; boff = rng.normal(0, 1, (K, 3)); boff /= np.linalg.norm(boff, axis=1, keepdims=True); boff[:, 2] = np.abs(boff[:, 2]) * 0.8 - (0.25 if not P.get('flat') else 0.45)
        boff[0] = (0, 0, 0.35); bsz = rng.uniform(0.5, 0.68, K); bsz[0] = 0.62
        which = rng.integers(0, K, n * 6)
        pts = c + boff[which] * rad * 0.5 + d * rad * (rr * bsz[which] * bump(d))[:, None]
        ok = pts[:, 2] > P['fork'] + 0.4
        pts = pts[ok]
        for _ in range(P['gaps']):
            g = pts[rng.integers(len(pts))]; pts = pts[np.linalg.norm(pts - g, axis=1) > rng.uniform(0.9, 1.5)]
        return pts[:n]
    else:
        rr = np.where(u < 0.8, 0.8 + 0.2 * rng.random(n * 6), 0.4 + 0.4 * rng.random(n * 6))
        ok = d[:, 2] > (0.05 if P.get('umbrella') else -0.15)
    pts = c + d * rad * (rr * bump(d))[:, None]
    ok &= pts[:, 2] > P['fork'] + 0.4
    pts = pts[ok]
    for _ in range(P['gaps']):   # sky holes
        g = pts[rng.integers(len(pts))]; pts = pts[np.linalg.norm(pts - g, axis=1) > rng.uniform(1.0, 1.7)]
    return pts[:n]

def colonize(P, rng):
    H, fork = P['H'], P['fork']; D = P['D']
    nodes = []; parent = []
    nz = int(fork / D) + 1; lx, ly = P['lean']; ph = rng.uniform(0, 6.28, 2)
    for i in range(nz + 1):
        z = fork * i / nz
        bd = P.get('bend', 0.12); nodes.append([lx * z + bd * math.sin(z * 0.9 + ph[0]), ly * z + bd * math.sin(z * 0.8 + ph[1]), z]); parent.append(i - 1)
    nodes = np.array(nodes); nodes[:, :2] -= nodes[0, :2]
    A = envelope_points(P, rng)
    di, dk = 4.5 * D / 0.5, D * 1.1
    trop = np.array([0, 0, {'oak': 0.18, 'dead': 0.1, 'bush': 0.1}.get(P['kind'], 0.05)])
    nodes = list(nodes)
    for it in range(160):
        Nn = np.array(nodes)
        dmat = np.linalg.norm(A[:, None, :] - Nn[None, :, :], axis=2)
        near = dmat.argmin(1); dmin = dmat.min(1)
        A = A[dmin > dk]; near = near[dmin > dk]; dmin = dmin[dmin > dk]
        if len(A) == 0: break
        act = dmin < (di if it > 3 else 99)
        if not act.any(): break
        new = 0
        for ni in np.unique(near[act]):
            sel = act & (near == ni)
            v = A[sel] - Nn[ni]; v /= np.linalg.norm(v, axis=1, keepdims=True)
            d = nrm(v.sum(0) + trop + rng.normal(0, 0.12, 3))
            if parent[ni] >= 0:   # limit turning angle: keeps limbs sweeping instead of zig-zag
                pd = nrm(Nn[ni] - Nn[parent[ni]])
                if np.dot(d, pd) < 0.2: d = nrm(d + pd * 0.6)
            p = Nn[ni] + d * D
            if np.min(np.linalg.norm(Nn - p, axis=1)) < D * 0.45: continue
            nodes.append(p); parent.append(int(ni)); new += 1
        if new == 0: break
    return np.array(nodes), np.array(parent)

def skeleton(P):
    rng = np.random.default_rng(P['seed'])
    nodes, parent = colonize(P, rng)
    n = len(nodes); children = [[] for _ in range(n)]
    for i in range(1, n): children[parent[i]].append(i)
    nz0 = int(P['fork'] / P['D']) + 1
    for _ in range(3):   # relax kinks left by the fixed step length
        new = nodes.copy()
        for i in range(nz0 + 1, n):
            if children[i]: new[i] = 0.5 * nodes[i] + 0.25 * nodes[parent[i]] + 0.25 * np.mean(nodes[children[i]], axis=0)
        nodes = new
    e = 2.35 if P['kind'] == 'oak' else 2.2
    r = np.zeros(n)
    for i in range(n - 1, -1, -1):
        r[i] = 0.011 if not children[i] else sum(r[c] ** e for c in children[i]) ** (1 / e)
    nz = int(P['fork'] / P['D']) + 1
    r = 0.011 + (r - 0.011) * (P['r0'] - 0.011) / (r[nz] - 0.011)      # radius at the fork = r0, tips stay twig-thin
    # trunk taper + root flare below the fork
    for i in range(nz + 1):
        z = nodes[i][2]; f = z / P['fork']; rtop = max(r[c] for c in children[nz]) if children[nz] else P['r0']       # the trunk top must meet the leading limb exactly
        r[i] = max(P['r0'] * 1.1, rtop * 1.12) * (1 - f) + rtop * f          # no flare here: root_base models the buttresses
    chains = []
    stack = [(0, None)]
    while stack:
        start, par = stack.pop()
        idx = [start] if par is None else [par, start]
        cur = start
        while children[cur]:
            ch = sorted(children[cur], key=lambda c: -r[c]); nxt = ch[0]
            for o in ch[1:]: stack.append((o, cur))
            idx.append(nxt); cur = nxt
        rr = r[idx].copy()
        if par is not None: rr[0] = rr[1] * 1.0
        if par is None and len(idx) > nz + 3:      # the bole runs on as ONE tube into the leading limb (no ring at the fork); split where it has thinned
            cut = nz + 2
            while cut < len(idx) - 2 and rr[cut] > 0.5 * P['r0']: cut += 1
            chains.append(dict(idx=idx[:cut + 1], pts=nodes[idx[:cut + 1]], r=rr[:cut + 1], trunk=True, par_r=0, phase=0.0))
            chains.append(dict(idx=idx[cut:], pts=nodes[idx[cut:]], r=rr[cut:], trunk=False, par_r=0.0, phase=rng.random()))
        else:
            chains.append(dict(idx=idx, pts=nodes[idx], r=rr, trunk=par is None, par_r=r[par] if par is not None else 0, phase=rng.random()))
    # per-node phase: inherit from the first-order limb
    tips = [i for i in range(n) if not children[i]]
    return dict(nodes=nodes, parent=parent, r=r, children=children, chains=chains, tips=tips, P=P, rng_seed=P['seed'] + 1, nz=nz)

def build(name, lod):
    if TREES[name]['kind'] == 'bush':
        import veg_bush; return veg_bush.build(name, lod)       # v2 bushes: stems from the ground, leaves at every depth
    P = TREES[name]; S = skeleton(P); kind = P['kind']; C = (BLOD if kind == 'bush' else (DLOD if kind == 'dead' else LOD))[lod]; mb = MeshB(); H = P['H']
    rng = np.random.default_rng(S['rng_seed']); nodes = S['nodes']; r = S['r']; nz = S['nz']
    cc = np.array(P['c']); radv = np.array(P['rad'])
    tz = nodes[:nz + 1, 2]
    def axis(z): return np.array([np.interp(z, tz, nodes[:nz + 1, 0]), np.interp(z, tz, nodes[:nz + 1, 1]), z])
    def rfun(z): return float(np.interp(z, tz, r[:nz + 1]))
    knots = [(rng.uniform(min(0.8, P['fork'] * 0.5), P['fork'] + 0.3), rng.uniform(0, 6.28), rng.uniform(0.08, 0.16)) for _ in range(4)]
    for ch in S['chains']:
        rmax = ch['r'][1] if len(ch['r']) > 1 else ch['r'][0]
        if not ch['trunk'] and rmax < C['min_r']: continue
        pts = chaikin(ch['pts'], 2); rr = np.interp(np.linspace(0, 1, len(pts)), np.linspace(0, 1, len(ch['r'])), ch['r'])
        if ch['trunk'] and kind != 'bush':
            circ = 2 * math.pi * P['r0'] * 1.1; urep = 2 if circ > 1.8 else 1; tile_len = circ / urep
            top = max(0.6, tile_len / 2)
            mb.root_base(axis, rfun, P['seed'], lod, top=top, urep=urep, strength=P.get('roots', 1.0))
            t0 = top; k0 = int(np.argmax(pts[:, 2] > top + 0.05))
            rj = rfun(t0) * (1 + 0.22 * math.exp(-top / 0.4))
            pts = np.vstack([(axis(t0) - np.array([0, 0, 0.07]))[None, :], axis(t0)[None, :], pts[k0:]]); rr = np.concatenate([[rj, rj], rr[k0:]])       # 7 cm lap inside the base surface
            p2, r2 = resample(pts, rr, tile_len / C['k']); zt = p2[:, 2]
            def radial(i, a):
                if i <= 1: return 1.0
                t = 0.03 * math.sin(3 * a + zt[i] * 0.7)
                for zk, ak, amp in knots:
                    d = (a - ak + math.pi) % (2 * math.pi) - math.pi; t += amp * math.exp(-((zt[i] - zk) / 0.22) ** 2 - (d / 0.5) ** 2)
                return 1 + t
            mb.tube(p2, r2, C['tr_sides'], 'body', urep, tile_len, wind=(0, 0, 0, 0), wind1=(p2[-1][2] / H, 0, 0, 0.3), radial=radial, cap=True)
        else:
            p2, r2 = resample(pts, rr, C['ds'](rmax))
            keepn = max(2, int(np.sum(r2 > C['min_r'] * 0.55)) + 1); p2 = p2[:keepn]; r2 = r2[:keepn].copy()
            s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p2, axis=0), axis=1))])
            if ch['par_r'] > 0: r2 = r2 * (1 + 0.6 * np.exp(-s / (0.6 * ch['par_r'] + 0.05)))   # branch collar
            if ch['trunk']: p2[0, 2] = -0.04
            sides = C['sides'](rmax); circ = 2 * math.pi * rmax
            band = 'body' if rmax > 0.16 else 'limb'
            mb.tube(p2, r2, sides, band, 1, max(0.3, circ), wind=(p2[0][2] / H, ch['phase'], 0, 0.1), wind1=(p2[-1][2] / H, ch['phase'], 0, 1.0), cap=True)
    # foliage
    sc = C['scale']; par = S['parent']; upv = np.array([0, 0, 1.0])
    thr = 0.03 if kind != 'bush' else 0.02
    leafy = [i for i in range(len(nodes)) if (r[i] < thr and nodes[i][2] > P['fork'] + (0.8 if kind != 'bush' else 0.05))]
    for i in leafy:
        p = nodes[i]; bd = nrm(p - nodes[par[i]]); out = nrm(p - cc); tip = not S['children'][i]
        wind = (p[2] / H, (i * 0.618) % 1.0, 0, 1.0)
        if kind == 'oak':
            # v3 crown: about twice the clusters at 55-80 % of the old size, spread through the twig's volume instead of stacked on its node
            rf = float(np.linalg.norm((p - cc) / radv))                 # 0 centre .. ~1 crown surface
            ncard = OAK_TIP if tip else OAK_MID
            for q in range(ncard):
                key = rng.random(); d = nrm(bd * 0.5 + out * 0.6 + rng.normal(0, 0.6, 3)); L = rng.uniform(0.46, 0.78); droop = rng.uniform(0.1, 0.5)
                w = nrm(np.cross(d, out) + rng.normal(0, 0.5, 3)); flip = rng.random() < 0.5; u = rng.random(); mat = 1
                off = rng.normal(0, 0.2, 3) - bd * rng.uniform(0.0, 0.35)
                lit = 0.55 * (0.5 + 0.5 * out[2]) + 0.45 * min(rf, 1.0)
                if rf < 0.55 or out[2] < -0.25: tl = OAK_DARK if u < 0.75 else OAK_N[rng.integers(2)]      # shaded interior / underside
                elif lit > 0.68: tl = OAK_LIGHT if u < 0.26 else OAK_N[rng.integers(2)]                    # sunlit top and shoulders
                else: tl = OAK_N[rng.integers(2)] if u < 0.74 else (OAK_DARK if u < 0.93 else OAK_LIGHT)
                if tip and q == 0 and rng.random() < 0.03: tl = TWIG_S; mat = 2; L *= 0.9                  # a few dead twigs
                if key < C['keep']:
                    mb.card(p + off - d * (0.1 + L * (sc - 1) * 0.5), d, w, L * sc, L * sc, tl, C['segs'], 1, droop, 0, cc + (p - cc) * 0.35, 0.7, wind, mat, flip)
            u2 = rng.random(); key = rng.random(); dj = rng.normal(0, 0.3, 3); L = rng.uniform(0.42, 0.64); flip = rng.random() < 0.5; wj = rng.normal(0, 0.5, 3); dr = rng.uniform(0.0, 0.35); elen = rng.uniform(0.35, 0.72); mj = rng.normal(0, 0.03, 3); u3 = rng.random(); ti = rng.integers(2)
            if tip and rf > 0.8 and u2 < OAK_PROTRUDE:               # a twig standing clear of the crown outline: thin wood plus its own small cluster
                d = nrm(out * 0.9 + bd * 0.4 + dj); e = p + d * elen
                if key < C['keep'] * 1.6:
                    if lod == 0: mb.tube(np.array([p, (p + e) / 2 + mj, e]), [0.021, 0.015, 0.009], 3, 'limb', 1, 0.4, wind=wind, wind1=wind, cap=False)
                    mb.card(e - d * (0.18 + L * (sc - 1) * 0.5), d, nrm(np.cross(d, out + wj) + 1e-6), L * sc, L * sc, OAK_LIGHT if out[2] > 0.2 and u3 < 0.3 else OAK_N[ti], C['segs'], 1, dr, 0, cc + (p - cc) * 0.35, 0.7, wind, 1, flip)
                    w2 = nrm(np.cross(d, nrm(np.cross(d, out + wj) + 1e-6)))                # second card across the first: the protruding cluster has volume from every side
                    mb.card(e - d * (0.14 + L * (sc - 1) * 0.5), d, w2, L * sc * 0.9, L * sc * 0.9, OAK_N[1 - ti], 1, 1, dr, 0, cc + (p - cc) * 0.35, 0.7, wind, 1, not flip)
        elif kind == 'dead':
            for q in range(4 if tip else 2):
                key = rng.random(); d = nrm(bd + rng.normal(0, 0.6, 3) + upv * 0.15); big = rng.random() < 0.6; L = rng.uniform(0.9, 1.5) if big else rng.uniform(0.5, 0.8)
                w = nrm(np.cross(d, out) + rng.normal(0, 0.6, 3))
                if key < C['keep']:
                    mb.card(p - d * 0.05, d, w, L * sc, L * sc * (0.6 if big else 1.0), TWIG_L if big else TWIG_S, 1, 1, rng.uniform(-0.1, 0.25), 0, cc, 0.5, wind, 1, rng.random() < 0.5)
        elif kind == 'bush':
            for q in range(4 if tip else 3):
                key = rng.random(); d = nrm(bd * 0.4 + out * 0.8 + rng.normal(0, 0.5, 3)); L = rng.uniform(0.34, 0.52)
                w = nrm(np.cross(d, out) + rng.normal(0, 0.6, 3))
                if key < C['keep']:
                    mb.card(p - d * (0.08 + L * (sc - 1) * 0.5), d, w, L * sc, L * sc, BUSH_T[rng.integers(3)], C['segs'], 1, rng.uniform(0.0, 0.5), 0, cc * np.array([1, 1, 0.3]), 0.75, wind, 1, rng.random() < 0.5)
        else:
            hmin, hmax = P['hang']
            ncard = 4 if tip else 3
            rad_o = nrm(np.array([out[0], out[1], 0]) + 1e-6); tang = np.cross(upv, rad_o)
            for q in range(ncard):
                key = rng.random(); L = rng.uniform(hmin, hmax) * rng.uniform(0.6, 1.0)
                L = min(L, max(1.0, p[2] - P['ground_clear'] - rng.uniform(0, P.get('clear_var', 0.8))))
                yaw = rng.uniform(-1.2, 1.2); w = nrm(tang * math.cos(yaw) + rad_o * math.sin(yaw))
                off = rng.normal(0, 0.18, 3) * np.array([1, 1, 0.3]); flip = rng.random() < 0.5; wr = rng.uniform(0.9, 1.15); lift = rng.uniform(-0.15, 0.2)
                d = nrm(-upv + rad_o * rng.uniform(0.0, 0.3) + bd * 0.25); o = p + off + upv * 0.12; t2 = WIL_TILES[rng.integers(3)]
                while L > 0.25:                                  # long curtains are chained strips; leaves keep their real size
                    L1 = min(L, 2.45); tl = WIL_TILES[rng.integers(3)] if L1 > 1.3 else WIL_TILES[3]
                    ssc = min(max(L1 / 2.0, 1.0), 1.22); fr = min(1.0, L1 / (2.0 * ssc)); tl = (tl[0], tl[3] - (tl[3] - tl[1]) * fr, tl[2], tl[3])
                    if key < C['keep']:
                        mb.card(o, d, w, L1, 0.5 * ssc * wr * sc, tl, max(1, C['segs'] + (1 if lod == 0 else 0)), 1, 0.35, 0, cc + (p - cc) * 0.2 + upv * 1.0, 0.6, wind, 1, flip, lift=lift, uvaxis='v')
                    o = o + nrm(d - upv * 0.3) * (L1 * 0.68); d = nrm(-upv + rad_o * 0.05); L -= L1 * 0.68; lift = 0.0      # overlap: the strip's withes thin out toward its end
                    if L < 0.9: break
    if kind == 'oak':
        inner = [i for i in range(len(nodes)) if 0.03 <= r[i] < 0.10 and nodes[i][2] > P['fork'] + 1.0]
        for i in inner:
            p = nodes[i]; out = nrm(p - cc); rf = float(np.linalg.norm((p - cc) / radv)); wind = (p[2] / H, (i * 0.618) % 1.0, 0, 0.6)
            for q in range(OAK_INNER):
                key = rng.random(); d = nrm(rng.normal(0, 1, 3) + upv * 0.3 + out * 0.3); L = rng.uniform(0.6, 0.95); off = rng.normal(0, 0.3, 3); w = nrm(np.cross(d, rng.normal(0, 1, 3))); flip = rng.random() < 0.5
                tl = OAK_DARK if rng.random() < 0.85 else OAK_N[rng.integers(2)]; dr = rng.uniform(0.0, 0.4)
                if key < C['keep'] and rf < 0.9:
                    mb.card(p + off - d * (0.1 + L * (sc - 1) * 0.5), d, w, L * sc, L * sc, tl, 1, 1, dr, 0, cc + (p - cc) * 0.35, 0.7, wind, 1, flip)
    recenter(mb, xy=False)
    print('CARDTRIS', sum(len(f) - 2 for f, m in zip(mb.faces, mb.mat) if m >= 1), 'woodtris', sum(len(f) - 2 for f, m in zip(mb.faces, mb.mat) if m == 0), 'nodes', len(nodes), 'leafy', len(leafy))
    und = lambda: game_mat('MI_Veg_Understory', 'T_Veg_Understory', alpha=True, translucency=0.25)
    if kind == 'oak': mats = [game_mat('MI_Veg_OakBark', 'T_Veg_OakBark', basemask=True), game_mat('MI_Veg_OakLeaves', 'T_Veg_OakLeaves', alpha=True, translucency=0.35), und()]
    elif kind == 'willow': mats = [game_mat('MI_Veg_WillowBark', 'T_Veg_WillowBark', basemask=True), game_mat('MI_Veg_WillowLeaves', 'T_Veg_WillowLeaves', alpha=True, translucency=0.35)]
    elif kind == 'dead':
        frost = P.get('frost'); mats = [game_mat(f"MI_Veg_{P['bark']}", f"T_Veg_{P['bark']}", basemask=not frost),
                                        game_mat('MI_Veg_Understory_Frost', 'T_Veg_Understory', alpha=True, tint=(2.6, 2.8, 3.2)) if frost else und()]
    else: mats = [game_mat('MI_Veg_DarkBark', 'T_Veg_DarkBark'), und()]
    ob = mb.build(f'{name}_LOD{lod}', mats); ob['trunk_r'] = P['r0'] * 1.2
    return ob
