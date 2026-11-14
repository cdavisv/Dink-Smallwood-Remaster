#!/usr/bin/env python3
"""Runtime check of the town houses against a log of the rendered game:
    python3 -I Scripts/PhotorealQA/town_log_check.py <game log> [--out report.txt]

UDinkEnvironmentSubsystem::ApplyTownHouses logs, per screen it dresses, how many kit modules it placed, how many it
could not (unknown mesh) and how many sprite cards it hid. The environment layer only runs in a process that renders,
so no headless automation test can see it; this compares those log lines of a capture run with
Content/Dink/Data/Art/town_houses.json: every module of the screen placed, none unknown, and exactly the cards of the
screen's `hide` lists hidden (each listed origin found once, as an actor card or as a decor instance).
Exit code 1 when a screen of the file is missing from the log or a count differs."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINE = re.compile(r'DINK ENV: town houses on screen (\d+): (\d+) modules placed \((\d+) of unknown mesh\), (\d+) sprite cards hidden')


def main():
    log = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    town = json.load(open(os.path.join(ROOT, 'Content/Dink/Data/Art/town_houses.json')))['screens']
    seen = {}
    for line in open(log, errors='replace'):
        m = LINE.search(line)
        if m: seen[int(m.group(1))] = tuple(int(m.group(i)) for i in (2, 3, 4))
    rows, bad = [], 0
    for key in sorted(town, key=int):
        modules = sum(len(h.get('modules') or []) for h in town[key]['houses'])
        hide = len({o for h in town[key]['houses'] for o in h.get('hide') or []})
        got = seen.get(int(key))
        ok = got == (modules, 0, hide)
        bad += not ok
        rows.append('screen %s: file %d modules, %d cards to hide; game %s -> %s' % (
            key, modules, hide, 'placed %d (%d unknown mesh), hid %d' % got if got else 'did not dress it', 'ok' if ok else 'MISMATCH'))
    rows.append('%d screens, %d modules, %d cards: %s' % (len(town), sum(len(h.get('modules') or []) for r in town.values() for h in r['houses']),
                                                        sum(len({o for h in r['houses'] for o in h.get('hide') or []}) for r in town.values()),
                                                        'all as the file says' if not bad else '%d screens differ' % bad))
    text = '\n'.join(rows) + '\n'
    if out: open(out, 'w').write(text)
    sys.stdout.write(text)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
