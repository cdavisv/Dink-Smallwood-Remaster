#!/usr/bin/env python3
"""Write the dink.CaptureScript that photographs physical-mapping spots (the worst of summarise_phys_audit.py's
phys_mismatches.csv, or --subjects) at the play camera: _0 at rest, _1 after walking towards the subject's middle for 4 s,
_2 with the hardness prisms shown (dink.GreyboxBlockers 1); --overhead adds _3/_4 from above. phys_audit_sheet.py lays them out.

    python3 -I Scripts/phys_audit_shots.py <audit dir> <shot dir> [--top N] [--subjects 588:S588_P05,470:tile4_1] [--overhead] > shots.txt

Dink is put on a free pixel (1997 hardness 0, tools/dinkex/out/hardness) south of the subject, so the play camera, which
looks north over his shoulder, has the subject in front of him."""
import argparse
import csv
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))


def free_pixel(screen, x, y, below, repo=REPO):
    path = os.path.join(repo, 'tools', 'dinkex', 'out', 'hardness', f'SCR_{screen:03d}.png')
    if not os.path.exists(path):
        return x, below
    im = Image.open(path)
    px = im.load()

    def free(cx, cy):
        for dy in range(-10, 11, 5):
            for dx in range(-10, 11, 5):
                qx, qy = cx + dx, cy + dy
                if not (0 <= qx < 600 and 0 <= qy < 400) or px[qx, qy] != 0:
                    return False
        return True
    for d in range(0, 160, 6):
        for cx, cy in ((x, below + d), (x - d, below + d // 2), (x + d, below + d // 2), (x, below - d)):
            if 15 <= cx < 585 and 15 <= cy < 385 and free(cx, cy):
                return cx, cy
    return x, below


def subject_box(origins, scr, subj):
    """Map-pixel box of a subject: an origin (its 1997 hardbox, else its sprite point) or "tile<tx>_<ty>" (a 50 px tile)."""
    if subj.startswith('tile'):
        tx, ty = (int(v) for v in subj[4:].split('_'))
        return tx * 50, ty * 50, tx * 50 + 49, ty * 50 + 49
    r = origins.get((scr, subj))
    if not r:
        return None
    l, t, rr, b = (int(float(r[k])) for k in ('box_l', 'box_t', 'box_r', 'box_b'))
    if rr < l:
        l = rr = int(float(r['sprite_x']))
        t = b = int(float(r['sprite_y']))
    return l, t, rr, b


def capture_lines(scr, name, box, shots, repo=REPO, overhead=False):
    """The lines of one spot: Dink on a free pixel south of the box (_0, at rest), walked towards its middle for 4 s (_1),
    the hardness prisms shown (_2); with overhead also a high view with (_3) and without (_4) the prisms."""
    l, t, rr, b = box
    cx, cy = max(5, min(594, (l + rr) // 2)), max(5, min(394, (t + b) // 2))
    x, y = free_pixel(scr, cx, min(392, b + 45), min(392, b + 45), repo)
    tag = os.path.join(shots, f'{scr:03d}_{name}')
    out = [f'dink.Goto {scr} {x} {y}', 'wait 4', f'shot {tag}_0.png', f'dink.WalkTo {cx} {cy} 4', 'wait 6', 'dink.Player',
           f'shot {tag}_1.png', 'dink.GreyboxBlockers 1', 'wait 1', f'shot {tag}_2.png']
    if overhead:
        out += ['dink.CameraDistance 900', 'dink.View -90 -62', 'wait 1', f'shot {tag}_3.png', 'dink.GreyboxBlockers 0', 'wait 1',
                f'shot {tag}_4.png', 'dink.CameraDistance 400', 'dink.View -90 -12']
    else:
        out += ['dink.GreyboxBlockers 0']
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('audit')
    ap.add_argument('shots')
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--subjects', default='', help='comma list of <screen>:<origin or tile<tx>_<ty>>, e.g. 588:S588_P05,470:tile4_1')
    ap.add_argument('--mismatches', default='')
    ap.add_argument('--repo', default=REPO)
    ap.add_argument('--overhead', action='store_true', help='also a high view of each spot (_3 with prisms, _4 without)')
    a = ap.parse_args(argv)
    origins = {}
    with open(os.path.join(a.audit, 'phys_origins.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            origins[(int(r['screen']), r['origin'])] = r
    picks = []
    if a.subjects:
        for item in a.subjects.split(','):
            scr, subj = item.split(':', 1)
            picks.append((int(scr), subj))
    else:
        with open(a.mismatches or os.path.join(a.audit, 'phys_mismatches.csv'), newline='', encoding='utf-8') as f:
            seen = set()
            for m in csv.DictReader(f):
                subj = m['subject'].replace('tile ', 'tile').replace(',', '_')
                key = (int(m['screen']), subj)
                if key in seen or subject_box(origins, *key) is None:
                    continue
                seen.add(key)
                picks.append(key)
                if len(picks) >= a.top:
                    break
    out = ['wait 25', 'dink.Fact lifemax 900', 'dink.Fact life 900', 'dink.Fact strength 3']
    for scr, subj in picks:
        box = subject_box(origins, scr, subj)
        if box:
            out += capture_lines(scr, subj, box, a.shots, a.repo, a.overhead)
    out.append('quit')
    print('\n'.join(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
