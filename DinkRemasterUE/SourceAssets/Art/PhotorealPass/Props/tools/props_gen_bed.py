# Round-2 generator: the oak bed. The blanket and the pillow are Blender cloth simulations (cached in _build/bake/cache) over a
# straw tick; the same simulated grids feed the high source (full resolution) and the game mesh (every 4th row).
# exec'd by props_bake.py (uses MB, NT, m_wood, vnoise, fbm, ASSETS, BK).
_SIMC = os.path.join(BK, 'cache'); os.makedirs(_SIMC, exist_ok=True)


def _tmp_ob(name, V, F):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(int(i) for i in f) for f in F]); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o


def cloth_sim(key, V, F, colliders, frames=70, pressure=None, self_col=False, mass=0.25, bend=0.6, stiff=12.0, friction=25.0, grow=0.0, pin=None):
    """drop the mesh V, F as cloth onto the collider meshes [(V, F)]; returns the settled vertex positions (cached by key)"""
    p = os.path.join(_SIMC, key + '.npy')
    if os.path.exists(p) and not os.environ.get('RESIM'):
        P = np.load(p)
        if len(P) == len(V):
            return P
    sc = bpy.context.scene; made = []
    for i, (cv, cf) in enumerate(colliders):
        o = _tmp_ob('col%d' % i, cv, cf); o.modifiers.new('col', 'COLLISION'); o.collision.thickness_outer = 0.008; o.collision.thickness_inner = 0.02; o.collision.cloth_friction = friction; made.append(o)
    ob = _tmp_ob('cloth', V, F); made.append(ob)
    md = ob.modifiers.new('c', 'CLOTH'); st = md.settings; st.quality = 10; st.mass = mass; st.tension_stiffness = stiff; st.compression_stiffness = stiff; st.shear_stiffness = stiff * 0.4
    st.bending_stiffness = bend; st.air_damping = 2.0; st.tension_damping = 6; st.compression_damping = 6; st.bending_damping = 0.6
    if grow:                                             # the cloth is cut larger than its mesh: it buckles into folds
        st.shrink_min = -grow
    if pin is not None:
        vg = ob.vertex_groups.new(name='pin'); vg.add([int(i) for i in pin], 1.0, 'REPLACE'); st.vertex_group_mass = 'pin'; st.pin_stiffness = 1.0
    if pressure:
        st.use_pressure = True; st.uniform_pressure_force = pressure
    cs = md.collision_settings; cs.use_collision = True; cs.distance_min = 0.006; cs.collision_quality = 4; cs.use_self_collision = self_col; cs.self_distance_min = 0.007; cs.self_friction = 8
    sc.frame_start = 1; sc.frame_end = frames; md.point_cache.frame_start = 1; md.point_cache.frame_end = frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); n = len(ev.data.vertices); P = np.zeros(n * 3, np.float32); ev.data.vertices.foreach_get('co', P); P = P.reshape(n, 3).astype(float)
    for o in made:
        me = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
    sc.frame_set(1); np.save(p, P); print('SIM', key, 'done'); sys.stdout.flush()
    return P


def grid_faces(ny, nx, off=0):
    return [(off + j * nx + i, off + j * nx + i + 1, off + (j + 1) * nx + i + 1, off + (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]


def grid_normals(G):
    du = np.gradient(G, axis=1); dv = np.gradient(G, axis=0); N = np.cross(du, dv); return N / (np.linalg.norm(N, axis=2)[..., None] + 1e-12)


def sheet_solid(b, top, und, uv, mat_top, mat_und=None, rim=True):
    """closed sheet between two (ny, nx, 3) grids: a chart for the top, one for the underside, four rim strips. uv (ny, nx, 2) metres"""
    ny, nx = top.shape[:2]; F = grid_faces(ny, nx); b.uvoff = False
    b.add(top.reshape(-1, 3), F, mat_top, uv.reshape(-1, 2))
    uo = np.array([(uv[..., 0].max() - uv[..., 0].min()) * 1.5 + 0.2, 0.0])      # the underside is its own island even where it is welded to the top
    b.add(und.reshape(-1, 3), [f[::-1] for f in F], mat_und if mat_und is not None else mat_top, uv.reshape(-1, 2) + uo)
    b.uvoff = True
    if rim:
        for idx in ([(0, i) for i in range(nx)], [(j, nx - 1) for j in range(ny)], [(ny - 1, i) for i in range(nx - 1, -1, -1)], [(j, 0) for j in range(ny - 1, -1, -1)]):
            T = np.array([top[j, i] for j, i in idx]); U = np.array([und[j, i] for j, i in idx]); n = len(idx)
            s_ = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(T, axis=0), axis=1))]); th = float(np.linalg.norm(T - U, axis=1).mean())
            b.add(np.concatenate([T, U]), [(k, n + k, n + k + 1, k + 1) for k in range(n - 1)], mat_top, [(x, 0.0) for x in s_] + [(x, max(th, 0.01)) for x in s_])


