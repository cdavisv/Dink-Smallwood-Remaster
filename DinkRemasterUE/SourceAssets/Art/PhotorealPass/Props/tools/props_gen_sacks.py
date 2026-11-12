# Round-2 generators: jute sacks, shaped by cloth simulation (pressure = the grain inside): a full sack lying on its side and a feed
# sack stood on end with a tied neck. exec'd by props_bake.py after props_gen_bed.py (uses cloth_sim, sheet_solid, sel4, m_cloth).
_FLOOR = ([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [(0, 1, 2, 3)])


def _fit(P, lo, hi, tol=0.25):
    """scale and move the simulated points into the round-1 bounds (kept so placements still fit)"""
    a, b_ = P.min(0), P.max(0); k = (np.array(hi) - np.array(lo)) / (b_ - a); print('SIM FIT', np.round(b_ - a, 3), 'scale', np.round(k, 3))
    k = np.clip(k, 1 - tol, 1 + tol); return (P - a) * k + np.array(lo)


def sack_lying(b):
    """SM_Sack_Grain_PR: a full grain sack on its side, 0.97 x 0.69 x 0.26 m, mouth (+X) rolled and sewn with twine"""
    hi = b.hi; nx, ny = 52, 38; LX, LY = 1.06, 0.78
    PX, PY = np.meshgrid(np.linspace(-LX / 2, LX / 2, nx), np.linspace(-LY / 2, LY / 2, ny))
    inner = np.ones((ny, nx), bool); inner[0, :] = inner[-1, :] = inner[:, 0] = inner[:, -1] = False
    it = np.arange(ny * nx).reshape(ny, nx); ib = np.full((ny, nx), -1); ib[inner] = ny * nx + np.arange(inner.sum()); ib[~inner] = it[~inner]
    edge = np.minimum(np.minimum(PX + LX / 2, LX / 2 - PX), np.minimum(PY + LY / 2, LY / 2 - PY)); bulge = 0.02 * np.sqrt(np.clip(edge / 0.08, 0, 1))
    P0 = np.stack([PX, PY, 0.2 + bulge + 0.003 * vnoise(np.stack([PX, PY, 0 * PX], -1).reshape(-1, 3), 3, 7.0).reshape(PX.shape)], -1)
    Vt = P0.reshape(-1, 3); Vb = np.stack([PX, PY, 0.2 - bulge], -1)[inner]
    F = grid_faces(ny, nx) + [(ib[j, i], ib[j + 1, i], ib[j + 1, i + 1], ib[j, i + 1]) for j in range(ny - 1) for i in range(nx - 1)]
    P = cloth_sim('sack_lying', np.concatenate([Vt, Vb]), F, [_FLOOR], frames=70, pressure=45.0, mass=0.4, bend=0.4, stiff=18.0, grow=0.04)
    P = _fit(P, [-0.47, -0.347, 0.0], [0.5, 0.345, 0.257])
    Gt = P[:ny * nx].reshape(ny, nx, 3); Gb = P[ib.ravel()].reshape(ny, nx, 3); uv = np.stack([PX, PY], -1)
    st = b.d(3, 1); sel = (lambda G: sel4(G, st)) if st > 1 else (lambda G: G)
    if not hi:                                                # the game mesh keeps a wedge of thickness at the seams so its LODs stay closed solids
        Gb = Gb.copy(); Gb[..., 2] = np.minimum(Gb[..., 2], Gt[..., 2] - 0.02 * np.clip(edge / 0.06, 0, 1)); Gb[..., 2] = np.maximum(Gb[..., 2], 0.0)
    sheet_solid(b, sel(Gt), sel(Gb), sel(uv), 'jute', rim=False)
    seam = Gt[:, -1]                                           # the mouth: a rolled hem along the +X edge, whipped with twine
    b.tube([p + [0.004, 0, 0] for p in seam[::b.d(6, 1)]], b.d(0.011, 0.009), sides=b.d(5, 10), mat='jute')
    if hi:
        for k in range(3, ny - 3, 3):
            p = seam[k]; q = seam[k + 1]
            ring = [p + [0.004 + 0.0125 * math.cos(t), (q[1] - p[1]) * t / 6.28, 0.0125 * math.sin(t)] for t in np.linspace(0, 6.28, 10)]
            b.tube(ring, 0.0022, sides=5, mat='twine')
        tail = seam[3]; b.tube(resamp([tail + [0.01, 0, 0.01], tail + [0.04, -0.03, 0.02], tail + [0.06, -0.07, -0.01], tail + [0.05, -0.11, -0.04]], 4), 0.0022, sides=5, mat='twine')
        for (row, s_) in ((Gt[0], 1), (Gt[-1], -1)):          # side seams: a raised sewn ridge
            b.tube([p + [0, -s_ * 0.002, 0] for p in row[::1]], 0.004, sides=6, mat='jute')
    return {}


def sack_standing(b):
    """SM_FeedSack_Jute_PR: a feed sack stood on end, 0.75 x 0.57 x 0.77 m: weight settled to the bottom, neck gathered and whipped with
    twine, a ruff of loose cloth above the tie"""
    hi = b.hi; r = b.rng; n = 72; ky = 0.76
    prof = [(0.03, 0.012), (0.12, 0.01), (0.22, 0.012), (0.3, 0.04), (0.335, 0.12), (0.34, 0.25), (0.33, 0.38), (0.29, 0.48), (0.2, 0.555), (0.1, 0.6), (0.065, 0.625)]
    pr = []
    for a_, b_ in zip(prof[:-1], prof[1:]):
        m = max(2, int(np.hypot(b_[0] - a_[0], b_[1] - a_[1]) / 0.022)); pr += [(a_[0] + (b_[0] - a_[0]) * t, a_[1] + (b_[1] - a_[1]) * t) for t in np.linspace(0, 1, m + 1)[:-1]]
    pr.append(prof[-1]); m = len(pr); arc = np.concatenate([[0], np.cumsum([np.hypot(pr[i + 1][0] - pr[i][0], pr[i + 1][1] - pr[i][1]) for i in range(m - 1)])])
    V = []; F = []
    for i, (q, z) in enumerate(pr):
        for k in range(n):
            a = 2 * math.pi * k / n; pl = 1 + 0.1 * math.sin(a * 9 + 1.0) * np.clip((z - 0.45) / 0.15, 0, 1)             # pleats start toward the neck
            V.append((q * pl * math.cos(a), q * pl * ky * math.sin(a), z + 0.02))
    for i in range(m - 1):
        for k in range(n):
            k1 = (k + 1) % n; F.append((i * n + k, i * n + k1, (i + 1) * n + k1, (i + 1) * n + k))
    c0 = len(V); V.append((0, 0, 0.032)); F += [(c0, (k + 1) % n, k) for k in range(n)]                                   # bottom fan
    c1 = len(V); V.append((0, 0, pr[-1][1] + 0.02)); F += [(c1, (m - 1) * n + k, (m - 1) * n + (k + 1) % n) for k in range(n)]   # diaphragm at the tie (simulation only)
    pin = list(range((m - 1) * n, m * n)) + [c1]
    P = cloth_sim('sack_standing', np.array(V), F, [_FLOOR], frames=70, pressure=7.0, mass=0.5, bend=0.5, stiff=18.0, grow=0.05, pin=pin)
    zr = P[(m - 1) * n:m * n, 2].mean()
    P = _fit(P, [-0.365, -0.283, 0.0], [0.37, 0.275, zr])
    G = P[:m * n].reshape(m, n, 3); G = np.concatenate([G, G[:, :1]], 1)                                                  # close the seam column
    U = np.stack([np.tile(np.linspace(0, 2 * math.pi * 0.3, n + 1), (m, 1)), np.tile(arc[:, None], (1, n + 1))], -1)
    if not hi:
        G = sel4(G, 3); U = sel4(U, 3)
    mm, nn = G.shape[:2]; b.uvoff = False
    b.add(G.reshape(-1, 3), grid_faces(mm, nn), 'jute', U.reshape(-1, 2)); b.uvoff = True
    ring = G[0, :-1]; cb = P[c0]                                                                                          # the bottom, its own chart
    b.add(np.concatenate([[cb], ring]), [(0, 1 + (k + 1) % (nn - 1), 1 + k) for k in range(nn - 1)], 'jute', [(0, 0)] + [(p[0] - cb[0], p[1] - cb[1]) for p in ring])
    neck = G[-1, :-1]; cn = neck.mean(0); b.add(np.concatenate([[cn], neck]), [(0, 1 + k, 1 + (k + 1) % (nn - 1)) for k in range(nn - 1)], 'jute', [(0, 0)] + [(p[0] - cn[0], p[1] - cn[1]) for p in neck])
    rn = float(np.linalg.norm(neck[:, :2] - cn[:2], axis=1).mean())
    ns = b.d(24, 96); ruff = [(rn * 0.75, -0.012), (rn, 0.0), (rn * 1.25, 0.03), (rn * 2.1, 0.085), (rn * 2.6, 0.125), (rn * 2.7, 0.135), (rn * 2.45, 0.128), (rn * 1.9, 0.085), (rn * 1.0, 0.035), (rn * 0.5, 0.03)]

    def gather(Q):                                              # the ruff: loose cloth above the tie, gathered in uneven folds, flopping to one side
        a = np.arctan2(Q[:, 1], Q[:, 0]); h = np.clip(Q[:, 2] / 0.13, 0, 1); rr_ = np.hypot(Q[:, 0], Q[:, 1])
        k = 1 + h * (0.22 * np.sin(a * 7 + 0.6) + 0.12 * np.sin(a * 13 + 2.0) + 0.1 * vnoise(Q, 9, 18.0))
        return np.c_[Q[:, 0] * k + 0.035 * h ** 2, Q[:, 1] * k * 0.85, Q[:, 2] - 0.03 * h ** 2 * np.cos(a) + 0.012 * h * np.sin(a * 5)] + cn
    b.lathe(ruff, n=ns, mat='jute', sub=b.d(1, 3), deform=gather)
    for k in range(b.d(1, 5)):                                  # the tie: turns of twine whipped round the neck
        zz = cn[2] + 0.004 + 0.0045 * k * b.d(0, 1)
        b.tube([[cn[0] + (rn * 1.08 + 0.003) * math.cos(t), cn[1] + (rn * 1.08 + 0.003) * 0.9 * math.sin(t), zz + 0.003 * math.sin(t * 2 + k)] for t in np.linspace(0, 2 * math.pi, b.d(12, 40) + 1)[:-1]],
               b.d(0.009, 0.0032), sides=b.d(5, 6), mat='twine', closed=True, up=[0, 0, 1])
    if hi:
        b.tube([p * [1.004, 1.004, 1.0] for p in G[:, 0]], 0.0045, sides=6, mat='jute')                                    # side seam
        t0 = cn + [rn * 1.1, 0, 0.01]; b.tube(resamp([t0, t0 + [0.03, -0.02, -0.02], t0 + [0.045, -0.03, -0.07], t0 + [0.04, -0.035, -0.12]], 4), 0.003, sides=5, mat='twine')
    return {}


def sack_mats():
    return {'jute': m_cloth('H_jute', 'hessian_230', 0.34, (0.13, 0.075, 0.035), (0.5, 0.34, 0.17), grime=1.2, rough=(0.82, 0.98)),
            'twine': m_plain('H_twine', (0.16, 0.12, 0.07), (0.38, 0.3, 0.19), 0.85, 0.95, scale=300.0, bump=0.0006)}


_SK = dict(cls='prop', px=2048, mats=sack_mats, slots=None, extrude=0.025, maxdist=0.09, third_party=['hessian_230'], sharp=50.0, int_watts=25.0)
ASSETS['SM_Sack_Grain_PR'] = dict(_SK, fn=sack_lying, slots=[('MI_Sack_Grain', 'opaque', None)], int_light=(0.8, -0.7, 0.9),
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.12), 120), 'close': ((0.85, -1.1, 0.95), (0.05, 0, 0.12), 35), 'int': ((0.85, -1.1, 0.95), (0.05, 0, 0.12), 35)})
ASSETS['SM_FeedSack_Jute_PR'] = dict(_SK, fn=sack_standing, slots=[('MI_FeedSack_Jute', 'opaque', None)], int_light=(0.8, -0.7, 1.1),
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.38), 120), 'close': ((0.8, -1.15, 1.2), (0, 0, 0.4), 35), 'int': ((0.8, -1.15, 1.2), (0, 0, 0.4), 35)})
