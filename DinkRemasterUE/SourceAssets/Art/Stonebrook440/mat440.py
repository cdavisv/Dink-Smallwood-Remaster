"""Materials for the SCR_440 kit.

* Tiling building materials load the numpy PBR sets (and reuse two existing Stonebrook sets by path).
* Prop source materials are procedural Cycles node trees driven by per-part mesh attributes
  (grain frame, polish, edge, bark).  They are baked to one unique BC/N/ORM set per prop.
"""
import bpy, math
import numpy as np
from pathlib import Path

NORMAL_PREVIEW_STRENGTH = 1.0


# --------------------------------------------------------------------------- image based
def image_material(name, tex_paths, normal_strength=NORMAL_PREVIEW_STRENGTH, two_sided=False):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; bs = nt.nodes['Principled BSDF']
    for suffix, path in tex_paths.items():
        img = bpy.data.images.load(str(path), check_existing=True)
        img.colorspace_settings.name = 'sRGB' if suffix == 'BC' else 'Non-Color'
        node = nt.nodes.new('ShaderNodeTexImage'); node.image = img; node.label = suffix; node.name = 'TEX_' + suffix
        if suffix == 'BC':
            nt.links.new(node.outputs['Color'], bs.inputs['Base Color'])
        elif suffix == 'N':
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_strength
            nt.links.new(node.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
        elif suffix == 'ORM':
            sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(node.outputs['Color'], sep.inputs[0])
            nt.links.new(sep.outputs['Green'], bs.inputs['Roughness']); nt.links.new(sep.outputs['Blue'], bs.inputs['Metallic'])
    return mat


# --------------------------------------------------------------------------- procedural node helpers
class NB:
    def __init__(self, mat):
        self.nt = mat.node_tree; self.n = self.nt.nodes; self.l = self.nt.links

    def node(self, typ, **inputs):
        nd = self.n.new(typ)
        for k, v in inputs.items():
            if k.startswith('_'):
                setattr(nd, k[1:], v)
            else:
                self.set(nd.inputs[k], v)
        return nd

    def set(self, sock, v):
        if hasattr(v, 'is_output') or isinstance(v, bpy.types.NodeSocket):
            self.l.new(v, sock)
        else:
            if isinstance(v, (tuple, list)) and len(v) == 3 and getattr(sock, 'type', '') == 'RGBA':
                v = tuple(v) + (1.0,)
            if isinstance(v, (int, float)) and getattr(sock, 'type', '') == 'RGBA':
                v = (v, v, v, 1.0)
            sock.default_value = v

    def attr(self, name):
        a = self.node('ShaderNodeAttribute', _attribute_name=name, _attribute_type='GEOMETRY')
        return a

    def math(self, op, a, b=None, clamp=False):
        m = self.node('ShaderNodeMath', _operation=op, _use_clamp=clamp)
        self.set(m.inputs[0], a)
        if b is not None:
            self.set(m.inputs[1], b)
        return m.outputs[0]

    def vmath(self, op, a, b=None):
        m = self.node('ShaderNodeVectorMath', _operation=op)
        self.set(m.inputs[0], a)
        if b is not None:
            self.set(m.inputs[1], b)
        return m.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else m.outputs['Vector']

    def mix(self, fac, a, b, blend='MIX'):
        m = self.node('ShaderNodeMix', _data_type='RGBA', _blend_type=blend)
        self.set(m.inputs['Factor'], fac); self.set(m.inputs[6], a); self.set(m.inputs[7], b)
        return m.outputs[2]

    def fmix(self, fac, a, b):
        m = self.node('ShaderNodeMix', _data_type='FLOAT')
        self.set(m.inputs['Factor'], fac); self.set(m.inputs[2], a); self.set(m.inputs[3], b)
        return m.outputs[0]

    def maprange(self, v, a, b, c=0.0, d=1.0, interp='SMOOTHSTEP'):
        m = self.node('ShaderNodeMapRange', _interpolation_type=interp, _clamp=True)
        self.set(m.inputs['Value'], v); m.inputs['From Min'].default_value = a; m.inputs['From Max'].default_value = b
        m.inputs['To Min'].default_value = c; m.inputs['To Max'].default_value = d
        return m.outputs['Result']

    def noise(self, vec, scale, detail=4, rough=.5, dist=0.0, dims='3D', w=None):
        m = self.node('ShaderNodeTexNoise', _noise_dimensions=dims)
        self.set(m.inputs['Vector'], vec); m.inputs['Scale'].default_value = scale
        m.inputs['Detail'].default_value = detail; m.inputs['Roughness'].default_value = rough
        m.inputs['Distortion'].default_value = dist
        return m

    def voronoi(self, vec, scale, feature='F1', randomness=1.0):
        m = self.node('ShaderNodeTexVoronoi', _feature=feature)
        self.set(m.inputs['Vector'], vec); m.inputs['Scale'].default_value = scale
        m.inputs['Randomness'].default_value = randomness
        return m

    def scale_vec(self, vec, sx, sy, sz):
        return self.vmath('MULTIPLY', vec, (sx, sy, sz))

    def sep(self, vec):
        s = self.node('ShaderNodeSeparateXYZ'); self.set(s.inputs[0], vec); return s

    def comb(self, x, y, z):
        c = self.node('ShaderNodeCombineXYZ'); self.set(c.inputs[0], x); self.set(c.inputs[1], y); self.set(c.inputs[2], z)
        return c.outputs[0]

    def ao(self, dist, inside=False, local=True):
        a = self.node('ShaderNodeAmbientOcclusion', _inside=inside, _only_local=local, _samples=8)
        a.inputs['Distance'].default_value = dist
        return a.outputs['AO']


def finish_procedural(mat, nb, base, rough, metal, height, bump_strength=1.0, bump_dist=1.0):
    """Expose channels under fixed names for the baker and wire a preview BSDF."""
    bs = mat.node_tree.nodes['Principled BSDF']
    for nm, sock in (('OUT_BC', base), ('OUT_R', rough), ('OUT_M', metal)):
        r = nb.n.new('NodeReroute'); r.name = nm; nb.l.new(sock, r.inputs[0])
    nb.l.new(base, bs.inputs['Base Color']); nb.l.new(rough, bs.inputs['Roughness']); nb.l.new(metal, bs.inputs['Metallic'])
    bump = nb.node('ShaderNodeBump'); bump.name = 'BUMP'
    bump.inputs['Strength'].default_value = bump_strength; bump.inputs['Distance'].default_value = bump_dist
    nb.l.new(height, bump.inputs['Height']); nb.l.new(bump.outputs['Normal'], bs.inputs['Normal'])
    em = nb.n.new('ShaderNodeEmission'); em.name = 'BAKE_EMIT'
    mat['dink_procedural'] = 1
    return mat


def wood_material(name, early, late, rings_per_m=180, late_lo=.55, late_hi=.92, rough=.62, weather=0.0,
                  bark_dark=(.06, .05, .04), bark_light=(.20, .18, .15), fibre=.12):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; nb = NB(mat)
    g = nb.attr('grain').outputs['Vector']
    pol = nb.attr('polish').outputs[0]; bark_f = nb.attr('bark').outputs[0]; logr = nb.attr('logr').outputs[0]
    gaxis = nb.attr('gaxis').outputs['Vector']
    geo = nb.node('ShaderNodeNewGeometry')
    endness = nb.maprange(nb.math('ABSOLUTE', nb.vmath('DOT_PRODUCT', geo.outputs['Normal'], gaxis)), .55, .85)
    # gently wandering growth rings around the pith (part-local XY origin)
    dn = nb.noise(nb.scale_vec(g, 2.2, 2.2, .35), 1.0, detail=3)
    off = nb.vmath('MULTIPLY', nb.vmath('SUBTRACT', dn.outputs['Color'], (.5, .5, .5)), (.012, .012, 0))
    gs = nb.sep(nb.vmath('ADD', g, off))
    r = nb.vmath('LENGTH', nb.comb(gs.outputs[0], gs.outputs[1], 0.0))
    ringn = nb.noise(nb.scale_vec(g, 30, 30, 2), 1.0, detail=2)
    ring = nb.math('FRACT', nb.math('ADD', nb.math('MULTIPLY', r, rings_per_m), nb.math('MULTIPLY', ringn.outputs[0], .35)))
    late_b = nb.maprange(ring, late_lo, late_hi)
    fib = nb.noise(nb.scale_vec(g, 260, 260, 6), 1.0, detail=2)
    pores = nb.maprange(nb.noise(nb.scale_vec(g, 700, 700, 25), 1.0, detail=0).outputs[0], .62, .70)
    broad = nb.noise(nb.scale_vec(g, 3, 3, .6), 1.0, detail=3)
    col = nb.mix(late_b, early, late)
    col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', fib.outputs[0], .5), fibre * 2), col, (0, 0, 0), 'MIX')
    col = nb.mix(nb.math('MULTIPLY', pores, .25), col, (.02, .015, .01))
    col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', broad.outputs[0], .5), .5), col, (.6, .55, .48), 'OVERLAY')
    # ---- end grain: uneven ring widths, sapwood/heartwood, radial drying checks, axe marks
    angle = nb.math('ARCTAN2', gs.outputs[1], gs.outputs[0])
    has_log = nb.math('GREATER_THAN', logr, .001)
    rn = nb.math('DIVIDE', r, nb.math('MAXIMUM', logr, .05))                 # 0 pith .. 1 bark
    cn = nb.noise(nb.comb(nb.math('MULTIPLY', angle, 1.3), nb.math('MULTIPLY', r, 4.0), 7.0), 1.0, detail=3)
    crack_line = nb.math('ABSOLUTE', nb.math('SINE', nb.math('ADD', nb.math('MULTIPLY', angle, 3.5), nb.math('MULTIPLY', cn.outputs[0], 2.6))))
    crack_w = nb.math('ADD', .008, nb.math('MULTIPLY', rn, .05))
    keep = nb.maprange(nb.noise(nb.comb(nb.math('MULTIPLY', angle, 2.0), 3.0, 1.0), 1.0, detail=1).outputs[0], .45, .55)
    checks = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.math('LESS_THAN', crack_line, crack_w), keep),
                     nb.math('MULTIPLY', endness, nb.maprange(rn, .15, .45)))
    sap = nb.math('MULTIPLY', nb.maprange(rn, .62, .78), has_log)
    col = nb.mix(nb.math('MULTIPLY', endness, .30), col, (0, 0, 0))
    col = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', endness, nb.math('SUBTRACT', 1.0, sap)), nb.math('MULTIPLY', has_log, .25)), col, (.05, .03, .015))
    col = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', endness, sap), .35), col, (.55, .45, .32))
    col = nb.mix(nb.math('MULTIPLY', checks, .9), col, (.008, .006, .005))
    chop = nb.attr('chop').outputs[0]
    cuts = None
    for k, (ang, sc) in enumerate(((.35, 9.0), (1.45, 11.0), (2.5, 7.5), (3.6, 13.0))):
        rot = nb.node('ShaderNodeVectorRotate', _rotation_type='Z_AXIS'); nb.set(rot.inputs['Vector'], g); rot.inputs['Angle'].default_value = ang
        wv = nb.node('ShaderNodeTexWave', _wave_type='BANDS', _bands_direction='X', _wave_profile='SAW')
        nb.set(wv.inputs['Vector'], rot.outputs[0]); wv.inputs['Scale'].default_value = sc; wv.inputs['Distortion'].default_value = 1.5
        wv.inputs['Detail'].default_value = 1.0
        line = nb.maprange(wv.outputs[1], .93, .99)
        mask = nb.maprange(nb.noise(nb.vmath('ADD', g, (k * 3.1, k * 1.7, 0)), 7.0, detail=2).outputs[0], .55, .62)
        c = nb.math('MULTIPLY', line, mask)
        cuts = c if cuts is None else nb.math('MAXIMUM', cuts, c)
    cuts = nb.math('MULTIPLY', cuts, chop)
    worn = nb.math('MULTIPLY', chop, .35)
    col = nb.mix(worn, col, (.32, .25, .17))
    col = nb.mix(nb.math('MULTIPLY', cuts, .7), col, (.05, .035, .02))
    if weather:
        wn = nb.noise(nb.scale_vec(g, 1.5, 1.5, .4), 1.0, detail=4)
        wf = nb.math('MULTIPLY', nb.maprange(wn.outputs[0], .3, .7), weather)
        col = nb.mix(wf, col, (.13, .12, .105))
    # ---- bark: irregular plates split by deep furrows, moss in the crevices, crustose lichen on plates
    bw = nb.noise(nb.scale_vec(g, 9, 9, 2), 1.0, detail=4, rough=.6)
    gb = nb.vmath('ADD', g, nb.vmath('MULTIPLY', nb.vmath('SUBTRACT', bw.outputs['Color'], (.5, .5, .5)), (.03, .03, .09)))
    # interlacing vertical furrows: ridged noise stretched along the grain, two scales
    n1 = nb.noise(nb.scale_vec(gb, 34, 34, 2.6), 1.0, detail=3, rough=.55, dist=.4)
    n2 = nb.noise(nb.scale_vec(gb, 75, 75, 6), 1.0, detail=2, rough=.5)
    r1 = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', n1.outputs[0], .5)), 2.0)
    r2 = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', n2.outputs[0], .5)), 2.0)
    fw = nb.noise(nb.scale_vec(g, 20, 20, 3), 1.0, detail=3)
    furrow = nb.math('MAXIMUM', nb.maprange(r1, .16, .02), nb.math('MULTIPLY', nb.maprange(r2, .10, .01), .75))
    # occasional cross-checks break the plates into irregular blocks
    vk = nb.voronoi(nb.scale_vec(gb, 22, 22, 9), 1.0, feature='DISTANCE_TO_EDGE')
    furrow = nb.math('MAXIMUM', furrow, nb.math('MULTIPLY', nb.maprange(vk.outputs['Distance'], .05, .0), nb.maprange(fw.outputs[0], .5, .65)))
    vc = nb.voronoi(nb.scale_vec(gb, 22, 22, 9), 1.0, feature='F1')
    plate_tone = nb.sep(vc.outputs['Color']).outputs[0]
    fibre_b = nb.noise(nb.scale_vec(g, 220, 220, 22), 1.0, detail=3)
    plate_col = nb.mix(nb.math('MULTIPLY', plate_tone, .8), bark_dark, bark_light)
    plate_col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', fibre_b.outputs[0], .5), .8), plate_col, (.6, .55, .48), 'OVERLAY')
    bark_col = nb.mix(nb.math('MULTIPLY', furrow, .92), plate_col, (.014, .011, .008))
    mossm = nb.math('MULTIPLY', furrow, nb.maprange(nb.noise(nb.scale_vec(g, 11, 11, 4), 1.0, detail=4).outputs[0], .48, .66))
    mossn = nb.noise(nb.scale_vec(g, 400, 400, 120), 1.0, detail=2)
    bark_col = nb.mix(nb.math('MULTIPLY', mossm, .9), bark_col, nb.mix(mossn.outputs[0], (.020, .035, .010), (.07, .095, .025)))
    lichm = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, furrow), nb.maprange(nb.noise(nb.scale_vec(g, 26, 26, 9), 1.0, detail=6, rough=.7).outputs[0], .60, .66))
    bark_col = nb.mix(nb.math('MULTIPLY', lichm, .85), bark_col, (.26, .28, .21))
    orange = nb.math('MULTIPLY', lichm, nb.maprange(nb.noise(nb.scale_vec(g, 60, 60, 60), 1.0, detail=1).outputs[0], .70, .74))
    bark_col = nb.mix(orange, bark_col, (.30, .17, .04))
    ring_edge = nb.math('MULTIPLY', has_log, nb.math('GREATER_THAN', r, nb.math('SUBTRACT', logr, .012)))
    barkm = nb.math('MAXIMUM', bark_f, ring_edge)
    col = nb.mix(barkm, col, bark_col)
    # hand polish (oiled, darker, glossy) on handles
    col = nb.mix(nb.math('MULTIPLY', pol, .45), col, nb.mix(.5, col, (.12, .07, .035), 'MULTIPLY'))
    cav = nb.ao(.04)
    col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, cav), .5), col, (0, 0, 0))
    rgh = nb.math('ADD', rough, nb.math('MULTIPLY', nb.math('SUBTRACT', fib.outputs[0], .5), .12))
    rgh = nb.fmix(nb.math('MULTIPLY', endness, .7), rgh, .9)
    rgh = nb.fmix(barkm, rgh, nb.math('ADD', .86, nb.math('MULTIPLY', mossm, .1)))
    rgh = nb.fmix(pol, rgh, .30)
    metal = nb.math('MULTIPLY', r, 0.0)
    h = nb.math('ADD', nb.math('MULTIPLY', late_b, -.25), nb.math('MULTIPLY', fib.outputs[0], .25))
    h = nb.math('ADD', h, nb.math('MULTIPLY', checks, -2.5))
    h = nb.math('ADD', h, nb.math('MULTIPLY', cuts, -2.0))
    hb = nb.math('ADD', nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, furrow), 5.0), nb.math('MULTIPLY', fibre_b.outputs[0], .8))
    h = nb.math('ADD', nb.math('MULTIPLY', h, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', pol, .8))), nb.math('MULTIPLY', hb, barkm))
    return finish_procedural(mat, nb, col, rgh, metal, h, bump_strength=1.0, bump_dist=.0012)


def iron_material(name, base=(.085, .082, .078), rust_amount=.72, polish_col=(.30, .295, .285)):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; nb = NB(mat)
    pos = nb.node('ShaderNodeTexCoord').outputs['Object']
    g = nb.attr('grain').outputs['Vector']
    p = nb.vmath('ADD', pos, nb.vmath('MULTIPLY', g, (.37, .37, .37)))
    edge_attr = nb.attr('edge').outputs[0]; pol = nb.attr('polish').outputs[0]
    # forging hammer marks
    ham = nb.voronoi(p, 60.0, 'F1')
    rn = nb.noise(p, 7.0, detail=10, rough=.62)
    cav = nb.ao(.03)
    edges = nb.math('SUBTRACT', 1.0, nb.ao(.0025, inside=True))
    rust = nb.maprange(nb.math('ADD', rn.outputs[0], nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, cav), .35)), 1 - rust_amount * .5, 1.02 - rust_amount * .38)
    rust = nb.math('MULTIPLY', rust, nb.math('SUBTRACT', 1.0, nb.math('MAXIMUM', edge_attr, nb.math('MULTIPLY', pol, .8))))
    wear = nb.math('MAXIMUM', nb.math('MULTIPLY', nb.maprange(edges, .45, .85), .7), edge_attr)
    rf = nb.noise(p, 90.0, detail=3)
    rust_col = nb.mix(rf.outputs[0], (.20, .075, .025), (.36, .15, .05))
    metal_col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', ham.outputs['Distance'], .3), .4), base, (.10, .10, .095))
    metal_col = nb.mix(wear, metal_col, polish_col)
    col = nb.mix(rust, metal_col, rust_col)
    scratch = nb.noise(nb.scale_vec(p, 400, 6, 6), 1.0, detail=2)
    rgh = nb.fmix(wear, nb.math('ADD', .52, nb.math('MULTIPLY', nb.math('SUBTRACT', ham.outputs['Distance'], .3), .15)),
                  nb.math('ADD', .20, nb.math('MULTIPLY', scratch.outputs[0], .12)))
    rgh = nb.fmix(rust, rgh, .88)
    metal = nb.fmix(rust, 1.0, 0.0)
    h = nb.math('ADD', nb.math('MULTIPLY', ham.outputs['Distance'], .6), nb.math('MULTIPLY', nb.math('MULTIPLY', rust, rf.outputs[0]), 1.4))
    h = nb.math('ADD', h, nb.math('MULTIPLY', nb.math('MULTIPLY', scratch.outputs[0], edge_attr), .3))
    return finish_procedural(mat, nb, col, rgh, metal, h, bump_dist=.0006)


