"""Offline check of the hair motion weight (HAIR_MOTION_HLSL in Scripts/import_photoreal_art.py) on the three meshes:
which hair vertices move and how much, and a render of a tip offset (side view, front view).
Usage: python3 -I hair_check.py <Characters dir> <out_dir>"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fbxread
from PIL import Image, ImageDraw

root, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)


def weight(uv, seam=.2):
    u, v = uv[:, 0], 1.0 - uv[:, 1]           # engine v runs down the atlas
    w = np.zeros(len(u))
    lock = (u >= .5) & (v <= .7505)
    edge = np.abs(v - .375) <= .0008
    row = (v >= .375).astype(float)
    t = np.clip((v - row * .375) / .375, 0, 1); t = np.where(edge, seam, t)
    tile = row * 16 + np.clip(np.floor((u - .5) * 32), 0, 15)
    kind = np.where(tile < 8.5, .3, np.where(tile < 18.5, .55, np.where(tile < 25.5, .8, 1.0)))
    return np.where(lock, kind * t ** 1.5, 0.0)


report = {}
panels = []
for ch in ('Dink', 'Mother', 'Milder'):
    r = fbxread.read(os.path.join(root, ch, 'Export', f'SK_{ch}_Photoreal_LOD0.fbx'))
    obj = r.find('Objects'); con = r.find('Connections'); g = obj.find('Geometry')
    V = g.find('Vertices').props[0].reshape(-1, 3)
    PVI = g.find('PolygonVertexIndex').props[0]
    pm = g.find('LayerElementMaterial').find('Materials').props[0]
    L = g.find('LayerElementUV'); UV = L.find('UV').props[0].reshape(-1, 2); UVI = L.find('UVIndex').props[0]
    name_of = {n.props[0]: n.props[1].split('\x00')[0] for n in obj.kids if n.name in ('Model', 'Material')}
    mesh_model = [n.props[0] for n in obj.all('Model') if n.props[2] == 'Mesh'][0]
    mats = [name_of[c.props[1]] for c in con.kids if c.props[0] == 'OO' and c.props[2] == mesh_model and name_of.get(c.props[1], '').startswith('MI_')]
    hair = mats.index(f'MI_{ch}_PR_Hair')
    # per polygon-vertex: vertex index and uv
    poly = np.cumsum(np.r_[0, (PVI[:-1] < 0).astype(int)])
    vid = np.where(PVI < 0, -PVI - 1, PVI)
    sel = pm[poly] == hair
    vv = vid[sel]; uv = UV[UVI[sel]]
    w = weight(uv)
    # per vertex: max weight over its corners (a seam vertex with two uvs takes the larger)
    if ch == 'Mother':
        d = np.linalg.norm(V[vv] - np.array([-0.13, 9.99, 165.72]), axis=1)
        tt = np.clip((d - 5.5) / 4.0, 0, 1); w = w * tt * tt * (3 - 2 * tt)
    W = np.zeros(len(V)); np.maximum.at(W, vv, w)
    hv = np.unique(vv)
    disagree = 0
    corner_w = {}
    for a, b in zip(vv, w):
        corner_w.setdefault(a, []).append(b)
    split = [k for k, l in corner_w.items() if max(l) - min(l) > .05]
    report[ch] = {'hair_vertices': int(len(hv)), 'moving (w>0.05)': int((W[hv] > .05).sum()), 'w>=0.5': int((W[hv] >= .5).sum()),
                  'max w': round(float(W[hv].max()), 3), 'vertices whose corners disagree (uv seams)': len(split),
                  'static cap/brow/wide-tile vertices': int((W[hv] == 0).sum())}
    # render: hair vertices coloured by weight, side and front, plus the displaced position for a 1.5 cm tip offset backward
    P = V[hv]; ww = W[hv]
    c = P.mean(0)
    img = Image.new('RGB', (520, 280), (250, 250, 250)); dr = ImageDraw.Draw(img)
    S = 9.0
    for k, (ax, label) in enumerate(((1, 'side (y)'), (0, 'front (x)'))):
        ox = 130 + k * 260; oy = 140
        for p_, q in zip(P, ww):
            x = ox + (p_[ax] - c[ax]) * S; y = oy - (p_[2] - c[2]) * S
            col = (int(255 * q), 60, int(255 * (1 - q)))
            dr.point((x, y), fill=col)
        dr.text((ox - 120, 4), f'{ch} {label}: red moves, blue static', fill=(0, 0, 0))
    img.save(os.path.join(out, f'hair_weight_{ch}.png'))
    panels.append(img)
sheet = Image.new('RGB', (520, 280 * 3), (255, 255, 255))
for i, p in enumerate(panels): sheet.paste(p, (0, 280 * i))
sheet.save(os.path.join(out, 'hair_weight_sheet.png'))
json.dump(report, open(os.path.join(out, 'hair_weight.json'), 'w'), indent=1)
print(json.dumps(report, indent=1))
