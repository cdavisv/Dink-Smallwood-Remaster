"""Binary FBX audit of the re-exported hero LODs (stdlib + the data repo's dinkasset.fbxparse).
python3 audit_fbx.py <out.json> <fbx dir>..."""
import json, sys, hashlib
from pathlib import Path
here = Path(__file__).resolve()
project = next(p for p in here.parents if (p / 'DinkRemaster.uproject').exists())
for c in (project.parent / 'tools/blender', project.parent / 'Dink-Smallwood-Remaster/tools/blender', Path.home() / 'Repos/Dink-Smallwood/Dink-Smallwood-Remaster/tools/blender'):
    if (c / 'dinkasset').is_dir(): sys.path.insert(0, str(c)); break
from dinkasset import fbxparse
rows = {}
for d in sys.argv[2:]:
    for p in sorted(Path(d).glob('*.fbx')):
        r = fbxparse.inspect(p)
        assert abs(r['unit_scale_factor'] - 1) < 1e-6, p
        assert len([m for m in r['models'].values() if m['type'] == 'Mesh']) == 1, p
        assert len([m for m in r['models'].values() if m['type'] == 'LimbNode']) == 89, p
        assert r['models']['root']['parent'] == 'Armature' and all(abs(v - 1) < 1e-6 for v in r['models']['root']['scaling']), p
        rows[p.name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size, 'unit_scale_factor': r['unit_scale_factor'],
                        'meshes': 1, 'bones': 89}
Path(sys.argv[1]).write_text(json.dumps(rows, indent=2) + '\n')
print('HERO FBX AUDIT PASS', len(rows), 'files: one mesh, 89 bones, header 1 cm, root scale 1')
