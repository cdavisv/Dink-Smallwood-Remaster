"""Tile engine capture frames (Saved/AnimationPass/frames/<name>*/NN.png) into one strip."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
project = Path(__file__).resolve().parents[2]
name = sys.argv[1]
crop = tuple(int(v) for v in sys.argv[2].split(',')) if len(sys.argv) > 2 else None
files = []
for folder in sorted((project / 'Saved/AnimationPass/frames').glob(name + '*')):
    files += sorted(folder.glob('*.png'))
tiles = []
for f in files:
    im = Image.open(f).convert('RGB')
    if crop:
        im = im.crop(crop)
    im.thumbnail((int(sys.argv[3]) if len(sys.argv) > 3 else 240, 400))
    tiles.append((im, f.parent.name[len(name):] + f.stem))
per_row = 8
w, h = tiles[0][0].size
rows = (len(tiles) + per_row - 1) // per_row
sheet = Image.new('RGB', (w * per_row, h * rows), (20, 20, 24))
draw = ImageDraw.Draw(sheet)
for i, (im, label) in enumerate(tiles):
    x, y = (i % per_row) * w, (i // per_row) * h
    sheet.paste(im, (x, y))
    draw.text((x + 4, y + 3), label, fill=(255, 255, 0))
target = project / 'Saved/AnimationPass' / (name + '_engine.png')
sheet.save(target)
print(target, len(tiles))
