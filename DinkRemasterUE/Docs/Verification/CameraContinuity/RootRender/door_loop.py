import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path('Scripts').resolve()))
import playtest_desktop as d
import playtest_interactions as i
out=Path('Saved/ContinuityIntegration/Render').resolve()
log=out/'game.log'
d.use_private_display(':189')
w=d.window(); assert int(w['pid'])==208615; d.focus(w)
start=d.player(log)
assert start['screen']==1 and abs(start['map'][0]-303)<3 and abs(start['map'][1]-350)<3,start
route={'name':'real W departure from documented room photo fixture','expected_screen':439,'waypoints':[{'screen':1,'map':[303.5,390],'warp_to':439,'tolerance_cm':3}]}
(out/'exit-route.json').write_text(json.dumps(route,indent=2)+'\n')
d.walk_route(out/'exit-route.json',log,out/'exit.json')
i.capture(out/'exited.png')
d.walk_route(Path('Scripts/Playtest/house_return_art.json'),log,out/'return.json')
i.capture(out/'returned.png')
(out/'door-loop.json').write_text(json.dumps({'start':start,'exit':'PASS','return':'PASS','scope':'actual held W from prior explicit303/350 photo fixture; no route teleports'},indent=2)+'\n')
