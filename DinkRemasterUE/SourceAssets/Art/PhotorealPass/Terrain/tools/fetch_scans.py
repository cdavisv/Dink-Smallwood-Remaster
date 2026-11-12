from pathlib import Path
import json,subprocess,os,sys,hashlib,zipfile,datetime,fcntl
TP=str(Path(__file__).resolve().parents[6]/'DinkRemasterUE/SourceAssets/Art/PhotorealPass/ThirdParty')
CSV=TP+'/downloads.csv'
HDR='source,asset_id,asset_url,file,sha256,licence,author,resolution,used_by,date\n'
def curl(url,out):
    return subprocess.run(['curl','-fL','--proto','=https','-s','--retry','3','-o',out,url]).returncode
def sha(f):
    h=hashlib.sha256(); h.update(open(f,'rb').read()); return h.hexdigest()
def ledger(rows):
    os.makedirs(TP,exist_ok=True)
    with open(CSV,'a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        if f.tell()==0: f.write(HDR)
        for r in rows: f.write(','.join('"%s"'%x if ',' in x else x for x in r)+'\n')
def ph(aid,used):
    d=f'{TP}/polyhaven/{aid}'
    if os.path.isdir(d) and len(os.listdir(d))>=4: print('have',aid); return
    os.makedirs(d,exist_ok=True)
    curl(f'https://api.polyhaven.com/files/{aid}','/tmp/_x') if False else None
    tmp=f'api/phf_{aid}.json'; curl(f'https://api.polyhaven.com/files/{aid}',tmp); F=json.load(open(tmp))
    tmp2=f'api/phi_{aid}.json'; curl(f'https://api.polyhaven.com/info/{aid}',tmp2); I=json.load(open(tmp2))
    author=';'.join(I.get('authors',{}).keys())
    want={'Diffuse':'jpg','nor_gl':'jpg','arm':'jpg','Rough':'jpg','AO':'jpg','Displacement':'png'}
    rows=[]
    for m,fmt in want.items():
        if m not in F: continue
        if m in('Rough','AO') and 'arm' in F: continue
        e=F[m].get('2k',{}).get(fmt)
        if not e: print('missing',aid,m); continue
        fn=os.path.basename(e['url'].split('?')[0]); out=f'{d}/{fn}'
        if curl(e['url'],out): print('FAIL',aid,m); continue
        rows.append(['polyhaven',aid,f'https://polyhaven.com/a/{aid}',fn,sha(out),'CC0-1.0',author,'2k',used,datetime.date.today().isoformat()])
    ledger(rows); print('ok',aid,len(rows),I.get('dimensions'))
def acg(aid,used):
    d=f'{TP}/ambientcg/{aid}'
    if os.path.isdir(d) and len(os.listdir(d))>=4: print('have',aid); return
    os.makedirs(d,exist_ok=True)
    z=f'api/{aid}_2K-JPG.zip'
    if curl(f'https://ambientcg.com/get?file={aid}_2K-JPG.zip',z): print('FAIL',aid); return
    rows=[]
    with zipfile.ZipFile(z) as Z:
        for n in Z.namelist():
            b=os.path.basename(n)
            if not b.lower().endswith(('.jpg','.png')) or 'NormalDX' in b or b!=n: continue
            out=f'{d}/{b}'; open(out,'wb').write(Z.read(n))
            rows.append(['ambientcg',aid,f'https://ambientcg.com/a/{aid}',b,sha(out),'CC0-1.0','ambientCG (Lennart Demes)','2k',used,datetime.date.today().isoformat()])
    os.remove(z); ledger(rows); print('ok',aid,len(rows))
for a in sys.argv[1:]:
    src,aid,used=a.split(':')
    (ph if src=='ph' else acg)(aid,used if '/' in used else 'Terrain/'+used)
