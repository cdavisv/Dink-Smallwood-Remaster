#!/usr/bin/env python3
"""Side-by-side sheet of a rendering_set.py capture: one row per frame, one column per variant (same camera).

    python3 -I Scripts/PhotorealQA/rendering_sheet.py <set dir> <out.jpg> <variant> [<variant> ...] [--only a,b] [--width 640]

Each cell is labelled `<variant> <frame>`; a missing frame stays dark."""
import os, sys
from PIL import Image, ImageDraw


def main():
    argv = sys.argv[1:]
    only, width = None, 640
    if '--only' in argv: i = argv.index('--only'); only = argv[i + 1].split(','); del argv[i:i + 2]
    if '--width' in argv: i = argv.index('--width'); width = int(argv[i + 1]); del argv[i:i + 2]
    src, out, variants = argv[0], argv[1], argv[2:]
    frames = sorted({f[:-4] for v in variants if os.path.isdir(os.path.join(src, v)) for f in os.listdir(os.path.join(src, v)) if f.endswith('.png')})
    if only: frames = [f for f in frames if any(o in f for o in only)]
    h = width * 9 // 16
    sheet = Image.new('RGB', (len(variants) * (width + 4) + 4, len(frames) * (h + 4) + 4), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for r, f in enumerate(frames):
        for c, v in enumerate(variants):
            x, y = 4 + c * (width + 4), 4 + r * (h + 4)
            p = os.path.join(src, v, f + '.png')
            if os.path.exists(p):
                im = Image.open(p).convert('RGB'); im.thumbnail((width, h), Image.LANCZOS); sheet.paste(im, (x, y))
            d.rectangle((x, y, x + 8 * len(v + f) + 14, y + 16), fill=(0, 0, 0))
            d.text((x + 4, y + 2), '%s  %s' % (v, f), fill=(255, 255, 0))
    sheet.save(out, quality=90)
    print(out, sheet.size)


if __name__ == '__main__':
    main()
