"""Contact sheet of delivered characters. Per character: row 1 = body montage (front / three-quarter / back), face close-up
at 0.6 m (sun) and the same in overcast, 3 m gameplay shot; row 2 = hair acceptance test, strand groom (top) against the
derived game cards (bottom) from the same cameras.
usage: contact_sheet.py <out.png> <Name:reviewdir:tag[:hairtag]> ..."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
rows = []
for spec in sys.argv[2:]:
    p = spec.split(':'); name, d, tag = p[0], Path(p[1]), p[2]; htag = p[3] if len(p) > 3 else tag
    h = 900; ims = []
    for f in (f'{tag}_body.png', f'{tag}_close.png', f'{tag}_game.png'):
        if (d / f).exists():
            im = Image.open(d / f).convert('RGB'); ims.append(im.resize((int(im.size[0] * h / im.size[1]), h), Image.LANCZOS))
    w = sum(i.size[0] for i in ims); row = Image.new('RGB', (w, h + 40), (24, 24, 24)); x = 0
    for i in ims: row.paste(i, (x, 40)); x += i.size[0]
    ImageDraw.Draw(row).text((12, 12), f'{name}  (LOD0, Cycles, AgX; front / three-quarter / back | face at 0.6 m in sun and in overcast | 3 m gameplay distance)', fill=(230, 230, 230)); rows.append(row)
    hc = d / f'{htag}_hair_compare.png'
    if hc.exists():
        im = Image.open(hc).convert('RGB'); k = min(1.0, w / im.size[0]); im = im.resize((int(im.size[0] * k), int(im.size[1] * k)), Image.LANCZOS)
        r2 = Image.new('RGB', (w, im.size[1] + 40), (24, 24, 24)); r2.paste(im, (0, 40))
        ImageDraw.Draw(r2).text((12, 12), f'{name} hair acceptance: top = Cycles strand groom (hair Curves), bottom = game hair cards derived from it; same cameras (2 m sun, 0.5 m sun, 0.5 m overcast, back)', fill=(230, 230, 230)); rows.append(r2)
W = max(r.size[0] for r in rows); H = sum(r.size[1] for r in rows)
sheet = Image.new('RGB', (W, H), (24, 24, 24)); y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.size[1]
sheet.save(sys.argv[1]); print('contact sheet', sys.argv[1], sheet.size)
