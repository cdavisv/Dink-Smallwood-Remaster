"""Photoreal slime ("puddle" foe): a glistening, spotted, slug-like gelatinous mass. New 10-bone rig and clips (no earlier asset existed).
v2 (12 Nov 2026, after review): translucent shell (opacity in BC alpha) over an interior of murk, bubbles, grit and a victim's bones;
wet meniscus skirt at the ground; slime-trail decal mesh (SM_Slime_Trail); lopsided mound.
usage: blender -b -t 4 --python slime.py -- <stage>   stage: look | final [res] | review tag shots [samples] | export
"""
import bpy, sys, os, math, json, random
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *

A = args(); STAGE = A[0] if A else 'look'
DST = OUT / 'Slime'; (DST / 'Review').mkdir(parents=True, exist_ok=True); (DST / 'Work').mkdir(exist_ok=True)
random.seed(651); V = Vector
VARIANTS = {'Blue': ((.012, .016, .05), (.035, .05, .135), (.40, .29, .17)), 'Green': ((.09, .08, .012), (.24, .22, .03), (.05, .16, .42)), 'Red': ((.07, .025, .02), (.19, .08, .055), (.30, .48, .50))}
SEGX = [-.30, -.15, 0.0, .14, .27]
TINT = {'Blue': (.17, .28, .72), 'Green': (.55, .54, .10), 'Red': (.62, .22, .15)}      # colour of light through the clear gel


def deform(dirs, detail=True):
    d = np.asarray(dirs, float); x = d[:, 0]; y = d[:, 1]; z = d[:, 2]
    th = np.arctan2(y, x)
    lob = 1 + .07 * np.sin(3 * th + 1.0) + .05 * np.sin(5 * th + 2.3) + .035 * np.sin(8 * th + .4) + .02 * np.sin(13 * th + 4.0)
    px = x * .385; py = y * .245 * np.where(y < 0, 1.17, .90)                    # slumps wider to one side
    wrap = lambda a_: (a_ + np.pi) % (2 * np.pi) - np.pi
    taper = 1 - .42 * ss(.0, -.38, px) ; py = py * taper
    hgt = .205 * (1 + .30 * gauss(px - .09, .16) - .38 * ss(-.08, -.36, px) - .12 * ss(.22, .38, px))
    hgt = hgt * (1 + .17 * np.tanh(y * 2.0) + .08 * np.sin(2.1 * th + .8))        # crest pushed off-centre
    up = z > 0
    pz = np.where(up, np.abs(z) ** .82 * hgt, z * .018)
    edge = (1 - np.clip(np.abs(z), 0, 1)) ** 3                                 # the foot flange spreading on the ground
    rad = 1 + (.16 * edge) * lob + (lob - 1) * (1 - np.clip(z, 0, 1)) ** 1.5
    rad = rad + (.30 * gauss(wrap(th - 2.35), .28) + .17 * gauss(wrap(th + .95), .22) + .10 * gauss(wrap(th - .5), .15)) * (1 - np.clip(z, 0, 1)) ** 1.6   # pseudopods creeping out
    px = px * rad; py = py * rad
    p = np.stack([px, py, pz], 1)
    lump = (np.sin(px * 19 + 1.3) * np.sin(py * 23 + .4) * np.sin(pz * 31 + 2.0) * .016 + np.sin(px * 11 + 2.1) * np.sin(py * 13 + 1.7) * .018 + np.sin(px * 43 + .3) * np.sin(py * 39 + 2.9) * .003) * np.clip(z + .15, 0, 1)
    nrm = np.stack([x / .385, y / .245, np.where(up, z / .205, z * 3)], 1); nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    lump = lump + .024 * np.sin(px * 7.3 + py * 4.1 + .5) * np.sin(py * 9.7 - px * 3.3 + 1.9) * np.clip(z + .15, 0, 1) + .012 * np.sin(px * 15.1 - py * 11.3 + 2.2) * np.clip(z, 0, 1)
    p += nrm * lump[:, None]
    # a sagging pseudopod at the front left, and a dimple line down the back
    p[:, 2] -= .012 * gauss(py, .03) * ss(-.25, .0, px) * up * (pz > .1)
    p[:, 2] = np.maximum(p[:, 2], -.004)
    return p


def blob(sub):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1); o = bpy.context.object
    co = co_np(o.data); co /= np.linalg.norm(co, axis=1)[:, None]; set_co(o.data, deform(co))
    co = co_np(o.data); co[:, 2] -= co[:, 2].min(); set_co(o.data, co)
    o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); return o


