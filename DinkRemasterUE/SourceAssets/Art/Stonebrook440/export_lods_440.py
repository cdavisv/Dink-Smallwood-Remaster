"""Write one FBX per LOD for every SCR_440 asset (Unreal does not treat the companion exporter's
sibling _LODn meshes as an LODGroup; see Scripts/ART_PIPELINE.md).  Uses the companion exporter's
own export_fbx (FBX_SCALE_ALL, apply_unit_scale=True) and checks every file with its stdlib parser.

    blender -b --factory-startup -t 3 -P export_lods_440.py
"""
import bpy, json, sys
from pathlib import Path
from types import SimpleNamespace
ART = Path(__file__).resolve().parent; UE = ART.parents[2]; REPO = UE.parent
sys.path.insert(0, str(REPO / 'tools/blender'))
from dinkasset import common, export_ue, fbxparse   # noqa: E402

bpy.ops.wm.open_mainfile(filepath=str(ART / 'KIT_Stonebrook440.blend'))
spec = json.loads((ART / 'art_manifest.json').read_text())
out_dir = ART / 'Export/LODs'; out_dir.mkdir(parents=True, exist_ok=True)
report = {'files': [], 'passed': True}
for asset in common.find_assets():
    a = spec['assets'][asset.name]
    with export_ue.unhidden(asset.all_objects()), common.at_origin(asset):
        for lod, render in enumerate(asset.renders):
            out = out_dir / f'{asset.name}_LOD{lod}.fbx'
            proxy = SimpleNamespace(renders=[render], collision=asset.collision if lod == 0 else [], armatures=[], sockets=[])
            export_ue.export_fbx(proxy, str(out), 'all', None)
            version, nodes = fbxparse.parse(str(out))
            objects = next(n for n in nodes if n.name == 'Objects'); zero = 0; count = 0
            for geo in objects.find('Geometry'):
                for layer in geo.find('LayerElementNormal'):
                    vals = layer.first('Normals').props[0]; count += len(vals) // 3
                    zero += sum(sum(v * v for v in vals[i:i + 3]) < 1e-10 for i in range(0, len(vals), 3))
            ins = fbxparse.inspect(str(out))
            ok = ins['unit_scale_factor'] == 100 and zero == 0
            report['passed'] &= ok
            report['files'].append({'file': str(out.relative_to(ART)), 'asset': asset.name, 'lod': lod, 'unit_scale_factor': ins['unit_scale_factor'],
                                    'zero_normals': zero, 'normal_count': count, 'triangles': common.tri_count(render),
                                    'collision_hulls': len(asset.collision) if lod == 0 else 0, 'ok': ok})
(ART / 'fbx_lod_export.json').write_text(json.dumps(report, indent=2) + '\n')
print('LOD EXPORT', 'PASS' if report['passed'] else 'FAIL', len(report['files']), 'files')
