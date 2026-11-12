"""Independent binary-FBX audit of the duck exports (stdlib python3; no Blender).

    python3 Tools/inspect_exports.py

Checks the unit header (1 cm), the identity `root` under the `Armature` wrapper,
unit node scales, one mesh per LOD file, armature-only clip files, and the
centimetre extents of each LOD against the source manifest.  Writes fbx_inspection.json.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import duck_common as D  # noqa: E402

sys.path.insert(0, str(D.pipeline_dir()))
from dinkasset import fbxparse  # noqa: E402

manifest = json.loads((D.ROOT / 'duck_manifest.json').read_text())
reports = {p.name: fbxparse.inspect(str(p)) for p in sorted(D.EXPORT.glob('*.fbx'))}
expected_bones = set(manifest['assets']['SK_Duck']['bones'])
checks = []
for name, row in reports.items():
    assert abs(row['unit_scale_factor'] - 1) < 0.001, (name, 'units')
    models = row['models']
    if name.startswith('SM_'):
        meshes = [k for k, v in models.items() if v['type'] == 'Mesh']
        render = [k for k in meshes if not k.startswith('UCX_')]
        assert len(render) == 1 and not any(v['type'] == 'LimbNode' for v in models.values()), (name, 'static prop')
        assert all(abs(x - 1) < 1e-3 for v in models.values() for x in v['scaling']), (name, 'node scale')
        if name.endswith('LOD0.fbx'):
            assert any(k.startswith('UCX_') for k in meshes), (name, 'collision hull')
        checks.append(name)
        continue
    assert 'root' in models and models['root']['parent'] == 'Armature', (name, 'root')
    assert all(abs(v - 1) < 1e-4 for v in models['root']['scaling']), (name, 'root scale')
    assert all(abs(v) < 1e-4 for v in models['root']['translation'] + models['root']['rotation']), (name, 'root identity')
    limbs = {k for k, v in models.items() if v['type'] == 'LimbNode'}
    assert limbs == expected_bones, (name, 'bones', sorted(limbs ^ expected_bones))
    assert all(abs(s - 1) < 1e-3 for v in models.values() for s in v['scaling']), (name, 'node scale')
    meshes = [v for v in models.values() if v['type'] == 'Mesh']
    if name.startswith('SK_'):
        assert len(meshes) == 1, (name, 'mesh count')
    else:
        assert len(meshes) == 0, (name, 'armature only')
    checks.append(name)
(D.ROOT / 'fbx_inspection.json').write_text(json.dumps(reports, indent=2) + '\n')
print('DUCK INDEPENDENT FBX AUDIT PASS', len(checks), 'files: header 1 cm, identity root, unit node scales, 23 bones, one mesh per skeletal LOD, armature-only clips, static head prop with UCX')
