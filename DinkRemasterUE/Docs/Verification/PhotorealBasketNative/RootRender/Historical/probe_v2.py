import sys,json,time,re,math
from pathlib import Path
sys.path.insert(0,str(Path('Scripts').resolve()))
import playtest_desktop as d
import playtest_interactions as i
out=Path('Saved/BasketReviewed/Render').resolve();log=out/'game.log'
d.use_private_display(':189');w=d.window();assert int(w['pid'])==232554;d.focus(w)
start=i.setup([409,146],0,log)
d.console("py exec(open(%r).read())"%str(out/'trace_basket_v2.py'));d.console("py qa_basket_trace('basket-axis-trace-v2')")
t=json.loads((out/'basket-axis-trace-v2.json').read_text());assert t['radius']==28 and t['half_height']==96
hit=t['traces'][0]['hit_text'];assert hit==t['traces'][1]['hit_text'] and 'bBlockingHit=True' in hit and 'bStartPenetrating=False' in hit
read=json.loads((out/'basket-game-distance.json').read_text());targets=[m for m in read['nearby_static_meshes']if '/PhotorealBasketV1/SM_Basket_Wicker_01.'in m['mesh']];assert len(targets)==1;target=targets[0]
assert '.'+target['actor']+'.'+target['component'] in hit,(target,hit)
m=re.search(r'Location=\(X=([^,]+),Y=([^,]+),Z=([^\)]+)\)',hit);expected=[float(v)for v in m.groups()]
states=[start];contact=None
for step in range(14):
 d.run('wtype','-P','w','-s','100','-p','w');time.sleep(.2);state=d.player(log);states.append(state)
 (out/'contact_samples_v2.json').write_text(json.dumps({'states':states,'expected_native_capsule_hit_center':expected},indent=2)+'\n')
 assert state['screen']==1 and not state['move_ignored'] and state['world'][2]>95,state
 if math.dist(state['world'][:2],expected[:2])<=12:
  contact=state;break
assert contact is not None,(states,expected)
i.capture(out/'basket-contact-v2.png')
d.console('dink.View 180 -18');d.run('wtype','-P','w','-s','900','-p','w');time.sleep(.5);away=d.player(log);i.capture(out/'basket-departure-v2.png')
assert away['map'][0]<contact['map'][0]-20 and not away['move_ignored'],away
result={'result':'PASS','pid':232554,'method':'Explicitsetupat409/146; actual100msW samples approach actual capsule-trace hit on native basket, then realWdeparture. No geometry or gameplay edits.','scope':'Bounded single-axis contact/departure; not stable-long-hold/all-directions proof. Initial long-holdstraight-Xassertion failed and is retained inHistorical.','start':start,'samples':states,'contact':contact,'departure':away,'trace_component_actor':target['actor'],'trace_component':target['component'],'native_hit_center':expected,'contact_delta_cm':math.dist(contact['world'][:2],expected[:2]),'target_mesh':target['mesh']}
(out/'fixture_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
