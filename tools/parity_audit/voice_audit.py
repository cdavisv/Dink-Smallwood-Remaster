"""Voice audit: every spoken line of the story against what plays (voice.json) and the exact text sent to the speech
model (SourceAssets/Audio/Voice/*_manifest.json `tts_text`). Words must match after stage directions and model tags are
removed. Needs tools/dinkink/out/line_ids.csv. Usage: python3 -I tools/parity_audit/voice_audit.py <repo root> <out dir>
"""
import csv, glob, json, os, re, sys
repo, out = sys.argv[1], sys.argv[2]
V = os.path.join(repo, 'DinkRemasterUE/SourceAssets/Audio/Voice')
ink = {}
for r in csv.DictReader(open(os.path.join(repo, 'tools/dinkink/out/line_ids.csv'), encoding='utf-8')):
    if r['kind'] == 'spoken':
        ink[r['id']] = r['text']
voice = json.load(open(os.path.join(repo, 'DinkRemasterUE/Content/Dink/Data/Audio/voice.json')))['lines']
gen = {}
for m in glob.glob(os.path.join(V, '*_manifest.json')):
    d = json.load(open(m))
    ls = list(d.get('lines', []))
    for vv in (d.get('voices') or {}).values():
        ls += vv.get('lines', [])
    for l in ls:
        gen.setdefault(l['id'], []).append((os.path.basename(m), l.get('text', ''), l.get('tts_text', ''), l.get('file', '')))
vl = {r['id']: r for r in csv.DictReader(open(os.path.join(V, 'voice_lines.csv'), encoding='utf-8'))}
def words(s):
    s = re.sub(r'\[[^\]]*\]', ' ', s)      # ElevenLabs tags
    s = re.sub(r'<[^>]*>', ' ', s)         # 1997 stage directions
    s = re.sub(r'&[A-Za-z0-9_\-]+|<N>', ' ', s)
    s = s.replace('`', '')
    return re.findall(r"[a-z0-9']+", s.lower())
rows = []
for i, t in sorted(ink.items()):
    v = voice.get(i)
    g = gen.get(i, [])
    k = vl.get(i, {}).get('kind', '')
    if not v:
        status = 'unvoiced-' + (k or 'unknown')
    elif not g:
        same = [j for j, gg in gen.items() if voice.get(j, {}).get('voice') == v['voice'] and words(gg[-1][2] or gg[-1][1]) == words(t)]
        status = 'voiced-copy-of-identical-text' if same else 'voiced-no-manifest'
    else:
        _, gt, tt, f = g[-1]
        sent = tt or gt
        if words(sent) == words(t):
            status = 'voiced-text-match'
        else:
            status = 'voiced-TEXT-DIFFERS'
    rows.append({'id': i, 'status': status, 'text': t, 'tts_sent': (g[-1][2] or g[-1][1]) if g else '', 'asset': v['asset'] if v else ''})
extra = sorted(set(voice) - set(ink))
w = csv.DictWriter(open(os.path.join(out, 'voice_audit.csv'), 'w', newline='', encoding='utf-8'), fieldnames=list(rows[0]))
w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter(r['status'] for r in rows)); print('voice ids not in story:', len(extra), extra[:5])
for r in rows:
    if r['status'] in ('voiced-TEXT-DIFFERS', 'voiced-no-manifest'): print(r['id'], '|', r['text'], '|', r['tts_sent'])
