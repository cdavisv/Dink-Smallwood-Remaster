#!/usr/bin/env python3
"""ingame3_sheet.py: builds Saved/PhotorealPass/ingame4/contact_sheet.png (ingame2 | ingame3 per camera, then the
calibration pairs engine | Blender reference, indoor before | after, the town kit test house) and the *_close crops."""
import glob, os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
PASS = os.path.abspath(os.path.join(HERE, '..', '..', 'Saved', 'PhotorealPass'))
NEW, OLD, CAL = PASS + '/ingame5', PASS + '/ingame4', PASS + '/lighting/cal'
REV = os.path.abspath(PASS + '/../../SourceAssets/Art/PhotorealPass')
REF = {'oak': 'Vegetation/Review/SM_Veg_Oak_Large_01_game.png', 'pine': 'Vegetation/Review/SM_Veg_Pine_Large_01_game.png', 'willow': 'Vegetation/Review/SM_Veg_Willow_01_game.png',
       'bush': 'Vegetation/Review/SM_Veg_Bush_close.png', 'grassgrid': 'Vegetation/Review/GrassPatch_carpet_close.png', 'carpet': 'Vegetation/Review/GrassPatch_carpet_close.png',
       'carpetgame': 'Vegetation/Review/GrassPatch_carpet_game.png'}
W, H, PAD, BAR = 560, 315, 6, 20
try: font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 13)
except Exception: font = ImageFont.load_default()
def fit(path, crop32=False):
    im = Image.open(path).convert('RGB')
    if crop32:
        w, h = im.size; cw = int(h * 1.5); im = im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    im.thumbnail((W, H), Image.LANCZOS)
    cell = Image.new('RGB', (W, H), (12, 12, 12)); cell.paste(im, ((W - im.width) // 2, (H - im.height) // 2)); return cell
pairs = []
for f in sorted(glob.glob(NEW + '/[0-9][0-9]_*.png')):
    n = os.path.basename(f)
    if n.endswith('_close.png') or n[:2] in ('29', '47', '48', '49'): continue
    pairs.append((n[:-4], OLD + '/' + n if os.path.exists(OLD + '/' + n) else None, f, 'ingame4', 'ingame5', False))
for shot, ref in REF.items():
    e = f'{CAL}/final_{shot}.png'
    if os.path.exists(e): pairs.append(('calibration ' + shot, e, REV + '/' + ref, 'engine (central 3:2 crop)', 'Cycles reference', True))
for f in sorted(glob.glob(NEW + '/indoor/indoor_*_before.png')):
    pairs.append((os.path.basename(f)[7:-11], f, f.replace('_before', '_after'), 'indoor set off', 'indoor set on', False))
CAL2 = PASS + '/lighting/cal2'
for shot, ref in (('Cottage_gameplay', 'Structures/review/sb6/Cottage_gameplay.png'), ('Cottage_roof', 'Structures/review/sb6/Cottage_roof.png'), ('Boulders_gameplay', 'Structures/review/sb6/Boulders_gameplay.png')):
    if os.path.exists(f'{CAL2}/r0_{shot}.png'): pairs.append(('calibration ' + shot, f'{CAL2}/r0_{shot}.png', REV + '/' + ref, 'engine (central crop)', 'Cycles reference', True))
for shot, ref in (('Yard_gameplay', 'Structures/review/sb6/Yard_gameplay.png'), ('House_gameplay', 'Structures/review/town4/House_gameplay.png'), ('House_street', 'Structures/review/town4/House_street.png')):
    if os.path.exists(f'{CAL2}/r1_{shot}_a.png'): pairs.append(('calibration ' + shot + ' (after the LOD section fix)', f'{CAL2}/r1_{shot}_a.png', REV + '/' + ref, 'engine (central crop)', 'Cycles reference', True))
extra = [f for f in (f'{CAL}/final_plaster.png', f'{CAL}/final_dungeon.png', f'{CAL}/final_town.png', f'{CAL}/final_townclose.png', f'{CAL}/final_townback.png',
                     f'{CAL}/final_cottage.png', f'{CAL}/final_structs.png', NEW + '/indoor/hero_face_b.png', NEW + '/indoor/heroclose_gameplay_a.png',
                     NEW + '/29_burnable_pine_307_before.png', NEW + '/29_burnable_pine_307_after.png') if os.path.exists(f)]
for i in range(0, len(extra), 2):
    a, b = extra[i], extra[i + 1] if i + 1 < len(extra) else None
    pairs.append(('engine: ' + os.path.basename(a)[:-4].replace('final_', '') + (' | ' + os.path.basename(b)[:-4].replace('final_', '') if b else ''), a, b, '', '', False))
cols = 2; rows = (len(pairs) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (2 * W + PAD) + PAD * (cols + 1), rows * (H + BAR + PAD) + PAD), (24, 24, 24)); d = ImageDraw.Draw(sheet)
for i, (name, a, b, la, lb, crop) in enumerate(pairs):
    x = PAD + (i % cols) * (2 * W + 2 * PAD); y = PAD + (i // cols) * (H + BAR + PAD)
    d.text((x + 2, y + 3), f'{name}   {la}', fill=(230, 230, 230), font=font); d.text((x + W + PAD + 2, y + 3), lb, fill=(230, 230, 230), font=font)
    if a: sheet.paste(fit(a, crop), (x, y + BAR))
    if b and os.path.exists(b): sheet.paste(fit(b), (x + W + PAD, y + BAR))
sheet.save(NEW + '/contact_sheet.png'); print(NEW + '/contact_sheet.png', sheet.size, len(pairs), 'pairs')
for n in ('13_hero_front_2m', '15_pines_183', '18_meadow_low_604', '25_oaks_664'):
    f = f'{NEW}/{n}.png'
    if os.path.exists(f):
        im = Image.open(f); w, h = im.size; im.crop((w // 4, h // 4 - h // 8, 3 * w // 4, 3 * h // 4 - h // 8)).resize((w, h), Image.LANCZOS).save(f'{NEW}/{n}_close.png')
