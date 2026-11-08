"""Drive only the owned private display; persist actual-input/pose/exposure evidence."""
import argparse,json,re,sys,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Scripts'))
import playtest_desktop as d
import playtest_interactions as q
p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['doors','fist','motion','exposure','camera']);p.add_argument('--log',type=Path,default=ROOT/'Saved/Playtest/private-session.log');a=p.parse_args()
out=ROOT/'Saved/Playtest/verified-live';out.mkdir(parents=True,exist_ok=True);d.use_private_display();d.focus(d.window());records=[]
def c(command):
 text=q.command_output(command,a.log);records.append({'command':command,'log':text});return text
state=d.player(a.log)
def healthy():
 text=c('dink.Inventory');match=re.search(r'life (\d+)/',text);assert match and int(match[1])>0,'Positive health must be verified'
 assert not re.search(r'  menu \d+\.',q.story(a.log)['log']),'Active menu'
 return text
def observe(kind):
 path=ROOT/'Scripts/Playtest/observe_live_animation.py';text=c(f"py QA_CAPTURE_KIND='{kind}'; exec(open('{path}').read())")
 assert ('QA_CAMERA_READBACK_DONE' if kind=='camera' else 'QA_ANIMATION_OBSERVER_REGISTERED '+kind) in text,text
if a.phase=='doors':
 assert state['screen']==1,'Fresh house required'
 for i in range(16):
  if not d.player(a.log)['move_ignored']:break
  d.run('wtype','-k','space');time.sleep(.35)
 else:raise RuntimeError('Opening dialogue remains active')
 q.capture(out/'house-before.png');d.walk_route(ROOT/'Scripts/Playtest/house_exit_art.json',a.log,out/'house-exit.json');q.capture(out/'house-outside.png');d.walk_route(ROOT/'Scripts/Playtest/house_return_art.json',a.log,out/'house-return.json');q.capture(out/'house-returned.png')
elif a.phase=='fist':
 inv=healthy();assert not state['move_ignored'] and 'item-fst (armed)' in inv
 observe('fist');offset=a.log.stat().st_size;burst=out/'fist-burst';assert not (burst/'ready.json').exists(),'Preserve existing evidence; choose a fresh output directory'
 process=subprocess.Popen([sys.executable,str(ROOT/'Scripts/Playtest/capture_private_burst.py'),'--out',str(burst)])
 for i in range(100):
  if (burst/'ready.json').exists():break
  assert process.poll() is None,'Capture ended early';time.sleep(.02)
 else:raise RuntimeError('Capture not ready')
 stamp=time.monotonic();d.run('wtype','-k','f');assert process.wait(timeout=12)==0
 with a.log.open('rb') as f:f.seek(offset);native=f.read().decode('utf-8',errors='replace')
 (out/'fist-key.json').write_text(json.dumps({'input':'Actual F key; no procedure/pose setters','before':state,'after':d.player(a.log),'input_monotonic':stamp,'native_log':native},indent=2)+'\n')
elif a.phase=='motion':
 healthy();c('dink.Goto 439 450 350');observe('motion');time.sleep(4);x=json.loads((out/'motion.json').read_text());assert 'error' not in x,x.get('error');healthy();assert d.player(a.log)['screen']==439
elif a.phase=='camera':observe('camera')
else:
 healthy();assert state['screen']==439,'Park Dink439 first';first=c('dink.Origin S438_P03');time.sleep(.3);second=c('dink.Origin S438_P03');target=[float(v) for v in re.search(r'world=([^ ]+)',second)[1].split(',')]
 text=c('getall SpringArmComponent TargetOffset');path=re.search(r'SpringArmComponent ([^ ]+)\.TargetOffset',text)[1];saved=re.search(r'TargetOffset = (\([^\n]+\))',text)[1]
 probe=c('getall SpringArmComponent bDoCollisionTest');probe_value=re.search(r'bDoCollisionTest = (\w+)',probe)[1]
 bias=c('r.DefaultFeature.AutoExposure.Bias');original=re.search(r'r.DefaultFeature.AutoExposure.Bias\s*=\s*"([^"\n]+)"',bias)[1]
 try:
  c(f'set {path} bDoCollisionTest false');c(f'set {path} TargetOffset (X={target[0]-state["world"][0]:.3f},Y={target[1]-state["world"][1]:.3f},Z={target[2]+32-state["world"][2]:.3f})');c('fov 30');c('dink.View 30 -12');c('dink.ScreenInfo 0')
  for label,value in [('default',float(original)),('zero',0),('minus1',-1),('minus2',-2)]:
   c(f'r.DefaultFeature.AutoExposure.Bias {value}');time.sleep(3.2);q.capture(out/f'exposure-{label}.png')
 finally:
  c('r.DefaultFeature.AutoExposure.Bias '+original);c(f'set {path} TargetOffset {saved}');c(f'set {path} bDoCollisionTest {probe_value}');c('fov 90');c('dink.ScreenInfo 1');c('r.DefaultFeature.AutoExposure.Bias')
(out/(a.phase+'-receipt.json')).write_text(json.dumps({'phase':a.phase,'initial':state,'records':records,'final':d.player(a.log)},indent=2)+'\n');print('LIVE REVIEW COMPLETE:',a.phase)