def _tick(x, y, sd=77):
    """top surface of the straw tick: sagging, rounded at the edges, lumpy"""
    x0, x1, ym, z0 = -1.12, 1.12, 0.585, 0.6
    ex = np.clip(np.minimum(x - x0, x1 - x) / 0.14, 0, 1); ey = np.clip((ym - np.abs(y)) / 0.14, 0, 1); e = np.sqrt(1 - (1 - ex) ** 2) * np.sqrt(1 - (1 - ey) ** 2)
    P = np.stack([x, y, np.zeros_like(x)], -1).reshape(-1, 3)
    z = z0 - 0.07 * (1 - e) - 0.04 * np.exp(-((x + 0.1) / 0.7) ** 2 - (y / 0.42) ** 2)
    z = z + (0.016 * vnoise(P, sd, 4.0) + 0.009 * vnoise(P, sd + 1, 11.0)).reshape(x.shape) * (0.3 + 0.7 * e)
    return z


def bed(b):
    """SM_Bed_Oak_PR 2.5 x 1.36 x 1.15 m: four capped posts, plank head (-X) and foot boards, pegged side rails, a straw tick in striped
    linen, a pillow, a wool blanket simulated over it, hanging over the rails and turned back at the head end"""
    r = b.rng; hi = b.hi; hx, hy = 1.19, 0.62; ps = 0.105
    for sx in (-1, 1):
        for sy in (-1, 1):
            hgt = 1.115 if sx < 0 else 0.7
            b.box([sx * hx - ps / 2, sy * hy - ps / 2, 0.0], [sx * hx + ps / 2, sy * hy + ps / 2, hgt], 'wood', grain=2, jit=0.002, taper=0.93, seg=b.d(1, 5))
            b.box([sx * hx - ps / 2 - 0.006, sy * hy - ps / 2 - 0.006, hgt - 0.004], [sx * hx + ps / 2 + 0.006, sy * hy + ps / 2 + 0.006, hgt + 0.03], 'wood', grain=0, jit=0.002)
            if hi:
                for zz in (0.31, 0.41):
                    b.rivet([sx * hx, sy * (hy + ps / 2 - 0.002), zz], [0, sy, 0], r=0.01, h=0.004, mat='wood', n=8)
    for (sx, zs) in ((-1, (0.5, 0.67, 0.84, 1.0)), (1, (0.3, 0.45, 0.6))):
        for za, zb_ in zip(zs[:-1], zs[1:]):
            b.box([sx * hx - 0.016, -hy + 0.04, za + 0.002], [sx * hx + 0.016, hy - 0.04, zb_ - 0.002], 'wood', grain=1, jit=0.003, seg=b.d(1, 6))
    rails = []
    for sy in (-1, 1):
        lo_, hi_ = [-hx + 0.04, sy * hy - 0.02, 0.26], [hx - 0.04, sy * hy + 0.02, 0.46]
        b.box(lo_, hi_, 'wood', grain=0, jit=0.003, seg=b.d(1, 8)); rails.append((lo_, hi_))
    for x in (-0.8, 0.0, 0.8):                             # slats the tick lies on
        b.box([x - 0.06, -hy + 0.02, 0.4], [x + 0.06, hy - 0.02, 0.425], 'wood', grain=1, jit=0.002)
    # ---- straw tick
    def tick_grid(nx, ny):
        X, Y = np.meshgrid(np.linspace(-1.12, 1.12, nx), np.linspace(-0.585, 0.585, ny)); Z = _tick(X, Y)
        top = np.stack([X, Y, Z], -1); k = 0.985                                           # the underside is flat on the slats, tucked in a little
        und = np.stack([X * k, Y * k, np.full_like(X, 0.427)], -1); return top, und, np.stack([X, Y], -1)
    top, und, uv = tick_grid(*b.d((17, 11), (90, 52))); sheet_solid(b, top, und, uv, 'tick')
    ct, cu, _ = tick_grid(46, 26); nC = 46 * 26
    colV = np.concatenate([ct.reshape(-1, 3), cu.reshape(-1, 3)]); colF = grid_faces(26, 46) + [f[::-1] for f in grid_faces(26, 46, nC)]

    def boxmesh(lo_, hi_):
        (x0, y0, z0), (x1, y1, z1) = lo_, hi_
        return ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    cols = [(colV, colF)] + [boxmesh(*rl) for rl in rails] + [boxmesh([hx - 0.03, -hy, 0.2], [hx + 0.03, hy, 0.62]), boxmesh([-hx - 0.03, -hy, 0.2], [-hx + 0.03, hy, 1.0])]
    # ---- pillow: a sewn linen case blown up with pressure and dropped on the tick
    pnx, pny = 34, 22; PX, PY = np.meshgrid(np.linspace(-0.2, 0.2, pnx), np.linspace(-0.33, 0.33, pny))
    edge = np.minimum(np.minimum(PX + 0.2, 0.2 - PX), np.minimum(PY + 0.33, 0.33 - PY)); bulge = 0.012 * np.sqrt(np.clip(edge / 0.05, 0, 1))
    inner = np.ones((pny, pnx), bool); inner[0, :] = inner[-1, :] = inner[:, 0] = inner[:, -1] = False
    idx_b = np.full((pny, pnx), -1); idx_b[inner] = pny * pnx + np.arange(inner.sum()); idx_t = np.arange(pny * pnx).reshape(pny, pnx); idx_b[~inner] = idx_t[~inner]
    cx, cz = -0.83, 0.72
    Vt = np.stack([PX + cx, PY + 0.03, cz + bulge], -1).reshape(-1, 3); Vb = np.stack([PX + cx, PY + 0.03, cz - bulge], -1)[inner]
    Fp = grid_faces(pny, pnx) + [(idx_b[j, i], idx_b[j + 1, i], idx_b[j + 1, i + 1], idx_b[j, i + 1]) for j in range(pny - 1) for i in range(pnx - 1)]
    Pp = cloth_sim('bed_pillow', np.concatenate([Vt, Vb]), Fp, cols[:1], frames=45, pressure=22.0, mass=0.15, bend=0.2, stiff=20.0, grow=0.05)
    Gt = Pp[:pny * pnx].reshape(pny, pnx, 3); Gb = Pp[idx_b.ravel()].reshape(pny, pnx, 3); puv = np.stack([PX, PY], -1)
    st = b.d(3, 1); sel = lambda G: sel4(G, st) if st > 1 else G
    sheet_solid(b, sel(Gt), sel(Gb), sel(puv), 'tick', rim=False)
    # ---- blanket: cloth dropped over the tick and the rails; the head end starts folded back on itself
    xb, xf, yw, sp = -0.38, 1.085, 0.82, 0.02; fold = 0.3
    bnx = int(round((xf - xb + fold) / sp)) + 1; bny = int(round(2 * yw / sp)) + 1
    U, Vv = np.meshgrid(np.linspace(-fold, xf - xb, bnx), np.linspace(-yw, yw, bny))            # U = distance along the blanket from the fold line
    Xi = np.where(U >= 0, xb + U, xb - U * 0.96 + 0.004); P0 = np.stack([Xi, Vv, np.zeros_like(U)], -1).reshape(-1, 3)
    zi = _tick(np.clip(Xi, -1.1, 1.1), np.clip(Vv, -0.58, 0.58)) + 0.03 + np.where(U < 0, 0.028 + 0.02 * np.clip(-U / 0.05, 0, 1), 0.0)
    zi = zi + 0.004 * vnoise(P0, 5, 9.0).reshape(U.shape)
    B0 = np.stack([Xi, Vv, zi], -1).reshape(-1, 3)
    Pb = cloth_sim('bed_blanket', B0, grid_faces(bny, bnx), cols, frames=90, self_col=True, mass=0.35, bend=0.12, stiff=10.0, grow=0.07)
    G = Pb.reshape(bny, bnx, 3); buv = np.stack([U, Vv], -1)
    if not hi:
        G = sel4(G); buv = sel4(buv)
    N = grid_normals(G); sheet_solid(b, G, G - N * b.d(0.006, 0.005), buv, 'blanket', 'lining')
    return {}