def straw_material(name, base=(.42, .32, .13), dark=(.10, .075, .035), green=.0, rough=.82):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; nb = NB(mat)
    g = nb.attr('grain').outputs['Vector']
    pos = nb.node('ShaderNodeTexCoord').outputs['Object']
    p = nb.vmath('ADD', g, nb.vmath('MULTIPLY', pos, (.0, .0, .0)))
    wob = nb.noise(nb.scale_vec(g, 5, 5, 5), 1.0, detail=2)
    pw = nb.vmath('ADD', p, nb.vmath('MULTIPLY', nb.vmath('SUBTRACT', wob.outputs['Color'], (.5, .5, .5)), (.04, .04, .02)))
    s1 = nb.noise(nb.scale_vec(pw, 650, 650, 7), 1.0, detail=3)
    s2 = nb.noise(nb.scale_vec(pw, 180, 180, 2.5), 1.0, detail=3)
    st = nb.math('ADD', nb.math('MULTIPLY', s1.outputs[0], .55), nb.math('MULTIPLY', s2.outputs[0], .45))
    gap = nb.maprange(st, .42, .30)
    col = nb.mix(nb.maprange(st, .35, .7), nb.mix(.5, base, dark), base)
    col = nb.mix(nb.math('MULTIPLY', gap, .35), col, dark)
    if green:
        gr = nb.maprange(nb.noise(nb.scale_vec(g, 7, 7, 3), 1.0, detail=3).outputs[0], .55, .7)
        col = nb.mix(nb.math('MULTIPLY', gr, green), col, (.22, .22, .09))
    bl = nb.noise(nb.scale_vec(g, 30, 30, 30), 1.0, detail=2)
    col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', bl.outputs[0], .5), .7), col, (.95, .85, .6), 'OVERLAY')
    cav = nb.ao(.05)
    col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, cav), .35), col, (0, 0, 0))
    rgh = nb.math('ADD', rough, nb.math('MULTIPLY', gap, .12))
    metal = nb.math('MULTIPLY', st, 0.0)
    h = nb.math('ADD', st, nb.math('MULTIPLY', gap, -.6))
    return finish_procedural(mat, nb, col, rgh, metal, h, bump_dist=.003)


