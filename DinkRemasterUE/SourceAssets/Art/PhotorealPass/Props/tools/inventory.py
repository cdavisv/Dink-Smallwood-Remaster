"""Prop inventory for the photoreal pass: which prop sprite families are still placeholder (from Saved/Import/art_coverage.csv,
written by Scripts/art_coverage.py, joined with coverage.csv for the class id) and which stylised opening-cottage props need a
photoreal replacement.   python3 -I inventory.py   (from anywhere) -> Props/inventory.json (merged into Props/manifest.json by props_publish.py)"""
import csv, collections, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); PROPS = os.path.dirname(HERE)
P = os.path.abspath(os.path.join(PROPS, '..', '..', '..', '..'))
cov = {r['origin_id'] + '|' + r['type']: r for r in csv.DictReader(open(os.path.join(P, 'Saved', 'Import', 'coverage.csv')))}
rows = list(csv.DictReader(open(os.path.join(P, 'Saved', 'Import', 'art_coverage.csv'))))
classes = {}
for r in csv.DictReader(open(os.path.join(P, '..', 'tools', 'data', 'sprite_classes.csv'))):
    classes.setdefault(r['class_id'], r)
KINDS = ('prop', 'other')
cls = collections.defaultdict(lambda: dict(placeholder=0, final=0, cut=0, families=collections.Counter(), category='', name=''))
for r in rows:
    if r['art_kind'] not in KINDS or r['type'] != 'placement':
        continue
    d = cov.get(r['origin_id'] + '|' + r['type'], {}).get('detail', '')
    head = re.sub(r"\(type \d+\)", "", d.split(";")[0]).split()          # same parse as Scripts/art_coverage.py parse_detail
    cid = head[1] if len(head) > 1 else '?'
    c = cls[cid]; c[r['state']] += 1; c['families'][r['sprite_family']] += 1
    if cid in classes:
        c['category'] = classes[cid]['category']; c['name'] = classes[cid]['name']; c['pixel_size'] = classes[cid]['pixel_size']
out = []
for cid, c in sorted(cls.items(), key=lambda kv: -kv[1]['placeholder']):
    out.append({'class_id': cid, 'name': c['name'], 'category': c['category'], 'placeholder': c['placeholder'], 'final': c['final'], 'cut': c['cut'],
                'sprite_px': c.get('pixel_size', ''), 'sprite_families': dict(c['families'].most_common())})
old = json.load(open(os.path.join(P, 'SourceAssets', 'Art', 'Stonebrook', 'Export', 'manifest.json')))
cott = []
for a in old['assets']:
    if a['class'].startswith('prop'):
        b = a['bounds_cm']
        cott.append({'name': a['name'], 'class': a['class'], 'size_m': [round(x / 100, 3) for x in b['size_cm']], 'pivot': a['pivot_rule'], 'lod0_triangles': a['tris']['LOD0'],
                     'source': 'SourceAssets/Art/Stonebrook (stylised kit of screen 1); read-only reference'})
json.dump({'generated_from': 'Saved/Import/art_coverage.csv + coverage.csv + tools/data/sprite_classes.csv', 'scope': 'placements whose art_kind is prop or other', 'placeholder_prop_classes': out, 'opening_cottage_props': cott},
          open(os.path.join(PROPS, 'inventory.json'), 'w'), indent=1)
for o in out[:200]:
    print(o['placeholder'], o['final'], o['class_id'], o['category'], o['sprite_px'], list(o['sprite_families'])[:2])
print(len(out), sum(o['placeholder'] for o in out))
