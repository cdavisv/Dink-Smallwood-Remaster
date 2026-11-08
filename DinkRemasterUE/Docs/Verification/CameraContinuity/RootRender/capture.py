import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path('Scripts').resolve()))
import playtest_desktop as d
import playtest_interactions as i
out=Path('Saved/ContinuityIntegration/Render').resolve()
log=out/'game.log'
d.use_private_display(':189')
w=d.window()
assert int(w['pid'])==208615,w
d.focus(w)
for n in range(15):
    state=d.player(log)
    if not state['move_ignored']: break
    d.run('wtype','-k','space','-s','650')
else: raise RuntimeError('Opening dialogue did not release movement')
d.console('DisableAllScreenMessages')
d.console("py exec(open(%r).read())" % str(out/'read_runtime.py'))
fixtures=[('opaque-north-corner-root',[178,120],180,-25),('opaque-room-root',[303,350],270,-18)]
for label,point,yaw,pitch in fixtures:
    i.setup(point,yaw,log)
    d.console(f'dink.View {yaw} {pitch}')
    time.sleep(4)
    d.console(f"py qa_v_read('{label}')")
    time.sleep(1)
    read=json.loads((Path('Saved/VisualQA/Runtime')/(label+'.json')).read_text())
    assert read['pid']==208615 and read['probe_enabled'],read
    assert read['managed_occluders']==0 and read['fading_occluders']==0
    native={}
    for command,expected in [('getall DinkInteriorCameraComponent bEnableWallCutaway',' = False'),('getall DinkInteriorCameraComponent ManagedOccluderCount',' = 0'),('getall DinkInteriorCameraComponent FadingOccluderCount',' = 0'),('getall SpringArmComponent bDoCollisionTest',' = True')]:
        offset=log.stat().st_size
        d.console(command)
        with log.open() as h:
            h.seek(offset)
            response=h.read()
        assert expected in response,(command,response)
        native[command]=response
    read['native_policy_readback']=native
    i.capture(out/(label+'.png'))
    (out/(label+'.json')).write_text(json.dumps(read,indent=2)+'\n')
    print(label,read['managed_occluders'],read['probe_enabled'],flush=True)
(out/'capture_receipt.json').write_text(json.dumps({'pid':208615,'fixtures':fixtures,'scope':'photo teleport fixtures, not traversal route','passed':True},indent=2)+'\n')
