"""dragon_statue (159 struct/stone/mdink/monum- frames 5, 6): a weathered stone dragon rearing on an orb.

The dragon is the build_dragon source re-posed (tail wrapped down round the orb, wings folded half up), at
0.42 scale, fused with the orb and a low plinth and given one carved-stone material.

    tools/bl.sh build_statue.py [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_dragon as D
import build_props as P
from pplib import NT, fbm
from mathutils import Matrix

SCRIPT = 'build_statue.py'
SC = 0.42; ORB = 0.46; ORB_Z = 0.18 + ORB


def build_hi(c):
    # re-pose through the joint table: tail curls down and round, wings half raised
    D.J.update({'tail1': (0, 0.72, 0.95), 'tail2': (0.25, 1.08, 0.45), 'tail3': (0.75, 1.12, -0.25), 'tail4': (1.15, 0.6, -0.85), 'tail5': (1.05, -0.1, -1.25), 'tail6': (0.55, -0.6, -1.45), 'tail7': (0.0, -0.75, -1.5)})
    for s, sx in (('l', 1), ('r', -1)):
        D.J.update({'welbow_' + s: (0.85 * sx, 0.62, 3.35), 'wwrist_' + s: (1.35 * sx, 0.55, 4.25), 'f1_' + s: (1.9 * sx, 0.75, 5.0), 'f2_' + s: (2.0 * sx, 1.05, 3.6), 'f3_' + s: (1.45 * sx, 1.2, 2.5)})
    D.MEMBRANE_THICK = 0.065                   # a stone wing is a slab, and it must survive the voxel fusion
    parts = D.build_hi(c)
    for o in parts:
        o.data.materials.clear(); o.matrix_world = Matrix.Translation((0, 0.02, ORB_Z + ORB - 0.035)) @ Matrix.Scale(SC, 4); L.apply_xf(o)
    orb = L.icosphere('orb', ORB, 6, c); Pq = L.co(orb); Pq[:, 2] += ORB_Z; L.set_co(orb, Pq)
    plinth = L.sweep('plinth', [(0, 0, 0.0, 0.50, 0.50, 7), (0, 0, 0.03, 0.52, 0.52, 7), (0, 0, 0.12, 0.50, 0.50, 7), (0, 0, 0.16, 0.42, 0.42, 5), (0, 0, 0.22, 0.34, 0.34, 3)], nu=64, nv=24, c=c, up=(0, 1, 0), cap=0.9)
    body = parts[0]; rest = parts[1:]
    # carve it as one stone: fuse everything by a voxel remesh, then chisel marks and weathering by displacement
    allp = [body, orb, plinth] + rest; st = L.join(allp, 'statue')
    for a in list(st.data.attributes):
        if a.name in ('scute', 'crystal'):
            st.data.attributes.remove(a)
    L.mod(st, 'REMESH', mode='VOXEL', voxel_size=0.0075, adaptivity=0.0, use_smooth_shade=True); L.apply_mods(st); L.mod(st, 'SMOOTH', factor=0.5, iterations=3); L.apply_mods(st)
    L.displace_np(st, lambda Q: 0.002 * fbm(Q, 3, 11, 3) - 0.003 * (1 - np.abs(fbm(Q, 5, 18, 3))) ** 4 + 0.001 * fbm(Q, 7, 60, 2))
    st.data.materials.append(P.rock_mat('stone', 'rock_face_03', tint=(0.80, 0.82, 0.86), value=0.85, sat=0.35, moss=0.55, lichen=0.5, dirt_z=0.2, scale=2.2, seed=9.0))
    return [st]


WEAK = ('The dragon is the creature source shrunk and fused, so it has the same invented anatomy, softened by the voxel fusion: claws, horns, teeth and wing fingers are blunt nubs, as on a worn carving, but nothing reads as tool-cut. '
        'Wing membranes are flat 27 mm slabs. The tail wraps the orb without touching it everywhere. Stone is one tinted rock scan with procedural moss and lichen; no bedding, chips or repairs. '
        'The original is a dark blue-grey statue lit from the side; this one is paler grey.')


def main(mode):
    L.reset(); asset = 'SM_Dragon_Statue_PR'; outdir = os.path.join(L.UNC, 'dragon_statue', 'Dragon_Statue'); hi = build_hi(L.coll('Source_Hi'))
    R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=38, el=10, fill=1.0, lens=60, spp=192, res=(1000, 1200))
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, -0.3, 2.3), radius=0.55, az=42, el=4, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
    if mode == 'review':
        shots(hi, 'Dragon_Statue_hi', L.REVIEW); return
    lo = L.make_lo(hi, 9000, asset, L.coll(asset), angle=72, margin=0.004); ids = L.origin_ids(['dragon_statue'])
    L.finish_static(asset, 'prop', lo, hi, outdir, 2048, families=['dragon_statue', '159 struct/stone/mdink/monum- frames 5, 6'], origin=ids,
                    dresses='stone statue of a dragon rearing on an orb, 3 m to the wing tips on a 1 m plinth: wings half raised, tail wound down round the orb, grey weathered stone with moss and lichen',
                    extrude=0.012, maxdist=0.03, third_party=['rock_face_03'], script=SCRIPT + ' final', weaknesses=WEAK, extra={'contact_crop': 0.95,
                    'triangle_note': '9,000 triangles: above the 6,000 soft target of class prop (hard cap 20,000), spent on the wings and the wound tail'})
    for o in hi:
        o.hide_render = True
    shots([lo], 'render', outdir); L.save_blend()


if __name__ == '__main__':
    a = L.args(); main(a[0] if a else 'review')
