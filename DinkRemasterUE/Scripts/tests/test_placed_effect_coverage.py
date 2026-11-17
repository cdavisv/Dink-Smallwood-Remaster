"""Effect rows of families.json as Scripts/art_coverage.py reads them (the mirror of UDinkArtFamilySubsystem::DressActor)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import art_coverage  # noqa: E402


class Assets:
    def resolve(self, path):
        return (not path.endswith('MI_Missing'), 'file not found')


def load(rows):
    with tempfile.TemporaryDirectory() as tmp:
        art = Path(tmp) / 'Content' / 'Dink' / 'Data' / 'Art'
        art.mkdir(parents=True)
        (art / 'families.json').write_text(json.dumps({'schema': 'dink-art-families/1', 'families': rows}))
        notes = []
        with mock.patch.object(art_coverage, 'PROJECT', tmp):
            return art_coverage.load_families(Assets(), notes), notes


class PlacedEffectRows(unittest.TestCase):
    def test_placed_effect_row_binds_with_its_material(self):
        (rows, _, _), notes = load([{'family': 'fire_fx', 'effect': '/Game/Dink/A/MI_Fire.MI_Fire', 'effect_placed': True}])
        self.assertEqual(notes, [])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]['placed_fx'])
        self.assertEqual(rows[0]['mesh'], '/Game/Dink/A/MI_Fire.MI_Fire')

    def test_script_only_effect_row_binds_no_placement(self):
        (rows, _, _), notes = load([{'family': 'sparkle_fx', 'effect': '/Game/Dink/A/MI_Sparkle.MI_Sparkle', 'effect_size_cm': 70}])
        self.assertEqual(rows, [])
        self.assertEqual(len(notes), 1)

    def test_missing_material_leaves_the_row_out(self):
        (rows, _, _), notes = load([{'family': 'fire_fx', 'effect': '/Game/Dink/A/MI_Missing', 'effect_placed': True}])
        self.assertEqual(rows, [])
        self.assertIn('MI_Missing', notes[0])

    def test_mesh_rows_are_not_placed_effects(self):
        (rows, _, _), _ = load([{'family': 'barrel', 'mesh': '/Game/Dink/A/SM_Barrel.SM_Barrel'}])
        self.assertFalse(rows[0]['placed_fx'])


if __name__ == '__main__':
    unittest.main()
