import bpy,json,sys,hashlib,bmesh,math
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O/'Pipeline'))
from dinkasset import validate,export_ue
bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPropsV1_Export.blend'))
r=validate.validate_scene();(O/'guide_validation.json').write_text(json.dumps(r,indent=2));print('GUIDE_VALIDATION',r.get('summary'),flush=True)


checks={};deps=json.loads((O/'geometry_report.json').read_text());source=Path(deps['immutable_source']);source=source if source.is_absolute()else O/source;checks['preliminary_original_file_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==deps['immutable_source_sha256']
checks['oak_reference_sha256']=hashlib.sha256((O/'Inputs/GeneratedOak_Albedo_V1.png').read_bytes()).hexdigest()=='fea05123f8c56d9a03fc5e0fe717be72215ba33ae9282be44006cf17446a782a'
checks['all_transforms_applied']=all(tuple(bpy.data.objects[n].scale)==(1,1,1) and max(abs(x)for x in bpy.data.objects[n].rotation_euler)<1e-7 for n in deps['assets'])
checks['all_finite_geometry_UVs']=all(all(math.isfinite(x)for v in bpy.data.objects[n].data.vertices for x in v.co) and all(math.isfinite(x)for u in bpy.data.objects[n].data.uv_layers[0].data for x in u.uv) for n in deps['assets'])
checks['all_baked_PBR_payloads_present']=all((O/'Textures'/('T_'+n[3:]+'_Photo_'+role+'.png')).exists()for n in deps['assets']for role in ['BC','N','ORM'])
rows=json.loads((O/'render_receipt.json').read_text());checks['matched_camera_light_exposure_pairs']=len(rows)==8 and all(all(pair[0][k]==pair[1][k]for k in ['camera_matrix','lens','lights','exposure','view_transform'])for pair in [[r for r in rows if r['view']==v] for v in ['table-joinery','bed-cloth','gameplay-distance','cloth-detail']])
checks['guide_no_errors']=r['summary']['errors']==0
(O/'technical_validation.json').write_text(json.dumps({'checks':checks,'passed':all(checks.values()),'guide_summary':r['summary'],'native_imported':False,'source_only':True},indent=2))
print('TECHNICAL_CHECKS',checks,flush=True)
if not all(checks.values()):print('VALIDATION_REQUIRES_FIX',flush=True)
import os,sys
sys.stdout.flush();sys.stderr.flush();os._exit(0)
