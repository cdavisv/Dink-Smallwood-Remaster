"""Stream contact sheet: one row per delivered creature, final baked-game-mesh review renders. usage: python3 -I contact_sheet.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
OUT = Path(__file__).resolve().parents[1]
ROWS = [
    ('Pillbug (SK_Pillbug + SM_Pillbug_Corpse)', 'Pillbug/Review', ['r3_game.png', 'r3_close.png', 'r3_back.png', 'r3_run05.png', 'corpse_game.png']),
    ('Pig (SK_Pig)', 'Pig/Review', ['final_game.png', 'final_close.png', 'final_side.png', 'final_walk06.png', 'final_feed07.png']),
    ('Duck (SK_Duck, SK_Duck_Headless, SM_Duck_Head)', 'Duck/Review', ['final_mid.png', 'final_close.png', 'final_back.png', 'final_headless.png', 'final_head.png']),
    ('Slime (SK_Slime: blue / green / red)', 'Slime/Review', ['final_game.png', 'final_close.png', 'green_close.png', 'red_close.png', 'final_attack07.png']),
]
TW, TH = 480, 360
try: font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 20)
except Exception: font = ImageFont.load_default()
rows = [(t, d, [f for f in fs if (OUT / d / f).exists()]) for t, d, fs in ROWS]; rows = [r for r in rows if r[2]]
sheet = Image.new('RGB', (TW * 5, (TH + 30) * len(rows)), (24, 24, 24)); dr = ImageDraw.Draw(sheet)
for r, (title, d, fs) in enumerate(rows):
    y = r * (TH + 30); dr.text((8, y + 4), title, fill=(235, 235, 235), font=font)
    for c, f in enumerate(fs):
        im = Image.open(OUT / d / f).convert('RGB'); im.thumbnail((TW, TH)); sheet.paste(im, (c * TW + (TW - im.width) // 2, y + 30))
sheet.save(OUT / 'contact_sheet.png'); print('contact sheet', sheet.size, [len(r[2]) for r in rows])
