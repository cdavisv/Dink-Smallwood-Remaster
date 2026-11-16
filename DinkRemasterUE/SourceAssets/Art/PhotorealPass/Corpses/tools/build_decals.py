"""Ground decals made from the 1997 pictures themselves (blood 187 / 188 / 189, burn holes 158), for the deferred decals that
environment.json `decals` binds by picture (`pictures`). Numpy and PIL only, no Blender:

    python3 -I build_decals.py            (from anywhere; writes ../Decals/T_Decal_<Set>_{BC,N,ORM}.png, decals.json, preview.png)

Each 2 x 2 atlas cell is one picture frame: the picture's opaque pixels are laid on the ground at the card's size and taken as the
wet area (tools/gore_sheets.py draws it: dark middle, drying rim, soaked fringe, a few fine drops round it), so a decal never
covers less ground than the 1997 picture. The cell is a square of CELL_OVER_CARD x the longer card side, picture in the middle,
image right = east, image down = south (the screen's own axes): the game sizes the decal from the placement's card and does not turn it.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); CORP = os.path.dirname(HERE); UE = os.path.abspath(os.path.join(CORP, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
import gore_sheets as GS
OUT = os.path.join(CORP, 'Decals'); SPR = os.path.join(UE, 'ImportData', 'sprites')
CELL = 512; CELL_OVER_CARD = 1.15
# set -> four cells: (picture, card width m, card height m of its most common placement, kind)
SETS = {
    'Blood1997A': [('187_01', 0.80, 0.45), ('187_02', 0.53, 0.30), ('187_03', 0.97, 1.40), ('188_02', 0.95, 0.72)],
    'Blood1997B': [('188_04', 0.97, 1.40), ('189_01', 0.57, 0.68), ('189_02', 0.97, 0.72), ('189_04', 1.27, 1.40)],
    'Burn1997': [('158_01', 2.21, 1.95), ('158_02', 2.20, 2.24), ('158_03', 1.84, 1.75), ('158_01', 1.01, 0.88)],
}


PIXELS = {'158_01': (23, 20), '158_03': (42, 40), '158_02': (23, 23), '188_04': (39, 56), '189_04': (51, 56), '187_03': (39, 56), '187_01': (32, 18), '187_02': (21, 12), '188_02': (38, 29), '189_01': (23, 27), '189_02': (39, 29)}      # true pixel size of each picture (placements.json card.pixel_w / pixel_h)


def picture_mask(key, up=12):
    """opaque pixels of the extracted picture as a smooth mask. The file is stretched to a power-of-two canvas, so it is first
    brought back to its true pixel grid, then enlarged and rounded off (no pixel stairs may survive into the decal)."""
    pw, ph = PIXELS[key]; a = np.asarray(Image.open(os.path.join(SPR, key + '.png')).convert('RGBA').resize((pw, ph), Image.NEAREST))
    m = Image.fromarray(((a[..., 3] > 0) * 255).astype(np.uint8), 'L').resize((pw * up, ph * up), Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.42 * up))
    v = np.asarray(m, np.float32) / 255.0; v = np.clip((v - 0.30) / 0.30, 0, 1)        # a one-pixel tongue keeps its width
    return Image.fromarray((v * 255).astype(np.uint8), 'L'), float((a[..., 3] > 0).mean())


def cell(set_name, i, key, w, h):
    side = CELL_OVER_CARD * max(w, h); seed = int(key.replace('_', '')) * 10 + i; m, frac = picture_mask(key); area = frac * w * h
    if set_name.startswith('Blood'):
        # 15 Nov 2026 look pass: the red of 187-189 (bright, saturated), a spray of fine drops and cast-off lines round the picture's own
        # drops, and only a thin red-brown stain round them (the grey damp-earth fringe read as a dirty halo on grass)
        sh = GS.blood_sheet(CELL, side, seed, stamp=(m, w, h, (0.0, 0.0)), n_drops=110, reach=0.11 * side, drop_r=(0.003, 0.013), casts=5, mist=420, edge_noise=0.25, soak_m=0.025,
                            thin=(170, 14, 9), mid=(128, 7, 5), deep=(74, 3, 3), dried=(104, 15, 10), smear=(140, 13, 9), damp=(84, 30, 20))
    else:
        sh = GS.scorch_sheet(CELL, side, seed, stamp=(m, w, h, (0.0, 0.0)), soft=True, through=True)       # burnt through: black void, far wall of the hole, charred rim
    edge = 6; sh['BC'][:edge, :, 3] = 0; sh['BC'][-edge:, :, 3] = 0; sh['BC'][:, :edge, 3] = 0; sh['BC'][:, -edge:, 3] = 0       # nothing bleeds into the next cell
    got = float((sh['BC'][..., 3] > 84).mean()) * side * side
    return sh, {'cell': i, 'picture': key, 'card_m': [w, h], 'cell_m': round(side, 3), 'picture_area_m2': round(area, 3), 'decal_area_m2': round(got, 3)}


def main():
    os.makedirs(OUT, exist_ok=True); sets = []; prev = []
    for name, cells in SETS.items():
        atlas = {'BC': np.zeros((2 * CELL, 2 * CELL, 4), np.uint8), 'N': np.zeros((2 * CELL, 2 * CELL, 3), np.uint8), 'ORM': np.zeros((2 * CELL, 2 * CELL, 3), np.uint8)}; rows = []
        atlas['N'][...] = (128, 128, 255)
        for i, (key, w, h) in enumerate(cells):
            sh, row = cell(name, i, key, w, h); y, x = (i // 2) * CELL, (i % 2) * CELL; rows.append(row); prev.append(sh)
            for role in atlas:
                atlas[role][y:y + CELL, x:x + CELL] = sh[role]
            if row['decal_area_m2'] < row['picture_area_m2']:
                raise SystemExit('%s cell %d covers less ground than picture %s' % (name, i, key))
        files = {role: os.path.basename(p) for role, p in GS.save(atlas, os.path.join(OUT, 'T_Decal_' + name)).items()}
        sets.append({'name': name, 'files': files, 'resolution_px': 2 * CELL, 'atlas': '2 x 2, one 1997 picture frame per cell', 'cells': rows,
                     'material': 'deferred decal, translucent: base colour = BC.rgb, opacity = BC.a, normal = N (OpenGL: flip green), roughness = ORM.G',
                     'known_weaknesses': 'the outline is the 1997 picture enlarged (39 to 51 pixels across), smoothed and broken up by noise: no single thrown drop with a tail as a photograph would show; '
                                         '512 px per cell, so the largest placements (3.4 m) show 0.8 cm texels; ' + ('wet look is roughness and a thin normal relief only.' if name.startswith('Blood') else 'no depth: a charred patch, not a pit.')})
    doc = {'schema': 'dink-decals/1', 'folder': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Corpses/Decals', 'generated_by': 'Corpses/tools/build_decals.py', 'cell_over_card': CELL_OVER_CARD, 'sets': sets}
    open(os.path.join(OUT, 'decals.json'), 'w').write(json.dumps(doc, indent=1) + '\n')
    # preview: soft alpha over a ground colour
    ims = []
    for s in prev:
        bc = s['BC'].astype(np.float32) / 255.0; g = np.asarray((118, 104, 70), np.float32) / 255.0
        ims.append(Image.fromarray((np.clip(bc[..., :3] * bc[..., 3:] + g * (1 - bc[..., 3:]), 0, 1) * 255).astype(np.uint8)).resize((300, 300), Image.LANCZOS))
    sh = Image.new('RGB', (300 * 4, 300 * 3))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % 4) * 300, (i // 4) * 300))
    sh.save(os.path.join(OUT, 'preview.png'))
    for s in sets:
        for r in s['cells']:
            print('%-11s cell %d  picture %s  %.2f m2 in the picture -> %.2f m2 in the decal' % (s['name'], r['cell'], r['picture'], r['picture_area_m2'], r['decal_area_m2']))


if __name__ == '__main__':
    main()
