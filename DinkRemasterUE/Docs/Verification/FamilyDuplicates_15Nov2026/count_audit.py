"""Per dink.SceneAudit line (one screen), what draws each copy of the A208 pairs found in it: FamilyArt meshes (actor
component or instance) and visible cards. Usage: count_audit.py <pairs.csv> <audit.jsonl> [label]"""
import csv, json, sys, collections
pairs = [r for r in csv.DictReader(open(sys.argv[1])) if r['decision'] == 'pair']
origins = {o for r in pairs for o in (r['copy_a'], r['copy_b'])}
group = {}
for r in pairs:  # one group per object: every copy points at the copy that is kept for it
    for o in (r['copy_a'], r['copy_b']):
        k = r['dropped_for'].split(';')[0] if r['dropped_for'] else r['kept'].split(';')[0]
        group.setdefault(o, k or o)
label = sys.argv[3] if len(sys.argv) > 3 else ''
for line in open(sys.argv[2]):
    a = json.loads(line)
    mesh, card = collections.Counter(), collections.Counter()
    for p in a['prims']:
        cn = p.get('cn', '')
        hits = ([p['o']] if p.get('o') else []) + [i['o'] for i in p.get('is', []) or [] if i.get('o')]
        for o in hits:
            if o not in origins: continue
            if cn.startswith('FamilyArt'): mesh[o] += 1
            elif cn == 'Card' or cn.startswith('Decor_'): card[o] += 1
    objs = collections.defaultdict(list)
    for o in set(mesh) | set(card): objs[group[o]].append(o)
    for k, os_ in sorted(objs.items()):
        n = sum(mesh[o] + card[o] for o in os_)
        print(f"{label} screen {a['screen']}: object {k}: {n} drawn ({', '.join(f'{o} {mesh[o]} mesh {card[o]} card' for o in sorted(os_))})")
