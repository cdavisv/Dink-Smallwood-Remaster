"""Fetch CC0 scans (Poly Haven / ambientCG) into PhotorealPass/ThirdParty and append the ledger. Run: python3 -I fetch_scans.py"""
import subprocess, json, os, hashlib, zipfile, datetime, csv, io, sys, re
TP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ThirdParty'))
LEDGER = os.path.join(TP, 'downloads.csv')
DATE = '2026-11-11'
def curl(url, out=None):
    cmd = ['curl', '-fsL', '--proto', '=https', url]
    if out: cmd += ['-o', out]
    r = subprocess.run(cmd, capture_output=not out)
    if r.returncode: raise SystemExit(f'curl failed {url}')
    return r.stdout
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def ledger(rows):
    buf = io.StringIO(); w = csv.writer(buf, lineterminator='\n')
    for r in rows: w.writerow(r)
    with open(LEDGER, 'a') as f: f.write(buf.getvalue())
def polyhaven(aid, maps, used_by, res='2k'):
    d = os.path.join(TP, 'polyhaven', aid)
    if os.path.isdir(d): print('have', aid); return
    info = json.loads(curl(f'https://api.polyhaven.com/info/{aid}'))
    files = json.loads(curl(f'https://api.polyhaven.com/files/{aid}'))
    os.makedirs(d)
    authors = '; '.join(info.get('authors', {}).keys())
    rows = []
    for m in maps:
        e = files[m][res]['jpg']; fn = os.path.basename(e['url'])
        assert re.fullmatch(r'[A-Za-z0-9_.-]+', fn)
        p = os.path.join(d, fn); curl(e['url'], p)
        rows.append(['polyhaven', aid, f'https://polyhaven.com/a/{aid}', f'polyhaven/{aid}/{fn}', sha(p), 'CC0-1.0', authors, res, used_by, DATE])
    ledger(rows); print('ok', aid, len(rows))
def ambientcg(aid, used_by, attr='2K-JPG'):
    d = os.path.join(TP, 'ambientcg', aid)
    if os.path.isdir(d): print('have', aid); return
    os.makedirs(d)
    zn = f'{aid}_{attr}.zip'; zp = os.path.join(d, zn)
    curl(f'https://ambientcg.com/get?file={zn}', zp)
    rows = [['ambientcg', aid, f'https://ambientcg.com/a/{aid}', f'ambientcg/{aid}/{zn}', sha(zp), 'CC0-1.0', 'ambientCG', attr, used_by, DATE]]
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            b = os.path.basename(n)
            if not re.fullmatch(r'[A-Za-z0-9_.-]+\.(jpg|png)', b): continue
            if z.getinfo(n).file_size > 200e6: continue
            with open(os.path.join(d, b), 'wb') as f: f.write(z.read(n))
            rows.append(['ambientcg', aid, f'https://ambientcg.com/a/{aid}', f'ambientcg/{aid}/{b}', sha(os.path.join(d, b)), 'CC0-1.0', 'ambientCG', attr, used_by, DATE])
    ledger(rows); print('ok', aid, len(rows))
if __name__ == '__main__':
    PH = ['Diffuse', 'nor_gl', 'Rough', 'AO', 'Displacement']
    jobs = json.loads(sys.argv[1])
    for j in jobs:
        if j[0] == 'ph': polyhaven(j[1], PH, j[2])
        else: ambientcg(j[1], j[2], *(j[3:]))
