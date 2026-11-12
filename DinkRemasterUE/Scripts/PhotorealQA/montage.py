#!/usr/bin/env python3
"""montage.py <out.jpg> <cols> <cell width> <png...>: labelled grid of captures (16:9 cells)."""
import sys, os
from PIL import Image, ImageDraw
out, cols, cw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); fs = sys.argv[4:]
ch = cw * 9 // 16; rows = (len(fs) + cols - 1) // cols
sheet = Image.new('RGB', (cols * cw, rows * ch), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB'); im.thumbnail((cw, ch), Image.LANCZOS)
    x, y = (i % cols) * cw, (i // cols) * ch
    sheet.paste(im, (x + (cw - im.width) // 2, y))
    d.text((x + 4, y + 2), os.path.basename(f)[:-4], fill=(255, 255, 0))
sheet.save(out, quality=88)