def sel4(G, st=4):
    return G[np.ix_(sorted(set(list(range(0, G.shape[0], st)) + [G.shape[0] - 1])), sorted(set(list(range(0, G.shape[1], st)) + [G.shape[1] - 1])))]


def m_cloth(name, scan, tile, c0, c1, stripes=None, quilt=None, grime=0.6, rough=(0.78, 0.97), border=None):
    """woven cloth from a scan (weave value recoloured between c0 and c1), dirt and grease in the folds, pale rubbed high threads;
    stripes = (period m, width fraction, colour) woven ticking stripes along UV u; quilt = (cell m, depth) stitched diamonds;
    border = (v half-width m, band m, colour) a woven band along the two long edges"""
    s = NT(name); uv = s.vec(s.UV, scale=(1 / tile, 1 / tile, 1))
    d = s.bw(s.img('polyhaven/%s/%s_diff_2k.jpg' % (scan, scan), uv)); nm = s.img('polyhaven/%s/%s_nor_gl_2k.jpg' % (scan, scan), uv, 'Non-Color'); hg = s.img('polyhaven/%s/%s_disp_2k.jpg' % (scan, scan), uv, 'Non-Color')
    big = s.noise(3.0, 4.0, 0.6); col = s.mix(c0, c1, s.sat(s.add(s.mul(s.sub(d, 0.5), 2.2), s.add(0.5, s.mul(s.sub(big, 0.5), 0.9)))))
    u = s.sep(s.UV)[0]; v = s.sep(s.UV)[1]; h = s.mul(hg, 0.5)
    if stripes:
        per, wf, sc_ = stripes; fr = s.math('FRACT', s.mul(v, 1 / per)); m = s.mul(s.step(fr, 0.5 - wf / 2 - 0.02, 0.5 - wf / 2), s.inv(s.step(fr, 0.5 + wf / 2, 0.5 + wf / 2 + 0.02)))
        col = s.mix(col, s.mix(col, sc_, 1.0, 'MULTIPLY'), s.mul(m, s.add(0.6, s.mul(d, 0.4))))
    if border:
        hw, bw_, bc_ = border; av = s.math('ABSOLUTE', v); m = s.mul(s.step(av, hw - bw_ - 0.004, hw - bw_), s.inv(s.step(av, hw - 0.012, hw - 0.008)))
        col = s.mix(col, s.mix(bc_, col, 0.25), m)
    if quilt:
        cell, dep = quilt; a_ = s.math('ABSOLUTE', s.math('SINE', s.mul(s.add(u, v), math.pi / cell))); b_ = s.math('ABSOLUTE', s.math('SINE', s.mul(s.sub(u, v), math.pi / cell)))
        q = s.math('POWER', s.mul(a_, b_), 0.4); h = s.add(h, s.mul(q, dep / 0.002)); col = s.mix(col, s.mix(col, (0.6, 0.55, 0.47), 1.0, 'MULTIPLY'), s.mul(s.inv(s.step(q, 0.0, 0.3)), 0.4))
    ao = s.ao(0.06, 8); dirt = s.sat(s.add(s.mul(s.inv(ao), 1.4), s.mul(s.sub(s.noise(7.0, 4.0, 0.65), 0.55), grime)))
    col = s.mix(col, s.mix(col, (0.36, 0.29, 0.2), 1.0, 'MULTIPLY'), dirt)
    st = s.step(s.noise(4.5, 3.0, 0.5), 0.66, 0.78); col = s.mix(col, s.mix(col, (0.6, 0.47, 0.3), 1.0, 'MULTIPLY'), s.mul(st, grime))      # old stains
    rg = s.mixf(rough[0], rough[1], d)
    return s.finish(col, rg, 0.0, height=h, bump=0.002, bevel=0.0, nmap=(nm, 1.0))


