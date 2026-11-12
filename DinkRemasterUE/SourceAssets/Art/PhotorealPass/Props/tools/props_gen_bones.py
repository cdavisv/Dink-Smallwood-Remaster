# Round-2 generators: human skull and a scatter of remains. The skull is sculpted as a union of ellipsoids minus the cavities
# (orbits, nasal aperture, temporal fossae), voxel-remeshed and smoothed (cached); the game mesh is a decimation of that sculpt with
# its own smart-projected UV islands. exec'd by props_bake.py after props_gen_bed.py (uses _SIMC, _tmp_ob, MB, NT, m_plain, ASSETS).


def _ells(items, sub=4):
    V = []; F = []
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    P = np.array([v.co[:] for v in bm.verts]); T = [[v.index for v in f.verts] for f in bm.faces]; bm.free()
    for (c, r) in items:
        n0 = len(V); V += list(P * np.array(r) + np.array(c)); F += [tuple(n0 + i for i in t) for t in T]
    return V, F


def _apply(ob, typ, **kw):
    md = ob.modifiers.new('m', typ)
    for k, v in kw.items():
        setattr(md, k, v)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='m'); ob.select_set(False)


def _read(ob):
    me = ob.data; V = np.array([v.co[:] for v in me.vertices]); F = [tuple(p.vertices) for p in me.polygons]; return V, F


def organic(key, pos, neg, voxel=0.0022, smooth=6):
    """sculpt: union of the ellipsoids `pos`, minus `neg`, voxel remesh, smooth. Returns V, F (cached)"""
    p = os.path.join(_SIMC, key + '.npz')
    if os.path.exists(p) and not os.environ.get('RESIM'):
        d = np.load(p, allow_pickle=True); return d['V'], [tuple(f) for f in d['F']]
    oa = _tmp_ob('pos', *_ells(pos)); _apply(oa, 'REMESH', mode='VOXEL', voxel_size=voxel)
    if neg:
        ob = _tmp_ob('neg', *_ells(neg)); _apply(ob, 'REMESH', mode='VOXEL', voxel_size=voxel)
        _apply(oa, 'BOOLEAN', operation='DIFFERENCE', object=ob, solver='EXACT'); me = ob.data; bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
        _apply(oa, 'REMESH', mode='VOXEL', voxel_size=voxel)
    _apply(oa, 'SMOOTH', factor=0.7, iterations=smooth)
    V, F = _read(oa); me = oa.data; bpy.data.objects.remove(oa); bpy.data.meshes.remove(me)
    np.savez(p, V=V, F=np.array(F, dtype=object)); print('SCULPT', key, len(V), 'verts'); sys.stdout.flush()
    return V, F


def lo_from(V, F, target):
    """decimate a sculpt to about `target` triangles and unwrap it; returns per-loop vertices, faces and UVs in metres"""
    ob = _tmp_ob('lo', V, F); me = ob.data; nt_ = sum(len(f) - 2 for f in F)
    _apply(ob, 'DECIMATE', ratio=min(1.0, target / nt_))
    ob.select_set(True); bpy.context.view_layer.objects.active = ob; me = ob.data; me.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(angle_limit=math.radians(48), island_margin=0.02); bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False); uv = me.uv_layers.active.data; LV = []; LU = []; LF = []
    for pl in me.polygons:
        i0 = len(LV)
        for li in pl.loop_indices:
            LV.append(me.vertices[me.loops[li].vertex_index].co[:]); LU.append(uv[li].uv[:])
        LF.append(tuple(range(i0, i0 + pl.loop_total)))
    LV = np.array(LV); LU = np.array(LU); a3 = sum(pl.area for pl in me.polygons); a2 = 0.0
    for f in LF:
        q = LU[list(f)]; a2 += 0.5 * abs(sum(q[i][0] * q[(i + 1) % len(f)][1] - q[(i + 1) % len(f)][0] * q[i][1] for i in range(len(f))))
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me); bpy.context.view_layer.update()
    return LV, LF, LU * math.sqrt(a3 / max(a2, 1e-9))


