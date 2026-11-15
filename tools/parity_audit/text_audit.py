"""Independent story-text audit: 1997 DinkC scripts vs the shipped Ink story and voice data.

The 1997 side is read straight from bin/dink/story/*.c with a small scanner of its own
(it does not use tools/dinkc), the remaster side straight from the shipped
DinkRemasterUE/Content/Dink/Data/Story/dink.json (it does not use tools/dinkink).

Usage: python3 -I text_audit.py <repo root> <out dir>
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

SAY = re.compile(r'\b(say_stop_npc|say_stop_xy|say_stop|say_xy|say)\s*\(\s*["\']([^"]*)"', re.I)
OPT = re.compile(r'^\s*((?:\([^"]*\)\s*)*)"([^"]*)"')
COLOUR = re.compile(r'^`.')
VAR = re.compile(r'&[A-Za-z0-9_\-]+')


def norm(text):
    text = text.replace(' ', ' ')
    text = COLOUR.sub('', text)
    text = VAR.sub('&V', text)
    return text.rstrip()


def scan_1997(story_dir):
    rows = []
    for name in sorted(os.listdir(story_dir)):
        if not name.lower().endswith('.c'):
            continue
        script = name[:-2].lower()
        with open(os.path.join(story_dir, name), encoding='latin-1') as f:
            lines = f.read().split('\n')
        in_choice = False
        in_title = False
        for no, raw in enumerate(lines, 1):
            line = raw.rstrip('\r')
            s = line.lstrip(' \t')
            if in_title:
                if re.match(r'title_end\b', s, re.I):
                    in_title = False
                else:
                    rows.append((script, no, 'title', '', line))
                continue
            if s.startswith('//'):
                continue
            if in_choice:
                if re.match(r'choice_end\b', s, re.I):
                    in_choice = False
                    continue
                if re.match(r'title_start\b', s, re.I):
                    in_title = True
                    continue
                m = OPT.match(s)
                if m:
                    rows.append((script, no, 'option', m.group(1).strip(), m.group(2)))
                continue
            if re.match(r'choice_start\b', s, re.I):
                in_choice = True
                continue
            m = SAY.search(s)
            if m:
                rows.append((script, no, m.group(1).lower(), '', m.group(2)))
    return rows


def walk_ink(story_json):
    """Return every output line of the compiled story as dicts: knot, text, tags."""
    root = story_json['root']
    out = []

    def walk(node, knot):
        if isinstance(node, list):
            cur, tags, in_tag, tag_buf, in_ev, ev_items = [], [], False, [], False, []
            in_str, str_buf, str_tags = False, [], []
            for item in node:
                if isinstance(item, str):
                    if item == '#':
                        in_tag, tag_buf = True, []
                    elif item == '/#':
                        in_tag = False
                        (str_tags if in_str else tags).append(''.join(tag_buf).strip())
                    elif in_tag and item.startswith('^'):
                        tag_buf.append(item[1:])
                    elif item == 'str' and in_ev:
                        in_str, str_buf, str_tags = True, [], []
                    elif item == '/str' and in_ev:
                        in_str = False
                        out.append({'knot': knot, 'text': ''.join(str_buf), 'tags': str_tags, 'option': True})
                    elif in_ev and in_str:
                        if item.startswith('^'):
                            (tag_buf if in_tag else str_buf).append(item[1:])
                    elif item == 'ev':
                        in_ev, ev_items = True, []
                    elif item == '/ev':
                        in_ev = False
                        if 'out' in ev_items:
                            cur.append('&V')
                    elif in_ev:
                        ev_items.append(item)
                    elif item.startswith('^'):
                        cur.append(item[1:])
                    elif item == '\n':
                        text = ''.join(cur)
                        if text.strip() or tags:
                            out.append({'knot': knot, 'text': text, 'tags': tags})
                        cur, tags = [], []
                elif isinstance(item, (list, dict)):
                    if in_ev:
                        ev_items.append('x')
                        continue
                    # a choice's text container ("s") carries the text and the #opt tag
                    walk(item, knot)
            text = ''.join(cur)
            if text.strip() or tags:
                out.append({'knot': knot, 'text': text, 'tags': tags, 'open': True})
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in ('#f', '#n'):
                    continue
                walk(v, k[2:] if (k.startswith('d_') and knot is None) else knot)

    top = root[-1]
    if isinstance(top, dict):
        for k, v in top.items():
            if k.startswith('d_'):
                walk(v, k[2:])
    return out


def main():
    repo, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    rows = scan_1997(os.path.join(repo, 'bin/dink/story'))
    story = json.load(open(os.path.join(repo, 'DinkRemasterUE/Content/Dink/Data/Story/dink.json'), encoding='utf-8'))
    ink = walk_ink(story)
    names = {}
    # Ink knot names: d_<script> with - and . replaced? read the converter's names table
    with open(os.path.join(repo, 'DinkRemasterUE/Content/Dink/Data/Story/names.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            names.setdefault(r.get('ink', ''), r.get('dinkc', ''))
    by_key = defaultdict(list)
    by_text = defaultdict(list)
    by_script_text = defaultdict(list)
    by_scr = defaultdict(list)
    for e in ink:
        src = next((t[4:] for t in e['tags'] if t.startswith('src:')), None)
        lid = next((t.split(':', 1)[1] for t in e['tags'] if t.startswith('id:') or t.startswith('opt:')), None)
        if lid is None:
            lid = next((t[4:] for t in e['tags'] if t.startswith('opt:')), None)
        script = (lid.split('.')[0] if lid else None)
        e['script'], e['src'], e['id'] = script, src, lid
        if script and src:
            by_key[(script, int(src))].append(e)
        by_text[norm(e['text'])].append(e)
        sc = lid.split('.')[0] if lid else e['knot']
        by_script_text[(sc, norm(e['text']))].append(e)
        by_scr[sc].append(e)
    results = []
    for script, no, kind, cond, text in rows:
        n = norm(text)
        cands = by_key.get((script, no), [])
        if kind in ('option', 'title'):
            cands = [e for e in by_script_text.get((script, n), [])]
            if not cands:
                cands = [e for e in by_scr.get(script, []) if e.get('option') == (kind == 'option')]
        texts = [norm(c['text']) for c in cands]
        if kind == 'option' and re.search(r'&(savegameinfo|buttoninfo)', text):
            # the engine fills these in at run time (save slot description, button binding): the remaster's
            # Ink calls the same functions ({savegameinfo(n)}), so there is no literal text to compare
            status = 'engine-function'
        elif n in texts:
            status = 'same' if len(set(texts)) == 1 else 'same+variant'
        elif cands:
            status = 'differs'
        elif n in by_text:
            status = 'same-text-elsewhere'
        elif not n.strip():
            status = 'empty'
        else:
            status = 'missing'
        results.append({'script': script, 'line': no, 'kind': kind, 'cond': cond, 'text_1997': text,
                        'status': status, 'ink_ids': ' '.join(sorted({c['id'] or '' for c in cands})),
                        'ink_texts': ' || '.join(sorted(set(c['text'].replace(' ', ' ') for c in cands)))})
    with open(os.path.join(outdir, 'text_audit.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    count = defaultdict(int)
    for r in results:
        count[(r['kind'] if r['kind'] in ('option', 'title') else 'say', r['status'])] += 1
    print('1997 lines scanned:', len(results), ' ink output lines:', len(ink))
    for k in sorted(count):
        print(k, count[k])
    # ink spoken lines with no 1997 counterpart
    keys97 = {(s, n) for s, n, *_ in rows}
    extra = [e for e in ink if e['id'] and e['src'] and (e['script'], int(e['src'])) not in keys97
             and any(t.startswith(('id:', 'opt:')) for t in e['tags'])]
    with open(os.path.join(outdir, 'ink_extra.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id', 'src', 'text'])
        for e in extra:
            w.writerow([e['id'], e['src'], e['text']])
    print('ink lines with an id and no 1997 line at that script:line:', len(extra))


if __name__ == '__main__':
    main()
