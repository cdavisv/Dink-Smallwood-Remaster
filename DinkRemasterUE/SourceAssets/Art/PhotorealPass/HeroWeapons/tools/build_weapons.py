"""The hero's weapons (art row DS-04, bug A203): longsword, claw sword and light sword (item-sw1..3), the wooden bow
(item-b1, item-b3), the blue bow (item-b2) and the throwing axe (item-axe), after the 1997 item pictures 438/7, 20, 21,
8 and 13, 12, 6.

Grip convention, the same for every mesh (Blender axes; the FBX keeps X):
  origin  = centre of the grip, where the middle of the fist closes
  +X      = along the blade / haft towards the tip (swords, axe); along the bow's upper limb (bows)
  XY      = the plane of the blade (its flats face +Z and -Z); the axe's two bits point to +Y and -Y;
            the claws of the claw sword are on +Y; a bow's string is on -Y and its back (towards the target) on +Y

    HeroWeapons/tools/bl.sh <name,name|all> [review|final]      (review = source renders only)
    python3 -I HeroWeapons/tools/build_weapons.py --manifest    (system Python: rewrites HeroWeapons/manifest.json)
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)                                   # .../PhotorealPass/HeroWeapons
UNCT = os.path.join(os.path.dirname(KIT), 'Unclaimed', 'tools')
REPO = os.path.abspath(os.path.join(KIT, '..', '..', '..', '..'))
SCRIPT = 'build_weapons.py'


def kit_manifest():
    """HeroWeapons/manifest.json in the kit importer's schema (Scripts/import_town_exteriors.py, dink-props/1)."""
    import glob
    assets, materials = [], {}
    for path in sorted(glob.glob(os.path.join(KIT, '*', 'manifest.json'))):
        m = json.load(open(path)); roles = {}
        for t in m['textures']:
            roles[os.path.splitext(os.path.basename(t['file']))[0].rsplit('_', 1)[1]] = t['file']
        row = {'baked': True, 'kind': 'opaque', 'files': {r: roles[r] for r in ('BC', 'N', 'ORM')}}
        if 'E' in roles:
            row['files']['E'] = roles['E']; row['emissive_nits'] = m.get('emissive_nits', 60.0)
        materials[m['materials'][0]] = row
        assets.append({'name': m['name'], 'class': m['class'], 'fbx': m['fbx'], 'materials': m['materials'], 'dimensions_m': [round(float(v), 3) for v in m['dimensions_m']],
                       'collision_hulls': 0, 'families': m['families'], 'folder': os.path.relpath(os.path.dirname(path), REPO).replace(os.sep, '/'), 'grip': m['grip']})
        # a bow cut into rigid parts for the draw (tools/build_bow_parts.py): the same material, one mesh a part
        for part in m.get('parts', []):
            assets.append({'name': part['name'], 'class': 'weapon part', 'fbx': part['fbx'], 'materials': m['materials'], 'dimensions_m': [round(float(v), 3) for v in part['dimensions_m']],
                           'collision_hulls': 0, 'families': m['families'], 'folder': os.path.relpath(os.path.dirname(path), REPO).replace(os.sep, '/') + '/Parts', 'part_of': m['name'], 'origin_cm': part['origin_cm']})
    out = {'schema': 'dink-props/1', 'root': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/HeroWeapons', 'generated_by': 'HeroWeapons/tools/build_weapons.py --manifest (do not edit by hand)',
           'summary': '%d meshes of the hero\'s weapons: six hand-held weapons, the arrow and the quiver with one baked opaque set each (BC / N OpenGL / ORM, E for the light sword), and the two bows cut into rigid parts for the draw (their bow\'s material). Pivot at the grip centre, +X to the tip.' % len(assets),
           'assets': assets, 'flipbooks': [], 'not_imported': [],
           'integration': {'contract': {'textures': 'BC sRGB; N linear OpenGL (flip green on import); ORM linear (R occlusion, G roughness, B metallic); E sRGB emissive',
                                        'uv': 'UV0, unique bake, no tiling', 'collision': 'none'}, 'materials': materials}}
    open(os.path.join(KIT, 'manifest.json'), 'w').write(json.dumps(out, indent=1) + '\n'); print('wrote manifest.json:', len(assets), 'assets')


if __name__ == '__main__' and '--manifest' in sys.argv:
    kit_manifest(); sys.exit(0)

import bpy
import numpy as np
sys.path.insert(0, UNCT)
import pplib as L
import build_tools as T
from pplib import NT, smoothstep


# ------------------------------------------------------------------------------------------------ materials
def blade_steel(name, tint=(0.61, 0.645, 0.70), seed=0.0, glow=None):
    """polished sword steel with a cold blue cast (the 1997 blades are pale blue): draw-filed lengthwise, a brighter ground
    bevel towards both edges, faint water stains and a few nicks; glow = emission colour for the light sword"""
    t = NT(name); sp = t.sep(t.obj)
    scr = t.noise(1.0, 3, 0.6, vec=t.mapping(scale=(5, 420, 420), loc=(seed, 0, 0))); fine = t.noise(1.0, 2, 0.5, vec=t.mapping(scale=(18, 1500, 1500)))
    stain = t.ramp(t.noise(16, 5, 0.7, vec=t.mapping(loc=(seed, 2, 0))), [(0.52, 0.0), (0.74, 1.0)]); n2 = t.noise(120, 3, 0.6)
    hi_c = tuple(min(1.0, c * 1.22) for c in tint); lo_c = tuple(c * 0.80 for c in tint)
    base = t.mix(scr, lo_c, hi_c); base = t.mix(t.math('MULTIPLY', stain, 0.30), base, tuple(c * 0.50 for c in tint))
    edge = t.ramp(t.pointiness, [(0.53, 0.0), (0.60, 1.0)]); base = t.mix(t.math('MULTIPLY', edge, 0.7), base, (0.86, 0.88, 0.90))
    rough = t.mixf(scr, 0.20, 0.36); rough = t.mixf(t.math('MULTIPLY', stain, 0.6), rough, 0.5); rough = t.mixf(edge, rough, 0.12)
    h = t.math('ADD', t.math('MULTIPLY', scr, 0.6), t.math('MULTIPLY', fine, 0.4))
    if glow:
        rough = t.mixf(scr, 0.42, 0.55)
    kw = dict(base=base, rough=rough, metal=1.0, normal=t.bump(t.math('ADD', h, t.math('MULTIPLY', n2, 0.15)), 0.10, 0.0004))
    if glow:
        core = t.maprange(t.math('ABSOLUTE', sp[1]), 0.0, 0.03, 1.0, 0.45, interp='SMOOTHSTEP'); kw.update(emission=t.mix(core, (0.0, 0.0, 0.0), t.mix(scr, tuple(c * 0.85 for c in glow), glow)), emission_strength=1.0)
    t.set(**kw); return t.mat