def water_material(name):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; nb = NB(mat)
    pos = nb.node('ShaderNodeTexCoord').outputs['Object']
    rip = nb.noise(nb.scale_vec(pos, 6, 9, 1), 1.0, detail=6, rough=.55)
    rip2 = nb.noise(nb.scale_vec(pos, 40, 40, 1), 1.0, detail=2)
    muck = nb.maprange(nb.noise(pos, 3.0, detail=5).outputs[0], .55, .8)
    col = nb.mix(muck, (.010, .016, .012), (.05, .045, .025))
    pollen = nb.maprange(nb.noise(pos, 70.0, detail=1).outputs[0], .72, .76)
    col = nb.mix(nb.math('MULTIPLY', pollen, nb.math('MULTIPLY', muck, .9)), col, (.25, .23, .12))
    rgh = nb.fmix(nb.math('MAXIMUM', muck, pollen), .035, .45)
    metal = nb.math('MULTIPLY', muck, 0.0)
    h = nb.math('ADD', rip.outputs[0], nb.math('MULTIPLY', rip2.outputs[0], .25))
    return finish_procedural(mat, nb, col, rgh, metal, h, bump_dist=.0015)


# --------------------------------------------------------------------------- baking
def _img(name, px, noncolor):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    im = bpy.data.images.new(name, px, px, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    im.generated_color = (.5, .5, 1, 1) if noncolor else (0, 0, 0, 1)
    return im


def _set_target(ob, img):
    for slot in ob.material_slots:
        nt = slot.material.node_tree
        node = nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage')
        node.name = 'BAKE_TARGET'; node.image = img
        for n in nt.nodes:
            n.select = False
        node.select = True; nt.nodes.active = node


def _route(ob, channel):
    for slot in ob.material_slots:
        nt = slot.material.node_tree; out = nt.nodes['Material Output']
        if channel is None:
            nt.links.new(nt.nodes['Principled BSDF'].outputs[0], out.inputs['Surface'])
        else:
            em = nt.nodes['BAKE_EMIT']
            nt.links.new(nt.nodes[channel].outputs[0], em.inputs['Color'])
            em.inputs['Strength'].default_value = 1.0
            nt.links.new(em.outputs[0], out.inputs['Surface'])


def _pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def bake_asset(ob, short, px, tex_dir, samples=6, margin=8):
    """Bake the procedural slots of ob into T_S440_<short>_{BC,N,ORM}.png and replace them by one
    image material MI_S440_<short>.  Returns the new material."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
    scene.render.bake.margin = margin; scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    out = {}
    for ch, noncolor, kind in (('OUT_BC', False, 'EMIT'), ('OUT_R', True, 'EMIT'), ('OUT_M', True, 'EMIT'), ('AO', True, 'AO'), ('N', True, 'NORMAL')):
        img = _img('BAKE_%s_%s' % (short, ch), px, noncolor)
        _set_target(ob, img)
        _route(ob, ch if kind == 'EMIT' else None)
        scene.cycles.samples = 12 if kind == 'AO' else (1 if kind == 'NORMAL' else samples)
        if kind == 'NORMAL':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z', margin=margin)
        else:
            bpy.ops.object.bake(type=kind, margin=margin)
        out[ch] = img
    _route(ob, None)
    names = {}
    bc = out['OUT_BC']; bc.filepath_raw = str(Path(tex_dir) / ('T_S440_%s_BC.png' % short)); bc.file_format = 'PNG'; bc.save()
    nn = out['N']; nn.filepath_raw = str(Path(tex_dir) / ('T_S440_%s_N.png' % short)); nn.file_format = 'PNG'; nn.save()
    ao = _pixels(out['AO'])[..., 0]; r = _pixels(out['OUT_R'])[..., 0]; m = _pixels(out['OUT_M'])[..., 0]
    orm = _img('T_S440_%s_ORM' % short, px, True)
    arr = np.dstack((np.clip(ao * .85 + .15, 0, 1), np.clip(r, .03, 1), np.clip(m, 0, 1), np.ones_like(ao)))
    orm.pixels.foreach_set(arr.ravel().astype(np.float32))
    orm.filepath_raw = str(Path(tex_dir) / ('T_S440_%s_ORM.png' % short)); orm.file_format = 'PNG'; orm.save()
    stats = {'mean_metal': float(m.mean()), 'mean_rough': float(r.mean())}
    for k in ('OUT_BC', 'N', 'OUT_R', 'OUT_M', 'AO'):
        bpy.data.images.remove(out[k])
    bpy.data.images.remove(orm)
    final = image_material('MI_S440_' + short, {s: Path(tex_dir) / ('T_S440_%s_%s.png' % (short, s)) for s in ('BC', 'N', 'ORM')})
    procedural = [s.material for s in ob.material_slots]
    ob.data.materials.clear(); ob.data.materials.append(final)
    for p in ob.data.polygons:
        p.material_index = 0
    for pm in procedural:
        pm.use_fake_user = True   # retained in the .blend for re-baking
    return final, stats
