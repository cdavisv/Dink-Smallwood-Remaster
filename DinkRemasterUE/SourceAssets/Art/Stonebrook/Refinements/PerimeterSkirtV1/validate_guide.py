"""Keep the guide's raw missing-collision finding and its explicit exception."""
import argparse
import json
from pathlib import Path
import sys
import bpy

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--pipeline', type=Path, required=True, help='Repository tools/blender directory')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
sys.path.insert(0, str(args.pipeline.resolve()))
from dinkasset.validate import validate_scene

bpy.ops.wm.open_mainfile(filepath=str(root / 'PerimeterSkirtV1.blend'))
report = validate_scene()
(root / 'guide_validation.json').write_text(json.dumps(report, indent=2) + '\n')
assert report['summary'] == {'assets': 1, 'assets_passed': 0, 'errors': 1, 'warnings': 0}
assert [f['code'] for a in report['assets'] for f in a['findings']] == ['COLLISION_MISSING']
receipt = {'raw_guide_passed': False, 'raw_errors': 1, 'raw_warnings': 0,
    'accepted_exception': 'COLLISION_MISSING',
    'reason': 'Owner-authorized render-only seam closure must have no UCX/native collision/navigation/overlaps.',
    'all_other_guide_checks_passed': True, 'native_tested': False}
(root / 'guide_exception.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('GUIDE_HAS_EXACTLY_AUTHORIZED_COLLISION_EXCEPTION', flush=True)
