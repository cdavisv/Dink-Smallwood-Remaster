import bpy,sys,json,os
from pathlib import Path
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O/'Pipeline'))
from dinkasset import validate
bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealBarrelV1_Source.blend'))
c=bpy.data.collections['SM_Barrel_Oak_01']
s=next(s for s in bpy.data.scenes if c.name in s.collection.children)
bpy.context.window.scene=s
report=validate.validate_scene(only=['SM_Barrel_Oak_01'])
(O/'guide_validation_source_scene.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));sys.stdout.flush();sys.stderr.flush();os._exit(0)
