"""Bake-source fabric/leather shaders (scan-driven micro detail + authored colour, wear, dirt, stitches) and
the game-side review materials that read the baked BC/N/ORM sets."""
import bpy, math
import numpy as np
from prlib import *
TP = OUT.parent / 'ThirdParty' / 'polyhaven'
SCAN = {'rough_linen': ('rough_linen_diff_2k.jpg', 'rough_linen_nor_gl_2k.jpg', 'rough_linen_rough_2k.jpg'),
        'caban': ('caban_diff_2k.jpg', 'caban_nor_gl_2k.jpg', 'caban_rough_2k.jpg'),
        'brown_leather': ('brown_leather_albedo_2k.jpg', 'brown_leather_nor_gl_2k.jpg', 'brown_leather_rough_2k.jpg'),
        'fabric_leather_02': ('fabric_leather_02_diff_2k.jpg', 'fabric_leather_02_nor_gl_2k.jpg', 'fabric_leather_02_rough_2k.jpg'),
        'Metal054A': ('@ambientcg/Metal054A/Metal054A_2K-JPG_Color.jpg', '@ambientcg/Metal054A/Metal054A_2K-JPG_NormalGL.jpg', '@ambientcg/Metal054A/Metal054A_2K-JPG_Roughness.jpg'),
        'mail_tile': ('#gen/mail_diff.png', '#gen/mail_nor.png', '#gen/mail_rough.png'),
        'hessian_230': ('hessian_230_diff_2k.jpg', 'hessian_230_nor_gl_2k.jpg', 'hessian_230_rough_2k.jpg')}