def slimemat(mat, var='Blue'):
    c1, c2, cs = VARIANTS[var]
    t = NT(mat); tc = t.node('ShaderNodeTexCoord'); P = tc.outputs['Object']; geo = t.node('ShaderNodeNewGeometry'); pz = t.sepxyz(P)[2]; up = t.sepxyz(geo.outputs['Normal'])[2]
    big, _ = t.noise(P, 5, 3, .55, dist=.5); mid, _ = t.noise(P, 26, 4, .65); fine, _ = t.noise(P, 190, 3, .6)
    A1 = t.node('ShaderNodeRGB'); A1.name = 'VAR_C1'; A1.outputs[0].default_value = (*c1, 1); A2 = t.node('ShaderNodeRGB'); A2.name = 'VAR_C2'; A2.outputs[0].default_value = (*c2, 1); A3 = t.node('ShaderNodeRGB'); A3.name = 'VAR_CS'; A3.outputs[0].default_value = (*cs, 1)
    c = t.mix(t.smooth(big, .3, .72), A1.outputs[0], A2.outputs[0])
    c = t.mix(1.0, c, t.ramp(t.noise(P, 6, 2, .5)[0], [(.3, .8), (.5, 1.0), (.72, 1.2)]), 'MULTIPLY')
    # pigment spots: irregular raised tubercles, crowded on the back, sparse toward the foot
    wv = t.vmath('ADD', P, t.vmath('SCALE', t.noise(P, 14, 2, .5)[1], s=.03))
    clus, _ = t.noise(P, 4.5, 2, .5)
    sd, sc_ = t.voronoi(wv, 30, 'F1'); rnd = t.math('MULTIPLY', t.sep(sc_)[0], t.smooth(clus, .38, .6))
    spot = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(sd, .10, .26)), t.math('MULTIPLY', t.math('GREATER_THAN', rnd, .34), t.smooth(pz, .015, .07)))
    sd2, sc2 = t.voronoi(wv, 55, 'F1'); spot2 = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(sd2, .14, .26)), t.math('MULTIPLY', t.math('GREATER_THAN', t.sep(sc2)[1], .72), t.smooth(pz, .02, .08)))
    spots = t.math('MAXIMUM', spot, t.math('MULTIPLY', spot2, .8))
    scol = t.mix(mid, t.mix(.35, A3.outputs[0], A1.outputs[0]), A3.outputs[0])
    c = t.mix(t.math('MULTIPLY', spots, .8), c, scol)
    c = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(sd, .28, .36), t.math('SUBTRACT', 1.0, t.smooth(sd, .36, .46))), t.math('MULTIPLY', t.math('GREATER_THAN', rnd, .34), .5)), c, t.mix(.5, A1.outputs[0], (0, 0, 0)))   # dark rim round each spot
    # pale translucent foot margin and wrinkles
    foot = t.math('SUBTRACT', 1.0, t.smooth(pz, .0, .035))
    c = t.mix(t.math('MULTIPLY', foot, .6), c, t.mix(.6, A2.outputs[0], (.42, .38, .30)))
    thin = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(up, -.1, .55)), t.smooth(pz, .02, .1))
    c = t.mix(t.math('MULTIPLY', thin, .45), c, t.mix(.5, A2.outputs[0], (.5, .5, .45)))
    wr, _ = t.noise(t.mapping(P, (22, 22, 70), (.3, .2, 0)), 1.0, 4, .7, dist=1.2); wline = t.math('SUBTRACT', 1.0, t.smooth(t.math('ABSOLUTE', t.math('SUBTRACT', wr, .5)), 0, .06))
    c = t.mix(t.math('MULTIPLY', wline, .03), c, t.mix(.6, A1.outputs[0], (0, 0, 0)))
    # soil, grit and leaf crumbs stuck to the mucus near the ground
    gn, _ = t.noise(P, 75, 3, .7); gd, gc = t.voronoi(P, 160, 'F1')
    grit = t.math('MULTIPLY', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(gd, .12, .3)), t.math('GREATER_THAN', t.sep(gc)[0], t.math('ADD', .45, t.math('MULTIPLY', t.smooth(pz, .0, .12), .6)))), 1.0)
    soil = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(pz, .0, .05)), t.smooth(gn, .3, .55))
    dirt = t.math('MAXIMUM', grit, soil)
    c = t.mix(t.math('MULTIPLY', dirt, .92), c, t.mix(t.sep(gc)[1], (.07, .05, .03), (.26, .20, .12)))
    # roughness: wet mucus sheen, drier tacky patches on the crest
    dry, _ = t.noise(P, 9, 3, .6)
    r = t.math('ADD', .10, t.math('MULTIPLY', t.noise(P, 8, 2, .5)[0], .14)); r = t.math('ADD', r, t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(dry, .55, .8), t.smooth(up, .3, .9)), .22)); r = t.mixf(dirt, r, .85)
    # height
    h = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, t.smooth(sd, .0, .3)), t.math('MULTIPLY', t.math('GREATER_THAN', rnd, .34), .0030))
    h = t.math('ADD', h, t.math('MULTIPLY', spot2, .0012)); h = t.math('ADD', h, t.math('MULTIPLY', t.noise(P, 7, 2, .4)[0], .0022))
    h = t.math('SUBTRACT', h, t.math('MULTIPLY', wline, .00012)); h = t.math('ADD', h, t.math('MULTIPLY', grit, .0022))
    
    n = t.bump(h, 1.0, 1.0)
    sss = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, dirt), t.math('ADD', .55, t.math('MULTIPLY', foot, .35)))
    b = t.finish(c, r, n, sss=sss, sss_radius=(.03, .03, .03), coat=None)
    # opacity (BC alpha): clear gel between pigment, opaque spots, grit and the pigmented crest
    cl, _ = t.noise(P, 6.5, 3, .6, dist=.8)
    cl2, _ = t.noise(P, 3.0, 2, .4)
    op = t.math('ADD', .04, t.math('MULTIPLY', t.smooth(cl2, .45, .8), .36)); op = t.math('ADD', op, t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(up, .55, 1.0), t.smooth(big, .45, .75)), .22))
    op = t.math('MAXIMUM', op, t.math('MULTIPLY', spots, .96)); op = t.math('MAXIMUM', op, dirt); op = t.math('MAXIMUM', op, t.math('MULTIPLY', wline, .0))
    t.bake['alpha'] = t.math('MINIMUM', op, 1.0)
    BAKE[mat.name] = t.bake; return mat


