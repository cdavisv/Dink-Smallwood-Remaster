"""The no-sprite exemption depends on declared identity AND every actual use."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'art_standard_check.py'
spec = importlib.util.spec_from_file_location('art_standard_architecture', SCRIPT)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
PACKAGE = '/Game/Dink/Fixtures/SM_TestRoof'
OBJECT = PACKAGE + '.SM_TestRoof'
DECLARATION = {'screens': [1], 'purpose': 'exposed interior roof adaptation'}


class ArchitecturePolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.art = self.root / 'SourceAssets/Art'
        self.data = self.root / 'Content/Dink/Data/Art'
        self.art.mkdir(parents=True)
        self.data.mkdir(parents=True)
        asset = self.root / 'Content/Dink/Fixtures/SM_TestRoof.uasset'
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b'fixture existence only; no native load')
        self.record = {'class': 'kit_piece', 'materials': ['MI_Stonebrook_Oak'],
                       'triangles': 10, 'content_path': PACKAGE,
                       'authored_architecture': dict(DECLARATION)}
        self.documents = {'room.json': {'schema': 'dink-art/1', 'screen': 1,
                                       'elements': [{'mesh': OBJECT}]}}
        for key, value in [('PROJECT', str(self.root)), ('ART', str(self.art)), ('DATA_ART', str(self.data))]:
            patcher = patch.object(C, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def result(self):
        (self.art / 'manifest.json').write_text(json.dumps({'assets': {'SM_TestRoof': self.record}}))
        for p in self.data.glob('*.json'):
            p.unlink()
        for name, data in self.documents.items():
            (self.data / name).write_text(json.dumps(data))
        result = C.check(argparse.Namespace())
        asset = result[0][('.', 'SM_TestRoof')]
        # package_of(root manifest) uses '.', preserving a fixture-independent key.
        exempt = C.authored_architecture_exempt(asset, {PACKAGE}, C.architecture_runtime_uses())
        return exempt, result[2]

    def assert_family_refused(self):
        exempt, violations = self.result()
        self.assertFalse(exempt)
        self.assertTrue(any(kind == 'family' for values in violations.values() for kind, _ in values))

    def test_three_kit_classes_require_actual_matching_elements(self):
        for kind in ('kit_piece', 'kit_wall', 'kit_ceiling'):
            with self.subTest(kind=kind):
                self.record['class'] = kind
                exempt, violations = self.result()
                self.assertTrue(exempt)
                self.assertEqual(dict(violations), {})

    def test_prop_and_building_classes_never_qualify(self):
        for kind in ('prop', 'prop_large', 'building', 'door'):
            with self.subTest(kind=kind):
                self.record['class'] = kind
                self.assert_family_refused()

    def test_name_and_source_record_without_declaration_are_not_enough(self):
        del self.record['authored_architecture']
        self.assert_family_refused()

    def test_declaration_shape_and_values_are_strict(self):
        bad = [None, {}, True, {'screens': [1]}, {'purpose': 'roof'},
               {'screens': [1], 'purpose': ''}, {'screens': [1], 'purpose': '  '},
               {'screens': [], 'purpose': 'roof'}, {'screens': [0], 'purpose': 'roof'},
               {'screens': [-1], 'purpose': 'roof'}, {'screens': [True], 'purpose': 'roof'},
               {'screens': [1.0], 'purpose': 'roof'}, {'screens': ['1'], 'purpose': 'roof'},
               {'screens': [1, 1], 'purpose': 'roof'},
               {'screens': [1], 'purpose': 'roof', 'waive_all': True}]
        for declaration in bad:
            with self.subTest(declaration=declaration):
                self.record['authored_architecture'] = declaration
                self.assert_family_refused()

    def test_different_or_malformed_runtime_screen_refuses(self):
        for screen in (2, 0, True, '1', None):
            with self.subTest(screen=screen):
                self.documents['room.json']['screen'] = screen
                self.assert_family_refused()

    def test_replacement_or_asset_list_use_refuses_even_with_valid_element(self):
        for field in ('replacements', 'assets'):
            with self.subTest(field=field):
                self.documents['room.json'][field] = [{'mesh': OBJECT}]
                self.assert_family_refused()
                del self.documents['room.json'][field]

    def test_other_schema_and_nested_element_use_refuse(self):
        self.documents['room.json']['schema'] = 'dink-creatures/1'
        self.assert_family_refused()
        self.documents['room.json']['schema'] = 'dink-art/1'
        self.documents['room.json']['elements'] = [{'child': {'mesh': OBJECT}}]
        self.assert_family_refused()

    def test_another_manifest_on_undeclared_screen_refuses(self):
        self.documents['other.json'] = {'schema': 'dink-art/1', 'screen': 2,
                                        'elements': [{'mesh': OBJECT}]}
        self.assert_family_refused()

    def test_context_and_family_uses_do_not_qualify_for_this_exemption(self):
        # Existing render-only/family rules stay independent; test THIS exemption.
        self.documents['room.json']['context'] = {}
        self.assertFalse(self.result()[0])
        del self.documents['room.json']['context']
        self.documents['families.json'] = {'schema': 'dink-art-families/1',
                                           'families': [{'family': 'real-fixture-family', 'mesh': OBJECT}]}
        self.assertFalse(self.result()[0])

    def test_absent_runtime_uses_and_conflicting_declarations_refuse(self):
        self.result()
        asset = C.load_sources()[0][('.', 'SM_TestRoof')]
        self.assertFalse(C.authored_architecture_exempt(asset, set(), {}))
        self.assertFalse(C.authored_architecture_exempt(asset, {PACKAGE}, {}))
        asset.architecture_declarations.append({'screens': [2], 'purpose': 'different'})
        self.assertFalse(C.authored_architecture_exempt(asset, {PACKAGE}, C.architecture_runtime_uses()))


if __name__ == '__main__':
    unittest.main()
