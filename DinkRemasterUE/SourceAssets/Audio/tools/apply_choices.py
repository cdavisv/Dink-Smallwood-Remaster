"""Validate exported listening decisions and select existing audio without regeneration.
Run with --choices /path/audio_choices.csv; use --check to validate without writes.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import wave

ROOT = Path(__file__).resolve().parents[3]
AUDIO = ROOT / 'SourceAssets/Audio'
# Original music numbers and named script cues, as recorded in Music/README.md.
ALIASES = {
 '01_title': ['1003'], '02_stonebrook_village': ['104'], '03_home_interior': ['105'],
 '04_terris_town': ['1','1005','102','103'], '05_overworld_wilds': ['100'],
 '06_wonder': ['wanderer.mid','mystery.mid'], '07_battle': ['battle.mid'],
 '08_cave': ['caveexpl.mid','1010'], '09_villain': ['bullythe.mid'],
 '10_love': ['love.mid','lovin.mid'], '11_sorrow_resolve': ['insper.mid'],
 '12_murkwood': ['1002'], '13_windemere_port': ['106'], '14_royal_court': ['1011','1012'],
 '15_goblin_lands': ['1004','1009'], '16_darklands': ['1007'], '17_koka_isle': ['1016'],
 '18_snow_castle': ['107','101'], '19_edge_of_the_world': ['1013'], '20_joppa_isle': ['1008'],
 '21_final_approach': ['1015','1006','1018'], '22_waltz': ['denube.mid'],
 '23_stinger_creepy': ['creepy.mid'], '24_stinger_sneaky': ['sneaky.mid'],
 '25_stinger_urgent': ['urgent.mid'], '26_stinger_planning': ['planning.mid'],
 '27_stinger_mystery_x': ['xfiles.mid'], '28_story': ['story.mid','5.mid'],
}
LOOPS = set(range(2,11)) | set(range(12,22))

def atomic(path, text):
 path.parent.mkdir(parents=True, exist_ok=True)
 tmp = path.with_suffix(path.suffix+'.tmp'); tmp.write_text(text); os.replace(tmp,path)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--choices',type=Path,default=AUDIO/'approved_choices.csv')
 p.add_argument('--check',action='store_true'); args=p.parse_args()
 raw=args.choices.read_bytes(); choices=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
 if not choices: raise ValueError('No listening decisions')
 ledger=ROOT/'SourceAssets/asset_ledger.csv'
 with ledger.open(newline='') as f: reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
 by_input={r['asset_path']:r for r in rows}
 seen=set(); assets=[]; sounds={}; music={}; rejected=[]; selected={}; counts={'sfx':0,'music':0,'rejected':0}
 def asset(name,folder,source,loop):
  with wave.open(str(ROOT/source),'rb') as w:
   if w.getsampwidth()!=2 or w.getframerate()!=44100 or w.getnframes()==0: raise ValueError('Invalid engine WAV '+source)
   duration=w.getnframes()/w.getframerate()
  path=f'{folder}/{name}.{name}'
  assets.append({'name':name,'folder':folder,'source':source,'sha256':hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),'loop':loop,'duration_s':duration})
  return {'asset':path,'loop':loop}
 def alias(key,row):
  key=key.lower()
  if key in music and music[key]!=row:raise ValueError('Conflicting music alias '+key)
  music[key]=row
 for c in choices:
  kind,ident,choice=c['kind'],c['id'],c['choice']; key=(kind,ident)
  if key in seen:raise ValueError('Duplicate choice '+str(key))
  seen.add(key)
  if kind=='sfx':
   if not re.fullmatch(r'\d{2}_[a-z0-9]+',ident) or choice not in ['a','b','neither']:raise ValueError('Invalid SFX decision '+str(c))
   candidates=[f'SourceAssets/Audio/SFX/delivered/{ident}_{v}.mp3' for v in ['a','b']]
   if any(x not in by_input for x in candidates):raise ValueError('Unknown SFX '+ident)
   for index,path in enumerate(candidates):
    status='rejected' if choice=='neither' else ('approved' if choice=='ab'[index] else 'not_selected')
    selected[path]=(status,c)
   if choice=='neither':rejected.append(c); counts['rejected']+=1; continue
   sounds[str(int(ident[:2]))]=asset('SFX_'+ident,'/Game/Dink/Audio/SFX',f'SourceAssets/Audio/SFX/{ident}_{choice}.wav',int(ident[:2]) in {23,34})
   counts['sfx']+=1
  elif kind=='music':
   if ident not in ALIASES or choice not in ['keep','regenerate']:raise ValueError('Invalid music decision '+str(c))
   path=f'SourceAssets/Audio/Music/delivered/{ident}.mp3'
   if path not in by_input:raise ValueError('Unknown music '+ident)
   selected[path]=('approved' if choice=='keep' else 'rejected',c)
   if choice!='keep':rejected.append(c);counts['rejected']+=1;continue
   loop=int(ident[:2]) in LOOPS
   source=f'SourceAssets/Audio/Music/loops/{ident}_loop.wav' if loop else f'SourceAssets/Audio/Music/{ident}.wav'
   row=asset('MUS_'+ident,'/Game/Dink/Audio/Music',source,loop)
   alias(ident,row)
   for k in ALIASES[ident]:
    alias(k,row)
    if k.isdigit():alias(k+'.mid',row)
   counts['music']+=1
  else:raise ValueError('Unknown audio kind '+kind)
 if len(seen)!=76:raise ValueError(f'Expected full76-row review, got{len(seen)}')
 screens=json.loads((ROOT/'ImportData/screens.json').read_text())['screens']
 screen_music={}
 for s in screens:
  raw_key=str(s['music']['raw'])
  if raw_key in music and s['music'].get('file'):
   alias(Path(s['music']['file']).name,music[raw_key])
  if raw_key=='105' and s['region']=='edge_of_the_world':screen_music[str(s['screen'])]=music['19_edge_of_the_world']
 # Start a new game with the approved home cue rather than an empty inherited track.
 if '03_home_interior' in music:screen_music['1']=music['03_home_interior']
 runtime={'schema':'dink-audio/1','sounds':sounds,'music':music,'screen_music':screen_music,'volumes':{'music':.35,'sfx':.8},'rejected':rejected}
 result={'schema':'dink-audio-selection/1','review_sha256':hashlib.sha256(raw).hexdigest(),'counts':counts,'assets':assets,'runtime':runtime}
 if not args.check:
  for row in rows:
   if row['asset_path'] in selected:
    status,c=selected[row['asset_path']];row['status']=status
    note=row['notes'].split(' | Owner review:')[0]
    row['notes']=note+' | Owner review: '+c['choice']+('; '+c['note'] if c['note'] else '')
  output=io.StringIO(newline='');w=csv.DictWriter(output,fieldnames=fields);w.writeheader();w.writerows(rows)
  atomic(ledger,output.getvalue())
  atomic(AUDIO/'approved_choices.csv',raw.decode('utf-8-sig'))
  atomic(AUDIO/'selection_manifest.json',json.dumps(result,indent=2)+'\n')
  atomic(AUDIO/'review_decisions.json',json.dumps({'source':str(args.choices),'sha256':result['review_sha256'],'counts':counts,'choices':choices},indent=2)+'\n')
 print('AUDIO CHOICES '+('VALID' if args.check else 'APPLIED')+': '+str(counts)+'; '+str(len(assets))+' approved assets')
if __name__=='__main__':main()