def interior():
    """What is suspended in the gel: a murky core mass, gas bubbles, grit, and the bones of something it ate (ribs and a small bird skull)."""
    rnd = random.Random(77); objs = []
    def add(vs, fs, kind):
        o = mesh_obj('in', vs, fs); set_color_attr(o.data, 'msk', np.tile(np.array((kind, rnd.random(), 0, 0), float), (len(vs), 1))); objs.append(o); return o
    def core_fn(d, p):
        q = V((p.x + .03, p.y + .012, p.z)); k = 1 + .22 * noise.noise(V(d) * 2.1) + .10 * noise.noise(V(d) * 5.3 + V((3, 1, 2))); return V((q.x * k, q.y * k, max(q.z * k, -.03)))
    vs, fs, d = ellipsoid((0, .01, .07), (.18, .10, .05), 28, 16, fn=core_fn); add(vs, fs, 0.0)
    def inside(p, k):                                              # inside the shell with margin k
        hx = .205 * (1 + .30 * math.exp(-((p.x - .09) / .16) ** 2)); return (p.x / (.36 * k)) ** 2 + (p.y / (.22 * k)) ** 2 + (max(p.z, 0) / (hx * k)) ** 2 < 1 and p.z > .03
    def in_core(p): return ((p.x + .03) / .25) ** 2 + ((p.y - .02) / .15) ** 2 + ((p.z - .075) / .08) ** 2 < 1
    n = 0
    while n < 18:                                                  # bubbles, larger toward the crest
        p = V((rnd.uniform(-.3, .34), rnd.uniform(-.2, .2), rnd.uniform(.04, .22)))
        if not inside(p, .78) or in_core(p): continue
        r = rnd.uniform(.004, .009) + .008 * (p.z > .15) * rnd.random(); vs, fs, d = ellipsoid(p, (r, r, r * rnd.uniform(.85, 1.1)), 10, 6); add(vs, fs, .33); n += 1
    n = 0
    while n < 16:                                                  # grit and pebbles sinking toward the foot
        p = V((rnd.uniform(-.3, .34), rnd.uniform(-.2, .2), rnd.uniform(.035, .11)))
        if not inside(p, .8) or in_core(p): continue
        r = rnd.uniform(.004, .010); sd = rnd.random() * 50
        vs, fs, d = ellipsoid(p, (r * rnd.uniform(.7, 1.3), r * rnd.uniform(.7, 1.3), r * rnd.uniform(.5, 1)), 7, 5, fn=lambda d_, q: q * (1 + .35 * noise.noise(V(d_) * 2 + V((sd, 0, 0))))); add(vs, fs, 1.0); n += 1
    for (c, yaw, L, bend) in (((.10, -.085, .125), .5, .11, .035), ((.02, .095, .115), 2.4, .09, .03), ((-.14, -.03, .10), 1.4, .075, .02)):       # ribs
        c = V(c); dr = V((math.cos(yaw), math.sin(yaw), .15)).normalized(); up = V((0, 0, 1)); pts = []; rad = []
        for i in range(9):
            a = i / 8 - .5; pts.append(c + dr * (a * L) + up * (bend * (1 - (2 * a) ** 2) - bend * .6)); rad.append(.0038 + .0022 * (abs(a) > .42) + .0008 * math.sin(i * 2.1))
        vs, fs, ts, an = tube(pts, rad, 7); add(vs, fs, .66)
    sk = V((.185, .045, .125)); ya = -.7; fw = V((math.cos(ya), math.sin(ya), -.25)).normalized()                                                # small bird skull with bill
    vs, fs, d = ellipsoid(sk, (.021, .017, .016), 12, 8); add(vs, fs, .66)
    st = []
    for i, (a, r, rz) in enumerate(((.012, .011, .008), (.026, .009, .006), (.042, .0085, .004), (.056, .006, .0028), (.064, .002, .0015))):
        st.append((sk + fw * a + V((0, 0, -.004)), V((-fw.y, fw.x, 0)) * r, V((0, 0, 1)) * rz, None, 2.2))
    vs, fs = loft(st, 10); add(vs, fs, .66)
    for sg in (1, -1):
        e = sk + fw * .011 + V((-fw.y, fw.x, 0)) * (sg * .0125) + V((0, 0, .003)); vs, fs, d = ellipsoid(e, (.0052, .0045, .0052), 8, 5); add(vs, fs, 1.0)   # dark orbits
    o = join(objs, 'SlimeInterior'); return o


def coremat(mat, var='Blue'):
    c1, c2, cs = VARIANTS[var]
    t = NT(mat); tc = t.node('ShaderNodeTexCoord'); P = tc.outputs['Object']; ma = t.attr('msk'); mR, mG, mB = t.sep(ma.outputs['Color'])[:3]
    A1 = t.node('ShaderNodeRGB'); A1.name = 'VAR_C1'; A1.outputs[0].default_value = (*c1, 1); A2 = t.node('ShaderNodeRGB'); A2.name = 'VAR_C2'; A2.outputs[0].default_value = (*c2, 1)
    isBub = t.math('COMPARE', mR, .33, .1); isBone = t.math('COMPARE', mR, .66, .1); isGrit = t.math('GREATER_THAN', mR, .9)
    cl, _ = t.noise(P, 9, 4, .7, dist=1.5); fn, _ = t.noise(P, 45, 3, .65)
    c = t.mix(t.smooth(cl, .3, .7), t.mix(.35, A1.outputs[0], (.02, .018, .015)), t.mix(.3, A2.outputs[0], (.22, .19, .14)))        # murk
    vv = t.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); t.link(t.vmath('ADD', P, t.vmath('SCALE', t.noise(P, 20, 2, .5)[1], s=.04)), vv.inputs['Vector']); vv.inputs['Scale'].default_value = 26
    thr = t.math('SUBTRACT', 1.0, t.smooth(vv.outputs['Distance'], .0, .05)); c = t.mix(t.math('MULTIPLY', thr, .5), c, t.mix(.4, A2.outputs[0], (.45, .42, .36)))   # pale threads
    c = t.mix(t.math('MULTIPLY', t.smooth(fn, .55, .75), .5), c, (.012, .01, .008))
    c = t.mix(isBub, c, t.mix(.25, (.62, .68, .68), A2.outputs[0]))
    bst, _ = t.noise(P, 60, 3, .7); c = t.mix(isBone, c, t.mix(t.smooth(bst, .4, .7), (.66, .58, .42), (.36, .28, .16)))
    c = t.mix(isGrit, c, t.mix(mG, (.035, .026, .018), (.14, .11, .08)))
    r = t.math('ADD', .45, t.math('MULTIPLY', fn, .3)); r = t.mixf(isBub, r, .04); r = t.mixf(isBone, r, t.math('ADD', .35, t.math('MULTIPLY', bst, .3))); r = t.mixf(isGrit, r, .85)
    h = t.math('ADD', t.math('MULTIPLY', cl, .004), t.math('ADD', t.math('MULTIPLY', thr, .0012), t.math('MULTIPLY', fn, .0008))); h = t.mixf(isBub, h, 0.0)
    t.finish(c, r, t.bump(h, 1.0, 1.0)); BAKE[mat.name] = t.bake; return mat


