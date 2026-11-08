"""Independent source/LOD/material/collision/mipmap checks; never modifies oldFields."""
import bpy,json,sys,hashlib,struct,csv
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1];FIELDS=ROOT.parent;PROJECT=FIELDS.parents[2]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import validate,common
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'PineRefinementV3.blend'));name='SM_Pine_Stonebrook_V3';verdict=validate.validate_scene(only=[name]);(ROOT/'pine_validation.json').write_text(json.dumps(verdict,indent=2)+'\n');geometry=json.loads((ROOT/'pine_geometry_report.json').read_text());lods=[]
for lod in range(3):
 ob=bpy.data.objects[name+'_LOD%d'%lod];mesh=ob.data;branch={v.value for v in mesh.attributes['source_branch_id'].data if v.value>=0};spray={v.value for v in mesh.attributes['source_spray_id'].data if v.value>=0};assert len(branch)==584 and len(spray)==1853
 zero=sum(n.vector.length<1e-4 for n in mesh.corner_normals);assert zero==0,(lod,zero)
 tris=sum(len(p.vertices)-2 for p in mesh.polygons);assert tris<=[25000,12000,7000][lod],(lod,tris)
 lo,hi=common.world_bounds(ob);lods.append({'lod':lod,'triangles':tris,'retained_branch_ids':sorted(branch),'retained_spray_ids':sorted(spray),'zero_corner_normals':zero,'bounds_min_m':list(lo),'bounds_max_m':list(hi)})
assert max(abs((lods[0]['bounds_max_m'][i]-lods[0]['bounds_min_m'][i])-geometry['dimensions_m'][i]) for i in range(3))<.0001
co=bpy.data.objects['UCX_'+name+'_LOD0_01']
def signature(ob):
 return {'vertices':[list(v.co) for v in ob.data.vertices],'faces':[list(p.vertices) for p in ob.data.polygons],'matrix_world':[list(r) for r in ob.matrix_world]}
ours=signature(co)
with bpy.data.libraries.load(str(FIELDS/'KIT_StonebrookFields.blend'),link=False) as (available,loaded):loaded.objects=['UCX_SM_Pine_Stonebrook_01_LOD0_01']
assert signature(loaded.objects[0])==ours,'OriginalUCXchanged'
alpha=Image.open(ROOT/'Textures/T_PineV3_Sprays_BC.png').getchannel('A');mips=[]
while True:
 a=np.asarray(alpha).astype('float32')/255;mips.append({'size':alpha.size[0],'mean_alpha':float(a.mean()),'coverage_above_clip':float((a>.12).mean())})
 if alpha.size[0]==1:break
 alpha=alpha.resize((max(1,alpha.size[0]//2),max(1,alpha.size[1]//2)),Image.Resampling.BOX)
assert mips[-1]['mean_alpha']>.12,'Distantalpha losesentiretuft'
# Source oldledger is read-only; independently verify its artifact hashes.
oldrows=list(csv.DictReader((FIELDS/'candidate_ledger.csv').open()));checked=[]
for row in oldrows:
 path=PROJECT/row['asset_path']
 if path.is_file():
  digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==row['sha256'],str(path);checked.append(row['asset_path'])
report={'passed':verdict['summary']['errors']==0,'guide_summary':verdict['summary'],'lods':lods,'original_ucx_identical':True,'alpha_mips':mips,'old_fields_rows_verified':len(checked),'old_fields_ledger_sha256':hashlib.sha256((FIELDS/'candidate_ledger.csv').read_bytes()).hexdigest(),'old_fields_manifest_sha256':hashlib.sha256((FIELDS/'art_manifest.json').read_bytes()).hexdigest()}
(ROOT/'pine_source_checks.json').write_text(json.dumps(report,indent=2)+'\n');print('PINE SOURCE CHECKS',report['guide_summary'],'oldFields',len(checked),'UCXidentical,all584branches/1853spraysretained,alphaMip1',mips[-1],flush=True)
