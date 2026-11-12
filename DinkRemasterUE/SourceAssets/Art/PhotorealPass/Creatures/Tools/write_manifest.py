"""Writes Creatures/manifest.json: the stream inventory plus one entry per delivered creature (entries live in entries/<Name>.json).
usage: python3 -I write_manifest.py   (run from anywhere; art_coverage.csv must exist: python3 -I Scripts/art_coverage.py from the project root)"""
import csv, json, collections, hashlib
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parents[1]; ART = OUT.parents[1]; PROJ = ART.parents[1]; REPO = PROJ.parent
rows = list(csv.DictReader(open(PROJ / 'Saved/Import/art_coverage.csv')))
cls = {}
for r in csv.DictReader(open(REPO / 'tools/data/sprite_classes.csv')): cls.setdefault(r['seq'], r['class_id'])
fam = collections.defaultdict(collections.Counter)
for r in rows:
    if r['art_kind'] == 'creature': fam[r['sprite_family']][r['state']] += 1
byclass = collections.defaultdict(collections.Counter); families = []
for f, c in sorted(fam.items(), key=lambda t: -t[1].get('placeholder', 0)):
    seq = f.split()[0]; cid = cls.get(seq, '?'); byclass[cid].update(c)
    families.append({'sprite_family': f, 'class_id': cid, **{k: c.get(k, 0) for k in ('placeholder', 'final', 'cut')}})
creatures = json.load(open(PROJ / 'Content/Dink/Data/Art/creatures.json'))
bound = collections.Counter(p['mesh'].split('.')[-1] for p in creatures.get('placements', []))
inventory = {
    'generated_from': ['Saved/Import/art_coverage.csv (Scripts/art_coverage.py)', 'Content/Dink/Data/Art/creatures.json', 'tools/data/sprite_classes.csv'],
    'existing_sources': [
        {'asset': 'SK_Pillbug', 'path': 'SourceAssets/Art/Creatures/Pillbug', 'rig': '43 bones: root, pelvis, tergite_01..07, tail, head, leg_NN_upper/lower_l/r (14 two-bone legs), antenna_01/02_l/r', 'clips': ['Pillbug_Idle', 'Pillbug_Walk', 'Pillbug_Run'], 'fps': 40, 'imported': True, 'look': 'stylised (flat turquoise plates, ochre rims)'},
        {'asset': 'SK_Pig', 'path': 'SourceAssets/Art/Creatures/Pig', 'rig': '26 bones: root, pelvis, spine_01..03, neck_01..02, head, jaw, ear_l/r, upperarm/lowerarm/hand_l/r, thigh/calf/foot_l/r, tail_01..03', 'clips': ['Pig_Idle', 'Pig_Walk', 'Pig_Run', 'Pig_Feed'], 'fps': 30, 'imported': True, 'look': 'stylised (smooth pale toy pig)'},
        {'asset': 'SK_Duck (+ SK_Duck_Headless, SM_Duck_Head)', 'path': 'SourceAssets/Art/Creatures/Duck (untracked candidate)', 'rig': '23 bones: root, pelvis, spine_01..02, neck_01..03, head, jaw, wing/wingtip_l/r, tail_01..02, thigh/calf/foot/toes_l/r', 'clips': ['Duck_Idle', 'Duck_Walk', 'Duck_Run', 'Duck_Peck', 'Duck_Quack', 'Duck_Hit', 'Duck_Death', 'Duck_HeadlessRun', 'Duck_HeadlessDeath'], 'fps': 30, 'imported': False, 'look': 'stylised candidate, never imported'}],
    'runtime_binding': 'Content/Dink/Data/Art/creatures.json (schema dink-creatures/1): `assets` (mesh, skeleton, animation_reports, body_boxes, locomotion blendspace) and `placements` (origin -> mesh). Written by Scripts/import_creature_art.sh from each creature source manifest; UDinkCreatureSubsystem attaches the mesh to the existing actor. See Scripts/ART_PIPELINE.md "Pig pen and own-rig creatures".',
    'placements_bound_today': dict(bound),
    'placeholder_by_class': [{'class_id': k, **{s: v.get(s, 0) for s in ('placeholder', 'final', 'cut')}} for k, v in sorted(byclass.items(), key=lambda t: -t[1].get('placeholder', 0))],
    'placeholder_by_sprite_family': families,
}
entries = {}
for p in sorted((OUT / 'entries').glob('*.json')) if (OUT / 'entries').exists() else []:
    e = json.loads(p.read_text())
    for t in e.get('textures', []):
        q = OUT / e['folder'] / t['file']
        if q.exists():
            t['px'] = list(Image.open(q).size); t['sha256'] = hashlib.sha256(q.read_bytes()).hexdigest()[:16]
        else: t['missing'] = True
    entries[e['asset']] = e
man = {'schema': 'dink-photoreal-creatures/1', 'date': '2026-11-12', 'stream': 'PhotorealPass/Creatures', 'contact_sheet': 'contact_sheet.png', 'tools': 'Tools/ (crlib.py shared; one script per creature; stages look/final/review/export)',
       'inventory': inventory, 'creatures': entries}
(OUT / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n'); print('manifest written:', len(entries), 'creatures;', sum(f['placeholder'] for f in families), 'placeholder creature placements in', len(families), 'families')