def bone_mat(name, col=(0.62, 0.52, 0.33), seed=0.0):
    """old bone / horn: long fibres, pores, brown grime in the hollows, hand-polished high spots"""
    t = NT(name); fib = t.noise(1.0, 5, 0.65, vec=t.mapping(scale=(60, 9, 60), loc=(seed, 0, 0))); n = t.noise(40, 4, 0.6); pore = t.ramp(t.noise(700, 2, 0.5), [(0.62, 0.0), (0.72, 1.0)])
    base = t.mix(fib, tuple(c * 0.50 for c in col), tuple(min(1, c * 1.15) for c in col)); ao = t.ao(0.006, 12)
    grime = t.math('MULTIPLY', t.ramp(ao, [(0.55, 1.0), (0.95, 0.0)]), t.ramp(n, [(0.2, 0.5), (0.8, 1.0)])); base = t.mix(t.math('MULTIPLY', grime, 0.8), base, (0.10, 0.06, 0.03))
    base = t.mix(t.math('MULTIPLY', pore, 0.5), base, (0.16, 0.10, 0.05)); crack = t.ramp(t.noise(1.0, 3, 0.7, vec=t.mapping(scale=(14, 260, 14), loc=(0, seed, 3))), [(0.70, 0.0), (0.74, 1.0)])
    base = t.mix(t.math('MULTIPLY', crack, 0.5), base, (0.12, 0.07, 0.035))
    stainb = t.ramp(t.noise(11, 5, 0.7, vec=t.mapping(loc=(seed, 5, 1))), [(0.40, 0.0), (0.75, 1.0)]); base = t.mix(t.math('MULTIPLY', stainb, 0.70), base, (0.26, 0.15, 0.06))
    t.set(base=base, rough=t.mixf(fib, 0.42, 0.62), metal=0.0, normal=t.bump(t.math('SUBTRACT', t.math('MULTIPLY', fib, 0.8), t.math('ADD', pore, t.math('MULTIPLY', crack, 2.0))), 0.45, 0.0007)); return t.mat


def bronze_mat(name, seed=0.0):
    """green bronze: verdigris in every hollow and over most of the faces, warm metal showing where a hand rubs"""
    t = NT(name); n1 = t.noise(22, 5, 0.7, vec=t.mapping(loc=(seed, 0, 0))); n2 = t.noise(160, 3, 0.6); ao = t.ao(0.006, 12)
    pat = t.ramp(n1, [(0.2, (0.020, 0.085, 0.050)), (0.5, (0.040, 0.150, 0.080)), (0.85, (0.085, 0.230, 0.130))]); metal_c = t.mix(n2, (0.36, 0.22, 0.07), (0.60, 0.40, 0.15))
    wear = t.math('MULTIPLY', t.ramp(t.pointiness, [(0.51, 0.0), (0.56, 1.0)]), t.ramp(n2, [(0.25, 0.4), (0.7, 1.0)])); wear = t.math('MAXIMUM', wear, t.ramp(t.noise(48, 5, 0.75, vec=t.mapping(loc=(3, seed, 1))), [(0.50, 0.0), (0.62, 0.9)]))
    wear = t.math('MULTIPLY', wear, t.ramp(ao, [(0.5, 0.0), (0.9, 1.0)])); base = t.mix(wear, pat, metal_c)
    t.set(base=base, rough=t.mixf(wear, t.mixf(n2, 0.62, 0.85), 0.3), metal=t.mixf(wear, 0.15, 1.0), normal=t.bump(t.math('ADD', n2, t.math('MULTIPLY', n1, 0.5)), 0.3, 0.0006)); return t.mat


def silver_mat(name, seed=0.0):
    """bright silver, black tarnish in the hollows, fine polishing marks"""
    t = NT(name); n2 = t.noise(180, 3, 0.6, vec=t.mapping(loc=(seed, 0, 0))); ao = t.ao(0.006, 12); scr = t.noise(1.0, 2, 0.5, vec=t.mapping(scale=(300, 16, 300)))
    tarn = t.math('MULTIPLY', t.ramp(ao, [(0.5, 1.0), (0.93, 0.0)]), t.ramp(n2, [(0.2, 0.6), (0.8, 1.0)])); base = t.mix(scr, (0.80, 0.81, 0.82), (0.93, 0.93, 0.92)); base = t.mix(t.math('MULTIPLY', tarn, 0.85), base, (0.05, 0.045, 0.04))
    t.set(base=base, rough=t.mixf(tarn, t.mixf(scr, 0.14, 0.26), 0.6), metal=t.mixf(tarn, 1.0, 0.7), normal=t.bump(t.math('ADD', scr, n2), 0.08, 0.0004)); return t.mat


def leather_mat(name, col=(0.25, 0.020, 0.016), pitch=1150.0):
    """a leather thong wound round the grip: the turns are a bump along X with a dark line between them, worn and darkened by the hand"""
    t = NT(name); sp = t.sep(t.obj); ang = t.math('ARCTAN2', sp[2], sp[1]); ph = t.math('ADD', t.math('MULTIPLY', sp[0], pitch), ang); wrap = t.math('ABSOLUTE', t.math('SINE', t.math('MULTIPLY', ph, 0.5)))
    n = t.noise(260, 4, 0.6); n1 = t.noise(30, 4, 0.6); gap = t.ramp(wrap, [(0.0, 1.0), (0.22, 0.0)])
    base = t.mix(n, tuple(c * 0.6 for c in col), tuple(min(1, c * 1.35) for c in col)); base = t.mix(t.math('MULTIPLY', t.ramp(n1, [(0.4, 0.0), (0.8, 1.0)]), 0.5), base, tuple(c * 0.3 for c in col))
    base = t.mix(t.math('MULTIPLY', gap, 0.85), base, (0.012, 0.008, 0.006))
    t.set(base=base, rough=t.mixf(n1, 0.55, 0.82), metal=0.0, normal=t.bump(t.math('ADD', t.math('POWER', wrap, 0.5), t.math('MULTIPLY', n, 0.30)), 0.8, 0.0007)); return t.mat


def gem_mat(name, col):
    t = NT(name); n = t.noise(90, 2, 0.5); t.set(base=t.mix(n, tuple(c * 0.6 for c in col), col), rough=0.06, metal=0.0, coat=1.0, coat_rough=0.03); return t.mat


def string_mat():
    t = NT('string'); sp = t.sep(t.obj); tw = t.math('SINE', t.math('ADD', t.math('MULTIPLY', sp[0], 2600.0), t.math('MULTIPLY', t.math('ARCTAN2', sp[2], sp[1]), 2.0)))
    t.set(base=t.mix(tw, (0.42, 0.36, 0.24), (0.70, 0.63, 0.46)), rough=0.8, metal=0.0, normal=t.bump(tw, 0.6, 0.0003)); return t.mat


