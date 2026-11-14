#!/usr/bin/env python3
"""Lay captures out as one labelled sheet (JPEG) for Docs/Verification.

    python3 -I Scripts/CreatureQA/sheet.py --out Docs/Verification/X/sheet.jpg --columns 3 --width 640 \\
        "label one=path/one.png" "label two=path/two.png" ...

A cell may crop its picture first: "label=path.png@x0,y0,x1,y1" (fractions of the picture, 0..1). Original sprite frames
(small PNGs with alpha) are enlarged without smoothing when the path contains "/sprites/".
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for name in ("DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cell(spec, width, height):
    label, _, rest = spec.partition("=")
    path, _, crop = rest.partition("@")
    img = Image.open(path)
    sprite = "/sprites/" in path.replace(os.sep, "/")
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        back = Image.new("RGBA", img.size, (86, 112, 66, 255))
        back.alpha_composite(img)
        img = back
    img = img.convert("RGB")
    if crop:
        x0, y0, x1, y1 = (float(v) for v in crop.split(","))
        img = img.crop((int(x0 * img.width), int(y0 * img.height), int(x1 * img.width), int(y1 * img.height)))
    scale = min(width / img.width, height / img.height)
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    img = img.resize(size, Image.NEAREST if sprite else Image.LANCZOS)
    out = Image.new("RGB", (width, height + 26), (24, 24, 24))
    out.paste(img, ((width - size[0]) // 2, (height - size[1]) // 2))
    ImageDraw.Draw(out).text((6, height + 4), label, fill=(235, 235, 235), font=font(15))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--columns", type=int, default=3)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--aspect", type=float, default=16 / 9)
    ap.add_argument("--quality", type=int, default=88)
    ap.add_argument("cells", nargs="+")
    args = ap.parse_args()
    height = round(args.width / args.aspect)
    cells = [cell(c, args.width, height) for c in args.cells]
    rows = (len(cells) + args.columns - 1) // args.columns
    sheet = Image.new("RGB", (args.columns * args.width + (args.columns + 1) * 4, rows * (height + 26) + (rows + 1) * 4), (60, 60, 60))
    for i, c in enumerate(cells):
        sheet.paste(c, (4 + (i % args.columns) * (args.width + 4), 4 + (i // args.columns) * (height + 30)))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(args.out, quality=args.quality)
    print(args.out, sheet.size)


if __name__ == "__main__":
    main()
