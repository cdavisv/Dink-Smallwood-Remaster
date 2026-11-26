"""The gnome's outfit maps: the Unclaimed source's maps with the dead texels of the hat filled from the cloth round them.

In the source's bake the occlusion of the hat is zero and its normals are broken in places: a black blot on the back of
the cone and black patches along the brim (seen in Blender and, on the first-pass figure, in the game). Two steps (run_townsfolk.sh Gnome outfit runs the second; the first needs the packed clothes):

    blender -b -t 4 <Characters>/NPC/Gnome/Work/gnome_packed.blend --python gnome_outfit.py      the hat's UV faces -> NPC/Gnome/cfg/mantle_uv.json
    python3 -I gnome_outfit.py                                                                   NPC/Gnome/Textures/T_Gnome_PR_Outfit_{BC,ORM,N}.png

The hat is every connected piece of the clothes above the brow (z over 1.68 m on the rig). Inside its faces a texel without
light in the occlusion map, with a normal that points into the cloth, or near black in the colour map takes the value of the
nearest sound texel of the hat (the stars stay where they are)."""
import json, sys
from pathlib import Path
CHARS = Path(__file__).resolve().parent.parent; HERE = CHARS / 'NPC/Gnome'
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
            if z.min() > 1.68: out += [[[round(c, 5) for c in uv[l].uv] for l in p.loop_indices] for p in ps]
    (HERE / 'cfg/mantle_uv.json').write_text(json.dumps(out)); print('[PR] gnome_outfit: hat faces', len(out)); sys.exit(0)

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
SRC = CHARS.parent / 'Unclaimed/npc_gnome_purple/Gnome_Wizard'
S = 2048; mask = Image.new('L', (S, S), 0); d = ImageDraw.Draw(mask)
for poly in json.loads((HERE / 'cfg/mantle_uv.json').read_text()): d.polygon([(u * S, (1 - v) * S) for u, v in poly], fill=255, outline=255)
m = np.asarray(mask.filter(ImageFilter.MaxFilter(9)), np.float32) / 255.0 > 0.5      # four texels over the seams


def fill(a, bad):
    """nearest good texel of the hat: grow the good area into the bad one ring at a time"""
    out = a.copy(); known = m & ~bad; todo = bad.copy(); rounds = 0
    while todo.any() and rounds < 600:
        acc = np.zeros_like(out); cnt = np.zeros(known.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            k = np.roll(known, (dy, dx), (0, 1)); acc += np.roll(out, (dy, dx), (0, 1)) * k[..., None]; cnt += k
        new = todo & (cnt > 0); out[new] = acc[new] / cnt[new][:, None]; known |= new; todo &= ~new; rounds += 1
    return out


(HERE / 'Textures').mkdir(parents=True, exist_ok=True)
for role in ('BC', 'ORM', 'N'):
    a = np.asarray(Image.open(SRC / f'T_Gnome_Wizard_PR_Outfit_{role}.png').convert('RGB').resize((S, S), Image.LANCZOS), np.float32) / 255.0
    if role == 'BC': lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32); bad = m & (lum < float(np.median(lum[m])) * 0.10)
    elif role == 'ORM': bad = m & (a[..., 0] < 0.30)      # occlusion: the bake found no light there
    else: bad = m & ((a[..., 2] < 0.55) | (np.abs(a[..., :2] - 0.5).max(axis=-1) > 0.42))      # normals that point into the cloth or lie flat in it
    bad = np.asarray(Image.fromarray((bad * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)), np.uint8) > 127      # and the soft edge round each blot
    bad &= m
    out = fill(a, bad)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(HERE / f'Textures/T_Gnome_PR_Outfit_{role}.png', optimize=True)
    print('townsfolk gnome_outfit', f'T_Gnome_PR_Outfit_{role}.png', 'hat texels', int(m.sum()), 'filled', int(bad.sum()))
