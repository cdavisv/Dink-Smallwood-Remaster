"""Offline check of the skirt bell (Scripts/import_photoreal_art.py SKIRT_MOTION_HLSL) on a character's LOD0 (Mother, Milder).

Poses the legs (walk contact, hurry stride, a turn-in-place half step), skins with linear blend skinning as the engine does,
and compares the skinned skirt with the bell: hem edge stretch and leg/shoe vertices that come through the skirt.
Usage: python3 -I skirt_check.py <SK_<Name>_Photoreal_LOD0.fbx> <out_dir>
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fbxread

fbx, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
r = fbxread.read(fbx)
obj = r.find('Objects')
con = r.find('Connections')
name_of = {}
for n in obj.kids:
    if n.name in ('Model', 'Deformer', 'Material', 'Geometry'):
        name_of[n.props[0]] = n.props[1].split('\x00')[0]
geo = obj.find('Geometry')
V = geo.find('Vertices').props[0].reshape(-1, 3).astype(np.float64)
PVI = geo.find('PolygonVertexIndex').props[0]
mats_poly = geo.find('LayerElementMaterial').find('Materials').props[0]
# material order = order of Material -> mesh model connections
mesh_model = [n.props[0] for n in obj.all('Model') if n.props[2] == 'Mesh'][0]
mat_ids = [c.props[1] for c in con.kids if c.props[0] == 'OO' and c.props[2] == mesh_model and name_of.get(c.props[1], '').startswith('MI_')]
mat_names = [name_of[m] for m in mat_ids]
polys = []; cur = []
for i in PVI:
    if i < 0: cur.append(-i - 1); polys.append(cur); cur = []
    else: cur.append(int(i))
assert len(polys) == len(mats_poly)
# bones and clusters
clusters = {}
bone_of_cluster = {}
for c in con.kids:
    if c.props[0] == 'OO' and name_of.get(c.props[1]) is not None:
        pass
cl_nodes = {n.props[0]: n for n in obj.all('Deformer') if n.props[2] == 'Cluster'}
for c in con.kids:
    if c.props[0] == 'OO' and c.props[2] in cl_nodes:
        bone_of_cluster[c.props[2]] = name_of.get(c.props[1])
nv = len(V)
W = {}
bind = {}
for cid, n in cl_nodes.items():
    b = bone_of_cluster.get(cid)
    tl = n.find('TransformLink').props[0].reshape(4, 4).T  # column-major in file
    bind[b] = tl
    ix = n.find('Indexes'); wt = n.find('Weights')
    if ix is not None:
        W[b] = (ix.props[0].astype(int), wt.props[0].astype(np.float64))
parent = {}
model_name = {n.props[0]: n.props[1].split('\x00')[0] for n in obj.all('Model')}
for c in con.kids:
    if c.props[0] == 'OO' and c.props[1] in model_name and c.props[2] in model_name:
        parent[model_name[c.props[1]]] = model_name[c.props[2]]
scale = 100.0 if np.ptp(V[:, 2]) < 10 else 1.0  # to cm
V = V * scale
for b in bind: bind[b] = bind[b].copy(); bind[b][:3, 3] *= scale
P = {b: bind[b][:3, 3] for b in bind}
up = np.array([0, 0, 1.0])
fwd = P['ball_l'] - P['foot_l']; fwd[2] = 0; fwd /= np.linalg.norm(fwd)
lat = P['thigh_l'] - P['thigh_r']; lat[2] = 0; lat /= np.linalg.norm(lat)
print('cm scale', scale, 'height', np.ptp(V[:, 2]), 'pelvis z', P['pelvis'][2], 'knee z', P['calf_l'][2], 'ankle z', P['foot_l'][2])
print('materials', mat_names, 'forward', fwd.round(3), 'left', lat.round(3))


def rot(axis, deg):
    a = math.radians(deg); axis = axis / np.linalg.norm(axis); x, y, z = axis; c, s = math.cos(a), math.sin(a); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s], [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


order = []
def visit(b):
    if b in order: return
    if parent.get(b) in bind: visit(parent[b])
    order.append(b)
for b in bind: visit(b)


def pose(rots):
    """rots: bone -> world-axis rotation (3x3) applied at the bone's joint; returns posed global 4x4 per bone."""
    G = {}
    for b in order:
        p = parent.get(b)
        if p in G:
            local = np.linalg.inv(bind[p]) @ bind[b]
            g = G[p] @ local
        else:
            g = bind[b].copy()
        if b in rots:
            R = np.eye(4); R[:3, :3] = rots[b]
            piv = g[:3, 3].copy()
            T1 = np.eye(4); T1[:3, 3] = -piv; T2 = np.eye(4); T2[:3, 3] = piv
            g = T2 @ R @ T1 @ g
        G[b] = g
    return G