_SK_POS = [((0, 0.03, 0.126), (0.077, 0.094, 0.074)), ((0, -0.02, 0.118), (0.066, 0.058, 0.058)), ((0, 0.03, 0.062), (0.058, 0.07, 0.04)), ((0, 0.082, 0.088), (0.052, 0.042, 0.052)),
           ((0.03, -0.08, 0.108), (0.03, 0.012, 0.01)), ((-0.03, -0.08, 0.108), (0.03, 0.012, 0.01)), ((0, -0.085, 0.102), (0.014, 0.011, 0.015)),
           ((0.055, -0.066, 0.066), (0.02, 0.02, 0.015)), ((-0.055, -0.066, 0.066), (0.02, 0.02, 0.015)), ((0.069, -0.022, 0.064), (0.007, 0.042, 0.008)), ((-0.069, -0.022, 0.064), (0.007, 0.042, 0.008)),
           ((0, -0.064, 0.046), (0.036, 0.034, 0.032)), ((0, -0.064, 0.022), (0.035, 0.035, 0.012)), ((0, -0.091, 0.084), (0.0105, 0.011, 0.02)),
           ((0.05, 0.03, 0.02), (0.012, 0.015, 0.016)), ((-0.05, 0.03, 0.02), (0.012, 0.015, 0.016)),
           ((0.036, -0.068, 0.078), (0.031, 0.022, 0.03)), ((-0.036, -0.068, 0.078), (0.031, 0.022, 0.03)), ((0, 0.03, 0.024), (0.036, 0.052, 0.022))]
_SK_NEG = [((0.034, -0.096, 0.086), (0.0185, 0.024, 0.0165)), ((-0.034, -0.096, 0.086), (0.0185, 0.024, 0.0165)), ((0.037, -0.074, 0.084), (0.013, 0.016, 0.011)), ((-0.037, -0.074, 0.084), (0.013, 0.016, 0.011)),
           ((0.006, -0.102, 0.054), (0.008, 0.02, 0.012)), ((-0.006, -0.102, 0.054), (0.008, 0.02, 0.012)), ((0, -0.102, 0.065), (0.0065, 0.02, 0.015)),
           ((0.09, -0.035, 0.096), (0.02, 0.036, 0.03)), ((-0.09, -0.035, 0.096), (0.02, 0.036, 0.03)), ((0.06, -0.084, 0.04), (0.011, 0.014, 0.014)), ((-0.06, -0.084, 0.04), (0.011, 0.014, 0.014)),
           ((0.047, -0.028, 0.03), (0.018, 0.028, 0.02)), ((-0.047, -0.028, 0.03), (0.018, 0.028, 0.02)), ((0, 0.045, 0.014), (0.014, 0.017, 0.012)), ((0, -0.058, 0.01), (0.022, 0.024, 0.012))]


def _skull_parts(b, M=None, tris=1300, mat='skull'):
    V, F = organic('skull', _SK_POS, _SK_NEG)
    n0 = len(b.V)
    if b.hi:
        b.add(V, F, mat)
    else:
        LV, LF, LU = lo_from(V, F, tris); b.add(LV, LF, mat, LU)
    r = np.random.default_rng(8); missing = {2, 9, 10}
    for k in range(14):                                       # upper teeth round the dental arch, three lost
        if k in missing:
            continue
        t = math.radians(-78 + 12 * k); molar = abs(k - 6.5) > 3.4; w = 0.0048 if molar else 0.0036
        c = (0.029 * math.sin(t) * (1.08 if molar else 1.0), -0.064 - 0.03 * math.cos(t), 0.0082 + r.uniform(-0.0008, 0.0008))
        b.blob(c, (w, 0.0042 if molar else 0.003, 0.0078 if not molar else 0.0068), sub=b.d(1, 3), mat='tooth', lump=0.06, seed=k, M=Matrix.Rotation(-t, 4, 'Z') @ Matrix.Rotation(r.uniform(-0.12, 0.12), 4, 'Y'))
    if M is not None:
        b.xform_since(n0, M)


def skull(b):
    """SM_Skull_PR: human skull without the jaw, 0.17 x 0.22 x 0.2 m, facing -Y, resting on its teeth and mastoids"""
    _skull_parts(b); return {}


def _long_bone(b, p0, p1, r=0.0125, sd=0):
    p0 = np.array(p0, float); p1 = np.array(p1, float); L = np.linalg.norm(p1 - p0); d = (p1 - p0) / L; side = np.cross(d, [0, 0, 1.0]); side /= np.linalg.norm(side)
    ts = np.linspace(0, 1, b.d(8, 28)); rad = r * np.interp(ts, [0, 0.05, 0.14, 0.5, 0.86, 0.95, 1], [1.5, 1.75, 1.15, 0.95, 1.2, 1.8, 1.4])
    pts = [p0 + d * L * t + side * 0.012 * math.sin(t * 3.1) * (L / 0.4) for t in ts]
    b.tube(pts, rad, sides=b.d(8, 18), mat='bone', shape=[1, 0.9, 1.04, 0.88, 1.0, 0.93, 1.05, 0.9] + ([1, 0.9, 1.04, 0.88, 1.0, 0.93, 1.05, 0.9, 1.0, 0.95] if b.hi else []))
    for (pe, sg) in ((p0, -1), (p1, 1)):                      # knuckled ends: two condyles one end, head and trochanter the other
        for k, off in enumerate((0.9, -0.9)):
            q = pe + side * r * off * (1.0 if sg > 0 else 0.75) + d * sg * r * (0.3 if k == 0 else -0.2 * (sg < 0))
            b.blob(q, (r * 1.25, r * 1.2, r * 1.15), sub=b.d(1, 3), mat='spongy', lump=0.12, seed=sd * 7 + k + (sg > 0) * 3)


