"""Side-by-side: original 1997 vision 1/2 screen 439 (rendered from tools/dinkex/out) vs. the ruin seen
along the original sprite's viewing direction.  Original effects are marked on the left image and
their 3D target labels listed.  Output: Previews/compare_vision1.png, compare_vision2.png."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
KIT = HERE.parent; UE = KIT.parents[2]; REPO = UE.parent
sys.path.insert(0, str(HERE))
import ruin_common as R

OUT = REPO / 'tools/dinkex/out'


def original(vision):
    seqs = {q['seq']: q for q in json.loads((OUT / 'sequences.json').read_text())['sequences']}
    s = json.loads((OUT / 'screens/SCR_439.json').read_text())
    im = Image.new('RGBA', (600, 400), (0, 0, 0, 255))
    for t in s['tiles']:
        ts = Image.open(OUT / f"tiles/ts{t['tileset']:02d}.png").convert('RGBA')
        r = t['src']; im.paste(ts.crop((r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h'])), (t['x'], t['y']))
    pls = sorted([p for p in s['placements'] if p['vision'] in (0, vision) and p['type'] != 2], key=lambda p: p['que'] or p['y'])
    for p in pls:
        q = seqs.get(p['seq']); fr = [f for f in (q or {}).get('frames', []) if f['frame'] == p['frame'] and f.get('image')]
        if not fr:
            continue
        sp = Image.open(OUT / fr[0]['image']).convert('RGBA')
        im.paste(sp, (p['map_x'] - fr[0]['origin']['x'], p['y'] - fr[0]['origin']['y']), sp)
    return im


for v in (1, 2):
    if not (OUT / 'screens/SCR_439.json').exists():
        print('tools/dinkex/out missing; skip'); break
    left = original(v).crop((80, 40, 480, 340)).resize((900, 675), Image.LANCZOS).convert('RGB')
    d = ImageDraw.Draw(left)
    for e in R.exterior_effects():
        if e['vision'] != v:
            continue
        x, y = e['visual_pixel']; X, Y = (x - 80) * 2.25, (y - 40) * 2.25
        d.ellipse((X - 7, Y - 7, X + 7, Y + 7), outline=(0, 255, 255), width=3)
        d.text((X + 9, Y - 6), e['id'][-3:], fill=(0, 255, 255))
    rp = KIT / f'Previews/_compare_v{v}_render.png'
    right = Image.open(rp).convert('RGB').resize((900, 600)) if rp.exists() else Image.new('RGB', (900, 600))
    canvas = Image.new('RGB', (1800, 700), (20, 20, 20))
    canvas.paste(left.resize((900, 675)), (0, 0)); canvas.paste(right, (900, 40))
    d = ImageDraw.Draw(canvas)
    d.text((10, 680), f'Original SCR_439 vision {v} (cyan = effect visual points)', fill=(255, 255, 255))
    d.text((910, 680), 'Ruin kit, orthographic along the fitted sprite view direction (Blender preview)', fill=(255, 255, 255))
    canvas.save(KIT / f'Previews/compare_vision{v}.png')
    print('wrote compare', v)
