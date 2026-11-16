#!/usr/bin/env python3
"""Contact sheet of physical-mapping captures (phys_audit_shots.py naming: <screen>_<subject>_<0|1|2>.png = at rest, after
walking into the subject, hardness prisms shown). One row per subject, three columns, a caption per row.

    python3 -I Scripts/phys_audit_sheet.py <shot dir> <out.jpg> [--subjects 588_S588_P05,...] [--captions captions.csv] [--width 480]

captions.csv: subject,caption (optional)."""
import argparse
import csv
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('shots')
    ap.add_argument('out')
    ap.add_argument('--subjects', default='')
    ap.add_argument('--captions', default='')
    ap.add_argument('--width', type=int, default=480)
    a = ap.parse_args(argv)
    names = sorted({f.rsplit('_', 1)[0] for f in os.listdir(a.shots) if f.endswith('.png')})
    if a.subjects:
        names = [n for n in a.subjects.split(',') if n]
    caps = {}
    if a.captions and os.path.exists(a.captions):
        with open(a.captions, newline='', encoding='utf-8') as f:
            caps = {r['subject']: r['caption'] for r in csv.DictReader(f)}
    w = a.width
    h = w * 9 // 16
    cap_h = 22
    sheet = Image.new('RGB', (3 * w, len(names) * (h + cap_h)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 14)
    except OSError:
        font = ImageFont.load_default()
    for row, n in enumerate(names):
        y = row * (h + cap_h)
        draw.text((6, y + 3), f"{n}: {caps.get(n, '')}  [at rest | walked in | hardness shown]", fill=(235, 235, 235), font=font)
        for col in range(3):
            p = os.path.join(a.shots, f'{n}_{col}.png')
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert('RGB').resize((w, h))
            sheet.paste(im, (col * w, y + cap_h))
    sheet.save(a.out, quality=82)
    print(f'{a.out}: {len(names)} rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