def skin(G):
    out = np.zeros_like(V); hom = np.c_[V, np.ones(nv)]
    tot = np.zeros(nv)
    for b, (ix, wt) in W.items():
        M = G[b] @ np.linalg.inv(bind[b])
        out[ix] += (hom[ix] @ M.T)[:, :3] * wt[:, None]; tot[ix] += wt
    return out / np.maximum(tot, 1e-9)[:, None]


# bind frame helper: bind space = FBX space here (pelvis rigid; the tests keep the pelvis still)
def bell(Vskin, G, rk=7.0, ra=6.0, clear=1.5, spread=2.5, top=2.0, full=.55, drape=3.0, NS=4):
    hl, kl, al = G['thigh_l'][:3, 3], G['calf_l'][:3, 3], G['foot_l'][:3, 3]
    hr, kr, ar = G['thigh_r'][:3, 3], G['calf_r'][:3, 3], G['foot_r'][:3, 3]
    hipZ = .5 * (hl[2] + hr[2]); kneeZ = .5 * (kl[2] + kr[2]); ankZ = .5 * (al[2] + ar[2])
    Pz = V[:, 2]
    e0, e1 = hipZ + top, hipZ + (kneeZ - hipZ) * full
    t = np.clip((Pz - e0) / (e1 - e0), 0, 1); w = t * t * (3 - 2 * t)
    A = .5 * (hl[:2] + hr[:2])
    d = V[:, :2] - A; rho = np.linalg.norm(d, axis=1); u = d / np.maximum(rho, 1e-3)[:, None]
    need = np.zeros(nv)
    for h, k, a in ((hl, kl, al), (hr, kr, ar)):
        # the fabric hangs from the leg: every point of the leg at or above this height pushes it out (a curtain)
        for j in range(2 * NS + 1):
            f = j / NS
            Ls = h + (k - h) * f if f <= 1 else k + (a - k) * (f - 1)
            rl = (rk if f <= 1 else rk + (ra - rk) * (f - 1)) + clear
            # below the contact the fabric hangs (curtain); above it, it runs straight up to the waist (a tent line)
            hang = np.where(Pz <= Ls[2], 1.0, np.clip((hipZ - Pz) / max(hipZ - Ls[2], 1.0), 0, 1))
            g = Ls[:2] - A
            along = (g * u).sum(1); across = np.abs(g[0] * u[:, 1] - g[1] * u[:, 0])
            s = np.clip(across / (rl * spread), 0, 1)
            cover = rl * (1 - s * s) ** 2
            need = np.maximum(need, (along + cover) * hang)
    rho2 = .5 * (rho + need + np.sqrt((rho - need) ** 2 + 4.0))
    push = np.maximum(rho2 - rho, 0)
    Pb = np.c_[A + u * rho2[:, None], Pz + push * push / (2 * np.maximum(hipZ - Pz, 10))]
    return Vskin + (Pb - Vskin) * w[:, None], w


CH = [m for m in mat_names if m.endswith('_PR_Outfit')][0][3:-len('_PR_Outfit')]
outfit = mat_names.index('MI_%s_PR_Outfit' % CH)
skin_m = mat_names.index('MI_%s_PR_Skin' % CH); gear = mat_names.index('MI_%s_PR_Gear' % CH)
edges = set()
for p, m in zip(polys, mats_poly):
    if m != outfit: continue
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        edges.add((min(a, b), max(a, b)))
E = np.array(sorted(edges))
knee_z = P['calf_l'][2]
low = (V[E[:, 0], 2] < knee_z) & (V[E[:, 1], 2] < knee_z)
E = E[low]
L0 = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
leg_verts = np.unique(np.concatenate([np.array(p) for p, m in zip(polys, mats_poly) if m in (skin_m, gear)]))
leg_verts = leg_verts[V[leg_verts, 2] < knee_z]
skirt_verts = np.unique(E.ravel())


