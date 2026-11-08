"""Export individual foliage LOD FBXs for Unreal's explicit import_lod path.

The companion exporter emits sibling meshes without an FBX LODGroup. Unreal's
combine-meshes import merges those siblings; separate files prevent that ambiguity.
Run after the normal companion export. Does not change source meshes.
"""
import bpy,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,export_ue,fbxparse
ART=ROOT/'SourceAssets/Art/StonebrookExterior'
bpy.ops.wm.open_mainfile(filepath=str(ART/'KIT_StonebrookExterior.blend'))
path=ART/'exterior_manifest.json';spec=json.loads(path.read_text())
report=[]
for asset in common.find_assets():
    if asset.cls_name!='foliage':continue
    validation=export_ue.validate.validate_scene(only=[asset.name])
    if validation['summary']['errors']:raise RuntimeError(f'Foliage validation failed: {asset.name}')
    folder=ART/'Export/Game/Dink/Foliage/StonebrookExterior';folder.mkdir(parents=True,exist_ok=True)
    files=[]
    with export_ue.unhidden(asset.all_objects()),common.at_origin(asset):
        for lod in range(3):
            render=bpy.data.objects[asset.name+'_LOD'+str(lod)]
            proxy=SimpleNamespace(renders=[render],collision=asset.collision if lod==0 else [],armatures=[],sockets=[])
            target=folder/(asset.name+'_LOD'+str(lod)+'.fbx')
            export_ue.export_fbx(proxy,str(target),'all',None)
            files.append(str(target.relative_to(ART)))
            version,top=fbxparse.parse(str(target));objects=next(n for n in top if n.name=='Objects')
            zero=0;normal_count=0
            for geometry in objects.find('Geometry'):
                for layer in geometry.find('LayerElementNormal'):
                    values=layer.first('Normals').props[0]
                    normal_count+=len(values)//3
                    zero+=sum(sum(v*v for v in values[i:i+3])<1e-8 for i in range(0,len(values),3))
            if zero:raise RuntimeError(f'{target.name} contains {zero} zero normals')
            parsed=fbxparse.inspect(str(target));render_nodes=[k for k in parsed['models'] if not k.startswith('UCX_')]
            if render_nodes!=[render.name]:raise RuntimeError(f'LOD file contains unexpected nodes: {render_nodes}')
            report.append({'file':str(target.relative_to(ART)),'render_nodes':render_nodes,
                           'unit_scale_factor':parsed['unit_scale_factor'],'zero_normals':zero,'normal_count':normal_count})
    spec['assets'][asset.name]['lod_fbx']=files
    spec['assets'][asset.name]['full_fbx']=spec['assets'][asset.name].get('full_fbx',spec['assets'][asset.name]['fbx'])
    spec['assets'][asset.name]['fbx']=files[0]
path.write_text(json.dumps(spec,indent=2)+'\n')
(ART/'foliage_lod_export.json').write_text(json.dumps({'passed':True,'files':report},indent=2)+'\n')
print('FOLIAGE INDIVIDUAL LODS:',len(report),'files,0 zero normals')
