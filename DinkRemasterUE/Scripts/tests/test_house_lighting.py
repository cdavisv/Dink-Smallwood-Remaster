"""Owner/source/geometry preservation tests; no native rendering claim."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import math
import tempfile
import unittest

P = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('house_lighting_under_test', P / 'Scripts/house_lighting.py')
lighting = importlib.util.module_from_spec(spec); spec.loader.exec_module(lighting)


class HouseLighting(unittest.TestCase):
    def setUp(self):
        self.profile = lighting.load_profile(P)
        self.manifest = json.loads((P / 'Content/Dink/Data/Art/stonebrook.json').read_text())
        self.layout = json.loads((P / 'SourceAssets/Art/Stonebrook/room_layout.json').read_text())

    def test_current_source_and_runtime_match_authority(self):
        lighting.validate_source_layout(self.profile, self.layout)
        self.assertEqual(lighting.apply_lighting(self.profile, self.manifest), self.manifest)
        self.assertEqual(len(self.manifest['lights']), 8)
        self.assertEqual(self.manifest['lights'][:2], self.profile['legacy_lights'][:2])
        self.assertEqual(sum(x['lumens'] for x in self.manifest['lights']), 1110)

    def test_absolute_centres_and_inward_axes_from_original_placements(self):
        expected = {
            'NorthWall_1': ([-184286.25375, 392253.48, 185], 90),
            'NorthWall_6': ([-183356.56625, 392253.48, 185], 90),
            'WestWall_2': ([-184595.16, 392752.23, 185], 0),
            'WestWall_4': ([-184595.16, 393127.23, 185], 0),
            'EastWall_2': ([-183047.66, 392752.23, 185], 180),
            'EastWall_4': ([-183047.66, 393127.23, 185], 180),
        }
        for row in self.manifest['lights'][2:]:
            centre, yaw = expected[row['name'].removeprefix('Daylight_')]
            self.assertLess(math.dist(row['world_cm'], centre), 1e-8)
            self.assertEqual(row['rotation_deg'], [0, yaw, 0])
            self.assertEqual((row['kind'], row['source_width_cm'], row['source_height_cm']), ('rect', 80, 130))
            self.assertEqual((row['lumens'], row['kelvin'], row['radius_cm']), (170, 5000, 1000))

    def test_only_lights_change_and_input_is_not_mutated(self):
        old = copy.deepcopy(self.manifest); old['lights'] = copy.deepcopy(self.profile['legacy_lights'])
        before = copy.deepcopy(old); result = lighting.apply_lighting(self.profile, old)
        self.assertEqual(old, before)
        self.assertEqual({k: v for k, v in result.items() if k != 'lights'}, {k: v for k, v in old.items() if k != 'lights'})

    def test_legacy_regeneration_drift_does_not_restore_150lm_fireplace(self):
        old = copy.deepcopy(self.manifest)
        old['lights'] = copy.deepcopy(self.profile['legacy_lights'])
        old['lights'][1].update(lumens=150, kelvin=2700)
        old['lights'][1]['world_cm'][2] = 90
        with self.assertRaises(ValueError): lighting.apply_lighting(self.profile, old)
        result = lighting.apply_lighting(self.profile, old, generated_from_legacy_layout=True)
        self.assertEqual(result['lights'][1], self.profile['practical_points'][1])
        self.assertEqual(result['lights'][1]['lumens'], 40)
        self.assertEqual(result['lights'][1]['kelvin'], 2000)
        self.assertEqual(result['lights'][1]['world_cm'][2], 55)

    def test_window_geometry_changes_refuse_even_legacy_regeneration(self):
        for field, value in [('world_cm', [0, 0, 0]), ('scale', [1, 1, 1]), ('collision', False)]:
            bad = copy.deepcopy(self.manifest)
            row = next(x for x in bad['elements'] if x['name'] == 'WestWall_2')
            row[field] = value
            with self.assertRaises(ValueError): lighting.apply_lighting(self.profile, bad, generated_from_legacy_layout=True)

    def test_missing_duplicate_and_foreign_window_refuse(self):
        for change in ['missing', 'duplicate', 'foreign_mesh']:
            bad = copy.deepcopy(self.manifest)
            index = next(i for i, x in enumerate(bad['elements']) if x['name'] == 'WestWall_2')
            if change == 'missing': del bad['elements'][index]
            elif change == 'duplicate': bad['elements'].append(copy.deepcopy(bad['elements'][index]))
            else: bad['elements'][index]['mesh'] = '/Game/OtherWindow.OtherWindow'
            with self.assertRaises(ValueError): lighting.apply_lighting(self.profile, bad)

    def test_source_layout_changes_refuse(self):
        bad = copy.deepcopy(self.layout)
        row = next(x for x in bad['elements'] if x['name'] == 'NorthWall_1')
        row['source_pixel'][0] += .1
        with self.assertRaises(ValueError): lighting.validate_source_layout(self.profile, bad)

    def test_other_screen_or_render_context_refuse(self):
        for field, value in [('screen', 439), ('screen', True), ('context', {})]:
            bad = copy.deepcopy(self.manifest); bad[field] = value
            with self.assertRaises(ValueError): lighting.apply_lighting(self.profile, bad)

    def test_foreign_light_inventory_is_not_overwritten(self):
        bad = copy.deepcopy(self.manifest); bad['lights'].append(copy.deepcopy(bad['lights'][0]))
        with self.assertRaises(ValueError): lighting.apply_lighting(self.profile, bad)
        bad = copy.deepcopy(self.manifest); bad['lights'][2]['name'] = 'UnrelatedTaskLight'
        with self.assertRaises(ValueError): lighting.apply_lighting(self.profile, bad)

    def test_daylight_tuning_preserves_exact_practicals_and_scene(self):
        profile = copy.deepcopy(self.profile); profile['daylight']['lumens_per_window'] = 180
        result = lighting.apply_lighting(profile, self.manifest)
        self.assertEqual(result['lights'][:2], self.manifest['lights'][:2])
        self.assertTrue(all(x['lumens'] == 180 for x in result['lights'][2:]))
        self.assertEqual({k:v for k,v in result.items() if k != 'lights'}, {k:v for k,v in self.manifest.items() if k != 'lights'})

    def test_nonfinite_or_mistyped_parameters_refuse(self):
        for value in [True, '170', -1, float('nan'), float('inf')]:
            bad = copy.deepcopy(self.profile); bad['daylight']['lumens_per_window'] = value
            with self.assertRaises(ValueError): lighting.apply_lighting(bad, self.manifest)

    def test_rectangle_cannot_intersect_source_frame(self):
        for key, value in [('source_width_cm', 82.5), ('source_height_cm', 136), ('outside_wall_cm', 0)]:
            bad = copy.deepcopy(self.profile); bad['daylight'][key] = value
            with self.assertRaises(ValueError): lighting.apply_lighting(bad, self.manifest)

    def test_source_fingerprints_required_and_changed_bytes_refuse(self):
        bad = copy.deepcopy(self.profile); bad['source_files_sha256'] = {}
        with self.assertRaises(ValueError): lighting.validate_profile(bad)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); target = root / lighting.PROFILE; target.parent.mkdir(parents=True)
            profile = copy.deepcopy(self.profile)
            for relative in profile['source_files_sha256']:
                f = root / relative; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(b'original witness')
                profile['source_files_sha256'][relative] = hashlib.sha256(f.read_bytes()).hexdigest()
            target.write_text(json.dumps(profile)); lighting.load_profile(root)
            f.write_bytes(b'changed witness')
            with self.assertRaises(ValueError): lighting.load_profile(root)

    def test_importer_preflight_precedes_any_asset_import_and_overlay_precedes_metadata_save(self):
        tree = ast.parse((P / 'Scripts/import_stonebrook_art.py').read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        validate = next(n.lineno for n in calls if n.func.attr == 'validate_source_layout')
        first_tools = min(n.lineno for n in calls if n.func.attr in ['get_asset_tools', 'execute_console_command'])
        self.assertLess(validate, first_tools)
        overlay = next(n for n in calls if n.func.attr == 'apply_lighting')
        self.assertTrue(any(k.arg == 'generated_from_legacy_layout' and isinstance(k.value, ast.Constant) and k.value.value is True for k in overlay.keywords))
        metadata = max(n.lineno for n in calls if n.func.attr == 'write_text')
        self.assertLess(overlay.lineno, metadata)


if __name__ == '__main__': unittest.main()
