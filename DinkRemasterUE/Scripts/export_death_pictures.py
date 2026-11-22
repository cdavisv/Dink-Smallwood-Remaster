#!/usr/bin/env python3
"""Export the 1997 death pictures the corpse layer shows (UDinkCorpsePresenter, doc/remaster/GORE_STORY_PARITY.md G4).

    python3 -I Scripts/export_death_pictures.py [--dinkex ../tools/dinkex/out] [--out Content/Dink/Data/Sprites/Death]

In 1997 a killed monster or person leaves its death picture (add_kill_sprite, dink.cpp:12359-12420: sequence
base_death + direction, or base_walk + 5) on the ground until the screen is drawn again. The remaster draws class-bound
creatures' corpses as meshes; every other kill shows this picture on a card. For every sequence of dink.ini whose
graphics folder is a death or corpse folder, the LAST frame that has pixels is written as <seq>.png (RGBA, the original's
colour key as alpha, exactly the 1997 pixels) and its size and anchor go to death_pictures.json. Ducks (110-129) are the
duck class's (PR #113) and Dink's own death (436) is the hero's; both are left out. Deterministic: exporting twice gives
byte-identical files. Needs tools/dinkex/out (python3 -m dinkex extract, see the root AGENTS.md).
"""
import argparse
import json
import os
import shutil
import sys

# the dragons' death pictures live in the foes/dragon folder without "death" in their path (f2-x3, f2-x7) and the
# pillbug's in foes/pill (f1-x1, f1-x3)
EXTRA = {141, 143, 212, 216}
SKIP = set(range(110, 130)) | {436}
# the explosion add_kill_sprite falls back to when a sprite has no death picture (base 164, brain 7: played once, then
# gone, dink.cpp:12384-12385, 12416): every frame is exported, as an animation
ANIMATIONS = {164}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--dinkex', default=os.path.join(here, '..', '..', 'tools', 'dinkex', 'out'))
    ap.add_argument('--out', default=os.path.join(here, '..', 'Content', 'Dink', 'Data', 'Sprites', 'Death'))
    a = ap.parse_args()
    seqs = json.load(open(os.path.join(a.dinkex, 'sequences.json')))['sequences']
    os.makedirs(a.out, exist_ok=True)
    table = {}
    animations = {}
    for s in sorted(seqs, key=lambda s: s['seq']):
        if s['seq'] in ANIMATIONS:
            frames = [f for f in s.get('frames', []) if f.get('width') and f.get('image')]
            rows = []
            for f in frames:
                src = os.path.join(a.dinkex, f['image'])
                dst = os.path.join(a.out, f"{s['seq']}_{f['frame']:02d}.png")
                if not os.path.exists(dst) or open(dst, 'rb').read() != open(src, 'rb').read():
                    shutil.copyfile(src, dst)
                rows.append({'frame': f['frame'], 'width': f['width'], 'height': f['height'], 'delay_ms': f.get('delay_ms') or 0})
            animations[str(s['seq'])] = {'frames': rows, 'source': s.get('path') or ''}
            continue
        path = s.get('path') or ''
        if s['seq'] in SKIP or not ('/death' in path or s['seq'] in EXTRA):
            continue
        frames = [f for f in s.get('frames', []) if f.get('width') and f.get('image')]
        if not frames:
            continue
        f = frames[-1]
        src = os.path.join(a.dinkex, f['image'])
        if not os.path.exists(src):
            print(f'missing picture {src}', file=sys.stderr)
            return 1
        dst = os.path.join(a.out, f"{s['seq']}.png")
        if not os.path.exists(dst) or open(dst, 'rb').read() != open(src, 'rb').read():
            shutil.copyfile(src, dst)
        table[str(s['seq'])] = {'frame': f['frame'], 'width': f['width'], 'height': f['height'],
                                'origin_x': f['origin']['x'], 'origin_y': f['origin']['y'], 'source': path}
    with open(os.path.join(a.out, 'death_pictures.json'), 'w') as o:
        json.dump({'schema': 'dink-death-pictures/1',
                   'note': 'Last frame of each 1997 death sequence (Scripts/export_death_pictures.py); shown on a card by '
                           'UDinkCorpsePresenter where a killed sprite has no class corpse. width/height/origin in 1997 pixels.',
                   'pictures': table, 'animations': animations}, o, indent=1, sort_keys=True)
        o.write('\n')
    print(f'{len(table)} death pictures, {len(animations)} animations -> {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
