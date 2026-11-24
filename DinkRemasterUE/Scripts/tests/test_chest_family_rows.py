"""Treasure chest rows of families.json (15 to 17 Nov 2026): one mesh per picture of the opening, the lid at that picture's angle.

Resolved with Scripts/art_coverage.py's mirror of DinkArtFamily::Resolve (sequence-and-frame row, then class row, then
plain sequence row), on the real families.json, with every mesh taken as present."""
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
from art_coverage import family_binding, load_families  # noqa: E402

CLOSED = '/Game/Dink/Photoreal/Props/SM_Chest_Small_PR.SM_Chest_Small_PR'
# the lid's angle on frames 2 to 6 (FableF/chest_states: the Props chest with its lid turned on the hinges)
LID = ['/Game/Dink/Photoreal/FableF/SM_Chest_Small_Lid%03d_PR.SM_Chest_Small_Lid%03d_PR' % (a, a) for a in (13, 44, 74, 96, 110)]
STATES = [CLOSED] + LID


class AllPresent:
    def resolve(self, game_path):
        return True, ''


class ChestFamilyRowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notes = []
        cls.rows = load_families(AllPresent(), notes)[0]
        cls.notes = notes

    @staticmethod
    def raw_rows(seq):
        """families.json's own rows of a chest sequence by frame (keys the coverage mirror does not carry)"""
        import json
        rows = json.loads((PROJECT / 'Content/Dink/Data/Art/families.json').read_text())['families']
        return {r['frame']: r for r in rows if r['family'].startswith('%d ' % seq) and 'frame' in r}

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
        self.assertEqual(meshes, STATES)
        # every state stands where the closed chest stands (an open lid widens the bounds), and all six are turned alike
        raw = self.raw_rows(175)
        for f in range(1, 7):      # frame 1 too: ch2-500 plays 177's frame 1 on a 176 chest
            self.assertEqual(raw[f].get('stands_as'), CLOSED, f)
        self.assertEqual(len({raw[f].get('yaw_offset', 0) for f in range(1, 7)}), 1)
        # on the 1997 hardbox, not on the middle of a picture that includes the chest's shadow
        self.assertEqual({raw[f].get('anchor') for f in range(1, 7)}, {'hardbox'})

    def test_the_saved_pictures_are_open(self):
        # ch1-* save editor_seq 175 with editor_frame 4 (seven scripts) or 6 (two): the next visit shows an open chest
        # with the lid where that picture has it: two thirds up (frame 4), right up and leaning back (frame 6)
        for frame in (4, 6):
            row = family_binding(self.rows, 175, None, frame)
            self.assertEqual(row['mesh'], STATES[frame - 1])
            self.assertTrue(row['scripted'])

    def test_the_front_and_mirrored_chest_pictures_are_the_same_chest(self):
        # chst2 (176: the chest seen from the front, class chest_medium) and chst3 (177: turned the other way, class
        # chest_large) are the small chest's pictures from other sides, 44 and 59 px wide: the same meshes by frame
        for seq, cls in ((176, 'chest_medium'), (177, 'chest_large')):
            meshes = [family_binding(self.rows, seq, cls, f)['mesh'] for f in range(1, 7)]
            self.assertEqual(meshes, STATES, seq)
            self.assertTrue(all(family_binding(self.rows, seq, cls, f)['scripted'] for f in range(1, 7)), seq)
        # ch2-500 opens its 176 chest with the pictures of 177 and saves 177/6: open on the next visit
        self.assertEqual(family_binding(self.rows, 177, None, 6)['mesh'], STATES[5])
        # 1997 draws 175 from the front right, 176 from the front, 177 from the front left: three different turns
        self.assertEqual(len({self.raw_rows(seq)[1].get('yaw_offset', 0) for seq in (175, 176, 177)}), 3)
        # no class row: a chest_medium or chest_large placement with a picture outside these frames keeps its card
        self.assertIsNone(family_binding(self.rows, 176, 'chest_medium'))
        self.assertIsNone(family_binding(self.rows, 177, 'chest_large'))


if __name__ == '__main__':
    unittest.main()
