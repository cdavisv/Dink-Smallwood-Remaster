import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
import sys
D=Path(sys.argv[sys.argv.index('--out')+1]).resolve() if '--out' in sys.argv else Path(__file__).resolve().parent;assert not (D/'REFLECTION_CONTROL.json').exists(),'Use a fresh copied study folder; preserve frozen proof'
bpy.ops.wm.open_mainfile(filepath=str(D/'ActualCottagePane_OpticalReference.blend'));r=json.loads((D/'REFERENCE.json').read_text());center=Vector(r['views'][-1]['target']);s=bpy.context.scene;light=bpy.data.objects['ReflectionSoftbox'];light.location=center+Vector((-1.8,-.65,-.15));light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler();bpy.data.objects['PatternReferenceCard'].hide_render=True;pane=bpy.data.objects['InsetGlassPane.009'];rows=[]
for state in ['glass','bare']:
 pane.hide_render=state=='bare';filename='outside_grazing_reflection_'+state+'.png';s.render.filepath=str(D/filename);bpy.ops.render.render(write_still=True);rows.append({'file':filename,'glass_visible':state=='glass','sha256':hashlib.sha256((D/filename).read_bytes()).hexdigest()});print('REFLECTION_CONTROL_DONE',filename,flush=True)
pane.hide_render=False;bpy.ops.wm.save_as_mainfile(filepath=str(D/'ActualCottagePane_ReflectionControl.blend'),compress=True);(D/'REFLECTION_CONTROL.json').write_text(json.dumps({'status':'RENDERED_REVIEW_PENDING','card_visible':False,'camera':list(s.camera.location),'target':list(center),'light_location':list(light.location),'light_policy':'Softbox placed on idealreflectiondirection opposite camera X/Z, samefrontY. Barecontrolremoveonlypane.','views':rows,'qualification':'CPUclosedpane/thinwall sourceonly; not nativeone-sidedopticalparity.'},indent=2)+'\n')
