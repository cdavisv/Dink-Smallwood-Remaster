"""Compose review contact sheets from Working/frames (python3 + Pillow).

    python3 Tools/make_sheets.py

Writes Previews/preview_duck_turnaround.png and Previews/preview_duck_clips.png.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402

FR = D.WORKING / 'frames'
turn = sorted(FR.glob('turn_*.png'))
if turn:
    w, h = Image.open(turn[0]).size
    sheet = Image.new('RGB', (w * 3, h * 2), (20, 20, 20))
    for i, p in enumerate(turn[:6]):
        sheet.paste(Image.open(p).convert('RGB'), ((i % 3) * w, (i // 3) * h))
    sheet.save(D.PREVIEWS / 'preview_duck_turnaround.png')
rows = []
for name in D.ACTIONS:
    fs = sorted(FR.glob('clip_%s_*.png' % name))
    if fs:
        rows.append((name, fs))
if rows:
    w, h = Image.open(rows[0][1][0]).size
    cols = max(len(fs) for _, fs in rows)
    sheet = Image.new('RGB', (w * cols, h * len(rows)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for r, (name, fs) in enumerate(rows):
        for c, p in enumerate(fs):
            sheet.paste(Image.open(p).convert('RGB'), (c * w, r * h))
            frame = p.stem.split('_f')[-1]
            d.text((c * w + 6, r * h + 6), '%s f%s' % (name, frame), fill=(255, 235, 120))
    sheet.save(D.PREVIEWS / 'preview_duck_clips.png')
print('sheets written')
