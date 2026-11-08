import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path('Scripts').resolve()))
import playtest_desktop as d
import playtest_interactions as i
out=Path('Saved/BasketReviewed/Render').resolve();log=out/'game.log';pid=json.loads((out/'fixture_results.json').read_text())['pid']
d.use_private_display(':189');w=d.window();assert int(w['pid'])==pid;d.focus(w)
start=d.player(log);assert start['screen']==1 and not start['move_ignored']
d.walk_route(Path('Scripts/Playtest/house_exit_art.json'),log,out/'exit.json');i.capture(out/'exited.png')
d.walk_route(Path('Scripts/Playtest/house_return_art.json'),log,out/'return.json');i.capture(out/'returned.png')
policy={}
for cmd,expected in [('getall DinkInteriorCameraComponent bEnableWallCutaway',' = False'),('getall DinkInteriorCameraComponent ManagedOccluderCount',' = 0'),('getall DinkInteriorCameraComponent FadingOccluderCount',' = 0'),('getall SpringArmComponent bDoCollisionTest',' = True')]:
 offset=log.stat().st_size;d.console(cmd)
 with log.open()as f:f.seek(offset);text=f.read()
 assert expected in text,(cmd,text)
 policy[cmd]=text
(out/'door_loop.json').write_text(json.dumps({'passed':True,'pid':pid,'start':start,'exit':'PASS','return':'PASS','native_policy':policy,'scope':'Actual W route from preceding basket probe departure; photo/contact setup was earlier explicitly teleported, no teleports in door exit/return route.'},indent=2)+'\n');print('BASKET_DOOR_LOOP_PASS',flush=True)
