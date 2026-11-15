"""Gore placements of the 1997 maps (blood, burns, corpses, heads, bones, skulls) and how the remaster draws them.

Joins tools/dinkex/out/screens (the placements), tools/data/sprite_classes.csv (the class of each picture),
DinkRemasterUE/Saved/gore_cov.csv (Scripts/art_coverage.py --out Saved/gore_cov.csv: final / placeholder and the
evidence) and, when present, DinkRemasterUE/ImportData/placements.json (the importer's card size in metres).
Usage: python3 -I tools/parity_audit/gore_placements.py <repo root> <out csv>
"""
import csv, json, glob, os, sys, re
repo = sys.argv[1]; out = sys.argv[2]
cls = {(r['seq'], r['frame']): r for r in csv.DictReader(open(os.path.join(repo, 'tools/data/sprite_classes.csv')))}
cov = {r['origin_id']: r for r in csv.DictReader(open(os.path.join(repo, 'DinkRemasterUE/Saved/gore_cov.csv')))}
GORE = set('blood_splat duck_head duck_corpse pillbug_corpse burn_hole_decal burn_damage_decal burnt_floor_hole dragon_corpse corpse_maiden corpse_knight corpse_girl corpse_merchant corpse_mom corpse_soldier corpse_peasant dink_dead bones skull'.split())
rows = []
for f in sorted(glob.glob(os.path.join(repo, 'tools/dinkex/out/screens/SCR_*.json'))):
    d = json.load(open(f))
    for p in d['placements']:
        c = cls.get((str(p['seq']), str(p['frame'])))
        if not c or c['class_id'] not in GORE: continue
        cv = cov.get(p['id'], {})
        pic = p.get('pic') or {}
        # card size in metres at the screen's scale is in the importer; report pixels
        rows.append(dict(origin=p['id'], screen=d['screen'], seq=p['seq'], frame=p['frame'], cls=c['class_id'], kind=p['kind'], vision=p['vision'], size=p['size'],
                         px=f"{pic.get('width')}x{pic.get('height')}", state=cv.get('state',''), evidence=cv.get('evidence','')[:160], name=d.get('name','')))
imp = os.path.join(repo, 'DinkRemasterUE/ImportData/placements.json')
if os.path.exists(imp):
    cards = {p['id']: p for p in json.load(open(imp))['placements']}
    for r in rows:
        p = cards.get(r['origin'], {})
        c = p.get('card') or {}
        r['card_w_m'], r['card_h_m'], r['repr'] = c.get('width_m', ''), c.get('height_m', ''), p.get('representation', '')
w = csv.DictWriter(open(out, 'w', newline=''), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows)); print(Counter((r['cls'], r['state']) for r in rows))