def _rib(b, c, R, a0, a1, tilt, sd=0, r=0.0052):
    n = b.d(9, 30); pts = []; rad = []
    for i, t in enumerate(np.linspace(0, 1, n)):
        a = a0 + (a1 - a0) * t; q = R * (1 + 0.25 * t)
        pts.append((c[0] + q * math.cos(a), c[1] + q * math.sin(a), c[2] + r + tilt * t * t + 0.004 * math.sin(t * 9 + sd))); rad.append(r * (1.25 - 0.55 * t) * (1.25 if i == 0 else 1.0))
    b.tube(pts, rad, sides=b.d(6, 12), mat='bone', shape=ell(1.35, 0.7, b.d(6, 12)), up=[0, 0, 1], ups=[(0, 0, 1)] * n)


def bones(b):
    """SM_Bones_Scatter_PR, 0.8 x 0.7 m: a skull on its side, four long bones with knuckled ends, five ribs (one snapped)"""
    M = Matrix.Translation((-0.275, -0.225, 0.0835)) @ Matrix.Rotation(math.radians(55), 4, 'Z') @ Matrix.Rotation(math.radians(96), 4, 'Y') @ Matrix.Translation((0, 0, -0.1))
    _skull_parts(b, M=M, tris=1000, mat='skull')
    for k, (p0, p1) in enumerate((((-0.1, -0.33, 0.02), (0.3, -0.26, 0.02)), ((-0.36, 0.1, 0.02), (-0.05, 0.27, 0.02)), ((0.02, -0.12, 0.02), (0.3, 0.09, 0.045)), ((0.33, -0.12, 0.018), (0.16, 0.22, 0.018)))):
        _long_bone(b, p0, p1, r=0.0125 - 0.0015 * (k > 1), sd=k)
    for k, (c, R, a0, a1, tilt) in enumerate((((-0.12, 0.0, 0.0), 0.085, 0.3, 2.6, 0.03), ((-0.1, 0.03, 0.0), 0.1, 0.5, 2.8, 0.05), ((0.12, 0.2, 0.0), 0.08, 3.4, 5.6, 0.02), ((0.05, -0.2, 0.0), 0.09, 2.2, 4.3, 0.04),
                                              ((-0.2, 0.2, 0.0), 0.07, 4.2, 5.4, 0.01))):
        _rib(b, c, R, a0, a1, tilt, sd=k)
    return {}