def feather_mat(name, col=(0.62, 0.035, 0.022)):
    """a dyed goose feather vane: red, the barbs a fine slanted ridge, darker towards the quill and where the dye lies thick"""
    t = NT(name); sp = t.sep(t.obj); barb = t.math('SINE', t.math('ADD', t.math('MULTIPLY', sp[0], 2400.0), t.math('MULTIPLY', t.math('ADD', t.math('ABSOLUTE', sp[1]), t.math('ABSOLUTE', sp[2])), 3800.0)))
    n = t.noise(90, 4, 0.6); split = t.ramp(t.noise(26, 3, 0.5, vec=t.mapping(scale=(9, 1, 1))), [(0.60, 0.0), (0.72, 1.0)])
    base = t.mix(n, tuple(c * 0.62 for c in col), tuple(min(1.0, c * 1.25) for c in col)); base = t.mix(t.math('MULTIPLY', split, 0.45), base, tuple(c * 0.35 for c in col))
    t.set(base=base, rough=t.mixf(n, 0.62, 0.80), metal=0.0, normal=t.bump(t.math('ADD', t.math('MULTIPLY', barb, 0.7), t.math('MULTIPLY', n, 0.3)), 0.6, 0.0003)); return t.mat


def hide_mat(name, col=(0.082, 0.040, 0.018), seed=0.0, bands=()):
    """thick vegetable-tanned leather of a quiver: dark brown, mottled, pored, rubbed paler on the edges and scuffed where it is handled;
    bands = [(x0, x1)] along the object's X get a darker, smoother strap leather"""
    t = NT(name); sp = t.sep(t.obj); n = t.noise(420, 4, 0.65, vec=t.mapping(loc=(seed, 0, 0))); n1 = t.noise(11, 5, 0.62, vec=t.mapping(loc=(seed, 3, 0))); pore = t.voronoi(900.0)
    scuff = t.ramp(t.noise(38, 4, 0.7, vec=t.mapping(scale=(0.25, 1, 1), loc=(seed, 7, 0))), [(0.58, 0.0), (0.74, 1.0)])
    base = t.mix(n1, tuple(c * 0.55 for c in col), tuple(min(1.0, c * 1.45) for c in col)); base = t.mix(t.math('MULTIPLY', t.ramp(n, [(0.35, 0.0), (0.8, 1.0)]), 0.25), base, tuple(c * 0.45 for c in col))
    base = t.mix(t.math('MULTIPLY', scuff, 0.35), base, tuple(min(1.0, c * 2.0 + 0.02) for c in col))
    rough = t.mixf(n1, 0.50, 0.74)
    for x0, x1 in bands:
        m = t.math('MULTIPLY', t.maprange(sp[0], x0 - 0.002, x0 + 0.001, 0.0, 1.0), t.maprange(sp[0], x1 - 0.001, x1 + 0.002, 1.0, 0.0))
        base = t.mix(m, base, t.mix(n1, tuple(c * 0.30 for c in col), tuple(c * 0.55 for c in col))); rough = t.mixf(m, rough, 0.42)
    edge = t.ramp(t.pointiness, [(0.53, 0.0), (0.62, 1.0)]); base = t.mix(t.math('MULTIPLY', edge, 0.45), base, tuple(min(1.0, c * 1.9) for c in col))
    t.set(base=base, rough=rough, metal=0.0, normal=t.bump(t.math('ADD', t.math('MULTIPLY', n, 0.6), t.math('MULTIPLY', pore, 0.4)), 0.5, 0.0005)); return t.mat


def lacquer_mat(name, seed=0.0):
    """the blue bow: wood stained blue-black, the grain showing through, rubbed pale on the edges and beside the grip, with
    sinew bindings below the nocks and at both ends of the grip"""
    t = NT(name); sp = t.sep(t.obj); ax = t.math('ABSOLUTE', sp[0])
    gr = t.noise(1.0, 6, 0.7, vec=t.mapping(scale=(1.3, 95, 95), loc=(seed, 0, 0)), distortion=0.9); fine = t.noise(1.0, 3, 0.6, vec=t.mapping(scale=(4.0, 320, 320))); n2 = t.noise(150, 3, 0.6)
    pore = t.ramp(t.noise(1.0, 2, 0.5, vec=t.mapping(scale=(9.0, 600, 600))), [(0.58, 0.0), (0.68, 1.0)])
    stain = t.ramp(t.math('ADD', t.math('MULTIPLY', gr, 0.7), t.math('MULTIPLY', fine, 0.3)), [(0.28, (0.012, 0.020, 0.045)), (0.50, (0.035, 0.058, 0.115)), (0.74, (0.085, 0.125, 0.205))])
    stain = t.mix(t.math('MULTIPLY', pore, 0.7), stain, (0.008, 0.010, 0.018))
    wear = t.math('MULTIPLY', t.ramp(t.pointiness, [(0.505, 0.0), (0.55, 1.0)]), t.ramp(n2, [(0.3, 0.3), (0.7, 1.0)]))
    wear = t.math('MAXIMUM', wear, t.math('MULTIPLY', t.ramp(t.noise(60, 5, 0.8, vec=t.mapping(loc=(2, seed, 5))), [(0.60, 0.0), (0.72, 1.0)]), t.maprange(ax, 0.07, 0.22, 0.75, 0.15)))
    wood = t.mix(gr, (0.16, 0.115, 0.07), (0.34, 0.25, 0.15)); base = t.mix(wear, stain, wood)
    band = t.math('MAXIMUM', t.math('MULTIPLY', t.maprange(ax, 0.560, 0.566, 0.0, 1.0), t.maprange(ax, 0.596, 0.602, 1.0, 0.0)), t.math('MULTIPLY', t.maprange(ax, 0.074, 0.078, 0.0, 1.0), t.maprange(ax, 0.094, 0.098, 1.0, 0.0)))
    turn = t.math('ABSOLUTE', t.math('SINE', t.math('MULTIPLY', sp[0], 2400.0))); sinew = t.mix(turn, (0.30, 0.24, 0.15), (0.56, 0.48, 0.33))
    base = t.mix(band, base, sinew)
    h = t.math('ADD', t.math('ADD', t.math('MULTIPLY', gr, 0.6), t.math('MULTIPLY', fine, 0.4)), t.math('MULTIPLY', pore, -0.8)); h = t.mixf(band, h, t.math('ADD', t.math('MULTIPLY', turn, 1.6), 1.0))
    t.set(base=base, rough=t.mixf(band, t.mixf(wear, t.mixf(gr, 0.40, 0.58), 0.72), 0.7), metal=0.0, normal=t.bump(h, 0.55, 0.0006)); return t.mat


