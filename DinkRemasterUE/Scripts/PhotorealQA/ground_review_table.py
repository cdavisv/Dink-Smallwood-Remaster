#!/usr/bin/env python3
"""The screen-ground review as tables (Markdown on stdout):
    python3 -I Scripts/PhotorealQA/ground_review_table.py

Reads Content/Dink/Data/Environment/ground_classes.json (what each screen's ground is made of, written by the world
export) and ground_review.json (the verdicts of the in-game review) and applies Scripts/art_coverage.py
screen_ground_state() to every screen, assuming every texture exists (art_coverage.py itself checks the assets).
Prints: the verdict per tile class with the screens that were looked at; how many screens each reason keeps open;
the screens that count final."""
import collections, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'Scripts'))
from art_coverage import screen_ground_state    # noqa: E402


def main():
    env = os.path.join(ROOT, 'Content', 'Dink', 'Data', 'Environment')
    facts = json.load(open(os.path.join(env, 'ground_classes.json')))['screens']
    review = json.load(open(os.path.join(env, 'ground_review.json')))
    use = collections.defaultdict(list)
    for number, row in facts.items():
        for cls in row['classes']:
            use[(cls, 'indoor' if row['indoor'] else 'outdoor')].append(int(number))
    print('| Tile class | Where | Screens | Verdict | Looked at (screens) | Why |')
    print('|---|---|---:|---|---|---|')
    for (cls, where), screens in sorted(use.items(), key=lambda kv: (kv[0][1], -len(kv[1]), kv[0][0])):
        v = (review['classes'].get(cls) or {}).get(where)
        if v is None:
            print('| %s | %s | %d | not reviewed | | no screen of it was captured |' % (cls, where, len(screens)))
        else:
            print('| %s | %s | %d | %s | %s | %s |' % (cls, where, len(screens), v['verdict'], ', '.join(str(s) for s in v['seen']), v.get('reason') or v.get('note', '')))
    states, reasons, final = collections.Counter(), collections.Counter(), []
    for number, row in sorted(facts.items(), key=lambda kv: int(kv[0])):
        state, evidence = screen_ground_state(row, review, lambda path: (True, ''))
        finding = (review.get('screens') or {}).get(number)
        if state == 'final' and finding and finding.get('verdict') != 'pass':
            state, evidence = 'placeholder', 'not final: this screen in the review'
        states[state] += 1
        if state == 'final':
            final.append(int(number))
            continue
        for reason in evidence.split('not final: ', 1)[-1].split('; '):
            key = reason.split(' (')[0] if reason.startswith('tile class') else 'a layer the mask cannot carry' if reason.startswith('layer ') else \
                'water tiles without a water surface' if 'water tiles without' in reason else reason
            reasons[key] += 1
    print('\n%d screens: %d final, %d placeholder (before the screens an art manifest dresses are taken out).\n' % (len(facts), states['final'], states['placeholder']))
    print('| Reason a screen stays placeholder | Screens |')
    print('|---|---:|')
    for key, n in reasons.most_common():
        print('| %s | %d |' % (key, n))
    print('\nFinal screens: ' + ', '.join(str(n) for n in final))


if __name__ == '__main__':
    main()
