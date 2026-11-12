"""Write <kit>/manifest.json from modules.json + notes.json and build <kit>/contact_sheet.png from review renders.
python3 -I finish.py KITDIR RENDERDIR [SHEET_PATH]"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
KIT = os.path.abspath(sys.argv[1]); RD = sys.argv[2]
SHEET = sys.argv[3] if len(sys.argv) > 3 else os.path.join(KIT, 'contact_sheet.png')
notes = json.load(open(os.path.join(KIT, 'tools', 'notes.json')))
mods = []
for f in notes.get('module_files', ['modules.json']):
    mods += json.load(open(os.path.join(KIT, f)))
for m in mods:
    m.update(notes.get('all_modules', {}))
    m.update(notes['modules'].get(m['name'], {}))
    m.setdefault('status', 'interim')
man = {k: v for k, v in notes.items() if k not in ('modules', 'all_modules', 'sheet_top', 'module_files', 'prefix')}
man['modules'] = mods
json.dump(man, open(os.path.join(KIT, 'manifest.json'), 'w'), indent=1)
try:
    font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 16)
except Exception:
    font = ImageFont.load_default()
tops = [t for t in notes.get('sheet_top', []) if os.path.exists(os.path.join(RD, t + '.png'))]
cw, ch, cols = 480, 360, 4
W = cols * cw
tw = W // 2; th = int(tw * 850 / 1300); trows = (len(tops) + 1) // 2
shots = []
for m in mods:
    for suf in ('_sun', '_close'):
        p = os.path.join(RD, m['name'] + suf + '.png')
        if os.path.exists(p):
            shots.append((m, suf, p))
rows = (len(shots) + cols - 1) // cols
s = Image.new('RGB', (W, trows * (th + 4) + rows * (ch + 24) + 4), (18, 18, 18)); d = ImageDraw.Draw(s)
for k, t in enumerate(tops):
    s.paste(Image.open(os.path.join(RD, t + '.png')).convert('RGB').resize((tw, th), Image.LANCZOS), ((k % 2) * tw, (k // 2) * (th + 4)))
    d.text(((k % 2) * tw + 6, (k // 2) * (th + 4) + 4), t, fill=(255, 255, 255), font=font)
pre = notes.get('prefix', 'SM_')
for i, (m, suf, p) in enumerate(shots):
    x = (i % cols) * cw; y = trows * (th + 4) + (i // cols) * (ch + 24)
    d.text((x + 4, y + 3), '%s%s  %s tris  [%s]' % (m['name'].replace(pre, ''), ' (1.5 m eye)' if suf == '_close' else '', m['lod0_triangles'], m['status']), fill=(235, 235, 235), font=font)
    s.paste(Image.open(p).convert('RGB').resize((cw, ch), Image.LANCZOS), (x, y + 22))
s.save(SHEET)
print('manifest + sheet', len(mods), s.size)
