"""Exercise publication against real changed files and stale verification receipts."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publish_floor_surface as publish


class FloorPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.house = self.root / 'Content/Dink/Data/Art/stonebrook.json'
        self.house.parent.mkdir(parents=True)
        self.document = {'schema': 'dink-art/1', 'screen': 1,
                         'assets': [{'mesh': publish.OLD, 'expected_size_cm': [200, 200, 14]}],
                         'elements': [{'name': 'Floor_' + str(i), 'mesh': publish.OLD,
                                       'world_cm': [i * 200, 0, 0], 'collision': True} for i in range(56)],
                         'lights': [{'intensity': 40}], 'warp_overrides': [{'extent': [40, 30, 100]}]}
        self.house.write_text(json.dumps(self.document, indent=2) + '\n')
        self.other = self.root / 'Content/Dink/Data/AI/adaptation.ini'
        self.other.parent.mkdir(parents=True)
        self.other.write_text('original brain values\n')
        source = self.root / 'SourceAssets/Art/Stonebrook/Refinements/FloorOakV1'
        source.mkdir(parents=True)
        texture = source / 'texture.png'
        texture.write_bytes(b'approved source pixels')
        row = {'file': texture.name, 'sha256': publish.sha(texture)}
        self.texture = texture
        manifest = source / 'material_manifest.json'
        manifest.write_text(json.dumps({'textures': {'BC': row}, 'source_files': {}, 'source_image': row}))
        importer = self.root / 'Scripts/import_floor_surface.py'
        importer.parent.mkdir()
        importer.write_text('verified native importer\n')
        names = ['Content/Dink/Kits/Stonebrook/Refinements/FloorOakV1/SM_Floor_Oak_2m_01.uasset',
                 'Content/Dink/Materials/Stonebrook/Refinements/MI_Stonebrook_FloorOakV1.uasset']
        names += ['Content/Dink/Textures/Stonebrook/Refinements/T_Stonebrook_FloorOakV1_' + c + '.uasset'
                  for c in ('BC', 'N', 'ORM')]
        packages = {}
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('native saved ' + name).encode())
            packages[name] = publish.sha(path)
        self.package = self.root / names[0]
        self.verify = self.root / 'verified.json'
        self.verify.write_text(json.dumps({'passed': True, 'mode': 'verify', 'project': str(self.root),
            'native_geometry_uv_nails_collision_nanite_unchanged': True,
            'protected_changes': [], 'runtime_data_changes': [],
            'runtime_data_sha256': {str(p.relative_to(self.root)): publish.sha(p) for p in (self.house, self.other)},
            'source_manifest_sha256': publish.sha(manifest), 'importer_sha256': publish.sha(importer),
            'saved_package_sha256': packages}))

    def run_publisher(self, apply=False):
        argv = ['publish_floor_surface.py', '--project', str(self.root), '--verification', str(self.verify)]
        if apply:
            argv.append('--apply')
        with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            publish.main()

    def test_verified_publication_and_repeated_checks_preserve_the_apply_receipt(self):
        self.run_publisher(apply=True)
        expected = json.loads(json.dumps(self.document))
        for row in expected['assets'] + expected['elements']:
            row['mesh'] = publish.NEW
        self.assertEqual(json.loads(self.house.read_text()), expected)
        applied = self.root / 'Saved/Art/floor_surface_publication.json'
        pinned = applied.read_bytes()
        self.run_publisher()
        self.run_publisher()
        self.assertEqual(applied.read_bytes(), pinned)
        self.run_publisher(apply=True)
        self.run_publisher()

    def test_intervening_house_transform_collision_light_and_warp_edits_are_rejected(self):
        original = self.house.read_bytes()
        mutations = [lambda d: d['elements'][0]['world_cm'].__setitem__(0, 123),
                     lambda d: d['elements'][0].__setitem__('collision', False),
                     lambda d: d['lights'][0].__setitem__('intensity', 400),
                     lambda d: d['warp_overrides'][0]['extent'].__setitem__(0, 400)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                document = json.loads(original)
                mutate(document)
                self.house.write_text(json.dumps(document))
                changed = self.house.read_bytes()
                with self.assertRaises(AssertionError):
                    self.run_publisher(apply=True)
                self.assertEqual(self.house.read_bytes(), changed)
        self.house.write_bytes(original)

    def test_other_gameplay_data_drift_is_rejected(self):
        self.other.write_text('changed brain values\n')
        with self.assertRaises(AssertionError):
            self.run_publisher(apply=True)

    def test_new_and_missing_gameplay_data_are_rejected(self):
        extra = self.other.with_name('new.ini')
        extra.write_text('new values\n')
        with self.assertRaises(AssertionError):
            self.run_publisher(apply=True)
        extra.unlink()
        self.other.unlink()
        with self.assertRaises(AssertionError):
            self.run_publisher(apply=True)

    def test_intervening_edit_after_publication_cannot_use_the_idempotent_exception(self):
        self.run_publisher(apply=True)
        document = json.loads(self.house.read_text())
        document['elements'][0]['collision'] = False
        self.house.write_text(json.dumps(document))
        with self.assertRaises(AssertionError):
            self.run_publisher(apply=True)

    def test_stale_saved_package_is_rejected(self):
        self.package.write_bytes(b'changed native mesh')
        with self.assertRaises(AssertionError):
            self.run_publisher(apply=True)

    def test_stale_source_pixels_are_rejected_even_with_an_unchanged_manifest(self):
        self.texture.write_bytes(b'new source pixels')
        with self.assertRaises(AssertionError):
            self.run_publisher(apply=True)


if __name__ == '__main__':
    unittest.main()
