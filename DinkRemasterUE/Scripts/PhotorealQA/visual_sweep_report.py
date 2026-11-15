#!/usr/bin/env python3
"""Detectors and contact sheets for a visual sweep (see visual_sweep.py).

    python3 -I Scripts/PhotorealQA/visual_sweep_report.py <out dir> [--log=<game log>] [--sheets=<dir>] [--per-sheet=20]

Reads <out dir>/sweep_index.json, NNN_play.png / NNN_over.png and audit.jsonl; writes into <out dir>:
  detectors.csv     one row per screen: frame luma (mean, 5th/95th percentile, near-black and clipped shares), magenta
                    share, and from the scene audit: primitives with an engine default material (WorldGrid, default,
                    basic-shape), empty/default texture parameters, script-sprite placeholder markers, visible sprite
                    cards next to photoreal meshes, props floating above or sunk into what lies under them, coplanar
                    flat meshes (z-fighting candidates), faceted meshes, local lights
  findings.json     the detector hits with the primitive, mesh and material behind each
  meshes.csv        every static mesh seen, with LOD0 counts, hard-vertex share and the screens it is on
  log_findings.txt  material, texture, Nanite and Dink warnings/errors of the game log, counted
  sheets/           contact sheets (jpg): play_NN.jpg and over_NN.jpg, --per-sheet screens each, labelled
Needs Pillow and numpy."""
import collections, csv, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# meshes that hang on walls or ceilings or sit on roofs by design: never "floating"
HUNG = ('Hanging', 'Torch_Wall', 'Roof', 'Chimney', 'Gable', 'Sconce', 'Ceiling', 'Beam', 'Rafter', 'Lamp_Wall', '/Engine/BasicShapes/Plane', 'Cloud', 'Bird')
GROUND_WORDS = ('terrain', 'meadow', 'ground', 'floor', 'earth', 'sand', 'snow', 'turf', 'grass', 'dirt', 'path', 'mud', 'cobble', 'plank', 'water', 'ice', 'rock_floor', 'cave')


def font(size):
    for f in ('/usr/share/fonts/TTF/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf', '/usr/share/fonts/noto/NotoSans-Regular.ttf'):
        if os.path.exists(f): return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def frame_stats(path):
    im = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0
    luma = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    magenta = (r > 0.7) & (b > 0.7) & (g < 0.3)
    return {'mean': float(luma.mean()), 'p5': float(np.percentile(luma, 5)), 'p95': float(np.percentile(luma, 95)),
            'black': float((luma < 0.03).mean()), 'clip': float((luma > 0.98).mean()), 'magenta': float(magenta.mean())}


def groundlike(hit):
    z, actor, comp, mat = hit
    m = (mat or '').lower()
    return actor == 'DinkGreyboxScreen' or any(w in m for w in GROUND_WORDS)


def is_card(p):
    """A 1997 sprite picture on a flat card (placeholder card or instanced background card)."""
    return 'DinkCard' in (p.get('mesh') or '').rsplit('/', 1)[-1]


def is_photoreal(p):
    """Authored 3D art: a mesh of the project that is not a sprite card or generated greybox geometry."""
    mesh = p.get('mesh') or ''
    return mesh.startswith('/Game/Dink/') and not is_card(p) and '/_Generated/' not in mesh


