#!/usr/bin/env python3
"""contact_sheet.py <after dir>: before | after pairs from identical cameras -> ../contact_sheet.png"""
import sys, glob, os
from PIL import Image, ImageDraw, ImageFont
L = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Saved', 'PhotorealPass', 'lighting'))
after = sys.argv[1]
names = sorted(os.path.basename(f) for f in glob.glob(f'{L}/before/*.png'))
W, H, PAD, BAR = 640, 360, 6, 22
cols = 2  # pairs per row
rows = (len(names) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (2 * W + PAD) + PAD * (cols + 1), rows * (H + BAR + PAD) + PAD), (24, 24, 24))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 14)
except Exception:
    font = ImageFont.load_default()
for i, n in enumerate(names):
    x = PAD + (i % cols) * (2 * W + 2 * PAD)
    y = PAD + (i // cols) * (H + BAR + PAD)
    draw.text((x + 2, y + 3), f'{n[:-4]}   before', fill=(230, 230, 230), font=font)
    draw.text((x + W + PAD + 2, y + 3), 'after', fill=(230, 230, 230), font=font)
    for j, d in enumerate((f'{L}/before', after)):
        f = f'{d}/{n}'
        if os.path.exists(f):
            sheet.paste(Image.open(f).convert('RGB').resize((W, H), Image.LANCZOS), (x + j * (W + PAD), y + BAR))
sheet.save(f'{L}/contact_sheet.png')
print(f'{L}/contact_sheet.png', sheet.size)