def skirt(low):
    """Wet meniscus: the lowest band of the shell itself, copied, pushed out along its own horizontal normal and laid on the ground,
    so it follows every bay between pseudopods instead of bridging them. v = 0 where it climbs the body, 1 at the outer edge."""
    me = low.data; co = co_np(me); n = nrm_np(me); H = .03
    faces = [p for p in me.polygons if all(co[v, 2] < H for v in p.vertices) and p.normal.z > -.3]
    idx = sorted({v for p in faces for v in p.vertices}); remap = {v: k for k, v in enumerate(idx)}; vs = []; uv = []
    for v in idx:
        d = V((n[v, 0], n[v, 1], 0))
        if d.length < 1e-4: d = V((co[v, 0], co[v, 1], 0))
        d.normalize(); t_ = min(1.0, max(0.0, co[v, 2] / H)); w = .020 + .012 * noise.noise(V((co[v, 0] * 9, co[v, 1] * 9, 0)))
        p = V((co[v, 0], co[v, 1], 0)) + d * (w * (1 - t_) ** 1.5 + .0025)
        vs.append((p.x, p.y, .0006 + .017 * t_ ** 2)); uv.append(((math.atan2(co[v, 1], co[v, 0]) / math.tau + .5) * 6, 1 - t_))
    o = mesh_obj('SlimeSkirt', vs, [tuple(remap[v] for v in p.vertices) for p in faces]); o.data.uv_layers.new(name='UVMap'); uvl = o.data.uv_layers.active.data
    for pl in o.data.polygons:
        us = [uv[v][0] for v in pl.vertices]; wrap_ = max(us) - min(us) > 3
        for li in pl.loop_indices:
            u, v_ = uv[o.data.loops[li].vertex_index]; uvl[li].uv = (u + 6 if wrap_ and u < 3 else u, v_)
    return o


