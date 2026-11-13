"""Label strip for the build review montages written by render_physique.py (left to right: scrawny, farmhand, brawny).
usage: python3 -I physique_labels.py <Review dir> <file> [<file> ...]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
d = Path(sys.argv[1]); names = ('Scrawny (new game)', 'Farmhand (exported mesh, mid game)', 'Brawny (late game)')
font = ImageFont.load_default(size=22)
for f in sys.argv[2:]:
    im = Image.open(d / f).convert('RGB'); w, h = im.size; out = Image.new('RGB', (w, h + 40), (24, 24, 24)); out.paste(im, (0, 40)); dr = ImageDraw.Draw(out)
    for i, n in enumerate(names): dr.text((i * w // 3 + 12, 8), n, fill=(235, 235, 235), font=font)
    out.save(d / f); print('labelled', f)
