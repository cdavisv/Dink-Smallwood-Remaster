import sys,json,time,os
from pathlib import Path
sys.path.insert(0,str(Path('Scripts').resolve()))
import playtest_desktop as d
import playtest_interactions as i
out=Path('Saved/BasketReviewed/Render').resolve();log=out/'game.log'
receipt=json.loads(Path(Path.home()/'Work/DinkQA/Tools/game.json').read_text());pid=receipt['game_pid']
assert str(Path.cwd()/'DinkRemaster.uproject') in receipt['command']
d.use_private_display(':189');w=d.window();assert int(w['pid'])==pid;d.focus(w)
for n in range(15):
 state=d.player(log)
 if not state['move_ignored']:break
 d.run('wtype','-k','space','-s','650')
else:raise RuntimeError('Openingdialogue remainsfrozen')
d.console('DisableAllScreenMessages');d.console("py exec(open(%r).read())"%str(out/'read_runtime.py'))
views=[]
for label,point,yaw,pitch in [('basket-game-distance',[409,146],0,-18),('basket-diagonal',[409,170],-35,-22),('basket-overhead',[446,190],-90,-30)]:
 i.setup(point,yaw,log);d.console(f'dink.View {yaw} {pitch}');time.sleep(3)
 d.console(f"py qa_v_read('{label}')");time.sleep(.5)
 read=json.loads((Path('Saved/VisualQA/Runtime')/(label+'.json')).read_text());assert read['pid']==pid
 matches=[m for m in read['nearby_static_meshes'] if '/PhotorealBasketV1/SM_Basket_Wicker_01.' in m['mesh']]
 assert len(matches)==1 and matches[0]['visible'] and not matches[0]['actor_hidden'],matches
 (out/(label+'.json')).write_text(json.dumps(read,indent=2)+'\n');i.capture(out/(label+'.png'));views.append({'label':label,'player':d.player(log),'target':matches[0]})
before=i.setup([409,146],0,log);d.run('wtype','-P','w','-s','1100','-p','w');time.sleep(.5);contact=d.player(log)
d.run('wtype','-P','w','-s','400','-p','w');time.sleep(.3);stable=d.player(log);i.capture(out/'basket-contact.png')
assert 418<contact['map'][0]<435 and abs(contact['map'][1]-146)<3,contact
assert abs(contact['world'][2]-98)<3 and not contact['move_ignored'],contact
assert sum((a-b)**2 for a,b in zip(contact['world'],stable['world']))<1,(contact,stable)
d.console('dink.View 180 -18');d.run('wtype','-P','w','-s','900','-p','w');time.sleep(.5);away=d.player(log);i.capture(out/'basket-departure.png')
assert away['map'][0]<contact['map'][0]-20 and not away['move_ignored'],away
result={'result':'PASS','pid':pid,'scope':'Explicit photo/contact fixture teleports; actual heldW approach/stablecontact/departure; not universal all-direction collision coverage. Door loop separately documented.','views':views,'before':before,'contact':contact,'stable_contact':stable,'departure':away}
(out/'fixture_results.json').write_text(json.dumps(result,indent=2)+'\n');print('BASKET_RENDER_CONTACT_PASS',flush=True)