def fx_textures():
    """Generated wet-film (meniscus) and slime-trail texture sets (numpy; no third-party pixels)."""
    from PIL import Image
    T = DST / 'Textures'; rng = np.random.default_rng(3)
    def vnoise(shape, sc, seed, tile_x=True):
        g = np.random.default_rng(seed).random((sc + 1, sc + 1));  g[:, -1] = g[:, 0] if tile_x else g[:, -1]
        yy, xx = np.mgrid[0:shape[0], 0:shape[1]]; fx = xx / shape[1] * sc; fy = yy / shape[0] * sc; ix = np.minimum(fx.astype(int), sc - 1); iy = np.minimum(fy.astype(int), sc - 1); tx = fx - ix; ty = fy - iy
        tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty); return g[iy, ix] * (1 - tx) * (1 - ty) + g[iy, ix + 1] * tx * (1 - ty) + g[iy + 1, ix] * (1 - tx) * ty + g[iy + 1, ix + 1] * tx * ty
    def srgb(x_): return np.where(x_ <= .0031308, x_ * 12.92, 1.055 * np.clip(x_, 0, 1) ** (1 / 2.4) - .055)
    def save(name, col, a, h, rough, hs=6.0):
        Image.fromarray((np.concatenate([np.clip(srgb(col), 0, 1), np.clip(a, 0, 1)[..., None]], -1) * 255 + .5).astype(np.uint8)[::-1], 'RGBA').save(T / (name + '_BC.png'))
        gy, gx = np.gradient(h); nx = -gx * hs; ny = -gy * hs; ln = np.sqrt(nx * nx + ny * ny + 1)
        Image.fromarray((np.stack([nx / ln * .5 + .5, ny / ln * .5 + .5, 1 / ln * .5 + .5], -1) * 255 + .5).astype(np.uint8)[::-1]).save(T / (name + '_N.png'))
        Image.fromarray((np.stack([np.ones_like(rough), np.clip(rough, 0, 1), np.zeros_like(rough)], -1) * 255 + .5).astype(np.uint8)[::-1]).save(T / (name + '_ORM.png'))
        return {'BC': T / (name + '_BC.png'), 'N': T / (name + '_N.png'), 'ORM': T / (name + '_ORM.png')}
    # meniscus: u tiles round the foot, v 0 at the body .. 1 at the outer edge
    H, W = 128, 512; v = (np.mgrid[0:H, 0:W][0] + .5) / H; n1 = vnoise((H, W), 12, 1); n2 = vnoise((H, W), 40, 2)
    edge = .62 + .38 * n1; a = np.clip((edge - v) / .22, 0, 1) ** .8 * (.72 + .2 * n2) * np.clip(v / .08, .55, 1); a = np.maximum(a, np.clip(1 - v / .3, 0, 1) * .85)
    col = np.ones((H, W, 3)) * np.array((.030, .026, .020)) * (.8 + .4 * n2[..., None]); h = np.clip((edge - v) / .3, 0, 1) ** .5 * .5 + .04 * n2
    wet = save('T_Slime_Wet', col, a, h, .05 + .10 * n2 + .5 * np.clip((v - edge + .1) / .1, 0, 1))
    # trail: u 0 old end .. 1 fresh end at the slime, v across
    H, W = 512, 1024; yy, xx = np.mgrid[0:H, 0:W]; u = (xx + .5) / W; v = (yy + .5) / H * 2 - 1
    n1 = vnoise((H, W), 6, 4, False); n2 = vnoise((H, W), 24, 5, False); n3 = vnoise((H, W), 90, 6, False)
    centre = .16 * np.sin(u * 5.2 + .7) + .07 * np.sin(u * 13 + 2.1); half = (.42 + .16 * np.sin(u * 7.1 + 1.0) + .22 * (n1 - .5)) * np.clip(u / .12, 0, 1) ** .6 * (.72 + .28 * u)
    d = np.abs(v - centre) / np.maximum(half, 1e-3)                                  # 0 centre .. 1 edge
    body = np.clip((1 - d) / .16, 0, 1); gaps = np.clip((n2 - .30 - .25 * (1 - u)) / .12, 0, 1); body = body * (.35 + .65 * gaps)
    streak = .5 + .5 * np.sin((v - centre) * 70 + n1 * 9 + np.sin(u * 30) * .6); rim = np.exp(-((d - .93) / .07) ** 2) * (d < 1.15)
    age = np.clip(u * 1.25, 0, 1)                                                   # old end has dried to a silvery crust
    a = np.clip(body * (.66 + .22 * age) * (.8 + .2 * streak) + rim * .32 * (.5 + .5 * n3), 0, .92)
    col = np.ones((H, W, 3)) * np.array((.034, .030, .024)); dry = np.clip(rim + (1 - age) * .6 * body, 0, 1)[..., None]; col = col * (1 - dry * .7) + np.array((.30, .30, .27)) * dry * .7 * (.7 + .5 * n3[..., None])
    bub = np.zeros((H, W))
    for i in range(140):
        bu = rng.uniform(.1, .98); bv = rng.uniform(-.6, .6); br = rng.uniform(.004, .013); dd = np.hypot((u - bu) * 2, (v - bv - (.16 * math.sin(bu * 5.2 + .7)))) / br
        bub = np.maximum(bub, np.clip(1 - np.abs(dd - .8) / .25, 0, 1) * (dd < 1.2))
    col = col * (1 - .6 * bub[..., None]) + np.array((.5, .5, .48)) * .6 * bub[..., None]; a = np.maximum(a, bub * .7 * (body > .1))
    h = body * (.4 + .12 * streak) + rim * .25 + bub * .3
    trail = {}
    for var in VARIANTS:                                                            # the trail carries a little of the body's pigment
        tc_ = np.array(TINT[var]) * .22; k_ = (.38 * (1 - dry) * body[..., None])
        trail[var] = save('T_Slime_Trail_' + var, col * (1 - k_) + tc_ * k_, a, h, .06 + .12 * n3 + .5 * dry[..., 0] + .2 * (1 - age), hs=10.0)
    return wet, trail


