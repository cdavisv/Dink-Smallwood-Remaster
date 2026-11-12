#!/usr/bin/env python3
"""Per-screen ground colour grid for the presentation layer (python3 -I Scripts/export_ground_colour.py).

Reads ImportData/screens.json (each screen's terrain layers and ground_mask PNG: R/G/B = weight of layer 1/2/3)
and the mean base colour of every terrain set (SourceAssets/Art/PhotorealPass/Terrain/<set>/T_Terrain_<set>_BC.png),
and writes Content/Dink/Data/Environment/ground_colour.json: a W x H grid of sRGB bytes per screen (base64).
UDinkEnvironmentSubsystem::GroundColourAt reads it so tree trunks can blend their foot toward the soil under
them (family art, visual only). Re-run after Scripts/import_greybox.sh --export or a terrain texture change."""
import base64, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent.parent
W, H = 12, 8
screens = json.loads((HERE / 'ImportData/screens.json').read_text())['screens']
cat = json.loads((HERE / 'SourceAssets/Art/PhotorealPass/Environment/terrain_layers.json').read_text())
means = {}
def mean_of(layer):
    if layer not in means:
        set_name = (cat['layers'].get(layer) or {}).get('set', layer)
        path = HERE / f'SourceAssets/Art/PhotorealPass/Terrain/{set_name}/T_Terrain_{set_name}_BC.png'
        if not path.exists():
            means[layer] = None
        else:
            a = np.asarray(Image.open(path).convert('RGB').resize((64, 64), Image.BOX), dtype=np.float64) / 255.0
            lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).reshape(-1, 3).mean(0)
            means[layer] = lin
    return means[layer]
out = {}
for s in screens:
    layers = s.get('ground_layers'); mask = s.get('ground_mask')
    if not layers or not mask or not (HERE / 'ImportData' / mask).exists():
        continue
    cols = [mean_of(l['name']) for l in layers]
    if any(c is None for c in cols):
        continue
    m = np.asarray(Image.open(HERE / 'ImportData' / mask).convert('RGBA').resize((W, H), Image.BOX), dtype=np.float64)[:, :, :3] / 255.0
    lin = sum(m[:, :, i:i + 1] * cols[i] for i in range(len(cols))) / np.maximum(m[:, :, :len(cols)].sum(axis=2, keepdims=True), 1e-6)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.maximum(lin, 0), 1 / 2.4) - 0.055)
    out[str(s['screen'])] = base64.b64encode((np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()).decode('ascii')
dest = HERE / 'Content/Dink/Data/Environment/ground_colour.json'
text = json.dumps({'schema': 'dink-environment-ground-colour/1', 'w': W, 'h': H, 'encoding': 'sRGB bytes, rows north to south', 'screens': out}, sort_keys=True)
if not dest.exists() or dest.read_text() != text:
    dest.write_text(text)
print(f'{dest}: {len(out)} screens, {W}x{H}; layer means (linear): ' + ', '.join(f'{k} {np.round(v, 3).tolist()}' for k, v in sorted(means.items()) if v is not None)[:600])
