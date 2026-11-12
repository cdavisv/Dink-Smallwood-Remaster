from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_runtime_hardness_descriptors import build,write_missing,activation_plan

class FoundationDescriptorTests(unittest.TestCase):
    def test_authority_roles_bindings_and_no_native_or_world_writes(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);bundle=root/'bundle';game=root/'game';bundle.mkdir();(game/'Hardness').mkdir(parents=True)
            screen=dict(screen=209,id='SCR_209',collision_hash='c'*40,corners=dict(nw=[0,0],ne=[6,0],sw=[0,4],se=[6,4]))
            (bundle/'screens.json').write_text(json.dumps(dict(screens=[screen])))
            (bundle/'collision.json').write_text(json.dumps(dict(screens={'SCR_209':{'fill_solid':[[0,0,1,1]],'fill_water':[],'sprite':[[2,2,4,4]]}})))
            (game/'frames.csv').write_text('seq,frame\n173,1\n');(game/'placements.csv').write_text('origin,que\nS209_P13,0\n')
            layer=game/'Hardness/SCR_209_layers.json';layer.write_text(json.dumps(dict(schema='dinkex.runtime-hardness/1',width=600,height=400,vision=0,skipped_tile_indices=[])))
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            data=build(bundle,game);packet=json.loads(data['SCR_209.json'])
            self.assertEqual(packet['fill_solid'],[[0,0,1,1]])
            self.assertIsNone(packet['low_mesh']);self.assertNotIn('sprite',packet)
            self.assertTrue(packet['solid_mesh'].endswith('_FixedSolidV1.SM_SCR_209_FixedSolidV1'))
            self.assertEqual(packet['gameplay_files_sha1']['Hardness/SCR_209_layers.json'],hashlib.sha1(layer.read_bytes()).hexdigest())
            self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
    def test_output_preflight_refuses_changed_existing_before_partial_write(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);(root/'SCR_002.json').write_bytes(b'original')
            with self.assertRaises(ValueError):write_missing(root,{'SCR_001.json':b'new','SCR_002.json':b'changed'})
            self.assertFalse((root/'SCR_001.json').exists());self.assertEqual((root/'SCR_002.json').read_bytes(),b'original')

    def test_authored_screens_excluded_from_source_staging_plan(self):
        files={'SCR_001.json':b'{"screen":1}','SCR_209.json':b'{"screen":209}'}
        plan=activation_plan(files,[dict(schema='dink-art/1',authored_collision_screens=[1])])
        self.assertEqual(plan['screens'][0]['activation'],'excluded_authored_legacy')
        self.assertEqual(plan['screens'][1]['activation'],'requires_native_staging_verification')
        self.assertTrue(all(not row['publish_marker'] for row in plan['screens']))
        self.assertFalse(plan['world_changed']);self.assertFalse(plan['native_verified'])
        with self.assertRaises(ValueError):activation_plan(files,[dict(schema='dink-art/1',authored_collision_screens=[True])])