# ------------------------------------------------------------------------------------------------ parts
def blade(name, x0, length, w0, w1, thick, c, hi, fuller=0.55, claws=None, belly=0.0):
    """double-edged blade along +X from x0: width w0 at the guard to w1 before the point, lenticular-diamond section with a
    fuller over `fuller` of its length. claws = [(x, reach, span)]: hooked teeth on the +Y edge, their points raked back to the hilt.
    belly > 0 swells the blade before the point (leaf shape)."""
    xs = set(np.linspace(0.0, 1.0, 241 if hi else 25).tolist())
    xs |= {0.80, 0.86, 0.90, 0.935, 0.96, 0.98, 0.992}
    for (cx, reach, span) in (claws or []):
        u0 = (cx - x0) / length; du = span / length
        xs |= set((u0 + du * np.array([-0.02, 0.0, 0.03, 0.10, 0.25, 0.45, 0.70, 1.0] if not hi else np.linspace(-0.04, 1.02, 60))).tolist())
    xs = np.array(sorted(x for x in xs if 0.0 <= x <= 0.992)); M = 41 if hi else 5
    V = []; F = []
    for u in xs:
        x = x0 + u * length
        tip = smoothstep(0.80, 1.0, u); w = (w0 + (w1 - w0) * u + belly * math.sin(math.pi * min(1.0, u / 0.8)) ** 2 * (0.3 + 0.7 * u)) * (1.0 - tip ** 1.7 * 0.985)
        t = thick * (1.0 - 0.45 * u) * (1.0 - tip * 0.75); wp = w
        for (cx, reach, span) in (claws or []):
            s = (x - cx) / span
            if 0.0 <= s <= 1.0:      # steep hooked rise on the hilt side, long fall to the tip side
                wp += reach * (smoothstep(0.0, 0.34, s) * (1.0 - s) ** 1.25) * 1.45
        f = thick * 0.42 * (1.0 - smoothstep(fuller - 0.12, fuller, u)) * smoothstep(-0.01, 0.03, u)
        ys = np.linspace(-1.0, 1.0, M); top = []
        for yn in ys:
            y = yn * (wp if yn > 0 else w); a = abs(yn); xs_ = x - (0.62 * (wp - w) * yn ** 3 if yn > 0 else 0.0); z = t * (1.0 - a) ** 0.82 * (0.55 + 0.45 * (1.0 - a)) + 0.00018 * (1 - a ** 8) - f * math.exp(-(yn / 0.30) ** 2) * (1.0 - 0.0)
            top.append((xs_, y, max(z, 0.00012 if 0 < a < 1 else 0.0)))
        ring = top + [(p[0], p[1], -p[2]) for p in top[-2:0:-1]]; V.append(ring)
    n = len(V[0]); verts = [p for r in V for p in r]
    for i in range(len(V) - 1):
        for j in range(n):
            a = i * n + j; b = i * n + (j + 1) % n; F.append((a, b, b + n, a + n))
    tipi = len(verts); verts.append((x0 + length, 0.0, 0.0)); last = (len(V) - 1) * n
    for j in range(n):
        F.append((last + j, last + (j + 1) % n, tipi))
    F.append(tuple(range(n - 1, -1, -1)))
    ob = L.new_obj(name, verts, F, c); L.fix_normals(ob); return ob


def guard(name, x, half, c, hi, rad=(0.0095, 0.0080), sweep_fwd=0.012, knob=1.45, n=2.6):
    """cross-guard through (x, 0, 0) along Y: a rounded bar swelling to knobbed ends that lean towards the blade"""
    q = 4 if hi else 1; rows = []
    for s in np.linspace(-1, 1, 9):
        k = 1.0 + (knob - 1.0) * smoothstep(0.62, 0.92, abs(s)) - 0.18 * smoothstep(0.15, 0.6, abs(s)) * (1 - smoothstep(0.6, 0.8, abs(s))) + 0.22 * (1 - smoothstep(0.0, 0.3, abs(s)))
        rows.append((x + sweep_fwd * s * s, s * half, 0.0, rad[0] * k, rad[1] * k, n))
    return L.sweep(name, rows, nu=12 * q, nv=18 * q, c=c, up=(0, 0, 1), cap=0.75)


def studs(name, pts, r, c, hi):
    obs = []
    for i, p in enumerate(pts):
        for sz in (1, -1):
            o = L.icosphere('%s%d%s' % (name, i, 'ab'[sz > 0]), radius=r, sub=3 if hi else 1, c=c, scale=(1, 1, 0.55)); o.location = (p[0], p[1], sz * p[2]); L.apply_xf(o); obs.append(o)
    return obs


def grip(name, c, hi, x0=-0.056, x1=0.058, a=0.0128, b=0.0155):
    q = 4 if hi else 1
    return L.sweep(name, [(x0, 0, 0, a * 0.92, b * 0.92, 2.2), (x0 * 0.5, 0, 0, a * 1.04, b * 1.04, 2.2), (0.0, 0, 0, a * 1.08, b * 1.08, 2.2), (x1 * 0.5, 0, 0, a * 1.02, b * 1.02, 2.2), (x1, 0, 0, a * 0.9, b * 0.9, 2.2)], nu=12 * q, nv=14 * q, c=c, up=(0, 0, 1), cap=0.9)


def pommel(name, x, c, hi, r=0.021, flat=0.62):
    o = L.icosphere(name, radius=r, sub=4 if hi else 2, c=c, scale=(0.62, 1.0, flat)); o.location = (x, 0, 0); L.apply_xf(o); return o


def _put(hi, pairs):
    """assign source materials (only on the high source)"""
    out = []
    for obs, mat in pairs:
        for o in (obs if isinstance(obs, (list, tuple)) else [obs]):
            if hi:
                m = mat(); e = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Emission Color']
                if not e.links:                      # the emissive bake reads this colour whatever the strength: black where nothing glows
                    e.default_value = (0.0, 0.0, 0.0, 1.0)
                o.data.materials.append(m)
            out.append(o)
    return out


# ------------------------------------------------------------------------------------------------ weapons
def longsword(hi, c):
    """item-sw1 (438/7): pale blue blade, bone cross-guard with three red studs, red grip"""
    bl = blade('blade', 0.066, 0.80, 0.027, 0.017, 0.0050, c, hi); gd = guard('guard', 0.066, 0.105, c, hi); gr = grip('grip', c, hi); pm = pommel('pommel', -0.072, c, hi)
    st = studs('stud', [(0.066, 0.0, 0.0105), (0.076, 0.088, 0.0125), (0.076, -0.088, 0.0125)], 0.0062, c, hi)
    return _put(hi, [(bl, lambda: blade_steel('steel')), (gd, lambda: bone_mat('bone')), (pm, lambda: bone_mat('bone_p', seed=3.0)), (gr, lambda: leather_mat('leather_red')), (st, lambda: gem_mat('garnet', (0.55, 0.02, 0.03)))])