def film_material(name, tex):
    """Review stand-in for a translucent wet film / decal: alpha-blended, dark, glossy."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(b.outputs[0], o.inputs[0])
    def im(p_, linear):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(str(p_), check_existing=True); n.image.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'; return n
    bc = im(tex['BC'], False); nt.links.new(bc.outputs[0], b.inputs['Base Color']); nt.links.new(bc.outputs['Alpha'], b.inputs['Alpha'])
    orm = im(tex['ORM'], True); sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs[0], sp.inputs[0]); nt.links.new(sp.outputs[1], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(im(tex['N'], True).outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    b.inputs['Specular IOR Level'].default_value = .8; m.use_backface_culling = False; return m


def shell_material(name, tex, tint):
    """Review stand-in for the translucent gel (Unreal: translucent or Substrate material driven by the same maps):
    opacity from BC alpha; clear parts refract and show the interior; shadow rays pass tinted so the inside is lit."""
    m = game_material(name, tex, sss=True, sss_scale=1.0, sss_radius=(.03, .03, .03)); nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'); bc = b.inputs['Base Color'].links[0].from_node
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(bc.outputs['Alpha'], inv.inputs[1])
    tw = nt.nodes.new('ShaderNodeMath'); tw.operation = 'MULTIPLY'; tw.inputs[1].default_value = .95; nt.links.new(inv.outputs[0], tw.inputs[0]); nt.links.new(tw.outputs[0], b.inputs['Transmission Weight'])
    mixc = nt.nodes.new('ShaderNodeMix'); mixc.data_type = 'RGBA'; nt.links.new(inv.outputs[0], mixc.inputs[0]); nt.links.new(bc.outputs[0], mixc.inputs[6]); mixc.inputs[7].default_value = (*tint, 1)
    nt.links.new(mixc.outputs[2], b.inputs['Base Color']); b.inputs['IOR'].default_value = 1.36
    for l in list(b.inputs['Subsurface Weight'].links): nt.links.remove(l)
    b.inputs['Subsurface Weight'].default_value = 0.0
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); nt.links.new(mixc.outputs[2], tr.inputs[0]); lp = nt.nodes.new('ShaderNodeLightPath'); mx = nt.nodes.new('ShaderNodeMixShader')
    sh = nt.nodes.new('ShaderNodeMath'); sh.operation = 'MULTIPLY'; nt.links.new(lp.outputs['Is Shadow Ray'], sh.inputs[0]); nt.links.new(inv.outputs[0], sh.inputs[1])
    nt.links.new(sh.outputs[0], mx.inputs[0]); nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0]); return m


def make_rig(coll):
    ad = bpy.data.armatures.new('Armature'); arm = bpy.data.objects.new('Armature', ad); coll.objects.link(arm)
    activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    def bone(name, h, parent=None):
        b = ad.edit_bones.new(name); b.head = h; b.tail = (h[0], h[1] + .06, h[2]); b.roll = 0
        if parent: b.parent = ad.edit_bones[parent]
        return b
    bone('root', (0, 0, 0)); ad.edit_bones['root'].tail = (0, .1, 0)
    bone('pelvis', (0, 0, .06), 'root')
    names = ['body_01', 'body_02', 'body_03', 'body_04', 'head']
    for nme, x in zip(names, SEGX): bone(nme, (x, 0, .05), 'pelvis')
    for nme, par, x, z in (('hump_02', 'body_02', -.15, .15), ('hump_03', 'body_03', 0.0, .20), ('hump_04', 'body_04', .14, .21)): bone(nme, (x, 0, z), par)
    bpy.ops.object.mode_set(mode='OBJECT')
    for b in arm.pose.bones: b.rotation_mode = 'QUATERNION'
    return arm


def skin(ob, arm):
    names = ['body_01', 'body_02', 'body_03', 'body_04', 'head']; humps = {1: 'hump_02', 2: 'hump_03', 3: 'hump_04'}
    for g in list(ob.vertex_groups): ob.vertex_groups.remove(g)
    G = {n: ob.vertex_groups.new(name=n) for n in names + list(humps.values())}
    for v in ob.data.vertices:
        x, z = v.co.x, v.co.z; w = {}
        for k, sx in enumerate(SEGX):
            lo = SEGX[k - 1] if k > 0 else sx - 1; hi = SEGX[k + 1] if k < 4 else sx + 1
            a = max(0.0, 1 - abs(x - sx) / ((hi - sx) if x > sx else (sx - lo))) if (k not in (0, 4) or (k == 0 and x > sx) or (k == 4 and x < sx)) else 1.0
            a = a * a * (3 - 2 * a)
            if a <= 0: continue
            hz = min(1.0, max(0.0, (z - .03) / .15)); hz = hz * hz * (3 - 2 * hz)
            if k in humps: w[humps[k]] = w.get(humps[k], 0) + a * hz; w[names[k]] = w.get(names[k], 0) + a * (1 - hz)
            else: w[names[k]] = w.get(names[k], 0) + a
        tot = sum(w.values())
        for nme, x_ in sorted(w.items(), key=lambda q: -q[1])[:4]: G[nme].add([v.index], x_ / tot, 'REPLACE')
    ob.parent = arm; md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = arm


def make_actions(arm):
    sc = bpy.context.scene; sc.render.fps = 30; arm.animation_data_create(); out = {}
    segs = ['body_01', 'body_02', 'body_03', 'body_04', 'head']; humps = ['hump_02', 'hump_03', 'hump_04']
    def clip(name, frames, fn, loop, extra=None):
        act = bpy.data.actions.new('Slime_' + name); act.use_fake_user = True; arm.animation_data.action = act
        for f in range(1, frames + 1):
            t = (f - 1) / (frames - 1)
            for b in arm.pose.bones: b.matrix_basis = Matrix.Identity(4)
            fn(t)
            for b in arm.pose.bones:
                b.keyframe_insert('location', frame=f, group=b.name); b.keyframe_insert('rotation_quaternion', frame=f, group=b.name); b.keyframe_insert('scale', frame=f, group=b.name)
        out[name] = {'action': 'Slime_' + name, 'frames': [1, frames], 'fps': 30, 'duration_s': (frames - 1) / 30, 'loop': loop, 'root_motion': False, **(extra or {})}
    P = arm.pose.bones
    def idle(t):
        ph = t * math.tau
        for k, h in enumerate(humps): P[h].location = (0, 0, .012 * math.sin(ph - k * .9));
        for k, s in enumerate(segs): P[s].location = (.006 * math.sin(ph + k * .7) * (k - 2), 0, 0)
        P['head'].rotation_quaternion = Quaternion((0, 0, 1), .04 * math.sin(ph))
    def walk(t):
        ph = t * math.tau
        for k, s in enumerate(segs):
            P[s].location = (.05 * math.sin(ph - k * 1.05), .008 * math.sin(ph * 1 - k * .8) * (1 if k % 2 else -1), 0)
        for k, h in enumerate(humps):
            # where neighbours bunch together the crest rises, where they spread it sinks
            d = math.cos(ph - (k + 1) * 1.05); P[h].location = (0, 0, -.03 * d)
        P['head'].rotation_quaternion = Quaternion((0, 0, 1), .06 * math.sin(ph))
    def attack(t):
        e = math.sin(min(1, t / .45) * math.pi / 2) if t < .45 else math.cos((t - .45) / .55 * math.pi / 2)
        wind = math.sin(min(1, t / .25) * math.pi) if t < .25 else 0
        P['head'].location = (.20 * e - .06 * wind, 0, .07 * e); P['body_04'].location = (.11 * e - .05 * wind, 0, .03 * e); P['body_03'].location = (.04 * e - .03 * wind, 0, 0)
        P['hump_04'].location = (.03 * e, 0, .05 * e + .03 * wind); P['hump_03'].location = (0, 0, -.03 * e + .04 * wind); P['hump_02'].location = (0, 0, -.02 * e)
        P['head'].rotation_quaternion = Quaternion((0, 1, 0), -.35 * e)
    def death(t):
        q = math.sin(t * math.tau * 5) * max(0, 1 - t / .35) * .012
        e = 0 if t < .3 else (1 - math.cos(min(1, (t - .3) / .6) * math.pi)) / 2
        for k, s in enumerate(segs): P[s].location = ((k - 2) * .045 * e + q, 0, 0)          # no sinking: the foot stays on the ground, only the crest collapses
        for k, h in enumerate(humps): P[h].location = (q, (.02 if k % 2 else -.02) * e, -(.10 + .03 * k) * e)
    clip('Idle', 61, idle, True); clip('Walk', 28, walk, True, {'nominal_speed_cm_s': 30}); clip('Attack', 16, attack, False); clip('Death', 31, death, False, {'hold_last_frame': True})
    arm.animation_data.action = None
    for b in arm.pose.bones: b.matrix_basis = Matrix.Identity(4)
    return out


def shots(arm, tag, which, samples=48, scale=1.0, var='Blue'):
    R = lambda w, h: (int(w * scale), int(h * scale)); fl = []; D = DST / 'Review'
    def has(a): return ('Slime_' + a) in bpy.data.actions
    if 'game' in which:
        set_action(arm, 'Slime_Idle' if has('Idle') else None, 10); f = D / (tag + '_game.png'); shoot(f, game_cam((0, 0, .1), 6.0, -55, 45), (0, 0, .1), 210, R(1200, 900), samples); fl.append(f)
    if 'close' in which:
        set_action(arm, 'Slime_Idle' if has('Idle') else None, 10); f = D / (tag + '_close.png'); shoot(f, (.95, -.62, .42), (.1, 0, .1), 50, R(1200, 900), samples); fl.append(f)
    if 'var' in which:
        set_action(arm, 'Slime_Idle', 10); f = D / (tag + '_close.png'); shoot(f, (.95, -.62, .42), (.1, 0, .1), 50, R(1200, 900), samples); fl.append(f)
    if 'back' in which:
        set_action(arm, 'Slime_Idle', 30); f = D / (tag + '_back.png'); shoot(f, (-1.1, .7, .16), (0, 0, .09), 60, R(1200, 900), samples); fl.append(f)
    if 'pose' in which:
        for act, fr, az in (('Slime_Walk', 8, -75), ('Slime_Attack', 7, -60), ('Slime_Death', 31, -50)):
            set_action(arm, act, fr); f = D / ('%s_%s%02d.png' % (tag, act[6:].lower(), fr)); shoot(f, game_cam((0, 0, .1), 2.2, az, 28), (0, 0, .1), 75, R(1000, 750), samples); fl.append(f)
    set_action(arm, None, 1); return fl


if STAGE in ('look', 'final'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1; sc.render.fps = 30
    coll = bpy.data.collections.new('SK_Slime'); sc.collection.children.link(coll); coll['dink_class'] = 'creature'; coll['dink_path'] = 'Slime'; coll['dink_tex_px'] = 2048
    arm = make_rig(coll)
    mat = slimemat(bpy.data.materials.new('MI_Slime'), 'Blue')
    high = blob(8); high.name = 'SlimeHigh'; high.data.materials.append(mat)
    low = blob(6); low.name = 'SK_Slime_LOD0'; low.data.materials.append(mat)
    for c in list(low.users_collection): c.objects.unlink(low)
    coll.objects.link(low); decimate_to(low, 8600); clean_mesh(low)
    skin(low, arm); acts = make_actions(arm)
    log('LOD0 tris', tri_count(low), 'dims', tuple(round(x, 3) for x in low.dimensions))
    if STAGE == 'look':
        low.hide_render = True; setup_review(samples=32, ground='forrest_ground_03', ground_scale=1.6)
        shots(arm, 'look', ('game', 'close'), 32, .75)
    else:
        res = int(A[1]) if len(A) > 1 else 2048
        uv = uv_unwrap(low, angle=75, hidden_scale=1.0)
        tex = {}
        for var in VARIANTS:
            c1, c2, cs = VARIANTS[var]; nt = mat.node_tree
            nt.nodes['VAR_C1'].outputs[0].default_value = (*c1, 1); nt.nodes['VAR_C2'].outputs[0].default_value = (*c2, 1); nt.nodes['VAR_CS'].outputs[0].default_value = (*cs, 1)
            tex[var] = bake_set(low, DST / 'Textures', 'T_Slime_' + var, res=res, extra=('sss', 'alpha'), source=high, cage=.012, maxray=.03, bc_only=(var != 'Blue'), shared_prefix='T_Slime_Blue')
        # interior (own 1024 set, same-mesh bake), meniscus skirt, trail decal
        inner = interior(); cmat = coremat(bpy.data.materials.new('MI_Slime_Core'), 'Blue'); inner.data.materials.append(cmat); uv_unwrap(inner, angle=66, hidden_scale=1.0); ctex = {}
        for var in VARIANTS:
            c1, c2, cs = VARIANTS[var]; nt = cmat.node_tree; nt.nodes['VAR_C1'].outputs[0].default_value = (*c1, 1); nt.nodes['VAR_C2'].outputs[0].default_value = (*c2, 1)
            ctex[var] = bake_set(inner, DST / 'Textures', 'T_Slime_Core_' + var, res=1024, bc_only=(var != 'Blue'), shared_prefix='T_Slime_Core_Blue')
        for o_ in (low, inner): o_.hide_render = False
        wet, trail = fx_textures(); sk = skirt(low)
        mat.name = 'MI_Slime_Procedural'; mat.use_fake_user = True; low.material_slots[0].material = shell_material('MI_Slime', tex['Blue'], TINT['Blue'])
        cmat.name = 'MI_Slime_Core_Procedural'; cmat.use_fake_user = True; inner.material_slots[0].material = game_material('MI_Slime_Core', ctex['Blue'])
        sk.data.materials.append(film_material('MI_Slime_Wet', wet))
        for var in ('Green', 'Red'):
            shell_material('MI_Slime_' + var, tex[var], TINT[var]).use_fake_user = True; game_material('MI_Slime_Core_' + var, ctex[var]).use_fake_user = True
        for o_ in (inner, sk): skin(o_, arm)
        low = join([low, inner, sk], 'SK_Slime_LOD0')
        tc = bpy.data.collections.new('SM_Slime_Trail'); sc.collection.children.link(tc); tc['dink_class'] = 'prop'; tc['dink_path'] = 'Slime'
        N_ = 10; vs = []; fs = []
        for i in range(N_ + 1):
            a_ = i / N_; x_ = -1.35 * (1 - a_); yo = .05 * math.sin(a_ * 4.0 + .5) * (1 - a_)
            vs += [V((x_, yo - .27, .003)), V((x_, yo + .27, .003))]
        fs = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(N_)]
        tr = mesh_obj('SM_Slime_Trail_LOD0', vs, fs, tc); tr.data.uv_layers.new(name='UVMap'); uvl = tr.data.uv_layers.active.data
        for lp in tr.data.loops: uvl[lp.index].uv = ((lp.vertex_index // 2) / N_, float(lp.vertex_index % 2))
        tr.data.materials.append(film_material('MI_Slime_Trail', trail['Blue']))
        for var in ('Green', 'Red'): film_material('MI_Slime_Trail_' + var, trail[var]).use_fake_user = True
        high.hide_render = True; high.hide_viewport = True
        hc = bpy.data.collections.new('SlimeHigh_Source'); sc.collection.children.link(hc)
        for c in list(high.users_collection): c.objects.unlink(high)
        hc.objects.link(high)
        from dinkasset import common, make_lods
        asset = common.Asset(coll); make_lods.make_lods(asset, [.5, .25], replace=True, force=True); asset.refresh()
        for m in asset.renders: clean_mesh(m); limit_weights(m); m.hide_render = m.name != low.name
        (DST / 'slime_build.json').write_text(json.dumps({'uv': uv, 'texture_px': res, 'lods': [{'name': m.name, 'triangles': tri_count(m)} for m in asset.renders], 'dimensions_m': list(low.dimensions), 'actions': acts,
                                                           'bones': [{'name': b.name, 'parent': b.parent.name if b.parent else None, 'head': list(b.head_local)} for b in arm.data.bones]}, indent=1, default=str))
        bpy.ops.wm.save_as_mainfile(filepath=str(DST / 'SK_Slime.blend'))
        for im in bpy.data.images:
            if im.filepath and str(DST / 'Textures') in bpy.path.abspath(im.filepath): im.filepath = '//Textures/' + Path(im.filepath).name
        bpy.ops.wm.save_as_mainfile(filepath=str(DST / 'SK_Slime.blend'), relative_remap=False); log('FINAL SAVED')
if STAGE == 'review':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Slime.blend')); arm = bpy.data.objects['Armature']
    sm = int(A[3]) if len(A) > 3 else 64; setup_review(samples=sm, ground='forrest_ground_03', ground_scale=1.6)
    var = A[4] if len(A) > 4 else 'Blue'
    ob_ = bpy.data.objects['SK_Slime_LOD0']
    if var != 'Blue':
        for sl in ob_.material_slots:
            if sl.material.name in ('MI_Slime', 'MI_Slime_Core'): sl.material = bpy.data.materials[sl.material.name + '_' + var]
        bpy.data.objects['SM_Slime_Trail_LOD0'].material_slots[0].material = bpy.data.materials['MI_Slime_Trail_' + var]
    bpy.context.scene.cycles.max_bounces = 12; bpy.context.scene.cycles.transmission_bounces = 10; bpy.context.scene.cycles.transparent_max_bounces = 24
    bpy.data.objects['SM_Slime_Trail_LOD0'].location = (-.22, .02, 0)
    shots(arm, A[1], A[2].split(','), sm)
if STAGE == 'export':
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Slime.blend')); arm = bpy.data.objects['Armature']
    for o in list(bpy.data.objects):
        if o.name == 'SlimeHigh': bpy.data.objects.remove(o)
    if len(A) > 1 and A[1] == 'trail':
        from dinkasset import export_ue
        sc = bpy.context.scene; o = bpy.data.objects['SM_Slime_Trail_LOD0']
        for v in o.data.vertices: v.co *= 100
        sc.unit_settings.scale_length = .01
        for material in bpy.data.materials:
            if material.node_tree: material.node_tree.nodes.clear()
        proxy = type('ExportAsset', (), {'renders': [o], 'collision': [], 'armatures': [], 'sockets': []})()
        with export_ue.unhidden([o]): export_ue.export_fbx(proxy, str(DST / 'Export' / (o.name + '.fbx')), 'all', 'Armature')
        log('exported trail')
    else:
        bpy.data.objects.remove(bpy.data.objects['SM_Slime_Trail_LOD0'])
        export_skeletal('SK_Slime', arm, DST / 'Export', {'Idle': 'Slime_Idle', 'Walk': 'Slime_Walk', 'Attack': 'Slime_Attack', 'Death': 'Slime_Death'}, 'A_Slime', 30, DST / 'slime_validation.json')
