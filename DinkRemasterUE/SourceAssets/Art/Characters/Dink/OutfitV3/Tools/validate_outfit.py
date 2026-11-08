"""Source review validation only; no export/import/manifest production."""
import bpy,json,sys
from pathlib import Path
ART=Path(__file__).resolve().parents[1];PROJECT=ART.parents[4]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import validate
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));bpy.data.objects['Armature'].data.pose_position='REST'
result=validate.validate_scene(only=['SK_Dink_OutfitV3']);(ART/'validation_review.json').write_text(json.dumps(result,indent=2)+'\n')
print('OUTFIT SOURCE VALIDATION',result['summary'])
for a in result['assets']:
 for f in a['findings']:
  if f['severity'] in ['error','warning']:print(f['severity'],f['code'],f['message'])
if result['summary']['errors']:raise RuntimeError('Sourcecandidate hasvalidation errors')
