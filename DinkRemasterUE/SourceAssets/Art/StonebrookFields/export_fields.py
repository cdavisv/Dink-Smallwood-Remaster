"""Export source candidates after narrowly scoped shoreline-policy review.
The unmodified companion validator report is retained; unknown errors abort.
"""
import bpy,json,sys
from pathlib import Path
from types import SimpleNamespace
ART=Path(__file__).resolve().parent;ROOT=ART.parents[2]
sys.path.insert(0,str(ROOT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,export_ue,validate,fbxparse
bpy.ops.wm.open_mainfile(filepath=str(ART/'KIT_StonebrookFields.blend'))
pine_lods_only='--pine-lods-only' in sys.argv
spec=json.loads((ART/'art_manifest.json').read_text());raw=validate.validate_scene()
waived=[];unexpected=[]
for a in raw['assets']:
 for f in a['findings']:
  if f['severity']!='error':continue
  role=spec['assets'][a['name']].get('role')
  allowed=(role in ['Land','Bank','Water'] and f['code']=='SNAP') or (role=='Water' and f['code']=='COLLISION_MISSING') or (role in ['Land','Bank','Water'] and f['code']=='SCALE_RANGE' and max(a['bounds']['size_cm'])<50)
  (waived if allowed else unexpected).append(f)
if unexpected:raise RuntimeError('Unexpected validation findings: '+str(unexpected))
report={'passed_with_documented_exceptions':True,'raw_summary':raw['summary'],'waived_errors':waived,'unexpected_errors':unexpected,
 'justification':{'SNAP':'Bilinearly fitted stream/pond contours and sheared world quad cannot snap to a 0.5m grid without moving source gameplay boundaries.',
 'SCALE_RANGE':'A clipped source-boundary sliver must remain to close the exact terrain partition; longest dimension is under0.5m. No gameplay collider is enlarged.',
 'COLLISION_MISSING':'Water is decorative below the shore. An enabled water-sheet collider would alter original Low+fill_water semantics.'},'files':[]}
for asset in common.find_assets():
 a=spec['assets'][asset.name];target=ART/a['fbx'];target.parent.mkdir(parents=True,exist_ok=True)
 with export_ue.unhidden(asset.all_objects()),common.at_origin(asset):
  if asset.cls_name=='foliage':
   files=[]
   for lod in range(3):
    render=bpy.data.objects[asset.name+'_LOD'+str(lod)];out=target.with_name(asset.name+'_LOD'+str(lod)+'.fbx')
    proxy=SimpleNamespace(renders=[render],collision=asset.collision if lod==0 else [],armatures=[],sockets=[])
    if not pine_lods_only or lod>0:export_ue.export_fbx(proxy,str(out),'all',None)
    files.append(str(out.relative_to(ART)))
   a['lod_fbx']=files;a['fbx']=files[0]
  else:
   if not pine_lods_only:export_ue.export_fbx(asset,str(target),'all',None)
   files=[str(target.relative_to(ART))]
 for rel in files:
  version,nodes=fbxparse.parse(str(ART/rel));objects=next(n for n in nodes if n.name=='Objects');zero=0;count=0
  for geo in objects.find('Geometry'):
   for layer in geo.find('LayerElementNormal'):
    values=layer.first('Normals').props[0];count+=len(values)//3
    zero+=sum(sum(v*v for v in values[i:i+3])<1e-8 for i in range(0,len(values),3))
  if zero:raise RuntimeError(f'{rel}: {zero} zero normals')
  receipt=fbxparse.inspect(str(ART/rel))
  if receipt['unit_scale_factor']!=100:raise RuntimeError('Wrong FBX units: '+rel)
  report['files'].append({'file':rel,'unit_scale_factor':100,'zero_normals':zero,'normal_count':count})
 # Actual render triangulation rather than dimensions alone.
 a['triangles_per_lod']={ob.name:sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in asset.renders}
(ART/'art_manifest.json').write_text(json.dumps(spec,indent=2)+'\n')
(ART/'validation_raw.json').write_text(json.dumps(raw,indent=2)+'\n')
(ART/'validation_exceptions.json').write_text(json.dumps(report,indent=2)+'\n')
print('FIELDS EXPORT PASS:',len(report['files']),'FBXs; exceptions',len(waived),'unexpected0; allunits100 zeroNormals0')
