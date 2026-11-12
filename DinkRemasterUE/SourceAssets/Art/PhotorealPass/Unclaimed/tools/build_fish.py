"""fish (434 animals/fish/fish1) and fish_flopping (439, 441 animals/fish/flop): a 45 cm trout-built fish on a spine chain.

    tools/bl.sh build_fish.py [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_fish.py'
ZC = 0.075
J = {'nose': (-0.225, 0, ZC), 's1': (-0.14, 0, ZC), 's2': (-0.05, 0, ZC), 's3': (0.04, 0, ZC), 's4': (0.11, 0, ZC), 's5': (0.185, 0, ZC), 'tail': (0.29, 0, ZC)}
BONES = [('root', (0, 0, 0), (0, 0.05, 0), None), ('spine_01', 's2', 's1', 'root'), ('head', 's1', 'nose', 'spine_01'), ('spine_02', 's2', 's3', 'root'), ('spine_03', 's3', 's4', 'spine_02'), ('spine_04', 's4', 's5', 'spine_03'), ('tail_01', 's5', 'tail', 'spine_04')]


def fin(name, base0, base1, tip0, tip1, c, hi, thick=0.0012, belly=0.0):
    """rayed fin as a thin closed shell: u along the base, v out along the rays"""
    b0, b1, t0, t1 = (np.array(p, float) for p in (base0, base1, tip0, tip1)); nu, nv = (24, 14) if hi else (5, 3)

    def fn(U, V):
        B = b0[None] * (1 - U[:, None]) + b1[None] * U[:, None]; T_ = t0[None] * (1 - U[:, None]) + t1[None] * U[:, None]; P = B * (1 - V[:, None]) + T_ * V[:, None]
        P = P + (T_ - B) * (belly * np.sin(np.pi * U) * V)[:, None]; return P
    o = L.grid_surface(name, fn, nu, nv, c, closed_u=False); L.mod(o, 'SOLIDIFY', thickness=thick, offset=0.0); L.apply_mods(o); L.fix_normals(o); return o


def build(hi, c):
    q = 5 if hi else 1
    body = L.sweep('body', [(-0.225, 0, ZC - 0.004, 0.007, 0.009, 2.2), (-0.20, 0, ZC - 0.002, 0.022, 0.03, 2.1), (-0.14, 0, ZC, 0.035, 0.052, 2.1), (-0.05, 0, ZC + 0.002, 0.041, 0.064, 2.05), (0.04, 0, ZC + 0.001, 0.035, 0.057, 2.05),
                            (0.11, 0, ZC, 0.021, 0.039, 2.05), (0.165, 0, ZC, 0.010, 0.021, 2.1), (0.192, 0, ZC, 0.006, 0.018, 2.2)], nu=20 * q, nv=24 * q, c=c, up=(0, 0, 1), cap=0.6)
    fins = [fin('caudal_u', (0.185, 0, ZC + 0.004), (0.19, 0, ZC + 0.017), (0.262, 0, ZC + 0.006), (0.295, 0, ZC + 0.078), c, hi), fin('caudal_l', (0.19, 0, ZC - 0.017), (0.185, 0, ZC - 0.004), (0.295, 0, ZC - 0.078), (0.262, 0, ZC - 0.006), c, hi),
            fin('dorsal', (-0.045, 0, ZC + 0.062), (0.045, 0, ZC + 0.056), (-0.005, 0, ZC + 0.112), (0.075, 0, ZC + 0.078), c, hi, belly=0.15), fin('adipose', (0.115, 0, ZC + 0.036), (0.135, 0, ZC + 0.03), (0.135, 0, ZC + 0.05), (0.15, 0, ZC + 0.04), c, hi),
            fin('anal', (0.105, 0, ZC - 0.036), (0.06, 0, ZC - 0.05), (0.14, 0, ZC - 0.06), (0.09, 0, ZC - 0.085), c, hi), fin('pelvic_l', (-0.005, 0.012, ZC - 0.058), (0.025, 0.012, ZC - 0.055), (0.03, 0.03, ZC - 0.082), (0.065, 0.022, ZC - 0.07), c, hi),
            fin('pelvic_r', (0.025, -0.012, ZC - 0.055), (-0.005, -0.012, ZC - 0.058), (0.065, -0.022, ZC - 0.07), (0.03, -0.03, ZC - 0.082), c, hi),
            fin('pect_l', (-0.135, 0.032, ZC - 0.03), (-0.12, 0.034, ZC - 0.012), (-0.07, 0.07, ZC - 0.06), (-0.055, 0.06, ZC - 0.022), c, hi), fin('pect_r', (-0.12, -0.034, ZC - 0.012), (-0.135, -0.032, ZC - 0.03), (-0.055, -0.06, ZC - 0.022), (-0.07, -0.07, ZC - 0.06), c, hi)]
    eyes = [C.ball('eye_%d' % k, (-0.182, sy * 0.0235, ZC + 0.01), 0.0105, c, seg=16 if hi else 8, squash=(1, 0.6, 1)) for k, sy in enumerate((1, -1))]
    if hi:
        Pq = L.co(body); N = L.vnormals(body); x, z = Pq[:, 0], Pq[:, 2] - ZC
        gill = np.exp(-((x + 0.148 - 0.5 * z * z * 6) / 0.004) ** 2) * smoothstep(0.05, 0.03, np.abs(z)); mouth = np.exp(-((z + 0.006 + (x + 0.225) * 0.25) / 0.0025) ** 2) * smoothstep(-0.175, -0.2, x)
        L.set_co(body, Pq + N * (-0.0022 * gill - 0.002 * mouth + 0.0004 * fbm(Pq, 3, 90, 2))[:, None]); C.set_attr(body, 'line', np.clip(gill + mouth, 0, 1))
        t = NT('skin'); sp = t.sep(t.obj); zz = t.math('SUBTRACT', sp[2], ZC); n = t.noise(40, 5, 0.65); n2 = t.noise(200, 3, 0.6); ln = t.attr('line')
        sc = t.voronoi(1.0, vec=t.mapping(scale=(210, 210, 300)), feature='DISTANCE_TO_EDGE'); sce = t.ramp(sc, [(0.0, 1.0), (0.12, 0.0)]); head = t.maprange(sp[0], -0.15, -0.135, 1.0, 0.0)
        back = t.mix(n, (0.020, 0.040, 0.055), (0.055, 0.095, 0.115)); flank = t.mix(n, (0.30, 0.36, 0.40), (0.52, 0.58, 0.60)); belly = t.mix(n2, (0.62, 0.62, 0.58), (0.80, 0.80, 0.76))
        col = t.mix(t.maprange(t.math('ADD', zz, t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.02)), 0.005, 0.04, 0.0, 1.0, interp='SMOOTHSTEP'), flank, back); col = t.mix(t.maprange(zz, -0.02, -0.045, 0.0, 1.0, interp='SMOOTHSTEP'), col, belly)
        band = t.math('MULTIPLY', t.ramp(t.math('ABSOLUTE', t.math('ADD', zz, 0.004)), [(0.006, 1.0), (0.02, 0.0)]), 0.35); col = t.mix(band, col, (0.50, 0.22, 0.26))                    # the rosy lateral band
        spots = t.math('MULTIPLY', t.ramp(t.voronoi(95, feature='F1', vec=t.mapping(loc=(1, 2, 3))), [(0.12, 1.0), (0.2, 0.0)]), t.maprange(zz, -0.012, 0.01, 0.0, 1.0)); col = t.mix(t.math('MULTIPLY', spots, 0.85), col, (0.012, 0.014, 0.016))
        col = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', sce, t.math('SUBTRACT', 1.0, head)), 0.35), col, (0.05, 0.07, 0.08)); col = t.mix(ln, col, (0.03, 0.012, 0.012))
        t.set(base=col, rough=t.mixf(n2, 0.16, 0.32), metal=t.math('MULTIPLY', t.maprange(zz, -0.04, 0.03, 0.25, 0.55), t.math('SUBTRACT', 1.0, ln)), normal=t.bump(t.math('MULTIPLY', t.ramp(sc, [(0.0, 0.0), (0.3, 1.0)]), t.math('SUBTRACT', 1.0, head)), 0.5, 0.0006), coat=0.6, coat_rough=0.08)
        body.data.materials.append(t.mat)
        f = NT('fin'); uv = f.sep(f.uv); ray = f.ramp(f.math('ABSOLUTE', f.math('SUBTRACT', f.math('FRACT', f.math('MULTIPLY', uv[0], 11.0)), 0.5)), [(0.0, 1.0), (0.14, 0.0)]); fn_ = f.noise(60, 4, 0.6)
        fc = f.mix(uv[1], (0.10, 0.12, 0.12), (0.30, 0.30, 0.26)); fc = f.mix(f.math('MULTIPLY', ray, 0.6), fc, (0.04, 0.05, 0.055)); fc = f.mix(f.math('MULTIPLY', f.ramp(fn_, [(0.6, 0.0), (0.7, 1.0)]), 0.6), fc, (0.015, 0.018, 0.02))
        f.set(base=fc, rough=0.3, normal=f.bump(ray, 0.6, 0.0006), coat=0.5, coat_rough=0.1)
        for o in fins:
            o.data.materials.append(f.mat)
        e = NT('eye'); nrm = e.sep(e.gnormal); side = e.math('ABSOLUTE', nrm[1]); e.set(base=e.mix(e.ramp(side, [(0.86, 0.0), (0.9, 1.0)]), e.mix(e.noise(300, 2, 0.5), (0.45, 0.42, 0.30), (0.70, 0.68, 0.55)), (0.006, 0.006, 0.006)), rough=0.04, metal=0.3, coat=1.0, coat_rough=0.02)
        for o in eyes:
            o.data.materials.append(e.mat)
    return [body] + fins + eyes


WEAK = ('Body is one swept solid with gill and mouth lines pressed in: no opening mouth, gill covers, nostrils or lateral-line scales, and the scale pattern is a Voronoi grid in the normal map. '
        'Fins are 1.2 mm opaque shells with rays painted on; real fins are translucent. A generic trout: the original frame is a pale blue fish seen from above through water. '
        'Seven-bone spine chain with automatic weights, checked in one bend (render_pose.png); no swim or flop clips, which is what both families actually show. The flopping fish is this mesh on its side.')


def main(mode):
    L.reset(); asset = 'SK_Fish_PR'; outdir = os.path.join(L.UNC, 'fish', 'Fish'); hi = build(True, L.coll('Source_Hi'))
    R_ = L.review_setup(ground='coast_sand_01', ground_scale=1.2, exposure=-5.1)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=28, el=22, fill=0.8, lens=80, spp=192, fstop=8)
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(-0.14, 0, ZC), radius=0.1, az=-30, el=14, fill=0.9, lens=100, res=(1000, 800), spp=192, fstop=11)
    if mode == 'review':
        shots(hi, 'Fish_hi', L.REVIEW); return
    lo = L.make_lo(hi, 1800, asset, L.coll(asset), angle=66, margin=0.008); arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset)); fams = ['fish', 'fish_flopping']; ids = L.origin_ids(fams)
    C.finish_creature(asset, 'creature', lo, hi, arm, outdir, 1024, families=fams + ['434 animals/fish/fish1', '439, 441 animals/fish/flop'], origin=ids,
                      dresses='trout-built fish, 52 cm with the tail: dark blue-grey back, silver flanks with a rosy band and black spots, pale belly, rayed fins',
                      weaknesses=WEAK, script=SCRIPT + ' final', extrude=0.003, maxdist=0.008, ss=2)
    shots([lo], 'render', outdir)
    C.pose(arm, {'spine_02': (0, 0, 14), 'spine_03': (0, 0, 20), 'spine_04': (0, 0, 22), 'tail_01': (0, 0, 20), 'head': (0, 0, -10)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=10, el=50, fill=0.8, lens=80, res=(1000, 750), spp=128); C.pose(arm, {}); L.save_blend()


if __name__ == '__main__':
    a = L.args(); main(a[0] if a else 'review')
