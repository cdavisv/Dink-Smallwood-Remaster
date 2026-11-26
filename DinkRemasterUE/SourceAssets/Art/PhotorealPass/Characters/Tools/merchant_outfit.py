"""The merchant's outfit colour map: the Unclaimed source's map with the mantle and its collar painted as brown fur.

The 1997 pictures 341-399 (people/merchant) show a pelt on the shoulders of the coat; the source's mantle is plain grey
cloth. Two steps (run_townsfolk.sh Merchant outfit runs the second; the first needs the packed clothes):

    blender -b -t 4 <Characters>/NPC/Merchant/Work/merchant_packed.blend --python merchant_outfit.py      the mantle's UV faces -> NPC/Merchant/cfg/mantle_uv.json
    python3 -I merchant_outfit.py                                                                         NPC/Merchant/Textures/T_Merchant_PR_Outfit_BC.png

The mantle is every connected piece of the clothes that lies between the collar bone and the chin (z 1.28 to 1.60 m on
the rig). The fur is paint: a mottled brown with short strokes of darker and tawny hair over the cloth's own light and
dark. The normal and roughness maps stay the cloth's."""
import json, sys
from pathlib import Path
CHARS = Path(__file__).resolve().parent.parent; HERE = CHARS / 'NPC/Merchant'
try:
    import bpy
except ImportError:
    bpy = None
if bpy is not None:
    import numpy as np
    out = []
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        me = o.data; n = len(me.vertices); parent = list(range(n))
        def find(i):
            while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
            return i
        for e in me.edges:
            a, b = find(e.vertices[0]), find(e.vertices[1])
            if a != b: parent[a] = b
        co = np.array([v.co[:] for v in me.vertices]); uv = me.uv_layers.active.data; comps = {}
        for p in me.polygons: comps.setdefault(find(p.vertices[0]), []).append(p)
        for ps in comps.values():
            z = co[sorted({v for p in ps for v in p.vertices})][:, 2]
            if z.min() > 1.28 and z.max() < 1.60: out += [[[round(c, 5) for c in uv[l].uv] for l in p.loop_indices] for p in ps]
    (HERE / 'cfg/mantle_uv.json').write_text(json.dumps(out)); print('[PR] merchant_outfit: mantle faces', len(out)); sys.exit(0)

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
SRC = CHARS.parent / 'Unclaimed/npc_merchant_blue/Merchant/T_Merchant_PR_Outfit_BC.png'; DST = HERE / 'Textures/T_Merchant_PR_Outfit_BC.png'
a = np.asarray(Image.open(SRC).convert('RGB'), np.float32) / 255.0; S = a.shape[0]
mask = Image.new('L', (S, S), 0); d = ImageDraw.Draw(mask)
for poly in json.loads((HERE / 'cfg/mantle_uv.json').read_text()): d.polygon([(u * S, (1 - v) * S) for u, v in poly], fill=255, outline=255)
m = np.asarray(mask.filter(ImageFilter.MaxFilter(5)), np.float32)[..., None] / 255.0      # two texels over the seams
rng = np.random.default_rng(371)
lum = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32)); mean = float(lum[m[..., 0] > 0.5].mean()); shade = np.clip(lum / max(mean, 1e-3), 0.55, 1.3)[..., None]
# mottled pelt: soft patches, then short strokes of single hairs in three tones
patch = np.asarray(Image.fromarray((rng.random((S // 24, S // 24)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC), np.float32)[..., None] / 255.0
fur = np.array([0.205, 0.120, 0.060], np.float32) * (0.70 + 0.60 * patch)
strokes = Image.fromarray((np.clip(fur, 0, 1) * 255).astype(np.uint8)); ds = ImageDraw.Draw(strokes)
ys, xs = np.nonzero(m[..., 0] > 0.5)
for tone, count, length in (((0.085, 0.046, 0.022), 0.060, 5), ((0.30, 0.185, 0.10), 0.050, 5), ((0.40, 0.28, 0.16), 0.010, 4)):
    pick = rng.integers(0, len(xs), int(len(xs) * count)); ang = rng.normal(np.pi / 2, 0.55, len(pick)); ln = length * (0.6 + 0.8 * rng.random(len(pick)))
    col = tuple(int(c * 255) for c in tone)
    for x, y, t, l in zip(xs[pick], ys[pick], ang, ln): ds.line([(x, y), (x + np.cos(t) * l, y + np.sin(t) * l)], fill=col, width=1)
fur = np.asarray(strokes.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255.0 * shade
out = a * (1 - m) + fur * m
DST.parent.mkdir(parents=True, exist_ok=True); Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(DST, optimize=True)
print('townsfolk merchant_outfit', DST.name, 'mantle texels', int((m[..., 0] > 0.5).sum()))