def poke(X):
    """leg, shoe vertices outside the skirt: radially beyond the skirt surface at their azimuth and height (bins)."""
    A = .5 * (P['thigh_l'][:2] + P['thigh_r'][:2])
    S = X[skirt_verts]; ds = S[:, :2] - A; az = np.arctan2(ds[:, 1], ds[:, 0]); rr = np.linalg.norm(ds, axis=1)
    nb_a, nb_z = 48, 24
    zb = np.clip(((S[:, 2] - S[:, 2].min()) / (knee_z - S[:, 2].min()) * nb_z).astype(int), 0, nb_z - 1)
    ab = ((az + math.pi) / (2 * math.pi) * nb_a).astype(int) % nb_a
    rmax = np.zeros((nb_a, nb_z)); np.maximum.at(rmax, (ab, zb), rr)
    Lg = X[leg_verts]; dl = Lg[:, :2] - A; azl = np.arctan2(dl[:, 1], dl[:, 0]); rl = np.linalg.norm(dl, axis=1)
    zl = ((Lg[:, 2] - S[:, 2].min()) / (knee_z - S[:, 2].min()) * nb_z).astype(int)
    ok = (zl >= 0) & (zl < nb_z)
    al_ = ((azl + math.pi) / (2 * math.pi) * nb_a).astype(int) % nb_a
    lim = rmax[al_[ok], zl[ok]]
    return int(((rl[ok] > lim + .3) & (lim > 0)).sum()), int(ok.sum())


poses = {
    'idle': {},
    'walk_contact': {'thigh_l': rot(lat, -28), 'calf_l': rot(lat, 6), 'thigh_r': rot(lat, 14), 'calf_r': rot(lat, 30)},
    'hurry_stride': {'thigh_l': rot(lat, -38), 'calf_l': rot(lat, 10), 'thigh_r': rot(lat, 22), 'calf_r': rot(lat, 45)},
    'swing_knee_up': {'thigh_l': rot(lat, -45), 'calf_l': rot(lat, 70), 'thigh_r': rot(lat, 5), 'calf_r': rot(lat, 5)},
    'side_step': {'thigh_l': rot(fwd, 18), 'thigh_r': rot(fwd, -6)},
}
# sign check: a negative angle about +left must swing the left knee forward
g_ = pose({'thigh_l': rot(lat, -28)})
if np.dot(g_['calf_l'][:3, 3] - P['calf_l'], fwd) < 0:
    poses = {k: {b: R.T for b, R in v.items()} for k, v in poses.items()}
report = {}
from PIL import Image, ImageDraw
CW, CH, SC = 260, 300, 2.4   # panel size px, px per cm
img = Image.new('RGB', (CW * len(poses), CH * 2 + 20), (250, 250, 250)); dr = ImageDraw.Draw(img)
def colour(x):
    x = min(max((x - 1.0) / .5, -1.0), 1.0)
    return (int(255 * min(1, 1 + x)), int(255 * (1 - abs(x))), int(255 * min(1, 1 - x))) if x >= 0 else (int(255 * (1 + x)), int(255 * (1 + x)), 255)
for col, (name, rots) in enumerate(poses.items()):
    G = pose(rots)
    S0 = skin(G)
    S1, w = bell(S0, G)
    row = {}
    for r_, (tag, X) in enumerate((('skinned', S0), ('bell', S1))):
        L = np.linalg.norm(X[E[:, 0]] - X[E[:, 1]], axis=1); ratio = L / np.maximum(L0, 1e-6)
        n_out, n_leg = poke(X)
        row[tag] = {'hem_stretch_max': round(float(ratio.max()), 3), 'hem_stretch_p99': round(float(np.percentile(ratio, 99)), 3),
                    'edges_over_1.25': int((ratio > 1.25).sum()), 'edges_under_0.8': int((ratio < .8).sum()), 'leg_verts_outside': n_out, 'leg_verts': n_leg}
        ox, oy = col * CW + CW // 2, r_ * CH + CH - 10
        to = lambda p: (ox + float(p @ fwd) * SC, oy - float(p[2]) * SC)
        for v in X[leg_verts][::3]:
            x, y = to(v); dr.point((x, y), fill=(150, 150, 150))
        for (a, b), q in zip(E, ratio):
            dr.line([to(X[a]), to(X[b])], fill=colour(q), width=1)
        dr.text((col * CW + 4, r_ * CH + 4), f"{name} {tag}", fill=(0, 0, 0))
        dr.text((col * CW + 4, r_ * CH + 16), f"max {row[tag]['hem_stretch_max']} >1.25: {row[tag]['edges_over_1.25']}  legs out {n_out}", fill=(0, 0, 0))
    report[name] = row
dr.text((4, CH * 2 + 4), 'side view, forward to the right; edge colour = length / bind (blue shorter, red 1.5x); grey = legs and shoes below the knee', fill=(0, 0, 0))
img.save(os.path.join(out, 'skirt_bell_offline.png'))
json.dump(report, open(os.path.join(out, 'skirt_bell_offline.json'), 'w'), indent=1)
print(json.dumps(report, indent=1))