def clawsword(hi, c):
    """item-sw2 (438/20): the same pale blade with four hooked claws on one edge near the hilt, green bronze guard with red studs, dark red grip"""
    bl = blade('blade', 0.066, 0.84, 0.029, 0.018, 0.0054, c, hi); q = 4 if hi else 1; cl = []
    for k, (cx, reach) in enumerate([(0.150, 0.058), (0.222, 0.050), (0.288, 0.041), (0.346, 0.031)]):
        w = 0.029 - 0.011 * (cx - 0.066) / 0.84          # the blade's half width there: each claw grows out of the edge, sweeps out and hooks back to the hilt
        cl.append(L.sweep('claw%d' % k, [(cx + 0.012, w - 0.010, 0, 0.0125, 0.0030, 2.0), (cx + 0.010, w + 0.10 * reach, 0, 0.0112, 0.0030, 2.0), (cx + 0.002, w + 0.45 * reach, 0, 0.0082, 0.0024, 2.0),
                                         (cx - 0.012, w + 0.78 * reach, 0, 0.0050, 0.0016, 2.0), (cx - 0.030, w + 0.97 * reach, 0, 0.0022, 0.0009, 2.0), (cx - 0.043, w + 1.03 * reach, 0, 0.0004, 0.0003, 2.0)],
                           nu=8 * q, nv=14 * q, c=c, up=(0, 0, 1), cap=0.3))
    gd = guard('guard', 0.066, 0.092, c, hi, rad=(0.012, 0.010), sweep_fwd=0.030, knob=1.3); gr = grip('grip', c, hi); pm = pommel('pommel', -0.072, c, hi, r=0.020)
    st = studs('stud', [(0.066, 0.0, 0.0125), (0.086, 0.074, 0.0135), (0.086, -0.074, 0.0135)], 0.0060, c, hi)
    return _put(hi, [([bl] + cl, lambda: blade_steel('steel', seed=4.0)), (gd, lambda: bronze_mat('bronze')), (pm, lambda: bronze_mat('bronze_p', seed=5.0)), (gr, lambda: leather_mat('leather_dark', col=(0.19, 0.025, 0.02))), (st, lambda: gem_mat('garnet', (0.55, 0.02, 0.03)))])


def lightsword(hi, c):
    """item-sw3 (438/21): a broad cream-white blade that shines, silver guard with blue studs, blue grip"""
    bl = blade('blade', 0.066, 0.86, 0.033, 0.024, 0.0056, c, hi, fuller=0.35); gd = guard('guard', 0.066, 0.100, c, hi, rad=(0.012, 0.0095), sweep_fwd=0.010, knob=1.5); gr = grip('grip', c, hi); pm = pommel('pommel', -0.073, c, hi, r=0.022, flat=0.7)
    st = studs('stud', [(0.066, 0.0, 0.0115), (0.074, 0.082, 0.0135), (0.074, -0.082, 0.0135), (-0.073, 0.0, 0.0125)], 0.0062, c, hi)
    return _put(hi, [(bl, lambda: blade_steel('lightsteel', tint=(0.96, 0.90, 0.72), seed=7.0, glow=(1.0, 0.90, 0.62))), (gd, lambda: silver_mat('silver')), (pm, lambda: silver_mat('silver_p', seed=2.0)),
                     (gr, lambda: leather_mat('leather_blue', col=(0.022, 0.060, 0.26))), (st, lambda: gem_mat('sapphire', (0.02, 0.07, 0.55)))])


