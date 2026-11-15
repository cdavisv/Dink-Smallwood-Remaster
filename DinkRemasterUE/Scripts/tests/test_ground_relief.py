"""Parallax relief of the ground (M_Env_Terrain): every layer of the catalogue gets a depth from the rule in
terrain_layers.json, the world export and the material builder use the same rule, and the importer passes it on."""
from pathlib import Path
import json
import re
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
try:
    from export_import_bundle import load_terrain_catalogue  # noqa: E402
except ImportError as error:    # the world export needs numpy and Pillow
    raise unittest.SkipTest('world export helpers need numpy and Pillow: %s' % error)


class GroundRelief(unittest.TestCase):
    def setUp(self):
        self.cat = load_terrain_catalogue(PROJECT)
        self.raw = json.loads((PROJECT / 'SourceAssets/Art/PhotorealPass/Environment/terrain_layers.json').read_text())
        self.sets = {s['name']: s for s in json.loads((PROJECT / 'SourceAssets/Art/PhotorealPass/Terrain/manifest.json').read_text())['sets']}

    def test_every_layer_has_a_depth_within_the_rule(self):
        rule = self.raw['relief']
        for name, layer in self.cat['resolved_layers'].items():
            self.assertIn('relief_cm', layer, name)
            self.assertGreaterEqual(layer['relief_cm'], 0.0, name)
            row = self.raw['layers'][name]
            if 'relief_cm' in row:
                self.assertEqual(layer['relief_cm'], round(float(row['relief_cm']), 2), name)
            else:
                self.assertLessEqual(layer['relief_cm'], rule['max_cm'], name)
                k = rule['structured_exaggeration' if row.get('structured') else 'exaggeration']
                want = min(self.sets[row['set']]['height_range_m'] * 100.0 * k, rule['max_cm'])
                self.assertAlmostEqual(layer['relief_cm'], want, delta=0.006, msg=name)

    def test_material_builder_and_importer_carry_the_depth(self):
        builder = (PROJECT / 'Scripts/import_environment_materials.py').read_text()
        for key in ("'relief_cm'", "'exaggeration'", "'structured_exaggeration'", "'max_cm'", "'default_cm'", "Relief{L}Cm"):
            self.assertIn(key, builder, key)
        bundle = (PROJECT / 'Plugins/DinkImport/Source/DinkImport/Private/DinkImportBundle.cpp').read_text()
        self.assertIn('TEXT("relief_cm")', bundle)
        assets = (PROJECT / 'Plugins/DinkImport/Source/DinkImport/Private/DinkGreyboxAssets.cpp').read_text()
        self.assertRegex(assets, r'TEXT\("Relief"\)\) \+ Suffix\[I\] \+ TEXT\("Cm"\)')
        self.assertIn('L.ReliefCm', assets)   # part of the per-screen instance's hash: a new depth rebuilds it

    def test_relief_is_presentation_only(self):
        # the ground mesh stays the flat sheet: the importer writes its quads at height 0 and the collision mesh apart
        assets = (PROJECT / 'Plugins/DinkImport/Source/DinkImport/Private/DinkGreyboxAssets.cpp').read_text()
        self.assertIn('FVector3f P[4] = {At(X0, Y0, 0), At(X1, Y0, 0), At(X1, Y1, 0), At(X0, Y1, 0)};', assets)
        self.assertFalse(re.search(r'ReliefCm[^;\n]*(Collision|Hardness|BodySetup)', assets))


if __name__ == '__main__':
    unittest.main()
