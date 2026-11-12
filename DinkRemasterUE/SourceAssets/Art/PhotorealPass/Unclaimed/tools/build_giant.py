"""stone_giant (821-829 foes/stonegnt/walk, 816 attack): a knuckle-walking giant of bedded sandstone.

    tools/bl.sh build_giant.py [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_props as P
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_giant.py'
J = {'pelvis': (0, 0.38, 0.95), 'spine': (0, 0.12, 1.30), 'chest': (0, -0.20, 1.62), 'neck': (0, -0.42, 1.80), 'head': (0, -0.58, 1.84), 'brow': (0, -0.71, 1.92), 'jaw': (0, -0.70, 1.72)}
R = {'pelvis': (0.31, 0.28, 0.29), 'spine': (0.41, 0.36, 0.38), 'chest': (0.54, 0.42, 0.46), 'neck': 0.21, 'head': (0.19, 0.21, 0.20), 'brow': (0.18, 0.08, 0.055), 'jaw': (0.15, 0.12, 0.09)}
E = [('pelvis', 'spine'), ('spine', 'chest'), ('chest', 'neck'), ('neck', 'head'), ('head', 'brow'), ('head', 'jaw')]
for s, sx in (('l', 1), ('r', -1)):
    J.update({'shoulder_' + s: (0.60 * sx, -0.22, 1.68), 'elbow_' + s: (0.84 * sx, -0.50, 1.06), 'wrist_' + s: (0.74 * sx, -0.82, 0.44), 'fist_' + s: (0.72 * sx, -0.96, 0.19),
              'k1_' + s: (0.60 * sx, -1.08, 0.10), 'k2_' + s: (0.72 * sx, -1.12, 0.10), 'k3_' + s: (0.84 * sx, -1.08, 0.10), 'thumb_' + s: (0.55 * sx, -0.92, 0.2),
              'hip_' + s: (0.30 * sx, 0.36, 0.86), 'knee_' + s: (0.44 * sx, 0.10, 0.50), 'ankle_' + s: (0.43 * sx, 0.30, 0.15), 'foot_' + s: (0.45 * sx, 0.04, 0.09), 'toe_' + s: (0.46 * sx, -0.14, 0.07)})
    R.update({'shoulder_' + s: (0.31, 0.3, 0.3), 'elbow_' + s: 0.215, 'wrist_' + s: 0.19, 'fist_' + s: (0.21, 0.2, 0.17), 'k1_' + s: 0.075, 'k2_' + s: 0.08, 'k3_' + s: 0.075, 'thumb_' + s: 0.07,
              'hip_' + s: (0.27, 0.28, 0.3), 'knee_' + s: 0.2, 'ankle_' + s: 0.15, 'foot_' + s: (0.17, 0.2, 0.09), 'toe_' + s: (0.16, 0.1, 0.07)})
    E += [('chest', 'shoulder_' + s), ('shoulder_' + s, 'elbow_' + s), ('elbow_' + s, 'wrist_' + s), ('wrist_' + s, 'fist_' + s), ('fist_' + s, 'k1_' + s), ('fist_' + s, 'k2_' + s), ('fist_' + s, 'k3_' + s), ('fist_' + s, 'thumb_' + s),
          ('pelvis', 'hip_' + s), ('hip_' + s, 'knee_' + s), ('knee_' + s, 'ankle_' + s), ('ankle_' + s, 'foot_' + s), ('foot_' + s, 'toe_' + s)]
BONES = [('root', (0, 0, 0), (0, 0.12, 0), None), ('pelvis', 'pelvis', 'spine', 'root'), ('spine_01', 'spine', 'chest', 'pelvis'), ('spine_02', 'chest', 'neck', 'spine_01'), ('neck_01', 'neck', 'head', 'spine_02'), ('head', 'head', 'brow', 'neck_01')]
for s in 'lr':
    BONES += [('upperarm_' + s, 'shoulder_' + s, 'elbow_' + s, 'spine_02'), ('lowerarm_' + s, 'elbow_' + s, 'wrist_' + s, 'upperarm_' + s), ('hand_' + s, 'wrist_' + s, 'k2_' + s, 'lowerarm_' + s),
              ('thigh_' + s, 'hip_' + s, 'knee_' + s, 'pelvis'), ('calf_' + s, 'knee_' + s, 'ankle_' + s, 'thigh_' + s), ('foot_' + s, 'ankle_' + s, 'toe_' + s, 'calf_' + s)]


def build_hi(c):
    body = C.graph_body('body', J, E, R, c, voxel=0.014, smooth=6); L.subsurf(body, 1)
    Pq = L.co(body); N = L.vnormals(body); x, y, z = Pq[:, 0], Pq[:, 1], Pq[:, 2]
    # bedded rock: stepped strata tilted across the body, blocky jointing, chips; deep-set eye pits under the brow
    w = fbm(Pq, 3, 1.4, 3); w2 = fbm(Pq, 21, 0.7, 2); s_ = z + 0.35 * y + 0.18 * x + 0.16 * w; band = (s_ / (0.11 + 0.05 * w2)) % 1.0; thick = 0.5 + 0.5 * fbm(Pq, 23, 2.5, 2)
    step = smoothstep(0.0, 0.2, band) * (1 - smoothstep(0.8, 1.0, band)) * (0.35 + 0.65 * smoothstep(-0.3, 0.3, fbm(Pq, 25, 1.8, 2)))
    joint = np.minimum(np.abs(((x + 0.3 * w) / 0.31) % 1.0 - 0.5), np.abs(((y + 0.2 * w) / 0.37) % 1.0 - 0.5)); cr = smoothstep(0.035, 0.0, joint)
    chips = -0.012 * smoothstep(0.25, 0.6, fbm(Pq, 7, 7, 3)); lump = 0.012 * fbm(Pq, 11, 3.5, 3)
    eye = np.exp(-(((np.abs(x) - 0.085) / 0.035) ** 2 + ((z - 1.855) / 0.022) ** 2)) * smoothstep(-0.6, -0.7, y)
    mouth = np.exp(-((z - (1.735 - 0.5 * x * x)) / 0.012) ** 2) * smoothstep(-0.66, -0.74, y) * (1 - smoothstep(0.1, 0.13, np.abs(x)))
    L.set_co(body, Pq + N * ((step - 0.5) * 0.024 * (0.6 + 0.8 * thick) - cr * 0.02 + chips * 1.5 + lump - eye * 0.05 - mouth * 0.022)[:, None])
    body.data.materials.append(P.rock_mat('stone', 'rock_boulder_dry', tint=(0.95, 0.78, 0.56), value=0.95, sat=0.8, moss=0.25, lichen=0.3, dirt_z=0.25, scale=1.3, seed=12.0))
    return [body]


WEAK = ('NOT photoreal at 1 m: a blob figure with a rock texture. The body is a fused joint graph with strata, jointing and chips from displacement; it does not break into separate blocks at the joints, so it reads as a stone-skinned ape rather than as stacked rock. '
        'Eyes and mouth are displaced pits only. The game mesh is a decimation (no joint loops) and stone should not stretch: skinned deformation will smear the bedding at the shoulders and hips; rigid chunks per bone would be the right build. '
        'Inverse-distance or bone-heat automatic weights, one test pose. No animation clips, no Physics Asset.')


def main(mode):
    L.reset(); asset = 'SK_Stone_Giant_PR'; outdir = os.path.join(L.UNC, 'stone_giant', 'Stone_Giant'); hi = build_hi(L.coll('Source_Hi'))
    R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=36, el=12, fill=1.25, lens=60, spp=192)
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, -0.6, 1.75), radius=0.6, az=30, el=6, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
    if mode == 'review':
        shots(hi, 'Stone_Giant_hi', L.REVIEW); return
    lo = L.make_lo(hi, 14000, asset, L.coll(asset), angle=72, margin=0.004); arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset)); ids = L.origin_ids(['stone_giant'])
    C.finish_creature(asset, 'creature', lo, hi, arm, outdir, 2048, families=['stone_giant', '821-829 foes/stonegnt/walk', '816 foes/stonegnt/attack'], origin=ids,
                      dresses='stone giant: a knuckle-walking, ape-built giant of bedded tan sandstone, 2.1 m at the shoulder and 1.9 m across, with massive forearms, a small head sunk between the shoulders and deep-set eye pits',
                      weaknesses=WEAK, script=SCRIPT + ' final', extrude=0.015, maxdist=0.04, third_party=['rock_boulder_dry'], extra={'contact_crop': 0.9})
    shots([lo], 'render', outdir)
    C.pose(arm, {'upperarm_l': (-35, 0, 0), 'lowerarm_l': (-20, 0, 0), 'thigh_r': (-20, 0, 0), 'calf_r': (15, 0, 0), 'head': (0, 0, 20), 'spine_02': (0, 0, 8)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=36, el=12, fill=1.25, lens=60, res=(1000, 750), spp=128); C.pose(arm, {}); L.save_blend()


if __name__ == '__main__':
    a = L.args(); main(a[0] if a else 'review')