def c8(r, g, b): return tuple(((x / 255) / 12.92 if x / 255 <= .04045 else ((x / 255 + .055) / 1.055) ** 2.4) for x in (r, g, b))
# col: main dye; col2: patch variation; worn: abraded colour; dirt: grime colour
FABRIC = {
 'linen':         dict(scan='rough_linen', tile=.42, rot=.06, col=c8(92, 108, 128), col2=c8(110, 122, 136), worn=c8(140, 148, 156), dirt=c8(70, 60, 46), nstr=1.0, rough=(.78, .97), lumk=.9, wear=.35, dirtk=.4, fade=.18, thread=c8(150, 150, 140), stitch_h=.0005),
 'wool':          dict(scan='caban', tile=.36, rot=.9, col=c8(100, 100, 56), col2=c8(88, 92, 50), worn=c8(132, 132, 84), dirt=c8(64, 52, 36), nstr=1.3, rough=(.82, .98), lumk=.9, wear=.3, dirtk=.6, fade=.2, thread=c8(70, 72, 44), stitch_h=.0004),
 'leather_brown': dict(scan='brown_leather', tile=.34, rot=.3, col=c8(128, 82, 50), col2=c8(108, 66, 40), worn=c8(150, 112, 76), dirt=c8(40, 30, 22), nstr=1.2, rough=(.42, .78), lumk=.9, wear=.75, dirtk=.5, fade=.1, thread=c8(168, 150, 116), stitch_h=.0007),
 'leather_red':   dict(scan='brown_leather', tile=.22, rot=1.2, col=c8(150, 38, 30), col2=c8(126, 30, 26), worn=c8(170, 96, 76), dirt=c8(44, 26, 20), nstr=1.2, rough=(.40, .75), lumk=.9, wear=.8, dirtk=.5, fade=.1, thread=c8(190, 170, 130), stitch_h=.0007),
 'leather_boot':  dict(scan='fabric_leather_02', tile=.30, rot=.5, col=c8(104, 66, 40), col2=c8(86, 54, 34), worn=c8(136, 100, 66), dirt=c8(72, 58, 40), nstr=1.6, rough=(.45, .85), lumk=.9, wear=.85, dirtk=1.0, fade=.08, thread=c8(150, 130, 100), stitch_h=.0007, mud=1.0),
 'leather_sole':  dict(scan='brown_leather', tile=.2, rot=2.0, col=c8(52, 38, 26), col2=c8(44, 32, 22), worn=c8(110, 90, 66), dirt=c8(70, 56, 38), nstr=1.5, rough=(.7, .95), lumk=1.0, wear=.6, dirtk=1.0, fade=.0, thread=c8(120, 100, 80), stitch_h=.0006, mud=1.0),
 'leather_belt':  dict(scan='brown_leather', tile=.18, rot=.2, col=c8(84, 52, 32), col2=c8(70, 42, 28), worn=c8(140, 100, 64), dirt=c8(34, 24, 18), nstr=1.0, rough=(.36, .7), lumk=.9, wear=.9, dirtk=.4, fade=.05, thread=c8(170, 150, 110), stitch_h=.0007),
 'leather_pack':  dict(scan='fabric_leather_02', tile=.38, rot=1.1, col=c8(140, 94, 56), col2=c8(118, 76, 44), worn=c8(166, 126, 84), dirt=c8(46, 34, 24), nstr=1.5, rough=(.45, .82), lumk=.9, wear=.8, dirtk=.6, fade=.12, thread=c8(180, 160, 120), stitch_h=.0007),
 'leather_pack_flap': dict(scan='brown_leather', tile=.3, rot=2.4, col=c8(132, 86, 50), col2=c8(112, 70, 42), worn=c8(160, 120, 80), dirt=c8(44, 32, 22), nstr=1.3, rough=(.42, .8), lumk=.9, wear=.85, dirtk=.5, fade=.15, thread=c8(180, 160, 120), stitch_h=.0007),
 'linen_red':     dict(scan='rough_linen', tile=.40, rot=.04, col=c8(146, 34, 30), col2=c8(124, 28, 28), worn=c8(172, 92, 78), dirt=c8(62, 42, 32), nstr=1.15, rough=(.78, .97), lumk=.9, wear=.42, dirtk=.5, fade=.2, thread=c8(112, 26, 24), stitch_h=.0005, stains=1.0),
 'leather_black': dict(scan='brown_leather', tile=.18, rot=.2, col=c8(36, 32, 31), col2=c8(31, 28, 27), worn=c8(60, 52, 46), dirt=c8(44, 40, 36), nstr=1.0, rough=(.36, .7), lumk=.6, wear=.25, dirtk=.25, fade=.05, thread=c8(120, 104, 80), stitch_h=.0007),
 'leather_shoe':  dict(scan='fabric_leather_02', tile=.30, rot=.5, col=c8(70, 48, 34), col2=c8(58, 40, 30), worn=c8(124, 94, 66), dirt=c8(84, 70, 54), nstr=1.6, rough=(.45, .85), lumk=.9, wear=.85, dirtk=1.0, fade=.08, thread=c8(130, 112, 88), stitch_h=.0007, mud=1.0),
 'wool_tan':      dict(scan='caban', tile=.36, rot=.9, col=c8(150, 112, 74), col2=c8(134, 98, 64), worn=c8(176, 146, 108), dirt=c8(70, 54, 38), nstr=1.3, rough=(.82, .98), lumk=.9, wear=.3, dirtk=.6, fade=.2, thread=c8(104, 78, 52), stitch_h=.0004),
 'wool_blue':     dict(scan='caban', tile=.30, rot=.4, col=c8(48, 66, 118), col2=c8(40, 54, 98), worn=c8(96, 112, 150), dirt=c8(52, 46, 44), nstr=1.3, rough=(.82, .98), lumk=.9, wear=.4, dirtk=.5, fade=.25, thread=c8(34, 44, 80), stitch_h=.0005),
 'leather_tabard': dict(scan='brown_leather', tile=.34, rot=.3, col=c8(156, 100, 56), col2=c8(134, 82, 46), worn=c8(184, 140, 94), dirt=c8(46, 34, 24), nstr=1.2, rough=(.42, .78), lumk=.9, wear=.75, dirtk=.55, fade=.12, thread=c8(190, 170, 130), stitch_h=.0007),
 'leather_grey':  dict(scan='fabric_leather_02', tile=.30, rot=.5, col=c8(78, 74, 72), col2=c8(66, 62, 60), worn=c8(128, 116, 100), dirt=c8(80, 66, 48), nstr=1.6, rough=(.45, .85), lumk=.9, wear=.85, dirtk=1.0, fade=.08, thread=c8(120, 110, 96), stitch_h=.0007, mud=1.0),
 'steel':         dict(scan='Metal054A', tile=.22, rot=.5, col=c8(168, 170, 176), col2=c8(150, 152, 160), worn=c8(214, 216, 220), dirt=c8(74, 56, 42), nstr=.9, rough=(.30, .70), lumk=.45, wear=.8, dirtk=.75, fade=0, thread=c8(150, 150, 150), stitch_h=0, metal=2),
 'mail':          dict(scan='mail_tile', tile=.060, rot=0, col=c8(172, 174, 180), col2=c8(156, 158, 164), worn=c8(210, 212, 216), dirt=c8(70, 54, 42), nstr=1.6, rough=(.28, .9), lumk=1.0, wear=.15, dirtk=.45, fade=0, thread=c8(150, 150, 150), stitch_h=0, metal=2),
 'cord':          dict(scan='hessian_230', tile=.08, rot=.4, col=c8(150, 124, 88), col2=c8(130, 106, 76), worn=c8(170, 150, 120), dirt=c8(60, 48, 36), nstr=.8, rough=(.8, .95), lumk=.6, wear=.2, dirtk=.6, fade=.0, thread=c8(150, 124, 88), stitch_h=0),
 'brass':         dict(scan='brown_leather', tile=.1, rot=0, col=c8(196, 158, 86), col2=c8(170, 132, 70), worn=c8(226, 196, 120), dirt=c8(70, 62, 40), nstr=.25, rough=(.28, .55), lumk=.15, wear=.6, dirtk=.9, fade=0, thread=c8(196, 158, 86), stitch_h=0, metal=1),
 'iron':          dict(scan='brown_leather', tile=.1, rot=0, col=c8(104, 100, 96), col2=c8(84, 78, 72), worn=c8(150, 148, 144), dirt=c8(84, 50, 30), nstr=.3, rough=(.35, .7), lumk=.15, wear=.5, dirtk=.9, fade=0, thread=c8(104, 100, 96), stitch_h=0, metal=1),
}
_img = {}
def scan_img(scan, k):
    key = (scan, k)
    if key not in _img:
        f_ = SCAN[scan][k]; pth = (TP.parent / f_[1:]) if f_[0] == '@' else ((OUT / 'Tools' / f_[1:]) if f_[0] == '#' else (TP / scan / f_))
        im = bpy.data.images.load(str(pth), check_existing=True)
        if k: im.colorspace_settings.name = 'Non-Color'
        _img[key] = im
    return _img[key]
