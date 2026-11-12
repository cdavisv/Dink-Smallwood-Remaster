"""Stream contact sheet: one row per delivered creature, final baked-game-mesh review renders. usage: python3 -I contact_sheet.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
OUT = Path(__file__).resolve().parents[1]
ROWS = [
    ('Pillbug (SK_Pillbug + SM_Pillbug_Corpse): game 6 m / 1 m / back / run / corpse', 'Pillbug/Review', ['r4_game.png', 'r4_close.png', 'r4_back.png', 'r3_run05.png', 'corpse_game.png']),
    ('Pig v2 (SK_Pig): game 6 m / 1 m / side / back / feed pose', 'Pig/Review', ['final_game.png', 'final_close.png', 'final_side.png', 'final_back.png', 'final_feed07.png']),
    ('Pig v2 poses: walk f6 / run f4', 'Pig/Review', ['final_walk06.png', 'final_run04.png']),
    ('Duck v2 (SK_Duck): game 6 m / 2 m / 1 m / back / walk', 'Duck/Review', ['final_game.png', 'final_mid.png', 'final_close.png', 'final_back.png', 'final_walk04.png']),
    ('Duck v2 gore and underside (SK_Duck_Headless, SM_Duck_Head): headless run / severed head / underside / peck / quack', 'Duck/Review', ['final_headless.png', 'final_head.png', 'final_under.png', 'final_peck18.png', 'final_quack08.png']),
    ('Slime v2 (SK_Slime blue / green / red, SM_Slime_Trail): game 6 m / 1 m / green / red / back', 'Slime/Review', ['final_game.png', 'final_close.png', 'green_close.png', 'red_close.png', 'final_back.png']),
    ('Slime v2 poses: walk f8 / attack f7 / death f31', 'Slime/Review', ['final_walk08.png', 'final_attack07.png', 'final_death31.png']),
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