def bed_mats():
    return {'wood': m_wood('H_wood', dark=(0.04, 0.022, 0.011), mid=(0.16, 0.09, 0.045), light=(0.36, 0.23, 0.13), tile=0.7, grease=0.5, wear=0.45, scratch=0.3, bevel=0.004),
            'tick': m_cloth('H_tick', 'rough_linen', 0.35, (0.27, 0.22, 0.15), (0.55, 0.48, 0.36), stripes=(0.085, 0.3, (0.3, 0.36, 0.5)), grime=1.0),
            'blanket': m_cloth('H_blanket', 'caban', 0.3, (0.11, 0.11, 0.035), (0.3, 0.28, 0.1), quilt=(0.24, 0.004), grime=0.8, border=(0.82, 0.07, (0.3, 0.07, 0.04))),
            'lining': m_cloth('H_lining', 'caban', 0.3, (0.12, 0.03, 0.02), (0.3, 0.085, 0.05), grime=0.8)}


ASSETS['SM_Bed_Oak_PR'] = dict(cls='prop', px=2048, fn=bed, mats=bed_mats, slots=[('MI_Bed_Oak', 'opaque', None)], extrude=0.02, maxdist=0.05, third_party=['rough_wood', 'rough_linen', 'caban'], sharp=40.0,
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.5), 60), 'close': ((0.3, -1.9, 1.75), (-0.35, 0, 0.6), 30), 'int': ((1.9, -2.5, 2.0), (0, 0, 0.5), 30)}, int_light=(1.2, -1.2, 1.7), int_watts=45.0)