_mean = {}
def scan_mean(scan):
    if scan not in _mean:
        im = scan_img(scan, 0); a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(-1, 4)
        _mean[scan] = float(np.median((a[:, 0] * .2126 + a[:, 1] * .7152 + a[:, 2] * .0722)[::7]))
    return _mean[scan]

class NT:
    def __init__(self, mat):
        mat.use_nodes = True; self.nt = mat.node_tree; self.nt.nodes.clear()
    def n(self, typ, **kw):
        nd = self.nt.nodes.new(typ)
        for k, v in kw.items():
            if k == 'ins':
                for ik, iv in v.items():
                    if hasattr(iv, 'is_linked') or iv.__class__.__name__.startswith('NodeSocket'): self.nt.links.new(iv, nd.inputs[ik])
                    else: nd.inputs[ik].default_value = iv
            else: setattr(nd, k, v)
        return nd
    def math(self, op, a, b=None, clamp=False):
        nd = self.n('ShaderNodeMath', operation=op, use_clamp=clamp, ins={0: a} if b is None else {0: a, 1: b}); return nd.outputs[0]
    def mix(self, fac, a, b, blend='MIX'):
        nd = self.n('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        for sock, v in ((nd.inputs[0], fac), (nd.inputs[6], a), (nd.inputs[7], b)):
            if hasattr(v, 'node'): self.nt.links.new(v, sock)
            else: sock.default_value = v if not isinstance(v, tuple) else (*v, 1) if len(v) == 3 else v
        return nd.outputs[2]
    def ramp(self, x, a, b):
        nd = self.n('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', ins={0: x, 1: a, 2: b, 3: 0.0, 4: 1.0}); return nd.outputs[0]
    def noise(self, vec, scale, detail=3, rough=.55):
        nd = self.n('ShaderNodeTexNoise', ins={'Vector': vec, 'Scale': scale, 'Detail': detail, 'Roughness': rough}); return nd.outputs[0]
    def link(self, a, b): self.nt.links.new(a, b)

def fabric_source(name, fabric, seed=0.0):
    """Bake-source material for the high-detail mesh. Needs uv 'UVMetric' and float point attributes
    'd_stitch' / 'd_seam' (metres; large when absent)."""
    F = FABRIC[fabric]; mat = bpy.data.materials.new(name); T = NT(mat)
    out = T.n('ShaderNodeOutputMaterial'); bs = T.n('ShaderNodeBsdfPrincipled'); T.link(bs.outputs[0], out.inputs[0])
    uvn = T.n('ShaderNodeUVMap', uv_map='UVMetric')
    mp = T.n('ShaderNodeMapping', ins={'Vector': uvn.outputs[0]}); s = 1 / F['tile']; mp.inputs['Scale'].default_value = (s, s, s); mp.inputs['Rotation'].default_value = (0, 0, F['rot']); mp.inputs['Location'].default_value = (seed * .37, seed * .61, 0)
    d = T.n('ShaderNodeTexImage', image=scan_img(F['scan'], 0), ins={'Vector': mp.outputs[0]})
    nm = T.n('ShaderNodeTexImage', image=scan_img(F['scan'], 1), ins={'Vector': mp.outputs[0]})
    rg = T.n('ShaderNodeTexImage', image=scan_img(F['scan'], 2), ins={'Vector': mp.outputs[0]})
    geo = T.n('ShaderNodeNewGeometry'); pos = geo.outputs['Position']
    posv = T.n('ShaderNodeVectorMath', operation='ADD', ins={0: pos, 1: (seed * 3.1, seed * 1.7, seed * .9)}).outputs[0]
    bw = T.n('ShaderNodeRGBToBW', ins={0: d.outputs[0]}).outputs[0]
    lum = T.math('POWER', T.math('DIVIDE', bw, scan_mean(F['scan'])), F['lumk'])
    # macro colour: dye patches + broad value drift
    patch = T.ramp(T.noise(posv, 5.0, 3), .35, .65)
    base = T.mix(patch, F['col'], F['col2'])
    val = T.math('ADD', T.math('MULTIPLY', T.noise(posv, 2.2, 2), .36), .84)
    base = T.mix(1.0, base, T.n('ShaderNodeCombineColor', ins={0: val, 1: val, 2: val}).outputs[0], 'MULTIPLY')
    base = T.mix(1.0, base, T.n('ShaderNodeCombineColor', ins={0: lum, 1: lum, 2: lum}).outputs[0], 'MULTIPLY')
    # curvature: ridges wear pale, cavities hold dirt
    pt = geo.outputs['Pointiness']
    breakup = T.noise(posv, 38.0, 4, .7)
    ridge_m = T.math('MULTIPLY', T.ramp(pt, .505, .56), T.math('ADD', T.math('MULTIPLY', breakup, 1.2), .2), clamp=True)
    scuff = T.math('MULTIPLY', T.ramp(T.noise(posv, 23.0, 5, .75), .62, .82), .4)
    wear = T.math('MULTIPLY', T.math('MAXIMUM', ridge_m, scuff), F['wear'], clamp=True)
    base = T.mix(wear, base, F['worn'])
    cav = T.ramp(pt, .487, .44)
    z = T.n('ShaderNodeSeparateXYZ', ins={0: pos}).outputs[2]
    grime = T.ramp(T.noise(posv, 7.0, 4, .6), .42, .72)
    dirt = T.math('MAXIMUM', T.math('MULTIPLY', cav, .8), T.math('MULTIPLY', grime, .45))
    if F.get('mud'):
        mud = T.math('MULTIPLY', T.ramp(z, .16, .0), T.math('ADD', T.math('MULTIPLY', T.ramp(T.noise(posv, 24.0, 4, .7), .35, .65), .8), .25), clamp=True)
        dirt = T.math('MAXIMUM', dirt, mud)
    else:
        # hems and seat pick up grime: trouser knees and bottoms, sleeve ends
        low = T.math('MULTIPLY', T.ramp(z, .62, .30), T.ramp(T.noise(posv, 9.0, 4, .6), .3, .7))
        dirt = T.math('MAXIMUM', dirt, T.math('MULTIPLY', low, .7))
    dirt = T.math('MULTIPLY', dirt, F['dirtk'], clamp=True)
    base = T.mix(dirt, base, F['dirt'])
    # sun fade on up-facing cloth
    nz = T.n('ShaderNodeSeparateXYZ', ins={0: geo.outputs['Normal']}).outputs[2]
    fade = T.math('MULTIPLY', T.ramp(nz, .2, .95), F['fade'])
    base = T.mix(fade, base, F['worn'])
    if F.get('stains'):   # kitchen wear: grease spots and wiped hands on the lap, pale flour/ash dusting
        ny = T.n('ShaderNodeSeparateXYZ', ins={0: geo.outputs['Normal']}).outputs[1]
        lap = T.math('MULTIPLY', T.math('MULTIPLY', T.ramp(z, .50, .78), T.ramp(z, 1.30, 1.05)), T.ramp(ny, .1, -.5))
        spot = T.math('MAXIMUM', T.ramp(T.noise(posv, 13.0, 4, .6), .66, .72), T.math('MULTIPLY', T.ramp(T.noise(posv, 47.0, 3, .6), .70, .76), .8))
        grease = T.math('MULTIPLY', T.math('MULTIPLY', spot, lap), .75 * F['stains'], clamp=True)
        dark = tuple(c * .42 for c in F['col'])
        base = T.mix(grease, base, dark)
        dust = T.math('MULTIPLY', T.math('MULTIPLY', T.math('MULTIPLY', T.ramp(T.noise(posv, 6.5, 6, .75), .50, .78), T.ramp(T.noise(posv, 31.0, 4, .7), .35, .7)), lap), .16 * F['stains'], clamp=True)
        base = T.mix(dust, base, c8(176, 160, 140))
    else: grease = None
    # stitches and seams
    hmix = T.math('MULTIPLY', T.noise(posv, 900.0, 2), .00006)
    if F['stitch_h'] > 0:
        ds = T.n('ShaderNodeAttribute', attribute_name='d_stitch').outputs['Fac']
        line = T.ramp(T.math('ABSOLUTE', ds), .0010, .0005)
        dash = None
        for k in ((1.0, .8, .9), (.9, -1.0, .35)):
            ph = T.n('ShaderNodeVectorMath', operation='DOT_PRODUCT', ins={0: pos, 1: k}).outputs['Value']
            w = T.ramp(T.math('SINE', T.math('MULTIPLY', ph, 2 * math.pi / .0052)), -.25, .1)
            dash = w if dash is None else T.math('MAXIMUM', dash, w)
        st = T.math('MULTIPLY', line, dash)
        base = T.mix(st, base, F['thread'])
        dm = T.n('ShaderNodeAttribute', attribute_name='d_seam').outputs['Fac']
        groove = T.ramp(T.math('ABSOLUTE', dm), .0022, .0)
        pucker = T.math('MULTIPLY', T.ramp(T.math('ABSOLUTE', ds), .004, .001), T.math('SINE', T.math('MULTIPLY', T.n('ShaderNodeVectorMath', operation='DOT_PRODUCT', ins={0: pos, 1: (1.0, .8, .9)}).outputs['Value'], 2 * math.pi / .0052)))
        hmix = T.math('ADD', hmix, T.math('ADD', T.math('MULTIPLY', st, F['stitch_h']), T.math('ADD', T.math('MULTIPLY', groove, -.0009), T.math('MULTIPLY', pucker, .00012))))
        base = T.mix(T.math('MULTIPLY', groove, .35), base, F['dirt'])
    T.link(base, bs.inputs['Base Color'])
    rr = T.n('ShaderNodeMapRange', ins={0: rg.outputs[0], 1: 0.0, 2: 1.0, 3: F['rough'][0], 4: F['rough'][1]}).outputs[0]
    rr = T.math('ADD', rr, T.math('ADD', T.math('MULTIPLY', dirt, .12), T.math('MULTIPLY', wear, -.10 if 'leather' in fabric else .04)), clamp=True)
    if F.get('stains'): rr = T.math('ADD', rr, T.math('MULTIPLY', grease, -.32), clamp=True)
    if F.get('metal') == 2: rr = T.math('ADD', rr, T.math('MULTIPLY', wear, -.14), clamp=True)
    elif F.get('metal'): rr = T.math('ADD', T.math('MULTIPLY', T.noise(posv, 60.0, 4, .7), F['rough'][1] - F['rough'][0]), F['rough'][0] + 0.0)
    T.link(rr, bs.inputs['Roughness'])
    nmap = T.n('ShaderNodeNormalMap', uv_map='UVMetric', ins={'Color': nm.outputs[0], 'Strength': F['nstr']})
    bump = T.n('ShaderNodeBump', ins={'Height': hmix, 'Normal': nmap.outputs[0], 'Strength': 1.0, 'Distance': 1.0})
    T.link(bump.outputs[0], bs.inputs['Normal'])
    bs.inputs['Metallic'].default_value = 0
    return mat

def game_material(name, bc, n, orm, alpha=False, sss=None, vcol=False, two_sided=False, ao_mix=.6, spec=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name); T = NT(mat)
    out = T.n('ShaderNodeOutputMaterial'); bs = T.n('ShaderNodeBsdfPrincipled'); T.link(bs.outputs[0], out.inputs[0])
    def img(path, noncolor):
        im = bpy.data.images.load(str(path), check_existing=True); im.reload()
        if noncolor: im.colorspace_settings.name = 'Non-Color'
        return T.n('ShaderNodeTexImage', image=im)
    b = img(bc, False); col = b.outputs[0]
    if orm:
        o = img(orm, True); sep = T.n('ShaderNodeSeparateColor', ins={0: o.outputs[0]})
        T.link(sep.outputs[1], bs.inputs['Roughness']); T.link(sep.outputs[2], bs.inputs['Metallic'])
        aov = T.math('ADD', T.math('MULTIPLY', sep.outputs[0], ao_mix), 1 - ao_mix)
        col = T.mix(1.0, col, T.n('ShaderNodeCombineColor', ins={0: aov, 1: aov, 2: aov}).outputs[0], 'MULTIPLY')
    if vcol:
        vc = T.n('ShaderNodeVertexColor', layer_name='Col'); col = T.mix(1.0, col, vc.outputs[0], 'MULTIPLY')
    T.link(col, bs.inputs['Base Color'])
    if n:
        nn = img(n, True); nm = T.n('ShaderNodeNormalMap', ins={'Color': nn.outputs[0]}); T.link(nm.outputs[0], bs.inputs['Normal'])
    if alpha:
        T.link(b.outputs[1], bs.inputs['Alpha'])
        try: mat.surface_render_method = 'DITHERED'
        except Exception: pass
    if sss:
        s = img(sss, False)
        bs.inputs['Subsurface Weight'].default_value = .6; bs.inputs['Subsurface Scale'].default_value = .0024
        T.link(s.outputs[0], bs.inputs['Subsurface Radius'])
        try: bs.subsurface_method = 'RANDOM_WALK_SKIN'
        except Exception: pass
    if spec is not None: bs.inputs['Specular IOR Level'].default_value = spec
    mat.use_backface_culling = not two_sided
    return mat