def support_gap(minz, maxz, hits):
    """(gap below the bottom, sunk depth) against the first ground-like surface; None when nothing ground-like lies under it."""
    grey = [x[0] for x in hits if x[1] == 'DinkGreyboxScreen']
    # the greybox screen's collision is a ground plane plus 3 m prisms over the hardness: a prism top is not ground
    plane = min(grey) if len(grey) > 1 else (grey[0] if grey and grey[0] <= minz + 150.0 else None)
    hits = [x for x in hits if x[1] != 'DinkGreyboxScreen' or (plane is not None and x[0] <= plane + 1.0)]
    ground = [x for x in hits if groundlike(x)]
    if not ground: return None
    top = ground[0][0]
    if top > minz + 2.0: return (0.0, top - minz)      # the ground surface passes above the bottom: sunk by this much
    under = [x for x in hits if x[0] <= minz + 2.0]
    first = under[0][0] if under else top            # a non-ground support (table, floor mesh) right under it counts
    return (minz - first, 0.0)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0])
    opt = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    per = int(opt.get('per-sheet') or 20)
    index = json.load(open(os.path.join(out, 'sweep_index.json')))
    # one audit line per screen, written in the order of the index: the line's own screen number says where the player
    # really stood (a refused teleport leaves him on the previous screen; that screen is then "not captured")
    lines = []
    if os.path.exists(os.path.join(out, 'audit.jsonl')):
        for line in open(os.path.join(out, 'audit.jsonl'), encoding='utf-8', errors='replace'):
            try: lines.append(json.loads(line))
            except ValueError: pass
    audit, stood = {}, {}
    for s, row in zip(index, lines):
        stood[s['screen']] = row['screen']
        if row['screen'] == s['screen']: audit[s['screen']] = row
    findings = collections.defaultdict(list)
    meshes = {}
    rows = []
    for s in index:
        n = s['screen']
        rec = {'screen': n, 'region': s['region'], 'kind': s['kind'], 'indoor': int(s['indoor']), 'reached': int(s['reached'])}
        for view in ('play', 'over'):
            f = os.path.join(out, '%03d_%s.png' % (n, view))
            if os.path.exists(f):
                st = frame_stats(f)
                for k, v in st.items(): rec['%s_%s' % (view, k)] = round(v, 4)
            else:
                rec['%s_mean' % view] = ''
        a = audit.get(n)
        rec['captured'] = int(stood.get(n) == n)
        if n in stood and stood[n] != n:
            findings[n].append({'what': 'not captured: the teleport was refused, the player stayed on screen %d' % stood[n]})
        cnt = collections.Counter()
        if a:
            prims = a['prims']
            photoreal = [p for p in prims if is_photoreal(p)]
            for p in prims:
                label = {'a': p['a'], 'o': p.get('o', ''), 'cn': p['cn'], 'mesh': p.get('mesh', ''), 'mats': [m.get('m') for m in p.get('mats', [])]}
                if p.get('default'):
                    cnt['default_mat'] += 1; findings[n].append(dict(label, what='engine default material'))
                if any(m.get('badtex') for m in p.get('mats', [])):
                    cnt['bad_tex'] += 1; findings[n].append(dict(label, what='empty/default texture: ' + ';'.join(m['badtex'] for m in p['mats'] if m.get('badtex'))))
                if p['a'] == 'DinkScriptSpriteActor':
                    cnt['script_marker'] += 1; findings[n].append(dict(label, what='script-sprite placeholder marker'))
                card = is_card(p)
                if card: cnt['cards'] += p.get('inst', 1) if p['c'].endswith('InstancedStaticMeshComponent') else 1
                mesh = p.get('mesh') or ''
                if mesh and p['c'] != 'SkeletalMeshComponent':
                    m = meshes.setdefault(mesh, {'mesh': mesh, 'v': p.get('v', 0), 't': p.get('t', 0), 'hard': p.get('hard', -1), 'facet': p.get('facet', -1), 'nanite': p.get('nanite', 0), 'screens': set(), 'uses': 0})
                    m['screens'].add(n); m['uses'] += p.get('inst', 1)
                # floating / sunk (props only: not cards, not ground and not huge pieces)
                minz, maxz = p['min'][2], p['max'][2]
                ext = [p['max'][i] - p['min'][i] for i in range(3)]
                hung = any(w in (p.get('mesh') or '') for w in HUNG)
                if not card and not hung and p['a'] not in ('DinkGreyboxScreen', 'DinkScriptSpriteActor') and max(ext[0], ext[1]) < 2500 and ext[2] > 8:
                    items = p.get('is') or [{'o': p.get('o', ''), 'min': p['min'], 'max': p['max'], 'g': p.get('g', [])}]
                    for it in items:
                        g = support_gap(it['min'][2], it['max'][2], it.get('g', []))
                        if not g: continue
                        h = it['max'][2] - it['min'][2]
                        gap, sunk = g
                        if gap > max(8.0, 0.08 * h):
                            cnt['floating'] += 1; findings[n].append(dict(label, o=it.get('o') or label['o'], what='floating %.0f cm above the surface under it (height %.0f cm)' % (gap, h)))
                        elif sunk > max(25.0, 0.45 * h):
                            cnt['sunk'] += 1; findings[n].append(dict(label, o=it.get('o') or label['o'], what='sunk %.0f cm into the surface (height %.0f cm)' % (sunk, h)))
                if p.get('facet', -1) >= 0.3 and p.get('v', 0) > 24 and not card:
                    cnt['faceted'] += 1
            if photoreal and cnt['cards']:
                findings[n].append({'what': '%d sprite cards visible next to %d photoreal meshes' % (cnt['cards'], len(photoreal))})
            # z-fighting candidates: two flat meshes whose tops lie within 0.3 cm and whose footprints overlap
            flats = [p for p in prims if p['max'][2] - p['min'][2] < 3.0 and not is_card(p)]
            for i in range(len(flats)):
                for j in range(i + 1, len(flats)):
                    a1, b1 = flats[i], flats[j]
                    if abs(a1['max'][2] - b1['max'][2]) > 0.3: continue
                    ox = min(a1['max'][0], b1['max'][0]) - max(a1['min'][0], b1['min'][0])
                    oy = min(a1['max'][1], b1['max'][1]) - max(a1['min'][1], b1['min'][1])
                    if ox > 20 and oy > 20:
                        cnt['zfight'] += 1
                        findings[n].append({'what': 'coplanar overlap (z-fighting candidate) %s / %s' % (a1['cn'], b1['cn']), 'mesh': a1.get('mesh'), 'mesh2': b1.get('mesh')})
            rec.update(prims=len(prims), photoreal=len(photoreal), lights=len(a.get('lights', [])),
                       local_lights=sum(1 for l in a.get('lights', []) if 'Directional' not in l['c'] and 'Sky' not in l['c']))
        for k in ('default_mat', 'bad_tex', 'script_marker', 'cards', 'floating', 'sunk', 'zfight', 'faceted'): rec[k] = cnt[k]
        if rec.get('play_mean', '') != '' and rec['captured']:
            if rec['play_mean'] < 0.10: findings[n].append({'what': 'play frame dark: mean luma %.3f' % rec['play_mean']})
            if rec['play_clip'] > 0.08: findings[n].append({'what': 'play frame blown: %.0f%% clipped' % (100 * rec['play_clip'])})
            if rec['play_magenta'] > 0.003: findings[n].append({'what': 'magenta pixels %.2f%%' % (100 * rec['play_magenta'])})
        rows.append(rec)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(os.path.join(out, 'detectors.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    json.dump({str(k): v for k, v in sorted(findings.items())}, open(os.path.join(out, 'findings.json'), 'w'), indent=1)
    with open(os.path.join(out, 'meshes.csv'), 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['mesh', 'lod0_vertices', 'lod0_triangles', 'hard_vertex_share', 'facet_vertex_share', 'nanite', 'uses', 'screens'])
        for m in sorted(meshes.values(), key=lambda m: (-m['facet'], -m['hard'], m['mesh'])):
            w.writerow([m['mesh'], m['v'], m['t'], m['hard'], m['facet'], m['nanite'], m['uses'], ' '.join(str(x) for x in sorted(m['screens']))])
    if opt.get('log') and os.path.exists(opt['log']):
        pat = re.compile(r'(Failed to compile Material|missing usage flag|Default Material will be used|Nanite|LogTexture.*(Error|Warning)|LogMaterial.*(Error|Warning)|LogDink.*(Error|Warning)|LogStaticMesh.*(Error|Warning)|Error: )')
        counts = collections.Counter()
        for line in open(opt['log'], errors='replace'):
            if pat.search(line):
                key = re.sub(r'^\[[^\]]*\]\[[ 0-9]*\]', '', line.strip())
                key = re.sub(r'\d+(\.\d+)?', '#', key)[:300]
                counts[key] += 1
        with open(os.path.join(out, 'log_findings.txt'), 'w') as f:
            for k, v in counts.most_common(): f.write('%6d  %s\n' % (v, k))
    # contact sheets
    sheets = opt.get('sheets') or os.path.join(out, 'sheets')
    os.makedirs(sheets, exist_ok=True)
    W, H, BAR, PAD, COLS = 320, 180, 16, 4, 5
    fnt = font(11)
    flag = {r['screen']: r for r in rows}
    for view in ('play', 'over'):
        for k in range(0, len(index), per):
            chunk = index[k:k + per]
            rws = (len(chunk) + COLS - 1) // COLS
            sheet = Image.new('RGB', (COLS * (W + PAD) + PAD, rws * (H + BAR + PAD) + PAD), (20, 20, 20))
            d = ImageDraw.Draw(sheet)
            for i, s in enumerate(chunk):
                x = PAD + (i % COLS) * (W + PAD); y = PAD + (i // COLS) * (H + BAR + PAD)
                n = s['screen']; r = flag[n]
                marks = ''.join(c for c, key in (('D', 'default_mat'), ('S', 'script_marker'), ('F', 'floating'), ('K', 'sunk'), ('Z', 'zfight')) if r.get(key))
                d.text((x + 2, y + 2), '%03d %s %s %s' % (n, s['region'][:14], s['kind'][:4], marks), fill=(235, 235, 235), font=fnt)
                f = os.path.join(out, '%03d_%s.png' % (n, view))
                if os.path.exists(f): sheet.paste(Image.open(f).convert('RGB').resize((W, H), Image.LANCZOS), (x, y + BAR))
                else: d.text((x + 100, y + 80), 'no frame', fill=(200, 80, 80), font=fnt)
            sheet.save(os.path.join(sheets, '%s_%02d.jpg' % (view, k // per + 1)), quality=82)
    tot = collections.Counter()
    for r in rows:
        for key in ('default_mat', 'bad_tex', 'script_marker', 'floating', 'sunk', 'zfight', 'faceted'): tot[key] += 1 if r.get(key) else 0
    print('%d screens, %d audited, screens with: %s' % (len(rows), len(audit), ', '.join('%s %d' % kv for kv in sorted(tot.items()))))
    print('sheets ->', sheets)


if __name__ == '__main__':
    main()
