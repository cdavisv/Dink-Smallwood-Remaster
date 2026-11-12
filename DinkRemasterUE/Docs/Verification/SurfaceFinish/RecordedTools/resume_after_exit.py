import hashlib,json,math,sys,time
from pathlib import Path
ROOT=Path(Path.home()/'Work/DinkSurfaceDelivery/DinkRemasterUE')
OUT=Path(Path.home()/'Work/DinkQA/SurfaceNative/AfterFinal');LOG=OUT/'game.log'
sys.path.insert(0,str(ROOT/'Scripts'))
import playtest_desktop as d
import playtest_interactions as q
d.use_private_display();window=d.window();launch=json.loads((OUT/'launch.json').read_text())
assert window['pid']==launch['game_pid']==364612
assert not (OUT/'receipt.json').exists() and not (OUT/'actual-return.json').exists()
exit_path=OUT/'actual-exit.json';exit_sha=hashlib.sha256(exit_path.read_bytes()).hexdigest();assert json.loads(exit_path.read_text())['result']=='PASS'
d.focus(window);records=[]
def command(value):
 response=q.command_output(value,LOG);records.append({'command':value,'response':response});return response
outside=d.player(LOG);assert outside['screen']==439 and not outside['move_ignored'],outside
assert 'QA_FLOOR_READER_READY' in command("py QA_FLOOR_PHASE='AfterFinal'; exec(open('/home/artist/Work/DinkQA/SurfaceNative/read_floor_runtime.py').read())")
assert 'QA_NATIVE_CAMERA_READER_READY' in command("py QA_NATIVE_CAMERA_OUTPUT='SurfaceFloor'; exec(open('/home/artist/Work/DinkQA/read_native_camera.py').read())")
assert 'QA_UNDERFLOOR_PASS actual-outside' in command("py qa_fu_read('actual-outside',False)")
assert 'QA_NATIVE_CAMERA_READ outdoor-after-exit' in command("py qa_nc_read('outdoor-after-exit')")
camera=ROOT/'Saved/Playtest/SurfaceFloor/outdoor-after-exit.json';native=json.loads(camera.read_text())
assert not native['interior_mode'] and 399<math.dist(native['pawn_cm'],native['camera_cm'])<401,native
(OUT/'outdoor-after-exit-camera.json').write_bytes(camera.read_bytes());q.capture(OUT/'outdoor-after-exit.png')
d.walk_route(ROOT/'Scripts/Playtest/house_return_art.json',LOG,OUT/'actual-return.json')
route_final=d.player(LOG);assert route_final['screen']==1 and not route_final['move_ignored'],route_final
assert 'QA_UNDERFLOOR_PASS actual-return' in command("py qa_fu_read('actual-return',True)")
for label,point,yaw,pitch in [('door-room',(303.5,345),270,-18),('floor-close',(355,335),270,-40)]:
 command(f'dink.Goto 1 {point[0]} {point[1]}');command(f'dink.View {yaw} {pitch}');time.sleep(2)
 assert 'QA_UNDERFLOOR_PASS '+label in command(f'py qa_fu_read({label!r},True)')
 assert 'QA_FLOOR_READ '+label in command(f'py qa_fs_read({label!r})')
 assert 'QA_NATIVE_CAMERA_READ '+label in command(f'py qa_nc_read({label!r})')
 camera=ROOT/'Saved/Playtest/SurfaceFloor'/(label+'.json');(OUT/(label+'-camera.json')).write_bytes(camera.read_bytes());q.capture(OUT/(label+'.png'))
assert hashlib.sha256(exit_path.read_bytes()).hexdigest()==exit_sha
(OUT/'receipt.json').write_text(json.dumps({'phase':'AfterFinal','actual_route_exercised':True,'underfloor_runtime_checked':True,'controller_recovery_same_process':True,'method':'Actual keyboard exit passed before reader error on unexposed Python navigation alias. Reader corrected to native reflected name; same owned game resumed outdoors without restart/teleport/asset changes. Actual keyboard return then passed; only afterward separate photographic fixture teleports. Read-only inspection, normal view yaw/pitch only.','preserved_exit_sha256':exit_sha,'recovery_outside':outside,'actual_route_final':route_final,'records':records,'window':window},indent=2)+'\n')
print('FINAL ACTUAL EXIT/RETURN, UNDERFLOOR OWNER/COLLISION/NAV,400CM OUTDOOR CAMERA, PHOTO FIXTURES PASS',flush=True)
command('Quit')
