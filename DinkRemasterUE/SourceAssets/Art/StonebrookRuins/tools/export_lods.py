"""Export one FBX per LOD for every ruin asset (Unreal explicit import_lod path).

The companion exporter (dink.py export_ue) writes the _LOD0.._LOD2 siblings into one FBX; the
Stonebrook import notes record that Unreal merges such siblings instead of building a LOD chain.
Like StonebrookExterior/export_foliage_lods.py this writes Export/.../<Asset>_LOD<n>.fbx: one render
mesh per file, UCX hulls and SOCKET_ empties only in LOD0.  Same FBX settings as export_ue
(FBX_SCALE_ALL, apply_unit_scale=True, Z up, -Y forward).  Does not change source meshes.

    blender -b --factory-startup -t 3 -P export_lods.py
"""
import bpy, json, sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
KIT = HERE.parent; UE = KIT.parents[2]
for cand in [UE.parent / 'tools/blender', UE.parent / 'Dink-Smallwood-Remaster/tools/blender']:
    if (cand / 'dinkasset').exists():
        sys.path.insert(0, str(cand)); break
from dinkasset import common, export_ue, fbxparse
from dinkasset import conventions as C

bpy.ops.wm.open_mainfile(filepath=str(KIT / 'KIT_StonebrookRuins.blend'))
spec_path = KIT / 'ruins_manifest.json'; spec = json.loads(spec_path.read_text())
report = []
for asset in common.find_assets():
    validation = export_ue.validate.validate_scene(only=[asset.name])
    if validation['summary']['errors']:
        raise RuntimeError(f'validation failed: {asset.name}')
    folder = KIT / ('Export' + C.content_path(asset.cls_name, asset.name, 'StonebrookRuins').rsplit('/', 1)[0])
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    with export_ue.unhidden(asset.all_objects()), common.at_origin(asset):
        for lod in range(3):
            render = bpy.data.objects[asset.name + '_LOD' + str(lod)]
            proxy = SimpleNamespace(renders=[render], collision=asset.collision if lod == 0 else [], armatures=[],
                                    sockets=asset.sockets if lod == 0 else [])
            target = folder / (asset.name + '_LOD' + str(lod) + '.fbx')
            export_ue.export_fbx(proxy, str(target), 'all', None)
            parsed = fbxparse.inspect(str(target))
            render_nodes = [k for k in parsed['models'] if not k.startswith('UCX_') and not k.startswith('SOCKET_')]
            if render_nodes != [render.name]:
                raise RuntimeError(f'{target.name}: unexpected render nodes {render_nodes}')
            ucx = [k for k in parsed['models'] if k.startswith('UCX_')]
            socks = [k for k in parsed['models'] if k.startswith('SOCKET_')]
            files.append(str(target.relative_to(KIT)))
            report.append({'asset': asset.name, 'lod': lod, 'file': str(target.relative_to(KIT)),
                           'render_nodes': render_nodes, 'ucx_nodes': len(ucx), 'socket_nodes': len(socks),
                           'unit_scale_factor': parsed.get('unit_scale_factor'),
                           'triangles': common.tri_count(render)})
    spec['assets'][asset.name]['lod_fbx'] = files
    spec['assets'][asset.name]['expected_lods'] = 3
spec_path.write_text(json.dumps(spec, indent=2) + '\n')
(KIT / 'lod_export.json').write_text(json.dumps({'passed': True, 'files': report}, indent=2) + '\n')
print('RUIN LOD FBX:', len(report), 'files')
