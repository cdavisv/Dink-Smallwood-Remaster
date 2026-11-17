"""Treasure chest rows of families.json (15 and 16 Nov 2026): closed while the lid is down, open from frame 3 on.

Resolved with Scripts/art_coverage.py's mirror of DinkArtFamily::Resolve (sequence-and-frame row, then class row, then
plain sequence row), on the real families.json, with every mesh taken as present."""
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
from art_coverage import family_binding, load_families  # noqa: E402

CLOSED = '/Game/Dink/Photoreal/Props/SM_Chest_Small_PR.SM_Chest_Small_PR'
OPEN = '/Game/Dink/Photoreal/Props/SM_Chest_Small_Open_PR.SM_Chest_Small_Open_PR'


class AllPresent:
    def resolve(self, game_path):
        return True, ''


class ChestFamilyRowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notes = []
        cls.rows = load_families(AllPresent(), notes)[0]
        cls.notes = notes

    def test_no_chest_row_is_dropped_or_bound_twice(self):
        self.assertFalse([n for n in self.notes if 'chest' in n or '175 ' in n], self.notes)

    def test_the_placed_chest_is_closed(self):
        row = family_binding(self.rows, 175, 'chest_small', 1)
        self.assertEqual(row['mesh'], CLOSED)
        self.assertTrue(row['scripted'], 'every chest carries a ch1-* script')
        # a placement whose class is only known as chest_small (no frame) still takes the closed chest
        self.assertEqual(family_binding(self.rows, 175, 'chest_small')['mesh'], CLOSED)

    def test_the_lid_follows_the_pictures_of_the_opening(self):
        meshes = [family_binding(self.rows, 175, None, f)['mesh'] for f in range(1, 7)]
        self.assertEqual(meshes, [CLOSED, CLOSED, OPEN, OPEN, OPEN, OPEN])

    def test_the_saved_pictures_are_open(self):
        # ch1-* save editor_seq 175 with editor_frame 4 (seven scripts) or 6 (two): the next visit shows an open chest
        for frame in (4, 6):
            row = family_binding(self.rows, 175, None, frame)
            self.assertEqual(row['mesh'], OPEN)
            self.assertTrue(row['scripted'])

    def test_the_front_and_mirrored_chest_pictures_are_the_same_chest(self):
        # chst2 (176: the chest seen from the front, class chest_medium) and chst3 (177: turned the other way, class
        # chest_large) are the small chest's pictures from other sides, 44 and 59 px wide: the same two meshes by frame
        for seq, cls in ((176, 'chest_medium'), (177, 'chest_large')):
            meshes = [family_binding(self.rows, seq, cls, f)['mesh'] for f in range(1, 7)]
            self.assertEqual(meshes, [CLOSED, CLOSED, OPEN, OPEN, OPEN, OPEN], seq)
            self.assertTrue(all(family_binding(self.rows, seq, cls, f)['scripted'] for f in range(1, 7)), seq)
        # ch2-500 opens its 176 chest with the pictures of 177 and saves 177/6: open on the next visit
        self.assertEqual(family_binding(self.rows, 177, None, 6)['mesh'], OPEN)
        # no class row: a chest_medium or chest_large placement with a picture outside these frames keeps its card
        self.assertIsNone(family_binding(self.rows, 176, 'chest_medium'))
        self.assertIsNone(family_binding(self.rows, 177, 'chest_large'))


if __name__ == '__main__':
    unittest.main()