def m_bone(name, frame=None, spongy=0.22, sutures=False):
    """old bone out of the ground: ivory to tan, soil-stained in the hollows and where it lay, pitted (more where spongy), hairline
    cracks, lichen specks; sutures = dark zig-zag seams of the cranium, drawn in the skull's own frame (frame = (location, euler))"""
    s = NT(name); PL = s.P
    if frame is not None:
        mp = s.node('ShaderNodeMapping', vector_type='TEXTURE'); s.L.new(s.P, mp.inputs[0]); mp.inputs['Location'].default_value = frame[0]; mp.inputs['Rotation'].default_value = frame[1]; PL = mp.outputs[0]
    big = s.noise(11.0, 4.0, 0.6); med = s.noise(48.0, 4.0, 0.65); fine = s.noise(520.0, 2.0); ao = s.ao(0.015, 8); aol = s.ao(0.07, 8); z = s.sep(s.P)[2]
    col = s.ramp(big, [(0.3, (0.27, 0.2, 0.115)), (0.52, (0.44, 0.36, 0.23)), (0.78, (0.6, 0.53, 0.39))])
    soil = s.sat(s.add(s.add(s.mul(s.inv(aol), 1.5), s.mul(s.sub(med, 0.5), 1.0)), s.add(s.sub(s.mul(s.inv(s.step(z, 0.0, 0.06)), 0.7), 0.25), s.mul(s.step(s.noise(7.0, 4.0, 0.6), 0.42, 0.62), 1.1))))
    col = s.mix(col, s.ramp(fine, [(0.3, (0.07, 0.048, 0.028)), (0.7, (0.17, 0.12, 0.07))]), s.mul(soil, 0.88))
    pit = s.mul(s.inv(s.step(s.voro(850.0, 'F1'), 0.22, 0.42)), s.step(s.noise(26.0, 3.0), 0.9 - spongy * 1.6, 1.05 - spongy * 1.6))
    col = s.mix(col, s.mix(col, (0.3, 0.22, 0.14), 1.0, 'MULTIPLY'), s.mul(pit, 0.85))
    ck = s.mul(s.inv(s.step(s.voro(26.0, 'DISTANCE_TO_EDGE'), 0.0, 0.007)), s.step(s.noise(7.0, 3.0), 0.5, 0.62))
    col = s.mix(col, (0.08, 0.055, 0.035), s.mul(ck, 0.8)); h = s.sub(s.sub(s.mul(med, 0.35), s.mul(pit, 0.9)), s.mul(ck, 0.9))
    if sutures:
        xl, yl, zl = s.sep(PL); wig = s.add(s.mul(s.sub(s.noise(260.0, 2.0, 0.5, vec=PL), 0.5), 0.011), s.mul(s.sub(s.noise(70.0, 2.0, 0.5, vec=PL), 0.5), 0.012))
        line = lambda v: s.inv(s.step(s.math('ABSOLUTE', s.add(v, wig)), 0.0005, 0.0015))
        sag = s.mul(line(xl), s.mul(s.step(zl, 0.12, 0.135), s.step(yl, -0.03, -0.015)))
        cor = s.mul(line(s.add(yl, s.sub(0.018, s.mul(s.sub(zl, 0.19), 0.45)))), s.step(zl, 0.085, 0.1))
        lam = s.mul(line(s.sub(yl, s.add(0.07, s.mul(s.sub(0.2, zl), 0.42)))), s.step(zl, 0.07, 0.085))
        su = s.mx(s.mx(sag, cor), lam); col = s.mix(col, (0.07, 0.048, 0.03), s.mul(su, 0.9)); h = s.sub(h, s.mul(su, 1.2))
    li = s.mul(s.step(s.noise(19.0, 3.0, 0.5), 0.7, 0.76), s.step(s.sep(s.geo.outputs['Normal'])[2], 0.2, 0.6))
    col = s.mix(col, s.ramp(fine, [(0.3, (0.2, 0.23, 0.13)), (0.7, (0.42, 0.44, 0.3))]), s.mul(li, 0.8))
    rough = s.mixf(s.ramp(med, [(0.3, 0.46), (0.7, 0.74)]), 0.93, s.mx(s.mx(soil, pit), li))
    return s.finish(col, rough, 0.0, height=h, bump=0.0009, bevel=0.0)


def bone_mats(frame=None):
    return {'skull': m_bone('H_skull', frame=frame, sutures=True), 'bone': m_bone('H_bone', spongy=0.2), 'spongy': m_bone('H_spongy', spongy=0.55),
            'tooth': m_plain('H_tooth', (0.34, 0.26, 0.14), (0.66, 0.6, 0.44), 0.28, 0.5, scale=160.0, bump=0.0003)}


ASSETS['SM_Skull_PR'] = dict(cls='prop_small', px=1024, fn=skull, mats=bone_mats, slots=[('MI_Skull', 'opaque', None)], extrude=0.004, maxdist=0.012, sharp=60.0, int_watts=6.0,
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.1), 300), 'close': ((0.32, -0.55, 0.42), (0, 0, 0.09), 50), 'int': ((0.32, -0.55, 0.42), (0, 0, 0.09), 50), 'side': ((-0.5, -0.32, 0.22), (0, 0, 0.09), 50)},
    int_light=(0.3, -0.35, 0.4), floor='ForestFloor')
ASSETS['SM_Bones_Scatter_PR'] = dict(cls='prop', px=2048, meta={'rehull': True}, fn=bones, slots=[('MI_Bones_Scatter', 'opaque', None)], extrude=0.004, maxdist=0.012, sharp=60.0, int_watts=14.0,
    mats=lambda: bone_mats(((-0.275 - 0.1 * math.sin(math.radians(96)) * math.cos(math.radians(55)), -0.225 - 0.1 * math.sin(math.radians(96)) * math.sin(math.radians(55)), 0.0835 - 0.1 * math.cos(math.radians(96))), (0.0, math.radians(96), math.radians(55)))),
    views={'game': ((1.6, -4.4, 6.0), (0, 0, 0.05), 130), 'close': ((0.55, -0.95, 0.75), (-0.05, -0.05, 0.04), 40), 'int': ((0.55, -0.95, 0.75), (-0.05, -0.05, 0.04), 40)},
    int_light=(0.5, -0.5, 0.6), floor='ForestFloor')