def _bow(hi, c, wood, wrap):
    """self bow, 1.30 m between the nocks, strung: limbs along X, back to +Y, string on -Y; a wrapped grip and horn nocks"""
    q = 4 if hi else 1; half = 0.65; rows = []

    def yc(s):
        return -0.150 * s * s - 0.030 * s ** 4 + 0.022 * smoothstep(0.80, 1.0, abs(s))
    for s in np.linspace(-1, 1, 33):
        a_ = abs(s); thick = 0.0135 * (1 - 0.62 * smoothstep(0.08, 1.0, a_)); wide = 0.0125 + 0.0060 * math.sin(math.pi * min(1.0, a_ / 0.75)) ** 1.2 * (1 - smoothstep(0.7, 1.0, a_)) - 0.0065 * smoothstep(0.55, 1.0, a_)
        rows.append((s * half, yc(s), 0.0, thick, wide, 2.6))
    stave = L.sweep('stave', rows, nu=10 * q, nv=64 * q, c=c, up=(0, 0, 1), cap=0.6)
    gw = L.sweep('wrap', [(s * half, yc(s), 0.0, 0.0146, 0.0138, 2.4) for s in np.linspace(-0.105, 0.105, 7)], nu=10 * q, nv=10 * q, c=c, up=(0, 0, 1), cap=0.9)
    parts = [(stave, wood), (gw, wrap)]; tips = []
    for sgn in (-1, 1):
        nk = L.sweep('nock%d' % (sgn > 0), [(sgn * half * s, yc(s) + 0.001, 0.0, 0.0056, 0.0066, 2.2) for s in (0.955, 0.975, 0.99, 1.012)], nu=8 * q, nv=6 * q, c=c, up=(0, 0, 1), cap=0.5); tips.append(nk)
    sy = yc(0.972) - 0.004; string = L.tube('string', [(-half * 0.972, sy, 0.0), (-half * 0.5, sy, 0.0), (0.0, sy, 0.0), (half * 0.5, sy, 0.0), (half * 0.972, sy, 0.0)], 0.0013, sides=8 if hi else 5, c=c)
    loops = [L.ring('loop%d' % (sgn > 0), 0.0068, 0.0015, c, seg=16 if hi else 8, sides=6 if hi else 4) for sgn in (-1, 1)]
    for sgn, lp in zip((-1, 1), loops):
        from mathutils import Matrix
        L.xform(lp, Matrix.Translation((sgn * half * 0.972, yc(0.972), 0.0)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
    parts += [(tips, lambda: bone_mat('horn', col=(0.20, 0.15, 0.10), seed=6.0)), ([string] + loops, string_mat)]
    return _put(hi, parts)


def bow_wood(hi, c):
    """item-b1 and item-b3 (438/8, 13): brown yew bow with a pale grip binding"""
    return _bow(hi, c, lambda: T.wood_mat('yew', axis=0, light=(0.27, 0.15, 0.065), dark=(0.10, 0.05, 0.022)), lambda: leather_mat('binding', col=(0.50, 0.44, 0.28), pitch=1500.0))


def bow_blue(hi, c):
    """item-b2 (438/12): the same bow in blue-grey lacquer with a grey binding"""
    return _bow(hi, c, lambda: lacquer_mat('lacquer'), lambda: leather_mat('binding', col=(0.34, 0.36, 0.42), pitch=1500.0))


def axe(hi, c):
    """item-axe (438/6): double-bitted throwing axe, 0.60 m: two pale steel crescent bits on a dark haft"""
    q = 4 if hi else 1; xc = 0.405; nu = 48 * q // 2; nv = 40 * q // 2; V = []; F = []; R = 0.150

    def surf(u, v, side):
        a = abs(v); hx = 0.021 + 0.085 * a ** 1.7 + 0.004 * a; yy = v * (R + 0.016 * (1.0 - u * u) * a)            # convex cutting edge, concave necks
        z = (0.0125 * (1.0 - a) ** 0.75 * (0.6 + 0.4 * (1 - a)) + 0.0075 * math.exp(-(v / 0.17) ** 2)) * (1.0 - 0.55 * abs(u) ** 3) + 0.0002
        if a > 0.999:
            z = 0.0
        return (xc + u * hx, yy, side * z)
    us = np.linspace(-1, 1, nu + 1); vs = np.linspace(-1, 1, nv + 1); idx = {}
    for side in (1, -1):
        for i, u in enumerate(us):
            for j, v in enumerate(vs):
                rim = (i in (0, nu)) or (j in (0, nv)); key = (0 if rim else side, i, j)
                if key not in idx:
                    p = surf(u, v, side); idx[key] = len(V); V.append((p[0], p[1], 0.0 if rim else p[2]))
        for i in range(nu):
            for j in range(nv):
                k = [idx[(0 if ((a in (0, nu)) or (b in (0, nv))) else side, a, b)] for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
                F.append(tuple(k if side < 0 else k[::-1]))
    head = L.new_obj('head', V, F, c); L.clean_mesh(head); L.fix_normals(head)
    haft = L.sweep('haft', [(-0.125, 0, 0, 0.0165, 0.0135, 2.3), (-0.105, 0, 0, 0.0180, 0.0145, 2.3), (-0.06, 0, 0, 0.0150, 0.0125, 2.3), (0.0, 0, 0, 0.0152, 0.0128, 2.3), (0.12, 0, 0, 0.0140, 0.0120, 2.3), (0.30, 0, 0, 0.0142, 0.0118, 2.4), (0.44, 0, 0, 0.0150, 0.0112, 2.6), (0.462, 0, 0, 0.0155, 0.0112, 2.6)],
                   nu=12 * q, nv=24 * q, c=c, up=(0, 0, 1), cap=0.75)
    return _put(hi, [(head, lambda: blade_steel('axesteel', tint=(0.60, 0.64, 0.70), seed=9.0)), (haft, lambda: T.wood_mat('walnut', axis=0, grip=(-0.07, 0.07), dark_from=(0.30, 0.40), light=(0.105, 0.072, 0.046), dark=(0.035, 0.024, 0.016)))])


def _vanes(name, x0, x1, r0, height, c, hi, turn=0.0):
    """three feather vanes round a shaft that runs along X: cut high at the back (the nock end, small x) and tapering to the front, 0.7 mm thick"""
    n = 14 if hi else 6; t = 0.00035; V = []; F = []
    for k in range(3):
        a = turn + 2 * math.pi * k / 3; ca, sa = math.cos(a), math.sin(a); base = len(V)
        for i in range(n + 1):
            u = i / n; x = x0 + (x1 - x0) * u; h = height * (min(1.0, u / 0.10) ** 0.6) * (1.0 - 0.80 * u ** 1.5) + 0.0005        # steep cut at the nock end, long taper forward
            for r in (r0 * 0.6, r0 + h):
                for sgn in (-1, 1):
                    V.append((x, r * ca - sgn * t * sa, r * sa + sgn * t * ca))
        for i in range(n):
            b = base + i * 4; q = b + 4                # per station: (root -, root +, top -, top +)
            F += [(b + 0, b + 2, q + 2, q + 0), (b + 1, q + 1, q + 3, b + 3), (b + 2, b + 3, q + 3, q + 2)]
        F += [(base + 0, base + 1, base + 3, base + 2), (base + n * 4 + 0, base + n * 4 + 2, base + n * 4 + 3, base + n * 4 + 1)]
    ob = L.new_obj(name, V, F, c, smooth=False); L.fix_normals(ob); return ob


def _arrow(hi, c, tag='', length=0.80, head=True, turn=0.0, vane=(0.030, 0.142, 0.0185)):
    """one arrow along +X with the string groove of its nock at the origin: horn nock, three red vanes bound at both ends, an ash shaft and a
    leaf-shaped steel head (the arrow of the 1997 bow pictures: yellow shaft, red feathers, a pale steel point). head=False stops the shaft at
    `length` with no point (the arrows that stand in the quiver). Returns [(objects, material maker)]."""
    q = 2 if hi else 1; r = 0.0042
    shaft = L.tube('shaft' + tag, [(0.008, 0, 0), (0.25 * length, 0, 0), (0.6 * length, 0, 0), (length - (0.05 if head else 0.0), 0, 0)], r, sides=6 * q, c=c)
    nock = L.sweep('nock' + tag, [(-0.004, 0, 0, 0.0034, 0.0046, 2.2), (0.0, 0, 0, 0.0050, 0.0050, 2.2), (0.006, 0, 0, 0.0052, 0.0052, 2.0), (0.013, 0, 0, 0.0044, 0.0044, 2.0)], nu=6 * q, nv=5 * q, c=c, up=(0, 0, 1), cap=0.5)
    vanes = _vanes('vanes' + tag, vane[0], vane[1], r, vane[2], c, hi, turn)
    binds = [L.tube('bind%d%s' % (i, tag), [(a, 0, 0), (b, 0, 0)], r + 0.0007, sides=6 * q, c=c) for i, (a, b) in enumerate(((vane[0] - 0.011, vane[0] + 0.001), (vane[1] - 0.002, vane[1] + 0.012)))]
    parts = [(shaft, lambda: T.wood_mat('ash', axis=0, light=(0.60, 0.45, 0.20), dark=(0.36, 0.24, 0.09))), (nock, lambda: bone_mat('hornnock', col=(0.20, 0.15, 0.10), seed=3.0)),
             (vanes, lambda: feather_mat('feather')), (binds, string_mat)]
    if head:
        x = length - 0.062
        socket = L.tube('socket' + tag, [(x - 0.012, 0, 0), (x + 0.014, 0, 0)], [r + 0.0012, r + 0.0006], sides=6 * q, c=c)
        leaf = L.sweep('head' + tag, [(x + 0.006, 0, 0, 0.0034, 0.0046, 2.0), (x + 0.020, 0, 0, 0.0030, 0.0100, 1.7), (x + 0.036, 0, 0, 0.0024, 0.0088, 1.6), (x + 0.052, 0, 0, 0.0014, 0.0046, 1.6), (x + 0.062, 0, 0, 0.0004, 0.0008, 1.6)],
                       nu=6 * q, nv=8 * q, c=c, up=(0, 0, 1), cap=0.3)
        parts.append(([socket, leaf], lambda: blade_steel('arrowsteel', tint=(0.60, 0.64, 0.70), seed=4.0)))
    return parts


def arrow(hi, c):
    """the arrow on the bow (graphics/dink/bow/idle and hit; the flying arrow is sequence 25): 0.80 m, nock at the origin, +X to the point
    (at the full draw of 69 cm its head stands 11 cm ahead of the bow hand; at 0.74 m it lay on the knuckles)"""
    return _put(hi, _arrow(hi, c))


def quiver(hi, c):
    """the quiver of red-fletched arrows that the armed bow puts on Dink's back (graphics/dink/bow/idle, hit and walk): a brown leather tube
    0.54 m long with two bands and a sewn seam, open at the top, eight arrows standing in it nock up, their big red feathers 22 to 33 cm
    above the mouth (1997 shows them as a red plume above his head; a first version with war-arrow feathers 16 to 25 cm up read as a thin
    stick with a few red marks at the play camera's distance). Origin on the tube's axis at its middle, +X to the mouth; the side that
    lies on the back is -Y."""
    from mathutils import Matrix, Vector
    seg = 32 if hi else 16; kr, kz = 1.12, 1.08
    prof = [(0.0, -0.250), (0.034, -0.250), (0.0405, -0.238), (0.0425, -0.200), (0.0445, -0.196), (0.0445, -0.168), (0.0432, -0.164), (0.0490, 0.168), (0.0512, 0.172), (0.0512, 0.204), (0.0500, 0.208),
            (0.0512, 0.236), (0.0540, 0.241), (0.0540, 0.250), (0.0500, 0.2525), (0.0470, 0.244), (0.0455, 0.150), (0.0, 0.150)]
    body = L.lathe('quiver', [(r * kr, z * kz) for r, z in prof], seg=seg, c=c, cap0=False, cap1=False)
    L.xform(body, Matrix.Rotation(math.pi / 2, 4, 'Y'))                      # the lathe's +Z becomes +X

    def wall(x):
        return kr * (0.0432 + (x / kz + 0.164) * (0.0490 - 0.0432) / 0.332)
    # the seam down the side, sewn with a pale thong: a low ridge and a row of stitches across it
    seam = L.tube('seam', [(x, 0.0, wall(x) + 0.0006) for x in np.linspace(-0.160 * kz, 0.165 * kz, 9)], 0.0024, sides=8 if hi else 5, c=c)
    stitches = [L.tube('stitch%d' % i, [(x - 0.004, -0.0065, wall(x) + 0.0010), (x, 0.0, wall(x) + 0.0034), (x + 0.004, 0.0065, wall(x) + 0.0010)], 0.0011, sides=6 if hi else 3, c=c)
                for i, x in enumerate(np.linspace(-0.15 * kz, 0.155 * kz, 20))]
    parts = [(body, lambda: hide_mat('quiverhide', bands=((-0.200 * kz, -0.164 * kz), (0.168 * kz, 0.208 * kz), (0.236 * kz, 0.26 * kz)))), (seam, lambda: hide_mat('seamhide', col=(0.060, 0.030, 0.014), seed=5.0)), (stitches, string_mat)]
    # Two lashing straps hold the quiver on the pack Dink wears: a flat dark strap round the tube with a bronze buckle on the
    # outer side (+Y); at the tube's two flanks its ends leave the leather and run on towards the back (-Y), round the pack
    # (in the game they end inside the pack the quiver lies on: hero_weapons.json bows.worn).
    for i, x in enumerate((-0.118 * kz, 0.052 * kz)):
        rr = wall(x) + 0.0004; hw = 0.0115; th = 0.0034
        band = L.lathe('strap%d' % i, [(rr, -hw), (rr + th, -hw + 0.0012), (rr + th, hw - 0.0012), (rr, hw)], seg=seg, c=c, cap0=False, cap1=False)
        L.xform(band, Matrix.Translation((x, 0.0, 0.0)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
        tails = [L.box('strap%d_tail%d' % (i, k), (x - hw, -0.115, sz * (rr + th * 0.5) - th * 0.5), (x + hw, 0.004, sz * (rr + th * 0.5) + th * 0.5), c=c, hi=hi, bevel=0.0010)
                 for k, sz in enumerate((-1.0, 1.0))]
        frame = L.ring('buckle%d' % i, 0.0135, 0.0021, c=c, seg=28 if hi else 10, sides=8 if hi else 4, squash=0.8)
        L.xform(frame, Matrix.Translation((x, rr + th + 0.0018, 0.0)) @ Matrix.Rotation(math.pi / 2, 4, 'X') @ Matrix.Scale(1.25, 4, (1, 0, 0)))
        prong = L.tube('buckle%d_prong' % i, [(x, rr + th + 0.0030, -0.0135), (x, rr + th + 0.0042, 0.0), (x, rr + th + 0.0030, 0.0150)], 0.0013, sides=6 if hi else 3, c=c)
        parts += [([band] + tails, lambda: hide_mat('straphide', col=(0.038, 0.019, 0.009), seed=9.0)), ([frame, prong], lambda: bronze_mat('bucklebronze', seed=3.0))]
    rnd = np.random.RandomState(11); mouth = 0.250 * kz; plug = 0.150 * kz
    spots = [(0.0, 0.0)] + [(0.027 * kr * math.cos(a), 0.027 * kr * math.sin(a)) for a in np.linspace(0.3, 2 * math.pi + 0.3, 7, endpoint=False)]
    for i, (py, pz) in enumerate(spots):
        top = mouth + 0.22 + 0.11 * rnd.rand(); out = 1.9 + 0.5 * (rnd.rand() - 0.5)          # nock height; how much the arrow leans out of the mouth
        nock = Vector((top, py * (1.0 + out * (top - plug)), pz * (1.0 + out * (top - plug)))); foot = Vector((plug - 0.01, py, pz))
        M = Matrix.Translation(nock) @ Vector((1, 0, 0)).rotation_difference(foot - nock).to_matrix().to_4x4()          # the arrow's +X (to its point) goes down into the tube
        for obs, mat in _arrow(hi, c, tag='_q%d' % i, length=(foot - nock).length, head=False, turn=rnd.rand() * 2.0, vane=(0.032, 0.185, 0.0245)):
            for o in (obs if isinstance(obs, (list, tuple)) else [obs]):
                L.xform(o, M)
            parts.append((obs, mat))
    return _put(hi, parts)


W_COMMON = ' Baked from a procedural source: no maker\'s marks, engraving or damage from use beyond stains and edge wear. Static (no cloth, tassel or scabbard). The grip transform was derived from the hand bone landmarks and checked in one idle and one attack frame only.'
SPECS = {
    'Sword_Long': dict(fn=longsword, item='item-sw1', pic='438/7', px=2048, hand='hand_r', emis=None, shot=dict(az=20, el=38), weak='Guard and pommel are swept and scaled solids pushed together (no peened tang, no rain-guard).' + W_COMMON,
                       dresses='longsword, 0.94 m over all, 0.80 m blade 5.4 cm wide at the guard with a fuller: blue-cast polished steel, bone cross-guard 21 cm with three garnets a side, red leather-bound grip, bone pommel'),
    'Sword_Claw': dict(fn=clawsword, item='item-sw2', pic='438/20', px=2048, hand='hand_r', emis=None, shot=dict(az=20, el=38), weak='The four claws are separate hooked blades pushed into the +Y edge, not forged from it.' + W_COMMON,
                       dresses='claw sword, 0.98 m over all, 0.84 m blade with four hooked claws on one edge above the guard: blue-cast steel, green bronze guard and pommel with garnets, dark red grip'),
    'Sword_Light': dict(fn=lightsword, item='item-sw3', pic='438/21', px=2048, hand='hand_r', emis=5.0, nits=0.9, shot=dict(az=20, el=38), weak='The shine is an emissive map on the blade (0.9 nits in game by the kit material: at 6 and at 45 the blade was a flat white shape in daylight, with no steel left to see): it lights nothing around it and has no halo; a light or bloom is runtime work.' + W_COMMON,
                        dresses='light sword, 1.0 m over all, 0.86 m broad cream-white blade that glows, silver guard and pommel with sapphires, blue leather grip'),
    'Bow_Wood': dict(fn=bow_wood, item='item-b1, item-b3', pic='438/8, 438/13', px=2048, hand='hand_l', emis=None, shot=dict(az=8, el=52), weak='Strung and at rest only: the string is a straight static tube and the limbs do not bend with the draw clip (a drawn bow needs a skinned or morphing mesh, or a second mesh swapped at full draw). No arrow; item-b3\'s flame arrow is an effect.' + W_COMMON,
                     dresses='yew self bow, 1.30 m nock to nock, strung with 15 cm brace height: brown stave, pale grip binding, dark horn nocks, flax string'),
    'Bow_Blue': dict(fn=bow_blue, item='item-b2', pic='438/12', px=2048, hand='hand_l', emis=None, shot=dict(az=8, el=52), weak='Same geometry as the wooden bow; only the surface differs. Strung and at rest only (see the wooden bow). No arrow.' + W_COMMON,
                     dresses='the blue bow: the same 1.30 m bow in blue-black stained wood, the grain showing, rubbed pale on its edges, sinew bindings below the nocks and beside the grey grip binding'),
    'Arrow': dict(fn=arrow, item='item-b1, item-b2, item-b3 (the arrow on the bow)', pic='graphics/dink/bow/idle, hit', px=1024, hand='the bow (hero_weapons.json bows.arrow)', emis=None, shot=dict(az=8, el=40),
                  weak='One arrow for all three bows (item-b3 shoots flame arrows in 1997: the flame is an effect). The vanes are thin solids with a painted barb pattern, not feather cards. Procedural bake, no fletcher\'s marks.',
                  dresses='arrow, 0.80 m: ash shaft, dark horn nock, three red goose-feather vanes 11 cm long bound with flax at both ends, a leaf-shaped steel head on a socket; origin in the nock, +X to the point'),
    'Quiver': dict(fn=quiver, item='item-b1, item-b2, item-b3 (worn on the back while a bow is armed)', pic='graphics/dink/bow/idle, hit, walk', px=2048, hand='spine_03 (hero_weapons.json bows.worn)', emis=None, shot=dict(az=20, el=30),
                   weak='Lashed to the pack with two straps whose ends stop inside it (they do not go round the pack, and no baldric crosses the chest); the quiver sits on the back by its attachment row alone. The arrows are fixed in the tube and their number never changes (1997 draws the same quiver whatever was shot). Procedural bake.',
                   dresses='quiver, brown leather tube 0.54 m long, 12 cm across at the mouth, two dark bands, two lashing straps with bronze buckles, a sewn seam and a rolled rim, eight red-fletched arrows standing in it nock up, their feathers 15 cm long; origin on the axis at the middle, +X to the mouth, -Y on the back'),
    'Axe': dict(fn=axe, item='item-axe', pic='438/6', px=1024, hand='hand_r', emis=None, shot=dict(az=20, el=40), weak='Head and haft are two solids pushed together, no eye or wedge. This is the axe in the hand; the thrown axe in flight (sequence 85) stays an effect.' + W_COMMON,
                     dresses='double-bitted throwing axe, 0.59 m: two crescent bits of blue-cast steel 31 cm across, dark walnut haft with a swelling at the butt; grip centre 12.5 cm above the butt'),
}


def build(name, mode):
    sp = SPECS[name]; L.reset(); asset = 'SM_Hero_%s_PR' % name; outdir = os.path.join(KIT, name); hi = sp['fn'](True, L.coll('Source_Hi'))
    R = L.review_setup(ground='weathered_brown_planks', ground_scale=1.6, exposure=-5.0)

    def shots(obs, tag, d):
        zmin = min(float(L.co(o)[:, 2].min()) for o in obs)
        for o in obs:
            o.location.z += 0.004 - zmin
        bpy.context.view_layer.update(); sh = sp['shot']
        L.shot(R, os.path.join(d, '%s_beauty.png' % tag), obs, az=sh['az'], el=sh['el'], fill=0.92, lens=70, res=(1600, 900), spp=192, fstop=11)
        lo_, hi_ = L.bounds(obs); cc = np.array([0.03, 0.0, 0.02])
        L.shot(R, os.path.join(d, '%s_close.png' % tag), center=cc, radius=0.17, az=-28, el=42, fill=0.9, lens=90, res=(1200, 900), spp=192, fstop=11)
        for o in obs:
            o.location.z -= 0.004 - zmin
        bpy.context.view_layer.update()
    if mode == 'review':
        shots(hi, name + '_hi', os.environ.get('DINK_REVIEW') or os.path.join(KIT, '_review')); return
    lo = L.join(sp['fn'](False, L.coll(asset)), asset); L.clean_mesh(lo); L.fix_normals(lo); L.smart_uv(lo, angle=60, margin=0.006); L.pack_uv(lo, margin=0.006)
    grip_note = {'origin': 'grip centre', 'x': 'towards the tip (upper limb for a bow)', 'bone': sp['hand'], 'item': sp['item'], 'picture_1997': sp['pic']}
    extra = {'grip': grip_note, 'pivot': 'grip centre at the origin; +X to the tip; flats of the blade on +Z / -Z (see tools/build_weapons.py)'}
    if sp.get('nits'):
        extra['emissive_nits'] = sp['nits']
    L.finish_static(asset, 'weapon', lo, hi, outdir, sp['px'], families=['hero weapon ' + sp['item']], origin={}, dresses=sp['dresses'], extrude=0.0012, maxdist=0.004, third_party=['weathered_brown_planks (render floor)'],
                    script=SCRIPT + ' ' + name + ' final', ss=1, weaknesses=sp['weak'], collision=False, extra=extra, emissive=bool(sp['emis']), emissive_strength=sp['emis'], keep_hi=False)
    shots([lo], 'render', outdir); L.save_blend()


if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        build(n, mode)
