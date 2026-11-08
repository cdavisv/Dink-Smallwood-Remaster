import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent;P=OUT/'SM_Fireplace_Stonebrook_V2.blend';before=hashlib.sha256(P.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(P));s=bpy.context.scene
producer=OUT/'build_fireplace_v2.py';script=producer.read_text();exec(compile(script[script.index('# Neutral studio/front/three-quarter/detail'):],str(producer),'exec'))
assert hashlib.sha256(P.read_bytes()).hexdigest()==before
j={'production_blend_sha256':before,'generator_sha256':hashlib.sha256(producer.read_bytes()).hexdigest(),'render_source':'Actual saved production .blend reopened; same preview block; no source mutation','render_backend':'Cycles CPU40samples, AgX, 1100square, area lights; studio evidence, not game screenshot','previews':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('preview-*.png')},'visual_status':'candidate awaiting parent review; not imported into UE'};(OUT/'preview_contract.json').write_text(json.dumps(j,indent=2)+'\n')
