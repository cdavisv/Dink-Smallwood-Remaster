#!/usr/bin/env python3
"""Quality sheet per stop: one column per scalability lap, from a dink.Perf.Route --shots directory.

  python3 -I Scripts/perf/level_sheet.py SHOTS_DIR OUT_DIR [--laps default1,epic1,high1,medium1,low1,lowplus1] [--width 480]

Shots are <lap>_<stop>.png (Scripts/perf/make_route.py --shots). Writes OUT_DIR/levels_<stop>.jpg (one row per stop,
grouped four stops per sheet) as small JPEGs for Docs/Verification.
"""
import argparse
import glob
import os
from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shots")
    ap.add_argument("out")
    ap.add_argument("--laps", default="default1,epic1,high1,medium1,low1,lowplus1")
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--per-sheet", type=int, default=4)
    a = ap.parse_args()
    laps = a.laps.split(",")
    stops = sorted({os.path.basename(f)[len(l) + 1:-4] for l in laps for f in glob.glob(os.path.join(a.shots, f"{l}_*.png"))})
    os.makedirs(a.out, exist_ok=True)
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    W = a.width
    H = W * 9 // 16
    PAD, BAR = 4, 20
    for start in range(0, len(stops), a.per_sheet):
        group = stops[start:start + a.per_sheet]
        sheet = Image.new("RGB", (PAD + len(laps) * (W + PAD), PAD + len(group) * (H + BAR + PAD)), (20, 20, 20))
        draw = ImageDraw.Draw(sheet)
        for r, stop in enumerate(group):
            y = PAD + r * (H + BAR + PAD)
            for c, lap in enumerate(laps):
                x = PAD + c * (W + PAD)
                draw.text((x + 2, y + 2), f"{stop}  {lap}", fill=(230, 230, 230), font=font)
                path = os.path.join(a.shots, f"{lap}_{stop}.png")
                if os.path.exists(path):
                    sheet.paste(Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS), (x, y + BAR))
        out = os.path.join(a.out, f"levels_{start // a.per_sheet + 1}.jpg")
        sheet.save(out, quality=82)
        print(out, sheet.size)


if __name__ == "__main__":
    main()
