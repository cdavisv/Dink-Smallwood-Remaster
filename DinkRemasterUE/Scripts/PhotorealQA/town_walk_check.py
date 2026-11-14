#!/usr/bin/env python3
"""Can a walking player get inside an assembled town house?
    python3 -I Scripts/PhotorealQA/town_walk_check.py [--out report.txt] [--radius-cm 30]

The kit houses have no collision of their own: the player is stopped by the 1997 hardness (ImportData/collision.json:
solid, low, sprite, fill_water and fill_solid rectangles; a door's warp rectangle takes the player away, so it counts as
closed). The ground behind a wall line, the inside of a 1997 building, has hardness 0, so a house body that stands
there is only safe when that ground cannot be reached. This check erodes the walkable ground by the capsule radius,
labels it over each 1997 building's block of screens (the building's screens and one screen around them) and reports,
per assembled house, how much of its core (60 cm inside its walls) lies in its street: the walkable component that
holds the most points 3 m in front of that house's front wall (the side away from the body). Front points that fall in
another component are listed: such ground lies behind or inside the building.
Exit code 1 when more than 2 m2 of any house core can be reached from a street. It is a check of the exported
collision, not a walk in the running game, and it does not ask whether the ground BEHIND a row of houses (the inside
of the 1997 building) can be reached some other way."""
import json, math, os, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'Scripts'))
from export_import_bundle import label_components    # noqa: E402
BLOCKING = ('solid', 'low', 'sprite', 'warp', 'fill_water', 'fill_solid')
LIMIT_M2 = 2.0


def erode(mask, r):
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r or (dx == 0 and dy == 0): continue
            sh = np.zeros_like(mask)
            sh[max(0, -dy):mask.shape[0] + min(0, -dy), max(0, -dx):mask.shape[1] + min(0, -dx)] = mask[max(0, dy):mask.shape[0] + min(0, dy), max(0, dx):mask.shape[1] + min(0, dx)]
            out &= sh
    return out


def main():
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    radius_cm = float(sys.argv[sys.argv.index('--radius-cm') + 1]) if '--radius-cm' in sys.argv else 30.0
    data = json.load(open(os.path.join(ROOT, 'Content/Dink/Data/Art/town_houses.json'))); town = data['screens']
    coll = json.load(open(os.path.join(ROOT, 'ImportData/collision.json')))['screens']
    mpp = {}
    for p in json.load(open(os.path.join(ROOT, 'ImportData/placements.json')))['placements']: mpp.setdefault(p['screen'], p['m_per_px'])
    gpx = lambda screen, x, y: ((screen - 1) % 32 * 600 + x, (screen - 1) // 32 * 400 + y)

    def walkable(n):
        row = coll.get('SCR_%03d' % n)
        if row is None: return None
        m = np.ones((400, 600), bool)
        for k in BLOCKING:
            for x0, y0, x1, y1 in row.get(k) or []: m[y0:y1, x0:x1] = False
        return m

    rows_out, bad = [], 0
    for b in data['buildings']:
        cols = sorted({(n - 1) % 32 for n in b['screens']}); rows = sorted({(n - 1) // 32 for n in b['screens']})
        c0, c1, r0, r1 = max(0, cols[0] - 1), min(31, cols[-1] + 1), max(0, rows[0] - 1), min(23, rows[-1] + 1)
        wd, hd = (c1 - c0 + 1) * 600, (r1 - r0 + 1) * 400
        walk = np.zeros((hd, wd), bool)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                m = walkable(r * 32 + c + 1)
                if m is not None: walk[(r - r0) * 400:(r - r0 + 1) * 400, (c - c0) * 600:(c - c0 + 1) * 600] = m
        scale = sum(mpp[n] for n in b['screens']) / len(b['screens'])
        rpx = max(1, int(round(radius_cm / (scale * 100.0))))
        lab, cnt = label_components(erode(walk, rpx))
        area = np.bincount(lab.ravel(), minlength=cnt + 1)
        ys, xs = np.mgrid[0:hd, 0:wd]; gx, gy = xs + c0 * 600, ys + r0 * 400
        rows_out.append('building %s (screens %s), capsule radius %d px' % (b['id'], ', '.join(map(str, b['screens'])), rpx))
        for hid in b['houses']:
            s = int(hid[1:4]); h = [h for h in town[str(s)]['houses'] if h['id'] == hid][0]
            core = np.zeros((hd, wd), bool); seeds = {}; cm = mpp[s] * 100.0
            for f in town[str(s)]['footprints']:      # the bodies cut from this wall run share its origin and yaw
                if abs(f['px'][0] - h['start_px'][0]) > 0.6 or abs(f['px'][1] - h['start_px'][1]) > 0.6 or abs(f['yaw'] - h['yaw']) > 0.1: continue
                ox, oy = gpx(s, *f['px']); a = math.radians(f['yaw']); c, si = math.cos(a), math.sin(a)
                x0, y0, x1, y1 = f['rect_cm']
                lx = ((gx - ox) * c + (gy - oy) * si) * cm; ly = (-(gx - ox) * si + (gy - oy) * c) * cm
                core |= (lx >= x0 + 60) & (lx <= x1 - 60) & (ly >= y0 + 60) & (ly <= y1 - 60)
                for px in np.arange(x0, x1 + 1.0, 100.0):      # 3 m in front of the front wall, every metre along it
                    x = int(round(ox + (px * c - (y1 + 300.0) * si) / cm)) - c0 * 600; y = int(round(oy + (px * si + (y1 + 300.0) * c) / cm)) - r0 * 400
                    if 0 <= x < wd and 0 <= y < hd and lab[y, x]: seeds[int(lab[y, x])] = seeds.get(int(lab[y, x]), 0) + 1
            if not seeds:
                rows_out.append('  house %s: no walkable point in front of it, not checked' % hid); bad += 1; continue
            main = max(seeds, key=lambda l: (seeds[l], area[l]))
            inside = float((core & (lab == main)).sum()) * mpp[s] ** 2
            ok = inside <= LIMIT_M2; bad += not ok
            other = ['%d front points in another walkable component of %.0f m2' % (seeds[l], area[l] * mpp[s] ** 2) for l in sorted(seeds, key=lambda l: -seeds[l]) if l != main]
            rows_out.append('  house %s: core %.0f m2; its street is %.0f m2 of walkable ground (%d of %d front points); %.1f m2 of the core lies in it -> %s%s' % (
                hid, float(core.sum()) * mpp[s] ** 2, area[main] * mpp[s] ** 2, seeds[main], sum(seeds.values()), inside, 'closed' if ok else 'CAN BE WALKED INTO',
                '; note: ' + ', '.join(other) + ' (ground behind or inside the building)' if other else ''))
    rows_out.append('%d houses checked: %s' % (sum(len(b['houses']) for b in data['buildings']), 'none can be walked into' if not bad else '%d fail' % bad))
    text = '\n'.join(rows_out) + '\n'
    if out: open(out, 'w').write(text)
    sys.stdout.write(text)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
