"""Stack the engine frames of several capture tags into one sheet per state, one row per tag.
  python3 -I Scripts/AnimationQA/compare.py <state> <crop l,t,r,b> <every> <tag> [tag ...]
Writes Saved/AnimationPass/compare_<state>.png."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
project = Path(__file__).resolve().parents[2]
state, crop, every, tags = sys.argv[1], tuple(int(v) for v in sys.argv[2].split(',')), int(sys.argv[3]), sys.argv[4:]
rows = []
for tag in tags:
    files = []
    for folder in sorted((project / 'Saved/AnimationPass/frames').glob('%s_%s*' % (tag, state))):
        files += sorted(folder.glob('*.png'))
    tiles = [Image.open(f).convert('RGB').crop(crop) for f in files[::every]]
    for t in tiles:
        t.thumbnail((170, 300))
    rows.append((tag, tiles))
w = max(sum(t.width for t in tiles) for _, tiles in rows)
h = sum(tiles[0].height for _, tiles in rows if tiles)
sheet = Image.new('RGB', (w, h), (20, 20, 24))
draw = ImageDraw.Draw(sheet)
y = 0
for tag, tiles in rows:
    x = 0
    for t in tiles:
        sheet.paste(t, (x, y)); x += t.width
    draw.text((4, y + 3), tag, fill=(255, 255, 0))
    y += tiles[0].height if tiles else 0
out = project / 'Saved/AnimationPass' / ('compare_%s.png' % state)
sheet.save(out)
print(out.name, [len(t) for _, t in rows])
