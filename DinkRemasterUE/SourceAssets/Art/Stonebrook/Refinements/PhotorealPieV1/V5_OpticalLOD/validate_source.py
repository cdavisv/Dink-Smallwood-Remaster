import bpy,sys,os,json
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'Pipeline'));from dinkasset import validate
bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPieV1_Export.blend'));r=validate.validate_scene(only=['SM_Pie_Rustic_01']);(O/'guide_validation.json').write_text(json.dumps(r,indent=2)+'\n');print(r['summary']);sys.stdout.flush();os._exit(0 if r['passed']else 1)
