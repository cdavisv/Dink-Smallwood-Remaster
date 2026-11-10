"""Owner/source/geometry preservation tests; no native rendering claim."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import math
import os
import runpy
import sys
import tempfile
import types
import unittest
from unittest import mock

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
        validate = next(n.lineno for n in calls if n.func.attr == 'preflight_source')
        first_tools = min(n.lineno for n in calls if n.func.attr in ['get_asset_tools', 'execute_console_command'])
        self.assertLess(validate, first_tools)
        overlay = next(n for n in calls if n.func.attr == 'apply_lighting')
        self.assertTrue(any(k.arg == 'generated_from_legacy_layout' and isinstance(k.value, ast.Constant) and k.value.value is True for k in overlay.keywords))
        metadata = max(n.lineno for n in calls if n.func.attr == 'write_text')
        self.assertLess(overlay.lineno, metadata)

    def test_complete_preflight_rejects_runtime_float_and_scaled_aperture_mismatches(self):
        invalid = [('source_width_cm', 82.5), ('source_width_cm', 81.812499999),
                   ('source_height_cm', 135.999999999), ('lumens_per_window', 1e300),
                   ('radius_cm', 1e-300), ('kelvin', 1e-300)]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                profile = copy.deepcopy(self.profile); profile['daylight'][key] = value
                with self.assertRaises(ValueError): lighting.preflight_source(profile, self.layout)
        rows = lighting.preflight_source(self.profile, self.layout)
        self.assertEqual(rows, self.manifest['lights'])

    def test_complete_preflight_validates_generated_practical_specs(self):
        profile = copy.deepcopy(self.profile)
        for group in ['practical_points', 'legacy_lights']: profile[group][0]['kind'] = 'unsupported'
        with self.assertRaises(ValueError): lighting.preflight_source(profile, self.layout)

    def _entry_fixture(self, root, profile):
        """Only text/hash witnesses; no FBX/model/native processing is claimed."""
        for relative in profile['source_files_sha256']:
            path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'entry-preflight source hash witness')
            profile['source_files_sha256'][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        source = root / 'SourceAssets/Art/Stonebrook'
        (source / 'room_layout.json').write_text(json.dumps(self.layout))
        (source / 'art_manifest.json').write_text(json.dumps({'assets': {}, 'materials': {}}))
        path = root / lighting.PROFILE; path.parent.mkdir(parents=True); path.write_text(json.dumps(profile))
        scripts = root / 'Scripts'; scripts.mkdir()
        (scripts / 'house_lighting.py').write_bytes((P / 'Scripts/house_lighting.py').read_bytes())
        data = root / 'Content/Dink/Data/Art/stonebrook.json'; data.parent.mkdir(parents=True)
        data.write_text(json.dumps(self.manifest))
        return data

    def test_actual_importer_entry_rejects_invalid_lighting_before_any_native_work(self):
        class NativeWorkReached(RuntimeError): pass
        variants = [(None, None), ('source_width_cm', 82.5), ('lumens_per_window', 1e300), ('radius_cm', 1e-300)]
        for key, value in variants:
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as name:
                root = Path(name); profile = copy.deepcopy(self.profile)
                if key: profile['daylight'][key] = value
                data = self._entry_fixture(root, profile); before = data.read_bytes(); native_calls = []
                stub = types.ModuleType('unreal')
                stub.Paths = types.SimpleNamespace(project_dir=lambda: str(root), convert_relative_path_to_full=lambda x: x)
                def native_access():
                    native_calls.append('get_asset_tools')
                    raise NativeWorkReached('First native access; import/material/save must not run for invalid input')
                stub.AssetToolsHelpers = types.SimpleNamespace(get_asset_tools=native_access)
                def unexpected(attribute):
                    native_calls.append(attribute)
                    raise NativeWorkReached('Unexpected native access: ' + attribute)
                stub.__getattr__ = unexpected
                environment = {k:v for k,v in os.environ.items() if not k.startswith('DINK_ART_')}
                with mock.patch.dict(sys.modules, {'unreal': stub}), mock.patch.dict(os.environ, environment, clear=True):
                    if key is None:
                        with self.assertRaises(NativeWorkReached): runpy.run_path(str(P / 'Scripts/import_stonebrook_art.py'), run_name='__main__')
                        self.assertEqual(native_calls, ['get_asset_tools'])  # Positive control actually traversed preflight.
                    else:
                        with self.assertRaisesRegex(ValueError, 'scaled clear aperture|runtime float'):
                            runpy.run_path(str(P / 'Scripts/import_stonebrook_art.py'), run_name='__main__')
                        self.assertEqual(native_calls, [])
                self.assertEqual(data.read_bytes(), before)

    def test_actual_standalone_apply_entry_rejects_same_invalid_profiles_without_writes(self):
        for key, value in [('source_width_cm', 82.5), ('lumens_per_window', 1e300), ('radius_cm', 1e-300)]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as name:
                root = Path(name); profile = copy.deepcopy(self.profile); profile['daylight'][key] = value
                data = self._entry_fixture(root, profile); before = data.read_bytes()
                with mock.patch.object(sys, 'argv', ['house_lighting.py', '--apply']):
                    with self.assertRaisesRegex(ValueError, 'scaled clear aperture|runtime float'):
                        runpy.run_path(str(root / 'Scripts/house_lighting.py'), run_name='__main__')
                self.assertEqual(data.read_bytes(), before)


if __name__ == '__main__': unittest.main()
