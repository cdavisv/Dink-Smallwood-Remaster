"""Download CC0 scan maps from Poly Haven into PhotorealPass/ThirdParty and log them in downloads.csv.

    python3 -I fetch_scan.py <asset_id> "<used_by>" [res=2k] [maps=diff,nor_gl,rough,ao]

Only polyhaven.com (CC0). Sends no project details: plain curl with its default user agent.
"""
import csv, hashlib, json, os, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TP = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'ThirdParty')
CSV = os.path.join(TP, 'downloads.csv')
HEADER = 'source,asset_id,asset_url,file,sha256,licence,author,resolution,used_by,date'.split(',')
KEYS = {'diff': 'Diffuse', 'nor_gl': 'nor_gl', 'rough': 'Rough', 'ao': 'AO', 'disp': 'Displacement', 'arm': 'arm'}


def curl(url, out=None):
    cmd = ['curl', '-fsL', '--proto', '=https', '-m', '300', url] + (['-o', out] if out else [])
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        raise SystemExit('curl failed %s: %s' % (url, r.stderr.decode()[:200]))
    return r.stdout


def main():
    aid = sys.argv[1]; used = sys.argv[2]; res = sys.argv[3] if len(sys.argv) > 3 else '2k'
    maps = (sys.argv[4] if len(sys.argv) > 4 else 'diff,nor_gl,rough,ao').split(',')
    files = json.loads(curl('https://api.polyhaven.com/files/' + aid))
    info = json.loads(curl('https://api.polyhaven.com/info/' + aid))
    author = '; '.join(sorted(info.get('authors', {}).keys()))
    d = os.path.join(TP, 'polyhaven', aid); os.makedirs(d, exist_ok=True)
    rows = list(csv.DictReader(open(CSV))) if os.path.exists(CSV) else []
    have = {r['file'] for r in rows}
    for m in maps:
        k = KEYS[m]
        if k not in files:
            print('no map', m, 'for', aid); continue
        e = files[k][res]; fmt = 'jpg' if 'jpg' in e else 'png'; url = e[fmt]['url']
        if not url.startswith('https://dl.polyhaven.org/'):
            raise SystemExit('unexpected host ' + url)
        name = os.path.basename(url); rel = 'polyhaven/%s/%s' % (aid, name); path = os.path.join(d, name)
        if not os.path.exists(path):
            curl(url, path)
        sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        if rel not in have:
            rows.append(dict(source='polyhaven', asset_id=aid, asset_url='https://polyhaven.com/a/' + aid, file=rel, sha256=sha, licence='CC0-1.0',
                             author=author, resolution=res, used_by=used, date=datetime.date.today().isoformat()))
        print('ok', rel)
    with open(CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, HEADER, lineterminator='\n'); w.writeheader(); w.writerows(rows)


main()
