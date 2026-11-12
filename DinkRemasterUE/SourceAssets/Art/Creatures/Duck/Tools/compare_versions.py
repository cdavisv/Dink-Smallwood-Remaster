"""Side-by-side v1 / v2 / v3 at the game camera distance and close up (python3 + Pillow).

    python3 Tools/compare_versions.py

v2 and v3 are real renders from the same 4 m / 1.7 m / 35 mm game camera (v2 rendered from the
Working/v2 snapshot).  The v1 source was overwritten before this camera existed, so its game-distance
panel is its beauty render scaled to the same pixels-per-metre (approximation; camera height differs).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402

W = D.WORKING
v1_beauty = Image.open(W / 'v1_previews' / 'preview_duck_beauty.png').convert('RGB')
v2_beauty = Image.open(W / 'v2_previews' / 'preview_duck_beauty.png').convert('RGB')
v3_beauty = Image.open(D.PREVIEWS / 'preview_duck_beauty.png').convert('RGB')
v2_game = Image.open(W / 'v2_game' / 'preview_duck_game_distance.png').convert('RGB')
v3_game = Image.open(D.PREVIEWS / 'preview_duck_game_distance.png').convert('RGB')
# pixels per metre: beauty 85 mm at 1.48 m over 1600 px; game 35 mm at 4.0 m over 1280 px
ratio = (35 / 4.0 * 1280) / (85 / 1.48 * 1600)
v1_game_like = v1_beauty.resize((round(1600 * ratio), round(1200 * ratio)), Image.LANCZOS)
C = 220  # crop around the duck in the 1280x720 game frame
cx, cy = 640, 400


def crop(im):
    return im.crop((cx - C // 2, cy - C // 2, cx + C // 2, cy + C // 2))


def pad(im):
    out = Image.new('RGB', (C, C), (60, 70, 60))
    out.paste(im, ((C - im.width) // 2, (C - im.height) // 2))
    return out


games = [pad(v1_game_like), crop(v2_game), crop(v3_game)]
S = 3
cell = C * S
sheet = Image.new('RGB', (cell * 3, cell + int(cell * 0.75)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, (g, b, lab) in enumerate(zip(games, (v1_beauty, v2_beauty, v3_beauty), ('v1', 'v2', 'v3'))):
    sheet.paste(g.resize((cell, cell), Image.LANCZOS), (i * cell, 0))
    sheet.paste(b.resize((cell, int(cell * 0.75)), Image.LANCZOS), (i * cell, cell))
    d.text((i * cell + 10, 10), lab + (' game distance (approx: scaled beauty)' if i == 0 else ' game camera 4 m / 1.7 m / 35 mm (x3 crop)'), fill=(255, 235, 120))
    d.text((i * cell + 10, cell + 10), lab + ' close-up beauty', fill=(255, 235, 120))
sheet.save(D.PREVIEWS / 'preview_duck_compare_v1_v2_v3.png')
print('compare sheet written')
