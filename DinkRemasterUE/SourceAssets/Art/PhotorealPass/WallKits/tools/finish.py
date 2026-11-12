"""Write WallKits/manifest.json from modules.json and build contact_sheet.png from the review renders.  python3 -I finish.py RENDER_DIR"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.dirname(HERE)
RD = sys.argv[1]
mods = json.load(open(os.path.join(OUT, 'modules.json')))
notes = json.load(open(os.path.join(HERE, 'notes.json')))
for m in mods:
    m.update(notes['modules'].get(m['name'], {}))
    m.setdefault('status', 'interim')
man = {
    'schema': 'dink-wallkits/1',
    'root': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/WallKits',
    'fit': notes['fit'],
    'materials': notes['materials'],
    'third_party': notes['third_party'],
    'validator': notes.get('validator', ''),
    'modules': mods,
}
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
try:
    font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 18)
except Exception:
    font = ImageFont.load_default()
cw, ch, cols = 520, 390, 2
rows = (len(mods) + cols - 1) // cols
RH = 693
s = Image.new('RGB', (cols * (cw * 2 + 10), rows * (ch + 26) + 2 * (RH + 26)), (18, 18, 18)); d = ImageDraw.Draw(s)
for a, kind in enumerate(('Plaster', 'Dungeon')):
    y0 = rows * (ch + 26) + a * (RH + 26)
    d.text((4, y0 + 3), 'assembled %s room corner, gameplay camera: sun and torch' % kind.lower(), fill=(235, 235, 235), font=font)
    for k, mode in enumerate(('sun', 'torch')):
        p = os.path.join(RD, 'Room_%s_%s.png' % (kind, mode))
        if os.path.exists(p):
            s.paste(Image.open(p).convert('RGB').resize((1040, RH), Image.LANCZOS), (k * 1050, y0 + 24))
for i, m in enumerate(mods):
    x = (i % cols) * (cw * 2 + 10); y = (i // cols) * (ch + 26)
    d.text((x + 4, y + 3), '%s   %s tris   %s   [%s]' % (m['name'], m['lod0_triangles'], ', '.join(m['families']) or 'authored', m['status']), fill=(235, 235, 235), font=font)
    for k, mode in enumerate(('sun', 'torch')):
        p = os.path.join(RD, '%s_%s.png' % (m['name'], mode))
        if os.path.exists(p):
            s.paste(Image.open(p).convert('RGB').resize((cw, ch), Image.LANCZOS), (x + k * cw, y + 24))
s.save(os.path.join(OUT, 'contact_sheet.png'))
print('manifest + sheet', len(mods), s.size)
