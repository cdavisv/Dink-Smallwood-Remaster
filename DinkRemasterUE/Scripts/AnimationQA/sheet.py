"""Tile capture frames into a small JPEG contact sheet.
  python3 -I Scripts/AnimationQA/sheet.py <out.jpg> <crop x0,y0,x1,y1> <tile height> <frame dir> [<frame dir> ...]
Each directory becomes one row (its NN.png in order), labelled with its name."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
out, crop, th = sys.argv[1], tuple(int(v) for v in sys.argv[2].split(',')), int(sys.argv[3])
rows = []
for d in sys.argv[4:]:
    fs = sorted(Path(d).glob('*.png'))
    tiles = []
    for f in fs:
        im = Image.open(f).convert('RGB').crop(crop)
        tiles.append(im.resize((int(im.width * th / im.height), th)))
    if tiles: rows.append((Path(d).name, tiles))
W = max(sum(t.width for t in ts) for _, ts in rows) + 4
H = len(rows) * (th + 16)
sheet = Image.new('RGB', (W, H), (20, 20, 20))
dr = ImageDraw.Draw(sheet)
y = 0
for name, ts in rows:
    dr.text((4, y + 2), name, fill=(255, 255, 0))
    x = 2
    for t in ts:
        sheet.paste(t, (x, y + 14)); x += t.width
    y += th + 16
sheet.save(out, quality=82)
print(out, sheet.size)
