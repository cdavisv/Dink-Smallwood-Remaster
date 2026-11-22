"""Tile the frames of one secondary-motion capture (Saved/SecondaryMotion/frames/<name>/) into a JPEG sheet.

  python3 -I Scripts/AnimationQA/secondary_strip.py <name> [x0,y0,x1,y1 crop] [columns] [out.jpg]

Pairs (NN_off.png / NN_on.png) become two rows: switched off above, on below, same instant."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

project = Path(__file__).resolve().parents[2]
name = sys.argv[1]
crop = tuple(int(v) for v in sys.argv[2].split(',')) if len(sys.argv) > 2 and sys.argv[2] != '-' else None
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 0
dest = Path(sys.argv[4]) if len(sys.argv) > 4 else project / 'Saved/SecondaryMotion' / (name + '.jpg')
src = project / 'Saved/SecondaryMotion/frames' / name
files = sorted(src.glob('*.png'))
if not files:
    sys.exit('no frames in %s' % src)
pairs = any(f.stem.endswith('_off') for f in files)
rows = [[f for f in files if f.stem.endswith('_off')], [f for f in files if f.stem.endswith('_on')]] if pairs else [files]
if not pairs and cols:
    rows = [files[i:i + cols] for i in range(0, len(files), cols)]
tiles = [[Image.open(f).convert('RGB') for f in r] for r in rows]
if crop:
    tiles = [[t.crop(crop) for t in r] for r in tiles]
w, h = tiles[0][0].size
scale = min(1.0, 360.0 / w)
tw, th = int(w * scale), int(h * scale)
sheet = Image.new('RGB', (tw * max(len(r) for r in tiles), th * len(tiles) + 18), (255, 255, 255))
draw = ImageDraw.Draw(sheet)
for y, r in enumerate(tiles):
    for x, t in enumerate(r):
        sheet.paste(t.resize((tw, th)), (x * tw, y * th))
        draw.text((x * tw + 4, y * th + 4), rows[y][x].stem, fill=(255, 255, 0))
draw.text((4, th * len(tiles) + 3), '%s: %s' % (name, 'top switched off, bottom on (same instant)' if pairs else 'in time order, left to right'), fill=(0, 0, 0))
dest.parent.mkdir(parents=True, exist_ok=True)
sheet.save(dest, quality=88)
print('wrote', dest, sheet.size)
