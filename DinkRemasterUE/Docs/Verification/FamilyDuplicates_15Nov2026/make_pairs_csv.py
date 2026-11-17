"""Offline mirror of the A208 rule (DinkFamilyDuplicates.cpp) over ImportData/placements.json; writes the evidence CSV.
Usage: make_pairs_csv.py <ImportData dir> <visual-sweep audit.jsonl> <out.csv>. Rows: every same-class pair on different screens
within 1 m (the brief's measurement); decision = pair (one object) or why it stays two. Eligibility of the runtime
(family-bound, not scripted, &vision 0) is not mirrored: both_familyart_in_sweep marks pairs that master drew twice."""
import json, math, sys, collections, csv
B, AUDIT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(B + '/placements.json'))['placements']
drawn = collections.Counter()
for line in open(AUDIT):
    r = json.loads(line)
    for p in r['prims']:
        if not p.get('cn', '').startswith('FamilyArt'): continue
        if p.get('o'): drawn[p['o']] += 1
        for i in p.get('is', []) or []:
            if i.get('o'): drawn[i['o']] += 1
MAX_WORLD_CM, MAX_PX, SIZE_TOL = 100.0, 4.0, 0.05
def foot(p):  # where the family mesh stands: the card centre along local east, the placement's y
    return p['map_x'] + p['card']['offset_x_m'] / p['scale_x'], p['map_y']
def outside_px(p):
    x, y = foot(p)
    dx = max(0.0 - x, 0.0, x - 600.0); dy = max(0.0 - y, 0.0, y - 400.0)
    return math.hypot(dx, dy)
def gpx(p):
    n = p['screen'] - 1; x, y = foot(p); return ((n % 32) * 600 + x, (n // 32) * 400 + y)
def rank(p): return (outside_px(p), p['screen'], p['id'])
def size_px(p): return p['card']['width_m'] / p['scale_x']
by = collections.defaultdict(list)
for p in P:
    if p.get('class_id'): by[p['class_id']].append(p)
rows = []
for c, L in by.items():
    for i in range(len(L)):
        for j in range(i + 1, len(L)):
            a, b = L[i], L[j]
            if a['screen'] == b['screen']: continue
            d = math.dist(a['world'], b['world']) * 100
            if d >= MAX_WORLD_CM: continue
            if rank(b) < rank(a): a, b = b, a
            px = math.dist(gpx(a), gpx(b))
            same_pic = a['seq'] == b['seq'] and a['frame'] == b['frame']
            same_size = abs(size_px(a) / size_px(b) - 1) <= SIZE_TOL
            vision = bool(a['vision'] or b['vision'])
            pair = same_pic and same_size and px <= MAX_PX and not vision
            ina, inb = outside_px(a) == 0, outside_px(b) == 0
            case = 'one_inside' if ina != inb else ('both_inside' if ina else 'none_inside')
            why = 'pair' if pair else 'vision-gated copy (left alone)' if vision else ('offset %.1f px > %g' % (px, MAX_PX) if px > MAX_PX else ('picture differs' if not same_pic else 'size differs'))
            rows.append(dict(class_id=c, kept=a['id'] if pair else '', dropped=b['id'] if pair else '', copy_a=a['id'], copy_b=b['id'],
                screen_a=a['screen'], screen_b=b['screen'], rep_a=a['representation'], rep_b=b['representation'],
                outside_px_a=round(outside_px(a), 1), outside_px_b=round(outside_px(b), 1), case=case,
                world_cm=round(d, 1), map_px=round(px, 1), seq=a['seq'], frame=a['frame'],
                script_a=a['script'], script_b=b['script'],
                both_familyart_in_sweep=int(drawn[a['id']] > 0 and drawn[b['id']] > 0), decision=why))
rows.sort(key=lambda r: (r['decision'] != 'pair', r['class_id'], r['copy_a']))
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(rows)
cnt = collections.Counter((r['decision'] == 'pair', r['case']) for r in rows)
print(len(rows), dict(cnt))
print('pairs with both FamilyArt in sweep:', sum(1 for r in rows if r['decision'] == 'pair' and r['both_familyart_in_sweep']))
print('not pairs:', [(r['copy_a'], r['copy_b'], r['decision']) for r in rows if r['decision'] != 'pair'])
reps = collections.Counter((r['rep_a'], r['rep_b']) for r in rows if r['decision'] == 'pair'); print(reps)
# Greedy over the whole world, best rank first: a copy is dropped when a partner of it is already kept (as the C++).
partners = collections.defaultdict(set)
for r in rows:
    if r['decision'] == 'pair': partners[r['copy_a']].add(r['copy_b']); partners[r['copy_b']].add(r['copy_a'])
byid = {p['id']: p for p in P}
kept, dropped = set(), {}
for o in sorted(partners, key=lambda o: rank(byid[o])):
    k = sorted((q for q in partners[o] if q in kept), key=lambda q: rank(byid[q]))
    if k: dropped[o] = k[0]
    else: kept.add(o)
for r in rows:
    if r['decision'] != 'pair': continue
    a, b = r['copy_a'], r['copy_b']
    r['kept'] = ';'.join(x for x in (a, b) if x in kept); r['dropped'] = ';'.join(x for x in (a, b) if x in dropped)
    r['dropped_for'] = ';'.join(dropped[x] for x in (a, b) if x in dropped)
for r in rows: r.setdefault('dropped_for', '')
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(rows)
print('origins kept', len(kept), 'dropped', len(dropped), 'pair rows with both copies kept (chain ends)', sum(1 for r in rows if r['decision']=='pair' and not r['dropped']))
json.dump({'dropped': dropped, 'kept': sorted(kept)}, open(OUT.replace('.csv', '_dropped.json'), 'w'), indent=1)
for ex in ('S177_P04', 'S186_P02', 'S191_P12', 'S073_P01', 'S414_P02'):
    print([(r['kept'], r['dropped'], r['case'], r['rep_a'], r['rep_b'], r['both_familyart_in_sweep']) for r in rows if ex in (r['copy_a'], r['copy_b'])])
