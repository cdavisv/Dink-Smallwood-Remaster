#!/usr/bin/env python3
"""Review sheets of the screen-ground captures:
    python3 -I Scripts/PhotorealQA/ground_sheet.py <capture dir> <out dir> [--by-class]

Reads <capture dir>/ground_index.json (written by ground_script.py) and the NNN_play / NNN_close / NNN_above PNGs.
Default: one JPEG per two screens (ground_<a>_<b>.jpg), three views each, labelled with the tile classes and layers.
--by-class: one JPEG per reason a screen was chosen (layer_MeadowTurf.jpg, class_cliff_face.jpg, ...), the screens of
that reason in rows, for the review record. Needs Pillow."""
import json, os, re, sys
from PIL import Image, ImageDraw

CELL = (640, 360)
VIEWS = (('play', 'play camera'), ('close', '1.1 m above the ground'), ('above', 'from above the south edge'))


def row_image(folder, rec):
    row = Image.new('RGB', (CELL[0] * 3, CELL[1] + 36), (24, 24, 24)); d = ImageDraw.Draw(row)
    classes = ', '.join('%s %d' % kv for kv in sorted(rec['classes'].items(), key=lambda kv: -kv[1]))
    d.text((6, 3), 'screen %d (%s, %s%s): %s' % (rec['screen'], rec['region'], rec['kind'], ', indoor' if rec['indoor'] else '', classes), fill=(240, 240, 240))
    d.text((6, 19), 'layers: %s%s%s   chosen for: %s' % (', '.join(rec['layers']), '   NOT DRAWN: ' + ', '.join(rec['dropped']) if rec['dropped'] else '',
                                                    '' if rec['water_rects'] or not rec['classes'].get('water') else '   water tiles, no water surface', '; '.join(rec['why'])), fill=(200, 200, 160))
    for i, (kind, _) in enumerate(VIEWS):
        f = os.path.join(folder, '%03d_%s.png' % (rec['screen'], kind))
        if os.path.isfile(f): row.paste(Image.open(f).convert('RGB').resize(CELL, Image.LANCZOS), (i * CELL[0], 36))
    return row


def stack(rows, path):
    sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)), (24, 24, 24)); y = 0
    for r in rows: sheet.paste(r, (0, y)); y += r.height
    sheet.save(path, quality=84)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    folder, out = os.path.abspath(args[0]), os.path.abspath(args[1]); os.makedirs(out, exist_ok=True)
    index = [r for r in json.load(open(os.path.join(folder, 'ground_index.json'))) if os.path.isfile(os.path.join(folder, '%03d_play.png' % r['screen']))]
    if '--by-class' in sys.argv:
        groups = {}
        for rec in index:
            for why in rec['why']: groups.setdefault(why, []).append(rec)
        for why, recs in sorted(groups.items()):
            name = re.sub(r'[^A-Za-z0-9]+', '_', why).strip('_')
            for k in range(0, len(recs), 4):
                stack([row_image(folder, r) for r in recs[k:k + 4]], os.path.join(out, '%s%s.jpg' % (name, '' if len(recs) <= 4 else '_%d' % (k // 4 + 1))))
        print('%d sheets -> %s' % (len(os.listdir(out)), out))
        return
    for k in range(0, len(index), 2):
        pair = index[k:k + 2]
        stack([row_image(folder, r) for r in pair], os.path.join(out, 'ground_%s.jpg' % '_'.join('%03d' % r['screen'] for r in pair)))
    print('%d sheets -> %s' % ((len(index) + 1) // 2, out))


if __name__ == '__main__':
    main()
