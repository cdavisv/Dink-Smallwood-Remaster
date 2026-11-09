import json,os,sys,time
from pathlib import Path
ROOT=Path('/home/davisc/Work/DinkSurfaceDelivery/DinkRemasterUE')
PHASE=os.environ.get('DINK_FLOOR_PHASE','Before')
RESUME=os.environ.get('DINK_FLOOR_RESUME_PHOTOS')=='1'
PHOTOS_ONLY=os.environ.get('DINK_FLOOR_PHOTOS_ONLY')=='1'
EXPECT_UNDERLAY=os.environ.get('DINK_FLOOR_EXPECT_UNDERLAY')=='1'
assert not (RESUME and PHOTOS_ONLY)
OUT=Path('/home/davisc/Work/DinkQA/SurfaceNative')/PHASE
LOG=OUT/'game.log'
sys.path.insert(0,str(ROOT/'Scripts'))
import playtest_desktop as d
import playtest_interactions as q
d.use_private_display()
launch=json.loads(Path('/home/davisc/Work/DinkQA/Tools/game.json').read_text())
window=d.window();assert window['pid']==launch['game_pid']
assert str(ROOT/'DinkRemaster.uproject') in launch['command']
assert not (OUT/'receipt.json').exists()
if RESUME:
 assert json.loads((OUT/'launch.json').read_text())['game_pid']==window['pid']
else:
 (OUT/'launch.json').write_text(json.dumps(launch,indent=2)+'\n')
(ROOT/'Saved/Playtest/SurfaceFloor').mkdir(parents=True,exist_ok=True)
d.focus(window)
records=[]
def command(value):
 response=q.command_output(value,LOG);records.append({'command':value,'response':response});return response
command('dink.ScreenInfo 0');command('DisableAllScreenMessages')
assert 'QA_FLOOR_READER_READY' in command(f"py QA_FLOOR_PHASE={PHASE!r}; exec(open('/home/davisc/Work/DinkQA/SurfaceNative/read_floor_runtime.py').read())")
assert 'QA_NATIVE_CAMERA_READER_READY' in command("py QA_NATIVE_CAMERA_OUTPUT='SurfaceFloor'; exec(open('/home/davisc/Work/DinkQA/read_native_camera.py').read())")
if not RESUME:
 for attempt in range(30):
  if not d.player(LOG)['move_ignored']:break
  d.run('wtype','-k','space');time.sleep(.4)
 else:raise RuntimeError('Opening dialogue still owns input')
 initial=d.player(LOG);assert initial['screen']==1 and initial['radius']==28
 if not PHOTOS_ONLY:
  d.walk_route(ROOT/'Scripts/Playtest/house_exit_art.json',LOG,OUT/'actual-exit.json')
  if EXPECT_UNDERLAY:
   time.sleep(.5)
   assert 'QA_UNDERFLOOR_PASS actual-outside' in command("py qa_fu_read('actual-outside',False)")
   assert 'QA_NATIVE_CAMERA_READ outdoor-after-exit' in command("py qa_nc_read('outdoor-after-exit')")
   camera=ROOT/'Saved/Playtest/SurfaceFloor/outdoor-after-exit.json'
   native=json.loads(camera.read_text())
   import math
   assert not native['interior_mode'] and 399<math.dist(native['pawn_cm'],native['camera_cm'])<401,native
   (OUT/'outdoor-after-exit-camera.json').write_bytes(camera.read_bytes())
   q.capture(OUT/'outdoor-after-exit.png')
  d.walk_route(ROOT/'Scripts/Playtest/house_return_art.json',LOG,OUT/'actual-return.json')
  route_final=d.player(LOG);assert route_final['screen']==1 and not route_final['move_ignored']
 else:
  route_final=None

else:
 initial={'recovery':'See unchanged actual-exit.json; first controller passed both actual routes before photographic reader failure'}
 prior_route=json.loads((OUT/'actual-return.json').read_text())
 assert prior_route['result']=='PASS' and json.loads((OUT/'actual-exit.json').read_text())['result']=='PASS'
 route_final=prior_route['steps'][-1]['observed']
 assert d.player(LOG)['screen']==1
if EXPECT_UNDERLAY:
 assert 'QA_UNDERFLOOR_PASS actual-return' in command("py qa_fu_read('actual-return',True)")
for label,point,yaw,pitch in [('door-room',(303.5,345),270,-18),('floor-close',(355,335),270,-40)]:
 command(f'dink.Goto 1 {point[0]} {point[1]}');command(f'dink.View {yaw} {pitch}');time.sleep(2)
 if EXPECT_UNDERLAY:
  assert 'QA_UNDERFLOOR_PASS '+label in command(f'py qa_fu_read({label!r},True)')
 assert 'QA_FLOOR_READ '+label in command(f'py qa_fs_read({label!r})')
 assert 'QA_NATIVE_CAMERA_READ '+label in command(f'py qa_nc_read({label!r})')
 camera=ROOT/'Saved/Playtest/SurfaceFloor'/(label+'.json')
 (OUT/(label+'-camera.json')).write_bytes(camera.read_bytes())
 q.capture(OUT/(label+'.png'))
(OUT/'receipt.json').write_text(json.dumps({'phase':PHASE,'photo_recovery_same_process':RESUME,'actual_route_exercised':not PHOTOS_ONLY,'underfloor_runtime_checked':EXPECT_UNDERLAY,'method':('Photographic fixture teleports only; no actual-route claim. ' if PHOTOS_ONLY else 'Fresh actual keyboard exit and return precede separate photographic fixture teleports. ')+'No material/light/collision/property setters. Normal view yaw/pitch only.','initial':initial,'actual_route_final':route_final,'records':records,'window':window},indent=2)+'\n')
print('FLOOR '+PHASE+(' PHOTOGRAPHIC FIXTURES ONLY PASS' if PHOTOS_ONLY else ' ACTUAL ROUTE AND PHOTO FIXTURES PASS'),flush=True)
command('Quit')
