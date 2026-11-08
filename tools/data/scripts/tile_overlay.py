"""Draw the current tile labels onto each tileset sheet for review.
Writes out/tiles/tsNN_labels.png. Usage: python3 tile_overlay.py [ts ...]"""
import os
import sys
from PIL import Image, ImageDraw
import dinkdata as d
from tile_sheets import tile_usage, OUT, SCALE
from tile_labels import label

AB = {'grass': 'GRS', 'grass_rocky': 'GRk', 'rock_mass': 'ROCK', 'gravel': 'grav', 'path': 'PATH',
      'dirt': 'dirt', 'sand': 'SAND', 'water': 'WAT', 'ice': 'ICE', 'snow': 'SNOW', 'lava': 'LAVA',
      'cliff_face': 'CLF', 'forest_canopy': 'FOR', 'wasteland': 'WST', 'chasm': 'PIT',
      'cave_floor': 'cFL', 'cave_wall': 'cWL', 'wood_floor': 'WOOD', 'stone_floor': 'STN',
      'structure_facade': 'FAC', 'void': 'VOID'}


def main(argv):
    use = tile_usage()
    sel = [int(a) for a in argv] or sorted({d.tile_of(t)[0] for t in use})
    S = 50 * SCALE
    for ts in sel:
        im = Image.open(os.path.join(OUT, 'ts%02d.png' % ts)).convert('RGB')
        dr = ImageDraw.Draw(im)
        for cell in range(128):
            num = (ts - 1) * 128 + cell
            if num not in use:
                continue
            lab = label(num)
            ox, oy = (cell % 12) * S, (cell // 12) * S
            if lab is None:
                txt, col = 'MISSING', (255, 0, 0)
            else:
                txt = AB[lab['terrain']] + ('|' + AB[lab['transition']] if lab['transition'] else '')
                col = {'high': (255, 255, 255), 'medium': (255, 200, 0), 'low': (255, 60, 60)}[lab['confidence']]
            dr.rectangle([ox + 2, oy + 40, ox + 8 + 7 * len(txt), oy + 54], fill=(0, 0, 0))
            dr.text((ox + 4, oy + 41), txt, fill=col)
        im.save(os.path.join(OUT, 'ts%02d_labels.png' % ts))
    print('overlays:', sel)


if __name__ == '__main__':
    main(sys.argv[1:])
