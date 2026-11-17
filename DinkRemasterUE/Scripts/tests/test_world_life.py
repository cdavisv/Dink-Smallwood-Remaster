"""Stream world-alive: the shared wind node (Scripts/world_life_wind.py) and the motion tool of the audit
(Scripts/PhotorealQA/world_life_motion.py). Stdlib unittest; numpy and Pillow for the motion tool.

    python3 -I -m unittest discover -s Scripts/tests -p 'test_world_life.py'
"""
import importlib.util, json, os, re, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wind = load(os.path.join(SCRIPTS, 'world_life_wind.py'), 'world_life_wind')


class WindNode(unittest.TestCase):
    def test_every_input_is_used(self):
        for name in wind.WIND_INPUTS:
            self.assertRegex(wind.WIND_HLSL, r'\b%s\b' % re.escape(name), name)

    def test_no_time_times_changing_speed(self):
        # the gust field's travel is integrated on the CPU (WG.zw); absolute T only drives the pre-layer constant travel
        for line in wind.WIND_HLSL.splitlines():
            if 'travel' in line or 'gp =' in line or 'hp =' in line:
                self.assertNotRegex(line, r'T\s*\*[^;]*W[DG]\.', line)
        self.assertIn('WG.zw', wind.WIND_HLSL)

    def test_defaults_reproduce_master(self):
        # WorldLife 0 by default: the old travel and no lean; direction 0.8/0.6, strength 1, no pushes
        self.assertEqual(wind.MPC_WORLD_SCALARS['WorldLife'], 0.0)
        self.assertEqual(wind.MPC_WORLD_VECTORS['WindDir'], (0.8, 0.6, 1.0, 1.0))
        self.assertIn('lerp(float2(0.92, 0.39) * T, WG.zw, wl)', wind.WIND_HLSL)
        self.assertRegex(wind.WIND_HLSL, r'float lean = .*\* wl;')
        for i in range(4):
            self.assertEqual(wind.MPC_WORLD_VECTORS['Push%d' % i][3], 0.0)

    def test_push_only_on_low_growth(self):
        self.assertIn('(WP.z - Obj.z) / 150.0', wind.WIND_HLSL)
        self.assertIn('saturate(PushOn)', wind.WIND_HLSL)

    def test_balanced_braces(self):
        self.assertEqual(wind.WIND_HLSL.count('{'), wind.WIND_HLSL.count('}'))
        self.assertEqual(wind.WIND_HLSL.count('('), wind.WIND_HLSL.count(')'))

    def test_importer_hook(self):
        src = open(os.path.join(SCRIPTS, 'import_photoreal_art.py')).read()
        self.assertIn('world_life_wind.wire_wind(', src)
        self.assertIn('push=foliage', src)
        self.assertNotIn("float3 dir = float3(0.8, 0.6, 0.0);", src)   # the old inline node is gone


class WorldLifeJson(unittest.TestCase):
    def test_regions_and_ranges(self):
        path = os.path.join(os.path.dirname(SCRIPTS), 'Content/Dink/Data/Environment/world_life.json')
        data = json.load(open(path))
        regions = data['wind']['regions']
        self.assertGreaterEqual(len(regions), 20)
        for name, row in regions.items():
            self.assertTrue(0.0 <= row['strength'] <= 2.0, name)
            self.assertTrue(0.0 <= row['gustiness'] <= 1.0, name)
        self.assertNotIn('164', data['fire']['sequences'])


class MotionTool(unittest.TestCase):
    def test_motion_share(self):
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest('numpy/Pillow missing')
        motion = load(os.path.join(SCRIPTS, 'PhotorealQA/world_life_motion.py'), 'world_life_motion')
        with tempfile.TemporaryDirectory() as tmp:
            a = np.zeros((90, 160, 3), np.uint8)
            b = a.copy()
            b[:45, :80] = 200          # a quarter of the frame changes
            for p in (0, 1):
                for k, im in (('0', a), ('2', b if p else a), ('c0', a), ('c1', a)):
                    Image.fromarray(im).save(os.path.join(tmp, 'P%d_407_%s.png' % (p, k)))
            json.dump([{'screen': 407, 'region': 'stonebrook', 'kind': 'settlement', 'name': 'x'}], open(os.path.join(tmp, 'audit_index.json'), 'w'))
            argv = sys.argv
            sys.argv = ['x', tmp]
            try:
                motion.main()
            finally:
                sys.argv = argv
            rows = list(__import__('csv').DictReader(open(os.path.join(tmp, 'motion.csv'))))
            self.assertEqual(float(rows[0]['p0_moving']), 0.0)
            self.assertAlmostEqual(float(rows[0]['p1_moving']), 0.25, delta=0.03)
            self.assertTrue(os.path.exists(os.path.join(tmp, 'sheets', 'motion_00.jpg')))


if __name__ == '__main__':
    unittest.main()
