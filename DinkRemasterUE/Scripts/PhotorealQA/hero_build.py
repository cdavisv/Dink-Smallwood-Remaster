"""The hero's build in the running game: one capture script that photographs him at three confidences
(new game, mid game, late game) from fixed cameras, and the contact sheet of the result.

  python3 -I Scripts/PhotorealQA/hero_build.py script   # writes Saved/HeroBuild/hero_build.txt
  Scripts/PhotorealQA/run_capture.sh <ABSOLUTE path of Saved/HeroBuild/hero_build.txt>
  python3 -I Scripts/PhotorealQA/hero_build.py sheet    # writes Saved/HeroBuild/hero_build_<view>.png

dink.HeroConfidence is the review switch of ADinkGreyboxCharacter: it shows the build, posture and gait of that
confidence at once, whatever the player's stats. Output stays under Saved/ (git-ignored)."""
import sys
from pathlib import Path
project = Path(__file__).resolve().parents[2]; out = project / 'Saved/HeroBuild'
STAGES = (('c000', 0.0, 'New game: scrawny'), ('c045', 0.45, 'Mid game: farmhand'), ('c100', 1.0, 'Late game: brawny'))
# camera offset and target from the player's ground point (cm; he faces +X after dink.Goto), horizontal field of view
VIEWS = (('front', (-450, 0, 110), (0, 0, 95), 46), ('threeq', (-340, 290, 120), (0, 0, 95), 46), ('side', (0, 450, 110), (0, 0, 95), 46),
         ('back', (450, 60, 120), (0, 0, 95), 46), ('torso', (-235, 45, 140), (0, 0, 128), 40))
if sys.argv[1:] == ['script']:
    rows = ['wait 22', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.ScreenScripts 0',
            'dink.Goto 438 300 200', 'wait 2', 'dink.CalAnchor 0 0']
    (out / 'frames').mkdir(parents=True, exist_ok=True)
    for tag, confidence, _ in STAGES:
        rows += ['dink.HeroConfidence %g' % confidence, 'wait 2']
        for view, cam, target, fov in VIEWS:
            rows += ['dink.CalCam %d %d %d %d %d %d %d 1' % (*cam, *target, fov), 'wait 2', 'shot %s/frames/%s_%s.png' % (out, tag, view)]
    rows += ['dink.CalCam off', 'dink.HeroConfidence -1', 'wait 1', 'quit']
    (out / 'hero_build.txt').write_text('\n'.join(rows) + '\n'); print(out / 'hero_build.txt')
elif sys.argv[1:] == ['sheet']:
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=22)
    for view, *_ in VIEWS:
        ims = [Image.open(out / 'frames' / ('%s_%s.png' % (tag, view))).convert('RGB') for tag, _, _ in STAGES]
        w, h = ims[0].size; crop = (w // 2 - h * 5 // 16, 0, w // 2 + h * 5 // 16, h); cw = crop[2] - crop[0]
        sheet = Image.new('RGB', (cw * len(ims), h + 40), (24, 24, 24)); draw = ImageDraw.Draw(sheet)
        for i, (im, (_, _, label)) in enumerate(zip(ims, STAGES)):
            sheet.paste(im.crop(crop), (i * cw, 40)); draw.text((i * cw + 12, 8), label, fill=(235, 235, 235), font=font)
        sheet.save(out / ('hero_build_%s.png' % view)); print(out / ('hero_build_%s.png' % view))
else:
    raise SystemExit(__doc__)
