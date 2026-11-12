"""Run the existing project Blender asset validator against the actual baked source."""
import bpy,sys,json
from pathlib import Path
H=Path(__file__).resolve().parents[1];P=next(p for p in H.parents if(p/'DinkRemaster.uproject').exists());sys.path.insert(0,str(P.parent/'tools/blender'));from dinkasset import validate
bpy.ops.wm.open_mainfile(filepath=str(H/'SK_Mother_ClothingRealismV1_Baked.blend'))
r=validate.validate_scene(only=['SK_Mother']);(H/'asset_validation.json').write_text(json.dumps(r,indent=2)+'\n');print('ACTUAL ASSET VALIDATION',r['summary'],flush=True)
assert r['summary']['errors']==0
