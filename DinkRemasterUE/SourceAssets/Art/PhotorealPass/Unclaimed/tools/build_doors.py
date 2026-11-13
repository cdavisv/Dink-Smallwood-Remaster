"""Doors and windows of the unclaimed families: church door (60/7), castle door (68/1), log cabin door (59/2), snow-house
door (96/10), small church window (60/2, 60/9) and the stained-glass windows (60/4, 60/5, 60/6).

Door leaves follow the `door` class: hinge edge at x = 0, centred through the thickness, floor at z = 0, leaf along +X.

    tools/bl.sh build_doors.py <name,name|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
import build_props as P
import build_props3 as P3
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_doors.py'


def plank_mat(name, plank_w=0.16, light=(0.15, 0.085, 0.036), dark=(0.05, 0.026, 0.011), x0=0.0, weather=0.3):
    """a door leaf of vertical planks: each plank its own tone and grain offset, dark open joints, weathering low down, nail heads in rows"""
    t = NT(name); sp = t.sep(t.obj); fx = t.math('DIVIDE', t.math('SUBTRACT', sp[0], x0), plank_w); idx = t.math('FLOOR', fx); fr = t.math('FRACT', fx); rnd = t.sep(t.voronoi(1.0, vec=t.comb(idx, 0.0, 0.0), out='Color'))
    gr = t.noise(1.0, 6, 0.65, vec=t.comb(t.math('ADD', t.math('MULTIPLY', sp[0], 60.0), t.math('MULTIPLY', rnd[0], 40.0)), t.math('MULTIPLY', sp[1], 60.0), t.math('MULTIPLY', sp[2], 2.2)), distortion=0.9)
    pore = t.ramp(t.noise(1.0, 2, 0.5, vec=t.comb(t.math('MULTIPLY', sp[0], 420.0), t.math('MULTIPLY', sp[1], 420.0), t.math('MULTIPLY', sp[2], 8.0))), [(0.56, 0.0), (0.66, 1.0)])
    base = t.ramp(gr, [(0.3, dark), (0.5, light), (0.72, tuple(min(1, v * 1.45) for v in light))]); base = t.hsv(base, v=t.maprange(rnd[1], 0, 1, 0.75, 1.2)); base = t.mix(t.math('MULTIPLY', pore, 0.7), base, tuple(v * 0.35 for v in dark))
    joint = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', fr, 0.5)), [(0.465, 0.0), (0.495, 1.0)]); base = t.mix(t.math('MULTIPLY', joint, 0.92), base, (0.008, 0.006, 0.004))
    wz = t.maprange(t.math('ADD', sp[2], t.math('MULTIPLY', t.math('SUBTRACT', gr, 0.5), 0.5)), 0.0, 0.7, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', wz, weather), base, (0.22, 0.20, 0.17))       # rain-bleached and splashed low down
    grime = t.ramp(t.noise(5, 5, 0.65), [(0.4, 0.0), (0.75, 1.0)]); base = t.mix(t.math('MULTIPLY', grime, 0.4), base, (0.03, 0.022, 0.015))
    t.set(base=base, rough=t.mixf(gr, 0.55, 0.78), normal=t.bump(t.math('ADD', t.math('ADD', t.math('MULTIPLY', gr, 0.6), t.math('MULTIPLY', pore, -0.9)), t.math('MULTIPLY', joint, -5.0)), 0.4, 0.0012)); return t.mat


def leaf(parts, c, hi, w, spring, kind, th=0.06, plank_w=0.16, mat_kw=None, straps=(0.35, 1.4), strap_len=0.75, ring=True, ledges=(), x0=0.0, rise=None, name='leaf'):
    """one plank leaf with iron strap hinges on the x0 edge; returns the leaf object"""
    out = [(x + w / 2 + x0, z) for x, z in L.arch_outline(w, spring, kind, n=18, rise=rise)]; lf = L.prism(name, out, -th / 2, th / 2, c, hi, bevel=0.006); parts.append(lf); im = T.iron_mat('iron_' + name, rust=0.55, seed=21.0) if hi else None
    if hi:
        lf.data.materials.append(plank_mat('planks_' + name, plank_w=plank_w, x0=x0, **(mat_kw or {})))
    for k, z in enumerate(straps):                             # strap hinges on both faces, tapering to a point
        for sy in (-1, 1):
            o = L.sweep('strap_%s%d%d' % (name, k, sy), [(x0 - 0.02, sy * (th / 2 + 0.004), z, 0.006, 0.032, 5), (x0 + 0.1, sy * (th / 2 + 0.004), z, 0.005, 0.03, 5), (x0 + strap_len * 0.7, sy * (th / 2 + 0.004), z, 0.004, 0.02, 5), (x0 + strap_len, sy * (th / 2 + 0.004), z, 0.003, 0.006, 4)],
                        nu=8 if hi else 4, nv=24 if hi else 5, c=c, up=(0, 1, 0), cap=0.6)
            if hi:
                o.data.materials.append(im)
            parts.append(o)
        o = L.sweep('pin_%s%d' % (name, k), [(x0 - 0.022, 0, z - 0.06, 0.014, 0.014, 2), (x0 - 0.022, 0, z + 0.06, 0.014, 0.014, 2)], nu=10 if hi else 6, nv=6 if hi else 3, c=c, up=(0, 1, 0), cap=0.7)
        if hi:
            o.data.materials.append(im)
        parts.append(o)
    for k, z in enumerate(ledges):                             # ledges across the back
        o = L.box('ledge_%s%d' % (name, k), (x0 + 0.03, th / 2, z - 0.06), (x0 + w - 0.03, th / 2 + 0.035, z + 0.06), c, hi, bevel=0.005, warp=0.002, seed=k)
        if hi:
            o.data.materials.append(T.wood_mat('ledge', axis=0, light=(0.15, 0.085, 0.036), dark=(0.05, 0.026, 0.011)))
        parts.append(o)
    if ring:
        rg = L.ring('ring_' + name, 0.055, 0.008, c, seg=32 if hi else 10, sides=8 if hi else 4); L.xform(rg, Matrix.Translation((x0 + w - 0.14, -th / 2 - 0.012, 1.02)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        bs = C.ball('boss_' + name, (x0 + w - 0.14, -th / 2 - 0.004, 1.075), 0.022, c, seg=12 if hi else 6, squash=(1, 0.5, 1))
        for o in (rg, bs):
            if hi:
                o.data.materials.append(im)
            parts.append(o)
    return lf


def door_church(hi, c):
    parts = []; leaf(parts, c, hi, 1.15, 1.85, 'round', th=0.065, plank_w=0.164, straps=(0.35, 1.05, 1.75), strap_len=0.8, mat_kw=dict(light=(0.10, 0.058, 0.026), dark=(0.035, 0.018, 0.008))); return parts


def door_castle(hi, c):
    parts = []; leaf(parts, c, hi, 1.9, 2.5, 'round', th=0.09, plank_w=0.19, straps=(0.45, 1.5, 2.55), strap_len=1.3, ledges=(0.4, 1.4, 2.4), mat_kw=dict(light=(0.17, 0.10, 0.045), dark=(0.06, 0.03, 0.013), weather=0.4)); return parts


def door_cabin(hi, c):
    parts = []; leaf(parts, c, hi, 1.0, 1.95, 'flat', th=0.05, plank_w=0.2, straps=(0.35, 1.6), strap_len=0.6, ledges=(0.3, 1.0, 1.7), mat_kw=dict(light=(0.20, 0.12, 0.055), dark=(0.07, 0.038, 0.017), weather=0.5)); return parts


def door_snow(hi, c):
    """two-leaf plank door in a dark timber frame with a projecting lintel (the frame travels with the asset; the leaves do not open separately)"""
    parts = []; wm = [T.wood_mat('frame_%s' % 'xyz'[a], axis=a, light=(0.10, 0.058, 0.026), dark=(0.035, 0.018, 0.008)) for a in range(3)] if hi else [None] * 3
    for k, (mn, mx) in enumerate((((-0.02, -0.07, 0), (0.1, 0.07, 2.2)), ((1.38, -0.07, 0), (1.5, 0.07, 2.2)), ((-0.14, -0.1, 2.2), (1.62, 0.1, 2.36)))):
        d = np.abs(np.array(mx) - np.array(mn)); o = L.box('frame%d' % k, mn, mx, c, hi, bevel=0.008, warp=0.002, seed=k)
        if hi:
            o.data.materials.append(wm[int(np.argmax(d))])
        parts.append(o)
    kw = dict(light=(0.14, 0.08, 0.035), dark=(0.045, 0.024, 0.01), weather=0.35)
    leaf(parts, c, hi, 0.635, 2.18, 'flat', th=0.05, plank_w=0.16, straps=(0.4, 1.75), strap_len=0.45, ring=False, mat_kw=kw, x0=0.105, name='l')
    leaf(parts, c, hi, 0.635, 2.18, 'flat', th=0.05, plank_w=0.16, straps=(), ring=True, mat_kw=kw, x0=0.745, name='r')
    return parts


# ---------------------------------------------------------------------------------------------- windows
def surround(parts, c, hi, w, spring, kind, depth=0.3, jamb=0.16, seed=0, tint=(0.42, 0.44, 0.50), rise=None):
    """dressed-stone window surround: sill, jamb stones and an arch of voussoirs following the outline"""
    m = [P3.stone(90 + seed + k, tint=tuple(v * (1 + 0.06 * k) for v in tint), value=0.75, sat=0.4, moss=0.25, lichen=0.3) for k in range(3)] if hi else [None] * 3
    P3.blocks(parts, 'sill', (-w / 2 - jamb - 0.05, -depth / 2 - 0.05, -0.14), (w / 2 + jamb + 0.05, depth / 2, 0.0), c, hi, m[0], seed=seed)
    n = max(2, int(spring / 0.3))
    for s in (-1, 1):
        for k in range(n):
            x0 = s * w / 2; P3.blocks(parts, 'jamb', (min(x0, x0 + s * jamb), -depth / 2, k * spring / n + 0.003), (max(x0, x0 + s * jamb), depth / 2, (k + 1) * spring / n - 0.003), c, hi, m[(k + (s > 0)) % 3], seed=seed + 10 + k + 5 * s)
    out = L.arch_outline(w, spring, kind, n=11, rise=rise)[2:]
    for k in range(len(out) - 1):
        a = np.array(out[k]); b = np.array(out[k + 1]); mid = (a + b) / 2; d = b - a; ln = float(np.linalg.norm(d)); ang = math.atan2(d[1], d[0])
        o = P3.blocks(parts, 'vous', (-ln / 2 - 0.004, -depth / 2, 0.0), (ln / 2 + 0.004, depth / 2, jamb), c, hi, m[k % 3], seed=seed + 30 + k, bevel=0.008)
        L.xform(o, Matrix.Translation((mid[0], 0, mid[1])) @ Matrix.Rotation(-(ang + math.pi), 4, 'Y'))


def glass_mat(name, stained=None, w=0.6, h=1.6, seed=0.0, z0=0.14):
    """leaded glass. Plain: small dark quarries. stained = palette: irregular coloured pieces round a robed figure with a pale face, iron saddle bars across"""
    t = NT(name); sp = list(t.sep(t.obj)); sp[2] = t.math('SUBTRACT', sp[2], z0); n = t.noise(30, 4, 0.6); n2 = t.noise(300, 3, 0.6)          # z0: the sill lifts the glass off the pivot plane
    if not stained:
        a = t.math('MULTIPLY', t.math('ADD', sp[0], t.math('MULTIPLY', sp[2], 0.75)), 13.0); b = t.math('MULTIPLY', t.math('SUBTRACT', sp[0], t.math('MULTIPLY', sp[2], 0.75)), 13.0)
        lead = t.math('MAXIMUM', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', a), 0.5)), [(0.43, 0.0), (0.47, 1.0)]), t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', b), 0.5)), [(0.43, 0.0), (0.47, 1.0)]))
        cv = t.sep(t.voronoi(1.0, vec=t.comb(t.math('FLOOR', a), t.math('FLOOR', b), 0.0), out='Color')); col = t.mix(cv[0], (0.004, 0.006, 0.012), (0.014, 0.022, 0.036)); tilt = cv[1]
    else:
        v = t.mapping(scale=(11.0, 1.0, 9.0), loc=(seed, 0, seed * 0.7)); cell = t.voronoi(1.0, vec=v, feature='DISTANCE_TO_EDGE'); cv = t.sep(t.voronoi(1.0, vec=v, out='Color')); lead = t.ramp(cell, [(0.0, 1.0), (0.05, 0.0)])
        bars = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', t.math('MULTIPLY', sp[2], 2.6)), 0.5)), [(0.47, 0.0), (0.49, 1.0)]); lead = t.math('MAXIMUM', lead, bars)
        fx = t.math('DIVIDE', sp[0], w * 0.30); fz = t.math('DIVIDE', t.math('SUBTRACT', sp[2], h * 0.48), h * 0.34); fig = t.ramp(t.vmath('LENGTH', t.comb(fx, fz, 0.0)), [(0.85, 1.0), (1.0, 0.0)])
        face = t.ramp(t.vmath('LENGTH', t.comb(t.math('DIVIDE', sp[0], w * 0.11), t.math('DIVIDE', t.math('SUBTRACT', sp[2], h * 0.80), w * 0.13), 0.0)), [(0.9, 1.0), (1.0, 0.0)])
        bg = t.ramp(cv[0], [(0.0, stained[0]), (0.34, stained[1]), (0.67, stained[2]), (1.0, stained[0])], interp='CONSTANT'); robe = t.ramp(cv[1], [(0.0, stained[3]), (0.5, stained[4]), (1.0, stained[3])], interp='CONSTANT')
        col = t.mix(fig, bg, robe); col = t.mix(face, col, (0.55, 0.42, 0.30)); col = t.hsv(col, v=t.maprange(n, 0.2, 0.8, 0.65, 1.3)); tilt = cv[2]
    dust = t.ramp(t.noise(6, 5, 0.65), [(0.5, 0.0), (0.8, 1.0)]); col = t.mix(t.math('MULTIPLY', dust, 0.35), col, (0.09, 0.09, 0.085)); base = t.mix(lead, col, t.mix(n2, (0.035, 0.037, 0.04), (0.10, 0.105, 0.11)))
    t.set(base=base, rough=t.mixf(lead, t.mixf(n, 0.06, 0.3), 0.55), metal=t.mixf(lead, 0.0, 0.85), normal=t.bump(t.math('ADD', t.math('MULTIPLY', lead, 2.0), tilt), 0.4, 0.003), spec=0.7); return t.mat


def window(hi, c, w, spring, kind, stained=None, lights=1, seed=0, rise=None):
    parts = []; surround(parts, c, hi, w, spring, kind, seed=seed, rise=rise)
    out = L.arch_outline(w - 0.01, spring, kind, n=18, rise=rise); g = L.prism('glass', out, -0.012, 0.012, c, hi, bevel=0.002); parts.append(g)
    if hi:
        hgt = max(z for x, z in out); g.data.materials.append(glass_mat('glass', stained=stained, w=w / lights, h=hgt, seed=float(seed)))
    if lights == 2:                                             # a stone mullion between the two lights
        P3.blocks(parts, 'mullion', (-0.04, -0.07, 0.0), (0.04, 0.07, spring + (w / 2) * 0.55), c, hi, P3.stone(99, tint=(0.42, 0.44, 0.50), value=0.75, sat=0.4, moss=0.2) if hi else None, seed=77, bevel=0.01)
    for o in parts:                                # stand it on its sill: the pivot plane is the underside of the sill
        Pq = L.co(o); Pq[:, 2] += 0.14; L.set_co(o, Pq)
    return parts


PAL_A = ((0.010, 0.030, 0.20), (0.015, 0.11, 0.05), (0.03, 0.10, 0.22), (0.30, 0.012, 0.010), (0.36, 0.20, 0.02))
PAL_B = ((0.20, 0.13, 0.015), (0.012, 0.035, 0.16), (0.05, 0.02, 0.10), (0.26, 0.20, 0.10), (0.30, 0.02, 0.012))
W_DOOR = ' One slab with the plank joints, grain and nails in the textures: the joints are not modelled gaps and the edge of the leaf shows no board ends. Iron straps are plain tapered bars without nail heads; there is no lock or latch. No frame or wall: the opening belongs to the building family.'
W_GLASS = ' The glass is opaque: colour, lead and saddle bars are baked onto a flat pane, so it does not transmit light or throw colour (a translucent or emissive material is engine work). The surround is bevelled 12-triangle blocks with open joints.'
SH_DOOR = dict(az=24, el=8, fill=1.1, close=(0.75, 0.0, 0.45, 0.25))
SPECS = {
    'Door_Church': dict(fn=door_church, fam='church_door', seq='60 struct/church/chrch- frame 7', cls='door', px=1024, tris=900, ground='weathered_brown_planks', third=['rusty_metal_02'], pivot_rule='hinge', shot=SH_DOOR, extrude=0.004, maxdist=0.012,
                        weak='The original shows the door in its stone arch; only the leaf is built.' + W_DOOR, dresses='church door leaf, 1.15 x 2.4 m, round-headed, seven dark oak planks, three iron strap hinges, ring handle',
                        extra={'pivot': 'hinge edge at x = 0, centred through the thickness, floor at z = 0; the leaf extends along +X'}),
    'Door_Castle': dict(fn=door_castle, fam='castle_door', seq='68 struct/castle/cdoor- frame 1', cls='door', px=2048, tris=1100, ground='weathered_brown_planks', third=['rusty_metal_02'], pivot_rule='hinge', shot=SH_DOOR, extrude=0.004, maxdist=0.012,
                        weak='A single wide leaf; a gate this size would be two leaves with a wicket.' + W_DOOR, dresses='castle door leaf, 1.9 x 3.45 m, round-headed, ten oak planks ledged behind, three long strap hinges, ring handle',
                        extra={'pivot': 'hinge edge at x = 0, centred through the thickness, floor at z = 0; the leaf extends along +X'}),
    'Door_Cabin': dict(fn=door_cabin, fam='log_cabin_door', seq='59 struct/cabin/cabin- frame 2', cls='door', px=1024, tris=800, ground='weathered_brown_planks', third=['rusty_metal_02'], pivot_rule='hinge', shot=SH_DOOR, extrude=0.004, maxdist=0.012,
                       weak=W_DOOR.strip(), dresses='log cabin door leaf, 1.0 x 1.95 m, five weathered planks ledged behind, two strap hinges, ring handle',
                       extra={'pivot': 'hinge edge at x = 0, centred through the thickness, floor at z = 0; the leaf extends along +X'}),
    'Door_Snow_House': dict(fn=door_snow, fam='snow_house_door', seq='96 struct/building/build- frame 10', cls='prop', px=1024, tris=1300, ground='weathered_brown_planks', third=['rusty_metal_02'], shot=dict(az=20, el=8, fill=1.1, close=(0.5, 0.0, 0.5, 0.3)), extrude=0.004, maxdist=0.012,
                            weak='Frame and both leaves are one mesh, so it cannot swing; it is classed as a prop with a base-centre pivot for that reason. Split the leaves off as door-class assets if it must open.' + W_DOOR,
                            dresses='house door in its frame, 1.6 x 2.36 m: two plank leaves with strap hinges and a ring, dark timber posts and a projecting lintel',
                            extra={'pivot': 'base centre of the frame (the leaves are not separate), front on -Y'}),
    'Window_Church_Small': dict(fn=lambda hi, c: window(hi, c, 0.5, 0.62, 'round', seed=1), fam='church_window_small', seq='60 struct/church/chrch- frames 2, 9', cls='prop', px=1024, tris=0, lo='param', ground='forrest_ground_01', third=['rock_face_03'], extrude=0.006, maxdist=0.02,
                                shot=dict(az=18, el=6, fill=1.1, close=(0.5, 0.0, 0.5, 0.3)), weak='A 19-pixel dark frame: built as a small round-headed leaded window in a stone surround.' + W_GLASS,
                                dresses='small church window, 0.5 x 0.87 m opening: round-headed, dark leaded quarries, dressed dark stone surround and sill'),
    'Window_Stained_Twin': dict(fn=lambda hi, c: window(hi, c, 1.3, 1.5, 'pointed', stained=PAL_A, lights=2, seed=3), fam='church_stained_glass', seq='60 struct/church/chrch- frame 4', cls='prop', px=2048, tris=0, lo='param', ground='forrest_ground_01', third=['rock_face_03'],
                                extrude=0.006, maxdist=0.02, shot=dict(az=16, el=6, fill=1.1, close=(0.4, 0.0, 0.5, 0.25)),
                                weak='The figures are abstract: an oval of robe colours with a pale disc for a face in each light, not drawn saints. No tracery above the mullion.' + W_GLASS,
                                dresses='two-light stained-glass window, 1.3 m wide and 2.6 m to the point: blue and green ground, red and amber figures, lead cames and saddle bars, stone surround with a mullion'),
    'Window_Stained_Lancet': dict(fn=lambda hi, c: window(hi, c, 0.62, 1.35, 'pointed', stained=PAL_B, seed=6), fam='church_stained_glass', seq='60 struct/church/chrch- frames 5, 6', cls='prop', px=1024, tris=0, lo='param', ground='forrest_ground_01', third=['rock_face_03'],
                                  extrude=0.006, maxdist=0.02, shot=dict(az=16, el=6, fill=1.1, close=(0.5, 0.0, 0.5, 0.25)),
                                  weak='One lancet stands for both original frames (5 and 6 differ in their glass); the figure is abstract.' + W_GLASS,
                                  dresses='single-light stained-glass lancet, 0.62 m wide and 1.9 m to the point: amber and blue ground, a robed figure in ivory and red, stone surround'),
}
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
