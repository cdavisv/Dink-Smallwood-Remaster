"""sprite_pictures.json (picture cards of script sprites, A53) matches the extracted 1997 sequences."""
import importlib.util
import json
from pathlib import Path
import unittest

UE = Path(__file__).resolve().parents[2]
SCRIPT = UE / 'Scripts/export_sprite_pictures.py'
spec = importlib.util.spec_from_file_location('export_sprite_pictures', SCRIPT)
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
DATA = UE / 'Content/Dink/Data/Art/sprite_pictures.json'
DINKEX = UE.parent / 'tools/dinkex/out/sequences.json'


class SpritePictures(unittest.TestCase):
    def test_filter_and_format(self):
        seqs = [{'seq': 10, 'path': 'tiles/s', 'frames': [{'frame': 1, 'width': 50, 'height': 50, 'image': 'a.png'}]},
                {'seq': 12, 'path': 'graphics/dink/idle/ds-i2-', 'frames': [{'frame': 1, 'width': 9, 'height': 9, 'image': 'b.png'}]},
                {'seq': 581, 'path': 'graphics/people/gnome/green/c13w1-', 'ini_origin': {'x': 29, 'y': 55},
                 'frames': [{'frame': 1, 'width': 51, 'height': 74, 'origin': {'x': 29, 'y': 55}, 'image': 'c.png'},
                            {'frame': 2, 'width': 0, 'height': 0, 'empty': True}]}]
        self.assertEqual(S.pictures(seqs), {'581_01': [51, 74, 29, 55]})

    def test_committed_file(self):
        data = json.loads(DATA.read_text())
        self.assertEqual(data['schema'], 'dink-sprite-pictures/1')
        pics = data['pictures']
        # The green gnome dink.ini puts in 581-589, and Seth's pose and walks that s7-mil.c's init lines load over it.
        for key in ('581_01', '583_01', '587_01', '589_01', 'init_pose_01', 'init_seth1w_01', 'init_seth9w_08'):
            self.assertIn(key, pics)
        self.assertEqual(pics['init_pose_01'], [66, 160, 41, 129])   # s7-mil.c:13: origin 41,129 from the line
        self.assertTrue(all(len(v) == 4 and v[0] > 0 and v[1] > 0 for v in pics.values()))
        self.assertFalse(any(k.split('_')[0] in ('10',) for k in pics))

    def test_init_lines(self):
        story = {'s7-mil': 'init("load_sequence_now graphics\\effects\\magic\\pose 580 75 41 129 -30 -16 31 10");\n'
                           'init("load_sequence_now graphics\\dink\\idle\\ds-i2- 12 250 33 70 -12 -9 12 9");',
                 'x': 'init("load_sequence_now graphics\\effects\\magic\\pose 580 75 41 129 -30 -16 31 10");'}
        self.assertEqual(S.init_lines(story), [(580, 'graphics/effects/magic/pose', 41, 129, '')])
        self.assertEqual(S.init_stem('graphics/effects/magic/seth1w'), 'init_seth1w')

    @unittest.skipUnless(DINKEX.exists(), 'tools/dinkex/out not extracted')
    def test_up_to_date(self):
        seqs = json.loads(DINKEX.read_text())['sequences']
        pics = json.loads(DATA.read_text())['pictures']
        self.assertEqual({k: v for k, v in pics.items() if not k.startswith('init_')}, S.pictures(seqs))


if __name__ == '__main__':
    unittest.main()
